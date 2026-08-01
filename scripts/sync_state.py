#!/usr/bin/env python3
"""
State management for the Tamil learning system.

Word-state lives in ONE place: progress/lexicon.json — a word-keyed map where each
record carries both axes (recognition + production), its phonetics, provenance, and
last-surfaced date. This script owns all writes to it. The LLM (Anna) calls
`update` at the end of a session to record what it observed.

  progress/lexicon.json     → word-state (this file's domain)
  progress/learner.json     → continuity: running story (debrief), soak order, status (thin, LLM-facing)
  progress/episodes.json    → episodes / listens (audio artifacts)
  progress/session_log.json → momentum log, one entry per session-DAY (repeat
      update calls in one close merge into that day's entry, never mint a row)

Usage:
    # After a session: record production + recognition movement
    python scripts/sync_state.py update --produced-cold poren --stuck-word வை

    # Show current state (what Anna reads at session start)
    python scripts/sync_state.py status

Canonical-at-write: produced/recognition words are resolved phonetic->script against
the lexicon. A produced word that resolves to no record is WARNED and SKIPPED rather
than silently poisoning state — production presupposes a recognition record.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Windows consoles default to cp1252, which can't print Tamil — the status digest
# crashed mid-print on a fresh laptop (2026-07-15) and a dead digest invites the
# agent to improvise state. Harmless everywhere else.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Andrew's local clock — canonical here; outreach scripts import it for the rails.
LOCAL_TZ = ZoneInfo("America/New_York")

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"
LEARNER_PATH = BASE / "progress" / "learner.json"
EPISODES_PATH = BASE / "progress" / "episodes.json"
SESSION_LOG_PATH = BASE / "progress" / "session_log.json"
FEEDBACK_LOG_PATH = BASE / "progress" / "feedback_log.json"
KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
SLIP_LOG_PATH = BASE / "progress" / "slip_log.json"

# How a slip stops being live evidence. After this many days with no recurrence a
# tag RETIRES — it is not "fixed", it is just no longer evidence. Retiring is not
# disappearing: a retired tag that was never confirmed landed comes back as
# UNVERIFIED, a re-eligible check (Andrew, 2026-07-30). The ledger never forgets;
# the SURFACE forgets, and then asks again.
#
# 21 days deliberately matches generate_callbacks.INTERVAL_DAYS["cold"] — a
# pattern and a cold word age on the same clock, so there is one recheck rhythm
# in the system rather than two constants drifting apart.
SLIP_RETIRE_DAYS = 21
# Recurrence that makes a slip a pattern rather than a one-off — the same bar
# protocol/diagnosis.md sets for the system's own bugs: one is noise, two is signal.
SLIP_PATTERN_COUNT = 2

# The sprint deadline (profile.md Phase 1.5): Andrew lands in India the week of
# 2026-08-12. The deck countdown is computed against this; clear it after the trip.
TRIP_DATE = date(2026, 8, 12)

# Recognition ladder. A word the learner *recognizes* is comfortable or solid;
# struggled means shaky; unseen means no record. The floor counts cold production
# among words that are at least comfortable.
RECOGNITION_LEVELS = ["struggled", "comfortable", "solid"]
RECOGNIZED = {"comfortable", "solid"}
DEMOTE = {"solid": "comfortable", "comfortable": "struggled", "struggled": "struggled"}
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


def mark_exposed(lexicon: dict, keys: list[str], phon_index: dict | None = None,
                 today: str | None = None) -> list[str]:
    """A dose carrying these words went OUT THE DOOR — stamp the delivery.

    Exposure is one of the ledger's three declared events (2026-07-26): a rep is
    Andrew producing the word, an ask is spend, an exposure is delivery. It is
    declared by the seam that ASSEMBLES the dose (episode registration, soak
    sheet, drill sheet, knock push), never mined from prose. The stamp is what
    closes the background rotation loop: being exposed moves a word to the back
    of its own queue, so coverage is guaranteed instead of hoped for.

    Mutates in place; callers own the save. Returns the keys actually stamped."""
    if phon_index is None:
        phon_index = build_phonetic_index(lexicon)
    today = today or date.today().isoformat()
    marked = []
    for k in keys:
        key = resolve(k, lexicon, phon_index)
        if key is None:
            print(f"   ⚠ exposure: '{k}' not in lexicon — skipped")
            continue
        lexicon[key]["last_surfaced"] = today
        lexicon[key]["exposures"] = lexicon[key].get("exposures", 0) + 1
        marked.append(key)
    return marked


def record_exposure(keys: list[str]) -> list[str]:
    """Load-stamp-save wrapper around `mark_exposed` for delivery seams that do
    not already hold the lexicon in memory (knock push, soak, drill, drain).
    The caller adds LEXICON_PATH to its commit when this returns anything."""
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None or not keys:
        return []
    marked = mark_exposed(lexicon, keys)
    if marked:
        save_json(LEXICON_PATH, lexicon)
        print(f"   Exposure stamped: {', '.join(marked)}")
    return marked


def mark_soak_delivered(channel: str) -> bool:
    """The lane that RENDERED the standing order stamps it consumed.

    The episode lane clears itself for free: registration writes the payload
    into episodes.json and creates any missing lexicon row, so "newest episode
    carries it" is answerable. The soak and drill lanes have neither — and
    inferring delivery from `last_surfaced` fails on exactly the words that
    matter, because `split_payload` deliberately passes Tamil-script payload
    items that are legitimately PRE-lexicon (a brand-new word), while
    `mark_exposed` can only stamp rows that already exist. One such word
    (நிறைஞ்சிடுச்சு, 2026-07-27) held an order at NOT YET PRODUCED through a
    successful render — the M72/M73/M74 re-dispatch loop, one layer in.

    So the lane declares it instead of the checker guessing. Same ledger law as
    exposure (2026-07-26): delivery is declared by the seam that ships the dose.

    Returns False when there is no order to stamp; callers add LEARNER_PATH to
    their commit when this returns True."""
    learner = load_json(LEARNER_PATH)
    if not learner or not (learner.get("soak_order") or {}):
        return False
    learner["soak_order"]["delivered"] = {
        "channel": channel, "at": date.today().isoformat()}
    save_json(LEARNER_PATH, learner)
    print(f"   Soak order marked delivered by the {channel} lane")
    return True


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
    """True when the standing soak order hasn't been carried by the newest
    episode — the same answer `status` prints as NOT YET PRODUCED.

    Only VERIFIABLE items count. A payload token that resolves to no lexicon
    key can never appear in an episode's word list, so counting it as pending
    is an infinite dispatch loop, not a to-do (2026-07-23: 'avasaram' against
    the key 'அவசரம் இருக்கு' produced three unwanted episodes in one evening).

    Lives here rather than in `studio_watchdog` (2026-07-28) because the session
    ticket needs the same answer and cannot import the studio — `run_studio`
    pulls the whole render stack. One definition, three readers; the watchdog
    re-exports it."""
    soak = (load_json(LEARNER_PATH) or {}).get("soak_order") or {}
    raw = [w for w in soak.get("payload", []) if w]
    if not raw:
        return False
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
    """Never soaked anywhere — no episode appearance, never surfaced. The
    teach-first law hangs on this: an UNSEEN item may be TAUGHT (shown, with its
    meaning) but never cold-quizzed. One definition; the knock menu, the volley
    picker, and the session ticket all read it."""
    return not rec.get("seen_in") and not rec.get("last_surfaced")


def is_pattern(rec: dict) -> bool:
    """A pattern/lemma record is a generative structure (e.g. the present/future
    toggle), tracked on the same axes as a word but metered separately."""
    return rec.get("type") == "pattern"


def compute_floor(lexicon: dict) -> dict:
    """The viability floor: of the WORDS recognized (comfortable+solid),
    how many fire cold? This is the one honest word-level progress meter.
    Patterns are excluded — they get their own Engines meter. Ear-only
    (direction=catch) items are excluded too: they clear on recognition and
    are never forced to fire, so counting them makes the meter lie."""
    recognized = [w for w, r in lexicon.items()
                  if not is_pattern(r) and r.get("direction") != "catch"
                  and r.get("recognition") in RECOGNIZED]
    cleared = [w for w in recognized if lexicon[w].get("production") == "cold"]
    total = len(recognized)
    pct = (len(cleared) / total * 100) if total else 0.0
    return {"cleared": len(cleared), "total": total, "pct": pct}


def compute_engines(lexicon: dict) -> dict:
    """The engine meter: of the tracked generative patterns, how many fire cold —
    i.e. the learner can produce a NOVEL instance unaided? Reported separately
    from the word-level viability floor so neither muddies the other. Ear-only
    (direction=catch) patterns are excluded — they clear on recognition (the
    deck's catch side meters them), so they'd pin this meter below 100% forever."""
    patterns = [w for w, r in lexicon.items()
                if is_pattern(r) and r.get("direction") != "catch"]
    online = [w for w in patterns if lexicon[w].get("production") == "cold"]
    total = len(patterns)
    pct = (len(online) / total * 100) if total else 0.0
    return {"online": len(online), "total": total, "pct": pct}


def compute_deck(lexicon: dict, deck: str = "trip") -> dict:
    """A named deck is a finite, deadline-driven set (e.g. the India-trip survival
    phrases) tagged `deck: "<name>"`. Its meter is the headline during a sprint:
    of the deck's members, how many fire cold? Members are counted regardless of
    type — a chunk fires cold when said whole, a frame when a novel slot-fill lands.
    Anna narrates the countdown to the deadline (Python counts; Anna narrates).

    Members carry a `direction`: "fire" (default — cleared when production goes
    cold) or "catch" (ear-only — the win is comprehension, cleared when recognition
    reaches solid; never forced to fire). cleared/total/pct stay the FIRE side so
    every caller's headline is honest; caught/catch_total meter the ear."""
    members = {w: r for w, r in lexicon.items() if r.get("deck") == deck}
    fire = [w for w, r in members.items() if r.get("direction", "fire") != "catch"]
    catch = [w for w, r in members.items() if r.get("direction") == "catch"]
    cleared = [w for w in fire if members[w].get("production") == "cold"]
    caught = [w for w in catch if members[w].get("recognition") == "solid"]
    total = len(fire)
    pct = (len(cleared) / total * 100) if total else 0.0
    # Survival-tier headline (2026-07-18, Andrew — refines the 07-13 touchdown bar:
    # the narrated meter counts the tier that decides freezing at the table, not the
    # whole inventory; a 2.5/day full-deck ask read as failure at a winnable 1.1/day
    # survival pace). Tier stays a menu concern owned by suggest_targets — joined
    # lazily so the lexicon schema stays frozen; no curriculum file → survival
    # degrades to the whole fire side.
    try:
        from suggest_targets import DECK_TIERS, deck_registers
        regs = deck_registers(deck)
        surv = [w for w in fire if DECK_TIERS.get(regs.get(w, ""), 1) == 0] if regs else fire
    except Exception:
        surv = fire
    # Coverage rides alongside the headline (2026-07-25): cold/total is honest
    # about what it counts and blind to distribution — it read as a won sprint
    # while 50 of 70 fire items had never been worked. `untouched` is the count
    # of members with no `last_surfaced` at all; the per-tier/per-register
    # breakdown lives on the ticket (suggest_targets → deck_coverage).
    untouched = sum(1 for w in fire if not members[w].get("last_surfaced"))
    surv_untouched = sum(1 for w in surv if not members[w].get("last_surfaced"))
    return {"cleared": len(cleared), "total": total, "pct": pct,
            "caught": len(caught), "catch_total": len(catch),
            "surv_cleared": sum(1 for w in surv if members[w].get("production") == "cold"),
            "surv_total": len(surv),
            "untouched": untouched, "surv_untouched": surv_untouched,
            "catch_untouched": sum(1 for w in catch if not members[w].get("last_surfaced"))}


# --- Episode helpers (progress/episodes.json — a flat {id: episode} map) ------

def compute_status() -> str:
    """The status line IS the scoreboard (post the 2026-06-30 listens pivot):
    the deck countdown during a sprint, the floor otherwise. Never a chore line —
    episodes are self-contained doses; nothing is ever 'under-listened'."""
    lexicon = load_json(LEXICON_PATH) or {}
    deck = compute_deck(lexicon)
    if deck["total"]:
        days = (TRIP_DATE - date.today()).days
        never = (f" · {deck['untouched']} never worked" if deck["untouched"] else "")
        return (f"Trip Deck {deck['surv_cleared']}/{deck['surv_total']} survival cold · "
                f"{days} days to touchdown · "
                f"{burn_rate(deck['surv_total'] - deck['surv_cleared'], days)} · "
                f"full deck {deck['cleared']}/{deck['total']}{never}")
    floor = compute_floor(lexicon)
    return f"Viability floor {floor['cleared']}/{floor['total']} fire cold ({floor['pct']:.0f}%)"


def cold_fires_recent(days: int = 7) -> int:
    """COLD fires in the trailing `days`-day window, across chat sessions and phone
    replies — the pace side of the burn rate. Live from the logs, never stored.
    Replies count per word via reply_fired_cold (the judge grades each word on its
    own, post revealed-cap); entries from before per-word verdicts (2026-07-03)
    fall back to the flat verdict-gated count."""
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    n = 0
    for s in load_json(SESSION_LOG_PATH) or []:
        if s.get("date", "") >= cutoff:
            n += len(s.get("cold", []))
    for k in load_json(KNOCK_LOG_PATH) or []:
        if k.get("reply_at", "") < cutoff:
            continue
        if "reply_fired_cold" in k:
            n += len(k["reply_fired_cold"])
        elif k.get("reply_verdict") == "cold":
            n += len(k.get("reply_fired", []))
    return n


def burn_rate(pending: int, days_left: int, window: int = 7) -> str:
    """The honest pace line: cold/day needed to clear the given pending count by
    the deadline vs. the trailing cold/day actually happening (survival tier since
    2026-07-18). Python states the math; Anna narrates what it means."""
    need = pending / max(days_left, 1)
    pace = cold_fires_recent(window) / window
    return f"need {need:.1f} cold/day, trailing {window}-day pace {pace:.1f}/day"


def fires_today() -> int:
    """Words fired (cold or hinted) TODAY, across chat sessions and phone replies —
    the fast per-day reward counter appended to the scoreboard. Computed live from
    the logs, never stored (a stored counter is a meter that can lie)."""
    today = date.today().isoformat()
    n = 0
    for s in load_json(SESSION_LOG_PATH) or []:
        if s.get("date") == today:
            n += len(s.get("cold", [])) + len(s.get("hinted", []))
    for k in load_json(KNOCK_LOG_PATH) or []:
        # reply_fired is only ever non-empty for a scored (cold/hinted) reply
        if k.get("reply_at", "").startswith(today):
            n += len(k.get("reply_fired", []))
    return n


def compute_recent_missions(episodes: dict, n: int = 4) -> list[dict]:
    # No listens count here — each episode is a self-contained dose (the
    # 2026-06-30 pivot); surfacing a counter to Anna invites listen-chasing.
    return [{"mission": int(m), "title": ep.get("title", f"Mission {m}")}
            for m, ep in sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:n]]


def write_thin_learner(learner: dict, episodes: dict):
    thin = {
        "learner": learner.get("learner", "Andrew"),
        "last_debrief": learner.get("last_debrief", ""),
        "soak_order": learner.get("soak_order", {}),
        "next_engine": learner.get("next_engine", ""),
        # The ≤FOCUS_SIZE drill cohort — stored state, not an emergent sort
        # (2026-07-26): membership is a fact in a file, immune to counting bugs.
        "focus_cohort": learner.get("focus_cohort", []),
        # The slip ledger's two learner-side books. THIS IS A WHITELIST — a key
        # missing here is DELETED on the next update, not merely left stale.
        # `slip_closes` was absent from it, so `--slip-tested tag:landed` wrote a
        # close and the very same close's write_thin_learner erased it: no slip
        # had ever actually been closed since the mechanism shipped 2026-07-30,
        # and nothing surfaced the loss because a wiped close is indistinguishable
        # from never having tested. Found 2026-07-31 while wiring
        # slip_commissions, which landed in the identical trap on its first run.
        # Any future learner-side book must be added here too.
        "slip_closes": learner.get("slip_closes", {}),
        "slip_commissions": learner.get("slip_commissions", {}),
        "recent_missions": compute_recent_missions(episodes),
        "status": compute_status(),
    }
    save_json(LEARNER_PATH, thin)
    print(f"  Updated learner.json ({LEARNER_PATH.relative_to(BASE)})")


# --- Commands ----------------------------------------------------------------

def cmd_update(args):
    lexicon = load_json(LEXICON_PATH)
    learner = load_json(LEARNER_PATH)
    episodes = load_json(EPISODES_PATH) or {}
    if lexicon is None or learner is None:
        print("Error: lexicon.json or learner.json missing. See BOOTSTRAP.md.")
        sys.exit(1)

    phon_index = build_phonetic_index(lexicon)
    today = date.today().isoformat()
    applied = {"cold": [], "hinted": [], "demoted": []}  # for the session log

    # ── THE COMMISSION GATE (2026-08-01, Andrew: "block the close") ──────
    # NEVER COMMISSIONED was advisory and got walked past for mechanical
    # reasons — venum-for-kudunga sat 24 days between first slip and first
    # dose while the ticket warned daily ("the flag needs teeth", feedback
    # 07-31, second occurrence of the commissioning complaint). Same law as
    # wants_scheduled_push: when prose fails, Python catches the
    # contradiction and forces the re-ask. Runs BEFORE any write so a
    # refused close is safely re-runnable — touch() counts reps, so a
    # partially-applied close must never happen.
    slip_rows = parse_slip_args(getattr(args, "slip", None) or [])
    declared = {canon_tag(t) for t in getattr(args, "slip_commissioned", None) or []}
    landed_now = {canon_tag(r.rpartition(":")[0])
                  for r in getattr(args, "slip_tested", None) or []
                  if r.strip().lower().endswith(":landed")}
    # A declared tag only counts as covered if an order will actually stand —
    # a --slip-commissioned with no order is the typo record_slip_commission
    # rejects later, and it must not sweet-talk the gate first.
    order_stands = bool(args.soak_channel or args.soak_payload
                        or (learner.get("soak_order") or {}).get("channel"))
    sim = [{"tag": canon_tag(r["tag"]), "date": today} for r in slip_rows]
    owed = [p for p in slip_patterns(log=(load_json(SLIP_LOG_PATH) or []) + sim)
            if p["uncommissioned"] and p["tag"] not in landed_now
            and not (p["tag"] in declared and order_stands)]
    reason = getattr(args, "no_commission", None)
    if owed and not reason:
        print("⛔ CLOSE REFUSED — live slip pattern(s) with no dose ever built:")
        for p in owed:
            print(f"   ⚠ {p['tag']} — {p['count']}× over {p['span_days']}d")
        print("   Commission in THIS close:   --soak-payload … --soak-channel "
              "soak|episode|drill --slip-commissioned <tag>")
        print("   …or close over it, reason on the record:   --no-commission '<why>'")
        print("   Nothing was written. Re-run the FULL close with one of the above.")
        sys.exit(2)
    if owed:
        print(f"  ⚠ closing over uncommissioned slip(s) "
              f"({', '.join(p['tag'] for p in owed)}) — reason: {reason}")

    def touch(key):
        """Worked in a session: refresh the date AND count the rep.
        `last_surfaced` is one overwritten date, so it can say WHEN but never HOW
        MANY — and the focus set needs a count (2026-07-26). Both channels write
        THIS counter now: sessions here, knocks at the judge seam
        (knock_reply.apply_verdict) — declared events, never text forensics."""
        lexicon[key]["last_surfaced"] = today
        lexicon[key]["reps"] = lexicon[key].get("reps", 0) + 1

    def set_recognition(word, level):
        """Set recognition; create a record if the word is new (script only)."""
        key = resolve(word, lexicon, phon_index)
        if key is None:
            if not is_tamil(word):
                print(f"  ! '{word}' is new but phonetic — add it in Tamil script so it can be canonical. Skipped.")
                return
            lexicon[word] = {
                "gloss": "", "phonetic": [], "recognition": level,
                "production": "none", "seen_in": [], "last_surfaced": today,
            }
            print(f"  + New word '{word}' → recognition {level} (gloss empty — fill in later)")
            return
        lexicon[key]["recognition"] = level
        touch(key)
        print(f"  Recognition '{key}' → {level}")

    def demote_recognition(word):
        key = resolve(word, lexicon, phon_index)
        if key is None:
            print(f"  ! '{word}' not in lexicon — nothing to demote. Skipped.")
            return
        cur = lexicon[key].get("recognition", "struggled")
        new = DEMOTE.get(cur, "struggled")
        lexicon[key]["recognition"] = new
        touch(key)
        applied["demoted"].append(key)
        print(f"  Recognition '{key}' demoted {cur} → {new}")

    def set_production(word, level):
        key = resolve(word, lexicon, phon_index)
        if key is None:
            print(f"  ! Produced '{word}' but no record resolves — add recognition first (script). Skipped.")
            return
        lexicon[key]["production"] = level
        touch(key)
        applied[level].append(key)
        print(f"  Produced {level.upper()}: {key}")

    def teach_word(spec):
        """A word taught in-session enters the lexicon at `struggled` recognition.

        The live teaching surface had NO write path (2026-07-28): `--mastered`/
        `--comfortable` overstate what one generous first contact proves,
        `--stuck-word` and `--mark-seen` both refuse an absent key, and
        `seed-deck` is a deck-authoring flow. So the pakkam/paakkalaam deep-dive
        taught பக்கத்துல, ஆச்சு and இருக்கேன் and recorded NONE of them — the next
        ticket could not know they were taught, and a queued soak order carried a
        word the lexicon had never heard of. `struggled` is the honest level: it
        is what a first contact buys. Production stays unset until he fires it,
        so this can never inflate the floor. Accepts `WORD` or `WORD=gloss`.
        """
        word, _, gloss = spec.partition("=")
        word, gloss = word.strip(), gloss.strip()
        if not is_tamil(word):
            print(f"  ! '{word}' is phonetic — teach it in Tamil script so the key "
                  f"can be canonical. Skipped.")
            return
        key = resolve(word, lexicon, phon_index)
        if key is not None:
            touch(key)
            if gloss and not lexicon[key].get("gloss"):
                lexicon[key]["gloss"] = gloss
            print(f"  Taught (already known): {key} — refreshed, recognition left "
                  f"at {lexicon[key].get('recognition', 'struggled')}")
            return
        lexicon[word] = {
            "gloss": gloss, "phonetic": [], "recognition": "struggled",
            "production": "none", "seen_in": [], "last_surfaced": today,
        }
        print(f"  + Taught '{word}' → recognition struggled"
              f"{', gloss: ' + gloss if gloss else ' (gloss empty — fill in later)'}")

    # Taught this session — must run BEFORE the axes below, so a word taught and
    # then fired in the same close resolves instead of being refused.
    for spec in args.teach:
        teach_word(spec)

    # Recognition movement
    for w in args.mastered_word:
        set_recognition(w, "solid")
    for w in args.comfortable_word:
        set_recognition(w, "comfortable")
    for w in args.stuck_word:
        demote_recognition(w)

    # Production axis
    for w in args.produced_cold:
        set_production(w, "cold")
    for w in args.produced_hinted:
        set_production(w, "hinted")

    # Listened episodes — hearing an episode surfaces its words (audio side of the
    # recency bridge): bump last_surfaced on each of its words that is in the lexicon.
    for mission in args.listened:
        ep = episodes.get(str(mission))
        if not ep:
            print(f"  ! No episode M{mission} to log a listen for. Skipped.")
            continue
        ep["listens"] = ep.get("listens", 0) + 1
        surfaced = 0
        for w in ep.get("words", []):
            key = resolve(w, lexicon, phon_index)
            if key:
                lexicon[key]["last_surfaced"] = today
                surfaced += 1
        print(f"  Listened M{mission} (now {ep['listens']}x) — surfaced {surfaced} lexicon words")

    # Next engine focus — the frame to unlock next, surfaced in the ticket and digest.
    if args.next_engine:
        learner["next_engine"] = args.next_engine
        print(f"  Next engine set: {args.next_engine}")

    # Mark-seen — update last_surfaced without touching recognition/production.
    # Closes the lore-memo gap: a frame a knock introduced is no longer UNSEEN.
    for key in args.mark_seen:
        if key in lexicon:
            touch(key)
            print(f"  Marked seen: {key}")
        else:
            print(f"  ! '{key}' not in lexicon — skipped")

    # Soak order — the intentional payload for the NEXT audio dose (what Anna
    # wants soaked), read by the Director and by the soak sheet. Overwrites;
    # fail-forward, no history.
    #
    # It used to REBUILD the dict from three keys, which silently ate every
    # other key on the next write. That is why the 2026-07-18 narrated_drama
    # decision ("commissioned by Anna via soak order, form: …, scale: …") never
    # had an implementation: nothing wrote a form, nothing read one, and a
    # hand-placed one died at the next close. The order is a BRIEFING now —
    # unnamed keys survive, and it carries `channel` (which lane renders it)
    # and `focus` (what to permute over the payload) beside the words.
    if (args.soak_payload or args.soak_seed or args.soak_focus
            or args.soak_channel or args.soak_form):
        order = dict(learner.get("soak_order") or {})
        # Per-field, not rebuild-from-args. The old code recomputed `payload`
        # on every write, so once the order also carried a focus and a channel,
        # setting one of those ALONE would have silently wiped the words — the
        # same class of bug as the clobber above, introduced by fixing it.
        if args.soak_payload:
            order["payload"] = [resolve(w, lexicon, phon_index) or w
                                for w in canon_payload(args.soak_payload)]
        order.setdefault("payload", [])
        order["scene_seed"] = args.soak_seed or order.get("scene_seed", "")
        if args.soak_focus is not None:
            order["focus"] = args.soak_focus
        if args.soak_channel is not None:
            order["channel"] = args.soak_channel
        if args.soak_form is not None:
            order["form"] = args.soak_form
        # A re-set order is a NEW order: drop any prior lane's delivery stamp, or
        # a close on the same day a dose already shipped would read as already
        # produced and never render (date compare alone can't see it — `from` and
        # `delivered.at` are both today). Any change to the brief invalidates it.
        order.pop("delivered", None)
        order["from"] = today
        learner["soak_order"] = order
        extra = "".join(f" · {k}: {order[k]}"
                        for k in ("channel", "form", "focus") if order.get(k))
        print(f"  Soak order set: {', '.join(order['payload']) or '(seed only)'}{extra}")

    if args.debrief:
        learner["last_debrief"] = args.debrief

    # The chat lane's half of the slip ledger. `last_debrief` above is prose and
    # is OVERWRITTEN every close by design (it is the running story); a mistake
    # recorded only there survives exactly as long as Anna keeps retyping it.
    # This is the accumulating half — same ledger the knock judge writes to, so
    # a slip made at the table and a slip made on the phone are one history.
    # (parsed once, up at the gate — the gate and the writer must see one list)
    if slip_rows:
        channel = (learner.get("soak_order") or {}).get("channel", "")
        written = append_slips(slip_rows, lane="chat", modality="session",
                               dose_channel=channel)
        for row in written:
            print(f"  Slip logged: {row['tag']} — “{row['said']}” → “{row['want']}”")
        for p in slip_patterns():
            if p["pattern"] and p["live"] and p["tag"] in {r["tag"] for r in written}:
                print(f"  ⚠ {p['tag']} is now {p['count']}× over {p['span_days']}d "
                      f"— it is a pattern, not a one-off.")

    # The other half of the loop: a slip he was deliberately TESTED on. Capture
    # says what broke; this says whether it healed — and without it a slip can
    # only ever age out on the clock, which cannot distinguish "he learned it"
    # from "nothing asked him".
    for tag, outcome, msg in record_slip_test(getattr(args, "slip_tested", None) or []):
        mark = {"landed": "✓", "missed": "✗", "bad": "!"}[outcome]
        print(f"  {mark} slip {tag}: {msg}")

    # Which debt does the order just set actually PAY? Declared, never inferred:
    # a payload word and a slip tag are different vocabularies, and the slips
    # that most need a dose (1pl-past-om, past-tense) hang off no single word.
    # Reads the order from `learner` as mutated above, so setting the order and
    # naming its debt in ONE close works — which is the only ergonomic worth
    # having here (2026-07-31, Andrew's option A).
    for tag, msg in record_slip_commission(getattr(args, "slip_commissioned", None) or [],
                                           learner.get("soak_order") or {}):
        mark = "✓" if msg.startswith("commissioned") else "!"
        print(f"  {mark} slip {tag}: {msg}")

    # Both writers above persist straight to LEARNER_PATH, but this function is
    # holding a `learner` read BEFORE they ran and write_thin_learner rebuilds
    # the file from it — so without this re-read the close or commission is
    # erased by the very call that made it. That is exactly how slip_closes was
    # lost silently for a day (2026-07-30 → 07-31).
    fresh = load_json(LEARNER_PATH) or {}
    for book in ("slip_closes", "slip_commissions"):
        if fresh.get(book):
            learner[book] = fresh[book]

    # No streak bookkeeping — recency comes from the session log, and a stored
    # streak is a meter that lies the moment a day is skipped (Enjoyment Clause).
    learner.pop("streak", None)

    # Focus cohort — stored membership, reconciled only here and at the judge
    # seam: leave on graduation, enter on seat-open (2026-07-26).
    from suggest_targets import reconcile_focus  # lazy: suggest_targets imports us
    old_cohort = learner.get("focus_cohort", [])
    learner["focus_cohort"] = reconcile_focus(lexicon, old_cohort)
    left = sorted(set(old_cohort) - set(learner["focus_cohort"]))
    entered = sorted(set(learner["focus_cohort"]) - set(old_cohort))
    if left or entered:
        print(f"  Focus cohort: -{left or '[]'} +{entered or '[]'}"
              f" ({len(learner['focus_cohort'])} seats held)")

    save_json(LEXICON_PATH, lexicon)
    if episodes:
        save_json(EPISODES_PATH, episodes)
    write_thin_learner(learner, episodes)

    floor = compute_floor(lexicon)
    engines = compute_engines(lexicon)

    # Momentum log — ONE entry per session-day that did something.
    #
    # It used to append unconditionally, so every extra `update` call in a close
    # forged a session: repairing a bad key, or setting the soak order in a
    # second command, each minted a row. 38 rows for 26 real days by 2026-07-31
    # — 12 duplicated dates, the counter ~46% high, and the last-5 view in
    # show_status padded with near-empty rows. Worse, cold_fires_recent() and
    # fires_today() SUM word lists across entries, so a word logged twice in one
    # close inflated the trailing pace the burn rate is computed from.
    # Merging restores the documented contract instead of adding a guard on top.
    if applied["cold"] or applied["hinted"] or applied["demoted"] or args.listened or args.debrief:
        log = load_json(SESSION_LOG_PATH) or []
        entry = log[-1] if log and log[-1].get("date") == today else None
        if entry is None:
            entry = {"date": today, "cold": [], "hinted": [], "demoted": [],
                     "listened": [], "note": ""}
            log.append(entry)
        # Union, not concatenate — the same word re-logged is one fire, not two.
        for field, values in (("cold", applied["cold"]), ("hinted", applied["hinted"]),
                              ("demoted", applied["demoted"]), ("listened", list(args.listened))):
            have = entry.setdefault(field, [])
            have.extend(v for v in values if v not in have)
        # Percentages are a snapshot: the latest call is the truest.
        entry["floor_pct"] = round(floor["pct"], 1)
        entry["engines_pct"] = round(engines["pct"], 1)
        # The debrief is rewritten whole and cumulatively by Anna, so a later
        # one supersedes rather than appends. An update that carries no debrief
        # must never blank the one already written.
        if args.debrief:
            entry["note"] = args.debrief
        save_json(SESSION_LOG_PATH, log)
        print(f"  Logged session ({len(log)} total)")

    print(f"\nViability floor: {floor['cleared']}/{floor['total']} fire cold ({floor['pct']:.0f}%)")
    if engines["total"]:
        print(f"Engines online: {engines['online']}/{engines['total']} ({engines['pct']:.0f}%)")
    deck = compute_deck(lexicon)
    if deck["total"]:
        catch = f" · catch {deck['caught']}/{deck['catch_total']} solid" if deck["catch_total"] else ""
        print(f"Trip Deck: {deck['surv_cleared']}/{deck['surv_total']} survival cold · "
              f"full deck {deck['cleared']}/{deck['total']}{catch}")
        if deck["untouched"]:
            print(f"  ⚠ Coverage: {deck['untouched']} fire item(s) never worked "
                  f"({deck['surv_untouched']} survival)")
    print(f"Fired today: {fires_today()}")
    print("State updated.")


def cmd_add_pattern(args):
    """Seed a generative pattern/lemma record into the lexicon. Patterns are
    tracked on the same axes as words but metered separately (Engines). Movement
    afterward reuses the normal flags, e.g. `update --produced-cold '<key>'` the
    day the learner generates a NOVEL instance of the pattern unaided."""
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:
        print("Error: lexicon.json missing. See BOOTSTRAP.md.")
        sys.exit(1)
    if args.key in lexicon:
        print(f"  ! '{args.key}' already exists — not overwriting. Move its axes with `update`.")
        return
    today = date.today().isoformat()
    lexicon[args.key] = {
        "type": "pattern",
        "gloss": args.gloss,
        "phonetic": [],
        "recognition": args.recognition,
        "production": "none",
        "seen_in": [],
        "last_surfaced": today,
    }
    save_json(LEXICON_PATH, lexicon)
    print(f"  + Pattern '{args.key}' seeded — {args.gloss}")
    print(f"    (recognition {args.recognition}, production none)")
    print(f"    Log a cold novel instance later with:  update --produced-cold '{args.key}'")


def cmd_add_word(args):
    """Seed a word/chunk record with its gloss and phonetics in one shot — the
    proper birth of a new lexicon entry (update --comfortable-word creates
    gloss-less stubs; soak orders don't create records at all). Without a record,
    a word can never be resolved, scored, or surface on a ticket."""
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:
        print("Error: lexicon.json missing. See BOOTSTRAP.md.")
        sys.exit(1)
    if not is_tamil(args.key):
        print(f"  ! '{args.key}' isn't Tamil script — records must be canonical script.")
        sys.exit(1)
    if args.key in lexicon:
        rec = lexicon[args.key]
        if args.gloss and not rec.get("gloss"):
            rec["gloss"] = args.gloss
        for phon in args.phonetic:
            if phon not in rec.setdefault("phonetic", []):
                rec["phonetic"].append(phon)
        save_json(LEXICON_PATH, lexicon)
        print(f"  '{args.key}' already exists — merged gloss/phonetics, learning state untouched.")
        return
    lexicon[args.key] = {
        "gloss": args.gloss,
        "phonetic": list(args.phonetic),
        "recognition": args.recognition,
        "production": "none",
        "seen_in": [],
        "last_surfaced": date.today().isoformat(),
    }
    save_json(LEXICON_PATH, lexicon)
    print(f"  + '{args.key}' — {args.gloss} (recognition {args.recognition}, phonetic {list(args.phonetic)})")


def cmd_seed_deck(args):
    """Idempotently load a curated deck file (e.g. curriculum/trip_deck.json) into
    the lexicon, tagging each entry `deck: <name>`. The deck file is CONTENT (Anna
    drafts it, the Oracle vets it); this command is the MECHANISM that lands it —
    the same LLM-writes / Python-owns-state split as word_pool.json.

    Each deck entry: {"tamil", "gloss", "phonetic": [...], "type": "chunk"|"frame",
    "recognition"?, "direction"?: "fire"|"catch", "pairs_with"?}. A "frame" is stored as a lexicon
    `pattern` (an Engine); a "chunk" is word-like (counts in the viability floor).
    "catch" marks ear-only items (cleared by recognition, never forced to fire);
    "pairs_with" names the chunk that answers it — hear X → say Y, validated to
    resolve inside the same file so a pair can never be silently split.
    Re-runnable and the file is the source of truth: existing entries get the deck
    tag + direction + any missing gloss/phonetic without clobbering their learning
    state; new entries are created; lexicon entries tagged with this deck but no
    longer in the file are un-tagged (their learning state stays)."""
    path = Path(args.file)
    if not path.is_absolute():
        path = BASE / path
    entries = load_json(path)
    if entries is None:
        print(f"Error: deck file not found: {path}")
        sys.exit(1)
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:
        print("Error: lexicon.json missing. See BOOTSTRAP.md.")
        sys.exit(1)
    today = date.today().isoformat()
    # `pairs_with` is the ONE relation the schema carries: a catch item names the
    # chunk Andrew must say back to it (hear X → say Y). It lives on the catch
    # side because that is the direction of the drill, and it must resolve inside
    # the same file — an unresolvable pair is a SPLIT pair, which is exactly the
    # failure it exists to prevent (2026-07-26: the maami's "eat more" kept its
    # deck slot while its refusal was dropped, and nothing could notice). A split
    # pair refuses the whole seed BEFORE any write: fix the file, re-run.
    in_file = {e.get("tamil") for e in entries}
    split = [(e.get("tamil"), e.get("pairs_with")) for e in entries
             if e.get("pairs_with") and e["pairs_with"] not in in_file]
    if split:
        for tamil, pair in split:
            print(f"  ✗ '{tamil}' pairs_with '{pair}', which is not in this deck — split pair.")
        print("  Error: seed refused, nothing written. A pair must resolve inside the file.")
        sys.exit(1)
    created = updated = 0
    for e in entries:
        tamil = e.get("tamil")
        if not tamil:
            print(f"  ! deck entry missing 'tamil' — skipped: {e}")
            continue
        pair = e.get("pairs_with")
        lex_type = "pattern" if e.get("type") == "frame" else e.get("type", "chunk")
        # Chunks/words must be canonical Tamil script; frames use the `frame:...`
        # key convention (like add-pattern), so they're exempt from the script check.
        if lex_type != "pattern" and not is_tamil(tamil):
            print(f"  ! '{tamil}' isn't Tamil script — chunks must be canonical script. Skipped.")
            continue
        if tamil in lexicon:
            rec = lexicon[tamil]
            rec["deck"] = args.deck
            rec["direction"] = e.get("direction", "fire")
            rec.setdefault("type", lex_type)
            if pair:
                rec["pairs_with"] = pair
            else:
                rec.pop("pairs_with", None)  # the file is the source of truth
            if e.get("gloss"):
                rec["gloss"] = e["gloss"]  # deck file is the curated content source — its gloss wins
            for phon in e.get("phonetic", []):
                if phon not in rec.setdefault("phonetic", []):
                    rec["phonetic"].append(phon)
            updated += 1
        else:
            lexicon[tamil] = {
                "type": lex_type,
                "gloss": e.get("gloss", ""),
                "phonetic": e.get("phonetic", []),
                "recognition": e.get("recognition", "comfortable"),
                "production": "none",
                "seen_in": [],
                "last_surfaced": None,
                "deck": args.deck,
                "direction": e.get("direction", "fire"),
                **({"pairs_with": pair} if pair else {}),
            }
            created += 1
    # The deck file is the source of truth: un-tag lexicon entries that left it.
    pruned = []
    for w, rec in lexicon.items():
        if rec.get("deck") == args.deck and w not in in_file:
            del rec["deck"]
            rec.pop("direction", None)
            rec.pop("pairs_with", None)
            pruned.append(w)
    save_json(LEXICON_PATH, lexicon)
    deck = compute_deck(lexicon, args.deck)
    print(f"  Seeded deck '{args.deck}': +{created} new, {updated} re-tagged, {len(pruned)} un-tagged.")
    for w in pruned:
        print(f"    - un-tagged (stays in lexicon): {w}")
    print(f"  Trip Deck now: {deck['cleared']}/{deck['total']} fire cold ({deck['pct']:.0f}%)"
          + (f" · catch {deck['caught']}/{deck['catch_total']} solid" if deck["catch_total"] else ""))


def git_sync_counts() -> tuple[int, int] | None:
    """(behind, ahead) of origin/main after a fetch, or None when it can't be
    known (offline, no git, not a clone). The clone is ONE OF MANY writers —
    cloud Anna (knocks, judged replies, scheduled pushes) commits to main all
    day — so status must know whether it's reading today's story or yesterday's."""
    try:
        subprocess.run(["git", "fetch", "--quiet", "origin", "main"],
                       cwd=BASE, timeout=20, capture_output=True, check=True)
        out = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"],
            cwd=BASE, timeout=10, capture_output=True, text=True, check=True).stdout
        ahead, behind = (int(x) for x in out.split())
        return behind, ahead
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError):
        return None


def sync_banner(counts: tuple[int, int] | None) -> str | None:
    """The staleness gate's voice — printed ABOVE everything else in the digest
    so no agent can read state past it. 2026-07-15: a session opened on a clone
    14 commits behind and re-collected a paid field mission, missed the morning
    trailer, and taught past the story. Pull-before-read is design, not hygiene."""
    if counts is None:
        return ("⚠ SYNC UNKNOWN — couldn't reach origin. If this machine has been "
                "offline or idle, this digest may be stale; reconnect and `git pull "
                "--ff-only` before trusting it.")
    behind, ahead = counts
    lines = []
    if behind:
        lines.append(f"⛔ STATE IS STALE — {behind} commit{'s' if behind != 1 else ''} "
                     f"behind origin/main. STOP: run `git pull --ff-only` (or rebase if "
                     f"diverged) and re-run status. Everything below may be yesterday's story.")
    if ahead:
        lines.append(f"⚠ {ahead} local commit{'s' if ahead != 1 else ''} not on origin — "
                     f"push after the session close, or cloud Anna knocks on stale state.")
    return "\n".join(lines) or None


def knocks_since(klog: list, last_session: str | None, cap: int = 6) -> list[dict]:
    """Knock-log entries on/after the last logged session date, newest last —
    the between-session story the debrief alone can't carry (replies, fires,
    and trailers land on origin while the laptop sleeps)."""
    if not klog:
        return []
    entries = [k for k in klog if not last_session or k.get("date", "") >= last_session]
    return entries[-cap:]


def knock_line(k: dict) -> str:
    """One digest line per knock: what went out, what came back."""
    body = (k.get("body") or "").replace("\n", " ")
    if len(body) > 90:
        body = body[:87] + "…"
    if k.get("reply"):
        n = len(k.get("exchanges", [])) or 1
        reply = k["reply"].replace("\n", " ")
        if len(reply) > 40:
            reply = reply[:37] + "…"
        back = f"→ {n} repl{'ies' if n != 1 else 'y'}, last: '{reply}' ({k.get('reply_verdict', '?')})"
        fired = k.get("reply_fired_cold") or []
        if fired:
            back += f" · fired COLD: {', '.join(fired)}"
        # What Anna actually CORRECTED, not just that a reply happened. Until
        # 2026-07-30 this line stopped at the verdict, so a session opened knowing
        # Andrew replied and it was "hinted" with no idea what was wrong — the
        # correction sat in reply_line, read back only by the reveal-window and
        # deck-coverage scans. That is how the same recast could ship three times
        # in three weeks and look like normal progress.
        recasts = [x.get("reply_line", "") for x in k.get("exchanges", [])] or \
                  [k.get("reply_line", "")]
        recasts = [r.split(" · ")[0].strip() for r in recasts if r]
        if recasts:
            back += "\n      corrected: " + " | ".join(r[:88] for r in recasts[-2:])
    elif k.get("response"):
        back = f"→ {k['response']}"
    else:
        back = "→ (no response yet)"
    return f"  {k.get('date', '?')} [{k.get('modality', '?')}] {k.get('move', '?')} — \"{body}\" {back}"


def unpaid_trailer(klog: list, last_session: str | None) -> dict | None:
    """The newest knock, if it's a trailer whose promised teach no session has
    paid off yet (no session logged on/after its date). daily_session.md: an
    outstanding trailer's payoff IS the opening beat — this makes that rule
    data the agent can't overlook."""
    if not klog:
        return None
    k = klog[-1]
    if "trailer" not in (k.get("move") or "").lower():
        return None
    if last_session and last_session >= k.get("date", ""):
        return None
    return k


def cmd_status(_args):
    lexicon = load_json(LEXICON_PATH)
    learner = load_json(LEARNER_PATH)
    episodes = load_json(EPISODES_PATH) or {}
    if not learner:
        print("No learner.json found.")
        return

    banner = sync_banner(git_sync_counts())
    if banner:
        print(banner)
        print()

    # Anna is time-aware at inference: every load path reads this line, so "ping
    # me in an hour" / "tonight at 9" can become a real scheduled push (push_queue.py).
    print(f"Now: {datetime.now(LOCAL_TZ):%a %Y-%m-%d %H:%M %Z}")
    print(f"Learner: {learner.get('learner')}")
    # No streak theatre — the honest signal is recency (a scoreboard that lies
    # teaches the player to ignore all the meters).
    slog = load_json(SESSION_LOG_PATH) or []
    last = slog[-1].get("date") if slog else None
    gap = (date.today() - date.fromisoformat(last)).days if last else None
    if last:
        gap_str = "today" if not gap else f"{gap} day{'s' if gap != 1 else ''} ago"
        print(f"Last logged session: {last} ({gap_str})")
    print(f"Status: {compute_status()}")  # live — the stored learner.json copy goes stale between updates
    print(f"Story so far: {learner.get('last_debrief', '')}")
    next_engine = learner.get("next_engine", "")
    if next_engine and lexicon:
        r = lexicon.get(next_engine, {})
        prod = r.get("production", "none")
        if prod != "cold":
            gloss = r.get("gloss", "")
            unseen = is_unseen(r)
            tag = "UNSEEN — teach first" if unseen else f"production: {prod}"
            print(f"Next engine: {next_engine} — {gloss}  [{tag}]")

    soak = learner.get("soak_order", {})
    if soak.get("payload") or soak.get("scene_seed"):
        items = canon_payload(soak.get("payload", []))
        soak_from = soak.get("from")
        soak_age = (date.today() - date.fromisoformat(soak_from)).days if soak_from else None
        stale = " ⚠ stale — chat hasn't fed the Director lately" if soak_age and soak_age > 7 else ""
        # The auto-drain answer, computed — not left to the agent's eye: has the
        # newest episode carried this payload yet? Resolved the same way the
        # watchdog resolves it (split_payload), because these two checks drive
        # the SAME dispatch from two doors — the session-open drain and the
        # cron. On 2026-07-23 only the cron's copy was fixed and this one kept
        # saying NOT YET PRODUCED, which would have re-armed the loop at the
        # next session. One rule, one resolver.
        resolved, unresolved = split_payload(soak.get("payload", []), lexicon)
        newest_words = (episodes[max(episodes, key=int)].get("words", [])
                        if episodes else [])
        channel = soak.get("channel") or "episode"
        lane = {"soak": "python scripts/render_soak.py",
                "drill": "python scripts/render_drill.py"}.get(
                    channel, "python scripts/run_studio.py")
        if channel == "episode":
            produced = bool(resolved) and all(w in newest_words for w in resolved)
        else:
            # The soak and drill lanes register no episode, so the newest-episode
            # compare can NEVER clear them — that is the 2026-07-23 re-dispatch
            # loop (M72/M73/M74 in one evening) with a new trigger. The lane that
            # rendered the order stamps it delivered (mark_soak_delivered); an
            # earlier version of this check read last_surfaced instead and hung
            # forever on a pre-lexicon payload word, which is the same loop.
            deliv = soak.get("delivered") or {}
            produced = (deliv.get("channel") == channel
                        and (deliv.get("at") or "") >= (soak_from or ""))
        if unresolved:
            drain = (f" · ⚠ payload unverifiable ({', '.join(unresolved)}) — fix the soak "
                     f"order; NOT dispatching on an item that can never match")
        elif produced:
            drain = f" · produced ✓ (the {channel} lane carried it — no dispatch needed)"
        else:
            drain = (f" · ⚠ NOT YET PRODUCED — dispatch `{lane}` in the background now "
                     f"(session-open auto-drain)")
        focus = f" · focus: {soak['focus']}" if soak.get("focus") else ""
        print(f"Soak order [{channel}]: [{', '.join(items)}] — {soak.get('scene_seed', '')}"
              f"{focus} (from {soak.get('from', '?')}){stale}{drain}")
    else:
        print("Soak order: ⚠ none set — chat hasn't handed anything to the Director.")

    # The between-session story — what the phone channel did while no laptop was
    # open. The debrief is Anna's memory of the last CLOSE; these are the doses
    # and replies SINCE. Re-collecting something listed here as answered is the
    # bug this section exists to prevent (2026-07-15).
    klog = load_json(KNOCK_LOG_PATH) or []
    since = knocks_since(klog, last)
    if since:
        print(f"\nKnocks since last logged session ({len(since)} shown — replies here are already judged; don't re-collect):")
        for k in since:
            print(knock_line(k))
    trailer = unpaid_trailer(klog, last)
    if trailer:
        body = (trailer.get("body") or "").replace("\n", " ")
        print(f"🎬 UNPAID TRAILER: \"{body}\" — its promised teach OPENS the session (pay it off in the first two exchanges).")

    # The error memory, ahead of the meters. A word being not-yet-cold says it
    # needs another rep; a repeated slip says HOW the rep keeps failing, which is
    # the difference between re-asking the same thing the same way and teaching
    # the thing that is actually broken.
    slip_block = format_slip_block(slip_patterns())
    if slip_block:
        print()
        for line in slip_block:
            print(line)
    print()

    if lexicon:
        by_level = {lvl: 0 for lvl in RECOGNITION_LEVELS}
        cold = hinted = 0
        for r in lexicon.values():
            if is_pattern(r):
                continue  # patterns are metered separately (Engines)
            by_level[r.get("recognition", "struggled")] = by_level.get(r.get("recognition", "struggled"), 0) + 1
            if r.get("production") == "cold":
                cold += 1
            elif r.get("production") == "hinted":
                hinted += 1
        print(f"Recognition — solid: {by_level['solid']}, comfortable: {by_level['comfortable']}, struggled: {by_level['struggled']}")
        print(f"Production — cold: {cold}, hinted: {hinted}")
        floor = compute_floor(lexicon)
        print(f"Viability floor: {floor['cleared']}/{floor['total']} recognized words fire cold ({floor['pct']:.0f}%)")
        engines = compute_engines(lexicon)
        if engines["total"]:
            print(f"Engines online: {engines['online']}/{engines['total']} patterns fire cold ({engines['pct']:.0f}%)")
        deck = compute_deck(lexicon)
        if deck["total"]:
            catch = f" · catch {deck['caught']}/{deck['catch_total']} solid" if deck["catch_total"] else ""
            print(f"Trip Deck: {deck['cleared']}/{deck['total']} deck phrases fire cold ({deck['pct']:.0f}%){catch} — the sprint headline")
            if deck["untouched"] or deck["catch_untouched"]:
                ear = f" + {deck['catch_untouched']} ear-only" if deck["catch_untouched"] else ""
                print(f"  ⚠ Coverage: {deck['untouched']} fire item(s){ear} never worked "
                      f"({deck['surv_untouched']} of them survival tier) — see the ticket for the register breakdown.")
                print("    ENGINEERING NUMBER — steers what Python picks; never narrated to Andrew "
                      "(a global deficit recited in a warm voice is guilt machinery, 2026-07-17).")
        print(f"Fired today: {fires_today()}")

    if episodes:
        recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:6]
        print("\nRecent episodes (immersion tank — no listen bookkeeping; each is a self-contained dose):")
        for m, ep in recent:
            dur = ep.get("duration_min")
            dur_str = f" ({dur:.1f} min)" if dur else ""
            print(f"  M{m}: {ep.get('title', m)}{dur_str}")


# Knock tap responses (from Home Assistant's actionable notification). Both are
# SOAK-tier signals — they record that the knock landed and let the nudge gate
# back off; neither touches the production/viability floor (that only flips when
# Anna witnesses an unaided cold fire in chat). 'listened' additionally credits
# the soak: it bumps the latest published episode's listens + surfaces its words.
#   ack      — "got it / played the memo"      → knock marked landed, no learning write
#   listened — "I listened to the episode"     → knock marked landed + episode soak credit
KNOCK_RESPONSES = {"ack", "listened"}
# A later tap may only *upgrade* an earlier one (strictly more signal); same-or-less is a no-op.
KNOCK_UPGRADES = {None: KNOCK_RESPONSES, "ack": {"listened"}}


def credit_latest_episode_listen() -> str | None:
    """Soak credit for a 'listened' tap. 'Latest published' = the highest mission
    key in episodes.json (the newest one in the feed). Mirrors `update --listened`,
    but a tap can't name a mission so it always credits the newest episode.
    Returns a one-line summary, or None if there's nothing to credit."""
    episodes = load_json(EPISODES_PATH) or {}
    if not episodes:
        return None
    mission = max(episodes, key=int)
    ep = episodes[mission]
    lexicon = load_json(LEXICON_PATH) or {}
    learner = load_json(LEARNER_PATH) or {}
    phon_index = build_phonetic_index(lexicon)
    today = date.today().isoformat()
    ep["listens"] = ep.get("listens", 0) + 1
    surfaced = 0
    for w in ep.get("words", []):
        key = resolve(w, lexicon, phon_index)
        if key:
            lexicon[key]["last_surfaced"] = today
            surfaced += 1
    save_json(EPISODES_PATH, episodes)
    save_json(LEXICON_PATH, lexicon)
    write_thin_learner(learner, episodes)  # refresh recent_missions + status line
    return f"M{mission} '{ep.get('title', mission)}' now {ep['listens']}x — surfaced {surfaced} words"


def cmd_knock_response(args):
    """Record Andrew's tap response against the most recent knock.
    Called by the log-knock-response GitHub Actions workflow when HA fires the event.
    Idempotent: a duplicate tap is a no-op, but 'listened' may upgrade a prior 'ack'."""
    from datetime import datetime
    response = args.response.strip().lower()
    if response not in KNOCK_RESPONSES:
        print(f"  Unknown knock response '{response}' (expected one of {sorted(KNOCK_RESPONSES)}). Skipping.")
        return
    log = load_json(KNOCK_LOG_PATH) or []
    # Only FIRED reaches can be tapped; silence entries (acted=False) carry no
    # notification, so skip them and mark the most recent actual knock.
    fired = [k for k in log if k.get("acted", True)]
    if not fired:
        print("No fired knocks in knock_log.json to respond to.")
        sys.exit(1)
    # Notifications stack (2026-07-11): a tap carries its knock's timestamp as
    # knock_id, so an old notification acks the right entry. No id → last fired.
    kid = (getattr(args, "knock_id", "") or "").strip()
    last = next((k for k in reversed(fired) if k.get("timestamp") == kid), None) if kid else None
    if last is None:
        if kid:
            print(f"  ⚠ knock_id {kid!r} not in the log — marking the most recent knock")
        last = fired[-1]
    prior = last.get("response")
    if prior is not None and response not in KNOCK_UPGRADES.get(prior, set()):
        print(f"  Most recent knock ({last['date']}) already '{prior}'; '{response}' adds nothing. Skipping.")
        return

    last["response"] = response
    last["response_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # 'listened' is the only response that credits a soak (the episode, not the knock).
    if response == "listened":
        summary = credit_latest_episode_listen()
        if summary:
            last["episode_credit"] = summary
            print(f"  Listened → {summary}")
        else:
            print("  Listened, but no episodes in episodes.json to credit.")

    save_json(KNOCK_LOG_PATH, log)
    print(f"  Knock {last['date']} marked '{response}'")


_TAG_RE = re.compile(r"[^a-z0-9]+")


def canon_tag(s: str) -> str:
    """Normalise a slip tag to a stable slug. The JUDGE names the pattern (it owns
    the morphology — same seam as the fired-word contract); Python only makes the
    name comparable, so 'Past tense' and 'past-tense' are one row and not two.

    Deliberately NOT a closed vocabulary. A fixed enum would force every new error
    into a pre-imagined bucket and silently mislabel the ones that matter most —
    the whole point of the ledger is to show a pattern nobody named in advance.
    The cost is drift (two slugs for one pattern), which is visible in the summary
    and cheap for Anna to merge; the cost of an enum is invisible and is not."""
    return _TAG_RE.sub("-", (s or "").strip().casefold()).strip("-")


def parse_slip_args(raw_specs: list[str]) -> list[dict]:
    """CLI `--slip 'tag|said|want|note'` specs → ledger rows. Shared by the
    close's writer AND the commission gate, which must judge the same rows the
    close is about to append — a slip whose second occurrence lands in this very
    close becomes a pattern the gate already has to see."""
    rows = []
    for raw in raw_specs:
        parts = [p.strip() for p in raw.split("|")]
        if not parts or not parts[0]:
            print(f"  ! --slip {raw!r} has no tag before the first '|' — skipped")
            continue
        parts += [""] * (4 - len(parts))
        rows.append({"tag": parts[0], "said": parts[1],
                     "want": parts[2], "note": parts[3]})
    return rows


def append_slips(entries: list[dict], lane: str, modality: str = "",
                 dose_channel: str = "", when: str = "") -> list[dict]:
    """Append structured errors to the slip ledger. THE LEDGER IS APPEND-ONLY —
    nothing here ever rewrites or prunes a row.

    That is the whole reason this file exists rather than a field on learner.json:
    the system's existing error memory was `last_debrief`, a single string
    OVERWRITTEN on every close (2026-07-30 audit), so a mistake survived only as
    long as Anna retyped it. It also never crossed lanes — `daily_session.md`
    drew repairs from "the day's" chat session, and knock corrections lived only
    as prose in knock_log.json that nothing read back. Result: 'romba nalla
    irukku' → 'irundhuchu' was corrected on 07-08, 07-25 and 07-30, near-verbatim,
    with no mechanism able to notice.

    `dose_channel` is the channel of the soak order live when the slip happened —
    the counter behind audio_channels.md's "the same mistake twice through one
    format is that format's answer." That law shipped 2026-07-28 with nothing
    counting formats, so it could never fire.

    `when` overrides the stamped date. Spans and recurrence are computed from it,
    so it must be the date the mistake was MADE, not the date it was recorded: a
    reply typed at 9pm local is judged after midnight UTC on the runner, and
    `date.today()` there files it under tomorrow — the same local-vs-UTC seam
    apply_verdict already handles with `today_local` for capped fires."""
    if not entries:
        return []
    log = load_json(SLIP_LOG_PATH) or []
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    today = when or datetime.now(LOCAL_TZ).date().isoformat()
    # Resolve `want` to a lexicon key here, once, so every caller gets the same
    # answer and the ticket can hang a slip off the floor-gap row it belongs to.
    # An unresolvable want is normal and fine — a slip about an ENDING often has
    # no single word behind it, and the tag carries the meaning regardless.
    lexicon = load_json(LEXICON_PATH) or {}
    phon_index = build_phonetic_index(lexicon)
    written = []
    for e in entries:
        tag = canon_tag(e.get("tag", ""))
        if not tag:
            continue
        if not e.get("word"):
            e = dict(e, word=resolve(e.get("want", ""), lexicon, phon_index) or "")
        row = {
            "at": now,
            "date": today,
            "lane": lane,
            "modality": modality,
            "tag": tag,
            "said": (e.get("said") or "").strip(),
            "want": (e.get("want") or "").strip(),
            "note": (e.get("note") or "").strip(),
            "word": (e.get("word") or "").strip(),
        }
        if dose_channel:
            row["dose_channel"] = dose_channel
        log.append(row)
        written.append(row)
    if written:
        save_json(SLIP_LOG_PATH, log)
    return written


def slip_closes() -> dict[str, str]:
    """tag → the date it was last observed LANDING. Read-side of the only way a
    slip closes: somebody watched him fire it right, unaided, later.

    Stored dated, never as a bare tag. `slips_closed` (a flat list of names,
    2026-07-30, removed the same day) made closing permanent and unfalsifiable —
    a tag on that list could never be live again no matter how often he missed
    it. A date can be voided by a later failure; a name cannot."""
    raw = (load_json(LEARNER_PATH) or {}).get("slip_closes") or {}
    return {canon_tag(k): v for k, v in raw.items() if v}


def slip_commissions() -> dict[str, list[dict]]:
    """tag → the doses built to pay that debt: [{channel, at, payload}, …].

    The missing link (2026-07-31, Andrew). `dose_channel` is stamped onto a slip
    ROW at the instant it is written, from whatever order happened to be standing
    — so `channels` answered "has he ever slipped while SOME order stood", never
    "was a dose built for THIS". Commissioning the right dose could not clear
    NEVER COMMISSIONED; only slipping again could. The flag was cleared by
    failing and ignored by fixing, which is why it became noise to read past.

    Stored like `slip_closes`: on the learner, keyed by canonical tag, dated.
    A list rather than one entry, because trying a SECOND format is exactly the
    event `audio_channels.md`'s escalation law needs to see."""
    raw = (load_json(LEARNER_PATH) or {}).get("slip_commissions") or {}
    return {canon_tag(k): list(v) for k, v in raw.items() if v}


def record_slip_commission(tags: list[str], order: dict,
                           today: str = "") -> list[tuple[str, str]]:
    """Declare that the standing soak order pays off these slip tags.

    The seam that does the work declares it — the same law as the delivery stamp
    (`mark_soak_delivered`) and the exposure stamp. Python cannot infer this: a
    payload word and a slip tag are different vocabularies, and guessing the link
    from word overlap would be a silent wrong answer on exactly the ending-shaped
    slips (1pl-past-om, past-tense) that hang off no single word."""
    today = today or datetime.now(LOCAL_TZ).date().isoformat()
    if not tags:
        return []
    channel = (order or {}).get("channel") or ""
    payload = list((order or {}).get("payload") or [])
    learner = load_json(LEARNER_PATH) or {}
    book = dict(learner.get("slip_commissions") or {})
    out = []
    known = {p["tag"] for p in slip_patterns()}
    for raw in tags:
        tag = canon_tag(raw)
        if not tag:
            out.append((raw, "expected a slip tag"))
            continue
        if not channel:
            out.append((tag, "no soak order is standing — set one in this same call"))
            continue
        # A tag with no ledger history is a typo, and silently booking a
        # commission against it would mark a debt paid that never existed.
        if tag not in known:
            out.append((tag, "no slip logged under that tag — check the spelling"))
            continue
        entries = list(book.get(tag) or [])
        entries.append({"channel": channel, "at": today, "payload": payload})
        book[tag] = entries
        out.append((tag, f"commissioned via the {channel} lane"))
    learner["slip_commissions"] = book
    save_json(LEARNER_PATH, learner)
    return out


def record_slip_test(results: list[str], today: str = "") -> list[tuple[str, str, str]]:
    """Log the OUTCOME of putting a retired slip to the test: 'tag:landed' or
    'tag:missed'. This is the observation the ledger's own standard demands —
    "a slip is not closed by being corrected; it is closed by firing right,
    unaided, later" — and it is the half that never existed, so nothing could
    ever close except by hand, permanently, on Anna's say-so.

    landed → a dated close. missed → a slip row, because a failed test IS a
    recurrence: it revives the tag, bumps the count, and keeps one ledger rather
    than a second parallel record of the same event.

    Word-anchored slips could in principle close themselves off the lexicon
    going cold; ending-shaped ones (1pl-past-om, past-tense) hang off no row and
    cannot. Rather than build two close paths with different guarantees, both go
    through this one and Anna reports. The weaker guarantee is stated out loud
    in the protocol: this asserts an OBSERVATION, not a verdict."""
    today = today or datetime.now(LOCAL_TZ).date().isoformat()
    learner = load_json(LEARNER_PATH) or {}
    closes = dict(learner.get("slip_closes") or {})
    out, missed = [], []
    for raw in results:
        tag, _, outcome = (raw or "").rpartition(":")
        tag, outcome = canon_tag(tag), outcome.strip().lower()
        if not tag or outcome not in ("landed", "missed"):
            out.append((raw, "bad", "expected 'tag:landed' or 'tag:missed'"))
            continue
        if outcome == "landed":
            closes[tag] = today
            out.append((tag, "landed", f"closed as of {today} — revives if it comes back"))
        else:
            closes.pop(tag, None)
            missed.append({"tag": tag, "said": "", "want": "",
                           "note": "tested and missed — still not landed"})
            out.append((tag, "missed", "still live; the failed test is on the ledger"))
    if missed:
        append_slips(missed, lane="chat", modality="test", when=today)
    learner["slip_closes"] = closes
    learner.pop("slips_closed", None)   # the bare-tag list this replaces
    save_json(LEARNER_PATH, learner)
    return out


def slip_patterns(log: list | None = None, today=None) -> list[dict]:
    """Aggregate the ledger by tag, newest-recurrence first. The MENU, not the
    choice — Python counts and groups; Anna reads the group and decides what it
    means and what to do about it (the 2026-06-17 division of labour).

    Returns one row per tag: how often, over how long, in which lanes, through
    which dose channels, and whether it is still live. `escalate` marks the case
    the channel law cares about — recurred, and every attempt so far went through
    ONE format."""
    log = load_json(SLIP_LOG_PATH) if log is None else log
    log = log or []
    today = today or date.today()
    closes = slip_closes()
    commissions = slip_commissions()
    by_tag: dict[str, dict] = {}
    for row in log:
        tag = row.get("tag")
        if not tag:
            continue
        agg = by_tag.setdefault(tag, {
            "tag": tag, "count": 0, "first": row.get("date"), "last": row.get("date"),
            "lanes": [], "channels": [], "words": [], "examples": [], "notes": [],
            # rows that carry a legacy dose_channel: a slip made WHILE an order
            # stood, which is the pre-2026-07-31 evidence that a dose existed.
            "dosed_rows": [],
        })
        if row.get("dose_channel"):
            agg["dosed_rows"].append((row.get("date") or "", row["dose_channel"],
                                      row.get("lane") or ""))
        agg["count"] += 1
        # first/last are MIN/MAX over the rows, not first-seen/last-seen. The
        # ledger is append-only but not guaranteed date-ordered: append_slips
        # takes a `when` override precisely so a slip is filed under the day the
        # mistake was MADE, and the 07-30 seeding backfilled three weeks of
        # history in one write. A last-seen `last` collapses the span and
        # inflates days_quiet, which can retire a slip that is still live.
        if row.get("date") and row["date"] > (agg["last"] or ""):
            agg["last"] = row["date"]
        if row.get("date") and row["date"] < (agg["first"] or row["date"]):
            agg["first"] = row["date"]
        for key, field in (("lanes", "lane"), ("channels", "dose_channel"), ("words", "word")):
            v = row.get(field)
            if v and v not in agg[key]:
                agg[key].append(v)
        if row.get("said") or row.get("want"):
            agg["examples"].append((row.get("date"), row.get("said", ""), row.get("want", "")))
        if row.get("note") and row["note"] not in agg["notes"]:
            agg["notes"].append(row["note"])

    out = []
    for agg in by_tag.values():
        try:
            days_quiet = (today - date.fromisoformat(agg["last"])).days
        except (TypeError, ValueError):
            days_quiet = 0
        agg["days_quiet"] = days_quiet
        agg["span_days"] = _span_days(agg["first"], agg["last"])
        # A close is DATED, and a failure after it voids it. That is the whole
        # difference between retiring a pattern and losing it: "he landed it on
        # 08-20" is a claim about 08-20, not about all future time, so a slip
        # that comes back on 09-02 is live again with its history intact. The
        # bare-tag close this replaces (2026-07-30, removed same day) silenced a
        # tag permanently — which muted the single most informative event the
        # ledger can record: a pattern you believed had landed, coming back.
        closed_on = closes.get(agg["tag"], "")
        agg["closed_on"] = closed_on if closed_on and closed_on >= (agg["last"] or "") else ""
        agg["closed"] = bool(agg["closed_on"])
        agg["reopened"] = bool(closed_on) and not agg["closed"]
        agg["live"] = not agg["closed"] and days_quiet <= SLIP_RETIRE_DAYS
        agg["pattern"] = agg["count"] >= SLIP_PATTERN_COUNT
        # RETIRED but never confirmed: quiet long enough to stop being evidence,
        # yet nothing ever observed him getting it right. Silence has two causes
        # — he learned it, or nothing ever asked him — and the ledger cannot tell
        # them apart, so it must not pretend. This surfaces as a re-eligible
        # CHECK rather than vanishing (Andrew, 2026-07-30: "words shouldn't
        # disappear into the aether; they should be retired and then come back").
        # Passive by design: it asks for a test, it does not earn a commission.
        agg["unverified"] = (agg["pattern"] and not agg["live"]
                             and not agg["closed"])
        # Two different failures, two different instructions. NEVER COMMISSIONED
        # means he has been corrected in passing and nothing was ever built for
        # it — the fix is to commission anything at all. ESCALATE means a dose
        # was built, through one format, and he slipped again anyway — that is
        # the audio_channels law, and telling it to "change format" when no
        # format was ever tried would be advice for a problem he doesn't have.
        # Doses DECLARED for this tag (2026-07-31), merged with the legacy
        # dose_channel stamps so "which formats have been tried" is one answer.
        agg["commissions"] = sorted(commissions.get(agg["tag"], []),
                                    key=lambda c: c.get("at") or "")
        for c in agg["commissions"]:
            if c.get("channel") and c["channel"] not in agg["channels"]:
                agg["channels"].append(c["channel"])
        agg["uncommissioned"] = agg["pattern"] and agg["live"] and not agg["channels"]
        # ESCALATE means a dose was built and he slipped ANYWAY — so it needs a
        # slip dated after a dose existed, not merely a dose and a live tag. A
        # legacy dose_channel row qualifies by construction (the order stood when
        # that slip was made); a declared commission has to be beaten by a later
        # slip. Without this, commissioning a debt today would instantly accuse
        # the new dose of having failed, on evidence that predates it.
        dosed_since = min(
            [c["at"] for c in agg["commissions"] if c.get("at")]
            + [d for d, _, _ in agg.get("dosed_rows", [])] or [""]) or ""
        agg["slipped_after_dose"] = bool(dosed_since) and (agg["last"] or "") > dosed_since
        agg["escalate"] = (agg["pattern"] and agg["live"]
                           and len(agg["channels"]) == 1
                           and (agg["slipped_after_dose"] or bool(agg.get("dosed_rows"))))
        out.append(agg)
    # Live first, then the unverified rechecks, then everything settled.
    out.sort(key=lambda a: (a["live"] and a["pattern"], a["unverified"],
                            a["last"] or "", a["count"]), reverse=True)
    return out


def _span_days(first: str, last: str) -> int:
    try:
        return (date.fromisoformat(last) - date.fromisoformat(first)).days
    except (TypeError, ValueError):
        return 0


def format_slip_block(patterns: list[dict], limit: int = 6) -> list[str]:
    """Render repeated slips for a reader surface. One renderer, three callers
    (status, the knock context, the ticket) — the 07-26 quiet-hours argument:
    four copies of a rule means one of them is the gap, and the gap is the lane
    that fires.

    Two sections, because they carry two different instructions. LIVE is
    evidence and earns a dose. UNVERIFIED is a question — it has gone quiet
    without anyone ever seeing him get it right, and the only honest thing to do
    with it is test it."""
    live = [p for p in patterns if p["live"] and p["pattern"]]
    unverified = [p for p in patterns if p["unverified"]]
    if not live and not unverified:
        return []
    lines = []
    if not live:
        lines.append("No live slips — nothing repeated recently.")
    else:
        lines += ["REPEATED SLIPS — mistakes he has made more than once, newest first.",
                  "  These are the primary signal for what to drill. A slip is not closed by",
                  "  being corrected; it is closed by firing right, unaided, later."]
    for p in live[:limit]:
        when = (f"{p['count']}× over {p['span_days']}d" if p["span_days"]
                else f"{p['count']}×")
        quiet = f", last {p['days_quiet']}d ago" if p["days_quiet"] else ", today"
        lines.append(f"  ⚠ {p['tag']} — {when}{quiet}")
        for d, said, want in p["examples"][-2:]:
            lines.append(f"      {d}: said “{said}” → wanted “{want}”")
        if p["notes"]:
            lines.append(f"      pattern: {p['notes'][-1]}")
        if p.get("commissions"):
            c = p["commissions"][-1]
            lines.append(f"      ✓ dose commissioned {c.get('at','')} "
                         f"({c.get('channel','?')} lane"
                         + (f": {', '.join(c['payload'])}" if c.get("payload") else "")
                         + ") — don't re-order it; test whether it landed.")
        if p["uncommissioned"]:
            # The instruction names the exact flag, because the flag is the only
            # thing that can turn this warning off and prose has already failed
            # here once: daily_session.md sits at its word ceiling and
            # audio_channels.md had a third raise refused in advance, so the
            # place to say it is where the agent is already looking. Same law as
            # the 07-23 scheduling detector — when prose has been walked past,
            # the mechanism carries the rule (2026-07-31).
            lines.append("      ⚠ NEVER COMMISSIONED — corrected in passing every "
                         "time and no dose was ever built for it. This one is owed "
                         "a soak order, not another recast.")
            lines.append(f"        → order it, then DECLARE it in the same close: "
                         f"--soak-payload … --slip-commissioned {p['tag']}")
        elif p["escalate"]:
            lines.append(f"      ⚠ ESCALATE — a {p['channels'][0]} dose was built "
                         f"for this and he slipped again. audio_channels.md: change "
                         f"the format, never loop harder.")
    if len(live) > limit:
        lines.append(f"  … {len(live) - limit} more live slip(s) behind these")
    if unverified:
        lines.append("")
        lines.append("RETIRED BUT UNVERIFIED — quiet, and never once confirmed landed.")
        lines.append("  Silence here has two causes and the ledger cannot tell them apart:")
        lines.append("  he learned it, or nothing ever asked him. Worth a CHECK, not a dose —")
        lines.append("  slip it into a scene and see. Report with --slip-tested tag:landed|missed.")
        for p in unverified[:limit]:
            ago = f"{p['days_quiet']}d quiet" if p["days_quiet"] else "today"
            lines.append(f"  ○ {p['tag']} — {p['count']}× to {p['last']}, {ago}"
                         + ("  · came back after a close" if p["reopened"] else ""))
            for d, said, want in p["examples"][-1:]:
                lines.append(f"      {d}: said “{said}” → wanted “{want}”")
            if p["notes"]:
                lines.append(f"      pattern: {p['notes'][-1]}")
        if len(unverified) > limit:
            lines.append(f"  … {len(unverified) - limit} more unverified behind these")
    return lines


def cmd_slips(args):
    """Read the slip ledger (aggregated), or close a tag by name.

    Capture is NOT here: slips are written by the judge that saw the mistake
    (knock_reply.py) and by `update --slip` at session close, both through
    append_slips(). Reading is the common case — this is Anna's error memory."""
    if args.tested:
        for tag, outcome, msg in record_slip_test(args.tested):
            mark = {"landed": "✓", "missed": "✗", "bad": "!"}[outcome]
            print(f"  {mark} {tag}: {msg}")
        return

    patterns = slip_patterns()
    if not patterns:
        print("No slips logged yet.")
        return
    live = [p for p in patterns if p["live"] and p["pattern"]]
    unver = [p for p in patterns if p["unverified"]]
    print(f"SLIP LEDGER ({sum(p['count'] for p in patterns)} slips, "
          f"{len(patterns)} patterns, {len(live)} live, {len(unver)} awaiting a check):")
    for p in patterns[:args.n]:
        state = ("LIVE" if p["live"] and p["pattern"] else
                 f"closed {p['closed_on']}" if p["closed"] else
                 "UNVERIFIED" if p["unverified"] else
                 "quiet" if not p["live"] else "once")
        print(f"\n  [{state}] {p['tag']} — {p['count']}× "
              f"({p['first']} → {p['last']}, {p['span_days']}d span)")
        if p["lanes"]:
            print(f"        lanes: {', '.join(p['lanes'])}"
                  + (f" · dose channels tried: {', '.join(p['channels'])}"
                     if p["channels"] else " · no dose ever commissioned for it"))
        for d, said, want in p["examples"][-3:]:
            print(f"        {d}: “{said}” → “{want}”")
        if p["notes"]:
            print(f"        pattern: {p['notes'][-1]}")
        for c in p.get("commissions", []):
            print(f"        ✓ dose commissioned {c.get('at','')} via the "
                  f"{c.get('channel','?')} lane"
                  + (f" — {', '.join(c['payload'])}" if c.get("payload") else ""))
        if p["uncommissioned"]:
            print("        ⚠ NEVER COMMISSIONED — owed a dose, not another recast.")
        elif p["escalate"]:
            print(f"        ⚠ ESCALATE — {p['channels'][0]} was tried; change format.")
        if p["unverified"]:
            print("        ○ never confirmed landed — test it, then --tested "
                  f"{p['tag']}:landed|missed")
        if p["reopened"]:
            print("        ⚠ CAME BACK after being closed — the loudest signal here.")


def cmd_feedback(args):
    """Capture (append a dated note) or read (list recent) the feedback ledger.
    Feeds the Diagnosis pass (protocol/diagnosis.md): Anna proposes fixes from
    REPRODUCED patterns, never one-offs — capture is cheap, change is not."""
    log = load_json(FEEDBACK_LOG_PATH) or []
    if args.note:
        log.append({"date": date.today().isoformat(), "note": args.note})
        save_json(FEEDBACK_LOG_PATH, log)
        print(f"  Logged feedback ({len(log)} total): {args.note}")
        return
    if not log:
        print("No feedback logged yet.")
        return
    print(f"FEEDBACK LEDGER ({len(log)} entries) — diagnose patterns, not one-offs:")
    for e in log[-args.n:]:
        print(f"  {e['date']}  {e['note']}")


def cmd_migrate_session_log(args):
    """One-time repair of rows minted before the same-day merge landed (2026-07-31).

    Until today the momentum log appended on every `update`, so a close split
    across several calls — repairing a key, setting the soak order separately,
    rewriting a debrief — wrote one row per CALL. 38 rows for 19 real
    session-days: the log read exactly double.

    Merging is lossless in the way that matters. Word lists union (and on this
    history no word appears in two rows of one day, so no count moves). The
    debrief is rewritten whole and cumulatively by Anna, so the last non-empty
    one supersedes rather than concatenating — that is the same rule the live
    path now follows. Meters are a snapshot: the last row that carries them wins.

    Previews by default; --apply writes. Deliberately NOT run by anything
    automatic — it edits the record of what Andrew actually did, which is his
    call to make once, not a repair that should quietly re-run."""
    log = load_json(SESSION_LOG_PATH) or []
    if not log:
        print("session_log.json is empty — nothing to migrate.")
        return

    merged, by_date = [], {}
    for row in log:
        d = row.get("date")
        if d not in by_date:
            # deepcopy, not dict(): a shallow copy shares the LIST objects with
            # the source row, so extending the merged row silently extended the
            # original too — and the before/after conservation check below then
            # compared the mutated history against itself and reported phantom
            # duplicates. Caught on this migration's first dry run.
            import copy
            by_date[d] = copy.deepcopy(row)
            merged.append(by_date[d])
            continue
        into = by_date[d]
        for field in ("cold", "hinted", "demoted", "listened"):
            have = into.setdefault(field, [])
            have.extend(v for v in row.get(field, []) if v not in have)
        for meter in ("floor_pct", "engines_pct"):
            if row.get(meter) is not None:
                into[meter] = row[meter]
        if row.get("note"):
            into["note"] = row["note"]

    dupes = len(log) - len(merged)
    print(f"session_log.json: {len(log)} rows over {len(merged)} session-days "
          f"({dupes} forged by multi-call closes)")
    if not dupes:
        print("  nothing to do.")
        return

    # Prove the merge conserves the numbers anything downstream reads.
    for field in ("cold", "hinted", "demoted"):
        before = sum(len(r.get(field, [])) for r in log)
        after = sum(len(r.get(field, [])) for r in merged)
        flag = "" if before == after else f"  ⚠ {before - after} duplicate(s) collapsed"
        print(f"  {field:<8} {before} → {after}{flag}")
    lost = sum(1 for r in log if r.get("note")) - sum(1 for r in merged if r.get("note"))
    print(f"  {'debriefs':<8} {sum(1 for r in log if r.get('note'))} → "
          f"{sum(1 for r in merged if r.get('note'))}"
          f"{'' if not lost else f'  ({lost} superseded — the last of each day is kept)'}")

    if not args.apply:
        print("\n  DRY RUN — nothing written. Re-run with --apply to commit the change.")
        print("  (git holds the current file; `git checkout -- progress/session_log.json` reverts.)")
        return
    save_json(SESSION_LOG_PATH, merged)
    print(f"\n  ✅ written — {len(merged)} rows, one per session-day.")


def main():
    parser = argparse.ArgumentParser(description="Tamil learning state management")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show current state")

    up = sub.add_parser("update", help="Update state after a session")
    up.add_argument("--listened", type=int, action="append", default=[],
                    help="Mission number(s) the learner listened to (bumps listens + surfaces words)")
    up.add_argument("--soak-payload", type=str, action="append", default=[],
                    help="Word(s) to soak in the next audio episode (the Director's payload)")
    up.add_argument("--soak-seed", type=str, default=None,
                    help="One-line scene seed for the next audio soak")
    up.add_argument("--soak-focus", type=str, default=None,
                    help="What the next dose PERMUTES, free text ('the -ஆச்சு tail over "
                         "போ and முடி') — a carousel brief, not a word list")
    up.add_argument("--soak-channel", type=str, default=None,
                    choices=["episode", "soak", "drill"],
                    help="Which lane renders the order (default: episode). Capacity "
                         "routes this, never the curriculum — protocol/audio_channels.md")
    # Deferred import: suggest_targets imports THIS module, so a module-level
    # import would be circular. The palette has one owner either way.
    from suggest_targets import ALL_FORMS, COMMISSIONED_FORMS
    up.add_argument("--soak-form", type=str, default=None, choices=ALL_FORMS,
                    help=f"Commission an episode FORM instead of letting the divergence "
                         f"gate roll one. {'/'.join(COMMISSIONED_FORMS)} can ONLY arrive "
                         f"this way; the rest are normally spec-rotated and this pins them.")
    up.add_argument("--teach", type=str, action="append", default=[],
                    metavar="WORD[=GLOSS]",
                    help="Word(s) TAUGHT this session — creates the lexicon record at "
                         "`struggled` recognition, seen today, production unset. The "
                         "entry path the Teach Beat and lore tangent never had; Tamil "
                         "script only, so the key stays canonical.")
    up.add_argument("--mastered-word", type=str, action="append", default=[],
                    help="Word(s) now solid in recognition")
    up.add_argument("--comfortable-word", type=str, action="append", default=[],
                    help="Word(s) now comfortable in recognition")
    up.add_argument("--stuck-word", type=str, action="append", default=[],
                    help="Word(s) that failed cold recall — demotes recognition one level")
    up.add_argument("--produced-cold", type=str, action="append", default=[],
                    help="Word(s) produced COLD — no hint (production axis)")
    up.add_argument("--produced-hinted", type=str, action="append", default=[],
                    help="Word(s) produced only after a hint (production axis)")
    up.add_argument("--debrief", type=str, default=None,
                    help="Running 'story so far' — rewrite cumulatively (carry what matters, prune what resolved); Anna's persistent narrative memory, not a one-line log")
    up.add_argument("--next-engine", type=str, default=None,
                    help="Frame key to set as the engine to unlock next (e.g. 'frame:polite-nga')")
    up.add_argument("--mark-seen", type=str, action="append", default=[],
                    help="Frame/word key(s) to mark as seen today (sets last_surfaced; closes lore-memo gap)")
    up.add_argument("--slip", type=str, action="append", default=[],
                    help="A mistake worth remembering: 'tag|what he said|what it should be|the pattern in one clause'. "
                         "Repeatable. Appends to the slip ledger — never overwrites. The knock judge writes these "
                         "itself; this is the chat lane's half, so a session mistake accumulates the same way.")
    up.add_argument("--slip-tested", type=str, action="append", default=[], metavar="TAG:landed|missed",
                    help="Report an UNVERIFIED slip you deliberately tested this session. 'landed' closes it as of "
                         "today (a later miss revives it); 'missed' logs the failure and keeps it live. Only for a "
                         "slip you actually put in his mouth unaided — it asserts an observation, not a verdict.")
    up.add_argument("--slip-commissioned", type=str, action="append", default=[], metavar="TAG",
                    help="Declare that the soak order set in THIS call pays off that slip tag. Repeatable. "
                         "Without it a dose cannot clear NEVER COMMISSIONED — nothing links a payload word to a "
                         "tag, so the flag would stay on for ever no matter what was built. Only for a dose that "
                         "genuinely targets the pattern; it says a debt was ordered, never that it landed "
                         "(that is --slip-tested).")
    up.add_argument("--no-commission", type=str, default=None, metavar="REASON", dest="no_commission",
                    help="Close despite a live uncommissioned slip pattern, with the reason on the record. "
                         "Without this (or a --slip-commissioned covering the debt) the gate REFUSES the "
                         "close and writes nothing (2026-08-01, Andrew's call).")

    ap = sub.add_parser("add-pattern", help="Seed a generative pattern/lemma record (tracked as an Engine)")
    ap.add_argument("key", help="Canonical key, e.g. 'frame:present-future-toggle'")
    ap.add_argument("--gloss", required=True,
                    help="Human description of the engine, e.g. '-உறேன் (now) vs -வேன் (later) on any verb'")
    ap.add_argument("--recognition", default="comfortable", choices=RECOGNITION_LEVELS,
                    help="Starting recognition level (default: comfortable)")

    aw = sub.add_parser("add-word", help="Seed a word/chunk record (gloss + phonetics) — a word without a record can't be resolved or scored")
    aw.add_argument("key", help="Canonical Tamil script, e.g. 'என்ன சமைக்கிற?'")
    aw.add_argument("--gloss", required=True, help="English gloss")
    aw.add_argument("--phonetic", action="append", default=[],
                    help="Phonetic spelling(s) Andrew might type (repeatable)")
    aw.add_argument("--recognition", default="comfortable", choices=RECOGNITION_LEVELS,
                    help="Starting recognition level (default: comfortable)")

    sd = sub.add_parser("seed-deck", help="Load a curated deck file (chunks/frames) into the lexicon, tagged with a deck name")
    sd.add_argument("file", help="Path to the deck JSON (e.g. curriculum/trip_deck.json), absolute or repo-relative")
    sd.add_argument("--deck", default="trip", help="Deck name to tag entries with (default: trip)")

    kr = sub.add_parser("knock-response", help="Log Andrew's tap response against its knock (by --knock-id; most recent if absent)")
    kr.add_argument("response", help="The tap value: 'ack' (got it) or 'listened' (heard the episode → soak credit)")
    kr.add_argument("--knock-id", default="", dest="knock_id",
                    help="The knock's log timestamp (from the notification's action_data); empty → most recent")

    fb = sub.add_parser("feedback", help="Append a feedback note (capture), or list recent (diagnosis)")
    fb.add_argument("note", nargs="?", default=None, help="The feedback to log; omit to list recent")
    fb.add_argument("-n", type=int, default=20, help="How many recent entries to show when listing")

    sl = sub.add_parser("slips", help="Read the slip ledger (what Andrew keeps getting wrong), or report a test")
    sl.add_argument("-n", type=int, default=15, help="How many patterns to show")
    sl.add_argument("--tested", action="append", default=[], metavar="TAG:landed|missed",
                    help="Report the outcome of putting a slip to the test. 'landed' closes it AS OF TODAY "
                         "(a later miss revives it, history intact); 'missed' logs the failure and keeps it live. "
                         "This asserts an observation — that he fired it right unaided — not a verdict.")

    ml = sub.add_parser("migrate-session-log",
                        help="One-time repair: collapse same-day momentum rows minted by "
                             "multi-call closes (2026-07-31). Previews unless --apply.")
    ml.add_argument("--apply", action="store_true",
                    help="Actually write. Without it this only reports what would change.")

    args = parser.parse_args()
    if args.command == "update":
        cmd_update(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "add-pattern":
        cmd_add_pattern(args)
    elif args.command == "add-word":
        cmd_add_word(args)
    elif args.command == "seed-deck":
        cmd_seed_deck(args)
    elif args.command == "feedback":
        cmd_feedback(args)
    elif args.command == "slips":
        cmd_slips(args)
    elif args.command == "knock-response":
        cmd_knock_response(args)
    elif args.command == "migrate-session-log":
        cmd_migrate_session_log(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
