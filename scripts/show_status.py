#!/usr/bin/env python3
"""
Display progress dashboard for Tamil learning.
Reads learner.json and derives tier data from tier_X_name.json files.

Usage:
    python scripts/show_status.py
"""

import json
from pathlib import Path


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_tier_words(tiers_data: list) -> dict[int, list[str]]:
    """Extract all Tamil words per tier from consolidated tier files."""
    tier_words: dict[int, set[str]] = {}
    for data in tiers_data:
        tier_num = int(data.get("tier", 1))
        words = tier_words.setdefault(tier_num, set())
        for v in data.get("vocabulary", []):
            words.add(v["tamil"])
    return {t: sorted(ws) for t, ws in tier_words.items()}


def main():
    base = Path(__file__).parent.parent
    learner = load_json(base / "progress" / "learner.json")
    vocab_state = load_json(base / "progress" / "vocab_state.json")
    
    # Load all Tier data
    tiers_dir = base / "curriculum" / "tiers"
    tiers_data = []
    if tiers_dir.exists():
        for f in sorted(tiers_dir.glob("tier_*.json")):
            tiers_data.append(load_json(f))

    if not learner or not vocab_state:
        print("⚠️  No learner.json or vocab_state.json found. Start a session first.")
        return

    # Merge data for display logic (preferring vocab_state for words and sessions)
    display_data = {**learner, **vocab_state}

    print("=" * 55)
    print("📊 COIMBATORE MAPPILLAI — STATUS REPORT")
    print("=" * 55)

    # Current position
    print(f"\n🎯 Current Position: Tier {display_data.get('current_tier', 1)}")
    print(f"📅 Total Sessions: {display_data.get('total_sessions', 0)}")

    # Streak
    streak = display_data.get("streak", {})
    current_streak = streak.get("current", 0)
    best_streak = streak.get("best", 0)
    if current_streak > 0:
        print(f"🔥 Streak: {current_streak} days (Best: {best_streak})")
    elif best_streak > 0:
        print(f"💤 Streak: broken (Best was {best_streak})")
    else:
        print(f"🚀 Streak: Start your first session!")

    # Tier progress
    if tiers_data:
        tier_words = get_tier_words(tiers_data)
        comfortable = set(display_data.get("comfortable_words", []))
        mastered = set(display_data.get("mastered_words", []))
        known = comfortable | mastered

        total_words = sum(len(ws) for ws in tier_words.values())
        print(f"\n📚 VOCABULARY PROGRESS ({total_words} total lemmas)")
        print("-" * 55)

        tier_labels = {1: "Tier 1 Survival", 2: "Tier 2 Comfortable", 3: "Tier 3 Embedded"}

        for tier_num in sorted(tier_words.keys()):
            words = tier_words[tier_num]
            count = sum(1 for w in words if w in known)
            total = len(words)
            label = tier_labels.get(tier_num, f"Tier {tier_num}")
            pct = (count / total * 100) if total > 0 else 0
            bar_len = 20
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)

            print(f"  {label}")
            print(f"    [{bar}] {count}/{total} ({pct:.0f}%)")

    # Struggled words
    struggled = display_data.get("struggled_words", [])
    if struggled:
        print(f"\n⚠️  STRUGGLED WORDS ({len(struggled)})")
        print("-" * 55)
        for word in struggled[:10]:
            print(f"  • {word}")
        if len(struggled) > 10:
            print(f"  ... and {len(struggled) - 10} more")

    # Recent sessions
    sessions = display_data.get("session_history", [])
    if sessions:
        print(f"\n📝 RECENT SESSIONS")
        print("-" * 55)
        for session in sessions[-5:]:
            date = session.get("date", "?")
            tier = session.get("tier", "?")
            mission = session.get("mission", "?")
            zinger = session.get("zinger", "")
            print(f"  {date} | T{tier}M{mission} | {zinger}")

    # Recommendations
    print(f"\n💡 NEXT STEPS")
    print("-" * 55)
    print(f"  • Status: {display_data.get('status', 'Ready for more.')}")
    if not sessions:
        print("  • Start with Tier 1: Survival")
        print("  • Run a session: [Tamil Lesson]")
    elif struggled:
        print(f"  • Review your {len(struggled)} struggled words before advancing")
    
    print(f"  • Current focus: Tier {display_data.get('current_tier', 1)} Missions")

    print("\n" + "=" * 55)

    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
