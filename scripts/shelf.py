#!/usr/bin/env python3
"""THE SHELF — the one audio lane that runs without him.

Every hourly tick asks: is the week's authored supply under the floor, is it
his waking hours, and has a shelf dose gone out inside the spacing? If a dose
is owed, it builds the TURN that has gone longest unmade — a rotation spine, a
soak or a drill — by running that lane's own script. Nothing here writes,
renders or publishes; each lane already knows how, and delivers itself.

WHAT THIS REPLACES (2026-10-15). `render_rotation.py --if-short` was the shelf,
and it could only ever build a rotation tape on the default spine: every
unattended tape was `inventory`, four in a row to 10-15 (Andrew: "I want
variety"). The gate moved here whole when the shelf learned to dispatch other
lanes, because a rotation script that runs the soak and drill lanes is no
longer a rotation script. `render_rotation` lost its `--if-short`.

THE SHELF, NOT THE LEARNER (2026-09-19). The floor asks whether the WEEK
PRODUCED enough audio, never whether Andrew listened to it. A gate on his
listening would be a streak with a new name, and a fade answered with
accountability machinery is the one move DECISIONS 07-04 forbids outright.

  python scripts/shelf.py --minutes 8     # the cron's call (anna.yml)
"""
import argparse
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import rails
from rebuild_rss import feed_items
from state_io import local_today

# The formats that count as the shelf being stocked, for the spacing: a dose
# that asks nothing he has to sit down for. An episode is NOT here — it asks
# something, and the floor exists for the days he has nothing to give. Drill
# joins on his word (2026-10-15), though it asks for his voice: his to skip.
PLEASURE_FORMATS = {"rotation", "soak", "payoff", "drill"}

# The turns, by feed-id prefix. Episodes stay out: too dense to follow at speed
# ("I may know 70% of the words but at speed I can't decode them", 2026-10-15).
# Anna choosing the turn inside the call that writes the tape is the next step.
SHELF_TURNS = ("rotation_machines", "rotation_inventory", "rotation_room", "soak", "drill")


def shelf_turns(items: list[dict]) -> list[str]:
    """Every turn, longest-unmade first; a never-made turn leads, and the tuple
    order breaks ties so the sequence is deterministic."""
    last = {t: max((i.get("date") or "" for i in items
                    if (i.get("id") or "").startswith(t + "_")), default="")
            for t in SHELF_TURNS}
    return sorted(SHELF_TURNS, key=lambda t: last[t])


def owed(items: list[dict], today: date) -> str:
    """"" when a shelf dose is owed; otherwise the reason it is not, as a sentence."""
    window = (today - timedelta(days=rails.SUPPLY_WINDOW_DAYS - 1)).isoformat()
    produced = sum(i.get("minutes") or 0 for i in items if (i.get("date") or "") >= window)
    last = [i["date"] for i in items
            if (i.get("format") or "").split("/")[0] in PLEASURE_FORMATS and i.get("date")]
    gap = (today - date.fromisoformat(max(last))).days if last else None
    return rails.pleasure_due(produced, gap)


def turn_command(turn: str, minutes: float) -> list[str]:
    lane, _, spine = turn.partition("_")
    cmd = [sys.executable, str(BASE / "scripts" / f"render_{lane}.py")]
    return cmd + (["--spine", spine, "--minutes", str(minutes)] if spine else [])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--minutes", type=float, default=8, help="a rotation tape's cap")
    args = ap.parse_args(argv)
    # THE TAPE WAITS FOR HIS MORNING (2026-10-15, Andrew). The supply window
    # rolls at local midnight, so the floor went short overnight and the hourly
    # cron built tapes at 00:15, 01:30, 03:27 — and `push_to_phone` held each
    # ping for quiet hours and dropped it. Building at the first waking tick
    # lands the tape and its ping together.
    if not rails.in_waking_window():
        print("   [supply] quiet hours — the tape waits for the first waking tick, so its ping lands")
        return 0
    if why := owed(feed_items(), local_today()):
        print(f"   [supply] no tape — {why}")
        return 0
    # A soak or drill with nothing to work from makes no tape and exits 0; left
    # at the head of the order it would win every tick and the shelf would
    # starve silently. So a turn that adds no feed item passes the turn on.
    for turn in shelf_turns(feed_items()):
        print(f"   [supply] turn: {turn}")
        before = {i.get("id") for i in feed_items()}
        subprocess.run(turn_command(turn, args.minutes), cwd=BASE)
        if any(i.get("id") not in before for i in feed_items()):
            return 0
        print(f"   [supply] {turn} made no tape — the turn passes on")
    # AN ABSENCE MUST BE LOUD: every lane ran and the feed did not move.
    print("   [supply] ⚠ no turn made a tape — the shelf is still short")
    return 1


if __name__ == "__main__":
    sys.exit(main())
