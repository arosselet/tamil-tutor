# The One-Year Comprehension Goal — open planning

> **Status: PARTLY EXECUTED as of 2026-08-25.** It sat open for seven days while the commit log
> filled with a spine refactor and a smoke-test split — good work, and not this work. On
> 2026-08-25 Andrew read it back and said *"adjust our system towards meeting our goals"*, and
> four of the six proposed changes landed that day (§6 below, marked ✅), with five entries in
> `docs/DECISIONS.md` following from it. **The goal in §5 is still NOT adopted** — question 1 is
> the live edge and nothing downstream of it is settled. Resume at **Open Questions**.
>
> **Read this document for its shape, not only its conclusions.** It measures the OUTCOME rather
> than the machine, which nothing else in the repo does; it reports per-row transitions because
> net counts hide churn; it marks its own load-bearing assumption (the 1,500–2,500 figure) as
> unverified; it splits the goal into a finite cheap layer and an unbounded expensive one; and
> it says *no* out loud — "Tier C in 12 months: not reachable. Stated plainly so it is not
> discovered next August." That last property is why it is worth keeping open rather than
> closing to feel finished.

## The question, in Andrew's words

> *"I want to come back this time next year and catch most of what is said."*

Asked 2026-08-17, six days into his first month living in Coimbatore, two days after the 08-16
disillusionment signal (`progress/feedback_log.json`) and the same day the constitution was
rewritten around **the threshold is comprehension; production is the engine**.

---

## 1. Baseline evidence (measured 2026-08-17)

Reconstructed from git rather than trusting the current snapshot. See *How to re-measure*.

### Recognition history

| date | rows | solid | comfortable | struggled | machines solid |
|---|---|---|---|---|---|
| 2026-07-01 | 212 | 93 | 72 | 47 | 1 |
| 2026-07-16 | 273 | 93 | 79 | 101 | 1 |
| 2026-08-01 | 328 | 95 | 87 | 146 | 3 |
| 2026-08-17 | 339 | 95 | 88 | 156 | 3 |

### Per-row transitions (net counts hide churn; these are the real numbers)

- **Jul 1 to Aug 17 (47 days): 6 upgrades, 1 downgrade, 37 new rows.**
- **Aug 2 to Aug 17 (15 days, six of them immersed in country): 1 upgrade.**
  (`சும்மா சொல்றாங்க`, struggled to comfortable.)

**Measured recognition rate: ~0.13 upgrades/day.** The ledger grew 127 rows since July 1 while
`solid` grew by 2 — the system has been acquiring inventory, not converting it.

### Three structural facts behind that rate

1. **"Solid" is mostly an assertion.** Only **19 of 95** solid rows have `reps > 0` — i.e. have
   ever been tested. The rest were seeded at import. Example: `முதல்ல` is marked solid, appears
   in 24 episodes of `seen_in`, `last_surfaced` 2026-06-24, never once tested. **Real verified
   solid is plausibly 20-40, not 95.** Every projection below is unreliable until this is fixed.
2. **The ear has almost no input channel.** Recognition is written by exactly two things:
   Anna's in-session judgment (`scripts/sync_state.py:539`) and a successful eavesdrop catch
   (`scripts/knock_reply.py:440`). There have been **11 eavesdrop knocks out of 132 total**. The
   axis promoted to headline on 08-16 is tested roughly twice a month.
3. **Input volume is ~1.3 min/day.** 74 episodes, ~237 verified minutes plus 10 placeholder
   `3.0` durations, so **~4 hours of generated Tamil in the 6 months since 2026-02-19**. (The
   placeholder problem is already an open item in `docs/feature_inbox.md` — `get_duration` has a
   bare `except: return 3.0`.)

---

## 2. Scoping the goal

### Two layers, very different costs

- **Parsing layer** — the agglutinative stack: case, tense, person, mood, and the clitics
  (`-aam`, `-nu`, `-la`, `-e`, `-dhaan`). Without segmentation a known root is still
  unintelligible. **Finite: ~50-80 productive patterns for colloquial speech.** 26 are mapped,
  3 solid on the ear. This is the cheap, high-leverage half.
- **Lexical layer** — roots. Order of **1,500-2,500 families** for "most" of everyday talk.

> **Confidence note.** The lexical figure extrapolates from general SLA findings (roughly 95%
> known-word coverage needed for listening comprehension; spoken registers more lexically
> restricted than written; ~2,000 families covering English conversation). **No Tamil-specific
> coverage corpus was consulted.** Treat it as order-of-magnitude. Finding real Coimbatore-Tamil
> frequency data would materially sharpen this plan and is an open task.

### Three difficulty tiers (the phrase "what is said" hides all three)

- **Tier A — follow the topic.** Multi-party talk; who, what, mood. **Already demonstrated** on
  the 08-15 gossip tape (marriage / next month / in a hurry / Savitha annoyed).
- **Tier B — follow directed speech.** Someone speaks *to* him about everyday things; he gets
  the sentence, not just the gist. Repeats only for speed or unknown words.
- **Tier C — follow unrestricted multi-party family conversation** at native speed: gossip
  register, jokes, cross-talk, decades of shared context. **This is the literal ask.** It is
  also the hardest listening environment that exists.

---

## 3. The arithmetic

Tier C in 365 days needs roughly 1,500-2,000 items at verified solid recognition plus most of
the pattern inventory, so **~5 items/day sustained**. Measured rate is **0.13/day**. A **~40x
gap**; ~20x even if the target is scoped down to 1,000 items.

---

## 4. Verdict

- **Tier C in 12 months: not reachable.** Stated plainly so it is not discovered next August.
- **Tier B in 12 months: reachable — but only if the daily loop changes shape.**

**The gap is throughput, not capacity.** The machine delivers ~1.3 min of Tamil a day and spends
session time forcing production — the expensive axis (75 cold fires over 30 sessions, ~2.5 per
session, each costing a session moment). Nothing in the current design moves recognition at
volume, because the system was built to force output. The ear has been flat for seven weeks
because almost nothing feeds or tests it.

---

## 5. Proposed goal (not yet adopted)

> **By August 2027: when someone speaks to me directly at the table about everyday things, I
> follow the sentence — not just the topic — and I need a repeat only when it is fast or carries
> a word I do not know. In multi-party talk, I reliably follow who did what to whom.**

Tier B plus the useful half of Tier C. Testable with instruments that already exist (eavesdrop
tape plus directed-speed ambush). Tier C proper: 2-3 years.

### Checkpoints

| by | target |
|---|---|
| Nov 2026 | machines heard 13/26 · daily eavesdrop channel live · input >=30 min/day |
| Feb 2027 | machines heard 22/26 · native media is the primary source · 400+ verified-solid roots |
| May 2027 | full pattern inventory mapped (~60), half solid · 800+ roots |
| Aug 2027 | Tier B holds under test · 1,200+ roots · Tier C partial |

---

## 6. Proposed changes (✅ = landed 2026-08-25)

1. **Invert the daily budget** — from ~15 min production-forcing to **45-60 min comprehension
   input** (~300 hrs/year). Production stays daily but stops owning the clock.
   **✅ PARTLY, 2026-08-25.** The session inverted: the ear leads, ~3 fires are the probe, Ear
   Day is the volume shape (DECISIONS → "Input first; production is the probe"). The *minutes*
   half did not — it became a dial in `profile.md` → Calibration Notes with a proposed 15
   min/day, and **Andrew sets the number**. 45–60 is still unpriced against the Enjoyment
   Clause; see open question 6, which this does not answer.
2. **Ungate Phase 2 now.** `progress/profile.md` gates native media behind clearing the
   viability floor. Under the 08-17 position that gate is backwards — it makes comprehension
   wait on the production odometer.
   **✅ DONE 2026-08-25.** The gate is off and `profile.md` carries "The Native-Media Lane"
   with an explicit on-ramp — vlogs re-watched, then serials, then films — because films are
   the destination and the hardest listening environment there is, not the entry point.
3. **Change the item source.** 333 hand-curated rows in `curriculum/word_pool.json` cannot scale
   to thousands. Media supplies items; the system's job becomes selection and testing, not
   authoring.
4. **Give the ear a real test channel.** Eavesdrop tapes are the right instrument and have fired
   11 times. Should be near-daily. Cheapest item on this list.
   **✅ UNBLOCKED 2026-08-25**, and the diagnosis here was incomplete. The eavesdrop lane was
   not merely under-used: its pool was 9 rows, because `ear_targets` gated membership on the
   `direction: "catch"` tag. `morning_knock.remaining_room` reads that pool to decide the
   cadence is overdue, so the "highest-value move right now" warning was being computed against
   a nearly-empty queue. The pool is now 29 with the machines in it. Cadence still needs
   watching — an unblocked lane is not a used one.
5. **Machines first, and it is not close.** 3/26 to 26/26 is 23 upgrades; at one per week, six
   months. Disproportionately unlocks parsing on every sentence. Year-one priority #1, ahead of
   vocabulary volume.
   **✅ REACHABLE 2026-08-25.** They now hold reserved seats at the head of ticket block
   **1a. THE EAR** and reach the knock menu as `[ear-behind]`. The asymmetry this exposes is
   the sharpest single number in the project: **21 of 26 machines fire cold and 3 are heard** —
   his mouth is a full lap ahead of his ear on the exact inventory comprehension rides on.
6. **The wife question.** The highest-bandwidth Tamil in his life is in the house, and the
   constitution deliberately keeps her out (Resource not teacher; 60-second vibe checks; never
   an examiner — the heist). Those rules exist for real reasons. But no generated system
   competes with a native speaker for 300 hours of input. Worth reopening *deliberately* and
   narrowly (e.g. a fixed Tamil-only daily window), not as "make her teach you."
   **Andrew's call; the tradeoff is real and was named, not hand-waved.**

---

## 7. Open questions — resume here

1. **Adopt the Tier B goal, or re-scope?** STILL OPEN and still the live edge — the 08-25 work
   changed the machine's direction, not the destination. Andrew has since named an intermediate
   marker in his own words that is worth scoping against: *"reaching a point where I can start
   more enjoying Tamil movies would be a huge unlock."* That is nearer than Tier C and further
   than Tier B, and it is testable by simply trying it.
2. **Re-test the 76 untested "solid" rows.** No projection here is trustworthy until the
   baseline is real. What is the cheapest way to re-test at volume — batch eavesdrop tapes?
3. **The wife question** (item 6). Genuinely Andrew's decision, RAISED AND NOT ANSWERED
   2026-08-25 — and the broad framing was withdrawn as too vague to act on. The narrow version,
   which asks nobody to become a teacher: when he does not catch something, use the antifreeze
   line he already owns (*enna sonninga?*) instead of letting it pass, and let the Oracle decode
   the two or three `[heard]` lines a week that neither he nor Anna can crack — the existing
   vibe-check mechanism pointed at heard lines instead of drafted ones.
4. **Find Tamil-specific frequency/coverage data** to replace the extrapolated 1,500-2,500.
5. **Ship `ears_pct`** (already logged in `docs/feature_inbox.md`) — none of the checkpoints are
   verifiable without a longitudinal record of the headline axis.
6. **Does the daily-budget inversion break the Enjoyment Clause?** 45-60 min/day is a large ask
   against "contact time > completion" and a documented history of fades. Unresolved.
7. ~~**What happens to the Trip Deck**~~ — **ANSWERED AND EXECUTED 2026-08-18**: retired now
   rather than at the end of the stay (Andrew: lean and coherent is the success criterion, not
   day-to-day teaching). Scoped in the deck-retirement work order (retired 2026-08-26, executed
   whole), decided in `DECISIONS.md`, shipped
   the same day. The tier ordering was migrated onto the lexicon rows as `register` and kept; the
   container, the deadline (`TRIP_DATE`), the burn rate and the sprint meter are gone. Nine ticket
   selectors became five, and no section claims primacy any more.

---

## How to re-measure

All read-only.

- `python scripts/sync_state.py status` — current meters, including `Machines heard`.
- `python scripts/generate_callbacks.py` — what the return clock is actually returning.
- **Untested "solid" count:** load `progress/lexicon.json`, take rows where `recognition` is
  `solid`, and count how many have `reps > 0`. On 2026-08-17 that was 19 of 95.
- **Recognition upgrades since a past commit:** load `progress/lexicon.json` from
  `git show <sha>:progress/lexicon.json`, rank `{struggled:0, comfortable:1, solid:2}`, and count
  rows whose rank increased. Sample historical shas with
  `git log --format="%H %ad" --date=short -- progress/lexicon.json`.

---

*Recorded 2026-08-18 (measurements taken 2026-08-17). Companion: `docs/DECISIONS.md` → "The threshold is comprehension;
production is the engine" — the position this plan is scoped against.*
