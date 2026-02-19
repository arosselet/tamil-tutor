#!/usr/bin/env python3
"""
Display progress dashboard for Tamil learning.
Reads learner.json and derives tier data from levels.json.

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


def get_tier_words(levels: dict) -> dict[int, list[str]]:
    """Extract all Tamil words per tier from levels.json."""
    tier_words: dict[int, set[str]] = {}
    for level_data in levels.values():
        tier = level_data.get("tier", 1)
        words = tier_words.setdefault(tier, set())
        for ep in level_data.get("episodes", []):
            for w in ep.get("vocab", []):
                words.add(w["tamil"])
    return {t: sorted(ws) for t, ws in tier_words.items()}


def main():
    base = Path(__file__).parent.parent
    learner = load_json(base / "progress" / "learner.json")
    levels = load_json(base / "curriculum" / "levels.json")

    if not learner:
        print("⚠️  No learner.json found. Start a session first.")
        return

    print("=" * 55)
    print("📊 MADRAS MAPPILLAI — STATUS REPORT")
    print("=" * 55)

    # Current position
    print(f"\n🎯 Current Position: Level {learner['current_level']}, Episode {learner['current_episode']}")
    print(f"📅 Total Sessions: {learner['total_sessions']}")

    # Streak
    streak = learner.get("streak", {})
    current_streak = streak.get("current", 0)
    best_streak = streak.get("best", 0)
    if current_streak > 0:
        print(f"🔥 Streak: {current_streak} days (Best: {best_streak})")
    elif best_streak > 0:
        print(f"💤 Streak: broken (Best was {best_streak})")
    else:
        print(f"🚀 Streak: Start your first session!")

    # Tier progress (derived from levels.json)
    if levels:
        tier_words = get_tier_words(levels)
        comfortable = set(learner.get("comfortable_words", []))
        mastered = set(learner.get("mastered_words", []))
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
    struggled = learner.get("struggled_words", [])
    if struggled:
        print(f"\n⚠️  STRUGGLED WORDS ({len(struggled)})")
        print("-" * 55)
        for word in struggled[:10]:
            print(f"  • {word}")
        if len(struggled) > 10:
            print(f"  ... and {len(struggled) - 10} more")

    # Recent sessions
    sessions = learner.get("sessions", [])
    if sessions:
        print(f"\n📝 RECENT SESSIONS")
        print("-" * 55)
        for session in sessions[-5:]:
            date = session.get("date", "?")
            level = session.get("level", "?")
            ep = session.get("episode", "?")
            energy = session.get("energy", "?")
            notes = session.get("notes", "")
            print(f"  {date} | L{level}E{ep} | {energy} | {notes[:40]}")

    # Recommendations
    print(f"\n💡 NEXT STEPS")
    print("-" * 55)
    if not sessions:
        print("  • Start with Level 1, Episode 1")
        print("  • Listen to audio/level1_ep1.mp3")
        print("  • Or start a session: [Tamil Lesson]")
    elif struggled:
        print(f"  • Review your {len(struggled)} struggled words before advancing")
        print(f"  • Current focus: Level {learner['current_level']}, Episode {learner['current_episode']}")
    else:
        print(f"  • Continue: Level {learner['current_level']}, Episode {learner['current_episode']}")

    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
