# Flag Semantics — Full Reference

All claims verified in source. Line numbers are stable as of the commit this skill was written against.

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
