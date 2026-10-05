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
  never restated taste.
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

Then the read-only sweep, all safe:
- `python scripts/sync_state.py status` — the ear, the floor, the soak order, the ear-block days
- `python scripts/sync_state.py feedback` — the accumulated ledger
- `grep -o '"move": "[^"]*"' progress/knock_log.json | tail -20` — dose shapes actually sent
- `progress/session_log.json` tail — what recent sessions actually did

The evidence decides; taste doesn't. A mechanism proposed before the sweep is a
symptom cap (`/debug` → KF-8 is the standing precedent).

## 4. One move, cheapest first

`protocol/diagnosis.md` law, verbatim: the default verdict is **change nothing**
(one data point is noise; a reproduced pattern is signal). Then at most one move:

1. **Turn a dial** — `progress/profile.md` Calibration Notes. Reversible. ~90% of healing.
2. **Prune** — delete the scene-type/meter/rule that isn't earning its place. First
   candidate: a "never" whose guarded failure can no longer happen — it is now only
   blocking (2026-10-05: the list ban was blocking the one format that measured him).
3. **Propose (gated)** — real structural gap → proposal + evidence to
   `docs/feature_inbox.md` for Andrew's yes/no. Building it is `/extend`'s job, later.

## 5. Close

Settled something → one line in `docs/DECISIONS.md` (title, date, one clause; the
narrative is the commit) so the next wave of this feeling meets a recorded conclusion. Nothing
settled → say "noise; nothing to change" and stop. That verdict is a success,
not a failure of the pass.
