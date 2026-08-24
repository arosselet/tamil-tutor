---
name: verify
description: Prove a change works end-to-end — change-type → verification-path map, flag semantics (what each --dry-run actually skips, verified in source), sandbox pattern, and the honest-residual rule. Use when you want to confirm a fix holds, verify a code change is wired correctly, or understand what a flag actually skips before running it.
---

# Verify — End-to-End Change Verification

## 1. Rails — read before touching anything

**Never exercise a change against live `progress/` state.** That directory holds real, irreplaceable learner data owned by Python. No verification step should write to it outside the smoke sandbox.

| Do NOT run in a verify pass | Why |
|---|---|
| `morning_knock.py` (bare) | Calls LLM, writes `knock_log.json`, fires real phone push, commits to `main` |
| `knock_reply.py TEXT` (bare) | Writes `lexicon.json` + `knock_log.json`, commits, fires push-back |
| `push_queue.py drain` (bare) | Fires real phone push, writes `knock_log.json` + `push_queue.json`, commits |
| `render_audio.py` | No dry-run flag — always writes `published_audio/`, `rss.xml`, commits, pushes |
| `sync_state.py update …` | Writes `lexicon.json`, `learner.json`, `session_log.json` |

**The canonical harness is `scripts/smoke_test.py`.** Extend it rather than writing ad-hoc scripts. CI (`.github/workflows/smoke.yml`) runs it on every push to `main` touching `scripts/**`, `.github/workflows/**`, or `requirements.txt`.

Safe to run locally (read-only or sandboxed):
```
python scripts/smoke_test.py          # sandboxed copy — never touches live progress/
python scripts/sync_state.py status   # read-only: loads and prints, no writes
python scripts/show_status.py         # read-only dashboard
```

---

## 2. Change-type → verification path

| What changed | Verification path |
|---|---|
| Knock/queue/judge logic (`morning_knock.py`, `knock_reply.py`, `push_queue.py`) | `python scripts/smoke_test.py` + add a smoke case for the fixed behavior (§3) |
| State schema or `sync_state.py` | Smoke test + `python scripts/sync_state.py status` (read-only) + confirm every changed field exists in `progress/*.example` templates |
| Drill pipeline (`render_drill.py`) | `--dry-run` (LLM fires, no TTS, no file writes) or `--no-publish` (LLM + TTS + MP3 written, no RSS/commit/push) — see `references/flags.md` for exact boundaries |
| Morning knock (`morning_knock.py`) | `--dry-run` (LLM fires; if Anna chooses audio, TTS fires AND the MP3 is written before the gate) — see `references/flags.md`; also add a smoke case if logic changed |
| Audio pipeline (`render_audio.py`) | Source-read only — no dry-run flag; trace what you checked and state what is unverified. Never run it in a verify pass. |
| `protocol/*.md` prose | No runtime surface. Verify by reading the changed text against `protocol/constitution.md` canonical rules. This is the honest answer; no runtime harness exists for prose. |
| `.github/workflows/*.yml` | `python scripts/smoke_test.py` reproduces the smoke job locally; `gh run watch <run-id>` watches CI after a push |

---

## 3. Adding a smoke case

Every fixed bug gets a case the day it's fixed. Pattern (from the existing s1–s8 in `smoke_test.py`):

All helpers used below (`canned_decision`, `Recorder`, `write_json`, `read_json`, `check`, `make_sandbox`) are defined at the top of `scripts/smoke_test.py` itself — no imports needed.

**Step 1 — Write the function** (add after the last `sN_*` function):

```python
def sN_your_description(mk, kr, pq, sb: Path):
    print("\nN. What this regression guards against")
    prog = sb / "progress"

    # Replace the stubbed boundaries on the relevant module (LLM, push, commit —
    # plus render_memo if the scenario takes the audio path). Since 2026-08-24
    # `run()` puts every one of these back after the case returns, so a stub can
    # no longer leak forward and a case can no longer depend on one leaking in:
    pushes, commits = Recorder(), Recorder()
    mk.push_to_phone, mk.commit_and_push = pushes, commits

    # Stub the LLM:
    mk.decide = lambda digest: canned_decision(True, "smoke body")
    # or: kr.judge = lambda k, r, t, h=None: canned_verdict([("போதும்", "cold")])

    # Set up fixture state in the sandbox:
    write_json(prog / "knock_log.json", [])

    # Invoke via sys.argv, same as the CLI does:
    sys.argv = ["morning_knock.py"]   # or ["knock_reply.py", "text"], ["push_queue.py", "drain"]
    mk.main()                         # or kr.main(), pq.main()

    # Assert:
    result = read_json(prog / "knock_log.json")
    check("what the bug was and that it's fixed", <condition>, f"got {result}")
```

**Step 2 — Call it from `main()`** (inside the `with tempfile.TemporaryDirectory(...)` block):
```python
sN_your_description(mk, kr, pq, sb)
```

Three invariants the sandbox enforces — do not break them:
- Modules are imported from the sandbox copy (asserted by `mk.__file__.startswith(str(sb))`).
- Replace `push_to_phone` and `commit_and_push` with fresh `Recorder()` per scenario before calling `main()`.
- **Run the one case you are working on**: `python scripts/smoke_test.py s41` (case
  number, exact) or `python scripts/smoke_test.py s41_slip` (name prefix). Each
  invocation builds its own sandbox, and all 71 cases pass alone — so a failure
  reproduces in one run instead of behind forty predecessors. No argument runs the
  whole suite, which is what CI does.
- **State a case's preconditions in the case.** Stubs are torn down between cases
  now, so anything your scenario needs — an open rails gate, a seeded lexicon row,
  a slip on the ledger — it must install itself. `s50` (`--force`) and `s69` (its
  own seed block) are the worked examples.
- `progress/` in the sandbox is seeded from `*.example` files — the real `progress/` is never touched.

---

## 4. Flag semantics

The single owner of command safety + flag semantics is **`references/flags.md`**
(full inventory + per-flag what-is-skipped detail). One standing warning worth
carrying everywhere: several `--dry-run` flags still fire the LLM — and
`morning_knock.py --dry-run` still writes a real MP3 on the audio path.

---

## 5. Honest residual — state what was NOT covered

End every verification pass by declaring what remained unexercised:

- **Actual TTS audio** — `--dry-run`/`--no-publish` stop before or skip delivery; voice quality, Tamil pronunciation, and timing are only verifiable by listening.
- **Phone delivery** — `push_to_phone` hits the Home Assistant webhook; correct body/URL can be confirmed in source, but actual device delivery is invisible to any local test.
- **CDN pre-warm** — `morning_knock.py` (audio modality) fetches the jsDelivr URL before pushing; this network call is never exercised in smoke.
- **Git operations** — `commit_and_push` is always stubbed in smoke; the concurrent-writer rebase (`git pull --rebase --autostash`) is never tested locally.
- **`render_audio.py` changes** — source-read is the only verification; name the exact lines you checked.
- **`protocol/*.md` prose** — reading against `protocol/constitution.md` is the only verification; no runtime surface exists.
