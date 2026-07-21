#!/usr/bin/env python3
"""
Render a SHOWCASE script to MP3 — no lifecycle hooks.

Usage:
    python scripts/render_demo.py content/scripts/anna_intro.md audio/anna_intro.mp3

Why this exists (replaces the lost, never-committed render_polyglot.py):
render_audio.py is the *lesson* pipeline — it registers a mission in episodes.json,
stamps seen_in into the lexicon, rebuilds the RSS feed, and git-pushes. Demo pieces
(the polyglot demo, Anna's introduction) are README artefacts, not lessons: they must
touch no state and reach no feed. Same parser, same TTS, zero side effects.

Difference from render_audio: language_code is derived per-voice (ta-IN / en-US /
fr-CA ...) instead of pinned to ta-IN, so multi-language demos render here too.
Pin voices with a `Voice Map: {"SPEAKER": "voice-name"}` comment in the script.

Also differs on cleaning: this path uses clean_keep_periods, not render_audio's
clean_for_tts. clean_for_tts strips every "." (a known pacing-wrecker — memos skip it
for the same reason, DECISIONS 2026-07-07). A showcase piece is long-form narration:
without sentence periods Chirp3-HD renders it as one breathless run-on and swallows the
tails of short sentences. Keep the periods; keep the breath long (~800ms).
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google.cloud import texttospeech

from render_audio import (SILENCE_FRAME, assign_voices, defang_hyphens,
                          get_raw_mp3_frames, parse_script)


def clean_keep_periods(text: str) -> str:
    """clean_for_tts, minus the period strip — sentence breaks are the pacing here."""
    text = re.sub(r"\s*\(.*?\)\s*", " ", text)
    text = re.sub(r"\s*\[.*?\]\s*", " ", text)
    for word, phonetic in {"JSON": "jay-son", "CLI": "C-L-I"}.items():
        text = re.sub(rf"\b{word}\b", phonetic, text, flags=re.IGNORECASE)
    text = re.sub(r"[*_#`]", "", text)
    text = defang_hyphens(text)
    return re.sub(r"\s+", " ", text).strip()


def lang_of(voice: str) -> str:
    """'ta-IN-Chirp3-HD-Orus' -> 'ta-IN'. The whole reason this file is separate."""
    return "-".join(voice.split("-")[:2])


def synth(text: str, voice: str) -> bytes:
    client = texttospeech.TextToSpeechClient()
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code=lang_of(voice), name=voice),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1.0),
    )
    return response.audio_content


async def main():
    parser = argparse.ArgumentParser(description="Render a showcase script — no state, no feed")
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    args = parser.parse_args()

    dialogue, voice_map = parse_script(args.input_file)
    if not dialogue:
        sys.exit("❌ No dialogue lines found.")

    cast = assign_voices(dialogue, voice_map, provider="google", voice_type="chirp")
    print("🎭 Cast:")
    for s, v in cast.items():
        print(f"   - {s}: {v}  [{lang_of(v)}]")

    audio = bytearray()
    tmp = Path("temp_demo_segments")
    tmp.mkdir(exist_ok=True)

    for i, line in enumerate(dialogue):
        if line["speaker"] == "PAUSE":
            audio.extend(SILENCE_FRAME * int(line.get("seconds", 1) * 41.666))
            continue
        text = clean_keep_periods(line["text"])
        if not text:
            continue
        voice = cast[line["speaker"]]
        print(f"   [{i+1}/{len(dialogue)}] {line['speaker']}: {text[:50]}...")
        seg = tmp / f"{i}.mp3"
        seg.write_bytes(synth(text, voice))
        audio.extend(get_raw_mp3_frames(str(seg)))
        audio.extend(SILENCE_FRAME * 34)  # ~800ms breath — showcase narration wants air
        seg.unlink()

    tmp.rmdir()
    out = Path(args.output_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    print(f"✅ {out} ({len(audio)/(1024*1024):.1f} MB) — no state touched, nothing published.")


if __name__ == "__main__":
    asyncio.run(main())
