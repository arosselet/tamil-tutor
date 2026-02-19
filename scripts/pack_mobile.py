#!/usr/bin/env python3
"""
Pack a mobile-ready bundle of the Tamil learning system.
SLIDING WINDOW: Only packs current level ± 1 in full detail.
All other levels are compressed to title + word list summary.

Includes:
  - Protocol files (PROTOCOL_MAP, philosophy, loop, session, sync, etc.)
  - curriculum_context.json (sliding window of levels)
  - learner.json
"""

import json
import zipfile
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "mobile_bundle.zip"
WINDOW = 1  # ±1 levels around current


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_curriculum_context() -> dict:
    """Build a compact curriculum context with a sliding window."""
    levels = load_json(BASE_DIR / "curriculum" / "levels.json")
    learner = load_json(BASE_DIR / "progress" / "learner.json")

    current = learner.get("current_level", 1)
    window_min = max(1, current - WINDOW)
    window_max = current + WINDOW

    summary = []
    active_levels = {}

    for level_num_str in sorted(levels.keys(), key=int):
        level_num = int(level_num_str)
        level_data = levels[level_num_str]

        # Extract flat word list for summary
        words = []
        for ep in level_data.get("episodes", []):
            for w in ep.get("vocab", []):
                if w["tamil"] not in words:
                    words.append(w["tamil"])

        summary.append({
            "level": level_num,
            "title": level_data.get("title", ""),
            "tier": level_data.get("tier", 1),
            "word_count": len(words),
            "words": words,
        })

        # Full detail for active window
        if window_min <= level_num <= window_max:
            active_levels[level_num_str] = level_data

    context = {
        "total_levels": len(levels),
        "current_level": current,
        "window": f"{window_min}-{window_max}",
        "summary": summary,
        "active_levels": active_levels,
    }

    return context


def pack():
    # 1. Protocol files
    protocol_files = [
        "protocol/PROTOCOL_MAP.md",
        "protocol/philosophy.md",
        "protocol/learning_loop.md",
        "protocol/session_protocol.md",
        "protocol/weekly_rotation.md",
        "protocol/mobile_sync.md",
        "protocol/sync_ingest.md",
    ]

    progress_files = [
        "progress/learner.json",
    ]

    # 2. Build curriculum context (sliding window)
    context = build_curriculum_context()
    context_path = BASE_DIR / "curriculum_context.json"
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    all_files = protocol_files + progress_files
    print(f"📦 Packing {len(all_files) + 1} files into {OUTPUT_FILE.name} (FLAT structure)...")
    print(f"   Sliding window: levels {context['window']} (current: {context['current_level']})")

    # Cleanup old master if it exists
    master_path = BASE_DIR / "MASTER_PROTOCOL.md"
    if master_path.exists():
        os.remove(master_path)

    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        # Pack protocol and progress files
        for rel_path in all_files:
            file_path = BASE_DIR / rel_path
            if not file_path.exists():
                print(f"  ⚠️  Skipping {rel_path} (not found)")
                continue

            arcname = file_path.name
            zf.write(file_path, arcname)
            print(f"  ✅ {arcname} ({file_path.stat().st_size:,} bytes)")

        # Pack the curriculum context
        zf.write(context_path, "curriculum_context.json")
        print(f"  ✅ curriculum_context.json ({context_path.stat().st_size:,} bytes)")

    # Cleanup temp file
    context_path.unlink()

    bundle_size = OUTPUT_FILE.stat().st_size
    print(f"\n✅ Pack Complete!")
    print(f"   Files:        {len(all_files) + 1}")
    print(f"   Compressed:   {bundle_size:,.0f} bytes")
    print(f"   Built:        {datetime.now().isoformat()}")

    # Compare with what full levels.json would have been
    full_levels_size = (BASE_DIR / "curriculum" / "levels.json").stat().st_size
    context_size = context_path.stat().st_size if context_path.exists() else 0
    # Re-read to get actual size since we deleted temp
    with zipfile.ZipFile(OUTPUT_FILE, "r") as zf:
        for info in zf.filelist:
            if info.filename == "curriculum_context.json":
                context_size = info.file_size
                break
    print(f"   📉 Curriculum: {context_size:,} bytes (was {full_levels_size:,} in full levels.json)")


if __name__ == "__main__":
    pack()
