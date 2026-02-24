#!/usr/bin/env python3
"""
Pack a mobile-ready bundle of the Tamil learning system.
Consolidated for the 3-Tier architecture.
"""

import json
import zipfile
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "mobile_bundle.zip"


def load_json(path: Path):
    if not path.exists():
        print(f"⚠️  {path} not found. Returning empty dict.")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_curriculum_context() -> dict:
    """Build a compact curriculum context for the 3 Tiers."""
    index_path = BASE_DIR / "curriculum" / "index.json"
    index = load_json(index_path)
    
    learner_path = BASE_DIR / "progress" / "learner.json"
    learner = load_json(learner_path)

    current_tier = learner.get("current_tier", 1)
    
    tiers_data = {}
    summary = []

    for tier_id, info in index.items():
        tier_num = int(tier_id)
        tier_file = info.get("file")
        tier_path = BASE_DIR / "curriculum" / "tiers" / tier_file
        
        if not tier_path.exists():
            print(f"⚠️  Tier file {tier_path} missing!")
            continue
            
        full_data = load_json(tier_path)
        
        # If it's the current tier, include full data (scenarios + vocab)
        if tier_num == current_tier:
            tiers_data[tier_id] = full_data
        
        # Always include a summary for every tier
        words = [v["tamil"] for v in full_data.get("vocabulary", [])]
        summary.append({
            "tier": tier_num,
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "word_count": len(words),
            "words": words
        })

    context = {
        "generated_at": datetime.now().isoformat(),
        "current_tier": current_tier,
        "active_tier_data": tiers_data,
        "summary": summary,
    }

    return context


def pack():
    # 1. Protocol files
    protocol_files = [
        "protocol/PROTOCOL_MAP.md",
        "protocol/philosophy.md",
        "protocol/learning_loop.md",
        "protocol/session_protocol.md",
        "protocol/episode_rotation.md",
        "protocol/mobile_sync.md",
    ]

    progress_files = [
        "progress/learner.json",
    ]

    # 2. Build curriculum context
    print("🏗️  Building curriculum context...")
    context = build_curriculum_context()
    context_path = BASE_DIR / "curriculum_context.json"
    
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    all_files_to_pack = []
    
    for rel_path in protocol_files + progress_files:
        p = BASE_DIR / rel_path
        if p.exists():
            all_files_to_pack.append(p)
        else:
            print(f"⚠️  Skipping missing file: {rel_path}")

    all_files_to_pack.append(context_path)

    print(f"📦 Packing {len(all_files_to_pack)} files into {OUTPUT_FILE.name}...")

    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in all_files_to_pack:
            arcname = file_path.name
            zf.write(file_path, arcname)
            print(f"  ✅ {arcname} ({file_path.stat().st_size:,} bytes)")

    context_path.unlink()

    print(f"\n✅ Pack Complete!")

if __name__ == "__main__":
    pack()
