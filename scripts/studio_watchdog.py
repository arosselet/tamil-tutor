#!/usr/bin/env python3
"""
Studio watchdog — self-healing production (feature inbox 2026-07-17, commissioned
2026-07-18). Nothing Anna orders should wait for human hands: each awake tick
notices work the studio left undone and runs the EXISTING dispatch — it never
invents a pipeline of its own. Local only (cloud-never-renders).

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
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_studio import AUDIO_DIR, BASE, episode_paths, git_dirty, lint, next_mission
from sync_state import EPISODES_PATH, LEARNER_PATH, canon_payload, load_json

LOCK_PATH = BASE / ".studio.lock"


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


def soak_pending() -> bool:
    """True when the current soak order hasn't been carried by the newest
    episode — the same answer sync_state status prints as NOT YET PRODUCED."""
    soak = (load_json(LEARNER_PATH) or {}).get("soak_order") or {}
    items = canon_payload([w for w in soak.get("payload", []) if w])
    if not items:
        return False
    episodes = load_json(EPISODES_PATH) or {}
    newest = episodes[max(episodes, key=int)].get("words", []) if episodes else []
    return not all(w in newest for w in items)


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
        stamp(f"mission {n} scripted but unrendered — rendering now")
        r = subprocess.run([sys.executable, str(BASE / "scripts" / "render_audio.py"),
                            str(episode_paths(n)["script"]),
                            str(AUDIO_DIR / f"tier2_mission{n}.mp3")], cwd=BASE)
        stamp(f"render {'done' if r.returncode == 0 else f'failed (exit {r.returncode}) — retry next tick'}")
        return

    if soak_pending():
        stamp("soak order not yet produced — dispatching run_studio.py")
        lock.close()  # run_studio takes the same lock itself
        r = subprocess.run([sys.executable, str(BASE / "scripts" / "run_studio.py")], cwd=BASE)
        stamp(f"dispatch {'done' if r.returncode == 0 else f'failed (exit {r.returncode}) — retry next tick'}")


if __name__ == "__main__":
    main()
