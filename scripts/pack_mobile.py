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

def merge_protocols():
    """Merge all protocols into a single MASTER_PROTOCOL.md."""
    protocol_dir = BASE_DIR / "protocol"
    files = [
        "philosophy.md",
        "learning_loop.md",
        "session_protocol.md",
        "weekly_rotation.md",
        "mobile_sync.md",
        "sync_ingest.md",
    ]
    
    master_content = "# MADRAS MAPPILLAI MASTER PROTOCOL\n\n"
    master_content += "This file contains all instructions for the Tamil Learning System.\n\n"
    
    for f in files:
        path = protocol_dir / f
        if path.exists():
            content = path.read_text()
            # Convert any internal links [label](protocol/file.md) to [label](MASTER_PROTOCOL.md)
            content = content.replace("protocol/", "")
            master_content += f"\n\n---\n\n" 
            master_content += content
            
    master_path = BASE_DIR / "MASTER_PROTOCOL.md"
    master_path.write_text(master_content)
    return master_path

def pack():
    # 1. Prepare the master protocol
    master_protocol = merge_protocols()
    
    # 2. Files to include
    files_to_pack = [
        master_protocol,
        BASE_DIR / "curriculum/levels.json",
        BASE_DIR / "curriculum/vocabulary_index.json",
        BASE_DIR / "progress/learner.json",
    ]
    
    print(f"📦 Packing {len(files_to_pack)} files into {OUTPUT_FILE.name} (FLAT structure)...")
    
    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files_to_pack:
            if not file_path.exists():
                print(f"  ⚠️  Skipping {file_path.name} (not found)")
                continue
                
            # FLAT: Only the filename, no directory structure
            arcname = file_path.name
            zf.write(file_path, arcname)
            print(f"  ✅ {arcname} ({file_path.stat().st_size:,} bytes)")

    # Cleanup temp master file if desired, but maybe keep it for reference?
    # os.remove(master_protocol)
    
    bundle_size = OUTPUT_FILE.stat().st_size
    print(f"\n✅ Pack Complete!")
    print(f"   Files:        {len(files_to_pack)}")
    print(f"   Compressed:   {bundle_size:,.0f} bytes")
    print(f"   Built:        {datetime.now().isoformat()}")

if __name__ == "__main__":
    pack()
