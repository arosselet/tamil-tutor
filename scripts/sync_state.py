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


def compute_floor(lexicon: dict) -> dict:
    """The viability floor: of the words recognized (comfortable+solid),
    how many fire cold? This is the one honest progress meter."""
    recognized = [w for w, r in lexicon.items() if r.get("recognition") in RECOGNIZED]
    cleared = [w for w in recognized if lexicon[w].get("production") == "cold"]
    total = len(recognized)
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

    # Append-only momentum log — one entry per session that did something.
    if applied["cold"] or applied["hinted"] or applied["demoted"] or args.listened or args.debrief:
        log = load_json(SESSION_LOG_PATH) or []
        log.append({
            "date": today,
            "floor_pct": round(floor["pct"], 1),
            "cold": applied["cold"],
            "hinted": applied["hinted"],
            "demoted": applied["demoted"],
            "listened": list(args.listened),
            "note": args.debrief or "",
        })
        save_json(SESSION_LOG_PATH, log)
        print(f"  Logged session ({len(log)} total)")

    print(f"\nViability floor: {floor['cleared']}/{floor['total']} fire cold ({floor['pct']:.0f}%)")
    print("State updated.")


def cmd_status(_args):
    lexicon = load_json(LEXICON_PATH)
    learner = load_json(LEARNER_PATH)
    episodes = load_json(EPISODES_PATH) or {}
    if not learner:
        print("No learner.json found.")
        return

    print(f"Learner: {learner.get('learner')}")
    print(f"Streak: {learner.get('streak', {}).get('current', 0)} days")
    print(f"Status: {learner.get('status', 'unknown')}")
    print(f"Last: {learner.get('last_debrief', '')}")
    soak = learner.get("soak_order", {})
    if soak.get("payload") or soak.get("scene_seed"):
        payload = ", ".join(soak.get("payload", []))
        print(f"Soak order: [{payload}] — {soak.get('scene_seed', '')} (from {soak.get('from', '?')})")
    print()

    if lexicon:
        by_level = {lvl: 0 for lvl in RECOGNITION_LEVELS}
        cold = hinted = 0
        for r in lexicon.values():
            by_level[r.get("recognition", "struggled")] = by_level.get(r.get("recognition", "struggled"), 0) + 1
            if r.get("production") == "cold":
                cold += 1
            elif r.get("production") == "hinted":
                hinted += 1
        print(f"Recognition — solid: {by_level['solid']}, comfortable: {by_level['comfortable']}, struggled: {by_level['struggled']}")
        print(f"Production — cold: {cold}, hinted: {hinted}")
        floor = compute_floor(lexicon)
        print(f"Viability floor: {floor['cleared']}/{floor['total']} recognized words fire cold ({floor['pct']:.0f}%)")

    if episodes:
        recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:6]
        print("\nRecent episodes:")
        for m, ep in recent:
            dur = ep.get("duration_min")
            dur_str = f" ({dur:.1f} min)" if dur else ""
            print(f"  M{m}: {ep.get('listens', 0)}x listened{dur_str}")


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
    up.add_argument("--debrief", type=str, default=None, help="One-line debrief note")

    args = parser.parse_args()
    if args.command == "update":
        cmd_update(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
