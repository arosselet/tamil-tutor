#!/usr/bin/env python3
"""L0.5 — THE OBSERVATION LOG. Every fact the system learns about Andrew and a
word, appended and never spent. `lexicon_view` folds it into the lexicon
(Phase 3, 2026-09-10); this file only appends and names the vocabulary.

WHY A LOG (2026-08-23 → 2026-09-10, five instances of one defect): setting a
field SPENDS an observation — the rung moves and the channel, the question and
the confidence are gone. So the same defect came back wearing a new field five
times, and August's only available repair was purging 108 rows. A log is what
makes revision cheap: change the policy, re-derive.

FOUR FIELDS CARRY THE DESIGN — `kind` (an exposure is not a test), `channel`
(carries TRUST: `seed` and `self-report` are recorded and never vote), `axis`
(the two move independently) and `source` (the artifact, for audit).

A JSON ARRAY, NOT JSONL: `publish.UNIONABLE` resolves a rebase conflict on an
append-only array by keeping every row from both sides, keyed on `id`. The knock
cron and the laptop both write here.

A BAD CONSTANT WARNS, IT DOES NOT RAISE — every unattended lane imports this.
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
    "knock", "text", "volley", "challenge", "fielding", "audio",  # a judged phone reply, by modality
    "episode", "drill", "soak", "rotation",   # a dose was delivered
    "check",        # the Receptive Check
    "media",        # native media he reported back on
    "ledger",       # carried over from the mutated ledger at the 2026-09-10 cutover:
                    # a watched writer moved the rung and the event was never logged
    # ── below this line: DECLARED, never watched. Excluded by default policy. ──
    "seed",         # the day-one self-estimate, 153 rows before session one
    "self-report",  # a mission debrief; he is reporting how it FEELS, not what happened
}
DECLARED = {"seed", "self-report"}
WATCHED = CHANNELS - DECLARED    # the policy's whole teeth: only these vote

KINDS = {
    "taught",       # a full Teach Beat — first contact, generously given
    "exposed",      # it went past him in a dose; heard is not known
    "tested",       # he was asked and something came back
    "asked-about",  # HE raised it: "I don't know this word" — free, unsolicited, honest
    "claimed",      # asserted without a test behind it (the seed's kind)
}

AXES = {"recognition", "production", None}
RESULTS = {"right", "wrong", "partial", None}
# The judges' vocabularies, translated into the log's. One home each.
CATCH_RESULT = {"caught": "right", "half-caught": "partial", "missed": "wrong", "miss": "wrong"}
HEARD_RESULT = {"right": "right", "misread": "wrong"}
FIRE_RESULT = {"cold": "right", "hinted": "partial", "capped": "partial"}


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

    Nothing here touches `lexicon.json`; `lexicon_view.observe` is the write
    path that records AND folds, and it is the one every writer uses."""
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
            "at": e.get("at") or now,
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
