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
from zoneinfo import ZoneInfo

# Windows consoles default to cp1252, which can't print Tamil — the status digest
# crashed mid-print on a fresh laptop (2026-07-15) and a dead digest invites the
# agent to improvise state. Harmless everywhere else.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Andrew's local clock — canonical here; outreach scripts import it for the rails.
LOCAL_TZ = ZoneInfo("America/New_York")


def local_today() -> date:
    """Today on ANDREW's clock, never the host's. The slip ledger dates slips,
    commissions and closes against each other, so a stamp taken from a UTC
    runner between 8pm and midnight lands a day ahead of one taken on his
    laptop — and `escalate` (a slip dated after its dose) then fires on a dose
    that had not failed. append_slips already documented this seam for its
    `when` argument; its own default, and the callers below, were still on
    local_today()."""
    return datetime.now(LOCAL_TZ).date()

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"
LEARNER_PATH = BASE / "progress" / "learner.json"
EPISODES_PATH = BASE / "progress" / "episodes.json"
SESSION_LOG_PATH = BASE / "progress" / "session_log.json"
FEEDBACK_LOG_PATH = BASE / "progress" / "feedback_log.json"
KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
SLIP_LOG_PATH = BASE / "progress" / "slip_log.json"

# Script-detection: Tamil script is the canonical lexicon key, so a phonetic-only
# token can never mint a record. PORT SURFACE — a fork to another language
# replaces this regex (moved here from sync_state.py 2026-08-04).
TAMIL_RE = re.compile(r"[஀-௿]")


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
