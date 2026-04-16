#!/usr/bin/env python3
"""
Generate a CALLBACKS list for the next mission brief using spaced repetition.

Scans all existing scripts to count per-word appearances, then selects
words that are due for resurfacing based on a simple interval schedule:

  - Words seen 1x: resurface within next 2 missions
  - Words seen 2-3x: resurface within next 4 missions
  - Words seen 4x+: resurface within next 8 missions
  - Struggled words get priority regardless of interval

Usage:
    python scripts/generate_callbacks.py [--next-mission 39]

Output:
    Prints a CALLBACKS block ready to paste into a mission brief,
    and optionally updates progress/word_tracker.json.
"""

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
LEARNER_PATH = BASE / "progress" / "learner.json"
VOCAB_STATE_PATH = BASE / "progress" / "vocab_state.json"
TRACKER_PATH = BASE / "progress" / "word_tracker.json"
SCRIPTS_DIR = BASE / "content" / "scripts"
TIERS_DIR = BASE / "curriculum" / "tiers"


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Updated {path.relative_to(BASE)}")


def get_all_known_words(learner: dict) -> set[str]:
    """All words the learner has encountered (mastered + comfortable + struggled)."""
    words = set()
    words.update(learner.get("mastered_words", []))
    words.update(learner.get("comfortable_words", []))
    words.update(learner.get("struggled_words", []))
    return words


def get_tier_vocab(tier_num: int) -> dict[str, str]:
    """Return {tamil: english} for a tier."""
    for f in TIERS_DIR.glob(f"tier_{tier_num}_*.json"):
        data = load_json(f)
        if data:
            return {v["tamil"]: v["english"] for v in data.get("vocabulary", [])}
    return {}


def extract_mission_number(filename: str) -> int | None:
    """Extract mission number from a script filename."""
    m = re.search(r"mission(\d+)", filename)
    return int(m.group(1)) if m else None


def scan_scripts() -> dict[str, dict]:
    """
    Scan all scripts and count Tamil word appearances per mission.
    Returns: {tamil_word: {appearances: int, last_seen_mission: int, missions: [int]}}
    """
    tracker: dict[str, dict] = {}

    for script_path in sorted(SCRIPTS_DIR.glob("*.md")):
        mission_num = extract_mission_number(script_path.name)
        if mission_num is None:
            continue

        text = script_path.read_text(encoding="utf-8")

        # Find all Tamil character sequences (Unicode Tamil block: 0B80-0BFF)
        tamil_words = re.findall(r"[\u0B80-\u0BFF]+", text)

        seen_in_this_mission: set[str] = set()
        for word in tamil_words:
            if len(word) < 2:  # skip single characters / particles
                continue
            if word not in seen_in_this_mission:
                seen_in_this_mission.add(word)
                if word not in tracker:
                    tracker[word] = {
                        "appearances": 0,
                        "last_seen_mission": 0,
                        "missions": [],
                    }
                tracker[word]["appearances"] += 1
                tracker[word]["last_seen_mission"] = max(
                    tracker[word]["last_seen_mission"], mission_num
                )
                tracker[word]["missions"].append(mission_num)

    return tracker


def get_resurfacing_interval(appearances: int) -> int:
    """How many missions before this word should reappear."""
    if appearances <= 1:
        return 2
    elif appearances <= 3:
        return 4
    else:
        return 8


def generate_callbacks(
    next_mission: int,
    tracker: dict[str, dict],
    learner: dict,
    tier_vocab: dict[str, str],
    max_callbacks: int = 5,
) -> list[dict]:
    """
    Select words due for callback in the next mission.
    Priority: struggled > due-for-review > recently-mastered
    """
    struggled = set(learner.get("struggled_words", []))
    mastered = set(learner.get("mastered_words", []))
    comfortable = set(learner.get("comfortable_words", []))
    known = mastered | comfortable | struggled

    candidates: list[dict] = []

    for word in known:
        info = tracker.get(word, {"appearances": 0, "last_seen_mission": 0, "missions": []})
        interval = get_resurfacing_interval(info["appearances"])
        missions_since = next_mission - info["last_seen_mission"]

        # Is this word due?
        is_due = missions_since >= interval or info["appearances"] == 0
        is_struggled = word in struggled

        if is_due or is_struggled:
            english = tier_vocab.get(word, "")
            # Check all tiers if not found
            if not english:
                for t in [1, 2, 3]:
                    tv = get_tier_vocab(t)
                    if word in tv:
                        english = tv[word]
                        break

            priority = 0
            if is_struggled:
                priority = 3  # highest
            elif is_due and missions_since > interval * 2:
                priority = 2  # overdue
            elif is_due:
                priority = 1  # due

            candidates.append({
                "word": word,
                "english": english,
                "priority": priority,
                "appearances": info["appearances"],
                "last_seen": info["last_seen_mission"],
                "status": "struggled" if is_struggled else (
                    "recently mastered" if word in comfortable else "mastered"
                ),
            })

    # Sort: struggled first, then overdue, then due. Within same priority, fewest appearances first
    candidates.sort(key=lambda c: (-c["priority"], c["appearances"], c["last_seen"]))

    return candidates[:max_callbacks]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate CALLBACKS for next mission")
    parser.add_argument("--next-mission", type=int, default=None,
                        help="Mission number (default: auto-detect from learner.json)")
    parser.add_argument("--save-tracker", action="store_true",
                        help="Save word_tracker.json with per-word appearance data")
    parser.add_argument("--max", type=int, default=5,
                        help="Max callback words (default: 5)")
    args = parser.parse_args()

    # Read word lists from vocab_state (Python-facing), fall back to learner.json
    vocab_state = load_json(VOCAB_STATE_PATH)
    learner = load_json(LEARNER_PATH)
    word_source = vocab_state if vocab_state else learner
    if not word_source:
        print("Error: No vocab_state.json or learner.json found.")
        sys.exit(1)

    # Auto-detect next mission
    next_mission = args.next_mission
    if next_mission is None:
        if learner:
            active = learner.get("active_mission", {})
            next_mission = active.get("mission", 39)
        else:
            next_mission = 39

    print(f"Scanning scripts for word appearances...")
    tracker = scan_scripts()
    print(f"  Found {len(tracker)} unique Tamil words across scripts\n")

    if args.save_tracker:
        save_json(TRACKER_PATH, tracker)
        print()

    # Get tier vocab for translations
    tier_vocab = {}
    for t in [1, 2, 3, 4]:
        tier_vocab.update(get_tier_vocab(t))

    callbacks = generate_callbacks(next_mission, tracker, word_source, tier_vocab, args.max)

    # Print the CALLBACKS block
    print(f"CALLBACKS for Mission {next_mission}:")
    print("-" * 50)
    if not callbacks:
        print("  (no words due for callback)")
    else:
        for cb in callbacks:
            status_tag = f"[{cb['status']}]"
            seen_info = f"seen {cb['appearances']}x, last M{cb['last_seen']}" if cb['appearances'] > 0 else "never seen in scripts"
            english = cb['english'] or '[unknown]'
            print(f"  - {cb['word']} — {english}  {status_tag}  ({seen_info})")

    # Also print a summary of word health
    print(f"\n--- Word Health Summary ---")
    known = get_all_known_words(word_source)
    never_seen = [w for w in known if w not in tracker or tracker[w]["appearances"] == 0]
    seen_once = [w for w in known if w in tracker and tracker[w]["appearances"] == 1]

    print(f"  Known words: {len(known)}")
    print(f"  Tracked in scripts: {len([w for w in known if w in tracker])}")
    if never_seen:
        print(f"  Never appeared in a script: {len(never_seen)}")
        for w in never_seen[:5]:
            print(f"    - {w}")
        if len(never_seen) > 5:
            print(f"    ... and {len(never_seen) - 5} more")
    if seen_once:
        print(f"  Seen only 1x: {len(seen_once)}")


if __name__ == "__main__":
    main()
