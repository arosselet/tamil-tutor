# Proposal: The Month With Edges

> **STATUS: PROPOSAL — awaiting Andrew's yes.** Nothing here is settled and no code
> follows until he names the approach (`/extend` Gate 3). On approval this file is
> deleted: its conclusions become `docs/DECISIONS.md` entries, its laws go to the files
> that own them, and git holds the reasoning. It is not a second narrative surface.
>
> Written 2026-09-17 from the session of the same evening. Evidence is cited inline so
> the argument can be re-checked rather than believed.

---

## 1. The signal

Three felt reports, escalating, the last two on one day:

- **2026-09-01** — *"I have this niggling doubt that I'm fooling myself, that I've built an
  agent that asks me a couple questions, gives me a bit of feedback, and gives me the
  illusion of progress, that I could keep this ritual for years and not get where I want."*
- **2026-09-16** — *"Our lessons are starting to feel narrow and repetitive."*
- **2026-09-16** — *"It's repetitive, it's narrowly checking things; the lessons are short and
  pointed at my failures."*

Per `docs/DECISIONS.md` → *"Felt experience is the primary diagnostic"*, and per the second
instance rule, this is a `/recalibrate` trigger, not a mood to manage.

## 2. The measurement

**The item set is not narrow.** Folded from `progress/observations.json`:

| window | items tested | tested exactly once |
|---|---|---|
| 14 days | 46 | 40 |
| 30 days | 102 | 76 |

Three quarters of what he is asked about in a month is touched once and not returned to.
That is a scatter, not a rotation.

**But one part of the system is exactly as narrow as he says it is.**
`scripts/suggest_targets.py:111` — **`FOCUS_SIZE = 12`**. Twelve words held as stored
membership in `learner.json`, drilled densely until they fire cold. A word leaves *only* on
graduation, and the vacated seat refills immediately from the global background.

He said he felt *"stuck in a little rotation of a few dozen words."* He is perceiving a
constant in the code. Both halves of "narrow and repetitive" are real, and they are two
different code paths: **narrow** is the twelve-seat conveyor, **scattered** is everything
else. He is standing on the seam.

## 3. The diagnosis

**There is no unit of progress between the day and the year.** A session is a day. The
comprehension goal is twelve months. Nothing in between has edges.

`focus_cohort` is a **conveyor, not a cohort**. It cannot be started, finished, won,
exceeded or reset — only turned. Its own docstring names what it inherited and what it
lost: *"What the deck proved and this keeps: a finite, visible, ordered set beats an
undifferentiated 339-row ledger. `FOCUS_SIZE` is that finite set now; what expired is the
deadline and the separate container."* **The boundary died with the container, and nothing
replaced it.**

The campaign block was the attempt to replace it and has no teeth: it reaches exactly one
consumer, `morning_knock.campaign_block()`, as prose for the model to read.
`suggest_targets.py` does not know it exists. `docs/PROTOCOL_MAP.md` states the split as a
design — *"It names no items; the ticket owns those."*

**Consequence.** Because nothing is ever finished, the only structure available to perceive
is the ritual — and rituals feel repetitive. And because the slip ledger is the only thing
carrying memory across days, the only visible continuity is his own recurring mistakes.
*"Short and pointed at my failures"* is not tone. It is the only cross-day memory the
machine has.

## 4. The object

**The campaign becomes a month with edges.** Not a new layer — the existing campaign block
and the existing `focus_cohort` fuse into one object with a date range, a name, a set, and
a win line.

- **Name** — capability-shaped: what this month *buys*, not a word count. The campaign
  block already holds this prose and keeps holding it.
- **Set** — **~30 items, cut once, held to the boundary.** A graduate leaves a *hole*, not a
  refilled seat. The hole is the remainder, and the remainder is what makes winning possible.
- **Won line — 15.** Both of Andrew's numbers, used as two numbers rather than averaged:
  15 is reachable (won), 30 is the ambition (exceeded). A single number forces a choice
  between disappointing and unreachable.
- **`FOCUS_SIZE` survives unchanged** as the dense-rotation window *inside* the month's set.
  The two-budget structure (focus / background) is proven and stays; what changes is that it
  draws from a bounded, named universe instead of the global pool.
- **Completion is a fold, never a stored counter.** A member closes when the observation log
  says it reached its target rung — `production: cold` for a mouth row, `recognition: solid`
  for an ear row. Both are already folds (`lexicon_view.derive`). **A stored counter can
  drift from reality; a fold cannot.** This is the honesty mechanism, and it is the direct
  answer to the deck's failure mode (45 of 70 items never asked while the meter reported a
  winning sprint).

## 5. The ear half

**Finding: the phone surface is already built and already correct.** The stars were retired
2026-09-13 for exactly the reason Andrew re-stated tonight — *"Stars measured mood, not the
tape… A tap should report a FACT"* — and replaced with three behavioural buttons (`finished
it` / `stopped early` / `lost the thread`), with quality moved to the **play count**.
Replays already count. **Nothing is proposed for the lock screen. It is done.**

What is missing is the granular half, and it does not belong on a phone:

- **The tap reports a fact.** Played; played again; lost the thread. Already shipped.
- **The session takes the measurement.** Anna picks **two or three lines** from a tape
  already heard — the lines carrying *this month's items* — and asks what they said.

**The constraint that makes or breaks it: a measurement, never a self-report.** *"Did you
catch it?"* cannot vote (`DECISIONS` → *"What he TOLD us and what we OBSERVED must never
share a field"*; *"seed and self-report are recorded and never vote"*), and Andrew already
rejected it on 2026-09-09: *"'did I get the gist' is not 'how many of the words we are
working on did I actually catch'."* **He must produce the meaning.** That is a `check`
event on a watched channel, and the rung follows.

The payoff tape stops being the test and becomes what it already is — **the answer key**.

**This is what makes an ear-shaped month closable**, and it removes the reason month one
would have had to be mouth-shaped.

## 6. What this replaces (Gate 4)

| Retired / absorbed | Why |
|---|---|
| `focus_cohort` as a free-floating conveyor | becomes the month's set, with a boundary |
| the campaign block as prose with one prose consumer | becomes the month's name and through-line, and now steers selection |
| `cmd_check --draw` — the monthly 30-row deterministic sample | replaced by the per-session, tape-anchored 2–3 item probe. `--heard` recording survives |
| the seed derivation in `floor_gap_targets` (`stable_jitter` path) | a month is cut deliberately; it is never derived from rep counts |
| `RETEST_SLOTS` / going-dark seat reservation *inside* the focus set | decay becomes a **month-cut** concern — a decayed row earns a seat in next month's cut, not a reserved seat every day |

**Honest scope correction.** In conversation I said most of the selector stack stops being
load-bearing. On closer reading that was overstated. The deletions above are real but
moderate; `recent_ask_counts`, the tier ordering and the background exposure queue all
survive and should. **The large simplification here is conceptual, not line-count**: one
bounded, named universe instead of pools competing for primacy on a 361-line ticket.

## 7. The laws this needs

Without these it becomes the ratchet Andrew is right to fear.

1. **Unmet is re-cut, never debt.** At the boundary, unmet items are re-cut by Anna — rolled
   only when genuinely central, dropped when the month said something wrong. Nothing is
   carried as a deficit and nothing is narrated as one. **The reset is the forgiveness
   mechanism**, and it must be written down or it becomes a streak by accident.
2. **Completion is derived, never stored.**
3. **Anna steers by the month; no number leaves his mouth.** `DECISIONS` #33 and
   `persona.md` are untouched — this is the standing law *"Meters steer Python's picks"*,
   extended to the month. The remainder is visible to Andrew on his own surfaces.
4. **The tap reports a fact; comprehension is never self-reported.**
5. **The month is re-cuttable mid-flight by Anna in one move, without ceremony** — the
   anti-frozen-deck rule. The deck's head froze because re-cutting cost something.

## 8. Out of scope, deliberately

- **The consolidation pass** (282 decisions, the inbox, the weirder smoke cases). Real, and
  second. Consolidating prose while the structural hole is open produces a tidier version of
  the same experience — and it is the more comfortable of the two jobs.
- **Native media (vlogs, phone calls).** No answer key, so it cannot be the instrument. The
  existing `feedback "[heard] …"` path already carries what it is good for. Build nothing.
- No new audio lane, no change to the knock rails, the studio, or the feed.

## 9. Risks and open questions

- **Month one can lose.** If ear rows close slowly, a mixed first month may miss 15 — and
  losing the first month is the worst possible start. Mitigation: cut month one weighted
  toward rows already in flight, so the win line is genuinely reachable.
- **Who cuts the first set?** Proposed: Anna, at the next session, from the live pool, with
  Andrew's veto in one sentence.
- **Thin end-of-month.** Once the set is closed, the live target list thins. That is the
  "exceeded" case working; overflow comes from the background queue, which is where breadth
  belongs.
- **Unanswered:** whether the month boundary is the calendar month or a rolling 30 days.
  Calendar is more legible; rolling avoids a stub first month. Andrew's call.

## 10. The silent no-op test

*"What does this look like when it silently does nothing, and can the system tell that state
apart from success?"*

It looks like: a month is cut, selection never references it, rows close from unrelated
activity, and the remainder counts down anyway. **Every instrument reads green.** So the
smoke cases must have teeth in that dimension:

- Over N session picks, **every item in the month's set is reached** (the `s34` `range(40)`
  pattern).
- A member closes **only** on a watched-channel event — an unwatched or self-reported one
  moves nothing.
- An unmet item at the boundary produces a re-cut, and **no debt field exists anywhere** to
  carry it.
- The remainder **equals the fold, recomputed** — asserted against a hand-built log, never
  against a stored number.
