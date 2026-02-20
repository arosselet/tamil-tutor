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

# Voice mapping — Indian Tamil
VOICES = {
    "HOST": "ta-IN-PallaviNeural",    # Female, Explainer
    "GUEST": "ta-IN-ValluvarNeural",  # Male, Learner
}

# Voice tuning for distinctiveness
VOICE_OPTS = {
    "ta-IN-PallaviNeural": {"rate": "+0%", "pitch": "-5Hz"},
    "ta-IN-ValluvarNeural": {"rate": "+0%", "pitch": "-5Hz"},
}

# Regex: matches "**Host:** text", "**Guest:** text", etc.
SPEAKER_RE = re.compile(
    r"^\s*(?:\*\s*)?\*\*\s*([A-Za-z]+)\s*:\s*(?:\*\*\s*)?(.*)", re.IGNORECASE
)


def parse_script(file_path: str) -> list[dict]:
    """Parse a markdown script for Host/Guest dialogue lines."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    dialogue = []
    for line in lines:
        line = line.strip()
        if not line:
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

    return dialogue


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


async def generate_segment(text: str, speaker: str, index: int, temp_dir: str) -> str:
    """Generate a single audio segment using edge-tts."""
    voice = VOICES.get(speaker, VOICES["HOST"])
    opts = VOICE_OPTS.get(voice, {"rate": "+0%", "pitch": "+0Hz"})

    communicate = edge_tts.Communicate(text, voice, rate=opts["rate"], pitch=opts["pitch"])

    filename = os.path.join(temp_dir, f"segment_{index:04d}.mp3")
    await communicate.save(filename)
    return filename


async def main():
    parser = argparse.ArgumentParser(description="Generate Dual-Voice Tamil Podcast Audio")
    parser.add_argument("input_file", help="Input markdown script")
    parser.add_argument("output_file", help="Output MP3 file")
    args = parser.parse_args()

    # 1. Parse
    print(f"📖 Parsing {args.input_file}...")
    dialogue = parse_script(args.input_file)
    if not dialogue:
        print("❌ No dialogue lines found! Ensure format is '**Speaker:** Text'.")
        return

    print(f"   Found {len(dialogue)} segments.")

    # 2. Temp directory
    temp_dir = "temp_audio_segments"
    os.makedirs(temp_dir, exist_ok=True)

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 3. Generate segments
    segment_files = []
    print("🎙️  Generating audio segments...")

    for i, line in enumerate(dialogue):
        clean_text = clean_for_tts(line["text"])
        speaker = line["speaker"]

        if not clean_text:
            continue

        preview = clean_text[:40] + ("..." if len(clean_text) > 40 else "")
        print(f"   [{i+1}/{len(dialogue)}] {speaker}: {preview}")

        seg_file = await generate_segment(clean_text, speaker, i, temp_dir)
        segment_files.append(seg_file)

    # 4. Stitch
    print(f"🔗 Stitching {len(segment_files)} segments → {args.output_file}...")
    with open(args.output_file, "wb") as outfile:
        for seg_file in segment_files:
            with open(seg_file, "rb") as infile:
                outfile.write(infile.read())

    # 5. Cleanup
    for f in segment_files:
        os.remove(f)
    os.rmdir(temp_dir)

    size_mb = os.path.getsize(args.output_file) / (1024 * 1024)
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
