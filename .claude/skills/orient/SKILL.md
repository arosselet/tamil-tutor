---
name: orient
description: First-session onboarding for this repo — what the system is, the two hats (Anna vs @build), reading order for @build context, subsystem map, and pointer to the project glossary. Use when: starting fresh work on this repo, onboarding a new model or engineer, or asking "where does X live?"
---

# Orient — Tamil Learning System Onboarding

## What This System Is

An n-of-1 Tamil-learning system for one learner (Andrew). One persistent LLM persona — **Anna** (elder brother, he/him) — runs a daily forced-output chat loop: Anna hands the learner an English situation, the learner must produce the Tamil back. A **studio** pipeline produces podcast episodes that soak exactly what the chat session just strained, closing the recognition-to-production loop. Between sessions, a **knock** system (GitHub Actions cron + `scripts/morning_knock.py`) does agentic phone outreach; Andrew types Tamil replies that `scripts/knock_reply.py` judges. Scheduled nudges live in `progress/push_queue.json`, drained at the start of every Anna wake-up by CI. All learner state lives in `progress/` as Python-owned JSON — never hand-edit it.

The design principle is **"LLM is the writer, Python is the brain"** — Python owns every state write, and every evidence field is the fold of `progress/observations.json`. Structure is controlled by budgets, not a freeze: content rows are always free; a file or field is budgeted in the diff that adds it. Full law lives in `docs/DECISIONS.md` (settled decisions, one line each — do not re-litigate) and `docs/PROTOCOL_MAP.md` (the only map); read both before any structural work.

---

## The Two Hats

### Anna (default) — run the lesson

No keyword needed. Invoked via `/anna` in Claude Code; any other agent reads `.claude/skills/anna/SKILL.md` directly.

His identity, loading order, and the session loop are owned by `.claude/skills/anna/SKILL.md` (which routes to `protocol/persona.md` + `protocol/daily_session.md`) — don't restate them here; read that shim if you need the sequence.

Anna does **not** load `docs/PROTOCOL_MAP.md`, `docs/DECISIONS.md`, or `BOOTSTRAP.md`. Those are the engineer's map.

### `@build` — work on the machine

Invoked by typing `@build` in the message. Role: Python developer and system architect. Edits the machine; never runs the lesson.

Files @build loads — see the reading order below.

---

## @build Reading Order

Read these before any structural work. Stop at the first doc that closes your question.

| # | File | Why it matters |
|---|---|---|
| 1 | `docs/DECISIONS.md` | Settled decisions — read before ANY structural change; prevents re-litigating closed questions |
| 2 | `docs/PROTOCOL_MAP.md` | Full architecture: subsystem map, state schema, Python brain inventory, the soak-order contract |
| 3 | `BOOTSTRAP.md` | Portability layer: the four-layer map (pedagogy / machinery / language pack / learner pack), port surface, and day-zero behavior |
| 4 | `protocol/constitution.md` | The canonical rules the learning system enforces — mandatory before editing any `protocol/` file |
| 5 | `docs/feature_inbox.md` | Where build-itches park, one line each — check before acting on an idea |

For the Python brain: read the script you intend to change, plus the `scripts/smoke/` layer file that covers it before touching anything that writes state — `smoke_test.py` itself is now only the dispatcher.

---

## Subsystem Map

`docs/PROTOCOL_MAP.md` — the only one (2026-09-10; the table that used to sit here was a second copy and drifted).

## Where to Go From Here

**Glossary** — every project-jargon term a newcomer will hit (viability floor, soak-order, engines, heist, Intercept, Breakdown, scene spec, etc.) with a 1–2 line definition and the file where each is defined: `references/glossary.md`.

**Sibling skills** (procedures, not orientation):

| Task | Skill |
|---|---|
| Diagnose a failure | `/debug` |
| Routine health checks | `/validate` |
| Make a change to the system | `/extend` |
| Prove a change works end-to-end | `/verify` |
| Pedagogy feels wrong (chore/drill/samey) | `/recalibrate` |
