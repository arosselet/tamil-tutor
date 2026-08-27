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
from state_io import (BASE, EPISODES_PATH, FEEDBACK_LOG_PATH, KNOCK_LOG_PATH,
                      LEARNER_PATH, LEXICON_PATH, LOCAL_TZ, SESSION_LOG_PATH,
                      load_json, local_today)
from state_io import canon_payload, is_unseen, soak_pending, split_payload
from sync_state import (RECOGNITION_LEVELS, compute_ear, compute_engines,
                        compute_machines,
                        compute_floor, compute_status, fires_today, is_pattern)


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
            cwd=BASE, timeout=10, capture_output=True, text=True, encoding="utf-8", check=True).stdout
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


# How the ALREADY ASKED block is bounded (2026-08-18, Andrew's call). The first
# cut printed the whole window — 50 rows, 27 of them single mentions — which is
# the accumulation shape the ticket's own budgets exist to stop, in a block added
# to prevent repetition. Sized to its siblings: `knocks_since` shows 6, the knock
# menu 6 fire + 2 catch.
ASK_BLOCK_CAP = 8
# Below this an item was asked ONCE inside the window, which is not a repeat —
# it is the case the cooldown is meant to allow.
ASK_REPEAT_FLOOR = 2


def _answered_targets(klog: list, days: int) -> set:
    """Targets that actually got a reply inside the window.

    The distinction the cooldown itself does not draw, and the one that matters
    most here: an ask that was ANSWERED tells you the item was worked, while an
    ask that drew silence tells you nothing — and silence is the case that
    quietly makes an item MORE eligible, since a reply-less ask never sets
    `last_surfaced` (`suggest_targets.recent_ask_counts`). Anna re-commissioning
    on the strength of an unanswered ask is the exact loop being closed."""
    cutoff = datetime.now(LOCAL_TZ).timestamp() - days * 86400
    out = set()
    for k in klog:
        if not k.get("acted", True) or not (k.get("reply") or k.get("exchanges")):
            continue
        try:
            ts = datetime.fromisoformat((k.get("timestamp") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.timestamp() >= cutoff and k.get("expected_target"):
            out.add(k["expected_target"])
    return out


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


HEARD_TAG = "[heard]"


def heard_in_the_wild(cap: int = 5) -> list[str]:
    """What Andrew heard OUT THERE and could not place — the highest-yield input
    this system gets, and until 2026-08-25 nothing read it back.

    THE CHANNEL ALREADY EXISTED; THE CONSUMPTION DID NOT. He has been producing
    these unprompted for months and they land in `feedback_log.json`, where the
    diagnosis pass reads them in `@build` — weeks later, if at all. On 2026-08-19
    he reported hearing "apora wandete" and not recognising it; BOTH words were
    already in the lexicon, one at `comfortable` after 22 sessions. That single
    line diagnosed the segmentation gap and proved the stored phonetics did not
    match real speech. No generated episode has produced evidence that good.

    So this is a READER, not a new store — no schema, no file, no meter. The
    convention is a `[heard]` prefix on an ordinary feedback note:

        python scripts/sync_state.py feedback "[heard] apora wandete"

    Anna's job is to DECODE it, never to grade it: what was it, why did it bounce,
    and were the words already his? A line whose words he owns is an ear problem
    and belongs to the eavesdrop dose; a line with a genuinely new word is a Teach
    Beat. Cleared by being worked in a session — Anna logs `[heard-worked] …` and
    it stops surfacing."""
    log = load_json(FEEDBACK_LOG_PATH) or []
    worked = {e.get("note", "")[len("[heard-worked]"):].strip().lower()
              for e in log if e.get("note", "").startswith("[heard-worked]")}
    body = [f"   {e.get('date', '?')} · {e['note'][len(HEARD_TAG):].strip()}"
            for e in log if e.get("note", "").startswith(HEARD_TAG)
            and e["note"][len(HEARD_TAG):].strip().lower() not in worked]
    # Returns the printable BLOCK, header included — the shape `format_slip_block`
    # already set, so the caller stays two lines and one owner holds the wording.
    #
    # This block does NOT claim the open (2026-08-26). It used to say "open the
    # session on one of these" while `unpaid_trailer` printed "its promised teach
    # OPENS the session" four lines above — two Python voices asserting the same
    # slot, with nothing ordering them, and neither one is the law. The open is
    # daily_session.md invariant 1; a wild line is ear work (invariant 2).
    return ["", "👂 HEARD IN THE WILD, NOT YET WORKED — work one of these into "
            "the session; decode it, never grade it. Close with "
            "`feedback \"[heard-worked] <line>\"`."] + body[-cap:] if body else []


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
    # A held channel must SAY it is held. Set silently, this bit looks exactly
    # like Anna choosing not to knock, and a forgotten one would read as her
    # going quiet for days with nothing anywhere to explain it.
    quiet_until = learner.get("quiet_until") or ""
    if quiet_until:
        lapsed = local_today() > date.fromisoformat(quiet_until)
        print(f"⏸ KNOCKS HELD through {quiet_until}"
              + (" — LAPSED, knocks resume; clear it with `--quiet-until \"\"`"
                 if lapsed else " (in transit — silence here is not a fade)"))
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
        _, unresolved = split_payload(soak.get("payload", []), lexicon)
        channel = soak.get("channel") or "episode"
        lane = {"soak": "python scripts/render_soak.py",
                "drill": "python scripts/render_drill.py"}.get(
                    channel, "python scripts/run_studio.py")
        # ONE RESOLVER (2026-08-27). The channel branch used to live here, in a
        # copy `state_io.soak_pending()` never learned — so the two doors onto the
        # same dispatch disagreed on any soak or drill order, and the one that was
        # wrong is the one the watchdog calls. Folded down into L0; this reads it.
        # `resolved` is non-empty by the time `produced` is consulted: an
        # unresolvable payload takes the branch below before this is read.
        produced = not soak_pending()
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
    # THE COOLDOWN, ON THE SURFACE ANNA ACTUALLY READS (2026-08-18).
    #
    # The knock lane has been guarded since KF-6: `due_menu_block` warns the
    # decider "asked/shown N× in last {ASK_COOLDOWN_DAYS}d". This brief — the
    # surface Anna reads when he writes the soak order, the campaign mission and
    # the slip medicine — never carried that signal at all, because it does not
    # import the selector. Three lanes choosing blind is how `இன்னொரு தடவ
    # சொல்லுங்க` reached six surfaces in eight days under four different move
    # names, which is KF-6's symptom coming back through the door KF-6 left open.
    #
    # ADVISORY BY CONSTRUCTION, and that is the honest limit: the soak order and
    # the campaign line are Anna's prose, so Python has no choke point to block
    # them the way the selector demotes a recently-asked row. This tells him; it
    # cannot stop him. The hard guard is still the knock lane's (KF-13's rule — say it in
    # the mandate, cap the blast radius in Python — is only half-satisfiable here).
    #
    # BOUNDED, BECAUSE THE FIRST CUT WAS NOT (2026-08-18, same day, found by
    # reading the block instead of the diff). It printed every row inside the
    # window: 50 of them on live state, 27 at a single mention — and widening
    # 3d → 7d in the same commit is what doubled it, so nobody saw the result.
    # A 50-line "do NOT re-commission these" list is not a guard, it is a wall
    # that buries the 6× and 5× rows which caused the incident. Every sibling
    # block here is capped for the same reason (`knocks_since` at 6, the knock
    # menu at 6 fire + 2 catch); this one simply had not been.
    #
    # ONE MENTION IS NOT A REPEAT. The floor is what the block is FOR: the
    # cooldown exists to catch an item reaching a second and third surface, and
    # an item asked once inside the window is the case it is meant to permit.
    # The count still comes from the unfiltered `recent_ask_counts` — the
    # selector's demotion is untouched and sees every row; this is the reading
    # surface, and only the reading is trimmed.
    from suggest_targets import ASK_COOLDOWN_DAYS, recent_ask_counts
    asked = recent_ask_counts(klog, lexicon or {})
    answered = _answered_targets(klog, ASK_COOLDOWN_DAYS)
    # Ties break UNANSWERED-first, then by key. Count alone leaves a long tie at
    # 2× — 15 of them on live state — and a cap has to cut somewhere: falling
    # through to the key alone would sort every `frame:` row ahead of every Tamil
    # one on codepoint order, which is arbitrary dressed as deterministic. An
    # unanswered repeat is the case this block exists for, so it goes on top; the
    # key is only the final tiebreak, and it is there so the order is stable.
    repeats = sorted(((w, n) for w, n in asked.items() if n >= ASK_REPEAT_FLOOR),
                     key=lambda kv: (-kv[1], kv[0] in answered, kv[0]))
    if repeats:
        print(f"\nALREADY ASKED (last {ASK_COOLDOWN_DAYS}d — do NOT re-commission these; "
              f"a repeat needs a genuinely new angle, or take another item):")
        for w, n in repeats[:ASK_BLOCK_CAP]:
            tail = "" if w in answered else " · UNANSWERED — silence is not a reason to re-ask"
            print(f"  - {w} — asked/shown {n}×{tail}")
        rest = len(repeats) - ASK_BLOCK_CAP
        if rest > 0:
            print(f"  (…{rest} more at {repeats[ASK_BLOCK_CAP][1]}× or fewer — not shown)")
    trailer = unpaid_trailer(klog, last)
    if trailer:
        body = (trailer.get("body") or "").replace("\n", " ")
        print(f"🎬 UNPAID TRAILER: \"{body}\" — its promised teach OPENS the session (pay it off in the first two exchanges).")

    # The error memory, ahead of the meters. A word being not-yet-cold says it
    # needs another rep; a repeated slip says HOW the rep keeps failing, which is
    # the difference between re-asking the same thing the same way and teaching
    # the thing that is actually broken.
    for line in heard_in_the_wild():
        print(line)

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
                # Patterns are metered separately — and on BOTH axes, which is
                # the 2026-08-16 correction. Engines reports the MOUTH (does the
                # machine fire cold); Machines heard reports the EAR (is it solid
                # on recognition). Before this line the ear axis was tracked on
                # every pattern record and surfaced on no meter at all: patterns
                # are skipped here, and compute_engines reads `production` only.
                # So the status line said "Engines online: 19/21 (90%)" while 12
                # of 26 machines Andrew produces cold were still `struggled` to
                # hear — the number he actually cares about, invisible for a year.
                # Ear-only patterns (direction=catch) are counted HERE and only
                # here; Engines excludes them by design, so this is the one meter
                # that sees the whole set.
                continue
            by_level[r.get("recognition", "struggled")] = by_level.get(r.get("recognition", "struggled"), 0) + 1
            if r.get("production") == "cold":
                cold += 1
            elif r.get("production") == "hinted":
                hinted += 1
        # The whole block is steering data, not narration material. The coverage
        # line has carried this warning alone since 07-17; it belongs on all of
        # them (2026-08-17) — Andrew is mastery-driven, and a performance
        # scoreboard read aloud to a learner like that predicts withdrawal when
        # the number is slow, which is what the 08-16 signal was.
        print("↓ ENGINEERING NUMBERS — they steer what Python picks. Never recite a "
              "fraction, percentage, countdown or streak at him (persona.md); the "
              "close names what got clearer.")
        print(f"Recognition — solid: {by_level['solid']}, comfortable: {by_level['comfortable']}, struggled: {by_level['struggled']}")
        print(f"Production — cold: {cold}, hinted: {hinted}")
        floor = compute_floor(lexicon)
        print(f"Viability floor: {floor['cleared']}/{floor['total']} recognized words fire cold ({floor['pct']:.0f}%)")
        engines = compute_engines(lexicon)
        if engines["total"]:
            print(f"Engines online: {engines['online']}/{engines['total']} patterns fire cold ({engines['pct']:.0f}%)")
        mach = compute_machines(lexicon)
        if mach["total"]:
            print(f"Machines heard: {mach['heard']}/{mach['total']} patterns solid on "
                  f"recognition WITH evidence ({mach['pct']:.0f}%) — PRIMARY STEER (2026-08-16)")
        ear = compute_ear(lexicon)
        if ear["total"]:
            print(f"Ear-only: {ear['caught']}/{ear['total']} solid on recognition "
                  f"— the win is comprehension; never forced to fire.")
            if ear["untouched"]:
                print(f"  ⚠ Coverage: {ear['untouched']} ear item(s) never worked — "
                      f"catch advances ONLY through eavesdrop. See the ticket for the "
                      f"register breakdown.")
                print("    ENGINEERING NUMBER — steers what Python picks; never narrated to Andrew "
                      "(a global deficit recited in a warm voice is guilt machinery, 2026-07-17).")
        print(f"Fired today: {fires_today()}")

    episodes = load_json(EPISODES_PATH) or {}
    if episodes:
        recent = sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:6]
        print("\nRecent episodes (immersion tank — no listen bookkeeping; each is a self-contained dose):")
        for m, ep in recent:
            dur = ep.get("duration_min")
            dur_str = f" ({dur:.1f} min)" if dur else ""
            print(f"  M{m}: {ep.get('title', m)}{dur_str}")
