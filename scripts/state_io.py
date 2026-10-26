#!/usr/bin/env python3
"""The state layer's shared vocabulary: where the files are, how to read and
write them, and how a token becomes a canonical lexicon key.

Extracted from `sync_state.py` 2026-08-04. Ten scripts were importing
`load_json`, `LEXICON_PATH` and friends *from the state brain* — they did not
want the brain, they wanted IO, and that mis-shape was invisible until the
brain hit its size ceiling and had to be split.

THE WRITERS OF `learner.json`, NAMED (2026-10-12). This docstring used to say
`sync_state.py` "is the only writer". It never was: `slips.py` books slip
commissions and closes, and `mark_soak_attempted` below stamps the soak order.
Each is a seam declaring what it did — the law the delivery stamp follows — so
they are blessed here by name rather than funnelled through one file that would
have to import the slip ledger. What holds them to one standard is `save_json`:
every write is atomic and shape-checked, so no writer can leave a half-file.
The list is a ratchet (`s132`): a fourth writer is a red run until it is named.

THE BOOKS ARE CHECKED ON READ, AND REFUSED ON WRITE (2026-10-12). A truncated
write or a bad rebase used to surface as a bare JSONDecodeError — or worse, as
nothing, wherever a caller caught it and moved on (`run_studio` did, for both
the learner and the lexicon). `load_json` now raises `CorruptBook`, naming the
file, what is wrong, and how to restore it, before any caller sees a byte.

Import direction is one-way and must stay that way: this module imports from
nothing in `scripts/`, and everything else may import from it.
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from language import is_canonical

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

# The judge seat (2026-10-12): model-drafted target-language strings the ledger
# does not attest, held from publish until a reviewer passes or rejects them.
# One writer, `scripts/provenance.py`.
REVIEW_QUEUE_PATH = BASE / "progress" / "review_queue.json"

# The outreach policy (2026-10-12): approved knob values, the weekly digest the
# knock lane reads, and the proposals awaiting Andrew. One writer, `reflect.py`;
# the bounds and the reader are `rails.py`.
POLICY_PATH = BASE / "progress" / "policy.json"

# The live conversation in progress (2026-10-26): its transcript, its target queue
# and where the rotation stands. One writer, `scripts/live.py`. Not the learner
# model — nothing here votes; the close books what the gates earned.
LIVE_SESSION_PATH = BASE / "progress" / "live_session.json"


class CorruptBook(RuntimeError):
    """A book in `progress/` that does not parse, or parses into the wrong shape.
    A RuntimeError on purpose, NOT a ValueError: half a dozen callers catch
    ValueError around date parsing, and a corrupt book must never be one of the
    things a broad handler quietly walks past."""


# The shape of every book: (top level, every row). Checked at read and at write.
# Keyed by file name, so the log's own path (declared in `observations.py`, which
# imports this file) needs no import back.
BOOK_SHAPES = {
    "learner.json": (dict, None), "lexicon.json": (dict, dict),
    "episodes.json": (dict, dict), "audio_titles.json": (dict, dict),
    "observations.json": (list, dict), "knock_log.json": (list, dict),
    "session_log.json": (list, dict), "feedback_log.json": (list, dict),
    "slip_log.json": (list, dict), "push_queue.json": (list, dict),
    "review_queue.json": (list, dict), "policy.json": (dict, None),
    "live_session.json": (dict, None),
}
# The learner's structured fields. A field absent is fine (day zero has few);
# a field PRESENT in the wrong type is a corrupted book, whatever parsed.
LEARNER_FIELDS = {"soak_order": dict, "slip_closes": dict, "slip_commissions": dict,
                  "ladder": dict, "month": dict, "learner": str, "timezone": str}


def book_problem(path: Path, data) -> str:
    """What is wrong with this book's shape, or "" — "" also for any file that
    is not a book, which keeps its old contract."""
    shape = BOOK_SHAPES.get(path.name) if path.parent.name == "progress" else None
    if not shape:
        return ""
    top, row = shape
    if not isinstance(data, top):
        return f"top level is a {type(data).__name__}, the book is a {top.__name__}"
    rows = list(data.items()) if isinstance(data, dict) else list(enumerate(data))
    for key, value in rows:
        if row and not isinstance(value, row):
            return f"row {key!r} is a {type(value).__name__}, every row is a {row.__name__}"
    if path.name == "learner.json":
        for key, kind in LEARNER_FIELDS.items():
            if key in data and data[key] is not None and not isinstance(data[key], kind):
                return f"`{key}` is a {type(data[key]).__name__}, expected a {kind.__name__}"
    return ""


def _corrupt(path: Path, why: str) -> CorruptBook:
    rel = f"progress/{path.name}"
    return CorruptBook(
        f"❌ CORRUPT BOOK: {rel} — {why}. Nothing was read from it and nothing will "
        f"be written over it. A truncated write or a bad rebase does this: "
        f"`git diff -- {rel}` shows what changed, `git checkout -- {rel}` restores "
        f"the last committed copy.")


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        if path.name in BOOK_SHAPES and path.parent.name == "progress":
            raise _corrupt(path, f"not valid JSON ({e})") from None
        raise
    if (why := book_problem(path, data)):
        raise _corrupt(path, why)
    return data


def save_json(path: Path, data):
    """Atomic, and a book is shape-checked first: the new content goes to a
    sibling temp file and is swapped in whole, so a crash mid-write leaves the
    OLD book, never half of the new one."""
    if (why := book_problem(path, data)):
        raise _corrupt(path, f"refused to WRITE it: {why}")
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --- The two ladders -----------------------------------------------------------
# ONE FACT, AND IT HAD THREE HOMES until 2026-09-10: `generate_callbacks` held
# RECOGNITION_RANK, `knock_reply` held PRODUCTION_RANK and RECOGNITION_NEXT, and
# `sync_state` held DEMOTE. Nothing named what a rung IS, so each file that
# needed to compare or step one restated the ladder slightly differently — the
# same shape as every other defect this month, one level down. They live at L0
# because the rungs are a property of the ledger, not of any lane that moves one,
# and because the observation log's derivation (L0.7) must read them without
# reaching upward for a lane.
#
# `untested` IS NOT A RUNG ABOVE OR BELOW `struggled` — it is the ABSENCE of one
# (2026-10-04, Andrew). Until then a row nobody had tested read `struggled`, so
# "we have no evidence" and "he struggles" were one value: 356 of 392 rows, sari
# among them, and every planner re-aired known words as if they were weak. The
# production axis always had this — `none` is not a grade. It ranks with
# `struggled` so no ordering anywhere moves; a pass climbs to `comfortable`, a
# miss lands on `struggled`, which from here on means a test came back wrong.
RECOGNITION_DEFAULT = "untested"
RECOGNITION_RANK = {"untested": 0, "struggled": 0, "comfortable": 1, "solid": 2}
RECOGNITION_NEXT = {"untested": "comfortable", "struggled": "comfortable", "comfortable": "solid"}
DEMOTE = {"solid": "comfortable", "comfortable": "struggled", "struggled": "struggled",
          "untested": "struggled"}
PRODUCTION_RANK = {"none": 0, "hinted": 1, "cold": 2}


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


def local_date(ts_iso: str):
    """An ISO stamp on ANDREW's clock, or None if it is unparseable. The
    row-level companion to `local_today` — every log this repo keeps stamps UTC
    and every question about it ("today?", "which day?") is asked in his
    timezone. Moved here from `morning_knock` on 2026-09-04: it is a clock
    helper, and it belongs beside the clock rather than inside the lane that
    happened to need it first."""
    try:
        return datetime.fromisoformat(ts_iso).astimezone(LOCAL_TZ).date()
    except (ValueError, TypeError):
        return None


def is_fire(entry: dict) -> bool:
    """Did this knock-log row actually reach him? Legacy entries (written before
    `acted` existed) were all fires. The third read-only state predicate, beside
    `is_unseen` and `soak_pending` — moved here from `morning_knock` 2026-09-04
    so `rails.py` can count reaches without importing a lane."""
    return entry.get("acted", True)


# WHAT A DOSE WANTS FROM HIM — the stance vocabulary. "give" answers his own
# question; "ask" is every tug; "lure" survives for rows written before
# 2026-10-08. `is_give` and the demand brake it fed retired that day with the
# gifts; the rails and the log still read the label.
STANCES = {"give", "ask", "lure"}


# The script range, the stem tail and `is_tamil` (now `is_canonical`) moved to `language.py` on
# 2026-08-28 — the L0 language pack, which is now the ONE file a port to another
# language rewrites. They were declared here from 2026-08-04 (with the last three
# stray copies folded in on 08-24); what this file kept was a label, not a
# boundary, because two more port-surface values — the pinned voices and the repo
# identity — could never live beside a paths-and-clock module. Import them from
# `language`, never re-declare them: `smoke/compose.py` fails the build on a
# second copy.


# --- Lexicon helpers ---------------------------------------------------------

def resolve(word: str, lexicon: dict) -> str | None:
    """Resolve a token to its canonical lexicon key, or None.

    SCRIPT ONLY since 2026-09-21 — "a record carries its Tamil key; phonetics
    are generated for display, never stored" (DECISIONS 2026-09-13). This used
    to consult a `build_phonetic_index` map built from each row's stored
    `phonetic` list, so a Latin spelling someone had pre-named resolved and one
    nobody had guessed did not. Every key now reaches Python from a model
    holding the Tamil, so the match is script to script and the index is gone.

    It stays a named function rather than an inline `in`: ONE resolver is the
    contract every writer is canonical-at-write against, and a second copy is
    how the two halves drift apart."""
    return word if word in lexicon else None


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
# They land beside `resolve` and `is_canonical` rather than in a new module because
# that is what they are: lexicon-key resolution, one rung wider. `sync_state`
# keeps every writer.

def canon_payload(items: list[str]) -> list[str]:
    """Split comma-joined payload elements into a flat word list. A close once
    passed `--soak-payload "frame:idum,பாத்துக்கறேன்"` as one string (2026-07-13);
    the stored blob could never textually match an episode's words, so the
    session-open drain check read 'not produced' forever. Applied at write AND
    at read, so already-stored blobs heal too."""
    return [p.strip() for item in items for p in item.split(",") if p.strip()]


def resolve_soak_item(token: str, lexicon: dict) -> str | None:
    """A soak-payload token → its canonical lexicon key, or None.

    Wider than resolve() on purpose: Anna writes the soak order in prose and
    reaches for the bare headword (அவசரம்) where the lexicon key is the whole
    chunk ('அவசரம் இருக்கு'). A payload item that resolves to nothing can never
    appear in an episode's word list, so the produced-check stays False forever
    — on 2026-07-23 that dispatched a fresh episode every hour until the cron
    was pulled (M72, M73, M74 in one evening).

    THE LATIN HALF WENT 2026-09-21 with the stored `phonetic` list it read: a
    payload written 'avasaram' matched the chunk by its stored spelling. Anna
    writes the order in script now, so the prefix walk is the script one and a
    Latin fragment lands in `split_payload`'s unresolved list — loud, which is
    what the 07-23 loop needed and never had.
    """
    exact = resolve(token, lexicon)
    if exact is not None:
        return exact
    # a Tamil token that is a prefix of a longer chunk key
    if is_canonical(token):
        for key in lexicon:
            if key.startswith(token):
                return key
    return None


def split_payload(items: list[str], lexicon: dict) -> tuple[list[str], list[str]]:
    """(resolved canonical keys, tokens that resolve to nothing). Callers must
    treat the unresolved list as a WARNING and never as 'still pending' — an
    unverifiable item is a broken order, not unfinished work."""
    resolved, unresolved = [], []
    for token in canon_payload(items):
        key = resolve_soak_item(token, lexicon)
        if key:
            resolved.append(key)
        elif is_canonical(token) or token.startswith("frame:"):
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
    if all(w in newest for w in resolved):
        return False
    # A RENDER ALREADY RAN AGAINST THIS ORDER AND COULD NOT CLAIM IT (2026-09-11).
    # `claim_payload` injects the commissioned payload into the sidecar so the
    # registration carries it, but only for a key `payload_present` can find in
    # the script; when it cannot, it prints one line into a render log and the
    # order stays here saying "dispatch now" FOR EVER. M91 rendered, published
    # and committed against சமைக்கிற while the script said சமைக்குறீங்க — the
    # same verb, a Kongu spelling of the tense marker the stem rule cannot
    # bridge — and every session open after it would have dispatched another.
    # That is the 07-23 three-episodes-in-one-evening loop with a new trigger.
    # The dispatch question and the evidence question are NOT the same question:
    # the word list still answers "did the payload land" and still under-claims,
    # while a recorded attempt answers "has this order had its render" and
    # bounds the loop at one. The brief reads the same stamp and says STALLED
    # rather than the lie it would otherwise print.
    return not ((soak.get("attempted") or {}).get("at", "") >= (soak.get("from") or ""))


def mark_soak_attempted(episode: str, unclaimed: list[str]) -> None:
    """Record that a render ran against the standing order — the seam that did
    the work declares it, the same law as `mark_soak_delivered` and the slip
    commission book. Written on a SUCCESSFUL render only: a stamp for a render
    that never landed would retire an order nothing carried."""
    learner = load_json(LEARNER_PATH) or {}
    if not (learner.get("soak_order") or {}):
        return
    learner["soak_order"]["attempted"] = {
        "at": local_today().isoformat(), "episode": str(episode),
        "unclaimed": list(unclaimed)}
    save_json(LEARNER_PATH, learner)


def is_unseen(rec: dict) -> bool:
    """Never TAUGHT — no Teach Beat has carried it, on any channel. The
    teach-first law hangs on this: an UNSEEN item may be TAUGHT (shown, with its
    meaning) but never cold-quizzed. One definition; the knock menu, the volley
    picker and the session ticket all read it.

    Reads the fold, not a delivery stamp (2026-08-31, Andrew: "I can't catch a
    word I don't know in the first place"): `last_surfaced` is written by every
    lane that merely APPEARS a word, and none of those teach.

    `seen_in` LEFT THIS PREDICATE 2026-09-13, and it is the third cut on one
    line — after `last_surfaced` (2026-08-31) and callbacks (2026-09-01). Both
    of those removed a stamp that named the wrong EVENT; this one removes the
    last stamp that names the wrong PARTY. `seen_in` is written when a render
    finishes, which is a fact about the machine, so 142 rows were cold-quizzable
    on the strength of a backfill note reading "payload — dated from git" —
    words that went past Andrew's ear for weeks while nothing ever told him to
    listen for one. `seen_in` stays on the row as provenance (the studio counts
    it); it just no longer speaks for him. `taught_on` is now the fold's answer
    to a narrower question — was he THERE — and `lexicon_view.derive` owns it."""
    return not rec.get("taught_on")
