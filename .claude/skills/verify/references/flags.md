# Command Safety & Flag Semantics — Full Reference

The single owner of "what does this command touch" (2026-07-18 consolidation —
`/validate` §3 and `/verify` §4 point here instead of restating). All claims
verified in source. Line numbers are stable as of the commit this skill was
written against.

---

## Command inventory — safe vs mutating

| Script | Subcommand / invocation | Safe / Mutating | What it changes |
|---|---|---|---|
| `smoke_test.py` | (no args) | **SAFE** | Sandbox only — nothing in the real repo |
| `sync_state.py` | `status` | **SAFE** | Nothing |
| `sync_state.py` | `feedback` (no note arg) | **SAFE** | Nothing |
| `show_status.py` | (no args) | **SAFE** | Nothing |
| `suggest_targets.py` | (no args) | **SAFE** | Nothing |
| `generate_callbacks.py` | (no args) | **SAFE** | Nothing |
| `push_queue.py` | `list` | **SAFE** | Nothing |
| `studio_watchdog.py` | (no args, nothing pending) | **SAFE** | Nothing — pure reads until a pending state is found |
| `sync_state.py` | `update [flags]` | **MUTATING** | `lexicon.json`, `learner.json`, `episodes.json` (if `--listened`), `session_log.json` |
| `sync_state.py` | `add-word <key> --gloss …` | **MUTATING** | `lexicon.json` |
| `sync_state.py` | `add-pattern <key> --gloss …` | **MUTATING** | `lexicon.json` |
| `sync_state.py` | `seed-deck <file> [--deck <name>]` | **MUTATING** | `lexicon.json` |
| `sync_state.py` | `feedback "<note>"` | **MUTATING** | `feedback_log.json` |
| `sync_state.py` | `knock-response ack\|listened` | **MUTATING** | `knock_log.json`; if `listened`: also `episodes.json`, `lexicon.json`, `learner.json` |
| `render_chat.py` | (no args) | **MUTATING** | `progress/chat.md` (derived — rebuilds from `knock_log.json`) |
| `rebuild_rss.py` | (no args) | **MUTATING** | `rss.xml` (reads `published_audio/*.mp3` + `content/scripts/*.md`) |
| `studio_watchdog.py` | (no args, something pending) | **MUTATING** | Runs the existing dispatch: `render_audio.py` or `run_studio.py` — see those rows |
| `run_studio.py` | (no args) | **MUTATING** | Episode artifacts in `content/`, then everything `render_audio.py` touches |
| `morning_knock.py` | `--dry-run` | **MUTATING (audio path)** | No log/commit/push — but if Anna picks the audio modality, a real MP3 is written to `published_audio/knocks/` *before* the dry-run gate, and the LLM call fires (details below) |
| `morning_knock.py` | (no args) | **MUTATING** | `knock_log.json`, `progress/chat.md`; audio: `published_audio/knocks/` + `rss.xml` (all audio → feed); commits + git push |
| `morning_knock.py` | `--force` | **MUTATING** | Same as above, skipping the rails gate |
| `knock_reply.py` | `--dry-run "<text>"` | **SAFE** | Nothing written (judge + print only — the LLM judge call still fires) |
| `knock_reply.py` | `"<text>"` | **MUTATING** | `lexicon.json`, `knock_log.json`, `feedback_log.json` (if meta_note); commits + git push |
| `push_queue.py` | `add --body … [flags]` | **MUTATING** | `push_queue.json`; commits unless `--no-commit` |
| `push_queue.py` | `drain [--dry-run] [--no-commit]` | **MUTATING** (default); `--dry-run` skips firing/commit | `push_queue.json`, `knock_log.json`; may push audio; commits + git push unless `--no-commit` |
| `push_queue.py` | `cancel <id> [--no-commit]` | **MUTATING** | `push_queue.json`; commits unless `--no-commit` |
| `render_drill.py` | `--dry-run` | **SAFE** | Prints the JSON cue sheet to stdout (the LLM sheet call fires) — no TTS, no file writes |
| `render_drill.py` | `--no-publish` | **MUTATING** | Renders to `published_audio/` only — skips RSS/commit/push/notify |
| `render_drill.py` | (no args) | **MUTATING** | `published_audio/`, `rss.xml`; commits + git push; phone push |
| `render_audio.py` | `<script> <output>` | **MUTATING** | `audio/`, `published_audio/`, `progress/episodes.json`, `progress/lexicon.json`, `rss.xml`; commits + git push |

> `progress/` holds real, irreplaceable learner state. Never run a mutating command against live `progress/` unless you mean it. The smoke test's sandbox pattern is the safe harness — extend it, don't bypass it.
>
> Commands marked "LLM … fires" need `OPENROUTER_API_KEY` — locally it's read from the repo's gitignored `.env` (`morning_knock.py` `load_env()`); in CI it's an Actions secret. A dry-run without the key fails at the LLM call, not silently.

---

## `morning_knock.py`

Source: `scripts/morning_knock.py` — `main()` at line 541.

| Flag | LLM fires? | TTS fires? | Files written? | Commit/push? | Phone push? |
|---|---|---|---|---|---|
| *(bare)* | YES | YES if Anna picks audio | `knock_log.json`, MP3 (audio), `rss.xml` (audio — via `refresh_feed()`, failure-tolerant), `chat.md` | YES | YES |
| `--dry-run` | **YES** | **YES if audio** | MP3 only (audio modality; written before the dry-run gate at line 594) | NO | NO |
| `--force` | YES | YES if audio | same as bare | YES | YES |

`--dry-run` detail: `rails_gate()` runs (no LLM), `build_digest()` runs (calls `sync_state.py status` as a subprocess — read-only), `decide(digest)` runs (LLM). For silence: the gate fires early (line 570), no writes. For fire: TTS renders if audio (line 587 calls `render_memo()`), then the dry-run gate returns before `log_decision()`, `refresh_feed()` (no rss.xml write on dry-run), `push_to_phone()`, or `commit_and_push()`.

`--force` detail: skips the rails gate's waking-hours/daily-cap/min-gap/next_check checks (line 115: `if force: return True, "forced"`). No other change — everything else runs identically to the bare invocation.

---

## `knock_reply.py`

Source: `scripts/knock_reply.py` — `main()` at line 285.

| Flag | LLM fires? | Files written? | Commit/push? | Phone push? |
|---|---|---|---|---|
| *(bare)* | YES | `lexicon.json`, `knock_log.json`, `feedback_log.json` (if `meta_note` present) | YES | YES |
| `--dry-run` | **YES** | NO | NO | NO |

`--dry-run` detail: `judge()` is called at line 318 (LLM fires). The gate at line 330 returns before `apply_verdict()` (line 336), before any `save_json()` calls, and before `commit_and_push()` (line 373) and `push_to_phone()` (line 381).

---

## `push_queue.py`

Source: `scripts/push_queue.py` — `cmd_drain()` at line 140, `cmd_add()` at line 105, `cmd_cancel()` at line 128.

### drain subcommand

| Flag | Files written? | Commit/push? | Phone push? |
|---|---|---|---|
| *(bare)* | `knock_log.json`, `push_queue.json` | YES | YES |
| `--dry-run` | NO | NO | NO |
| `--no-commit` | YES (both files) | NO | YES |

`--dry-run` detail: inside the fired loop, `if args.dry_run: continue` (line 188–189) skips `push_to_phone()`. After the loop, `if args.dry_run: print("..."); return` (lines 205–207) returns before writing `knock_log.json`, `push_queue.json`, or calling `commit_and_push()`.

`--no-commit` detail: `push_to_phone()` fires normally; `knock_log.json` and `push_queue.json` are written; `commit_and_push()` is behind `if not args.no_commit:` (line 211).

### add subcommand

`--no-commit`: `enqueue()` is called unconditionally (writes `push_queue.json`); `commit_and_push()` is behind `if not args.no_commit:` (line 110).

### cancel subcommand

`--no-commit`: `save_queue(kept)` is called unconditionally (writes `push_queue.json`); `commit_and_push()` is behind `if not args.no_commit:` (line 136).

---

## `render_drill.py`

Source: `scripts/render_drill.py` — `main()` at line 154.

| Flag | LLM fires? | TTS fires? | Files written? | Commit/push? | Phone push? |
|---|---|---|---|---|---|
| *(bare)* | YES | YES | `published_audio/drill_*.mp3` | YES (+ `rss.xml`) | YES |
| `--dry-run` | **YES** | NO | NO | NO | NO |
| `--no-publish` | YES | **YES** | `published_audio/drill_*.mp3` | NO | NO |

`--dry-run` detail: `write_sheet(pending)` is called at line 172 (LLM fires). The gate at lines 175–177 prints the JSON sheet and returns before `asyncio.run(render(...))`, any file writes, `rebuild_rss.py`, `commit_and_push()`, or `push_to_phone()`.

`--no-publish` detail: `write_sheet()` runs (LLM), `asyncio.run(render(sheet, mp3, args.gap))` runs (TTS, MP3 written). The gate at lines 184–185 returns before `rebuild_rss.py`, `commit_and_push()`, and `push_to_phone()`.

---

## `render_audio.py`

Source: `scripts/render_audio.py` — `main()` at line 393.

**No dry-run or no-publish flag.** Argparse (lines 393–399) only defines `input_file`, `output_file`, `--provider`, and `--voice-type`. Every run:
1. Renders TTS → writes `audio/<basename>` and `published_audio/<basename>` (lines 446–451).
2. Calls `register_mission_in_state()` → writes `episodes.json` and `lexicon.json` (line 459).
3. Runs `rebuild_rss.py` → writes `rss.xml` (line 461).
4. Runs `git add` + `git commit` + `git push` (lines 467–476).

Verify `render_audio.py` changes by source-read only. Never run it in a verify pass.
