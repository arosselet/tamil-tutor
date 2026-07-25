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
  #3  chained follow-up overwrote the original ask; chat lost chained replies (2026-07-06)
  #4  hinted-forever: reveal-capped fires now graduate cross-day (2026-07-08)
  #5  volley knock: binding targets + deterministic chain advance (2026-07-08)
  #6  eavesdrop dose: catch replies move recognition only, never production (2026-07-09)
  #7  stale clone read yesterday's story; comma-joined soak payload never matched (2026-07-15)
  #8  [SFX] lines silently dropped by the renderer — now a beat of air (2026-07-18)
  #9  special_* string-mission sidecar crashed the ticket sort; the ticket now
      smoke-runs end-to-end on day-zero state (2026-07-19, inbox item)
  #10 two renders shared one scratch dir — the first to finish deleted it under
      the second, losing a draft episode; hosts without secrets now skip
      instead of retrying hourly (2026-07-23)
  #11 an eavesdrop tape hearsayed about an unnamed அவங்க and the drift question
      asked WHO — unanswerable from the audio; the thread-blind catch judge then
      re-asked a catch that had already landed on turn 1 (2026-07-25)
  #12 the deck selector had no staleness term: tier → ripeness → alphabetical
      froze the head of every tier, 45 of 70 fire items were never asked once,
      and cold/total reported a winning sprint throughout (2026-07-25)
"""
import argparse
import email.utils
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import date as date_cls, datetime, timedelta, timezone
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
    # 2026-07-07: model returned single-quoted Python dict; {..} slice fallback found
    # braces but json.loads rejected single quotes → crash. ast.literal_eval now catches it.
    check("single-quoted keys", p("{'act': True, 'modality': 'text'}")
          == {"act": True, "modality": "text"})
    check("python-dict in prose", p("Here ya go: {'a': 1, 'b': False}")
          == {"a": 1, "b": False})
    # 2026-07-13: judge narrated its reasoning — including a literal `{noun}` frame
    # gloss — BEFORE its ```json fence; startswith fence-strip never fired and the
    # {..} slice bit on `{noun}` → crash, and a real cold fire was lost. Fenced
    # block anywhere in the text now wins.
    check("prose with {braces} before a json fence",
          p('The `{noun} kudunga` frame applies.\n```json\n{"verdict": "cold"}\n```')
          == {"verdict": "cold"})
    check("last fence wins when prose precedes multiple fences",
          p('thinking…\n```json\n{"draft": 1}\n```\nrevised:\n```json\n{"final": 2}\n```')
          == {"final": 2})
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

    mk.decide = lambda digest, vt=None: canned_decision(False)
    sys.argv = ["morning_knock.py"]
    mk.main()
    log = read_json(klog_path)
    check("silence logs acted=false", len(log) == 1 and log[0]["acted"] is False,
          f"log={log}")
    check("silence pushes nothing", len(pushes) == 0)
    check("silence still commits the log", len(commits) == 1)

    body = "smoke dose — sollu da"
    mk.decide = lambda digest, vt=None: canned_decision(True, body)
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
        kr.judge = lambda k, r, t, h=None, rr=None: verdict
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
    body budgets, continuity decay clock, UNSEEN teach-first flags. Plus the
    2026-07-11 lore format cooldown (four frame-etymology memos in four days)."""
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

    # lore format cooldown: SPENT inside the window, vein reminder after, silent when none
    lored = [{"acted": True, "move": "lore memo: -aachu frame",
              "timestamp": (now - timedelta(days=1)).isoformat()}]
    check("digest marks lore SPENT inside the cooldown",
          "SPENT" in mk.remaining_room(lored, now))
    lored[0]["timestamp"] = (now - timedelta(days=mk.LORE_COOLDOWN_DAYS + 2)).isoformat()
    check("expired cooldown becomes the different-vein reminder",
          "different vein" in mk.remaining_room(lored, now))
    check("no lore fires → no lore line in the rails",
          "lore" not in mk.remaining_room([], now).lower())

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


def s14_reply_correlation(kr):
    """2026-07-11 (KF-9): notifications stack (unique HA tag per knock); taps and
    replies carry the knock's log timestamp back as knock_id. find_knock targets
    the exact entry; a missing/stale/empty id returns None so callers fall back
    to last-fired (pre-migration notifications stay judgeable)."""
    print("\n14. Reply correlation (stacked notifications)")
    klog = [
        {"acted": True, "timestamp": "2026-07-11T08:00:00+00:00", "move": "volley"},
        {"acted": False, "timestamp": "2026-07-11T10:00:00+00:00", "move": "silence"},
        {"acted": True, "timestamp": "2026-07-11T12:00:00+00:00", "move": "lore memo"},
    ]
    hit = kr.find_knock(klog, "2026-07-11T08:00:00+00:00")
    check("find_knock targets an older stacked knock by id",
          hit is not None and hit["move"] == "volley")
    check("unknown id → None (caller falls back to last-fired)",
          kr.find_knock(klog, "2026-07-13T00:00:00+00:00") is None)
    check("empty id → None (id-less events keep last-fired behavior)",
          kr.find_knock(klog, "") is None)
    check("silence entries never match (no notification existed)",
          kr.find_knock(klog, "2026-07-11T10:00:00+00:00") is None)


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

    async def fake_render(memo_script, out_path, voice=None):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"smoke-mp3")
    mk.render_memo = fake_render

    d = canned_decision(True, "smoke audio dose")
    d["modality"] = "audio"
    d["memo_script"] = "வணக்கம் டா"
    mk.decide = lambda digest, vt=None: d
    sys.argv = ["morning_knock.py"]
    mk.main()

    paths = [str(p) for p in commits[-1][0]]
    check("audio knock commits the mp3", any("knocks" in p for p in paths), f"paths={paths}")
    check("audio knock commits rss.xml", any(p.endswith("rss.xml") for p in paths), f"paths={paths}")
    check("audio knock logs audio_url",
          bool(read_json(sb / "progress" / "knock_log.json")[-1].get("audio_url")))


def s10_chain_history(mk, kr, sb: Path):
    """#3 (2026-07-06): a chained follow-up must move the PIN, not overwrite the
    original ask; every exchange lands in `exchanges`; chat.md renders the full
    chain; revealed_recently() computes reveals from the log, not model memory."""
    print("\n10. Chain history + grounded reveals (regression #3)")
    prog = sb / "progress"
    lex_path, klog_path = prog / "lexicon.json", prog / "knock_log.json"
    write_json(lex_path, {
        "ஒரு மாசம் இருப்போம்": {"gloss": "We're staying one month",
                                  "phonetic": ["oru maasam iruppom"],
                                  "recognition": "solid", "production": "none", "seen_in": []},
        "வேண்டாம்": {"gloss": "Don't want / no thanks", "phonetic": ["vendaam"],
                      "recognition": "solid", "production": "none", "seen_in": []},
    })
    kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
    now = datetime.now(timezone.utc)
    log = read_json(klog_path)
    log.append({"date": now.date().isoformat(), "timestamp": now.isoformat(),
                "acted": True, "modality": "text", "move": "smoke chain",
                "body": "evlo naal irupeenga? fire it back",
                "expected_target": "ஒரு மாசம் இருப்போம்", "target_revealed": False})
    write_json(klog_path, log)

    # first reply fires cold; the judge chains a follow-up ask for a NEW target
    v = canned_verdict([("ஒரு மாசம் இருப்போம்", "cold")])
    v["follow_up_ask"] = "she piles more food — wave it off"
    v["follow_up_target"] = "வேண்டாம்"
    v["follow_up_target_revealed"] = False
    kr.judge = lambda k, r, t, h=None, rr=None: v
    sys.argv = ["knock_reply.py", "oru maasam iruppom"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("original ask survives the chain",
          entry["expected_target"] == "ஒரு மாசம் இருப்போம்",
          f"got {entry.get('expected_target')}")
    check("pin moved to the follow-up", entry.get("pinned_target") == "வேண்டாம்")

    # second reply is graded against the PIN, and both exchanges are on record
    kr.judge = lambda k, r, t, h=None, rr=None: canned_verdict([("வேண்டாம்", "cold")])
    sys.argv = ["knock_reply.py", "vendaam!"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("both exchanges recorded", len(entry.get("exchanges", [])) == 2,
          f"got {len(entry.get('exchanges', []))}")
    check("second reply graded against the pin",
          read_json(lex_path)["வேண்டாம்"]["production"] == "cold")
    check("fired accumulates across the chain",
          entry.get("reply_fired") == ["ஒரு மாசம் இருப்போம்", "வேண்டாம்"],
          f"got {entry.get('reply_fired')}")

    # the chat record shows every turn of the chain, not just the last
    chat = (prog / "chat.md").read_text(encoding="utf-8")
    check("chat renders the full chain",
          "oru maasam iruppom" in chat and "vendaam!" in chat)

    # grounded reveals: only Tamil actually printed in recent knock traffic lists
    log = read_json(klog_path)
    log.append({"date": now.date().isoformat(), "timestamp": now.isoformat(),
                "acted": True, "modality": "text", "move": "smoke recap",
                "body": "yesterday: oru maasam iruppom ✓ — solid",
                "expected_target": "", "target_revealed": False})
    write_json(klog_path, log)
    rr = kr.revealed_recently(read_json(klog_path), read_json(lex_path))
    check("revealed_recently sees the printed word", "ஒரு மாசம் இருப்போம்" in rr, f"got {rr}")


def s11_capped_graduation(kr, sb: Path):
    """#4 (2026-07-08): the reveal-cap's hinted-forever trap. Cold-quality fires
    the reveal window blocks are recorded CAPPED; capped fires on 2 distinct
    local days graduate the word to cold. Judge claims resolve against computed
    evidence (KF-6): a 'capped' with no reveal on record upgrades to cold; a
    'cold' on shown Tamil downgrades to capped."""
    print("\n11. Capped lane + cross-day graduation (regression #4)")
    prog = sb / "progress"
    lex_path, klog_path = prog / "lexicon.json", prog / "knock_log.json"
    kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
    now = datetime.now(timezone.utc)
    yday = now - timedelta(days=1)

    # (a) day 2 of capped fires → graduation to COLD, pace credited
    write_json(lex_path, {
        "பழகிப்போச்சு": {"gloss": "I'm used to it", "phonetic": ["pazhagippochu"],
                          "recognition": "solid", "production": "hinted",
                          "seen_in": [], "last_surfaced": "2026-07-01"},
    })
    day1 = {"date": yday.date().isoformat(), "timestamp": yday.isoformat(),
            "acted": True, "modality": "text", "move": "smoke lore",
            "body": "pazhagippochu — 'used to it'. let it sit in your ear.",
            "expected_target": "", "target_revealed": False,
            "exchanges": [{"at": yday.strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "reply": "pazhagippochu", "verdict": "hinted",
                           "fired": ["பழகிப்போச்சு"], "fired_cold": [],
                           "fired_capped": ["பழகிப்போச்சு"], "graduated": [],
                           "reply_line": "adhu dhaan"}]}
    day2 = {"date": now.date().isoformat(), "timestamp": now.isoformat(),
            "acted": True, "modality": "text", "move": "smoke ask",
            "body": "aunty warns the food is spicy — brush it off, you're used to it",
            "expected_target": "பழகிப்போச்சு", "target_revealed": False}
    write_json(klog_path, [day1, day2])
    kr.judge = lambda k, r, t, h=None, rr=None: canned_verdict([("பழகிப்போச்சு", "capped")])
    sys.argv = ["knock_reply.py", "pazhagippochu"]
    kr.main()
    lex = read_json(lex_path)
    check("2nd distinct capped day graduates to COLD",
          lex["பழகிப்போச்சு"]["production"] == "cold", lex["பழகிப்போச்சு"]["production"])
    entry = read_json(klog_path)[-1]
    check("graduation credits the cold pace",
          entry.get("reply_fired_cold") == ["பழகிப்போச்சு"],
          str(entry.get("reply_fired_cold")))
    check("exchange records the graduation",
          entry["exchanges"][-1].get("graduated") == ["பழகிப்போச்சு"],
          str(entry["exchanges"][-1]))

    # (b) judge says 'capped' but nothing on record revealed the word → COLD (KF-6)
    write_json(lex_path, {
        "வேண்டாம்": {"gloss": "don't want / no thanks", "phonetic": ["vendaam"],
                      "recognition": "solid", "production": "none",
                      "seen_in": [], "last_surfaced": "2026-07-01"},
    })
    write_json(klog_path, [{
        "date": now.date().isoformat(), "timestamp": now.isoformat(),
        "acted": True, "modality": "text", "move": "smoke ask",
        "body": "she piles more food — wave it off", "expected_target": "வேண்டாம்",
        "target_revealed": False}])
    kr.judge = lambda k, r, t, h=None, rr=None: canned_verdict([("வேண்டாம்", "capped")])
    sys.argv = ["knock_reply.py", "vendaam"]
    kr.main()
    check("unverifiable capped claim upgrades to COLD",
          read_json(lex_path)["வேண்டாம்"]["production"] == "cold")

    # (c) judge says 'cold' on Tamil the knock itself printed → capped (day 1: hinted)
    write_json(lex_path, {
        "போதும்": {"gloss": "enough", "phonetic": ["podhum"],
                    "recognition": "solid", "production": "none",
                    "seen_in": [], "last_surfaced": "2026-07-01"},
    })
    write_json(klog_path, [{
        "date": now.date().isoformat(), "timestamp": now.isoformat(),
        "acted": True, "modality": "text", "move": "smoke reveal",
        "body": "fire it back: podhum — one shot", "expected_target": "போதும்",
        "target_revealed": True}])
    kr.judge = lambda k, r, t, h=None, rr=None: canned_verdict([("போதும்", "cold")])
    sys.argv = ["knock_reply.py", "podhum"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("shown 'cold' lands as capped (axis holds at hinted on day 1)",
          read_json(lex_path)["போதும்"]["production"] == "hinted"
          and entry.get("reply_fired_capped") == ["போதும்"],
          f"prod={read_json(lex_path)['போதும்']['production']} capped={entry.get('reply_fired_capped')}")


def s12_volley(mk, kr, sb: Path):
    """#5 (2026-07-08): the standalone daily blitz. normalize_decision zips
    Anna's asks with Python's BINDING targets; the reply judge advances the
    volley pin deterministically — even on a miss (recast-and-move), ignoring
    the judge's own chain — and the queue is finite."""
    print("\n12. Volley knock — binding targets + deterministic advance (regression #5)")
    prog = sb / "progress"
    lex_path, klog_path = prog / "lexicon.json", prog / "knock_log.json"
    w1, w2, w3 = "போதும்", "வேண்டாம்", "பழகிப்போச்சு"
    menu = [{"target": w, "gloss": "g"} for w in (w1, w2, w3)]

    # normalize_decision: binding zip + Python-composed body
    raw = {"act": True, "modality": "volley", "move": "daily volley",
           "rationale": "smoke", "next_check_hours": 3,
           "notification_body": "model's own body — must be overridden",
           "expected_target": "", "target_revealed": True,
           "volley_asks": ["ask one", "ask two", "ask three"], "schedule": None}
    d = mk.normalize_decision(dict(raw), menu)
    check("volley zips asks with Python's targets",
          d.get("volley") == [{"target": w1, "ask": "ask one"},
                              {"target": w2, "ask": "ask two"},
                              {"target": w3, "ask": "ask three"}], str(d.get("volley")))
    check("volley body is composed from ask 1, target unrevealed",
          d["notification_body"] == "⚡ volley 1/3 — ask one"
          and d["expected_target"] == w1 and d["target_revealed"] is False)
    d = mk.normalize_decision(dict(raw), [])
    check("volley without a binding menu degrades to text",
          d["modality"] == "text" and not d.get("volley"))

    # reply flow: cold → advance; MISS → still advance; queue exhausts
    write_json(lex_path, {
        w: {"gloss": "g", "phonetic": [p], "recognition": "solid",
            "production": "none", "seen_in": [], "last_surfaced": "2026-07-01"}
        for w, p in [(w1, "podhum"), (w2, "vendaam"), (w3, "pazhagippochu")]})
    kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
    now = datetime.now(timezone.utc)
    write_json(klog_path, [{
        "date": now.date().isoformat(), "timestamp": now.isoformat(),
        "acted": True, "modality": "volley", "move": "daily volley",
        "body": "⚡ volley 1/3 — ask one", "expected_target": w1,
        "target_revealed": False,
        "volley": [{"target": w1, "ask": "ask one"}, {"target": w2, "ask": "ask two"},
                   {"target": w3, "ask": "ask three"}],
        "volley_next": 1}])

    v = canned_verdict([(w1, "cold")])
    v["follow_up_ask"] = "judge's own chain — must be ignored"
    v["follow_up_target"] = w3
    kr.judge = lambda k, r, t, h=None, rr=None: v
    sys.argv = ["knock_reply.py", "podhum"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("volley advance ignores the judge's chain and pins item 2",
          entry.get("pinned_target") == w2 and entry.get("volley_next") == 2,
          f"pin={entry.get('pinned_target')} next={entry.get('volley_next')}")
    check("push-back carries item 2's ask", "2/3 — ask two" in entry.get("reply_line", ""),
          entry.get("reply_line"))

    miss = canned_verdict([])
    miss["verdict"], miss["reply_line"] = "miss", "close — vendaam. adhu dhaan next time"
    kr.judge = lambda k, r, t, h=None, rr=None: miss
    sys.argv = ["knock_reply.py", "vanda"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("a MISS still advances the volley (recast-and-move)",
          entry.get("pinned_target") == w3 and entry.get("volley_next") == 3,
          f"pin={entry.get('pinned_target')} next={entry.get('volley_next')}")

    kr.judge = lambda k, r, t, h=None, rr=None: canned_verdict([(w3, "cold")])
    sys.argv = ["knock_reply.py", "pazhagippochu"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("exhausted volley chains nothing further",
          entry.get("volley_next") == 3
          and entry["exchanges"][-1]["reply_line"] == "adhu dhaan",
          f"next={entry.get('volley_next')} line={entry.get('reply_line')}")
    check("volley graded item 3 against its pin",
          read_json(lex_path)[w3]["production"] == "cold")
    check("original volley ask survives on record", entry.get("expected_target") == w1)


def s13_eavesdrop(mk, kr, sb: Path):
    """#6 (2026-07-09): the catch-axis knock. An eavesdrop reply is judged on
    the drift mandate and moves RECOGNITION one rung per catch (upgrades only,
    solid = the deck win); production and the fire meters never move."""
    print("\n13. Eavesdrop dose — drift replies move the catch axis only (regression #6)")
    prog = sb / "progress"
    lex_path, klog_path = prog / "lexicon.json", prog / "knock_log.json"
    w = "தெரியுமா"

    # normalize_decision: a tape-less eavesdrop degrades to text; a real one
    # keeps the modality and never counts as a revealed production ask
    raw = {"act": True, "modality": "eavesdrop", "move": "gossip tape",
           "rationale": "smoke", "next_check_hours": 3, "memo_script": "",
           "notification_body": "who's the news about?", "expected_target": w,
           "target_revealed": True, "schedule": None}
    d = mk.normalize_decision(dict(raw))
    check("tape-less eavesdrop degrades to text", d["modality"] == "text")
    raw["memo_script"] = "தெரியுமா… அவங்க பொண்ணு Chennai-ல வேலை-ஆம்!"
    d = mk.normalize_decision(dict(raw))
    check("eavesdrop keeps modality, target unrevealed",
          d["modality"] == "eavesdrop" and d["target_revealed"] is False)

    write_json(lex_path, {w: {
        "gloss": "you know?", "phonetic": ["theriyuma"], "recognition": "struggled",
        "production": "none", "seen_in": [], "last_surfaced": "2026-07-01",
        "deck": "trip", "direction": "catch", "type": "chunk"}})
    kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
    now = datetime.now(timezone.utc)

    def eavesdrop_knock() -> dict:
        return {"date": now.date().isoformat(), "timestamp": now.isoformat(),
                "acted": True, "modality": "eavesdrop", "move": "gossip tape",
                "body": "who's the news about?", "memo_script": raw["memo_script"],
                "expected_target": w, "target_revealed": False}

    def reply(text: str, verdict: str):
        kr.judge_catch = lambda k, r: {"verdict": verdict, "reply_line": "adhu dhaan 🎧",
                                       "meta_note": "", "rationale": "smoke"}
        sys.argv = ["knock_reply.py", text]
        kr.main()

    # caught → one rung; caught again → solid; production never moves
    log = read_json(klog_path); log.append(eavesdrop_knock()); write_json(klog_path, log)
    reply("her daughter got a job in Chennai", "caught")
    lex = read_json(lex_path)
    check("caught bumps recognition one rung", lex[w]["recognition"] == "comfortable")
    check("production untouched by a catch", lex[w]["production"] == "none")
    entry = read_json(klog_path)[-1]
    check("catch reply logs no production fire",
          entry.get("reply_fired") is None and entry["exchanges"][-1]["fired"] == [],
          str(entry.get("reply_fired")))
    check("catch verdict on record", entry.get("reply_verdict") == "caught")

    log = read_json(klog_path); log.append(eavesdrop_knock()); write_json(klog_path, log)
    reply("something about a wedding date", "caught")
    check("second catch reaches solid — the deck win",
          read_json(lex_path)[w]["recognition"] == "solid")

    # missed / chat move nothing
    log = read_json(klog_path); log.append(eavesdrop_knock()); write_json(klog_path, log)
    before = read_json(lex_path)[w]
    reply("no idea, too fast", "missed")
    after = read_json(lex_path)[w]
    check("missed drift moves no axis", after["recognition"] == before["recognition"])

    # ---- #11 (2026-07-25): the unanswerable tape + the thread-blind judge ----
    # A tape that hearsays about an unnamed அவங்க has no recoverable WHO, so the
    # drift question asks for what the audio never encoded. Andrew was scored
    # half-caught twice for exactly that, and his "who came?" was the right
    # question. Two guards: the tape must name someone up front, and the judge
    # must see its own thread so a later turn can't re-ask a settled catch.
    named = "நம்ம அக்கா இருக்காங்கல… அவங்க நேத்து வந்துட்டாங்களாம்!"
    unnamed = "ஹலோ? ஆமா, அவங்க நேத்து வந்துட்டாங்களாம். ஏதோ பிரச்சனை இருக்காம்."
    # A real call opens with a greeting, so the window is the opening TWO paragraphs —
    # a paragraph-one rule would have degraded the 07-19 and 07-22 tapes, which name
    # their subject perfectly well one beat in.
    greeted = "ஹலோ? ஆமா ஆமா, நான் தான்…\n\nஅந்த வீட்டு பொண்ணுக்கு கல்யாணம் ஆகுதாம்."
    # The 07-25 tape verbatim: it DOES say அக்கா — in paragraph 4, as the source of
    # the reassurance, never as the subject who came. A whole-tape check passes it;
    # that is the tape that left Andrew asking "who came?" with no answer in it.
    tape_0725 = ("ஹலோ, ஹலோ — கேக்குதா?\n\n"
                 "ஆமா, நேத்து அவங்க வந்துட்டாங்களாம்.\n\n"
                 "ஏதோ ஒரு பிரச்சனை இருக்காம்.\n\n"
                 "ஆனா, அக்கா சொன்னா — கவலைப்படாதன்னு.")
    check("tape naming a person passes the referent guard",
          mk.tape_names_a_referent(named))
    check("referent-less tape fails the guard", not mk.tape_names_a_referent(unnamed))
    check("a greeting first, referent one beat in, still passes",
          mk.tape_names_a_referent(greeted))
    check("the 07-25 tape fails — அக்கா arrives too late and is not the subject",
          not mk.tape_names_a_referent(tape_0725))
    raw["memo_script"] = unnamed
    check("referent-less eavesdrop degrades to text — never pushed unanswerable",
          mk.normalize_decision(dict(raw))["modality"] == "text")
    raw["memo_script"] = named
    check("named-referent eavesdrop still fires",
          mk.normalize_decision(dict(raw))["modality"] == "eavesdrop")

    # The judge sees the whole thread, not just the latest turn.
    fresh = eavesdrop_knock()
    check("first turn carries no prior_exchanges",
          "prior_exchanges" not in kr.catch_context(fresh, "someone turned up"))
    threaded = dict(fresh, exchanges=[
        {"at": "2026-07-25T15:18:58Z", "reply": "someone said there's a problem",
         "verdict": "caught", "fired": [], "reply_line": "adhu dhaan 🎧"}])
    ctx = kr.catch_context(threaded, "ok can you break it down line by line?")
    check("later turn is judged knowing the catch already landed",
          len(ctx.get("prior_exchanges", [])) == 1
          and "problem" in ctx["prior_exchanges"][0]["andrew_said"],
          str(ctx.get("prior_exchanges")))
    legacy = dict(fresh, reply="someone said there's a problem", reply_line="adhu dhaan")
    check("pre-exchanges knock still surfaces its one prior turn",
          len(kr.catch_context(legacy, "hint?").get("prior_exchanges", [])) == 1)


def s15_push_retry(mk):
    print("\n15. Push delivery retry (regression #4)")
    # 2026-07-14: a transient runner-DNS blip killed the notify step after the
    # knock was already logged and committed — a phantom "fired" knock, red run.
    # push_to_phone now retries transient OSErrors; a final failure still raises.
    import os, urllib.error

    class FakeResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    calls = {"n": 0}
    sleeps = []
    real_urlopen, real_sleep = mk.urllib.request.urlopen, mk.time.sleep
    os.environ["ANNA_PUSH_WEBHOOK_URL"] = "https://smoke.invalid/hook"
    try:
        mk.time.sleep = sleeps.append

        def flaky(req, *a, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise urllib.error.URLError(OSError("Temporary failure in name resolution"))
            return FakeResp()
        mk.urllib.request.urlopen = flaky
        mk.push_to_phone("smoke", None, knock_id="smoke")
        check("two blips then success — delivered", calls["n"] == 3, f"{calls['n']} calls")
        check("backoff between attempts", sleeps == [5, 10], f"sleeps={sleeps}")

        calls["n"] = 0
        def dead(req, *a, **kw):
            calls["n"] += 1
            raise urllib.error.URLError(OSError("no route"))
        mk.urllib.request.urlopen = dead
        try:
            mk.push_to_phone("smoke", None, knock_id="smoke")
            check("unreachable webhook still raises", False, "did not raise")
        except OSError:
            check("unreachable webhook still raises", True)
        check("gave up after 3 attempts", calls["n"] == 3, f"{calls['n']} calls")
    finally:
        mk.urllib.request.urlopen, mk.time.sleep = real_urlopen, real_sleep
        os.environ.pop("ANNA_PUSH_WEBHOOK_URL", None)


def s16_stale_clone_gates(sb: Path):
    print("\n16. Stale-clone gates + payload canon (regression 2026-07-15)")
    # A session opened on a clone 14 commits behind origin: re-collected a paid
    # field mission, missed the morning trailer, and the comma-joined soak payload
    # could never match an episode's words. The pure halves of the fixes:
    sys.path.insert(0, str(sb / "scripts"))
    ss = importlib.import_module("sync_state")

    check("behind origin → STALE banner", "STALE" in (ss.sync_banner((14, 0)) or ""))
    check("ahead only → unpushed warning", "not on origin" in (ss.sync_banner((0, 1)) or ""))
    check("in sync → no banner", ss.sync_banner((0, 0)) is None)
    check("sync unknown → soft warning", "SYNC UNKNOWN" in (ss.sync_banner(None) or ""))

    check("comma-joined payload splits",
          ss.canon_payload(["frame:idum,பாத்துக்கறேன்"]) == ["frame:idum", "பாத்துக்கறேன்"])
    check("clean payload passes through",
          ss.canon_payload(["a", "b"]) == ["a", "b"])

    check("no record → unseen", ss.is_unseen({}))
    check("surfaced → not unseen", not ss.is_unseen({"last_surfaced": "2026-07-01"}))
    check("in an episode → not unseen", not ss.is_unseen({"seen_in": ["M60"]}))

    trailer = {"date": "2026-07-15", "move": "session bell trailer", "body": "ஆச்சு today"}
    volley = {"date": "2026-07-15", "move": "afternoon volley", "body": "…"}
    check("newest-knock trailer with no session after → unpaid",
          ss.unpaid_trailer([volley, trailer], "2026-07-13") is trailer)
    check("session on/after trailer date → paid",
          ss.unpaid_trailer([trailer], "2026-07-15") is None)
    check("newest knock not a trailer → nothing owed",
          ss.unpaid_trailer([trailer, volley], "2026-07-13") is None)
    check("knocks_since filters to the gap",
          [k["date"] for k in ss.knocks_since([{"date": "2026-07-10"}, {"date": "2026-07-14"}],
                                              "2026-07-13")] == ["2026-07-14"])


def s17_campaign_digest(mk, sb: Path):
    print("\n17. Campaign block in the knock digest (2026-07-17)")
    # The campaign is Andrew-initiated prose in profile.md; the digest carries it
    # so cloud Anna steers by it. No section / placeholder / missing file ⇒ "".
    profile = sb / "progress" / "profile.md"
    original = profile.read_text(encoding="utf-8")
    # The day-zero example profile ships the section with the placeholder line.
    check("day-zero placeholder → no campaign block", mk.campaign_block() == "")

    profile.write_text(
        original.split("## The Campaign — This Week", 1)[0]
        + "## The Campaign — This Week\n\n"
        "> Contract: see daily_session.md.\n\n"
        "**Ask-machine week** (07-20 → 07-26): kudunga, sollunga, vaanga.\n"
        "- Mon: teach day\n\n## After The Campaign\n\nunrelated\n",
        encoding="utf-8")
    block = mk.campaign_block()
    check("live campaign lands in the digest", "Ask-machine week" in block)
    check("contract blockquote stripped", "Contract" not in block)
    check("next section not swept in", "unrelated" not in block)

    profile.write_text(profile.read_text(encoding="utf-8").replace(
        "**Ask-machine week** (07-20 → 07-26): kudunga, sollunga, vaanga.\n"
        "- Mon: teach day",
        "_(no campaign live yet — kick one off at the next session)_"),
        encoding="utf-8")
    check("placeholder → no campaign block", mk.campaign_block() == "")
    profile.write_text(original, encoding="utf-8")


# Word budgets for the protocol's prose surfaces (2026-07-16): every incident since
# April landed as a paragraph, and prose only accumulates — "earn its place" didn't
# enforce itself. Growth past a budget is a red run; raising a budget must ride the
# same diff as the growth, and the commit names the lines it retired (/extend Gate 4).
PROSE_BUDGETS = {
    "protocol/persona.md": 2000,
    "protocol/constitution.md": 1750,
    "protocol/daily_session.md": 1250,
    # Split out of daily_session.md (2026-07-23) rather than raise its budget:
    # channel routing is its own concern and Anna loads it only when choosing.
    "protocol/audio_channels.md": 400,
    "OUTREACH_MANDATE": 2000,
    "JUDGE_MANDATE": 1500,
    # Split out of JUDGE_MANDATE (2026-07-24) rather than raise its budget, the
    # same move audio_channels.md made on daily_session.md: "what this reply can
    # do beyond the text line" (schedule a push, speak back) is its own concern,
    # and the mandate was at 1498/1500 — a ceiling is a split signal, not a
    # bump-the-number signal.
    "REACH_MANDATE": 300,
    "CATCH_JUDGE_MANDATE": 300,
}


def s18_prose_budgets(mk, kr, sb: Path):
    print("\n18. Protocol prose word budgets (2026-07-16 — the subtraction mechanism)")
    strings = {"OUTREACH_MANDATE": mk.OUTREACH_MANDATE,
               "JUDGE_MANDATE": kr.JUDGE_MANDATE,
               "REACH_MANDATE": kr.REACH_MANDATE,
               "CATCH_JUDGE_MANDATE": kr.CATCH_JUDGE_MANDATE}
    for rel, budget in PROSE_BUDGETS.items():
        words = (len(strings[rel].split()) if rel in strings
                 else len((sb / rel).read_text(encoding="utf-8").split()))
        check(f"{rel}: {words}/{budget} words", words <= budget,
              f"over by {words - budget} — retire lines, or raise the budget in this "
              f"same diff and name what it retired")


def s20_fielding(mk, kr, sb: Path):
    """The fielding dose (2026-07-18): a Tamil question fired AT him, reply graded
    as production by the NORMAL judge — never the catch judge. The stimulus half
    of the exchange finally has a channel."""
    print("\n20. Fielding dose — heard question in, produced answer out")
    prog = sb / "progress"
    lex_path, klog_path = prog / "lexicon.json", prog / "knock_log.json"
    w = "சாப்பிட்டேன்"

    raw = {"act": True, "modality": "fielding", "move": "field the FAQ",
           "rationale": "smoke", "next_check_hours": 3, "memo_script": "",
           "notification_body": "she's asking you something — answer her",
           "expected_target": w, "target_revealed": True, "schedule": None}
    d = mk.normalize_decision(dict(raw))
    check("question-less fielding degrades to text", d["modality"] == "text")
    raw["memo_script"] = "சாப்டீங்களா?"
    d = mk.normalize_decision(dict(raw))
    check("fielding keeps modality, answer unrevealed",
          d["modality"] == "fielding" and d["target_revealed"] is False)

    mk.rails_gate = lambda force, now=None: (True, "smoke-open")
    mk.build_digest = lambda: "SMOKE DIGEST"
    mk.push_to_phone, mk.commit_and_push = Recorder(), Recorder()

    async def fake_render(memo_script, out_path, voice=None):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"smoke-mp3")
        fake_render.voice = voice
    mk.render_memo = fake_render
    mk.decide = lambda digest, vt=None: dict(d)
    sys.argv = ["morning_knock.py"]
    mk.main()
    entry = read_json(klog_path)[-1]
    check("fielding renders audio and logs the url", bool(entry.get("audio_url")))
    check("fielding speaks in the family voice, not Anna's",
          fake_render.voice == mk.EAVESDROP_VOICE)

    write_json(lex_path, {w: {
        "gloss": "I ate", "phonetic": ["saapten"], "recognition": "comfortable",
        "production": "none", "seen_in": ["M1"], "last_surfaced": "2026-07-01",
        "deck": "trip", "direction": "fire", "type": "chunk"}})
    kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
    catch_calls = Recorder()
    kr.judge_catch = catch_calls
    kr.judge = lambda k, r, t, h=None, rr=None: canned_verdict([(w, "cold")])
    sys.argv = ["knock_reply.py", "saapten!"]
    kr.main()
    check("fielding reply routes to the PRODUCTION judge", len(catch_calls) == 0)
    check("fielded answer moves the production axis",
          read_json(lex_path)[w]["production"] == "cold")


def s21_volley_represent(kr, sb: Path):
    """KF-11 (2026-07-18): a chat/meta reply mid-volley let the open ask vanish
    and the judge improvised the chain surface (re-asked an earlier item,
    declared the volley done, claimed an unrecorded score). Python now
    re-presents the pinned ask on chat verdicts and marks the chain closed
    after the last judged item."""
    print("\n21. Volley re-present on chat replies (KF-11)")
    prog = sb / "progress"
    klog_path = prog / "knock_log.json"
    write_json(prog / "lexicon.json", {})
    kr.commit_and_push = Recorder()

    def volley_knock(nxt: int, done: bool = False) -> dict:
        k = {"date": "2026-07-18", "timestamp": f"2026-07-18T15:0{nxt}:00+00:00",
             "acted": True, "modality": "volley", "move": "smoke volley",
             "body": "⚡ volley 1/3 — ask one", "expected_target": "t1",
             "target_revealed": False, "volley_next": nxt,
             "pinned_target": f"t{min(nxt, 3)}", "pinned_revealed": False,
             "volley": [{"target": "t1", "ask": "ask one"},
                        {"target": "t2", "ask": "ask two"},
                        {"target": "t3", "ask": "ask three"}]}
        if done:
            k["volley_done"] = True
        return k

    def reply(text: str, verdict: dict):
        kr.judge = lambda k, r, t, h=None, rr=None: verdict
        kr.push_to_phone = pushes = Recorder()
        sys.argv = ["knock_reply.py", text]
        kr.main()
        return pushes[-1][0]

    chat = {"verdict": "chat", "reply_line": "ha, all good", "rationale": "smoke",
            "fired": [], "follow_up_ask": "", "follow_up_target": "",
            "follow_up_target_revealed": True, "meta_note": "", "schedule": None}

    # the one owner of "the current ask" — judge context and re-presents both read it
    check("volley_open_ask names the current item",
          kr.volley_open_ask(volley_knock(nxt=2)) == "2/3 — ask two")
    check("volley_open_ask starts at ask one",
          kr.volley_open_ask(volley_knock(nxt=1)) == "1/3 — ask one")
    check("volley_open_ask clamps past the end",
          kr.volley_open_ask(volley_knock(nxt=3)) == "3/3 — ask three")
    check("no volley → no open ask", kr.volley_open_ask({"body": "x"}) is None)

    # chat mid-volley → the pinned ask is re-presented; pin and chain untouched
    write_json(klog_path, [volley_knock(nxt=2)])
    body = reply("wait, which one are we on?", dict(chat))
    entry = read_json(klog_path)[-1]
    check("chat mid-volley re-presents the open ask", "still open · 2/3 — ask two" in body, body)
    check("pin does not move on chat", entry["volley_next"] == 2 and entry["pinned_target"] == "t2")
    check("chat does not count as a chain step", entry.get("chained", 0) == 0)

    # judged reply on the LAST item closes the chain
    write_json(klog_path, [volley_knock(nxt=3)])
    miss = dict(chat); miss["verdict"] = "miss"; miss["reply_line"] = "adhu 'ask three' dhaan"
    body = reply("no idea", miss)
    entry = read_json(klog_path)[-1]
    check("last judged item marks the volley done", entry.get("volley_done") is True)
    check("no re-present after the chain closes", "still open" not in body, body)

    # chat AFTER the volley is done stays a plain chat
    body = reply("thanks anna", dict(chat))
    check("chat on a finished volley adds no ask", "still open" not in body, body)


def s19_watchdog_detection(sb: Path):
    print("\n19. Studio watchdog detection (self-healing production, 2026-07-18)")
    # The watchdog answers two questions before touching any dispatch; both
    # must be pure reads. Dispatch itself is the existing scripts, not tested here.
    sw = importlib.import_module("studio_watchdog")

    n = sw.next_mission() - 1
    check("newest script with no MP3 → unrendered", sw.scripted_unrendered() == n,
          f"got {sw.scripted_unrendered()}, want {n}")
    sw.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    (sw.AUDIO_DIR / f"tier2_mission{n}.mp3").write_bytes(b"x")
    check("MP3 present → nothing unrendered", sw.scripted_unrendered() is None)
    (sw.AUDIO_DIR / f"tier2_mission{n}.mp3").unlink()
    (sw.AUDIO_DIR / f"tier2_mission{n}_v2.mp3").write_bytes(b"x")
    check("_vN re-render counts as rendered", sw.scripted_unrendered() is None)
    (sw.AUDIO_DIR / f"tier2_mission{n}.mp3").write_bytes(b"x")

    learner = read_json(sb / "progress" / "learner.json")
    learner["soak_order"] = {"payload": ["வேணும்"], "scene_seed": "s", "from": "2026-07-18"}
    write_json(sb / "progress" / "learner.json", learner)
    write_json(sb / "progress" / "episodes.json", {})
    check("payload + no episode carrying it → soak pending", sw.soak_pending())
    write_json(sb / "progress" / "episodes.json", {"71": {"words": ["வேணும்"]}})
    check("newest episode carries payload → produced", not sw.soak_pending())
    learner["soak_order"] = {}
    write_json(sb / "progress" / "learner.json", learner)
    check("no soak order → nothing pending", not sw.soak_pending())


def s22_sfx_pause(sb: Path):
    print("\n22. [SFX] cues render as air, never dropped (M68 drama, 2026-07-18)")
    ra = importlib.import_module("render_audio")
    script = sb / "content" / "scripts" / "smoke_sfx.md"
    script.write_text(
        "# Tier 2, Mission 99 — Smoke\n\n"
        "[SFX: A phone rings in the dark.]\n\n"
        "**HOST (M):** Three fourteen in the morning.\n\n"
        "[SFX: Sheets rustle.]\n"
        "[Pause: 2 sec]\n", encoding="utf-8")
    dialogue, _ = ra.parse_script(str(script))
    check("SFX cue becomes a pause",
          dialogue[0]["speaker"] == "PAUSE" and dialogue[0]["seconds"] == 1.5,
          f"got {dialogue[0]}")
    check("SFX text never reaches a voice",
          not any("phone rings" in d.get("text", "") for d in dialogue))
    check("adjacent SFX + pause coalesce",
          dialogue[-1] == {"speaker": "PAUSE", "seconds": 3.5}, f"got {dialogue[-1]}")


def s23_ticket_end_to_end(sb: Path):
    print("\n23. suggest_targets: the ticket runs end-to-end (inbox 2026-07-17)")
    import contextlib
    import io
    st = importlib.import_module("suggest_targets")
    # The proven crash class: a special_* reference sidecar carries a STRING
    # mission; sorting it against integers took the ticket down (2026-07-17).
    (sb / "content" / "scripts" / "special_smoke.tags.json").write_text(
        json.dumps({"mission": "smoke reference tape", "register": "neutral"}),
        encoding="utf-8")
    cars = st.load_recent_sidecars()
    check("string-mission sidecar never enters the rotation",
          all(isinstance(c.get("mission"), int) for c in cars))
    check("sidecar history survives the special_ fixture", len(cars) > 0)

    argv, out = sys.argv, io.StringIO()
    try:
        sys.argv = ["suggest_targets.py"]
        with contextlib.redirect_stdout(out):
            st.main()
        ran = True
    except Exception as e:  # noqa: BLE001 — the check IS "it doesn't raise"
        ran, out = False, io.StringIO(f"raised {e!r}")
    finally:
        sys.argv = argv
    text = out.getvalue()
    check("ticket runs end-to-end on day-zero state", ran, text[:200])
    check("ticket prints the menu header", "SESSION TICKET" in text)
    check("day-zero ticket still serves new candidates",
          "not found" not in text, text[:200])

    print("\n24. feed duration is counted, not estimated (2026-07-22)")
    ra = importlib.import_module("render_audio")
    rr = importlib.import_module("rebuild_rss")
    # Our mp3s are raw frame concatenations with no Xing header, so a
    # filesize/bitrate estimate ran 3-5% long on every episode. 100 silence
    # frames is a known 2.4s: 24ms per frame at 24 kHz Layer III.
    fake = sb / "counted.mp3"
    fake.write_bytes(ra.SILENCE_FRAME * 100)
    check("frame scan is exact on a known frame count",
          abs(rr.mp3_duration(fake) - 2.4) < 0.01, rr.mp3_duration(fake))
    check("duration_hms rounds to the counted second",
          rr.duration_hms(fake, "FALLBACK") == "00:00:02", rr.duration_hms(fake, "x"))
    check("an unreadable file falls back instead of raising",
          rr.duration_hms(sb / "nope.mp3", "00:03:30") == "00:03:30")


def s25_studio_concurrency_and_secrets(sb: Path):
    print("\n25. Studio concurrency + credential-less hosts (2026-07-23)")
    ra = importlib.import_module("render_audio")
    sw = importlib.import_module("studio_watchdog")

    # --- the race that cost a draft episode -------------------------------
    # Renders used a fixed "temp_audio_segments"; whichever finished first
    # rmdir'd it out from under the other mid-run (FileNotFoundError on the
    # next segment write). Scratch dirs must be per-run.
    a, b = ra.new_scratch_dir(), ra.new_scratch_dir()
    try:
        check("two renders get distinct scratch dirs", a != b, f"{a} == {b}")
        check("scratch dirs are real and writable",
              Path(a).is_dir() and Path(b).is_dir())
        # the bug shape itself: a scratch dir assigned from a string literal
        src = Path(ra.__file__).read_text(encoding="utf-8")
        check("scratch dir is never a hardcoded path",
              'temp_dir = "' not in src and "temp_dir = '" not in src)
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)

    # --- the deadlock guard on the state lock -----------------------------
    # run_studio/watchdog hold .studio.lock and spawn the renderer; the child
    # must inherit, never block on its own parent.
    prev = os.environ.get("STUDIO_LOCK_HELD")
    os.environ["STUDIO_LOCK_HELD"] = "1"
    try:
        check("child inherits a parent-held lock (no self-deadlock)",
              ra.acquire_state_lock() is None)
    finally:
        os.environ.pop("STUDIO_LOCK_HELD", None)
        if prev is not None:
            os.environ["STUDIO_LOCK_HELD"] = prev

    # --- auth failures are permanent, not transient ------------------------
    class Denied(Exception):
        pass
    check("credential error is fatal",
          ra.is_auth_error(Exception("Could not automatically determine credentials")))
    check("permission error is fatal", ra.is_auth_error(Exception("403 Permission denied")))
    check("network blip stays retryable",
          not ra.is_auth_error(Denied("503 backend unavailable")))

    # --- credential detection: BOTH outcomes mocked, so the test is hermetic --
    # These assertions are the whole point of the feature — "skip cleanly when
    # the secret is absent" — so they must not themselves depend on the host's
    # secrets. The first version did, and CI (which has NO credentials, exactly
    # the case the feature targets) went red: the tests for graceful-skip broke
    # on a host with nothing to skip. Mock google.auth.default both ways.
    import google.auth
    real_default = google.auth.default
    try:
        google.auth.default = lambda *a, **k: (_ for _ in ()).throw(
            Exception("Could not automatically determine credentials"))
        reason = ra.google_credentials_ready()
        check("no ADC → a reason, not a crash", isinstance(reason, str) and bool(reason))

        google.auth.default = lambda *a, **k: (object(), "fake-project")
        check("ADC present → no reason", ra.google_credentials_ready() is None)

        # Re-rendering an existing script needs TTS only. Gating it on agy would
        # strand a scripted-but-unrendered episode on a host that can render.
        # (ADC still mocked-present here, so this isolates the agy axis.)
        rs = importlib.import_module("run_studio")
        real_which = rs.shutil.which
        rs.shutil.which = lambda cmd: None if cmd == "agy" else real_which(cmd)
        try:
            check("no agy → render path still allowed", rs.renderer_preflight() is None)
            check("no agy → fresh-episode path blocked", rs.preflight() is not None)
        finally:
            rs.shutil.which = real_which
    finally:
        google.auth.default = real_default

    check("watchdog: exit 3 → skip, no retry",
          "no retry" in sw.outcome(sw.EXIT_NOT_CONFIGURED, "dispatch"))
    check("watchdog: exit 0 → done", sw.outcome(0, "dispatch").endswith("done"))
    check("watchdog: other non-zero → retry next tick",
          "retry next tick" in sw.outcome(1, "dispatch"))


def s26_capacity_routing(sb: Path):
    print("\n26. Audio channel routes by capacity, not by default (2026-07-23)")
    # The felt signal: "totally tired, a longer drill for the park" produced a
    # dense 10-min two-voice scene, because every audio ask routed to the studio.
    # The routing table is the fix; this is the lint that keeps doc and code
    # honest about each other.
    routing = (REAL_BASE / "protocol" / "audio_channels.md").read_text(encoding="utf-8")
    check("routing table exists", "capacity routes" in routing)
    for script in ("render_soak.py", "render_drill.py", "run_studio.py"):
        check(f"routing names {script}", script in routing)
        check(f"{script} exists", (REAL_BASE / "scripts" / script).exists())
    session = (REAL_BASE / "protocol" / "daily_session.md").read_text(encoding="utf-8")
    check("the session choreography points at it", "audio_channels.md" in session)
    skill = (REAL_BASE / ".claude" / "skills" / "anna" / "SKILL.md").read_text(encoding="utf-8")
    check("Anna's skill routes by capacity, not straight to the studio",
          "capacity" in skill and "render_soak.py" in skill)

    # The soak channel's own law: passive means no response gap and no scene.
    soak = importlib.import_module("render_soak")
    check("soak mandate forbids a scene", "NO scene" in soak.SOAK_MANDATE)
    check("soak rhythm is Python's, not the model's",
          "Python owns all of that" in soak.SOAK_MANDATE)
    check("soak week-window is selectable", "days" in soak.week_payload.__code__.co_varnames)

    # The feed must actually carry it — a channel nobody can find is not a channel.
    rr = importlib.import_module("rebuild_rss")
    check("feed titles soak tracks", "nothing to do but listen" in rr.clean_title(
        "Soak", "soak_2026-07-23_2326.mp3"))
    check("feed durations are measured, not estimated",
          rr.audio_duration.__doc__ and "ffprobe first" in rr.audio_duration.__doc__)


def s27_schedule_and_soak_guards(sb: Path):
    print("\n27. Clock-requests get queued; soak orders can't loop (2026-07-23)")
    kr = importlib.import_module("knock_reply")

    # #11: Andrew asked for a 9am greeting. The judge acknowledged it warmly,
    # wrote a ledger note, and returned schedule:null — the mandate called
    # scheduling "usual to skip". Nothing was queued; nothing was delivered.
    real_ask = ("I am driving with my wife to Brampton this morning. When you knock, "
                "send an audio message, greet her and say something I've been learning "
                "this week. Not yet I mean 9am would be good.")
    check("the real 9am ask is detected", kr.wants_scheduled_push(real_ask))
    for t in ("ping me in an hour", "knock tomorrow morning", "remind me at 7:30 pm"):
        check(f"clock request detected: {t[:28]}", kr.wants_scheduled_push(t))
    for t in ("naan poren", "adhu dhaan, said it at dinner", "less of the aunty thing"):
        check(f"plain rep is not a clock request: {t[:28]}", not kr.wants_scheduled_push(t))
    # The scheduling rules moved to REACH_MANDATE (2026-07-24 split); the judge
    # still sees both, concatenated.
    check("mandate makes a clock-request mandatory", "MANDATORY" in kr.REACH_MANDATE)
    # Inverted 2026-07-24. This assertion used to require the refusal
    # ("cloud-never-renders" in JUDGE_MANDATE) and so pinned the bug in place:
    # the canon was corrected that morning while the test still demanded the
    # stale prose. A guard that outlives its rule enforces the rule.
    both = kr.JUDGE_MANDATE + kr.REACH_MANDATE
    check("mandate no longer claims the cloud cannot render",
          "cloud-never-renders" not in both and "needs the laptop" not in both)

    # #12: an unresolvable soak payload made the produced-check permanently
    # False, and the hourly cron shipped M72/M73/M74 in one evening.
    ss = importlib.import_module("sync_state")
    lex = {"அவசரம் இருக்கு": {"phonetic": ["avasaram irukku"], "gloss": "hurry"},
           "frame:needtogo-place": {"phonetic": [], "gloss": "must go to X"}}
    resolved, unresolved = ss.split_payload(["avasaram", "frame:needtogo-place"], lex)
    check("bare headword resolves to its chunk key",
          "அவசரம் இருக்கு" in resolved, f"got {resolved}")
    check("no false unresolved", unresolved == [], f"got {unresolved}")
    junk_r, junk_u = ss.split_payload(["definitely-not-a-word"], lex)
    check("genuine junk is reported, not silently kept", junk_u and not junk_r)

    sw = importlib.import_module("studio_watchdog")
    write_json(sb / "progress" / "learner.json",
               {**read_json(sb / "progress" / "learner.json"),
                "soak_order": {"payload": ["definitely-not-a-word"], "from": "2026-07-23"}})
    check("an unverifiable payload is NOT 'still pending' (no dispatch loop)",
          not sw.soak_pending())

    # Two doors drive the SAME dispatch — the cron and the session-open drain.
    # Fixing only one leaves the loop armed from the other, which is exactly
    # what nearly happened: sync_state's status kept saying NOT YET PRODUCED
    # after the watchdog was already satisfied. One resolver, both callers.
    status_src = (REAL_BASE / "scripts" / "sync_state.py").read_text(encoding="utf-8")
    check("the status drain-check uses the shared resolver",
          "split_payload(soak.get" in status_src)
    check("the watchdog drain-check uses the shared resolver",
          "split_payload" in (REAL_BASE / "scripts" / "studio_watchdog.py").read_text(encoding="utf-8"))

    # The rate rail, independent of any single root cause.
    check("unattended production is capped", sw.MAX_UNATTENDED_PER_DAY >= 1)
    today = datetime.now().date().isoformat()
    write_json(sb / "progress" / "episodes.json",
               {"70": {"words": [], "produced": today},
                "71": {"words": [], "produced": "2020-01-01"}})
    check("produced_today counts only today's", sw.produced_today() == 1)


def s28_cloud_writer(sb: Path):
    print("\n28. Studio writer is executor-agnostic; cloud carries its canon (2026-07-24)")
    rs = importlib.import_module("run_studio")

    # The resolver: agy local (Andrew's Gemini quota), OpenRouter in the cloud
    # where no agy/subagent binary exists.
    check("force agy → agy_print", rs.resolve_writer("agy").__name__ == "agy_print")
    check("force openrouter → openrouter_pass",
          rs.resolve_writer("openrouter").__name__ == "openrouter_pass")

    real_which = rs.shutil.which
    rs.shutil.which = lambda c: None if c == "agy" else real_which(c)
    try:
        check("auto with no agy → openrouter", rs.resolve_writer("auto").__name__ == "openrouter_pass")
        prev = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            check("no agy + no key → auto preflight fails",
                  rs.writer_preflight("auto") is not None)
            os.environ["OPENROUTER_API_KEY"] = "x"
            check("no agy + key → auto preflight ok", rs.writer_preflight("auto") is None)
            check("forced agy without agy → preflight fails",
                  rs.writer_preflight("agy") is not None)
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)
            if prev is not None:
                os.environ["OPENROUTER_API_KEY"] = prev
    finally:
        rs.shutil.which = real_which

    # inline_canon: the fix that made the cloud writer produce on-canon. The
    # thin slice caught it inventing a tags schema it had no filesystem to read;
    # the prompt's OWN 'protocol/...md' references are the manifest Python inlines.
    producer_prompt = rs.PRODUCER.format(draft="DRAFT", n=99)
    inlined = rs.inline_canon(producer_prompt)
    check("inline_canon pulls producer.md content into the prompt",
          "===== protocol/studio/producer.md =====" in inlined
          and len(inlined) > len(producer_prompt) + 1000)
    check("inline_canon includes a sample sidecar when tags are asked for",
          "EXAMPLE .tags.json" in inlined)
    # a prompt that references nothing is passed through untouched
    check("inline_canon is a no-op without file refs",
          rs.inline_canon("just do the thing") == "just do the thing")
    # the manifest follows the prompt: a made-up ref is reported, never fabricated
    check("inline_canon flags a missing referenced file",
          "referenced but missing" in rs.inline_canon("Read protocol/studio/nope.md now"))


def s29_one_runner_every_capability(mk, pq, kr, sb: Path):
    print("\n29. One workflow, every capability; the drain renders voice (2026-07-24)")

    # --- the consolidation ------------------------------------------------
    # Three workflows held three different subsets of the secrets, so what Anna
    # could DO depended on which event woke him. Andrew asked for a 20:00 voice
    # greeting for his brother; the reply lane had no TTS secret, so Anna
    # refused — while the knock lane rendered Tamil TTS in the same cloud daily.
    wf_dir = REAL_BASE / ".github" / "workflows"
    for retired in ("morning-knock.yml", "log-knock-response.yml", "push-queue.yml"):
        check(f"{retired} is retired", not (wf_dir / retired).exists())
    anna = (wf_dir / "anna.yml").read_text(encoding="utf-8")
    for trigger in ("schedule:", "repository_dispatch:", "workflow_dispatch:"):
        check(f"anna.yml carries the {trigger.rstrip(':')} trigger", trigger in anna)
    for secret in ("OPENROUTER_API_KEY", "ANNA_PUSH_WEBHOOK_URL", "GCP_SA_KEY"):
        check(f"{secret} is wired once, for every lane", anna.count(secret) >= 1)
    # Job-level env is what makes capability structural rather than remembered:
    # a new step cannot be added without it.
    # Comment lines stripped: this file EXPLAINS the bad context in prose, and a
    # guard that trips on its own documentation is a guard nobody keeps.
    job_env = "\n".join(ln for ln in anna.split("steps:")[0].splitlines()
                        if not ln.lstrip().startswith("#"))
    for var in ("OPENROUTER_API_KEY", "ANNA_PUSH_WEBHOOK_URL", "GOOGLE_APPLICATION_CREDENTIALS"):
        check(f"{var} is job-level, not per-step", var in job_env)
    # The 2026-07-24 outage — `runner` in job-level env, valid YAML that GitHub
    # rejects outright — was guarded here by a hand-rolled context whitelist.
    # RETIRED 2026-07-25 for actionlint in smoke.yml, which knows the whole
    # context-availability table (not just jobs.<id>.env), plus schema, action
    # refs and expression syntax. Verified against the real broken file: it flags
    # line 65 with the exact legal-context list the whitelist hard-coded.
    # What's asserted here now is that the mechanism is still WIRED — this suite
    # runs locally where actionlint may be absent, so the guard it can still keep
    # is "CI has not quietly dropped the linter".
    smoke_yml = (wf_dir / "smoke.yml").read_text(encoding="utf-8")
    check("CI lints the workflow files themselves", "./actionlint" in smoke_yml)
    check("the linter is version-pinned",
          re.search(r"actionlint_\d+\.\d+\.\d+_linux", smoke_yml) is not None)
    check("workflow changes trigger the lint", ".github/workflows/**" in smoke_yml)
    # ffprobe is installed because ubuntu-24.04 has no ffmpeg — but never on the
    # lock-screen lane, which has a standing latency constraint (rendering was kept
    # out of the reply path for the same reason). ~20s of apt before a recast is a
    # regression, and durations freeze at first publication anyway.
    ffstep = anna.split("Install ffprobe", 1)[1].split("- name:", 1)[0]
    check("ffprobe is installed for the lanes that publish new audio", "ffmpeg" in ffstep)
    check("the lock-screen lane skips the install",
          "if: github.event_name != 'repository_dispatch'" in ffstep)
    check("a failed install cannot cost a knock", "continue-on-error: true" in ffstep)
    check("one hourly cron replaces three expressions",
          anna.count("- cron:") == 1 and '- cron: "0 * * * *"' in anna)
    # Drain-first is load-bearing: it logs a reach, and rails_gate counts today's
    # reaches when deciding whether to knock. Drain last would double-push.
    # Search the steps block only — the header comment names these scripts too.
    steps = anna.split("steps:", 1)[1]
    check("the drain runs before the knock",
          steps.index("push_queue.py drain") < steps.index("morning_knock.py"))
    check("the drain runs before the reply judge",
          steps.index("push_queue.py drain") < steps.index("knock_reply.py"))
    check("the drain is unconditional (no `if:` gate on its step)",
          "continue-on-error: true\n        run: python scripts/push_queue.py drain" in anna)

    # --- the detector that dropped the 8pm push ---------------------------
    # Built 2026-07-23 to catch exactly this; it needed a clock AND a verb, and
    # "schedule" was not in the verb list — the most literal phrasing possible.
    real_8pm_ask = ("My brother James is arriving at 8pm. Schedule a push and say hello "
                    "(aloud a traditional greeting and a couple key survival items)")
    check("the real 8pm ask is detected", kr.wants_scheduled_push(real_8pm_ask))
    for t in ("queue something for 9pm", "play me a line at 7:30am",
              "wish her good morning tomorrow", "record a greeting for tonight"):
        check(f"clock request detected: {t[:30]}", kr.wants_scheduled_push(t))
    for t in ("naan poren", "said it at dinner", "less of the aunty thing",
              "adhu dhaan, she understood"):
        check(f"plain rep is not a clock request: {t[:30]}", not kr.wants_scheduled_push(t))

    # --- memo_script survives the trip from judge to queue ----------------
    # It used to be dropped on the floor here: maybe_enqueue_schedule was
    # text-only, so even a judge that composed a voice dose lost it.
    qpath = sb / "progress" / "push_queue.json"
    write_json(qpath, [])
    future = (datetime.now(timezone.utc) + timedelta(hours=2))
    out = mk.maybe_enqueue_schedule({"schedule": {
        "at_local": future.astimezone(mk.LOCAL_TZ).strftime("%Y-%m-%dT%H:%M"),
        "body": "James is here — say hello 🎧",
        "memo_script": "வணக்கம் ஜேம்ஸ்! நல்லா இருக்கீங்களா?",
        "move": "welcome james"}})
    check("a scheduled voice dose lands in the queue", out is not None)
    queued = read_json(qpath)
    check("memo_script survives judge → queue",
          len(queued) == 1 and "வணக்கம்" in queued[0].get("memo_script", ""),
          f"got {queued}")
    check("it is marked as needing a render", pq.needs_render(queued[0]))
    check("an already-rendered entry is not re-rendered",
          not pq.needs_render({**queued[0], "audio_url": "https://cdn/x.mp3"}))
    check("a text dose never asks for TTS",
          not pq.needs_render({"body": "text only", "memo_script": ""}))

    # --- the render itself, stubbed: fills audio_url, returns the mp3 -----
    calls = []
    real_render = pq.render_memo

    async def fake_render(script, out_path, voice):   # render_memo is a coroutine
        calls.append((script, voice))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"ID3fake")

    pq.render_memo = fake_render
    try:
        entry = dict(queued[0])
        mp3 = pq.render_entry(entry)
        check("render_entry returns an mp3 to commit", mp3 is not None and mp3.exists())
        check("it speaks the queued script", calls and "வணக்கம்" in calls[0][0])
        check("scheduled voice uses Anna's pinned voice", calls[0][1] == mk.ANNA_VOICE)
        check("audio_url is filled from the rendered path",
              entry.get("audio_url", "").startswith("https://cdn.jsdelivr.net/gh/")
              and entry["audio_url"].endswith(".mp3"))
        check("a rendered entry no longer needs rendering", not pq.needs_render(entry))
    finally:
        pq.render_memo = real_render

    # A TTS failure must not swallow the dose — the text still fires.
    pq.render_memo = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("403 Permission denied"))
    try:
        broken = dict(queued[0])
        check("TTS failure returns no mp3", pq.render_entry(broken) is None)
        check("TTS failure leaves no audio_url", not broken.get("audio_url"))
        check("TTS failure is recorded on the entry", "403" in broken.get("render_failed", ""))
    finally:
        pq.render_memo = real_render

    # --- the whole drain, end to end, with ORDER asserted -----------------
    # The ordering is the subtle part: push_to_phone pre-warms the jsDelivr URL,
    # so the mp3 has to be committed to main BEFORE the notification goes out —
    # otherwise the CDN has nothing to serve and iOS drops the inline player.
    # Committing the mp3 separately (not with the state) is what keeps the
    # retry property: a failed push leaves the entry queued.
    prog = sb / "progress"
    klog_path, q_path = prog / "knock_log.json", prog / "push_queue.json"
    events, saved = [], (pq.WAKING_START_HOUR, pq.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY)
    real_push, real_commit, real_feed = pq.push_to_phone, pq.commit_and_push, pq.refresh_feed
    pq.push_to_phone = lambda body, url=None, knock_id="": events.append(("push", url))
    pq.commit_and_push = lambda paths, msg: events.append(
        ("commit", "mp3" if any(str(p).endswith(".mp3") for p in paths) else "state",
         any(str(p).endswith("rss.xml") for p in paths)))

    # rebuild_rss titles a dose from knock_log.json, so WHEN the feed is rebuilt
    # decides whether the published title carries the move label. Record what the
    # log looked like at rebuild time — a label-less first write means a later
    # lane retitles a published item, which Apple Podcasts forks into a second
    # episode (2026-07-24 8pm dose, seen twice on one guid).
    rss_stub = sb / "rss.xml"

    def fake_feed():
        entries = read_json(klog_path) or []
        events.append(("feed", any(e.get("queue_id") == "qVOICE" for e in entries)))
        return rss_stub

    pq.refresh_feed = fake_feed
    pq.render_memo = fake_render
    try:
        pq.WAKING_START_HOUR, pq.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 99
        write_json(klog_path, [])
        write_json(q_path, [{**queued[0], "id": "qVOICE", "force": True,
                             "due": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}])
        pq.cmd_drain(argparse.Namespace(dry_run=False, no_commit=False))
        kinds = [e[0] for e in events]
        check("mp3 is committed before the notification fires",
              kinds[:2] == ["commit", "push"] and events[0][1] == "mp3", f"got {events}")
        check("state is committed after the push", kinds[-1] == "commit" and events[-1][1] == "state")
        feeds = [e for e in events if e[0] == "feed"]
        check("the feed is rebuilt exactly once per drain", len(feeds) == 1, f"got {feeds}")
        check("the feed is rebuilt only AFTER the fired dose is in the knock log",
              feeds and feeds[0][1], "rebuilt before the log write — title would publish label-less")
        check("the mp3 commit carries no feed rebuild",
              events[0][2] is False, f"got {events[0]}")
        check("rss.xml rides the state commit", events[-1][2] is True, f"got {events[-1]}")
        check("the notification carries the rendered audio_url",
              (events[1][1] or "").startswith("https://cdn.jsdelivr.net/gh/"), f"got {events[1]}")
        logged = read_json(klog_path)[-1]
        check("the fired voice dose logs as modality audio", logged.get("modality") == "audio")
        check("the log keeps what was HEARD for the reply judge",
              "வணக்கம்" in logged.get("memo_script", ""))
        check("the queue is emptied once fired", read_json(q_path) == [])
    finally:
        pq.WAKING_START_HOUR, pq.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = saved
        pq.push_to_phone, pq.commit_and_push, pq.refresh_feed = real_push, real_commit, real_feed
        pq.render_memo = real_render


def s30_anna_speaks_back(mk, kr, sb: Path):
    print("\n30. Anna can answer ALOUD from the lock screen (2026-07-24)")

    # The loop was three-quarters closed: audio out on the knock, text in from
    # the phone, cloud judgment, text back. push_to_phone(body, None, ...) was
    # hard-coded in BOTH reply paths, so Anna could never speak back.
    src = (REAL_BASE / "scripts" / "knock_reply.py").read_text(encoding="utf-8")
    check("the production reply no longer hard-codes a silent push",
          "push_to_phone(body, voice_url" in src)
    check("voice_reply is in the judge's return schema", '"voice_reply"' in kr.JUDGE_MANDATE)
    check("REACH rations it against lock-screen latency",
          "90 seconds" in kr.REACH_MANDATE and "SPEAK BACK" in kr.REACH_MANDATE)
    # The judge must see the split halves as one prompt.
    check("the split mandate is concatenated for the model",
          "JUDGE_MANDATE + \"\\n\" + REACH_MANDATE" in src)

    # normalize_verdict guards the new field the same way it guards the others.
    check("a missing voice_reply normalises to empty",
          kr.normalize_verdict({"verdict": "chat"})["voice_reply"] == "")
    check("a null voice_reply normalises to empty",
          kr.normalize_verdict({"verdict": "chat", "voice_reply": None})["voice_reply"] == "")
    check("a whitespace voice_reply normalises to empty",
          kr.normalize_verdict({"verdict": "chat", "voice_reply": "  "})["voice_reply"] == "")
    spoken = kr.normalize_verdict({"verdict": "chat", "voice_reply": " வணக்கம் "})["voice_reply"]
    check("a real voice_reply survives normalisation", spoken == "வணக்கம்")

    # The render: fills a URL, uses Anna's pinned voice, and a TTS failure must
    # still let the TEXT recast go out — silence is the one unacceptable outcome.
    calls, real_render = [], kr.render_memo

    async def fake_render(script, out_path, voice):
        calls.append((script, voice))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"ID3fake")

    kr.render_memo = fake_render
    try:
        mp3, url = kr.render_voice_reply("வணக்கம் James")
        check("voice reply renders an mp3", mp3 is not None and mp3.exists())
        check("it speaks what the judge wrote", calls and calls[0][0] == "வணக்கம் James")
        check("Anna answers in his own pinned voice", calls[0][1] == mk.ANNA_VOICE)
        check("the mp3 is served from the CDN, not a local path",
              (url or "").startswith("https://cdn.jsdelivr.net/gh/") and url.endswith(".mp3"))
    finally:
        kr.render_memo = real_render

    kr.render_memo = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("503 backend unavailable"))
    try:
        mp3, url = kr.render_voice_reply("வணக்கம்")
        check("a TTS failure yields no mp3 and no url", mp3 is None and url is None)
    finally:
        kr.render_memo = real_render
    # ...and the push still goes out, because voice_url is simply None by then.
    check("the text recast is never gated on the render succeeding",
          "if voice_url:" in src and "push_to_phone(body, voice_url" in src)


def s31_feed_carries_every_pushed_dose(sb: Path):
    print("\n31. Every pushed dose is findable in the feed (2026-07-24)")
    rr = importlib.import_module("rebuild_rss")

    # Andrew's rule: "all audio you push me should go in the feed" — a dismissed
    # notification must stay replayable. Three producers write to knocks/, and
    # only `knock_` was ever taught to the feed, so a scheduled dose and a spoken
    # reply titled as their raw filename and sorted BELOW every episode.
    cases = {
        "knocks/knock_2026-07-05T22-58.mp3": "Knock",
        "knocks/queued_q1784931404_2026-07-24T23-50-00.mp3": "Scheduled",
        "knocks/reply_2026-07-24T23-55-10.mp3": "Reply",
    }
    for path, kind in cases.items():
        title = rr.knock_title(path, {})
        check(f"{kind.lower()} audio gets a real title", title.startswith(f"{kind} — 2026-"),
              f"got {title!r}")
        check(f"{kind.lower()} title carries no raw filename",
              ".mp3" not in title and "_" not in title.split("·")[0], f"got {title!r}")
        m = rr.KNOCK_AUDIO_RE.match(os.path.basename(path))
        check(f"{kind.lower()} audio sorts in the dated push band", m is not None)

    # The move label: the knock lane logs `mp3` (repo path), while the drain and
    # the reply judge log only the CDN url they pushed. Both must resolve.
    log = sb / "progress" / "knock_log.json"
    cdn = "https://cdn.jsdelivr.net/gh/arosselet/tamil-tutor@main/published_audio/knocks"
    write_json(log, [
        {"move": "ambient dose", "mp3": "published_audio/knocks/knock_2026-07-05T22-58.mp3"},
        {"move": "welcome james", "audio_url": f"{cdn}/queued_q1784931404_2026-07-24T23-50-00.mp3"},
        {"move": "said it aloud", "reply_audio_url": f"{cdn}/reply_2026-07-24T23-55-10.mp3"},
    ])
    # rebuild_rss addresses the repo by RELATIVE path (AUDIO_DIR, the knock log),
    # so it must be exercised from a repo root — here, the sandbox's.
    cwd = os.getcwd()
    try:
        os.chdir(sb)
        labels = rr.knock_move_labels()
    finally:
        os.chdir(cwd)
    for path, move in (("knocks/knock_2026-07-05T22-58.mp3", "ambient dose"),
                       ("knocks/queued_q1784931404_2026-07-24T23-50-00.mp3", "welcome james"),
                       ("knocks/reply_2026-07-24T23-55-10.mp3", "said it aloud")):
        check(f"move label resolves: {move}", labels.get(path) == move, f"got {labels.get(path)!r}")
        check(f"title carries the move: {move}", move in rr.knock_title(path, labels))

    # "Nothing that isn't playable by my podcast player" (Andrew): extension is
    # not proof — a truncated render or an lfs pointer is a .mp3 that is not audio.
    check("a playability floor exists", rr.MIN_PLAYABLE_BYTES > 0)

    # Feed order must be a function of the library, not the host's listdir():
    # the two special_ files tie at (10, 0), and a rebuild on another machine
    # silently swapped them.
    src = (REAL_BASE / "scripts" / "rebuild_rss.py").read_text(encoding="utf-8")
    check("feed sort is deterministic (filename breaks ties)",
          "key=lambda f: (sort_key(f), f)" in src)

    # A dose is announced in Andrew's zone no matter which machine rebuilds.
    # `localtime=True` stamped the HOST's zone, so the laptop wrote -0400 and the
    # CI container +0000 for one listener in one timezone. Same instant, two
    # faces. Simulate a UTC host: the offset must not move.
    stamp = datetime(2026, 7, 24, 19, 56, 25, tzinfo=rr.LOCAL_TZ).timestamp()
    saved_tz = os.environ.get("TZ")
    try:
        os.environ["TZ"] = "UTC"
        time.tzset()
        pub = email.utils.format_datetime(datetime.fromtimestamp(stamp, rr.LOCAL_TZ))
        check("a pubDate is stamped in Andrew's zone on a UTC host", pub.endswith("-0400"),
              f"got {pub}")
        check("the pubDate names the local wall clock", "19:56:25" in pub, f"got {pub}")
    finally:
        if saved_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = saved_tz
        time.tzset()
    # Comments stripped, per s29: rebuild_rss EXPLAINS the retired host-clock call
    # in prose, and a guard that trips on its own documentation is one nobody keeps.
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    check("the feed never stamps in the host's zone",
          "localtime=True" not in code, "rebuild_rss still uses the host clock")

    # Measure once, then freeze. Duration described a file that never changes, but
    # was re-derived on every rebuild from whatever tool the host had — the laptop
    # has ffprobe, the CI container does not, so each cloud rebuild reverted the
    # library to the frame scan (M72: 13:12 announced for a 10:02 episode, 2026-07-25).
    # The real guard is behavioural: rebuild with ffprobe gone and nothing may move.
    feed = sb / "rss.xml"
    published = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
  <item><title>T</title>
    <enclosure url="{u}" length="9" type="audio/mpeg"/><guid>{u}</guid>
    <pubDate>Thu, 23 Jul 2026 23:27:39 -0400</pubDate>
    <itunes:duration>00:10:02</itunes:duration></item>
</channel></rss>"""
    cwd = os.getcwd()
    try:
        os.chdir(sb)
        url = f"{rr.BASE_URL}/{rr.AUDIO_DIR}/knocks/knock_2026-07-05T22-58.mp3"
        feed.write_text(published.format(u=url), encoding="utf-8")
        prior = rr.existing_items().get(url, {})
        check("a published duration is recovered for the rebuild",
              prior.get("duration") == "00:10:02", f"got {prior}")
        check("a published pubDate is still recovered alongside it",
              prior.get("pubDate", "").endswith("-0400"), f"got {prior}")
        # Malformed markup must not drop either field — one unescaped character
        # once wiped every saved date and collapsed the feed to a single "now".
        feed.write_text(published.format(u=url).replace("<title>T", "<title>R & D"),
                        encoding="utf-8")
        rescued = rr.existing_items().get(url, {})
        check("a malformed feed still yields both published values",
              rescued.get("duration") == "00:10:02" and rescued.get("pubDate"),
              f"got {rescued}")
    finally:
        os.chdir(cwd)
    check("duration is preserved, not re-derived",
          'prior.get("duration") or duration_hms' in code,
          "rebuild_rss still recomputes a published duration")


def s32_deck_rotation_and_coverage(mk, sb: Path):
    """Deck starvation (2026-07-25 audit). The deck's selector ordered by tier →
    ripeness → alphabetical, with no staleness term — so the head of each tier
    was frozen and the tail never surfaced: 16 frames took 51 of the deck's 74
    lifetime reps while 45 of 70 fire items had never been asked once, and
    `cold/total` reported a winning sprint throughout because it counts progress
    and cannot see distribution. Ripeness-first was rich-get-richer (an item only
    becomes `hinted` by being worked, which promoted it again).

    Two mechanisms, both proven here: least-recently-worked sorts first WITHIN a
    tier (the tier prefix itself is the 07-13 touchdown bar and must survive),
    and `deck_coverage` counts worked/total so the tail is legible."""
    print("\n32. Deck rotation + coverage: the tail is not starved (2026-07-25)")
    st = importlib.import_module("suggest_targets")
    ss = importlib.import_module("sync_state")
    today = date_cls.today()

    def ago(n):
        return (today - timedelta(days=n)).isoformat()

    def item(reg, **kw):
        base = {"deck": "trip", "gloss": "x", "phonetic": [], "type": "chunk",
                "recognition": "struggled", "production": "none",
                "seen_in": [1], "last_surfaced": None, "_reg": reg}
        base.update(kw)
        return base

    fixture = {
        # survival tier (antifreeze/frame/public), one row per starvation state
        "smoke:surv-hot": item("frame", type="pattern", production="hinted",
                               recognition="solid", last_surfaced=ago(2)),
        "smoke:surv-mid": item("antifreeze", recognition="comfortable", last_surfaced=ago(30)),
        "smoke:surv-tail": item("antifreeze"),                    # never worked, soaked
        "smoke:surv-unseen": item("public", seen_in=[]),          # never worked, never seen
        "smoke:surv-done": item("frame", type="pattern", production="cold",
                                recognition="solid", last_surfaced=ago(1)),
        "smoke:delight-new": item("social"),
        "smoke:dessert-new": item("gossip"),
        # ear-only: same law, and must never land in the fire tiers
        "smoke:ear-stale": item("gossip", direction="catch"),
        "smoke:ear-fresh": item("gossip", direction="catch",
                                recognition="comfortable", last_surfaced=ago(1)),
    }
    lex = {k: {kk: vv for kk, vv in v.items() if kk != "_reg"} for k, v in fixture.items()}
    deck_file = sb / "curriculum" / "trip_deck.json"
    lex_path = sb / "progress" / "lexicon.json"
    saved = (deck_file.read_bytes(), lex_path.read_bytes())
    try:
        write_json(deck_file, [{"tamil": k, "register": v["_reg"], "gloss": "x"}
                               for k, v in fixture.items()])
        write_json(lex_path, lex)
        deck = st.deck_status(lex, today=today)
        order = [t["word"] for t in deck["pending"]]

        # The regression: under the old key the ripe, recently-worked headliner
        # led its tier forever. Least-recently-worked now leads.
        check("a never-worked item outranks the ripe recently-worked headliner",
              order[0] == "smoke:surv-tail", f"got {order}")
        check("the worked headliner falls to the back of its tier",
              order.index("smoke:surv-hot") > order.index("smoke:surv-mid"), f"got {order}")
        check("staleness beats ripeness, not tier: survival still precedes delight",
              order.index("smoke:surv-unseen") < order.index("smoke:delight-new"), f"got {order}")
        check("the touchdown bar survives: delight still precedes dessert",
              order.index("smoke:delight-new") < order.index("smoke:dessert-new"), f"got {order}")
        check("a cold item leaves the pending queue", "smoke:surv-done" not in order)

        # The ear starved worst of all (1 of 12 ever touched) — same law applies.
        catch_order = [t["word"] for t in deck["catch_pending"]]
        check("the ear rotates too: the never-worked catch item leads",
              catch_order[0] == "smoke:ear-stale", f"got {catch_order}")

        # Rotation must not smuggle an UNSEEN item into a cold quiz (teach-first).
        vt = [t["target"] for t in mk.volley_targets(n=4)]
        check("rotation respects teach-first: UNSEEN stays out of the volley",
              "smoke:surv-unseen" not in vt, f"got {vt}")
        check("a never-worked but soaked item IS volley-eligible",
              "smoke:surv-tail" in vt, f"got {vt}")

        cov = st.deck_coverage(lex, today=today)
        surv, delight, dessert = (cov["tiers"][t] for t in ("survival", "delight", "dessert"))
        check("survival coverage counts worked, not cold",
              (surv["touched"], surv["total"], surv["cleared"]) == (3, 5, 1),
              f"got {surv}")
        check("ear-only items never inflate a fire tier",
              dessert["total"] == 1, f"dessert={dessert}")
        check("the ear is metered on its own axis",
              (cov["catch"]["touched"], cov["catch"]["total"]) == (1, 2), f"got {cov['catch']}")
        check("a fully starved register is visible by name",
              cov["registers"]["public"]["untouched"] == 1
              and cov["registers"]["antifreeze"]["touched"] == 1,
              f"got {cov['registers']}")
        check("delight/dessert starvation is reported, not hidden",
              (delight["untouched"], dessert["untouched"]) == (1, 1),
              f"got {delight} {dessert}")
        never = {u["word"] for u in cov["untouched"]}
        check("every never-worked item is named",
              never == {"smoke:surv-tail", "smoke:surv-unseen",
                        "smoke:delight-new", "smoke:dessert-new", "smoke:ear-stale"},
              f"got {sorted(never)}")
        check("soaked-but-never-asked is distinguished from never-encountered",
              [u["soaked_only"] for u in cov["untouched"]
               if u["word"] == "smoke:surv-unseen"] == [False], f"got {cov['untouched']}")
        check("the tail's depth is reported for the guard",
              cov["stalest_pending"] == st.NEVER_SURFACED, f"got {cov['stalest_pending']}")

        # The headline meter carries the same count, so a green sprint can never
        # again hide a starved deck.
        cd = ss.compute_deck(lex)
        check("the status meter carries the coverage count",
              (cd["untouched"], cd["surv_untouched"], cd["catch_untouched"]) == (4, 2, 1),
              f"got {cd}")
    finally:
        deck_file.write_bytes(saved[0])
        lex_path.write_bytes(saved[1])


def main():
    with tempfile.TemporaryDirectory(prefix="tamil-smoke-") as tmp:
        sb = make_sandbox(Path(tmp))
        print(f"sandbox: {sb}")
        mk, kr, pq = load_modules(sb)
        s1_parse_llm_json(mk)
        s2_rails_gate(mk, sb / "progress" / "knock_log.json")
        s15_push_retry(mk)   # needs the real push_to_phone — s3+ stub it out
        s3_knock_paths(mk, sb)
        s4_normalize(kr)
        s5_reply_judge(mk, kr, sb)
        s6_queue_drain(mk, pq, sb)
        s7_integrity(sb)
        s8_variety_and_decay(mk, kr, sb)
        s9_audio_knock_feed(mk, sb)
        s10_chain_history(mk, kr, sb)
        s11_capped_graduation(kr, sb)
        s12_volley(mk, kr, sb)
        s13_eavesdrop(mk, kr, sb)
        s14_reply_correlation(kr)
        s16_stale_clone_gates(sb)
        s17_campaign_digest(mk, sb)
        s18_prose_budgets(mk, kr, sb)
        s19_watchdog_detection(sb)
        s20_fielding(mk, kr, sb)
        s21_volley_represent(kr, sb)
        s22_sfx_pause(sb)
        s23_ticket_end_to_end(sb)
        s25_studio_concurrency_and_secrets(sb)
        s26_capacity_routing(sb)
        s27_schedule_and_soak_guards(sb)
        s28_cloud_writer(sb)
        s29_one_runner_every_capability(mk, pq, kr, sb)
        s30_anna_speaks_back(mk, kr, sb)
        s31_feed_carries_every_pushed_dose(sb)
        s32_deck_rotation_and_coverage(mk, sb)

    print(f"\n{'ALL GREEN' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
