#!/usr/bin/env python3
"""
scripts/apply_additions.py

Merges reviewed proposed_additions.json into the tier JSON files.

Workflow:
    1. Run: python scripts/tag_clusters.py --write
    2. Review and edit: curriculum/proposed_additions.json
       - Delete any entries you don't want
       - Edit tamil/english fields as needed
       - Each entry must have: tamil, english, cluster
    3. Run: python scripts/apply_additions.py --write

Usage:
    python scripts/apply_additions.py           # dry-run: show what would change
    python scripts/apply_additions.py --write   # commit to tier JSONs
    python scripts/apply_additions.py --tier 2  # only apply additions for tier 2
"""

import json
import sys
import argparse
from pathlib import Path

BASE = Path(__file__).parent.parent
TIERS_DIR = BASE / "curriculum" / "tiers"
ADDITIONS_PATH = BASE / "curriculum" / "proposed_additions.json"

# Cluster → target tier (rough sequence ordering; override in proposed_additions.json
# by adding a "tier" field to any entry if you want to place it differently)
CLUSTER_TO_TIER = {
    "verb_past":          2,
    "verb_present":       2,
    "verb_future":        3,
    "verb_command":       2,
    "connectors":         2,
    "family":             2,
    "pronouns":           2,
    "social_reaction":    2,
    "questions":          2,
    "emotions":           2,
    "descriptions":       2,
    "obligation_ability": 4,
    "proposals":          3,
    "daily_routine":      2,
    "home_kitchen":       2,
    "phone_scheduling":   2,
    "home_environment":   2,
}


def load_tier_files():
    files = {}
    for path in sorted(TIERS_DIR.glob("tier_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        files[data["tier"]] = (path, data)
    return files


def get_existing_tamil(tier_files):
    seen = set()
    for _, data in tier_files.values():
        for w in data.get("vocabulary", []):
            seen.add(w["tamil"])
    return seen


def main():
    parser = argparse.ArgumentParser(description="Merge proposed_additions.json into tier JSONs")
    parser.add_argument("--write", action="store_true", help="Write changes to disk")
    parser.add_argument("--tier", type=int, help="Only apply additions going into this tier")
    args = parser.parse_args()

    if not ADDITIONS_PATH.exists():
        sys.exit(
            f"Not found: {ADDITIONS_PATH.relative_to(BASE)}\n"
            "Run 'python scripts/tag_clusters.py --write' first."
        )

    all_additions = json.loads(ADDITIONS_PATH.read_text(encoding="utf-8"))
    tier_files = load_tier_files()
    existing = get_existing_tamil(tier_files)

    pending = {t: [] for t in tier_files}
    skipped_dup = 0
    skipped_no_tier = 0

    for cluster, items in all_additions.items():
        for item in items:
            tamil = item.get("tamil", "").strip()
            english = item.get("english", "").strip()
            if not tamil or not english:
                continue
            if tamil in existing:
                skipped_dup += 1
                continue

            # Allow per-entry tier override in the JSON
            target_tier = item.get("tier") or CLUSTER_TO_TIER.get(cluster)
            if target_tier is None:
                print(f"  WARN: no tier mapping for cluster '{cluster}' — skipping '{tamil}'")
                skipped_no_tier += 1
                continue
            if args.tier and target_tier != args.tier:
                continue
            if target_tier not in tier_files:
                print(f"  WARN: tier {target_tier} not found — skipping '{tamil}'")
                skipped_no_tier += 1
                continue

            pending[target_tier].append({
                "tamil": tamil,
                "english": english,
                "cluster": cluster,
            })
            existing.add(tamil)

    print("Additions to apply:")
    any_pending = False
    for tier_num, items in pending.items():
        if items:
            path, _ = tier_files[tier_num]
            print(f"  tier {tier_num} ({path.name}): +{len(items)} entries")
            for item in items[:5]:
                print(f"    {item['tamil']} — {item['english']}  [{item['cluster']}]")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")
            any_pending = True
    if skipped_dup:
        print(f"  Skipped {skipped_dup} duplicates (already in curriculum)")
    if skipped_no_tier:
        print(f"  Skipped {skipped_no_tier} entries with unmapped clusters")
    if not any_pending:
        print("  Nothing to apply.")
        return

    if args.write:
        for tier_num, items in pending.items():
            if not items:
                continue
            path, data = tier_files[tier_num]
            data["vocabulary"].extend(items)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  Wrote {path.name} (+{len(items)} entries)")
    else:
        print("\nDry-run — pass --write to commit.")


if __name__ == "__main__":
    main()
