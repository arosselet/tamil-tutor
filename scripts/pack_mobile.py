#!/usr/bin/env python3
"""
Pack a mobile-ready bundle of the Tamil learning system.
SLIDING WINDOW: Only packs current level ± 1 in full detail.
All other levels are summary only.

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

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "mobile_bundle.zip"
WINDOW = 1  # ±1 levels around current


def load_json(path: Path):
    if not path.exists():
        print(f"⚠️  {path} not found. Returning empty dict.")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_curriculum_context() -> dict:
    """Build a compact curriculum context with a sliding window."""
    # Use the new index.json + individual level files
    index_path = BASE_DIR / "curriculum" / "index.json"
    index = load_json(index_path)
    
    learner_path = BASE_DIR / "progress" / "learner.json"
    learner = load_json(learner_path)

    current = learner.get("current_level", 1)
    window_min = max(1, current - WINDOW)
    window_max = current + WINDOW

    summary = []
    active_levels_data = {}

    # Sort levels by numeric key
    sorted_levels = sorted(index.keys(), key=lambda x: int(x) if x.isdigit() else 999)

    for level_key in sorted_levels:
        if not level_key.isdigit():
            continue
            
        level_num = int(level_key)
        level_info = index[level_key]
        level_file = level_info.get("file")
        
        # Determine if this level is within the sliding window
        is_active = window_min <= level_num <= window_max

        if is_active:
            # Load full level data
            full_level_path = BASE_DIR / "curriculum" / "levels" / level_file
            if full_level_path.exists():
                full_data = load_json(full_level_path)
                active_levels_data[level_key] = full_data
                
                # Also create summary from full data
                words = []
                for ep in full_data.get("episodes", []):
                    for w in ep.get("vocab", []):
                        if w["tamil"] not in words:
                            words.append(w["tamil"])
                
                summary.append({
                    "level": level_num,
                    "title": full_data.get("title", ""),
                    "tier": full_data.get("tier", 1),
                    "word_count": len(words),
                    # "words": words # Omit words list for active levels in summary to save space? 
                                     # Actually user might want search across all levels. 
                                     # Let's keep it consistent.
                    "words": words
                })
            else:
                print(f"⚠️  Active level file {full_level_path} missing!")

        else:
            # For non-active levels, we only have the index info.
            # We don't want to load every JSON file just to get word counts if we can avoid it.
            # But to support "search", we might need the words. 
            # Compromise: Load the file, extract words, discard descriptions/scenarios.
            
            full_level_path = BASE_DIR / "curriculum" / "levels" / level_file
            if full_level_path.exists():
                full_data = load_json(full_level_path)
                words = []
                for ep in full_data.get("episodes", []):
                    for w in ep.get("vocab", []):
                        if w["tamil"] not in words:
                            words.append(w["tamil"])
                
                summary.append({
                    "level": level_num,
                    "title": full_data.get("title", ""),
                    "tier": full_data.get("tier", 1),
                    "word_count": len(words),
                    "words": words
                })

    context = {
        "generated_at": datetime.now().isoformat(),
        "total_levels": len(sorted_levels),
        "current_level": current,
        "window": f"{window_min}-{window_max}",
        "active_levels": active_levels_data, # Detailed scenarios/intros for active window
        "summary": summary, # Word lists for ALL levels (for search/reference)
    }

    return context


def pack():
    # 1. Protocol files (Mobile Essentials Only)
    protocol_files = [
        "protocol/PROTOCOL_MAP.md",
        "protocol/philosophy.md",
        "protocol/learning_loop.md",
        "protocol/session_protocol.md",
        "protocol/weekly_rotation.md",
        "protocol/mobile_sync.md",
        # Excluded: sync_ingest (desktop only), roles/* (audio pipeline)
    ]

    progress_files = [
        "progress/learner.json",
    ]

    # 2. Build curriculum context (sliding window)
    print("🏗️  Building curriculum context...")
    context = build_curriculum_context()
    context_path = BASE_DIR / "curriculum_context.json"
    
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    all_files_to_pack = []
    
    # Collect existing protocol/progress files
    for rel_path in protocol_files + progress_files:
        p = BASE_DIR / rel_path
        if p.exists():
            all_files_to_pack.append(p)
        else:
            print(f"⚠️  Skipping missing file: {rel_path}")

    # Add context file
    all_files_to_pack.append(context_path)

    print(f"📦 Packing {len(all_files_to_pack)} files into {OUTPUT_FILE.name}...")
    print(f"   Sliding window: levels {context['window']} (current: {context['current_level']})")

    # Cleanup old zip
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in all_files_to_pack:
            # Determine arcname (filename inside zip)
            # We want a flat structure for simplicity on mobile context injection?
            # Or preserve folders?
            # The prompt implies "limit to 10 files". A flat structure is often easier for 
            # simple "Upload these files" workflows. 
            # Let's stick to the previous script's logic: arcname = file_path.name (FLAT)
            
            arcname = file_path.name
            zf.write(file_path, arcname)
            print(f"  ✅ {arcname} ({file_path.stat().st_size:,} bytes)")

    # Cleanup temp file
    context_path.unlink()

    bundle_size = OUTPUT_FILE.stat().st_size
    print(f"\n✅ Pack Complete!")
    print(f"   Files:        {len(all_files_to_pack)}")
    print(f"   Compressed:   {bundle_size:,.0f} bytes")

if __name__ == "__main__":
    pack()
