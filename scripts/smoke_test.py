#!/usr/bin/env python3
"""
Smoke test for the rep channel — the plumbing that carries knocks, judged
replies, and scheduled pushes. Drives the REAL production functions against a
sandbox copy of the repo with the outside-world boundaries stubbed: the LLM call,
the TTS render (audio scenarios only), push_to_phone, and commit_and_push. No
secrets, no network, no writes outside the sandbox. CI runs it on any push that touches the machinery (smoke.yml);
locally:

  python scripts/smoke_test.py

A fixed bug becomes a case here the day it's fixed:
  #1  queue drain: oldest-due fires first, one non-forced per tick (2026-07-03)
  #2  prose-wrapped LLM JSON killed a knock tick (2026-07-04)
"""
import argparse
import importlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REAL_BASE = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    print(f"  [{'ok' if cond else 'FAIL'}] {name}" + ("" if cond else f" — {detail}"))
    if not cond:
        FAILURES.append(name)


class Recorder(list):
    """Stub for push_to_phone / commit_and_push — records instead of acting."""
    def __call__(self, *args, **kwargs):
        self.append(args)


# ── Sandbox ───────────────────────────────────────────────────────────────────

def make_sandbox(tmp: Path) -> Path:
    """Copy the repo (minus git/audio/secrets) and reset progress/ to day-zero
    fixtures — the .example files finally earn their keep as test fixtures."""
    sb = tmp / "repo"
    shutil.copytree(REAL_BASE, sb, ignore=shutil.ignore_patterns(
        ".git", ".env", "__pycache__", "audio", "published_audio",
        "*.mp3", "*.mp4", "*.ipynb", "*.jpg"))
    prog = sb / "progress"
    for ex in prog.glob("*.example"):
        shutil.copy(ex, prog / ex.name[: -len(".example")])
    (prog / "knock_log.json").write_text("[]", encoding="utf-8")
    (prog / "push_queue.json").write_text("[]", encoding="utf-8")
    return sb


def load_modules(sb: Path):
    """Import the SANDBOX copies of the scripts — their BASE resolves to the
    sandbox, so every path constant lands there without patching."""
    real_scripts = str(REAL_BASE / "scripts")
    sys.path = [p for p in sys.path if p != real_scripts]
    sys.path.insert(0, str(sb / "scripts"))
    mk = importlib.import_module("morning_knock")
    kr = importlib.import_module("knock_reply")
    pq = importlib.import_module("push_queue")
    check("modules imported from sandbox", mk.__file__.startswith(str(sb)),
          f"morning_knock loaded from {mk.__file__}")
    return mk, kr, pq


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Scenarios ─────────────────────────────────────────────────────────────────

def s1_parse_llm_json(mk):
    print("\n1. LLM response parsing (regression #2)")
    p = mk.parse_llm_json
    check("clean object", p('{"a": 1}') == {"a": 1})
    check("code fence", p('```json\n{"a": 1}\n```') == {"a": 1})
    check("prose-wrapped", p('My decision:\n{"a": {"b": 2}}\nHope that helps!')
          == {"a": {"b": 2}})
    try:
        p("no json here")
        check("garbage raises", False, "did not raise")
    except (json.JSONDecodeError, ValueError):
        check("garbage raises", True)


def s2_rails_gate(mk, klog_path: Path):
    print("\n2. Rails gate")
    noon_l = datetime.now(mk.LOCAL_TZ).replace(hour=12, minute=0, second=0, microsecond=0)
    noon = noon_l.astimezone(timezone.utc)
    night = noon_l.replace(hour=3).astimezone(timezone.utc)
    today = noon_l.date().isoformat()

    def fired(hours_ago: float) -> dict:
        ts = noon - timedelta(hours=hours_ago)
        return {"date": today, "timestamp": ts.isoformat(), "acted": True,
                "modality": "text", "move": "smoke", "body": "x"}

    write_json(klog_path, [])
    ok, why = mk.rails_gate(False, now=noon)
    check("empty log at noon → eligible", ok, why)
    ok, why = mk.rails_gate(False, now=night)
    check("3am → quiet hours", not ok and "quiet" in why, why)
    ok, why = mk.rails_gate(True, now=night)
    check("--force overrides quiet hours", ok, why)

    write_json(klog_path, [fired(12 - 3 * i) for i in range(mk.MAX_REACHES_PER_DAY)])
    ok, why = mk.rails_gate(False, now=noon)
    check("daily cap blocks", not ok and "cap" in why, why)

    write_json(klog_path, [fired(1)])
    ok, why = mk.rails_gate(False, now=noon)
    check("min gap blocks a 1h-ago fire", not ok and "gap" in why, why)

    entry = fired(10)
    entry["next_check"] = (noon + timedelta(hours=2)).isoformat()
    write_json(klog_path, [entry])
    ok, why = mk.rails_gate(False, now=noon)
    check("Anna's future next_check blocks", not ok and "next_check" in why, why)
    write_json(klog_path, [])


def canned_decision(act: bool, body: str = "") -> dict:
    return {"act": act, "modality": "text" if act else "silence", "move": "smoke move",
            "rationale": "smoke", "next_check_hours": 3, "notification_body": body,
            "expected_target": "", "target_revealed": False, "schedule": None}


def s3_knock_paths(mk, sb: Path):
    print("\n3. Knock fire + silence paths")
    klog_path = sb / "progress" / "knock_log.json"
    chat_path = sb / "progress" / "chat.md"
    mk.rails_gate = lambda force, now=None: (True, "smoke-open")
    mk.build_digest = lambda: "SMOKE DIGEST"
    pushes, commits = Recorder(), Recorder()
    mk.push_to_phone, mk.commit_and_push = pushes, commits

    mk.decide = lambda digest: canned_decision(False)
    sys.argv = ["morning_knock.py"]
    mk.main()
    log = read_json(klog_path)
    check("silence logs acted=false", len(log) == 1 and log[0]["acted"] is False,
          f"log={log}")
    check("silence pushes nothing", len(pushes) == 0)
    check("silence still commits the log", len(commits) == 1)

    body = "smoke dose — sollu da"
    mk.decide = lambda digest: canned_decision(True, body)
    mk.main()
    log = read_json(klog_path)
    check("fire logs acted=true with body", log[-1].get("acted") and log[-1]["body"] == body)
    check("fire pushes exactly once", len(pushes) == 1 and pushes[0][0] == body)
    check("fire commits knock_log + chat.md",
          len(commits) == 2 and any("chat.md" in str(p) for p in commits[-1][0]),
          f"paths={commits[-1][0] if commits else None}")
    check("chat.md carries the dose", body in chat_path.read_text(encoding="utf-8"))


def s4_normalize(kr):
    print("\n4. Verdict normalization")
    n = kr.normalize_verdict
    d = n({"verdict": "hinted", "fired": ["போதும்"], "reply_line": "x"})
    check("flat legacy fired tolerated", d["fired"] == [{"word": "போதும்", "verdict": "hinted"}])
    d = n({"verdict": "hinted", "fired": [{"word": "a", "verdict": "cold"},
                                          {"word": "b", "verdict": "hinted"}]})
    check("overall verdict = best word", d["verdict"] == "cold")
    d = n({"verdict": "cold", "fired": []})
    check("scored-but-empty degrades to miss", d["verdict"] == "miss")
    d = n({"verdict": "??", "fired": [{"word": "a", "verdict": "cold"}]})
    check("junk verdict → chat, fired cleared", d["verdict"] == "chat" and d["fired"] == [])


def canned_verdict(fired: list, reply_line: str = "adhu dhaan") -> dict:
    best = ("cold" if any(v == "cold" for _, v in fired) else
            "hinted" if fired else "chat")
    return {"verdict": best, "reply_line": reply_line, "rationale": "smoke",
            "fired": [{"word": w, "verdict": v} for w, v in fired],
            "follow_up_ask": "", "follow_up_target": "",
            "follow_up_target_revealed": True, "meta_note": "", "schedule": None}


def s5_reply_judge(mk, kr, sb: Path):
    print("\n5. Reply judge → production axis")
    prog = sb / "progress"
    lex_path = prog / "lexicon.json"
    klog_path = prog / "knock_log.json"
    write_json(lex_path, {
        "போதும்": {"gloss": "Enough", "phonetic": ["podhum"], "recognition": "solid",
                    "production": "none", "seen_in": [], "last_surfaced": "2026-07-01"},
        "ரொம்ப பிடிச்சிருக்கு": {"gloss": "I really like it",
                                   "phonetic": ["romba pidichirukku"],
                                   "recognition": "solid", "production": "none",
                                   "seen_in": [], "last_surfaced": "2026-07-01"},
    })
    kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
    now = datetime.now(timezone.utc)

    def knock(body: str, target: str, revealed: bool) -> dict:
        return {"date": now.date().isoformat(), "timestamp": now.isoformat(),
                "acted": True, "modality": "challenge", "move": "smoke",
                "body": body, "expected_target": target, "target_revealed": revealed}

    def reply(text: str, verdict: dict):
        kr.judge = lambda k, r, t, h=None: verdict
        sys.argv = ["knock_reply.py", text]
        kr.main()

    # unaided fire on an unrevealed target → cold lands, hinted word stays hinted
    log = read_json(klog_path)
    log.append(knock("say the line — go", "ரொம்ப பிடிச்சிருக்கு", False))
    write_json(klog_path, log)
    reply("romba pidichirukku, podhum",
          canned_verdict([("ரொம்ப பிடிச்சிருக்கு", "cold"), ("போதும்", "hinted")]))
    lex = read_json(lex_path)
    check("cold fire lands", lex["ரொம்ப பிடிச்சிருக்கு"]["production"] == "cold")
    check("hinted word records hinted", lex["போதும்"]["production"] == "hinted")
    entry = read_json(klog_path)[-1]
    check("cold pace credits the unrevealed word only",
          entry.get("reply_fired_cold") == ["ரொம்ப பிடிச்சிருக்கு"],
          f"got {entry.get('reply_fired_cold')}")

    # revealed target → judge's 'cold' is capped to hinted deterministically
    log = read_json(klog_path)
    log.append(knock("fire it back: podhum — one shot", "போதும்", True))
    write_json(klog_path, log)
    reply("podhum", canned_verdict([("போதும்", "cold")]))
    lex = read_json(lex_path)
    check("revealed-cap holds production at hinted", lex["போதும்"]["production"] == "hinted")
    check("revealed-cap credits no cold pace",
          read_json(klog_path)[-1].get("reply_fired_cold") == [])

    # upgrades only — a hinted re-fire never demotes a cold word
    lex["ரொம்ப பிடிச்சிருக்கு"]["production"] = "cold"
    write_json(lex_path, lex)
    log = read_json(klog_path)
    log.append(knock("she just finished cooking — one line", "ரொம்ப பிடிச்சிருக்கு", False))
    write_json(klog_path, log)
    reply("romba pidichirukku", canned_verdict([("ரொம்ப பிடிச்சிருக்கு", "hinted")]))
    check("phone rep never demotes",
          read_json(lex_path)["ரொம்ப பிடிச்சிருக்கு"]["production"] == "cold")

    # chat verdict moves nothing
    before = lex_path.read_text(encoding="utf-8")
    log = read_json(klog_path)
    log.append(knock("debrief — how did it land?", "", False))
    write_json(klog_path, log)
    reply("it went great, talk tomorrow", canned_verdict([]))
    check("chat verdict leaves the lexicon untouched",
          lex_path.read_text(encoding="utf-8") == before)

    # meta-direction in a reply → feedback ledger (2026-07-05)
    flog_path = prog / "feedback_log.json"
    n_before = len(read_json(flog_path)) if flog_path.exists() else 0
    log = read_json(klog_path)
    log.append(knock("gauntlet line — fire it", "போதும்", False))
    write_json(klog_path, log)
    v = canned_verdict([("போதும்", "hinted")])
    v["meta_note"] = "podhum is old muscle memory — stop teaching it"
    reply("Podhum (old muscle memory, this one's mine)", v)
    flog = read_json(flog_path)
    check("meta_note lands in the feedback ledger",
          len(flog) == n_before + 1 and flog[-1]["note"].startswith("[phone]"),
          str(flog[-1:]))


def s6_queue_drain(mk, pq, sb: Path):
    print("\n6. Queue drain (regression #1)")
    prog = sb / "progress"
    klog_path, q_path = prog / "knock_log.json", prog / "push_queue.json"
    pushes, commits = Recorder(), Recorder()
    pq.push_to_phone, pq.commit_and_push = pushes, commits
    saved = (pq.WAKING_START_HOUR, pq.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY)
    now = datetime.now(timezone.utc)

    def q_entry(qid: str, due_hours: float, force: bool = False) -> dict:
        return {"id": qid, "due": (now + timedelta(hours=due_hours)).isoformat(),
                "body": f"dose {qid}", "expected_target": "", "target_revealed": True,
                "audio_url": None, "move": "smoke", "force": force,
                "queued_at": now.isoformat()}

    args = argparse.Namespace(dry_run=False, no_commit=False)
    try:
        pq.WAKING_START_HOUR, pq.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 99
        write_json(klog_path, [])
        write_json(q_path, [q_entry("qOLD", -2), q_entry("qNEW", -1), q_entry("qFUT", +6)])
        pq.cmd_drain(args)
        kept = [e["id"] for e in read_json(q_path)]
        check("one non-forced per tick, OLDEST first",
              len(pushes) == 1 and pushes[0][0] == "dose qOLD", f"pushes={list(pushes)}")
        check("newer + future entries deferred, not dropped", kept == ["qNEW", "qFUT"],
              f"kept={kept}")
        check("fired entry logged with queue_id",
              read_json(klog_path)[-1].get("queue_id") == "qOLD")
        pq.cmd_drain(args)
        check("next tick fires the deferred one",
              len(pushes) == 2 and pushes[1][0] == "dose qNEW")

        # quiet hours defer non-forced; --force punches through
        pq.WAKING_START_HOUR, pq.WAKING_END_HOUR = 0, 0
        write_json(q_path, [q_entry("qQUIET", -1), q_entry("qFORCE", -1, force=True)])
        pq.cmd_drain(args)
        check("quiet hours defers non-forced, fires forced",
              len(pushes) == 3 and pushes[2][0] == "dose qFORCE"
              and [e["id"] for e in read_json(q_path)] == ["qQUIET"])

        # daily cap defers non-forced; forced ignores it
        pq.WAKING_START_HOUR, pq.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 0
        write_json(q_path, [q_entry("qCAP", -1), q_entry("qFORCE2", -1, force=True)])
        pq.cmd_drain(args)
        check("cap defers non-forced, fires forced",
              len(pushes) == 4 and pushes[3][0] == "dose qFORCE2"
              and [e["id"] for e in read_json(q_path)] == ["qCAP"])
    finally:
        pq.WAKING_START_HOUR, pq.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = saved


def s8_variety_and_decay(mk, kr, sb: Path):
    """The 2026-07-05 push-feedback fixes: demand-streak surfaced to the digest,
    body budgets, continuity decay clock, UNSEEN teach-first flags."""
    print("\n8. Variety + decay helpers")
    now = datetime.now(timezone.utc)

    # demand streak counts trailing FIRES that carried an ask; silence skipped
    klog = [
        {"acted": True, "expected_target": "x"},
        {"acted": True, "expected_target": ""},
        {"acted": True, "expected_target": "y"},
        {"acted": False, "expected_target": ""},
        {"acted": True, "expected_target": "z"},
    ]
    check("demand_streak counts trailing asks", mk.demand_streak(klog) == 2,
          str(mk.demand_streak(klog)))
    check("demand_streak zero after a no-ask fire",
          mk.demand_streak([{"acted": True, "expected_target": ""}]) == 0)

    # the rails digest carries the no-ask directive once the streak hits 2
    fired = [{"acted": True, "expected_target": "x", "date": now.date().isoformat(),
              "timestamp": (now - timedelta(hours=5 - i)).isoformat()}
             for i in range(2)]
    room = mk.remaining_room(fired, now)
    check("digest carries the NO-ASK directive at streak 2", "NO-ASK" in room,
          room.splitlines()[-1])

    # lock-screen body budget
    check("over_budget flags a long body",
          mk.over_budget("x" * 200) and not mk.over_budget("x" * 100))

    # continuity decay clock (judge context)
    k = {"timestamp": (now - timedelta(hours=5)).isoformat()}
    h = kr.hours_since_exchange(k, now)
    check("hours_since_exchange reads the knock time", h is not None and 4.9 < h < 5.1, str(h))
    k["reply_at"] = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    h = kr.hours_since_exchange(k, now)
    check("last exchange (reply_at) wins over the knock time",
          h is not None and 0.9 < h < 1.1, str(h))
    check("missing timestamps → None", kr.hours_since_exchange({}, now) is None)

    # never-soaked deck items are flagged UNSEEN on the menu (teach before quiz)
    lex_path = sb / "progress" / "lexicon.json"
    write_json(lex_path, {
        "வணக்கம்": {"gloss": "hello", "phonetic": ["vanakkam"], "recognition": "struggled",
                     "production": "none", "seen_in": [], "last_surfaced": None,
                     "deck": "trip", "direction": "fire"},
    })
    menu = mk.deck_due_list()
    check("never-soaked deck item flagged UNSEEN", "UNSEEN" in menu, menu)
    lex = read_json(lex_path)
    lex["வணக்கம்"]["last_surfaced"] = "2026-07-01"
    write_json(lex_path, lex)
    check("soaked item loses the UNSEEN flag", "UNSEEN" not in mk.deck_due_list())


def s7_integrity(sb: Path):
    print("\n7. State integrity sweep")
    for f in sorted((sb / "progress").glob("*.json")):
        try:
            read_json(f)
            check(f"{f.name} valid JSON", True)
        except json.JSONDecodeError as e:
            check(f"{f.name} valid JSON", False, str(e))
    for e in read_json(sb / "progress" / "knock_log.json"):
        if not ("date" in e and "timestamp" in e):
            check("knock_log entries carry date+timestamp", False, str(e)[:80])
            break
    else:
        check("knock_log entries carry date+timestamp", True)


def s9_audio_knock_feed(mk, sb: Path):
    print("\n9. Audio knock refreshes the feed (all audio -> rss.xml, 2026-07-05)")
    mk.rails_gate = lambda force, now=None: (True, "smoke-open")
    mk.build_digest = lambda: "SMOKE DIGEST"
    pushes, commits = Recorder(), Recorder()
    mk.push_to_phone, mk.commit_and_push = pushes, commits

    async def fake_render(memo_script, out_path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"smoke-mp3")
    mk.render_memo = fake_render

    d = canned_decision(True, "smoke audio dose")
    d["modality"] = "audio"
    d["memo_script"] = "வணக்கம் டா"
    mk.decide = lambda digest: d
    sys.argv = ["morning_knock.py"]
    mk.main()

    paths = [str(p) for p in commits[-1][0]]
    check("audio knock commits the mp3", any("knocks" in p for p in paths), f"paths={paths}")
    check("audio knock commits rss.xml", any(p.endswith("rss.xml") for p in paths), f"paths={paths}")
    check("audio knock logs audio_url",
          bool(read_json(sb / "progress" / "knock_log.json")[-1].get("audio_url")))


def main():
    with tempfile.TemporaryDirectory(prefix="tamil-smoke-") as tmp:
        sb = make_sandbox(Path(tmp))
        print(f"sandbox: {sb}")
        mk, kr, pq = load_modules(sb)
        s1_parse_llm_json(mk)
        s2_rails_gate(mk, sb / "progress" / "knock_log.json")
        s3_knock_paths(mk, sb)
        s4_normalize(kr)
        s5_reply_judge(mk, kr, sb)
        s6_queue_drain(mk, pq, sb)
        s7_integrity(sb)
        s8_variety_and_decay(mk, kr, sb)
        s9_audio_knock_feed(mk, sb)

    print(f"\n{'ALL GREEN' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
