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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from generate_callbacks import due_callbacks, load_json, days_since, NEVER_SURFACED
from sync_state import is_unseen

# Windows consoles default to cp1252, which can't print Tamil (2026-07-15).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
LEXICON_PATH = BASE / "progress" / "lexicon.json"
WORD_POOL_PATH = BASE / "curriculum" / "word_pool.json"
KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
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


def recent_ask_counts(klog: list, lexicon: dict, days: int = 3, now=None) -> dict:
    """word → how many fired knocks in the last `days` asked for it (the original
    `expected_target`) or printed it (body/memo/recast, whole chains).

    Lives here, not in `morning_knock`, because the selector is shared and the
    ticket must stay importable without the OpenAI/TTS stack (2026-07-25). It
    guards a gap staleness cannot see: an ask with no reply never sets
    `last_surfaced`, so a missed item stays maximally stale and would be
    re-asked forever — the original KF-6 symptom (the same ask fired 5× in 4
    days and capped itself at hinted, 2026-07-06)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    recent = []
    for k in klog:
        if not k.get("acted", True):  # legacy entries (no 'acted') were all fires
            continue
        try:
            ts = datetime.fromisoformat((k.get("timestamp") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff:
            continue
        texts = [k.get("body", ""), k.get("memo_script", ""), k.get("reply_line", "")]
        texts += [x.get("reply_line", "") for x in k.get("exchanges", [])]
        # Every item of a volley was asked, not just the one that opened it —
        # `expected_target` names item 1 and Python walks the rest, so items 2..n
        # were invisible to this count while being the deck's main volume channel
        # (2026-07-25). Their asks are English situations, so only the targets
        # carry the signal.
        targets = {k.get("expected_target", "")}
        targets |= {v.get("target", "") for v in (k.get("volley") or [])}
        recent.append((targets, " ".join(t for t in texts if t).lower()))
    counts = {}
    for word, rec in lexicon.items():
        probes = [word.lower()] + [p.lower() for p in rec.get("phonetic", []) if p]
        n = sum(1 for tgts, blob in recent
                if word in tgts or any(p in blob for p in probes))
        if n:
            counts[word] = n
    return counts


def deck_status(lexicon: dict, deck: str = "trip", today=None,
                asked: dict | None = None) -> dict | None:
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
    today = today or date.today()
    regs = deck_registers(deck)
    if asked is None:
        asked = recent_ask_counts(load_json(KNOCK_LOG_PATH) or [], lexicon)
    fire = [(w, r) for w, r in members if r.get("direction", "fire") != "catch"]
    catch = [(w, r) for w, r in members if r.get("direction") == "catch"]
    cold = [w for w, r in fire if r.get("production") == "cold"]

    def stale(r: dict) -> int:
        ds = days_since(r.get("last_surfaced"), today)
        return NEVER_SURFACED if ds is None else ds

    pending = [{
        "word": w, "gloss": r.get("gloss", ""),
        "kind": "frame" if r.get("type") == "pattern" else r.get("type", "chunk"),
        "recognition": r.get("recognition"), "production": r.get("production", "none"),
        "tier": TIER_NAMES.get(DECK_TIERS.get(regs.get(w, ""), 1)),
        "unseen": is_unseen(r), "staleness": stale(r),
        "last_surfaced": r.get("last_surfaced"), "asks": asked.get(w, 0),
    } for w, r in fire if r.get("production") != "cold"]
    # ONE ordering law, owned here, read by every channel (2026-07-25):
    #   tier → least-recently-WORKED → least-recently-ASKED → ripeness → key
    # Tier is the 07-13 touchdown bar and stays primary. Staleness is the same
    # coverage-first law floor_gap_targets has always used; ripeness-first alone
    # was rich-get-richer (an item only becomes `hinted` by being worked, which
    # promoted it again) and the last tiebreak was alphabetical, so the head of
    # each tier froze: 16 frames took 51 of the deck's 74 lifetime reps while 50
    # of 70 fire items had never been worked at all (2026-07-25 audit).
    # Ask-count breaks the ties staleness cannot: 50 items sit together at
    # NEVER_SURFACED, and an ask that got no reply never sets `last_surfaced` —
    # so without this a missed item would be re-asked forever (KF-6, 2026-07-06).
    # Subordinating it to tier also repairs the knock-side version this replaces,
    # where a stable re-sort by ask count alone let an asked-once SURVIVAL item
    # fall below an unasked dessert one.
    pending.sort(key=lambda c: (DECK_TIERS.get(regs.get(c["word"], ""), 1),
                                -c["staleness"], c["asks"],
                                PROD_ORDER.get(c["production"], 1),
                                RECOG_ORDER.get(c["recognition"], 1), c["word"]))
    catch_pending = [{
        "word": w, "gloss": r.get("gloss", ""),
        "kind": "frame" if r.get("type") == "pattern" else r.get("type", "chunk"),
        "recognition": r.get("recognition"), "staleness": stale(r),
        "last_surfaced": r.get("last_surfaced"), "asks": asked.get(w, 0),
    } for w, r in catch if r.get("recognition") != "solid"]
    # Same law on the ear: catch starved hardest of all (1 of 12 items ever
    # touched, and that one took all 5 catch reps).
    catch_pending.sort(key=lambda c: (-c["staleness"], c["asks"],
                                      RECOG_ORDER.get(c["recognition"], 1), c["word"]))
    return {"total": len(fire), "cold": len(cold), "pending": pending,
            "catch_total": len(catch),
            "caught": sum(1 for _, r in catch if r.get("recognition") == "solid"),
            "catch_pending": catch_pending}


def deck_coverage(lexicon: dict, deck: str = "trip", today=None) -> dict | None:
    """COVERAGE, not progress — the meter the deck never had. `compute_deck`
    answers "how many fire cold?"; this answers "how many have ever been WORKED
    at all?" (a session rep, a judged reply, or a show dose — anything that sets
    `last_surfaced`). An ask with no reply does not count, which is exactly why
    `recent_ask_counts` is the third term of the sort key and not this meter.

    The pair matters because a value-ordered queue starves its tail silently: on
    2026-07-25 the headline read 15/34 survival at 3.4 cold/day against a needed
    1.1 — a won sprint — while 50 of 70 fire items had never been worked at all,
    and the two survival registers that decide freezing at the table
    (antifreeze, public) sat at 3/18. cold/total is honest about what it counts
    and structurally blind to distribution. Reported per tier and per register so
    the blindness has nowhere to hide.

    `soaked_only` = never worked, but heard in an episode: a different state from
    never encountered, and the cheaper one to fix."""
    members = [(w, r) for w, r in lexicon.items() if r.get("deck") == deck]
    if not members:
        return None
    today = today or date.today()
    regs = deck_registers(deck)

    def bucket() -> dict:
        return {"total": 0, "touched": 0, "untouched": 0, "cleared": 0}

    # Tier/register buckets are the FIRE side only — the same split every other
    # caller keeps ("cleared/total/pct stay the FIRE side so every caller's
    # headline is honest", compute_deck). The ear gets its own bucket; folding it
    # into the tiers would inflate survival with catch frames.
    tiers: dict[str, dict] = {}
    registers: dict[str, dict] = {}
    untouched: list[dict] = []
    fire, catch = bucket(), bucket()
    for w, r in members:
        is_catch = r.get("direction") == "catch"
        reg = regs.get(w, "")
        tier = TIER_NAMES.get(DECK_TIERS.get(reg, 1), "delight")
        worked = bool(r.get("last_surfaced"))
        done = (r.get("recognition") == "solid") if is_catch else (r.get("production") == "cold")
        buckets = [catch] if is_catch else [fire, tiers.setdefault(tier, bucket()),
                                            registers.setdefault(reg or "?", bucket())]
        for b in buckets:
            b["total"] += 1
            b["touched" if worked else "untouched"] += 1
            b["cleared"] += done
        if not worked and not done:
            untouched.append({
                "word": w, "gloss": r.get("gloss", ""), "tier": tier,
                "register": reg or "?", "direction": "catch" if is_catch else "fire",
                "soaked_only": bool(r.get("seen_in")),
            })
    untouched.sort(key=lambda c: (DECK_TIERS.get(
        regs.get(c["word"], ""), 1), c["word"]))
    return {"tiers": tiers, "registers": registers, "untouched": untouched,
            "fire": fire, "catch": catch}


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
    deck = deck_status(lexicon, today=today)
    if deck:
        print("\n★ TRIP DECK  (the sprint headline — force these before the general floor)")
        print("-" * 60)
        print(f"  {deck['cold']}/{deck['total']} deck phrases fire cold. "
              f"Not-yet-cold ({len(deck['pending'])}) — pick from these first:")
        for t in deck["pending"][:12]:
            tag = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
            if t.get("unseen"):
                tag += " · ⚠ UNSEEN — teach first (show it, gloss it), NEVER cold-quiz"
            if t["staleness"] >= NEVER_SURFACED:
                tag += " · never worked"
            tier = f" · {t['tier']}" if t.get("tier") else ""
            print(f"  - [{t['kind']}{tier}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{tag}]")
        hidden = len(deck["pending"]) - 12
        if hidden > 0:
            print(f"  … {hidden} more below the cut (least-recently-worked first — the tail rotates up)")
        if deck["catch_total"]:
            print(f"\n  EAR-ONLY ({deck['caught']}/{deck['catch_total']} solid) — eavesdrop/soak targets; "
                  f"win = recognition, never force these to fire:")
            for t in deck["catch_pending"][:8]:
                never = " · never worked" if t["staleness"] >= NEVER_SURFACED else ""
                print(f"  - [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{t['recognition']}{never}]")

    cov = deck_coverage(lexicon, today=today)
    if cov:
        print("\n★ DECK COVERAGE  (how many have been WORKED — the meter cold/total can't see)")
        print("  ENGINEERING NUMBERS — they steer selection; they are never narrated to Andrew.")
        print("-" * 60)
        for tier in ("survival", "delight", "dessert"):
            b = cov["tiers"].get(tier)
            if not b:
                continue
            regs_in = sorted((r, x) for r, x in cov["registers"].items()
                             if TIER_NAMES.get(DECK_TIERS.get(r, 1), "delight") == tier)
            detail = ", ".join(f"{r} {x['touched']}/{x['total']}" for r, x in regs_in)
            flag = "  ⚠" if b["untouched"] else ""
            print(f"  {tier:9} worked {b['touched']:2}/{b['total']:2} · cold {b['cleared']:2}{flag}"
                  + (f"   ({detail})" if detail else ""))
        c = cov["catch"]
        if c["total"]:
            print(f"  {'ear-only':9} worked {c['touched']:2}/{c['total']:2} · solid {c['cleared']:2}"
                  + ("  ⚠" if c["untouched"] else ""))
        if cov["untouched"]:
            u_fire = [u for u in cov["untouched"] if u["direction"] == "fire"]
            u_catch = [u for u in cov["untouched"] if u["direction"] == "catch"]
            soaked = sum(1 for u in cov["untouched"] if u["soaked_only"])
            ear = f" + {len(u_catch)} ear-only" if u_catch else ""
            print(f"\n  ⚠ NEVER WORKED: {len(u_fire)} fire item(s){ear} "
                  f"({soaked} heard in an episode but never asked).")
            starving = [f"{r} ({x['untouched']})" for r, x in sorted(
                cov["registers"].items(), key=lambda kv: -kv[1]["untouched"])
                if x["untouched"]]
            if starving:
                print("     Starving registers: " + ", ".join(starving))
            print("     They now sort to the head of their tier — fire from the top and this drains.")

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
