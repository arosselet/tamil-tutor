#!/usr/bin/env python3
"""
Registers a new mission in progress/vocab_state.json.
Parses the markdown script to extract the title and vocabulary payload.

Usage:
    python scripts/add_mission_to_state.py content/scripts/tier2_mission41.md
"""

import json
import re
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).parent.parent
VOCAB_STATE_PATH = BASE / "progress" / "vocab_state.json"
AUDIO_DIR = BASE / "audio"

def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_duration(mp3_path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", str(mp3_path)],
            capture_output=True, text=True
        )
        d = json.loads(result.stdout)
        return float(d["format"]["duration"]) / 60
    except Exception:
        return 3.0

def parse_script(script_path: Path):
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title: # Tier 2, Mission 41 — The Coffee Ritual
    title_match = re.search(r"^# Tier 2, Mission \d+ — (.*)$", content, re.M)
    title = title_match.group(1) if title_match else f"Mission {script_path.stem}"

    # Extract bolded Tamil words
    # Matches **தமிழ்** or **தமிழ் (English)**
    words = re.findall(r"\*\*([^\*]+)\*\*", content)
    # Clean up: take only the Tamil part if there's parens
    cleaned_words = []
    for w in words:
        tamil = re.split(r"[\(\s]", w)[0]
        if tamil and any('\u0b80' <= c <= '\u0bff' for c in tamil):
            if tamil not in cleaned_words:
                cleaned_words.append(tamil)

    return title, cleaned_words

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_mission_to_state.py <script_path>")
        sys.exit(1)

    script_path = Path(sys.argv[1])
    if not script_path.exists():
        print(f"Error: {script_path} not found.")
        sys.exit(1)

    mission_match = re.search(r"mission(\d+)", script_path.name)
    if not mission_match:
        print(f"Error: Could not determine mission number from {script_path.name}")
        sys.exit(1)
    
    mission_num = mission_match.group(1)
    title, words = parse_script(script_path)
    
    mp3_path = AUDIO_DIR / f"tier2_mission{mission_num}.mp3"
    duration = get_duration(mp3_path)

    vocab_state = load_json(VOCAB_STATE_PATH)
    if "episodes" not in vocab_state:
        vocab_state["episodes"] = {}

    # Initialize or update entry
    if mission_num not in vocab_state["episodes"]:
        vocab_state["episodes"][mission_num] = {
            "title": title,
            "listens": 0,
            "words": words,
            "duration_min": duration
        }
        print(f"Added Mission {mission_num} to vocab_state.json")
    else:
        # Update metadata but preserve listen count
        vocab_state["episodes"][mission_num].update({
            "title": title,
            "words": words,
            "duration_min": duration
        })
        print(f"Updated Mission {mission_num} in vocab_state.json")

    save_json(VOCAB_STATE_PATH, vocab_state)

if __name__ == "__main__":
    main()
