# The Tamil Protocol Map (`@build` reference)

The architecture of the learning system — **for working *on* the machine**, not for running it. Anna and the studio don't load this file; it's the engineer's map.

## The two halves

The system splits cleanly into **conversation** (Anna — always-on, small) and **production** (the studio — isolated, dispatched). They meet at exactly one interface: the **soak-order**.

```
protocol/
├── persona.md          Anna — the one persistent voice (elder brother, he/him)
├── constitution.md     Universal law: philosophy, tactical & canonical rules
├── daily_session.md    The ~10–15 min forced-output loop (the choreography)
├── session_tools.md    Anna's live formats (drill, roleplay, recall, reading, zinger)
└── studio/             The backstage production crew — runs in an isolated context
    ├── studio.md       Orchestrator + the soak-order contract (the front door)
    ├── director.md     Soak-order + ticket → Master Lesson Plan
    ├── architect.md    Lesson Plan → two-voice script
    ├── producer.md     Dialect pass + integrity + .tags.json sidecar
    ├── hosts.md        Cast bible + production-only rules (fourth wall, script-only)
    └── dialect.md      Coimbatore spoken-register rules
```

## The interface: the soak-order

Anna writes it at Close & Log; the studio consumes it. It is the *only* thing that crosses between the two halves (`progress/learner.json` → `soak_order`):

- `payload` — the words chat just strained
- `scene_seed` — one line of the running story

Anna hands **meaning**; the studio derives the rest (register / form / ingredient, callbacks, density) and owns the **craft**.

## Invocation shells (thin, per-agent — all substance lives in `protocol/`)

| Entry | Claude | Gemini |
|---|---|---|
| **Anna** (conversation) | `.claude/skills/anna/SKILL.md` | `.gemini/commands/anna.toml` |
| **Studio** (production) | `.claude/agents/studio.md` (subagent) | `.gemini/commands/studio.toml` |

Anna can commission the studio end-to-end mid-session; `/studio` also runs standalone (e.g. on Gemini for the long mixed-language script writing).

## State (`progress/` — Python-owned, never hand-edit)

| File | Owner | Holds |
|---|---|---|
| `lexicon.json` | `sync_state.py` | Word brain: recognition + production axes, patterns/engines, viability floor |
| `learner.json` | `sync_state.py` | Continuity: streak, running story (`last_debrief`), `soak_order`, status |
| `episodes.json` | `sync_state.py` / `render_audio.py` | Episode registry |
| `session_log.json` | `sync_state.py` | Append-only momentum log |
| `profile.md` | Anna (LLM) | Teacher's notebook — assessment, gaps, terrain |

## Python brain (`scripts/`)

`sync_state.py` (owns all state writes) · `suggest_targets.py` (the ticket + scene-spec divergence gate) · `generate_callbacks.py` (spaced repetition) · `render_audio.py` (TTS + register episode + RSS) · `show_status.py` · `build_playlist.py` · `rebuild_rss.py` / `rebuild_playlist_rss.py`.

The LLM is the writer; Python is the brain. Never hand-edit Python-owned JSON.

## Structure freeze — Anna 1.0

This shape is **frozen.** The discipline: **add content freely, change structure rarely.**

- ✅ Content (a word, a scene, an episode, a memory) → always open; *that is the learning.*
- 🛑 Structure (a new file, a schema, a meter, a refactor) → frozen. Route the itch to `docs/feature_inbox.md`; don't act on it mid-session.

Test for any change: *does it add a row of data, or change a schema?* Rows are free; schema changes wait.
