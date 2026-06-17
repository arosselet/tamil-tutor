#!/usr/bin/env python3
"""
ONE-TIME migration: fold the scattered word-state into a single word-keyed lexicon.

Today a word's state is smeared across five structures:
  - mastered_words / comfortable_words / struggled_words  (recognition, bucketed)
  - production            (a separate {word: cold|hinted} map, keyed inconsistently)
  - phonetic_aliases      (a phonetic->script side-table)
  - word_tracker.json     (per-word appearance/recency)
  - episodes[].words      (a noisy regex scrape — NOT a source here)

This produces progress/lexicon.json, where each word is ONE record holding all of it.
It is NON-DESTRUCTIVE: it writes a new file and deletes nothing. Inspect the output and
the report before any reader/writer is pointed at the lexicon.

Lexicon keys come only from the curated recognition lists + resolved production keys —
never the episode scrape — so junk tokens can't enter by construction.

Usage:
    python scripts/migrate_lexicon.py            # write progress/lexicon.json + print report
    python scripts/migrate_lexicon.py --dry-run  # print report only, write nothing
"""

import argparse
import json
from pathlib import Path

BASE = Path(__file__).parent.parent
VOCAB_STATE_PATH = BASE / "progress" / "vocab_state.json"
WORD_TRACKER_PATH = BASE / "progress" / "word_tracker.json"
TIERS_DIR = BASE / "curriculum" / "tiers"
LEXICON_PATH = BASE / "progress" / "lexicon.json"

RECOGNITION_FROM_LIST = {
    "mastered_words": "solid",
    "comfortable_words": "comfortable",
    "struggled_words": "struggled",
}
# Higher wins if a word somehow appears in multiple recognition lists.
RECOGNITION_RANK = {"struggled": 0, "comfortable": 1, "solid": 2}


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_gloss_map() -> dict[str, str]:
    """{tamil: english} across every tier — curriculum is the source of glosses."""
    glosses: dict[str, str] = {}
    for f in sorted(TIERS_DIR.glob("tier_*.json")):
        data = load_json(f) or {}
        for v in data.get("vocabulary", []):
            tamil, english = v.get("tamil"), v.get("english")
            if tamil and english and tamil not in glosses:
                glosses[tamil] = english
    return glosses


def reverse_aliases(aliases: dict[str, str]) -> dict[str, list[str]]:
    """phonetic->script  becomes  script->[phonetic, ...]"""
    by_script: dict[str, list[str]] = {}
    for phon, script in aliases.items():
        by_script.setdefault(script, []).append(phon)
    for script in by_script:
        by_script[script].sort()
    return by_script


def main():
    parser = argparse.ArgumentParser(description="Fold word-state into progress/lexicon.json")
    parser.add_argument("--dry-run", action="store_true", help="Print report only; write nothing")
    args = parser.parse_args()

    vocab = load_json(VOCAB_STATE_PATH)
    if not vocab:
        print("Error: progress/vocab_state.json not found.")
        return
    tracker = load_json(WORD_TRACKER_PATH) or {}
    glosses = build_gloss_map()
    aliases = vocab.get("phonetic_aliases", {})
    phonetic_by_script = reverse_aliases(aliases)

    # --- 1. Recognition axis: build one record per recognized word ---
    lexicon: dict[str, dict] = {}
    multi_listed: list[tuple[str, str, str]] = []  # (word, existing_level, dropped_level)

    # Insert in mastery order (solid -> comfortable -> struggled) for readable top-down output.
    for list_key in ("mastered_words", "comfortable_words", "struggled_words"):
        level = RECOGNITION_FROM_LIST[list_key]
        for word in vocab.get(list_key, []):
            if word in lexicon:
                # Already placed by a higher-ranked list; record the conflict.
                multi_listed.append((word, lexicon[word]["recognition"], level))
                continue
            missions = sorted(set(tracker.get(word, {}).get("missions", [])))
            lexicon[word] = {
                "gloss": glosses.get(word, ""),
                "phonetic": phonetic_by_script.get(word, []),
                "recognition": level,
                "production": "none",
                "seen_in": missions,
                "last_surfaced": None,
            }

    recognized = set(lexicon.keys())

    # --- 2. Production axis: attach where it lands on a recognized word ---
    orphans: list[tuple[str, str, str]] = []  # (raw_key, resolved_key, level)
    attached = 0
    for raw_key, level in vocab.get("production", {}).items():
        resolved = aliases.get(raw_key, raw_key)
        if resolved in recognized:
            lexicon[resolved]["production"] = level
            attached += 1
        else:
            orphans.append((raw_key, resolved, level))

    # --- 3. Report ---
    missing_gloss = sorted(w for w, r in lexicon.items() if not r["gloss"])

    print("=" * 64)
    print("LEXICON MIGRATION REPORT")
    print("=" * 64)
    print(f"Records written:       {len(lexicon)}")
    print(f"  solid:               {sum(1 for r in lexicon.values() if r['recognition']=='solid')}")
    print(f"  comfortable:         {sum(1 for r in lexicon.values() if r['recognition']=='comfortable')}")
    print(f"  struggled:           {sum(1 for r in lexicon.values() if r['recognition']=='struggled')}")
    print(f"Production attached:   {attached}")
    print(f"  cold:                {sum(1 for r in lexicon.values() if r['production']=='cold')}")
    print(f"  hinted:              {sum(1 for r in lexicon.values() if r['production']=='hinted')}")

    # The whole point of the meter: floor = cold among recognized / recognized.
    cold = sum(1 for r in lexicon.values() if r["production"] == "cold")
    total = len(lexicon)
    print(f"\nViability floor (clean): {cold}/{total} recognized words fire cold "
          f"({(cold/total*100 if total else 0):.0f}%)")

    if orphans:
        print(f"\n--- ORPHAN production keys ({len(orphans)}) — DECIDE BY HAND ---")
        print("    (produced state for a word not in any recognition list — not guessed into the file)")
        for raw, resolved, level in orphans:
            shown = raw if raw == resolved else f"{raw} -> {resolved}"
            print(f"    {shown}  [{level}]")
        print("    Resolve each by either: add a phonetic alias, OR add the word to a")
        print("    recognition list (likely it's known), OR confirm it's noise to drop.")

    if multi_listed:
        print(f"\n--- Words in MULTIPLE recognition lists ({len(multi_listed)}) — kept higher ---")
        for word, kept, dropped in multi_listed:
            print(f"    {word}: kept '{kept}', dropped '{dropped}'")

    if missing_gloss:
        print(f"\n--- Missing gloss ({len(missing_gloss)}) — not in any curriculum tier ---")
        print("    " + ", ".join(missing_gloss))

    if args.dry_run:
        print("\n[dry-run] No file written.")
        return

    with open(LEXICON_PATH, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {LEXICON_PATH.relative_to(BASE)} ({len(lexicon)} records). Existing files untouched.")


if __name__ == "__main__":
    main()
