---
name: extend
description: The change discipline for @build — gates that every modification must pass before code is written. Use when adding, editing, or removing any file, prompt, script, constant, or schema field in the Tamil system.
---

# Extend — Change Discipline

Every change to the machine passes these seven gates in order. Each gate has an
explicit stop-condition. Do not jump ahead.

---

## Gate 1 — DECISIONS check

Read `docs/DECISIONS.md` (thin index of conclusions; substance lives in git history).

**Stop condition:** the change re-litigates a settled decision. Reopening requires new
evidence taken to Andrew — never silent drift. Common reopened traps: adding a schema
field, adding a tracking mechanism, adding a persona.

---

## Gate 2 — Structure-freeze test

Anna 1.0 is frozen. Full law: `docs/PROTOCOL_MAP.md` → "Structure freeze — Anna 1.0".

Ask: *does this add a row of data, or change a schema / add a file / add a meter?*

- Row of data (a word, a scene, a memory) → proceed.
- Schema change / new file / new meter → write one line in `docs/feature_inbox.md`
  and **stop**, unless Andrew explicitly commissioned it this session.

---

## Gate 3 — Explore before implement

Andrew is an architect. When he names a problem he wants the shape and tradeoffs
explored together first. (`docs/DECISIONS.md` → "Explore before implementing.")

**Stop condition:** Andrew has not yet *explicitly* said yes — named the approach,
approved the tradeoff, or said "do it." Silence, a question, or non-objection is NOT
alignment. Until then: state the real situation sharply; do not produce a
bullet-pointed action plan, and write no code.

**Exploring includes the plumbing.** Read the owning file and the relevant log *before*
proposing any mechanism — never hand Andrew a choice between mechanisms the evidence
hasn't earned. A mechanism proposed before diagnosis is a symptom cap, and the better
half of the real fix is often a deletion only reading the file can find (the full
precedent lives in `/debug` → KF-8).

---

## Gate 4 — What does this replace?

Every addition must earn its place. Before writing any code, state out loud:
*"This replaces / simplifies ___."* (`docs/DECISIONS.md` → "Every addition must earn its place.")

**The word budget (2026-07-16).** The protocol's prose surfaces — `persona.md`,
`constitution.md`, `daily_session.md`, the outreach mandate — carry word budgets asserted
by `scripts/smoke_test.py` → `PROSE_BUDGETS`; growth past budget is a red run. Raising a
budget is allowed only in the same diff as the growth, and the commit must name the lines
it retired. A file that keeps hitting its ceiling is carrying crud or doing too many jobs —
a split-or-retire signal, never a bump-the-number reflex.

If you cannot name what it replaces, that is the signal to stop.

---

## Gate 5 — Surgical-edit routing

Concerns are separated on purpose. Find the one file that owns the concern you are
touching; edit only that file. (`docs/DECISIONS.md` → "Surgical edits to the relevant file.")

Routing table: `references/routing.md` — concern → exact file (with line references
where the value is a constant).

---

## Gate 6 — Port-surface check

The three items below are invisible to a `swap-the-.md-files` pass. Changing any of
them silently breaks a port to another language. Document what you changed and why in
the commit body if you touch one. (`BOOTSTRAP.md` → "What Generalizes" → Layer 1.)

| Item | Location |
|---|---|
| LLM prompts with Tamil-specific prose rules (script vs. phonetic, Woven Thanglish) | `scripts/morning_knock.py` (decide prompt), `scripts/knock_reply.py` (judge prompt), `scripts/render_drill.py` (drill-script prompt) |
| `TAMIL_RE` — script-detection regex that enforces Tamil script as canonical lexicon keys | `scripts/sync_state.py` line 56 |
| Pinned TTS voice IDs — `ANNA_VOICE` for knocks/drills; voice pools for episodes | `scripts/morning_knock.py` line 50; `scripts/render_audio.py` |

Also check: `REPO = "arosselet/tamil-tutor"` (`scripts/morning_knock.py` line 51) —
the jsDelivr CDN URL for knock audio; a fork must update this.

**Cloud rendering:** the cloud DOES render — knock memos and scheduled voice doses, in
`anna.yml`, the single workflow that carries every secret. The old "cloud never renders /
do not add TTS to other workflows" rule was dropped 2026-07-24 (it was misnamed: the
blocker was always the *writer*, `agy`, never the renderer). Episode TTS is still local
today, but that is a build not yet done, not a law. (`docs/DECISIONS.md` → "Cloud produces
episodes" and "One runner, every capability.")

---

## Gate 7 — Post-change duties

Run these after every non-trivial change to the machinery:

1. **New smoke case for every fixed plumbing bug.** (`scripts/smoke_test.py` docstring:
   "A fixed bug becomes a case here the day it's fixed.") Add a scenario function
   (`sN_...`) following the existing pattern; do not write ad-hoc scripts.

   Safe to run (sandboxed — no secrets, no network, no writes outside tempdir):
   ```
   python scripts/smoke_test.py
   ```

2. **Run `/verify`** — the sibling skill that proves the change end-to-end.

3. **Never hand-edit Python-owned JSON.** State advances through `sync_state.py`;
   `progress/*.json` files are the brain. (`docs/DECISIONS.md` → "LLM is the writer,
   Python is the brain.")

4. **Commit hygiene.** Match the house style from the real log:
   `Subsystem: what changed (context if needed)` — short subject, sentence case,
   parenthetical for date/feedback attribution. No ticket numbers.

5. **CI git identity is `github-actions[bot]`** — never a noreply alias that credits
   a real GitHub user. (`docs/DECISIONS.md` → "CI git identity is `github-actions[bot]`.")

---

## Sibling skills

- `/orient` — what the system is; glossary of project jargon
- `/debug` — symptom → evidence triage; per-subsystem failure playbooks
- `/validate` — routine health checks; safe/mutating command inventory
- `/verify` — proving a change works end-to-end
- `/recalibrate` — pedagogy felt-signals; felt signal → evidence → one move
