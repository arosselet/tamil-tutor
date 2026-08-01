---
name: orient
description: First-session onboarding for this repo — what the system is, the two hats (Anna vs @build), reading order for @build context, subsystem map, and pointer to the project glossary. Use when: starting fresh work on this repo, onboarding a new model or engineer, or asking "where does X live?"
---

# Orient — Tamil Learning System Onboarding

## What This System Is

An n-of-1 Tamil-learning system for one learner (Andrew). One persistent LLM persona — **Anna** (elder brother, he/him) — runs a daily forced-output chat loop: Anna hands the learner an English situation, the learner must produce the Tamil back. A **studio** pipeline produces podcast episodes that soak exactly what the chat session just strained, closing the recognition-to-production loop. Between sessions, a **knock** system (GitHub Actions cron + `scripts/morning_knock.py`) does agentic phone outreach; Andrew types Tamil replies that `scripts/knock_reply.py` judges. Scheduled nudges live in `progress/push_queue.json`, drained at the start of every Anna wake-up by CI. All learner state lives in `progress/` as Python-owned JSON — never hand-edit it.

The design principle is **"LLM is the writer, Python is the brain"** — Python owns every state write. Structure is frozen at **Anna 1.0**: content rows are always free; schema changes park in `docs/feature_inbox.md`. Full law lives in `docs/DECISIONS.md` (settled decisions — do not re-litigate) and `docs/PROTOCOL_MAP.md` (the architecture map); read both before any structural work.

---

## The Two Hats

### Anna (default) — run the lesson

No keyword needed. Invoked via `/anna` (Claude Code) or `.gemini/commands/anna.toml` (Gemini).

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
| 5 | `docs/feature_inbox.md` | Where build-itches park during the structure freeze — check before acting on an idea |

For the Python brain: read the script you intend to change, plus `scripts/smoke_test.py` before touching anything that writes state.

---

## Subsystem Map

| Subsystem | Entry File | One-line purpose |
|---|---|---|
| Chat loop (Anna) | `.claude/skills/anna/SKILL.md` | Daily forced-output session; commissions studio, queues pushes |
| Studio (audio) | `protocol/studio/studio.md` | Three-pass episode pipeline: Director → Architect → Producer → render |
| Knock (outreach) | `scripts/morning_knock.py` | Agentic phone reach: rails gate + Anna's fire/silence policy; CI workflow: `.github/workflows/anna.yml` |
| Push queue | `scripts/push_queue.py` | Durable scheduled pushes, composed at add-time (voice doses rendered at fire time); drained at the start of every Anna wake-up by `.github/workflows/anna.yml` |
| Reply judge | `scripts/knock_reply.py` | Judges typed Tamil replies; moves the production axis; triggered by `.github/workflows/anna.yml` |
| State | `scripts/sync_state.py` | Owns all writes to `progress/`; run `python scripts/sync_state.py status` to inspect safely |
| CI | `.github/workflows/` | Two workflows: `anna.yml` (every trigger, every secret — consolidated 2026-07-24) and `smoke.yml` |

---

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
