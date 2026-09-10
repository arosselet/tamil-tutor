#!/usr/bin/env python3
"""PHASE 1 — reconstruct the observation log from what the repo already recorded.

Phase 0 wired only what nothing else captures (`taught`, `claimed`). Everything
else was left deliberately uninstrumented because it is DERIVABLE, and this is
the file that makes good on that: `knock_log.json` holds every judged reply with
its verdict and its fired lists, `session_log.json` holds every cold / hinted /
demoted row by date, and git holds the lexicon's first populated commit — the
153 rows Andrew estimated before session one.

WHAT THIS REPLACES: the guesswork in `docs/ledger_audit_2026-09-10.md`. That
sampled 30 rows to estimate an error rate because nothing could answer the
question directly. This answers it for all of them — not "what does Andrew
know", which still needs testing, but "what evidence exists for this row, and
where did it come from", which is the question that was actually unanswerable.

IDEMPOTENT BY CONSTRUCTION. Every backfilled event's `id` is a digest of the
facts that produced it, so a second run mints the identical ids and writes
nothing new. That matters more than it looks: this will be re-run as the
derivation improves (Phase 2 diffs its output against the live lexicon), and a
backfill that doubles its rows on the second pass is a backfill nobody dares
re-run. Live events keep their random uuid4 — only reconstruction is keyed.

WHAT IT REFUSES TO INVENT, and each absence is reported rather than filled:
  - `reply_verdict: "chat"` (40 of 87) is Andrew talking, not a test. No event.
  - A word that resolves to no lexicon row is counted and named, never guessed.
  - EXPOSURE COUNTS. A row's `exposures` was a bare integer with no dates
    behind it; the cutover carries the last delivery stamp as one `ledger`
    event and lets the counter restart. It is the fourth sort key of a fairness
    queue, and every row reset together.
  - THE WORDS HE NAMED OUT OF A TAPE before 2026-09-10, and the session
    promotions before that date: recorded live since, unrecoverable before.
    The cutover carries the RUNG they left behind (below), not the event.

THE CUTOVER (`--cutover`, 2026-09-10, Phase 3): the moment the lexicon stopped
being mutated and became the fold. Every live rung the log cannot show is
carried as a `ledger` event — "a watched writer moved this and the receipt is
lost" — EXCEPT the recognition rung of a seeded row, which is the day-one claim
finally ceasing to vote. Then every row is rebuilt from the log and the two
dead fields (`deck`, `lemma`) are dropped. Idempotent like the rest: a second
run finds no deficit and writes nothing.

DRY RUN IS THE DEFAULT. `--write` is required to touch the file, because this
reads history and history does not change: a run that surprises you should cost
nothing to have made.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import lexicon_view
import observations
from state_io import (BASE, KNOCK_LOG_PATH, LEXICON_PATH, PRODUCTION_RANK,
                      RECOGNITION_RANK, SESSION_LOG_PATH, load_json, save_json)

# The lexicon's first populated commit: 153 rows at solid 93 / comfortable 54 /
# struggled 6, before a single session had happened. `profile.md` calls this the
# "~100 word families by his own estimate"; the 2026-08-23 root cause calls it
# the defect's origin. It is not evidence and never was — it is a CLAIM, and
# giving it a channel is what finally lets every reader say so.
SEED_COMMIT = "f1d9d3e"


def digest(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def event(at, word, channel, kind, axis=None, result=None, source="", note=""):
    return {"id": digest(source, word, kind, axis, result), "at": at, "word": word,
            "channel": channel, "kind": kind, "axis": axis, "result": result,
            "source": source, "note": note}


def from_seed(report):
    """The day-one estimate, as claims rather than as knowledge."""
    r = subprocess.run(["git", "show", f"{SEED_COMMIT}:progress/lexicon.json"],
                       cwd=BASE, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        report.append(f"! seed commit {SEED_COMMIT} unreadable — no seed events")
        return []
    rows = json.loads(r.stdout)
    at = subprocess.run(["git", "show", "-s", "--format=%cI", SEED_COMMIT], cwd=BASE,
                        capture_output=True, text=True, encoding="utf-8").stdout.strip()
    out = [event(at, w, "seed", "claimed", axis="recognition",
                 source=f"git:{SEED_COMMIT}",
                 note=f"declared {v.get('recognition', '?')} before session one")
           for w, v in rows.items()]
    report.append(f"seed      {len(out):>4} claims from {SEED_COMMIT} ({at[:10]})")
    return out


# A judged reply's verdict, per axis. `chat` is absent on purpose — it means he
# talked, which is not a test of anything and must not become one.
EAR = observations.CATCH_RESULT
CUTOVER = "2026-09-10"


def from_knocks(report):
    """Every judged reply. The ear lane scores its declared target; every lane
    scores the words the judge saw fire."""
    log = load_json(KNOCK_LOG_PATH) or []
    out, skipped_chat = [], 0
    for e in log:
        verdict = e.get("reply_verdict")
        if not verdict:
            continue
        at = e.get("reply_at") or e.get("timestamp") or ""
        src = f"knock:{e.get('timestamp', '')}"
        modality = e.get("modality") or "knock"
        if verdict == "chat":
            skipped_chat += 1
            continue
        # The ear: one declared target per tape, scored caught / half / missed.
        target = e.get("expected_target")
        if modality == "eavesdrop" and target and verdict in EAR:
            out.append(event(at, target, "eavesdrop", "tested", axis="recognition",
                             result=EAR[verdict], source=src,
                             note=f"declared target, {verdict}"))
        # The mouth: cold is unaided, capped rode the hinted rung, and anything
        # else in `reply_fired` fired with help. Three results, not two.
        cold = set(e.get("reply_fired_cold") or [])
        capped = set(e.get("reply_fired_capped") or [])
        for word in (e.get("reply_fired") or []):
            res = "right" if word in cold else ("partial" if word in capped else "partial")
            out.append(event(at, word, modality, "tested", axis="production",
                             result=res, source=src,
                             note="cold fire" if word in cold else f"{verdict} fire"))
    report.append(f"knocks    {len(out):>4} events from {len(log)} entries "
                  f"({skipped_chat} 'chat' replies skipped — talking is not a test)")
    return out


def from_sessions(report):
    """Anna's own observation, one row per session day."""
    out = []
    for day in (load_json(SESSION_LOG_PATH) or []):
        at, src = f"{day['date']}T12:00:00Z", f"session:{day['date']}"
        for word in (day.get("cold") or []):
            out.append(event(at, word, "session", "tested", axis="production",
                             result="right", source=src, note="fired cold in session"))
        for word in (day.get("hinted") or []):
            out.append(event(at, word, "session", "tested", axis="production",
                             result="partial", source=src, note="fired with a hint"))
        for word in (day.get("demoted") or []):
            out.append(event(at, word, "session", "tested", axis="recognition",
                             result="wrong", source=src, note="failed cold recall"))
    report.append(f"sessions  {len(out):>4} events")
    return out


def git_date(*paths) -> str:
    """When a file was first added, from history — `--all`, because most episode
    mp3s have since left the tree. Empty when git has never seen any of them."""
    r = subprocess.run(["git", "log", "--all", "--diff-filter=A", "--format=%cI", "--", *paths],
                       cwd=BASE, capture_output=True, text=True, encoding="utf-8")
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def from_episodes(report):
    """Every `seen_in` mission on a row is a Teach Beat the episode lane gave.
    Dated from git (the registry dates 15 of 76), so `taught_on` is real."""
    lex = load_json(LEXICON_PATH) or {}
    dates, out, undated = {}, [], set()
    for word, rec in lex.items():
        for n in rec.get("seen_in") or []:
            if n not in dates:
                dates[n] = git_date(f"published_audio/tier2_mission{n}.mp3",
                                    f"content/scripts/tier2_mission{n}.md",
                                    f"content/scripts/tier2_mission{n}_breakdown.md",
                                    f"content/scripts/tier2_mission{n}_remix.md",
                                    f"content/lessons/tier2_mission{n}_brief.md")
            if not dates[n]:
                undated.add(n)
                continue
            out.append(event(dates[n], word, "episode", "taught", source=f"episode:M{n}",
                             note="new_words_landed payload — dated from git"))
    report.append(f"episodes  {len(out):>4} teach events across {len(dates)} missions"
                  + (f" ({len(undated)} missions git cannot date: {sorted(undated)[:6]})" if undated else ""))
    return out


def cutover(events, report) -> list:
    """Carry every live rung the log cannot show, as `ledger` events. See the
    module docstring. Returns the carries; the caller appends and rebuilds."""
    lex = load_json(LEXICON_PATH) or {}
    view = lexicon_view.derive(events)
    carries, seeded_dropped = [], 0

    def stamp(day):
        return f"{day}T12:00:00Z" if day else f"{CUTOVER}T12:00:00Z"

    for word, rec in lex.items():
        row = view.get(word) or {"recognition": "struggled", "production": "none",
                                 "channels": set(), "last_surfaced": None}
        note = "carried from the mutated ledger at the cutover; the observing event was never logged"
        gap = RECOGNITION_RANK.get(rec.get("recognition"), 0) - RECOGNITION_RANK[row["recognition"]]
        if gap > 0 and "seed" in row["channels"]:
            seeded_dropped += 1                      # the claim stops voting — no carry
        for i in range(max(gap, 0) if "seed" not in row["channels"] else 0):
            carries.append(event(stamp(rec.get("heard_on") or rec.get("last_surfaced")), word,
                                 "ledger", "tested", axis="recognition", result="right",
                                 source=f"ledger:{CUTOVER}:{i}", note=note))
        live_p, log_p = rec.get("production", "none"), row["production"]
        if PRODUCTION_RANK.get(live_p, 0) > PRODUCTION_RANK[log_p]:
            carries.append(event(stamp(rec.get("last_surfaced")), word, "ledger", "tested",
                                 axis="production", result="right" if live_p == "cold" else "partial",
                                 source=f"ledger:{CUTOVER}", note=note))
        ls = rec.get("last_surfaced")
        if ls and (row["last_surfaced"] or "") < ls:
            carries.append(event(stamp(ls), word, "ledger", "exposed", source=f"ledger:{CUTOVER}",
                                 note=f"carried delivery stamp; exposures was {rec.get('exposures', 0)}"))
    report += ["", f"CUTOVER: {len(carries)} rungs and stamps carried as `ledger` events; "
                   f"{seeded_dropped} seeded rows keep only what the log shows"]
    return carries


def coverage(events, report):
    """THE QUESTION THIS WHOLE PHASE EXISTS TO ANSWER — and it is about the
    ledger, never about Andrew. How many rows have evidence, how many have only
    the day-one claim, and how many have nothing at all."""
    lex = load_json(LEXICON_PATH) or {}
    tested, claimed_only = set(), set()
    for e in events:
        if e["kind"] == "tested":
            tested.add(e["word"])
        elif e["channel"] == "seed":
            claimed_only.add(e["word"])
    claimed_only -= tested
    unknown = {e["word"] for e in events} - set(lex)
    silent = set(lex) - tested - claimed_only
    report += ["",
               f"LEXICON COVERAGE ({len(lex)} rows)",
               f"  tested at least once      {len(tested & set(lex)):>4}",
               f"  day-one claim only        {len(claimed_only & set(lex)):>4}",
               f"  no evidence of any kind   {len(silent):>4}",
               f"  events naming no row      {len(unknown):>4}"
               + (f"  e.g. {sorted(unknown)[:3]}" if unknown else "")]

    # THE BACKFILL'S OWN HONESTY CHECK, and it must stay even when it reads zero.
    # A row carrying `reps`, `heard_on` or a production level is asserting it was
    # tested. Where history cannot produce the event behind that assertion, the
    # evidence is gone — `apply_heard_words` moved rungs from 2026-08-31 without
    # ever writing the words down, which is now fixed forward at the judge seam
    # but cannot be recovered backwards. Reporting the number is the difference
    # between a known limit and a silent one.
    claims = {w for w, v in lex.items()
              if (v.get("reps", 0) or 0) > 0 or v.get("heard_on")
              or v.get("production", "none") not in ("none", None)}
    orphaned = claims - tested
    report += ["",
               f"UNCORROBORATED ({len(orphaned)} rows)",
               "  the row says it was tested; no log can produce the event.",
               "  mostly apply_heard_words catches, never written down — see docstring."]


def main():
    ap = argparse.ArgumentParser(description="Rebuild the observation log from history")
    ap.add_argument("--write", action="store_true",
                    help="actually append; without it nothing is written")
    ap.add_argument("--cutover", action="store_true",
                    help="carry every unshown live rung as a ledger event, rebuild the "
                         "lexicon from the log and drop the dead fields (implies --write)")
    args = ap.parse_args()

    report = []
    events = (from_seed(report) + from_knocks(report) + from_sessions(report)
              + from_episodes(report))
    existing = observations.load_json(observations.OBSERVATIONS_PATH) or []
    if args.cutover:
        events += cutover(existing + events, report)
    events.sort(key=lambda e: (e["at"], e["word"]))
    have = {e.get("id") for e in existing}
    fresh = [e for e in events if e["id"] not in have]

    print("\n".join(report))
    print(f"\nreconstructed {len(events)} events · {len(fresh)} new · "
          f"{len(events) - len(fresh)} already present (idempotent)")
    coverage_lines = []
    coverage(events, coverage_lines)
    print("\n".join(coverage_lines))

    if not (args.write or args.cutover):
        print("\nDRY RUN — nothing written. Re-run with --write.")
        return
    observations.save_json(observations.OBSERVATIONS_PATH, existing + fresh)
    print(f"\n✅ wrote {len(fresh)} events → {observations.OBSERVATIONS_PATH.name} "
          f"({len(existing) + len(fresh)} total)")
    if args.cutover:
        lex = load_json(LEXICON_PATH) or {}
        for rec in lex.values():
            rec.pop("deck", None)
            rec.pop("lemma", None)
        orphans = lexicon_view.rebuild(lex, existing + fresh)
        save_json(LEXICON_PATH, lex)
        print(f"✅ lexicon rebuilt from the log — {len(lex)} rows"
              + (f"; {len(orphans)} logged words have no row: {orphans[:8]}" if orphans else ""))


if __name__ == "__main__":
    main()
