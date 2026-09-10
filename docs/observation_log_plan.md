# The Observation Log — open planning

> **Status: DIRECTION APPROVED 2026-09-10, not yet built.** Andrew lifted the *Structure
> freeze — Anna 1.0* for this specifically: *"structure freeze is a suggestion and this sounds
> like a more foundational solution to a very persistent problem. I agree it has been earned."*
>
> **Read this for its shape.** It is the third open planning document in this repo, after
> `comprehension_plan.md` (which measures the outcome) and this one (which fixes the
> instrument). It names its own risk, and it says what it will NOT do.

## The problem, in one line

**Evidence is applied and then discarded.** `rec["recognition"] = next_level` spends an
observation to move a field, and the observation itself is gone — what channel it came from,
what was asked, how confident it was, what else was true that day. Provenance has been the
named missing thing since 2026-08-23 and it keeps not getting added, because there is nowhere
to put it: the row is the only artifact.

**One defect, five faces, all the same shape** (see `DECISIONS.md` → "What he TOLD us and what
we OBSERVED must never share a field"): the day-one seed estimate; the mission debrief logged
as live fire; "didn't do it" indistinguishable from "couldn't do it"; the Receptive Check's
gist self-report; and `struggled` doing the work of *never introduced*, *introduced and did
not stick*, and *never asked*.

Each was patched locally. It came back each time, because the shape was never addressed.

## The one idea

**An observation is an event, not a field mutation.** Append-only log; the lexicon becomes a
derived view over it.

```
{ "at":      "2026-09-05T10:38:00Z",
  "word":    "வந்துட்டேன்",
  "channel": "eavesdrop",        // where it came from — carries trust
  "kind":    "tested",           // taught | exposed | tested | asked-about | claimed
  "axis":    "recognition",      // recognition | production | null
  "result":  "wrong",            // right | wrong | partial | null
  "source":  "knock:2026-09-05T10-38",   // the artifact, for audit
  "note":    "read as 'came', not 'came to where we are'" }
```

Four decisions inside that shape, each load-bearing:

- **`kind` and `result` are separate.** An exposure has no result. A test does. **`asked-about`
  is its own kind** — Andrew volunteering *"enaa is a new word for me actually"* is evidence of
  a different sort than a failed test, and it is currently thrown away entirely.
- **`channel` carries trust, and a policy decides what counts.** `seed` and `self-report` are
  recorded and excluded by default. **The ritual survives; its output stops voting.**
- **`axis` is explicit**, because recognition and production move independently and always have.
- **`source` points at the artifact**, so any claim can be walked back to the knock, session or
  episode that produced it.

## What it dissolves

| Today | Under the log |
|---|---|
| Provenance is a missing companion field | Inherent — every event has a channel |
| The seed estimate is indistinguishable from evidence | `channel: seed`, excluded by policy |
| A mission debrief counts as strongest evidence | `channel: self-report`, recorded, not counted |
| "Never tested" is a default pretending to be a judgment | Absence of `kind: tested` events |
| Teach-vs-drill reads one overloaded field | Two queries: does a `taught` event exist; what do later tests say |
| A bad rule can only be fixed by purging rows | Re-derive history under the new policy |

**That last row is the one Andrew asked for by name.** He said failing forward is fine and
discontinuities in the measurement are fine. A log is what makes revision cheap. The August
purge dropped 108 rows because re-reading them was impossible; with a log they would have been
re-scored, not deleted.

## Migration — four phases, and the first is free

- **Phase 0 — write events alongside.** Every current writer also appends. Nothing reads the
  log. Strictly additive, reversible by deleting a file, and the daily loop never notices.
- **Phase 1 — backfill from what is recoverable.** `knock_log.json` holds every reply with its
  verdict and timestamp; `session_log.json` holds cold/hinted by date; git holds the lexicon's
  whole history, including the first populated commit whose 153 rows become `channel: seed`.
  **The backfill is itself the audit** — it says, for all 360 rows, what evidence exists and
  from where. It does NOT say what Andrew knows; rows with no evidence still need testing, so
  `ledger_audit_2026-09-10.md` keeps its job and gets sharper about which rows are worth
  sampling.
- **Phase 2 — derive in parallel and diff.** Build the view, compare against the live lexicon,
  and explain every divergence before trusting it. A divergence is a finding, not a bug to
  paper over.
- **Phase 3 — flip the readers.** `lexicon.json` becomes generated. Meters become queries with
  a stated policy.

## What this does NOT touch

The lanes, the studio, the feed, the rails, the publishing tail, the knock policy, the persona,
the dialect pack. **This is the state layer only** — one JSON file and three writers
(`knock_reply.py`, `render_audio.py`, `sync_state.py`). Nothing about how Anna talks or what
gets rendered changes.

## The honest risk

This is the class of refactor that eats weeks and shows nothing. Two mitigations, both real:

1. **Phase 0 and 1 deliver on their own.** A backfilled log answers "what do we actually know
   about this word, and how" for every row, with no behaviour change at all.
2. **Nothing is deleted.** The log is additive; the lexicon stays authoritative until Phase 3.
   If the idea is wrong, the loss is an append-only file nobody reads.

The risk that is NOT mitigated: attention. This is engineering, and the daily session is the
point. **The lesson of May 2026 is that the machine can be improving while the learner fades.**
Phase 0 must not become a reason to skip a session.

## The companion problem — a map bigger than our own footprint

The lexicon holds what the system introduced, so it can never name a hole. Selection therefore
happens entirely inside the system's own output.

**The in-country harvest that would have fixed this expired with the return flight, and the
next trip may be a year out** (Andrew, 2026-09-10), so waiting is not a plan. The sources that
exist without a trip:

- **Spoken-Tamil subtitle and transcript corpora** — film and serial subtitles are colloquial
  register, free, and large. Not Kongu, and that matters far less for a *frequency list* than
  for pronunciation: the high-frequency verbs, tails, clitics and glue are largely shared, and
  those are exactly the layer `comprehension_plan.md` §2 calls the cheap, finite, high-leverage
  half.
- **Transcripts of whatever native media he actually watches** — the auxiliary lane producing
  the map as a by-product of being used.

Kept deliberately **separate from `lexicon.json`**, with its own lifecycle: the lexicon is what
he has met, the inventory is what the register uses, and *what is missing* is the set
difference. That question cannot be asked today at all.

## Open

1. Does the Receptive Check get rebuilt on the log, or stay independent? (Probably the log —
   an event with `channel: check`.)
2. What is the default policy for the headline meters, stated in one sentence?
3. Inventory sourcing: pick a corpus, or start from his own media transcripts and grow?
