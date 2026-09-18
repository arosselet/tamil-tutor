# Proposal: The Household and the Month

> **STATUS: PROPOSAL — agreed in shape with Andrew 2026-09-18, awaiting his final yes on
> this text.** It is written to be the *only* input to a separate build session. That
> session should read this file top to bottom, then `AGENTS.md`, then run `/orient` and
> `/extend` before touching code. On approval-and-build this file is deleted: its
> decisions become `docs/DECISIONS.md` entries (§11 drafts them), its laws move to the
> files that own them, and git holds the reasoning.
>
> Supersedes the 2026-09-17 draft of this file ("The Month With Edges"), which was right
> about the month and wrong about what fills it. What survives from it is named in §9.

---

## 1. The signal

Five felt reports in eighteen days, all logged in `progress/feedback_log.json`:

- **09-01** — *"I have this niggling doubt that I'm fooling myself … the illusion of
  progress, that I could keep this ritual for years and not get where I want."*
- **09-16** — *"Our lessons are starting to feel narrow and repetitive."*
- **09-16** — *"It's repetitive, it's narrowly checking things; the lessons are short and
  pointed at my failures."*
- **09-17** — *"I am struggling with continuity, enjoyment and long term planning of my
  lessons."*
- **09-17** — *"The post-trip horizon gap needs to be filled to restore long-term planning
  and enjoyment."*

And in conversation 2026-09-18, the sentence the whole design answers: *"I am begging you
for continuity and shot down the main scaffold off which you could build recurring stakes,
characters, etc."*

## 2. The diagnosis

**The system has never had a reason to continue that it supplied itself.** It ran ten
months before the Trip Deck existed. The deck was contrived around 2026-07-13, when the
tickets were booked, and for eight weeks the trip did four jobs no code did: a **horizon**
(weeks away, not a year), a **room** (real people to use it on), a **story** (every
session was a step toward the table), and a **reason for drilling** (survival lines had to
fire cold on arrival). The May 2026 fade is the pre-deadline evidence that the long-term
version of this problem was never solved; the deadline masked it and its removal exposed it.

What is left is a machine whose every selector chooses by **deficit**:
`floor_gap_targets`, the 12-seat `focus_cohort` conveyor (`FOCUS_SIZE`), the slip ledger,
retest slots, payoff re-sends. A deficit-seeking machine points at failures by
construction — *"pointed at my failures"* is an accurate description of the selection law,
not of Anna's tone. And because the slip ledger is the only memory that crosses days, the
only continuity he can perceive is his own recurring mistakes.

Measured 2026-09-17: 102 items tested in 30 days, 76 exactly once. The item set is a
scatter; what is narrow is the conveyor, and what is missing is any *thing the days are
about*.

Two June decisions removed the scaffold that could have carried continuity:

- **2026-06-20** — *"Serialization / recurring audio cast rejected; variety is structural."*
- **2026-06-28** — *"Narrative-saga continuity rejected. Serialized fictional plot rings
  hollow … Scenes are disposable one-use pegs."*

Their fear — invented stakes, a plot he is asked to care about — was fair. But the
premise that made them safe (*"the one true narrative is my own progress"*, JOURNEY ch. 6)
held only while the trip was the story. Post-trip, "my own progress" is the slip ledger.

## 3. The idea in one paragraph

**A fictional Coimbatore household, recurring, and a calendar month that is one arc of its
life.** The audio lives in that household; Anna talks about it like a show the two of them
follow; each month's vocabulary comes *out of* the arc's scripts rather than the arc being
wrapped around a gap list; and the month is won by an **ear test on the arc's finale** —
Andrew follows the last episode without the script and says what happened. Deficit
machinery keeps running, demoted to maintenance woven into the household's content.

**Why this is not hokey, and why it is the goal rather than decoration.** The adopted goal
(`docs/comprehension_plan.md` §5) is to follow the family table at native speed by August
2027. What makes a real table hard is not only vocabulary but **shared context** — who
Chitra is, why Mama is sulking, what "that business last Deepavali" refers to. Disposable
scenes cannot teach that by design; a recurring household does. Following the fictional
family *is* the goal in miniature. The stakes are the goal's own register — food, plans,
who is coming, health, the day just had — soap-sized, not plot-twist-sized.

## 4. The object

### 4.1 The household (the canon)

- **Fictional, never a mirror of anyone Andrew knows** (Andrew, 2026-09-18, explicit). No
  names, roles, or situations lifted from his in-laws or his wife's family. The build
  session must not read `progress/` debriefs or feedback for character material.
- **Where:** one file, `content/household.md` — studio domain (the stray-write tripwire
  already polices `content/`), readable by Anna.
- **Contents, and nothing else:**
  1. **Place** — one paragraph. A Coimbatore neighbourhood, the house, the rhythm of a day.
  2. **Cast** — at most **seven** people across generations (an elder or two, a middle
     generation, young adults, one recurring outsider such as a neighbour or the milk man).
     Per person: name, relation, age band, one or two concrete traits (a tic, a want, a
     way of talking — including register: the grandmother's older Kongu forms, the
     college-going cousin's English code-switching), and a **pinned TTS voice** (see §4.4).
  3. **Standing facts** — the short list of things that are true and that scripts must not
     contradict (who is married to whom, who lives where, what happened in past arcs).
  4. **This arc** — the premise and a running beat log: one line per episode, written
     after it renders, saying what happened.
  5. **Past arcs** — one line each. Detail lives in git.
- **Budget:** a word cap enforced in `scripts/smoke/ratchets.py` like every other prose
  surface. Start at **1,200 words**, re-census after the first arc. Canon that outgrows it
  is compressed at the month boundary (this arc's beat log collapses to its one-line
  past-arc entry), never raised.
- **Who writes it:** the cast/place/standing facts are drafted once by the build session
  (or a studio pass it commissions) and **approved by Andrew before the first episode**.
  After that: Anna writes the arc premise at month cut; the studio's Producer pass appends
  the beat line after render. Andrew overrides at will.

### 4.2 The month is an arc

- **Calendar month** (Andrew's call, 2026-09-17). `month.closes_on` on the branch already
  implements it.
- **Named for what is happening in the household** — *"Priya's engagement"*, *"Paati comes
  to stay"*, *"The new shop"* — which replaces the campaign block's week name.
- **Premise written at cut**: two or three sentences — the situation, what will be
  resolved by the finale, which everyday domains it naturally exercises (food, visitors,
  health, errands, money, plans). The premise is chosen with the vocabulary in mind — Anna
  picks a situation whose domains cover what the ticket says is thin — but the words are
  never listed in it.
- **Episodes are the arc's beats.** Roughly two to four studio episodes a week, as now.
  Each is a scene in the household, and each still gets its register / form / dramatic
  ingredient from the **divergence gate** (`suggest_targets.scene_spec`, window 3) — the
  06-20 variety law survives intact. Variety comes from the gate; continuity comes from the
  people. A `lore` episode can be Maya and Raj unpacking a word *from* the household; a
  `phone_call` is a household member on the phone; a `vignette` is a slice of a morning.
- **The finale** is the last episode of the month, commissioned in the final week. It
  resolves the premise and deliberately re-uses the arc's vocabulary.

### 4.3 Membership and the meters

Two meters, with different jobs. **Only one is the win.**

- **The win — the finale ear test.** Andrew listens to the finale **without the caption
  sheet** (it can be released after the test), then in a session tells Anna what happened.
  The finale's sidecar carries a short list of **key lines** (the Architect marks them:
  six to ten lines the resolution turns on). Anna records each as `right | partial |
  wrong` by what he says they meant — never by asking whether he caught it. **Won** when
  two thirds of key lines are `right` (partial counts half). The rule and threshold live in
  Python, not prose. He can re-listen before the test as many times as he likes; the test
  is one attempt per month; a lost finale re-cuts with no debt (§6 law 1).
- **The standing — vocabulary the arc carried.** Membership is the **union of the NEW
  payload items of the month's arc episodes**, read from the episodes' `.tags.json`
  sidecars within the month's date range — **derived, not stored**. Completion is the fold
  the branch already built (`month.standing`): a member closes on the derived rung of the
  axis it entered for. It steers Python's picks and is visible on Andrew's own surfaces;
  it is not the win and **no number leaves Anna's mouth** (`persona.md`, DECISIONS #33).
- **Size, as intent not quota:** Andrew's numbers — *"30–40 a month ideally but maybe
  realistically 15"* — become the Director's guide for how many NEW items an arc
  introduces across its episodes (~30). They are not a win line.
- **Ear rung for a member:** `recognition` reaching **`comfortable`** or better, matching
  `suggest_targets.RECOGNIZED`. (The branch used `solid`; 4 of 366 rows are solid today, so
  an ear member would essentially never close. Decision taken here; Andrew may override.)

### 4.4 Voices

The household needs consistent voices per character across episodes. `render_audio.py`
already supports a per-script **Voice Map** (`VOICE_MAP_RE`) and gender tags. The build
session must **verify** how many distinct voices per gender the configured provider offers
before fixing the cast size — seven characters is the ceiling, the real number is whatever
keeps every recurring character distinguishable. The canon pins each character's voice;
the Architect copies that map into every script.

### 4.5 The chat session

- **Anna opens inside the household.** *"Did you hear what Mama said to Priya?"* — a
  question about the last episode, in Tamil at his level, is the session's running thread
  (replacing "the campaign's through-line in one breath" in `.claude/skills/anna/SKILL.md`).
  Anna is a fellow listener, never a character in it: the fourth wall in the audio stays
  up, and Anna never appears in the audio.
- **Practice lives in the household's situations.** Production asks, volleys and role-play
  use the household as the situation source — *"Paati asks if you've eaten; answer her"* —
  so a drill on a slip is still a moment in the world.
- **Maintenance is maintenance.** Slips, retests and gap targets are still worked; they
  are no longer what a session is *about*. The session is about the household; the medicine
  rides inside it.
- **The anna-gets-a-menu rule stands** (limits + energy + selectable formats; the running
  order barely exists). The household is the setting, not a script.

### 4.6 The knocks

The knock digest reads the arc (premise + last beat) where it reads the campaign block
today (`morning_knock.campaign_block`). Volley and ask situations may draw on the household.
**Eavesdrop tapes set inside the household are a later increment**, not this build — they
are the obvious next step (an overheard household moment is exactly the table's genre), but
this build proves the arc on the episode lane first.

### 4.7 Andrew's wife

**Explicitly not a mechanism.** Field missions failed because they were homework Anna
collected, and the debriefs were self-estimates (Andrew, 2026-09-09). He is shy, prefers to
work independently, and goes to her with real junctures. The household gives him more of
those — something to tell her about — and whether he does is his. Anna never assigns,
asks about, collects or scores anything involving her. This is a law (§6 law 5), not an
omission.

## 5. What this replaces (Gate 4)

| Retired / changed | Becomes |
|---|---|
| DECISIONS 2026-06-20 *serialization / recurring cast rejected* and 2026-06-28 *narrative-saga continuity rejected* | Superseded with reason (§11). The variety half of 06-20 — the divergence gate — survives unchanged. |
| `protocol/studio/hosts.md` — the Intercept's *"not theater with a cast … two hosts who act bits out"* and the **no-fixed-characters** rule (referenced from `studio.md`) | The Intercept is performed by the household cast. Maya and Raj (Breakdown) stay — they become two people discussing the household. Fourth wall and Tamil-script-only stay. |
| `director.md` Step 4 *"The Scenario is not a plot; it is a sandbox"* | The scenario is **the next beat of the household's arc**, read from `content/household.md`, inside the gate's register/form/ingredient. |
| `soak_order.scene_seed` (one-line invented situation) | The arc's next beat. The payload half of `soak_order` survives. |
| The campaign block in `progress/profile.md` ("The Campaign — This Week") and its contract in `protocol/daily_session.md` | "The Month" block: arc name, premise pointer, and a short maintenance line. The live-medicine prose shrinks — the slip ledger already holds it (`slip_log.json`), and duplicating it in profile.md is part of why the week reads as failures. |
| `focus_cohort` as a refilling conveyor (`FOCUS_SIZE = 12`, `reconcile_focus`) | The dense-rotation window draws **first from the month's open members**, then background as now. A graduate leaves a hole, not a refilled seat. `sync_state reseed-focus` retires if nothing else needs it. |
| The seed derivation in `floor_gap_targets` (`stable_jitter`) as the source of focus membership | Membership comes from what the arc taught. |
| `cmd_check --draw` monthly 30-row random sample | **Keep for now.** It is the only instrument that has never run and the one that re-bases the goal (owed since 09-10). Revisit after the first finale; the finale test may absorb it. |
| The branch's `month.cut()` from the gap pool, `set` stored in learner.json, `won_at` line | Membership derived from arc sidecars; win is the finale. See §9. |

**Honest scope.** This build adds one content file and changes several prose and code
surfaces; the large simplification is conceptual — one named, bounded, *narrated* universe
instead of pools competing for primacy. Every prose surface touched is at or near budget
(`daily_session.md` sits at 1320/1320): the build pays for its words by retiring the ones
this table names, and a budget raise without a named retirement is a red run.

## 6. The laws

1. **Unmet is re-cut, never debt.** A lost finale, an unfinished arc, open members at the
   boundary: none is carried as a deficit, none is narrated as one, and no field anywhere
   records it. Open members may be offered to the next arc's Director as candidates, with
   no privilege. The reset is the forgiveness mechanism.
2. **Completion is derived, never stored** — membership from sidecars, rungs from the
   observation log, the finale verdict from recorded `check`-style events.
3. **Comprehension is measured, never self-reported.** He produces the meaning; Anna
   records what he produced. *"Did you get it?"* never votes.
4. **Fictional, always.** No character, name or situation mirrors anyone Andrew knows.
5. **His wife is never a channel.** No assignment, collection or score involving her.
6. **The canon is bounded.** Word-budgeted; compressed at the boundary; scripts never
   contradict standing facts.
7. **Variety is still structural.** The divergence gate governs every arc episode; the
   household is a setting, never a reason to repeat register or form.
8. **Anna steers by the month; no number leaves his mouth.**
9. **The month is re-cuttable mid-flight in one move** — a premise that isn't working is
   replaced, not endured. The frozen deck is the failure this prevents.

## 7. The silent no-op test

*What does this look like when it silently does nothing?* It looks like: a month record
exists, the canon file exists, and episodes keep being generated as disposable scenes that
never read either; the finale is never commissioned; the standing counts down from unrelated
activity. Every instrument would read green. So the smoke suite must have teeth in exactly
those places (add to `scripts/smoke/state.py` / `compose.py` as fits their lanes):

- **The Director brief reads the canon.** A run of `run_studio` against a sandbox with a
  canon file produces a brief that contains the arc premise and the last beat; with the
  canon missing, it fails **loudly**, never falls back to a free scenario.
- **The beat log grows.** A render of an arc episode appends exactly one beat line; a
  render that doesn't is a red run.
- **Membership is the sidecar fold.** Build sidecars by hand; the standing's members equal
  the union of their NEW payloads within the date range, and nothing else. Delete a
  sidecar and the member goes away — no stored copy survives.
- **Selection reaches the month.** Over N picks (the `s34` `range(40)` pattern), every open
  month member is reached; a closed member is not re-drilled.
- **The finale verdict is a fold.** Hand-built key-line events produce the verdict; there
  is no stored `won` field to flip.
- **No debt survives a boundary.** After a re-cut, no field anywhere names the previous
  month's unmet items (the branch's `s112` already proves this for the old shape — adapt it).
- **The canon budget holds** in ratchets, like every prose surface.
- **The fourth wall holds.** Existing checks keep passing; Anna's name never appears in a
  script.

## 8. Build order

Each increment is shippable and leaves the system working. Stop and show Andrew after 1.

1. **The canon.** Draft `content/household.md` (place, cast with voices verified against
   the provider, standing facts) and its ratchet budget. **Andrew approves the cast before
   anything consumes it.** This is the step most likely to be hokey; iterate on it with him.
2. **The studio reads it.** Director Step 4 and `studio.md` contract change; `hosts.md`
   retirement; Producer appends the beat line; `scene_seed` → next beat; sidecar gains the
   `arc` name and, for a finale, `key_lines`. Smoke: brief-reads-canon, beat-log-grows.
3. **The month record, reshaped.** Adapt `scripts/month.py` from the branch (§9):
   membership derived from arc sidecars, ear rung `comfortable`, finale verdict fold, no
   debt, mid-flight re-cut. `sync_state.py month` becomes the one writer for the premise /
   re-cut and the recorder for finale key lines. Smoke: membership-is-sidecar-fold,
   finale-verdict-is-fold, no-debt.
4. **Selection draws from the month.** `suggest_targets`' focus window reads open members
   first; the conveyor refill and jitter seed retire. `suggest_targets.py` is at its 588
   ceiling — this increment must retire at least what it adds there. Smoke: every-member-
   reached.
5. **Anna and the knocks.** `daily_session.md` campaign contract → the month block (paid for
   by retirements, §5); `SKILL.md` open-on-the-household; `morning_knock.campaign_block`
   reads the arc; the campaign heading guard in ratchets follows the rename. Write the §11
   DECISIONS entries; delete this file.

**Timing.** Build through the rest of September. **The first arc opens 2026-10-01** — a full calendar month, no stub. September's remaining sessions run as today.

## 9. What already exists on this branch

`proposal/month-with-edges` carries a commit (17c3e89) built from the previous draft:
`scripts/month.py`, `sync_state.py month`, ratchet/layer entries and smoke `s112`. It is
**unwired** (selection never reads it). Keep and adapt; don't start over:

- **Keep:** `closes_on` (calendar month), `is_over` (a record with no close reads as over),
  `standing` as a fold with `missing` loud, `is_closed(row, axis)` with the axis fixed at
  entry, `carry` with no debt field, the layer number (month below `suggest_targets`), the
  budget entry (re-census to fit the reshaped file).
- **Change:** membership source (sidecars, not `cut()` from the gap pool); drop the stored
  `set` and `won_at`; ear rung `comfortable`; add the finale verdict; `target_rung` still
  decides a member's axis at entry.
- **Drop:** the stub-month scaling of defaults (no stub: the first arc starts on the 1st)
  and the `--size/--won-at` flags.
- **Pre-existing, not ours:** smoke `s100` reports one divergent lexicon row (அப்படியா?!,
  `last_surfaced` file 2026-09-14 vs log 2026-08-15) on a clean tree. Fix it or leave it,
  but don't mistake it for this build's failure.

## 10. Risks and open questions

- **Hokeyness.** The antidote is ordinariness: soap-sized stakes, people with specific tics,
  the goal's own topics. If the first arc reads hollow to Andrew, that is a felt signal to
  log and a premise to re-cut, not a reason to add plot.
- **Canon drift.** Generated continuity decays — a name changes, a dead grandfather speaks.
  The budget and the standing-facts list are the defence; a contradiction found is a
  studio defect to fix at the Producer pass, not a canon to grow.
- **Production cost.** No new episodes, same TTS spend; the Director reads one more small
  file. The running-cost budget ($5–10 USD/month) is unaffected. Verify, don't assume.
- **He stops listening.** On 08-23 he stopped listening to episodes while immersed and said
  it was not a fade. At home, the episodes are the only table. If listening drops during
  the first arc, read it as signal about this design.
- **Finale threshold.** Two thirds of key lines is a starting number, not a law of nature;
  re-base it after two finales from what the verdicts actually look like.
- **The finale may be the only ear test that runs.** If so, it should absorb
  `check --draw` rather than sit beside it — decide after the first finale.

## 11. DECISIONS entries to write on build (drafts)

- **The post-trip era is a household, and the month is its arc** (2026-09-18, Andrew) The
  system never had a reason to continue it supplied itself; the Trip Deck lent it one for
  eight weeks. A fictional recurring Coimbatore household is the continuity; a calendar
  month is one arc of its life; the vocabulary comes out of the arc; the win is an ear test
  on the finale.
- **Supersedes 2026-06-20 and 2026-06-28 on continuity; variety stays structural**
  (2026-09-18, Andrew) Their premise — "the one true narrative is my own progress" — held
  only while the trip was the story. The divergence gate is untouched; the cast recurs.
- **The household is fictional, always** (2026-09-18, Andrew) Never a mirror of anyone he
  knows.
- **The wife is never a channel** (2026-09-18, Andrew) Nothing assigned, collected or
  scored involving her; the household gives him things to tell her, and that is his.
- **The month's win is the finale ear test; the vocabulary count steers and never wins**
  (2026-09-18) Membership is a fold over arc sidecars; completion is a fold over the log;
  the verdict is a fold over key-line events. Nothing about the month is a stored counter.
- **Unmet is re-cut, never debt** (2026-09-17/18, Andrew) The reset is the forgiveness
  mechanism.
