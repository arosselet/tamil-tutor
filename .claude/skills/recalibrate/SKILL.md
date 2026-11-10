---
name: recalibrate
description: Structured pedagogy recalibration — felt signal → evidence → one move. Use when Andrew questions the pedagogy or curriculum ("feels like a chore/drill", "not landing", "strengthen the curriculum", "review the system against my goals"), or reports the same felt-complaint a second time. NOT for plumbing symptoms — that's /debug.
---

# Recalibrate — Felt Signal → Evidence → One Move

June–July 2026: the same "system isn't landing" conversation was re-derived from
scratch ~10 times ("7/10 → 10/10" ×3, "top-down curriculum strengthening" ×3,
"it's a drill/chore" ×4) — each an unscoped architecture session, several ending
in mechanisms later reverted. This skill replaces that with a bounded pass. The
law underneath is `protocol/diagnosis.md` (Anna's periodic self-check); this is
the same discipline run deliberately, with Andrew at the table.

## 1. Capture the felt signal, verbatim

One sentence in Andrew's words — not your paraphrase. Log it immediately:
`python scripts/sync_state.py feedback "<what Andrew said>"` (mutating, one line).
The ledger across sessions is what turns feelings into evidence.

## 2. Check it isn't already settled

- `docs/DECISIONS.md` — has this axis been ruled on? If yes, name the entry to
  Andrew before anything else. Reopening a settled decision needs *new evidence*,
  never restated taste. But naming the entry is where the answer starts: give its
  reason in a sentence and test whether that reason still holds. *"It's not 'we
  settled this 09-13', it's 'does that logic still apply, was it a proper move?'"*
  (Andrew, 2026-10-13.) His felt signal is itself new evidence about the entry.
- `progress/feedback_log.json` — prior felt-signals on the same axis. A signal's
  **third strike on one axis is a design flaw, not noise** (precedent: 07-11
  "walking into a drill" → 07-17 "starved of teaching" → 07-17 "it's a chore"
  became the break contract only on the third).

## 3. Evidence before proposals — read, don't theorize

**First, audit the model against Andrew (2026-10-04).** Every planner acts on the
lexicon's picture of him, so a complaint about what the system *does* may be a
true picture driven badly — or a false picture driven well. Tuning selection,
format or pedagogy only helps in the first case. Draw ~15 rows the complaint
touches and ask him their meanings (ask-then-reveal, never "which do you know").
If the rungs disagree with his answers, the move is the feedback loop, not the
planner. Precedent: "why do I keep hearing words I know" — 356 of 392 rows read
`struggled`; of 46 swept words, 31 came back right and 4 half-right. Two cheap tells that
the picture is stale: an implausible distribution (sari as `struggled` after
eight months), and evidence about the machine (`taught`, `exposed`) outnumbering
evidence about him (`tested`, `attended`) by an order of magnitude.

**Second, trace the behaviour to the rule producing it (2026-10-05).** A
complaint about what the system does is a rule doing its job somewhere. Find it
(`grep` the protocol and mandates for the behaviour) and read the symptom it was
written for. If that symptom can no longer happen, the rule is the fault, and
the move is to retire or loosen it. Precedent: "the same few dozen words" traced
to the vocabulary fence (95% coverage over a fence of ~135 words) fed by a false
picture, and the check that would have fixed it was banned by Rule 4 as a list.

**Third, when the complaint is sameness, read what Anna reads (2026-10-16).** *"Now
every lesson takes that shape. What happened?"* had no single rule behind it. Run
`sync_state.py open` and `status` and mark every line worded as an instruction: several
meters and cues, each leaning the same way, had turned every lesson into
clip-then-questions. The move was to reword and demote those lines.

Then the read-only sweep, all safe:
- `python scripts/sync_state.py status` — the ear, the soak order, the ear-block days (`--numbers` adds the floor)
- `python scripts/sync_state.py feedback` — the accumulated ledger
- `grep -o '"move": "[^"]*"' progress/knock_log.json | tail -20` — dose shapes actually sent
- `progress/session_log.json` tail — what recent sessions actually did

The evidence decides; taste doesn't. A mechanism proposed before the sweep is a
symptom cap (`/debug` → KF-8 is the standing precedent).

## 4. One move, subtraction first

`protocol/diagnosis.md` law, verbatim: the default verdict is **change nothing**
(one data point is noise; a reproduced pattern is signal). Then at most one move:

1. **Prune** — retire or loosen the rule step 3 traced, or the scene-type/meter
   that isn't earning its place. Subtraction first, because every addition is a
   rule a future symptom has to trace through. First candidate: a "never" whose
   guarded failure can no longer happen — it is now only blocking (2026-10-05: the
   list ban was blocking the one format that measured him).
2. **Turn a dial** — `progress/profile.md` Calibration Notes. Reversible.
3. **Propose (gated)** — real structural gap → proposal + evidence to
   `docs/feature_inbox.md` for Andrew's yes/no. Building it is `/extend`'s job, later.

**A meter or a rating ask is the wrong answer to an engagement complaint (2026-10-16).**
A felt/shape sensor was built and withdrawn the same day: *"a new tracking feels the
wrong move to answer this problem… I was hoping more for a sharp diagnosis."* Engagement
is read from how he is showing up — replies, silence, what he comes back for, what he
says unprompted — and he is asked only when that is unclear. Give him the diagnosis
before any move, in plain words.

## 5. Close

Settled something → one line in `docs/DECISIONS.md` (title, date, one clause; the
narrative is the commit) so the next wave of this feeling meets a recorded conclusion. The
repo is the only place a conclusion counts: one saved to an assistant's memory is on one
machine and invisible to every other agent (Andrew, 2026-10-13 and 10-14). Nothing
settled → say "noise; nothing to change" and stop. That verdict is a success,
not a failure of the pass.
