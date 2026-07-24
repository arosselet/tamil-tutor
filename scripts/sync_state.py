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
  progress/session_log.json → append-only momentum log, one entry per session

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
    return {"cleared": len(cleared), "total": total, "pct": pct,
            "caught": len(caught), "catch_total": len(catch),
            "surv_cleared": sum(1 for w in surv if members[w].get("production") == "cold"),
            "surv_total": len(surv)}


# --- Episode helpers (progress/episodes.json — a flat {id: episode} map) ------

def compute_status() -> str:
    """The status line IS the scoreboard (post the 2026-06-30 listens pivot):
    the deck countdown during a sprint, the floor otherwise. Never a chore line —
    episodes are self-contained doses; nothing is ever 'under-listened'."""
    lexicon = load_json(LEXICON_PATH) or {}
    deck = compute_deck(lexicon)
    if deck["total"]:
        days = (TRIP_DATE - date.today()).days
        return (f"Trip Deck {deck['surv_cleared']}/{deck['surv_total']} survival cold · "
                f"{days} days to touchdown · "
                f"{burn_rate(deck['surv_total'] - deck['surv_cleared'], days)} · "
                f"full deck {deck['cleared']}/{deck['total']}")
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

    def touch(key):
        lexicon[key]["last_surfaced"] = today

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
            lexicon[key]["last_surfaced"] = today
            print(f"  Marked seen: {key}")
        else:
            print(f"  ! '{key}' not in lexicon — skipped")

    # Soak order — the intentional payload for the NEXT audio episode (what Anna
    # wants soaked), read by the Director. Overwrites; fail-forward, no history.
    if args.soak_payload or args.soak_seed:
        payload = [resolve(w, lexicon, phon_index) or w
                   for w in canon_payload(args.soak_payload)]
        learner["soak_order"] = {
            "payload": payload,
            "scene_seed": args.soak_seed or learner.get("soak_order", {}).get("scene_seed", ""),
            "from": today,
        }
        print(f"  Soak order set: {', '.join(payload) or '(seed only)'}")

    if args.debrief:
        learner["last_debrief"] = args.debrief

    # No streak bookkeeping — recency comes from the session log, and a stored
    # streak is a meter that lies the moment a day is skipped (Enjoyment Clause).
    learner.pop("streak", None)

    save_json(LEXICON_PATH, lexicon)
    if episodes:
        save_json(EPISODES_PATH, episodes)
    write_thin_learner(learner, episodes)

    floor = compute_floor(lexicon)
    engines = compute_engines(lexicon)

    # Append-only momentum log — one entry per session that did something.
    if applied["cold"] or applied["hinted"] or applied["demoted"] or args.listened or args.debrief:
        log = load_json(SESSION_LOG_PATH) or []
        log.append({
            "date": today,
            "floor_pct": round(floor["pct"], 1),
            "engines_pct": round(engines["pct"], 1),
            "cold": applied["cold"],
            "hinted": applied["hinted"],
            "demoted": applied["demoted"],
            "listened": list(args.listened),
            "note": args.debrief or "",
        })
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
    "recognition"?, "direction"?: "fire"|"catch"}. A "frame" is stored as a lexicon
    `pattern` (an Engine); a "chunk" is word-like (counts in the viability floor).
    "catch" marks ear-only items (cleared by recognition, never forced to fire).
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
    created = updated = 0
    for e in entries:
        tamil = e.get("tamil")
        if not tamil:
            print(f"  ! deck entry missing 'tamil' — skipped: {e}")
            continue
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
            }
            created += 1
    # The deck file is the source of truth: un-tag lexicon entries that left it.
    in_file = {e.get("tamil") for e in entries}
    pruned = []
    for w, rec in lexicon.items():
        if rec.get("deck") == args.deck and w not in in_file:
            del rec["deck"]
            rec.pop("direction", None)
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
        if unresolved:
            drain = (f" · ⚠ payload unverifiable ({', '.join(unresolved)}) — fix the soak "
                     f"order; NOT dispatching on an item that can never match")
        elif resolved and all(w in newest_words for w in resolved):
            drain = " · produced ✓ (newest episode carries it — no dispatch needed)"
        else:
            drain = " · ⚠ NOT YET PRODUCED — dispatch the studio in the background now (session-open auto-drain)"
        print(f"Soak order: [{', '.join(items)}] — {soak.get('scene_seed', '')} (from {soak.get('from', '?')}){stale}{drain}")
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
    elif args.command == "knock-response":
        cmd_knock_response(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
