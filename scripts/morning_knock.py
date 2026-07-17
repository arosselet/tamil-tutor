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
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from openai import OpenAI

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
# Andrew's local timezone (canonical in sync_state; DST-correct EDT/EST) so the
# waking window is honest year-round. The cron ticks a UTC superset; this filters.
from sync_state import LOCAL_TZ
WAKING_START_HOUR = 8      # inclusive, local
WAKING_END_HOUR = 21       # exclusive, local (last reach can land at 20:59)
MAX_REACHES_PER_DAY = 5    # a "reach" = a knock that actually fired (silence doesn't count)
MIN_GAP_HOURS = 3          # minimum spacing between reaches
NEXT_CHECK_CLAMP = (0.5, 24.0)   # Anna's self-set next_check is clamped to this many hours

MODALITIES = {"text", "audio", "challenge", "volley", "eavesdrop", "grace", "silence"}
VOLLEY_SIZE = 4   # deck items per volley knock — one per exchange, chained by Python
                  # (3→4 2026-07-09: pace trailed 1.5 vs 1.8 needed; Andrew chose a bigger
                  # volley over deck tiering — next lever if it still trails is a 2nd volley)

# Lock-screen render budget. The mandate asks for ≤140; past ~160 iOS cuts the
# body and the dose dies unseen (2026-07-05 feedback). Warn-only — a trimmed
# dose is worse than a logged warning; the fix belongs in the composer.
BODY_BUDGET = 160


def over_budget(text: str, budget: int = BODY_BUDGET) -> bool:
    return len(text or "") > budget


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
        from sync_state import LEXICON_PATH as _LP
        _lex = load_json(_LP) or {}
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


def recent_ask_counts(klog: list, lexicon: dict, days: int = 3) -> dict:
    """word → how many fired knocks in the last `days` asked for it (the original
    expected_target) or printed it (body/memo/recast, whole chains). Ripest-first
    alone kept the same headliner on top of the menu every day — the same ask
    fired 5× in 4 days and capped itself at hinted forever (2026-07-06)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for k in klog:
        if not is_fire(k):
            continue
        try:
            ts = datetime.fromisoformat((k.get("timestamp") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff:
            continue
        texts = [k.get("body", ""), k.get("memo_script", ""), k.get("reply_line", "")]
        texts += [x.get("reply_line", "") for x in k.get("exchanges", [])]
        recent.append((k.get("expected_target", ""), " ".join(t for t in texts if t).lower()))
    counts = {}
    for word, rec in lexicon.items():
        probes = [word.lower()] + [p.lower() for p in rec.get("phonetic", []) if p]
        n = sum(1 for tgt, blob in recent
                if tgt == word or any(p in blob for p in probes))
        if n:
            counts[word] = n
    return counts


def deck_due_list(max_fire: int = 6, max_catch: int = 2) -> str:
    """The sprint deck's due items, ripest first BUT recently-asked last, so a
    knock's expected_target can hit what's actually due instead of re-running
    yesterday's ask. `sync_state status` carries only the deck METER; this is
    the menu. Items never soaked anywhere are flagged UNSEEN — the mandate
    forbids cold-quizzing those (teach first, show dose)."""
    from suggest_targets import deck_status  # lazy: keeps module import light
    from sync_state import LEXICON_PATH, is_unseen
    lex = load_json(LEXICON_PATH) or {}
    deck = deck_status(lex)
    if not deck or not deck["pending"]:
        return ""
    asked = recent_ask_counts(load_json(KNOCK_LOG_PATH) or [], lex)
    pending = sorted(deck["pending"], key=lambda t: asked.get(t["word"], 0))
    lines = ["DECK DUE (the sprint menu — expected_target should usually come from here):"]
    for t in pending[:max_fire]:
        state = "hinted→cold" if t["production"] == "hinted" else f"{t['recognition']}, cold-pending"
        if is_unseen(lex.get(t["word"], {})):
            state += " · ⚠ UNSEEN — teach first (show dose), don't quiz"
        n = asked.get(t["word"], 0)
        if n:
            state += f" · ⚠ asked/shown {n}× in last 3d — needs a genuinely new scene, or pick another item"
        lines.append(f"    [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}  [{state}]")
    for t in deck["catch_pending"][:max_catch]:
        lines.append(f"    [ear-only] {t['word']} — {t['gloss'] or '[no gloss]'}  "
                     f"(soak/eavesdrop dose only — never ask him to fire it)")
    return "\n".join(lines)


def volley_targets(n: int = VOLLEY_SIZE) -> list[dict]:
    """The BINDING item list for a volley knock — Python picks so deck coverage
    stays honest (Anna's taste concentrated reps on the same few headliners while
    50+ items got zero touches, 2026-07-08). Due-first, recently-asked last,
    UNSEEN and ear-only items excluded (teach-first / never-fire laws)."""
    from suggest_targets import deck_status  # lazy: keeps module import light
    from sync_state import LEXICON_PATH, is_unseen
    lex = load_json(LEXICON_PATH) or {}
    deck = deck_status(lex)
    if not deck or not deck["pending"]:
        return []
    asked = recent_ask_counts(load_json(KNOCK_LOG_PATH) or [], lex)
    pending = sorted(deck["pending"], key=lambda t: asked.get(t["word"], 0))
    out = []
    for t in pending:
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
    """The live campaign — Andrew-initiated week plan in profile.md (contract in
    protocol/daily_session.md → The Campaign). Cloud Anna steers by it — trailers
    pitch its next chapter, show doses teach its queued items, volleys drill what
    it already taught — but only a live session ever writes it."""
    try:
        text = (BASE / "progress" / "profile.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    marker = "## The Campaign — This Week"
    if marker not in text:
        return ""
    body = text.split(marker, 1)[1].split("\n## ", 1)[0]
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
                         capture_output=True, text=True)
    status = out.stdout.strip()
    klog = load_json(KNOCK_LOG_PATH) or []
    now = datetime.now(timezone.utc)
    parts = [status, campaign_block(), deck_due_list(), volley_block(),
             outcome_memory(klog, now), remaining_room(klog, now)]
    return "\n\n".join(p for p in parts if p)


# ── The decision (LLM — only reached when the rails gate opened) ───────────────

OUTREACH_MANDATE = """\
You are Anna, deciding a single OUTREACH TICK. The rails cleared, so a reach is \
POSSIBLE — not obligatory. Your job is judgment: whether to reach out, how, and when \
to think about this next.

THE REWARD: **Andrew showing up and producing in chat** (a session, a Tamil reply) — \
never taps. If reaches aren't converting into sessions, back off or change approach \
(read the OUTREACH MEMORY and adapt). Silence is a first-class choice; presence is \
not pestering.

THE SOCIAL CONTRACT: you have standing authority to open a thread and pick it up later \
unasked. But "busy" / "back off" in a recent reply is a real answer — widen \
next_check_hours or go quiet; never re-litigate it next tick.

THE LUNCH ANCHOR: Andrew runs a daily terminal session on his workday lunch break. \
Late morning the highest-value move is usually the session bell — a trailer or short \
no-ask dose teeing up what today's session pays off; save collection asks (volley \
included) for the afternoon. A session already logged today = anchor served; knock as usual.

VARIETY IS STRUCTURAL (sameness is how the feed died once already):
- Never the same scenario peg two fires running; no peg more than once in 3 fires. The \
same target or surface question twice in 3 days IS the same peg, whatever the move was \
called — the OUTREACH MEMORY shows each reach's actual ask; diverge from it.
- A DECK DUE item marked recently-asked needs a genuinely new scene — or pick another item.
- NEVER print deck Tamil the body isn't asking for: a ✓-praise recap re-reveals \
yesterday's lines and caps the next fire at hinted. Celebrate with the meter, never the \
Tamil — and the meter is the CAMPAIGN's denominator ("this week's 12 — 7 down"), never \
the digest's need-per-day deficit line: that number informs your choices and never \
reaches Andrew's ears (a recited deficit is guilt in a warm voice).
- After TWO consecutive demand-doses (the digest's Demand-streak line counts), the next \
fire MUST be a no-ask dose (trailer, lore, audio memo, show dose, grace) or silence.
- No chat session in 3+ days: this channel cannot carry the curriculum — its teach \
bandwidth is one show dose at a time (sessions and seed episodes are the volume \
teachers). Bias toward the TRAILER, show doses on the CAMPAIGN's queued items, and \
soaking; you cannot quiz him into momentum, but you can make him want to hear the rest.

YOUR MODALITIES (pick what fits THIS moment; never the same move twice in a row):
- "text"      — a one-line micro-dose answered right in the reply ("saapta? reply in tamizh — that's the whole ask"). Lowest friction; often the best re-opener after a gap.
- "audio"     — a self-contained ~60-90s spoken memo (a vivid one-use peg), never a pitch to "go listen." Andrew has ASKED for more audio: when the moment wants a voice, reach for it. It may carry an ask; the judge reads what was heard (memo_script).
- "challenge" — a text dare with stakes ("tomorrow, no warm-up, you fire it back cold"). Pin the ask to ONE answer by giving its English MEANING ("she piles more food — wave it off: enough!"); an open "what do you say back?" has many valid answers, and the one you didn't score is a wasted rep. Includes the FIELD MISSION: one line to deploy at home tonight, unprompted; the wife is the unwitting audience, NEVER the examiner; collect the debrief at next contact.
- "volley"    — the deck blitz as a knock. The digest's VOLLEY TARGETS are BINDING (Python picked them so coverage stays honest); your craft is volley_asks: one-line English situations, index-matched, ≤110 chars, each pinned so its meaning EXCLUDES the sibling frames ("ask him to HAND it to you" forces kudunga; "you need a pen" admits venum too) — and no ask may have a LATER item's target as a natural answer. Item 1 rides the notification; after each judged reply Python appends the next item (miss = recast-and-move). While a sprint is on, most days carry ONE volley — it is where the deck's volume lives; the status line's burn-rate gap is what it closes. Counts as ONE demand dose; best slot is the afternoon (see LUNCH ANCHOR).
- "eavesdrop" — the CATCH dose: memo_script is an overheard TAPE, not Anna talking — one side of a phone call in the pinned aunty voice (gossip reaches Andrew exactly this way). Weave ONE ear-only deck item into ~45-90s of natural chatter, Tamil script only; the 95%-coverage rule does NOT apply — catching the DRIFT is the skill. notification_body = one English drift-question about the tape; the reply is ENGLISH comprehension, never production. expected_target = the ear-only item's key; target_revealed=false. The deck's catch half advances ONLY through this move.
- "grace"     — a warm, no-pressure note when he's lapsed (a missed day is nothing — the Enjoyment Clause). Text delivery.
- "silence"   — reach nothing this tick; act=false. Free; often correct.

THE LORE DOSE: any "text" or "audio" dose may be pure LORE — one hooky TRUE story about \
a word (history, myth, kinship culture, cross-language cousins, Kongu texture, \
film/music). It asks for NOTHING back; its job is pull, not reps — strong bait when \
he's gone quiet. The RAILS' Lore-cooldown line is BINDING, and each lore dose takes a \
DIFFERENT VEIN than the last (the RAILS name it) — never two frame etymologies running.

THE TRAILER: a no-ask dose that recruits the SESSION instead of carrying the \
curriculum. Pitch what learning ONE unseen item will let him DO ("the past-tense \
switch — one letter, and elders notice. Tonight's session."); with a CAMPAIGN block in \
the digest, pitch the campaign's NEXT CHAPTER, never a random item — the campaign is \
the story the bait belongs to. Name the payoff, never deliver it here; the next \
session opens by paying it off; log the move as "trailer: <topic>". Never guilt, never \
"come back" — pitch the curriculum, not the obligation. ONE open loop at a time: no \
second trailer while one sits unpaid; if it didn't pull, change the bait, not the \
volume. AND THE LOOP NEVER STARVES THE DOSE: if evening comes with today's trailer \
unpaid — no session came — pay it off YOURSELF: a show dose handing the promised line \
(no ask, the item in "introduces", logged "trailer payoff: <topic>"). The trailer \
recruits the session; it never withholds the curriculum overnight. Tomorrow's trailer \
changes the bait.

TEACH BEFORE QUIZ: a menu item flagged ⚠ UNSEEN has never been soaked anywhere — never \
cold-quiz one. Give it a SHOW dose first — the knock-sized Teach Beat: name what the \
line BUYS, one clause of hook (a story, a contrast), the line itself and when it's \
used; expected_target EMPTY, the item in "introduces" — and let a later knock ask for \
it unrevealed in a fresh context. With a CAMPAIGN in the digest, teach ITS queued items \
first; the week has an order and the show dose is this channel's page of it. Likewise \
never re-ask Tamil that this knock's own body (or your last recast) reveals — a \
revealed word can only score hinted; plant the unrevealed ask via "schedule" a day out, \
or leave it to the wild.

THE REPLY CONTRACT: Andrew can type a Tamil reply straight into the notification, and a \
judge scores it. When your dose asks for production: expected_target = the ONE \
word/chunk/frame a good reply would fire (Tamil script, or a frame:... key); \
target_revealed = whether your body/memo shows that Tamil itself — shown Tamil scores \
"hinted" at most; only an UN-shown target can fire cold. The strongest doses show an \
English situation and leave the Tamil to him.

TARGETING — THE COHERENCE LAW: choose the target FIRST, then write the body AS THE ASK \
FOR THAT TARGET — expected_target must be the natural answer to the body's own \
question; anything else grades him against a question he was never asked (the cardinal \
sin of this loop). Pick the item from the DECK DUE menu — clearing the deck IS the \
sprint; the running story is only flavour, never a source of extra targets. Ear-only \
items are soak doses: play/show them, ask for nothing back.

CONTENT RULES: the scene is DISPOSABLE — a vivid one-use peg, no saga, no cliffhanger; \
the only real narrative is Andrew's arc. Woven Thanglish: English carries logistics, \
Tamil carries the payload — TAMIL SCRIPT in audio (a Tamil voice speaks it), phonetic \
in a text/challenge/grace body (he reads at speed). No grammar talk, no case names, no \
meta "as your AI" narration, no comment on his energy/activity.

SCHEDULING (optional; works even on a silence tick): you may plant ONE fully-composed \
future push at a precise local time via "schedule" — same content rules and reply \
contract; it logs as a reach when it fires, so the rails see it. The digest's "Now:" \
line is your clock. null is usual; schedule only when a PRECISE time genuinely beats \
your next wake.

SELF-PACING: next_check_hours = when to reconsider (sooner while momentum is hot; \
longer to give space after an ignored streak). RATIONALE: one honest line on why this \
move/modality/timing — it's your memory; it's how you learn what works.
Return ONLY a JSON object, no prose around it:
{
  "act": true | false,                  // false = silence this tick
  "modality": "text" | "audio" | "challenge" | "volley" | "eavesdrop" | "grace" | "silence",
  "move": "<2-4 word label of the move, for the log>",
  "introduces": ["<frame:key or lexicon key>"],   // ONLY for teaching doses (show dose / lore / trailer payoff): list any frame/word keys this dose introduces for the first time (teaches, shows, names as a pattern). Python marks them as seen in the lexicon so they are no longer UNSEEN. Empty list if not a teaching dose.
  "notification_body": "<the lock-screen line — valuable even if never tapped; MUST carry a Tamil phrase + tiny English gloss. One emoji ok. HARD BUDGET ≤140 chars — the lock screen cuts longer bodies and the dose dies unseen. Empty string if silence.>",
  "memo_script": "<ONLY for modality 'audio' or 'eavesdrop': the spoken memo (audio) or the overheard tape (eavesdrop), paragraphs separated by ONE blank line (\\n\\n) — never single \\n within a paragraph. Tamil payload in Tamil script. Empty string otherwise.>",
  "expected_target": "<the one word/chunk/frame a good reply would fire (Tamil script or frame:... key); empty string if this dose asks for nothing specific>",
  "target_revealed": true | false,      // does the body/memo show that Tamil itself?
  "volley_asks": ["<one-line English situation for VOLLEY TARGET 1>", "<…one per listed VOLLEY TARGET, index-matched>"],   // ONLY for modality "volley"; omit otherwise. Python zips these with its binding targets and composes the body from ask 1.
  "next_check_hours": <number>,         // when to reconsider (clamped to a sane range)
  "schedule": {"at_local": "YYYY-MM-DDTHH:MM", "body": "<the full dose>", "expected_target": "<or empty>", "target_revealed": true | false, "move": "<2-4 words>"} | null,
  "rationale": "<one line: why this choice>"
}
"""


def mark_frames_seen(keys: list[str]) -> None:
    """When a lore or trailer knock introduces a frame, mark it seen in the lexicon
    (last_surfaced = today). Closes the pipeline gap: lore memos were leaving
    frames UNSEEN even after Andrew heard them (2026-07-16)."""
    from sync_state import LEXICON_PATH, load_json as _load, save_json as _save
    lex = _load(LEXICON_PATH) or {}
    today = date.today().isoformat()
    changed = []
    for key in keys:
        if key in lex:
            lex[key]["last_surfaced"] = today
            changed.append(key)
        else:
            print(f"   ⚠ introduces: '{key}' not in lexicon — skipped")
    if changed:
        _save(LEXICON_PATH, lex)
        print(f"   Marked seen (introduces): {', '.join(changed)}")


def maybe_enqueue_schedule(decision: dict) -> Path | None:
    """If the decision planted a scheduled push, land it in the queue (text-only;
    fires via the hourly drain). Returns the queue path for the commit, or None."""
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
        if (d.get("memo_script") or "").strip():
            d["target_revealed"] = False  # the tape plays Tamil, but the ask is comprehension
        else:
            d["modality"] = "text"  # no tape to render — plain dose
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
            d = parse_llm_json(resp.choices[0].message.content)
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


def commit_and_push(paths: list[Path], msg: str):
    rels = [str(p.relative_to(BASE)) for p in paths]
    subprocess.run(["git", "add", *rels], cwd=BASE, check=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=BASE, check=True)
    # main has three writers (knock CI, ack CI, the laptop) and this checkout goes
    # minutes stale during the LLM/TTS steps — land our commit on top of theirs.
    subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=BASE, check=True)
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


def push_to_phone(body: str, audio_url: str | None, knock_id: str = ""):
    """Push a notification. audio_url is optional — a text/challenge/grace dose has none.
    knock_id = the knock's log-entry timestamp; it rides the notification's action_data
    and comes back with taps/replies so the judge grades the knock Andrew actually
    answered. Notifications stack (unique HA tag per knock, 2026-07-11) — last-fired
    correlation is only the fallback for id-less events."""
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
            return
        except OSError as e:  # URLError, gaierror, timeouts
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

    body = decision.get("notification_body", "")
    mp3 = None
    audio_url = None
    if decision["modality"] in ("audio", "eavesdrop"):
        print("3. render…")
        mp3 = KNOCKS_DIR / f"knock_{now.strftime('%Y-%m-%dT%H-%M')}.mp3"
        voice = EAVESDROP_VOICE if decision["modality"] == "eavesdrop" else ANNA_VOICE
        asyncio.run(render_memo(decision.get("memo_script", ""), mp3, voice))
        audio_url = jsdelivr_url(mp3)

    print("\n--- notification body ---\n" + body + "\n")
    if over_budget(body):
        print(f"   ⚠ body is {len(body)} chars (budget {BODY_BUDGET}) — the lock screen will cut it")

    if args.dry_run:
        print(f"[dry-run] would push ({decision['modality']}) + log; stopping.", mp3 or "")
        return

    path = log_decision(now, decision, acted=True, audio_url=audio_url, mp3=mp3)
    from sync_state import LEXICON_PATH as _LP
    extra_paths: list[Path] = []
    if decision.get("introduces"):
        mark_frames_seen(decision["introduces"])
        extra_paths.append(_LP)
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
