# The One-Year Comprehension Goal — open planning

> **Status: GOAL ADOPTED 2026-08-31.** It sat open for seven days, then thirteen more. §5 is now
> settled and question 1 is closed. What changed the answer was not new ambition but a
> measurement: the ear is sampled once every 72 hours on ONE word (§3, corrected 2026-08-31), so
> the 0.13 upgrades/day this document built its 40x gap on is a property of the instrument, not
> of Andrew. The destination in §5 is therefore bounded by **register** rather than by tier, and
> its checkpoints are denominated in a meter being repaired the same week.
>
> Four of the six proposed changes landed 2026-08-25 (§6, marked ✅), with five entries in
> `docs/DECISIONS.md` following from it. Resume at **Open Questions**.
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

> **CORRECTED 2026-08-31, and the correction is load-bearing.** That rate is honest as a count
> and wrong as a rate of *learning*. Recognition has exactly one live test instrument — the
> eavesdrop tape — and `knock_reply.apply_catch_verdict` scores a single `expected_target` per
> tape, on a lane that fires every third day: **0.32 ear-tests/day against ~2-3 mouth-tests.**
> Measured row-by-row from git, 07-25 to 08-31: **79 production upgrades, 8 recognition
> upgrades** — a 10x gap that instrument cadence alone very nearly explains. The hit rates run
> the other way (ear ~67%, mouth ~37%): tested, the ear passes more often than the mouth. **The
> 40x gap prices a broken meter.** Not retracted — the throughput problem in §4 is real and
> unchanged — but it can no longer be read as a ceiling on capacity.

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

## 5. The goal — ADOPTED 2026-08-31

> **By August 2027: when the family talks at the table about the things they talk about every
> day — food, plans, who is coming, health, the day just had — I follow the SENTENCES, not just
> the topic. And I open turns nobody invited me into.**

**Bounded by register, not by tier — and that is the whole choice.** Tier B relaxes the
*environment* and buys accommodated speech, which is the wrong room: people slow down for the
foreigner, and the table does not. Tier C relaxes nothing and stays 2-3 years. This relaxes the
**range**: the table, at native speed, unaccommodated, on the topics that recur — not the jokes,
not the cross-talk, not forty years of shared reference. It is the first slice of Tier C rather
than a lesser destination, so year-one work and year-three work are the same work.

The pedagogy under it: the coverage threshold (~95% known words for adequate listening) is
reached **per register, not globally.** That is why films are a separate ladder rather than a
later rung, and why a bounded band is the only place the threshold is reachable early enough to
start compounding.

**The second clause is UNMEASURED, and the claim that it is the harder one is withdrawn
(2026-09-09).** This paragraph argued that four missions died because they required him to
open, so the system was optimised for the response slot he was already good at. The evidence
under it was not evidence: the missions were declined, not attempted (Andrew, 2026-09-09 —
*"that's just me shrugging off your demand to collect homework I wasn't actually doing"*), and
the debriefs that scored them were self-estimates. **So initiation has never been tested, in
either direction.** Andrew's read is that it needs no separate work — *"answering is how I build
up my foundation; if I can reply then I can also open unasked"* — and nothing in the record
contradicts it, because the record is empty. **Deferred to the next in-country test rather than
argued**: he is home, there is no table, and it is untestable until there is. Re-open it with
observation, never with another theory. What survives from the old paragraph: the discourse
openers (`namma mama irukkaar-la…`, `adhukku appuram?`) are ordinary vocabulary that happen to
do opening work, they enter through the normal teach beat, and the thin backchannel set behind
`grab-the-owned-one` is the real gap.

**Load-bearing assumption, and the check:** that a family table is not open-domain. Ten minutes
of harvested, native-ruled family speech yields the distinct-root inventory of *his* table —
which is also the Tamil-specific coverage data question 4 says this document never had. That
measurement expires with the return flight.

### Checkpoints

Denominated in a meter being repaired the same week. Re-base them at the first Receptive Check
rather than defending them.

| by | target | confidence |
|---|---|---|
| Sep 2026 | table denominator measured from harvested speech · the words he names in a tape are recorded instead of discarded · ear block logged 5 days in 7 | the middle one shipped 2026-08-31 |
| Dec 2026 | machines heard 10/26 · 120+ verified-solid roots · first Receptive Check logged | good on machines: finite, high-frequency, they convert fast once actually tested |
| Mar 2027 | machines 16/26 · 250+ roots · one channel followed without subtitles | moderate |
| Aug 2027 | machines 20/26 · ~400 roots · the recurring band holds under a harvested-clip test · turns opened unprompted at the table | the roots figure is the soft one — re-base it in December |

**Retired from the set:** `Nov 2026 — machines heard 13/26`, which priced a learning rate off a
broken measuring rate. The row's other two clauses (daily eavesdrop channel, input >=30 min/day)
survive in the habits below.

### The habits — two, and only two

A five-habit plan fails against a documented fade (May 2026) and the Enjoyment Clause.

1. **One ear block a day, 10-15 min, at its own anchor — REWRITTEN 2026-09-09.**
   **What it retires, and why it produced nothing in 25 days: the old habit could not be
   performed as written.** It prescribed a vlog channel with the face visible and *English
   subtitles on the first pass*, and in the same sentence attached it to "the walk, the dishes,
   the commute; never a new desk slot." You cannot read subtitles on a walk. The lane it draws
   on says "face visible, the situation carrying half the meaning". The instruction contained no
   executable action, which is a better root cause than the one recorded below and supersedes it.
   **Now:** a screen block at its own slot, separate from the chat session and later in the day
   (Andrew, 2026-09-09 — two blocks apart, not stacked). **Mostly authored** material: episodes,
   soaks, drills, rotation tapes, which are comprehensible by construction under the 95%
   coverage rule. **Native media is auxiliary** until a Receptive Check says coverage has
   closed — it is below the floor today, and sending him there first buys a discouraging
   evening. When it does run: one channel, re-watched, English subtitles on the first pass and
   **none on the re-watch**, which is where the ear does its work.
   **The desk clause is dead, and it was a residual** (Andrew's read, confirmed): "never a desk
   slot" was reasoned from 2026-08-25, when the only dose was a podcast and he was not finding
   time at his computer. Two desk sessions a day are not unreasonable now, and the walk and the
   dishes keep the job they are actually good at — **re-listening to material already
   understood**, which is the rotation lane's whole design.
2. **The daily eavesdrop tape** — after the scoring fix it is both the dose and the meter, it
   arrives on the phone, and it costs no new time at all.

The chat session stays exactly as it is: the production probe, ~3 fires. **Do not double it.** A
second chat session doubles the axis already at 21/21 and leaves the one at 3/26 untouched.

**Why the media lane produced nothing in its first six days** (checked 2026-08-31: zero mentions
across the whole span of `chat.md`, Receptive Growth Log still empty). It closes with *"it
replaces nothing and is owed nothing"* — it was written as a **permission**, and permissions do
not produce behaviour. That sentence is the Enjoyment Clause doing its job and it should stay for
everything else; habit 1 is the single exception that gets to be asked for.

> **RE-CHECKED 2026-09-09 at 25 days: still zero — and the diagnosis above is half of it.**
> The permission reading is real and stays. It is not sufficient: the habit was also
> **unperformable as written** (subtitles on a walk — see habit 1). Two faults, and only one
> was named, which is why naming it changed nothing. **The general lesson is the one this repo
> already knows and did not apply to itself: check that the instruction can be executed before
> concluding the learner lacked motivation.** A permission nobody can act on and a permission
> nobody chose to act on look identical from the log.

---

## 6. Proposed changes (✅ = landed 2026-08-25)

1. **Invert the daily budget** — from ~15 min production-forcing to **45-60 min comprehension
   input** (~300 hrs/year). Production stays daily but stops owning the clock.
   **✅ PARTLY, 2026-08-25.** The session inverted: the ear leads, ~3 fires are the probe, Ear
   Day is the volume shape (DECISIONS → "Input first; production is the probe"). The *minutes*
   half did not — it became a dial in `profile.md` → Calibration Notes with a proposed 15
   min/day, and **Andrew sets the number**.
   **✅ SET 2026-09-09, at 10-15 min/day, and 45-60 is withdrawn rather than deferred.** The
   number is his, chosen against the Enjoyment Clause rather than around it: 45-60 was never
   priced in *attention*, only in money, and money turns out not to bind at all (below). Two
   desk blocks of ~15 min each is what he will actually do, and a dial he meets beats a dial
   that is correct on paper. **The cost objection is retired outright** — measured 2026-09-09
   at 526 chars/min against Chirp3-HD's 1M free chars/month, authored audio is free to ~63
   min/day, so §4's "a boutique cannot solve a volume problem" was true about *effort* and
   false about *money*. What remains scarce is pipeline throughput, not budget.
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

1. ~~**Adopt the Tier B goal, or re-scope?**~~ **ANSWERED 2026-08-31 — re-scoped, and it is
   neither B nor C.** Why it sat open thirteen days: the A/B/C ladder is receptive-only, Andrew's
   goal has a production half (*"and participate"*), and you cannot pick a rung when half the
   goal is not on the ladder. The dimension relaxed is the **range**; the horizon on unrestricted
   Tier C stays 2-3 years and is explicitly not what he is committing to. The movie marker is
   **not** the intermediate target it was proposed as here — films are open-domain and
   native-speed, and coverage is reached per register, so they are a separate ladder. See §5.
2. **Re-test the untested "solid" rows.** ~~76~~ — **10 as of 2026-08-31**: the 08-24 purge
   dropped 108 unearned rows and the headline went *up*. Largely answered by deletion rather than
   by re-testing. What survives is the general question — how to test recognition at volume — and
   the multi-target eavesdrop change is the first real answer to it.
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
