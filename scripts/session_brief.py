#!/usr/bin/env python3
"""The session brief: what Anna reads at the start of a session.

`sync_state status` — the agent-facing load. Git sync banner, the local clock,
the soak order and its commission, what the last knock asked and whether it was
answered, the meters, and the slip block. It is a READ surface: nothing here
mutates state, which is the whole reason it is no longer inside the writer.

Not to be confused with `show_status.py`, which is Andrew's human dashboard —
bars, percentages, the episode list. Same underlying meters, different audience,
and they were checked for overlap before this split: there is very little.

Split out of `sync_state.py` 2026-08-04. This module sits ABOVE the brain rather
than beside it: it imports sync_state, slips and state_io, and sync_state
imports it back only inside `main`'s subcommand dispatch, where a deferred
import is ordinary practice rather than a cycle-dodge.
"""

import subprocess
from datetime import date, datetime

from slips import format_slip_block, slip_patterns
from state_io import (BASE, EPISODES_PATH, KNOCK_LOG_PATH, LEARNER_PATH,
                      LEXICON_PATH, LOCAL_TZ, SESSION_LOG_PATH, load_json,
                      local_today)
from sync_state import (RECOGNITION_LEVELS, canon_payload, compute_deck,
                        compute_engines, compute_floor, compute_status,
                        fires_today, is_pattern, is_unseen, split_payload)


def git_sync_counts() -> tuple[int, int] | None:
    """(behind, ahead) of origin/main after a fetch, or None when it can't be
    known (offline, no git, not a clone). The clone is ONE OF MANY writers —
    cloud Anna (knocks, judged replies, scheduled pushes) commits to main all
    day — so status must know whether it's reading today's story or yesterday's."""
    try:
        subprocess.run(["git", "fetch", "--quiet", "origin", "main"],
                       cwd=BASE, timeout=20, capture_output=True, check=True)
        out = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"],
            cwd=BASE, timeout=10, capture_output=True, text=True, check=True).stdout
        ahead, behind = (int(x) for x in out.split())
        return behind, ahead
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError):
        return None


def sync_banner(counts: tuple[int, int] | None) -> str | None:
    """The staleness gate's voice — printed ABOVE everything else in the digest
    so no agent can read state past it. 2026-07-15: a session opened on a clone
    14 commits behind and re-collected a paid field mission, missed the morning
    trailer, and taught past the story. Pull-before-read is design, not hygiene."""
    if counts is None:
        return ("⚠ SYNC UNKNOWN — couldn't reach origin. If this machine has been "
                "offline or idle, this digest may be stale; reconnect and `git pull "
                "--ff-only` before trusting it.")
    behind, ahead = counts
    lines = []
    if behind:
        lines.append(f"⛔ STATE IS STALE — {behind} commit{'s' if behind != 1 else ''} "
                     f"behind origin/main. STOP: run `git pull --ff-only` (or rebase if "
                     f"diverged) and re-run status. Everything below may be yesterday's story.")
    if ahead:
        lines.append(f"⚠ {ahead} local commit{'s' if ahead != 1 else ''} not on origin — "
                     f"push after the session close, or cloud Anna knocks on stale state.")
    return "\n".join(lines) or None


def knocks_since(klog: list, last_session: str | None, cap: int = 6) -> list[dict]:
    """Knock-log entries on/after the last logged session date, newest last —
    the between-session story the debrief alone can't carry (replies, fires,
    and trailers land on origin while the laptop sleeps)."""
    if not klog:
        return []
    entries = [k for k in klog if not last_session or k.get("date", "") >= last_session]
    return entries[-cap:]


def knock_line(k: dict) -> str:
    """One digest line per knock: what went out, what came back."""
    body = (k.get("body") or "").replace("\n", " ")
    if len(body) > 90:
        body = body[:87] + "…"
    if k.get("reply"):
        n = len(k.get("exchanges", [])) or 1
        reply = k["reply"].replace("\n", " ")
        if len(reply) > 40:
            reply = reply[:37] + "…"
        back = f"→ {n} repl{'ies' if n != 1 else 'y'}, last: '{reply}' ({k.get('reply_verdict', '?')})"
        fired = k.get("reply_fired_cold") or []
        if fired:
            back += f" · fired COLD: {', '.join(fired)}"
        # What Anna actually CORRECTED, not just that a reply happened. Until
        # 2026-07-30 this line stopped at the verdict, so a session opened knowing
        # Andrew replied and it was "hinted" with no idea what was wrong — the
        # correction sat in reply_line, read back only by the reveal-window and
        # deck-coverage scans. That is how the same recast could ship three times
        # in three weeks and look like normal progress.
        recasts = [x.get("reply_line", "") for x in k.get("exchanges", [])] or \
                  [k.get("reply_line", "")]
        recasts = [r.split(" · ")[0].strip() for r in recasts if r]
        if recasts:
            back += "\n      corrected: " + " | ".join(r[:88] for r in recasts[-2:])
    elif k.get("response"):
        back = f"→ {k['response']}"
    else:
        back = "→ (no response yet)"
    return f"  {k.get('date', '?')} [{k.get('modality', '?')}] {k.get('move', '?')} — \"{body}\" {back}"


def unpaid_trailer(klog: list, last_session: str | None) -> dict | None:
    """The newest knock, if it's a trailer whose promised teach no session has
    paid off yet (no session logged on/after its date). daily_session.md: an
    outstanding trailer's payoff IS the opening beat — this makes that rule
    data the agent can't overlook."""
    if not klog:
        return None
    k = klog[-1]
    if "trailer" not in (k.get("move") or "").lower():
        return None
    if last_session and last_session >= k.get("date", ""):
        return None
    return k


def cmd_status(_args):
    lexicon = load_json(LEXICON_PATH)
    learner = load_json(LEARNER_PATH)
    episodes = load_json(EPISODES_PATH) or {}
    if not learner:
        print("No learner.json found.")
        return

    banner = sync_banner(git_sync_counts())
    if banner:
        print(banner)
        print()

    # Anna is time-aware at inference: every load path reads this line, so "ping
    # me in an hour" / "tonight at 9" can become a real scheduled push (push_queue.py).
    # The zone is NAMED, not just abbreviated (2026-08-09): it is now a field in
    # learner.json, and a dial you can change is a dial you can forget to change.
    # "EDT" on the third morning in Coimbatore is the tell that the switch never
    # happened — but only if the line says which zone it thinks it is in.
    print(f"Now: {datetime.now(LOCAL_TZ):%a %Y-%m-%d %H:%M %Z} ({LOCAL_TZ.key})")
    print(f"Learner: {learner.get('learner')}")
    # No streak theatre — the honest signal is recency (a scoreboard that lies
    # teaches the player to ignore all the meters).
    slog = load_json(SESSION_LOG_PATH) or []
    last = slog[-1].get("date") if slog else None
    gap = (local_today() - date.fromisoformat(last)).days if last else None
    if last:
        gap_str = "today" if not gap else f"{gap} day{'s' if gap != 1 else ''} ago"
        print(f"Last logged session: {last} ({gap_str})")
    print(f"Status: {compute_status()}")  # live — the stored learner.json copy goes stale between updates
    print(f"Story so far: {learner.get('last_debrief', '')}")
    next_engine = learner.get("next_engine", "")
    if next_engine and lexicon:
        r = lexicon.get(next_engine, {})
        prod = r.get("production", "none")
        if prod != "cold":
            gloss = r.get("gloss", "")
            unseen = is_unseen(r)
            tag = "UNSEEN — teach first" if unseen else f"production: {prod}"
            print(f"Next engine: {next_engine} — {gloss}  [{tag}]")

    soak = learner.get("soak_order", {})
    if soak.get("payload") or soak.get("scene_seed"):
        items = canon_payload(soak.get("payload", []))
        soak_from = soak.get("from")
        soak_age = (local_today() - date.fromisoformat(soak_from)).days if soak_from else None
        stale = " ⚠ stale — chat hasn't fed the Director lately" if soak_age and soak_age > 7 else ""
        # The auto-drain answer, computed — not left to the agent's eye: has the
        # newest episode carried this payload yet? Resolved the same way the
        # watchdog resolves it (split_payload), because these two checks drive
        # the SAME dispatch from two doors — the session-open drain and the
        # cron. On 2026-07-23 only the cron's copy was fixed and this one kept
        # saying NOT YET PRODUCED, which would have re-armed the loop at the
        # next session. One rule, one resolver.
        resolved, unresolved = split_payload(soak.get("payload", []), lexicon)
        newest_words = (episodes[max(episodes, key=int)].get("words", [])
                        if episodes else [])
        channel = soak.get("channel") or "episode"
        lane = {"soak": "python scripts/render_soak.py",
                "drill": "python scripts/render_drill.py"}.get(
                    channel, "python scripts/run_studio.py")
        if channel == "episode":
            produced = bool(resolved) and all(w in newest_words for w in resolved)
        else:
            # The soak and drill lanes register no episode, so the newest-episode
            # compare can NEVER clear them — that is the 2026-07-23 re-dispatch
            # loop (M72/M73/M74 in one evening) with a new trigger. The lane that
            # rendered the order stamps it delivered (mark_soak_delivered); an
            # earlier version of this check read last_surfaced instead and hung
            # forever on a pre-lexicon payload word, which is the same loop.
            deliv = soak.get("delivered") or {}
            produced = (deliv.get("channel") == channel
                        and (deliv.get("at") or "") >= (soak_from or ""))
        if unresolved:
            drain = (f" · ⚠ payload unverifiable ({', '.join(unresolved)}) — fix the soak "
                     f"order; NOT dispatching on an item that can never match")
        elif produced:
            drain = f" · produced ✓ (the {channel} lane carried it — no dispatch needed)"
        else:
            drain = (f" · ⚠ NOT YET PRODUCED — dispatch `{lane}` in the background now "
                     f"(session-open auto-drain)")
        focus = f" · focus: {soak['focus']}" if soak.get("focus") else ""
        print(f"Soak order [{channel}]: [{', '.join(items)}] — {soak.get('scene_seed', '')}"
              f"{focus} (from {soak.get('from', '?')}){stale}{drain}")
    else:
        print("Soak order: ⚠ none set — chat hasn't handed anything to the Director.")

    # The between-session story — what the phone channel did while no laptop was
    # open. The debrief is Anna's memory of the last CLOSE; these are the doses
    # and replies SINCE. Re-collecting something listed here as answered is the
    # bug this section exists to prevent (2026-07-15).
    klog = load_json(KNOCK_LOG_PATH) or []
    since = knocks_since(klog, last)
    if since:
        print(f"\nKnocks since last logged session ({len(since)} shown — replies here are already judged; don't re-collect):")
        for k in since:
            print(knock_line(k))
    trailer = unpaid_trailer(klog, last)
    if trailer:
        body = (trailer.get("body") or "").replace("\n", " ")
        print(f"🎬 UNPAID TRAILER: \"{body}\" — its promised teach OPENS the session (pay it off in the first two exchanges).")

    # The error memory, ahead of the meters. A word being not-yet-cold says it
    # needs another rep; a repeated slip says HOW the rep keeps failing, which is
    # the difference between re-asking the same thing the same way and teaching
    # the thing that is actually broken.
    slip_block = format_slip_block(slip_patterns())
    if slip_block:
        print()
        for line in slip_block:
            print(line)
    print()

    if lexicon:
        by_level = {lvl: 0 for lvl in RECOGNITION_LEVELS}
        cold = hinted = 0
        for r in lexicon.values():
            if is_pattern(r):
                continue  # patterns are metered separately (Engines)
            by_level[r.get("recognition", "struggled")] = by_level.get(r.get("recognition", "struggled"), 0) + 1
            if r.get("production") == "cold":
                cold += 1
            elif r.get("production") == "hinted":
                hinted += 1
        print(f"Recognition — solid: {by_level['solid']}, comfortable: {by_level['comfortable']}, struggled: {by_level['struggled']}")
        print(f"Production — cold: {cold}, hinted: {hinted}")
        floor = compute_floor(lexicon)
        print(f"Viability floor: {floor['cleared']}/{floor['total']} recognized words fire cold ({floor['pct']:.0f}%)")
        engines = compute_engines(lexicon)
        if engines["total"]:
            print(f"Engines online: {engines['online']}/{engines['total']} patterns fire cold ({engines['pct']:.0f}%)")
        deck = compute_deck(lexicon)
        if deck["total"]:
            catch = f" · catch {deck['caught']}/{deck['catch_total']} solid" if deck["catch_total"] else ""
            print(f"Trip Deck: {deck['cleared']}/{deck['total']} deck phrases fire cold ({deck['pct']:.0f}%){catch} — the sprint headline")
            if deck["untouched"] or deck["catch_untouched"]:
                ear = f" + {deck['catch_untouched']} ear-only" if deck["catch_untouched"] else ""
                print(f"  ⚠ Coverage: {deck['untouched']} fire item(s){ear} never worked "
                      f"({deck['surv_untouched']} of them survival tier) — see the ticket for the register breakdown.")
                print("    ENGINEERING NUMBER — steers what Python picks; never narrated to Andrew "
                      "(a global deficit recited in a warm voice is guilt machinery, 2026-07-17).")
        print(f"Fired today: {fires_today()}")

    if episodes:
        recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:6]
        print("\nRecent episodes (immersion tank — no listen bookkeeping; each is a self-contained dose):")
        for m, ep in recent:
            dur = ep.get("duration_min")
            dur_str = f" ({dur:.1f} min)" if dur else ""
            print(f"  M{m}: {ep.get('title', m)}{dur_str}")
