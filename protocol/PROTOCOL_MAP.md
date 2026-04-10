# The Tamil Protocol Map

This document defines the structure and execution of the Tamil language learning system.

## Project Structure

- `curriculum/`          → Tiered vocabulary and grammar progression.
- `progress/`            → JSON tracking of the learner's vocabulary state.
- `protocol/`            → The generative logic (how to write lessons).
- `protocol/roles/`      → Specific instructions for the AI agents (Director, Architect, Producer).
- `content/beats/`       → Intermediate "Beat Sheets" for mission planning.
- `content/scripts/`     → Final TTS-ready lesson scripts.
- `scripts/`             → Python tools (audio gen, vocab builder, dashboard, spaced repetition)

---

## Core Protocols

| Module | Location | Purpose |
|:---|:---|:---|
| **Philosophy** | `protocol/philosophy.md` | Core philosophy, tactical rules, and **canonical rules** (referenced by all roles) |
| **Learning Loop** | `protocol/learning_loop.md` | 5-phase immersion cycle |
| **Session** | `protocol/session_protocol.md` | Interactive lesson handling |
| **Inspiration** | `protocol/episode_rotation.md` | Optional episode flavors and seeds |
| **Director** | `protocol/roles/director.md` | Vocabulary payload (NEW + callbacks) + beat sheet |
| **Architect** | `protocol/roles/architect.md` | Two-voice script with full creative freedom |
| **Producer** | `protocol/roles/producer.md` | Dialect ear and cleanup for spoken Coimbatore Tamil |
