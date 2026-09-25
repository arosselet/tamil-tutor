#!/usr/bin/env python3
"""Was the dose HEARD? The evidence half of the slip ledger's escalation law.

WHAT THIS REPLACES (2026-09-25). `slips.slip_patterns` set `escalate` when a slip
was dated after the dose's COMMISSION date. A commission is a dose that was
built, not a dose that was heard, and `daily_session.md` already says so: "a
delivered dose is not a heard dose; do not escalate a treatment from an unplayed
tape." The rule was the one place that law did not reach, and it steered Anna's
next commission ("change the format, never loop harder") off doses nobody had
been shown to play.

FOUND BY a hand-run reflection (progress/reflections/2026-09-25.md), by joining
slip timestamps to listen events. All three `nga-has-no-address` slips (09-11,
09-16 and 09-20 20:48Z) predate the only listen evidence for the soak built for
them (a rating at 09-20 23:07Z). Of the four ESCALATE flags that day, none had
evidence the dose was ever heard.

THREE STATES, because "we don't know yet" and "it didn't work" are different
findings and the old rule could only say the second:

  heard         an `attended` observation on a payload word IN THE SAME LANE, on
                or after the commission date. Only THIS state can escalate, and
                only on a slip dated a LATER DAY than the listen.
  awaiting      the dose was built after the attendance recorder worked and
                nothing shows it was played. Not a failure; the move is to cue
                the ear block, never to build a second dose on an unplayed first.
  unverifiable  every commission predates a working recorder, so its effect can
                never be known. Derived from the dates, never written to state:
                the ledgers stay append-only and Python-owned.

SAME LANE, because the first version of this join was wrong on the real ledger
and the real ledger caught it (2026-09-25). Matching on the word alone let a
25-word ROTATION rating (09-20 20:04Z) that happened to carry one soak payload
word count as hearing the SOAK, which kept an ESCALATE alive that the soak's own
listen (23:07Z) refutes. A commission records a lane and a payload, not an
artifact id, so lane + payload word + date is the closest join the data allows:
it can credit a different soak that repeats a word, never a rotation.

THE SILENT NO-OP, answered out loud: with almost no attendance events logged
(ratings only), nearly every tag reads `awaiting` and ESCALATE goes quiet. That
must not look like "all healed", so the digest carries a summary line that counts
each state, including a plain "0 heard".

A payload entry `frame:*` names a pattern, not a word, so it cannot be joined to
an attended word and never counts as heard. That errs toward `awaiting`, which
withholds an escalation rather than inventing one.

Layering: imports `state_io` and `observations` only; `slips` imports FROM here.
"""

from collections import Counter

from observations import OBSERVATIONS_PATH
from state_io import load_json, local_date

# The lanes a dose can be commissioned to, and the ONE list of them: read by
# sync_state's --soak-channel choices and by escalation_note below, which names
# the lanes not yet tried. It is one list because two copies of this rule is
# exactly how the escalation came to name a lane by taste (2026-09-11): the
# NEVER COMMISSIONED notice in the digest read "owed a soak order" while its
# own sibling in `cmd_slips` read "owed a dose", and the digest is the copy Anna
# reads at every close. Twelve consecutive orders went soak or drill and the
# episode lane went 27 days unreached. (Moved here from slips.py 2026-09-25.)
DOSE_CHANNELS = ("episode", "soak", "drill")
# The first day the attendance recorder WORKED, not the day the log began. The
# rating lane was wired 2026-09-10 but looked missions up under the feed stem
# while the registry is keyed by number, so it minted no `attended` event for any
# lane until c84d22a (2026-09-19 19:48 EDT): every listen before it went
# unrecorded whatever happened in the room. A dose commissioned earlier has no
# record to be found, so its effect is unknowable, not absent.
ATTENDANCE_LOGGED_SINCE = "2026-09-19"
# A listen is stamped with the feed item's FORMAT (`sync_state.cmd_rate`), which
# is not the commission's lane: an episode dose is aired as a "mission".
ATTENDED_AS = {"episode": "mission"}


def attended_events() -> list[dict]:
    """Every listen the log holds. Read once per ledger pass, not per tag."""
    return [o for o in (load_json(OBSERVATIONS_PATH) or []) if o.get("kind") == "attended"]


def _bare(word: str) -> str:
    """A payload phrase and a registry phrase differ by punctuation ("சமைக்கிற?")."""
    return word.strip(" ?!.,")


def _heard_at(commission: dict, attended: list[dict]) -> str:
    """The earliest listen, in the lane the dose was commissioned to, on one of its
    words, on or after the day it was commissioned; "" when there is none."""
    words = {_bare(w) for w in commission.get("payload") or [] if not w.startswith("frame:")}
    lane = ATTENDED_AS.get(commission.get("channel"), commission.get("channel"))
    since = commission.get("at") or ""
    days = [(o["at"], local_date(o["at"])) for o in attended
            if o.get("channel") == lane and _bare(o.get("word") or "") in words]
    return min((at for at, d in days if d and d.isoformat() >= since), default="")


def judge_dose(commissions: list[dict], slip_days: list[str],
               attended: list[dict]) -> tuple[str, str, bool]:
    """(state, heard_at, slipped_after_heard) for one tag. A slip follows a listen
    only when it is dated a LATER DAY: a slip row's `at` is when it was WRITTEN (a
    chat slip is logged at session close), so same-day order cannot be trusted, and
    withholding an escalation for a day is the cheap error."""
    if not commissions:
        return "", "", False
    heard = min((h for h in (_heard_at(c, attended) for c in commissions) if h), default="")
    if heard:
        return "heard", heard, any(d > local_date(heard).isoformat() for d in slip_days)
    logged = any((c.get("at") or "") >= ATTENDANCE_LOGGED_SINCE for c in commissions)
    return ("awaiting" if logged else "unverifiable"), "", False


def dose_note(p: dict) -> str:
    """The one line a surface prints for a tag's dose state ("" when it has none)."""
    state = p.get("dose_state")
    if state == "heard":
        return f"✓ heard {p['heard_at'][:10]} and no slip since — test it, don't re-order it."
    if state == "awaiting":
        return ("⏳ dose built, nothing shows it was heard — not a failed treatment. "
                "Cue the ear block; don't build a second dose on an unplayed first.")
    if state == "unverifiable":
        return ("○ every dose for this predates a working attendance recorder — its effect can "
                "never be known; a fresh dose can be tested.")
    return ""


def dose_summary(patterns: list[dict]) -> str:
    """Counts of each dose state across live patterns, so a quiet ESCALATE reads
    as "nothing heard yet" and never as "nothing wrong"."""
    n = Counter(p.get("dose_state") for p in patterns if p.get("dose_state"))
    if not n:
        return ""
    return (f"Dose evidence: {n['heard']} heard, {n['awaiting']} awaiting attendance, "
            f"{n['unverifiable']} unverifiable — ESCALATE needs a listen; "
            f"'awaiting' is not 'failed'.")


def _and_join(items) -> str:
    items = list(items)
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else "".join(items)


def escalation_note(channels) -> str:
    """"soak tried; drill and episode untried" — the half of the rule that says
    change the format TO WHAT.

    `audio_channels.md` has said "change the format, never loop harder" since
    07-28, and both places that printed it named `channels[0]` — the OLDEST lane
    tried — and then stopped, so the one question the reader has was the one
    answer the ledger withheld while holding it in hand. Tried keeps the order
    the doses were commissioned in; the remainder is listed in DOSE_CHANNELS
    order. Every lane tried is not "no advice available": it says the repair has
    outlived the audio surface, which is worth hearing plainly."""
    tried = [c for c in channels if c in DOSE_CHANNELS]
    left = [c for c in DOSE_CHANNELS if c not in tried]
    if not tried:
        return "a dose was built and he slipped again"
    if not left:
        return "every lane tried and it still slips — this has outgrown the audio lanes"
    return f"{_and_join(tried)} tried; {_and_join(left)} untried"
