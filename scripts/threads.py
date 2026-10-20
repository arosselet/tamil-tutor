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
    python scripts/threads.py map      # THE MAP: where we are this week, said to him
"""

import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import ladder
from lexicon_view import derive
from observations import OBSERVATIONS_PATH, WATCHED
from slips import canon_tag, slip_closes, slip_patterns
from state_io import (LEARNER_PATH, LEXICON_PATH, SESSION_LOG_PATH, SLIP_LOG_PATH,
                      load_json, local_date, soak_pending)

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


def rooms(lex: dict, events: list) -> dict[str, tuple[int, int]]:
    """Per ladder room: (rows his, rows) among the rows whose register LEADS
    there (2026-10-09, Andrew). Printed beside the stated lean on Andrew's
    surfaces so whoever moves it sees the books first — derived every time,
    never stored, never said to him.

    WHAT IT DOES NOT MEASURE: a `register` names the kind of phrase (a frame, a
    social nicety), not who he would say it to, and only ~1 row in 5 carries
    one. That is why it informs the lean and does not move it."""
    view, keys = derive(events), {room: [w for w, r in lex.items() if r.get("register") in ladder.LEADS[room]]
                                  for room in ladder.ORDER}
    return {room: (sum(is_his(view.get(w, {}), lex[w]) for w in ks), len(ks)) for room, ks in keys.items()}


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
    learner = load_json(LEARNER_PATH) or {}
    if map_push_due(learner, klog, local_date(now.isoformat()) or now.date()):
        out["map"] = "where we are this week (THE MAP below) — the week's headline, a give"
    return out


def block(klog: list, now: datetime, *, arc: bool, phone: bool = True) -> str:
    """The digest section the outreach decider reads in place of PROGRESS.
    `phone=False` is the session's read: the map is said whole there, so the
    push's [map] thread is left out."""
    lex = load_json(LEXICON_PATH) or {}
    events = load_json(OBSERVATIONS_PATH) or []
    threads = live(klog, now, arc=arc, lex=lex, events=events)
    if not phone:
        threads.pop("map", None)
    won = became_yours(lex, events, now - timedelta(days=WON_DAYS))
    lines = ["THREADS (a push tugs ONE of these by its id, or stays silent):"]
    lines += [f"    [{k}] {v}" for k, v in threads.items()] or ["    (none live — silence)"]
    if "map" in threads:
        lines += ["  THE MAP (for a [map] push — headline only; the full map waits for a session):"]
        lines += ["    " + ln for ln in map_lines(now, lex=lex, events=events)]
    if won:
        lines.append("  Just became his (name it if it fits — never test it again to prove it):")
        lines += [f"    {t['word']} — {t['gloss'][:60]} (on {t['on']})" for t in won]
    return "\n".join(lines)


# ── Did he come back? (the return measure, 2026-10-08) ─────────────────────
#
# Rio: "stop measuring push reply rate and start measuring thread return rate —
# the question isn't 'did he answer the push' but 'did he come back tomorrow'."
# Before this, "showing up" meant one thing: a `sync_state update` row in
# session_log.json. That file stopped at 09-25 while he sat a lesson on 10-03 and
# a sweep on 10-04, so the outreach memory read two weeks of contact as absence.
#
# CONTACT IS A FACT ABOUT ANDREW, never about the machine: a reply or a tap on a
# push, a press of play (`attended`), an answer he gave (a watched `tested`), or a
# closed session. A delivery, a render or a taught row is the system's act, not
# his. Derived on every read — no new store. A session that teaches and logs
# nothing is still invisible; that is the light session start's job to close.
#
# THESE NUMBERS STEER ANNA AND ARE NEVER SAID TO HIM. Counted at him, "came back"
# is a streak.

BACK_DAYS = 2      # "did he come back tomorrow" — a tug at 21:00 earns the next day
TOUCH_DAYS = 7     # the tugged word turned up again in anything he answered or played


def contact_days(klog: list, events: list, slog: list | None = None) -> dict[str, set]:
    """local day -> the kinds of contact he made that day."""
    days: dict[str, set] = {}
    def add(at, what):
        d = local_date(at or "")
        if d:
            days.setdefault(d.isoformat(), set()).add(what)
    for e in events:
        if e.get("channel") in WATCHED and e.get("kind") in ("attended", "tested"):
            add(e.get("at"), "played" if e["kind"] == "attended" else f"answered ({e['channel']})")
    for k in klog:
        add(k.get("reply_at"), "replied")
        add(k.get("response_at"), "tapped")
        for x in k.get("exchanges") or []:
            add(x.get("at"), "replied")
    for s in slog if slog is not None else (load_json(SESSION_LOG_PATH) or []):
        if s.get("date"):
            days.setdefault(s["date"], set()).add("session")
    return days


def last_contact(days: dict) -> str | None:
    return max(days) if days else None


def returns(klog: list, events: list, now: datetime, days_back: int = 14,
            contact: dict | None = None) -> dict:
    """Over the tugs of the last `days_back` days that named a thread: how many
    he answered, how many were followed by contact within BACK_DAYS, and — for
    word threads — how many saw that word again in his own activity within
    TOUCH_DAYS. Tugs too young to have had their window are left out, never
    counted as misses."""
    contact = contact_days(klog, events) if contact is None else contact
    since = (now - timedelta(days=days_back)).isoformat()
    out = {"tugs": 0, "answered": 0, "came_back": 0, "word_tugs": 0, "touched": 0}
    for k in klog:
        at, thread = k.get("timestamp") or "", k.get("thread") or ""
        if not (k.get("acted") and thread and at >= since):
            continue
        sent = datetime.fromisoformat(at)
        if now - sent < timedelta(days=BACK_DAYS):
            continue
        answered = bool(k.get("reply") or k.get("response"))
        day = local_date(at)
        later = {(day + timedelta(days=i)).isoformat() for i in range(1, BACK_DAYS + 1)}
        out["tugs"] += 1
        out["answered"] += answered
        out["came_back"] += answered or any(contact.get(d) for d in later)
        if thread.startswith("word:") and now - sent >= timedelta(days=TOUCH_DAYS):
            word, t0 = thread[5:], sent.timestamp()
            out["word_tugs"] += 1
            out["touched"] += any(e.get("word") == word and e.get("channel") in WATCHED
                                  and e.get("kind") in ("attended", "tested")
                                  and t0 < _ts(e.get("at")) <= t0 + TOUCH_DAYS * 86400
                                  for e in events)
    return out


def return_line(klog: list, events: list, now: datetime, contact: dict) -> str:
    """The outreach memory's line. Only thread-tagged tugs count, so it starts
    empty and says so rather than reading as zero."""
    r = returns(klog, events, now, contact=contact)
    if not r["tugs"]:
        return "\n  Return measure: no thread-tagged tug old enough to judge yet."
    word = (f" · the tugged word turned up again in his own activity within {TOUCH_DAYS}d: "
            f"{r['touched']} of {r['word_tugs']}" if r["word_tugs"] else "")
    return (f"\n  Tugs that named a thread (14d, old enough to judge): {r['tugs']} · answered "
            f"{r['answered']} · he came back within {BACK_DAYS}d after {r['came_back']}{word}. "
            "Steer by it; never say it to him.")


# ── THE MAP — where we are, said to him (2026-10-19, Andrew) ───────────────
#
# Andrew: "I don't know what week I'm on. I don't know what words you're trying
# to teach me, what words you think I struggled with." Every line below already
# lived in the books — the wall, the almost-his list, the soak order, the slip
# ledger — behind a pull-only offer and a laptop CLI he never opens: "all my
# interactions are via the tutor." So the map is SAID to him, by Anna in a
# session or by a push, a few times a week and whenever the week turns.
#
# SHOW THE MAP, NEVER THE DEBT (constitution → Ground Covered). What guards it:
# every line is absence-blind (a missed day changes nothing on it), small and
# winnable (this week's few words, never the 396 tracked), and forward-looking.
# The only number is an accumulator that cannot fall — "became yours this
# month". The 07-17 big-denominator recital ("need 2.4/day, trailing 0.7") and
# the 09-05 failure tally stay retired; this replaces the 08-25 blanket ban
# that took the small, winnable picture down with them.

MAP_EVERY = 3      # days — "a few times a week"; a new calendar week is due at once
IN_PLAY_CHANNELS = {"session", "text", "audio"}   # what Anna explicitly TAUGHT him


def week_label(d: date) -> str:
    """Calendar, like the month (`month.closes_on`): a week he already recognises."""
    return f"{d:%B}, week {(d.day - 1) // 7 + 1}"


def in_play(lex: dict, events: list, now: datetime, learner: dict) -> list[str]:
    """The words this week is aiming at him: the standing soak order's payload,
    then what Anna taught him in the last 7 days — minus anything already his.
    Episode/rotation exposure is left out: a tape airs ~60 words a week, and a
    list that long is the 396 again."""
    view, cut = derive(events), (now - timedelta(days=WON_DAYS)).isoformat()
    words = list((learner.get("soak_order") or {}).get("payload") or [])
    words += [e["word"] for e in sorted(events, key=lambda e: e.get("at") or "")
              if e.get("kind") == "taught" and e.get("channel") in IN_PLAY_CHANNELS
              and (e.get("at") or "") >= cut and e.get("word")]
    return [w for w in dict.fromkeys(words) if not is_his(view.get(w, {}), lex.get(w) or {})]


def untaught(words: list[str], events: list) -> list[str]:
    """The words no teaching event has reached — `taught_on` in the fold. An
    episode airing leaves a word pending, not taught. Such a word is shown with
    its meaning first; it is never quizzed or used as material he is assumed to
    have (2026-10-20, Andrew: "tested on something that was never explained")."""
    view = derive(events)
    return [w for w in words if not view.get(w, {}).get("taught_on")]


def map_lines(now: datetime, *, learner=None, lex=None, events=None) -> list[str]:
    learner = load_json(LEARNER_PATH) or {} if learner is None else learner
    lex = load_json(LEXICON_PATH) or {} if lex is None else lex
    events = load_json(OBSERVATIONS_PATH) or [] if events is None else events
    today = local_date(now.isoformat()) or now.date()
    gloss = lambda w: w + (f" — {g}" if (g := (lex.get(w) or {}).get("gloss")) else "")
    out = [f"THE MAP — {week_label(today)}"]
    arc = learner.get("month") or {}
    if arc.get("name") and (arc.get("closes") or "") >= today.isoformat():
        out.append(f"  The month: {arc['name']} (runs to {arc['closes']})")
    lean = (learner.get("ladder") or {}).get("lean")
    if lean in ladder.ORDER:
        out.append(f"  Room we're working: {ladder.ROOMS[lean]}")
    order = learner.get("soak_order") or {}
    if order.get("scene_seed"):
        out.append(f"  {'Coming up' if soak_pending() else 'On'} tape this week: {order['scene_seed']}")
    play = in_play(lex, events, now, learner)
    out.append("  In play this week:" + ("" if play else " (nothing new — a breather)"))
    new = set(untaught(play, events))
    out += [f"    {gloss(w)}" + (" (new — taught first)" if w in new else "") for w in play[:8]]
    near = almost_yours(lex, events, now, n=5)
    if near:
        out.append("  Almost yours:")
        out += [f"    {gloss(t['word'])}" for t in near]
    month_start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    won = became_yours(lex, events, month_start)
    week = [t for t in won if t["on"] >= (today - timedelta(days=WON_DAYS)).isoformat()]
    out.append(f"  Became yours this month: {len(won)}"
               + (" — this week: " + ", ".join(t["word"] for t in week) if week else ""))
    live = [p for p in slip_patterns(today=today) if p.get("live") and p.get("pattern")]
    if live:
        out.append("  What we're working on (from your own slips — the fix, not the miss):")
        for p in live[:4]:
            ex = p["examples"][-1] if p.get("examples") else None
            out.append(f"    {p['tag']}" + (f" — wanted “{ex[2]}”" if ex and ex[2] else ""))
    return out


def map_due(learner: dict, today: date) -> str:
    """Why Anna owes him the map in a session today, or "" — derived from the one
    stored date (`sync_state.py map --shown`), never a flag."""
    try:
        then = date.fromisoformat(learner.get("map_shown") or "")
    except ValueError:
        return "never shown"
    if then.isocalendar()[:2] != today.isocalendar()[:2]:
        return "a new week"
    return f"{MAP_EVERY}+ days since" if (today - then).days >= MAP_EVERY else ""


def map_push_due(learner: dict, klog: list, today: date) -> bool:
    """The phone half: one push a week may carry the map's headline, for the
    weeks he lives on the phone. Due while this week has neither a session map
    nor a push that tugged `map`."""
    week = today.isocalendar()[:2]
    def this_week(day: str) -> bool:
        try:
            return date.fromisoformat(day[:10]).isocalendar()[:2] == week
        except ValueError:
            return False
    return not (this_week(learner.get("map_shown") or "") or any(
        k.get("acted") and k.get("thread") == "map" and this_week(k.get("timestamp") or "")
        for k in klog))


def main():
    now = datetime.now(timezone.utc)
    lex = load_json(LEXICON_PATH) or {}
    events = load_json(OBSERVATIONS_PATH) or []
    if sys.argv[1:] == ["map"]:
        print("\n".join(map_lines(now)))
        return
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
