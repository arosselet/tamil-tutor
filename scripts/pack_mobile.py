#!/usr/bin/env python3
"""
Pack a mobile-ready bundle of the Tamil learning system.
FLATTENED VERSION: All files in the root of the ZIP.
MERGED VERSION: All protocols merged into MASTER_PROTOCOL.md.

Includes:
  - MASTER_PROTOCOL.md (philosophy, loop, session, sync)
  - levels.json
  - vocabulary_index.json
  - learner.json
"""

import zipfile
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "mobile_bundle.zip"

def pack():
    # 1. Individual files to include (crisp separation of concerns)
    protocol_files = [
        "protocol/PROTOCOL_MAP.md",
        "protocol/philosophy.md",
        "protocol/learning_loop.md",
        "protocol/session_protocol.md",
        "protocol/weekly_rotation.md",
        "protocol/mobile_sync.md",
        "protocol/sync_ingest.md",
    ]
    
    curriculum_files = [
        "curriculum/levels.json",
        "curriculum/vocabulary_index.json",
    ]
    
    progress_files = [
        "progress/learner.json",
    ]
    
    all_files = protocol_files + curriculum_files + progress_files
    
    print(f"📦 Packing {len(all_files)} files into {OUTPUT_FILE.name} (FLAT structure)...")
    
    # Cleanup old master if it exists
    master_path = BASE_DIR / "MASTER_PROTOCOL.md"
    if master_path.exists():
        os.remove(master_path)
    
    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in all_files:
            file_path = BASE_DIR / rel_path
            if not file_path.exists():
                print(f"  ⚠️  Skipping {rel_path} (not found)")
                continue
                
            # FLAT: Only the filename, no directory structure inside the ZIP
            arcname = file_path.name
            zf.write(file_path, arcname)
            print(f"  ✅ {arcname} ({file_path.stat().st_size:,} bytes)")

    bundle_size = OUTPUT_FILE.stat().st_size
    print(f"\n✅ Pack Complete!")
    print(f"   Files:        {len(all_files)}")
    print(f"   Compressed:   {bundle_size:,.0f} bytes")
    print(f"   Built:        {datetime.now().isoformat()}")

if __name__ == "__main__":
    pack()
