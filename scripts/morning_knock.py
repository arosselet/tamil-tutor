#!/usr/bin/env python3
"""
Anna's between-session outreach — an AGENT deciding whether/how/when to reach out,
not a fixed cron job. The schedule is the heartbeat (a tick + a safety net); the
POLICY is Anna's.

Division of labour:
  - Python owns the RAILS (hard, non-negotiable) and the TICK: waking hours, a
    daily cap, a minimum gap, and Anna's own `next_check` soft-gate. It cheaply
    skips a tick (no LLM) unless a reach is actually possible and due.
  - Anna owns the POLICY: at each wake he decides fire-or-silence, the move, the
    MODALITY (text micro-dose / audio memo / challenge / volley / eavesdrop tape /
    grace / silence), his own
    next check-in time (self-pacing), and logs a one-line rationale so his choices
    stay inspectable — and so he can learn from what worked.

The reward Anna optimises for is ANDREW SHOWING UP (chat sessions / returns), not
taps. A tap is a weak "it landed" signal; an ignored streak means back off or
change the approach. READ-ONLY on the learning brain: outreach never logs reps or
advances the floor.

  python scripts/morning_knock.py --dry-run   # gate + decide + render only (no commit/push/notify)
  python scripts/morning_knock.py             # full: rails gate, then Anna decides & (maybe) reaches out
  python scripts/morning_knock.py --force      # skip the rails gate (manual one-off)

Secrets (in .env locally; GitHub Actions secrets in CI):
  OPENROUTER_API_KEY     — the one-shot that makes the decision (one key, any model)
  ANNA_PUSH_WEBHOOK_URL  — the Home Assistant webhook
GCP TTS auth comes from ADC locally / a service-account secret in CI (only needed
when Anna chooses the audio modality).
"""
import argparse
import asyncio
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from mandates import OUTREACH_MANDATE

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from language import ANNA_VOICE, EAVESDROP_VOICE, REFERENT_NOUNS
# `render_memo` and the four TTS primitives it composed left for `memo.py` on
# 2026-09-04. They were here because the knock spoke first; `push_queue` and
# `reply_common` call it too, and a lane cannot be a foundation for its peers.
from memo import render_memo
from push_queue import maybe_enqueue_schedule
from publish import (BODY_BUDGET, KNOCKS_DIR,
                     commit_and_push, jsdelivr_url, load_env, over_budget,
                     publish, push_to_phone)
from writer import (BOOL, INT, STR, STRS, ask_json, executor_name, nullable, obj,
                    to_phonetic, voice_canon)

# ── The rails (hard, Python-enforced — Anna cannot cross these) ───────────────
# The BUDGET itself — the waking window, the daily cap, the min gap, and the
# counter that reads them off the knock log — moved to `rails.py` on 2026-09-04,
# because `push_queue` obeys the same numbers and was importing them from THIS
# FILE. A lane cannot be a foundation for its peers. What stays here is
# `rails_gate` below: whether to wake ANNA is the knock lane's own policy, and no
# other lane asks it.
from rails import (MAX_REACHES_PER_DAY, MIN_GAP_HOURS, WAKING_END_HOUR,
                   WAKING_START_HOUR, in_waking_window, last_fire, reaches_today)
from state_io import (KNOCK_LOG_PATH, LEARNER_PATH, LEXICON_PATH, LOCAL_TZ,
                      SESSION_LOG_PATH, STANCES, is_fire, is_give, load_json,
                      local_date)

NEXT_CHECK_CLAMP = (0.5, 24.0)   # Anna's self-set next_check is clamped to this many hours

MODALITIES = {"text", "audio", "challenge", "volley", "eavesdrop", "fielding", "grace", "silence"}
VOLLEY_SIZE = 4   # menu items per volley knock — one per exchange, chained by Python
                  # (3→4 2026-07-09: pace trailed 1.5 vs 1.8 needed; Andrew chose a bigger
                  # volley over tiering — next lever if it still trails is a 2nd volley)



# ── The rails gate (no LLM — cheap; runs every tick) ──────────────────────────

def rails_gate(force: bool, now: datetime | None = None) -> tuple[bool, str]:
    """Should this tick WAKE Anna to decide? True only if a reach is genuinely
    possible now: inside waking hours, under the daily cap, past the min gap, and
    past Anna's own next_check. Everything here is deterministic and free — the
    LLM is only spent when a reach is actually on the table. `now` is injectable
    for testing (defaults to the real UTC clock)."""
    if force:
        return True, "forced"
    now = now or datetime.now(timezone.utc)
    now_local = now.astimezone(LOCAL_TZ)

    # The transit bit (2026-08-10, Andrew). Set for a flight, cleared on landing.
    # It sits FIRST because it is the only rail that means "he cannot receive
    # this at all": Apple queues exactly one push for an unreachable phone, so a
    # dose fired into a flight overwrites the last one and is destroyed. Skipping
    # here — before the LLM, before anything is logged — is the whole point: no
    # row is written, so the unanswered stretch can never reach the ignore-streak
    # and be read as fading. Deleting these four lines removes the feature.
    quiet_until = (load_json(LEARNER_PATH) or {}).get("quiet_until") or ""
    if quiet_until and now_local.date() <= date.fromisoformat(quiet_until):
        return False, f"quiet_until {quiet_until} — in transit, not fading"

    # CALL IT, don't re-derive it (2026-09-04). This was a hand-rolled
    # `WAKING_START_HOUR <= now_local.hour < WAKING_END_HOUR` — the exact compare
    # `smoke/publish.py` already forbids in four other lanes, and this file was
    # the one lane missing from that list. Two copies of a host rule is how a
    # host rule drifts: a weekend clause added to `in_waking_window` would have
    # reached the queue, the drill, the soak and push_to_phone, and silently
    # missed the knock gate.
    if not in_waking_window(now):
        return False, f"quiet hours ({now_local:%H:%M} {now_local.tzname()})"

    klog = load_json(KNOCK_LOG_PATH) or []
    n_today = reaches_today(klog, now_local.date())
    if n_today >= MAX_REACHES_PER_DAY:
        return False, f"daily cap reached ({n_today}/{MAX_REACHES_PER_DAY})"

    lf = last_fire(klog)
    if lf:
        gap = (now - datetime.fromisoformat(lf["timestamp"])).total_seconds() / 3600
        if gap < MIN_GAP_HOURS:
            return False, f"min-gap not met ({gap:.1f}h < {MIN_GAP_HOURS}h)"

    # Anna's own soft gate — his chosen cadence. Set on the most recent decision.
    if klog:
        nc = klog[-1].get("next_check")
        if nc and now < datetime.fromisoformat(nc):
            return False, f"Anna's next_check not due (set for {nc})"

    return True, f"eligible ({n_today}/{MAX_REACHES_PER_DAY} today) — waking Anna to decide"


# ── The digest Anna reads (state + outcome memory + his remaining room) ────────

def outcome_memory(klog: list, now: datetime) -> str:
    """The learning substrate: recent reaches with their outcomes, framed around
    the real reward (did Andrew SHOW UP?), plus the ignore-streak. This is what
    lets Anna adapt instead of repeating a rigid policy."""
    slog = load_json(SESSION_LOG_PATH) or []
    last_session = slog[-1].get("date") if slog else None
    fires = [k for k in klog if is_fire(k)]

    lines = []
    for k in fires[-5:]:
        modality = k.get("modality", "audio")
        move = k.get("move", "—")
        if k.get("reply"):
            # a typed reply carries real signal (incl. "busy"/"back off") — surface
            # it verbatim so Anna reads intent, not just a tap/no-tap count.
            detail = f'replied ({k.get("reply_verdict", "?")}): "{k["reply"][:60]}"'
        elif k.get("response"):
            detail = f"tapped ({k['response']})"
        else:
            detail = "no-tap"
        # the ask itself, not just the move name — move names hid same-ask
        # repeats from the variety law ('evlo naal' fired 5× in 4 days under
        # differently-named moves, 2026-07-06)
        ask = k.get("expected_target") or "no-ask"
        body_head = (k.get("body") or "").replace("\n", " ")[:48]
        lines.append(f"    {k.get('date','?')} · {modality}/{move} · "
                     f"asked: {ask} · “{body_head}…” · {detail}")

    # Ignore streak = trailing reaches with no tap AND no session since.
    streak = 0
    for k in reversed(fires):
        after = local_date(k.get("timestamp", ""))
        session_after = last_session and after and last_session >= after.isoformat()
        if k.get("response") or session_after:
            break
        streak += 1

    since = "never" if not last_session else last_session
    verdict = ""
    if streak >= 3:
        verdict = (f"  ⚠ {streak} reaches in a row led to no session and no tap — the current "
                   "approach isn't converting. Give space, or change the move/modality entirely.")
    elif last_session and (now.astimezone(LOCAL_TZ).date() - date.fromisoformat(last_session)).days >= 3:
        verdict = "  ⚠ No session in 3+ days — cold-start risk; a low-friction reply-in-tamizh ask may re-open the loop."

    body = "\n".join(lines) if lines else "    (no reaches logged yet)"
    return (f"OUTREACH MEMORY (reward = Andrew showing up in chat, NOT taps):\n"
            f"  Last chat session: {since}\n"
            f"  Recent reaches (newest last):\n{body}\n"
            f"  Ignore-streak: {streak} unanswered reaches.{verdict}")


def demand_streak(klog: list) -> int:
    """Trailing consecutive FIRES that wanted something — an ASK (Tamil back now)
    or a LURE (his attendance later). The variety rule reads this: after 2, the
    next fire must be a GIVE or silence — Python counts; the mandate owns the
    rule (policy stays Anna's).

    The reading moved from "carries an expected_target" to `state_io.is_give` on
    2026-09-05; that docstring holds the evidence and the reason."""
    n = 0
    for k in reversed([k for k in klog if is_fire(k)]):
        if is_give(k):
            break
        n += 1
    return n


LORE_COOLDOWN_DAYS = 7    # a converting format is a bet that paid off, not one to re-place
# THE FLOOR THE CEILING NEVER HAD (2026-08-31, Andrew: "it's become kind of muddied /
# missing"). Every tick printed "lore is SPENT"; no tick ever printed "lore is overdue",
# so the only pressure on this dose pushed one way. Eavesdrop has had both rails since
# 07-25 — a cooldown AND a cadence — and lore was the asymmetry left behind.
#
# 10 IS MEASURED, NOT CHOSEN. Gaps between fired lore doses after the cooldown landed:
# 8, 6, 8, 8 — then 15, then a 3-fire month. The 6-8 band is the system self-regulating,
# and it is the band Andrew endorsed lore in ("I genuinely enjoy that little dose of
# lore… high density learning", 2026-07-28). So the floor sits ABOVE the whole healthy
# band: at 10 it cannot fire during normal operation, and every warning it does print is
# real drift. A floor inside the band would be a weekly quota wearing a cadence's
# clothes — which is the 07-11 mistake ("engagement is evidence, not a mandate"), and a
# warning that fires constantly is noise by construction and gets walked past.
LORE_CADENCE_DAYS = 10
EAVESDROP_CADENCE_DAYS = 3  # catch items need an eavesdrop dose at least this often


def last_lore(klog: list) -> dict | None:
    """Most recent fired lore dose ('lore' in the move label — the log's naming
    convention). Lore had no format-level guard: it fired four days running
    (2026-07-07→10), every one a frame etymology, because engagement with the
    format read as a mandate to repeat it (2026-07-11). Python counts; the
    mandate owns the rule — same seam as demand_streak."""
    for k in reversed([k for k in klog if is_fire(k)]):
        if "lore" in (k.get("move") or "").lower():
            return k
    return None


def last_eavesdrop(klog: list) -> dict | None:
    """Most recent fired eavesdrop dose. Catch items advance ONLY through this
    modality; the cadence gate enforces a floor frequency."""
    for k in reversed([k for k in klog if is_fire(k)]):
        if k.get("modality") == "eavesdrop":
            return k
    return None


def remaining_room(klog: list, now: datetime) -> str:
    now_local = now.astimezone(LOCAL_TZ)
    n_today = reaches_today(klog, now_local.date())
    lf = last_fire(klog)
    gap_str = "no reach yet today"
    if lf:
        gap = (now - datetime.fromisoformat(lf["timestamp"])).total_seconds() / 3600
        gap_str = f"last reach {gap:.1f}h ago"
    streak = demand_streak(klog)
    streak_str = f"\n  Demand-streak: {streak} consecutive fires carried an ask"
    if streak >= 2:
        streak_str += " — the variety rule says the next fire must be a NO-ASK dose or silence."
    lore_str = ""
    lore = last_lore(klog)
    if lore is None:
        lore_str = ("\n  ⚠ Lore: NEVER fired — a word with a story has more retrieval "
                    "hooks than a word with a scene. Take a no-ask lore dose when one fits.")
    else:
        ldate = local_date(lore.get("timestamp", ""))
        if ldate:
            age = (now_local.date() - ldate).days
            if age < LORE_COOLDOWN_DAYS:
                until = (ldate + timedelta(days=LORE_COOLDOWN_DAYS)).isoformat()
                lore_str = (f"\n  Lore-cooldown: “{lore.get('move', 'lore')}” fired {age}d ago — "
                            f"lore is SPENT until {until}; pick another move.")
            elif age >= LORE_CADENCE_DAYS:
                lore_str = (f"\n  ⚠ Lore: OVERDUE — last was “{lore.get('move', 'lore')}” "
                            f"{age}d ago, past the {LORE_CADENCE_DAYS}d cadence. It is a "
                            f"no-ask dose and takes a DIFFERENT vein than that one.")
            else:
                lore_str = (f"\n  Last lore: “{lore.get('move', 'lore')}” ({age}d ago) — a new "
                            f"lore dose must take a different vein than that one.")
    # Eavesdrop cadence — catch items advance ONLY through eavesdrop; surface a
    # warning when the cadence has lapsed so Anna doesn't keep skipping it.
    eavesdrop_str = ""
    try:
        from suggest_targets import ear_targets
        _lex = load_json(LEXICON_PATH) or {}
        _catch_pending = ear_targets(_lex)["pending"]
        if _catch_pending:
            le = last_eavesdrop(klog)
            if le is None:
                eavesdrop_str = (f"\n  ⚠ Eavesdrop: {len(_catch_pending)} catch item(s) pending, "
                                 f"NEVER fired — catch advances ONLY through eavesdrop; "
                                 f"this is the highest-value move right now.")
            else:
                ld = local_date(le.get("timestamp", ""))
                age = (now_local.date() - ld).days if ld else EAVESDROP_CADENCE_DAYS
                if age >= EAVESDROP_CADENCE_DAYS:
                    eavesdrop_str = (f"\n  ⚠ Eavesdrop: {len(_catch_pending)} catch item(s) pending, "
                                     f"last eavesdrop {age}d ago (cadence: every {EAVESDROP_CADENCE_DAYS}d) — "
                                     f"consider eavesdrop this tick.")
    except Exception:
        pass  # never let a cadence check kill a reach

    return (f"RAILS (hard — stay well inside; silence is free):\n"
            f"  Waking window {WAKING_START_HOUR}:00–{WAKING_END_HOUR}:00 {now_local.tzname()}; "
            f"now {now_local:%H:%M}.\n"
            f"  Reaches today: {n_today}/{MAX_REACHES_PER_DAY}. Min gap {MIN_GAP_HOURS}h ({gap_str})."
            f"{streak_str}{lore_str}{eavesdrop_str}")


def due_menu_block(max_fire: int = 6, max_catch: int = 2) -> str:
    """The pool's due items in the selector's own order — tier-first,
    coverage-first, recently-asked demoted. `sync_state status` carries the
    meters; this is the MENU. Items never soaked anywhere are flagged UNSEEN —
    the mandate forbids cold-quizzing those (teach first, show dose).

    Was `deck_due_list`, reading `deck_status` (2026-07-25 → 2026-08-18). Same
    order, same ownership rule — this module does not re-sort, because when it
    did an asked-once SURVIVAL item could fall below an unasked dessert one. What
    changed is the population: the 83-row container retired and the ordering it
    carried (`register` → tier) moved onto the rows, so the menu is now drawn
    from the whole pool instead of from a set with an expiry date."""
    from suggest_targets import ASK_COOLDOWN_DAYS, drill_menu, ear_targets
    lex = load_json(LEXICON_PATH) or {}
    menu = drill_menu(lex, max_n=max_fire)
    if not menu:
        return ""
    lines = ["DUE MENU (expected_target should usually come from here):"]
    for t in menu:
        state = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
        if t["unseen"]:
            state += " · ⚠ UNSEEN — teach first (show dose), don't quiz"
        if t["retest"]:
            state += f" · GOING DARK, {t['staleness']}d silent since it was hinted"
        if t["asks"]:
            state += (f" · ⚠ asked/shown {t['asks']}× in last {ASK_COOLDOWN_DAYS}d — needs a genuinely "
                      f"new scene, or pick another item")
        lines.append(f"    [{t['kind']} · {t['tier']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{state}]")
    # ONE OF EACH, WHERE BOTH EXIST (2026-08-25). The ear queue widened past the
    # catch tag the same day and the machines hold reserved seats at its head, so a
    # straight slice handed BOTH knock slots to machines — and the paired catch
    # drills (the maami's "eat more", answered) stopped reaching the knock lane
    # entirely. That is the starvation the reservation was built to end, running
    # the other way. The queue owns the ORDER; two slots is this caller's budget,
    # and how it spends them is its own call.
    _ear = ear_targets(lex)["pending"]
    _machines = [t for t in _ear if not t.get("ear_only")]
    _catch = [t for t in _ear if t.get("ear_only")]
    _picked = [q[0] for q in (_machines, _catch) if q][:max_catch]
    _picked += [t for t in _ear if t not in _picked][:max_catch - len(_picked)]
    for t in _picked:
        if t.get("pairs_with"):
            # A paired catch item is the one ear-only case he DOES answer: the
            # line is aimed at him and silence is the failure (2026-07-26).
            lines.append(f"    [pair] {t['word']} — {t['gloss'] or '[no gloss]'}  "
                         f"→ he answers: {t['pairs_with']} — {t['response_gloss'] or '[no gloss]'}  "
                         f"(play HER line, let him answer — never quiz the catch half alone)")
        elif t.get("ear_only"):
            lines.append(f"    [ear-only] {t['word']} — {t['gloss'] or '[no gloss]'}  "
                         f"(soak/eavesdrop dose only — never ask him to fire it)")
        else:
            # A MACHINE, NOT A CATCH ROW (2026-08-25). The ear queue widened past the
            # catch tag, and this line used to be the only thing it could say — which
            # would have told Anna never to fire a frame Andrew fires cold every
            # session. The catch law is a property of the ROW, never of the block.
            lines.append(f"    [ear-behind] {t['word']} — {t['gloss'] or '[no gloss]'}  "
                         f"(he FIRES this; the EAR is what is behind — eavesdrop/soak it, "
                         f"and a fire here earns no ear credit)")
    return "\n".join(lines)


def volley_targets(n: int = VOLLEY_SIZE) -> list[dict]:
    """The BINDING item list for a volley knock — Python picks so coverage stays
    honest (Anna's taste concentrated reps on the same few headliners while 50+
    items got zero touches, 2026-07-08). The order is `drill_menu`'s own —
    tier-first, coverage-first, recently-asked demoted (2026-07-25); UNSEEN and
    ear-only items excluded (teach-first / never-fire laws).

    IT SEARCHES A BOUNDED SLICE, and that bound is deliberate (2026-08-18). It
    used to walk every pending deck row — 35 of them — looking for VOLLEY_SIZE
    non-UNSEEN items; it now sees `drill_menu`'s FOCUS_SIZE head. Drawing deeper
    would be the obvious "fix" and is the wrong one: the focus set IS the
    dense-rotation budget, so a volley reaching past it would drill words the
    budget says are not in rotation.

    So this returns SHORT when the head is unseen-heavy, and `volley_block`
    emits nothing below two — which is correct, not a failure: a focus set that
    is mostly UNSEEN wants a teach/show dose, not a cold blitz. Measured against
    live state the head is nowhere near that (28 unseen rows, diluted among 125
    tied at never-surfaced, so ~1-5 of any 12), and a freshly seeded set returns
    zero under the old code too — every row is unseen and nothing is quizzable
    yet. If a volley ever goes missing on a day that looks drillable, this bound
    is the first place to look, and the answer is a teach dose, not a bigger
    slice."""
    from suggest_targets import drill_menu  # lazy: keeps module import light
    lex = load_json(LEXICON_PATH) or {}
    out = []
    for t in drill_menu(lex):
        if t["unseen"]:
            continue  # UNSEEN — teach first (show dose), never cold-quiz
        out.append({"target": t["word"], "gloss": t.get("gloss", "")})
        if len(out) == n:
            break
    return out


def volley_block() -> str:
    vt = volley_targets()
    if len(vt) < 2:
        return ""
    lines = ["VOLLEY TARGETS (binding, in this order — Python picked the due items; "
             "you write the English situations if you fire a volley):"]
    lines += [f"    {i}. {t['target']} — {t['gloss'] or '[no gloss]'}"
              for i, t in enumerate(vt, 1)]
    return "\n".join(lines)


def campaign_block() -> str:
    """The live campaign — the named week and its through-line in profile.md
    (contract in protocol/daily_session.md → The Campaign). Cloud Anna steers by
    it: trailers pitch its next chapter, doses are framed by its story. It names
    no items — the ticket owns those (2026-07-26). Only a live session writes it,
    and exactly one such heading exists: the two-heading split that shipped on
    07-24 fed three days of knocks a won-and-closed campaign (smoke s17)."""
    try:
        text = (BASE / "progress" / "profile.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    # Match the HEADING, never its title. The title is Anna's prose and she
    # renames it with every campaign — "The Last Week Before, and the Month
    # During" (2026-08-04) missed the exact string this used to require, and
    # six days of knocks steered with no campaign at all, silently. The
    # contract fixes the prefix; everything after it belongs to her.
    marker = "## The Campaign"
    heading = next((l for l in text.splitlines() if l.startswith(marker)), None)
    if heading is None:
        return ""
    body = text.split(heading, 1)[1].split("\n## ", 1)[0]
    # Drop the standing contract blockquote; the mandate already carries the rules.
    body = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith(">")).strip()
    if not body or "no campaign live" in body:
        return ""
    return "CAMPAIGN (the live week plan — steer by it):\n" + body[:1500]


def build_digest() -> str:
    """Everything Anna needs to make a policy call: learning state + the live
    campaign + the due menu + outcome memory + how much room the rails
    leave him right now."""
    out = subprocess.run([sys.executable, str(BASE / "scripts" / "sync_state.py"), "status"],
                         capture_output=True, text=True, encoding="utf-8")
    status = out.stdout.strip()
    klog = load_json(KNOCK_LOG_PATH) or []
    now = datetime.now(timezone.utc)
    parts = [status, campaign_block(), due_menu_block(), volley_block(),
             outcome_memory(klog, now), remaining_room(klog, now)]
    return "\n\n".join(p for p in parts if p)


# ── The decision (LLM — only reached when the rails gate opened) ───────────────

def knock_exposures(decision: dict) -> list[str]:
    """The DECLARED exposure of a knock — what Tamil actually went out the door
    (2026-07-26 ledger law; never mined from the dose's prose):
      - `introduces` keys (teaching doses show the item — the 2026-07-16 gap),
      - a revealed `expected_target` (the body/memo printed the Tamil itself),
      - an eavesdrop's target (the tape SPEAKS it; target_revealed is false
        there only because the ask is comprehension, not because it was hidden).
    A hidden target is an ASK — spend, not exposure — and stamps nothing."""
    keys = list(decision.get("introduces") or [])
    target = (decision.get("expected_target") or "").strip()
    if target and (decision.get("target_revealed") or decision.get("modality") == "eavesdrop"):
        keys.append(target)
    return keys




# The nouns themselves are LANGUAGE (`language.REFERENT_NOUNS`, moved 2026-09-03) —
# 26 rows of Tamil kinship culture that a port replaces wholesale. The WINDOW is
# not: how much of a tape's opening must name its subject is a fact about how a
# phone call is structured, and it stays with the lane that reads it.
REFERENT_WINDOW = 2  # paragraphs — a real call opens with a greeting before the news


def tape_names_a_referent(memo_script: str) -> bool:
    """Does the tape name who it is about, up front? The gossip opener
    (frame:youknow-la — 'நம்ம X இருக்காங்கல…') exists to do this; a tape that skips
    it hearsays about an unnamed அவங்க and cannot be asked 'who?'.

    A FLOOR, not a proof of answerability — the window is what discriminates. On the
    four tapes on record (07-16/19/22/25) only the 07-25 one fails, and only within
    the opening: it does say அக்கா later, but as the SOURCE of the reassurance, not
    the subject who came, so a whole-tape check would have passed the exact tape that
    left Andrew asking 'who came?' with no answer in the audio."""
    opening = "\n\n".join((memo_script or "").split("\n\n")[:REFERENT_WINDOW])
    return any(noun in opening for noun in REFERENT_NOUNS)


def normalize_decision(d: dict, volley_menu: list | None = None) -> dict:
    """Guard the decision's JSON into the shape Python relies on. For a volley,
    Anna's asks are zipped with PYTHON's binding targets (volley_targets) —
    the model writes the situations, never the picks — and the body is composed
    from ask 1 so the coherence law holds by construction."""
    d["modality"] = d.get("modality") if d.get("modality") in MODALITIES else "text"
    if d["modality"] == "silence":
        d["act"] = False
    lo, hi = NEXT_CHECK_CLAMP
    try:
        d["next_check_hours"] = max(lo, min(hi, float(d.get("next_check_hours", 3))))
    except (TypeError, ValueError):
        d["next_check_hours"] = 3.0
    # Reply-judge fields. Default target_revealed=True: if the decision didn't say,
    # assume the Tamil was shown, so a reply caps at "hinted" — the cold axis stays honest.
    d["expected_target"] = (d.get("expected_target") or "").strip()
    d["target_revealed"] = bool(d.get("target_revealed", True))
    d["introduces"] = [k for k in (d.get("introduces") or []) if isinstance(k, str) and k.strip()]
    # AN ABSENCE MUST BE LOUD, and the DIRECTION of the default is the whole
    # point: "give" would silently reset the demand brake, which is the bug this
    # field exists to fix, so an unlabelled dose costs Anna a break rather than
    # buying her a free one. Silence is exempt — it never reaches the streak.
    if d.get("stance") not in STANCES:
        if d.get("act"):
            print(f"   ⚠ dose declared no stance ({d.get('stance')!r}) — counting it as ASK")
        d["stance"] = "ask"
    d["schedule"] = d.get("schedule") if isinstance(d.get("schedule"), dict) else None
    if d["modality"] == "eavesdrop":
        # A defective eavesdrop is REFUSED, never degraded to text (2026-08-01,
        # enforcing the twice-signalled 07-28 ruling "wire real audio or do not
        # run them"): the body is a drift question about a tape, so a text
        # degrade pushes a question whose audio never ships — the exact broken
        # promise Andrew reported twice. A lost dose is cheaper than a wrong
        # one; the next tick tries fresh. Referent rule unchanged from 07-25:
        # hearsay about an unnamed அவங்க has no recoverable WHO.
        if not (d.get("memo_script") or "").strip():
            print("   ⚠ eavesdrop with no tape — refused (text eavesdrops are "
                  "banned; the drift question's audio would never ship)")
            d["modality"], d["act"] = "silence", False
        elif not tape_names_a_referent(d["memo_script"]):
            print("   ⚠ eavesdrop tape names nobody in its opening — refused "
                  "(the drift question would have no answer in the audio)")
            d["modality"], d["act"] = "silence", False
        else:
            d["target_revealed"] = False  # the tape plays Tamil, but the ask is comprehension
    if d["modality"] == "fielding":
        if (d.get("memo_script") or "").strip():
            d["target_revealed"] = False  # the question plays Tamil; the ANSWER was never shown
        else:
            d["modality"] = "text"  # no question to render — plain dose
    if d["modality"] == "volley":
        asks = [a.strip() for a in (d.get("volley_asks") or [])
                if isinstance(a, str) and a.strip()]
        items = [{"target": t["target"], "ask": a}
                 for t, a in zip(volley_menu or [], asks)]
        if len(items) >= 2:
            d["volley"] = items
            d["expected_target"] = items[0]["target"]
            d["target_revealed"] = False  # volley asks are English situations by contract
            d["notification_body"] = f"⚡ volley 1/{len(items)} — {items[0]['ask']}"
        else:
            d["modality"] = "text"  # no binding menu / no usable asks — plain dose
    return d


# The knock's own top-level shape, declared beside the lane that reads it — the
# 2026-08-23 rule, and not a candidate for centralising: a generic
# `{"type": "object"}` is what made `claude -p` answer in an envelope and a lane
# render an empty dose with every instrument green. Keys mirror OUTREACH_MANDATE.
# `volley_asks` and `schedule` WERE absent on purpose, and the reasoning had a
# false premise — corrected 2026-09-05. The old note ended "undeclared keys still
# pass through untouched", which is true of the API path and FALSE of the agent
# path: `claude -p --json-schema` deletes what `obj()` did not name (see
# `writer.obj`, and the six fields lost to it this month). So leaving a
# conditional key undeclared did not make it optional, it made it impossible —
# every volley ask and every scheduled push this lane composed was being dropped
# before Python could read it. `writer.nullable` is how "or null" is said in a
# place both executors respect. Retires two KNOWN_GAPS licences in smoke s82.
DECIDE_SCHEMA = obj(act=BOOL, modality=STR, move=STR, stance=STR,
                    introduces=STRS, notification_body=STR, memo_script=STR,
                    expected_target=STR, target_revealed=BOOL,
                    next_check_hours=INT, rationale=STR,
                    volley_asks=nullable(STRS),
                    # No `memo_script` here: the outreach mandate's scheduled dose
                    # is text, and only the reply lane offers one a voice.
                    schedule=nullable(obj(
                        at_local=STR, body=STR, expected_target=STR,
                        target_revealed=BOOL, move=STR)))


def decide(digest: str, volley_menu: list | None = None) -> dict:
    """Ask cloud Anna what to do this tick. The executor is the HOST's choice, not
    this lane's (`writer.ask_json`, 2026-08-23) — which is what stops a local
    `--force` from billing cash against a subscription already paid for. In
    Actions `have_agent()` is False, so the API branch runs exactly as before.

    RETIRED HERE: this function's own three-attempt parse-retry loop. `ask_json`
    carries the identical contract — re-roll a bad draw, never re-roll a
    truncation (`parse_llm_response` names the ceiling, and that is not a parser
    gap) — so a second copy was one more per-lane invariant free to drift."""
    canon = voice_canon()
    print(f"   [decide] {executor_name()}")
    d = ask_json(canon + "\n\n---\n\n" + OUTREACH_MANDATE,
                 f"TODAY'S DIGEST:\n\n{digest}", DECIDE_SCHEMA, answer_tokens=1600)
    return normalize_decision(d, volley_menu)


# ── Delivery plumbing (proven — preserved) ────────────────────────────────────


# ── Orchestration ─────────────────────────────────────────────────────────────

def log_decision(now: datetime, decision: dict, *, acted: bool,
                 audio_url: str | None = None, mp3: Path | None = None) -> Path:
    """Record every WAKE — fire or silence — so the self-schedule (next_check) and
    the rationale persist across stateless CI runs, and the outcome memory grows."""
    klog = load_json(KNOCK_LOG_PATH) or []
    entry = {
        "date": now.date().isoformat(),
        "timestamp": now.isoformat(),
        "acted": acted,
        "modality": decision.get("modality"),
        "move": decision.get("move"),
        "rationale": decision.get("rationale"),
        "next_check": (now + timedelta(hours=decision["next_check_hours"])).isoformat(),
    }
    if acted:
        entry["body"] = decision.get("notification_body")
        entry["expected_target"] = decision.get("expected_target", "")
        entry["stance"] = decision.get("stance", "ask")   # what it wanted; is_give reads this
        entry["target_revealed"] = decision.get("target_revealed", True)
        if decision.get("volley"):
            # the reply judge walks this queue deterministically (knock_reply.py)
            entry["volley"] = decision["volley"]
            entry["volley_next"] = 1
        if audio_url:
            entry["audio_url"] = audio_url
            entry["memo_script"] = decision.get("memo_script", "")  # the reply judge reads what was heard
        if mp3:
            entry["mp3"] = str(mp3.relative_to(BASE))
    klog.append(entry)
    KNOCK_LOG_PATH.write_text(json.dumps(klog, ensure_ascii=False, indent=2), encoding="utf-8")
    return KNOCK_LOG_PATH


def main():
    ap = argparse.ArgumentParser(description="Anna's agentic between-session outreach")
    ap.add_argument("--dry-run", action="store_true",
                    help="gate + decide + render only; no commit, push, or notification")
    ap.add_argument("--force", action="store_true",
                    help="skip the rails gate entirely — waking hours, cap, gaps (manual one-off)")
    args = ap.parse_args()

    load_env(BASE / ".env")

    should_wake, reason = rails_gate(args.force)
    if not should_wake:
        print(f"[rails] skip — {reason}")
        return
    print(f"[rails] wake — {reason}")

    now = datetime.now(timezone.utc)
    print("1. digest…")
    digest = build_digest()
    print("2. Anna decides…")
    decision = decide(digest, volley_targets())
    print(f"   → act={decision.get('act')} modality={decision['modality']} "
          f"move={decision.get('move')!r} next_check={decision['next_check_hours']}h")
    print(f"   rationale: {decision.get('rationale')}")

    acting = bool(decision.get("act")) and decision["modality"] != "silence"

    if not acting:
        print("   Anna chose silence.")
        if args.dry_run:
            print("[dry-run] would log the silence + next_check; stopping.")
            return
        # The silence tick writes a log entry and reaches nobody, so: no audio,
        # no feed rebuild, no push. chat.md still follows the log — `publish`
        # owns that now, and a silence is exactly the tick most likely to be
        # forgotten by a hand-built list.
        commit_and_push(*publish(
            [log_decision(now, decision, acted=False),
             maybe_enqueue_schedule(decision)],
            f"Anna: silence ({decision.get('rationale','')[:50]})"))
        print("done — silence logged, next_check set.")
        return

    # The body is READ; memo_script below is SPOKEN and keeps its script.
    # Written back into `decision` so the log and chat.md record what he was
    # actually sent, not what the model first wrote.
    decision["notification_body"] = body = to_phonetic(
        decision.get("notification_body", ""))
    mp3 = None
    audio_url = None
    if decision["modality"] in ("audio", "eavesdrop", "fielding"):
        print("3. render…")
        mp3 = KNOCKS_DIR / f"knock_{now.strftime('%Y-%m-%dT%H-%M')}.mp3"
        # fielding speaks in the family voice too — the question comes AT him, not from Anna
        voice = EAVESDROP_VOICE if decision["modality"] in ("eavesdrop", "fielding") else ANNA_VOICE
        asyncio.run(render_memo(decision.get("memo_script", ""), mp3, voice))
        audio_url = jsdelivr_url(mp3)

    print("\n--- notification body ---\n" + body + "\n")
    if over_budget(body):
        print(f"   ⚠ body is {len(body)} chars (budget {BODY_BUDGET}) — the lock screen will cut it")

    if args.dry_run:
        print(f"[dry-run] would push ({decision['modality']}) + log; stopping.", mp3 or "")
        return

    # LOG and EXPOSURE are this lane's — only it knows what it wrote and what went
    # out the door. Everything after them is the shared tail, and the lane stops
    # spelling it out: `publish` owns feed -> commit -> push (2026-08-23).
    path = log_decision(now, decision, acted=True, audio_url=audio_url, mp3=mp3)
    from sync_state import record_exposure
    exposed = record_exposure(knock_exposures(decision))
    print("4. commit + push…")
    commit_and_push(*publish(
        [path, LEXICON_PATH if exposed else None,
         maybe_enqueue_schedule(decision)],
        f"Anna reach ({decision['modality']}/{decision.get('move')})", mp3=mp3))
    print("5. notify…")
    push_to_phone(body, audio_url, knock_id=now.isoformat())
    print("\ndone — reached out & logged.")


if __name__ == "__main__":
    main()
