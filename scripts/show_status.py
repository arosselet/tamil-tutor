#!/usr/bin/env python3
"""
Progress dashboard for the Tamil learning system — the human-facing "Show my status".

Word-state is read from progress/lexicon.json (the single source). The centerpiece
is the viability floor: of the words recognized, how many fire cold. Continuity
(streak, status line) comes from learner.json; episodes from episodes.json.

Usage:
    python scripts/show_status.py
"""

import json
from pathlib import Path

RECOGNIZED = {"comfortable", "solid"}


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def main():
    base = Path(__file__).parent.parent
    learner = load_json(base / "progress" / "learner.json")
    lexicon = load_json(base / "progress" / "lexicon.json")
    episodes = load_json(base / "progress" / "episodes.json") or {}
    session_log = load_json(base / "progress" / "session_log.json") or []

    if not learner or not lexicon:
        print("⚠️  Missing learner.json or lexicon.json. Run migrate_lexicon.py / start a session.")
        return

    print("=" * 55)
    print("📊 COIMBATORE MAPPILLAI — STATUS REPORT")
    print("=" * 55)

    streak = learner.get("streak", {})
    cur, best = streak.get("current", 0), streak.get("best", 0)
    if cur > 0:
        print(f"\n🔥 Streak: {cur} days (Best: {best})")
    elif best > 0:
        print(f"\n💤 Streak: broken (Best was {best})")
    else:
        print("\n🚀 Streak: Start your first session!")

    # --- The viability floor: the one honest meter ---
    recognized = [w for w, r in lexicon.items() if r.get("recognition") in RECOGNIZED]
    cold = [w for w in recognized if lexicon[w].get("production") == "cold"]
    total = len(recognized)
    pct = (len(cold) / total * 100) if total else 0
    print(f"\n🎯 VIABILITY FLOOR — recognized words that fire cold")
    print("-" * 55)
    print(f"    [{bar(pct)}] {len(cold)}/{total} ({pct:.0f}%)")
    print(f"    Floor gap: {total - len(cold)} recognized words not yet cold.")

    # --- Recognition breakdown ---
    levels = {"solid": 0, "comfortable": 0, "struggled": 0}
    for r in lexicon.values():
        levels[r.get("recognition", "struggled")] = levels.get(r.get("recognition", "struggled"), 0) + 1
    print(f"\n📚 RECOGNITION ({len(lexicon)} words tracked)")
    print("-" * 55)
    print(f"    solid: {levels['solid']}   comfortable: {levels['comfortable']}   struggled: {levels['struggled']}")

    struggled = sorted(w for w, r in lexicon.items() if r.get("recognition") == "struggled")
    if struggled:
        print(f"\n⚠️  STRUGGLED ({len(struggled)}) — candidates for interactive drilling")
        print("-" * 55)
        print("    " + ", ".join(struggled[:12]) + (" ..." if len(struggled) > 12 else ""))

    # --- Episodes ---
    if episodes:
        recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:5]
        print(f"\n🎧 RECENT EPISODES")
        print("-" * 55)
        for m, ep in recent:
            print(f"    M{m}: {ep.get('listens', 0)}x — {ep.get('title', '')}")

    # --- Momentum: recent sessions from the append-only log ---
    if session_log:
        print(f"\n📈 RECENT SESSIONS ({len(session_log)} logged)")
        print("-" * 55)
        for s in session_log[-5:]:
            moved = len(s.get("cold", [])) + len(s.get("hinted", []))
            print(f"    {s.get('date','?')} | floor {s.get('floor_pct','?')}% | +{moved} produced | {s.get('note','')[:40]}")

    print(f"\n💡 {learner.get('status', 'Ready for more.')}")
    print("=" * 55)


if __name__ == "__main__":
    main()
