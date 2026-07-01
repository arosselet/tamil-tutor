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
    MODALITY (text micro-dose / audio memo / challenge / grace / silence), his own
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
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from render_audio import generate_segment_google, get_raw_mp3_frames, SILENCE_FRAME

OPENROUTER_BASE = "https://openrouter.ai/api/v1"   # OpenAI-compatible; one key, many models
MODEL = "anthropic/claude-sonnet-4.6"   # Andrew's default; fallback e.g. "google/gemini-2.5-flash"
ANNA_VOICE = "ta-IN-Chirp3-HD-Orus"     # pinned: Anna always sounds like the same someone
REPO = "arosselet/tamil-tutor"          # for the jsDelivr URL
KNOCKS_DIR = BASE / "published_audio" / "knocks"   # tracked, jsDelivr-served dir
KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
SESSION_LOG_PATH = BASE / "progress" / "session_log.json"

# ── The rails (hard, Python-enforced — Anna cannot cross these) ───────────────
# Andrew's local timezone; DST-correct (EDT/EST) so the waking window is honest
# year-round. The cron ticks a superset in UTC; this is the precise filter.
LOCAL_TZ = ZoneInfo("America/New_York")
WAKING_START_HOUR = 8      # inclusive, local
WAKING_END_HOUR = 21       # exclusive, local (last reach can land at 20:59)
MAX_REACHES_PER_DAY = 3    # a "reach" = a knock that actually fired (silence doesn't count)
MIN_GAP_HOURS = 3          # minimum spacing between reaches
NEXT_CHECK_CLAMP = (0.5, 24.0)   # Anna's self-set next_check is clamped to this many hours

MODALITIES = {"text", "audio", "challenge", "grace", "silence"}


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
        tapped = "tapped" if k.get("response") else "no-tap"
        modality = k.get("modality", "audio")
        move = k.get("move", "—")
        lines.append(f"    {k.get('date','?')} · {modality}/{move} · {tapped}")

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


def remaining_room(klog: list, now: datetime) -> str:
    now_local = now.astimezone(LOCAL_TZ)
    n_today = fires_today(klog, now_local.date())
    lf = last_fire(klog)
    gap_str = "no reach yet today"
    if lf:
        gap = (now - datetime.fromisoformat(lf["timestamp"])).total_seconds() / 3600
        gap_str = f"last reach {gap:.1f}h ago"
    return (f"RAILS (hard — stay well inside; silence is free):\n"
            f"  Waking window {WAKING_START_HOUR}:00–{WAKING_END_HOUR}:00 {now_local.tzname()}; "
            f"now {now_local:%H:%M}.\n"
            f"  Reaches today: {n_today}/{MAX_REACHES_PER_DAY}. Min gap {MIN_GAP_HOURS}h ({gap_str}).")


def build_digest() -> str:
    """Everything Anna needs to make a policy call: learning state + outcome memory
    + how much room the rails leave him right now."""
    out = subprocess.run([sys.executable, str(BASE / "scripts" / "sync_state.py"), "status"],
                         capture_output=True, text=True)
    status = out.stdout.strip()
    klog = load_json(KNOCK_LOG_PATH) or []
    now = datetime.now(timezone.utc)
    return f"{status}\n\n{outcome_memory(klog, now)}\n\n{remaining_room(klog, now)}"


# ── The decision (LLM — only reached when the rails gate opened) ───────────────

OUTREACH_MANDATE = """\
You are Anna, deciding a single OUTREACH TICK. The rails already cleared, so a reach \
is POSSIBLE — but possible is not obligatory. Your job is judgment: decide whether to \
reach out at all, and if so, how — then choose when you want to think about this next.

THE REWARD you are optimising: **Andrew showing up and producing in chat** (a session, \
a reply in Tamil). NOT taps. A tap ("Got it") is only a weak "it landed" signal; do not \
farm easy taps. If reaches aren't converting into sessions, the right move is usually to \
back off or change approach — read the OUTREACH MEMORY and adapt. Silence is a first-class \
choice; presence is not pestering.

YOUR MODALITIES (pick what fits THIS moment; never the same move twice in a row):
- "text"      — a one-line micro-dose answered right in the reply ("saapta? reply in tamizh — that's the whole ask"). No audio. Lowest friction; often the best re-opener after a gap.
- "audio"     — a self-contained ~60-90s spoken memo (a vivid one-use peg for a word). A dose in itself, never a pitch to "go listen to an episode."
- "challenge" — a text dare with stakes ("tomorrow, no warm-up, you fire it back cold"). Text delivery. \
Includes the FIELD MISSION: assign one line to deploy at home tonight, unprompted ("'suvaiya \
irukku' at dinner — debrief tomorrow"). The wife is the unwitting audience, NEVER the examiner; \
collect the debrief at next contact.
- "grace"     — a warm, no-pressure note when he's lapsed (a missed day is nothing — the Enjoyment Clause). Text delivery.
- "silence"   — reach nothing this tick. Set act=false. Choose this freely; often correct.

SELF-PACING: set next_check_hours = how long until you want to reconsider reaching out \
(you are choosing your own cadence, inside the rails). Sooner if momentum is hot; longer \
to give space after an ignored streak.

RATIONALE: one honest line on WHY this move/modality/timing — this is your memory; it's \
how you learn what works.

CONTENT RULES (unchanged):
- The scene is DISPOSABLE — a vivid one-use peg, then dropped. NO serialized saga, NO \
cliffhanger. The only real narrative is ANDREW'S arc (the heist toward the reveal).
- Woven Thanglish: English carries logistics, Tamil carries the payload. In AUDIO, Tamil \
payload must be in TAMIL SCRIPT (a Tamil TTS voice speaks it — never romanized). In a \
text/challenge/grace body, phonetic Tamil is fine (he reads at speed).
- No grammar talk, no case names, no meta "as your AI" narration, no comment on his energy/activity.

THE REPLY CONTRACT: Andrew can type a Tamil reply straight into the notification, and a \
judge will score it against what you asked for. So when your dose asks for production, \
declare the target: expected_target = the ONE lexicon word/chunk/frame a good reply would \
fire (Tamil script, or a frame:... key). target_revealed = whether your notification body \
or memo hands him that Tamil itself — if it does, his reply is reading it back, worth \
"hinted" at most; only an UN-shown target can be fired cold. The strongest doses show a \
situation in English and leave the Tamil to him.

Return ONLY a JSON object, no prose around it:
{
  "act": true | false,                  // false = silence this tick
  "modality": "text" | "audio" | "challenge" | "grace" | "silence",
  "move": "<2-4 word label of the move, for the log>",
  "notification_body": "<the lock-screen line — valuable even if never tapped; MUST carry a Tamil phrase + tiny English gloss. One emoji ok. Empty string if silence.>",
  "memo_script": "<ONLY for modality 'audio': the spoken memo, paragraphs separated by ONE blank line, plain text, Tamil payload in Tamil script. Empty string otherwise.>",
  "expected_target": "<the one word/chunk/frame a good reply would fire (Tamil script or frame:... key); empty string if this dose asks for nothing specific>",
  "target_revealed": true | false,      // does the body/memo show that Tamil itself?
  "next_check_hours": <number>,         // when to reconsider (clamped to a sane range)
  "rationale": "<one line: why this choice>"
}
"""


def decide(digest: str) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=1600,
        messages=[
            {"role": "system", "content": persona + "\n\n---\n\n" + OUTREACH_MANDATE},
            {"role": "user", "content": f"TODAY'S DIGEST:\n\n{digest}"},
        ],
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    d = json.loads(text, strict=False)
    # Normalise / guard the fields Python relies on.
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
    return d


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


async def render_memo(memo_script: str, out_path: Path):
    import tempfile
    paras = [p.strip() for p in memo_script.split("\n\n") if p.strip()]
    audio = bytearray()
    tmp = tempfile.mkdtemp()
    for i, para in enumerate(paras):
        seg = await generate_segment_google(para, ANNA_VOICE, i, tmp)
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


def jsdelivr_url(mp3: Path) -> str:
    rel = mp3.relative_to(BASE).as_posix()
    return f"https://cdn.jsdelivr.net/gh/{REPO}@main/{rel}"  # unique daily filename => always fresh


def push_to_phone(body: str, audio_url: str | None):
    """Push a notification. audio_url is optional — a text/challenge/grace dose has none."""
    webhook = os.environ["ANNA_PUSH_WEBHOOK_URL"]
    payload = {"title": "Anna", "text_content": body}
    if audio_url:
        payload["audio_url"] = audio_url
    req = urllib.request.Request(webhook, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        print(f"   HA push -> HTTP {r.status}")


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
                    help="skip the rails gate (manual one-off; still respects the daily cap at fire time)")
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
    decision = decide(digest)
    print(f"   → act={decision.get('act')} modality={decision['modality']} "
          f"move={decision.get('move')!r} next_check={decision['next_check_hours']}h")
    print(f"   rationale: {decision.get('rationale')}")

    acting = bool(decision.get("act")) and decision["modality"] != "silence"

    if not acting:
        print("   Anna chose silence.")
        if args.dry_run:
            print("[dry-run] would log the silence + next_check; stopping.")
            return
        path = log_decision(now, decision, acted=False)
        commit_and_push([path], f"Anna: silence ({decision.get('rationale','')[:50]})")
        print("done — silence logged, next_check set.")
        return

    body = decision.get("notification_body", "")
    mp3 = None
    audio_url = None
    if decision["modality"] == "audio":
        print("3. render…")
        mp3 = KNOCKS_DIR / f"knock_{now.strftime('%Y-%m-%dT%H-%M')}.mp3"
        asyncio.run(render_memo(decision.get("memo_script", ""), mp3))
        audio_url = jsdelivr_url(mp3)

    print("\n--- notification body ---\n" + body + "\n")

    if args.dry_run:
        print(f"[dry-run] would push ({decision['modality']}) + log; stopping.", mp3 or "")
        return

    path = log_decision(now, decision, acted=True, audio_url=audio_url, mp3=mp3)
    commit_paths = [path] if mp3 is None else [mp3, path]
    print("4. commit + push…")
    commit_and_push(commit_paths, f"Anna reach ({decision['modality']}/{decision.get('move')})")
    print("5. notify…")
    push_to_phone(body, audio_url)
    print("\ndone — reached out & logged.")


if __name__ == "__main__":
    main()
