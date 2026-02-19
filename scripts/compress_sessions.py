#!/usr/bin/env python3
"""
Compress old sessions in learner.json.

Sessions older than 7 days are folded: their comfortable/struggled outcomes
are merged into the accumulated word lists, and the session objects are removed.

Usage:
    python scripts/compress_sessions.py
    python scripts/compress_sessions.py --days 14   # Keep 14 days instead of 7
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse

BASE = Path(__file__).parent.parent


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def compress(days: int = 7):
    learner_path = BASE / "progress" / "learner.json"
    learner = load_json(learner_path)

    sessions = learner.get("sessions", [])
    if not sessions:
        print("No sessions to compress.")
        return

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    comfortable = set(learner.get("comfortable_words", []))
    struggled = set(learner.get("struggled_words", []))
    mastered = set(learner.get("mastered_words", []))

    recent = []
    compressed_count = 0

    for session in sessions:
        session_date = session.get("date", "")
        if session_date >= cutoff_str:
            # Keep recent sessions
            recent.append(session)
        else:
            # Fold outcomes into accumulated lists
            for word in session.get("comfortable", []):
                comfortable.add(word)
                struggled.discard(word)
            for word in session.get("struggled", []):
                if word not in comfortable:
                    struggled.add(word)
            compressed_count += 1

    # Promote: words in comfortable across many sessions that never appear
    # in struggled anymore → move to mastered
    # (For now, just maintain the lists. Promotion can be a future refinement.)

    learner["sessions"] = recent
    learner["comfortable_words"] = sorted(comfortable)
    learner["struggled_words"] = sorted(struggled)
    learner["mastered_words"] = sorted(mastered)

    # Update tier_progress targets from levels.json
    levels_path = BASE / "curriculum" / "levels.json"
    if levels_path.exists():
        levels = load_json(levels_path)
        tier_counts: dict[int, int] = {}
        for level_data in levels.values():
            tier = level_data.get("tier", 1)
            seen = set()
            for ep in level_data.get("episodes", []):
                for w in ep.get("vocab", []):
                    seen.add(w["tamil"])
            tier_counts[tier] = tier_counts.get(tier, 0) + len(seen)

        # Update targets (won't be exact due to cross-level dedup, but close enough)
        tier_progress = learner.get("tier_progress", {})
        tier_map = {1: "tier1", 2: "tier2", 3: "tier3"}
        for t, key in tier_map.items():
            if key in tier_progress:
                tier_progress[key]["target"] = tier_counts.get(t, tier_progress[key].get("target", 0))
        learner["tier_progress"] = tier_progress

    save_json(learner_path, learner)

    print(f"✅ Compressed {compressed_count} old sessions (older than {days} days)")
    print(f"   Kept {len(recent)} recent sessions")
    print(f"   Comfortable: {len(comfortable)} words")
    print(f"   Struggled: {len(struggled)} words")
    print(f"   Mastered: {len(mastered)} words")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress old sessions in learner.json")
    parser.add_argument("--days", type=int, default=7, help="Keep sessions from the last N days (default: 7)")
    args = parser.parse_args()
    compress(args.days)
