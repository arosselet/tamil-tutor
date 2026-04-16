# The Tamil Protocol Map

This document defines the structure and execution of the Tamil language learning system.

## Project Structure

- `curriculum/`          → Tiered vocabulary and grammar progression.
- `progress/`            → Learner state: JSON (Python-managed) and profile (LLM-maintained).
- `protocol/`            → The generative logic (how to write lessons).
- `protocol/roles/`      → Role instructions for Director, Architect, Producer.
- `content/beats/`       → Intermediate beat sheets for mission planning.
- `content/scripts/`     → Final TTS-ready lesson scripts.
- `scripts/`             → Python tools (audio gen, vocab builder, spaced repetition).

---

## Core Protocols

| Module | Location | Purpose |
|:---|:---|:---|
| **Philosophy** | `protocol/philosophy.md` | Core philosophy, tactical rules, and **canonical rules** (referenced by all roles) |
| **Hosts** | `protocol/hosts.md` | Cast bible — all four voices (Intercept hosts + Breakdown analysts). Read by Architect, Producer, Director. |
| **Dialect** | `protocol/dialect.md` | Tamil/Coimbatore spoken dialect rules — verb forms, Sandhi, Kongu layer. Language-specific; swappable. |
| **Learning Loop** | `protocol/learning_loop.md` | 5-phase immersion cycle |
| **Session** | `protocol/session_protocol.md` | Interactive lesson handling |
| **Inspiration** | `protocol/episode_rotation.md` | Optional episode flavors and seeds |
| **Director** | `protocol/roles/director.md` | Vocabulary payload (NEW + callbacks) + beat sheet. Reads `progress/profile.md`. |
| **Architect** | `protocol/roles/architect.md` | Two-voice script — structure and story only. Reads `protocol/hosts.md` + `protocol/dialect.md`. |
| **Producer** | `protocol/roles/producer.md` | Dialect pass + script integrity. Applies `protocol/dialect.md`. |

## Learner State Files

| File | Managed by | Purpose |
|:---|:---|:---|
| `progress/learner.json` | Python (`sync_state.py`) | Thin working memory — active mission, streak, status line |
| `progress/vocab_state.json` | Python (`sync_state.py`) | Full vocab tracking — mastered, comfortable, struggled, episode listen counts |
| `progress/word_tracker.json` | Python (`generate_callbacks.py`) | Per-word appearance counts across scripts — drives spaced repetition |
| `progress/profile.md` | LLM (`@tutor`) | Teacher's notebook — learner assessment, gaps, terrain map, 3-month goal. Rewritten every ~5 sessions. |
