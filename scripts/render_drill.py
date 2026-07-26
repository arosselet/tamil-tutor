#!/usr/bin/env python3
"""
The drill track — a hands-free SPOKEN production volley from the deck's due list.

Everything else in the system is typed chat or listen-only immersion; the trip is
spoken. This closes that gap Pimsleur-style: Anna speaks an English cue, silence
while Andrew SAYS THE TAMIL OUT LOUD, then the answer lands (twice). Built straight
from the due fire-side deck items, so a walk or the dishes becomes deck reps.

Same one-shot family as the knock: the LLM writes the sheet (cues + answers),
Python owns the menu (deck due list), the render, and the publish. READ-ONLY on
the learning brain — listening isn't producing; no reps are logged. The cold
fires happen later, in chat or on a knock reply, where a judge can hear them.

  python scripts/render_drill.py --dry-run     # write + print the sheet only
  python scripts/render_drill.py               # sheet → render → RSS + commit/push + phone push
  python scripts/render_drill.py --no-publish  # render to published_audio/ only

Secrets: OPENROUTER_API_KEY (the sheet), GCP ADC (TTS), ANNA_PUSH_WEBHOOK_URL (the push).
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from morning_knock import (OPENROUTER_BASE, MODEL, ANNA_VOICE, load_env,
                           push_to_phone, commit_and_push, jsdelivr_url)
from render_audio import generate_segment_google, get_raw_mp3_frames, SILENCE_FRAME, clean_for_tts
from suggest_targets import deck_status
from sync_state import LEXICON_PATH, load_json

DRILLS_DIR = BASE / "published_audio"   # feed root — rebuild_rss picks up drill_*.mp3
SILENCE_PER_SEC = 41.666                # frames per second (matches render_audio)

DRILL_MANDATE = """\
You are Anna, writing a DRILL SHEET — a hands-free spoken production drill Andrew \
runs while driving or doing dishes. The rhythm per item: you speak a short English \
cue, then silence while HE SAYS THE TAMIL OUT LOUD, then you give the answer (it \
plays twice). Your job is only the sheet: the cues and the answers.

RULES:
- Items come from the DECK DUE list below, in the order given. A chunk's answer is \
the chunk itself, said whole. A frame becomes TWO consecutive items, each a \
different NOVEL slot-fill using everyday trip nouns/verbs (tea, auto, temple, \
bathroom, eat, sit, come...).
- The cue is a compact English situation or meaning ("ask your maama for a coffee", \
"tell her: we went to the temple, it was great"). NEVER put any Tamil in the cue — \
the silence is where he produces it unaided. Cues stay under ~12 words.
- The answer is natural standard Coimbatore colloquial in TAMIL SCRIPT ONLY (a \
Tamil voice speaks it). Polite -nga register by default; nee only where the deck \
item itself is nee-form.
- "intro": one short Anna line in his own voice setting the contract — out loud, \
before the answer comes, no mumbling. "outro": one short warm line, no homework.
- No grammar talk, no numbering, no meta-narration.

Return ONLY a JSON object, no prose around it:
{
  "title": "<3-5 word label for the feed>",
  "intro": "<one spoken line>",
  "items": [{"cue": "<English>", "answer_ta": "<Tamil script>"}, ...],
  "outro": "<one spoken line>"
}
"""


def deck_due_payload(max_entries: int) -> list[dict]:
    """The selector's order, but interleaved frame/chunk — a drill is mouth-reps,
    and a slot-fill and a said-whole phrase are different work, so a run of six
    frames is a worse drill than an alternating six.

    That is now the ONLY reason. Until 2026-07-25 this also worked around a
    starving sort: `deck_status` broke ties alphabetically and ASCII 'frame:'
    keys sorted ahead of every Tamil-script chunk, so a straight head-slice was
    all frames. The selector is coverage-first now (a plain top-6 measures 2
    frames / 4 chunks), so this is a pedagogy choice and no longer a guard —
    delete it the day that stops being true."""
    deck = deck_status(load_json(LEXICON_PATH) or {})
    if not deck or not deck["pending"]:
        return []
    frames = [t for t in deck["pending"] if t["kind"] == "frame"]
    chunks = [t for t in deck["pending"] if t["kind"] != "frame"]
    out = []
    while len(out) < max_entries and (frames or chunks):
        if frames:
            out.append(frames.pop(0))
        if chunks and len(out) < max_entries:
            out.append(chunks.pop(0))
    return out


def write_sheet(pending: list[dict]) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    menu = "\n".join(f"- [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}"
                     for t in pending)
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=2400,
        messages=[
            {"role": "system", "content": persona + "\n\n---\n\n" + DRILL_MANDATE},
            {"role": "user", "content": f"DECK DUE:\n{menu}"},
        ],
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    sheet = json.loads(text, strict=False)
    sheet["items"] = [i for i in sheet.get("items", [])
                      if i.get("cue", "").strip() and i.get("answer_ta", "").strip()]
    return sheet


def silence(seconds: float) -> bytes:
    return SILENCE_FRAME * int(seconds * SILENCE_PER_SEC)


async def render(sheet: dict, out_path: Path, gap: float):
    """Anna's one pinned voice throughout (cue in English, answer in Tamil script) —
    the drill should sound like the same someone as the knocks."""
    audio = bytearray()
    tmp = tempfile.mkdtemp()
    idx = 0

    async def seg(text: str) -> bytes:
        nonlocal idx
        idx += 1
        f = await generate_segment_google(clean_for_tts(text), ANNA_VOICE, idx, tmp)
        frames = get_raw_mp3_frames(f)
        os.remove(f)
        return frames

    print(f"   intro: {sheet['intro'][:60]}")
    audio.extend(await seg(sheet["intro"]))
    audio.extend(silence(1.5))
    for n, item in enumerate(sheet["items"], 1):
        print(f"   [{n}/{len(sheet['items'])}] {item['cue'][:40]} → {item['answer_ta'][:30]}")
        audio.extend(await seg(item["cue"]))
        audio.extend(silence(gap))              # his turn — out loud
        answer = await seg(item["answer_ta"])
        audio.extend(answer)
        audio.extend(silence(0.9))
        audio.extend(answer)                    # the echo sets it
        audio.extend(silence(1.4))
    audio.extend(await seg(sheet["outro"]))
    os.rmdir(tmp)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    print(f"   rendered -> {out_path} ({len(audio)/1024:.0f} KB)")


def main():
    ap = argparse.ArgumentParser(description="Spoken production drill from the deck's due list")
    ap.add_argument("--entries", type=int, default=8,
                    help="deck entries to drill (frames expand to 2 items; default 8)")
    ap.add_argument("--gap", type=float, default=3.5,
                    help="seconds of silence for Andrew's out-loud attempt (default 3.5)")
    ap.add_argument("--dry-run", action="store_true", help="write + print the sheet; no TTS or publish")
    ap.add_argument("--no-publish", action="store_true", help="render only; skip RSS/commit/push/notify")
    args = ap.parse_args()

    load_env(BASE / ".env")

    pending = deck_due_payload(args.entries)
    if not pending:
        print("No due fire-side deck items — nothing to drill.")
        return

    print(f"1. sheet… ({len(pending)} deck entries)")
    sheet = write_sheet(pending)
    print(f"   → '{sheet.get('title', 'Drill')}' · {len(sheet['items'])} items")

    if args.dry_run:
        print(json.dumps(sheet, ensure_ascii=False, indent=2))
        return

    now = datetime.now()
    mp3 = DRILLS_DIR / f"drill_{now.strftime('%Y-%m-%d_%H%M')}.mp3"
    print("2. render…")
    asyncio.run(render(sheet, mp3, args.gap))

    if args.no_publish:
        return

    print("3. publish…")
    subprocess.run([sys.executable, str(BASE / "scripts" / "rebuild_rss.py")], cwd=BASE, check=True)
    commit_and_push([mp3, BASE / "rss.xml"], f"Drill track: {sheet.get('title', mp3.stem)}")
    # This lane had NO quiet-hours check at all and pushed a drill at 23:42
    # (2026-07-26). The guard lives in push_to_phone now, so every lane —
    # including ones not written yet — inherits it.
    print("4. notify…")
    pushed = push_to_phone(f"drill's up — {len(sheet['items'])} out loud, gaps are yours 🎧",
                           jsdelivr_url(mp3))
    print(f"done — drill on the feed{' and the lock screen' if pushed else ''}.")


if __name__ == "__main__":
    main()
