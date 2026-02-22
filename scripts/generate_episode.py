#!/usr/bin/env python3
"""
Generate dual-voice Tamil podcast audio from a markdown script.

Usage:
    python scripts/generate_episode.py <input_script.md> <output.mp3>

Example:
    python scripts/generate_episode.py content/scripts/level1_ep1.md audio/level1_ep1.mp3

Reads **Host:** and **Guest:** lines from the script, generates TTS audio
segments using edge-tts, and stitches them into a single MP3.
"""

import re
import os
import asyncio
import argparse
import subprocess
from dotenv import load_dotenv

import edge_tts
from google.cloud import texttospeech

# Voice mapping — Indian Tamil (Edge-TTS)
EDGE_VOICES = {
    "HOST": "ta-IN-PallaviNeural",    # Female, Explainer
    "GUEST": "ta-IN-ValluvarNeural",  # Male, Learner
}

# Google Cloud TTS Voice mapping — Indian Tamil
# Tiers: Chirp (Gemini), Wavenet
GOOGLE_VOICES = {
    "CHIRP": {
        "HOST": "ta-IN-Chirp3-HD-Achernar", # Female
        "GUEST": "ta-IN-Chirp3-HD-Charon",   # Male
    },
    "WAVENET": {
        "HOST": "ta-IN-Wavenet-B",
        "GUEST": "ta-IN-Wavenet-A",
    }
}

# Voice tuning for distinctiveness (Edge only)
EDGE_VOICE_OPTS = {
    "ta-IN-PallaviNeural": {"rate": "+0%", "pitch": "-5Hz"},
    "ta-IN-ValluvarNeural": {"rate": "+0%", "pitch": "-5Hz"},
}

# Regex: matches "**Host:** text", "**Guest:** text", etc.
SPEAKER_RE = re.compile(
    r"^\s*(?:\*\s*)?\*\*\s*([A-Za-z]+)\s*:\s*(?:\*\*\s*)?(.*)", re.IGNORECASE
)
PAUSE_RE = re.compile(r"\[Pause:\s*(\d+)\s*sec.*\]", re.IGNORECASE)


def parse_script(file_path: str) -> list[dict]:
    """Parse a markdown script for Host/Guest dialogue lines and Pauses."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

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

        if line == "---":
            dialogue.append({"speaker": "PAUSE", "seconds": 1})
            continue

        match = SPEAKER_RE.match(line)
        if match:
            speaker = match.group(1).upper()
            text = match.group(2).strip()

            # Normalize speaker labels
            if "HOST" in speaker:
                speaker = "HOST"
            elif "GUEST" in speaker:
                speaker = "GUEST"

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

    return final_dialogue


def clean_for_tts(text: str) -> str:
    """
    Clean text for TTS consumption.
    - Strip parenthetical guides: "வணக்கம் (Vanakkam)" → "வணக்கம்"
    - Strip periods (to prevent "hoo" sound in some TTS voices)
    - Phonetic replacements for common tech terms
    - Collapse whitespace
    - Remove stray markdown
    """
    # Strip parenthetical English guides
    text = re.sub(r"\s*\(.*?\)\s*", " ", text)
    
    # Phonetic replacements for better TTS
    replacements = {
        "JSON": "jay-son",
        "CLI": "C-L-I",
    }
    for word, phonetic in replacements.items():
        # Match word with boundaries to avoid partial replacement (e.g., "CLIENT")
        text = re.sub(rf"\b{word}\b", phonetic, text, flags=re.IGNORECASE)

    # Remove periods
    text = text.replace(".", "")
    # Remove markdown formatting
    text = re.sub(r"[*_#`]", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def generate_segment_edge(text: str, speaker: str, index: int, temp_dir: str) -> str:
    """Generate a single audio segment using edge-tts."""
    voice = EDGE_VOICES.get(speaker, EDGE_VOICES["HOST"])
    opts = EDGE_VOICE_OPTS.get(voice, {"rate": "+0%", "pitch": "+0Hz"})

    communicate = edge_tts.Communicate(text, voice, rate=opts["rate"], pitch=opts["pitch"])

    filename = os.path.join(temp_dir, f"segment_{index:04d}.mp3")
    await communicate.save(filename)
    return filename


async def generate_segment_google(text: str, speaker: str, index: int, temp_dir: str, voice_type: str) -> str:
    """Generate a single audio segment using Google Cloud TTS."""
    client = texttospeech.TextToSpeechClient()

    # Select the voice based on type and speaker
    tier = GOOGLE_VOICES.get(voice_type.upper(), GOOGLE_VOICES["CHIRP"])
    voice_name = tier.get(speaker, tier["HOST"])

    input_text = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="ta-IN",
        name=voice_name
    )

    # We want MP3 output to match the stitching logic.
    # We specify 24000Hz to match our SILENCE_FRAME and stitching assumptions.
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        sample_rate_hertz=24000
    )

    response = client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )

    filename = os.path.join(temp_dir, f"segment_{index:04d}.mp3")
    with open(filename, "wb") as out:
        out.write(response.audio_content)

    return filename


def get_raw_mp3_frames(filepath: str) -> bytes:
    """Extract raw MPEG audio chunk, stripping wrapper ID3 and Xing/Info headers."""
    with open(filepath, "rb") as f:
        data = f.read()

    offset = 0
    if data.startswith(b"ID3"):
        # The size is stored in bytes 6, 7, 8, 9 as 7-bit synchsafe integers
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        offset = 10 + size

    # check if the first byte after ID3 is a sync word
    if offset < len(data) - 1 and data[offset] == 0xFF and (data[offset+1] & 0xE0) == 0xE0:
        padding = (data[offset+2] & 0x02) >> 1
        frame_len = 144 + padding
        
        # Check for Xing/Info in this first frame
        frame_data = data[offset:offset+frame_len]
        if b"Xing" in frame_data or b"Info" in frame_data:
            offset += frame_len

    end_offset = len(data)
    if end_offset >= 128 and data[-128:].startswith(b"TAG"):
        end_offset -= 128

    return data[offset:end_offset]

# A single valid MPEG-2 L3 raw frame of silence (24000Hz, 48kbps, Mono).
# Generated via edge-tts with <break time="1000ms"/> and extracted frame 5.
import base64
SILENCE_FRAME_B64 = "//NkxJoiPA4Vgc1AAVXPcXO05CbzflKqdX8LXO/PQy7v6mbnkYz3BsVdxH7xI1psbFEYzt6Fxl0w17Szht3EmOWRKhJANxpojDXhk+E+3qNp+0+oomHuYca0xPxKUOihtdfcvPB+yzd2o2Sbh5zuLHVDDK9juB8rHhbq9lYT0XEdvYWKCGEeTvz8YP2XWipB"
SILENCE_FRAME = base64.b64decode(SILENCE_FRAME_B64)

async def main():
    parser = argparse.ArgumentParser(description="Generate Dual-Voice Tamil Podcast Audio")
    parser.add_argument("input_file", help="Input markdown script")
    parser.add_argument("output_file", help="Output MP3 file")
    parser.add_argument("--provider", choices=["edge", "google"], default="google", help="TTS provider (default: google)")
    parser.add_argument("--voice-type", choices=["chirp", "wavenet"], default="chirp", 
                        help="Google voice tier (default: chirp)")
    args = parser.parse_args()

    print(f"📖 Parsing {args.input_file}...")
    dialogue = parse_script(args.input_file)
    if not dialogue:
        print("❌ No dialogue lines found!")
        return

    print(f"   Found {len(dialogue)} segments.")
    print(f"   Provider: {args.provider}")
    if args.provider == "google":
        print(f"   Tier: {args.voice_type}")

    temp_dir = "temp_audio_segments"
    os.makedirs(temp_dir, exist_ok=True)

    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    print("🎙️  Generating audio segments...")

    # We will build the final MP3 purely in memory directly from frames.
    final_audio_data = bytearray()

    for i, line in enumerate(dialogue):
        speaker = line["speaker"]

        if speaker == "PAUSE":
            seconds = line.get("seconds", 1)
            print(f"   [{i+1}/{len(dialogue)}] ⏸️  Pause for {seconds} seconds")
            # 1 second = 1000ms / 24ms per frame = ~42 frames
            frames_needed = int(seconds * 41.666)
            final_audio_data.extend(SILENCE_FRAME * frames_needed)
            continue

        clean_text = clean_for_tts(line["text"])

        if not clean_text:
            continue

        preview = clean_text[:40] + ("..." if len(clean_text) > 40 else "")
        print(f"   [{i+1}/{len(dialogue)}] {speaker}: {preview}")

        if args.provider == "google":
            seg_file = await generate_segment_google(clean_text, speaker, i, temp_dir, args.voice_type)
        else:
            seg_file = await generate_segment_edge(clean_text, speaker, i, temp_dir)

        raw_frames = get_raw_mp3_frames(seg_file)
        final_audio_data.extend(raw_frames)
        
        # Add a tiny 250ms natural breathing pause between spoken lines
        final_audio_data.extend(SILENCE_FRAME * 10)
        
        os.remove(seg_file)

    print(f"🔗 Saving pure MPEG stream → {args.output_file}...")
    with open(args.output_file, "wb") as outfile:
        outfile.write(final_audio_data)

    os.rmdir(temp_dir)

    size_mb = len(final_audio_data) / (1024 * 1024)
    print(f"✅ Done! {args.output_file} ({size_mb:.1f} MB)")

    # 6. Upload to Home Assistant
    load_dotenv()
    ha_host = os.getenv("HOMEASSISTANT_HOST", "homeassistant")
    print(f"📡 Uploading to Home Assistant: {args.output_file} -> {ha_host}:/config/www/episode.mp3")
    try:
        subprocess.run(
            ["scp", args.output_file, f"{ha_host}:/config/www/episode.mp3"],
            check=True
        )
        print("✅ Upload complete!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Upload failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
