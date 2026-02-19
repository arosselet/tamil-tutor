#!/usr/bin/env python3
"""
Merge expansion level files into levels.json and rebuild vocabulary_index.json.
"""
import json
from pathlib import Path
from datetime import datetime

CURRICULUM = Path("/home/roshana/projects/Tamil2/curriculum")

def merge_levels():
    """Merge all level files into a single levels.json."""
    with open(CURRICULUM / "levels.json", "r", encoding="utf-8") as f:
        levels = json.load(f)

    expansion_files = [
        "levels_expansion.json",  # 9-12
        "levels_13_16.json",
        "levels_17_20.json",
    ]

    for fname in expansion_files:
        fpath = CURRICULUM / fname
        with open(fpath, "r", encoding="utf-8") as f:
            new_levels = json.load(f)
        levels.update(new_levels)
        print(f"  Merged {fname}: levels {', '.join(sorted(new_levels.keys(), key=int))}")

    with open(CURRICULUM / "levels.json", "w", encoding="utf-8") as f:
        json.dump(levels, f, ensure_ascii=False, indent=2)

    print(f"\nlevels.json now has {len(levels)} levels")
    return levels


def rebuild_vocab_index(levels):
    """Rebuild vocabulary_index.json from levels.json."""
    # Level title to category slug
    def slugify(title):
        return title.lower().replace(" ", "_").replace(":", "").replace("&", "and")

    # Tier mapping
    tier_map = {}
    for level_num, level_data in levels.items():
        tier_map[int(level_num)] = level_data.get("tier", 1)

    seen = set()
    words = []

    for level_num in sorted(levels.keys(), key=int):
        level_data = levels[level_num]
        category = slugify(level_data["title"])
        tier = level_data.get("tier", 1)

        for ep in level_data.get("episodes", []):
            for word in ep.get("vocab", []):
                tamil = word["tamil"]
                # deduplicate by Tamil text
                if tamil not in seen:
                    seen.add(tamil)
                    words.append({
                        "tamil": tamil,
                        "english": word["english"],
                        "level": int(level_num),
                        "episode": ep["episode"],
                        "tier": tier,
                        "category": category,
                        "mastery_score": 0,
                        "times_reviewed": 0,
                        "last_reviewed": None,
                    })

    # Group by tier
    tier_counts = {}
    for w in words:
        t = w["tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1

    # Tier level ranges
    tier_levels = {}
    for level_num, level_data in levels.items():
        t = level_data.get("tier", 1)
        nums = tier_levels.setdefault(t, [])
        nums.append(int(level_num))

    tier_breakdown = {}
    for t in sorted(tier_counts.keys()):
        nums = sorted(tier_levels[t])
        tier_names = {1: "tier1_survival", 2: "tier2_comfortable", 3: "tier3_embedded"}
        tier_breakdown[tier_names.get(t, f"tier{t}")] = {
            "count": tier_counts[t],
            "levels": f"{min(nums)}-{max(nums)}"
        }

    index = {
        "metadata": {
            "total_unique_lemmas": len(words),
            "tier_breakdown": tier_breakdown,
            "last_built": datetime.now().isoformat(),
        },
        "words": words,
    }

    with open(CURRICULUM / "vocabulary_index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\nvocabulary_index.json rebuilt:")
    print(f"  Total unique lemmas: {len(words)}")
    for tier_name, info in tier_breakdown.items():
        print(f"  {tier_name}: {info['count']} words (levels {info['levels']})")


if __name__ == "__main__":
    print("Merging levels...")
    levels = merge_levels()
    print("\nRebuilding vocabulary index...")
    rebuild_vocab_index(levels)
    print("\nDone!")
