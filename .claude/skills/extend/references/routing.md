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
| Scene-spec divergence gate (register / form / dramatic ingredient) | `scripts/suggest_targets.py` | `scene_spec()` at line 221; divergence window = 3 |
| Session law (invariants, shapes, campaign contract, close mechanics) | `protocol/daily_session.md` | Word-budgeted — see `/extend` Gate 4 |
| Pedagogical law and canonical rules (Fresh Execution, recast rules) | `protocol/constitution.md` | Dialect *examples* are Tamil; edit inline for other languages |
| All state writes to `progress/*.json` | `scripts/sync_state.py` | Never hand-edit Python-owned JSON directly |
| Paths, load/save, `local_today`, token→canonical-key `resolve` | `scripts/state_io.py` | Imports nothing from `scripts/`; everything may import it. If this file grows, something that mutates state has leaked in |
| The agent-facing `status` load (banner, soak order, meters, slip block) | `scripts/session_brief.py` | A READ surface — renders state, never mutates it. Sits ABOVE `sync_state` in the import graph |
| Lexicon key script enforcement (`TAMIL_RE`) | `scripts/state_io.py` line 54 | Port surface — see `/extend` Gate 6 |
| Outreach rails (waking hours, daily cap, min gap) | `scripts/morning_knock.py` lines 60–63 | `WAKING_START_HOUR`, `WAKING_END_HOUR`, `MAX_REACHES_PER_DAY`, `MIN_GAP_HOURS` |
| Outreach decision prompt (Anna's fire/silence policy prose) | `scripts/morning_knock.py` | Policy is Anna's; Python holds only the rails |
| Anna's pinned TTS voice for knocks and drills | `scripts/morning_knock.py` line 50 | `ANNA_VOICE`; imported by `render_drill.py` — one change covers both |
| CDN/repo URL for knock audio links (jsDelivr) | `scripts/morning_knock.py` line 51 | `REPO = "arosselet/tamil-tutor"` — update on a fork |
| Knock reply judge prompt (phonetic→script matching, verdict rules) | `scripts/knock_reply.py` | Port surface — Tamil-specific rules embedded in prose |
| Slip contract — how an error is named as a pattern (`SLIP_MANDATE`) | `scripts/knock_reply.py` | Port surface — its worked examples are Tamil morphology |
| The slip ledger: capture, aggregation, retirement, escalation | `scripts/slips.py` | `SLIP_RETIRE_DAYS` (matches `INTERVAL_DAYS["cold"]`), `SLIP_PATTERN_COUNT`; one renderer (`format_slip_block`) feeds all three surfaces |
| How a slip CLOSES — the observation, not a verdict | `scripts/slips.py` | `record_slip_test`/`slip_closes`; closes are dated so a later miss revives them. Never reintroduce a bare-tag close list |
| Drill script prompt (cue/answer format, Tamil script rule) | `scripts/render_drill.py` | Port surface — Tamil-specific rules embedded in prose |
| Episode TTS voice pool (Chirp / WaveNet / Edge pools) | `scripts/render_audio.py` lines 44–74 | Episode pools are local-render today; the cloud calls this module's Google segment renderer for knocks and scheduled voice doses |
| RSS feed structure | `scripts/rebuild_rss.py` | `rss.xml` is the only feed (playlist retired 2026-07-03) |
| Calibration dials (coverage %, new-word counts, pacing) | `progress/profile.md` → Calibration Notes | Change the number, not a prompt or protocol prose |
| Spaced-repetition callback generation | `scripts/generate_callbacks.py` | |
| Scheduled push composition and queue drain | `scripts/push_queue.py` | `drain --dry-run` previews without firing; `memo_script` makes an entry a voice dose rendered at fire time |
| CI workflow — triggers, secrets, step order | `.github/workflows/anna.yml` | ONE workflow for every trigger; job-level `env` so no lane can miss a secret |
| Smoke-test regression cases | `scripts/smoke_test.py` | Add a case the day a bug is fixed — never ad-hoc scripts |
