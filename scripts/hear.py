#!/usr/bin/env python3
"""The ear — a spoken turn becomes the text knock_reply would have received.

Voice turns, level 1 (2026-10-25, Andrew; `docs/voice_turn_plan.md`). The "Talk to
Anna" Shortcut records a short clip, base64-encodes it and sends it INSIDE a
`voice-turn` dispatch. This script reads it, makes ONE multimodal call to the
writer's OpenRouter model, and hands the transcript to `knock_reply.run` with the
payload's intent and knock_id, exactly as if he had typed it. From there the turn
takes the typed routing: sort, message, catch, or the production judge.

THE CLIP NEVER TOUCHES ENV OR THE LOG. It is read from `$GITHUB_EVENT_PATH`, the
event file on the runner's disk. A step's `env:` values are printed into the run
log, and run logs on a public repo are public. A typed reply's text already shows
there; the audio must not. Only its size is ever printed. Nothing is stored: the
transcript and the `heard` block are committed with the exchange, the same
exposure as a typed reply, and the clip dies with the runner.

THE EAR IS BLIND (`HEAR_MANDATE`): told who speaks, never what was asked. Told the
target, it would echo the target back, and the judge's `said` rule (a word he
never typed can never score — now, a word the ear never heard) would be checking
the ear against itself.

THE SILENT NO-OP, answered. A turn that dies quietly looks exactly like Anna
ignoring him, the expired-PAT outage again. So every failure before the handoff
(no clip, an undecodable clip, the ear erroring, no speech heard) pushes
"Couldn't hear that one" to the phone AND exits non-zero, so the run goes red.

    python scripts/hear.py                       # the runner: reads the event file
    python scripts/hear.py --clip turn.m4a --dry-run   # laptop: hear, print, stop
    python scripts/hear.py --clip turn.m4a --intent reply   # laptop: a real turn
"""
import argparse
import base64
import binascii
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

import reply_common
from mandates import HEAR_MANDATE
from publish import load_env, push_to_phone

HEARD_NOTHING = "Couldn't hear that one — try again?"
CONFIDENCE = ("high", "medium", "low")


class Unheard(Exception):
    """Any failure before the handoff. Its message goes to the log, never the clip."""


def payload_from_event(path: str) -> dict:
    """The dispatch's client_payload, off the event file. Never from env."""
    if not path or not Path(path).exists():
        raise Unheard("no GITHUB_EVENT_PATH — this lane only runs on a voice-turn dispatch")
    return json.loads(Path(path).read_text(encoding="utf-8")).get("client_payload") or {}


def clip_from(payload: dict) -> tuple[str, str]:
    """(base64 audio, format). Shortcuts' Base64 Encode can wrap lines, so the
    whitespace goes; validation decodes it once so a garbled clip fails here,
    loudly, and not as a puzzling ear error."""
    audio = "".join((payload.get("audio") or "").split())
    if not audio:
        raise Unheard("the dispatch carried no audio")
    try:
        size = len(base64.b64decode(audio, validate=True))
    except (binascii.Error, ValueError) as e:
        raise Unheard(f"the audio is not valid base64 ({e})")
    print(f"   clip: {size // 1024} KB {payload.get('format') or 'm4a'}")
    return audio, (payload.get("format") or "m4a").lower()


def hear(audio_b64: str, fmt: str) -> dict:
    """ONE ear call through `writer.hear_json`, with the blind mandate and a
    passthrough clip; Gemini takes AAC, so m4a goes as-is until the first real
    clip says otherwise (slice 2 of the plan)."""
    from writer import OPENROUTER_MODEL, hear_json
    try:
        d = hear_json(HEAR_MANDATE, audio_b64, fmt)
    except Exception as e:  # the ear's failure is a push, not a stack trace he never sees
        raise Unheard(f"the ear failed: {type(e).__name__}: {str(e)[:200]}")
    heard = {"transcript": (d.get("transcript") or "").strip(),
             "meaning": (d.get("meaning") or "").strip(),
             "confidence": d.get("confidence") if d.get("confidence") in CONFIDENCE else "low",
             "model": OPENROUTER_MODEL}
    if not heard["transcript"]:
        raise Unheard(f"the ear heard no speech (confidence {heard['confidence']})")
    return heard


def main():
    ap = argparse.ArgumentParser(description="Hear a spoken turn and hand it to knock_reply")
    ap.add_argument("--clip", help="a local audio file instead of the dispatch's event file")
    ap.add_argument("--intent", default="", help="with --clip: message | reply")
    ap.add_argument("--knock-id", default="", help="with --clip: the knock being answered")
    ap.add_argument("--dry-run", action="store_true",
                    help="hear and print only: no handoff, no state, no push")
    args = ap.parse_args()
    load_env(BASE / ".env")

    knock_id, intent = args.knock_id, args.intent
    print("1. hearing the turn…")
    try:
        if args.clip:
            clip = Path(args.clip)
            audio = base64.b64encode(clip.read_bytes()).decode()
            payload = {"audio": audio, "format": clip.suffix.lstrip(".") or "m4a"}
        else:
            payload = payload_from_event(os.environ.get("GITHUB_EVENT_PATH", ""))
            knock_id = payload.get("knock_id") or ""
            intent = payload.get("intent") or ""
        heard = hear(*clip_from(payload))
    except Unheard as e:
        print(f"   ⚠ {e}")
        if not args.dry_run:
            push_to_phone(HEARD_NOTHING, None, knock_id=knock_id, requested=True)
        sys.exit(1)

    print(f"   heard ({heard['confidence']}): {heard['transcript']}")
    print(f"   meant: {heard['meaning']}")
    if args.dry_run:
        print("[dry-run] no handoff.")
        return

    # Typed intent semantics hold: a knock_id means a reply; none means the
    # Shortcut's menu chose. knock_reply logs which.
    reply_common.SPOKEN = heard
    import knock_reply  # late: its import pulls the whole grading lane
    print("2. handing off to knock_reply — the typed routing, spoken")
    knock_reply.run(heard["transcript"], knock_id, intent)


if __name__ == "__main__":
    main()
