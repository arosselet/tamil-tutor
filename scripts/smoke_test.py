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
    # 2026-07-07: model returned single-quoted Python dict; {..} slice fallback found
    # braces but json.loads rejected single quotes → crash. ast.literal_eval now catches it.
    check("single-quoted keys", p("{'act': True, 'modality': 'text'}")
          == {"act": True, "modality": "text"})
    check("python-dict in prose", p("Here ya go: {'a': 1, 'b': False}")
          == {"a": 1, "b": False})
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
        s10_chain_history(mk, kr, sb)
        s11_capped_graduation(kr, sb)
        s12_volley(mk, kr, sb)
        s13_eavesdrop(mk, kr, sb)

    print(f"\n{'ALL GREEN' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
