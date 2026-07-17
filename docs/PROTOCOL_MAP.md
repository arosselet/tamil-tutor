# The Tamil Protocol Map (`@build` reference)

The architecture of the learning system — **for working *on* the machine**, not for running it. Anna and the studio don't load this file; it's the engineer's map.

Companion: **`docs/DECISIONS.md`** — settled decisions and engineering discipline. Read it before proposing any structural change; don't re-litigate what it closes.

This map describes the **Tamil instantiation**. For what generalizes beyond it — the four-layer boundary (pedagogy / machinery / language pack / learner pack), the Python port surface, and day-zero behavior — see `BOOTSTRAP.md` → "What Generalizes".

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

- `payload` — the words chat just strained — or, when a campaign is live, a **seed order**: 2–4 unseen deck items the episode teaches first (captions carry the load; the render's `seen_in` stamp is what opens them to the drilling channels)
- `scene_seed` — one line of the running story

Anna hands **meaning**; the studio derives the rest (register / form / ingredient, callbacks, density) and owns the **craft**.

A second, softer interface exists since 2026-07-17: the **campaign block** (`progress/profile.md` → "The Campaign — This Week") — an Andrew-initiated one-week unit plan in Anna-owned prose. Sessions, the studio, and the knock digest all read it; only a live session writes it.

## Invocation shells (thin, per-agent — all substance lives in `protocol/`)

| Entry | Claude | Gemini |
|---|---|---|
| **Anna** (conversation) | `.claude/skills/anna/SKILL.md` | `.gemini/commands/anna.toml` |
| **Studio** (production) | `.claude/agents/studio.md` (subagent) | `.gemini/commands/studio.toml` |

Anna can commission the studio end-to-end mid-session; `/studio` also runs standalone (e.g. on Gemini for the long mixed-language script writing).

**Default episode dispatch (2026-07-09 — the writer-only split):** `python scripts/run_studio.py` — three sandboxed **print-only** agy/Gemini calls (Director → Architect → Producer; Gemini never writes a file, never sees git); Python persists the three artifacts, lints them deterministically (sidecar schema, Woven-Thanglish density tripwire, fourth wall, deck-payload **verbatim** fidelity), and `render_audio.py` owns render/registration/commit. Non-zero exit ⇒ fall back to the Claude studio subagent.

## State (`progress/` — Python-owned, never hand-edit)

| File | Owner | Holds |
|---|---|---|
| `lexicon.json` | `sync_state.py` | Word brain: recognition + production axes, patterns/engines, deck tags + fire/catch direction, viability floor |
| `learner.json` | `sync_state.py` | Continuity: running story (`last_debrief`), `soak_order`, status (no streak — recency from the session log is the honest signal) |
| `episodes.json` | `sync_state.py` / `render_audio.py` | Episode registry |
| `session_log.json` | `sync_state.py` | Append-only momentum log |
| `feedback_log.json` | `sync_state.py feedback` | The ledger the diagnosis pass reads |
| `knock_log.json` | `morning_knock.py` / `knock_reply.py` | Anna's outreach memory: every wake (fire or silence), replies, verdicts |
| `push_queue.json` | `push_queue.py` | Scheduled pushes, fully composed at add-time; drained every 30 min by CI |
| `profile.md` | Anna (LLM) | Teacher's notebook — assessment, gaps, calibration dials, sprint priorities |

## Python brain (`scripts/`)

`sync_state.py` (owns all state writes; `seed-deck` loads curated decks from `curriculum/`; live burn-rate on the status line) · `suggest_targets.py` (the ticket + scene-spec divergence gate) · `generate_callbacks.py` (spaced repetition) · `render_audio.py` (TTS + register episode + RSS) · `render_drill.py` (spoken production volley from the deck's due list — cue → silence → answer; read-only on the brain) · `show_status.py` (human dashboard) · `morning_knock.py` (agentic outreach: rails gate + Anna's fire/silence policy; digest carries the deck-due menu + binding volley targets; audio memos — incl. eavesdrop tapes in a pinned aunty voice — land on `rss.xml` too) · `knock_reply.py` (judges phone replies, moves the production axis; capped lane + cross-day graduation; walks volley queues deterministically; eavesdrop replies take a separate drift-judge lane that moves the catch/recognition axis only) · `push_queue.py` (durable "ping me at X") · `rebuild_rss.py`.

The LLM is the writer; Python is the brain. Never hand-edit Python-owned JSON.

## Structure freeze — Anna 1.0

This shape is **frozen.** The discipline: **add content freely, change structure rarely.**

- ✅ Content (a word, a scene, an episode, a memory) → always open; *that is the learning.*
- 🛑 Structure (a new file, a schema, a meter, a refactor) → frozen. Route the itch to `docs/feature_inbox.md`; don't act on it mid-session.

Test for any change: *does it add a row of data, or change a schema?* Rows are free; schema changes wait.
