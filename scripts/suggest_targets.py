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
import json
import sys
from datetime import date
from pathlib import Path

from generate_callbacks import due_callbacks, load_json, days_since, NEVER_SURFACED
from sync_state import is_unseen

# Windows consoles default to cp1252, which can't print Tamil (2026-07-15).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"
WORD_POOL_PATH = BASE / "curriculum" / "word_pool.json"
SCRIPTS_DIR = BASE / "content" / "scripts"

RECOGNIZED = {"comfortable", "solid"}
# Most-ready-to-fire first: hinted is one hint from cold; among equals, the more
# strongly recognized word is the riper target for forced production.
PROD_ORDER = {"hinted": 0, "none": 1}
RECOG_ORDER = {"solid": 0, "comfortable": 1}

# ── Scene-spec palettes ──────────────────────────────────────────────
# Variety is structural, not taste: Python forces range on the axes that
# actually make an episode feel fresh, and Anna/the Director write the story
# inside that frame. The divergence gate forbids repeating any value used in
# the last DIVERGENCE_WINDOW episodes (read from the *.tags.json sidecars).
DIVERGENCE_WINDOW = 3

# Emotional tone — the axis that was stuck on "mild irritation".
REGISTERS = ["tenderness", "dread", "mischief", "pride", "suspicion",
             "grief/nostalgia", "delight", "embarrassment", "defiance", "reconciliation"]
# Episode structure (matches the Architect's Episode Form). "lore" is the
# stories-are-curriculum lens (constitution): the payload word as protagonist —
# gate-rotated like every form so it can't take over the feed.
FORMS = ["classic", "vignette", "story", "phone_call", "lore"]
# One dramatic ingredient — all free of vocabulary, all situational.
INGREDIENTS = {
    "subtext": "two people want opposite things under polite words",
    "turn": "the scene flips on a reveal partway through",
    "character": "a vivid, specific person — a tic, an obsession, a lie",
    "stakes": "something real is on the line, not just a chore",
    "genre": "a scam, a confession, a ghost story, a flirtation",
}


def floor_gap_targets(lexicon: dict, today, max_n: int) -> list[dict]:
    gap = []
    for w, r in lexicon.items():
        if r.get("type") == "pattern":
            continue  # patterns are forced via the Engines block, not the word floor
        if r.get("direction") == "catch":
            continue  # ear-only deck items — never forced to fire
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


# Touchdown bar (2026-07-13, Andrew — supersedes "deck tiering rejected" 2026-07-09,
# re-decided at trailing pace 0.4/day with 30 days left): survival (fast speech aimed
# at him — repair it, transact, don't freeze) outranks delight (the visible-trying
# wins at the family table); gossip/zinger are soak & dessert. Ordering only —
# nothing leaves the deck; the ambition is still to clear it whole.
DECK_TIERS = {"antifreeze": 0, "public": 0, "frame": 0,
              "faq": 1, "mil-table": 1, "social": 1,
              "gossip": 2, "zinger": 2}
TIER_NAMES = {0: "survival", 1: "delight", 2: "dessert"}


def deck_registers(deck: str = "trip") -> dict:
    """word → curriculum register, joined at menu time from the deck's curriculum
    file — ordering is a menu concern, not state, so the lexicon schema stays
    frozen. Missing file or register degrades to flat ordering."""
    path = BASE / "curriculum" / f"{deck}_deck.json"
    if not path.exists():
        return {}
    return {i.get("tamil", ""): i.get("register", "")
            for i in json.loads(path.read_text(encoding="utf-8"))}


def deck_status(lexicon: dict, deck: str = "trip") -> dict | None:
    """A finite, deadline-driven deck (the India-trip survival set), tagged
    `deck: "<name>"`. During a sprint this is the HEADLINE priority — Anna forces
    its not-yet-cold members first. Members split by `direction`: "fire" (default —
    force to cold production) vs "catch" (ear-only — the win is solid recognition
    via eavesdrop/soak; NEVER force these to fire). Returns fire progress + pending
    fire items (chunks said whole, frames want a novel slot-fill) + pending catch
    items, or None if no deck exists."""
    members = [(w, r) for w, r in lexicon.items() if r.get("deck") == deck]
    if not members:
        return None
    regs = deck_registers(deck)
    fire = [(w, r) for w, r in members if r.get("direction", "fire") != "catch"]
    catch = [(w, r) for w, r in members if r.get("direction") == "catch"]
    cold = [w for w, r in fire if r.get("production") == "cold"]
    pending = [{
        "word": w, "gloss": r.get("gloss", ""),
        "kind": "frame" if r.get("type") == "pattern" else r.get("type", "chunk"),
        "recognition": r.get("recognition"), "production": r.get("production", "none"),
        "tier": TIER_NAMES.get(DECK_TIERS.get(regs.get(w, ""), 1)),
        "unseen": is_unseen(r),
    } for w, r in fire if r.get("production") != "cold"]
    # Touchdown-bar tier first; within a tier, ripest first: hinted before none,
    # solid before comfortable.
    pending.sort(key=lambda c: (DECK_TIERS.get(regs.get(c["word"], ""), 1),
                                PROD_ORDER.get(c["production"], 1),
                                RECOG_ORDER.get(c["recognition"], 1), c["word"]))
    catch_pending = [{
        "word": w, "gloss": r.get("gloss", ""),
        "kind": "frame" if r.get("type") == "pattern" else r.get("type", "chunk"),
        "recognition": r.get("recognition"),
    } for w, r in catch if r.get("recognition") != "solid"]
    catch_pending.sort(key=lambda c: (RECOG_ORDER.get(c["recognition"], 1), c["word"]))
    return {"total": len(fire), "cold": len(cold), "pending": pending,
            "catch_total": len(catch),
            "caught": sum(1 for _, r in catch if r.get("recognition") == "solid"),
            "catch_pending": catch_pending}


def engines_to_fire(lexicon: dict) -> list[dict]:
    """Generative patterns (lemmas / frames) not yet firing cold. These are forced
    differently from words: the cold test is producing a NOVEL instance unaided,
    not reciting a memorized line."""
    out = []
    for w, r in lexicon.items():
        if r.get("type") != "pattern" or r.get("production") == "cold":
            continue
        if r.get("direction") == "catch":
            continue  # ear-only patterns (e.g. the quotative -nu) — train the ear, don't force

        out.append({"key": w, "gloss": r.get("gloss", ""),
                    "production": r.get("production", "none"), "unseen": is_unseen(r)})
    out.sort(key=lambda c: (c["production"] != "hinted", c["key"]))  # hinted (riper) first
    return out


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


def load_recent_sidecars(limit: int | None = None) -> list[dict]:
    """All *.tags.json sidecars, newest mission first. Skips unreadable ones.
    Only integer missions count: special_* reference tapes carry a string
    mission and belong to the feed, not the scene rotation."""
    cars = []
    for p in SCRIPTS_DIR.glob("*.tags.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(d.get("mission"), int):
            cars.append(d)
    cars.sort(key=lambda d: d.get("mission", 0), reverse=True)
    return cars[:limit] if limit else cars


def pick_divergent(palette, axis_key: str, sidecars: list[dict], rotate: int):
    """Choose a palette value that diverges from the last DIVERGENCE_WINDOW
    episodes on `axis_key`. Prefers values never used, then least-recently used.
    `rotate` (the episode count) spreads cold-start picks so we don't always
    land on the first palette entry before history accrues."""
    recent = {c.get(axis_key) for c in sidecars[:DIVERGENCE_WINDOW]}
    last_used: dict = {}
    for c in sidecars:  # newest-first → first occurrence is the most recent use
        v = c.get(axis_key)
        if v in palette and v not in last_used:
            last_used[v] = c.get("mission", 0)
    eligible = [v for v in palette if v not in recent] or list(palette)
    unused = [v for v in eligible if v not in last_used]
    if unused:
        return unused[rotate % len(unused)]
    return min(eligible, key=lambda v: last_used.get(v, -1))


def scene_spec(sidecars: list[dict]) -> dict:
    """The structural variety gate: register + form + dramatic ingredient,
    each forced to diverge from the last 3 episodes."""
    n = len(sidecars)
    ingredient = pick_divergent(list(INGREDIENTS), "dramatic_ingredient", sidecars, n)
    return {
        "register": pick_divergent(REGISTERS, "register", sidecars, n),
        "form": pick_divergent(FORMS, "episode_form", sidecars, n),
        "ingredient": ingredient,
        "ingredient_desc": INGREDIENTS[ingredient],
        "recent": [(c.get("mission"), c.get("register", "—"), c.get("episode_form", "—"))
                   for c in sidecars[:DIVERGENCE_WINDOW]],
    }


def main():
    parser = argparse.ArgumentParser(description="The session ticket: floor-gap + callbacks + new candidates")
    parser.add_argument("--floor-max", type=int, default=8, help="Max floor-gap words to force (default 8)")
    parser.add_argument("--callbacks-max", type=int, default=5, help="Max due callbacks (default 5)")
    parser.add_argument("--clusters", type=int, default=5, help="Max thin clusters to surface (default 5)")
    parser.add_argument("--per-cluster", type=int, default=5, help="Max new candidates per cluster (default 5)")
    args = parser.parse_args()

    lexicon = load_json(LEXICON_PATH)
    word_pool = load_json(WORD_POOL_PATH)
    learner = load_json(BASE / "progress" / "learner.json") or {}
    # An EMPTY lexicon ({}) is a valid day-zero state — the ticket still serves
    # the new-candidates section. Only a MISSING file is an error.
    if lexicon is None or not word_pool:
        print("Error: lexicon.json or word_pool.json not found. See BOOTSTRAP.md.")
        return
    today = date.today()

    print("=" * 60)
    print("SESSION TICKET — Python computes the menu; Anna picks the story.")
    print("=" * 60)

    # Next engine focus — the deliberate unlock priority (set via sync_state update
    # --next-engine). Surfaced first so Anna never re-derives the order session by session.
    next_engine_key = learner.get("next_engine", "")
    if next_engine_key and lexicon:
        r = lexicon.get(next_engine_key, {})
        prod = r.get("production", "none")
        if prod != "cold":
            gloss = r.get("gloss", "")
            unseen_flag = " · ⚠ UNSEEN — teach first (show it), NEVER cold-quiz" if is_unseen(r) else ""
            print(f"\n🎯 NEXT ENGINE: {next_engine_key} — {gloss}  [production: {prod}{unseen_flag}]")
            print(f"   One cold novel instance of this pattern = engine online.")

    # Trip Deck — the finite, deadline-driven sprint set. When it exists it is the
    # HEADLINE: force its not-yet-cold members first (Anna narrates the countdown).
    deck = deck_status(lexicon)
    if deck:
        print("\n★ TRIP DECK  (the sprint headline — force these before the general floor)")
        print("-" * 60)
        print(f"  {deck['cold']}/{deck['total']} deck phrases fire cold. "
              f"Not-yet-cold ({len(deck['pending'])}) — pick from these first:")
        for t in deck["pending"][:12]:
            tag = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
            if t.get("unseen"):
                tag += " · ⚠ UNSEEN — teach first (show it, gloss it), NEVER cold-quiz"
            tier = f" · {t['tier']}" if t.get("tier") else ""
            print(f"  - [{t['kind']}{tier}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{tag}]")
        if deck["catch_total"]:
            print(f"\n  EAR-ONLY ({deck['caught']}/{deck['catch_total']} solid) — eavesdrop/soak targets; "
                  f"win = recognition, never force these to fire:")
            for t in deck["catch_pending"][:8]:
                print(f"  - [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{t['recognition']}]")

    # 0. Scene spec — structural variety gate (audio episodes especially)
    spec = scene_spec(load_recent_sidecars())
    print("\n0. SCENE SPEC  (force range; vary everything EXCEPT the vocabulary)")
    print("-" * 60)
    print(f"  Register:   {spec['register']}")
    print(f"  Form:       {spec['form']}")
    print(f"  Ingredient: {spec['ingredient']} — {spec['ingredient_desc']}")
    if spec["recent"]:
        recent_str = ", ".join(f"M{m} {reg}/{form}" for m, reg, form in spec["recent"])
        print(f"  (diverging from last {DIVERGENCE_WINDOW}: {recent_str})")

    # 1. Floor-gap — what to FORCE
    print("\n1. FLOOR-GAP TARGETS  (recognized, not yet cold — force these)")
    print("-" * 60)
    gap = floor_gap_targets(lexicon, today, args.floor_max)
    if not gap:
        print("  (floor is clear — nothing recognized is stuck below cold)")
    for t in gap:
        tag = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
        print(f"  - {t['word']} — {t['gloss'] or '[no gloss]'}  [{tag}]")

    # 1b. Engines — generative patterns to force a novel instance of
    engines = engines_to_fire(lexicon)
    if engines:
        print("\n1b. ENGINES TO FIRE  (patterns — force a NOVEL instance, not a memorized line)")
        print("-" * 60)
        for e in engines:
            tag = "hinted→cold" if e["production"] == "hinted" else "cold-pending"
            if e.get("unseen"):
                tag += " · ⚠ UNSEEN — teach first (show it, gloss it), NEVER cold-quiz"
            print(f"  - {e['key']} — {e['gloss'] or '[no gloss]'}  [{tag}]")

    # 2. Callbacks — soft soak (reused logic)
    print("\n2. DUE CALLBACKS  (soft soak — weave in where they fit)")
    print("-" * 60)
    callbacks = due_callbacks(lexicon, today, args.callbacks_max)
    if not callbacks:
        print("  (nothing due — the recognized set is fresh)")
    for cb in callbacks:
        if cb.get("direction") == "catch":
            gap_tag = "ear"  # soak-by-design, not production debt
        else:
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
                          if r.get("type") != "pattern" and r.get("direction") != "catch"
                          and r.get("recognition") in RECOGNIZED and r.get("production") != "cold")
    print(f"\nFloor gap: {floor_gap_total} recognized words not yet firing cold.")
    print(f"Vocabulary fence: {len(fence)} words (the sea).")


if __name__ == "__main__":
    main()
