---
name: debug
description: Symptom-to-root-cause triage for the knock loop, push queue, reply judge, studio/feed, session state, and CI. Use when a knock didn't arrive, a reply scored wrong, the feed is stale, CI is red, the push queue misfired, Anna's behaviour looks like a plumbing bug, or Anna over-uses a format / the doses have drifted samey (behavioural drift is a plumbing symptom too).
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

This applies to **behavioural drift**, not just breakage: "Anna sends too much of
one thing" or "the doses all feel the same shape" is a triage-able symptom whose
evidence lives in the log's move labels and the decide prompt's incentive lines —
never propose a quota, rule, or mechanism from taste alone (KF-8: the drift had a
one-line author in the prompt, and no quota would have found it).

Unfamiliar with the jargon below (rails gate, deck, `expected_target`, soak order)?
Start with `/orient` → `references/glossary.md`.

---

## 2. Triage Table

| Observed symptom | Suspect subsystem | First evidence command |
|---|---|---|
| No knock arrived today | Rails gate blocked, or CI never ran | `gh run list --workflow=anna.yml --limit 10` |
| Knock arrived but no audio / "bad file type" | HA automation template branch | check `knock_log.json` → `audio_url` present? + HA Traces |
| Knock body asked X, reply scored against Y | Coherence mismatch (`expected_target` vs body) | read last entry in `knock_log.json` → compare `body` and `expected_target` |
| Reply scored wrong ("miss" when Andrew fired it) | Judge saw stale / mis-targeted knock | `knock_log.json` last entry → `target_revealed`, `expected_target`, `reply`, `reply_verdict` |
| Push arrived twice (or never) | Push queue multi-fire or drain skip | `python scripts/push_queue.py list` + `knock_log.json` → `scheduled` entries |
| Push arrived at wrong time | Queue entry `due` field / quiet-hours deferral | `knock_log.json` → `rationale` field on `scheduled: true` entry |
| A dose I just heard is missing from the RATING PICKER, but IS in my podcast app | `recent_audio.txt` stale — the feed moved, its derived copy did not (KF-15) | `diff <(cat progress/recent_audio.txt) <(python -c "import sys;sys.path.insert(0,'scripts');from rebuild_rss import feed_items;[print(d['title']) for d in feed_items()[:6]]")` — any difference is the bug |
| Feed shows stale / wrong episode | RSS rebuild didn't run, or episodes.json out of sync | `grep '<title>' rss.xml \| head -5` vs newest `.mp3` in `published_audio/` (+ `knocks/`) — first titles should match the newest files |
| Status looks wrong (floor/ear numbers) | the fold — a rung set by hand | `python scripts/lexicon_view.py` (safe; zero divergent rows is the contract, s100) |
| CI red — smoke workflow | Regression in knock/reply/queue plumbing | `gh run list --workflow=smoke.yml --limit 5` then `gh run view <id> --log` |
| CI red — knock/queue workflow | Missing secret, commit conflict, JSON parse fail | `gh run view <id> --log` |
| Audio knock missing from the podcast feed | Feed refresh failed in that knock run (all audio → feed since 2026-07-05; `publish.py refresh_feed()` is failure-tolerant by design) | `gh run view <id> --log` → look for `⚠ rss rebuild failed`; recover the URL from `knock_log.json` → `audio_url`, or rerun `python scripts/rebuild_rss.py` locally |
| Anna keeps making the same mistake | May be a protocol bug, not plumbing | read `progress/feedback_log.json`; if pattern appears 2+ times → `/extend` |
| **I replied and NOTHING happened — no run, no error, no trace** | Inbound leg dead: expired PAT, or the ANNA_REPLY automation (KF-12) | Actions list → filter `repository_dispatch`. **Zero since a datestamp = the return path, not your reply.** Knocks still arriving PROVES HA is alive — outbound crosses the same HA — so suspect the one thing unique to inbound: the token |
| Anna over-uses a format / doses feel same-shaped | Incentive drift in the decide prompt (a preference line, a reward framing) — not persona | `grep -o '"move": "[^"]*"' progress/knock_log.json \| tail -15` → then read the prompt's incentive lines in `morning_knock.py` |

---

## 3. Per-Subsystem Playbooks

See `references/subsystems.md` — load it when the triage table points to a specific subsystem.

---

## 4. Known Failure Modes (archived bugs — real precedents)

One line each; the write-up is the commit of that date, and the smoke case named in it.

- **KF-1** — Same-tick multi-fire push collision (2026-07-03, fixed)
- **KF-2** — Prose-wrapped LLM JSON killed a knock tick (2026-07-04, fixed)
- **KF-3** — Misaligned expected_target — coherence mismatch (2026-07-03–05, fixed)
- **KF-4** — HA audio branch silently disabled (2026-07-01, fixed)
- **KF-5** — Playlist masked newest episode / stale concatenation (2026-07-03, removed)
- **KF-7** — Single-quoted Python dict bypassed {..} slice fallback (2026-07-07, fixed)
- **KF-6** — Chain pin destroyed the ask · menu blind to recency · hallucinated reveals (2026-07-06, fixed)
- **KF-9** — Notifications clobbered each other — deliberate tag, obsolete reason (2026-07-11, fixed)
- **KF-10** — Prose + `{noun}` gloss before the judge's json fence (2026-07-13, fixed)
- **KF-11** — Volley surface desynced from the pin — the judge improvised the chain (2026-07-18, fixed)
- **KF-12** — Expired GitHub PAT killed the reply path, silently (2026-07-31, fixed)
- **KF-13** — `chat` froze a volley — a verdict overloaded with control flow (2026-08-04, fixed)
- **KF-14** — A blown token ceiling wearing KF-7's face (2026-08-05, fixed)
- **KF-15** — The picker's list ran on a different clock than the feed (2026-09-01, fixed)
- **KF-8** — Lore format takeover — incentive drift, not taste (2026-07-11, fixed)

---

## 5. Exit: Once Root-Caused

1. If the fix is a code change → use `/extend` (change discipline gate → surgical edit → smoke case).
2. Use `/verify` to prove the fix end-to-end.
3. Every fixed plumbing bug gets a new smoke case in the layer file that owns it under `scripts/smoke/` — this is the contract that keeps KF-1 and KF-2 from recurring. **Put teeth in the dimension that failed** (`/extend` Gate 7.2, the silent no-op test): assert the *effect*, round-trip through the writer and re-read the state file, and make the absence loud. A green case on a dead feature is the 2026-07-30 `s41` result.

**Triage note for the quiet class.** The KF archive below is loud failures — crashes, parse errors, visible desync — because that is what daily use surfaced first. Since 2026-07-24 the live class is *quiet*: nothing fails, every instrument reads green, and the dose is simply about the wrong thing. When Andrew's felt signal is "this doesn't feel like it's working on my mistakes" rather than "this broke", **do not start from the error log — there won't be one.** Start from the claim: name what the subsystem promises, then find the one place that would prove it happened, and check whether anything reads it.
4. If the fix is HA config → update the gitignored `docs/anna_knock_automation.yaml` mirror.
5. If the root cause is a pattern of 2+ feedback entries → log with `python scripts/sync_state.py feedback "note"` (mutating — appends to `progress/feedback_log.json`) before proposing the fix.

---

**Scope:** This skill owns triage only. Routine health checks → `/validate`. Making the fix → `/extend`. Proving it → `/verify`.
