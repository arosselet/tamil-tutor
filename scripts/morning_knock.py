#!/usr/bin/env python3
"""
The Morning Knock — Anna's once-a-day between-session audio nudge.

One-shot pipeline: read the briefing -> Anna (one Anthropic call) writes a FRESH
memo -> single-voice Chirp render -> commit -> jsDelivr serves it -> Home Assistant
pushes it to the phone. READ-ONLY on the learning brain: the knock observes, it never
logs reps or advances the floor.

  python scripts/morning_knock.py --dry-run   # generate + render only (no commit/push/notify)
  python scripts/morning_knock.py             # full: commit the mp3, fire the HA push

Secrets (in .env locally; GitHub Actions secrets in CI):
  OPENROUTER_API_KEY     — the one-shot that writes the memo (one key, any model)
  ANNA_PUSH_WEBHOOK_URL  — the Home Assistant webhook
GCP TTS auth comes from ADC locally / a service-account secret in CI (same as render_audio.py).
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from render_audio import generate_segment_google, get_raw_mp3_frames, SILENCE_FRAME

OPENROUTER_BASE = "https://openrouter.ai/api/v1"   # OpenAI-compatible; one key, many models
# Voice-critical but tiny/daily — default to a top model; Flash is a one-line swap + an easy A/B.
# Confirm exact slugs at https://openrouter.ai/models   [VERIFY]
MODEL = "anthropic/claude-sonnet-4.6"   # Andrew's default; fallback e.g. "google/gemini-2.5-flash"
ANNA_VOICE = "ta-IN-Chirp3-HD-Orus"     # pinned: Anna always sounds like the same someone
REPO = "arosselet/tamil-tutor"          # for the jsDelivr URL
KNOCKS_DIR = BASE / "audio" / "knocks"

# The choreography (persona.md is the voice; this is the loop). The policy is a
# JUDGMENT, not a decision tree: hand Anna the state + a palette, let him choose.
KNOCK_MANDATE = """\
You are writing ONE between-session "knock" — a short audio memo Anna leaves on Andrew's \
phone in the afternoon, on a day Andrew did NOT open the chat. It is a nudge, not a lesson.

Your one job: read the briefing below like someone who knows him, and leave something that \
makes him WANT to come back. Decide what he needs TODAY.

You have a palette of moves — pick like a brother who wants you to keep going, never the same \
move twice, NEVER a fixed template:
- grace if he's lapsed (a missed day is nothing — the Enjoyment Clause; never shame the pace),
- "press play" if there's an unlogged episode waiting (a listen is the soak),
- one specific word to catch and let sit in his ear,
- a real challenge with stakes ("next time, no warm-up, you fire it back cold"),
- occasionally his OWN arc reflected back ("you own N of these cold now; weeks ago it was single digits").

HARD RULES:
- The scene is DISPOSABLE — a vivid one-use peg for a word, then dropped. NO serialized saga, \
NO cliffhanger, NO manufactured suspense over a fictional plot. The only real narrative is \
ANDREW'S arc (the heist: passing as a local, the floor climbing toward the reveal to his wife).
- Woven Thanglish: English carries the logistics, Tamil carries the payload. The load-bearing \
action words are Tamil, in TAMIL SCRIPT (this is spoken by a Tamil TTS voice — never romanized/phonetic).
- No grammar talk, no case names, no meta "as your AI" narration, no comment on his energy/activity.
- ~60-90 seconds spoken (roughly 120-170 words).

Return ONLY a JSON object, no prose around it:
{
  "notification_body": "one short lock-screen line that is valuable even if never tapped — it \
MUST contain the target Tamil phrase (Tamil script) and a tiny English gloss, e.g. \
'அப்படி இல்ல · \\"not like that\\"'. One emoji ok.",
  "memo_script": "the spoken memo. Paragraphs separated by ONE blank line (the renderer splits \
on blank lines for pacing). Plain text only — no markdown, no stage directions, no speaker labels. \
Tamil payload in Tamil script."
}
"""


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


def gather_briefing() -> str:
    """The state Anna reads. sync_state status is compact and already carries everything the
    memo needs: streak, the running story, the soak order, unlogged episodes, the floor."""
    out = subprocess.run([sys.executable, str(BASE / "scripts" / "sync_state.py"), "status"],
                         capture_output=True, text=True)
    return out.stdout.strip()


def write_memo(briefing: str) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": persona + "\n\n---\n\n" + KNOCK_MANDATE},
            {"role": "user", "content": f"TODAY'S BRIEFING:\n\n{briefing}"},
        ],
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    return json.loads(text, strict=False)  # tolerate literal newlines inside the memo_script string


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
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE, check=True)  # works from CI's detached HEAD too


def jsdelivr_url(mp3: Path) -> str:
    rel = mp3.relative_to(BASE).as_posix()
    return f"https://cdn.jsdelivr.net/gh/{REPO}@main/{rel}"  # unique daily filename => always fresh


def push_to_phone(body: str, audio_url: str):
    webhook = os.environ["ANNA_PUSH_WEBHOOK_URL"]
    payload = json.dumps({"title": "Anna", "text_content": body, "audio_url": audio_url}).encode()
    req = urllib.request.Request(webhook, data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        print(f"   HA push -> HTTP {r.status}")


def main():
    ap = argparse.ArgumentParser(description="Anna's daily audio knock")
    ap.add_argument("--dry-run", action="store_true",
                    help="generate + render only; no commit, no push, no notification")
    args = ap.parse_args()

    load_env(BASE / ".env")

    print("1. briefing…")
    briefing = gather_briefing()
    print("2. Anna writes the knock…")
    memo = write_memo(briefing)
    print("\n--- notification body ---\n" + memo["notification_body"])
    print("\n--- memo script ---\n" + memo["memo_script"] + "\n")

    mp3 = KNOCKS_DIR / f"knock_{date.today().isoformat()}.mp3"
    print("3. render…")
    asyncio.run(render_memo(memo["memo_script"], mp3))

    if args.dry_run:
        print("\n[dry-run] stopping before commit/push/notify. Listen:", mp3)
        return

    audio_url = jsdelivr_url(mp3)
    # Record that Anna reached out — his outreach memory. NOT a learning-state change
    # (the knock never fakes reps); it lets the chat cash in ("caught the one I sent?").
    klog_path = BASE / "progress" / "knock_log.json"
    klog = json.loads(klog_path.read_text(encoding="utf-8")) if klog_path.exists() else []
    klog.append({"date": date.today().isoformat(), "body": memo["notification_body"],
                 "audio_url": audio_url, "mp3": str(mp3.relative_to(BASE))})
    klog_path.write_text(json.dumps(klog, ensure_ascii=False, indent=2), encoding="utf-8")

    print("4. commit + push the audio + knock-log (so jsDelivr can serve it)…")
    commit_and_push([mp3, klog_path], f"Morning knock {mp3.stem}")
    print("5. notify…")
    push_to_phone(memo["notification_body"], audio_url)
    print("\ndone — knock delivered & logged.")


if __name__ == "__main__":
    main()
