---
name: validate
description: Routine health check for the Tamil learning system. Run the smoke test, verify state invariants, confirm feed/registry coherence, and check CI green. Use proactively — after any machinery change, after a clone, before trusting state, or before a session. (For a specific symptom or failure, start with /debug instead.)
---

# Validate — Routine Health Check

Run these layers in order. Stop at the first failure and route to `/debug`.

---

## 1. When to validate

- After editing any file in `scripts/`, `.github/workflows/`, or `requirements.txt`
- Before trusting `sync_state.py status` (e.g. numbers look wrong)
- After a clone or bootstrap (BOOTSTRAP.md)
- Whenever a knock / reply / drain behaved unexpectedly

---

## 2. The layered checklist

### Layer 1 — Smoke test (local)

```
python scripts/smoke_test.py
```

**Safe.** Sandboxed: copies the repo to a tempdir, stubs LLM / TTS render / push / git. No writes outside the sandbox. Runs in seconds.

**Pass:** last line is `ALL GREEN`.  
**Fail:** any `[FAIL]` line prints the failing check name and detail. Stop here → `/debug`.

**What it covers:** LLM-response parsing, rails gate logic, knock fire/silence paths, verdict normalization, reply judge + production axis, queue drain (oldest-first, quiet-hours, daily-cap), state integrity (valid JSON, `knock_log` entries have `date`+`timestamp`), variety/decay helpers.

**What it does NOT cover:** studio/audio rendering, RSS correctness, real lexicon key canonicality in `progress/`, `sync_state.py` subcommands other than the functions they exercise.

### Layer 2 — Status clean

```
python scripts/sync_state.py status
```

**Safe (read-only).** Prints: current time (EDT/EST), learner name, last logged session + gap, Status line (Trip Deck or Viability floor), story, soak order, recognition/production breakdown, Engines, Trip Deck, fired today, recent episodes.

**Pass:** output completes without `Error:` or `not found`. A stale soak order prints `⚠ stale — chat hasn't fed the Director lately` (fires when the soak order is >7 days old, `sync_state.py:539`) — that's a content signal meaning "run a session," not an error; don't route it to `/debug`.  
**Fail:** `lexicon.json or learner.json missing` → bootstrap problem; `No learner.json found` → same.

### Layer 3 — State invariants

Check these manually or with quick one-liners. Each invariant has an enforcing code cite.

| Invariant | Enforcing code | Quick check |
|---|---|---|
| Every word key in `lexicon.json` is Tamil script matching `[஀-௿]+`, OR is a `frame:*` pattern key | `state_io.py` line 54 (`TAMIL_RE`); `add-word` rejects non-Tamil at line 408 | `python -c "import json,re; d=json.load(open('progress/lexicon.json')); bad=[k for k in d if not re.search(r'[஀-௿]',k) and not k.startswith('frame:')]; print(bad or 'ok')"` |
| Every lexicon entry's `recognition` is one of `struggled`, `comfortable`, `solid` | `sync_state.py` RECOGNITION_LEVELS line 53 | Scan for any value outside the set |
| Every lexicon entry's `production` is one of `none`, `hinted`, `cold` | `knock_reply.py` PRODUCTION_RANK line 42 | Scan for any value outside the set |
| `knock_log.json` entries carry `date` and `timestamp` | `smoke_test.py` s7_integrity | `python scripts/smoke_test.py` (already covered in Layer 1) |
| `learner.json` has fields `learner`, `last_debrief`, `soak_order`, `recent_missions`, `status` | `sync_state.py` write_thin_learner (lines 221-228) | `python -c "import json; d=json.load(open('progress/learner.json')); print([f for f in ['learner','last_debrief','soak_order','recent_missions','status'] if f not in d] or 'ok')"` |
| `progress/*.json.example` templates stay in sync with the schema each file expects | `smoke_test.py` make_sandbox lines 51-54 (copies `.example` → live file for testing) | Visually compare example keys against what `sync_state.py update` / `write_thin_learner` expects |

### Layer 4 — Feed / registry coherence

These three artefacts must agree. A drift means `render_audio.py` or `rebuild_rss.py` failed mid-run.

```
# Count missions in episodes.json
python -c "import json; e=json.load(open('progress/episodes.json')); print(f'{len(e)} episodes registered: {sorted(e.keys())}')"

# Count tier episodes in published_audio/
ls published_audio/tier*_mission*.mp3 2>/dev/null | wc -l

# Confirm rss.xml exists and has items
grep -c '<item>' rss.xml 2>/dev/null || echo "rss.xml missing"
```

**Pass:** `episodes.json` count roughly matches `published_audio/tier*_mission*.mp3` count; `rss.xml` items = episodes + drills + knocks (`published_audio/knocks/`) + the welcome track, so it exceeds the episode count. Exact numbers may differ if a file was rendered to `audio/` only (not `published_audio/`).

**Fail / mismatch:** An episode registered in `episodes.json` but missing from `published_audio/` means the render didn't complete. An `rss.xml` that predates the newest audio file means `rebuild_rss.py` didn't run. Route to `/debug`.

### Layer 5 — CI green

```
gh run list --workflow=smoke.yml --limit=5
```

**Safe (read-only git).** CI runs on push to `main` when `scripts/`, `.github/workflows/`, or `requirements.txt` change (verified: `smoke.yml`).

**Pass:** the most recent run shows `completed / success`.  
**Fail:** `failure` → the smoke test failed in CI on a real push. Route to `/debug`.

---

## 3. Command inventory — safe vs mutating

One owner, no restating (2026-07-18): the full inventory — every script, every
flag, safe vs mutating, exactly what each writes — lives in
**`/verify` → `references/flags.md`**. Read it before running anything you're
not certain about; `progress/` holds real, irreplaceable learner state.

---

## 4. What validation cannot catch

Validation checks **plumbing** (JSON, invariants, CI green). It cannot catch:

- **LLM-behavior quality:** Anna's voice drift, persona softening, wrong register, teaching pattern, soak-order staleness, or session choreography failures.
- **Content errors:** a word gloss that's wrong, a lexicon entry with bad phonetics, an episode that contains the wrong Tamil.

These are not plumbing — route behaviour complaints to `/debug`, and pedagogy felt-signals to `/recalibrate` (which wraps `protocol/diagnosis.md`).

---

## 5. Exit

Any layer fails → `/debug` with the symptom and which layer caught it.

All layers pass → state is coherent. If something still feels wrong in a *session*, that's a signal for the Diagnosis pass, not a plumbing bug.
