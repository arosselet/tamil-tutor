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

**The size budgets.** Both surfaces are ratcheted, asserted by the same smoke case
(`scripts/smoke_test.py` → `s18_size_budgets`):

| Surface | Table | Unit | Since |
|---|---|---|---|
| Protocol prose — `persona.md`, `constitution.md`, `daily_session.md`, `audio_channels.md`, `commissioning.md`, the LLM mandates | `PROSE_BUDGETS` | words | 2026-07-16 |
| Every `scripts/*.py` | `CODE_BUDGETS` | code lines (blanks, comments and docstrings are **free**) | 2026-07-31 |

One law for both: growth past budget is a red run; raising a budget is allowed only in the
same diff as the growth, and the commit must name what it retired. A file that keeps
hitting its ceiling is carrying crud or doing too many jobs — a split-or-retire signal,
never a bump-the-number reflex.

Two things specific to code. **Comments cost nothing** — the diagnosis layer is a third of
this codebase and it is why the silent-failure bugs were findable; the budget bounds
mechanism, so explain freely and cut logic. **A new `scripts/*.py` with no entry in
`CODE_BUDGETS` is itself a red run** — adding a file is the obvious way past a ceiling, so
budget it in the same diff that creates it. `smoke_test.py` is exempt on purpose (Gate 7
demands a case per fixed bug; test volume is the one growth this system wants unbounded).

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
| LLM prompts with Tamil-specific prose rules (script vs. phonetic, Woven Thanglish) | `scripts/morning_knock.py` (decide prompt), `scripts/knock_reply.py` (judge prompt + `SLIP_MANDATE`), `scripts/render_drill.py` (drill-script prompt) |
| `TAMIL_RE` — script-detection regex that enforces Tamil script as canonical lexicon keys | `scripts/state_io.py` line 54 |
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

2. **THE SILENT NO-OP TEST — answer it out loud before the case is written**
   (2026-07-31). *"What does this look like when it silently does nothing, and can the
   system tell that state apart from success?"*

   Every deep bug of 2026-07-24→31 was a state **indistinguishable from success**: the
   soak order was set but held no repair; the deck surfaced items but 45 of 70 were never
   asked while the meter reported a winning sprint; a callback rode the script but minted
   no lexicon record; `--slip-tested` wrote a close the same update erased. Nothing
   crashed. Every instrument read green. The common root cause: **the meters measured
   that a step RAN, never that its PURPOSE was served.**

   So the case must have teeth *in the dimension the thing can actually fail*:

   - **Assert the effect, not the execution.** Not "the order was written" but "the order
     contains the day's repair". Not "the item was surfaced" but "over N selections every
     item is reached" (`s34`'s `range(40)` loop is the pattern to copy).
   - **Round-trip through the writer.** Drive the real command entry point, then RE-READ
     the state file. `s41` shipped 2026-07-30 with a green case that never called
     `cmd_update` and never re-read `learner.json` — the feature was dead on arrival for a
     day because the whitelist in `write_thin_learner` deleted the field. The test tested
     the function; the bug was in the round trip.
   - **An absence must be loud.** A lookup that resolves to nothing, an unreadable
     sidecar, a flag nothing can discharge — report it. A warning that cannot be
     discharged is noise by construction, and gets walked past for mechanical reasons,
     not inattention.

   If the honest answer is "it would look exactly like success", the change is not
   finished — that is the bug, still in the diff.

3. **Run `/verify`** — the sibling skill that proves the change end-to-end.

4. **Never hand-edit Python-owned JSON.** State advances through `sync_state.py`;
   `progress/*.json` files are the brain. (`docs/DECISIONS.md` → "LLM is the writer,
   Python is the brain.")

5. **Commit hygiene.** Match the house style from the real log:
   `Subsystem: what changed (context if needed)` — short subject, sentence case,
   parenthetical for date/feedback attribution. No ticket numbers.

6. **CI git identity is `github-actions[bot]`** — never a noreply alias that credits
   a real GitHub user. (`docs/DECISIONS.md` → "CI git identity is `github-actions[bot]`.")

---

## Sibling skills

- `/orient` — what the system is; glossary of project jargon
- `/debug` — symptom → evidence triage; per-subsystem failure playbooks
- `/validate` — routine health checks; safe/mutating command inventory
- `/verify` — proving a change works end-to-end
- `/recalibrate` — pedagogy felt-signals; felt signal → evidence → one move
