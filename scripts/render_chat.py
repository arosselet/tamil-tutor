#!/usr/bin/env python3
"""
The readable chat record — progress/chat.md rendered from knock_log.json.

knock_log.json is the single source of truth for the phone loop (knocks,
scheduled pushes, judged replies). This renders it as the transcript Andrew
can actually open on his phone: every writer of the log (morning_knock.py,
knock_reply.py, push_queue.py drain) regenerates the file into its own
commit, so progress/chat.md on GitHub is always current. Chained replies
overwrite a knock's reply fields in the log — the latest exchange wins in
this file, and each earlier turn survives in the file's git history because
a fresh render was committed per reply.

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
            if e.get("reply"):
                when = f"{_local(e['reply_at']):%H:%M} · " if e.get("reply_at") else ""
                verdict = (e.get("reply_verdict") or "").upper()
                chain = f" · chain ×{e['chained']}" if e.get("chained") else ""
                lines += [f"**{when}Andrew** — **{verdict}**{chain}",
                          _quote(e["reply"]), ""]
                if e.get("reply_line"):
                    lines += ["**Anna ↩**", _quote(e["reply_line"]), ""]
            elif e.get("response") == "ack":
                lines += ["**Andrew** · 👍 acked", ""]

    CHAT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return CHAT_PATH


if __name__ == "__main__":
    print(render_chat())
