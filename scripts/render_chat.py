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
from sync_state import LOCAL_TZ

KNOCK_LOG_PATH = BASE / "progress" / "knock_log.json"
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

    by_day: dict = {}
    for e in spoken:
        by_day.setdefault(_local(e["timestamp"]).date(), []).append(e)

    lines = [HEADER]
    for day in sorted(by_day, reverse=True):
        lines.append(f"\n## {day:%A %Y-%m-%d}\n")
        for e in sorted(by_day[day], key=lambda x: x["timestamp"]):
            t = _local(e["timestamp"])
            tag = " / ".join(p for p in (e.get("modality"), e.get("move")) if p)
            audio = " 🎧" if e.get("audio_url") else ""
            lines += [f"**{t:%H:%M} · Anna**{audio}  ·  {tag}".rstrip(" ·"),
                      _quote(e["body"]), ""]
            exchanges = e.get("exchanges")
            if not exchanges and e.get("reply"):  # pre-2026-07-06 entries: last exchange only
                exchanges = [{"at": e.get("reply_at"), "reply": e["reply"],
                              "verdict": e.get("reply_verdict"),
                              "reply_line": e.get("reply_line")}]
            for x in exchanges or []:
                when = f"{_local(x['at']):%H:%M} · " if x.get("at") else ""
                verdict = (x.get("verdict") or "").upper()
                lines += [f"**{when}Andrew** — **{verdict}**",
                          _quote(x.get("reply", "")), ""]
                if x.get("reply_line"):
                    lines += ["**Anna ↩**", _quote(x["reply_line"]), ""]
            if not exchanges and e.get("response") == "ack":
                lines += ["**Andrew** · 👍 acked", ""]

    CHAT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return CHAT_PATH


if __name__ == "__main__":
    print(render_chat())
