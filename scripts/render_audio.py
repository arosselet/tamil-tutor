#!/usr/bin/env python3
"""
Generate multi-voice Tamil podcast audio from a markdown script.

Usage:
    python scripts/render_audio.py <input_script.md> <output.mp3>

Example:
    python scripts/render_audio.py content/scripts/tier1_mission1.md audio/tier1_mission1.mp3

Reads dialogues prefixed with **Speaker Name:**, generates TTS audio
segments using edge-tts or Google Chirp, and stitches them into a single MP3.
Supports a # Voice Map block in markdown comments for explicit voice assignment.
"""

import re
import os
import asyncio
import argparse
import random
import json
import subprocess
import time

import edge_tts
try:
    from google.cloud import texttospeech
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

# Voice pools — Indian Tamil
# Expanded Chirp pool with 30+ voices
_CHIRP_POOL_MALE = [
    "ta-IN-Chirp3-HD-Achird", "ta-IN-Chirp3-HD-Algenib", "ta-IN-Chirp3-HD-Algieba",
    "ta-IN-Chirp3-HD-Alnilam", "ta-IN-Chirp3-HD-Charon", "ta-IN-Chirp3-HD-Enceladus",
    "ta-IN-Chirp3-HD-Fenrir", "ta-IN-Chirp3-HD-Iapetus", "ta-IN-Chirp3-HD-Orus",
    "ta-IN-Chirp3-HD-Puck", "ta-IN-Chirp3-HD-Rasalgethi", "ta-IN-Chirp3-HD-Sadachbia",
    "ta-IN-Chirp3-HD-Sadaltager", "ta-IN-Chirp3-HD-Schedar", "ta-IN-Chirp3-HD-Umbriel",
    "ta-IN-Chirp3-HD-Zubenelgenubi"
]

_CHIRP_POOL_FEMALE = [
    "ta-IN-Chirp3-HD-Achernar", "ta-IN-Chirp3-HD-Aoede", "ta-IN-Chirp3-HD-Autonoe",
    "ta-IN-Chirp3-HD-Callirrhoe", "ta-IN-Chirp3-HD-Despina", "ta-IN-Chirp3-HD-Erinome",
    "ta-IN-Chirp3-HD-Gacrux", "ta-IN-Chirp3-HD-Kore", "ta-IN-Chirp3-HD-Laomedeia",
    "ta-IN-Chirp3-HD-Leda", "ta-IN-Chirp3-HD-Pulcherrima", "ta-IN-Chirp3-HD-Sulafat",
    "ta-IN-Chirp3-HD-Vindemiatrix", "ta-IN-Chirp3-HD-Zephyr"
]

_CHIRP_POOL = _CHIRP_POOL_MALE + _CHIRP_POOL_FEMALE

_WAVENET_POOL_MALE = ["ta-IN-Wavenet-B", "ta-IN-Wavenet-D"]
_WAVENET_POOL_FEMALE = ["ta-IN-Wavenet-A", "ta-IN-Wavenet-C"]
_WAVENET_POOL = _WAVENET_POOL_MALE + _WAVENET_POOL_FEMALE

_EDGE_POOL_MALE = ["ta-IN-ValluvarNeural"]
_EDGE_POOL_FEMALE = ["ta-IN-PallaviNeural"]
_EDGE_POOL = _EDGE_POOL_MALE + _EDGE_POOL_FEMALE

# Voice tuning for distinctiveness (Edge only)
EDGE_VOICE_OPTS = {
    "ta-IN-PallaviNeural": {"rate": "+0%", "pitch": "-5Hz"},
    "ta-IN-ValluvarNeural": {"rate": "+0%", "pitch": "-5Hz"},
}

# Regex: matches "**Speaker:** text"
SPEAKER_RE = re.compile(
    r"^\s*(?:\*\s*)?\*\*\s*([^:]+)\s*:\s*(?:\*\*\s*)?(.*)", re.IGNORECASE
)
PAUSE_RE = re.compile(r"\[Pause:\s*(\d+)\s*sec.*\]", re.IGNORECASE)
EMBED_RE = re.compile(r"\[Intercept (audio )?plays\]", re.IGNORECASE)
VOICE_MAP_RE = re.compile(r"Voice Map\s*:\s*(\{.*?\})", re.DOTALL | re.IGNORECASE)

def parse_script(file_path: str) -> tuple[list[dict], dict]:
    """Parse a markdown script for dialogue lines, pauses, and voice mapping."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract Voice Map from comments if present
    voice_map = {}
    map_match = VOICE_MAP_RE.search(content)
    if map_match:
        try:
            voice_map = json.loads(map_match.group(1))
            print(f"✅ Found explicit Voice Map: {voice_map}")
        except json.JSONDecodeError:
            print("⚠️ Warning: Failed to parse Voice Map JSON.")

    lines = content.splitlines()
    dialogue = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        pause_match = PAUSE_RE.search(line)
        if pause_match:
            seconds = int(pause_match.group(1))
            dialogue.append({"speaker": "PAUSE", "seconds": seconds})
            continue

        if EMBED_RE.search(line):
            dialogue.append({"speaker": "EMBED_INTERCEPT"})
            continue

        if line == "---":
            dialogue.append({"speaker": "PAUSE", "seconds": 1})
            continue

        match = SPEAKER_RE.match(line)
        if match:
            speaker = match.group(1).strip().upper()
            text = match.group(2).strip()

            if text:
                dialogue.append({"speaker": speaker, "text": text})

    # Coalesce consecutive pauses
    final_dialogue = []
    for item in dialogue:
        if item["speaker"] == "PAUSE":
            if final_dialogue and final_dialogue[-1]["speaker"] == "PAUSE":
                final_dialogue[-1]["seconds"] += item["seconds"]
            else:
                final_dialogue.append(item)
        else:
            final_dialogue.append(item)

    return final_dialogue, voice_map


def clean_for_tts(text: str) -> str:
    """Clean text for TTS consumption."""
    text = re.sub(r"\s*\(.*?\)\s*", " ", text)
    replacements = {"JSON": "jay-son", "CLI": "C-L-I"}
    for word, phonetic in replacements.items():
        text = re.sub(rf"\b{word}\b", phonetic, text, flags=re.IGNORECASE)
    text = text.replace(".", "")
    text = re.sub(r"[*_#`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def generate_segment_edge(text: str, voice: str, index: int, temp_dir: str) -> str:
    """Generate a single audio segment using edge-tts."""
    opts = EDGE_VOICE_OPTS.get(voice, {"rate": "+0%", "pitch": "+0Hz"})
    communicate = edge_tts.Communicate(text, voice, rate=opts["rate"], pitch=opts["pitch"])
    filename = os.path.join(temp_dir, f"segment_{index:04d}.mp3")
    await communicate.save(filename)
    return filename


async def generate_segment_google(text: str, voice: str, index: int, temp_dir: str, max_retries: int = 5) -> str:
    """Generate a single audio segment using Google Cloud TTS with exponential backoff."""
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice_params = texttospeech.VoiceSelectionParams(language_code="ta-IN", name=voice)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, sample_rate_hertz=24000)
    for attempt in range(max_retries):
        try:
            response = client.synthesize_speech(input=input_text, voice=voice_params, audio_config=audio_config)
            filename = os.path.join(temp_dir, f"segment_{index:04d}.mp3")
            with open(filename, "wb") as out:
                out.write(response.audio_content)
            return filename
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt + random.random()
            print(f"   ⚠️ Retry {attempt+1}/{max_retries} after {wait:.1f}s — {e}")
            time.sleep(wait)


def get_raw_mp3_frames(filepath: str) -> bytes:
    """Extract raw MPEG audio chunk."""
    with open(filepath, "rb") as f:
        data = f.read()
    offset = 0
    if data.startswith(b"ID3"):
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        offset = 10 + size
    if offset < len(data) - 1 and data[offset] == 0xFF and (data[offset+1] & 0xE0) == 0xE0:
        padding = (data[offset+2] & 0x02) >> 1
        frame_len = 144 + padding
        frame_data = data[offset:offset+frame_len]
        if b"Xing" in frame_data or b"Info" in frame_data:
            offset += frame_len
    end_offset = len(data)
    if end_offset >= 128 and data[-128:].startswith(b"TAG"):
        end_offset -= 128
    return data[offset:end_offset]


import base64
SILENCE_FRAME_B64 = "//NkxJoiPA4Vgc1AAVXPcXO05CbzflKqdX8LXO/PQy7v6mbnkYz3BsVdxH7xI1psbFEYzt6Fxl0w17Szht3EmOWRKhJANxpojDXhk+E+3qNp+0+oomHuYca0xPxKUOihtdfcvPB+yzd2o2Sbh5zuLHVDDK9juB8rHhbq9lYT0XEdvYWKCGEeTvz8YP2XWipB"
SILENCE_FRAME = base64.b64decode(SILENCE_FRAME_B64)

def assign_voices(dialogue, voice_map, provider, voice_type):
    """
    Assign voices to speakers. 
    Uses a random selection from the pool for each name encountered.
    Supports (M) or (F) in the speaker name for explicit gender casting.
    """
    speakers = set(d["speaker"] for d in dialogue if d["speaker"] != "PAUSE" and d["speaker"] != "EMBED_INTERCEPT")
    
    assigned = {}
    
    # 1. Respect explicit map (overrides)
    for speaker, voice in voice_map.items():
        assigned[speaker.upper()] = voice

    # 2. Select pool
    if provider == "google":
        pool_male = list(_CHIRP_POOL_MALE if voice_type == "chirp" else _WAVENET_POOL_MALE)
        pool_female = list(_CHIRP_POOL_FEMALE if voice_type == "chirp" else _WAVENET_POOL_FEMALE)
        pool_any = list(_CHIRP_POOL if voice_type == "chirp" else _WAVENET_POOL)
    else:
        pool_male = list(_EDGE_POOL_MALE)
        pool_female = list(_EDGE_POOL_FEMALE)
        pool_any = list(_EDGE_POOL)

    available_male = [v for v in pool_male if v not in assigned.values()]
    if not available_male: available_male = list(pool_male)
    random.shuffle(available_male)

    available_female = [v for v in pool_female if v not in assigned.values()]
    if not available_female: available_female = list(pool_female)
    random.shuffle(available_female)

    available_any = [v for v in pool_any if v not in assigned.values()]
    if not available_any: available_any = list(pool_any)
    random.shuffle(available_any)
    
    for s in sorted(list(speakers)):
        s_upper = s.upper()
        if s_upper not in assigned:
            if "(M)" in s_upper or "(MALE)" in s_upper:
                assigned[s_upper] = available_male.pop() if available_male else random.choice(pool_male)
            elif "(F)" in s_upper or "(FEMALE)" in s_upper:
                assigned[s_upper] = available_female.pop() if available_female else random.choice(pool_female)
            else:
                assigned[s_upper] = available_any.pop() if available_any else random.choice(pool_any)

    return assigned

async def main():
    parser = argparse.ArgumentParser(description="Generate Multi-Voice Tamil Podcast Audio")
    parser.add_argument("input_file", help="Input markdown script")
    parser.add_argument("output_file", help="Output MP3 file")
    parser.add_argument("--provider", choices=["edge", "google"], default="google", help="TTS provider (default: google)")
    parser.add_argument("--voice-type", choices=["chirp", "wavenet"], default="chirp", help="Google voice tier (default: chirp)")
    args = parser.parse_args()

    print(f"📖 Parsing {args.input_file}...")
    dialogue, voice_map = parse_script(args.input_file)
    if not dialogue:
        print("❌ No dialogue lines found!")
        return

    speaker_assignments = assign_voices(dialogue, voice_map, args.provider, args.voice_type)
    print(f"🎭 Cast Assignments:")
    for s, v in speaker_assignments.items():
        print(f"   - {s}: {v}")

    temp_dir = "temp_audio_segments"
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.output_file) or ".", exist_ok=True)

    print("🎙️ Generating audio segments...")
    final_audio_data = bytearray()

    for i, line in enumerate(dialogue):
        speaker = line["speaker"]
        if speaker == "PAUSE":
            seconds = line.get("seconds", 1)
            final_audio_data.extend(SILENCE_FRAME * int(seconds * 41.666))
            continue

        if speaker == "EMBED_INTERCEPT":
            print(f"   [{i+1}/{len(dialogue)}] ⚠️ Skipping [Intercept audio plays] — deprecated in single-script mode")
            continue

        voice = speaker_assignments.get(speaker)
        clean_text = clean_for_tts(line["text"])
        if not clean_text: continue

        print(f"   [{i+1}/{len(dialogue)}] {speaker} ({voice}): {clean_text[:40]}...")

        if args.provider == "google":
            seg_file = await generate_segment_google(clean_text, voice, i, temp_dir)
        else:
            seg_file = await generate_segment_edge(clean_text, voice, i, temp_dir)

        final_audio_data.extend(get_raw_mp3_frames(seg_file))
        final_audio_data.extend(SILENCE_FRAME * 10) # 250ms breath
        os.remove(seg_file)

    # Save outputs
    for folder in ["audio", "published_audio"]:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, os.path.basename(args.output_file))
        with open(path, "wb") as f:
            f.write(final_audio_data)
        print(f"💾 Saved → {path}")

    os.rmdir(temp_dir)
    print(f"✅ Success! ({len(final_audio_data)/(1024*1024):.1f} MB)")

    # Lifecycle hooks
    try:
        subprocess.run(["python3", "scripts/rebuild_rss.py"], check=True)
        subprocess.run(["git", "add", "published_audio/", "rss.xml"], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"Add lesson: {os.path.basename(args.output_file)}"], check=True)
            subprocess.run(["git", "push"], check=True)
    except Exception as e:
        print(f"⚠️ Lifecycle hooks failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
