#!/usr/bin/env python3
"""
The session "ticket" — the menu Python hands Anna so he never picks words by
eyeballing a 2000-line lexicon. Anna chooses the story and meaning; this script
computes the candidate set. The bright line: Python computes the menu, Anna
makes the choice.

THREE SELECTORS (2026-08-18, the deck retirement — it was nine, and three of them
claimed primacy in their own words, so whichever one Anna weighted that day
decided the session):
  1. THE POOL — everything not yet firing cold, ordered survival > delight >
     dessert (`tier_rank`, read off each row's `register`) and split into TWO
     BUDGETS. The focus set is ≤FOCUS_SIZE in dense rotation, drilled until they
     fire cold and then never drilled again; the background is exposure only —
     soak them into scenes so the tail can't rot, never force them to fire. One
     ranked list cannot do both jobs, and trying made it do neither. The ear
     (1a), coverage (1c) and the engines (1d) are views of this same population,
     not rival pools.
  2. DUE CALLBACKS — decay, reusing generate_callbacks.py (no duplicated logic).
     A different job from the pool: not "what is due" but "what is fading".
  3. NEW CANDIDATES BY CLUSTER — priority-1 word_pool entries not yet in the
     lexicon, grouped by cluster with a coverage stat so Anna can see which
     clusters are thin. Python shows coverage; Anna picks the cluster.

TWO READERS, AND THEY DO NOT GET THE SAME PAGE (2026-08-21). Anna reads the bare
command; the Director reads `--fence`. Measured against Anna's real load, the
ticket was 8,346 tokens and he could act on roughly 1,200 of them:
  - THE VOCABULARY FENCE (65% of the whole ticket) is the Architect's "sea"
    (architect.md) and no protocol file asks Anna to read it. Behind --fence.
  - THE SLIP LEDGER was printed here AND by `status`, both of which Anna loads
    every session — the same 21 lines twice. `status` keeps it (the knock lane
    reads that digest too); this file no longer repeats it. The per-row
    "SLIPPED once (…)" annotations stay: those are per-item, not the ledger.
  - BACKGROUND is not printed at all (Andrew, 2026-08-21): "EXPOSE, don't drill"
    is an instruction to the render lanes, which stamp exposure themselves.

Usage:
    python scripts/suggest_targets.py                 # Anna's menu
    python scripts/suggest_targets.py --fence         # + the Architect's sea
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from generate_callbacks import due_callbacks, load_json, days_since, NEVER_SURFACED
from slips import slip_patterns
from state_io import is_unseen, soak_pending, local_today

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
# How long a fired ask suppresses re-asking the same item. 3 → 7 (2026-08-18).
#
# THE WINDOW MUST EXCEED ANDREW'S REPLY LATENCY, or it expires before he ever
# answers and the guard protects nothing. The incident: `இன்னொரு தடவ சொல்லுங்க`
# was asked 08-09 (fielding), 08-12 (volley 3/4) and 08-16 (challenge) — gaps of
# exactly 3 and 4 days, so every re-ask landed just outside a 3-day window. Over
# that stretch he answered 4 of 14 knocks (jet lag, first week in country), so
# his real latency was 4–7 days against a 3-day guard.
#
# This is the second half of KF-6's law. That fix stopped the same ask firing
# under different move names by counting asks; it assumed an ask would be
# answered within the window. An UNANSWERED ask never sets `last_surfaced`, so
# the item stays maximally stale and silence makes it MORE eligible, not less —
# the guard is the only thing standing against that, and it was too short.
ASK_COOLDOWN_DAYS = 7


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

    Not to be confused with `recent_ask_counts`, which is an `ASK_COOLDOWN_DAYS`
    COOLDOWN — a
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
    """THE ordered pool — every row not yet firing cold, tier-first. TWO BUDGETS,
    not one ranked list (2026-07-26):

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

    THE MERGE (2026-08-18, the deck retirement). This was "the general floor —
    everything OUTSIDE the deck", one of three ticket sections claiming primacy
    in its own words, on a 361-line ticket where whichever one Anna weighted that
    day decided the session. Three pools became this one:

      TRIP DECK        the tier ordering, now `tier_rank` on every row. The
                       recognition gate went with it: the deck's pending rows
                       were 31/35 `struggled`, which this pool used to exclude
                       outright, so keeping that gate would have made the whole
                       migrated set unreachable — the ordering surviving with
                       nothing left to order. Teach-first still holds through the
                       `unseen` flag, which every consumer already reads.
      HINTED, GOING DARK  a retest RULE (`RETEST_DAYS`), not a rival pool — see
                       the reservation below.

    What the deck proved and this keeps: a finite, visible, ordered set beats an
    undifferentiated 339-row ledger. `FOCUS_SIZE` is that finite set now; what
    expired is the deadline and the separate container.

    `cohort` is the stored membership; None loads it from learner.json. A held
    word that graduated (or left the pool population) vacates its seat here; open
    seats are filled from the front of the background order. Persisting the
    result is the WRITE seams' job (`reconcile_focus` via sync_state /
    knock_reply), never this reader's."""
    if asked is None:
        asked = recent_ask_counts(load_json(KNOCK_LOG_PATH) or [], lexicon)
    if reps is None:
        reps = rep_counts(lexicon)
    if cohort is None:
        cohort = stored_focus_cohort()
    gap = []
    for w, r in lexicon.items():
        if r.get("type") == "pattern":
            continue  # patterns are forced via the Engines block, not the word pool
        if r.get("direction") == "catch":
            continue  # ear-only — never forced to fire; `ear_targets` owns them
        if r.get("production") == "cold":
            continue  # graduated: never drilled again, just used
        ds = days_since(r.get("last_surfaced"), today)
        staleness = NEVER_SURFACED if ds is None else ds
        gap.append({
            "word": w, "gloss": r.get("gloss", ""),
            "recognition": r.get("recognition"), "production": r.get("production", "none"),
            "register": r.get("register", ""), "tier_rank": tier_rank(r),
            "tier": TIER_NAMES[tier_rank(r)],
            "staleness": staleness, "soaked": len(r.get("seen_in", [])),
            "exposures": r.get("exposures", 0), "unseen": is_unseen(r),
            "retest": is_going_dark(r, ds),
            "asks": asked.get(w, 0), "reps": reps.get(w, 0),
        })
    by_word = {c["word"]: c for c in gap}
    if cohort:
        # Stored membership: held seats stand regardless of what any counter
        # says. Graduates (and words that left the pool population) drop out
        # of `by_word` and so vacate their seats here.
        focus = [by_word[w] for w in cohort if w in by_word][:FOCUS_SIZE]
    else:
        # SEED derivation — no cohort stored yet. Words already started hold
        # seats (most-repped first: they are mid-fight, benching them is the
        # churn the stored cohort exists to prevent).
        focus = sorted((c for c in gap if c["reps"]),
                       key=lambda c: (-c["reps"], stable_jitter(c["word"])))[:FOCUS_SIZE]
    held = {c["word"] for c in focus}
    background = sorted((c for c in gap if c["word"] not in held), key=pool_key)
    seats_open = FOCUS_SIZE - len(focus)
    if seats_open > 0:
        focus += take_seats(background, seats_open)
        taken = {c["word"] for c in focus}
        background = [c for c in background if c["word"] not in taken]
    for c in focus:
        c["band"] = "focus"
    for c in background:
        c["band"] = "background"
    # Within the focus set, tier first, then least-asked. The cooldown applies
    # INSIDE the set: a word asked inside the cooldown drops behind its
    # cohort-mates for a couple of days. That is the job `asks` was built for
    # and the only job it does now.
    focus.sort(key=lambda c: (c["tier_rank"], c["asks"], coverage_key(c)))
    return (focus[:max_n], background)


def take_seats(background: list[dict], seats: int) -> list[dict]:
    """Fill the focus set's open seats, holding up to RETEST_SLOTS for items
    going dark.

    A FLOOR, NEVER A CEILING — the idiom `generate_callbacks` already uses for
    PATTERN_SLOTS. When dark items win seats on the ordering itself the natural
    order stands untouched; the reservation only tops up the case where they won
    none. Capping instead would demote them in the very situation the seat exists
    to protect.

    This is what "HINTED, GOING DARK" became (2026-08-18). It was its own ticket
    section because `coverage_key` leads with fewest-LIFETIME-reps, so a
    repped-but-stale hinted row sorts behind every never-worked row in its tier
    FOREVER — the three FAQ answers sat hinted 22-28 days silent at 11 days to
    touchdown. Folding it in must not cost that reachability, which is the whole
    reason it is a reservation and not a flag: a flag on a row nothing selects
    changes nothing, and that is the silent no-op Gate 7.2 names."""
    natural = background[:seats]
    reserved = min(RETEST_SLOTS, seats // 2)
    if sum(1 for c in natural if c["retest"]) >= reserved:
        return natural
    dark = [c for c in background if c["retest"]][:reserved]
    rest = [c for c in background if not c["retest"]][:seats - len(dark)]
    return sorted(dark + rest, key=pool_key)


def pool_key(c: dict) -> tuple:
    """The pool's own order: the touchdown bar, then the shared law. Callers may
    prefix (the focus set adds the ask cooldown) but may not reorder or drop."""
    return (c["tier_rank"], coverage_key(c))


def reconcile_focus(lexicon: dict, cohort: list[str], today=None) -> list[str]:
    """The WRITE side of the stored cohort: leave on graduation, enter on
    seat-open (2026-07-26). Pure — returns the new membership, sorted for diff
    stability; the callers that persist it are the two seams where graduation
    can happen (sync_state.cmd_update and knock_reply's judge flow)."""
    focus, _bg = floor_gap_targets(lexicon, today or local_today(), FOCUS_SIZE,
                                   asked={}, cohort=cohort)
    return sorted(c["word"] for c in focus)


# The touchdown bar (2026-07-13, Andrew — supersedes "deck tiering rejected"
# 2026-07-09): survival (fast speech aimed at him — repair it, transact, don't
# freeze) outranks delight (the visible-trying wins at the family table);
# gossip/zinger are soak & dessert.
#
# KEPT PAST THE TRIP IT WAS CUT FOR (2026-08-18, the deck retirement). The deck
# was a CONTAINER — 83 rows, bounded, deadline-driven — and its reason expired at
# touchdown. This is an ORDERING, and it is durable knowledge about which
# failures cost most at a table. Retiring the one had to not delete the other, so
# `register` moved onto the lexicon row (through `sync_state seed-deck`, the
# writer path) and the curriculum-file join died with the container.
REGISTER_TIERS = {"antifreeze": 0, "public": 0, "frame": 0,
                  "faq": 1, "mil-table": 1, "social": 1,
                  "gossip": 2, "zinger": 2}
TIER_NAMES = {0: "survival", 1: "delight", 2: "dessert"}
# Seats held for items going dark, inside the focus set. See `floor_gap_targets`
# — a FLOOR, never a ceiling, the same shape as generate_callbacks' PATTERN_SLOTS.
RETEST_SLOTS = 2


def tier_rank(rec: dict) -> int:
    """THE tier prefix, defined once so every ordering reads one definition
    instead of a hand-copy.

    Extracted 2026-08-04 for the same reason `coverage_key` was on 07-26 — the
    term was hand-copied into two sorts and `retest_targets` (2026-08-01) was
    written without it at all. Consequence, found 8 days from touchdown: the
    three hinted FAQ answers — the questions every relative asks on day one,
    25-31 days silent — sat below a five-item cut behind ordinary words that
    happened to be staler. A single-axis sort is the recurring bug; the prefix
    belongs to the law.

    REPOINTED AT THE LEXICON 2026-08-18. It used to take a `word` and a `regs`
    map joined from `curriculum/trip_deck.json`, and ranked every non-member LAST
    (3) — correct while a bounded sprint had to not be crowded out by ordinary
    vocabulary, and meaningless the moment the container retired. Reading the row
    is also what makes the retirement safe: the join was keyed on `deck`
    membership, so deleting the tag would have dropped the ordering SILENTLY
    (Gate 7.2 — the selector keeps returning rows, they are simply no longer
    ordered, and every instrument reads green).

    An unregistered row degrades to delight (1). 256 of 339 rows carry no
    register and unordered-but-not-broken is the intended graceful degradation;
    classifying all 339 is a curriculum project, not this one."""
    return REGISTER_TIERS.get(rec.get("register", ""), 1)


def recent_ask_counts(klog: list, lexicon: dict, days: int = ASK_COOLDOWN_DAYS, now=None) -> dict:
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


def is_going_dark(rec: dict, staleness: int | None) -> bool:
    """A hinted item that has gone silent — the follow-up path hinted never had
    (2026-08-01; DECISIONS 07-28 called it "open and unanswered": cold is a
    one-way door and hinted was a no-way door).

    NEVER-SURFACED rows are excluded, not featured (2026-08-04). A hinted grade
    with no `last_surfaced` is a bootstrap artifact, not an item going dark —
    there is no prior test for a *re*-test to repeat. It also loses nothing by
    leaving: `coverage_key` leads with fewest-reps, so a never-worked row already
    sorts to the head of the pool. The old code ranked it FIRST on sentinel
    staleness and printed "worth asking why", spending the top slot on a word
    carrying a grade nobody set.

    Ear-only rows are excluded too — a retest is a PRODUCTION move."""
    return (rec.get("production") == "hinted"
            and rec.get("direction") != "catch"
            and staleness is not None and staleness < NEVER_SURFACED
            and staleness >= RETEST_DAYS)


# THE EAR'S POOL IS NOT THE CATCH TAG (2026-08-25). `direction: "catch"` answers a
# PRODUCTION question — never force this to fire — and it was doing double duty as
# the ear pool's membership test. That made a row have to be FORBIDDEN from
# production to be ELIGIBLE for ear work, and the two are independent.
#
# What it cost, measured on the live ledger the day this changed: 21 of the 26
# machines fire cold (the engines meter reads 21/21, saturated) and 3 are solid on
# the ear — he can SAY them and cannot HEAR them. Only 5 carried the catch tag, so
# the axis `sync_state status` prints as PRIMARY STEER (2026-08-16) could reach the
# ticket with 5 of its 26 rows. Exactly the failure `generate_callbacks` fixed for
# the callback lane on 08-17 — "eligible in principle and reachable in fact are two
# different things" — one lane over, never made here.
#
# A FLOOR, NEVER A CEILING, the same idiom as PATTERN_SLOTS and `take_seats`: the
# reservation only tops up the case where machines won no seat on the ordering
# itself. Capping would demote them in the one situation the seat exists to protect.
EAR_PATTERN_SLOTS = 4


def ear_targets(lexicon: dict, today=None, reps: dict | None = None) -> dict:
    """Comprehension targets: rows he has MET and cannot yet hear.

    Two populations, one queue, and they need OPPOSITE instructions:

      - `direction: "catch"` — ear-ONLY. Forcing them to fire is the mistake and
        they clear on recognition alone. That law is untouched.
      - the machines (`type: "pattern"`). He produces them and does not hear them,
        so ear work here is a soak/eavesdrop dose that simply does not ban a fire.

    `ear_only` carries the difference to every caller. One line for both is how the
    catch law gets lost — `due_menu_block` prints "never ask him to fire it", which
    is true of a catch row and false of a machine he fires cold every session.

    NOT a rival to the callback lane, and the division is deliberate: word-level ear
    return is `generate_callbacks`' job (every row, every level, recognition-keyed
    intervals). This queue is the machines and the catch pairs — the inventory that
    carries the sentence skeleton, and the one a menu can actually be made of.

    NEVER-SURFACED ROWS STAY IN, and this queue is the exception to the callbacks'
    met-only rule (tried and reverted 2026-08-25, caught by the s-cadence case before
    it shipped). A callback is a RETURN clock, so it returns what was met. This is a
    COVERAGE queue — `coverage_key` leads with fewest-lifetime-reps precisely so the
    never-worked row sorts to the head — and for a catch row, never-worked is not a
    row awaiting first contact elsewhere: the eavesdrop dose IS its first contact,
    and it advances through that dose and no other. Excluding them emptied the pool
    that `morning_knock.remaining_room` reads to decide the eavesdrop cadence is
    overdue, which is a warning going silent, behind a bare `except: pass`.

    Was the catch half of `deck_status` (retired 2026-08-18); the catch tag alone
    until 2026-08-25 — see EAR_PATTERN_SLOTS for what that cost."""
    today = today or local_today()
    if reps is None:
        reps = rep_counts(lexicon)

    def stale(r: dict) -> int:
        ds = days_since(r.get("last_surfaced"), today)
        return NEVER_SURFACED if ds is None else ds

    pool = [(w, r) for w, r in lexicon.items()
            if r.get("direction") == "catch" or r.get("type") == "pattern"]

    pending = [{
        "word": w, "gloss": r.get("gloss", ""),
        "kind": "frame" if r.get("type") == "pattern" else r.get("type", "chunk"),
        "recognition": r.get("recognition"), "staleness": stale(r),
        "last_surfaced": r.get("last_surfaced"),
        # Ear-only is the CATCH TAG, never "is it in this queue" — a machine sits
        # here precisely because his ear is behind his mouth on it.
        "ear_only": r.get("direction") == "catch",
        # The pair, resolved for the drill: hear this, say that. A catch item
        # with a partner is drillable as a UNIT — recognizing it is only half
        # the win if the answer doesn't arrive (2026-07-26).
        "pairs_with": r.get("pairs_with"),
        "response_gloss": lexicon.get(r.get("pairs_with") or "", {}).get("gloss", ""),
        "reps": reps.get(w, 0), "soaked": len(r.get("seen_in", [])),
        "exposures": r.get("exposures", 0),
        "production": r.get("production", "none"),
    } for w, r in pool if r.get("recognition") != "solid"]
    pending.sort(key=coverage_key)

    # The machines' reserved seats — a top-up, only when the natural order starved
    # them. Words outnumber machines in this queue and decay on the same clock, so
    # the majority wins every seat forever unless the minority is held one.
    held = [c for c in pending[:EAR_PATTERN_SLOTS] if c["kind"] == "frame"]
    if len(held) < EAR_PATTERN_SLOTS:
        seated = {c["word"] for c in
                  [c for c in pending if c["kind"] == "frame"][:EAR_PATTERN_SLOTS]}
        pending = ([c for c in pending if c["word"] in seated]
                   + [c for c in pending if c["word"] not in seated])

    return {"total": len(pool), "pending": pending,
            "caught": sum(1 for _, r in pool if r.get("recognition") == "solid"),
            "untouched": sum(1 for _, r in pool if not r.get("last_surfaced"))}


def register_coverage(lexicon: dict, today=None) -> dict | None:
    """COVERAGE, not progress — the meter a cold/total headline can't see. That
    one answers "how many fire cold?"; this answers "how many have ever been
    WORKED at all?" (a session rep, a judged reply, or a show dose — anything
    that sets `last_surfaced`). An ask with no reply does not count, which is
    exactly why `recent_ask_counts` is a sort term and not this meter.

    The pair matters because a value-ordered queue starves its tail silently: on
    2026-07-25 the headline read 15/34 survival at 3.4 cold/day against a needed
    1.1 — a won sprint — while 50 of 70 fire items had never been worked at all,
    and the two survival registers that decide freezing at the table
    (antifreeze, public) sat at 3/18.

    GENERALISED off the deck 2026-08-18: it buckets by `register`, which is now a
    property of the row, so it is no longer scoped to one container and any
    future curated set is metered the day it is seeded. Rows with no register
    are reported as one `unregistered` bucket rather than folded into delight —
    256 of 339 would swamp the tier they degrade into and hide the very
    distribution this block exists to show.

    `soaked_only` = never worked, but heard in an episode: a different state from
    never encountered, and the cheaper one to fix."""
    today = today or local_today()

    def bucket() -> dict:
        return {"total": 0, "touched": 0, "untouched": 0, "cleared": 0}

    # Tier/register buckets are the FIRE side only. The ear gets its own bucket;
    # folding it into the tiers would inflate survival with catch frames.
    tiers: dict[str, dict] = {}
    registers: dict[str, dict] = {}
    untouched: list[dict] = []
    fire, catch, unregistered = bucket(), bucket(), bucket()
    for w, r in lexicon.items():
        is_catch = r.get("direction") == "catch"
        reg = r.get("register", "")
        worked = bool(r.get("last_surfaced"))
        done = (r.get("recognition") == "solid") if is_catch else (r.get("production") == "cold")
        if is_catch:
            buckets = [catch]
        elif reg:
            buckets = [fire, tiers.setdefault(TIER_NAMES[tier_rank(r)], bucket()),
                       registers.setdefault(reg, bucket())]
        else:
            buckets = [unregistered]
        for b in buckets:
            b["total"] += 1
            b["touched" if worked else "untouched"] += 1
            b["cleared"] += done
        if reg and not worked and not done:
            untouched.append({
                "word": w, "gloss": r.get("gloss", ""), "tier": TIER_NAMES[tier_rank(r)],
                "register": reg, "direction": "catch" if is_catch else "fire",
                "soaked_only": bool(r.get("seen_in")),
            })
    if not (fire["total"] or catch["total"]):
        return None
    untouched.sort(key=lambda c: (tier_rank(c), c["word"]))
    return {"tiers": tiers, "registers": registers, "untouched": untouched,
            "fire": fire, "catch": catch, "unregistered": unregistered}


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


def drill_menu(lexicon: dict, today=None, asked: dict | None = None,
               reps: dict | None = None, max_n: int = FOCUS_SIZE) -> list[dict]:
    """The pool's head as one flat production menu — what the knock lane, the
    volley and the drill tape all pick from.

    It is a VIEW, not a pool: the focus set plus the engines, which are the same
    population seen through two gates (`floor_gap_targets` skips patterns because
    a pattern is forced by producing a NOVEL instance, not by reciting a line —
    that is the Engines block's whole job). Composed once here because all three
    lanes need exactly this composition, and hand-copying a composition into
    three files is the failure this module keeps recording (`coverage_key`
    07-26, `tier_rank` 08-04).

    Engines carry no register, so they land at delight and sort among the rest by
    the shared law. UNSEEN items ride WITH their flag rather than being dropped —
    the teach-first law is the caller's to apply, and the two callers apply it
    differently on purpose (the menu SHOWS them marked; a volley EXCLUDES them,
    because a volley is a cold demand and a menu is not)."""
    focus, _bg = floor_gap_targets(lexicon, today or local_today(), max_n,
                                   asked=asked, reps=reps)
    menu = [{"word": t["word"], "gloss": t["gloss"], "kind": "chunk",
             "production": t["production"], "recognition": t["recognition"],
             "tier": t["tier"], "tier_rank": t["tier_rank"], "unseen": t["unseen"],
             "retest": t["retest"], "asks": t["asks"], "reps": t["reps"],
             "staleness": t["staleness"], "exposures": t["exposures"]}
            for t in focus]
    if reps is None:
        reps = rep_counts(lexicon)
    for e in engines_to_fire(lexicon):
        r = lexicon.get(e["key"], {})
        ds = days_since(r.get("last_surfaced"), today or local_today())
        menu.append({"word": e["key"], "gloss": e["gloss"], "kind": "frame",
                     "production": e["production"], "recognition": r.get("recognition"),
                     "tier": TIER_NAMES[tier_rank(r)], "tier_rank": tier_rank(r),
                     "unseen": e["unseen"], "retest": is_going_dark(r, ds),
                     "asks": (asked or {}).get(e["key"], 0), "reps": reps.get(e["key"], 0),
                     "staleness": NEVER_SURFACED if ds is None else ds,
                     "exposures": r.get("exposures", 0)})
    menu.sort(key=lambda c: (c["tier_rank"], c["asks"], coverage_key(c)))
    return menu[:max_n]


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
        # The curriculum schema's key is "word" (2026-08-28). A language NAME in
        # a data contract is the one leak no constants file can contain, because
        # it travels in every deck a fork writes; language-tutor had already
        # chosen "word" for this field, so the two schemas now agree.
        word = entry["word"]
        if word in c["seen"]:
            continue  # word_pool has a few duplicate rows
        c["seen"].add(word)
        c["total"] += 1
        if word in lexicon:
            c["known"] += 1
        else:
            c["candidates"].append({"word": word, "gloss": entry.get("gloss", "")})

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
    # THE FENCE IS THE ARCHITECT'S, NOT ANNA'S (2026-08-21). It is the full list
    # of recognized words — "the sea" (architect.md:98) — and at 219 lines it was
    # 65% of the ticket's tokens and the single largest thing Anna loaded all
    # session. He cannot act on it: no protocol file asks him to read it, and the
    # coverage rule it feeds is a studio rule. run_studio passes --fence for the
    # Director; the bare command is Anna's and no longer carries it.
    parser.add_argument("--fence", action="store_true",
                        help="include the Vocabulary Fence (the Director needs it; Anna does not)")
    args = parser.parse_args()

    lexicon = load_json(LEXICON_PATH)
    word_pool = load_json(WORD_POOL_PATH)
    learner = load_json(BASE / "progress" / "learner.json") or {}
    # An EMPTY lexicon ({}) is a valid day-zero state — the ticket still serves
    # the new-candidates section. Only a MISSING file is an error.
    if lexicon is None or not word_pool:
        print("Error: lexicon.json or word_pool.json not found. See BOOTSTRAP.md.")
        return
    today = local_today()

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

    # One knock-log read and one ask count for the whole ticket — the pool and
    # the ledger block below both hang off them.
    asked = recent_ask_counts(load_json(KNOCK_LOG_PATH) or [], lexicon)
    reps = rep_counts(lexicon)
    slips = slip_patterns()
    slipped = slips_by_word(slips)

    # THE SLIP LEDGER — what he actually keeps getting wrong, ahead of the
    # commission because it is the evidence a commission is drawn FROM. Every
    # list below this answers "which item is due"; only this one answers "how is
    # he failing", and until 2026-07-30 nothing on the ticket answered that at
    # all. NOT A RIVAL AND NOT A HEADLINE (2026-08-18): it called itself "the
    # primary signal for what to teach" while `machines heard` called itself the
    # PRIMARY STEER and the deck called itself the sprint headline. Three claims
    # to the same throne on one ticket meant the day's session was decided by
    # whichever section Anna weighted that morning. The division is real and it
    # is stated instead: machines heard steers WHAT, this steers HOW.
    #
    # A pool row says ரொம்ப நல்லா இருக்கு is not yet cold, so the ticket
    # re-offers it and the scene re-asks it the same way; the ledger says he has
    # reached for the present tense three times running, which is a different
    # lesson entirely.
    # THE LEDGER IS PRINTED BY `status`, AND NOT AGAIN HERE (2026-08-21).
    # format_slip_block had two live callers and Anna loads BOTH of them every
    # session — session_brief (the status digest) and this ticket — so the whole
    # block arrived verbatim twice, 21 identical lines. The studio, the ticket's
    # other reader, has never referenced it: zero hits for "slip" across
    # protocol/studio/. So the duplicate is pure cost to the one reader who
    # already had it, and a block the other reader never wanted. `slips` is still
    # computed above — the pool annotates individual rows with "SLIPPED once (…)"
    # from it, which is per-item and not a duplicate of the ledger.

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

    # 1. The pool — two budgets. FOCUS is drilled; BACKGROUND is only exposed.
    # Tier-ordered (survival > delight > dessert), the one thing the retired deck
    # leaves behind. No section on this ticket claims primacy any more: `machines
    # heard` steers WHAT, the slip ledger steers HOW, and those are not rivals.
    print(f"\n1. FOCUS SET  (≤{FOCUS_SIZE} in dense rotation — DRILL these until they fire cold)")
    print("-" * 60)
    if commission:
        print("  ⚠ A COMMISSION IS LIVE (top of the ticket). It outranks this list — these are "
              "what the scene may draw on, not what it is about.")
    gap, background = floor_gap_targets(lexicon, today, args.floor_max,
                                        asked=asked, reps=reps,
                                        cohort=learner.get("focus_cohort"))
    if not gap:
        print("  (the pool is clear — nothing is stuck below cold)")
    # Which live slips attach to which pool word. STUCK_REPS still stands on
    # its own evidence (median 2 reps to cold, p90 5) but it fires at 10 and only
    # ever says "this isn't working"; a slip fires at 2 and says WHAT isn't
    # working, which is the part a fresh scene needs in order to be different.
    for t in gap:
        tag = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
        rep = f"{t['reps']} rep{'s' if t['reps'] != 1 else ''}" if t["reps"] else "never drilled"
        cool = f"  · asked in last {ASK_COOLDOWN_DAYS}d — vary the scene or take the next one" if t["asks"] else ""
        if t["reps"] >= STUCK_REPS:
            cool = (f"  · ⚠ STUCK — {t['reps']} reps and still not cold (most words take 2). "
                    f"Drilling it again won't work; change the angle.")
        if t["unseen"]:
            cool += "  · ⚠ UNSEEN — teach first (show it, gloss it), NEVER cold-quiz"
        print(f"  - [{t['tier']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{tag} · {rep}]{cool}")
        if t["retest"]:
            # What "HINTED, GOING DARK" became: a rule inside the pool, not a
            # rival list. A hit fires it cold for real; a miss is honest data.
            print(f"      ↳ GOING DARK — {t['staleness']}d silent since it was hinted. "
                  f"Retest it cold in a scene that does not hand it over.")
        if t["word"] in slipped:
            print(slip_note(slipped[t["word"]]))
    print("  Graduation is production going COLD. After that a word is never "
          "drilled again — it is just used.")

    ear = ear_targets(lexicon, today=today, reps=reps)
    if ear["total"]:
        # NO RATIO IN THIS HEADER (2026-08-25). It read "3/12 solid" while the
        # meters — where a number belongs — print Machines heard 3/26 two surfaces
        # away. A menu that carries its own score invites reading it as progress;
        # the ticket's job in this block is WHICH, never HOW MANY.
        print("\n1a. THE EAR  (comprehension — the primary steer; win = recognition, "
              "never a fire)")
        print("-" * 60)
        for t in ear["pending"][:8]:
            never = " · never worked" if t["staleness"] >= NEVER_SURFACED else ""
            # A machine sits here because his EAR is behind his MOUTH on it — 21 of
            # 26 fire cold, 3 are heard. Say which, or the block reads as one
            # do-not-fire list and the catch law quietly widens to cover them.
            axis = "" if t["ear_only"] else "  · he FIRES this — the ear is what is behind"
            print(f"  - [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{t['recognition']}{never}]{axis}")
            if t.get("pairs_with"):
                print(f"      ↳ he answers: {t['pairs_with']} — {t['response_gloss'] or '[no gloss]'}"
                      f"  (drill the PAIR: hear it, answer it — recognition alone isn't the win here)")

    # BACKGROUND IS NOT PRINTED (Andrew, 2026-08-21). It listed 8 of ~236 rows
    # not yet started under "EXPOSE, don't drill" — a block with no action verb
    # for the one reader who gets it. The exposure it asks for is stamped by the
    # render lanes, not by Anna, so nothing was ever waiting on him to read it.
    # `background` is still computed: floor_gap_targets returns the split and the
    # FOCUS budget is defined against it, so the number still does work upstream.

    cov = register_coverage(lexicon, today=today)
    if cov and cov["fire"]["total"]:
        print("\n1c. COVERAGE  (how many have been WORKED — the meter cold/total can't see)")
        print("  ENGINEERING NUMBERS — they steer selection; they are never narrated to Andrew.")
        print("-" * 60)
        for tier in ("survival", "delight", "dessert"):
            b = cov["tiers"].get(tier)
            if not b:
                continue
            regs_in = sorted((r, x) for r, x in cov["registers"].items()
                             if TIER_NAMES[tier_rank({"register": r})] == tier)
            detail = ", ".join(f"{r} {x['touched']}/{x['total']}" for r, x in regs_in)
            flag = "  ⚠" if b["untouched"] else ""
            print(f"  {tier:12} worked {b['touched']:3}/{b['total']:3} · cold {b['cleared']:3}{flag}"
                  + (f"   ({detail})" if detail else ""))
        c = cov["catch"]
        if c["total"]:
            print(f"  {'ear-only':12} worked {c['touched']:3}/{c['total']:3} · solid {c['cleared']:3}"
                  + ("  ⚠" if c["untouched"] else ""))
        u = cov["unregistered"]
        if u["total"]:
            print(f"  {'unranked':12} worked {u['touched']:3}/{u['total']:3} · cold {u['cleared']:3}"
                  f"   (no register — they sort as delight; ranking them is a curriculum job)")
        if cov["untouched"]:
            u_fire = [x for x in cov["untouched"] if x["direction"] == "fire"]
            u_catch = [x for x in cov["untouched"] if x["direction"] == "catch"]
            soaked = sum(1 for x in cov["untouched"] if x["soaked_only"])
            ear_str = f" + {len(u_catch)} ear-only" if u_catch else ""
            print(f"\n  ⚠ NEVER WORKED, among the ranked: {len(u_fire)} fire item(s){ear_str} "
                  f"({soaked} heard in an episode but never asked).")
            starving = [f"{r} ({x['untouched']})" for r, x in sorted(
                cov["registers"].items(), key=lambda kv: -kv[1]["untouched"])
                if x["untouched"]]
            if starving:
                print("     Starving registers: " + ", ".join(starving))
            print("     They sort to the head of their tier — fire from the top and this drains.")

    # 1d. Engines — generative patterns to force a novel instance of
    engines = engines_to_fire(lexicon)
    if engines:
        print("\n1d. ENGINES TO FIRE  (patterns — force a NOVEL instance, not a memorized line)")
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
        # Tag by the axis that SELECTED the row (2026-08-17), matching
        # generate_callbacks' own render. Reading `production` here labelled a
        # struggled frame pulled back for decay as "[retention]" — the Director
        # reads this block, so the tag was actively misdirecting the payload.
        tag = cb["recognition"] + (" · ear" if cb.get("direction") == "catch" else "")
        print(f"  - {cb['word']} — {cb['gloss'] or '[no gloss]'}  [{tag}]")

    # 3. New candidates by cluster — Anna picks the cluster
    print("\n3. NEW CANDIDATES BY CLUSTER  (priority-1, not yet met — pick a thin cluster)")
    print("-" * 60)
    ranked, per_cluster = new_candidates_by_cluster(lexicon, word_pool, args.clusters, args.per_cluster)
    if not ranked:
        print("  (no priority-1 clusters with unmet words)")
    for name, c in ranked:
        print(f"  [{name}]  known {c['known']}/{c['total']}")
        for cand in c["candidates"][:per_cluster]:
            print(f"      - {cand['word']} — {cand['gloss']}")

    # 4. Vocabulary fence — the sea the Architect swims in. Studio-only (--fence).
    if not args.fence:
        return
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
