#!/usr/bin/env python3
"""THE YEAR — the phase schedule between the month and the goal.

WHY THIS EXISTS. `month.py` gave the system a unit that can be finished; it did
not give it a REASON to prefer one month's work over another. The arc premise is
still chosen to cover "what the ticket says is thin", which is the deficit-seeking
machine one level up wearing a calendar. A month knows when it ends. It does not
know what it is FOR.

What it is for is the trip. Andrew's family is in Coimbatore, he goes roughly
once a year, and the next one is around August 2027 — so the year has a shape
the system has never been able to express: build, taper, immerse, harvest, and
build again. That shape answers three questions no other file can:

  1. WHICH DIRECTION the production work leans. Not every relative is the same
     problem. Addressing a child, a sibling-in-law and a father-in-law share
     almost no morphology at this level, and they are not equally safe to
     practise on: a seven-year-old niece tolerates error completely and cannot
     switch to English to be kind, while an elder switches by politeness reflex
     and cannot help it. So the ladder runs DOWN, then ACROSS, then UP — easiest
     room first, and the bare imperative (a verb stem with nothing on it) is also
     the cheapest door into the verb system.
  2. WHEN TO STOP ADDING. Six weeks out, intake goes to zero. An item learned in
     July is not available under pressure in August, and a FAILED retrieval in
     front of a mother-in-law does not cost one word — it costs the rest of the
     conversation, because he retreats to English. Volume drops, intensity rises,
     nothing new goes in. Same logic as tapering before a race.
  3. WHAT THE EAR SHOULD BE FED. The catch-the-drift carve-out (profile.md →
     Calibration) has always been a single fixed exception to the 95% coverage
     rule. It becomes a RAMP here: one voice with the situation given, then two,
     then three with nothing given — deliberately harder than a real room, so the
     real room feels slow. The 95% floor on the Intercept is untouched.

THIS IS NOT THE TRIP DECK RETURNING. `DECISIONS.md` -> "Retire the Trip Deck"
stands, and what it retired is worth naming precisely: a CONTAINER of curated
rows, keyed to a date that expired, with a burn rate and a sprint meter over it.
There is no container here, no curriculum join, no burn rate, no meter. The date
is an ANCHOR, not a deadline: every phase boundary is derived from it, so moving
the date re-phases the whole year in one edit and strands nothing. That is the
same argument `month.py` makes for itself — a bounded thing that RE-CUTS is not
the deck, and a year that ends in a harvest and opens again is the most re-cuttable
object in the system.

NOTHING HERE IS STORED BUT THE THREE DATES. The phases are a function of
(`opened`, `trip_from`, `trip_to`) and the constants below. There is no "current
phase" field to drift, no progress counter, no stored marker — ask, never read.
A stored phase would be the deck's dishonest meter rebuilt one layer up: green
while the calendar walked past it.

WHAT THIS FILE DOES NOT OWN: the month (its own file), the ORDER candidates
arrive in (`suggest_targets`, which imports THIS and not the other way), and
anything Andrew does. A milestone here is a sentence printed on a status
surface, never a field, never a thing collected, never a thing scored. The
field-mission lesson holds (DECISIONS -> the 09-09 withdrawal): homework Anna
collects is homework that does not happen.
"""
from datetime import date, timedelta

from state_io import load_json, local_today, LEARNER_PATH


# The record lives in learner.json under this key, Python-owned like every other
# field there. One year is live at a time; a finished year is overwritten and git
# holds it, exactly as the month and the campaign heading already work.
KEY = "year"

# The opening sweep. Three weeks, because it is an AUDIT and not a curriculum:
# `sync_state check --draw` re-bases a ledger that profile.md has called overdue
# since 2026-09-10. Andrew is ten months in, so this is not a day-zero inventory
# — it is the instrument the system already built and has never fired.
EXCAVATION_DAYS = 21

# Six weeks of taper before the trip. See the docstring: this is the one window
# where `intake` is forced to zero.
TAPER_DAYS = 42

# Four weeks after the trip. He comes home with hundreds of half-caught
# fragments — things heard twenty times and never understood, a word an uncle
# kept using — attached to real episodic memory and decaying fast. Harvested,
# the trip becomes curriculum; unharvested it is a fond blur, and it is the
# richest material the system will see all year.
HARVEST_DAYS = 28

# The ladder, in order. `direction` steers selection (see `LEADS`); `voices` and
# `situation_given` steer the ear ramp; `intake` overrides the profile dial only
# where it is not None; `marker` is one behavioural sentence for a status surface.
#
# Every marker is BEHAVIOURAL and involves a real human, because a marker the
# machine can award itself is a marker that measures the machine. Two of them
# cannot be scheduled at all — he can only become eligible for them — and that is
# deliberate: a milestone he can force is a milestone he can fake.
ORDER = ["excavation", "down", "across", "up", "taper", "trip", "harvest"]

PHASES = {
    "excavation": dict(
        direction="across", voices=1, situation_given=True, intake=None,
        marker="the Receptive Check is run and the ledger is re-based on it"),
    "down": dict(
        direction="down", voices=1, situation_given=True, intake=None,
        marker="sixty unscripted seconds with a child, and no English in them"),
    "across": dict(
        direction="across", voices=2, situation_given=True, intake=None,
        marker="five Tamil minutes with the one person briefed not to switch"),
    "up": dict(
        direction="up", voices=3, situation_given=False, intake=None,
        marker="a call he starts, to an elder — starts, not answers"),
    "taper": dict(
        direction="up", voices=3, situation_given=False, intake=0,
        marker="nothing new goes in; what he already has gets fast"),
    "trip": dict(
        direction="up", voices=3, situation_given=False, intake=0,
        marker="someone speaks to him in Tamil without thinking about it first"),
    "harvest": dict(
        direction="across", voices=2, situation_given=False, intake=None,
        marker="what he half-caught at the table is in the ledger"),
}

# Which of the lexicon's own `register` tags LEAD in each direction of address.
# This replaces `suggest_targets.REGISTER_TIERS` — a static survival/delight/
# dessert ordering left behind by the deck, which ranked by TOPIC, was blind to
# who Andrew was talking to, and degraded 283 of 366 rows to the middle rung and
# therefore ordered almost nothing.
#
# The shape is deliberately identical (0 leads, 1 middle, 2 trails) so this is a
# drop-in at every call site, and an unregistered row still degrades to the
# middle rather than to the back. What changes is that the lead set now MOVES
# with the phase: the elders' table leads when he is working up to the elders,
# and not in the month he is trying to make a nine-year-old laugh.
LEADS = {
    "down": {"frame", "public", "social"},
    "across": {"social", "gossip", "faq"},
    "up": {"mil-table", "antifreeze", "faq"},
}

# Dessert in every direction (constitution -> "respect loud, jaw-drop quiet").
TRAILS = {"zinger"}

# The label a ticket prints beside a row. It says WHERE IN THE ORDER, not what
# kind of thing it is — which is the honest change from `survival/delight/
# dessert`, three words that claimed to describe the item when they only ever
# described its position in a sort that has now moved.
RANK_NAMES = {0: "lead", 1: "mid", 2: "dessert"}

# Who a lean actually points at, for the surfaces that say it out loud.
ROOMS = {"down": "children", "across": "cousins and in-laws", "up": "elders"}


def _d(s) -> date | None:
    """An ISO date, or None for anything that is not one. Never raises: a
    malformed date is a LOUD problem (see `problem`), not a traceback in a lane
    that only wanted to know which way to lean."""
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def load(learner: dict | None = None) -> dict:
    """The live year, or {} when none has been opened (day zero, a fresh clone)."""
    if learner is None:
        learner = load_json(LEARNER_PATH) or {}
    rec = learner.get(KEY)
    return rec if isinstance(rec, dict) else {}


def problem(rec: dict) -> str:
    """Why there is no schedule, in one sentence, or "" when there is one.

    THE ABSENCE HAS TO BE LOUD (/extend Gate 7.2). Every failure mode below
    produces a system that looks exactly like success from the outside: the
    ticket still returns rows, they are simply no longer ordered by anything,
    and every meter reads green. That is the precise shape of the bug the deck
    retirement was built to avoid — `tier_rank`'s own docstring says so — so the
    schedule reports why it is empty instead of quietly being empty."""
    if not rec:
        return "no year is open — `sync_state.py year --from <date> --to <date>`"
    opened, tfrom, tto = (_d(rec.get("opened")), _d(rec.get("trip_from")),
                          _d(rec.get("trip_to")))
    if not opened:
        return f"year.opened is not a date: {rec.get('opened')!r}"
    if not tfrom or not tto:
        return f"the trip has no dates: {rec.get('trip_from')!r}..{rec.get('trip_to')!r}"
    if tto < tfrom:
        return f"the trip ends before it starts: {tfrom} .. {tto}"
    ladder = (tfrom - timedelta(days=TAPER_DAYS)) - (opened + timedelta(days=EXCAVATION_DAYS))
    if ladder.days < 3:
        return (f"no room for the ladder: {opened} + {EXCAVATION_DAYS}d excavation and "
                f"{TAPER_DAYS}d taper leave {ladder.days}d for down/across/up")
    return ""


def schedule(rec: dict) -> list[dict]:
    """Every phase with its dates, in order. [] when `problem` says why not.

    The three ladder phases split whatever is left between the excavation and
    the taper — evenly, and derived rather than declared, so a trip that moves
    six weeks does not need six edits. The remainder goes to the LAST of them:
    `up` is the phase nearest the trip and the one whose extra days are worth
    the most."""
    if problem(rec):
        return []
    opened, tfrom, tto = _d(rec["opened"]), _d(rec["trip_from"]), _d(rec["trip_to"])
    out, cursor = [], opened

    def span(name: str, days: int):
        nonlocal cursor
        out.append({"phase": name, "from": cursor.isoformat(),
                    "to": (cursor + timedelta(days=days - 1)).isoformat(),
                    **PHASES[name]})
        cursor += timedelta(days=days)

    span("excavation", EXCAVATION_DAYS)
    ladder = ((tfrom - timedelta(days=TAPER_DAYS)) - cursor).days
    third = ladder // 3
    span("down", third)
    span("across", third)
    span("up", ladder - 2 * third)       # the remainder lands nearest the trip
    span("taper", TAPER_DAYS)
    span("trip", (tto - tfrom).days + 1)
    span("harvest", HARVEST_DAYS)
    return out


def phase(rec: dict, today: date | None = None) -> dict:
    """The phase `today` falls in, or {} — before the year opens, after the
    harvest closes, or whenever `problem` has something to say."""
    iso = (today or local_today()).isoformat()
    for p in schedule(rec):
        if p["from"] <= iso <= p["to"]:
            return p
    return {}


def direction(rec: dict, today: date | None = None) -> str:
    """Which way the production work leans right now.

    OUTSIDE A YEAR THE ANSWER IS `across`, NOT NOTHING. A neutral middle is the
    honest default — it is what the flat ordering already did for the 283 rows
    carrying no register — and it means a lane that forgets to check whether a
    year is open still gets a sane sort instead of an exception. `problem` is
    where the absence is loud; a selector is not the place to shout."""
    return phase(rec, today).get("direction", "across")


def register_rank(row: dict, lean: str) -> int:
    """0 leads, 1 middle, 2 trails — the prefix every ordering carries.

    Drop-in for the retired `tier_rank`, with the same three rungs and the same
    graceful degradation (an unregistered row sorts middle, never last), and one
    difference that is the whole point: the lead set is a function of WHO he is
    working up to this quarter, not of a topic label frozen when the deck died."""
    reg = row.get("register", "")
    if reg in TRAILS:
        return 2
    return 0 if reg and reg in LEADS.get(lean, set()) else 1


def intake_cap(rec: dict, default: int, today: date | None = None) -> int:
    """New word types per audio dose, after the phase has had its say.

    Only the taper and the trip override it, and both override it to zero. The
    override is a FLOOR-BREAKER rather than a dial: everywhere else this returns
    the profile.md number untouched, because the calibration dial has one owner
    and it is not this file."""
    over = phase(rec, today).get("intake")
    return default if over is None else over


def days_to_trip(rec: dict, today: date | None = None) -> int | None:
    """Days until the family is in front of him. None when no year is open."""
    tfrom = _d(rec.get("trip_from"))
    return None if not tfrom else (tfrom - (today or local_today())).days


def is_over(rec: dict, today: date | None = None) -> bool:
    """Past the harvest. A year that cannot be scheduled reads as OVER, never as
    open — an unbounded year is the conveyor again, one scale up, and the whole
    point of this object is that it ends and re-cuts."""
    s = schedule(rec)
    return (s[-1]["to"] < (today or local_today()).isoformat()) if s else bool(rec)


def table(rec: dict, today: date | None = None) -> list[str]:
    """The phase table, one line per phase, `→` on the live one.

    A READ surface, so it lives here beside the schedule it renders rather than
    in `sync_state`, which owns WRITES. Both the command and the dashboard print
    it, and a second hand-rolled copy in either would be the one thing this
    codebase keeps recording: a composition hand-copied into two files, extended
    in one of them, silently divergent in the other."""
    iso = (today or local_today()).isoformat()
    return [f"{'→' if p['from'] <= iso <= p['to'] else ' '} {p['phase']:11} "
            f"{p['from']} → {p['to']}  lean {p['direction']:6} · ear {p['voices']}v"
            f"{'' if p['situation_given'] else '/cold'}"
            f"{'' if p['intake'] is None else f' · intake {p['intake']}'}"
            for p in schedule(rec)]


def opened_record(opened: str, trip_from: str, trip_to: str, prev: dict) -> dict:
    """The three dates, assembled — the whole of what is ever stored.

    Assembled HERE and not in the writer so that `problem` can be asked of the
    result before anything lands: a record that cannot be scheduled is worse
    than no record, because every selector falls back to a flat sort and nothing
    says why. The writer's job is to refuse it, not to work out what it is."""
    return {"opened": opened or local_today().isoformat(),
            "trip_from": trip_from or prev.get("trip_from", ""),
            "trip_to": trip_to or prev.get("trip_to", "")}


def status_line(rec: dict, today: date | None = None) -> str:
    """One line for the human dashboards and the agent brief.

    It names the problem when there is one. A blank line here, on a system whose
    selectors silently fell back to a flat sort, is exactly the state this file
    exists to make visible."""
    bad = problem(rec)
    if bad:
        return f"Year: NOT SCHEDULED — {bad}"
    p = phase(rec, today)
    if not p:
        s = schedule(rec)
        return (f"Year: opens {s[0]['from']}" if (today or local_today()).isoformat() < s[0]["from"]
                else f"Year: over since {s[-1]['to']} — re-cut it")
    left = (_d(p["to"]) - (today or local_today())).days
    d = days_to_trip(rec, today)
    return (f"Phase {ORDER.index(p['phase']) + 1}/{len(ORDER)} {p['phase']} "
            f"({left}d left) · leaning {p['direction']} · T-{d} to the trip\n"
            f"  next marker: {p['marker']}")
