#!/usr/bin/env python3
"""
Spaced-repetition callback picker — a small query over progress/lexicon.json.

A "callback" is a SOFT target: a recognized word going stale that the next audio
episode should try to weave back in for retention. It is NOT the intentional
payload for the next episode — that's the soak order Anna writes from a session.

Selection (rewired to the ear 2026-08-17 — see INTERVAL_DAYS for why):
  - Pool = EVERY row, words and patterns, at every recognition level. The old
    pool was recognized-words-only and skipped patterns; both exclusions were
    written when production was the headline, and both removed exactly the
    inventory the recognition headline now cares about.
  - Due-ness = a recognition-aware interval on `last_surfaced`. Solid is well
    retained (long interval); struggled has decayed most, and by the retrieval/
    storage account that makes it the most valuable thing to meet again, not
    the least (short interval).
  - Two pools, one clock: patterns get up to PATTERN_SLOTS of the ticket, because
    words outnumber them ~12:1 and would otherwise take every seat on staleness
    alone. Never more than half.
  - Never-surfaced rows are excluded: a return clock returns what was met. New
    ground is the main ticket's job (`coverage_key` sorts it to the head there).

Usage:
    python scripts/generate_callbacks.py [--max 5]
"""

import argparse
import json
from datetime import date
from pathlib import Path

from state_io import local_today

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"

# Days before an item is "due" to come back, by how well it is RETAINED on the
# ear (2026-08-17). This clock used to key on `production` — cold 21, hinted 10,
# none 5 — which was correct while production was the headline and is wrong now:
# due-ness was computed from the axis we retired. Same numbers, same expanding
# shape, keyed to the axis that decides whether he can follow a sentence.
#
# Bjork's retrieval/storage split is the reason the short end is short: the gain
# from a successful retrieval scales with how far retrieval strength has decayed,
# so a struggled item is not debt to feel bad about — it is the highest-yield
# inventory in the ledger, and 144 of the 313 rows are sitting in exactly that
# state with (until now) no scheduled return at all.
INTERVAL_DAYS = {"solid": 21, "comfortable": 10, "struggled": 5}
# Tie-break: when equally overdue, bring back the weaker trace first.
RECOGNITION_RANK = {"struggled": 0, "comfortable": 1, "solid": 2}
NEVER_SURFACED = 10 ** 6  # sentinel staleness for null last_surfaced
# THE MACHINES GET A LANE (2026-08-17). Pure overdue-order is right for one pool
# and wrong for two kinds of inventory. Letting patterns in (below) made them
# ELIGIBLE and not REACHABLE: on the live ledger 100 rows came back due, the
# first pattern sat at rank 59, and a 5-slot ticket therefore returned words
# only — the 26 machines had a return path in principle and none in fact. Words
# outnumber patterns ~12:1 and decay on the same clock, so the majority pool
# wins every slot forever unless the minority one is reserved a seat.
#
# The constitution's reason for the seat, not a tuning preference: the threshold
# is comprehension, and the machines carry the sentence skeleton he cannot hear.
# Capped at half the ticket so a reservation can never starve the words.
PATTERN_SLOTS = 2


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
        # PATTERNS ARE IN, as of 2026-08-17. They were excluded as "tracked
        # engines, not soak words" — true when an engine meant a thing he FIRES.
        # The engines are now metered on the ear too, and the 26 machines carry
        # the sentence skeleton he cannot hear; excluding them left the headline
        # set as the only inventory in the ledger with no return path at all.
        #
        # STRUGGLED IS IN, same date, and this is the bigger reversal. The old
        # rule dropped it because "repeated audio exposure doesn't fix cold-
        # production gaps" — sound reasoning aimed at production, and backwards
        # for recognition, which is precisely what repeated exposure DOES move.
        # It excluded 144 rows, the largest and cheapest-to-recover pool he owns.
        recog = rec.get("recognition", "struggled")
        interval = INTERVAL_DAYS.get(recog, 5)
        ds = days_since(rec.get("last_surfaced"), today)
        # NEVER-SURFACED ROWS ARE NOT DUE — they are new ground, not decayed
        # material, and a return clock returns what was actually met. They used
        # to enter at the NEVER_SURFACED sentinel and therefore outranked every
        # genuinely overdue row: on the live ledger all eight ticket slots came
        # back "(last: never surfaced)", so the clock had never once returned
        # anything. This is `retest_targets`' 2026-08-04 finding in a second
        # file, and the same argument applies — nothing is lost by leaving,
        # because `coverage_key` already sorts never-worked rows to the head of
        # the main ticket. 203 of 339 rows carry a date; that is the schedule.
        if ds is None:
            continue
        overdue = ds - interval
        if overdue >= 0:
            candidates.append({
                "word": word,
                "gloss": rec.get("gloss", ""),
                "production": rec.get("production", "none"),
                "recognition": recog,
                "direction": rec.get("direction", "fire"),
                "last_surfaced": rec.get("last_surfaced"),
                "overdue": overdue,
                "pattern": rec.get("type") == "pattern",
            })
    order = lambda c: (-c["overdue"], RECOGNITION_RANK.get(c["recognition"], 0))
    candidates.sort(key=order)
    natural = candidates[:max_n]
    pats = [c for c in candidates if c["pattern"]]
    # A FLOOR, NEVER A CEILING. When patterns already win seats on staleness the
    # natural order stands untouched; the reservation only tops up the case where
    # they won none. Capping instead would demote machines in the very situation
    # the seat exists to protect.
    reserved = min(len(pats), PATTERN_SLOTS, max_n // 2)
    if sum(1 for c in natural if c["pattern"]) >= reserved:
        return natural
    picked = pats[:reserved] + [c for c in candidates if not c["pattern"]][:max_n - reserved]
    picked.sort(key=order)
    return picked


def main():
    parser = argparse.ArgumentParser(description="Pick spaced-repetition callbacks from the lexicon")
    parser.add_argument("--max", type=int, default=5, help="Max callback words (default: 5)")
    args = parser.parse_args()

    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:  # empty ({}) is valid day-zero state; only missing is an error
        print("Error: progress/lexicon.json not found. See BOOTSTRAP.md.")
        return

    today = local_today()
    callbacks = due_callbacks(lexicon, today, args.max)

    print("CALLBACKS (soft target, weave into the next episode):")
    print("-" * 52)
    if not callbacks:
        print("  (nothing due — the recognized set is fresh)")
    for cb in callbacks:
        gloss = cb["gloss"] or "[no gloss]"
        when = cb["last_surfaced"] or "never surfaced"
        # Tag by the axis that SELECTED the row (2026-08-17). This read
        # `production` — floor-gap / retention — which mislabels every row now
        # that due-ness is computed on recognition: a struggled pattern pulled
        # back precisely because it had decayed printed "[retention]".
        tag = cb["recognition"] + (" · ear" if cb["direction"] == "catch" else "")
        print(f"  - {cb['word']} — {gloss}  [{tag}]  (last: {when})")

    # The backlog this file exists to drain — decayed rows, not production debt.
    backlog = len(due_callbacks(lexicon, today, 10 ** 6))
    print(f"\nDecay backlog: {backlog} met rows are past their return interval.")


if __name__ == "__main__":
    main()
