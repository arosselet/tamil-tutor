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
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from openai import OpenAI

from mandates import OUTREACH_MANDATE, PHONETIC_REWRITE

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from render_audio import generate_segment_google, get_raw_mp3_frames, SILENCE_FRAME, clean_memo_for_tts
from render_chat import render_chat

OPENROUTER_BASE = "https://openrouter.ai/api/v1"   # OpenAI-compatible; one key, many models
MODEL = "anthropic/claude-sonnet-4.6"   # Andrew's default; fallback e.g. "google/gemini-2.5-flash"
ANNA_VOICE = "ta-IN-Chirp3-HD-Orus"     # pinned: Anna always sounds like the same someone
EAVESDROP_VOICE = "ta-IN-Chirp3-HD-Kore"  # pinned: the overheard aunty is one consistent voice too — ear-training tracks a speaker, and the trip's real voices are the aunties, not Anna
REPO = "arosselet/tamil-tutor"          # for the jsDelivr URL
KNOCKS_DIR = BASE / "published_audio" / "knocks"   # tracked, jsDelivr-served dir
KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
SESSION_LOG_PATH = BASE / "progress" / "session_log.json"

# ── The rails (hard, Python-enforced — Anna cannot cross these) ───────────────
# Andrew's local timezone — canonical in `state_io`, which reads it from
# `learner.json.timezone` (2026-08-09), so the waking window follows him abroad on
# a one-field edit and stays DST-correct at home. The cron ticks a UTC superset;
# this filters.
from state_io import LEARNER_PATH, LEXICON_PATH, LOCAL_TZ
WAKING_START_HOUR = 8      # inclusive, local
WAKING_END_HOUR = 21       # exclusive, local (last reach can land at 20:59)
MAX_REACHES_PER_DAY = 5    # a "reach" = a knock that actually fired (silence doesn't count)
MIN_GAP_HOURS = 3          # minimum spacing between reaches
NEXT_CHECK_CLAMP = (0.5, 24.0)   # Anna's self-set next_check is clamped to this many hours

MODALITIES = {"text", "audio", "challenge", "volley", "eavesdrop", "fielding", "grace", "silence"}
VOLLEY_SIZE = 4   # deck items per volley knock — one per exchange, chained by Python
                  # (3→4 2026-07-09: pace trailed 1.5 vs 1.8 needed; Andrew chose a bigger
                  # volley over deck tiering — next lever if it still trails is a 2nd volley)

# Lock-screen render budget. The mandate asks for ≤140; past ~160 iOS cuts the
# body and the dose dies unseen (2026-07-05 feedback). Warn-only — a trimmed
# dose is worse than a logged warning; the fix belongs in the composer.
BODY_BUDGET = 160


def over_budget(text: str, budget: int = BODY_BUDGET) -> bool:
    return len(text or "") > budget


TAMIL_RUN = re.compile(r"[஀-௿]+")


def rephrase_phonetic(body: str) -> str:
    """Ask the composer to transliterate its own body. The lexicon backstop below
    only resolves 8 of the 23 bodies this has historically hit — colloquial
    contractions (நல்லாருக்கு) are not keys — so the model, which knows how it
    spelt the thing, does the work and the lexicon only catches what it misses."""
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=300,
        messages=[{"role": "system", "content": PHONETIC_REWRITE},
                  {"role": "user", "content": body}])
    return (resp.choices[0].message.content or "").strip()


def to_phonetic(text: str, label: str = "body") -> str:
    """Transliterate a surface Andrew READS, if the composer left script on it.

    The composer does the work, not a lookup table: it knows how it spelt the
    thing, so ரொம்ப நல்லாருக்கு comes back "romba nallarukku" with the colloquial
    contraction intact. A lexicon substitution was tried first (2026-08-03) and
    retired the same morning — it resolved 8 of 23 real bodies, and on the ones
    it did hit it swapped Andrew's contraction for the dictionary key's
    phonetic, flattening exactly the Kongu register the constitution exists to
    protect. Andrew: "brittle, and it violates my colloquial contractions."

    Leftovers WARN and ship. He reads enough script to take contextual clues, so
    a leaked word costs him far less than a dose he never gets — the opposite of
    the eavesdrop case, where the whole dose was the broken part.
    """
    if not TAMIL_RUN.search(text):
        return text
    print(f"   ✎ {label} carries Tamil script — asking for phonetics…")
    out = rephrase_phonetic(text) or text
    if TAMIL_RUN.search(out):
        print(f"   ⚠ script survived the rewrite: {' '.join(TAMIL_RUN.findall(out))}")
    return out


# ── State helpers ─────────────────────────────────────────────────────────────

def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def is_fire(entry: dict) -> bool:
    """A reach that actually went out. Legacy entries (no 'acted') were all fires."""
    return entry.get("acted", True)


def local_date(ts_iso: str):
    try:
        return datetime.fromisoformat(ts_iso).astimezone(LOCAL_TZ).date()
    except (ValueError, TypeError):
        return None


def last_fire(klog: list) -> dict | None:
    fires = [k for k in klog if is_fire(k) and k.get("timestamp")]
    return fires[-1] if fires else None


def fires_today(klog: list, now_local_date) -> int:
    return sum(1 for k in klog if is_fire(k) and local_date(k.get("timestamp", "")) == now_local_date)


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

    if not (WAKING_START_HOUR <= now_local.hour < WAKING_END_HOUR):
        return False, f"quiet hours ({now_local:%H:%M} {now_local.tzname()})"

    klog = load_json(KNOCK_LOG_PATH) or []
    n_today = fires_today(klog, now_local.date())
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
    """Trailing consecutive FIRES that carried an ask (non-empty expected_target).
    The variety rule reads this: after 2, the next fire must be a no-ask dose or
    silence — Python counts; the mandate owns the rule (policy stays Anna's)."""
    n = 0
    for k in reversed([k for k in klog if is_fire(k)]):
        if k.get("expected_target"):
            n += 1
        else:
            break
    return n


LORE_COOLDOWN_DAYS = 7    # a converting format is a bet that paid off, not one to re-place
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
    n_today = fires_today(klog, now_local.date())
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
    if lore:
        ldate = local_date(lore.get("timestamp", ""))
        if ldate:
            age = (now_local.date() - ldate).days
            if age < LORE_COOLDOWN_DAYS:
                until = (ldate + timedelta(days=LORE_COOLDOWN_DAYS)).isoformat()
                lore_str = (f"\n  Lore-cooldown: “{lore.get('move', 'lore')}” fired {age}d ago — "
                            f"lore is SPENT until {until}; pick another move.")
            else:
                lore_str = (f"\n  Last lore: “{lore.get('move', 'lore')}” ({age}d ago) — a new "
                            f"lore dose must take a different vein than that one.")
    # Eavesdrop cadence — catch items advance ONLY through eavesdrop; surface a
    # warning when the cadence has lapsed so Anna doesn't keep skipping it.
    eavesdrop_str = ""
    try:
        from suggest_targets import deck_status
        _lex = load_json(LEXICON_PATH) or {}
        _deck = deck_status(_lex)
        _catch_pending = (_deck.get("catch_pending") or []) if _deck else []
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


def deck_due_list(max_fire: int = 6, max_catch: int = 2) -> str:
    """The sprint deck's due items in the selector's own order — coverage-first,
    recently-asked demoted, both owned by `deck_status` since 2026-07-25 (this
    module used to re-sort by its own ask counts, which let an asked-once
    SURVIVAL item fall below an unasked dessert one). `sync_state status` carries
    only the deck METER; this is the menu. Items never soaked anywhere are
    flagged UNSEEN — the mandate forbids cold-quizzing those (teach first,
    show dose)."""
    from suggest_targets import ASK_COOLDOWN_DAYS, deck_status  # lazy: keeps module import light
    from sync_state import is_unseen
    lex = load_json(LEXICON_PATH) or {}
    deck = deck_status(lex)
    if not deck or not deck["pending"]:
        return ""
    lines = ["DECK DUE (the sprint menu — expected_target should usually come from here):"]
    for t in deck["pending"][:max_fire]:
        state = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
        if is_unseen(lex.get(t["word"], {})):
            state += " · ⚠ UNSEEN — teach first (show dose), don't quiz"
        if t["asks"]:
            state += (f" · ⚠ asked/shown {t['asks']}× in last {ASK_COOLDOWN_DAYS}d — needs a genuinely "
                      f"new scene, or pick another item")
        lines.append(f"    [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{state}]")
    for t in deck["catch_pending"][:max_catch]:
        if t.get("pairs_with"):
            # A paired catch item is the one ear-only case he DOES answer: the
            # line is aimed at him and silence is the failure (2026-07-26).
            lines.append(f"    [pair] {t['word']} — {t['gloss'] or '[no gloss]'}  "
                         f"→ he answers: {t['pairs_with']} — {t['response_gloss'] or '[no gloss]'}  "
                         f"(play HER line, let him answer — never quiz the catch half alone)")
        else:
            lines.append(f"    [ear-only] {t['word']} — {t['gloss'] or '[no gloss]'}  "
                         f"(soak/eavesdrop dose only — never ask him to fire it)")
    return "\n".join(lines)


def volley_targets(n: int = VOLLEY_SIZE) -> list[dict]:
    """The BINDING item list for a volley knock — Python picks so deck coverage
    stays honest (Anna's taste concentrated reps on the same few headliners while
    50+ items got zero touches, 2026-07-08). The order is `deck_status`'s own —
    coverage-first, recently-asked demoted (2026-07-25); UNSEEN and ear-only
    items excluded (teach-first / never-fire laws)."""
    from suggest_targets import deck_status  # lazy: keeps module import light
    from sync_state import is_unseen
    lex = load_json(LEXICON_PATH) or {}
    deck = deck_status(lex)
    if not deck or not deck["pending"]:
        return []
    out = []
    for t in deck["pending"]:
        if is_unseen(lex.get(t["word"], {})):
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
    campaign + the deck's due menu + outcome memory + how much room the rails
    leave him right now."""
    out = subprocess.run([sys.executable, str(BASE / "scripts" / "sync_state.py"), "status"],
                         capture_output=True, text=True, encoding="utf-8")
    status = out.stdout.strip()
    klog = load_json(KNOCK_LOG_PATH) or []
    now = datetime.now(timezone.utc)
    parts = [status, campaign_block(), deck_due_list(), volley_block(),
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


def maybe_enqueue_schedule(decision: dict) -> Path | None:
    """If the decision planted a scheduled push, land it in the queue; it fires
    via the drain on the next Anna wake-up. Returns the queue path for the
    commit, or None.

    Carries `memo_script` through since 2026-07-24: a scheduled dose may be a
    VOICE dose, rendered by the drain at fire time. Dropping it here was half of
    why "audio at a time" was impossible — the other half was the drain's
    workflow having no TTS secret."""
    s = decision.get("schedule")
    if not isinstance(s, dict) or not s.get("at_local") or not s.get("body"):
        return None
    from push_queue import enqueue, QUEUE_PATH  # lazy: push_queue imports this module
    try:
        due = datetime.fromisoformat(s["at_local"])
        if due.tzinfo is None:
            due = due.replace(tzinfo=LOCAL_TZ)
    except ValueError:
        print(f"   ! schedule.at_local unparseable ({s.get('at_local')!r}) — dropped")
        return None
    if due <= datetime.now(timezone.utc):
        print(f"   ! schedule.at_local is in the past ({s['at_local']}) — dropped")
        return None
    enqueue(s["body"], due, expected_target=s.get("expected_target", ""),
            target_revealed=bool(s.get("target_revealed", True)),
            memo_script=(s.get("memo_script") or "").strip(),
            move=s.get("move", "scheduled follow-up"))
    return QUEUE_PATH


def parse_llm_json(text: str) -> dict:
    """The mandates say 'return ONLY a JSON object', but models occasionally
    wrap it in a code fence, prose, or a Python-style dict (2026-07-04: empty
    text killed a knock; 2026-07-07: single-quoted keys bypassed the {..} slice
    fallback — 'Expecting property name enclosed in double quotes: char 1';
    2026-07-13: prose BEFORE a ```json fence, with a literal `{noun}` frame
    gloss in the prose — the startswith fence-strip never fired and the {..}
    slice bit on `{noun}`).
    Strategy: strip a leading fence → json.loads → fenced block ANYWHERE
    (last one wins — it's the artifact) → {..} slice + json.loads →
    ast.literal_eval (handles single quotes + Python True/False/None).
    Print the raw text before any re-raise so the Action log shows WHAT came back."""
    import ast as _ast
    import re as _re
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        for block in reversed(_re.findall(r"```(?:json)?\s*\n(.*?)```", text, _re.DOTALL)):
            try:
                return json.loads(block.strip(), strict=False)
            except json.JSONDecodeError:
                continue
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            print(f"--- unparseable LLM response (no braces) ---\n{text}\n---")
            raise
        slice_ = text[start : end + 1]
        try:
            return json.loads(slice_, strict=False)
        except json.JSONDecodeError:
            # Python-style dict: single-quoted keys, True/False/None literals
            try:
                result = _ast.literal_eval(slice_)
                if isinstance(result, dict):
                    return result
            except (ValueError, SyntaxError):
                pass
            print(f"--- unparseable LLM response (all fallbacks failed) ---\n{text}\n---")
            raise


def parse_llm_response(resp) -> dict:
    """`parse_llm_json` for a raw API response — plus the one check the text
    alone CANNOT make.

    2026-08-05: the judge spent all 800 of its tokens deliberating in prose
    (which slip tag to reuse) and was cut off mid-word, before it had emitted a
    single brace. `parse_llm_json` did its job — "no braces", JSONDecodeError at
    char 0 — but that is byte-identical to the KF-7/KF-10 signature, where the
    JSON existed and the PARSER missed it. Those two failures want opposite
    fixes: a parser gap wants another fallback, a truncation wants a bigger
    budget, and adding a fallback for a truncation is pure motion. Only
    `finish_reason` can tell them apart, and it lives on the response, not the
    text — so the check has to sit here.

    Raised as ValueError so `decide()`'s retry loop re-rolls it (a second draft
    may simply be terser); `judge()` has no retry, so it surfaces at once."""
    c = resp.choices[0]
    if getattr(c, "finish_reason", None) == "length":
        raise ValueError(f"LLM response TRUNCATED at the max_tokens ceiling "
                         f"({len(c.message.content or '')} chars emitted, no JSON reached) "
                         f"— raise the budget at the CALL SITE; this is not a parser "
                         f"gap.\n--- truncated response ---\n{c.message.content}\n---")
    return parse_llm_json(c.message.content)


# Person nouns that can carry a tape's referent (2026-07-25). Substring matching, so
# the pulli-less stems are deliberate — "மருமக" catches மருமகள்/மருமகன், "மச்சான"
# catches மச்சான். A definite description counts: "அந்த வீட்டு பொண்ணு" is a referent.
REFERENT_NOUNS = (
    "அக்கா", "அண்ணா", "அண்ணன்", "தங்கச்சி", "தம்பி", "அம்மா", "அப்பா",
    "மாமா", "மாமி", "அத்தை", "சித்தி", "சித்தப்பா", "பெரியம்மா", "பெரியப்பா",
    "பாட்டி", "தாத்தா", "மச்சான", "மாப்பிள்ளை", "மருமக", "பொண்ணு", "பையன்",
    "பிள்ளை", "குழந்தை", "வாத்தியார்", "டாக்டர்",
)
REFERENT_WINDOW = 2  # paragraphs — a real call opens "ஹலோ, கேக்குதா?" before the news


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


def decide(digest: str, volley_menu: list | None = None) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    messages = [
        {"role": "system", "content": persona + "\n\n---\n\n" + OUTREACH_MANDATE},
        {"role": "user", "content": f"TODAY'S DIGEST:\n\n{digest}"},
    ]
    last_err: Exception | None = None
    for attempt in range(1, 4):
        resp = client.chat.completions.create(model=MODEL, max_tokens=1600, messages=messages)
        try:
            d = parse_llm_response(resp)
            if attempt > 1:
                print(f"   [ok] parsed on attempt {attempt}")
            break
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"   ⚠ parse failed (attempt {attempt}/3): {exc}")
            last_err = exc
    else:
        raise last_err  # all 3 attempts returned unparseable JSON
    return normalize_decision(d, volley_menu)


# ── Delivery plumbing (proven — preserved) ────────────────────────────────────

def load_env(path: Path):
    """Minimal .env -> os.environ (don't overwrite anything already set, e.g. CI secrets)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def render_memo(memo_script: str, out_path: Path, voice: str = ANNA_VOICE):
    import tempfile
    paras = [p.strip() for p in memo_script.split("\n\n") if p.strip()]
    audio = bytearray()
    tmp = tempfile.mkdtemp()
    for i, para in enumerate(paras):
        seg = await generate_segment_google(clean_memo_for_tts(para), voice, i, tmp)
        audio.extend(get_raw_mp3_frames(seg))
        audio.extend(SILENCE_FRAME * 25)  # ~0.6s breath between paragraphs
        os.remove(seg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    print(f"   rendered -> {out_path} ({len(audio)/1024:.0f} KB)")


# Append-only state arrays whose rows carry a genuinely unique key. Two writers
# appending between one checkout and its push collide TEXTUALLY on rows that do
# not disagree — git sees adjacent edits to one JSON array, not two independent
# appends. rel -> (identity key, sort key). Nothing else is auto-resolvable:
# session_log merges same-day rows by rule (2026-07-31) and feedback_log has no
# key at all, so a conflict in either is a real disagreement and must stay loud.
UNIONABLE = {"progress/push_queue.json": ("id", "due"),
             "progress/knock_log.json": ("timestamp", "timestamp")}

# Files with NO state of their own — each is a pure render of a source of truth
# above. Merging one is meaningless: there is nothing in it to disagree about,
# only two renders of two different logs. Reconciling them was also actively
# harmful — a chat.md conflict is what aborted run 30865736387 on 2026-08-04
# while knock_log.json beside it union-resolved cleanly, losing a judged
# exchange to a file that could have been regenerated in a millisecond.
# Rebuild from the merged source instead of merging the output.
DERIVED = {"progress/chat.md": render_chat}


def _union_conflict(rel: str) -> bool:
    """Resolve ONE conflicted append-only array by keeping every row from both
    sides. Returns False if anything is off-pattern, which keeps the abort loud.

    NOTE THE REBASE INVERSION: replaying our commit onto origin/main, stage :2 is
    UPSTREAM (what they pushed) and :3 is OURS. Getting this backwards silently
    drops the other writer's row, which is the failure this exists to prevent."""
    key, order = UNIONABLE[rel]

    def side(stage: int):
        r = subprocess.run(["git", "show", f":{stage}:{rel}"], cwd=BASE,
                           capture_output=True, text=True, encoding="utf-8")
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None

    theirs, ours = side(2), side(3)
    if not isinstance(theirs, list) or not isinstance(ours, list):
        return False
    merged, seen = [], set()
    for row in theirs + ours:
        if not isinstance(row, dict) or row.get(key) is None:
            return False       # a keyless row cannot be deduped; refuse rather than guess
        if row[key] in seen:
            continue
        seen.add(row[key])
        merged.append(row)
    merged.sort(key=lambda r: str(r.get(order, "")))
    (BASE / rel).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(["git", "add", rel], cwd=BASE, check=True)
    print(f"   ↳ merged {rel}: {len(theirs)} theirs + {len(ours)} ours -> {len(merged)}")
    return True


def _rerender_derived(rel: str) -> bool:
    """Resolve a DERIVED conflict by rebuilding the file from its source of truth,
    discarding both sides of the conflict. Ordering is load-bearing: this must run
    AFTER the union pass, which is what leaves the merged source in the working
    tree for the renderer to read.

    The renderer carries its OWN idea of the repo root (render_chat computes it
    from __file__), so it is only this function's source of truth by coincidence
    of both being the checkout. Assert the coincidence rather than trust it: a
    renderer writing somewhere else would otherwise leave the conflict markers
    in place and `git add` them, resolving the rebase by committing garbage —
    silent, and exactly the direction this file's teeth are supposed to face."""
    written = Path(DERIVED[rel]()).resolve()
    if written != (BASE / rel).resolve():
        print(f"   ⚠ {rel} renderer wrote {written}, not {BASE / rel} — refusing")
        return False
    subprocess.run(["git", "add", rel], cwd=BASE, check=True)
    print(f"   ↳ re-rendered {rel} from its source (not merged)")
    return True


def _rebase_onto_main() -> bool:
    """Land our commit on origin/main, union-resolving append conflicts and
    re-rendering derived ones. False if a conflict is real, with the rebase
    aborted so the tree is left clean.

    RETIRED, 2026-08-04: the `for _ in range(5)` this used to open with. Every
    path inside it returned or broke, so the body could not run twice — it read
    as a five-try retry and was a one-shot. We replay exactly one commit (CI
    checks out clean and commits once), so one pass is also all that is correct."""
    if subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"],
                      cwd=BASE).returncode == 0:
        return True
    stopped = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"],
                             cwd=BASE, capture_output=True, text=True, encoding="utf-8").stdout.split()
    unresolvable = [f for f in stopped if f not in UNIONABLE and f not in DERIVED]
    # Sources of truth first, then the files rendered FROM that merged result.
    if (stopped and not unresolvable
            and all(_union_conflict(f) for f in stopped if f in UNIONABLE)
            and all(_rerender_derived(f) for f in stopped if f in DERIVED)):
        subprocess.run(["git", "rebase", "--continue"], cwd=BASE,
                       env={**os.environ, "GIT_EDITOR": "true"}, check=True)
        return True
    print(f"   ⚠ unresolvable rebase conflict: {unresolvable or stopped or 'none reported'}")
    subprocess.run(["git", "rebase", "--abort"], cwd=BASE)
    return False


def commit_and_push(paths: list[Path], msg: str):
    rels = [str(p.relative_to(BASE)) for p in paths]
    subprocess.run(["git", "add", *rels], cwd=BASE, check=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=BASE, check=True)
    # main has three writers (knock CI, ack CI, the laptop) and this checkout goes
    # minutes stale during the LLM/TTS steps — land our commit on top of theirs.
    # A conflict here used to raise and lose the whole tick's work, decision
    # included (2026-07-31): two lanes appending to push_queue.json in one window
    # is routine, not a disagreement, so it is merged rather than surrendered.
    if not _rebase_onto_main():
        raise RuntimeError("rebase onto origin/main needs a human — tree left clean")
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE, check=True)


def refresh_feed() -> Path | None:
    """All audio lands on the podcast feed (2026-07-05): rebuild rss.xml so a
    dismissed audio memo stays findable. Feed polish must never kill the knock."""
    try:
        subprocess.run([sys.executable, str(BASE / "scripts" / "rebuild_rss.py")],
                       cwd=BASE, check=True)
        return BASE / "rss.xml"
    except Exception as e:
        print(f"   ⚠ rss rebuild failed ({e}) — continuing without feed update")
        return None


def jsdelivr_url(mp3: Path) -> str:
    rel = mp3.relative_to(BASE).as_posix()
    return f"https://cdn.jsdelivr.net/gh/{REPO}@main/{rel}"  # unique daily filename => always fresh


def in_waking_window(now: datetime | None = None) -> bool:
    """Is it inside Andrew's waking hours, local time? The ONE definition — the
    rails gate, the queue's deferral, and `push_to_phone` all read this."""
    now = now or datetime.now(timezone.utc)
    return WAKING_START_HOUR <= now.astimezone(LOCAL_TZ).hour < WAKING_END_HOUR


def push_to_phone(body: str, audio_url: str | None, knock_id: str = "",
                  requested: bool = False) -> bool:
    """Push a notification. audio_url is optional — a text/challenge/grace dose has none.
    knock_id = the knock's log-entry timestamp; it rides the notification's action_data
    and comes back with taps/replies so the judge grades the knock Andrew actually
    answered. Notifications stack (unique HA tag per knock, 2026-07-11) — last-fired
    correlation is only the fallback for id-less events.

    QUIET HOURS ARE ENFORCED HERE, at the one chokepoint every lane shares
    (2026-07-26). They used to be enforced per-lane: `rails_gate` for knocks, a
    hand-rolled hour compare in `run_studio`, `in_waking_window` in the queue —
    and NOTHING in `render_drill` or `render_soak`, which is how a drill reached
    the phone at 23:42. Three copies and two gaps is the same shape as the
    ordering-law drift found the same day; the fix is one owner, not a fourth copy.

    `requested=True` is the deliberate exemption: a reply Andrew's own tap asked
    for is not an interruption, and the rails exist to stop UNrequested reaches.
    Returns True if it pushed, False if quiet hours held it back."""
    if not requested and not in_waking_window():
        local = datetime.now(LOCAL_TZ)
        print(f"   phone: quiet hours ({local:%H:%M} {local.tzname()}) — not pushed. "
              f"The artifact is on the feed for the morning.")
        return False
    if audio_url:
        # Pre-warm the CDN: iOS fetches the attachment the instant the notification
        # lands, and a never-before-requested jsDelivr path can take seconds on its
        # first pull from GitHub — long enough for iOS to drop the inline player.
        try:
            with urllib.request.urlopen(audio_url, timeout=60) as r:
                r.read()
        except OSError as e:
            print(f"   ⚠ CDN pre-warm failed ({e}) — pushing anyway")
    webhook = os.environ["ANNA_PUSH_WEBHOOK_URL"]
    payload = {"title": "Anna", "text_content": body}
    if knock_id:
        payload["knock_id"] = knock_id
    if audio_url:
        payload["audio_url"] = audio_url
    req = urllib.request.Request(webhook, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    # Delivery is the one network hop we don't control end-to-end: a transient
    # DNS blip on the runner (2026-07-14, first occurrence) killed an otherwise
    # perfect run at the last step. Retry absorbs blips; the final failure still
    # raises so a genuinely unreachable webhook stays a red run, not a silent drop.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as r:
                print(f"   HA push -> HTTP {r.status}")
            return True
        except OSError as e:  # URLError, gaierror, timeouts
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                # The work network's FortiGate substitutes its own CA on this hop
                # (2026-07-28, Andrew: accepted, "not worth engineering around").
                # Retry cannot heal it and it must not fail the run — on 07-28 a
                # fully successful local render exited non-zero here, read as
                # total failure, and got re-run into a duplicate soak tape. The
                # dose is on the feed; only the lock-screen ping is lost.
                print("   phone: work-network TLS inspection strips this hop "
                      "(known, accepted 2026-07-28) — not pushed; the dose is on the feed.")
                return False
            if attempt == 2:
                raise
            wait = 5 * (attempt + 1)
            print(f"   ⚠ push attempt {attempt + 1} failed ({e}) — retrying in {wait}s")
            time.sleep(wait)


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
        paths = [log_decision(now, decision, acted=False), render_chat()]
        qp = maybe_enqueue_schedule(decision)
        if qp:
            paths.append(qp)
        commit_and_push(paths, f"Anna: silence ({decision.get('rationale','')[:50]})")
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

    path = log_decision(now, decision, acted=True, audio_url=audio_url, mp3=mp3)
    from sync_state import record_exposure
    extra_paths: list[Path] = []
    if record_exposure(knock_exposures(decision)):
        extra_paths.append(LEXICON_PATH)
    commit_paths = [path, render_chat()] if mp3 is None else [mp3, path, render_chat()]
    commit_paths.extend(extra_paths)
    if mp3 is not None:
        rss = refresh_feed()
        if rss:
            commit_paths.append(rss)
    qp = maybe_enqueue_schedule(decision)
    if qp:
        commit_paths.append(qp)
    print("4. commit + push…")
    commit_and_push(commit_paths, f"Anna reach ({decision['modality']}/{decision.get('move')})")
    print("5. notify…")
    push_to_phone(body, audio_url, knock_id=now.isoformat())
    print("\ndone — reached out & logged.")


if __name__ == "__main__":
    main()
