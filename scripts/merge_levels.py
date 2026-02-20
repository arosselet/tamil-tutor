#!/usr/bin/env python3
"""
Merge individual level files into the master levels.json.
Reads index.json to determine which files to include.

Usage:
    python scripts/merge_levels.py
"""
import json
from pathlib import Path

CURRICULUM = Path("/home/roshana/projects/Tamil2/curriculum")


def merge_levels():
    """Build levels.json from index.json and individual level_* files."""
    index_file = CURRICULUM / "index.json"
    if not index_file.exists():
        print("index.json not found!")
        return {}

    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    levels = {}
    for level_str, meta in index_data.items():
        filename = meta.get("file")
        if not filename:
            continue
        
        file_path = CURRICULUM / "levels" / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                level_data = json.load(f)
            levels[level_str] = level_data
            print(f"  Merged Level {level_str} from {filename}")
        else:
            print(f"  Warning: {filename} not found for level {level_str}")

    with open(CURRICULUM / "levels.json", "w", encoding="utf-8") as f:
        json.dump(levels, f, ensure_ascii=False, indent=2)

    print(f"\nlevels.json now has {len(levels)} levels")
    return levels


if __name__ == "__main__":
    print("Building master levels.json...")
    levels = merge_levels()
    print("\nDone!")
