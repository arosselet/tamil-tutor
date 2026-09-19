#!/usr/bin/env python3
"""THE MONTH — one arc of the household's life, and the unit between the day and
the year.

WHY THIS EXISTS (2026-09-17, Andrew, twice in one day): *"Our lessons are
starting to feel narrow and repetitive"* and *"it's repetitive, it's narrowly
checking things; the lessons are short and pointed at my failures."* Measured
before building: 102 items tested in 30 days, 76 of them exactly once. The item
set is a SCATTER, not a rotation — so the felt complaint was never about
vocabulary. Because nothing is ever FINISHED, the only structure left to
perceive is the ritual; and because the slip ledger is the only memory that
crosses days, the only visible continuity is his own recurring mistakes. That is
the whole of "pointed at my failures", and it is architecture rather than tone.

RESHAPED 2026-09-19 ONTO THE ARC. The first version cut a month FROM THE GAP
POOL — a deliberate set of N items, stored, with a win line over it. That kept
the deficit machine and gave it a calendar: the month was still a list of things
he was bad at, merely bounded. Now membership is DERIVED from what the arc
actually taught (the union of the NEW payload of the month's episodes), so the
month is a record of what the household did, and the vocabulary comes out of the
story instead of the story being wrapped around a gap list.

WHAT THAT RETIRED, and it is most of the old file: `cut()`, the stored `set`,
`won_at`, `size`, the stub-month scaling of both, and the stored per-member
axis. A set nobody chose cannot feel like a rotation nobody chose if nobody
chooses it — the episodes do.

MEMBERSHIP IS DERIVED AND SO IS COMPLETION. Both are folds, every call. A stored
counter drifts from reality and reads green while doing nothing — which is
exactly how the Trip Deck reported a winning sprint while 45 of 70 items were
never asked once. A fold cannot. Delete a sidecar and the member goes away; no
stored copy survives it.

THE WIN IS THE FINALE EAR TEST, NEVER THE COUNT. The standing steers Python's
picks and is visible on Andrew's own surfaces; it is not the win and no number
leaves Anna's mouth (`persona.md`). What wins a month is: he listens to the
arc's last episode WITHOUT the caption sheet and says what happened, and two
thirds of the key lines come back right. Comprehension is produced, never
self-reported — *"did you get it?"* never votes.

THIS IS NOT THE DECK RETURNING. No container file, no curriculum join, no
deadline, no burn rate. `DECISIONS.md` -> "Retire the Trip Deck" stands: what it
retired was a bounded set keyed to a DATE THAT EXPIRED. A calendar month expires
on purpose, every month, and re-cuts itself.

WHAT THIS FILE DOES NOT OWN: the ORDER candidates arrive in (`suggest_targets`,
which sits ABOVE this file), which episodes exist, or what happens in the
household (`content/household.md`). Sidecars and episodes are PASSED IN rather
than read here — that is the layer boundary, not a convenience.
"""
from datetime import date

from state_io import load_json, local_today, LEARNER_PATH


# The record lives in learner.json under this key, Python-owned like every other
# field there. One month is live at a time — a finished month is overwritten and
# git holds it, exactly as the campaign heading has always worked (DECISIONS →
# "One campaign heading, always").
KEY = "month"

# The ear rung that closes a member. `solid` was the first choice and was wrong
# on the arithmetic: 4 of 366 rows are solid today, so an ear member would
# essentially never close and every arc would read as a loss. This matches
# `suggest_targets.RECOGNIZED`, which is the rung the rest of the system already
# treats as "he has this".
EAR_RUNG = {"comfortable", "solid"}

# Two thirds of the finale's key lines, with a partial worth half. A starting
# number and stated as one: re-base it after two finales from what the verdicts
# actually look like, never defend it.
WIN_SHARE = 2 / 3


def load(learner: dict | None = None) -> dict:
    """The live month, or {} when none has been opened (day zero, a fresh clone)."""
    if learner is None:
        learner = load_json(LEARNER_PATH) or {}
    rec = learner.get(KEY)
    return rec if isinstance(rec, dict) else {}


def closes_on(today: date) -> str:
    """The last day of Andrew's calendar month. Calendar, not rolling — his call
    2026-09-17: a reset that lands on a date he already recognises."""
    nxt = date(today.year + (today.month == 12), (today.month % 12) + 1, 1)
    return (nxt.fromordinal(nxt.toordinal() - 1)).isoformat()


def is_over(rec: dict, today: date | None = None) -> bool:
    """Past its close date. A month with no close never expires, which would be
    the conveyor again — so a record missing `closes` reads as OVER, not as
    open. An unbounded month is the bug this file exists to remove."""
    if not rec:
        return False
    return (rec.get("closes") or "") < (today or local_today()).isoformat()


def opened_record(name: str, today: date | None = None) -> dict:
    """A new arc. Three fields, and not one of them is a target.

    `cut()` lived here until 2026-09-19 and took a candidate list, a size and a
    win line. Nothing is chosen now: the arc's name says what is happening in the
    household, the episodes teach what they teach, and membership is whatever
    they taught."""
    today = today or local_today()
    return {"name": name, "opened": today.isoformat(), "closes": closes_on(today)}


def arc_missions(rec: dict, episodes: dict) -> list[int]:
    """The mission numbers produced inside this month's dates, oldest first.

    `episodes.json` is the registry and `produced` is its date. An episode with
    no date cannot be placed and is LEFT OUT rather than assumed recent — a
    denominator that quietly grows by guessing is the deck's dishonest meter in
    a new coat."""
    lo, hi = rec.get("opened") or "", rec.get("closes") or ""
    return sorted(int(n) for n, e in (episodes or {}).items()
                  if str(n).isdigit() and isinstance(e, dict)
                  and lo <= (e.get("produced") or "") <= hi)


def members(rec: dict, episodes: dict, sidecars: dict) -> list[str]:
    """THE MONTH'S VOCABULARY: the union of the NEW payload of its arc episodes.

    Read off the sidecars' `new_words_landed`, which is the Producer's record of
    what an episode actually taught — not what a plan intended to teach. Derived
    every call: delete a sidecar and the member is gone, which is the property
    that makes this impossible to inflate.

    `sidecars` is mission number -> parsed sidecar, passed in by the caller. A
    mission with no sidecar contributes nothing and is reported by `standing`,
    never silently skipped."""
    out = []
    for n in arc_missions(rec, episodes):
        for w in (sidecars.get(n) or {}).get("new_words_landed") or {}:
            if w not in out:
                out.append(w)
    return out


def axis_of(row: dict) -> str:
    """Which axis this member rides: the ear for a `catch` row, the mouth
    otherwise.

    THE STORED AXIS RETIRED WITH THE CUT (2026-09-19). It used to be decided at
    entry and written down, because `target_rung` also read "already cold at the
    mouth -> the ear is what's left" — true at cut time and self-defeating
    afterwards, since a mouth member going cold would re-read as an ear member
    and could never close. That clause existed to stop a month cut from the gap
    pool opening already-won. Membership is now what the arc TAUGHT, so a member
    is new by construction and cannot be pre-won; the clause is unnecessary, and
    without it the axis is a fact about the row that no longer needs storing."""
    return "ear" if row.get("direction") == "catch" else "mouth"


def is_closed(row: dict) -> bool:
    """Has this member reached the rung of the axis it rides?

    Both fields are derived by `lexicon_view`, so this asks the log and never a
    claim (DECISIONS -> "'Done' is observed, never declared")."""
    if axis_of(row) == "ear":
        return row.get("recognition") in EAR_RUNG
    return row.get("production") == "cold"


def standing(rec: dict, lexicon: dict, episodes: dict, sidecars: dict) -> dict:
    """The month's live state, recomputed every call. Never persisted.

    `missing` is loud on purpose (the absence rule, /extend Gate 7.2): a member
    that has left the lexicon is a broken month, not a quietly smaller one, and a
    silently shrinking denominator is that same failure wearing a new coat.
    `unrecorded` is the same rule one level up — an episode that rendered inside
    the month and left no sidecar taught words that no meter can see."""
    words = members(rec, episodes, sidecars)
    done, missing, still_open = [], [], []
    for w in words:
        row = lexicon.get(w)
        if not isinstance(row, dict):
            missing.append(w)
        elif is_closed(row):
            done.append(w)
        else:
            still_open.append(w)
    return {
        "total": len(words),
        "closed": len(done), "closed_words": done,
        "open_words": still_open, "missing": sorted(missing),
        "ear": sum(1 for w in words if axis_of(lexicon.get(w) or {}) == "ear"),
        "missions": arc_missions(rec, episodes),
        "unrecorded": [n for n in arc_missions(rec, episodes) if not sidecars.get(n)],
    }


def key_line_events(rec: dict, events: list) -> list[dict]:
    """The finale test's recorded lines, for THIS month's finale.

    Sourced on the finale's mission number so a re-cut month cannot inherit the
    previous arc's verdict, and so a second attempt is visibly a second attempt
    rather than a silent overwrite."""
    src = f"finale:M{rec.get('finale')}"
    return [e for e in (events or [])
            if isinstance(e, dict) and e.get("source") == src
            and e.get("channel") == "check"]


def verdict(rec: dict, events: list) -> dict:
    """THE WIN, as a fold over recorded key lines. There is no stored `won`.

    He listens to the finale with no caption sheet and says what each key line
    meant; Anna records what he PRODUCED against what the line says. *"Did you
    get it?"* never votes — comprehension is measured, never self-reported
    (DECISIONS). A partial counts half, because half-catching a line is a real
    and common state and scoring it as a miss makes the meter lie downward."""
    seen = key_line_events(rec, events)
    if not seen:
        return {"tested": 0, "score": 0.0, "of": 0, "won": False, "run": False}
    score = sum({"right": 1.0, "partial": 0.5}.get(e.get("result"), 0.0) for e in seen)
    return {"tested": len(seen), "score": score, "of": len(seen),
            "won": score >= WIN_SHARE * len(seen), "run": True}


def carry(rec: dict, lexicon: dict, episodes: dict, sidecars: dict) -> list[str]:
    """What an expiring month hands the next arc: its still-open members, offered
    as CANDIDATES and nothing more.

    THERE IS NO DEBT FIELD, and that is load-bearing (the anti-ratchet law).
    Unmet items are re-cut — rolled when still central, dropped when the month
    said something wrong — and nothing anywhere records that they went unmet.
    The reset IS the forgiveness mechanism (Andrew, on the May 2026 fade and the
    ADHD cost of a ratchet); a field counting what he missed would quietly
    become a streak, which is the one thing this whole object must never be."""
    return standing(rec, lexicon, episodes, sidecars)["open_words"]
