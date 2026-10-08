#!/usr/bin/env python3
"""THE LADDER — which room of the family table the production work leans toward.

WHY THERE IS NO YEAR ANY MORE (2026-10-08, Andrew: "retire the trip date,
obviously"). This file was `year.py`, a phase schedule anchored to a stored
trip date, with a T-minus on Andrew's dashboard and a six-week taper that forced new
words to zero before he flew. There is no trip deadline now. Anna is for the
lifetime of the connection, so a countdown has nothing to count to, and a taper
is race logic — it only made sense with a race. The excavation, taper, trip and
harvest phases, the intake-zero cap and every date retired with it.

WHAT SURVIVES IS THE LADDER, because its reason never depended on the trip. Not
every relative is the same problem. Addressing a child, a sibling-in-law and an
elder share almost no morphology at this level, and they are not equally safe
to practise on: a nine-year-old tolerates error completely and cannot switch to
English to be kind, while an elder switches by politeness reflex. So the work
runs DOWN, then ACROSS, then UP — easiest room first.

WHAT MOVES IT. The lean used to move on the calendar. It should move on
evidence — up a room when the books show the current room's register is mostly
his — and that rule is not built yet. Until it is, the lean is STATED: one
command (`sync_state.py ladder --lean down|across|up`), Andrew's or Anna's
call, and what is stored is the room and the day it was chosen. Nothing else:
no phase, no counter, no countdown. A stored meter is the Trip Deck's failure,
and this object refuses to grow one.

WHAT THIS FILE DOES NOT OWN: the month (`month.py`), the ORDER candidates
arrive in (`suggest_targets`, which imports this and not the other way), the
new-word dial (profile.md's, untouched), and anything Andrew does. A marker is a
sentence on a status surface, never a field, never collected, never scored.
"""
from state_io import load_json, local_today, LEARNER_PATH

# The record lives in learner.json under this key, Python-owned like every other
# field there. It replaced the `year` key on 2026-10-08 (swept by
# `sync_state.RETIRED_LEARNER_KEYS`).
KEY = "ladder"

ORDER = ["down", "across", "up"]

# Who each room is, for the surfaces that say it out loud.
ROOMS = {"down": "children", "across": "cousins and in-laws", "up": "elders"}

# One behavioural sentence per room. Every marker involves a real human, because
# a marker the machine can award itself is a marker that measures the machine.
MARKERS = {
    "down": "sixty unscripted seconds with a child, and no English in them",
    "across": "five Tamil minutes with the one person briefed not to switch",
    "up": "a call he starts, to an elder — starts, not answers",
}

# Which of the lexicon's own `register` tags LEAD in each room. This replaced
# `suggest_targets.REGISTER_TIERS` (2026-09-19) — a static survival/delight/
# dessert ordering left behind by the deck, which ranked by TOPIC, was blind to
# who Andrew was talking to, and ordered almost nothing. The shape is 0 leads,
# 1 middle, 2 trails, so an unregistered row degrades to the middle, never last.
LEADS = {
    "down": {"frame", "public", "social"},
    "across": {"social", "gossip", "faq"},
    "up": {"mil-table", "antifreeze", "faq"},
}

# Dessert in every room (constitution -> "respect loud, jaw-drop quiet").
TRAILS = {"zinger"}

# The label a ticket prints beside a row: WHERE IN THE ORDER, not what kind of
# thing it is.
RANK_NAMES = {0: "lead", 1: "mid", 2: "dessert"}


def load(learner: dict | None = None) -> dict:
    """The stated lean, or {} when none has been set (a fresh clone)."""
    if learner is None:
        learner = load_json(LEARNER_PATH) or {}
    rec = learner.get(KEY)
    return rec if isinstance(rec, dict) else {}


def problem(rec: dict) -> str:
    """Why there is no lean, in one sentence, or "" when there is one.

    THE ABSENCE HAS TO BE LOUD (/extend Gate 7.2). Without a lean every selector
    falls back to the neutral middle and still returns rows, so an unset ladder
    looks exactly like a working one from the outside."""
    if not rec:
        return "no lean is set — `sync_state.py ladder --lean down|across|up`"
    if rec.get("lean") not in ORDER:
        return f"ladder.lean is not a room: {rec.get('lean')!r}"
    return ""


def direction(rec: dict) -> str:
    """Which way the production work leans right now.

    UNSET, THE ANSWER IS `across`, NOT NOTHING. A neutral middle is the honest
    default — it is what the flat ordering did for rows with no register — and
    a lane that forgets to check still gets a sane sort instead of an exception.
    `problem` is where the absence is loud; a selector is not the place to shout."""
    return "across" if problem(rec) else rec["lean"]


def rung(rec: dict) -> dict:
    """The live room with its marker, or {} when no lean is set."""
    if problem(rec):
        return {}
    lean = rec["lean"]
    return {"direction": lean, "room": ROOMS[lean], "marker": MARKERS[lean],
            "since": rec.get("since", "")}


def register_rank(row: dict, lean: str) -> int:
    """0 leads, 1 middle, 2 trails — the prefix every ordering carries.

    The lead set is a function of WHO he is working toward, not of a topic label
    frozen when the deck died."""
    reg = row.get("register", "")
    if reg in TRAILS:
        return 2
    return 0 if reg and reg in LEADS.get(lean, set()) else 1


def record(lean: str, prev: dict) -> dict:
    """The record a `--lean` write stores: the room and the day it was chosen.
    Re-stating the same room keeps its original day — choosing a room is the
    event, repeating it is not."""
    since = prev.get("since") if prev.get("lean") == lean else ""
    return {"lean": lean, "since": since or local_today().isoformat()}


def table(rec: dict) -> list[str]:
    """The three rooms, `→` on the live one. A READ surface, so it lives here
    beside the data it renders; `sync_state` and `show_status` both print it."""
    live = rung(rec).get("direction")
    return [f"{'→' if r == live else ' '} {r:7} {ROOMS[r]:20} {MARKERS[r]}" for r in ORDER]


def status_line(rec: dict) -> str:
    """One line for the human dashboards. Names the problem when there is one —
    a blank line on a system whose selectors fell back to the middle is exactly
    the state this file exists to make visible."""
    bad = problem(rec)
    if bad:
        return f"Ladder: NOT SET — {bad}"
    r = rung(rec)
    since = f" since {r['since']}" if r["since"] else ""
    return (f"Ladder: working {r['direction']} — to the {r['room']}{since}\n"
            f"  next marker: {r['marker']}")
