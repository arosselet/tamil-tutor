#!/usr/bin/env python3
"""
Studio watchdog — self-healing production (feature inbox 2026-07-17, commissioned
2026-07-18). Nothing Anna orders should wait for human hands: each awake tick
notices work the studio left undone and runs the EXISTING dispatch — it never
invents a pipeline of its own. Local only — not because the cloud cannot render (it
can, and does), but because the knock-tick episode move is not built yet.

Two pending states, checked in order:
  1. scripted-but-unrendered — the newest mission script has no MP3. Re-lint
     first: lint-clean → render_audio.py (render only); lint-failing → these are
     failed artifacts left for inspection — report and STOP. Never render a bad
     script, never stack a fresh dispatch on top of one awaiting a human.
  2. soak order NOT YET PRODUCED (same computation as sync_state status) →
     run_studio.py, full dispatch. Exit 1 there is the fallback contract; here
     it just means "retry next tick" — the log carries the reason.

Nothing pending → exits silently, so the cron log only shows action.
`.studio.lock` is shared with run_studio.py: a tick never races a session-open
dispatch, and a session dispatch never races a tick.

Install (one-off; cron only fires while the laptop is awake, which is the spec —
a missed sleeping tick is caught by the next awake one). SSH_AUTH_SOCK points at
the gnome-keyring agent so the render's git push authenticates; PATH carries agy
and the anaconda python:

  (crontab -l 2>/dev/null; \
   echo '17 * * * * cd $HOME/projects/Tamil && SSH_AUTH_SOCK=/run/user/1000/keyring/ssh PATH=$HOME/.local/bin:$HOME/anaconda3/bin:/usr/bin:/bin python3 scripts/studio_watchdog.py >> studio_watchdog.log 2>&1') | crontab -
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_studio import (AUDIO_DIR, BASE, EXIT_NOT_CONFIGURED, episode_paths,
                        git_dirty, lint, next_mission, preflight,
                        renderer_preflight)
from state_io import EPISODES_PATH, LEARNER_PATH, load_json
from sync_state import canon_payload, soak_pending

LOCK_PATH = BASE / ".studio.lock"

# Unattended production is capped. The watchdog exists to catch work Andrew's
# absence stranded — not to set the pace. On 2026-07-23 a stuck produced-check
# dispatched M72/M73/M74 in one evening, three episodes nobody asked for; the
# root cause is fixed (split_payload), but rate stays a rail, not a hope.
# Anna commissioning in-session is unaffected — this bounds the CRON only.
#
# RAISED 1 -> 3 (2026-07-28, Andrew: "guardrails to a problem that was
# temporary — remove it or raise it"). He is right that 1 was sized to a fixed
# bug. It also became BINDING under the repair-first commissioning rule
# (daily_session.md Close & Log 2): when a day's unclosed repairs each earn
# their own order, one dose a day is the constraint that starves the fix. Kept
# rather than removed, because the cap never guarded that one bug — it bounds
# whatever the NEXT stuck predicate turns out to be, and the blast radius is
# unattended: renders, feed entries and phone pushes fired while he is out.
# Three is headroom (a repair dose, a campaign dose, one spare); the rail is
# that the number is finite, not that it is small.
MAX_UNATTENDED_PER_DAY = 3


def stamp(msg: str):
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] watchdog: {msg}", flush=True)


def try_lock():
    """Non-blocking probe of the shared dispatch lock. Returns the held fd, or
    None if a dispatch is in flight. No-op success where fcntl is missing."""
    try:
        import fcntl
    except ImportError:
        return open(LOCK_PATH, "w")
    fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fd.close()
        return None
    return fd


def scripted_unrendered() -> int | None:
    """Newest mission with a script on disk but no published MP3, else None."""
    n = next_mission() - 1
    if n < 1:
        return None
    rendered = (AUDIO_DIR / f"tier2_mission{n}.mp3").exists() or any(
        AUDIO_DIR.glob(f"tier2_mission{n}_v*.mp3"))  # a _vN re-render counts
    if episode_paths(n)["script"].exists() and not rendered:
        return n
    return None


def outcome(code: int, what: str) -> str:
    """One honest line per tick. EXIT_NOT_CONFIGURED is not a failure — this
    host simply isn't a studio host, so say so once and don't dress it as a
    retryable error (an absent secret never heals on the next tick)."""
    if code == 0:
        return f"{what} done"
    if code == EXIT_NOT_CONFIGURED:
        return f"{what} skipped — this host lacks the studio credentials (no retry)"
    return f"{what} failed (exit {code}) — retry next tick"


def produced_today() -> int:
    """Episodes this cron already produced today, from episodes.json stamps."""
    today = datetime.now().date().isoformat()
    episodes = load_json(EPISODES_PATH) or {}
    return sum(1 for e in episodes.values() if e.get("produced") == today)


def main():
    lock = try_lock()
    if lock is None:
        stamp("a dispatch holds .studio.lock — skipping this tick")
        return

    n = scripted_unrendered()
    if n is not None:
        problems = lint(n, baseline=git_dirty())  # current tree as baseline: no stray noise
        if problems:
            stamp(f"mission {n} scripted but lint-failing — left for inspection, not rendering:")
            for p in problems:
                print(f"   ✗ {p}")
            return
        # Re-rendering an existing script needs TTS credentials only — never agy.
        reason = renderer_preflight()
        if reason:
            stamp(f"mission {n} unrendered but this host cannot render — {reason}; skipping (no retry)")
            return
        stamp(f"mission {n} scripted but unrendered — rendering now")
        # We hold the lock; hand it to the child rather than have it wait on us.
        r = subprocess.run([sys.executable, str(BASE / "scripts" / "render_audio.py"),
                            str(episode_paths(n)["script"]),
                            str(AUDIO_DIR / f"tier2_mission{n}.mp3")], cwd=BASE,
                           env={**os.environ, "STUDIO_LOCK_HELD": "1"})
        stamp(outcome(r.returncode, "render"))
        return

    if soak_pending():
        n_today = produced_today()
        if n_today >= MAX_UNATTENDED_PER_DAY:
            stamp(f"soak order pending but {n_today}/{MAX_UNATTENDED_PER_DAY} episodes "
                  f"already produced unattended today — holding for a session")
            return
        # A fresh episode needs the writer AND the renderer.
        reason = preflight()
        if reason:
            stamp(f"soak order pending but this host is not a studio host — {reason}; "
                  f"skipping (no retry)")
            return
        stamp("soak order not yet produced — dispatching run_studio.py")
        lock.close()  # run_studio takes the same lock itself
        r = subprocess.run([sys.executable, str(BASE / "scripts" / "run_studio.py")], cwd=BASE)
        stamp(outcome(r.returncode, "dispatch"))


if __name__ == "__main__":
    main()
