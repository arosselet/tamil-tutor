#!/usr/bin/env python3
"""THE MONTH WITH EDGES — the unit of progress between the day and the year.

WHY THIS EXISTS (2026-09-17, Andrew, twice in one day): *"Our lessons are
starting to feel narrow and repetitive"* and *"it's repetitive, it's narrowly
checking things; the lessons are short and pointed at my failures."* Measured
before building: 102 items tested in 30 days, 76 of them exactly once. The item
set is a SCATTER, not a rotation — so the felt complaint is not about vocabulary.

What IS as narrow as he says is `suggest_targets.FOCUS_SIZE` — twelve seats that
refill the instant a word graduates. A conveyor cannot be started, finished, won,
exceeded or reset; it can only turn. The Trip Deck's boundary died with its
container (2026-08-26) and the campaign block never replaced it: it reaches one
prose consumer (`morning_knock.campaign_block`) and steers no selection at all.

So: because nothing is ever FINISHED, the only structure left to perceive is the
ritual — and because the slip ledger is the only memory that crosses days, the
only visible continuity is his own recurring mistakes. That is the whole of
"pointed at my failures", and it is architecture rather than tone.

THIS IS NOT THE DECK RETURNING. No container file, no curriculum join, no
deadline, no burn rate. `DECISIONS.md` → "Retire the Trip Deck" stands: what it
retired was a bounded set keyed to a DATE THAT EXPIRED. A calendar month expires
on purpose, every month, and re-cuts itself.

THE STANDING IS A FOLD, NEVER A STORED COUNTER. `closed()` reads the lexicon's
derived rungs, which are themselves the fold of the observation log
(`lexicon_view.derive`; DECISIONS → "The lexicon is a view over its log" and
"'Done' is observed, never declared"). A stored counter drifts from reality and
reads green while doing nothing — which is exactly how the deck reported a
winning sprint while 45 of 70 items were never asked once. A fold cannot.

MEMBERSHIP IS STORED; COMPLETION IS DERIVED. That split is the whole design.

WHAT THIS FILE DOES NOT OWN: the ORDER candidates arrive in. `cut()` takes an
already-ordered list and takes from the front. The tier law, the coverage term
and the ask cooldown stay in `suggest_targets`, which sits ABOVE this file — so
importing it here would be an upward edge (`s75`). Passing the order in is not a
convenience, it is the layer boundary.
"""
from datetime import date

from state_io import load_json, local_today, LEARNER_PATH


# The record lives in learner.json under this key, Python-owned like every other
# field there. One month is live at a time — a finished month is overwritten and
# git holds it, exactly as the campaign heading has always worked (DECISIONS →
# "One campaign heading, always").
KEY = "month"


def load(learner: dict | None = None) -> dict:
    """The live month, or {} when none has been cut (day zero, a fresh clone)."""
    if learner is None:
        learner = load_json(LEARNER_PATH) or {}
    rec = learner.get(KEY)
    return rec if isinstance(rec, dict) else {}


def target_rung(row: dict) -> str:
    """Which axis closes THIS member: WHICHEVER ONE IS STILL OPEN.

    - `direction: catch` — ear, always. An ear-only row is never forced to fire
      (`suggest_targets.ear_targets`; profile.md's "the win is comprehension").
    - already cold at the mouth — ear. The mouth is DONE; the only work left on
      that row is the ear, so counting it closed would be counting a finished
      job twice.
    - everything else — mouth.

    THE SECOND CLAUSE IS NOT A DETAIL. Without it the machines close a month for
    free: 21 of 21 fire cold and 3 of 26 are heard, so a month cut from patterns
    would open already won while the axis the goal actually rides sat untouched.
    That is the whole error this system keeps making one level up — reading the
    engine's odometer as the map (DECISIONS -> "The headline is the ear, not the
    mouth"), and a set that can be won without moving is the deck's dishonest
    meter rebuilt in a new file."""
    if row.get("direction") == "catch" or row.get("production") == "cold":
        return "ear"
    return "mouth"


def is_closed(row: dict, axis: str) -> bool:
    """Has this member reached the rung of THE AXIS IT WAS CUT FOR?

    `axis` is passed in, never recomputed — and that is the fix for a bug this
    file shipped with for about an hour. `target_rung` reads "already cold at the
    mouth -> the ear is what's left", which is right at CUT time and self-
    defeating afterwards: a mouth member going cold would re-read as an ear
    member and could never close at all. A member's axis is decided once, when
    someone cuts it, and then it is a fact about the month rather than a function
    of the row.

    Both fields read here are derived by `lexicon_view`, so this asks the log and
    never a claim (DECISIONS -> "'Done' is observed, never declared")."""
    if axis == "ear":
        return row.get("recognition") == "solid"
    return row.get("production") == "cold"


def standing(rec: dict, lexicon: dict) -> dict:
    """The month's live state, recomputed every call. Never persisted.

    MEMBERSHIP IS STORED, COMPLETION IS DERIVED. Each member carries the word and
    the axis it was cut for; whether it is DONE is asked of the lexicon's derived
    rungs every time this runs. A stored counter drifts and reads green while
    doing nothing — which is exactly how the deck reported a winning sprint with
    45 of 70 items never asked. A fold cannot.

    `missing` is loud on purpose (the absence rule, /extend Gate 7.2): a member
    that has left the lexicon is a broken month, not a quietly smaller one, and a
    silently shrinking denominator is that same failure wearing a new coat. It
    counts against the total and can never close."""
    members = [m for m in (rec.get("set") or []) if isinstance(m, dict)]
    done, missing, still_open = [], [], []
    for m in members:
        row = lexicon.get(m.get("word"))
        if not isinstance(row, dict):
            missing.append(m.get("word"))
        elif is_closed(row, m.get("axis", "mouth")):
            done.append(m.get("word"))
        else:
            still_open.append(m.get("word"))
    won_at = int(rec.get("won_at") or 0)
    return {
        "total": len(members),
        "closed": len(done), "closed_words": done,
        "open_words": still_open, "missing": sorted(missing),
        "ear": sum(1 for m in members if m.get("axis") == "ear"),
        "won_at": won_at,
        "remainder": max(0, won_at - len(done)),
        "won": bool(won_at) and len(done) >= won_at,
        "exceeded": max(0, len(done) - won_at) if won_at else 0,
    }


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


def cut(candidates: list[str], lexicon: dict, size: int, won_at: int,
        name: str = "", today: date | None = None) -> dict:
    """Cut a month from an ALREADY-ORDERED candidate list, front first.

    Deliberate, never derived: the old cohort seeded itself from rep counts with
    a jitter tiebreak, which is how a set nobody chose came to feel like a
    rotation nobody chose. Someone picks this one.

    EACH MEMBER'S AXIS IS DECIDED HERE AND STORED — see `is_closed` for why it
    cannot be re-read later.

    `won_at` is the line that can be WON; `size` is the line that can be
    EXCEEDED. Two numbers rather than one, because a single number forces a
    choice between disappointing and unreachable (Andrew, 2026-09-17: "30-40 a
    month ideally but maybe realistically 15")."""
    today = today or local_today()
    chosen, seen = [], set()
    for w in candidates:                      # de-dupe, order preserved
        row = lexicon.get(w)
        if w in seen or not isinstance(row, dict):
            continue
        seen.add(w)
        chosen.append({"word": w, "axis": target_rung(row)})
        if len(chosen) >= size:
            break
    return {"name": name, "opened": today.isoformat(), "closes": closes_on(today),
            "set": chosen, "won_at": min(won_at, len(chosen))}


def carry(rec: dict, lexicon: dict) -> list[str]:
    """What an expiring month hands the next cut: its still-open members, in
    their original order, offered as CANDIDATES and nothing more.

    THERE IS NO DEBT FIELD, and that is load-bearing (the anti-ratchet law).
    Unmet items are re-cut — rolled when still central, dropped when the month
    said something wrong — and nothing anywhere records that they went unmet.
    The reset IS the forgiveness mechanism (Andrew, on the May 2026 fade and the
    ADHD cost of a ratchet); a field counting what he missed would quietly
    become a streak, which is the one thing this whole object must never be."""
    return standing(rec, lexicon)["open_words"]
