#!/usr/bin/env python3
"""
State management for the Tamil learning system.

This script is the single source of truth for progress data. The LLM calls
this after the @tutor debrief to update state and recompute recommendations.

Usage:
    # After debrief: record listens and recompute status
    python scripts/sync_state.py update --listens 3 --stuck-word "வை"

    # Show current state summary (what the LLM should read)
    python scripts/sync_state.py status

    # Migrate: one-time move from old learner.json to new split format
    python scripts/sync_state.py migrate
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent.parent
LEARNER_PATH = BASE / "progress" / "learner.json"
VOCAB_STATE_PATH = BASE / "progress" / "vocab_state.json"
AUDIO_DIR = BASE / "audio"
SCRIPTS_DIR = BASE / "content" / "scripts"


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_mission_file(directory: Path, mission: int, extension: str) -> Path | None:
    """Find a file for a given mission number, tier-agnostic."""
    matches = list(directory.glob(f"*mission{mission}{extension}"))
    return matches[0] if matches else None


def get_episode_duration(mission: int) -> float | None:
    """Get duration in minutes for a mission's audio file."""
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


def get_available_missions() -> list[int]:
    """Return sorted list of mission numbers that have audio."""
    missions = []
    for f in AUDIO_DIR.glob("*.mp3"):
        m = re.search(r"mission(\d+)\.mp3$", f.name)
        if m:
            missions.append(int(m.group(1)))
    return sorted(missions)


def scan_script_words(mission: int) -> list[str]:
    """Extract Tamil words from a mission script."""
    script_path = find_mission_file(SCRIPTS_DIR, mission, ".md")
    if not script_path:
        return []
    text = script_path.read_text(encoding="utf-8")
    words = re.findall(r"[\u0B80-\u0BFF]{2,}", text)
    return list(set(words))


def compute_status(vocab_state: dict) -> str:
    """Compute a one-line status for learner.json based on listen counts."""
    episodes = vocab_state.get("episodes", {})
    under_listened = []
    for mission_str, ep in episodes.items():
        listens = ep.get("listens", 0)
        if listens < 3:
            under_listened.append((int(mission_str), listens))

    # Only care about recent episodes (last 8)
    under_listened.sort(key=lambda x: x[0], reverse=True)
    under_listened = under_listened[:8]
    recent_under = [(m, l) for m, l in under_listened if l < 3]

    if not recent_under:
        return "Ready for new episode."
    elif len(recent_under) <= 2:
        return f"{len(recent_under)} recent episodes under-listened. New episode OK, but re-listen playlist recommended."
    else:
        total_min = sum(
            get_episode_duration(m) or 3.0 for m, _ in recent_under
        )
        return f"{len(recent_under)} episodes under-listened (~{total_min:.0f} min). Re-listen playlist recommended before new production."


def compute_recent_missions(vocab_state: dict, n: int = 4) -> list[dict]:
    """Build the recent_missions list for thin learner.json."""
    episodes = vocab_state.get("episodes", {})
    recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:n]
    result = []
    for mission_str, ep in recent:
        result.append({
            "mission": int(mission_str),
            "title": ep.get("title", f"Mission {mission_str}"),
            "listens": ep.get("listens", 0),
        })
    return result


def write_thin_learner(learner: dict, vocab_state: dict):
    """Rewrite learner.json as the thin LLM-facing file."""
    thin = {
        "learner": learner.get("learner", "Andrew"),
        "current_tier": learner.get("current_tier", 2),
        "active_mission": learner.get("active_mission", {}),
        "streak": learner.get("streak", {}),
        "last_debrief": learner.get("last_debrief", ""),
        "recent_missions": compute_recent_missions(vocab_state),
        "status": compute_status(vocab_state),
    }
    save_json(LEARNER_PATH, thin)
    print(f"  Updated learner.json ({LEARNER_PATH.relative_to(BASE)})")


def cmd_migrate(_args):
    """Migrate from old learner.json to new split format."""
    learner = load_json(LEARNER_PATH)
    if not learner:
        print("Error: No learner.json found.")
        sys.exit(1)

    # Build vocab_state from old learner.json
    vocab_state = {
        "mastered_words": learner.get("mastered_words", []),
        "comfortable_words": learner.get("comfortable_words", []),
        "struggled_words": learner.get("struggled_words", []),
        "total_sessions": learner.get("total_sessions", 0),
        "session_history": learner.get("sessions", []),
        "episodes": {},
    }

    # Initialize episodes from available audio
    missions = get_available_missions()
    for m in missions:
        # Guess listens: older = more listened. Recent = 1.
        session_missions = {s.get("mission") for s in learner.get("sessions", [])}
        listens = 1  # default: heard at least once if audio exists
        vocab_state["episodes"][str(m)] = {
            "title": f"Mission {m}",
            "listens": listens,
            "words": scan_script_words(m),
            "duration_min": get_episode_duration(m),
        }

    save_json(VOCAB_STATE_PATH, vocab_state)
    print(f"  Created vocab_state.json with {len(vocab_state['episodes'])} episodes")

    # Preserve last_debrief from old format
    last_mission = learner.get("last_mission", {})
    debrief = last_mission.get("debrief", "")

    learner["last_debrief"] = debrief
    write_thin_learner(learner, vocab_state)
    print("\nMigration complete.")


def cmd_update(args):
    """Update state after a debrief session."""
    learner = load_json(LEARNER_PATH)
    vocab_state = load_json(VOCAB_STATE_PATH)
    if not learner or not vocab_state:
        print("Error: Run 'sync_state.py migrate' first.")
        sys.exit(1)

    # Record listens on under-listened episodes (the ones that would be in a playlist)
    if args.listens and args.listens > 0:
        bumped = []
        for mission_str in sorted(vocab_state["episodes"].keys(), key=int, reverse=True):
            ep = vocab_state["episodes"][mission_str]
            if ep.get("listens", 0) < 3:
                ep["listens"] = ep.get("listens", 0) + args.listens
                bumped.append(mission_str)
        if bumped:
            print(f"  Added {args.listens} listen(s) to {len(bumped)} under-listened episodes (M{', M'.join(bumped)})")
        else:
            print(f"  No under-listened episodes to update")

    # Record stuck word
    if args.stuck_word:
        struggled = vocab_state.get("struggled_words", [])
        if args.stuck_word not in struggled:
            struggled.append(args.stuck_word)
            vocab_state["struggled_words"] = struggled
            print(f"  Added '{args.stuck_word}' to struggled words")

    # Update debrief
    if args.debrief:
        learner["last_debrief"] = args.debrief

    # Update streak
    streak = learner.get("streak", {})
    today = date.today().isoformat()
    if streak.get("last_date") != today:
        streak["current"] = streak.get("current", 0) + 1
        streak["best"] = max(streak.get("best", 0), streak["current"])
        streak["last_date"] = today
        learner["streak"] = streak

    save_json(VOCAB_STATE_PATH, vocab_state)
    write_thin_learner(learner, vocab_state)
    print("\nState updated.")


def cmd_status(_args):
    """Print current state for the LLM or the human."""
    learner = load_json(LEARNER_PATH)
    vocab_state = load_json(VOCAB_STATE_PATH)
    if not learner:
        print("No learner.json found.")
        return

    print(f"Learner: {learner.get('learner')}")
    print(f"Mission: {learner.get('active_mission', {}).get('mission', '?')}")
    print(f"Streak: {learner.get('streak', {}).get('current', 0)} days")
    print(f"Status: {learner.get('status', 'unknown')}")
    print()

    if vocab_state:
        words = vocab_state.get("mastered_words", [])
        comfortable = vocab_state.get("comfortable_words", [])
        struggled = vocab_state.get("struggled_words", [])
        print(f"Words — mastered: {len(words)}, comfortable: {len(comfortable)}, struggled: {len(struggled)}")

        episodes = vocab_state.get("episodes", {})
        recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:6]
        print(f"\nRecent episodes:")
        for m, ep in recent:
            listens = ep.get("listens", 0)
            dur = ep.get("duration_min")
            dur_str = f" ({dur:.1f} min)" if dur else ""
            print(f"  M{m}: {listens}x listened{dur_str}")


def main():
    parser = argparse.ArgumentParser(description="Tamil learning state management")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("migrate", help="One-time migration from old learner.json")
    sub.add_parser("status", help="Show current state")

    update_p = sub.add_parser("update", help="Update state after debrief")
    update_p.add_argument("--listens", type=int, default=0,
                          help="Number of re-listens since last session")
    update_p.add_argument("--stuck-word", type=str, default=None,
                          help="A word that tripped you up")
    update_p.add_argument("--debrief", type=str, default=None,
                          help="One-line debrief note")

    args = parser.parse_args()
    if args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
