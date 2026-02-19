#!/usr/bin/env python3
"""
Display progress dashboard for Tamil learning.
Reads learner.json and vocabulary_index.json.

Usage:
    python scripts/show_status.py
"""

import json
from pathlib import Path
from datetime import datetime


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    base = Path(__file__).parent.parent
    learner = load_json(base / "progress" / "learner.json")
    vocab = load_json(base / "curriculum" / "vocabulary_index.json")

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

    # Tier progress
    if vocab:
        meta = vocab.get("metadata", {})
        tier_info = meta.get("tier_breakdown", {})

        print(f"\n📚 VOCABULARY PROGRESS ({meta.get('total_unique_lemmas', '?')} total lemmas)")
        print("-" * 55)

        comfortable = set(learner.get("comfortable_words", []))
        words = vocab.get("words", [])

        for tier_key, tier_data in tier_info.items():
            tier_num = int(tier_key.replace("tier", "").split("_")[0])
            tier_words = [w for w in words if w.get("tier") == tier_num]
            mastered = sum(1 for w in tier_words if w["tamil"] in comfortable)
            total = tier_data.get("count", len(tier_words))
            label = tier_key.replace("_", " ").title()
            pct = (mastered / total * 100) if total > 0 else 0
            bar_len = 20
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)

            print(f"  {label}")
            print(f"    [{bar}] {mastered}/{total} ({pct:.0f}%)")

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
