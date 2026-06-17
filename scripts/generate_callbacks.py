#!/usr/bin/env python3
"""
Spaced-repetition callback picker — a small query over progress/lexicon.json.

A "callback" is a SOFT target: a recognized word going stale that the next audio
episode should try to weave back in for retention. It is NOT the intentional
payload for the next episode — that's the soak order Anna writes from a session.

Selection:
  - Pool = recognized words (comfortable + solid). Struggled words are EXCLUDED:
    repeated audio exposure doesn't fix cold-production gaps; those belong in
    Anna's interactive modalities (roleplay, drill), not another podcast callback.
  - Due-ness = a state-aware interval on `last_surfaced`. A word produced `cold`
    is well-retained (long interval); a recognized word not yet cold is the floor
    gap (short interval — soaking helps it most).
  - Cold start: right after migration most `last_surfaced` are null, so selection
    falls back to floor-gap-first. As Anna logs sessions the dates accrue and this
    becomes genuine spaced repetition.

Usage:
    python scripts/generate_callbacks.py [--max 5]
"""

import argparse
import json
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"

RECOGNIZED = {"comfortable", "solid"}
# Days before a recognized word is "due" for a callback, by retention strength.
INTERVAL_DAYS = {"cold": 21, "hinted": 10, "none": 5}
# Tie-break: when equally overdue, soak the floor gap before the already-cold.
PRODUCTION_RANK = {"none": 0, "hinted": 1, "cold": 2}
NEVER_SURFACED = 10 ** 6  # sentinel staleness for null last_surfaced


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def days_since(iso: str | None, today: date) -> int | None:
    if not iso:
        return None
    y, m, d = (int(x) for x in iso.split("-"))
    return (today - date(y, m, d)).days


def due_callbacks(lexicon: dict, today: date, max_n: int) -> list[dict]:
    candidates: list[dict] = []
    for word, rec in lexicon.items():
        if rec.get("recognition") not in RECOGNIZED:
            continue
        prod = rec.get("production", "none")
        interval = INTERVAL_DAYS.get(prod, 5)
        ds = days_since(rec.get("last_surfaced"), today)
        overdue = NEVER_SURFACED if ds is None else ds - interval
        if overdue >= 0:
            candidates.append({
                "word": word,
                "gloss": rec.get("gloss", ""),
                "production": prod,
                "last_surfaced": rec.get("last_surfaced"),
                "overdue": overdue,
            })
    candidates.sort(key=lambda c: (-c["overdue"], PRODUCTION_RANK.get(c["production"], 0)))
    return candidates[:max_n]


def main():
    parser = argparse.ArgumentParser(description="Pick spaced-repetition callbacks from the lexicon")
    parser.add_argument("--max", type=int, default=5, help="Max callback words (default: 5)")
    args = parser.parse_args()

    lexicon = load_json(LEXICON_PATH)
    if not lexicon:
        print("Error: progress/lexicon.json not found. See BOOTSTRAP.md.")
        return

    today = date.today()
    callbacks = due_callbacks(lexicon, today, args.max)

    print(f"CALLBACKS (soft target, weave into the next episode):")
    print("-" * 52)
    if not callbacks:
        print("  (nothing due — the recognized set is fresh)")
    for cb in callbacks:
        gloss = cb["gloss"] or "[no gloss]"
        when = cb["last_surfaced"] or "never surfaced"
        gap = "floor-gap" if cb["production"] != "cold" else "retention"
        print(f"  - {cb['word']} — {gloss}  [{gap}]  (last: {when})")

    floor_gap = sum(1 for r in lexicon.values()
                    if r.get("recognition") in RECOGNIZED and r.get("production") != "cold")
    print(f"\nFloor gap: {floor_gap} recognized words not yet firing cold.")


if __name__ == "__main__":
    main()
