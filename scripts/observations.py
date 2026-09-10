#!/usr/bin/env python3
"""L0.5 — THE OBSERVATION LOG. Every fact the system learns about Andrew and a
word, appended and never spent.

WHAT THIS REPLACES: nothing yet, and that is deliberate. This is Phase 0 of
`docs/observation_log_plan.md` — strictly additive. Every existing writer keeps
mutating `lexicon.json` exactly as before and ALSO appends here; nothing reads
this file. Phase 3 is where the lexicon becomes a derived view and the
mutations go. Doing it in that order means the daily loop cannot notice.

WHY A LOG AT ALL (2026-08-23 → 2026-09-10, five instances of one defect).
Setting a field SPENDS an observation: `rec["recognition"] = nxt` moves a rung
and loses the channel it came from, what was asked, and how sure anyone was.
Provenance has been the named missing thing since the seed bug and kept not
getting added because there was nowhere to put it — the row was the only
artifact. So the same defect kept coming back wearing a new field: a day-one
self-estimate scored as evidence; a mission debrief logged as live fire;
"didn't do it" indistinguishable from "couldn't do it"; a gist self-report in
an evidence slot; and `struggled` meaning three different things at once.

THE PAYOFF ANDREW ASKED FOR BY NAME: cheap revision. "We can fail forward, we
can revise this, it's fine if we discover and fix and get discontinuities in
our measurements" (2026-09-10). A mutated field cannot be re-read, which is why
August's only available move was PURGING 108 rows. Under a log they get
re-scored instead, by changing a policy and re-deriving.

FOUR FIELDS CARRY THE DESIGN:
  `kind`    — an exposure is not a test. `asked-about` is its own evidence:
              Andrew volunteering "enaa is a new word for me actually" is the
              most honest signal this system receives and had nowhere to go.
  `channel` — carries TRUST. A reader's policy decides what counts; `seed` and
              `self-report` are recorded and excluded by default, which is how
              the mission ritual survives while its output stops voting.
  `axis`    — recognition and production move independently and always have.
  `source`  — points at the artifact (knock id, session date), so any claim can
              be walked back to what produced it.

A JSON ARRAY, NOT JSONL, and that is not a style choice: `publish.UNIONABLE`
resolves a rebase conflict on an append-only array by keeping every row from
both sides, keyed on a field. The knock cron and the laptop both write here, so
this file needs that resolver — and it needs a unique `id` for it to dedupe on,
which is why one is minted per event rather than keying on `at` (a retell
scores five words in the same second).

A BAD CONSTANT WARNS, IT DOES NOT RAISE. Every unattended lane imports this;
a typo that hard-crashes the knock cron is a worse failure than one that logs
loudly and keeps reaching him — the same call `_resolve_local_tz` makes for the
same reason. Nothing reads this file yet, so a junk row is recoverable and a
dead knock is not. `smoke/observations.py` is what actually catches the typo,
before it ships.
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from state_io import BASE, load_json, save_json

OBSERVATIONS_PATH = BASE / "progress" / "observations.json"

# Where an observation came from. The split that matters is not lane-by-lane, it
# is TRUSTED vs DECLARED: everything above the line is something the system
# watched happen, everything below is something it was told.
CHANNELS = {
    "session",      # Anna's own observation in a live session
    "eavesdrop",    # a judged catch — the one honest recognition instrument
    "knock",        # a judged typed reply on the phone
    "episode", "drill", "soak", "rotation",   # a dose was delivered
    "check",        # the Receptive Check, once it exists
    "media",        # native media he reported back on
    # ── below this line: DECLARED, never watched. Excluded by default policy. ──
    "seed",         # the day-one self-estimate, 153 rows before session one
    "self-report",  # a mission debrief; he is reporting how it FEELS, not what happened
}

KINDS = {
    "taught",       # a full Teach Beat — first contact, generously given
    "exposed",      # it went past him in a dose; heard is not known
    "tested",       # he was asked and something came back
    "asked-about",  # HE raised it: "I don't know this word" — free, unsolicited, honest
    "claimed",      # asserted without a test behind it (the seed's kind)
}

AXES = {"recognition", "production", None}
RESULTS = {"right", "wrong", "partial", None}


def _checked(value, allowed, field):
    """Return `value` if legal, else a loud, greppable marker. Never raises —
    see the module docstring: the knock cron must survive a typo."""
    if value in allowed:
        return value
    print(f"   ⚠ observations: unknown {field} {value!r} — recorded as-is, "
          f"not one of {sorted(a for a in allowed if a)}", file=sys.stderr)
    return f"unknown:{value}"


def record(word, channel, kind, *, axis=None, result=None, source="", note=""):
    """Append ONE observation. Returns the event written.

    Callers pass what they already know at the seam they already have; nothing
    here reads or touches `lexicon.json`, so a caller that fails to record has
    not corrupted anything — it has only lost a row, which Phase 2's diff will
    surface as a divergence."""
    return record_many([dict(word=word, channel=channel, kind=kind, axis=axis,
                             result=result, source=source, note=note)])[0]


def record_many(events):
    """Append several at once — one read and one write for a retell that scores
    a handful of words, instead of N of each."""
    log = load_json(OBSERVATIONS_PATH) or []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written = []
    for e in events:
        row = {
            "id": uuid.uuid4().hex[:12],
            "at": now,
            "word": e.get("word", ""),
            "channel": _checked(e.get("channel"), CHANNELS, "channel"),
            "kind": _checked(e.get("kind"), KINDS, "kind"),
            "axis": _checked(e.get("axis"), AXES, "axis"),
            "result": _checked(e.get("result"), RESULTS, "result"),
            "source": e.get("source") or "",
            "note": e.get("note") or "",
        }
        log.append(row)
        written.append(row)
    save_json(OBSERVATIONS_PATH, log)
    return written
