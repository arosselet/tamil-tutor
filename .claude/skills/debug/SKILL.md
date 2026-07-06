---
name: debug
description: Symptom-to-root-cause triage for the knock loop, push queue, reply judge, studio/feed, session state, and CI. Use when a knock didn't arrive, a reply scored wrong, the feed is stale, CI is red, the push queue misfired, or Anna's behaviour looks like a plumbing bug.
---

# Debug — Triage and Root-Cause

## 1. Doctrine

**Evidence before action. Plumbing before persona.**

When Anna seems wrong — forgetful, miscalibrated, missing — read the logs first.
The 2026-07-03 incident ("Anna had no knowledge of my reply") was a same-tick
multi-fire collision in the push queue, 100% plumbing, zero persona involvement.
Full law: `docs/DECISIONS.md` → "Fix the tool, not the personality."

Do not touch prompts, protocol files, or persona until you have a log-confirmed
root cause. If the root cause points to a code change, stop here and use `/extend`
for the fix and `/verify` to prove it.

Unfamiliar with the jargon below (rails gate, deck, `expected_target`, soak order)?
Start with `/orient` → `references/glossary.md`.

---

## 2. Triage Table

| Observed symptom | Suspect subsystem | First evidence command |
|---|---|---|
| No knock arrived today | Rails gate blocked, or CI never ran | `gh run list --workflow=morning-knock.yml --limit 10` |
| Knock arrived but no audio / "bad file type" | HA automation template branch | check `knock_log.json` → `audio_url` present? + HA Traces |
| Knock body asked X, reply scored against Y | Coherence mismatch (`expected_target` vs body) | read last entry in `knock_log.json` → compare `body` and `expected_target` |
| Reply scored wrong ("miss" when Andrew fired it) | Judge saw stale / mis-targeted knock | `knock_log.json` last entry → `target_revealed`, `expected_target`, `reply`, `reply_verdict` |
| Push arrived twice (or never) | Push queue multi-fire or drain skip | `python scripts/push_queue.py list` + `knock_log.json` → `scheduled` entries |
| Push arrived at wrong time | Queue entry `due` field / quiet-hours deferral | `knock_log.json` → `rationale` field on `scheduled: true` entry |
| Feed shows stale / wrong episode | RSS rebuild didn't run, or episodes.json out of sync | `grep '<title>' rss.xml \| head -5` vs newest `.mp3` in `published_audio/` (+ `knocks/`) — first titles should match the newest files |
| Status looks wrong (floor/deck numbers) | `lexicon.json` state, compute logic | `python scripts/sync_state.py status` (safe) |
| CI red — smoke workflow | Regression in knock/reply/queue plumbing | `gh run list --workflow=smoke.yml --limit 5` then `gh run view <id> --log` |
| CI red — knock/queue workflow | Missing secret, commit conflict, JSON parse fail | `gh run view <id> --log` |
| Audio knock missing from the podcast feed | Feed refresh failed in that knock run (all audio → feed since 2026-07-05; `morning_knock.py refresh_feed()` is failure-tolerant by design) | `gh run view <id> --log` → look for `⚠ rss rebuild failed`; recover the URL from `knock_log.json` → `audio_url`, or rerun `python scripts/rebuild_rss.py` locally |
| Anna keeps making the same mistake | May be a protocol bug, not plumbing | read `progress/feedback_log.json`; if pattern appears 2+ times → `/extend` |

---

## 3. Per-Subsystem Playbooks

See `references/subsystems.md` — load it when the triage table points to a specific subsystem.

---

## 4. Known Failure Modes (archived bugs — real precedents)

### KF-1: Same-tick multi-fire push collision (2026-07-03, fixed)
**Symptom:** Two queued pushes both due → both fire in one drain tick → Andrew's reply is
judged against the second (last-logged) knock, not the one he was actually answering.
**Root cause:** `push_queue.py cmd_drain` fired all due non-forced entries in one batch;
`knock_reply.py last_fired_knock()` always targets the last `acted=true` entry.
**Fix:** Drain caps at one non-forced fire per tick; the rest defers to the next tick.
**Verify:** `python scripts/smoke_test.py` → section 6 (regression #1).
**Commit:** `1f5b304`

### KF-2: Prose-wrapped LLM JSON killed a knock tick (2026-07-04, fixed)
**Symptom:** Knock workflow shows `Expecting value: line 1 column 1 (char 0)`; no knock fired.
**Root cause:** The decision model occasionally wraps its JSON in prose (or returns empty);
the old parser only handled ` ``` ` code fences, so bare prose raised immediately.
**Fix:** `parse_llm_json()` (in `morning_knock.py`) now: strips fences → tries `json.loads`
→ falls back to the outermost `{...}` slice → prints raw text before re-raising so the
log shows what came back, not just that it failed.
**Verify:** `python scripts/smoke_test.py` → section 1 (regression #2).
**Commit:** `dc1e1fd`

### KF-3: Misaligned expected_target — coherence mismatch (2026-07-03–05, fixed)
**Symptom:** Valid Tamil replies repeatedly scored as "miss"; judge felt rigid for days.
**Root cause:** The knock mandate let Anna write a body for one deck item while setting
`expected_target` to a different one ("evlo naal irupeenga?" graded against "we'll go back").
**Fix:** Coherence law (2026-07-05): pick `expected_target` first, write body as the
ask for that target. Judge voids a mis-targeted knock and grades against the body's natural
answers instead. Teach-before-quiz flag (UNSEEN) on never-soaked deck items.
**Verify:** read last `knock_log.json` entries — `body` and `expected_target` must be
aligned (the body's natural answer should be `expected_target`).
**Commit:** `3c4a534`

### KF-4: HA audio branch silently disabled (2026-07-01, fixed)
**Symptom:** Audio knocks deliver text only — no inline player, no attachment error.
**Root cause:** HA template condition `{{ x is defined and x }}` returns the URL *string*,
which a 2026-07 HA core update counts as falsy → automation always took the else branch.
**Fix:** Condition is now `{{ trigger.json.audio_url | default('') | length > 0 }}`.
**Verify:** HA Automation Traces → check "choice" field; `else` on an audio knock = bug.
**Where:** `docs/anna_knock_automation.yaml` (gitignored mirror; real value in HA).

### KF-5: Playlist masked newest episode / stale concatenation (2026-07-03, removed)
**Symptom:** Feed player shows old episode as the newest.
**Root cause:** `build_playlist.py` built a stale concatenation that appeared first in the
feed; listen-count signal that drove it went blind after the stop-chasing-listens pivot.
**Fix:** Playlist removed entirely. `rss.xml` is the only feed.
**Verify:** `cat rss.xml | grep '<title>' | head -5` — first episode title should match
the newest `.mp3` in `published_audio/`.

### KF-6: Chain pin destroyed the ask · menu blind to recency · hallucinated reveals (2026-07-06, fixed)
**Symptom:** Log's `expected_target` absurd vs the body (looked like KF-3 returning);
the same surface ask fired 5× in 4 days under different move names; correct unaided
productions stuck at hinted (a real cold denied for a reveal that never happened);
chat.md showed only the last reply of a chain — real cold fires vanished under a test reply.
**Root cause (three-part):** chained follow-ups overwrote `expected_target` and the reply
fields (only fired lists accumulated); `deck_due_list` ranked ripest-first with no recency
signal while outcome memory showed move names only, so the variety law had no evidence of
same-ask repeats; the judge's reveal-cap trusted model memory of what had been shown.
**Fix:** chain moves `pinned_target`/`pinned_revealed`; every exchange appends to
`exchanges` (chat renders the full chain); menu demotes+marks items asked/shown in 3 days
and outcome memory carries the ask; `revealed_recently()` computes reveals from the log —
the judge may cap against that list only.
**Verify:** `python scripts/smoke_test.py` → section 10 (regression #3).
**Commit:** `a13d3b9`

---

## 5. Exit: Once Root-Caused

1. If the fix is a code change → use `/extend` (change discipline gate → surgical edit → smoke case).
2. Use `/verify` to prove the fix end-to-end.
3. Every fixed plumbing bug gets a new smoke case in `scripts/smoke_test.py` — this is the contract that keeps KF-1 and KF-2 from recurring.
4. If the fix is HA config → update the gitignored `docs/anna_knock_automation.yaml` mirror.
5. If the root cause is a pattern of 2+ feedback entries → log with `python scripts/sync_state.py feedback "note"` (mutating — appends to `progress/feedback_log.json`) before proposing the fix.

---

**Scope:** This skill owns triage only. Routine health checks → `/validate`. Making the fix → `/extend`. Proving it → `/verify`.
