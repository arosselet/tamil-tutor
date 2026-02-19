#!/usr/bin/env python3
"""
Build vocabulary index from levels.json.
Produces curriculum/vocabulary_index.json with unique lemmas, English translations,
and tier/mastery metadata.
"""

import json
from pathlib import Path
from datetime import datetime


def build_index():
    base_dir = Path(__file__).parent.parent
    levels_file = base_dir / "curriculum" / "levels.json"
    output_file = base_dir / "curriculum" / "vocabulary_index.json"

    with open(levels_file, "r", encoding="utf-8") as f:
        levels = json.load(f)

    # Collect unique words, preserving first-seen metadata
    seen = {}
    for level_num, level_data in sorted(levels.items(), key=lambda x: int(x[0])):
        tier = level_data.get("tier", 1)
        category = level_data.get("title", "").lower().replace(" ", "_").replace("&", "and")

        for ep in level_data.get("episodes", []):
            for word_obj in ep.get("vocab", []):
                tamil = word_obj.get("tamil", "").strip()
                english = word_obj.get("english", "").strip()

                if not tamil:
                    continue

                # First occurrence wins for metadata
                if tamil not in seen:
                    seen[tamil] = {
                        "tamil": tamil,
                        "english": english,
                        "level": int(level_num),
                        "episode": ep.get("episode", 0),
                        "tier": tier,
                        "category": category,
                        "mastery_score": 0,
                        "times_reviewed": 0,
                        "last_reviewed": None,
                    }

    words = list(seen.values())

    # Count per tier
    tier_counts = {}
    for w in words:
        t = w["tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1

    index = {
        "metadata": {
            "total_unique_lemmas": len(words),
            "tier_breakdown": {
                "tier1_survival": {"count": tier_counts.get(1, 0), "levels": "1-3"},
                "tier2_comfortable": {"count": tier_counts.get(2, 0), "levels": "4-5"},
                "tier3_embedded": {"count": tier_counts.get(3, 0), "levels": "6-8"},
            },
            "last_built": datetime.now().isoformat(),
        },
        "words": words,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"✅ Built vocabulary index: {len(words)} unique lemmas")
    print(f"   Tier 1 (Survival):    {tier_counts.get(1, 0)} words")
    print(f"   Tier 2 (Comfortable): {tier_counts.get(2, 0)} words")
    print(f"   Tier 3 (Embedded):    {tier_counts.get(3, 0)} words")
    print(f"   Output: {output_file}")


if __name__ == "__main__":
    build_index()
