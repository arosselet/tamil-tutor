# The Tamil Protocol Map (`@build` reference)

The architecture of the learning system — **for working *on* the machine**, not for running it. Anna and the studio don't load this file; it's the engineer's map.

Companion: **`docs/DECISIONS.md`** — settled decisions and engineering discipline, one line each. Read it before proposing any structural change; don't re-litigate what it closes.

**This is the only map** (2026-09-10). The `/extend` routing table and the `/orient` subsystem table were second copies of the facts below and both drifted; a concern's owner is found here, and if this file is wrong it is fixed in the same diff as the code.

Open planning: **`docs/comprehension_plan.md`** — target design, worked learning experience,
proposals and implementation receipts. **`docs/ASTRA_REVIEW.md`** holds the evidence and
baseline. Read the plan before proposing curriculum or pacing changes; proposed choices
remain distinct from adopted decisions and shipped capabilities.

This map describes the **Tamil instantiation**. For what generalizes beyond it — the four-layer boundary (pedagogy / machinery / language pack / learner pack), the Python port surface, and day-zero behavior — see `BOOTSTRAP.md` → "What Generalizes".

## The two halves

The system splits cleanly into **conversation** (Anna — always-on, small) and **production** (the studio — isolated, dispatched). They meet at exactly one interface: the **soak-order**.

```
protocol/
├── persona.md          Anna — the one persistent voice (elder brother, he/him)
├── user.md             Who Andrew is to this family — the one home, IN the voice canon
├── toolbelt.md         Anna's reach — SESSION ONLY, never in the voice canon
├── heist.md            The secret and its ops — SESSION ONLY, out of the voice canon (2026-09-20)
├── learner_contract.md Andrew's half: the two anchors, the one habit asked, what he is owed — session only
├── constitution.md     Universal law: philosophy, tactical & canonical rules
├── daily_session.md    The comprehension-led session (opening gift, teaching, optional probes, arc)
├── diagnosis.md        The healing loop: feedback ledger → dial / prune / propose (periodic, evidence-gated)
├── dialect.md          Coimbatore spoken-register rules — top level, NOT studio-only:
│                       every pass that emits speakable Tamil reads it (knock lane, soak,
│                       drill, rotation, both reply judges) via `writer.voice_canon()`;
│                       the studio Producer reads it directly as part of its own canon
├── commissioning.md    Anna's audio authority and what a dose carries
├── audio_channels.md   Which channel carries a dose — capacity routes, curriculum fills
└── studio/             The backstage production crew — runs in an isolated context
    ├── studio.md       Orchestrator + the soak-order contract (the front door)
    ├── director.md     Soak-order + ticket → Master Lesson Plan
    ├── architect.md    Lesson Plan → two-voice script
    ├── producer.md     Dialect pass + integrity + .tags.json sidecar
    └── hosts.md        Voice conventions + production-only rules (fourth wall, script-only).
                        The CAST itself is `content/household.md`, not here (2026-09-19)
```

## The interface: the soak-order

Anna writes it at Close & Log; the studio consumes it. It is the *only* thing that crosses between the two halves (`progress/learner.json` → `soak_order`):

- `payload` — the words chat just strained — or, when an arc is live, a **seed order**: 2–4 unseen items the episode teaches first (captions carry the load; the render stamps `seen_in` but that no longer opens them — since 2026-09-13 an `attended` event does, because a finished render is a fact about the machine, not about Andrew)
- `scene_seed` — **the arc's next beat** (2026-09-19), read from the canon; not an invented one-off situation

Anna hands **meaning**; the studio derives the rest (register / form / ingredient, callbacks, density) and owns the **craft**.

A second, softer interface exists since 2026-07-17, cut back on 2026-07-26 and renamed on 2026-09-19: the **arc block** (`progress/profile.md` → "## The Arc") — the month's situation in the household, in Anna-owned prose. It names no items; the ticket owns those. Sessions, the studio, and the knock digest all read it; only a live session writes it, and exactly one such heading may exist.

## Invocation shells (thin, per-agent — all substance lives in `protocol/`)

| Entry | File | Note |
|---|---|---|
| **Anna** (conversation) | `.claude/skills/anna/SKILL.md` | Plain markdown — any agent reads it directly; `/anna` in Claude Code |
| **Studio** (production) | `.claude/agents/studio.md` | The subagent fallback; `run_studio.py` is the default dispatch |

The Gemini shells were retired 2026-08-20 (`agy` ran on no host; the files had drifted 5–8 weeks). Root `AGENTS.md` is a real file, not a symlink — see its header for why.

Anna can commission the studio end-to-end mid-session; the subagent also runs standalone.

**Default episode dispatch (2026-07-09 — the writer-only split; executor swapped 2026-08-18):** `python scripts/run_studio.py` — three **print-only** writer calls (Director → Architect → Producer) on `writer.MODEL`: `claude -p --allowedTools Read Glob Grep` on the laptop, the OpenRouter API in Actions, and the writer never writes a file or sees git either way. Python persists the three artifacts, lints them deterministically (sidecar schema, Woven-Thanglish density tripwire, fourth wall, payload fidelity — **verbatim for chunks, stem-tolerant for words**), and `render_audio.py` owns render/registration/commit. Non-zero exit ⇒ fall back to the Claude studio subagent.

## State (`progress/` — Python-owned, never hand-edit)

| File | Owner | Holds |
|---|---|---|
| `observations.json` | `lexicon_view.observe` / `expose` | THE LEDGER (2026-09-10): every observation as an event — word, channel, kind (taught / **attended** / exposed / tested / claimed), axis, result, source. Append-only; `seed` and `self-report` are recorded and never vote — and since 2026-09-13 a `taught` on a delivery channel is the same: recorded, pending, and it does not open the teach gate until an `attended` event (or a watched test) shows he was there. `attended` is the one kind that is a fact about Andrew rather than about the machine |
| `lexicon.json` | static half: `sync_state.py` · evidence half: `lexicon_view.rebuild` | Word brain. Gloss, phonetic, type, `register`, `direction`, `pairs_with` are curriculum; recognition, production, reps, exposures, heard_on, last_surfaced, seen_in, taught_on are THE FOLD of the log, one writer, and `lexicon_view.py` reports zero divergent rows or `s100` is red |
| `learner.json` | `sync_state.py` | Continuity: running story (`last_debrief`), `soak_order`, `month` (name + two dates + the finale's mission — membership and completion are BOTH folds), `year` (three dates — the phases are derived, never stored), status (no streak — recency from the session log is the honest signal) |
| `episodes.json` | `sync_state.py` / `render_audio.py` | Episode registry |
| `session_log.json` | `sync_state.py` | Append-only momentum log |
| `feedback_log.json` | `sync_state.py feedback` | The ledger the diagnosis pass reads |
| `knock_log.json` | `morning_knock.py` / `knock_reply.py` | Anna's outreach memory: every wake (fire or silence), replies, verdicts |
| `push_queue.json` | `push_queue.py` | Scheduled pushes, fully composed at add-time; drained at the start of every CI wake-up (hourly — the `*/30` cron was reverted 2026-07-30 on measured data) |
| `profile.md` | Anna (LLM) | Teacher's notebook — assessment, gaps, calibration dials, sprint priorities |

## Python brain (`scripts/`)

**Imports point one way, down the stack** (2026-08-23) — a lower layer never imports a higher one, and a channel never owns an invariant that more than one channel obeys. Bottom to top:

**L-1 `language.py`** — THE LANGUAGE PACK: every value a fork to another language replaces, and nothing else. The two script forms (`TAMIL_RE` for "is there script here", `TAMIL_RUN` for "where are the spans"), `TAMIL_TAIL_RE` (vowel signs + pulli, for stem-tolerant payload matching), `is_tamil`, the two pinned voices, and the repo identity every URL derives from. Imports nothing at all — `state_io` imports IT. **Two guards, two jobs** (2026-09-03): `s70` needles every public value so adding one arms the guard for it (2026-08-28) — that proves a DECLARED value has one home. `s91` proves the other half, which the needle guard structurally cannot: it sweeps every lane for target script on a mechanism line, because a fact the pack has never heard of contributes no needle to look for. It found `render_audio` classifying script with a character comparison at two sites, importing nothing from here at all. Dials are NOT here: a tripwire, a rail and a waking window are facts about Andrew, not about Tamil, and each already has one owner — since 2026-09-04 the rail and the window share theirs, `rails.py`, which is where they always belonged.

**L0.5 `observations.py`** — the log's vocabulary and its appender; nothing else. **L0.7 `lexicon_view.py`** — `derive` (pure fold), `rebuild` (the one writer of evidence fields), `observe` (append then fold), `expose` (the delivery seam every lane calls), `divergence` (the honesty check). `backfill_observations.py` sits above it: reconstruction from history and the 09-10 cutover.
**L0 `state_io.py`** — paths, load/save, `local_today` + `local_date`, token→key `resolve`, the soak payload resolvers, and the read-only predicates `is_unseen` / `soak_pending` / `is_fire`. Imports only the pack; everything else may import it. The clock helper and the fire predicate came home from `morning_knock` on 2026-09-04, along with three duplicate spellings of `KNOCK_LOG_PATH` — the paths this file declares had grown a *second* import authority, with half the lanes asking here and half asking the knock lane.
**L0.6 `household.py`** — the reader and the one appender for `content/household.md`, THE CANON: the place, the recurring cast, each character's pinned TTS voice, the standing facts, this month's arc premise and its beat log. `run_studio` refuses to spend a model pass without it (a free-standing scenario is a household that silently does not exist), copies the voice pins into every script itself — a table a model retypes is a table that drifts, and the ear tracks a speaker before a word — and appends one beat per render. It imports only L0: a canon reader that could see progress would start being chosen by deficit, which is the machine the whole object exists to escape.

**L1.1 `year.py`** — THE PHASE SCHEDULE, the unit above the month (2026-09-19). Three dates in `learner.json` (`opened`, `trip_from`, `trip_to`); seven phases derived from them — excavation, down, across, up, taper, trip, harvest. A phase decides three things and no more: the **lean** (`LEADS` / `register_rank`, which registers lead selection — this retired `suggest_targets`' static `REGISTER_TIERS` / `TIER_NAMES` / `tier_rank`), the **ear ramp** (voices, and whether the situation is given), and the **intake cap** (zero in the taper and the trip, the profile dial everywhere else). It imports `state_io` and nothing else — not the lexicon, not the log, not the month — because a schedule that can read progress is a schedule that has grown a meter, and the Trip Deck is what that looks like. Nothing but the three dates is stored; `s113` asserts by name that no phase, marker, burn rate or progress count is ever persisted. The T-minus prints on `show_status.py` and `sync_state.py year` and deliberately NOT on `compute_status`, which Anna loads.

**L1 selection** — `suggest_targets.py` (the ticket: the lean-ordered focus pool + the scene-spec divergence gate, plus the studio-only blocks — fence, coverage, background, candidates) · `generate_callbacks.py` (spaced repetition) · `slips.py` (the slip ledger: capture, patterns, retirement, closes). `sync_state.py` sits beside them and owns ALL state writes (`seed-deck` loads a curated set from `curriculum/`, registers and all; `unverify` drops to struggled every row rated recognized that nothing ever tested).
**L2 policy** — verdict caps, teach-first, the variety gate, ask cooldowns; these live with the lanes that read them. **`rails.py` is the exception that names the rule** (2026-09-04): the reach budget — the waking window, the daily cap, the min gap, `reaches_today` — is obeyed by *two* channels, the knock and the queue, so it cannot live inside either. A policy one lane reads stays with that lane; a rail more than one channel obeys gets a file. `morning_knock.rails_gate` stays put, because whether to wake **Anna** is the knock lane's own question and nothing else asks it.
**L3 `writer.py`** — model config, `budget()`, `JSON_MODE`, both JSON parsers, the phonetic rewrite, and **the one place that chooses an executor**: `claude -p` where a local agent exists, the paid API everywhere else, decided by asking which binary is on PATH — never by a lane, never by a flag someone has to remember. `mandates.py` holds prompt canon beside it.
**L4 `publish.py`** — the delivery tail: `load_env`, the rebase net with its union and re-render resolvers, `commit_and_push`, `refresh_feed`, `jsdelivr_url`, and `push_to_phone`, the one chokepoint where quiet hours are **enforced** — it reads the window from `rails.py` rather than owning it (2026-09-04; enforcing a rail and owning it are different jobs, and only one of them belongs to the tail). `publish()` assembles a dose's commit in the one correct order — feed after the log, mp3 at the front. `rebuild_rss.py` and `render_audio.py` (TTS + register episode + RSS) are its producers.
**L4.7 `memo.py`** — the voice-memo renderer: a script in, an mp3 out. Above the TTS primitives it composes, below every lane that speaks. It is *not* in `lanes.py` because its three callers — the knock, the queue's drain, both reply lanes — span two of the three families that file is built around.

**L5 the lanes** — `lanes.py` holds what a FAMILY shares (`deliver_rendered`: exposure → soak stamp → commit → notify, for the write→render→publish family) and nothing a lane declares for itself; `commit` and `notify` are passed IN, because a name looked up inside `lanes` would not see a lane's stub. `morning_knock.py` (agentic outreach: rails gate + Anna's fire/silence policy; digest carries the due menu + binding volley targets; audio memos — incl. eavesdrop tapes in a pinned aunty voice — land on `rss.xml` too) · `knock_reply.py` (judges phone replies, moves the production axis; capped lane + cross-day graduation; walks volley queues deterministically; eavesdrop replies take a separate drift-judge lane that moves the catch/recognition axis only) · `push_queue.py` (durable "ping me at X" — composed at add time, rendered at fire time, zero LLM calls when it fires) · `render_payoff.py` (a closed eavesdrop tape re-cut with a meaning after every line; the payoff REPLACES the raw tape in the feed, keyed on the file's existence — see `rebuild_rss.superseded`) · `render_soak.py` · `render_drill.py` (spoken production volley from the pool's due menu — cue → silence → answer; read-only on the brain) · `render_rotation.py` · `run_studio.py`.

**No lane is a foundation.** `morning_knock.py` had become one — four peers imported seven names from it, none of them knock-shaped — and `s92` now asserts it has no importers at all. `s75` could not catch that: three of the four borrowers sit *above* the knock lane, so importing down from them was legal and silent. The law it broke was the other one — *a channel never owns an invariant that more than one channel obeys* — and until 2026-09-04 nothing had teeth on it. `push_queue`, `reply_common` and `memo` are still imported by design; they are a store's public API and two files that exist to be shared.

Read surfaces above the brain: `session_brief.py` (the agent-facing `status` load) · `show_status.py` (human dashboard).

**Beside the stack — each has one job (mapped 2026-09-25, when `s125` began failing on any script the map omits):** `month.py` (the arc's month: membership and completion are folds, nothing stored beyond its dates) · `dose_evidence.py` (was the dose HEARD — the evidence half of the slip ledger's escalation law, joined by lane) · `knock_message.py` (the MESSAGE lane: Andrew talking TO Anna, nothing graded) · `reply_common.py` (what every inbound lane shares — answering aloud, the audio-request backstop, the meta-direction writer; split from `knock_reply.py`) · `audio_titles.py` (what a soak, drill or rotation is CALLED; one writer, `lanes.deliver_rendered`) · `render_chat.py` (`progress/chat.md`, derived from `knock_log.json`; never hand-edit) · `render_demo.py` (showcase scripts to MP3 with no lifecycle hooks — touches no state, reaches no feed) · `smoke_test.py` (the dispatcher; the cases live in `scripts/smoke/`). · `commissions.py` (the commission router: claims one due commission per tick from `progress/commissions/pending/`, validates deterministically, runs the lane script as a subprocess — write→render→publish→deliver inside the lane; pending→claimed→done/failed).

**Short interactive listening (2026-09-21):** `lesson_audio.py` accepts an authored
script and uses `memo.render_memo`; it renders locally by default, optionally publishes
only the named clip, and writes no learner state. `receptive_check.py` owns the
recognition command extracted from `sync_state.py`: the CLI keeps its existing
`check` entry point and adds `--session --source --note` for ordinary lesson
evidence without resetting the monthly cue. These reuse the existing event schema
and speech backend; playback and saving are separate operations.

The LLM is the writer; Python is the brain. Never hand-edit Python-owned JSON.

## Structure

Not frozen (the "Anna 1.0" freeze retired 2026-09-10 — stated in three files, lifted in one, read by nobody). The structure control is the ratchet: every prose surface and every script carries a budget in `scripts/smoke/ratchets.py`, a new file is budgeted in the diff that creates it, and `/extend` Gate 4 makes every addition name what it replaces. Rows of data are always free; a schema field is a budgeted addition like any other.
