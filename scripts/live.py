#!/usr/bin/env python3
"""THE LIVE LANE — a walk-paced conversation with Anna, one turn at a time
(2026-10-26, Andrew; `docs/live_conversation.md`).

WHY IT EXISTS. Ad-hoc Claude Code on a walk failed twice over: no speech back,
so he read dense text on a phone screen, and DESK VERBOSITY — sit-down coffee
lore and chill detail instead of short turns. Audio fixes the first. This lane
tests whether short GATED turns fix the second, before any audio is bolted on.

A GATED ROTATION, NOT OPEN CHAT. Python owns the clock: Anna opens, volleys
`VOLLEYS_PER_GATE` short turns with the target in play, then sets ONE gate where
he says it back; his answer is judged on intent, recast if needed, and the next
target starts. The model only writes the words for the job Python names. Open
talk is seasoning around the gates.

STATE. `progress/live_session.json` holds the transcript for the whole session
— not the message lane's 24h/8-turn window — and nothing in it votes. No turn
moves the learner model: the gates' verdicts are booked at CLOSE, through the
same seams every lane uses (`lexicon_view.observe`, `slips.append_slips`,
`reply_common.record_meta_note`), stamped `channel: "live"`. A fire is capped at
hinted: the target was woven into Anna's own turns, so it was shown.

TWO WAYS IN, ONE STATE MACHINE:

    python scripts/live.py start                 # Anna opens
    python scripts/live.py turn "romba nalla"    # one turn (opens a session if none)
    python scripts/live.py show                  # the transcript so far
    python scripts/live.py close [--publish]     # book what the gates earned
    python scripts/live.py whatsapp              # the runner: one inbound WhatsApp turn

The CLI is the simulation: a Claude Code cloud session (`/live`) relays his line
and prints Anna's verbatim. `whatsapp` is the same `take_turn`, reached through
the bridge (`bridge/whatsapp/`) and a `live-turn` dispatch; it reads the turn off
the event file, answers through Meta's Cloud API, and commits the session file
every turn, because each turn is a separate run. Knocks are untouched.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

import household
import threads
from lexicon_view import observe
from mandates import LIVE_MANDATE, LIVE_TURN_WORDS, SLIP_MANDATE
from observations import FIRE_RESULT, OBSERVATIONS_PATH
from publish import commit_and_push, load_env, publish
from reply_common import REPLY_FALLBACK, gate_reply, record_meta_note
from slips import append_slips
from state_io import (FEEDBACK_LOG_PATH, KNOCK_LOG_PATH, LEXICON_PATH, LIVE_SESSION_PATH,
                      REVIEW_QUEUE_PATH, SLIP_LOG_PATH, load_json, save_json)
from suggest_targets import drill_menu
from writer import STR, arr, ask_json, executor_name, obj, to_phonetic, voice_canon

VOLLEYS_PER_GATE = 2   # Anna's turns between gates — "volley, then a gate"
TARGETS = 4            # gates a session can hold; past them it is just talk
TEACH = 1              # UNSEEN targets a session may teach — the chat dial is ≤1–2 new words
IDLE_CLOSE_HOURS = 3   # WhatsApp has no "end": a turn after this long closes the old session first
END_RE = re.compile(r"^\s*(bye|stop|end|done)\b[\s.!]*$", re.I)
VERDICTS = {"cold", "hinted", "miss", "none"}
SIGN_OFF = "Nalla pesinom — booked. Poittu vaa!"

LIVE_SCHEMA = obj(reply_line=STR, gate_verdict=STR, said=STR, recast=STR, meta_note=STR,
                  slips=arr(tag=STR, said=STR, want=STR, note=STR))

TOO_LONG = ("\n\nOVERRIDE — your last reply_line ran {n} words. The cap is "
            f"{LIVE_TURN_WORDS}. Say the same thing in one short sentence.")

GRAPH = "https://graph.facebook.com/v21.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def words(text: str) -> int:
    return len((text or "").split())


def pick_targets(lex: dict) -> list[dict]:
    """The ticket: the selector's own order, never re-sorted here. TEACH-FIRST
    still holds — an UNSEEN item is never gated cold — but up to `TEACH` of them
    ride as `teach` targets: the first turn on one is a Teach Beat, the gate
    comes after the volleys (2026-10-26, Andrew). Without it a session drew only
    TAUGHT items, and on 10-26 one of twelve was: one gate, then just talk."""
    menu = drill_menu(lex)
    teach = [t for t in menu if t["unseen"]][:TEACH]
    return [{"word": t["word"], "gloss": t["gloss"], **({"teach": True} if t["unseen"] else {})}
            for t in menu if not t["unseen"] or t in teach][:TARGETS]


def calibration() -> str:
    """profile.md's Calibration Notes — the dials Anna is held to, as he set them."""
    try:
        text = (BASE / "progress" / "profile.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    return next((("## " + part).split("\n## ")[0] for part in text.split("\n## ")
                 if part.startswith("Calibration Notes")), "").strip()


def load_session() -> dict | None:
    """The open session, or None. A closed one stays on disk (the last transcript
    is readable until the next start) and is never resumed."""
    sess = load_json(LIVE_SESSION_PATH)
    return sess if sess and not sess.get("closed") else None


def new_session(channel: str) -> dict:
    at = now_iso()
    sess = {"id": at, "channel": channel, "started": at, "last_at": at,
            "targets": pick_targets(load_json(LEXICON_PATH) or {}), "at": 0,
            "phase": "volley", "volleys": 0, "turns": [], "seen_ids": []}
    print(f"   live session {at} · {len(sess['targets'])} target(s): "
          + ", ".join(t["word"] for t in sess["targets"]))
    return sess


def target(sess: dict) -> dict | None:
    return sess["targets"][sess["at"]] if sess["at"] < len(sess["targets"]) else None


def next_job(sess: dict) -> str:
    """THE ROTATION CLOCK — Python's, never the model's."""
    if not sess["turns"]:
        return "open"
    if sess["phase"] == "gate":
        return "judge"
    if target(sess) and sess["volleys"] >= VOLLEYS_PER_GATE:
        return "gate"
    if (target(sess) or {}).get("teach") and sess["volleys"] == 0:
        return "teach"
    return "volley"


def said_in(said: str, text: str) -> bool:
    """A fire must quote what he actually typed — the judge cannot credit a line
    he never wrote (the knock lane's `said_in_reply`, by token)."""
    toks = re.findall(r"\w+", (said or "").lower())
    have = set(re.findall(r"\w+", (text or "").lower()))
    return bool(toks) and all(t in have for t in toks)


def context(sess: dict, job: str, text: str) -> str:
    klog = load_json(KNOCK_LOG_PATH) or []
    tgt = target(sess)
    return json.dumps({
        "job": job,
        "target": tgt or "no targets left — just talk, short turns",
        "andrew_said": text,
        "transcript": [{"who": t["who"], "text": t["text"]} for t in sess["turns"]],
        "threads": threads.block(klog, datetime.now(timezone.utc), arc=True, phone=False),
        "calibration": calibration(),
    }, ensure_ascii=False, indent=2)


def ask(sess: dict, job: str, text: str) -> dict:
    """One writer call for this turn's job, held to walk length with ONE re-ask.
    Still long after it is recorded as `over_cap` on the turn, never trimmed:
    a cut sentence says less than a long one, and the overrun IS the evidence
    this simulation exists to collect."""
    system = (voice_canon() + "\n\n---\n\n" + household.load() + "\n\n---\n\n"
              + LIVE_MANDATE + ("\n" + SLIP_MANDATE if job == "judge" else ""))
    user = context(sess, job, text)
    print(f"   [live · {job}] {executor_name()}")
    d = ask_json(system, user, LIVE_SCHEMA, answer_tokens=600)
    n = words(d.get("reply_line"))
    if n > LIVE_TURN_WORDS:
        print(f"   ⚠ {n} words — over the walk cap ({LIVE_TURN_WORDS}); one re-ask")
        again = ask_json(system + TOO_LONG.format(n=n), user, LIVE_SCHEMA, answer_tokens=600)
        if words(again.get("reply_line")) and words(again.get("reply_line")) < n:
            d = again
    d["over_cap"] = words(d.get("reply_line")) > LIVE_TURN_WORDS
    d["system"] = system
    return d


def grade(d: dict, text: str) -> str:
    """The gate's verdict, made honest by Python: an unknown word is no grade, a
    fire must quote his text, and COLD IS CAPPED AT HINTED — the volleys put the
    target in his ear first, so the gate is never a cold test."""
    v = str(d.get("gate_verdict") or "none").strip().lower()
    v = v if v in VERDICTS else "none"
    if v in ("cold", "hinted") and not said_in(d.get("said", ""), text):
        print(f"   ⚠ judge credited {d.get('said')!r}, not in what he typed — no grade")
        v = "none"
    return "hinted" if v == "cold" else v


def take_turn(sess: dict, text: str) -> str:
    """One turn: his line in, Anna's line out, the clock advanced. Writes nothing
    to the books — only the session dict, which the caller saves."""
    job = next_job(sess)
    tgt = target(sess)
    d = ask(sess, job, text)
    held = gate_reply(d, d.pop("system"), "live", sess["id"])
    # Judged first, then made readable: a stray Tamil glyph mid-line (seen in the first
    # simulation, "sariyாna") goes to phonetics like every other read surface.
    line = to_phonetic((d.get("reply_line") or "").strip() or REPLY_FALLBACK, label="live turn")
    at = now_iso()
    if text:
        mine = {"who": "andrew", "at": at, "text": text}
        if job == "judge" and tgt:
            mine.update(target=tgt["word"], verdict=grade(d, text),
                        said=d.get("said", ""), recast=d.get("recast", ""),
                        slips=d.get("slips") or [])
        if (d.get("meta_note") or "").strip():
            mine["meta_note"] = d["meta_note"].strip()
        sess["turns"].append(mine)
    sess["turns"].append({"who": "anna", "at": at, "text": line, "job": job,
                          "target": (tgt or {}).get("word", ""),
                          **({"over_cap": True} if d["over_cap"] else {}),
                          **({"held": len(held)} if held else {})})
    if job == "gate":
        sess["phase"] = "gate"
    elif job == "judge":
        sess.update(phase="volley", volleys=0, at=sess["at"] + 1)
    elif job in ("volley", "teach"):
        sess["volleys"] += 1
    sess["last_at"] = at
    return line


def close(sess: dict) -> list[Path]:
    """BOOK WHAT THE GATES EARNED, once, at the end. A gate he did not try books
    nothing; talk alone never moves the learner model. Returns the books written."""
    graded = [t for t in sess["turns"] if t.get("verdict") in ("cold", "hinted", "miss")]
    # A Teach Beat books only if he wrote back after it: on WhatsApp a sent line is
    # not a read one. Taught AND attended, because `live` is not self-attending.
    taught = [t for i, t in enumerate(sess["turns"]) if t.get("job") == "teach"
              and any(u["who"] == "andrew" for u in sess["turns"][i + 1:])]
    events = [{"word": t["target"], "channel": "live", "kind": k, "at": t["at"],
               "source": f"live:{sess['id']}"} for t in taught for k in ("taught", "attended")]
    events += [{"word": t["target"], "channel": "live", "kind": "tested", "axis": "production",
                "result": FIRE_RESULT.get(t["verdict"], "wrong"), "source": f"live:{sess['id']}",
                "note": t.get("said") or t["text"][:80]} for t in graded]
    slips = [s for t in sess["turns"] for s in t.get("slips") or []]
    notes = [t["meta_note"] for t in sess["turns"] if t.get("meta_note")]
    if events:
        observe(events)
    if slips:
        append_slips(slips, lane="live", modality="live")
    for n in notes:
        record_meta_note({"meta_note": n})
    sess["closed"] = now_iso()
    save_json(LIVE_SESSION_PATH, sess)
    print(f"   closed: {len(taught)} taught, {len(graded)} gate(s) booked, {len(slips)} slip(s), {len(notes)} note(s)")
    return [LIVE_SESSION_PATH] + ([OBSERVATIONS_PATH, LEXICON_PATH] if events else []) \
        + ([SLIP_LOG_PATH] if slips else []) + ([FEEDBACK_LOG_PATH] if notes else [])


def stale(sess: dict) -> bool:
    last = datetime.fromisoformat(sess["last_at"].replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - last).total_seconds() > IDLE_CLOSE_HOURS * 3600


# ── WhatsApp — the runner side. The bridge forwards only {text, id}: his number
# never rides the dispatch, because the event payload is readable in a public
# repo's run. Who to answer is a secret, WHATSAPP_TO.

def whatsapp_send(text: str) -> None:
    """One text message through Meta's Cloud API. Raises on failure, so a turn
    that could not answer is a red run, never a silent one."""
    body = json.dumps({"messaging_product": "whatsapp", "to": os.environ["WHATSAPP_TO"],
                       "type": "text", "text": {"body": text}}).encode()
    req = urllib.request.Request(f"{GRAPH}/{os.environ['WHATSAPP_PHONE_ID']}/messages", data=body,
                                 headers={"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status >= 300:
            raise RuntimeError(f"WhatsApp send failed: HTTP {r.status}")


def whatsapp_turn(payload: dict, send=whatsapp_send) -> list[Path]:
    """One inbound message → one answer → the session committed. Idempotent on
    the message id, because Meta re-delivers a webhook it thinks was missed."""
    text, mid = (payload.get("text") or "").strip(), payload.get("id") or ""
    sess = load_session()
    if sess and mid and mid in sess.get("seen_ids", []):
        print(f"   duplicate delivery {mid} — already answered")
        return []
    books = []
    if sess and stale(sess):
        print(f"   session {sess['id']} idle past {IDLE_CLOSE_HOURS}h — closing it first")
        books += close(sess)
        sess = None
    if END_RE.match(text):
        books += close(sess) if sess else []
        send(SIGN_OFF)
        return books
    sess = sess or new_session("whatsapp")
    sess["seen_ids"] = (sess.get("seen_ids", []) + [mid])[-20:] if mid else sess.get("seen_ids", [])
    send(take_turn(sess, text))
    save_json(LIVE_SESSION_PATH, sess)
    held = sess["turns"][-1].get("held")
    return books + [LIVE_SESSION_PATH, REVIEW_QUEUE_PATH if held else None]


def main():
    ap = argparse.ArgumentParser(description="The live lane — a gated, walk-paced conversation")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start", help="Open a session; Anna speaks first")
    t = sub.add_parser("turn", help="One turn from Andrew")
    t.add_argument("text")
    sub.add_parser("show", help="Print the transcript so far")
    c = sub.add_parser("close", help="Book what the gates earned")
    c.add_argument("--publish", action="store_true", help="commit and push the books")
    sub.add_parser("whatsapp", help="The runner: one live-turn dispatch off $GITHUB_EVENT_PATH")
    args = ap.parse_args()
    load_env(BASE / ".env")

    if args.cmd == "whatsapp":
        path = os.environ.get("GITHUB_EVENT_PATH", "")
        payload = json.loads(Path(path).read_text(encoding="utf-8")).get("client_payload") or {}
        books = whatsapp_turn(payload)
        if books:
            commit_and_push(*publish(books, "Live: turn (whatsapp)"))
        return

    sess = load_session()
    if args.cmd == "show":
        for turn in (sess or {}).get("turns", []):
            mark = f"  [{turn['verdict']}]" if turn.get("verdict") else ""
            print(f"{'ANNA' if turn['who'] == 'anna' else 'YOU '}: {turn['text']}{mark}")
        return
    if args.cmd == "close":
        if not sess:
            print("no live session open")
            return
        books = close(sess)
        if args.publish:
            commit_and_push(*publish(books, "Live: session closed"))
        return
    if args.cmd == "start" and sess:
        print(f"a session is already open ({sess['id']}) — `close` it first")
        sys.exit(1)
    sess = sess or new_session("cli")
    line = take_turn(sess, args.text if args.cmd == "turn" else "")
    save_json(LIVE_SESSION_PATH, sess)
    print(f"\nANNA: {line}")


if __name__ == "__main__":
    main()
