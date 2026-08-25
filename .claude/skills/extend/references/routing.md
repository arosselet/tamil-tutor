# Surgical-Edit Routing Table

Companion to `/extend` Gate 5. Find the concern you are touching; edit **only that file**.
Every path below has been verified against the repo. If a file is missing, stop and
report — do not create a substitute.

| Concern | File | Notes |
|---|---|---|
| Anna's persona voice, heist framing, "What Anna Never Does" | `protocol/persona.md` | |
| Coimbatore spoken-register rules (verb collapse, fusion, slang) | `protocol/studio/dialect.md` | Producer applies; never put dialect rules in `architect.md` |
| Podcast cast names and regional voice identity | `protocol/studio/hosts.md` | Script-only rules live here (fourth wall, no ad-libs) |
| Word selection ticket (floor-gap targets, engines, new candidates) | `scripts/suggest_targets.py` | |
| Scene-spec divergence gate (register / form / dramatic ingredient) | `scripts/suggest_targets.py` | `scene_spec()`; divergence window = 3 |
| Session law (invariants, shapes, campaign contract, close mechanics) | `protocol/daily_session.md` | Word-budgeted — see `/extend` Gate 4 |
| Pedagogical law and canonical rules (Fresh Execution, recast rules) | `protocol/constitution.md` | Dialect *examples* are Tamil; edit inline for other languages |
| All state writes to `progress/*.json` | `scripts/sync_state.py` | Never hand-edit Python-owned JSON directly |
| Paths, load/save, `local_today`, token→canonical-key `resolve` | `scripts/state_io.py` | Imports nothing from `scripts/`; everything may import it. If this file grows, something that mutates state has leaked in |
| The agent-facing `status` load (banner, soak order, meters, slip block) | `scripts/session_brief.py` | A READ surface — renders state, never mutates it. Sits ABOVE `sync_state` in the import graph |
| Lexicon key script enforcement | `scripts/state_io.py` → `TAMIL_RE`, `TAMIL_RUN` | PORT SURFACE — the ONE declaration of the script range, guarded by `s70`; see `/extend` Gate 6 |
| Outreach rails (daily cap, min gap) | `scripts/morning_knock.py` → `MAX_REACHES_PER_DAY`, `MIN_GAP_HOURS` | The knock's own rails |
| Quiet hours (the waking window) | `scripts/publish.py` → `WAKING_START_HOUR`, `WAKING_END_HOUR` | Moved down 2026-08-23: it is EVERY lane's rule, enforced once at `push_to_phone`, never per-lane |
| Outreach decision prompt (Anna's fire/silence policy prose) | `scripts/morning_knock.py` | Policy is Anna's; Python holds only the rails |
| Anna's pinned TTS voice, and the overheard aunty's | `scripts/render_audio.py` → `ANNA_VOICE`, `EAVESDROP_VOICE` | Moved 2026-08-23 to the module that owns TTS; five lanes import them — one change covers all |
| CDN/repo URL for audio links (jsDelivr) | `scripts/publish.py` → `REPO` | `"arosselet/tamil-tutor"` — update on a fork |
| Knock reply judge prompt (phonetic→script matching, verdict rules) | `scripts/knock_reply.py` | Port surface — Tamil-specific rules embedded in prose |
| Slip contract — how an error is named as a pattern (`SLIP_MANDATE`) | `scripts/knock_reply.py` | Port surface — its worked examples are Tamil morphology |
| The slip ledger: capture, aggregation, retirement, escalation | `scripts/slips.py` | `SLIP_RETIRE_DAYS` (matches `INTERVAL_DAYS["cold"]`), `SLIP_PATTERN_COUNT`; one renderer (`format_slip_block`) feeds all three surfaces |
| How a slip CLOSES — the observation, not a verdict | `scripts/slips.py` | `record_slip_test`/`slip_closes`; closes are dated so a later miss revives them. Never reintroduce a bare-tag close list |
| Drill script prompt (cue/answer format, Tamil script rule) | `scripts/render_drill.py` | Port surface — Tamil-specific rules embedded in prose |
| Episode TTS voice pool (Chirp / WaveNet / Edge pools) | `scripts/render_audio.py` | Episode pools are local-render today; the cloud calls this module's Google segment renderer for knocks and scheduled voice doses |
| RSS feed structure | `scripts/rebuild_rss.py` | `rss.xml` is the only feed (playlist retired 2026-07-03) |
| Calibration dials (coverage %, new-word counts, pacing) | `progress/profile.md` → Calibration Notes | Change the number, not a prompt or protocol prose |
| Spaced-repetition callback generation | `scripts/generate_callbacks.py` | |
| Scheduled push composition and queue drain | `scripts/push_queue.py` | `drain --dry-run` previews without firing; `memo_script` makes an entry a voice dose rendered at fire time |
| CI workflow — triggers, secrets, step order | `.github/workflows/anna.yml` | ONE workflow for every trigger; job-level `env` so no lane can miss a secret |
| Smoke-test regression cases | `scripts/smoke/` — the layer file that owns the lane (`knock.py`, `state.py`, `publish.py`, `compose.py`, `render.py`, `queue.py`, `ratchets.py`) | Add a case the day a bug is fixed — never ad-hoc scripts. `scripts/smoke_test.py` gains one `run(...)` line; the harness is `smoke/_fixtures.py` |
