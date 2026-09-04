# Surgical-Edit Routing Table

Companion to `/extend` Gate 5. Find the concern you are touching; edit **only that file**.
Every path below has been verified against the repo. If a file is missing, stop and
report — do not create a substitute.

| Concern | File | Notes |
|---|---|---|
| Anna's persona voice, heist framing, "What Anna Never Does" | `protocol/persona.md` | Ships to six voice lanes via `writer.voice_canon()` — write for a generator that can act on nothing but voice, register and standing fact |
| Anna's tools and what he can reach for | `protocol/toolbelt.md` | **Session-only**, split from `persona.md` 2026-09-03. Never add it to `VOICE_CANON_FILES`: no voice lane can invoke a tool. A tool added here must also be reachable from `.claude/skills/anna/SKILL.md` step 1 (`s90`) |
| Coimbatore spoken-register rules (verb collapse, fusion, slang) | `protocol/dialect.md` | **Any lane that sends Tamil to a VOICE reads it via `writer.voice_canon()`** — knock memos, eavesdrop tapes, fielding questions, soak/drill/rotation sheets, voice replies. The studio Producer reads it as its own canon. Never put dialect rules in `architect.md`, and never hand a new voice lane `persona.md` alone: that is how this file reached exactly one reader until 2026-09-02 (`s89`) |
| Podcast cast names and regional voice identity | `protocol/studio/hosts.md` | Script-only rules live here (fourth wall, no ad-libs) |
| Word selection ticket (floor-gap targets, engines, new candidates) | `scripts/suggest_targets.py` | |
| Scene-spec divergence gate (register / form / dramatic ingredient) | `scripts/suggest_targets.py` | `scene_spec()`; divergence window = 3 |
| Session law (invariants, shapes, campaign contract, close mechanics) | `protocol/daily_session.md` | Word-budgeted — see `/extend` Gate 4 |
| Pedagogical law and canonical rules (Fresh Execution, recast rules) | `protocol/constitution.md` | Dialect *examples* are Tamil; edit inline for other languages |
| All state writes to `progress/*.json` | `scripts/sync_state.py` | Never hand-edit Python-owned JSON directly |
| Paths, load/save, `local_today`, token→canonical-key `resolve` | `scripts/state_io.py` | Imports nothing from `scripts/`; everything may import it. If this file grows, something that mutates state has leaked in |
| The agent-facing `status` load (banner, soak order, meters, slip block) | `scripts/session_brief.py` | A READ surface — renders state, never mutates it. Sits ABOVE `sync_state` in the import graph |
| Lexicon key script enforcement; stem-tolerant payload matching | `scripts/language.py` → `TAMIL_RE`, `TAMIL_RUN`, `TAMIL_TAIL_RE`, `strip_pulli` | THE LANGUAGE PACK — every value a port replaces, guarded per-value by `s70`; see `/extend` Gate 6 |
| Anything else a port replaces — kinship nouns, TTS locale, feed name and pitch | `scripts/language.py` → `REFERENT_NOUNS`, `voice_locale`, `FEED_TITLE`, `FEED_SUMMARY`, `CAPTION_COLUMNS` | If you are about to write target script in a lane, it belongs here instead and `s91` will say so. The TTS locale is DERIVED from the voice, never declared — declaring it would needle a prefix shared by all 35 voice IDs |
| Outreach rails (daily cap, min gap) | `scripts/morning_knock.py` → `MAX_REACHES_PER_DAY`, `MIN_GAP_HOURS` | The knock's own rails |
| Quiet hours (the waking window) | `scripts/publish.py` → `WAKING_START_HOUR`, `WAKING_END_HOUR` | Moved down 2026-08-23: it is EVERY lane's rule, enforced once at `push_to_phone`, never per-lane |
| Outreach decision prompt (Anna's fire/silence policy prose) | `scripts/morning_knock.py` | Policy is Anna's; Python holds only the rails |
| Anna's pinned TTS voice, and the overheard aunty's | `scripts/language.py` → `ANNA_VOICE`, `EAVESDROP_VOICE` | Moved 2026-08-28 from `render_audio` to the pack; six lanes import them straight from L-1. The episode POOLS stay in `render_audio` — one reader, one file |
| Repo identity — CDN (jsDelivr), raw feed URLs, site link | `scripts/language.py` → `REPO` | One fact, three spellings until 2026-08-28. `publish.jsdelivr_url` and `rebuild_rss`'s `BASE_URL`/`SITE_URL` all derive from it |
| Knock reply judge prompt (phonetic→script matching, verdict rules) | `scripts/knock_reply.py` | Port surface — Tamil-specific rules embedded in prose |
| Slip contract — how an error is named as a pattern (`SLIP_MANDATE`) | `scripts/mandates.py` | Port surface — its worked examples are Tamil morphology. It left `knock_reply.py` on 2026-08-24 with that file's five other mandates; this row said otherwise until 2026-09-04 (`s93`) |
| The slip ledger: capture, aggregation, retirement, escalation | `scripts/slips.py` | `SLIP_RETIRE_DAYS` (matches `INTERVAL_DAYS["cold"]`), `SLIP_PATTERN_COUNT`; one renderer (`format_slip_block`) feeds all three surfaces |
| How a slip CLOSES — the observation, not a verdict | `scripts/slips.py` | `record_slip_test`/`slip_closes`; closes are dated so a later miss revives them. Never reintroduce a bare-tag close list |
| Drill script prompt (cue/answer format, Tamil script rule) | `scripts/mandates.py` → `DRILL_MANDATE`, `LINT_MANDATE` | Port surface — Tamil-specific rules embedded in prose. `render_drill.py` imports them; its own `COMMISSION_BRIEF` is prompt prose but language-agnostic, so it is NOT port surface |
| Episode TTS voice pool (Chirp / WaveNet / Edge pools) | `scripts/render_audio.py` | Episode pools are local-render today; the cloud calls this module's Google segment renderer for knocks and scheduled voice doses |
| RSS feed structure | `scripts/rebuild_rss.py` | `rss.xml` is the only feed (playlist retired 2026-07-03) |
| Calibration dials (coverage %, new-word counts, pacing) | `progress/profile.md` → Calibration Notes | Change the number, not a prompt or protocol prose |
| Spaced-repetition callback generation | `scripts/generate_callbacks.py` | |
| Scheduled push composition and queue drain | `scripts/push_queue.py` | `drain --dry-run` previews without firing; `memo_script` makes an entry a voice dose rendered at fire time |
| CI workflow — triggers, secrets, step order | `.github/workflows/anna.yml` | ONE workflow for every trigger; job-level `env` so no lane can miss a secret |
| Smoke-test regression cases | `scripts/smoke/` — the layer file that owns the lane (`knock.py`, `state.py`, `publish.py`, `compose.py`, `render.py`, `queue.py`, `ratchets.py`) | Add a case the day a bug is fixed — never ad-hoc scripts. `scripts/smoke_test.py` gains one `run(...)` line; the harness is `smoke/_fixtures.py` |
