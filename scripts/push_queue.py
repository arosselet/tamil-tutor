#!/usr/bin/env python3
"""
Scheduled pushes — the durable "ping me at X" layer of Anna's outreach.

The knock system decides WHETHER to reach out (agentic, 2h ticks); this queue
delivers pushes Anna already decided on, at a chosen TIME — "ping me in an hour",
"field-mission debrief at 9pm", "deck rep tomorrow 8:15". Entries are fully
composed at add-time (no LLM at fire-time), live in progress/push_queue.json on
main, and are drained by a cheap CI tick (.github/workflows/push-queue.yml,
every 15 min) or by any local drain — whoever gets there first; the queue is
the single source of truth.

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

Secrets: ANNA_PUSH_WEBHOOK_URL (delivery). No LLM key needed.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from morning_knock import (KNOCK_LOG_PATH, LOCAL_TZ, WAKING_START_HOUR,
                           WAKING_END_HOUR, MAX_REACHES_PER_DAY, load_json,
                           load_env, push_to_phone, commit_and_push,
                           fires_today as reaches_today)

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


def in_waking_window(now: datetime) -> bool:
    return WAKING_START_HOUR <= now.astimezone(LOCAL_TZ).hour < WAKING_END_HOUR


def enqueue(body: str, due: datetime, *, expected_target: str = "",
            target_revealed: bool = True, audio_url: str | None = None,
            move: str = "scheduled push", force: bool = False) -> dict:
    """Append one composed push to the queue (no commit — callers own that, so a
    knock/judge run can land the queue write in its existing commit)."""
    entry = {
        "id": f"q{int(time.time())}",
        "due": due.astimezone(timezone.utc).isoformat(),
        "body": body,
        "expected_target": expected_target or "",
        "target_revealed": bool(target_revealed),
        "audio_url": audio_url or None,
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
                    move=args.move, force=args.force)
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
                         " 🎧" if e.get("audio_url") else ""])
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
        fired.append(e)
        n_today += 1

    if not fired:
        print("Nothing eligible to fire.")
        return

    for e in fired:
        print(f"  fire {e['id']} · {e.get('move','')} · {e['body'][:70]}")
        if args.dry_run:
            continue
        push_to_phone(e["body"], e.get("audio_url"))
        klog.append({
            "date": now.date().isoformat(),
            "timestamp": now.isoformat(),
            "acted": True,
            "scheduled": True,
            "queue_id": e["id"],
            "modality": "audio" if e.get("audio_url") else "text",
            "move": e.get("move", "scheduled push"),
            "rationale": f"scheduled at {e['queued_at'][:16]} for {e['due'][:16]}",
            "body": e["body"],
            "expected_target": e.get("expected_target", ""),
            "target_revealed": bool(e.get("target_revealed", True)),
        })

    if args.dry_run:
        print(f"[dry-run] would fire {len(fired)}, keep {len(kept)}.")
        return

    KNOCK_LOG_PATH.write_text(json.dumps(klog, ensure_ascii=False, indent=2), encoding="utf-8")
    save_queue(kept)
    if not args.no_commit:
        commit_and_push([QUEUE_PATH, KNOCK_LOG_PATH],
                        f"Scheduled push fired ({', '.join(e['id'] for e in fired)})")
    print(f"done — fired {len(fired)}, {len(kept)} still queued.")


def main():
    ap = argparse.ArgumentParser(description="Anna's scheduled-push queue")
    sub = ap.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="queue a push")
    add.add_argument("--at", help="fire time: HH:MM (local), YYYY-MM-DDTHH:MM (local), or ISO+offset")
    add.add_argument("--in", type=float, dest="in", help="fire in N minutes")
    add.add_argument("--body", required=True, help="the notification line (the whole dose)")
    add.add_argument("--expected-target", default="", help="lexicon word/chunk/frame a good reply fires")
    add.add_argument("--target-revealed", action="store_true",
                     help="the body shows that Tamil (reply caps at hinted)")
    add.add_argument("--audio-url", default="", help="optional already-rendered mp3 URL")
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
