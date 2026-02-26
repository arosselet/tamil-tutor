# Tamil Protocol Map (The Index)

**Purpose:** Primary entry point for any LLM agent interacting with this codebase. Routes to the right protocol file based on the task.

> **🤖 AGENT PROTOCOL:**
> 1. **ALWAYS** read `protocol/philosophy.md` first to understand the rules.
> 2. **ALWAYS** read `progress/learner.json` to know the learner's current state.
> 3. Then route to the appropriate protocol below.

## Routing

| User Says | Protocol | Action |
|---|---|---|
| `@tutor` (or request a lesson) | `protocol/learning_loop.md` | Entry point for learning and generation. Starts with Phase 1 Debrief. **NO TEMPLATING ALLOWED.** |
| `/build` (or default coding) | `<Self-Directed>` | Default engineering mode. Safe to edit protocol files and scripts. |
| "I listened to mission X" | `protocol/session_protocol.md` | Update `progress/learner.json` |
| "Show my progress" | Read `progress/learner.json` + `index.json` | Report tier progress, streaks |
| "Sync these updates" | `protocol/sync_ingest.md` | Apply mobile updates to learner.json + vocab index |
| *(On mobile, after progress)* | `protocol/mobile_sync.md` | Emit JSON progress blob for desktop Debrief |

## System Architecture

```
protocol/           → LLM instructions (you are here)
curriculum/
    ├── index.json      → Manifest (titles, tiers)
    └── tiers/          → Consolidated Tier buckets (tier_1_survival.json...)
content/scripts/     → Podcast scripts (Markdown)
audio/               → Generated MP3 files
progress/            → learner.json (learner state)
scripts/             → Python tools (audio gen, vocab builder, dashboard)
```

## Core Files

| Category | File | Purpose |
|---|---|---|
| **Philosophy** | `protocol/philosophy.md` | Dialect, goals, tactical rules |
| **Immersion Gradient** | `protocol/immersion_gradient.md` | TEACH/USE/CALLBACK modes, Host language ratio by tier |
| **Learning Loop** | `protocol/learning_loop.md` | 5-phase immersion cycle |
| **Session** | `protocol/session_protocol.md` | Interactive lesson handling |
| **Rotation** | `protocol/episode_rotation.md` | Rolling style rotation engine |
| **Director** | `protocol/roles/director.md` | Beat sheet + Word Status Sheet from vocabulary |
| **Architect** | `protocol/roles/architect.md` | Script from beat sheet (gradient-aware) |
| **Producer** | `protocol/roles/producer.md` | TTS-ready script (Tamil Script enforcement) |
| **Mobile Sync** | `protocol/mobile_sync.md` | Phone-side: when/how to emit progress JSON |
| **Sync Ingest** | `protocol/sync_ingest.md` | Desktop-side: apply mobile updates |
| **Curriculum** | `curriculum/tiers/tier_X.json` | Source of truth for Tiers + vocab |
| **Learner** | `progress/learner.json` | Source of truth for learner state |
