#!/usr/bin/env python3
"""
The session "ticket" — the menu Python hands Anna so he never picks words by
eyeballing a 2000-line lexicon. Anna chooses the story and meaning; this script
computes the candidate set. The bright line: Python computes the menu, Anna
makes the choice.

Four parts:
  1. FLOOR-GAP TARGETS — words recognized (comfortable/solid) but not yet firing
     cold. These are what to *force* this session. Ordered most-ready-to-fire
     first (a `hinted` word is one hint from cold; a `solid` word is well-soaked).
  2. DUE CALLBACKS — soft soak targets, reusing generate_callbacks.py (no
     duplicated logic).
  3. NEW CANDIDATES BY CLUSTER — priority-1 word_pool entries not yet in the
     lexicon, grouped by cluster with a coverage stat so Anna can see which
     clusters are thin. Python shows coverage; Anna picks the cluster.
  4. VOCABULARY FENCE — all recognized words (comfortable/solid) plus cold
     productions. This is "the sea" the Architect builds from. Every word of
     dialogue that isn't payload should come from this list.

Usage:
    python scripts/suggest_targets.py [--floor-max 8] [--clusters 5] [--per-cluster 5]
"""

import argparse
from datetime import date
from pathlib import Path

from generate_callbacks import due_callbacks, load_json, days_since, NEVER_SURFACED

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"
WORD_POOL_PATH = BASE / "curriculum" / "word_pool.json"

RECOGNIZED = {"comfortable", "solid"}
# Most-ready-to-fire first: hinted is one hint from cold; among equals, the more
# strongly recognized word is the riper target for forced production.
PROD_ORDER = {"hinted": 0, "none": 1}
RECOG_ORDER = {"solid": 0, "comfortable": 1}


def floor_gap_targets(lexicon: dict, today, max_n: int) -> list[dict]:
    gap = []
    for w, r in lexicon.items():
        if r.get("recognition") not in RECOGNIZED or r.get("production") == "cold":
            continue
        ds = days_since(r.get("last_surfaced"), today)
        staleness = NEVER_SURFACED if ds is None else ds
        gap.append({
            "word": w, "gloss": r.get("gloss", ""),
            "recognition": r.get("recognition"), "production": r.get("production", "none"),
            "staleness": staleness, "soaked": len(r.get("seen_in", [])),
        })
    # Least-recently-worked first (rotates as Anna logs sessions); among equals,
    # a hinted word is riper than none, a solid word riper than comfortable, and a
    # more-soaked word (more episodes heard) is riper than a barely-seen one. The
    # soak tiebreak is what carries the cold-start window before dates accrue.
    gap.sort(key=lambda c: (-c["staleness"],
                            PROD_ORDER.get(c["production"], 1),
                            RECOG_ORDER.get(c["recognition"], 1),
                            -c["soaked"],
                            c["word"]))
    return gap[:max_n]


def vocabulary_fence(lexicon: dict) -> list[dict]:
    """The 'sea' — every word the learner recognizes or produces cold.
    The Architect builds scenes from this pool. Words outside it are the +1."""
    fence = []
    for w, r in lexicon.items():
        recog = r.get("recognition", "")
        prod = r.get("production", "")
        if recog in RECOGNIZED or prod == "cold":
            fence.append({
                "word": w,
                "gloss": r.get("gloss", ""),
                "phonetic": r.get("phonetic", []),
            })
    fence.sort(key=lambda e: e["word"])
    return fence


def new_candidates_by_cluster(lexicon: dict, word_pool: list, n_clusters: int, per_cluster: int):
    """Priority-1 word_pool entries not yet in the lexicon, grouped by cluster.
    Coverage = how many of a cluster's priority-1 entries are already known."""
    clusters: dict[str, dict] = {}
    for entry in word_pool:
        if entry.get("priority") != 1:
            continue
        cluster = entry.get("cluster", "uncategorized")
        c = clusters.setdefault(cluster, {"total": 0, "known": 0, "candidates": [], "seen": set()})
        tamil = entry["tamil"]
        if tamil in c["seen"]:
            continue  # word_pool has a few duplicate rows
        c["seen"].add(tamil)
        c["total"] += 1
        if tamil in lexicon:
            c["known"] += 1
        else:
            c["candidates"].append({"tamil": tamil, "gloss": entry.get("gloss", "")})

    # Thinnest coverage first — that's where the floor is least served.
    ranked = sorted(
        (c for c in clusters.items() if c[1]["candidates"]),
        key=lambda kv: (kv[1]["known"] / kv[1]["total"] if kv[1]["total"] else 1.0, -kv[1]["total"]),
    )
    return ranked[:n_clusters], per_cluster


def main():
    parser = argparse.ArgumentParser(description="The session ticket: floor-gap + callbacks + new candidates")
    parser.add_argument("--floor-max", type=int, default=8, help="Max floor-gap words to force (default 8)")
    parser.add_argument("--callbacks-max", type=int, default=5, help="Max due callbacks (default 5)")
    parser.add_argument("--clusters", type=int, default=5, help="Max thin clusters to surface (default 5)")
    parser.add_argument("--per-cluster", type=int, default=5, help="Max new candidates per cluster (default 5)")
    args = parser.parse_args()

    lexicon = load_json(LEXICON_PATH)
    word_pool = load_json(WORD_POOL_PATH)
    if not lexicon or not word_pool:
        print("Error: lexicon.json or word_pool.json not found. See BOOTSTRAP.md.")
        return
    today = date.today()

    print("=" * 60)
    print("SESSION TICKET — Python computes the menu; Anna picks the story.")
    print("=" * 60)

    # 1. Floor-gap — what to FORCE
    print("\n1. FLOOR-GAP TARGETS  (recognized, not yet cold — force these)")
    print("-" * 60)
    gap = floor_gap_targets(lexicon, today, args.floor_max)
    if not gap:
        print("  (floor is clear — nothing recognized is stuck below cold)")
    for t in gap:
        tag = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
        print(f"  - {t['word']} — {t['gloss'] or '[no gloss]'}  [{tag}]")

    # 2. Callbacks — soft soak (reused logic)
    print("\n2. DUE CALLBACKS  (soft soak — weave in where they fit)")
    print("-" * 60)
    callbacks = due_callbacks(lexicon, today, args.callbacks_max)
    if not callbacks:
        print("  (nothing due — the recognized set is fresh)")
    for cb in callbacks:
        gap_tag = "floor-gap" if cb["production"] != "cold" else "retention"
        print(f"  - {cb['word']} — {cb['gloss'] or '[no gloss]'}  [{gap_tag}]")

    # 3. New candidates by cluster — Anna picks the cluster
    print("\n3. NEW CANDIDATES BY CLUSTER  (priority-1, not yet met — pick a thin cluster)")
    print("-" * 60)
    ranked, per_cluster = new_candidates_by_cluster(lexicon, word_pool, args.clusters, args.per_cluster)
    if not ranked:
        print("  (no priority-1 clusters with unmet words)")
    for name, c in ranked:
        print(f"  [{name}]  known {c['known']}/{c['total']}")
        for cand in c["candidates"][:per_cluster]:
            print(f"      - {cand['tamil']} — {cand['gloss']}")

    # 4. Vocabulary fence — the sea the Architect swims in
    print("\n4. VOCABULARY FENCE  (the sea — Architect builds from these; everything else is +1)")
    print("-" * 60)
    fence = vocabulary_fence(lexicon)
    if not fence:
        print("  (empty — no recognized words yet; Architect must scaffold heavily with English)")
    else:
        print(f"  {len(fence)} known words. The Architect should build dialogue from this pool.")
        print(f"  Words outside this list must be answerable from context within seconds.")
        print()
        for entry in fence:
            phon = entry["phonetic"][0] if entry["phonetic"] else ""
            phon_str = f" ({phon})" if phon else ""
            print(f"  - {entry['word']}{phon_str} — {entry['gloss'] or '[no gloss]'}")

    floor_gap_total = sum(1 for r in lexicon.values()
                          if r.get("recognition") in RECOGNIZED and r.get("production") != "cold")
    print(f"\nFloor gap: {floor_gap_total} recognized words not yet firing cold.")
    print(f"Vocabulary fence: {len(fence)} words (the sea).")


if __name__ == "__main__":
    main()
