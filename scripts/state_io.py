#!/usr/bin/env python3
"""The state layer's shared vocabulary: where the files are, how to read and
write them, and how a token becomes a canonical lexicon key.

Extracted from `sync_state.py` 2026-08-04. Ten scripts were importing
`load_json`, `LEXICON_PATH` and friends *from the state brain* — they did not
want the brain, they wanted IO, and that mis-shape was invisible until the
brain hit its size ceiling and had to be split. Nothing here mutates learner
state; that stays in `sync_state.py`, which is the only writer.

Import direction is one-way and must stay that way: this module imports from
nothing in `scripts/`, and everything else may import from it.
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Windows consoles default to cp1252, which can't print Tamil — the status digest
# crashed mid-print on a fresh laptop (2026-07-15) and a dead digest invites the
# agent to improvise state. Harmless everywhere else.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"
LEARNER_PATH = BASE / "progress" / "learner.json"
EPISODES_PATH = BASE / "progress" / "episodes.json"
SESSION_LOG_PATH = BASE / "progress" / "session_log.json"
FEEDBACK_LOG_PATH = BASE / "progress" / "feedback_log.json"
KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
SLIP_LOG_PATH = BASE / "progress" / "slip_log.json"


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Andrew's clock ----------------------------------------------------------

# Where he lives when he is home; the fallback when learner.json is silent (a
# fresh clone, or a fork that never set the field).
DEFAULT_TZ = "America/New_York"


def _resolve_local_tz() -> ZoneInfo:
    """Andrew's zone, read from `learner.json.timezone` — ONE dial (2026-08-09).

    Every clock-facing rule in the system already funnelled through the LOCAL_TZ
    constant below, so the zone was a one-line edit; what it was NOT was a
    *declared* one. It sat in source, in the state layer, next to nothing that
    would remind a traveller it existed. Moving it into learner.json makes the
    zone a fact about the learner rather than a fact about the code: he changes
    one field when he lands, everything downstream (quiet hours, the rails,
    local_today, feed pubDates) follows, and no script is touched.

    A bad zone name FALLS BACK rather than raising. This module is imported by
    every unattended lane — the knock cron, the push queue, the studio — and a
    typo that hard-crashes all of them is a worse failure than one that runs on
    the home zone and complains: the fallback keeps the machine reaching him.
    The complaint goes to stderr, and `session_brief` prints the live zone on
    every load, which is the check that actually gets read.
    """
    name = (load_json(LEARNER_PATH) or {}).get("timezone") or DEFAULT_TZ
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        print(f"⚠ learner.json names an unknown timezone {name!r} — falling back "
              f"to {DEFAULT_TZ}. Quiet hours and dates will be on the home clock.",
              file=sys.stderr)
        return ZoneInfo(DEFAULT_TZ)


# Andrew's local clock — canonical here; outreach scripts import it for the rails.
LOCAL_TZ = _resolve_local_tz()


def local_today() -> date:
    """Today on ANDREW's clock, never the host's. The slip ledger dates slips,
    commissions and closes against each other, so a stamp taken from a UTC
    runner between 8pm and midnight lands a day ahead of one taken on his
    laptop — and `escalate` (a slip dated after its dose) then fires on a dose
    that had not failed. append_slips already documented this seam for its
    `when` argument; its own default, and the callers below, were still on
    local_today()."""
    return datetime.now(LOCAL_TZ).date()


def in_transit(now: datetime | None = None) -> str:
    """The transit bit (2026-08-10, Andrew): a local date through which Andrew
    cannot receive anything AT ALL — set for a flight, cleared on landing.
    Returns the rails' reason string while it holds, "" once it lapses.

    It lives here, beside `local_today` and the timezone, for the reason those
    do: it is a fact about the LEARNER, not about knock policy. TWO lanes reach
    his phone — the rails gate and the push queue's drain — and until 2026-08-11
    only the rails read it, so a queued push still fired into the flight. That
    hole was invisible because the queue was empty every time the bit was set.
    A rule that must hold at two doors belongs under both of them.

    Why holding matters at all: Apple keeps exactly ONE notification for an
    unreachable phone, so a dose fired into a flight overwrites the last one and
    both are destroyed. Held here — before the LLM, before anything is logged —
    no row is written, so the unanswered stretch can never reach the
    ignore-streak and be read as fading.
    """
    quiet_until = (load_json(LEARNER_PATH) or {}).get("quiet_until") or ""
    now = (now or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ)
    if quiet_until and now.date() <= date.fromisoformat(quiet_until):
        return f"quiet_until {quiet_until} — in transit, not fading"
    return ""


# Script-detection: Tamil script is the canonical lexicon key, so a phonetic-only
# token can never mint a record. PORT SURFACE — a fork to another language
# replaces this regex (moved here from sync_state.py 2026-08-04).
TAMIL_RE = re.compile(r"[஀-௿]")


# --- Lexicon helpers ---------------------------------------------------------

def build_phonetic_index(lexicon: dict) -> dict[str, str]:
    """{phonetic -> script} built from each record's phonetic list."""
    index: dict[str, str] = {}
    for word, rec in lexicon.items():
        for phon in rec.get("phonetic", []):
            index.setdefault(phon, word)
    return index


def resolve(word: str, lexicon: dict, phon_index: dict[str, str]) -> str | None:
    """Resolve a phonetic-or-script token to its canonical lexicon key, or None."""
    if word in lexicon:
        return word
    return phon_index.get(word)


def is_tamil(word: str) -> bool:
    return bool(TAMIL_RE.search(word))
