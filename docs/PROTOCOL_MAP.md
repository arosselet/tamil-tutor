# The Tamil Protocol Map (`@build` reference)

The architecture of the learning system — **for working *on* the machine**, not for running it. Anna and the studio don't load this file; it's the engineer's map.

Companion: **`docs/DECISIONS.md`** — settled decisions and engineering discipline. Read it before proposing any structural change; don't re-litigate what it closes.

Open planning: **`docs/comprehension_plan.md`** — the one-year comprehension goal, its measured
baseline, and the questions still unanswered. Nothing in it is settled; read it before
proposing curriculum or pacing changes.

This map describes the **Tamil instantiation**. For what generalizes beyond it — the four-layer boundary (pedagogy / machinery / language pack / learner pack), the Python port surface, and day-zero behavior — see `BOOTSTRAP.md` → "What Generalizes".

## The two halves

The system splits cleanly into **conversation** (Anna — always-on, small) and **production** (the studio — isolated, dispatched). They meet at exactly one interface: the **soak-order**.

```
protocol/
├── persona.md          Anna — the one persistent voice (elder brother, he/him)
├── constitution.md     Universal law: philosophy, tactical & canonical rules
├── daily_session.md    The ~8–15 min forced-output loop (invariants + shapes + campaign)
├── diagnosis.md        The healing loop: feedback ledger → dial / prune / propose (periodic, evidence-gated)
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

- `payload` — the words chat just strained — or, when a campaign is live, a **seed order**: 2–4 unseen items the episode teaches first (captions carry the load; the render's `seen_in` stamp is what opens them to the drilling channels)
- `scene_seed` — one line of the running story

Anna hands **meaning**; the studio derives the rest (register / form / ingredient, callbacks, density) and owns the **craft**.

A second, softer interface exists since 2026-07-17, cut back to its through-line on 2026-07-26: the **campaign block** (`progress/profile.md` → "The Campaign — This Week") — the week's name and what its days add up to, in Anna-owned prose. It names no items; the ticket owns those. Sessions, the studio, and the knock digest all read it; only a live session writes it, and exactly one such heading may exist.

## Invocation shells (thin, per-agent — all substance lives in `protocol/`)

| Entry | File | Note |
|---|---|---|
| **Anna** (conversation) | `.claude/skills/anna/SKILL.md` | Plain markdown — any agent reads it directly; `/anna` in Claude Code |
| **Studio** (production) | `.claude/agents/studio.md` | The subagent fallback; `run_studio.py` is the default dispatch |

The Gemini shells were retired 2026-08-20 (`agy` ran on no host; the files had drifted 5–8 weeks). Root `AGENTS.md` is a real file, not a symlink — see its header for why.

Anna can commission the studio end-to-end mid-session; the subagent also runs standalone.

**Default episode dispatch (2026-07-09 — the writer-only split; executor swapped 2026-08-18):** `python scripts/run_studio.py` — three **print-only** writer calls (Director → Architect → Producer) on `morning_knock.MODEL`: `claude -p --allowedTools Read Glob Grep` on the laptop, the OpenRouter API in Actions, and the writer never writes a file or sees git either way. Python persists the three artifacts, lints them deterministically (sidecar schema, Woven-Thanglish density tripwire, fourth wall, payload fidelity — **verbatim for chunks, stem-tolerant for words**), and `render_audio.py` owns render/registration/commit. Non-zero exit ⇒ fall back to the Claude studio subagent.

## State (`progress/` — Python-owned, never hand-edit)

| File | Owner | Holds |
|---|---|---|
| `lexicon.json` | `sync_state.py` | Word brain: recognition + production axes, patterns/engines, `register` (the survival/delight/dessert ordering) + fire/catch direction, viability floor |
| `learner.json` | `sync_state.py` | Continuity: running story (`last_debrief`), `soak_order`, status (no streak — recency from the session log is the honest signal) |
| `episodes.json` | `sync_state.py` / `render_audio.py` | Episode registry |
| `session_log.json` | `sync_state.py` | Append-only momentum log |
| `feedback_log.json` | `sync_state.py feedback` | The ledger the diagnosis pass reads |
| `knock_log.json` | `morning_knock.py` / `knock_reply.py` | Anna's outreach memory: every wake (fire or silence), replies, verdicts |
| `push_queue.json` | `push_queue.py` | Scheduled pushes, fully composed at add-time; drained at the start of every CI wake-up (hourly — the `*/30` cron was reverted 2026-07-30 on measured data) |
| `profile.md` | Anna (LLM) | Teacher's notebook — assessment, gaps, calibration dials, sprint priorities |

## Python brain (`scripts/`)

**Imports point one way, down the stack** (2026-08-23) — a lower layer never imports a higher one, and a channel never owns an invariant that more than one channel obeys. Bottom to top:

**L0 `state_io.py`** — paths, load/save, `local_today`, the canonical script regex (the PORT SURFACE), token→key `resolve`, the soak payload resolvers, and the read-only predicates `is_unseen` / `soak_pending`. Imports nothing from `scripts/`; everything else may import it.
**L1 selection** — `suggest_targets.py` (the ticket: the tier-ordered focus pool + the scene-spec divergence gate, plus the studio-only blocks — fence, coverage, background, candidates) · `generate_callbacks.py` (spaced repetition) · `slips.py` (the slip ledger: capture, patterns, retirement, closes). `sync_state.py` sits beside them and owns ALL state writes (`seed-deck` loads a curated set from `curriculum/`, registers and all; `unverify` drops to struggled every row rated recognized that nothing ever tested).
**L2 policy** — rails, verdict caps, teach-first, the variety gate, ask cooldowns; these live with the lanes that read them.
**L3 `writer.py`** — model config, `budget()`, `JSON_MODE`, both JSON parsers, the phonetic rewrite, and **the one place that chooses an executor**: `claude -p` where a local agent exists, the paid API everywhere else, decided by asking which binary is on PATH — never by a lane, never by a flag someone has to remember. `mandates.py` holds prompt canon beside it.
**L4 `publish.py`** — the delivery tail: `load_env`, the rebase net with its union and re-render resolvers, `commit_and_push`, `refresh_feed`, `jsdelivr_url`, the waking window, and `push_to_phone`, the one chokepoint where quiet hours are enforced. `publish()` assembles a dose's commit in the one correct order — feed after the log, mp3 at the front. `rebuild_rss.py` and `render_audio.py` (TTS + register episode + RSS) are its producers.
**L5 the lanes** — `morning_knock.py` (agentic outreach: rails gate + Anna's fire/silence policy; digest carries the due menu + binding volley targets; audio memos — incl. eavesdrop tapes in a pinned aunty voice — land on `rss.xml` too) · `knock_reply.py` (judges phone replies, moves the production axis; capped lane + cross-day graduation; walks volley queues deterministically; eavesdrop replies take a separate drift-judge lane that moves the catch/recognition axis only) · `push_queue.py` (durable "ping me at X" — composed at add time, rendered at fire time, zero LLM calls when it fires) · `render_soak.py` · `render_drill.py` (spoken production volley from the pool's due menu — cue → silence → answer; read-only on the brain) · `render_longhaul.py` · `run_studio.py`.

Read surfaces above the brain: `session_brief.py` (the agent-facing `status` load) · `show_status.py` (human dashboard) · `studio_watchdog.py`.

The LLM is the writer; Python is the brain. Never hand-edit Python-owned JSON.

## Structure freeze — Anna 1.0

This shape is **frozen.** The discipline: **add content freely, change structure rarely.**

- ✅ Content (a word, a scene, an episode, a memory) → always open; *that is the learning.*
- 🛑 Structure (a new file, a schema, a meter, a refactor) → frozen. Route the itch to `docs/feature_inbox.md`; don't act on it mid-session.

Test for any change: *does it add a row of data, or change a schema?* Rows are free; schema changes wait.
