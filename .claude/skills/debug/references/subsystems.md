# Subsystem Playbooks (`/debug` depth reference)

Load this file when the triage table in `.claude/skills/debug/SKILL.md` points to a
specific subsystem. Each playbook: what the subsystem does, which files are the evidence,
and numbered steps.

---

## A. Knock Loop (`morning_knock.py` + `anna.yml`)

**What it does:** GitHub Actions cron is `0 * * * *` (24/7 hourly expression); GitHub
drops many scheduled ticks, so actual delivery is ~2h median — measured 2026-07-30,
and cadence is not a lever this end owns. The 8am–9pm local window is enforced by the
Rails Gate in `morning_knock.py`, NOT by the cron. The gate cheaply skips most ticks (no LLM).
When open, Anna decides fire/silence/modality via OpenRouter → optionally renders audio
via Google TTS → commits to `main` → pushes HA webhook.

**Evidence files:**
- `progress/knock_log.json` — one entry per WAKE (including silences); last entry is newest.
- GitHub Actions → **Anna Knock** workflow logs.

**Key knock_log fields to read:**
- `acted` (bool) — `false` = silence; no notification sent.
- `modality` — `"text"` | `"audio"` | `"challenge"` | `"volley"` | `"eavesdrop"` | `"fielding"` | `"grace"` | `"silence"`
- `rationale` — Anna's one-line reason; shows why he chose silence or this move.
- `next_check` — when Anna set his next wake; if this is far in the future, it explains a quiet day.
- `body` — the notification line.
- `expected_target` — the Tamil word/chunk/frame a good reply would fire (empty = no-ask dose).
- `target_revealed` (bool) — `true` = the body showed the Tamil; reply caps at "hinted".
- `audio_url` — present only on audio knocks; its absence on an audio knock is a bug.

**Playbook — no knock arrived:**
```
# SAFE (read-only)
gh run list --workflow=anna.yml --limit 10
```
1. Check: did the workflow even trigger? If missing today: GitHub schedule slip (common under load) — wait or use `workflow_dispatch` to trigger manually.
2. If it ran: `gh run view <run-id> --log` — look for `[rails] skip — ` lines. Common skip reasons:
   - `quiet hours (HH:MM EDT)` — the tick landed outside 8am–9pm.
   - `daily cap reached (5/5)` — five fires already today.
   - `min-gap not met (X.Xh < 3h)` — too close to last reach.
   - `Anna's next_check not due (set for ...)` — Anna soft-gated himself.
3. If `[rails] wake` but then stopped: look for the LLM/TTS step error. Common: missing secret (`OPENROUTER_API_KEY` not set), or KF-2 (prose-wrapped JSON).
4. If `act=false modality=silence`: Anna chose silence. Check rationale in the log; also check `progress/knock_log.json[-1]["rationale"]`.

**Playbook — audio knock delivered as text (no player):**
1. Read `progress/knock_log.json` last entry: is `audio_url` present?
   - If absent: Anna chose a text/challenge/grace modality — working as designed.
   - If present but phone showed text: HA automation took the `else` branch → KF-4.
2. In HA: open the "Notify Andrew" automation → Traces → look for `choice: else` on an audio entry.
3. Fix: update `docs/anna_knock_automation.yaml` mirror and the real HA automation. See KF-4 in SKILL.md.

---

## B. Push Queue (`push_queue.py` + `anna.yml`)

**What it does:** Durable "ping me at X" layer. Entries are fully composed at add-time
and drained at the START of every Anna wake-up (`anna.yml` — hourly tick, reply, or dispatch). Each fired entry is logged into
`knock_log.json` (field `scheduled: true`) so the reply judge and the rails see it.
Quiet hours and the daily cap apply to non-forced entries; `force: true` bypasses both.

**Evidence files:**
- `progress/push_queue.json` — pending entries, sorted by `due` (ascending).
- `progress/knock_log.json` — entries with `scheduled: true` are past-fired queue items.

**Playbook — push didn't arrive:**
```
# SAFE (read-only)
python scripts/push_queue.py list
gh run list --workflow=anna.yml --limit 10
```
1. Is the entry still in the queue? (`list` shows pending). If yes: check its `due` timestamp (UTC) vs now.
2. Is `force: false` and the entry is due in quiet hours? It defers silently to the next waking tick.
3. Is the daily cap already at 5 for today? Non-forced entry defers until the next day.
4. Did the drain step run? `gh run list --workflow=anna.yml` — the drain is the first step of EVERY run, so a missing drain means no run at all.
5. Drain locally (mutating!): only if you have confirmed the entry should fire and secrets are set.

```
# MUTATING — fires the push, commits, and notifies
python scripts/push_queue.py drain
```

**Playbook — push arrived twice (KF-1 pattern):**
1. Check `knock_log.json` for two entries with `scheduled: true` and the same `due` timestamp or close timestamps.
2. Confirm drain version is post `1f5b304`: it caps at `non_forced_fired = True` after the first non-forced fire per tick. If the bug recurs, add a smoke case.
3. If two forced entries fired: that is expected — `force: true` bypasses the cap by design.

**Playbook — check queue state:**
```
# SAFE (read-only)
python scripts/push_queue.py list

# SAFE (dry-run — prints what would fire, no writes)
python scripts/push_queue.py drain --dry-run
```

---

## C. Reply Judge (`knock_reply.py` + `anna.yml`)

**What it does:** Home Assistant fires a `repository_dispatch: knock-response` event when
Andrew taps or replies. The workflow calls either `sync_state.py knock-response ack` (tap)
or `knock_reply.py "<text>"` (typed Tamil). The judge scores per word, moves the production
axis (upgrades only — never demotes), and pushes a recast + scoreboard back.

**Evidence files:**
- `progress/knock_log.json` — last entry's `reply*` fields.
- `progress/lexicon.json` — production axis values for the scored word(s).
- GitHub Actions → **Log Knock Response** workflow logs.

**Key knock_log reply fields:**
- `reply` — Andrew's raw typed text.
- `reply_verdict` — `"cold"` | `"hinted"` | `"miss"` | `"chat"`
- `reply_fired` — list of words that fired (any grade).
- `reply_fired_cold` — words that got credit as cold after the revealed-cap.
- `reply_line` — Anna's push-back (recast + optional chained ask).
- `reply_at` — UTC timestamp of the reply.
- `chained` — number of chained follow-up asks on this knock.

**Playbook — reply scored wrong:**
1. Read the last `knock_log.json` entry. Confirm `reply` matches what Andrew typed.
2. Check `expected_target` vs the body: is this a coherence mismatch? (KF-3). The body's natural answer should be `expected_target`; if they diverge, the judge flagged it in `rationale`.
3. Check `target_revealed`: if `true`, the judge cannot credit that word as "cold" — this is the hard rule, enforced in `apply_verdict()` in `knock_reply.py`.
4. If the judge workflow ran: `gh run view <id> --log` — look for the `! '<word>' resolves to no lexicon record` line. A fired word that doesn't resolve to a lexicon key is skipped silently.
5. Dry-run a re-judge (safe, no writes):
```
# SAFE — prints verdict only; no state writes, no push-back
python scripts/knock_reply.py --dry-run "naan poren"
```
6. If the production axis is wrong in the lexicon (e.g. a cold fire didn't land): use a chat session and `sync_state.py update --produced-cold '<word>'` to correct it. That is a mutating operation — do it in a session context.

**Playbook — continuity decay (reply to old knock):**
- If `reply_at` or `timestamp` is >3h ago, the judge passes `hours_since_last_exchange` to the LLM. The mandate treats the scenario as expired; Anna grades the raw Tamil without requiring scene fidelity. This is intended — not a bug.

---

## D. Studio / Audio / RSS / Feed (`render_audio.py` + `rebuild_rss.py`)

**What it does:** Local-only pipeline today — not a law: the cloud can render, but the knock-tick episode move is unbuilt (see `docs/DECISIONS.md`).
`render_audio.py` reads a markdown script, calls Google TTS, stitches MP3, writes to
`published_audio/`, registers the episode in `progress/episodes.json`, stamps `seen_in`
in `progress/lexicon.json`, and calls `rebuild_rss.py` as a lifecycle hook.
`rebuild_rss.py` scans `published_audio/` for `tier*.mp3` and `drill_*.mp3` files,
reads matching scripts from `content/scripts/`, and writes `rss.xml`.

**Evidence files:**
- `published_audio/` — the actual audio files served to the feed.
- `progress/episodes.json` — episode registry (title, words, duration_min, listens).
- `rss.xml` — the feed. Only one feed; playlist was retired 2026-07-03 (KF-5).

**Playbook — feed shows stale / wrong episode:**
```
# SAFE (read-only)
ls -lt published_audio/*.mp3 | head -5          # newest by mtime
python -c "import json; e=json.load(open('progress/episodes.json')); mx=max(e,key=int); print(mx, e[mx]['title'])"
grep -c '<item>' rss.xml
```
1. Does the newest file in `published_audio/` appear in `rss.xml`? If not, `rebuild_rss.py` didn't run or ran from a different working directory.
2. Does `rebuild_rss.py` filter correctly? It includes `tier*.mp3` and `drill_*.mp3`, excludes legacy `level4_*`, demos, and standalone `*_intercept.mp3` files.
3. Is `episodes.json` stale vs `rss.xml`? They are separate: RSS reads `published_audio/` directly; `episodes.json` is the Python brain's registry. Both should agree on title/count.
4. To regenerate RSS locally (mutating — rewrites `rss.xml` in place, must be run from the repo root):
```
# MUTATING — rewrites rss.xml
python scripts/rebuild_rss.py
```
5. CDN lag: `rss.xml` is served from GitHub raw content, not jsDelivr. A fresh push takes ~30s for GitHub to serve the new content; podcast apps may cache longer.

---

## E. Session State (`sync_state.py`)

**What it does:** `sync_state.py` owns all writes to `progress/`. The `status` sub-command
is the safe read-only dashboard. `update` moves the recognition and production axes.

**Evidence command (safe, read-only):**
```
python scripts/sync_state.py status
```

**Playbook — floor/deck numbers look wrong:**
1. Run `status` — it recomputes live from `lexicon.json`; the stored `learner.json`
   status line can lag (it's updated by `update`, not by every read).
2. If a specific word's axis is wrong: read its record directly:
```
# SAFE (read-only)
python -c "import json; lex=json.load(open('progress/lexicon.json')); print(lex.get('போதும்', 'not found'))"
```
3. Verify canonical key: lexicon keys must be Tamil script (verified by `TAMIL_RE` in `state_io.py`). Phonetic variants live in the `phonetic` list. `resolve()` maps phonetic → script.
4. If a phone-rep cold fire didn't update the axis: the word may have resolved to `None` (no lexicon record). The judge prints `! '<word>' resolves to no lexicon record — not scored`. Fix: seed the record first (`sync_state.py add-word`).
5. To correct state from a known-good chat session — use `update` (mutating):
```
# MUTATING — moves production axis (upgrades only; no demotion from cmd line)
python scripts/sync_state.py update --produced-cold 'போதும்'
```

---

## F. CI / Workflows

**Four workflows (verified from `.github/workflows/`):**

| Workflow file | Name in Actions UI | Trigger | What it does |
|---|---|---|---|
| `anna.yml` | Anna | cron (hourly) + `repository_dispatch: knock-response` + dispatch | Every lane, every secret. Always drains the queue first (`push_queue.py drain`), then runs `morning_knock.py` (tick/dispatch), `knock_reply.py` (reply) or `sync_state.py knock-response` (tap) |
| `smoke.yml` | Smoke Test | push to main (scripts/**, workflows/**, requirements.txt) | Runs `smoke_test.py` sandboxed |

**Playbook — CI red:**
```
# SAFE (read-only)
gh run list --workflow=<filename> --limit 10
gh run view <run-id> --log
```

Common causes:
- **Missing secret:** `OPENROUTER_API_KEY`, `ANNA_PUSH_WEBHOOK_URL`, or `GCP_SA_KEY` not set → step fails with auth error or 401.
- **Git rebase conflict:** knock, queue, and laptop all push to `main`. Workflow uses `git pull --rebase --autostash origin main` before push; a conflict here leaves the runner in a bad state. Look for `CONFLICT` in the log.
- **Smoke test FAIL:** a regression in knock/reply/queue plumbing. The log names the failing case. Run `python scripts/smoke_test.py` locally to reproduce.
- **Fresh-clone red crons:** if secrets are not yet configured, knock and queue workflows fail loud on every tick. This is intentional (BOOTSTRAP.md). Disable Actions or add secrets before the first push.
