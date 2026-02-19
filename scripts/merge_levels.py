#!/usr/bin/env python3
"""
Merge expansion level files into levels.json.
Run after adding new level batch files (e.g., levels_9_12.json).

Usage:
    python scripts/merge_levels.py
"""
import json
from pathlib import Path

CURRICULUM = Path("/home/roshana/projects/Tamil2/curriculum")


def merge_levels():
    """Merge all level expansion files into levels.json."""
    with open(CURRICULUM / "levels.json", "r", encoding="utf-8") as f:
        levels = json.load(f)

    # Find all expansion files matching levels_*.json
    expansion_files = sorted(CURRICULUM.glob("levels_*.json"))

    if not expansion_files:
        print("No expansion files found.")
        return levels

    for fpath in expansion_files:
        with open(fpath, "r", encoding="utf-8") as f:
            new_levels = json.load(f)
        levels.update(new_levels)
        print(f"  Merged {fpath.name}: levels {', '.join(sorted(new_levels.keys(), key=int))}")

    with open(CURRICULUM / "levels.json", "w", encoding="utf-8") as f:
        json.dump(levels, f, ensure_ascii=False, indent=2)

    print(f"\nlevels.json now has {len(levels)} levels")
    return levels


if __name__ == "__main__":
    print("Merging levels...")
    levels = merge_levels()
    print("\nDone!")
