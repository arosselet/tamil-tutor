#!/usr/bin/env python3
"""THE THREADS — what Anna can tug on, read off the books (2026-10-08, Andrew with Rio).

Anna is a handful of ongoing threads, not lessons: words he is nursing from "I
recognise it" to "it comes out without thinking", the questions he asked, the
household story, the slips he has retired. A push tugs ONE live thread or stays
silent; a session names a word the moment it becomes his. Either claim — "this
one's almost yours", "that one just became yours" — is only honest if the books
say so, so this file computes both from the observation log and never from a
model's impression. Nothing here writes; there is no new state.

WHY (the knock log, 2026-08-15 -> 10-06): one-line asks on something he was
already working on came back most of the time — volleys 4/5, revives 2/2,
eavesdrops 7/14 — while 32 standalone gifts (lore, tidbits, patterns, fun facts)
drew 6 replies or taps between them. The outreach mandate was rewritten four
times in two weeks swinging between asks and gifts; this is the thing both
halves were reaching for. A gift is candy: it is handed out when the threads
are not pulling, and the fix for that is the threads.

REPLACES `morning_knock.progress_block` and `last_fired_on`: "patterns he fires
unaided / one step away" read the static rungs plus a date pulled from two logs;
the observation log already holds every one of those events with its channel.

    python scripts/threads.py          # the live threads, with each word's story
    python scripts/threads.py wall     # the trophy wall: what became his, slips retired
"""

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lexicon_view import derive
from observations import OBSERVATIONS_PATH, WATCHED
from slips import canon_tag, slip_closes
from state_io import LEXICON_PATH, SLIP_LOG_PATH, load_json, local_date

# A thread is LIVE while a watched test touched it this recently. Three weeks is
# the gap a busy stretch can open without the thread going cold; past it, "almost
# yours" is month-old evidence and reads as pressure, not pull (the 09-29
# freshness rail, which this replaces, said the same at 7 days of production only).
LIVE_DAYS = 21
WON_DAYS = 7    # "just became his" — recent enough to name, old enough to have happened

# English question words only: "Evlo aagum?" is an answer, not a question.
QUESTION_RE = re.compile(r"\b(what|why|how|which|break (it )?down|root|mean|difference)\b", re.I)


def is_his(row: dict, lexrow: dict) -> bool:
    """Owned: it comes out of his mouth unaided — or, for an ear-only row he is
    never asked to say, his ear has it solid."""
    if (lexrow or {}).get("direction") == "catch":
        return row.get("recognition") == "solid"
    return row.get("production") == "cold"


def _day(e) -> str:
    d = local_date(e.get("at") or "")
    return d.isoformat() if d else "?"


def story(word: str, events: list) -> dict:
    """Where he met it, where he last stumbled, where it last landed."""
    mine = sorted((e for e in events if e.get("word") == word and e.get("channel") in WATCHED),
                  key=lambda e: e.get("at") or "")
    tests = [e for e in mine if e.get("kind") == "tested"]
    stumbles = [e for e in tests if e.get("result") in ("partial", "wrong")]
    lands = [e for e in tests if e.get("result") == "right"]
    tag = lambda e: f"{_day(e)} ({e.get('channel')})" if e else None
    # `ledger` rows are the 09-10 cutover's carry-overs, dated to the cutover —
    # not when he met the word. Prefer any real first contact.
    first = next((e for e in mine if e.get("channel") != "ledger"), mine[0] if mine else None)
    return {"met": tag(first), "tests": len(tests),
            "stumble": tag(stumbles[-1] if stumbles else None),
            "landed": tag(lands[-1] if lands else None),
            "last_test": tests[-1].get("at") if tests else None}


def almost_yours(lex: dict, events: list, now: datetime, n: int = 6) -> list[dict]:
    """Words not yet his that a watched test touched within LIVE_DAYS and that
    have landed at least once — fired with a hint first, then stumbled-and-landed. Most recently touched first: the liveliest thread leads."""
    since = (now - timedelta(days=LIVE_DAYS)).isoformat()
    view, out = derive(events), []
    for word, row in view.items():
        lr = lex.get(word)
        if lr is None or is_his(row, lr):
            continue
        s = story(word, events)
        if not s["landed"] or (s["last_test"] or "") < since:
            continue
        # NURSED, not merely untested: he fired it with a hint, or he stumbled on
        # it and it has landed since. A row the sweep confirmed but nothing ever
        # asked him to say (சரி) is not a thread — tugging it would be a retest.
        hinted = row.get("production") == "hinted"
        if hinted or (s["stumble"] and s["landed"] > s["stumble"]):
            out.append({"word": word, "gloss": lr.get("gloss") or "", **s,
                        "hinted": hinted})
    out.sort(key=lambda t: (not t["hinted"], -_ts(t["last_test"])))
    return out[:n]


def _ts(at) -> float:
    try:
        return datetime.fromisoformat((at or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def became_yours(lex: dict, events: list, since: datetime) -> list[dict]:
    """Words that crossed into his since `since` — the fold before vs. the fold
    now, so the claim is exactly what the log supports. Dated to the first
    right answer after the cut."""
    cut = since.isoformat()
    before = derive([e for e in events if (e.get("at") or "") < cut])
    out = []
    for word, row in derive(events).items():
        lr = lex.get(word)
        if lr is None or not is_his(row, lr) or is_his(before.get(word, {}), lr):
            continue
        won = next((e for e in sorted(events, key=lambda e: e.get("at") or "")
                    if e.get("word") == word and (e.get("at") or "") >= cut
                    and e.get("kind") == "tested" and e.get("result") == "right"), None)
        out.append({"word": word, "gloss": lr.get("gloss") or "", "on": _day(won) if won else "?"})
    return sorted(out, key=lambda t: t["on"])


def retired_slips() -> list[dict]:
    """Slips he has since fired right, unaided — and has not slipped on since.
    A later slip voids the close (slips.slip_closes keeps closes dated for that)."""
    log = load_json(SLIP_LOG_PATH) or []
    last_slip, what = {}, {}
    for r in log:
        t = canon_tag(r.get("tag") or "")
        last_slip[t] = max(last_slip.get(t, ""), r.get("date") or "")
        what[t] = r.get("note") or what.get(t, "")
    return sorted(({"tag": t, "on": d, "was": what.get(t, "")}
                   for t, d in slip_closes().items() if last_slip.get(t, "") <= d),
                  key=lambda s: s["on"])


def questions(klog: list, now: datetime, days: int = 14) -> list[dict]:
    """What he asked from his phone lately — his own threads, answered once."""
    since = (now - timedelta(days=days)).isoformat()
    out = []
    for e in klog:
        if (e.get("timestamp") or "") < since:
            continue
        for x in e.get("exchanges") or ([{"reply": e["reply"]}] if e.get("reply") else []):
            r = (x.get("reply") or "").strip()
            if r and QUESTION_RE.search(r):
                out.append({"id": f"q:{(x.get('at') or e['timestamp'])[:10]}", "text": r[:140]})
    answered = {k.get("thread") for k in klog}
    return [q for q in out if q["id"] not in answered][-4:]


def live(klog: list, now: datetime, *, arc: bool, lex=None, events=None) -> dict:
    """id -> one-line label, for every thread a push may tug right now."""
    lex = load_json(LEXICON_PATH) or {} if lex is None else lex
    events = load_json(OBSERVATIONS_PATH) or [] if events is None else events
    out = {}
    for t in almost_yours(lex, events, now):
        bits = [f"met {t['met']}", f"stumbled {t['stumble']}" if t["stumble"] else "",
                f"landed {t['landed']}", "fired with a hint" if t["hinted"] else "stumbled, then landed"]
        out[f"word:{t['word']}"] = f"{t['gloss'][:60]} — " + "; ".join(b for b in bits if b)
    for q in questions(klog, now):
        out[q["id"]] = f'he asked: "{q["text"]}"'
    if arc:
        out["arc"] = "the household story (CAMPAIGN above) — an overheard tape hangs here"
    return out


def block(klog: list, now: datetime, *, arc: bool) -> str:
    """The digest section the outreach decider reads in place of PROGRESS."""
    lex = load_json(LEXICON_PATH) or {}
    events = load_json(OBSERVATIONS_PATH) or []
    threads = live(klog, now, arc=arc, lex=lex, events=events)
    won = became_yours(lex, events, now - timedelta(days=WON_DAYS))
    lines = ["THREADS (a push tugs ONE of these by its id, or stays silent):"]
    lines += [f"    [{k}] {v}" for k, v in threads.items()] or ["    (none live — silence)"]
    if won:
        lines.append("  Just became his (name it if it fits — never test it again to prove it):")
        lines += [f"    {t['word']} — {t['gloss'][:60]} (on {t['on']})" for t in won]
    return "\n".join(lines)


def main():
    now = datetime.now(timezone.utc)
    lex = load_json(LEXICON_PATH) or {}
    events = load_json(OBSERVATIONS_PATH) or []
    if sys.argv[1:] == ["wall"]:
        print("THE WALL — what became his (all time):")
        for t in became_yours(lex, events, datetime(2000, 1, 1, tzinfo=timezone.utc)):
            print(f"  {t['on']}  {t['word']} — {t['gloss']}")
        print("\nSlips retired (he fires them right now):")
        for s in retired_slips():
            print(f"  {s['on']}  {s['tag']} — was: {s['was']}")
        return
    print("ALMOST HIS (liveliest first):")
    for t in almost_yours(lex, events, now, n=12):
        print(f"  {t['word']} — {t['gloss']}\n      met {t['met']} · stumbled {t['stumble'] or '—'}"
              f" · landed {t['landed']} · {'fired with a hint' if t['hinted'] else 'stumbled, then landed'}")
    won = became_yours(lex, events, now - timedelta(days=WON_DAYS))
    print(f"\nBECAME HIS in the last {WON_DAYS} days:")
    for t in won or [{"word": "(none)", "gloss": "", "on": ""}]:
        print(f"  {t['on']}  {t['word']} — {t['gloss']}")


if __name__ == "__main__":
    main()
