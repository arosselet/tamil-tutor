# Tamil Protocol Map (The Index)

**Purpose:** Primary entry point for any LLM agent interacting with this codebase. Routes to the right protocol file based on the task.

> **🤖 AGENT PROTOCOL:**
> 1. **ALWAYS** read `protocol/philosophy.md` first to understand the rules.
> 2. **ALWAYS** read `progress/learner.json` to know the learner's current state.
> 3. Then route to the appropriate protocol below.

## Routing

| User Says | Protocol | Action |
|---|---|---|
| `[Tamil Lesson]` | `protocol/session_protocol.md` | Start an interactive teaching session |
| "Generate a podcast/script" | `protocol/roles/director.md` (Checkpoint) → `architect.md` → `producer.md` | Checkpoint + 3-step content pipeline |
| "I listened to episode X" / progress update | `protocol/session_protocol.md` | Update `progress/learner.json` |
| "Show my progress" | Read `progress/learner.json` + `curriculum/levels.json` | Report tier progress, streaks |
| "Sync these updates" / pastes JSON array | `protocol/sync_ingest.md` | Apply mobile updates to learner.json + vocab index |
| *(On mobile, after any progress)* | `protocol/mobile_sync.md` | Emit JSON progress blob for iOS Share |

## System Architecture

```
protocol/           → LLM instructions (you are here)
curriculum/
    ├── index.json      → Manifest (titles, tiers)
    └── levels/         → Individual level JSONs (level_01.json...)
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
| **Rotation** | `protocol/weekly_rotation.md` | 5-day style rotation engine |
| **Director** | `protocol/roles/director.md` | Beat sheet + Word Status Sheet from vocabulary |
| **Architect** | `protocol/roles/architect.md` | Script from beat sheet (gradient-aware) |
| **Producer** | `protocol/roles/producer.md` | TTS-ready script (Tamil Script enforcement) |
| **Mobile Sync** | `protocol/mobile_sync.md` | Phone-side: when/how to emit progress JSON |
| **Sync Ingest** | `protocol/sync_ingest.md` | Desktop-side: apply mobile updates |
| **Curriculum** | `curriculum/levels/level_XX.json` | Source of truth for levels + vocab |
| **Learner** | `progress/learner.json` | Source of truth for learner state |
