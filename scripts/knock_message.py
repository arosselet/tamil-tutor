#!/usr/bin/env python3
"""The MESSAGE lane — Andrew talking TO Anna, not answering her.

Reached from knock_reply.py when the phone says `intent=message` (the Shortcut's
"Message" button) and no `knock_id` came with it. Nothing here grades: no
production axis, no catch axis, no chains, no volley walk, no reveal caps. The
job is to DO the thing he asked.

WHY THIS EXISTS (2026-08-27). He typed "Send an audio greeting in Tamil" and got
three text acknowledgements. The cause was routing, not the model: every inbound
message resolved to `find_knock(...) or last_fired_knock(...)`, so a request he
typed cold was graded as a reply to whatever knock happened to be open — that
day, an eavesdrop from 02:46. The judge called it `chat` every time, which was
CORRECT and useless: the verdict was right, the lane was wrong. `chat` had become
the catch-all for "this wasn't a rep", with nowhere for the thing he actually
asked for to happen.

The signal was already in the environment and thrown away. Per
docs/home_assistant_knock_buttons.md §8.3 the notification's Reply ✍️ button
round-trips a `knock_id` and the Shortcut sends none — "the right default for 'I
want to say something to Anna now'." `or last_fired_knock()` collapsed that
distinction silently, and every run stayed green.

WHAT THE KNOCK IS FOR HERE. A message is not an answer to a knock, so this lane
never sets `response`, `reply` or `reply_verdict` on one — those say "he answered
this", and a nudge gate that believed a message was an answer would go quiet on
outreach he never got. The last fired knock is used as a THREAD ANCHOR only: the
exchange is appended to it so chat.md and `recent_exchanges` keep one continuous
record, tagged `intent: "message"` so nothing downstream can mistake it for a rep.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from mandates import (FORCE_SCHEDULE_ADDENDUM, FORCE_VOICE_ADDENDUM,
                      MESSAGE_MANDATE, REACH_MANDATE, THREAD_MANDATE,
                      VOICE_MANDATE)
from morning_knock import maybe_enqueue_schedule
from publish import commit_and_push, load_env, publish, push_to_phone
from reply_common import (ensure_voice, recent_exchanges, record_meta_note,
                          speak, wants_scheduled_push)
from state_io import FEEDBACK_LOG_PATH, KNOCK_LOG_PATH, load_json, save_json
from writer import STR, ask_json, executor_name, obj, voice_canon

# Declared beside the lane that reads it, like every other judge shape. `schedule`
# and `voice_reply` are absent on purpose: both are nullable/optional and obj()
# makes everything it names REQUIRED, so declaring them would force the model to
# invent one on every plain "thanks da". Undeclared keys still pass.
MESSAGE_SCHEMA = obj(reply_line=STR, meta_note=STR, rationale=STR, voice_reply=STR)


def judge_message(text: str, knock: dict, klog: list,
                  force_voice: bool = False, force_schedule: bool = False) -> dict:
    """Anna reading a message. Same persona, same thread, no grading mandate."""
    canon = voice_canon()
    context = {"andrew_said": text,
               "prior_exchanges": recent_exchanges(klog, knock) if knock else []}
    print(f"   [message] {executor_name()}")
    mandate = (MESSAGE_MANDATE + "\n" + VOICE_MANDATE + "\n" + REACH_MANDATE
               + "\n" + THREAD_MANDATE
               + (FORCE_VOICE_ADDENDUM if force_voice else "")
               + (FORCE_SCHEDULE_ADDENDUM if force_schedule else ""))
    d = ask_json(canon + "\n\n---\n\n" + mandate,
                 json.dumps(context, ensure_ascii=False, indent=2),
                 MESSAGE_SCHEMA, answer_tokens=900 if force_voice else 700)
    d["reply_line"] = (d.get("reply_line") or "").strip()
    d["meta_note"] = (d.get("meta_note") or "").strip()
    d["voice_reply"] = (d.get("voice_reply") or "").strip()
    return d


def handle_message(text: str, knock: dict | None, klog: list, dry_run: bool):
    """Answer him, and act. The two backstops below are the same pair the reply
    lane runs — a direct audio ask and a clock-bound ask each get one forced
    re-ask and then a LOUD note in the ledger. They matter more here, because
    this lane has no verdict to fall back on: an unanswered request would leave
    a friendly line on the lock screen and no trace that anything was missed."""
    print("1. MESSAGE — not a rep, nothing graded")
    verdict = judge_message(text, knock, klog)
    print(f"   → {verdict.get('rationale', '')}")

    verdict = ensure_voice(verdict, text,
                           lambda: judge_message(text, knock, klog, force_voice=True))

    if wants_scheduled_push(text) and not verdict.get("schedule"):
        print("   ⏰ time-bound request with no schedule — re-asking once, forced…")
        forced = judge_message(text, knock, klog, force_schedule=True)
        if forced.get("schedule"):
            verdict = forced
            print(f"   → scheduled: {forced['schedule'].get('at_local')}")
        else:
            print("   ⚠ still no schedule — logging the miss to the ledger")
            verdict["meta_note"] = (verdict.get("meta_note") or "").strip() or (
                f"MISSED SCHEDULE: Andrew asked for something at a time "
                f"({text[:80]!r}) in a MESSAGE and no push was queued.")

    if dry_run:
        spoken = verdict.get("voice_reply") or ""
        print(f"[dry-run] would push: {verdict['reply_line']}"
              + (f"\n[dry-run] would speak: {spoken}" if spoken else ""))
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if knock is not None:
        # Thread anchor only — see the module docstring. `intent` is what keeps
        # this out of every rep-counting read downstream.
        knock.setdefault("exchanges", []).append(
            {"at": now, "reply": text, "intent": "message", "verdict": "chat",
             "fired": [], "reply_line": verdict["reply_line"]})
        save_json(KNOCK_LOG_PATH, klog)

    voice_url, vmp3 = speak(verdict, knock, klog) if knock is not None else (None, None)
    meta = record_meta_note(verdict)

    print("2. commit + push…")
    commit_and_push(*publish(
        [KNOCK_LOG_PATH, FEEDBACK_LOG_PATH if meta else None,
         maybe_enqueue_schedule(verdict)],
        "Message: answered" + (" (aloud)" if voice_url else ""),
        mp3=vmp3 if voice_url else None))
    print("3. push back…")
    # NO knock_id (2026-08-28). A message is not an answer to a knock, and this
    # field is JUDGING CORRELATION: it rides action_data and comes back with the
    # tap, so a message pushed under the anchor's id would send a Reply ✍️ on
    # THIS notification into grading against a knock Andrew was never shown.
    # Empty routes it back to this lane instead, which is what continuing a
    # conversation should do.
    #
    # Found while chasing a message that looked undelivered; it turned out to be
    # four minutes of push latency, not a loss. The stale id was real anyway, so
    # the fix stands on correlation alone. (A pre-2026-08-19 HA automation would
    # ALSO derive the notification tag from this id and could collide with an
    # earlier push for the same knock — plausible, never observed, and not the
    # reason this changed.)
    push_to_phone(verdict["reply_line"], voice_url, knock_id="", requested=True)
    print(f"done — message answered{' (aloud 🎧)' if voice_url else ''}.")


def main():
    parser = argparse.ArgumentParser(description="Answer a message from Andrew")
    parser.add_argument("text")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_env()
    klog = load_json(KNOCK_LOG_PATH) or []
    fired = [k for k in klog if k.get("acted", True)]
    handle_message(args.text, fired[-1] if fired else None, klog, args.dry_run)


if __name__ == "__main__":
    main()
