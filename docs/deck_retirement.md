# Work Order — Retire the Trip Deck

> **Status: DECIDED, NOT EXECUTED.** Andrew, 2026-08-18: *"my vote is to retire the deck now…
> Un-muddying the waters isn't a future nice to have. I think deletion, cleanup should ease a lot
> of the other symptoms I am feeling. Instead of a dozen patchwork fixes in the coming weeks."*
> Scoped in the same conversation; execution deliberately deferred to a fresh context.
> **Read this whole file before touching anything** — step 0 is load-bearing and non-obvious.

## Why

The deck is a **container** (83 rows tagged `deck: "trip"`, bounded, deadline-driven). The tiers
are an **ordering** (`survival > delight > dessert`). The container's reason expired at touchdown
(2026-08-12); the ordering is durable knowledge about which failures cost most at a table.

The measured cost of keeping it: the session ticket is **361 lines across 9 pools**, and three of
them claim primacy in their own words — Trip Deck (*"the sprint headline — force these before the
general floor"*), Slip Ledger (*"the primary signal for what to teach"*), and Machines heard
(*"PRIMARY STEER"*). Whichever section Anna weights that day decides the session.

The deeper pattern: every pedagogical insight since July got a **new pool** — deck (07-13), focus
set (07-26), hinted-going-dark (08-01), callbacks, slip ledger, machines heard (08-16). Each
earned its place; none ever retired another. That is the accumulation failure mode `JOURNEY.md`
names as this project's worst tendency, expressed in selection surfaces rather than prose. Prose
got word budgets in July for exactly this reason. Selection never got the equivalent.

The deck is also a **production** construct (`X/N fire cold`), so it optimises the axis demoted on
2026-08-16, and its motivational device — a winnable countdown — is what the 08-17 no-numbers rule
banned.

**In fairness, it worked.** Survival went 15/34 (07-25) → 30/34 (08-18), the best conversion this
project has produced. The lesson to keep: *a finite, visible, ordered set beats an undifferentiated
339-row ledger.* What expired is the deadline and the separate container, not the idea.

## The invariant

**Retiring the container must not delete the ordering.** Everything else is negotiable.

---

## Step 0 — Migrate `register` onto lexicon rows (DO THIS FIRST)

**The trap.** Tiers are computed by `suggest_targets.tier_rank()`, which reads `regs` — loaded from
`curriculum/trip_deck.json`, **not** from the lexicon:

```
DECK_TIERS = {"antifreeze": 0, "public": 0, "frame": 0,
              "faq": 1, "mil-table": 1, "social": 1,
              "gossip": 2, "zinger": 2}
TIER_NAMES = {0: "survival", 1: "delight", 2: "dessert"}
```

Verified 2026-08-18: **0 of 339 lexicon rows carry a `register` field.** All 83 registers live in
`curriculum/trip_deck.json` (frame 20, mil-table 11, gossip 11, social 11, antifreeze 10, public 8,
faq 6, zinger 6). Remove the deck without migrating and the ordering vanishes **silently** — the
selector keeps returning rows, they are simply no longer tier-ordered. Nothing fails, every
instrument reads green. That is the exact silent-no-op class `/extend` Gate 7.2 exists for.

**Do:**
1. Add `register` to the lexicon row schema. **Gate 2 schema change — explicitly commissioned by
   Andrew, 2026-08-18, in this work order.** Record it in `DECISIONS.md` when done.
2. Migrate via a `sync_state.py` writer path (never hand-edit `progress/*.json`). The 83 keys in
   `trip_deck.json` map 1:1 onto lexicon keys.
3. Rows with no register keep today's fallback: `DECK_TIERS.get(..., 1)` → tier 1 (delight).
   That leaves 256 rows unordered-but-not-broken, which is the intended graceful degradation.
   **Do not attempt to classify all 339** — that is a curriculum project, not this one.
4. Repoint `tier_rank()` at the lexicon and delete the `regs`/`trip_deck.json` read path.
5. **Smoke first:** a case asserting tier ordering still holds for a lexicon row that has **no
   `deck` tag at all**. That case must go green *before* step 1 removes anything.

## Step 1 — Collapse the pools

Target: **9 pools → about 5.** Current ticket sections:

| section | disposition |
|---|---|
| ★ TRIP DECK | **merge** into one ordered pool with FOCUS SET |
| 1. FOCUS SET (≤12) | **merge** (keep `FOCUS_SIZE`; it is the dense-rotation budget) |
| ★ HINTED, GOING DARK | **fold in** — it is a retest *rule* (`RETEST_DAYS`), not a rival pool |
| ★ DECK COVERAGE | **keep, generalise** — worked-vs-tested is unique and nothing else provides it |
| ★ SLIP LEDGER | **keep** — different job (*how* a rep fails, not *what* to pick) |
| 2. DUE CALLBACKS | **keep** — different job (decay; `PATTERN_SLOTS` lands here) |
| 0. SCENE SPEC | **keep** — variety axes, not a target pool |
| 3. NEW CANDIDATES | **keep** — new ground; note `comprehension_plan.md` may retire `word_pool.json` |
| 4. VOCABULARY FENCE | **keep** — the Architect's sea, not a selector |

**Delete the primacy claim.** "force these before the general floor" goes. One headline:
`machines heard` steers *what*; the slip ledger steers *how*. Those are not rivals.

`deck_status()` becomes an ordering over the whole lexicon. Consider renaming to something without
"deck" in it, and keep `coverage_key` as the single ordering law it already is.

## Step 2 — Remove the deadline machinery

- `TRIP_DATE = date(2026, 8, 12)` (`sync_state.py:51`) has **an entry and no exit**. `s54` encodes
  two eras (pre-trip, during-trip); there is no third. After he flies home (~2026-09-12) the status
  line reads `in country, day 32`, then 33, forever. Either add the third era or delete the
  countdown outright — **deleting is preferred and is the point of this work order.**
- `burn_rate()` — a required pace needs a deadline. With none, it degrades to trailing pace only
  (already handled since 08-04). Strong candidate for deletion.
- Callers to clean: `knock_reply.py:56,524,527` · `show_status.py:19,57-67` ·
  `session_brief.py:26,340-342` · `sync_state.compute_deck`.

## Step 3 — Prose

- `progress/profile.md` — **Phase 1.5 says to revert itself**: *"After the trip: clear the sprint…
  Revert this section then."* Follow its own instruction. Also fix "Current Position" if it still
  references deck meters.
- `.claude/skills/orient/references/glossary.md` — `deck`, `Trip Sprint`, `fire / catch` entries.
- `.claude/skills/validate/SKILL.md` — mentions the deck in its status description.
- `docs/DECISIONS.md` — one entry, ≤150 words, naming what it retires.
- `docs/comprehension_plan.md` — this closes **open question #7**; link it.
- `content/trip_deck_cheatsheet.md` — leave alone. It is a historical artifact, not machinery.

## Step 4 — Data (be conservative)

- **Keep `deck: "trip"` on the 83 rows.** Stop *reading* it; do not strip it. It is provenance —
  the record of where those rows came from — and deleting data is the one irreversible move here.
- **Keep `curriculum/trip_deck.json` and the `seed-deck` command.** Curated-set seeding stays useful
  for any future set; only the *trip* framing is retiring.

## Test surface — 16 cases mention deck or `TRIP_DATE`

Review in this order (count = mentions):

```
29 s32_deck_rotation_and_coverage      21 s33_catch_response_pairs
16 s47_hinted_retest_block             13 s40_drill_consumes_its_commission
 7 s54_two_eras_not_a_deadline          6 s60_the_ear_meter
 5 s8_variety_and_decay                 4 s64_the_ask_cooldown_covers_the_session_lane
 3 s48_drill_answer_key_lint            3 s13_eavesdrop
 2 s38_teach_enters_the_lexicon          1 s61_no_number_is_recited_at_him
 1 s57_longhaul_tape                     1 s53_prune_duplicate_lexicon_rows
 1 s41_slip_ledger                       1 s20_fielding
```

`s54` is the one that most likely **retires wholesale** — it tests deadline behaviour that will no
longer exist. Do not weaken the others to make them pass: a case asserting tier ordering should
keep asserting it against the migrated `register`, not be deleted with the deck.

## Verification

1. `python scripts/smoke_test.py` — green, and every budget green (`suggest_targets.py` had **4
   lines of headroom** at 572/575 before this work; deletion should return a lot of it).
2. `python scripts/suggest_targets.py | wc -l` — should drop well below 361.
3. `python scripts/sync_state.py status` — no countdown, no burn rate, one headline.
4. **The ordering check, by hand:** a survival-register row with no `deck` tag must still outrank
   an ordinary row of equal staleness. If this cannot be demonstrated, step 0 failed.

## Rollback

Single revert. All state changes are additive (`register` added, `deck` retained), so no data is
destroyed and the migration is idempotent.

---

*Written 2026-08-18. Companions: `docs/comprehension_plan.md` (open question #7),
`docs/DECISIONS.md` → "The threshold is comprehension; production is the engine".*
