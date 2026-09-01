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
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from language import is_tamil

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
# The rating picker's list, published as PLAIN TEXT, one row per line (2026-08-27).
# Not JSON, and the reason is measured: raw.githubusercontent.com serves every raw
# file as "text/plain; charset=utf-8" with "nosniff", so iOS Shortcuts never parses
# it as JSON whatever the extension — a .json here arrives as one opaque blob and
# Choose from List draws a single unpickable row. Text plus Split Text by New Lines
# is deterministic and needs no parse at all. Nothing but the phone reads this.
# Derived from `rss.xml` and rewritten by whoever writes that —
# `rebuild_rss.write_recent_audio`, never the learner writer (2026-09-01).
RECENT_AUDIO_PATH = BASE / "progress" / "recent_audio.txt"

# The audio lanes' public names, stem -> title (2026-09-01). Soaks and drills
# leave no script and no caption, so the name the writer gives a dose exists for
# exactly one moment; this is where it is kept. See scripts/audio_titles.py.
AUDIO_TITLES_PATH = BASE / "progress" / "audio_titles.json"


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


# The script range, the stem tail and `is_tamil` moved to `language.py` on
# 2026-08-28 — the L0 language pack, which is now the ONE file a port to another
# language rewrites. They were declared here from 2026-08-04 (with the last three
# stray copies folded in on 08-24); what this file kept was a label, not a
# boundary, because two more port-surface values — the pinned voices and the repo
# identity — could never live beside a paths-and-clock module. Import them from
# `language`, never re-declare them: `smoke/compose.py` fails the build on a
# second copy.


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


# ── The soak order's payload, and the two read-only predicates over state ────
# Moved down from `sync_state` on 2026-08-23, the last step of the spine
# refactor, and this is where the cycle died: `suggest_targets` needed
# `is_unseen` and `soak_pending`, `sync_state` needed `reconcile_focus`, and the
# two imported each other — patched with a deferred import carrying the comment
# "lazy: suggest_targets imports us". Selection may depend on state; state may
# not depend on selection (2026-07-25). These four read state and decide nothing,
# so they belong at the bottom, and `reconcile_focus` — which WRITES — stays up
# in sync_state where it was.
#
# They land beside `resolve` and `is_tamil` rather than in a new module because
# that is what they are: lexicon-key resolution, one rung wider. `sync_state`
# keeps every writer.

def canon_payload(items: list[str]) -> list[str]:
    """Split comma-joined payload elements into a flat word list. A close once
    passed `--soak-payload "frame:idum,பாத்துக்கறேன்"` as one string (2026-07-13);
    the stored blob could never textually match an episode's words, so the
    session-open drain check read 'not produced' forever. Applied at write AND
    at read, so already-stored blobs heal too."""
    return [p.strip() for item in items for p in item.split(",") if p.strip()]


def resolve_soak_item(token: str, lexicon: dict, phon_index: dict[str, str]) -> str | None:
    """A soak-payload token → its canonical lexicon key, or None.

    Wider than resolve() on purpose: Anna writes the soak order in prose and
    reaches for the bare headword ('avasaram') where the lexicon key is the
    whole chunk ('அவசரம் இருக்கு', phonetic 'avasaram irukku'). A payload item
    that resolves to nothing can never appear in an episode's word list, so the
    produced-check stays False forever — on 2026-07-23 that dispatched a fresh
    episode every hour until the cron was pulled (M72, M73, M74 in one evening).
    """
    exact = resolve(token, lexicon, phon_index)
    if exact is not None:
        return exact
    t = token.strip().lower()
    if not t:
        return None
    # a phonetic that STARTS with the token ('avasaram' → 'avasaram irukku')
    for key, rec in lexicon.items():
        for p in rec.get("phonetic", []):
            if p and (p.lower() == t or p.lower().startswith(t + " ")):
                return key
    # a Tamil token that is a prefix of a longer chunk key
    if is_tamil(token):
        for key in lexicon:
            if key.startswith(token):
                return key
    return None


def split_payload(items: list[str], lexicon: dict) -> tuple[list[str], list[str]]:
    """(resolved canonical keys, tokens that resolve to nothing). Callers must
    treat the unresolved list as a WARNING and never as 'still pending' — an
    unverifiable item is a broken order, not unfinished work."""
    phon_index = build_phonetic_index(lexicon)
    resolved, unresolved = [], []
    for token in canon_payload(items):
        key = resolve_soak_item(token, lexicon, phon_index)
        if key:
            resolved.append(key)
        elif is_tamil(token) or token.startswith("frame:"):
            # A brand-new payload word is legitimately absent from the lexicon
            # until the episode that teaches it registers it — Tamil script and
            # frame keys stay verifiable, because that is exactly the form an
            # episode's word list stores. Only a LATIN fragment that resolves to
            # nothing ('avasaram' vs 'அவசரம் இருக்கு') can never match anything.
            resolved.append(token)
        else:
            unresolved.append(token)
    return resolved, unresolved


def soak_pending() -> bool:
    """True when the standing soak order hasn't been carried yet — the answer
    `status` prints as NOT YET PRODUCED, for EVERY channel.

    CHANNEL-AWARE SINCE 2026-08-27, and the docstring above used to be a lie.
    Two lanes clear an order two ways, by design: the episode lane registers its
    words in `episodes.json` and never stamps, while the soak and drill lanes
    register no episode and so stamp `delivered` instead. This function knew only
    the first, and its claim of parity with `status` stopped being true the day
    `session_brief` grew the branch and this copy did not. Measured on the live
    08-26 konjam order: the brief said produced ✓, this said pending — and its
    caller was the since-retired `studio_watchdog`, whose step 2 dispatched a full studio run on
    a True. That is the 2026-07-23 re-dispatch loop (M72/M73/M74 in one evening)
    with a new trigger, latent only because the cron was stale.

    Only VERIFIABLE items count. A payload token that resolves to no lexicon
    key can never appear in an episode's word list, so counting it as pending
    is an infinite dispatch loop, not a to-do (2026-07-23: 'avasaram' against
    the key 'அவசரம் இருக்கு' produced three unwanted episodes in one evening).

    Lives here rather than in a lane because the session ticket, the brief and
    selection all need the same answer. ONE resolver — a second copy is how this
    diverged the first time."""
    soak = (load_json(LEARNER_PATH) or {}).get("soak_order") or {}
    raw = [w for w in soak.get("payload", []) if w]
    if not raw:
        return False
    channel = soak.get("channel") or "episode"
    if channel != "episode":
        # Nothing to compare against: these lanes register no episode. The lane
        # that rendered the order stamps it, and the stamp must be no older than
        # the order or a previous week's delivery clears this week's ask.
        deliv = soak.get("delivered") or {}
        return not (deliv.get("channel") == channel
                    and (deliv.get("at") or "") >= (soak.get("from") or ""))
    resolved, unresolved = split_payload(raw, load_json(LEXICON_PATH) or {})
    if unresolved:
        print(f"  ⚠ soak payload unresolvable, ignored for the produced-check: "
              f"{', '.join(unresolved)} — fix the soak order")
    if not resolved:
        return False
    episodes = load_json(EPISODES_PATH) or {}
    newest = episodes[max(episodes, key=int)].get("words", []) if episodes else []
    return not all(w in newest for w in resolved)


def is_unseen(rec: dict) -> bool:
    """Never TAUGHT — no episode has carried it. The teach-first law hangs on
    this: an UNSEEN item may be TAUGHT (shown, with its meaning) but never
    cold-quizzed. One definition; the knock menu, the volley picker, and the
    session ticket all read it.

    IT NO LONGER READS `last_surfaced` (2026-08-31, Andrew: "I can't catch a
    word I don't know in the first place"). That field is the DELIVERY stamp —
    `mark_exposed` writes it from the soak sheet, the drill sheet, the knock
    push and the queue drain — and the constitution grants those lanes no
    teaching authority at all: "EXPOSE, don't drill" is the instruction they
    ship under. Only the seed episode teaches on the audio side ("captions
    doing the heavy lifting"), and that path stamps `seen_in`. So one soak loop
    repeating a word was silently retiring that word's right to ever get a
    Teach Beat, and it went straight into the cold-quiz pool instead. 51 rows
    were sitting in exactly that state when this was found — delivered by a
    tape, never taught, quizzable.

    THE SILENT NO-OP THIS CLOSES: a never-taught word and a taught one were
    byte-identical to every reader, so the gate could not fail loudly — it just
    produced a demand for a word Andrew had never met, which reads as Anna
    being careless rather than as a predicate reading the wrong field.

    THAT RESIDUAL IS NOW CLOSED (2026-09-01, Andrew). `seen_in` used to record
    every word a sidecar declared, `callbacks_used` included, so an episode
    credited itself with teaching words that merely rode past. The split needed
    NO new schema in the end: `seen_in` is TAUGHT and `exposures` /
    `last_surfaced` are APPEARED — both already existed, and one write site in
    `render_audio` conflated them. Only `new_words_landed` stamps this field now.

    Two measurements shaped that fix and are worth keeping. The 83-row estimate
    did not survive replaying all 278 rows against the sidecars: 192 are
    genuinely taught, 78 are UNDECIDABLE (episodes 6..41 predate sidecars, so no
    evidence exists either way), and only 8 are provably appeared-only. And the
    cheap predicate — `exposures == 0` — is FALSE: it selects 95 rows of which
    69 are genuinely taught, so adjudication has to read the sidecars, not the
    counter. `sync_state untaught` cleared the 26 rows that survived every
    guard; the guards spared anything he had produced, because graduation is
    final (07-26)."""
    return not rec.get("seen_in")
