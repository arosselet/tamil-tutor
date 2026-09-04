#!/usr/bin/env python3
"""
The readable chat record — progress/chat.md rendered from knock_log.json.

knock_log.json is the single source of truth for the phone loop (knocks,
scheduled pushes, judged replies). This renders it as the transcript Andrew
can actually open on his phone: every writer of the log (morning_knock.py,
knock_reply.py, push_queue.py drain) regenerates the file into its own
commit, so progress/chat.md on GitHub is always current. Chained replies
append to a knock's `exchanges` list, so every turn of a chain renders
(entries from before 2026-07-06 kept only their last exchange — those
render as-is; earlier turns survive in this file's git history).

Derived output — never hand-edit. Rebuild any time:

  python scripts/render_chat.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from state_io import KNOCK_LOG_PATH, LOCAL_TZ

CHAT_PATH = BASE / "progress" / "chat.md"

HEADER = """\
# Anna ↔ Andrew — the phone record

Rendered from `knock_log.json` on every knock, reply, and queue drain.
Newest day first. **Derived file — edits here are overwritten.**
"""


def _local(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(LOCAL_TZ)


def _quote(text: str) -> str:
    return "\n".join("> " + ln for ln in (text or "").strip().splitlines())


def render_chat() -> Path:
    log = json.loads(KNOCK_LOG_PATH.read_text(encoding="utf-8")) if KNOCK_LOG_PATH.exists() else []
    spoken = [e for e in log if e.get("acted", True) and e.get("body")]

    # Every TURN is filed under the local day it HAPPENED, not under the day its
    # knock fired (2026-08-28). The old grouping keyed `by_day` off the parent
    # entry's timestamp while each reply printed its own %H:%M, so the two
    # disagreed the moment an answer crossed midnight: an 18:57 knock answered at
    # 09:57 next morning rendered that reply under YESTERDAY's heading, and out of
    # order — sorted behind the 18:57 line it actually followed. The zone
    # conversion was never the bug (04:27Z really is 09:57 here); the day-key was
    # reading off the wrong object. An ack is a turn too, and `response_at`
    # already recorded when it landed, so it now buckets and stamps like the rest.
    turns: list = []                       # (local datetime, rendered block)
    for e in spoken:
        t = _local(e["timestamp"])
        tag = " / ".join(p for p in (e.get("modality"), e.get("move")) if p)
        audio = " 🎧" if e.get("audio_url") else ""
        turns.append((t, [f"**{t:%H:%M} · Anna**{audio}  ·  {tag}".rstrip(" ·"),
                          _quote(e["body"]), ""]))
        # Carried ONLY by a turn that left its knock's day. On-day turns still sit
        # directly under the knock, where a back-pointer would be pure noise.
        back = f"  ·  ↩ {t:%m-%d %H:%M} · {e.get('move') or 'knock'}"

        exchanges = e.get("exchanges")
        if not exchanges and e.get("reply"):  # pre-2026-07-06 entries: last exchange only
            exchanges = [{"at": e.get("reply_at"), "reply": e["reply"],
                          "verdict": e.get("reply_verdict"),
                          "reply_line": e.get("reply_line")}]
        for x in exchanges or []:
            a = _local(x["at"]) if x.get("at") else t
            when = f"{a:%H:%M} · " if x.get("at") else ""
            verdict = (x.get("verdict") or "").upper()
            block = [f"**{when}Andrew** — **{verdict}**"
                     f"{back if a.date() != t.date() else ''}",
                     _quote(x.get("reply", "")), ""]
            if x.get("reply_line"):
                block += ["**Anna ↩**", _quote(x["reply_line"]), ""]
            turns.append((a, block))
        if not exchanges and e.get("response") == "ack":
            a = _local(e["response_at"]) if e.get("response_at") else t
            when = f"{a:%H:%M} · " if e.get("response_at") else ""
            turns.append((a, [f"**{when}Andrew** · 👍 acked"
                              f"{back if a.date() != t.date() else ''}", ""]))

    by_day: dict = {}
    for when_dt, block in turns:
        by_day.setdefault(when_dt.date(), []).append((when_dt, block))

    lines = [HEADER]
    for day in sorted(by_day, reverse=True):
        lines.append(f"\n## {day:%A %Y-%m-%d}\n")
        for _, block in sorted(by_day[day], key=lambda wb: wb[0]):
            lines += block

    # newline="\n" or Windows writes CRLF here and the same log renders to two
    # different files depending on which machine rendered it — chat.md is a
    # tracked DERIVED file that both CI and the laptop regenerate, so byte
    # equality across platforms is the whole contract (s51).
    CHAT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return CHAT_PATH


if __name__ == "__main__":
    print(render_chat())
