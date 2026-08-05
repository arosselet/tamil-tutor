#!/usr/bin/env python3
"""
Progress dashboard for the Tamil learning system — the human-facing "Show my status".

Word-state is read from progress/lexicon.json (the single source). The centerpiece
is the viability floor: of the words recognized, how many fire cold. Continuity
(status line) comes from learner.json; episodes from episodes.json.

Usage:
    python scripts/show_status.py
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sync_state import compute_floor, compute_engines, compute_deck, burn_rate, TRIP_DATE

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
        print("⚠️  Missing learner.json or lexicon.json. See BOOTSTRAP.md.")
        return

    print("=" * 55)
    print("📊 COIMBATORE MAPPILLAI — STATUS REPORT")
    print("=" * 55)

    # No streak theatre — recency is the honest signal, guilt-free (Enjoyment Clause).
    last = session_log[-1].get("date") if session_log else None
    if last:
        print(f"\n📅 Last logged session: {last}")

    # --- The deck: the headline during a sprint (same math as sync_state) ---
    deck = compute_deck(lexicon)
    if deck["total"]:
        days = (TRIP_DATE - date.today()).days
        surv_pct = deck["surv_cleared"] / deck["surv_total"] * 100 if deck["surv_total"] else 0.0
        print(f"\n★ TRIP DECK — the sprint headline · {days} days to touchdown")
        print("-" * 55)
        print(f"    [{bar(surv_pct)}] {deck['surv_cleared']}/{deck['surv_total']} survival cold ({surv_pct:.0f}%)")
        print(f"    Full deck: {deck['cleared']}/{deck['total']} fire cold")
        print(f"    Burn rate: {burn_rate(deck['surv_total'] - deck['surv_cleared'], days)}")
        if deck["catch_total"]:
            print(f"    Ear-only (catch): {deck['caught']}/{deck['catch_total']} solid")
        # Coverage beside progress (2026-07-25): cold/total cannot see the tail —
        # it read as a won sprint while most of the deck had never been worked.
        if deck["untouched"] or deck["catch_untouched"]:
            worked = deck["total"] - deck["untouched"]
            ear = f" · +{deck['catch_untouched']} ear-only" if deck["catch_untouched"] else ""
            print(f"    ⚠ Coverage: {worked}/{deck['total']} ever worked — "
                  f"{deck['untouched']} never touched ({deck['surv_untouched']} survival){ear}")

    # --- The viability floor (compute_floor: patterns excluded, same as sync_state) ---
    floor = compute_floor(lexicon)
    print("\n🎯 VIABILITY FLOOR — recognized words that fire cold")
    print("-" * 55)
    print(f"    [{bar(floor['pct'])}] {floor['cleared']}/{floor['total']} ({floor['pct']:.0f}%)")
    print(f"    Floor gap: {floor['total'] - floor['cleared']} recognized words not yet cold.")

    # --- Engines: generative patterns firing cold ---
    engines = compute_engines(lexicon)
    if engines["total"]:
        print("\n⚙️  ENGINES — patterns that fire a novel instance cold")
        print("-" * 55)
        print(f"    [{bar(engines['pct'])}] {engines['online']}/{engines['total']} online ({engines['pct']:.0f}%)")

    # --- Recognition breakdown (words only; patterns are metered above) ---
    levels = {"solid": 0, "comfortable": 0, "struggled": 0}
    n_words = 0
    for r in lexicon.values():
        if r.get("type") == "pattern":
            continue
        n_words += 1
        levels[r.get("recognition", "struggled")] = levels.get(r.get("recognition", "struggled"), 0) + 1
    print(f"\n📚 RECOGNITION ({n_words} words tracked)")
    print("-" * 55)
    print(f"    solid: {levels['solid']}   comfortable: {levels['comfortable']}   struggled: {levels['struggled']}")

    # Words only (patterns are Engines, metered above); ear-only items are marked —
    # they want soak, not drilling.
    struggled = sorted(
        w + (" (ear)" if r.get("direction") == "catch" else "")
        for w, r in lexicon.items()
        if r.get("recognition") == "struggled" and r.get("type") != "pattern")
    if struggled:
        print(f"\n⚠️  STRUGGLED ({len(struggled)}) — candidates for interactive drilling")
        print("-" * 55)
        print("    " + ", ".join(struggled[:12]) + (" ..." if len(struggled) > 12 else ""))

    # --- Episodes (self-contained doses — no listen bookkeeping) ---
    if episodes:
        recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:5]
        print("\n🎧 RECENT EPISODES (the immersion tank)")
        print("-" * 55)
        for m, ep in recent:
            dur = ep.get("duration_min")
            dur_str = f" ({dur:.1f} min)" if dur else ""
            print(f"    M{m}: {ep.get('title', '')}{dur_str}")

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
