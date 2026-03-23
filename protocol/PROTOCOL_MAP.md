# The Tamil Protocol Map

This document defines the structure and execution of the Tamil language learning system.

## Project Structure

- `curriculum/`          → Tiered vocabulary and grammar progression.
- `progress/`            → JSON tracking of the learner's vocabulary state.
- `protocol/`            → The generative logic (how to write lessons).
- `protocol/roles/`      → Specific instructions for the AI agents (Director, Architect, Producer).
- `content/beats/`       → Intermediate "Beat Sheets" for mission planning.
- `content/scripts/`     → Final TTS-ready lesson scripts.
- `scripts/`             → Python tools (audio gen, vocab builder, dashboard)

---

## Core Protocols

| Module | Location | Purpose |
|:---|:---|:---|
| **Immersion Gradient** | `protocol/immersion_gradient.md` | Single source of truth for word weaving (TEACH/EXPOSE/USE/CALLBACK) |
| **Learning Loop** | `protocol/learning_loop.md` | 5-phase immersion cycle |
| **Session** | `protocol/session_protocol.md` | Interactive lesson handling |
| **Rotation** | `protocol/episode_rotation.md` | Examples of narrative styles and settings |
| **Director** | `protocol/roles/director.md` | Strategic planning (Narrative context + Word Retrieval) |
| **Architect** | `protocol/roles/architect.md` | Tactical writing (Scripting the Intercept + Breakdown) |
| **Producer** | `protocol/roles/producer.md` | Final TTS audit (Tamil Script + Spoken Register) |
| **Earworm** | `protocol/learning_loop.md` | (Note: Part of Discovery Phase — see Phase 3) |
