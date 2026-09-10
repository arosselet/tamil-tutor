#!/usr/bin/env python3
"""L0.7 — THE LEXICON IS A VIEW OVER THE OBSERVATION LOG (Phase 3, 2026-09-10).

Every evidence field on a lexicon row — `recognition`, `production`, `reps`,
`exposures`, `heard_on`, `last_surfaced`, `seen_in`, `taught_on` — is written by
exactly one function, `rebuild`, and it writes what the log supports. No writer
sets one directly; a writer records an event through `observe` and the rung
follows. The static half of a row (gloss, phonetic, type, register, direction,
pairs_with) is curriculum, not evidence, and stays hand-owned.

THE POLICY, in one sentence: **a rung is what watched tests support —
recognition climbs one per pass and falls one per miss, production is the best
grade ever fired, and declared channels never vote.** It replays the rules the
writers already used, so the cutover moved nothing the evidence did not, and a
better policy is one function away with a clean baseline behind it. A
recency-decayed rung was considered and refused: the ear is tested ~0.3 times a
day, so a clock would measure the instrument's cadence, not his ear.

THE FOLD IS SPARSE. A field is rewritten only where the log speaks to it; a row
the log has never mentioned keeps what the file says. On the live tree the log
speaks to every non-default value (the cutover carried each one as a `ledger`
event), so `--check` holds the file equal to the fold and CI runs it against the
real tree — that is the honesty guarantee. In a sandbox a fixture row keeps its
rungs until a writer speaks, which is what lets the suite state a row and then
drive a writer at it.

`seed` claims are the one exception to "unspoken keeps the file": a claim is an
opinion on an axis, so it makes the axis SPOKEN and then does not vote — the
fold returns the default. That single line is what four earlier patches were
each trying to say locally.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import observations
from observations import WATCHED
from state_io import (DEMOTE, LEXICON_PATH, PRODUCTION_RANK, RECOGNITION_NEXT,
                      build_phonetic_index, load_json, local_date, resolve, save_json)

EVIDENCE = ("recognition", "production", "reps", "exposures", "heard_on",
            "last_surfaced", "seen_in", "taught_on")
PRODUCTION_FOR = {"right": "cold", "partial": "hinted"}
EPISODE_SRC = re.compile(r"^episode:M?(\d+)$")


def derive(events):
    """Fold the log into `{word: evidence}`. Pure: events in, dict out, no file.

    `spoken` names the fields the log has an opinion on; `rebuild` rewrites only
    those. `tests` and `channels` are kept for the diff and the suite."""
    view = {}
    for e in sorted(events, key=lambda e: e.get("at") or ""):
        row = view.setdefault(e["word"], {
            "recognition": "struggled", "production": "none", "reps": 0,
            "exposures": 0, "heard_on": None, "last_surfaced": None, "seen_in": [],
            "taught_on": None, "tests": 0, "channels": set(), "spoken": set()})
        row["channels"].add(e["channel"])
        kind, axis, res = e["kind"], e.get("axis"), e.get("result")
        if kind == "claimed" and axis:
            row["spoken"].add(axis)          # an opinion: recorded, never counted
        if e["channel"] not in WATCHED:
            continue
        day = local_date(e.get("at") or "")
        day = day.isoformat() if day else None
        if day and kind in ("tested", "exposed", "taught"):
            row["last_surfaced"] = day
            row["spoken"].add("last_surfaced")
        if kind == "taught":
            row["taught_on"] = row["taught_on"] or day
            row["spoken"].add("taught_on")
            m = EPISODE_SRC.match(e.get("source") or "")
            if m and int(m.group(1)) not in row["seen_in"]:
                row["seen_in"].append(int(m.group(1)))
        elif kind == "exposed":
            row["exposures"] += 1
            row["spoken"].add("exposures")
        elif kind == "tested":
            row["tests"] = row["reps"] = row["reps"] + 1
            row["spoken"].add("reps")
            if axis == "recognition":
                row["heard_on"] = day or row["heard_on"]
                row["spoken"] |= {"recognition", "heard_on"}
                if res == "right":
                    row["recognition"] = RECOGNITION_NEXT.get(row["recognition"],
                                                              row["recognition"])
                elif res == "wrong":
                    row["recognition"] = DEMOTE.get(row["recognition"], "struggled")
            elif axis == "production":
                row["spoken"].add("production")
                nxt = PRODUCTION_FOR.get(res or "")
                if nxt and PRODUCTION_RANK[nxt] > PRODUCTION_RANK[row["production"]]:
                    row["production"] = nxt
    return view


def rebuild(lexicon: dict, events, only=None) -> list[str]:
    """Fold the log onto the rows, in place. `only` limits the rewrite to the
    words just written (every other row is already in sync, or `--check` says
    so). Returns words the log names that have no row — reported, never minted."""
    orphans = []
    for word, row in derive(events).items():
        if only is not None and word not in only:
            continue
        rec = lexicon.get(word)
        if rec is None:
            orphans.append(word)
            continue
        for field in row["spoken"]:
            rec[field] = row[field]
        if row["seen_in"]:
            rec["seen_in"] = sorted(set(rec.get("seen_in") or []) | set(row["seen_in"]))
    return orphans


def observe(events, lexicon: dict | None = None) -> list[dict]:
    """THE write path for evidence: append the events, fold them onto their
    rows. With `lexicon` given the caller's dict is folded in place and the
    caller saves; without it the file is loaded, folded and saved here."""
    written = observations.record_many(events)
    own = lexicon is None
    lexicon = load_json(LEXICON_PATH) or {} if own else lexicon
    rebuild(lexicon, load_json(observations.OBSERVATIONS_PATH) or [],
            only={e["word"] for e in written})
    if own:
        save_json(LEXICON_PATH, lexicon)
    return written


def expose(keys, channel: str, source: str = "", *, taught=(), kind="exposed",
           lexicon: dict | None = None, at: str | None = None) -> list[str]:
    """A dose carrying these words went out the door — the delivery seam every
    lane calls (episode registration, soak / drill / rotation sheet, knock push,
    queue drain). `taught` names the subset that was SHOWN, which is first
    contact and closes the teach gate; the rest merely appeared. Returns the
    keys that resolved; an unresolvable one is warned, never minted."""
    own = lexicon is None
    lex = (load_json(LEXICON_PATH) or {}) if own else lexicon
    if not lex or not keys:
        return []
    index = build_phonetic_index(lex)
    marked = []
    for k in keys:
        key = resolve(k, lex, index)
        if key is None:
            print(f"   ⚠ exposure: '{k}' not in lexicon — skipped")
        elif key not in marked:
            marked.append(key)
    shown = {resolve(k, lex, index) for k in taught}
    if marked:
        observe([dict(word=k, channel=channel, source=source, at=at,
                      kind="taught" if k in shown else kind) for k in marked], lexicon=lex)
        if own:
            save_json(LEXICON_PATH, lex)
            print(f"   Exposure stamped: {', '.join(marked)}")
    return marked


def divergence(lexicon: dict, events) -> list[str]:
    """Every row whose evidence fields differ from the fold — the honesty check.
    Empty on a healthy tree; a name here means a writer set a field by hand."""
    view = derive(events)
    out = []
    for word, rec in lexicon.items():
        row = view.get(word)
        if not row:
            continue
        for field in row["spoken"]:
            if field == "seen_in":
                continue
            if (rec.get(field) or None) != (row[field] or None):
                out.append(f"{word}: {field} file={rec.get(field)!r} log={row[field]!r}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Check the lexicon against the observation log")
    ap.add_argument("--rebuild", action="store_true",
                    help="rewrite every evidence field from the log (the cutover, or a repair)")
    args = ap.parse_args()
    events = load_json(observations.OBSERVATIONS_PATH) or []
    lex = load_json(LEXICON_PATH) or {}
    if args.rebuild:
        orphans = rebuild(lex, events)
        save_json(LEXICON_PATH, lex)
        print(f"rebuilt {len(lex)} rows from {len(events)} events"
              + (f" · {len(orphans)} words in the log have no row: {orphans[:5]}" if orphans else ""))
    bad = divergence(lex, events)
    print(f"{len(lex)} rows · {len(events)} events · {len(bad)} divergent")
    for line in bad[:40]:
        print("  " + line)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
