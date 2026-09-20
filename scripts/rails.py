#!/usr/bin/env python3
"""L2 — THE REACH BUDGET: when Anna may reach Andrew, and how often.

WHAT THIS REPLACES (2026-09-04). One concept that was living in two files at two
different layers, so no reader could find all of it:

  `publish.py` held the WHEN — the waking window and `in_waking_window` — because
  `push_to_phone` is the chokepoint that enforces it for every lane (2026-07-26).
  `morning_knock.py` held the HOW OFTEN — the daily cap, the min gap, and the
  counter that reads them off the knock log.

Both lanes that reach Andrew obey both halves. So `push_queue` imported half its
budget from `publish` and half from `morning_knock`, and a LANE became a
foundation for three of its peers — `knock_reply`, `knock_message` and
`reply_common` all import from `morning_knock` today. The map's own law says a
channel never owns an invariant that more than one channel obeys; this file is
that law applied to the one place it had been broken.

WHY A FILE AND NOT A BIGGER `publish.py`. The obvious move was to finish the
2026-07-26 consolidation by pushing the counts down beside the window. Measured
first: `publish.py` sat at 148/150 code lines. The ratchet's rule is that a file
at its ceiling wants a split, not a raise — so the budget landed on the same
answer the concern boundary did. `publish.py` is the delivery TAIL; whether a
reach is permitted at all is asked long before delivery, by two lanes that must
never have to touch each other to ask it.

THE L2 LINE, AMENDED. `docs/PROTOCOL_MAP.md` says policy "lives with the lanes
that read them." That holds for a policy ONE lane reads — `rails_gate` itself
stays in `morning_knock`, because only the knock lane decides whether to wake
Anna. It does not hold for a rail two channels obey. That is the whole
distinction, and it is what this file exists to mark.

Imports `state_io` and nothing else, so every lane — and `publish` itself — may
import it without a cycle.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from state_io import LOCAL_TZ, is_fire, local_date

# ── When (the waking window) ─────────────────────────────────────────────────
# Andrew's local timezone is canonical in `state_io`, which reads it from
# `learner.json.timezone` (2026-08-09), so the window follows him abroad on a
# one-field edit and stays DST-correct at home. The cron ticks a UTC superset;
# this filters.
WAKING_START_HOUR = 8      # inclusive, local
WAKING_END_HOUR = 21       # exclusive, local (last reach can land at 20:59)

# ── How often (the reach counts) ─────────────────────────────────────────────
MAX_REACHES_PER_DAY = 5    # a "reach" = a knock that actually fired (silence doesn't count)
MIN_GAP_HOURS = 3          # minimum spacing between reaches


def in_waking_window(now: datetime | None = None) -> bool:
    """Is it inside Andrew's waking hours, local time? The ONE definition — the
    rails gate, the queue's deferral, and `push_to_phone` all read this."""
    now = now or datetime.now(timezone.utc)
    return WAKING_START_HOUR <= now.astimezone(LOCAL_TZ).hour < WAKING_END_HOUR


def reaches_today(klog: list, now_local_date) -> int:
    """How many reaches actually went out today, on Andrew's clock.

    NAMED `reaches_today`, not `fires_today` (2026-09-04). It was the latter in
    `morning_knock`, and `sync_state.fires_today()` — a different function, no
    arguments — counts something else entirely: WORDS ANDREW FIRED today, cold or
    hinted. Two functions, one name, opposite subjects. `push_queue` had already
    hit the collision and aliased this one to `reaches_today` at its import line,
    which is the right name applied at the call site because the definition had
    the wrong one. Fixed at the definition; "fires" now means one thing in this
    repo, and it is Andrew's."""
    return sum(1 for k in klog
               if is_fire(k) and local_date(k.get("timestamp", "")) == now_local_date)


def last_fire(klog: list) -> dict | None:
    """The most recent reach that actually went out — the basis the min gap is
    measured from."""
    fires = [k for k in klog if is_fire(k) and k.get("timestamp")]
    return fires[-1] if fires else None


# ── How LITTLE (the supply floor) ────────────────────────────────────────────
# A rail is a bound, and a bound has two ends. Everything above is a CEILING —
# do not reach more than this. This is the FLOOR: do not let the shelf go empty.
#
# WHY IT EXISTS (2026-09-19, Andrew, measured). No audio lane is scheduled:
# every soak, drill, rotation and episode exists because Anna commissioned one
# INSIDE a session. And `commissioning.md` says the repair earns the dose —
# payload drawn from live slips, "commissioning nothing is a first-class
# outcome". Put those together and the supply of audio is gated on Andrew's
# attendance, which is exactly backwards: he is tired, so fewer sessions, so
# fewer commissions, so less in his ears, so he fades further. Every step
# behaves as designed. Measured over the ten days after he came home: 15.7
# authored minutes, no soak, no rotation, no drill.
#
# "A fade is palatability data, not a discipline failure" (DECISIONS, 07-04) —
# never answer a fade with accountability machinery. This is the opposite of
# accountability machinery: it makes the SYSTEM owe him contact, and it cannot
# be discharged by him doing anything.
SUPPLY_WINDOW_DAYS = 7
# 30 min/week is the calibration note's own arithmetic run backwards: the dial
# is 10-15 min/day of CONTACT at ~3.5 plays per tape, which needs ~129 authored
# minutes a month. This is a floor on what is PRODUCED, never on what he played
# — a floor he could fail by not listening would be a streak with a new name.
SUPPLY_FLOOR_MIN = 30
# Two days between pleasure doses. Not a ceiling on audio — episodes, knocks and
# payoffs are unaffected — just a spacing so a quiet week fills steadily instead
# of arriving all at once.
PLEASURE_MIN_GAP_DAYS = 2


def pleasure_due(produced_min: float, days_since_last: float | None) -> str:
    """"" when a no-strings dose is owed; otherwise the reason it is not.

    A REASON STRING, not a bool, for the same cause `year.problem` is one: this
    gate runs unattended on a cron, and "it did not fire" has several causes
    that look identical from the outside. The one that must never be silent is
    a floor that has quietly stopped being checked."""
    if days_since_last is not None and days_since_last < PLEASURE_MIN_GAP_DAYS:
        return f"last pleasure dose was {days_since_last:.1f}d ago (gap {PLEASURE_MIN_GAP_DAYS}d)"
    if produced_min >= SUPPLY_FLOOR_MIN:
        return (f"the shelf is stocked: {produced_min:.0f} min produced in "
                f"{SUPPLY_WINDOW_DAYS}d (floor {SUPPLY_FLOOR_MIN})")
    return ""
