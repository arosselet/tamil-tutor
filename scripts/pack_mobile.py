#!/usr/bin/env python3
"""
Pack a mobile-ready bundle of the Tamil learning system.

Includes only what's needed for live interactive lessons:
  - protocol/          (philosophy, roles, learning loop, sync protocol)
  - curriculum/        (levels.json, vocabulary_index.json)
  - progress/          (learner.json)

Excludes generated content (mp3s, scripts, audio/, content/).

Usage:
    python scripts/pack_mobile.py

Output:
    mobile_bundle.zip in the project root
"""

import zipfile
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

# What to include
INCLUDE_DIRS = [
    "protocol",
    "curriculum",
    "progress",
]

# What to exclude (glob patterns)
EXCLUDE_PATTERNS = {
    "protocol/roles",
    "*.mp3",
    "*.wav",
    "*.pyc",
    "__pycache__",
    ".DS_Store",
}

OUTPUT_FILE = BASE_DIR / "mobile_bundle.zip"


def should_include(path: Path) -> bool:
    """Check if a file should be included in the bundle."""
    name = path.name
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*."):
            if name.endswith(pattern[1:]):
                return False
        elif name == pattern:
            return False
    return True


def pack():
    file_count = 0
    total_size = 0

    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for dir_name in INCLUDE_DIRS:
            dir_path = BASE_DIR / dir_name
            if not dir_path.exists():
                print(f"  ⚠️  Skipping {dir_name}/ (not found)")
                continue

            for root, dirs, files in os.walk(dir_path):
                # Skip __pycache__ dirs
                dirs[:] = [d for d in dirs if d != "__pycache__"]

                for file_name in sorted(files):
                    file_path = Path(root) / file_name
                    if not should_include(file_path):
                        continue

                    arcname = file_path.relative_to(BASE_DIR)
                    zf.write(file_path, arcname)
                    size = file_path.stat().st_size
                    total_size += size
                    file_count += 1
                    print(f"  📦 {arcname} ({size:,} bytes)")

    bundle_size = OUTPUT_FILE.stat().st_size
    print(f"\n✅ Packed {file_count} files → {OUTPUT_FILE.name}")
    print(f"   Uncompressed: {total_size:,.0f} bytes")
    print(f"   Compressed:   {bundle_size:,.0f} bytes")
    print(f"   Built:        {datetime.now().isoformat()}")


def show_packing_list():
    """Display what would be packed (dry run)."""
    print("=" * 50)
    print("📋 MOBILE BUNDLE — PACKING LIST")
    print("=" * 50)
    print()
    print("INCLUDED:")
    for d in INCLUDE_DIRS:
        print(f"  ✅ {d}/")
    print()
    print("EXCLUDED:")
    print("  ❌ audio/          (generated MP3s)")
    print("  ❌ content/        (generated scripts)")
    print("  ❌ scripts/        (Python tools, desktop-only)")
    print("  ❌ *.mp3, *.wav    (binary audio)")
    print()


if __name__ == "__main__":
    show_packing_list()
    pack()
