#!/usr/bin/env python3
"""
State management for the Tamil learning system.

Word-state lives in ONE place: progress/lexicon.json — a word-keyed map where each
record carries both axes (recognition + production), its phonetics, provenance, and
last-surfaced date. This script owns all writes to it. The LLM (Anna) calls
`update` at the end of a session to record what it observed.

  progress/lexicon.json     → word-state (this file's domain)
  progress/learner.json     → continuity: streak, debrief, soak order, status (thin, LLM-facing)
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
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"
LEARNER_PATH = BASE / "progress" / "learner.json"
EPISODES_PATH = BASE / "progress" / "episodes.json"
SESSION_LOG_PATH = BASE / "progress" / "session_log.json"
FEEDBACK_LOG_PATH = BASE / "progress" / "feedback_log.json"
KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
AUDIO_DIR = BASE / "audio"

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


def is_pattern(rec: dict) -> bool:
    """A pattern/lemma record is a generative structure (e.g. the present/future
    toggle), tracked on the same axes as a word but metered separately."""
    return rec.get("type") == "pattern"


def compute_floor(lexicon: dict) -> dict:
    """The viability floor: of the WORDS recognized (comfortable+solid),
    how many fire cold? This is the one honest word-level progress meter.
    Patterns are excluded — they get their own Engines meter."""
    recognized = [w for w, r in lexicon.items()
                  if not is_pattern(r) and r.get("recognition") in RECOGNIZED]
    cleared = [w for w in recognized if lexicon[w].get("production") == "cold"]
    total = len(recognized)
    pct = (len(cleared) / total * 100) if total else 0.0
    return {"cleared": len(cleared), "total": total, "pct": pct}


def compute_engines(lexicon: dict) -> dict:
    """The engine meter: of the tracked generative patterns, how many fire cold —
    i.e. the learner can produce a NOVEL instance unaided? Reported separately
    from the word-level viability floor so neither muddies the other."""
    patterns = [w for w, r in lexicon.items() if is_pattern(r)]
    online = [w for w in patterns if lexicon[w].get("production") == "cold"]
    total = len(patterns)
    pct = (len(online) / total * 100) if total else 0.0
    return {"online": len(online), "total": total, "pct": pct}


def compute_deck(lexicon: dict, deck: str = "trip") -> dict:
    """A named deck is a finite, deadline-driven set (e.g. the India-trip survival
    phrases) tagged `deck: "<name>"`. Its meter is the headline during a sprint:
    of the deck's members, how many fire cold? Members are counted regardless of
    type — a chunk fires cold when said whole, a frame when a novel slot-fill lands.
    Anna narrates the countdown to the deadline (Python counts; Anna narrates)."""
    members = [w for w, r in lexicon.items() if r.get("deck") == deck]
    cleared = [w for w in members if lexicon[w].get("production") == "cold"]
    total = len(members)
    pct = (len(cleared) / total * 100) if total else 0.0
    return {"cleared": len(cleared), "total": total, "pct": pct}


# --- Episode helpers (progress/episodes.json — a flat {id: episode} map) ------

def find_mission_file(directory: Path, mission: int, extension: str) -> Path | None:
    matches = list(directory.glob(f"*mission{mission}{extension}"))
    return matches[0] if matches else None


def get_episode_duration(mission: int) -> float | None:
    path = find_mission_file(AUDIO_DIR, mission, ".mp3")
    if path is None:
        return None
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True
        )
        d = json.loads(result.stdout)
        return float(d["format"]["duration"]) / 60
    except Exception:
        return None


def compute_status(episodes: dict) -> str:
    under = [(int(m), ep.get("listens", 0)) for m, ep in episodes.items()
             if ep.get("listens", 0) < 3]
    under.sort(key=lambda x: x[0], reverse=True)
    under = under[:8]
    if not under:
        return "Ready for new episode."
    if len(under) <= 2:
        return f"{len(under)} recent episodes under-listened. New episode OK, but re-listen playlist recommended."
    total_min = sum(get_episode_duration(m) or 3.0 for m, _ in under)
    return f"{len(under)} episodes under-listened (~{total_min:.0f} min). Re-listen playlist recommended before new production."


def compute_recent_missions(episodes: dict, n: int = 4) -> list[dict]:
    recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:n]
    return [{"mission": int(m), "title": ep.get("title", f"Mission {m}"),
             "listens": ep.get("listens", 0)} for m, ep in recent]


def write_thin_learner(learner: dict, episodes: dict):
    thin = {
        "learner": learner.get("learner", "Andrew"),
        "streak": learner.get("streak", {}),
        "last_debrief": learner.get("last_debrief", ""),
        "soak_order": learner.get("soak_order", {}),
        "recent_missions": compute_recent_missions(episodes),
        "status": compute_status(episodes),
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

    # Soak order — the intentional payload for the NEXT audio episode (what Anna
    # wants soaked), read by the Director. Overwrites; fail-forward, no history.
    if args.soak_payload or args.soak_seed:
        payload = [resolve(w, lexicon, phon_index) or w for w in args.soak_payload]
        learner["soak_order"] = {
            "payload": payload,
            "scene_seed": args.soak_seed or learner.get("soak_order", {}).get("scene_seed", ""),
            "from": today,
        }
        print(f"  Soak order set: {', '.join(payload) or '(seed only)'}")

    if args.debrief:
        learner["last_debrief"] = args.debrief

    streak = learner.get("streak", {})
    if streak.get("last_date") != today:
        streak["current"] = streak.get("current", 0) + 1
        streak["best"] = max(streak.get("best", 0), streak["current"])
        streak["last_date"] = today
        learner["streak"] = streak

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
        print(f"Trip Deck: {deck['cleared']}/{deck['total']} fire cold ({deck['pct']:.0f}%)")
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


def cmd_seed_deck(args):
    """Idempotently load a curated deck file (e.g. curriculum/trip_deck.json) into
    the lexicon, tagging each entry `deck: <name>`. The deck file is CONTENT (Anna
    drafts it, the Oracle vets it); this command is the MECHANISM that lands it —
    the same LLM-writes / Python-owns-state split as word_pool.json.

    Each deck entry: {"tamil", "gloss", "phonetic": [...], "type": "chunk"|"frame",
    "recognition"?}. A "frame" is stored as a lexicon `pattern` (an Engine); a
    "chunk" is word-like (counts in the viability floor). Re-runnable as the deck
    grows: existing entries get the deck tag + any missing gloss/phonetic without
    clobbering their learning state; new entries are created."""
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
            rec.setdefault("type", lex_type)
            if not rec.get("gloss") and e.get("gloss"):
                rec["gloss"] = e["gloss"]
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
            }
            created += 1
    save_json(LEXICON_PATH, lexicon)
    deck = compute_deck(lexicon, args.deck)
    print(f"  Seeded deck '{args.deck}': +{created} new, {updated} re-tagged.")
    print(f"  Trip Deck now: {deck['cleared']}/{deck['total']} fire cold ({deck['pct']:.0f}%)")


def cmd_status(_args):
    lexicon = load_json(LEXICON_PATH)
    learner = load_json(LEARNER_PATH)
    episodes = load_json(EPISODES_PATH) or {}
    if not learner:
        print("No learner.json found.")
        return

    print(f"Learner: {learner.get('learner')}")
    last = learner.get("streak", {}).get("last_date")
    gap = (date.today() - date.fromisoformat(last)).days if last else None
    gap_str = f" (last active {gap} days ago)" if gap and gap > 1 else ""
    print(f"Streak: {learner.get('streak', {}).get('current', 0)} days{gap_str}")
    print(f"Status: {learner.get('status', 'unknown')}")
    print(f"Story so far: {learner.get('last_debrief', '')}")
    soak = learner.get("soak_order", {})
    if soak.get("payload") or soak.get("scene_seed"):
        payload = ", ".join(soak.get("payload", []))
        soak_from = soak.get("from")
        soak_age = (date.today() - date.fromisoformat(soak_from)).days if soak_from else None
        stale = " ⚠ stale — chat hasn't fed the Director lately" if soak_age and soak_age > 7 else ""
        print(f"Soak order: [{payload}] — {soak.get('scene_seed', '')} (from {soak.get('from', '?')}){stale}")
    else:
        print("Soak order: ⚠ none set — chat hasn't handed anything to the Director.")
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
            print(f"Trip Deck: {deck['cleared']}/{deck['total']} deck phrases fire cold ({deck['pct']:.0f}%) — the sprint headline")

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
    write_thin_learner(learner, episodes)  # refresh recent_missions + under-listened status
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
    if not log:
        print("No knocks in knock_log.json to respond to.")
        sys.exit(1)
    last = log[-1]
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

    ap = sub.add_parser("add-pattern", help="Seed a generative pattern/lemma record (tracked as an Engine)")
    ap.add_argument("key", help="Canonical key, e.g. 'frame:present-future-toggle'")
    ap.add_argument("--gloss", required=True,
                    help="Human description of the engine, e.g. '-உறேன் (now) vs -வேன் (later) on any verb'")
    ap.add_argument("--recognition", default="comfortable", choices=RECOGNITION_LEVELS,
                    help="Starting recognition level (default: comfortable)")

    sd = sub.add_parser("seed-deck", help="Load a curated deck file (chunks/frames) into the lexicon, tagged with a deck name")
    sd.add_argument("file", help="Path to the deck JSON (e.g. curriculum/trip_deck.json), absolute or repo-relative")
    sd.add_argument("--deck", default="trip", help="Deck name to tag entries with (default: trip)")

    kr = sub.add_parser("knock-response", help="Log Andrew's tap response against the most recent knock")
    kr.add_argument("response", help="The tap value: 'ack' (got it) or 'listened' (heard the episode → soak credit)")

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
