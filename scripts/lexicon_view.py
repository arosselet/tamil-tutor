#!/usr/bin/env python3
"""L0.7 — THE LEXICON IS A VIEW OVER THE OBSERVATION LOG (Phase 3, 2026-09-10).

Every evidence field on a lexicon row — `recognition`, `production`, `reps`,
`exposures`, `heard_on`, `last_surfaced`, `seen_in`, `taught_on` — is written by
exactly one function, `rebuild`, and it writes what the log supports. No writer
sets one directly; a writer records an event through `observe` and the rung
follows. The static half of a row (gloss, type, register, direction,
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
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import observations
from observations import WATCHED
from state_io import (DEMOTE, LEXICON_PATH, PRODUCTION_RANK, RECOGNITION_NEXT,
                      load_json, local_date, resolve, save_json)

EVIDENCE = ("recognition", "production", "reps", "exposures", "heard_on",
            "last_surfaced", "seen_in", "taught_on", "heard_times")
PRODUCTION_FOR = {"right": "cold", "partial": "hinted"}
EPISODE_SRC = re.compile(r"^episode:M?(\d+)$")
# A Teach Beat here needs nothing to prove he received it: Anna said it TO him,
# live, and there is no press of play between the teaching and the ear. Every
# other channel hands a file to a phone and hopes. Keep this set at one until a
# second channel can show the same thing (2026-09-13).
SELF_ATTENDING = {"session"}


def derive(events):
    """Fold the log into `{word: evidence}`. Pure: events in, dict out, no file.

    `spoken` names the fields the log has an opinion on; `rebuild` rewrites only
    those. `tests` and `channels` are kept for the diff and the suite."""
    view = {}
    for e in sorted(events, key=lambda e: e.get("at") or ""):
        row = view.setdefault(e["word"], {
            "recognition": "struggled", "production": "none", "reps": 0,
            "exposures": 0, "heard_on": None, "last_surfaced": None, "seen_in": [],
            "taught_on": None, "taught_pending": None, "heard_times": 0,
            "tests": 0, "channels": set(), "spoken": set()})
        row["channels"].add(e["channel"])
        kind, axis, res = e["kind"], e.get("axis"), e.get("result")
        if kind == "claimed" and axis:
            row["spoken"].add(axis)          # an opinion: recorded, never counted
        if e["channel"] not in WATCHED:
            continue
        day = local_date(e.get("at") or "")
        day = day.isoformat() if day else None
        if day and kind in ("tested", "exposed", "taught", "attended"):
            row["last_surfaced"] = day
            row["spoken"].add("last_surfaced")
        if kind == "taught":
            # `taught_on` is SPOKEN either way — that is the whole demotion. A
            # delivery-channel Teach Beat states an opinion the fold then
            # declines to count, exactly as a `seed` claim does, so a row taught
            # only by a render derives to None and `rebuild` writes the None.
            # No migration, no history rewrite: the events stay, they stop voting.
            row["spoken"].add("taught_on")
            if e["channel"] in SELF_ATTENDING:
                row["taught_on"] = row["taught_on"] or day
            else:
                row["taught_pending"] = row["taught_pending"] or day
            m = EPISODE_SRC.match(e.get("source") or "")
            if m and int(m.group(1)) not in row["seen_in"]:
                row["seen_in"].append(int(m.group(1)))
        elif kind == "attended":
            # The press of play that DISCHARGES a pending Teach Beat — and never
            # creates one. `or day` sat here for one commit and was the whole bug
            # wearing a new coat: a rating exposes every word the episode spoke,
            # so attendance-creates-teaching would have marked an entire tape
            # taught the moment he rated it. "Hearing is not knowing"
            # (2026-08-23) is exactly this line. Dated to the TEACHING, not to
            # the listening — the beat is when first contact happened.
            row["spoken"].add("taught_on")
            row["taught_on"] = row["taught_on"] or row["taught_pending"]
            # ATTENDANCE IMPLIES EXPOSURE, and saying so here is what keeps the
            # background rotation loop closed. The rating lane used to emit
            # `exposed`; if `attended` merely replaced it, `exposures` would stop
            # counting and coverage would quietly regress — s86's other half,
            # which warns that deleting a stamp "fixes" a symptom and silently
            # breaks the loop that makes coverage guaranteed rather than hoped
            # for. One event, both facts: he heard it, and it went past him.
            row["exposures"] += 1
            row["spoken"].add("exposures")
            # HOW MANY TIMES HE PRESSED PLAY ON A DOSE CARRYING THIS WORD
            # (2026-09-19, Andrew's design: one tap per listen). `exposures`
            # cannot answer this — every render lane increments it when a dose
            # SHIPS, so it conflates "was in something that went out" with "he
            # heard it". This counts only the kind that is a fact about Andrew.
            #
            # It is the diagnostic he asked for and the system could not give:
            # "he heard it three times and still missed the drift" and "he heard
            # it once and got it" are opposite findings, and until now they read
            # identically in the ledger.
            row["heard_times"] += 1
            row["spoken"].add("heard_times")
        elif kind == "exposed":
            row["exposures"] += 1
            row["spoken"].add("exposures")
        elif kind == "tested":
            # A watched test is attendance evidence after the fact: something
            # asked and he answered, so he was demonstrably there for the word.
            # This is what keeps the 110 render-taught-but-tested rows seen
            # while the 142 never-tested ones go back to UNSEEN (2026-09-13).
            row["taught_on"] = row["taught_on"] or row["taught_pending"]
            row["tests"] = row["reps"] = row["reps"] + 1
            row["spoken"].add("reps")
            if axis == "recognition":
                # THE EAR'S STAMP, AND ONLY THE EAR'S (2026-09-20). The rung is
                # what he KNOWS and a typed answer is real evidence of it;
                # `heard_on` is what his EAR was tested on, and a typed answer is
                # no evidence of that at all. Splitting them here is what stops
                # `is_heard`, `machines heard` and the never-tested draw pool
                # counting a chat line as a listen.
                #
                # SPOKEN either way — the same demotion shape as `taught_on`
                # above: the events stay, a text test stops voting on this one
                # field, and the fold writes the None. No migration, and every
                # pre-existing event gets its medium from its channel.
                row["spoken"] |= {"recognition", "heard_on"}
                if observations.medium_of(e) == "audio":
                    row["heard_on"] = day or row["heard_on"]
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
           mint: dict | None = None, lexicon: dict | None = None,
           at: str | None = None) -> list[str]:
    """A dose carrying these words went out the door — the delivery seam every
    lane calls (episode registration, soak / drill / rotation sheet, knock push,
    queue drain). `taught` names the subset that was SHOWN, which is first
    contact and closes the teach gate; the rest merely appeared. Returns the
    keys that resolved; an unresolvable one is warned, never minted — UNLESS the
    lane hands its static row in `mint` (2026-09-13, the rotation's intake quota).
    That door is narrow on purpose: the lane mints only what a teaching movement
    actually played."""
    own = lexicon is None
    lex = (load_json(LEXICON_PATH) or {}) if own else lexicon
    if not lex or not keys:
        return []
    for k, row in (mint or {}).items():
        if k not in lex:
            lex[k] = {"recognition": "struggled", "production": "none",
                      "seen_in": [], "last_surfaced": None, **row}
            print(f"   + intake: '{k}' enters the lexicon")
    marked = []
    for k in keys:
        key = resolve(k, lex)
        if key is None:
            print(f"   ⚠ exposure: '{k}' not in lexicon — skipped")
        elif key not in marked:
            marked.append(key)
    shown = {resolve(k, lex) for k in taught}
    if marked:
        observe([dict(word=k, channel=channel, source=source, at=at,
                      kind="taught" if k in shown else kind) for k in marked], lexicon=lex)
        if own:
            save_json(LEXICON_PATH, lex)
            print(f"   Exposure stamped: {', '.join(marked)}")
    return marked


def remerge() -> Path:
    """Resolve a rebase conflict on `lexicon.json` — the DERIVED resolver in
    `publish.py`'s net (2026-09-10, after run 34520445739 lost a judged reply to
    exactly this). Two writers colliding on the ledger never disagree about
    EVIDENCE: that is the fold of `observations.json`, which the union pass has
    already merged on disk by the time this runs. They can each have minted a
    row or filled a gloss, so the static halves are unioned by key — upstream's
    row where both have one, ours filling any field upstream left empty — and
    every evidence field is then rebuilt from the merged log.

    During a rebase stage :2 is UPSTREAM and :3 is OURS (see `_union_conflict`).
    Returns the path written, which is the contract `DERIVED` checks."""
    import subprocess

    def side(stage):
        r = subprocess.run(["git", "show", f":{stage}:progress/lexicon.json"],
                           cwd=LEXICON_PATH.parent.parent, capture_output=True,
                           text=True, encoding="utf-8")
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}

    theirs, ours = side(2), side(3)
    merged = {k: dict(v) for k, v in theirs.items()}
    for word, rec in ours.items():
        row = merged.setdefault(word, {})
        for field, value in rec.items():
            if field not in EVIDENCE and not row.get(field):
                row[field] = value
    orphans = rebuild(merged, load_json(observations.OBSERVATIONS_PATH) or [])
    save_json(LEXICON_PATH, merged)
    print(f"   ↳ lexicon re-merged: {len(theirs)} theirs + {len(ours)} ours -> {len(merged)} "
          f"rows, evidence rebuilt from the log"
          + (f"; {len(orphans)} logged words have no row" if orphans else ""))
    return LEXICON_PATH


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
