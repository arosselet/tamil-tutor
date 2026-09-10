#!/usr/bin/env python3
"""PHASE 2 — derive the lexicon from the observation log, and diff it against the
live file. READ-ONLY: nothing here writes state, and that is the phase.

Phase 3 is where the derived view becomes authoritative and the mutations leave
the writers. Before that can be trusted, every place the log and the ledger
disagree has to be EXPLAINED — a divergence is a finding, not a bug to paper
over. This file produces that list.

THE POLICY, in one sentence (open question 2 of `docs/observation_log_plan.md`):
**a rung is what the evidence supports — recognition climbs one step per passing
ear test and falls one per failure, production is the best result ever fired,
and only watched channels vote.**

WHY THE REPLAY MATCHES THE LIVE RULES rather than improving on them. It would be
easy to derive something smarter here — "solid needs two passes on separate
days", say. That would be a policy change and a data change landing together,
and every divergence would then have two possible causes. So Phase 2 replays the
rules the writers already used (`apply_catch_verdict` moves one rung per catch;
`sync_state` demotes one per failed recall; production upgrades only). Anything
the diff reports is then attributable to EVIDENCE — which is the whole question.
Better policies are Phase 3's to argue, with a clean baseline behind them.

WHAT `seed` AND `self-report` DO HERE: nothing, and loudly. They are read, they
are counted, and they never move a rung. That single line is what four earlier
patches were each trying to say locally.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import observations
from state_io import (DEMOTE, LEXICON_PATH, PRODUCTION_RANK, RECOGNITION_NEXT,
                      RECOGNITION_RANK, load_json)

# Channels the system WATCHED. Everything else was DECLARED — recorded for
# provenance, never counted as evidence. This set is the policy's whole teeth.
WATCHED = {"session", "eavesdrop", "knock", "text", "volley", "challenge",
           "fielding", "audio", "check", "media"}

PRODUCTION_FOR = {"right": "cold", "partial": "hinted"}


def derive(events):
    """Fold the log into `{word: {recognition, production, tests, channels}}`.

    Pure: takes events, returns a dict, touches no file. Phase 3 reuses this
    exact function as the lexicon's reader, which is why it takes events rather
    than reading them itself."""
    view = {}
    for e in sorted(events, key=lambda e: e.get("at", "")):
        row = view.setdefault(e["word"], {"recognition": "struggled",
                                          "production": "none", "tests": 0,
                                          "channels": set(), "last_tested": None})
        row["channels"].add(e["channel"])
        if e["kind"] != "tested" or e["channel"] not in WATCHED:
            continue                      # declared, or not a test: no rung moves
        row["tests"] += 1
        row["last_tested"] = e.get("at")
        if e["axis"] == "recognition":
            if e["result"] == "right":
                row["recognition"] = RECOGNITION_NEXT.get(row["recognition"],
                                                          row["recognition"])
            elif e["result"] == "wrong":
                row["recognition"] = DEMOTE.get(row["recognition"], "struggled")
        elif e["axis"] == "production":
            nxt = PRODUCTION_FOR.get(e["result"] or "")
            if nxt and PRODUCTION_RANK[nxt] > PRODUCTION_RANK[row["production"]]:
                row["production"] = nxt
    return view


def classify(word, live, row):
    """Name WHY the log and the ledger disagree about one row. The categories are
    the point: an unexplained divergence blocks Phase 3, an explained one does
    not."""
    d_rec = RECOGNITION_RANK[row["recognition"]] if row else 0
    l_rec = RECOGNITION_RANK.get(live.get("recognition", "struggled"), 0)
    d_pro = PRODUCTION_RANK[row["production"]] if row else 0
    l_pro = PRODUCTION_RANK.get(live.get("production", "none"), 0)
    if d_rec == l_rec and d_pro == l_pro:
        return "agree"
    if d_rec > l_rec or d_pro > l_pro:
        # The log knows something the ledger lost — a write that never landed, or
        # a demotion the ledger took and the evidence does not support.
        return "ledger-lost"
    asserts = bool(live.get("reps") or live.get("heard_on")
                   or live.get("production", "none") != "none")
    if row and "seed" in row["channels"] and not row["tests"]:
        return "seed-inflated"
    if asserts and (not row or not row["tests"]):
        return "uncorroborated"
    return "under-evidenced"


def main():
    ap = argparse.ArgumentParser(description="Derive the lexicon from the log and diff it")
    ap.add_argument("--show", metavar="CATEGORY",
                    help="list the rows in one category")
    args = ap.parse_args()

    events = observations.load_json(observations.OBSERVATIONS_PATH) or []
    lex = load_json(LEXICON_PATH) or {}
    view = derive(events)

    buckets = {}
    for word, live in lex.items():
        buckets.setdefault(classify(word, live, view.get(word)), []).append(word)

    print(f"derived {len(view)} words from {len(events)} events · "
          f"live lexicon has {len(lex)} rows\n")
    print("DIVERGENCE")
    for name in ("agree", "seed-inflated", "uncorroborated", "under-evidenced",
                 "ledger-lost"):
        rows = buckets.get(name, [])
        print(f"  {name:<18} {len(rows):>4}")
    orphan = set(view) - set(lex)
    print(f"  {'events, no row':<18} {len(orphan):>4}")

    if args.show:
        for word in sorted(buckets.get(args.show, [])):
            live, row = lex[word], view.get(word)
            print(f"  {word}  live={live.get('recognition')}/{live.get('production','none')}"
                  f"  derived={(row or {}).get('recognition','struggled')}/"
                  f"{(row or {}).get('production','none')}"
                  f"  tests={(row or {}).get('tests',0)}")


if __name__ == "__main__":
    main()
