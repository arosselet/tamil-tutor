#!/usr/bin/env python3
"""
The session "ticket" — the menu Python hands Anna so he never picks words by
eyeballing a 2000-line lexicon. Anna chooses the story and meaning; this script
computes the candidate set. The bright line: Python computes the menu, Anna
makes the choice.

Four parts:
  1. FOCUS SET + BACKGROUND — words recognized (comfortable/solid) but not yet
     firing cold, split into TWO BUDGETS. The focus set is ≤FOCUS_SIZE words in
     dense rotation, drilled until they fire cold and then never drilled again.
     The background is everything not yet started: exposure only — soak them into
     scenes so the tail can't rot, never force them to fire. One ranked list
     cannot do both jobs, and trying made it do neither.
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
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from generate_callbacks import due_callbacks, load_json, days_since, NEVER_SURFACED
from slips import format_slip_block, slip_patterns
from sync_state import is_unseen, soak_pending

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
# Commissioned-only forms: Anna asks for one through the soak order and the
# divergence gate must never roll it by itself — narrated_drama is a 12–18 min
# batch soak that has to be *chosen* ("commissioned, never spec-rotated",
# 2026-07-18). ALL_FORMS is the single owner of what the studio can build, so
# the gate, the CLI's --soak-form and the sidecar stamp cannot drift apart.
COMMISSIONED_FORMS = ["narrated_drama"]
ALL_FORMS = FORMS + COMMISSIONED_FORMS
# One dramatic ingredient — all free of vocabulary, all situational.
INGREDIENTS = {
    "subtext": "two people want opposite things under polite words",
    "turn": "the scene flips on a reveal partway through",
    "character": "a vivid, specific person — a tic, an obsession, a lie",
    "stakes": "something real is on the line, not just a chore",
    "genre": "a scam, a confession, a ghost story, a flirtation",
}


# How many words are in dense rotation at once, and how many of them get drilled
# on a given day (Andrew, 2026-07-26: "10-15 getting most reps until they fire
# cold, the remaining on a slow guaranteed background"). Graduation is production
# going cold — after that a word is never drilled again, it is just used.
FOCUS_SIZE = 12
# Drilling that isn't working, flagged not evicted. Measured 2026-07-26 over the
# 33 words that have actually gone cold: median 2 reps, p90 5, max 15. A word
# past 10 is at twice the p90 and the approach — not the word — is what needs
# changing. It keeps its seat (it IS unfinished); Anna is told to switch angle.
# Deliberately NOT an eviction rule: 33 data points cannot justify giving up on
# a word, and a silently parked word is the starvation this whole change fixes.
STUCK_REPS = 10
# Hinted items silent this long surface for a cold retest (2026-08-01). Hinted
# had no follow-up path at all ("open and unanswered", DECISIONS 07-28): cold is
# a one-way door and hinted was a no-way door.
RETEST_DAYS = 14


TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def probe_hit(probe: str, blob: str, tokens: set) -> bool:
    """Did this knock mention this lexicon entry?

    A multi-word probe is a phrase and matches as a substring. A SINGLE-word
    probe must match a whole token, because substring matching makes short keys
    swallow longer ones: நீ ('you', 2 chars) is inside நீங்க, and the 2026-07-26
    audit logged it at 17 reps when the real figure is far lower. Probe matching
    survives ONLY in `recent_ask_counts` (the reveal-cooldown), where Anna's free
    prose genuinely is the source — the counting path is declared events now."""
    if not probe:
        return False
    parts = TOKEN_RE.findall(probe)
    if len(parts) > 1:
        return probe in blob
    return bool(parts) and parts[0] in tokens


def stable_jitter(word: str) -> str:
    """The last tiebreak. Alphabetical was the old one, and it is the reason the
    head of a tie group froze: every pass through a cohort happened in the same
    order, so the tail of the alphabet was unreachable. A hash of the word is
    arbitrary but STABLE — deterministic for tests, and it spreads the cohort
    instead of ordering it by a property that correlates with nothing."""
    return hashlib.sha1(word.encode("utf-8")).hexdigest()


def coverage_key(c: dict) -> tuple:
    """THE ordering law, defined once and read by BOTH selectors — the deck and
    the general floor. It exists as a function because the 07-25 version was two
    hand-copied sort keys in two files: the law was extended in one and not the
    other, and the un-extended half froze for a day before anyone noticed
    (2026-07-26). A term added here reaches every channel or none.

        fewest LIFETIME reps → least-recently-worked → ripeness → least-exposed → jitter

    Reps lead because coverage is the property that fails silently; staleness
    cannot break the tie when most of the population has never been worked at
    all. Least-EXPOSED replaced the soak term (2026-07-26): `-soaked` sorted the
    already-heard EARLIER — a positive feedback loop, the anti-coverage direction
    for an exposure queue — and `seen_in` is provenance, not a fairness counter.
    Callers may prefix their own terms (the deck prefixes tier — the 07-13
    touchdown bar) but may not reorder or drop these."""
    return (c.get("reps", 0),
            -c.get("staleness", 0),
            PROD_ORDER.get(c.get("production"), 1),
            RECOG_ORDER.get(c.get("recognition"), 1),
            c.get("exposures", 0),
            stable_jitter(c["word"]))


def rep_counts(lexicon: dict) -> dict:
    """word → LIFETIME declared reps. THE coverage number.

    One counter, two writers: sessions (`sync_state.touch`) and the reply judge
    (`knock_reply.apply_verdict`, one increment per word in a judged reply's
    `fired` list — partial counts). Declared events only (2026-07-26): the old
    knock-side half MINED Anna's own prose for mentions, and the same-day audit
    found 100% of live "reps" were mentions (டீ at 21 via English "tea", a false
    STUCK flag on a never-drilled word, focus seats allocated by mention
    frequency). Probe matching survives only in `recent_ask_counts`.

    Not to be confused with `recent_ask_counts`, which is a 3-day COOLDOWN — a
    different question with a different answer. Using the cooldown as the
    coverage term was the other 2026-07-26 defect: on day 4 a word's count
    resets and it rejoins the front of the queue, so ~24 words cycled forever
    while 110 of 134 were never reachable at all."""
    return {w: r["reps"] for w, r in lexicon.items() if r.get("reps")}


def stored_focus_cohort() -> list[str]:
    """The persisted ≤FOCUS_SIZE membership (learner.json, Python-owned).
    [] means no cohort has been seeded yet — day-zero, or a template clone."""
    learner = load_json(BASE / "progress" / "learner.json") or {}
    return [w for w in learner.get("focus_cohort", []) if isinstance(w, str)]


def floor_gap_targets(lexicon: dict, today, max_n: int,
                      asked: dict | None = None, reps: dict | None = None,
                      cohort: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    """The general floor — everything outside the deck. TWO BUDGETS, not one
    ranked list (2026-07-26):

      FOCUS      ≤ FOCUS_SIZE words in dense rotation, drilled until they fire
                 cold. Membership is STORED STATE (learner.json), not an
                 emergent sort: a word enters when a seat opens and leaves only
                 on graduation, so membership is a fact readable in a file,
                 immune to counting bugs by construction (Andrew, 2026-07-26).
      BACKGROUND everything else. It is an EXPOSURE queue, not a drill queue —
                 soak/episode candidates that keep a word warm without forcing
                 it to fire. Least-exposed/least-recently-exposed first, so
                 coverage is guaranteed rather than hoped for.

    Coverage-first and dense-repetition are in real tension: one ranked list
    either touches all 134 words once a month (breadth, nothing graduates) or
    hammers a dozen (depth, the tail rots). Splitting the budget is what lets
    both hold. Simulated over 60 days: 66 graduate, 132 of 134 touched, no word
    drilled more than 5×.

    `cohort` is the stored membership; None loads it from learner.json. A held
    word that graduated (or left the floor population — demotion, deck re-tag)
    vacates its seat here; open seats are filled from the front of the
    background order. Persisting the result is the WRITE seams' job
    (`reconcile_focus` via sync_state / knock_reply), never this reader's."""
    if asked is None:
        asked = recent_ask_counts(load_json(KNOCK_LOG_PATH) or [], lexicon)
    if reps is None:
        reps = rep_counts(lexicon)
    if cohort is None:
        cohort = stored_focus_cohort()
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
            "exposures": r.get("exposures", 0),
            "asks": asked.get(w, 0), "reps": reps.get(w, 0),
        })
    by_word = {c["word"]: c for c in gap}
    if cohort:
        # Stored membership: held seats stand regardless of what any counter
        # says. Graduates (and words that left the floor population) drop out
        # of `by_word` and so vacate their seats here.
        focus = [by_word[w] for w in cohort if w in by_word][:FOCUS_SIZE]
    else:
        # SEED derivation — no cohort stored yet. Words already started hold
        # seats (most-repped first: they are mid-fight, benching them is the
        # churn the stored cohort exists to prevent).
        focus = sorted((c for c in gap if c["reps"]),
                       key=lambda c: (-c["reps"], stable_jitter(c["word"])))[:FOCUS_SIZE]
    held = {c["word"] for c in focus}
    background = sorted((c for c in gap if c["word"] not in held), key=coverage_key)
    seats_open = FOCUS_SIZE - len(focus)
    if seats_open > 0:
        focus += background[:seats_open]
        background = background[seats_open:]
    for c in focus:
        c["band"] = "focus"
    for c in background:
        c["band"] = "background"
    # Within the focus set, least-repped first — spread the reps across the
    # cohort rather than finishing one word at a time. The cooldown still
    # applies INSIDE the set: a word asked in the last 3 days drops behind its
    # cohort-mates for a couple of days. That is the job `asks` was built for
    # and the only job it does now.
    focus.sort(key=lambda c: (c["asks"], coverage_key(c)))
    return (focus[:max_n], background)


def reconcile_focus(lexicon: dict, cohort: list[str], today=None) -> list[str]:
    """The WRITE side of the stored cohort: leave on graduation, enter on
    seat-open (2026-07-26). Pure — returns the new membership, sorted for diff
    stability; the callers that persist it are the two seams where graduation
    can happen (sync_state.cmd_update and knock_reply's judge flow)."""
    focus, _bg = floor_gap_targets(lexicon, today or date.today(), FOCUS_SIZE,
                                   asked={}, cohort=cohort)
    return sorted(c["word"] for c in focus)


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


def deck_rank(word: str, regs: dict) -> int:
    """THE tier prefix — the 07-13 touchdown bar — defined once, so every
    deck-aware ordering reads one definition instead of a hand-copy.

    A non-member ranks AFTER every member (3). That is the whole point: a
    sprint-scoped block must not be crowded out by ordinary vocabulary.

    Extracted 2026-08-04 for the same reason `coverage_key` was on 07-26 — the
    term was hand-copied into two sorts and `retest_targets` (2026-08-01) was
    written without it at all. Consequence, found 8 days from touchdown: the
    deck's three hinted FAQ answers — the questions every relative asks on day
    one, 25-31 days silent — sat below that block's five-item cut behind
    ordinary words that happened to be staler. A single-axis sort in a
    deadline sprint is the recurring bug; the prefix belongs to the law."""
    return DECK_TIERS.get(regs.get(word, ""), 1) if word in regs else 3


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
        blob = " ".join(t for t in texts if t).lower()
        recent.append((targets, blob, set(TOKEN_RE.findall(blob))))
    counts = {}
    for word, rec in lexicon.items():
        probes = [word.lower()] + [p.lower() for p in rec.get("phonetic", []) if p]
        n = sum(1 for tgts, blob, tokens in recent
                if word in tgts or any(probe_hit(p, blob, tokens) for p in probes))
        if n:
            counts[word] = n
    return counts


def deck_status(lexicon: dict, deck: str = "trip", today=None,
                asked: dict | None = None, reps: dict | None = None) -> dict | None:
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
    if reps is None:
        reps = rep_counts(lexicon)
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
        "reps": reps.get(w, 0), "soaked": len(r.get("seen_in", [])),
        "exposures": r.get("exposures", 0),
    } for w, r in fire if r.get("production") != "cold"]
    # tier → ask-cooldown → coverage_key. Tier is the 07-13 touchdown bar and
    # stays primary; the 3-day cooldown rides next, exactly as inside the
    # floor's focus set — an unanswered ask is SPEND, and without this term a
    # hidden-target ask would sit at the front and re-fire forever (KF-6; the
    # old rep miner hid this by counting the ask as a rep). The rest is
    # `coverage_key`, the SHARED law, so the deck and the general floor cannot
    # drift apart (that drift is what happened on 07-25 → 07-26). The deck
    # keeps no focus/background split: it is a finite deadline set, so every
    # member has to clear, and the tiers already say what leads.
    pending.sort(key=lambda c: (deck_rank(c["word"], regs),
                                c["asks"], coverage_key(c)))
    catch_pending = [{
        "word": w, "gloss": r.get("gloss", ""),
        "kind": "frame" if r.get("type") == "pattern" else r.get("type", "chunk"),
        "recognition": r.get("recognition"), "staleness": stale(r),
        "last_surfaced": r.get("last_surfaced"), "asks": asked.get(w, 0),
        # The pair, resolved for the drill: hear this, say that. A catch item
        # with a partner is drillable as a UNIT — recognizing it is only half
        # the win if the answer doesn't arrive (2026-07-26).
        "pairs_with": r.get("pairs_with"),
        "response_gloss": lexicon.get(r.get("pairs_with") or "", {}).get("gloss", ""),
        "reps": reps.get(w, 0), "soaked": len(r.get("seen_in", [])),
        "exposures": r.get("exposures", 0),
        "production": r.get("production", "none"),
    } for w, r in catch if r.get("recognition") != "solid"]
    # Same shared law on the ear — no tier prefix, because catch items clear on
    # recognition and the touchdown bar is a production idea. The ear starved
    # hardest of all (1 of 12 items ever touched, and that one took all 5 reps).
    catch_pending.sort(key=coverage_key)
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
    untouched.sort(key=lambda c: (deck_rank(c["word"], regs), c["word"]))
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


def episode_commission(learner: dict | None = None) -> dict | None:
    """The standing soak order when it is a LIVE commission for THIS lane, else
    None. One predicate, read by both the form pin and the ticket section.

    Live means: it has a payload, it is routed to the episode channel, and it is
    still OWED. A consumed order must not keep commanding the ticket or pinning
    the next episode's form (2026-07-28) — that is how 07-23 produced three
    unwanted episodes in one evening.

    Owed is `soak_pending()` (does the newest episode carry the payload) OR the
    absence of a `delivered` stamp — the two seams disagree by design: the
    episode lane clears itself through registration and never stamps, the soak
    and drill lanes stamp because they have nothing to register. Reading both
    means neither lane can leave a filled order looking open."""
    if learner is None:
        learner = load_json(BASE / "progress" / "learner.json") or {}
    order = learner.get("soak_order") or {}
    if not [w for w in order.get("payload", []) if w]:
        return None
    if (order.get("channel") or "episode") != "episode":
        return None
    if order.get("delivered") or not soak_pending():
        return None
    return order


def commissioned_form(learner: dict | None = None) -> str | None:
    """The form the standing soak order ASKS FOR, or None to let the gate roll.

    Anna hands meaning, the studio owns craft (studio.md) — with one exception,
    the commissioned forms, which exist precisely because they cannot be rolled.
    Until 2026-07-27 this was doctrine with no implementation: `director.md` and
    `architect.md` both document narrated_drama arriving "via the soak order",
    but nothing wrote a form onto the order and nothing read one back.

    An unrecognised form is ignored rather than obeyed — a typo must not send the
    Director off-palette, and it must never silently mean 'no episode'."""
    order = episode_commission(learner)
    if order is None:
        return None
    form = (order.get("form") or "").strip()
    if form and form not in ALL_FORMS:
        print(f"  ⚠ soak order asks for form '{form}', which the studio cannot "
              f"build — ignoring; the spec rolls as usual")
        return None
    return form or None


def retest_targets(lexicon: dict, today=None, max_n: int = 5) -> list[dict]:
    """Hinted items going dark — the follow-up path hinted never had (2026-08-01).

    `coverage_key` leads with fewest-lifetime-reps, so a repped-but-stale hinted
    item sorts BEHIND every never-worked item in its tier forever: the three FAQ
    answers (ஒரு மாசம் இருப்போம் at 5 reps…) sat hinted 22–28 days silent while
    the ticket kept offering fresh ground — at 11 days to touchdown, the day-1
    aunt questions. This block cuts across the coverage sort on the staleness
    axis alone. A retest is a SESSION move — a scene that makes the item fire
    unaided — never a commission (the parked cold-decay item stays parked, and
    rechecks must not crowd the soak order out of new ground, the same call as
    slip retirement).

    Two corrections (2026-08-04), both found because the block was doing its job
    for the wrong five items:

    NEVER-SURFACED items are excluded, not featured. A hinted grade with no
    `last_surfaced` and no reps is a bootstrap artifact, not an item going dark
    — there is no prior test for a *re*-test to repeat. It also loses nothing by
    leaving: `coverage_key` leads with fewest-reps, so a never-worked item
    already sorts to the head of the main ticket. The old code ranked it FIRST
    here on sentinel staleness and printed "worth asking why", which spent the
    top slot of a five-item list on வை — a word carrying a grade nobody set.

    The sort carries `deck_rank`, so a sprint's own items lead. Without it the
    block ordered on staleness alone and ordinary vocabulary outranked the
    deck."""
    today = today or date.today()
    regs = deck_registers()
    out = []
    for w, r in lexicon.items():
        if r.get("production") != "hinted" or r.get("direction") == "catch":
            continue
        ds = days_since(r.get("last_surfaced"), today)
        if ds is None or ds < RETEST_DAYS:
            continue
        out.append({"word": w, "gloss": r.get("gloss", ""), "staleness": ds,
                    "reps": r.get("reps", 0), "deck": r.get("deck", "")})
    out.sort(key=lambda c: (deck_rank(c["word"], regs), -c["staleness"],
                            stable_jitter(c["word"])))
    return out[:max_n]


def slips_by_word(patterns: list[dict]) -> dict[str, list[dict]]:
    """Lexicon key → the live slip patterns that attach to it, worst first.

    Annotates a row Python ALREADY selected, so the bar is lower than the one
    format_slip_block uses: a single slip is not enough to commission a dose off
    (one is noise), but when the item is on the menu anyway, "last time he said
    pesa" is exactly what stops the next scene being the same scene."""
    out: dict[str, list[dict]] = {}
    for p in patterns:
        if not p["live"]:
            continue
        for w in p["words"]:
            out.setdefault(w, []).append(p)
    for rows in out.values():
        rows.sort(key=lambda p: p["count"], reverse=True)
    return out


def slip_note(patterns: list[dict]) -> str:
    """The one-line annotation hung off a selected item."""
    p = patterns[0]
    said = p["examples"][-1][1] if p["examples"] else ""
    times = f"{p['count']}×" if p["count"] > 1 else "once"
    tail = ("Not a repetition problem — teach the pattern."
            if p["count"] > 1 else "Worth one clause of contrast.")
    return (f"      ↳ SLIPPED {times} ({p['tag']})"
            + (f" — last time he said “{said}”. " if said else ". ") + tail)


def scene_spec(sidecars: list[dict], commissioned: str | None = None) -> dict:
    """The structural variety gate: register + form + dramatic ingredient,
    each forced to diverge from the last 3 episodes.

    A COMMISSIONED form overrides the form axis only — register and ingredient
    still diverge, so commissioning a shape never costs the variety it was not
    asked to decide."""
    n = len(sidecars)
    ingredient = pick_divergent(list(INGREDIENTS), "dramatic_ingredient", sidecars, n)
    return {
        "register": pick_divergent(REGISTERS, "register", sidecars, n),
        "form": commissioned or pick_divergent(FORMS, "episode_form", sidecars, n),
        "commissioned": bool(commissioned),
        "ingredient": ingredient,
        "ingredient_desc": INGREDIENTS[ingredient],
        "recent": [(c.get("mission"), c.get("register", "—"), c.get("episode_form", "—"))
                   for c in sidecars[:DIVERGENCE_WINDOW]],
    }


def main():
    parser = argparse.ArgumentParser(description="The session ticket: floor-gap + callbacks + new candidates")
    parser.add_argument("--floor-max", type=int, default=FOCUS_SIZE,
                        help=f"Max focus-set words to show (default {FOCUS_SIZE} — the whole cohort)")
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
            print("   One cold novel instance of this pattern = engine online.")

    # Trip Deck — the finite, deadline-driven sprint set. When it exists it is the
    # HEADLINE: force its not-yet-cold members first (Anna narrates the countdown).
    # One knock-log read, one ask count, both selectors — they share the ordering
    # law, so they must share the term that implements it.
    asked = recent_ask_counts(load_json(KNOCK_LOG_PATH) or [], lexicon)
    reps = rep_counts(lexicon)
    # One ledger read for the whole ticket: the deck list, the floor gap, and the
    # ledger block below all hang off it.
    slips = slip_patterns()
    slipped = slips_by_word(slips)
    deck = deck_status(lexicon, today=today, asked=asked, reps=reps)
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
            if t["word"] in slipped:
                print(slip_note(slipped[t["word"]]))
        hidden = len(deck["pending"]) - 12
        if hidden > 0:
            print(f"  … {hidden} more below the cut (least-recently-worked first — the tail rotates up)")
        if deck["catch_total"]:
            print(f"\n  EAR-ONLY ({deck['caught']}/{deck['catch_total']} solid) — eavesdrop/soak targets; "
                  f"win = recognition, never force these to fire:")
            for t in deck["catch_pending"][:8]:
                never = " · never worked" if t["staleness"] >= NEVER_SURFACED else ""
                print(f"  - [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{t['recognition']}{never}]")
                if t.get("pairs_with"):
                    print(f"      ↳ he answers: {t['pairs_with']} — {t['response_gloss'] or '[no gloss]'}"
                          f"  (drill the PAIR: hear it, answer it — recognition alone isn't the win here)")

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

    # 0. THE SLIP LEDGER — what he actually keeps getting wrong, ahead of the
    # commission because it is the evidence a commission is drawn FROM. Every
    # list below this answers "which item is due"; only this one answers "how is
    # he failing", and until 2026-07-30 nothing on the ticket answered that at
    # all. A floor-gap row says ரொம்ப நல்லா இருக்கு is not yet cold, so the ticket
    # re-offers it and the scene re-asks it the same way; the ledger says he has
    # reached for the present tense three times running, which is a different
    # lesson entirely.
    slip_block = format_slip_block(slips)
    if slip_block:
        print("\n★ SLIP LEDGER  (repeated mistakes — the primary signal for what to teach)")
        print("-" * 60)
        for line in slip_block:
            print(line)
        print("\n  A slip is not closed by being corrected — it closes when the right form")
        print("  fires unaided, later, in a scene that did not hand it over. Build for that.")

    retests = retest_targets(lexicon, today)
    if retests:
        print("\n★ HINTED, GOING DARK  (repped, then silent — retest cold in a scene)")
        print("-" * 60)
        for t in retests:
            age = f"{t['staleness']}d silent"
            deck_tag = " · DECK" if t["deck"] else ""
            print(f"  - {t['word']} — {t['gloss'] or '[no gloss]'}"
                  f"  [{t['reps']} rep{'s' if t['reps'] != 1 else ''} · {age}{deck_tag}]")
        print("  A hit fires it cold for real; a miss is honest data — log the slip.")

    # 0. THE COMMISSION — the repair that earned this dose, ahead of everything
    # the ticket computes. Before 2026-07-28 the order reached the Director only
    # as one prose clause in DIRECTOR ("read the soak-order in learner.json"), an
    # agentic read competing with a code-assembled list headed "DRILL these until
    # they fire cold". It lost: M77 dramatised the focus set and the commissioned
    # payload was absent. The FORM landed in the same run because it arrived as
    # computed context via scene_spec — so the commission arrives that way too.
    commission = episode_commission(learner)
    if commission:
        print("\n★ THE COMMISSION  (⚠ THIS OUTRANKS EVERY LIST BELOW — build the "
              "episode around it)")
        print("-" * 60)
        print("  PAYLOAD (must be audible in the script, repeatedly):")
        for item in [w for w in commission.get("payload", []) if w]:
            print(f"    → {item}")
        if commission.get("focus"):
            print(f"\n  FOCUS: {commission['focus']}")
        if commission.get("scene_seed"):
            print(f"\n  SCENE SEED: {commission['scene_seed']}")
        print(f"\n  Commissioned {commission.get('from', '—')} off a mistake Andrew is "
              f"still making. The lists below are the SEA this scene swims in; the")
        print("  payload above is what it is FOR. An episode that does not carry it "
              "has not filled the order, however good it is.")

    # 0. Scene spec — structural variety gate (audio episodes especially)
    spec = scene_spec(load_recent_sidecars(), commissioned_form(learner))
    print("\n0. SCENE SPEC  (force range; vary everything EXCEPT the vocabulary)")
    print("-" * 60)
    print(f"  Register:   {spec['register']}")
    print(f"  Form:       {spec['form']}"
          f"{'  ← COMMISSIONED by the soak order; do NOT re-pick' if spec['commissioned'] else ''}")
    print(f"  Ingredient: {spec['ingredient']} — {spec['ingredient_desc']}")
    if spec["recent"]:
        recent_str = ", ".join(f"M{m} {reg}/{form}" for m, reg, form in spec["recent"])
        print(f"  (diverging from last {DIVERGENCE_WINDOW}: {recent_str})")

    # 1. Floor-gap — two budgets. FOCUS is drilled; BACKGROUND is only exposed.
    print(f"\n1. FOCUS SET  (≤{FOCUS_SIZE} in dense rotation — DRILL these until they fire cold)")
    print("-" * 60)
    if commission:
        print("  ⚠ A COMMISSION IS LIVE (top of the ticket). It outranks this list — these are "
              "what the scene may draw on, not what it is about.")
    gap, background = floor_gap_targets(lexicon, today, args.floor_max,
                                        asked=asked, reps=reps,
                                        cohort=learner.get("focus_cohort"))
    if not gap:
        print("  (floor is clear — nothing recognized is stuck below cold)")
    # Which live slips attach to which floor-gap word. STUCK_REPS still stands on
    # its own evidence (median 2 reps to cold, p90 5) but it fires at 10 and only
    # ever says "this isn't working"; a slip fires at 2 and says WHAT isn't
    # working, which is the part a fresh scene needs in order to be different.
    for t in gap:
        tag = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
        rep = f"{t['reps']} rep{'s' if t['reps'] != 1 else ''}" if t["reps"] else "never drilled"
        cool = "  · asked in last 3d — vary the scene or take the next one" if t["asks"] else ""
        if t["reps"] >= STUCK_REPS:
            cool = (f"  · ⚠ STUCK — {t['reps']} reps and still not cold (most words take 2). "
                    f"Drilling it again won't work; change the angle.")
        print(f"  - {t['word']} — {t['gloss'] or '[no gloss]'}  [{tag} · {rep}]{cool}")
        if t["word"] in slipped:
            print(slip_note(slipped[t["word"]]))
    print("  Graduation is production going COLD. After that a word is never "
          "drilled again — it is just used.")

    if background:
        print(f"\n1a. BACKGROUND  ({len(background)} not yet started — EXPOSE, don't drill)")
        print("-" * 60)
        print("  Soak/episode candidates: work them into scenes so they stay warm and")
        print("  the tail can't rot. Never force these to fire — they are not the focus.")
        for t in background[:8]:
            print(f"  - {t['word']} — {t['gloss'] or '[no gloss]'}")
        if len(background) > 8:
            print(f"  … {len(background) - 8} more waiting behind them")

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
        print("  Words outside this list must be answerable from context within seconds.")
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
