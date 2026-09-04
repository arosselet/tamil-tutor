#!/usr/bin/env python3
"""
Scheduled pushes — the durable "ping me at X" layer of Anna's outreach.

The knock system decides WHETHER to reach out (agentic); this queue delivers
pushes Anna already decided on, at a chosen TIME — "ping me in an hour",
"field-mission debrief at 9pm", "deck rep tomorrow 8:15". Entries are fully
composed at add-time (no LLM at fire-time), live in progress/push_queue.json on
main, and are drained at the START of every Anna wake-up — the hourly tick, a
lock-screen reply, a manual dispatch (.github/workflows/anna.yml) — or by any
local drain; whoever gets there first, the queue is the single source of truth.

COMPOSED at add-time is not RENDERED at add-time (2026-07-24). An entry carrying
`memo_script` is a VOICE dose: the words are frozen when Anna writes them, but
the TTS runs at fire time, in the drain. That keeps the render off the reply
path — Andrew is waiting at the lock screen when the judge runs, and a minute of
TTS there is a minute he watches a blank notification shade — while still
honouring the "no LLM at fire-time" law, which TTS was never subject to.

Every fired entry is logged into knock_log.json exactly like a knock, so:
  - a phone reply gets judged against its expected_target (knock_reply.py), and
  - the anti-pester rails (daily cap, min gap) SEE scheduled pushes and back
    the ambient knocks off accordingly.

Quiet hours: a non-forced entry due in the sleep window simply waits and fires
on the first tick after 8am. --force marks an Andrew-requested ping that fires
whenever it's due (the rails protect him from UNrequested pushes, not requested
ones).

  python scripts/push_queue.py add --in 60 --body "saapta? reply in tamizh" \
      --expected-target "சாப்பிட்டேன்" [--force]
  python scripts/push_queue.py add --at 2026-07-02T08:15 --body "..."
  python scripts/push_queue.py list
  python scripts/push_queue.py drain [--dry-run]
  python scripts/push_queue.py cancel <id>

Secrets: ANNA_PUSH_WEBHOOK_URL (delivery); GCP TTS auth only when a due entry
carries a memo_script. No LLM key needed.
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from memo import render_memo
from publish import (KNOCKS_DIR, commit_and_push, jsdelivr_url,
                     load_env, publish, push_to_phone)
from rails import MAX_REACHES_PER_DAY, in_waking_window, reaches_today
from state_io import KNOCK_LOG_PATH, LOCAL_TZ, load_json
from language import ANNA_VOICE

QUEUE_PATH = BASE / "progress" / "push_queue.json"


def save_queue(queue: list):
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_due(at: str | None, in_minutes: float | None) -> datetime:
    """--in N minutes, or --at as 'HH:MM' (today local; tomorrow if past),
    'YYYY-MM-DDTHH:MM' (local), or full ISO with offset. Returns aware UTC."""
    now = datetime.now(timezone.utc)
    if in_minutes is not None:
        return now + timedelta(minutes=in_minutes)
    if not at:
        raise SystemExit("Need --at or --in.")
    if ":" in at and "T" not in at and "-" not in at:  # bare HH:MM
        h, m = map(int, at.split(":"))
        local = now.astimezone(LOCAL_TZ).replace(hour=h, minute=m, second=0, microsecond=0)
        if local < now.astimezone(LOCAL_TZ):
            local += timedelta(days=1)
        return local.astimezone(timezone.utc)
    dt = datetime.fromisoformat(at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(timezone.utc)


# `in_waking_window` comes from `rails.py` — one definition, read by the rails
# gate, this queue's deferral, and push_to_phone's backstop (2026-07-26; moved
# out of `publish` 2026-09-04, when the daily cap this queue also obeys joined
# it there). The comment this replaces said "imported from morning_knock" while
# the import line forty lines above already said `publish`: the attribution
# rotted the moment the definition moved, which is the argument for one home.


def needs_render(entry: dict) -> bool:
    """A voice dose that hasn't been rendered yet. `audio_url` already set means
    a local session handed over a finished mp3 — nothing to do."""
    return bool(entry.get("memo_script")) and not entry.get("audio_url")


def render_entry(entry: dict) -> Path | None:
    """Render a queued voice dose to a tracked mp3 and fill in its `audio_url`.
    Returns the mp3 path to commit, or None when there was nothing to render.

    This is the drain half of "audio at a scheduled time" (2026-07-24). It is
    the same call the knock tick has made daily since 2026-07-05 — the only
    reason the drain could not do it was that push-queue.yml was never given the
    TTS secret. A render failure must not swallow the dose: the text still
    fires, and the log records that the voice was lost.
    """
    if not needs_render(entry):
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    mp3 = KNOCKS_DIR / f"queued_{entry['id']}_{stamp}.mp3"
    try:
        asyncio.run(render_memo(entry["memo_script"], mp3, ANNA_VOICE))
    except Exception as exc:                       # noqa: BLE001 — text must still fire
        print(f"  ⚠ {entry['id']}: TTS failed ({exc}) — firing the text without voice")
        entry["render_failed"] = str(exc)[:200]
        return None
    entry["audio_url"] = jsdelivr_url(mp3)
    return mp3


def enqueue(body: str, due: datetime, *, expected_target: str = "",
            target_revealed: bool = True, audio_url: str | None = None,
            memo_script: str = "", move: str = "scheduled push",
            force: bool = False) -> dict:
    """Append one composed push to the queue (no commit — callers own that, so a
    knock/judge run can land the queue write in its existing commit).

    `memo_script` makes it a VOICE dose: the drain renders it at fire time and
    fills `audio_url` itself. `audio_url` stays available for an already-rendered
    mp3 (a local session can hand one over pre-made)."""
    entry = {
        "id": f"q{int(time.time())}",
        "due": due.astimezone(timezone.utc).isoformat(),
        "body": body,
        "expected_target": expected_target or "",
        "target_revealed": bool(target_revealed),
        "audio_url": audio_url or None,
        "memo_script": memo_script or "",
        "move": move,
        "force": bool(force),
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    queue = load_json(QUEUE_PATH) or []
    queue.append(entry)
    queue.sort(key=lambda e: e["due"])
    save_queue(queue)
    local = due.astimezone(LOCAL_TZ)
    print(f"Queued {entry['id']} → fires {local:%Y-%m-%d %H:%M %Z}"
          + ("" if entry["force"] or in_waking_window(due)
             else "  (quiet hours — will defer to the next waking tick)"))
    return entry


def cmd_add(args):
    due = parse_due(args.at, getattr(args, "in"))
    entry = enqueue(args.body, due, expected_target=args.expected_target,
                    target_revealed=args.target_revealed, audio_url=args.audio_url,
                    memo_script=args.memo_script, move=args.move, force=args.force)
    if not args.no_commit:
        local = due.astimezone(LOCAL_TZ)
        commit_and_push([QUEUE_PATH], f"Queue push {entry['id']} for {local:%m-%d %H:%M}")


def cmd_list(_args):
    queue = load_json(QUEUE_PATH) or []
    if not queue:
        print("Queue empty.")
        return
    for e in queue:
        local = datetime.fromisoformat(e["due"]).astimezone(LOCAL_TZ)
        flags = "".join([" ⚡force" if e.get("force") else "",
                         " 🎧" if e.get("audio_url") else "",
                         " 🎙" if needs_render(e) else ""])
        print(f"  {e['id']} · {local:%m-%d %H:%M %Z} · {e.get('move','')}{flags}\n"
              f"      {e['body'][:90]}")


def cmd_cancel(args):
    queue = load_json(QUEUE_PATH) or []
    kept = [e for e in queue if e["id"] != args.id]
    if len(kept) == len(queue):
        print(f"No entry {args.id}.")
        return
    save_queue(kept)
    print(f"Cancelled {args.id}.")
    if not args.no_commit:
        commit_and_push([QUEUE_PATH], f"Cancel queued push {args.id}")


def cmd_drain(args):
    """Fire everything due. Non-forced entries also need the waking window and
    room under the daily reach cap — otherwise they stay queued and fire on the
    first eligible tick (deferred, never dropped)."""
    queue = load_json(QUEUE_PATH) or []
    if not queue:
        print("Queue empty — nothing to drain.")
        return
    now = datetime.now(timezone.utc)
    klog = load_json(KNOCK_LOG_PATH) or []
    # count today's reaches the same way the rails do
    n_today = reaches_today(klog, now.astimezone(LOCAL_TZ).date())

    fired, kept = [], []
    non_forced_fired = False
    for e in queue:
        due = datetime.fromisoformat(e["due"])
        if due > now:
            kept.append(e)
            continue
        if not e.get("force") and not in_waking_window(now):
            kept.append(e)
            print(f"  {e['id']} due but quiet hours — deferred.")
            continue
        if not e.get("force") and n_today >= MAX_REACHES_PER_DAY:
            kept.append(e)
            print(f"  {e['id']} due but daily cap ({n_today}/{MAX_REACHES_PER_DAY}) — deferred.")
            continue
        if not e.get("force") and non_forced_fired:
            # One non-forced fire per drain. Originally this kept every reach
            # reply-addressable (pre-correlation, the judge could only target the
            # LAST logged fire); since 2026-07-11 replies carry knock_id, so what
            # remains is pacing — two doses landing in the same minute reads as
            # spam, and the next wake-up (tick, reply, or dispatch) will drain it.
            kept.append(e)
            print(f"  {e['id']} due but another non-forced push already fired this tick — deferred to next tick.")
            continue
        fired.append(e)
        n_today += 1
        if not e.get("force"):
            non_forced_fired = True

    if not fired:
        print("Nothing eligible to fire.")
        return

    for e in fired:
        voice = " 🎙 render" if needs_render(e) else ""
        print(f"  fire {e['id']} · {e.get('move','')}{voice} · {e['body'][:70]}")

    if args.dry_run:
        print(f"[dry-run] would fire {len(fired)}, keep {len(kept)}.")
        return

    # Render before pushing, and COMMIT the mp3s in their own commit before the
    # notification goes out: push_to_phone pre-warms the jsDelivr URL, and
    # jsDelivr can only serve a path that is already on main. Keeping this a
    # separate commit preserves the drain's retry property — a push that fails
    # below leaves the entry queued (save_queue runs after), so it fires again
    # next wake-up against an mp3 that is already published.
    #
    # The mp3 ONLY. The feed rebuild belongs with the knock-log write below, not
    # here — see the comment at that commit.
    rendered = [p for p in (render_entry(e) for e in fired) if p is not None]
    if rendered and not args.no_commit:
        commit_and_push(rendered,
                        f"Scheduled voice dose rendered ({', '.join(e['id'] for e in fired if e.get('memo_script'))})")

    for e in fired:
        # per-entry stamp, not the batch's `now` — it doubles as the reply
        # correlation id, so same-tick fires must never share one
        fired_at = datetime.now(timezone.utc).isoformat()
        # `force` is Andrew asking for it — the chokepoint's exemption, same
        # meaning as the deferral check above.
        push_to_phone(e["body"], e.get("audio_url"), knock_id=fired_at,
                      requested=bool(e.get("force")))
        klog.append({
            "date": now.date().isoformat(),
            "timestamp": fired_at,
            "acted": True,
            "scheduled": True,
            "queue_id": e["id"],
            "modality": "audio" if e.get("audio_url") else "text",
            "move": e.get("move", "scheduled push"),
            "rationale": f"scheduled at {e['queued_at'][:16]} for {e['due'][:16]}",
            "body": e["body"],
            "expected_target": e.get("expected_target", ""),
            "target_revealed": bool(e.get("target_revealed", True)),
            # the reply judge reads what was HEARD, exactly as for an audio knock
            **({"audio_url": e["audio_url"]} if e.get("audio_url") else {}),
            **({"memo_script": e["memo_script"]} if e.get("memo_script") else {}),
        })

    KNOCK_LOG_PATH.write_text(json.dumps(klog, ensure_ascii=False, indent=2), encoding="utf-8")
    save_queue(kept)
    # A scheduled dose is a knock push: a revealed target is a declared exposure
    # (2026-07-26 ledger law), stamped at the same seam that fired it.
    from state_io import LEXICON_PATH
    from sync_state import record_exposure
    exposed = record_exposure([e["expected_target"] for e in fired
                               if e.get("expected_target") and e.get("target_revealed", True)])
    if not args.no_commit:
        # `feed=True` with no mp3, and that pairing is the whole point: the mp3s
        # went out in their own commit above (the CDN pre-warm split, which is
        # what preserves this lane's retry property), but the REBUILD belongs
        # here, after the knock-log write. The rule and its incident now live in
        # publish.publish; this lane was the one that got it wrong, because its
        # legitimate two-commit split swept the rebuild along with the mp3.
        commit_and_push(*publish(
            [QUEUE_PATH, KNOCK_LOG_PATH, LEXICON_PATH if exposed else None],
            f"Scheduled push fired ({', '.join(e['id'] for e in fired)})", feed=True))
    print(f"done — fired {len(fired)}, {len(kept)} still queued.")


def main():
    ap = argparse.ArgumentParser(description="Anna's scheduled-push queue")
    sub = ap.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="queue a push")
    add.add_argument("--at", help="fire time: HH:MM (local), YYYY-MM-DDTHH:MM (local), or ISO+offset")
    add.add_argument("--in", type=float, dest="in", help="fire in N minutes")
    add.add_argument("--body", required=True, help="the notification line (the whole dose)")
    add.add_argument("--expected-target", default="", help="lexicon word/chunk/frame a good reply fires")
    # One default, three readers (2026-08-20). `store_true` defaulted the CLI to
    # False while enqueue() and the drain fallback both defaulted True, so a
    # CLI-queued dose silently meant "not revealed" and its reply could score
    # COLD off a body that had handed the Tamil over. True is the conservative
    # end — it caps the credit at hinted — so an unstated flag can never
    # over-credit. Pass --no-target-revealed when the body genuinely withholds it.
    add.add_argument("--target-revealed", action=argparse.BooleanOptionalAction,
                     default=True,
                     help="the body shows that Tamil (reply caps at hinted). "
                          "Default true; --no-target-revealed lets a reply score cold.")
    add.add_argument("--audio-url", default="", help="optional already-rendered mp3 URL")
    add.add_argument("--memo-script", default="",
                     help="spoken words for a VOICE dose — the drain renders it at fire time")
    add.add_argument("--move", default="scheduled push", help="2-4 word label for the log")
    add.add_argument("--force", action="store_true",
                     help="Andrew asked for this — fire even in quiet hours / over the cap")
    add.add_argument("--no-commit", action="store_true")
    add.set_defaults(func=cmd_add)

    ls = sub.add_parser("list", help="show the queue")
    ls.set_defaults(func=cmd_list)

    cancel = sub.add_parser("cancel", help="remove a queued push")
    cancel.add_argument("id")
    cancel.add_argument("--no-commit", action="store_true")
    cancel.set_defaults(func=cmd_cancel)

    drain = sub.add_parser("drain", help="fire everything due (CI tick / local)")
    drain.add_argument("--dry-run", action="store_true")
    drain.add_argument("--no-commit", action="store_true")
    drain.set_defaults(func=cmd_drain)

    args = ap.parse_args()
    load_env(BASE / ".env")
    args.func(args)


if __name__ == "__main__":
    main()
