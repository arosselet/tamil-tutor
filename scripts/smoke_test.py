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
import ast
import asyncio
import email.utils
import importlib
import inspect
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import tokenize
import types
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

    # 2026-08-05: the judge burned all 800 tokens reasoning in prose and was cut
    # off mid-word before its first brace. parse_llm_json correctly said "no
    # braces" and raised JSONDecodeError — indistinguishable from KF-7/KF-10,
    # where the JSON existed and the PARSER missed it. The two want opposite
    # fixes (bigger budget vs. another fallback), so the teeth here are on
    # TELLING THEM APART, not on raising: a truncation that merely raises the
    # old error is the silent no-op this guard exists to prevent.
    pr = mk.parse_llm_response
    fake = lambda text, reason: type("R", (), {"choices": [type("C", (), {
        "finish_reason": reason,
        "message": type("M", (), {"content": text})()})()]})()
    truncated = "Looking at this: the target is முடிஞ்சா, so the tag might be"
    try:
        pr(fake(truncated, "length"))
        check("truncation raises", False, "did not raise")
    except json.JSONDecodeError:
        check("truncation is NOT reported as a parse error", False,
              "raised JSONDecodeError — the old, ambiguous signal")
    except ValueError as exc:
        check("truncation is NOT reported as a parse error", True)
        check("truncation names itself", "TRUNCATED" in str(exc), str(exc)[:60])
        # The raw text is the recovery payload — losing it costs a re-run.
        check("truncation dump carries the partial text", truncated in str(exc))
    # No false positives: a complete response still parses, fence and all.
    check("finish_reason=stop parses normally",
          pr(fake('```json\n{"verdict": "cold"}\n```', "stop")) == {"verdict": "cold"})
    check("absent finish_reason parses normally",
          pr(fake('{"verdict": "miss"}', None)) == {"verdict": "miss"})


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
    check("flat legacy fired tolerated",
          d["fired"] == [{"word": "போதும்", "said": "போதும்", "verdict": "hinted"}])
    d = n({"verdict": "hinted", "fired": [{"word": "a", "verdict": "cold"},
                                          {"word": "b", "verdict": "hinted"}]})
    check("overall verdict = best word", d["verdict"] == "cold")
    d = n({"verdict": "cold", "fired": []})
    check("scored-but-empty degrades to miss", d["verdict"] == "miss")
    d = n({"verdict": "??", "fired": [{"word": "a", "verdict": "cold"}]})
    check("junk verdict → chat, fired cleared", d["verdict"] == "chat" and d["fired"] == [])

    # Credit is verified against his reply (2026-07-27). The 07-27 volley judge
    # fired கொஞ்சம்/நில்லுங்க against "Oru nimsham" — a phrase containing neither —
    # and Python derived a COLD headline from it. shown_in_knock can only demote;
    # nothing checked that a fired word was in the reply at all.
    d = n({"verdict": "cold", "fired": [{"word": "நில்லுங்க", "said": "nillunga",
                                          "verdict": "cold"}]}, "Oru nimsham")
    check("a fire he never typed is dropped", d["fired"] == [])
    check("...and the headline degrades, not celebrates", d["verdict"] == "miss")
    check("...and the drop is loud, not silent", len(d["unverified"]) == 1)
    d = n({"verdict": "cold", "fired": [{"word": "ஒரு நிமிஷம்", "said": "Oru nimsham",
                                          "verdict": "cold"}]}, "Oru nimsham")
    check("the substitution he DID say is credited to its own key",
          [i["word"] for i in d["fired"]] == ["ஒரு நிமிஷம்"] and d["verdict"] == "cold")
    d = n({"verdict": "cold", "fired": [{"word": "புரியல", "said": "Puriyila.",
                                          "verdict": "cold"}]}, "puriyila")
    check("case and punctuation don't cost him the credit", len(d["fired"]) == 1)
    d = n({"verdict": "hinted", "fired": [{"word": "போதும்", "verdict": "hinted"}]},
          "போதும் anna")
    check("a script reply is its own evidence when the judge quotes nothing",
          len(d["fired"]) == 1)
    d = n({"verdict": "hinted", "fired": [{"word": "போதும்", "verdict": "hinted"}]})
    check("no reply text ⇒ nothing to verify against, fire stands", len(d["fired"]) == 1)


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
        kr.judge = lambda k, r, t, h=None, rr=None, **kw: verdict
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
    # The waking window lives in morning_knock now — one owner, read by the
    # rails, this queue, and push_to_phone's backstop. Patch where it lives.
    saved = (mk.WAKING_START_HOUR, mk.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY)
    now = datetime.now(timezone.utc)

    def q_entry(qid: str, due_hours: float, force: bool = False) -> dict:
        return {"id": qid, "due": (now + timedelta(hours=due_hours)).isoformat(),
                "body": f"dose {qid}", "expected_target": "", "target_revealed": True,
                "audio_url": None, "move": "smoke", "force": force,
                "queued_at": now.isoformat()}

    args = argparse.Namespace(dry_run=False, no_commit=False)
    try:
        mk.WAKING_START_HOUR, mk.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 99
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
        mk.WAKING_START_HOUR, mk.WAKING_END_HOUR = 0, 0
        write_json(q_path, [q_entry("qQUIET", -1), q_entry("qFORCE", -1, force=True)])
        pq.cmd_drain(args)
        check("quiet hours defers non-forced, fires forced",
              len(pushes) == 3 and pushes[2][0] == "dose qFORCE"
              and [e["id"] for e in read_json(q_path)] == ["qQUIET"])

        # daily cap defers non-forced; forced ignores it
        mk.WAKING_START_HOUR, mk.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 0
        write_json(q_path, [q_entry("qCAP", -1), q_entry("qFORCE2", -1, force=True)])
        pq.cmd_drain(args)
        check("cap defers non-forced, fires forced",
              len(pushes) == 4 and pushes[3][0] == "dose qFORCE2"
              and [e["id"] for e in read_json(q_path)] == ["qCAP"])
    finally:
        mk.WAKING_START_HOUR, mk.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = saved


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
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: v
    sys.argv = ["knock_reply.py", "oru maasam iruppom"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("original ask survives the chain",
          entry["expected_target"] == "ஒரு மாசம் இருப்போம்",
          f"got {entry.get('expected_target')}")
    check("pin moved to the follow-up", entry.get("pinned_target") == "வேண்டாம்")

    # second reply is graded against the PIN, and both exchanges are on record
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: canned_verdict([("வேண்டாம்", "cold")])
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
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: canned_verdict([("பழகிப்போச்சு", "capped")])
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
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: canned_verdict([("வேண்டாம்", "capped")])
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
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: canned_verdict([("போதும்", "cold")])
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
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: v
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
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: miss
    sys.argv = ["knock_reply.py", "vanda"]
    kr.main()
    entry = read_json(klog_path)[-1]
    check("a MISS still advances the volley (recast-and-move)",
          entry.get("pinned_target") == w3 and entry.get("volley_next") == 3,
          f"pin={entry.get('pinned_target')} next={entry.get('volley_next')}")

    kr.judge = lambda k, r, t, h=None, rr=None, **kw: canned_verdict([(w3, "cold")])
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
    check("tape-less eavesdrop is REFUSED — text eavesdrops are banned (08-01; "
          "was degrade-to-text until the 07-28 double signal)",
          d["modality"] == "silence" and d["act"] is False)
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
        kr.judge_catch = lambda k, r, *a, **kw: {"verdict": verdict, "reply_line": "adhu dhaan 🎧",
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
    check("referent-less eavesdrop is refused — never pushed unanswerable, and "
          "never a tape-less text promise either",
          mk.normalize_decision(dict(raw))["modality"] == "silence")
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
        # requested=True: this case is about DELIVERY retry, not the rails —
        # without it the quiet-hours chokepoint short-circuits the whole test
        # whenever the suite runs after 21:00 local (2026-07-26).
        mk.push_to_phone("smoke", None, knock_id="smoke", requested=True)
        check("two blips then success — delivered", calls["n"] == 3, f"{calls['n']} calls")
        check("backoff between attempts", sleeps == [5, 10], f"sleeps={sleeps}")

        calls["n"] = 0
        def dead(req, *a, **kw):
            calls["n"] += 1
            raise urllib.error.URLError(OSError("no route"))
        mk.urllib.request.urlopen = dead
        try:
            mk.push_to_phone("smoke", None, knock_id="smoke", requested=True)
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
    sbf = importlib.import_module("session_brief")

    check("behind origin → STALE banner", "STALE" in (sbf.sync_banner((14, 0)) or ""))
    check("ahead only → unpushed warning", "not on origin" in (sbf.sync_banner((0, 1)) or ""))
    check("in sync → no banner", sbf.sync_banner((0, 0)) is None)
    check("sync unknown → soft warning", "SYNC UNKNOWN" in (sbf.sync_banner(None) or ""))

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
          sbf.unpaid_trailer([volley, trailer], "2026-07-13") is trailer)
    check("session on/after trailer date → paid",
          sbf.unpaid_trailer([trailer], "2026-07-15") is None)
    check("newest knock not a trailer → nothing owed",
          sbf.unpaid_trailer([trailer, volley], "2026-07-13") is None)
    check("knocks_since filters to the gap",
          [k["date"] for k in sbf.knocks_since([{"date": "2026-07-10"}, {"date": "2026-07-14"}],
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

    # 2026-07-26 regression: the block is parsed by an exact heading string, so a
    # SECOND "## The Campaign …" section silently orphans the live one. It shipped —
    # the won-and-closed week sat under the parsed heading from 07-24 while the live
    # week sat under "## The Campaign — PITCHED …", and three days of knocks steered
    # by a finished campaign. One heading, always; a finished week is overwritten.
    real = (REAL_BASE / "progress" / "profile.md").read_text(encoding="utf-8")
    heads = [l for l in real.splitlines() if l.startswith("## The Campaign")]
    check(f"real profile.md has exactly one campaign heading ({len(heads)})",
          len(heads) == 1,
          "a second '## The Campaign …' section orphans the live one — "
          "overwrite the finished week, don't archive it in the file")


# Word budgets for the protocol's prose surfaces (2026-07-16): every incident since
# April landed as a paragraph, and prose only accumulates — "earn its place" didn't
# enforce itself. Growth past a budget is a red run; raising a budget must ride the
# same diff as the growth, and the commit names the lines it retired (/extend Gate 4).
PROSE_BUDGETS = {
    "protocol/persona.md": 2000,
    # 1750 -> 1790 (2026-08-04): FIRST raise of this ceiling, and the growth is a
    # class of content no protocol file owned — a standing fact about the learner's
    # life, not a rule. M81 opened at the iron gate with sisters-in-law "recognised
    # from the old photos"; nothing said Andrew is ten years into this family, so
    # every generator filled the blank with the newcomer story. Retired in the same
    # diff (17 words back): the 08-03 leak clause compressed to its evidence, and
    # the zinger line's "surprise … that delight locals and in-laws". A second raise
    # is the split signal — the Core Philosophy's learner facts would leave first.
    "protocol/constitution.md": 1790,
    "protocol/daily_session.md": 1250,
    # Split out of daily_session.md (2026-07-23) rather than raise its budget:
    # channel routing is its own concern and Anna loads it only when choosing.
    # 400 -> 550 (2026-07-28): the file's JOB doubled by deliberate split, not by
    # crud. It always framed itself as two questions — what a dose carries, and
    # which channel carries it — and owned only the second; the commissioning law
    # ("the repair earns the dose") moved IN from daily_session.md Close & Log,
    # which kept a pointer and came out 43 words leaner. Same move audio_channels
    # itself made in 07-23 and JUDGE_MANDATE in 07-24: a ceiling is a split
    # signal. Raising this is the exception the rule allows — growth and raise in
    # one diff, naming what it retired — not the bump-the-number reflex.
    # 550 -> 640 (2026-07-28 evening, SECOND raise in one day — flagged as such).
    # The growth is a law the file did not have: capacity said WHEN a channel is
    # usable and nothing said WHICH format an error deserves, so "a chunk fires a
    # collision" was the only format guidance and it pointed at the loop for every
    # mix-up. Retired in the same diff: that clause, the "route by the situation"
    # bullet (its veto half is now the table's opening line), and the 07-23 story
    # compressed — 33 words back. THIS IS THE CEILING'S SECOND WARNING. A third
    # raise is not allowed: split "what it carries" from "which format carries it".
    # 640 -> 475 (2026-08-01): THE SPLIT WAS TAKEN, as the line above demanded —
    # "what it carries" left for commissioning.md; this file keeps only routing
    # and format, re-censused down with headroom.
    "protocol/audio_channels.md": 475,
    # Split out of audio_channels.md (2026-08-01) — the commissioning law
    # ("the repair earns the dose") is its own concern from channel routing,
    # and the parent had a third raise refused in advance.
    "protocol/commissioning.md": 300,
    "OUTREACH_MANDATE": 2000,
    "JUDGE_MANDATE": 1500,
    # Split out of JUDGE_MANDATE (2026-07-24) rather than raise its budget, the
    # same move audio_channels.md made on daily_session.md: "what this reply can
    # do beyond the text line" (schedule a push, speak back) is its own concern,
    # and the mandate was at 1498/1500 — a ceiling is a split signal, not a
    # bump-the-number signal.
    "REACH_MANDATE": 300,
    # Split out of JUDGE_MANDATE (2026-07-30) for the third time that file has
    # paid for growth by splitting rather than raising. The slip contract landed
    # it at 1764/1500; recording an error is its own concern from grading one
    # (the judge can grade without it, and a port swapping the Tamil examples
    # touches only this string), so it left as REACH_MANDATE and
    # CATCH_JUDGE_MANDATE did. JUDGE_MANDATE keeps only the JSON key.
    "SLIP_MANDATE": 250,
    # Split out of JUDGE_MANDATE (2026-08-02), the FOURTH time that file has paid
    # for growth by splitting instead of raising. Thread continuity — the 3-hour
    # scene decay, plus reading prior_exchanges across knocks as fact about what
    # Anna already sent — is its own concern from grading a reply, and both the
    # production judge and the catch judge need it identically. The retired lines
    # are JUDGE_MANDATE's old standalone "CONTINUITY DECAYS" paragraph, folded in.
    "THREAD_MANDATE": 250,
    "CATCH_JUDGE_MANDATE": 300,
}

# Words allowed per NEW docs/DECISIONS.md entry (dated 2026-08-02 or later).
# The log's own header has promised "the index of the conclusions — details
# live in git history" since April; July's entries ran 300-600 words of
# narrative each and the file reached 22k words, the accumulation pattern the
# word budgets killed everywhere else (2026-08-01, Andrew's forward cap). The
# archive is deliberately untouched: git owns the narratives already written.
DECISION_ENTRY_BUDGET = 150

# Code budgets for the Python surfaces (2026-07-31): the same ratchet, one layer
# down. The word budget held prose FLAT through July's build-out (8866 words on
# 07-01, 10671 on 07-31) while production Python went 2566 -> 6032 lines with a
# ~10% deletion rate — so April's "fight drift by adding" failure mode simply
# moved to the surface that had no ceiling. Growth past a budget is a red run,
# on the same terms as PROSE_BUDGETS: a raise rides the same diff as the growth
# and the commit names what it retired; a file that keeps hitting its ceiling is
# doing two jobs — split-or-retire, never the bump-the-number reflex.
#
# THE UNIT IS CODE LINES — blanks, comments and docstrings are NOT counted. A
# third of this codebase is comment, and that third is the diagnosis layer: the
# 07-31 silent-failure family was findable only because the "why" sits next to
# the mechanism. A budget that taxed explanation would buy smaller files by
# deleting the thing that makes them debuggable. This bounds mechanism only.
#
# Budgets were set at the 07-31 census rounded up to the next 25 with a minimum
# of 25 lines of headroom — tight enough to bind within weeks at a normal pace,
# loose enough that one ordinary bug fix does not trip it. Headroom is not an
# allowance to spend; it is the room to land a repair without ceremony.
CODE_BUDGETS = {
    "scripts/generate_callbacks.py": 100,
    # 775 -> 785 (2026-08-02) for the thread-continuity window. Retired in the
    # same diff: three inlined ISO-timestamp parsers collapsed into _ts(), the
    # two duplicated per-knock context builders replaced by one recent_exchanges,
    # and the dead reply_memo_script write (nothing ever read it). That paid for
    # most of the feature; these 10 are the remainder.
    # NOTE for the next raise: REFUSE it and split instead. ~150 of this file's
    # lines are prompt strings (JUDGE/SLIP/REACH/THREAD/CATCH mandates), which
    # code_lines counts as mechanism. mandates.py already exists as the home for
    # prompt canon — morning_knock.py made exactly this move on 2026-08-01 and
    # was re-censused DOWN afterwards. This file should follow, not grow again.
    "scripts/knock_reply.py": 785,
    # 700 -> 625 (2026-08-01): re-censused DOWN after OUTREACH_MANDATE moved to
    # mandates.py — the file sat at 699/700, one mechanical fix from a red build.
    # The split is the ceiling law working, not an allowance: prompt canon and
    # dispatch machinery are two concerns, and only one of them is code.
    # 625 → 632 (2026-08-05, Andrew): `parse_llm_response`, the finish_reason
    # guard. What it replaces is an IDIOM, not lines — the bare
    # `parse_llm_json(resp.choices[0].message.content)` repeated at all three
    # call sites, each of which reported a blown token ceiling as a parse error.
    # Stated plainly because the ratchet asks: this is +7 with nothing deleted,
    # the diagnosis layer growing, not mechanism. If this file trips again on
    # mechanism, that is the split-or-retire signal — not this.
    "scripts/morning_knock.py": 632,
    # The mandate as a module: almost entirely prompt string (word-budgeted as
    # OUTREACH_MANDATE in PROSE_BUDGETS above), so its code budget exists only
    # to satisfy the every-file-is-budgeted guard and to catch machinery
    # sneaking into a prose module.
    # 150 → 200 (2026-08-10) for the long-haul BASE_MANDATE and its five
    # SHAPE_CLAUSES, moved out of render_longhaul.py when THAT file hit 340/340 —
    # the split its own budget note prescribed, and the one morning_knock made on
    # 08-01. This is the ceiling law working as designed: the growth landed in the
    # prose module instead of the lane. Raising it here is cheap precisely because
    # this budget is a machinery TRAP, not a size limit — every line it now counts
    # is prompt string, and prompt strings are word-budgeted in PROSE_BUDGETS above.
    # What must still trip it is a def, a loop, or an import sneaking in.
    "scripts/mandates.py": 200,
    "scripts/push_queue.py": 250,
    "scripts/rebuild_rss.py": 350,
    "scripts/render_audio.py": 500,
    "scripts/render_chat.py": 100,
    "scripts/render_demo.py": 100,
    # 225 → 235 (2026-08-10). RETIRED IN THIS DIFF: `ask_json`'s private parse —
    # the char-0 `json.loads` and the `startswith("```")` fence-strip — replaced by
    # the `parse_llm_response` every other lane already used. That is a deletion;
    # the growth is the retry loop around it, which is mechanism and is the point:
    # a coin-flip parse is survivable in a lane that asks ONCE and fatal in one that
    # asks fifteen times, and the long-haul tape died at movement 5 of 15 proving it.
    # NOTE for the next raise: this file now holds a drill lane AND the LLM-call
    # helper three lanes import. That is the two-jobs smell, and the split is
    # already named — ask_json belongs beside parse_llm_json, not here.
    "scripts/render_drill.py": 235,
    # New file 2026-08-10 at 318 lines — the fourth audio lane. ~45 of those are
    # BASE_MANDATE + the five SHAPE_CLAUSES, which code_lines counts as mechanism
    # (prompt strings always do). Budgeted at 340 rather than 400: the headroom is
    # for diagnosis, not for a sixth shape. If this trips, the move is the one
    # morning_knock made on 08-01 and knock_reply was told to make — the mandates
    # go to mandates.py, prompt canon and dispatch machinery being two concerns —
    # NOT a bumped number.
    "scripts/render_longhaul.py": 340,
    "scripts/render_soak.py": 275,
    "scripts/run_studio.py": 425,
    "scripts/show_status.py": 125,
    # The state layer's shared vocabulary, split out of sync_state 2026-08-04:
    # paths, load/save, and token->canonical-key resolution. Ten scripts were
    # importing these FROM the state brain. Deliberately tiny and dependency-free
    # — if this file starts growing, something that mutates state has leaked in.
    "scripts/state_io.py": 60,
    # The slip ledger, split out of sync_state 2026-08-04. Always a subsystem
    # in a file about something else: it owns progress/slip_log.json outright
    # and is reached from three call sites. Imports state_io only — never
    # sync_state, which imports FROM here.
    "scripts/slips.py": 300,
    # The agent-facing session load, split out of sync_state 2026-08-04. A READ
    # surface: it renders state and never mutates it, which is why it no longer
    # lives inside the writer. Sits ABOVE sync_state in the import graph.
    "scripts/session_brief.py": 250,
    "scripts/studio_watchdog.py": 125,
    "scripts/suggest_targets.py": 575,
    # 1250 -> 1254 (2026-08-04): the tap lane's stage/commit/pull/push moved IN
    # from the "Log tap" step of anna.yml, where it was a hand-rolled
    # `git pull --rebase` with no union resolution and no derived re-render —
    # the one writing lane with no net under it. Nothing in THIS file was
    # retired, so this is a real raise, not a re-census: 5 lines of unbudgeted
    # YAML became 7 of budgeted Python. That is the ceiling law noticing
    # machinery migrate into a file that counts it from a file that doesn't, and
    # the alternative was leaving the gap open to keep a number flat.
    # 1254 -> 800 (2026-08-04): re-censused DOWN after the three-way split, the
    # same move morning_knock made on 08-01. The raise above still stands on its
    # own terms — the tap lane's 7 lines are still here, in cmd_knock_response —
    # but ~480 lines left for state_io, slips and session_brief, so a 1254
    # ceiling would have stopped measuring anything. The new number is the
    # post-split file plus normal headroom, not a target to grow into.
    "scripts/sync_state.py": 800,
}

# EXEMPT, deliberately: /extend Gate 7 requires a new case here the day a bug is
# fixed. Budgeting the file that carries the regression net would put the two
# mechanisms in direct conflict and the budget would win — a fixed bug would
# arrive with a reason not to pin it. Test volume is the one growth this system
# wants unbounded. The completeness guard below is what keeps this from becoming
# a hiding place: every OTHER scripts/*.py must carry a budget.
CODE_BUDGET_EXEMPT = {"scripts/smoke_test.py"}


def code_lines(src: str) -> int:
    """Executable lines: everything that is not blank, a comment, or a docstring."""
    return len(code_line_numbers(src))


def code_line_numbers(src: str) -> set[int]:
    """Which lines are mechanism. Split out of `code_lines` (2026-08-10) so a
    source-text assertion can search MECHANISM without matching the prose that
    explains it — a docstring quoting the code it retired otherwise fails the very
    check that proves the code is gone."""
    doc: set[int] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                doc.update(range(body[0].lineno, body[0].end_lineno + 1))
    comment = {tok.start[0] for tok in
               tokenize.generate_tokens(io.StringIO(src).readline)
               if tok.type == tokenize.COMMENT}
    out: set[int] = set()
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if not stripped or i in doc:
            continue
        if i in comment and stripped.startswith("#"):
            continue
        out.add(i)
    return out


def s18_size_budgets(mk, kr, sb: Path):
    print("\n18. Size budgets — prose (words) + Python (code lines) + static clean (0)")
    strings = {"OUTREACH_MANDATE": mk.OUTREACH_MANDATE,
               "JUDGE_MANDATE": kr.JUDGE_MANDATE,
               "REACH_MANDATE": kr.REACH_MANDATE,
               "SLIP_MANDATE": kr.SLIP_MANDATE,
               "THREAD_MANDATE": kr.THREAD_MANDATE,
               "CATCH_JUDGE_MANDATE": kr.CATCH_JUDGE_MANDATE}
    for rel, budget in PROSE_BUDGETS.items():
        words = (len(strings[rel].split()) if rel in strings
                 else len((sb / rel).read_text(encoding="utf-8").split()))
        check(f"{rel}: {words}/{budget} words", words <= budget,
              f"over by {words - budget} — retire lines, or raise the budget in this "
              f"same diff and name what it retired")

    # Read the real tree, not the sandbox: the budget binds the source as
    # committed, and the sandbox omits files by ignore-pattern.
    for rel, budget in CODE_BUDGETS.items():
        lines = code_lines((REAL_BASE / rel).read_text(encoding="utf-8"))
        check(f"{rel}: {lines}/{budget} code lines", lines <= budget,
              f"over by {lines - budget} — retire code, or raise the budget in this "
              f"same diff and name what it retired (comments and docstrings are "
              f"free; this counts mechanism only)")

    # STATIC CLEAN — the ratchet's fourth unit, budget zero (2026-08-04).
    #
    # The suite above proves BEHAVIOUR, and it can only prove what it executes.
    # Python resolves module globals at call time, so a name that no longer
    # exists is invisible until some test happens to run that exact line. On
    # 2026-08-04 the state_io extraction dropped the DEMOTE table; sync_state
    # still imported, every CLI path still ran, and 53 cases reported ALL GREEN
    # on a `--stuck-word` close that would have raised NameError — because
    # nothing demoted a word. pyflakes found it without running anything.
    #
    # This is the actionlint argument one language over. That linter was added
    # after a workflow that was valid YAML but rejected by GitHub sat unrunnable
    # through four pushes while this very suite went green beside it: "a file
    # that parses is not a workflow that runs" (smoke.yml). A file that imports
    # is not a file that runs either.
    #
    # Zero, not a number to tune. pyflakes has no severity levels and no
    # suppression pragma by design — it reports only what is nearly always a
    # bug, so the honest budget is none. A finding is either a defect or dead
    # code, and both get FIXED rather than allowed. When something must stay
    # that looks unused, make its purpose legible in code (run_studio's dispatch
    # lock became a module global with a comment) rather than parked behind a
    # directive this repo does not read.
    try:
        from pyflakes.api import checkPath
        from pyflakes.reporter import Reporter
    except ImportError:
        check("pyflakes is installed (declared in requirements.txt)", False,
              "pip install -r requirements.txt — the static gate cannot be "
              "skipped quietly; an absent linter reported as a pass is the "
              "silent no-op this rule exists to prevent")
    else:
        report = io.StringIO()
        found = sum(checkPath(py, Reporter(report, report))
                    for py in sorted((REAL_BASE / "scripts").glob("*.py")))
        check(f"pyflakes: {found}/0 findings across scripts/*.py", found == 0,
              f"undefined names, unused imports and dead locals are all defects "
              f"or dead code — fix them, never budget for them:\n{report.getvalue()}")

    # The decision log's forward entry cap — same law, third unit. Only entries
    # dated on/after 2026-08-02 are bound; a long conclusion goes in the commit
    # message, where the header says details live.
    entries, cur = [], None
    for line in (REAL_BASE / "docs" / "DECISIONS.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("- **"):
            cur = [line]
            entries.append(cur)
        elif cur is not None and (line.startswith("  ") or not line.strip()):
            cur.append(line)
        else:
            cur = None
    over = []
    for e in entries:
        m = re.search(r"\((\d{4}-\d{2}-\d{2})", " ".join(e[:2]))
        if m and m.group(1) >= "2026-08-02":
            words = sum(len(ln.split()) for ln in e)
            if words > DECISION_ENTRY_BUDGET:
                over.append(f"“{e[0][4:50]}…” at {words}")
    check(f"new DECISIONS entries stay ≤{DECISION_ENTRY_BUDGET} words "
          f"({len(entries)} entries scanned)", not over,
          "; ".join(over) + " — the log is an index of conclusions; the "
          "narrative belongs in the commit message (2026-08-01)")

    # A new file is the obvious way past a ceiling, so an unbudgeted one is a
    # red run rather than a silent exemption.
    on_disk = {f"scripts/{p.name}" for p in (REAL_BASE / "scripts").glob("*.py")}
    unbudgeted = sorted(on_disk - set(CODE_BUDGETS) - CODE_BUDGET_EXEMPT)
    check(f"every scripts/*.py carries a code budget ({len(on_disk)} files)",
          not unbudgeted,
          f"unbudgeted: {', '.join(unbudgeted)} — add each to CODE_BUDGETS in "
          f"the same diff that adds the file")


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
    kr.judge = lambda k, r, t, h=None, rr=None, **kw: canned_verdict([(w, "cold")])
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
        kr.judge = lambda k, r, t, h=None, rr=None, **kw: verdict
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

    # KF-13 (2026-08-04): the hold-cap. "chat" is the only verdict that keeps an item
    # open, so a mislabelled answer used to re-present it for ever — the 08-04 volley
    # burned six exchanges on two items and never reached item 4. One re-present is a
    # fair recovery; a second is a deadlock, so the pin advances on the second
    # consecutive chat no matter what the judge returned.
    #
    # TEETH: the way this silently does nothing is `held` never becoming true (wrong
    # field, or this exchange appended before the read) — which looks EXACTLY like the
    # old behaviour, green and broken. So drive the real entry point, then re-read the
    # log and assert the pin MOVED and the surface names the next item.
    k = volley_knock(nxt=2)
    k["exchanges"] = [{"reply": "wait, which one?", "verdict": "chat",
                       "reply_line": "ha, all good · still open · 2/3 — ask two"}]
    write_json(klog_path, [k])
    body = reply("sorry — still lost", dict(chat))
    entry = read_json(klog_path)[-1]
    check("second consecutive chat advances the pin (hold-cap)",
          entry["volley_next"] == 3 and entry["pinned_target"] == "t3",
          f"next={entry['volley_next']} pin={entry['pinned_target']}")
    check("capped advance puts the NEXT ask on the surface",
          "3/3 — ask three" in body and "still open" not in body, body)
    check("capped advance credits nothing — it is still a chat",
          entry["reply_verdict"] == "chat" and not entry.get("reply_fired"))

    # ...and `held` must be genuinely computed: a chat after a JUDGED exchange is this
    # item's first re-present, so it still holds. Without this the cap could be an
    # always-true constant and every check above would still pass.
    k = volley_knock(nxt=2)
    k["exchanges"] = [{"reply": "t1", "verdict": "cold", "reply_line": "adhu dhaan · 2/3 — ask two"}]
    write_json(klog_path, [k])
    body = reply("hang on", dict(chat))
    entry = read_json(klog_path)[-1]
    check("first chat after a judged reply still re-presents",
          "still open · 2/3 — ask two" in body and entry["volley_next"] == 2, body)

    # The cap is PER ITEM. A capped advance is itself logged "chat", so keying the cap on
    # the verdict would make the next chat advance again and the newly-pinned item would
    # never be re-presented once — the volley would walk itself shut on a run of chatter.
    # Keying on Python's own "still open · " marker is what makes this hold.
    k = volley_knock(nxt=2)
    k["exchanges"] = [{"reply": "thanks da", "verdict": "chat",
                       "reply_line": "got it · 2/3 — ask two"}]
    write_json(klog_path, [k])
    body = reply("one sec", dict(chat))
    entry = read_json(klog_path)[-1]
    check("chat after a capped advance re-presents, never double-advances",
          "still open · 2/3 — ask two" in body and entry["volley_next"] == 2,
          f"next={entry['volley_next']} body={body}")

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
    """Cues become air; they never eat the speech around them.

    THE SILENT NO-OP, and it ran for three weeks: when the parser drops a
    spoken line the render still succeeds — it is simply shorter. No crash, no
    warning, no lint, and a duration nobody has a reference for. M74 shipped
    with 18 of its 52 lines missing and taught the -க்கு போகணும் frame to an
    empty room. So every assertion below counts what reached a VOICE, not that
    the parse ran, and the last one holds the whole corpus to it (2026-08-10 —
    the half of the 07-18 audit that was missed)."""
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

    # A pause written INSIDE a spoken line is a beat in that line. The old
    # ordering asked "does this line CONTAIN a pause?" before "is this speech?",
    # so it answered yes and threw the dialogue away.
    inline = sb / "content" / "scripts" / "smoke_inline_pause.md"
    inline.write_text(
        "# Tier 2, Mission 98 — Smoke\n\n"
        "**RAJ (M):** He told our aunt, [Pause: 1 sec] \"station-kku poganum.\"\n\n"
        "**MAYA (F):** [Pause: 1 sec] Using that frame. [Pause: 0.5 sec] Need to go.\n\n"
        "**RAJ (M):** [pause] And she just fed him.\n\n"
        "[Pause: 2 sec]\n", encoding="utf-8")
    dlg, _ = ra.parse_script(str(inline))
    said = " ".join(d.get("text", "") for d in dlg)
    for fragment in ["He told our aunt,", "station-kku poganum.", "Using that frame.",
                     "Need to go.", "And she just fed him."]:
        check(f"inline pause keeps the speech: {fragment!r}", fragment in said, said)
    check("...and keeps it in written order, split around the beat",
          [d.get("text") for d in dlg[:3]] ==
          ["He told our aunt,", None, '"station-kku poganum."'], str(dlg[:3]))
    check("a fractional cue is honoured, not silently skipped",
          any(d.get("seconds") == 0.5 for d in dlg), str(dlg))
    check("a bare [pause] is one beat of air, never a spoken word",
          any(d.get("seconds") == 1.0 for d in dlg) and "pause" not in said.lower(), said)

    # THE CORPUS GUARD. The fixtures above prove the parser; this proves the
    # actual tank. Every line a writer meant to be heard must reach a voice —
    # a future script inventing a fourth pause dialect fails here, loudly.
    lost = []
    for path in sorted((REAL_BASE / "content" / "scripts").glob("*.md")):
        heard = " ".join(d.get("text", "")
                         for d in ra.parse_script(str(path))[0])
        for raw in path.read_text(encoding="utf-8").splitlines():
            m = ra.SPEAKER_RE.match(raw.strip())
            if not m:
                continue
            # re.split with one capture group interleaves text and the capture;
            # the even slots are the spoken pieces.
            for piece in ra.PAUSE_RE.split(m.group(2))[::2]:
                if piece and piece.strip() and piece.strip() not in heard:
                    lost.append(f"{path.name}: {piece.strip()[:40]}")
    check("no episode in the tank loses speech to a cue",
          not lost, f"{len(lost)} lost: {lost[:3]}")


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

    # --- GCP_SA_KEY → ADC, the same bridge anna.yml builds (2026-07-27) -----
    # CI writes the secret to a file and points GOOGLE_APPLICATION_CREDENTIALS
    # at it; a laptop had no equivalent, so a clone carrying the SAME secret in
    # .env still reported "this host cannot produce audio". A .env value must
    # also survive on one line, hence base64.
    import base64
    import contextlib
    import io
    saved_env = {k: os.environ.get(k) for k in ("GCP_SA_KEY", "GOOGLE_APPLICATION_CREDENTIALS")}
    key_file = Path(tempfile.gettempdir()) / "anna-gcp.json"
    try:
        doc = {"type": "service_account", "project_id": "smoke",
               "private_key": "-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n",
               "client_email": "a@smoke.iam.gserviceaccount.com"}
        for label, val in (("raw JSON", json.dumps(doc)),
                           ("base64 JSON", base64.b64encode(
                               json.dumps(doc).encode()).decode())):
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
            key_file.unlink(missing_ok=True)
            os.environ["GCP_SA_KEY"] = val
            check(f"{label} secret materializes a credentials file",
                  ra.materialize_sa_key() and key_file.exists())
            check(f"{label} secret points ADC at it",
                  os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == str(key_file))
            check(f"{label} round-trips intact",
                  json.loads(key_file.read_text(encoding="utf-8")) == doc)

        # A value that is not a key must be IGNORED, never written and never
        # half-configured: the real 2026-07-27 .env held 40 chars of something
        # else, and a silent write would have produced an auth error at
        # segment 0 instead of a legible reason before the render starts.
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        key_file.unlink(missing_ok=True)
        os.environ["GCP_SA_KEY"] = "2" * 40
        with contextlib.redirect_stdout(io.StringIO()) as warned:
            wrote = ra.materialize_sa_key()
        check("a non-key GCP_SA_KEY is ignored", wrote is None and not key_file.exists())
        check("...and says why, before any render starts",
              "not a service-account key" in warned.getvalue(), warned.getvalue())
        check("...and leaves ADC unconfigured rather than half-configured",
              not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

        # An operator-supplied path always wins over the secret.
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/preexisting.json"
        os.environ["GCP_SA_KEY"] = json.dumps(doc)
        check("an existing GOOGLE_APPLICATION_CREDENTIALS is never clobbered",
              ra.materialize_sa_key() is None
              and os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/preexisting.json")
    finally:
        key_file.unlink(missing_ok=True)
        for k, v in saved_env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

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
    # `status` moved to session_brief.py 2026-08-04; the law it asserts did not.
    status_src = (REAL_BASE / "scripts" / "session_brief.py").read_text(encoding="utf-8")
    check("the status drain-check uses the shared resolver",
          "split_payload(soak.get" in status_src)
    check("the watchdog drain-check uses the shared resolver",
          "split_payload" in (REAL_BASE / "scripts" / "studio_watchdog.py").read_text(encoding="utf-8"))

    # The rate rail, independent of any single root cause. Raised 1 -> 3 on
    # 2026-07-28 (Andrew) once repair-first commissioning made one-a-day the
    # binding constraint; the invariant was never the NUMBER, it is that the
    # number is FINITE — an unattended dispatcher with no ceiling is the
    # M72/M73/M74 evening waiting on the next stuck predicate.
    check("unattended production is capped", sw.MAX_UNATTENDED_PER_DAY >= 1)
    check("...and the cap is finite — never removed outright",
          isinstance(sw.MAX_UNATTENDED_PER_DAY, int)
          and sw.MAX_UNATTENDED_PER_DAY < 10,
          f"got {sw.MAX_UNATTENDED_PER_DAY!r} — raise it if it binds, never unbound")
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
    # ONE expression still (the 07-24 collapse of three holds). The interval is
    # back to hourly (2026-07-30): */30 ran for two days and was measured against
    # hourly slice-for-slice — 108.9 vs 108.7 median minutes between runs — so the
    # denser expression bought nothing at twice the runner minutes. GitHub drops
    # proportionally more of a denser schedule. The single-expression property and
    # the "don't re-open without data" conclusion are what this guards.
    check("one cron expression replaces three",
          anna.count("- cron:") == 1)
    check("the tick is hourly (*/30 measured identical, at 2x runner minutes)",
          '- cron: "0 * * * *"' in anna)
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

    # --- one serialised lane; nothing cancelled (2026-07-28) ---------------
    # Per-knock_id groups let two reply lanes run in parallel. On 07-28 a reply
    # to a stale notification raced the reply to that morning's knock; both
    # appended to the tail of the feedback_log array, the rebase conflicted, and
    # commit_and_push died — losing a judged exchange, not just a green tick.
    conc = anna.split("concurrency:", 1)[1].split("jobs:", 1)[0]
    conc_keys = "\n".join(ln for ln in conc.splitlines() if not ln.lstrip().startswith("#"))
    check("every lane shares ONE concurrency group",
          re.search(r"^\s*group:\s*anna\s*$", conc_keys, re.M) is not None)
    check("no lane is keyed by the knock it answers", "knock_id" not in conc_keys)
    # The half that makes serialising safe. Without it the group holds ONE
    # pending run and GitHub cancels it when the next reply arrives — which
    # would silently eat the middle of a burst (six dispatches in six minutes,
    # 07-28). `queue: max` holds 100, FIFO.
    check("the group queues instead of cancelling",
          re.search(r"^\s*queue:\s*max\s*$", conc_keys, re.M) is not None)
    # GitHub rejects the whole file if these two combine.
    check("cancel-in-progress stays false (illegal beside queue: max)",
          re.search(r"^\s*cancel-in-progress:\s*false\s*$", conc_keys, re.M) is not None)
    # `queue:` shipped 2026-05-07, after actionlint's newest release — the lint
    # step carries a message-exact suppression so the key can land. It is a lag,
    # not a waiver: if the pin ever moves past the key, drop the flag.
    check("the lint step tolerates the queue key actionlint doesn't know yet",
          "-ignore 'unexpected key \"queue\" for \"concurrency\" section'" in smoke_yml)

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
    events, saved = [], (mk.WAKING_START_HOUR, mk.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY)
    real_push, real_commit, real_feed = pq.push_to_phone, pq.commit_and_push, pq.refresh_feed
    pq.push_to_phone = lambda body, url=None, knock_id="", requested=False: (
        events.append(("push", url)))
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
        mk.WAKING_START_HOUR, mk.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 99
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
        mk.WAKING_START_HOUR, mk.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = saved
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
          "JUDGE_MANDATE + \"\\n\" + SLIP_MANDATE + \"\\n\" + REACH_MANDATE" in src)

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
    # `time.tzset()` is POSIX-only. Calling it unguarded raised AttributeError on
    # Andrew's Windows box, and because it fired mid-suite it aborted every case
    # AFTER this one — so the local health check has never once run to completion
    # there, only in CI (2026-07-31). The ASSERTIONS are host-zone independent by
    # construction (fromtimestamp is handed rr.LOCAL_TZ explicitly), so they run
    # everywhere; only the belt-and-braces UTC-host SIMULATION needs the syscall,
    # and it is skipped where the OS has none. Never guard by re-raising: a
    # cross-platform gap in the harness must not read as a failure of the code.
    can_simulate_host_tz = hasattr(time, "tzset")
    try:
        if can_simulate_host_tz:
            os.environ["TZ"] = "UTC"
            time.tzset()
        pub = email.utils.format_datetime(datetime.fromtimestamp(stamp, rr.LOCAL_TZ))
        # Expected offset comes from LOCAL_TZ at that instant. Hardcoding "-0400"
        # made this a test of New York rather than of "Andrew's zone" (2026-08-09).
        want_off = datetime.fromtimestamp(stamp, rr.LOCAL_TZ).strftime("%z")
        check("a pubDate is stamped in Andrew's zone on a UTC host", pub.endswith(want_off),
              f"got {pub}, wanted offset {want_off}")
        check("the pubDate names the local wall clock", "19:56:25" in pub, f"got {pub}")
    finally:
        if can_simulate_host_tz:
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
    # The OTHER population (2026-07-26): non-deck words, governed by
    # floor_gap_targets. Both never-surfaced and identical on every other term,
    # so the ask count is the only thing that can separate them — and `-a` sorts
    # first alphabetically, which is what the old key fell through to.
    lex.update({
        "smoke:floor-a": {"gloss": "asked 2 days ago", "phonetic": [], "type": "chunk",
                          "recognition": "comfortable", "production": "none",
                          "seen_in": [1], "last_surfaced": None},
        "smoke:floor-b": {"gloss": "never asked", "phonetic": [], "type": "chunk",
                          "recognition": "comfortable", "production": "none",
                          "seen_in": [1], "last_surfaced": None},
    })
    deck_file = sb / "curriculum" / "trip_deck.json"
    lex_path = sb / "progress" / "lexicon.json"
    klog_path = sb / "progress" / "knock_log.json"
    saved = (deck_file.read_bytes(), lex_path.read_bytes(), klog_path.read_bytes())
    # Yesterday's volley asked surv-tail as its SECOND item — `expected_target`
    # names only item 1, so items 2..n were invisible to the ask count while the
    # volley is the deck's main volume channel.
    recent_ts = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
    old_ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    klog = [{"acted": True, "timestamp": recent_ts, "modality": "volley",
             "expected_target": "smoke:surv-mid", "body": "volley 1/2",
             "volley": [{"target": "smoke:surv-mid", "ask": "a"},
                        {"target": "smoke:surv-tail", "ask": "b"}]},
            {"acted": True, "timestamp": old_ts, "modality": "knock",
             "expected_target": "smoke:floor-a", "body": "the floor ask"}]
    try:
        write_json(deck_file, [{"tamil": k, "register": v["_reg"], "gloss": "x"}
                               for k, v in fixture.items()])
        write_json(lex_path, lex)
        write_json(klog_path, klog)

        asked = st.recent_ask_counts(klog, lex)
        check("a volley's later items count as asked, not just item 1",
              asked.get("smoke:surv-tail") == 1, f"got {asked}")
        check("the volley's opening item still counts",
              asked.get("smoke:surv-mid") == 1, f"got {asked}")

        # Ask-count breaks the tie the 50-item never-worked cohort sits in:
        # surv-tail and surv-unseen are both NEVER_SURFACED, and tail was asked.
        deck = st.deck_status(lex, today=today)
        order = [t["word"] for t in deck["pending"]]
        check("within the never-worked cohort, least-asked leads (not alphabetical)",
              order.index("smoke:surv-unseen") < order.index("smoke:surv-tail"), f"got {order}")
        check("ask-count stays subordinate to tier: an asked survival item still "
              "outranks an unasked dessert one",
              order.index("smoke:surv-tail") < order.index("smoke:dessert-new"), f"got {order}")
        check("the ask count rides on the item for the menu's warning",
              [t["asks"] for t in deck["pending"] if t["word"] == "smoke:surv-tail"] == [1],
              f"got {deck['pending']}")
        check("the knock menu names the recent ask",
              "asked/shown 1×" in mk.deck_due_list(), f"got {mk.deck_due_list()}")
        # One owner: the knock channel no longer re-sorts, so its picks must be
        # the selector's own order.
        vt = [t["target"] for t in mk.volley_targets(n=4)]
        pend = [t["word"] for t in deck["pending"]]
        check("the volley reads the selector's order, it does not re-sort",
              [w for w in pend if w in vt] == vt, f"volley={vt} pending={pend}")
        check("recent_ask_counts has one home",
              not hasattr(mk, "recent_ask_counts"), "the knock-side copy survived")

        # THE 2026-07-26 defects, both halves. (1) The cooldown-as-coverage key
        # forgot floor-a's work on day 4 — that reset is why ~24 words cycled
        # forever while 110 of 134 were unreachable. (2) The knock rep counter
        # MINED Anna's prose for mentions — the same-day audit measured 100% of
        # live knock "reps" as mentions. Reps are DECLARED now: the judge seam
        # increments the lexicon counter per fired word (any verdict — partial
        # counts) and `rep_counts` reads that counter, never the log.
        kr = importlib.import_module("knock_reply")
        kr.apply_verdict({"fired": [{"word": "smoke:floor-a", "verdict": "hinted"}]},
                         {}, lex, [])
        check("a judged fired word increments the declared rep counter",
              lex["smoke:floor-a"].get("reps") == 1, f"got {lex['smoke:floor-a']}")
        reps = st.rep_counts(lex)
        mention = {"acted": True, "timestamp": recent_ts, "modality": "text",
                   "expected_target": "", "body": "Anna printed smoke:floor-b in prose"}
        check("a word PRINTED in a knock is a mention, never a rep",
              "smoke:floor-b" not in reps, f"got {reps}")
        check("the mention still feeds the reveal-cooldown — its one legitimate home",
              st.recent_ask_counts(klog + [mention], lex).get("smoke:floor-b") == 1,
              "the cooldown lost its probe matching")
        check("coverage counts LIFETIME reps, not the 3-day cooldown",
              reps.get("smoke:floor-a") == 1 and not asked.get("smoke:floor-a"),
              f"got {reps} / asked {asked}")
        focus, _bg = st.floor_gap_targets(lex, today, 20, asked=asked, reps=reps,
                                          cohort=[])
        order = [t["word"] for t in focus]
        check("the never-drilled word leads the drilled one (not alphabetical)",
              order.index("smoke:floor-b") < order.index("smoke:floor-a"), f"got {order}")
        check("the rep count rides on the item so the ticket can show it",
              [t["reps"] for t in focus if t["word"] == "smoke:floor-a"] == [1],
              "floor item lost its reps")
        check("the selector's default path reads the same declared counter",
              [t["word"] for t in st.floor_gap_targets(lex, today, 20, cohort=[])[0]] == order,
              "the default path disagrees with the injected one")
        # One law, one definition: the deck prefixes tier and then defers.
        check("both selectors share the ordering law",
              st.coverage_key({"word": "x", "reps": 0}) < st.coverage_key({"word": "x", "reps": 1}),
              "coverage_key does not lead with reps")

        # Re-run the ordering laws with an empty log, so the coverage assertions
        # below read the same fixture the rest of the case was written against.
        write_json(klog_path, [])
        deck = st.deck_status(lex, today=today, asked={})
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
        # A global deficit in a warm voice is guilt machinery (2026-07-17), and
        # this number is bigger and scarier than the burn rate that rule was
        # written for. Both surfaces that carry it must say so.
        import contextlib
        import io
        argv, out = sys.argv, io.StringIO()
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = argv
        check("the ticket marks coverage as an engineering number",
              "never narrated" in out.getvalue(), "coverage block carries no narration guard")

        # The headline meter carries the same count, so a green sprint can never
        # again hide a starved deck.
        cd = ss.compute_deck(lex)
        check("the status meter carries the coverage count",
              (cd["untouched"], cd["surv_untouched"], cd["catch_untouched"]) == (4, 2, 1),
              f"got {cd}")
    finally:
        deck_file.write_bytes(saved[0])
        lex_path.write_bytes(saved[1])
        klog_path.write_bytes(saved[2])


def s33_catch_response_pairs(mk, sb: Path):
    """Catch-and-response is a first-class curriculum kind, and the schema had no
    way to say it (2026-07-26 audit). The pairing lived as English prose in
    `note`/`gloss` — "the maami's line at the table" — so nothing could drill a
    pair as a pair, and nothing noticed when `seed-deck` dropped the response
    while its prompt kept its deck slot. `pairs_with` is the one relation the
    schema carries; it must resolve inside the deck file, ride onto the lexicon,
    and reach both surfaces that show catch items."""
    print("\n33. Catch/response pairs: hear X → say Y is representable (2026-07-26)")
    import contextlib
    import io
    st = importlib.import_module("suggest_targets")
    ss = importlib.import_module("sync_state")
    deck_file = sb / "curriculum" / "trip_deck.json"
    lex_path = sb / "progress" / "lexicon.json"
    saved = (deck_file.read_bytes(), lex_path.read_bytes())

    class Args:
        deck = "trip"

    def seed(entries):
        write_json(deck_file, entries)
        a = Args()
        a.file = str(deck_file)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ss.cmd_seed_deck(a)
        return buf.getvalue(), json.loads(lex_path.read_text(encoding="utf-8"))

    def ticket_text():
        argv, out = sys.argv, io.StringIO()
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = argv
        return out.getvalue()

    prompt = "இன்னும் கொஞ்சம் சாப்பிடுங்க"
    answer = "வேண்டாம்மா, வயிறு நிறைஞ்சிடுச்சு"
    paired = [
        {"tamil": prompt, "gloss": "eat more", "type": "chunk", "direction": "catch",
         "recognition": "struggled", "phonetic": ["innum konjam saapidunga"],
         "pairs_with": answer},
        {"tamil": answer, "gloss": "no thanks, I'm full", "type": "chunk",
         "recognition": "struggled", "phonetic": ["vendaamma"]},
    ]
    try:
        write_json(lex_path, {})
        out, lex = seed(paired)
        check("the pair rides from the deck file onto the lexicon",
              lex[prompt].get("pairs_with") == answer, f"got {lex.get(prompt)}")
        check("the answer is a FIRE item — the catch half alone is not the win",
              lex[answer].get("direction") == "fire", f"got {lex.get(answer)}")

        deck = st.deck_status(lex, today=date_cls.today(), asked={})
        cp = [t for t in deck["catch_pending"] if t["word"] == prompt]
        check("deck_status resolves the pair for the drill",
              cp and cp[0]["pairs_with"] == answer and cp[0]["response_gloss"] == "no thanks, I'm full",
              f"got {cp}")
        check("the ticket names the answer under the line he'll hear",
              "he answers:" in ticket_text(), "the ear-only block hid the pair")
        check("the knock menu marks a paired item so Anna plays HER line",
              "[pair]" in mk.deck_due_list() and "never quiz the catch half alone" in mk.deck_due_list(),
              f"got {mk.deck_due_list()}")

        # THE regression: the response was dropped from the deck file while its
        # prompt stayed. Silent before, then a loud drop — a HARD seed-time
        # error now (2026-07-26): the seed is refused whole BEFORE any write,
        # so a split pair can never half-land. Fix the file, re-run.
        before = lex_path.read_bytes()
        try:
            seed([paired[0]])
            check("a split pair refuses the whole seed", False, "seed did not exit")
        except SystemExit as e:
            check("a split pair refuses the whole seed, loudly", e.code == 1,
                  f"exit code {e.code}")
        check("a refused seed writes NOTHING — no half-landed deck",
              lex_path.read_bytes() == before, "lexicon changed on a refused seed")
    finally:
        deck_file.write_bytes(saved[0])
        lex_path.write_bytes(saved[1])


def s34_focus_and_background(sb: Path):
    """Two budgets, not one ranked list (Andrew, 2026-07-26: "10-15 getting most
    reps until they fire cold, the remaining on a slow guaranteed background").

    Coverage-first and dense-repetition genuinely conflict: one ranked list either
    touches every word once a month and graduates nothing, or hammers a dozen and
    lets the tail rot. The first attempt at the fix used a 3-day cooldown as the
    coverage term and reached 24 of 134 words in a simulated month, spending 100
    of 240 asks on ten words. Splitting the budget is what makes both hold."""
    print("\n34. Focus set + background: dense reps without starving the tail (2026-07-26)")
    st = importlib.import_module("suggest_targets")
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    klog_path = sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())
    today = date_cls.today()

    # 20 words, all recognized and none cold: more than the focus set can hold.
    lex = {f"smoke:w{i:02d}": {"gloss": f"w{i}", "phonetic": [], "type": "chunk",
                               "recognition": "comfortable", "production": "none",
                               "seen_in": [1], "last_surfaced": None,
                               **({"reps": 3} if i < 5 else {})}
           for i in range(20)}
    try:
        write_json(lex_path, lex)
        write_json(klog_path, [])
        # cohort=[] is the SEED path — no membership stored yet.
        focus, background = st.floor_gap_targets(lex, today, 99, cohort=[])
        fw = [t["word"] for t in focus]

        check("the focus set is capped at FOCUS_SIZE",
              len(focus) == st.FOCUS_SIZE, f"got {len(focus)}")
        check("everything else lands in background, nothing is dropped",
              len(focus) + len(background) == len(lex),
              f"{len(focus)}+{len(background)} != {len(lex)}")
        check("seeding gives words already started their focus seats",
              all(f"smoke:w{i:02d}" in fw for i in range(5)), f"got {fw}")
        check("open seats are filled from the never-drilled words",
              len([w for w in fw if not lex[w].get("reps")]) == st.FOCUS_SIZE - 5, f"got {fw}")
        check("the background is exposure-only and knows it",
              all(t["band"] == "background" for t in background), "band mislabelled")
        check("within the focus set the least-drilled lead, so the cohort advances together",
              [t["reps"] for t in focus] == sorted(t["reps"] for t in focus), f"got {fw}")

        # Membership is STORED STATE (2026-07-26): reconcile persists the seed,
        # and held seats then stand regardless of what any counter says —
        # a membership fact in a file cannot be reallocated by a counting bug.
        cohort = st.reconcile_focus(lex, [])
        check("reconcile seeds the same cohort the seed derivation shows",
              sorted(cohort) == sorted(fw), f"got {cohort}")
        noisy = {w: 99 for w in cohort}  # a corrupt counter must not move seats
        held = [t["word"] for t in st.floor_gap_targets(lex, today, 99, reps=noisy,
                                                        cohort=cohort)[0]]
        check("stored membership holds its seats against counter noise",
              sorted(held) == sorted(cohort), f"got {held}")

        # Graduation: cold leaves the cohort for good and the seat refills from
        # the background order — the ONLY way membership changes.
        lex["smoke:w00"]["production"] = "cold"
        cohort2 = st.reconcile_focus(lex, cohort)
        check("a word that fires cold leaves the cohort for good",
              "smoke:w00" not in cohort2, f"got {cohort2}")
        check("the other seats survive the graduation",
              set(cohort) - {"smoke:w00"} <= set(cohort2), f"got {cohort2}")
        focus2, bg2 = st.floor_gap_targets(lex, today, 99, cohort=cohort2)
        check("its seat is refilled from the background",
              len(focus2) == st.FOCUS_SIZE, f"got {len(focus2)}")
        check("the graduated word is gone from both budgets",
              "smoke:w00" not in [t["word"] for t in focus2] + [t["word"] for t in bg2],
              "a graduated word came back")

        # The tail must actually be reachable — the property the first fix lacked.
        # 6 drills + 2 exposures a day is Anna's pacing, not a code constant —
        # the property under test is that the ORDER spreads reps, at any pace.
        seen, reps = set(), {}
        for _ in range(40):
            f, b = st.floor_gap_targets(lex, today, 99, asked={}, reps=dict(reps),
                                        cohort=[])
            for t in f[:6]:
                seen.add(t["word"])
                reps[t["word"]] = reps.get(t["word"], 0) + 1
            # Exposure closes the loop through the REAL delivery seam
            # (sync_state.mark_exposed — the write every dose channel calls).
            # Without it the background order never changes and the SAME two
            # words are exposed forever: rotation is only guaranteed because
            # being exposed moves a word to the back of its own queue.
            for t in b[:2]:
                seen.add(t["word"])
                ss.mark_exposed(lex, [t["word"]], today=today.isoformat())
        check("every word is reachable — no word is stranded behind the alphabet",
              len(seen) == len(lex) - 1, f"reached {len(seen)} of {len(lex) - 1}")
        check("no word is hammered while others wait",
              max(reps.values()) - min(reps.values()) <= 2, f"spread {sorted(reps.values())}")
        check("the delivery stamp counts as well as dates",
              any(r.get("exposures") for r in lex.values()), "mark_exposed wrote no count")
        check("less-exposed sorts ahead of more-exposed — the 07-26 flip of `-soaked`",
              st.coverage_key({"word": "x", "exposures": 0})
              < st.coverage_key({"word": "x", "exposures": 3}),
              "coverage_key still rewards prior exposure")
    finally:
        lex_path.write_bytes(saved[0])
        klog_path.write_bytes(saved[1])


def s35_quiet_hours_chokepoint(sb: Path):
    """Quiet hours belong to `push_to_phone`, not to each lane (2026-07-26).

    They used to be enforced per-lane: `rails_gate` for knocks, `in_waking_window`
    in the queue, and a hand-rolled hour compare in both `run_studio` and
    `render_soak` — FOUR copies, and `render_drill` had none, which is how a drill
    reached the phone at 23:42. The gap was not on a CI lane, so nothing had fired
    from the runner — this case is what keeps it that way when a lane is added."""
    print("\n35. Quiet hours: one chokepoint, no per-lane copies (2026-07-26)")
    import contextlib
    import io
    mk = importlib.import_module("morning_knock")
    src_dir = Path(__file__).parent

    real_urlopen = mk.urllib.request.urlopen
    sent = []

    class FakeResp:
        status = 200
        def read(self): return b""
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, *a, **k):
        sent.append(getattr(req, "full_url", req))
        return FakeResp()

    # Built from LOCAL_TZ, not from frozen UTC instants. They used to be literals
    # (`3:42Z  # 23:42 EDT`), which quietly encoded America/New_York into the
    # quiet-hours case: the moment learner.json named another zone that same
    # instant became mid-morning and the check inverted (2026-08-09). A guard for
    # a rule stated in local hours has to be built in local hours.
    noon_l = datetime.now(mk.LOCAL_TZ).replace(hour=12, minute=0, second=0, microsecond=0)
    night = noon_l.replace(hour=23, minute=42).astimezone(timezone.utc)
    noon = noon_l.astimezone(timezone.utc)
    real_env = os.environ.get("ANNA_PUSH_WEBHOOK_URL")
    try:
        mk.urllib.request.urlopen = fake_urlopen
        os.environ["ANNA_PUSH_WEBHOOK_URL"] = "http://smoke.invalid/push"
        check("the waking window has ONE definition",
              mk.in_waking_window(noon) and not mk.in_waking_window(night),
              "in_waking_window disagrees with the rails")

        real_now = mk.in_waking_window
        mk.in_waking_window = lambda now=None: False
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                pushed = mk.push_to_phone("a drill at 23:42", None)
            check("an UNrequested push is refused during quiet hours",
                  pushed is False and not sent, f"sent={sent}")
            check("the refusal says where the artifact went",
                  "on the feed for the morning" in out.getvalue(), f"got {out.getvalue()!r}")
            with contextlib.redirect_stdout(io.StringIO()):
                pushed = mk.push_to_phone("your reply", None, requested=True)
            check("a REQUESTED push still lands — answering his tap is not an interruption",
                  pushed is True and len(sent) == 1, f"sent={sent}")
        finally:
            mk.in_waking_window = real_now
    finally:
        mk.urllib.request.urlopen = real_urlopen
        if real_env is None:
            os.environ.pop("ANNA_PUSH_WEBHOOK_URL", None)
        else:
            os.environ["ANNA_PUSH_WEBHOOK_URL"] = real_env

    # No lane may re-implement the rule; every push must go through the chokepoint.
    for name in ("run_studio.py", "push_queue.py", "render_drill.py", "render_soak.py"):
        src = (src_dir / name).read_text(encoding="utf-8")
        check(f"{name} does not hand-roll the waking-hour compare",
              "WAKING_START_HOUR <=" not in src, f"{name} carries its own copy")
    check("in_waking_window has one home",
          "def in_waking_window" not in (src_dir / "push_queue.py").read_text(encoding="utf-8"),
          "the queue's copy survived")


def s36_soak_order_carries_shape(sb: Path):
    """The soak order is a BRIEFING, not a word list (2026-07-27, Andrew: "soak
    is one flavour of briefing — why does learner.json need to change?").

    It didn't: nothing validates that file. What was broken is that `cmd_update`
    REBUILT the dict from three keys on every write, so any other key died at the
    next close — which is why the 2026-07-18 narrated_drama decision ("commissioned
    via soak order, form: …, scale: …") had no implementation anywhere in the repo.
    A shape could be decided in canon and never reach a renderer."""
    print("\n36. The soak order carries shape and focus, and no lane loops (2026-07-27)")
    import contextlib
    import io
    ss = importlib.import_module("sync_state")
    sbf = importlib.import_module("session_brief")

    def _capture(fn):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            fn(argparse.Namespace())
        return out.getvalue()

    learner_path = sb / "progress" / "learner.json"
    lex_path = sb / "progress" / "lexicon.json"
    saved = (learner_path.read_bytes(), lex_path.read_bytes())

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        for k, v in defaults.items():
            kw.setdefault(k, v)
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(argparse.Namespace(**kw))
        return read_json(learner_path).get("soak_order", {})

    try:
        write_json(lex_path, {"போறேன்": {"gloss": "I go", "phonetic": ["poren"],
                                         "type": "chunk", "recognition": "solid",
                                         "production": "cold", "seen_in": [],
                                         "last_surfaced": None}})
        learner = read_json(learner_path)
        learner["soak_order"] = {}
        write_json(learner_path, learner)

        order = update(soak_payload=["போறேன்"], soak_seed="s",
                       soak_focus="the -ஆச்சு tail over போ", soak_channel="soak")
        check("the order carries a focus", order.get("focus") == "the -ஆச்சு tail over போ")
        check("the order carries a channel", order.get("channel") == "soak")

        # THE BUG: a later close that touches only the payload used to rebuild the
        # dict down to three keys and silently drop everything else.
        order = update(soak_payload=["போறேன்"])
        check("a payload-only rewrite does not eat the focus",
              order.get("focus") == "the -ஆச்சு tail over போ", f"got {order}")
        check("a payload-only rewrite does not eat the channel",
              order.get("channel") == "soak", f"got {order}")

        # …and the inverse: setting a shape alone must not wipe the words.
        order = update(soak_focus="the -ல negative over முடி")
        check("a focus-only rewrite does not eat the payload",
              order.get("payload") == ["போறேன்"], f"got {order}")

        # And an unknown key survives, so the NEXT shape needs no writer change.
        learner = read_json(learner_path)
        # Deliberately a key that does NOT exist in canon. This fixture used to
        # be `scale: "long"`, which read as evidence that `scale` was real —
        # it never was (no writer, no reader; deleted 2026-08-05).
        learner["soak_order"]["not_a_real_key"] = "sentinel"
        write_json(learner_path, learner)
        check("an unnamed key survives a rewrite — the door is open",
              update(soak_payload=["போறேன்"]).get("not_a_real_key") == "sentinel")

        # A soak-channel order can never be cleared by the newest-EPISODE compare
        # (soak registers no episode), which is the 2026-07-23 M72/M73/M74
        # re-dispatch loop with a new trigger. Delivery clears it instead.
        write_json(sb / "progress" / "episodes.json", {})
        status = _capture(sbf.cmd_status)
        check("an undelivered soak order routes to the soak lane, not the studio",
              "render_soak.py" in status and "run_studio.py" not in status, status[:400])
        check("the rendering lane's own stamp clears it — no second dispatch",
              ss.mark_soak_delivered("soak")
              and "produced ✓" in _capture(sbf.cmd_status))

        # The shape that hung a real order through a SUCCESSFUL render: a
        # Tamil-script payload word that is legitimately pre-lexicon. It passes
        # split_payload by design, but mark_exposed can only stamp rows that
        # exist, so any last_surfaced-based check waits on it forever.
        learner = read_json(learner_path)
        learner["soak_order"]["payload"] = ["நிறைஞ்சிடுச்சு"]   # not in this lexicon
        write_json(learner_path, learner)
        res, unres = ss.split_payload(["நிறைஞ்சிடுச்சு"], read_json(lex_path))
        check("a pre-lexicon Tamil payload word is resolvable, not junk",
              res == ["நிறைஞ்சிடுச்சு"] and not unres, f"{res} / {unres}")
        check("...and a delivered order still clears with one in the payload",
              "produced ✓" in _capture(sbf.cmd_status))

        # A stamp from ANOTHER lane must not clear this one.
        ss.mark_soak_delivered("drill")
        check("a stamp from a different lane does not clear a soak order",
              "NOT YET PRODUCED" in _capture(sbf.cmd_status))
        ss.mark_soak_delivered("soak")

        # A NEW order supersedes an old delivery — `from` moves, the stamp doesn't.
        update(soak_payload=["போறேன்"])
        check("a freshly-set order is pending again despite the old stamp",
              "NOT YET PRODUCED" in _capture(sbf.cmd_status))
        ss.mark_soak_delivered("soak")

        # The reader half: the brief only reaches the sheet on the soak channel.
        rs = importlib.import_module("render_soak")
        rs_focus, rs_payload = rs.soak_brief()
        check("render_soak reads the order's focus",
              rs_focus == "the -ல negative over முடி", f"got {rs_focus!r}")
        check("a focused sheet gets the carousel brief",
              "CAROUSEL" in rs.FOCUS_BRIEF and "stays out" in rs.FOCUS_BRIEF)

        # A lane that ignores its payload can never satisfy the order that
        # dispatched it — that is the re-dispatch loop arriving through the door.
        check("the ordered words lead the menu even when the week-window missed them",
              [r["word"] for r in rs.with_payload([], rs_payload)] == ["போறேன்"])
        check("an ordered word already in the menu is not duplicated",
              len(rs.with_payload([{"word": "போறேன்", "gloss": "", "production": "cold",
                                    "last_surfaced": None}], rs_payload)) == 1)

        update(soak_payload=["போறேன்"], soak_channel="episode")
        check("an episode-channel order does NOT hijack the soak lane",
              rs.soak_brief() == (None, []))

        # --- The commissioned form: doctrine since 2026-07-18, wired 2026-07-27 ---
        st = importlib.import_module("suggest_targets")
        check("the divergence gate cannot roll a commissioned form by itself",
              all(f not in st.FORMS for f in st.COMMISSIONED_FORMS))
        check("ALL_FORMS is the one palette the CLI and the gate share",
              set(st.ALL_FORMS) == set(st.FORMS) | set(st.COMMISSIONED_FORMS))

        order = update(soak_form="narrated_drama")
        check("the order carries a commissioned form", order.get("form") == "narrated_drama")
        check("suggest_targets reads it back", st.commissioned_form() == "narrated_drama")

        sidecars = [{"mission": 70, "register": "dread", "episode_form": "classic",
                     "dramatic_ingredient": list(st.INGREDIENTS)[0]}]
        spec = st.scene_spec(sidecars, st.commissioned_form())
        check("a commissioned form overrides the gate", spec["form"] == "narrated_drama")
        check("and says so, so the Director does not re-pick", spec["commissioned"])
        check("register still diverges — commissioning a form costs no other variety",
              spec["register"] != "dread")
        check("an uncommissioned spec stays inside the rotated palette",
              st.scene_spec(sidecars)["form"] in st.FORMS
              and not st.scene_spec(sidecars)["commissioned"])

        # A typo must not steer the Director off-palette, and must never mean
        # "no episode" — the order still dispatches, the gate just rolls.
        learner = read_json(learner_path)
        learner["soak_order"]["form"] = "narrated_dramaa"
        write_json(learner_path, learner)
        with contextlib.redirect_stdout(io.StringIO()) as warned:
            bad = st.commissioned_form()
        check("an unbuildable form is ignored, not obeyed", bad is None)
        check("...and says so out loud rather than failing silently",
              "cannot build" in warned.getvalue(), warned.getvalue())

        update(soak_form="narrated_drama", soak_channel="soak")
        check("a form on a non-episode order does not reach the studio",
              st.commissioned_form() is None)
    finally:
        learner_path.write_bytes(saved[0])
        lex_path.write_bytes(saved[1])


def s37_repair_earns_the_dose(sb: Path):
    """The repair earns the dose (2026-07-28, Andrew's spoken felt signal:
    "I don't feel like Anna is commissioning enough audio, and specifically
    audio to close the gap in the mistakes I'm making... I shouldn't have to
    beg for a soak or an episode").

    The system had a channel-ROUTING law (audio_channels.md) and a PRODUCTION
    law (studio.md) and NO COMMISSIONING law: nothing said which gaps earn a
    dose. Close & Log step 2 was a menu ("payload... MAY be a seed order"), so
    the campaign's forward pull outranked the backward repair need and his
    errors went undosed — pakkathula reached the order as one of three items
    and the collision was still open hours later.

    This is a PROSE rule, so a prose lint is its only regression net. The
    2026-07-24 lesson (a dropped rule must be hunted in code, prompts, skills
    and tests) applies in reverse: assert every surface that carries it."""
    print("\n37. The repair earns the dose — commissioning is a priority (2026-07-28)")
    # The law lived in audio_channels.md from 07-28 and moved to its own file on
    # 2026-08-01 when the refused-in-advance third raise came due — "what a dose
    # carries" and "which channel carries it" are two files now, each pointing
    # at the other. Close & Log keeps a pointer, because that is where it fires.
    routing = (REAL_BASE / "protocol" / "commissioning.md").read_text(encoding="utf-8")
    check("the commissioning law exists", "repair earns the dose" in routing)
    check("...and it is an ORDER of precedence, not a menu",
          "Backward beats forward" in routing)
    # The repair population used to be enumerated in prose ("hinted, recast, or
    # corrected and still came out wrong") and scoped to "the day's" repairs —
    # which meant the chat session's own day, so a mistake made on the phone was
    # never in the draw at all (2026-07-30 audit: the same recast shipped 07-08,
    # 07-25 and 07-30). The population is now the slip ledger, which is that
    # enumeration made durable and cross-lane.
    check("...drawing the payload from the ledger, not one session's memory",
          "live slips" in routing and "sync_state.py slips" in routing)
    check("...and the ledger spans every lane, not just the day's session",
          "every* lane" in routing or "every lane" in routing)
    check("...and he never has to ask for it", "never has\nto ask" in routing
          or "never has to ask" in routing)
    check("a survived collision earns its own order, not a share of a mixed one",
          "earns its own order" in routing)
    # 2026-07-28 evening, Andrew: "using them in context can be very effective for
    # sticking in my brain... it shouldn't be the only choice when I'm struggling
    # regardless of whether two words sound similar." The scope rule had a format
    # clause welded to it ("a chunk fires it") and a chunk is what the soak loop
    # makes — so the rule read as "every mix-up gets the loop". Scope and format
    # are now separate questions, and format follows the ERROR, not the collision.
    check("the collision rule no longer prescribes a format",
          "chunk fires it" not in routing)
    check("...it says so explicitly, so the clause cannot grow back",
          "says nothing about its format" in routing)
    channels = (REAL_BASE / "protocol" / "audio_channels.md").read_text(encoding="utf-8")
    check("format follows the error, and capacity keeps its veto",
          "Capacity vetoes" in channels and "the ERROR chooses" in channels)
    check("...naming the mouth-takes-the-wrong-one case as an EPISODE, not a loop",
          "his mouth takes the wrong one" in channels)
    check("a repeated mistake escalates the format instead of repeating it",
          "same mistake twice through one format" in channels
          and "never loop harder" in channels)
    check("the forward seed order survives as the fallback, not the default",
          "seed order" in routing and "Only when none are live" in routing)
    check("the escalation law names the counter that makes it fireable",
          "ledger counts recurrences" in channels)
    check("the two halves are two files, each pointing at the other (08-01 split)",
          "audio_channels.md" in routing and "commissioning.md" in channels)

    session = (REAL_BASE / "protocol" / "daily_session.md").read_text(encoding="utf-8")
    # The PRIORITY must be stated where the order is actually set — a pointer
    # alone would make the loop depend on Anna following a link mid-close. The
    # wording moved to the ledger's vocabulary on 2026-07-30 ("live slips draw
    # first" IS backward-beats-forward); the duplicated law behind it was
    # retired to a pointer, so assert the rule and the owner, not the phrasing.
    check("Close & Log fires the rule at the moment the order is set",
          "repair earns the dose" in session and "Live slips draw first" in session)
    check("...and points at the file that owns it", "audio_channels.md" in session)
    check("...and says an unverified slip is a check, not a commission",
          "checks, not commissions" in session)

    # The glossary is what a new engineer reads before touching the interface.
    glossary = (REAL_BASE / ".claude" / "skills" / "orient" / "references"
                / "glossary.md").read_text(encoding="utf-8")
    check("the glossary carries the priority too", "repair earns the dose" in glossary)

    # A retry that does not exist is worse than no retry: it makes a dropped
    # dose look covered. The local cron was retired 2026-07-24.
    anna_skill = (REAL_BASE / ".claude" / "skills" / "anna"
                  / "SKILL.md").read_text(encoding="utf-8")
    check("Anna's skill does not promise a cron retry that was retired",
          "hourly local cron) retries any miss" not in anna_skill)


def s38_teach_enters_the_lexicon(sb: Path):
    """A word taught in-session can now exist (2026-07-28).

    The pakkam/paakkalaam deep-dive taught பக்கத்துல, ஆச்சு and இருக்கேன் and
    recorded none of them: --mastered/--comfortable overstate a first contact,
    --stuck-word and --mark-seen refuse an absent key, and seed-deck is a
    deck-authoring flow. So the live teaching surface wrote nothing, the next
    ticket could not know, and a queued soak order named a word the lexicon had
    never heard of. This is the write-side twin of the 07-27 credit-the-word-he-
    said fix: that taught the judge to credit a substitution, this lets a taught
    word exist at all."""
    print("\n38. A word taught in-session enters the lexicon (2026-07-28)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    lex_path, learner_path = sb / "progress" / "lexicon.json", sb / "progress" / "learner.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes())

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        return read_json(lex_path), out.getvalue()

    try:
        word = "பக்கத்துல"
        lex, _ = update(teach=[f"{word}=beside/next to"])
        rec = lex.get(word)
        check("a taught word is created", rec is not None, "still absent")
        check("...at struggled recognition, not solid",
              rec and rec["recognition"] == "struggled", f"got {rec}")
        check("...with production unset, so the floor cannot inflate",
              rec and rec["production"] == "none", f"got {rec}")
        check("...carrying the gloss", rec and rec["gloss"] == "beside/next to")
        check("...and seen today", rec and rec["last_surfaced"] == ss.local_today().isoformat())

        # Teaching runs before the axes, so teach-then-fire in ONE close resolves.
        lex, _ = update(teach=["ஆச்சு=it happened / it's done"], produced_cold=["ஆச்சு"])
        check("a word taught and fired in the same close is credited",
              lex["ஆச்சு"]["production"] == "cold", f"got {lex.get('ஆச்சு')}")

        # Re-teaching must not silently demote a word he already owns.
        lex, _ = update(teach=[word])
        check("re-teaching a known word does not reset its recognition",
              lex[word]["recognition"] == "struggled", f"got {lex[word]}")
        lex, out = update(teach=["pakkathula"])
        check("a phonetic teach is refused, so keys stay canonical",
              "pakkathula" not in lex and "phonetic" in out)
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])


def s41_slip_ledger(kr, sb: Path):
    """Mistakes accumulate, cross lanes, and reach the next lesson (2026-07-30).

    The audit that produced this: 'romba nalla irukku' → 'irundhuchu' was pushed
    back on 07-08, 07-25 and 07-30, near-verbatim, and nothing in the system
    could notice. Three independent holes, one per direction of the loop:

    1. CAPTURE — the diagnosis existed only as prose in knock_log's reply_line.
       The synthesis lived in learner.last_debrief, a single string OVERWRITTEN
       every close, so an error survived exactly as long as Anna retyped it.
    2. CREDIT — apply_verdict is upgrade-only on the phone, and the 07-30 volley
       scored ரொம்ப நல்லா இருக்கு as a hinted FIRE off a reply whose own recast
       corrected its tense. A wrong answer moved the axis and took a rep.
    3. RESURFACE — reply_line was read back only by the reveal-window and
       deck-coverage scans. Nothing on the status digest or the ticket said what
       he keeps getting wrong, so selection re-offered the item and the scene
       re-asked it the same way.
    """
    print("\n41. The slip ledger — errors accumulate and steer the next lesson (2026-07-30)")
    sl = importlib.import_module("slips")
    st = importlib.import_module("suggest_targets")
    slip_path = sb / "progress" / "slip_log.json"
    if slip_path.exists():
        slip_path.unlink()

    # --- 2. credit: a corrected item is not a fire -----------------------------
    d = kr.normalize_verdict(
        {"verdict": "hinted",
         "fired": [{"word": "ரொம்ப நல்லா இருக்கு", "said": "Romba nalla irukku",
                    "verdict": "hinted"}],
         "slips": [{"tag": "past-tense", "said": "irukku",
                    "want": "ரொம்ப நல்லா இருக்கு", "note": "present for a past scene"}],
         "reply_line": "x"},
        "Market ku ponnam, Romba nalla irukku")
    check("a word corrected in the same breath is not credited", d["fired"] == [])
    check("...and the headline degrades rather than celebrating", d["verdict"] == "miss")
    check("...and the drop is loud, not silent",
          any("corrected in the same breath" in u for u in d["unverified"]))
    d = kr.normalize_verdict(
        {"verdict": "cold",
         "fired": [{"word": "ஒரு நிமிஷம்", "said": "Oru nimsham", "verdict": "cold"}],
         "slips": [{"tag": "stranger-nga", "said": "pesa", "want": "pesunga", "note": "n"}],
         "reply_line": "x"}, "Oru nimsham")
    check("an unrelated slip does not cost him a clean fire",
          [i["word"] for i in d["fired"]] == ["ஒரு நிமிஷம்"] and d["verdict"] == "cold")
    check("a slip with no tag cannot enter the ledger",
          kr.normalize_verdict({"verdict": "chat", "slips": [{"said": "x", "want": "y"}]},
                               "")["slips"] == [])

    # --- 1. capture: append-only, cross-lane, dated by when it happened --------
    sl.append_slips([{"tag": "Past tense", "said": "irukku", "want": "irundhuchu",
                      "note": "present for a past scene"}],
                    lane="knock", when="2026-07-25")
    sl.append_slips([{"tag": "past-tense", "said": "irukku", "want": "irundhuchu",
                      "note": "present for a past scene"}],
                    lane="chat", when="2026-07-30")
    rows = read_json(slip_path)
    check("the ledger is append-only — the second write keeps the first", len(rows) == 2)
    check("...and tag casing/punctuation collapses to one pattern",
          {r["tag"] for r in rows} == {"past-tense"})
    check("...and each row keeps the lane it came from",
          {r["lane"] for r in rows} == {"knock", "chat"})
    pats = {p["tag"]: p for p in sl.slip_patterns(today=date_cls(2026, 7, 30))}
    p = pats["past-tense"]
    check("a mistake made twice is a pattern, not a one-off", p["pattern"] and p["count"] == 2)
    check("...spanning the real days it happened on, not the day it was written",
          p["span_days"] == 5 and p["first"] == "2026-07-25")
    check("...and it crosses lanes — the phone and the table are one history",
          sorted(p["lanes"]) == ["chat", "knock"])
    check("a pattern nothing was ever built for is NOT told to change format",
          p["uncommissioned"] and not p["escalate"])

    # A dose was commissioned and he slipped anyway — that is the escalation the
    # audio_channels law describes, and it could not fire before this counter.
    sl.append_slips([{"tag": "past-tense", "said": "irukku", "want": "irundhuchu"}],
                    lane="knock", dose_channel="soak", when="2026-07-30")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 7, 30))}["past-tense"]
    check("a slip that survived a dose escalates the FORMAT",
          p["escalate"] and p["channels"] == ["soak"])

    # --- retire → verify → revive: the surface forgets, then ASKS AGAIN --------
    # Andrew, 2026-07-30: "words shouldn't disappear into the aether. They should
    # be retired and then come back." Retiring on the clock alone cannot tell
    # "he learned it" from "nothing ever asked him", so a retired slip that was
    # never confirmed landed comes back as a CHECK rather than vanishing.
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 9, 30))}["past-tense"]
    check("a long-quiet slip stops being live evidence", not p["live"])
    check("...but its history is still on the record", p["count"] == 3)
    check("...and it does NOT vanish — it returns as an unverified check",
          p["unverified"] and not p["closed"])
    block = "\n".join(sl.format_slip_block([p]))
    check("...which the reader surface asks for by name",
          "UNVERIFIED" in block and "past-tense" in block)
    check("...and an unverified slip is a check, not a commission",
          "not a dose" in block.lower() or "worth a check" in block.lower())

    # Closing is an OBSERVATION and it is DATED. The bare-tag list this replaced
    # silenced a pattern permanently — muting the most informative event the
    # ledger can record: one you believed had landed, coming back.
    out = sl.record_slip_test(["past-tense:landed"], today="2026-09-30")
    check("a landed test closes the slip as of that date",
          out and out[0][1] == "landed")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 10, 1))}["past-tense"]
    check("...and a closed slip stops surfacing entirely",
          p["closed"] and not p["unverified"] and sl.format_slip_block([p]) == [])
    check("...but the close is dated, not permanent", p["closed_on"] == "2026-09-30")

    sl.append_slips([{"tag": "past-tense", "said": "irukku", "want": "irundhuchu"}],
                    lane="knock", when="2026-11-02")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 11, 2))}["past-tense"]
    check("A CLOSED SLIP THAT COMES BACK IS LIVE AGAIN — the close is voided",
          p["live"] and not p["closed"] and p["reopened"])
    check("...with its whole history intact, not restarted at one", p["count"] == 4)

    # A failed test is itself a recurrence — one ledger, not a parallel record.
    sl.record_slip_test(["past-tense:missed"], today="2026-11-03")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 11, 3))}["past-tense"]
    check("a failed test lands on the ledger as a recurrence",
          p["count"] == 5 and p["live"])
    check("a malformed test report is rejected, not guessed at",
          sl.record_slip_test(["nonsense"])[0][1] == "bad")

    # --- 3. resurface: status, and the ticket that picks the next lesson -------
    block = "\n".join(sl.format_slip_block(sl.slip_patterns(today=date_cls(2026, 7, 30))))
    check("the digest names the pattern, not just that a reply happened",
          "past-tense" in block and "irundhuchu" in block)
    check("...and says a recast does not close it",
          "closed by firing right" in block)

    src = (REAL_BASE / "scripts" / "session_brief.py").read_text(encoding="utf-8")
    check("the session digest shows what Anna CORRECTED on the phone",
          "corrected: " in src)
    check("the knock reply commits the ledger — an unpushed slip dies with the runner",
          "commit_paths.append(SLIP_LOG_PATH)" in
          (REAL_BASE / "scripts" / "knock_reply.py").read_text(encoding="utf-8"))

    # The ticket hangs the slip off the item it belongs to, so a selected word
    # arrives with HOW it keeps failing, not just that it is due.
    # An explicit key, not one scraped from the sandbox lexicon: the linkage under
    # test is slip → row, and it must hold whether or not the want resolves.
    key = "frame:day-recap"
    sl.append_slips([{"tag": "ending", "said": "ponnam", "want": "ponnom", "word": key,
                      "note": "the ending"}], lane="knock", when="2026-07-30")
    hung = st.slips_by_word(sl.slip_patterns(today=date_cls(2026, 7, 30)))
    check("a slip attaches to the lexicon row it is about", key in hung)
    check("...and annotates it with what he actually said",
          "SLIPPED" in st.slip_note(hung[key]))
    check("a single slip still annotates an item already selected",
          "once" in st.slip_note(hung[key]))

    slip_path.unlink()


def s39_ticket_carries_the_commission(sb: Path):
    """The episode lane must CONSUME the commission (2026-07-28, first real
    exercise of the repair-first law).

    frame:youknow-la was commissioned as an episode; M77 came back drilling the
    computed FOCUS SET with the payload absent. Cause: the ticket had no
    commission section at all. The order reached the Director only as one prose
    clause in DIRECTOR ("read the soak-order in progress/learner.json") — an
    agentic read competing with a code-assembled list headed "DRILL these until
    they fire cold" — and lost. In the SAME run the commissioned FORM landed
    perfectly, because it arrived through scene_spec() as computed context.

    That is the repo's own doctrine failing in the direction it predicts:
    code-assembled context beats an agentic read when the invariant is known.
    So the payload arrives the way the form does."""
    print("\n39. The ticket carries the commission, ahead of the focus set (2026-07-28)")
    import contextlib, io
    st = importlib.import_module("suggest_targets")
    learner_path = sb / "progress" / "learner.json"
    saved = learner_path.read_bytes()

    order = {"payload": ["frame:youknow-la"], "scene_seed": "Two aunties on the phone.",
             "focus": "The -ல tag as THE gossip opener.", "from": "2026-07-28",
             "channel": "episode", "form": "phone_call"}

    def ticket(o):
        learner = read_json(learner_path)
        if o is None:
            learner.pop("soak_order", None)
        else:
            learner["soak_order"] = o
        write_json(learner_path, learner)
        argv, out = sys.argv, io.StringIO()
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = argv
        return out.getvalue()

    try:
        text = ticket(order)
        check("the commissioned payload is IN the ticket, not left to an agentic read",
              "frame:youknow-la" in text.split("FOCUS SET")[0], text[:400])
        check("...with the focus that says what the dose is for",
              order["focus"] in text)
        check("...and the scene seed", order["scene_seed"] in text)
        check("...headed so it cannot be read as one more list",
              "THE COMMISSION" in text and "OUTRANKS" in text)
        check("the focus set says out loud that it is outranked",
              "A COMMISSION IS LIVE" in text.split("FOCUS SET")[1])
        check("the form is still pinned by the same order",
              "COMMISSIONED by the soak order" in text)

        # A consumed order must not keep steering the next episode. Before this,
        # commissioned_form() ignored `delivered` entirely.
        done = ticket({**order, "delivered": {"channel": "episode", "at": "2026-07-28"}})
        check("a delivered order stops commanding the ticket",
              "THE COMMISSION" not in done)
        check("...and stops pinning the form, so the divergence gate rolls again",
              "COMMISSIONED by the soak order" not in done)

        # The episode lane never stamps `delivered` — it clears itself by
        # registering the payload into episodes.json. Reading only the stamp
        # would leave a filled order commanding every future ticket, which is
        # the 07-23 three-episodes-in-one-evening failure wearing a new hat.
        eps_path = sb / "progress" / "episodes.json"
        saved_eps = eps_path.read_bytes()
        try:
            eps = read_json(eps_path)
            newest = str(max((int(k) for k in eps), default=0) + 1)
            eps[newest] = {"title": f"Mission {newest}", "listens": 0,
                           "words": ["frame:youknow-la"], "duration_min": 1.6,
                           "produced": "2026-07-28"}
            write_json(eps_path, eps)
            carried = ticket(order)
            check("an order the newest episode already carries is no longer live",
                  "THE COMMISSION" not in carried)
            check("...and the divergence gate takes the form axis back",
                  "COMMISSIONED by the soak order" not in carried)
        finally:
            eps_path.write_bytes(saved_eps)

        soaked = ticket({**order, "channel": "soak", "delivered": None})
        check("an order routed elsewhere does not command the episode ticket",
              "THE COMMISSION" not in soaked)
        empty = ticket({"payload": [], "channel": "episode"})
        check("an empty order is not a commission", "THE COMMISSION" not in empty)
        check("no order at all still builds a ticket",
              "SESSION TICKET" in ticket(None))
    finally:
        learner_path.write_bytes(saved)


def s40_drill_consumes_its_commission(sb: Path):
    """`--soak-channel drill` was a dead value (2026-07-28).

    `sync_state` accepted and stored it, `render_drill` never read it, and no lane
    stamped it delivered. Three consequences, all silent: the repair became an
    ordinary deck drill, the order stayed pending, and the session-open auto-drain
    then dispatched an EPISODE for it — the one lane Andrew had explicitly not
    chosen. Of the three channels on the routing table, only two worked.

    LEAD, not replace (Andrew's call): the repair leads and takes three angles,
    the due deck fills out the rest. A whole tape built from one item is the slow
    repetitive loop this lane exists to escape."""
    print("\n40. The drill lane consumes its commission (2026-07-28)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    rd = importlib.import_module("render_drill")
    lex_path, learner_path = sb / "progress" / "lexicon.json", sb / "progress" / "learner.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes())

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))

    def brief():
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            focus, lead = rd.drill_brief()
        return focus, lead, out.getvalue()

    try:
        # Planted rather than scanned: earlier cases blank the sandbox lexicon, and
        # this one needs one fire-side row and one ear-only row to exist for sure.
        fireable, earonly = "பக்கத்துல", "விட்டுடு"
        lex = read_json(lex_path)
        lex[fireable] = {"gloss": "beside/next to", "recognition": "struggled",
                         "production": "none"}
        lex[earonly] = {"gloss": "let it go", "recognition": "struggled",
                        "production": "none", "direction": "catch", "deck": "trip"}
        write_json(lex_path, lex)

        update(soak_payload=[fireable], soak_focus="close the pakkam collision",
               soak_channel="drill")
        focus, lead, _ = brief()
        check("a drill-routed order reaches the drill lane at all",
              [t["word"] for t in lead] == [fireable], f"got {lead}")
        check("...carrying the focus that says what the repair is",
              focus == "close the pakkam collision", f"got {focus!r}")

        # The repair leads; the deck fills the rest. Not replace.
        deck = [{"word": "X", "gloss": "", "kind": "chunk"},
                {"word": "Y", "gloss": "", "kind": "frame"}]
        merged = rd.with_lead(deck, lead)
        check("the repair leads the tape and the deck follows",
              [t["word"] for t in merged] == [fireable, "X", "Y"], f"got {merged}")
        check("...and a lead item already on the deck list is not drilled twice",
              [t["word"] for t in rd.with_lead(deck + lead, lead)]
              == [fireable, "X", "Y"])
        check("a commission still gets a tape when the deck has nothing due",
              [t["word"] for t in rd.with_lead([], lead)] == [fireable])

        # The mandate has to SAY it, or the writer treats the lead as deck rep one.
        brief_text = rd.COMMISSION_BRIEF.format(n=1, focus="\nWhat: the collision")
        check("the sheet writer is told the lead is a repair, not a deck rep",
              "REPAIR" in brief_text and "THREE items instead of one" in brief_text)
        check("...and told to vary the situation rather than the target",
              "never the target" in brief_text)

        # Ear-only is a recognition win. A drill's silence is a production demand,
        # and the deck law is that catch items are NEVER forced to fire.
        if earonly:
            update(soak_payload=[earonly], soak_channel="drill")
            _, lead_catch, warned = brief()
            check("an ear-only item routed to the drill lane is refused, not demanded",
                  lead_catch == [], f"got {lead_catch}")
            check("...and says why, so the mis-route is visible",
                  "ear-only" in warned and "soak or episode" in warned, warned)

        update(soak_payload=[fireable], soak_channel="soak")
        check("an order routed to another lane does not reach the drill",
              brief()[1] == [])
        update(soak_payload=[fireable], soak_channel="episode")
        check("...including the default episode lane", brief()[1] == [])

        # Without the stamp the order reads pending forever and the drain sends
        # an episode for a repair the drill already delivered.
        # The pieces above are only worth having if main() actually calls them.
        # Stub the LLM and run the real entry point through --dry-run.
        update(soak_payload=[fireable], soak_focus="the pakkam collision",
               soak_channel="drill")
        seen = {}
        real_write, real_argv = rd.write_sheet, sys.argv
        try:
            def spy(pending, n_lead=0, focus=None):
                seen.update(pending=[t["word"] for t in pending],
                            n_lead=n_lead, focus=focus)
                return {"title": "T", "intro": "i", "outro": "o", "items": []}
            rd.write_sheet = spy
            sys.argv = ["render_drill.py", "--dry-run"]
            with contextlib.redirect_stdout(io.StringIO()):
                rd.main()
        finally:
            rd.write_sheet, sys.argv = real_write, real_argv
        check("main() hands the commission to the sheet writer",
              seen.get("pending", [None])[0] == fireable, f"got {seen.get('pending')}")
        check("...counted as lead items, so the brief fires",
              seen.get("n_lead") == 1, f"got {seen.get('n_lead')}")
        check("...with the focus attached", seen.get("focus") == "the pakkam collision")

        with contextlib.redirect_stdout(io.StringIO()):
            stamped = ss.mark_soak_delivered("drill")
        order = read_json(learner_path)["soak_order"]
        check("the drill lane can stamp the order consumed", stamped)
        check("...naming itself as the lane that carried it",
              (order.get("delivered") or {}).get("channel") == "drill", f"got {order}")
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])


def s44_a_commission_can_discharge_the_flag(sb: Path):
    """NEVER COMMISSIONED could only ever be cleared by FAILING again (2026-07-31).

    `uncommissioned` read `agg["channels"]`, fed by `dose_channel` — stamped onto
    a slip ROW at the instant it is written, from whatever soak order happened to
    be standing. So the flag answered "has he ever slipped while SOME order
    stood", never "was a dose built for THIS". Nothing anywhere associated a
    commission with a tag, so building the right dose could not clear it and only
    a fresh slip could: cleared by failing, ignored by fixing. Proof on the day it
    was found — the போனோம் episode shipped and read `produced ✓` while both slips
    it was built for still printed the warning, permanently. A warning that can
    never be discharged becomes noise you learn to read past, which is the
    mechanical reason it was walked past rather than agent inattention.

    Andrew's option A: the close DECLARES which debt an order pays. Python cannot
    infer it — a payload word and a slip tag are different vocabularies, and the
    slips that most need a dose (1pl-past-om, past-tense) hang off no single word.

    The second bug, found wiring the first and far worse: `write_thin_learner` is
    a WHITELIST, and `slip_closes` was not on it. So `--slip-tested tag:landed`
    wrote a close and the very same close's update DELETED it. No slip had ever
    actually closed since the mechanism shipped 2026-07-30, and nothing surfaced
    the loss, because a wiped close looks exactly like never having tested."""
    print("\n44. A commissioned dose discharges the flag; a close survives (2026-07-31)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    sl = importlib.import_module("slips")
    learner_path = sb / "progress" / "learner.json"
    slip_path = sb / "progress" / "slip_log.json"
    saved = (learner_path.read_bytes(),
             slip_path.read_bytes() if slip_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[])

    def update(**kw):
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))

    def pat(tag):
        return {p["tag"]: p for p in sl.slip_patterns()}.get(tag)

    try:
        slip_path.write_text("[]", encoding="utf-8")
        learner = read_json(learner_path)
        for k in ("slip_closes", "slip_commissions"):
            learner.pop(k, None)
        write_json(learner_path, learner)

        # A pattern: same mistake twice, nothing ever built for it.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "smoke-tag", "said": "x", "want": "y"}],
                            lane="chat", when="2026-01-01")
            sl.append_slips([{"tag": "smoke-tag", "said": "x", "want": "y"}],
                            lane="chat", when=ss.local_today().isoformat())
        p = pat("smoke-tag")
        check("a twice-made mistake with no dose reads NEVER COMMISSIONED",
              p and p["uncommissioned"], f"got {p and p.get('uncommissioned')}")
        check("...and the surface names the flag that would clear it",
              any("--slip-commissioned smoke-tag" in ln
                  for ln in sl.format_slip_block([p])), "the instruction is missing")

        # Commissioning WITHOUT an order standing must refuse, not book a lie.
        # (The 08-01 gate would refuse this whole close — a declared tag with no
        # order does not cover the debt — so the override rides along; the gate
        # itself is s46's subject.)
        update(slip_commissioned=["smoke-tag"],
               no_commission="smoke: exercising the phantom-dose refusal")
        check("a commission with no standing order is refused",
              pat("smoke-tag")["uncommissioned"], "it booked a phantom dose")

        # The real path: set the order and name its debt in ONE close.
        update(soak_payload=["ஸ்மோக்பேலோடு"], soak_channel="episode",
               slip_commissioned=["smoke-tag"])
        p = pat("smoke-tag")
        check("declaring the debt in the same close clears the flag",
              not p["uncommissioned"], "still NEVER COMMISSIONED")
        check("...recording which lane carried it",
              p["commissions"] and p["commissions"][-1]["channel"] == "episode",
              f"got {p['commissions']}")
        check("...and the surface reports the dose instead of the warning",
              any("dose commissioned" in ln for ln in sl.format_slip_block([p]))
              and not any("NEVER COMMISSIONED" in ln for ln in sl.format_slip_block([p])))
        check("...but it does NOT accuse the new dose of having failed",
              not p["escalate"], "escalated on evidence that predates the dose")

        # It survives the next ordinary close — the whitelist bug.
        update(produced_cold=[], debrief="a later close")
        check("the commission survives a later update",
              not pat("smoke-tag")["uncommissioned"], "the whitelist ate it")

        # Only a slip DATED AFTER the dose escalates.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "smoke-tag", "said": "x", "want": "y"}],
                            lane="chat", when="2099-01-01")
        check("a slip made AFTER the dose escalates the format",
              pat("smoke-tag")["escalate"], "escalation never fired")

        # A tag with no history is a typo, not a debt.
        update(soak_payload=["ஸ்மோக்பேலோடு"], soak_channel="soak",
               slip_commissioned=["no-such-tag-at-all"])
        check("an unknown tag cannot be booked as commissioned",
              "no-such-tag-at-all" not in sl.slip_commissions(), "a typo booked a debt")

        # --- the whitelist bug, on the mechanism it actually broke -------------
        with contextlib.redirect_stdout(io.StringIO()):
            sl.record_slip_test(["smoke-tag:landed"])
        check("a close is recorded", sl.slip_closes().get("smoke-tag"))
        update(debrief="the close that used to erase it")
        check("...and SURVIVES the update that follows it",
              sl.slip_closes().get("smoke-tag"), "write_thin_learner deleted the close")
    finally:
        learner_path.write_bytes(saved[0])
        if saved[1] is not None:
            slip_path.write_bytes(saved[1])
        else:
            slip_path.unlink(missing_ok=True)


def s42_session_log_one_row_per_day(sb: Path):
    """A close is one session however many update calls it takes (2026-07-31).

    The momentum log appended unconditionally, so every extra `update` in a close
    forged a session — repairing a bad key, or setting the soak order in a second
    command, each minted a row. By 2026-07-31 it held 38 rows for 26 real
    session-days: 12 duplicated dates, the counter ~46% high, and show_status's
    last-5 view padded with near-empty rows. The quiet half is worse than the
    cosmetic one: cold_fires_recent() and fires_today() SUM word lists across
    entries, so a word logged twice in one close inflated the trailing pace that
    the burn rate — and therefore the sprint's whole honest-meter story — is
    computed from. Merging restores the documented contract rather than guarding
    it from outside."""
    print("\n42. One session-day, one log row (2026-07-31)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    learner_path = sb / "progress" / "learner.json"
    slog_path = sb / "progress" / "session_log.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes(),
             slog_path.read_bytes() if slog_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        return read_json(slog_path) or []

    try:
        slog_path.write_text("[]", encoding="utf-8")
        today = ss.local_today().isoformat()
        # Seed two words the sandbox lexicon can actually resolve, so the axes move.
        lex = read_json(lex_path)
        for w in ("ஸ்மோக்ஒன்", "ஸ்மோக்டூ"):
            lex.setdefault(w, {"gloss": "smoke", "phonetic": [], "recognition": "solid",
                               "production": "none", "seen_in": []})
        write_json(lex_path, lex)

        log = update(produced_cold=["ஸ்மோக்ஒன்"])
        check("the first call of a close opens the day's row", len(log) == 1, f"got {len(log)}")

        log = update(produced_cold=["ஸ்மோக்டூ"])
        check("a second update in the same close does NOT forge a session",
              len(log) == 1, f"got {len(log)} rows")
        check("...and its fires land in the same row",
              set(log[-1]["cold"]) == {"ஸ்மோக்ஒன்", "ஸ்மோக்டூ"}, f"got {log[-1]['cold']}")

        # The pace-corrupting half: re-logging one word must not count it twice.
        before = len(log[-1]["cold"])
        log = update(produced_cold=["ஸ்மோக்ஒன்"])
        check("...a word re-logged in the same day stays one fire, not two",
              len(log[-1]["cold"]) == before, f"got {log[-1]['cold']}")

        log = update(debrief="STORY SO FAR: first pass")
        log = update(soak_payload=["ஸ்மோக்டூ"], debrief="STORY SO FAR: rewritten")
        check("a later debrief supersedes rather than appending a row",
              len(log) == 1 and log[-1]["note"] == "STORY SO FAR: rewritten",
              f"got {len(log)} rows, note={log[-1]['note'][:40]!r}")

        log = update(produced_cold=["ஸ்மோக்ஒன்"])
        check("...and an update carrying no debrief never blanks the one written",
              log[-1]["note"] == "STORY SO FAR: rewritten", f"got {log[-1]['note'][:40]!r}")

        check("the row is still dated today", log[-1]["date"] == today)
        check("...and still carries the snapshot meters",
              "floor_pct" in log[-1] and "engines_pct" in log[-1], f"got {sorted(log[-1])}")

        # Yesterday's row is untouched: merging is same-day only, never a fold-up.
        log = read_json(slog_path)
        log.insert(0, {"date": "2020-01-01", "cold": ["old"], "hinted": [], "demoted": [],
                       "listened": [], "note": "ancient"})
        write_json(slog_path, log)
        log = update(produced_cold=["ஸ்மோக்டூ"])
        check("an older day is never merged into today", len(log) == 2, f"got {len(log)}")
        check("...and keeps its own note", log[0]["note"] == "ancient")

    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])
        if saved[2] is not None:
            slog_path.write_bytes(saved[2])


def s53_prune_duplicate_lexicon_rows(sb: Path):
    """Duplicate lexicon rows, and the rule that must NEVER fire (2026-08-04).

    Three near-identical key pairs turned up in an audit. Only two were
    duplicates: `எங்க` is "our (exclusive)" and `எங்க?` is "Where?" — two
    lemmas separated by one character of punctuation. The obvious architecture
    (normalise keys, strip terminal punctuation) would have merged them and
    destroyed a real distinction, so the duplicate signal is the PHONETIC plus
    strict domination, never the key.

    Gate 7.2 — this tool's silent failure is not doing nothing, it is deleting
    a row nobody can get back. The no-op reads as "no duplicates found", which
    is also what a correct run on clean data prints; the dangerous state is the
    opposite one. So every check below is about what must SURVIVE, and the
    homograph pair is the case that matters: it shares a stem, differs only by
    punctuation, and must come through untouched."""
    print("\n53. Duplicate lexicon rows are pruned on phonetic + domination (2026-08-04)")
    import contextlib, io, argparse as _ap
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    try:
        row = lambda **kw: {"gloss": "x", "phonetic": [], "recognition": "struggled",
                            "production": "none", "seen_in": [], "last_surfaced": None, **kw}
        lex = {
            # the real duplicate: same phonetic, and the stray carries nothing
            "அப்படியா?!": row(phonetic=["appadiya"], recognition="comfortable",
                              production="cold", type="chunk", deck="trip"),
            "அப்படியா": row(phonetic=["appadiya"]),
            # THE HOMOGRAPH — one character apart, different words, different
            # phonetics. A key-normalising rule merges these; this one must not.
            "எங்க": row(phonetic=["enga"], recognition="solid", production="cold"),
            "எங்க?": row(phonetic=["enga?"], recognition="solid"),
            # a frame legitimately shares its exemplar chunk's phonetic
            "வந்துட்டேன்": row(phonetic=["vandhutten"], recognition="solid", production="cold"),
            "frame:done-ittu": row(phonetic=["vandhutten"], type="pattern"),
            # shares a phonetic, but is RICHER — a duplicate that must not be
            # dropped just because something else got there first
            "ருசி": row(phonetic=["rusi"]),
            "கை ருசி": row(phonetic=["rusi"], recognition="solid", production="cold", reps=4),
        }
        write_json(lex_path, lex)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ss.cmd_prune_duplicates(_ap.Namespace(apply=False))
        check("a dry run writes nothing", read_json(lex_path) == lex, "the preview mutated the file")
        check("...and says so", "DRY RUN" in out.getvalue())

        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_prune_duplicates(_ap.Namespace(apply=True))
        after = read_json(lex_path)
        check("the dominated duplicate is dropped", "அப்படியா" not in after)
        check("...and the row that carried the state survives", "அப்படியா?!" in after)
        # The regression that matters most. Both must be here.
        check("a punctuation-only HOMOGRAPH pair survives whole — 'our' and "
              "'where?' are not duplicates",
              "எங்க" in after and "எங்க?" in after, f"got {sorted(after)}")
        check("a frame sharing its exemplar's phonetic is never pruned",
              "வந்துட்டேன்" in after and "frame:done-ittu" in after, f"got {sorted(after)}")
        check("the richer of two rows is never the one dropped",
              "கை ருசி" in after and "ருசி" not in after, f"got {sorted(after)}")
        check("nothing else was touched", len(after) == len(lex) - 2, f"got {sorted(after)}")

        with contextlib.redirect_stdout(out := io.StringIO()):
            ss.cmd_prune_duplicates(_ap.Namespace(apply=True))
        check("re-running on clean data is a no-op",
              read_json(lex_path) == after and "no strictly-dominated" in out.getvalue(),
              f"got {out.getvalue()!r}")
    finally:
        lex_path.write_bytes(saved)


def s54_two_eras_not_a_deadline(sb: Path):
    """The trip is a handover, not a terminus (2026-08-04, Andrew: "think of it
    as pre-trip and during-trip eras").

    TRIP_DATE was modelled as a deadline, so `compute_status` counted down past
    zero and `burn_rate`'s `max(days_left, 1)` clamp froze the required pace at
    its final day's value and reported it forever. On 2026-09-01 the scoreboard
    read "-20 days to touchdown · need 8.0 cold/day" — during the month in
    country, which is the era the whole deck exists to serve.

    Gate 7.2 — this failure never looked like nothing happening. It printed a
    confident, well-formed, wrong line every day, and it is the line Anna
    narrates from. So the checks below assert the ABSENCE of the burn ask in
    country, not merely the presence of new wording: a cosmetic relabel that
    left the quota in would pass a presence-only test and still be the bug."""
    print("\n54. The trip is two eras, not a deadline (2026-08-04)")
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    saved, real_today = lex_path.read_bytes(), ss.local_today
    try:
        # A deck with survival items still open, so the countdown branch is live.
        write_json(lex_path, {f"smoke:era{i}": {
            "gloss": "x", "phonetic": [], "type": "chunk", "recognition": "comfortable",
            "production": "cold" if i < 2 else "none", "seen_in": [],
            "last_surfaced": None, "deck": "trip"} for i in range(10)})

        def at(d):
            ss.local_today = lambda: d
            return ss.compute_status()

        before = at(ss.TRIP_DATE - timedelta(days=2))
        check("pre-trip still counts down", "2 days to touchdown" in before, f"got {before}")
        check("...and still names the pace it needs", "need " in before, f"got {before}")

        landing = at(ss.TRIP_DATE)
        check("the day he lands reads as day 1 in country, not zero",
              "in country, day 1" in landing, f"got {landing}")
        check("...and the countdown wording is gone", "touchdown" not in landing, f"got {landing}")
        # THE defect: a quota he cannot act on, stated with confidence. A
        # cosmetic relabel that left the ask in would pass a presence-only test.
        check("...and the required-pace ask is GONE, not merely reworded",
              "need " not in landing, f"got {landing}")
        check("...while the trailing pace survives — that one is still true",
              "trailing" in landing, f"got {landing}")

        deep = at(ss.TRIP_DATE + timedelta(days=20))
        check("three weeks in, the day count still advances",
              "in country, day 21" in deep, f"got {deep}")
        check("...and no negative day ever reaches the scoreboard",
              "day -" not in deep and "-20" not in deep, f"got {deep}")
        check("burn_rate itself refuses a quota past the deadline",
              "need" not in ss.burn_rate(8, 0) and "need" not in ss.burn_rate(8, -5),
              f"got {ss.burn_rate(8, 0)!r} / {ss.burn_rate(8, -5)!r}")
    finally:
        ss.local_today = real_today
        lex_path.write_bytes(saved)


def s55_demotion_survives_the_close(sb: Path):
    """A word that fails under pressure is demoted — and the path had no test.

    Caught 2026-08-04 while splitting sync_state: the state_io extraction dropped
    the DEMOTE table by an off-by-one, leaving `demote_recognition` referencing an
    undefined name. `python -m pyflakes` found it; the full smoke suite did not,
    and reported ALL GREEN on a commit where any close carrying `--stuck-word`
    against a known word would raise NameError and take the whole update down.

    That is the Gate 7.2 failure in its loudest form rather than its quietest: not
    a silent no-op, but a hard crash on a path nothing exercised. Demotion is not
    an edge case — it is the mechanism that keeps the viability floor honest
    ("expect Anna to demote over-counted 'solid' words as they fail under cold
    recall; that is the meter getting honest, not regression", profile.md). A
    floor that can only go up is the thing this whole system refuses to be.

    Round-trips through the real writer and re-reads the file, because the bug
    was in module-level state, not in the function's logic."""
    print("\n55. A demotion survives the close (2026-08-04)")
    import contextlib, io, argparse as _ap
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    learner_path = sb / "progress" / "learner.json"
    slog_path = sb / "progress" / "session_log.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes(), slog_path.read_bytes())
    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[], no_commission="smoke sandbox")
    try:
        write_json(lex_path, {
            "ஸ்மோக்சாலிட்": {"gloss": "was solid", "phonetic": ["solidword"], "type": "chunk",
                              "recognition": "solid", "production": "cold", "seen_in": [],
                              "last_surfaced": None},
            "ஸ்மோக்ஷேக்கி": {"gloss": "already shaky", "phonetic": ["shakyword"], "type": "chunk",
                              "recognition": "struggled", "production": "none", "seen_in": [],
                              "last_surfaced": None}})
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults,
                                           "stuck_word": ["ஸ்மோக்சாலிட்", "ஸ்மோக்ஷேக்கி"]}))
        lex = read_json(lex_path)
        check("a solid word demotes one step, not straight to the floor",
              lex["ஸ்மோக்சாலிட்"]["recognition"] == "comfortable",
              f"got {lex['ஸ்மோக்சாலிட்']['recognition']}")
        check("...and an already-shaky word stays put rather than falling off",
              lex["ஸ்மோக்ஷேக்கி"]["recognition"] == "struggled",
              f"got {lex['ஸ்மோக்ஷேக்கி']['recognition']}")
        check("...and the demotion is recorded in the day's row",
              sorted(read_json(slog_path)[-1]["demoted"]) == ["ஸ்மோக்சாலிட்", "ஸ்மோக்ஷேக்கி"],
              f"got {read_json(slog_path)[-1]}")
        # Production is a separate axis and must not move on a recognition demotion.
        check("...while production is left alone — the two axes are independent",
              lex["ஸ்மோக்சாலிட்"]["production"] == "cold",
              f"got {lex['ஸ்மோக்சாலிட்']['production']}")
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])
        slog_path.write_bytes(saved[2])


def s46_the_commission_gate_blocks_the_close(sb: Path):
    """A live slip pattern with no dose refuses the close (2026-08-01, Andrew).

    NEVER COMMISSIONED was advisory and got walked past for mechanical reasons —
    venum-for-kudunga sat 24 days between first slip and first dose while the
    ticket warned daily, and the 07-31 feedback entry named the escalation
    itself ("the flag needs teeth"). The gate is the wants_scheduled_push law
    applied to the close: Python catches the contradiction and forces the
    re-ask. It runs BEFORE any write, so a refused close is safely re-runnable.

    Gate 7.2 — a gate that never fires looks exactly like a compliant close, so
    the case asserts the REFUSAL (exit code AND, the effect, that nothing was
    written: no cold, no debrief, no slip row), then that each legal door
    opens: the override with a reason, a commission covering the debt in the
    same close, and a landed test discharging its own tag."""
    print("\n46. The commission gate blocks the close (2026-08-01)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    sl = importlib.import_module("slips")
    lex_path = sb / "progress" / "lexicon.json"
    learner_path = sb / "progress" / "learner.json"
    slip_path = sb / "progress" / "slip_log.json"
    slog_path = sb / "progress" / "session_log.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes(),
             slip_path.read_bytes() if slip_path.exists() else None,
             slog_path.read_bytes() if slog_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[], no_commission=None)

    def update(**kw):
        out, code = io.StringIO(), 0
        try:
            with contextlib.redirect_stdout(out):
                ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        except SystemExit as e:
            code = e.code
        return code, out.getvalue()

    try:
        # Clean ledger, then one live uncommissioned pattern.
        slip_path.write_text("[]", encoding="utf-8")
        learner = read_json(learner_path)
        for k in ("slip_closes", "slip_commissions"):
            learner.pop(k, None)
        write_json(learner_path, learner)
        lex = read_json(lex_path)
        lex["கேட்வேர்ட்"] = {"gloss": "gate word", "recognition": "solid",
                            "production": "none", "phonetic": [], "seen_in": []}
        write_json(lex_path, lex)
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "gate-tag", "said": "a", "want": "b"}],
                            lane="chat", when="2026-01-01")
            sl.append_slips([{"tag": "gate-tag", "said": "a", "want": "b"}],
                            lane="chat", when=ss.local_today().isoformat())

        before = (lex_path.read_bytes(), learner_path.read_bytes(),
                  slip_path.read_bytes())
        code, out = update(produced_cold=["கேட்வேர்ட்"], debrief="a close over a debt")
        check("the close is refused, loudly, naming the tag",
              code == 2 and "gate-tag" in out, f"exit {code}")
        check("...and a refused close writes NOTHING — no rep, no cold, no debrief",
              (lex_path.read_bytes(), learner_path.read_bytes(),
               slip_path.read_bytes()) == before, "a partial close leaked")

        # Door 1: the override, reason on the record.
        code, out = update(produced_cold=["கேட்வேர்ட்"], no_commission="trip-eve triage")
        check("the override closes, echoing the reason",
              code == 0 and "trip-eve triage" in out, f"exit {code}")
        check("...and the overridden close actually applied",
              read_json(lex_path)["கேட்வேர்ட்"]["production"] == "cold")

        # Door 2: commission the debt in the same close.
        code, _ = update(soak_payload=["கேட்வேர்ட்"], soak_channel="soak",
                         slip_commissioned=["gate-tag"])
        check("a close that commissions the debt passes the gate", code == 0)
        check("...and the debt is booked",
              "gate-tag" in sl.slip_commissions(), "the gate passed but nothing was booked")

        # The sim path: a slip whose SECOND occurrence arrives in this very
        # close is already a pattern to the gate.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "gate-tag3", "said": "a", "want": "b"}],
                            lane="chat", when="2026-01-03")
        n_rows = len(read_json(slip_path))
        code, out = update(slip=["gate-tag3|x|y|"])
        check("a second occurrence landing IN the close trips the gate",
              code == 2 and "gate-tag3" in out, f"exit {code}")
        check("...and the refused slip row was NOT appended",
              len(read_json(slip_path)) == n_rows, "the gate wrote before refusing")

        # Door 3: a landed test in the same close discharges its own tag.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "gate-tag4", "said": "a", "want": "b"}],
                            lane="chat", when="2026-01-04")
            sl.append_slips([{"tag": "gate-tag4", "said": "a", "want": "b"}],
                            lane="chat", when=ss.local_today().isoformat())
        code, _ = update(slip_tested=["gate-tag4:landed"])
        check("a landed test in the same close discharges its own tag", code == 0)
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])
        if saved[2] is not None:
            slip_path.write_bytes(saved[2])
        if saved[3] is not None:
            slog_path.write_bytes(saved[3])


def s47_hinted_retest_block(sb: Path):
    """Hinted had no follow-up path ("open and unanswered", DECISIONS 07-28;
    built 2026-08-01). `coverage_key` leads with fewest-reps, so a
    repped-but-stale hinted item sorts behind every never-worked item in its
    tier FOREVER — the three FAQ answers sat hinted 22–28 days silent at 11
    days to touchdown. The retest block cuts across the sort on staleness.

    Gate 7.2 — the silent no-op is an empty block reading as "nothing stale",
    so the case asserts presence, ordering, the fresh and ear-only exclusions,
    and that the real ticket entry point prints the block at all.

    EXTENDED 2026-08-04, after the block spent four weeks working for the wrong
    five items. The 08-01 case asserted ordering at `max_n=100` — where nothing
    can fall off — so it never tested the CUT, which is the only place this
    block can fail silently. It still returned five rows and still read as
    success while the deck's three hinted FAQ answers sat below the line behind
    ordinary vocabulary that happened to be staler, and while the top slot went
    to a bootstrap artifact (hinted, zero reps, never surfaced).

    Both new assertions have teeth in that dimension: the deck's items must
    survive a cut that is too small to hold everything, and must do so while
    being FRESHER than the non-deck rows they outrank — a staleness-only sort
    passes every other check in this case and fails these two."""
    print("\n47. Hinted items going dark get a retest block (2026-08-01)")
    import contextlib, io
    st = importlib.import_module("suggest_targets")
    lex_path = sb / "progress" / "lexicon.json"
    deck_path = sb / "curriculum" / "trip_deck.json"
    saved = (lex_path.read_bytes(), deck_path.read_bytes())
    try:
        lex = read_json(lex_path)
        mk_day = lambda d: (date_cls.today() - timedelta(days=d)).isoformat()
        lex["ரீடெஸ்ட்1"] = {"gloss": "stale hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(20), "reps": 5}
        lex["ரீடெஸ்ட்2"] = {"gloss": "staler hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(30), "reps": 2}
        lex["ரீடெஸ்ட்3"] = {"gloss": "fresh hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(3), "reps": 1}
        lex["ரீடெஸ்ட்4"] = {"gloss": "stale but ear-only", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(30),
                           "direction": "catch", "reps": 0}
        # Deck members, deliberately FRESHER than the non-deck rows above: only a
        # tier prefix can float them: staleness alone sinks both.
        lex["ரீடெஸ்ட்5"] = {"gloss": "deck, faq", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(16),
                           "reps": 5, "deck": "trip"}
        lex["ரீடெஸ்ட்6"] = {"gloss": "deck, social", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(15),
                           "reps": 3, "deck": "trip"}
        # The bootstrap artifact: a hinted grade with no work behind it. There is
        # no prior test for a RE-test to repeat, and it is already at the head of
        # the main ticket (coverage_key leads with fewest-reps), so it must not
        # spend a slot here.
        lex["ரீடெஸ்ட்7"] = {"gloss": "hinted, never surfaced", "production": "hinted",
                           "recognition": "struggled", "last_surfaced": None, "reps": 0}
        write_json(lex_path, lex)
        write_json(deck_path, [{"tamil": "ரீடெஸ்ட்5", "register": "faq", "gloss": "x"},
                               {"tamil": "ரீடெஸ்ட்6", "register": "social", "gloss": "x"}])
        rows = st.retest_targets(lex, date_cls.today(), max_n=100)
        words = [r["word"] for r in rows]
        check("a hinted item silent past RETEST_DAYS surfaces", "ரீடெஸ்ட்1" in words)
        check("...most-stale first",
              "ரீடெஸ்ட்2" in words and words.index("ரீடெஸ்ட்2") < words.index("ரீடெஸ்ட்1"))
        check("a recently-worked hinted item does not", "ரீடெஸ்ட்3" not in words)
        check("ear-only items are excluded — a retest is a production move",
              "ரீடெஸ்ட்4" not in words)
        check("a hinted grade with no work behind it is excluded — nothing to re-test",
              "ரீடெஸ்ட்7" not in words, f"got {words}")
        # THE 2026-08-04 defect. A staleness-only sort passes every check above
        # and fails both of these: the deck rows are the two FRESHEST candidates.
        check("the sprint's own items lead, even when non-deck rows are staler",
              words[:2] == ["ரீடெஸ்ட்5", "ரீடெஸ்ட்6"], f"got {words}")
        cut = [r["word"] for r in st.retest_targets(lex, date_cls.today(), max_n=2)]
        check("...and they survive a cut too small to hold everything — the "
              "block's only real failure mode is the line, not the order",
              cut == ["ரீடெஸ்ட்5", "ரீடெஸ்ட்6"], f"got {cut}")

        out, real_argv = io.StringIO(), sys.argv
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = real_argv
        check("the ticket prints the block — the pieces are only worth having "
              "if the entry point calls them", "HINTED, GOING DARK" in out.getvalue())
    finally:
        lex_path.write_bytes(saved[0])
        deck_path.write_bytes(saved[1])


def s56_timezone_is_one_dial(sb: Path):
    """The zone is a field in learner.json, and it SURVIVES the next update
    (2026-08-09).

    `LOCAL_TZ` was already the single definition every clock-facing rule read —
    quiet hours, the rails gate, `local_today`, feed pubDates — but it lived in
    source as `ZoneInfo("America/New_York")`. Fine while he is home; a code edit
    on the road, from an airport, on the day the rails matter most. Andrew asked
    for the dial to move into his profile: one field, changed when he lands.

    The trap this section exists for is NOT the read — that is four lines — it is
    `write_thin_learner`, a whitelist that DELETES any learner key not named in
    it. That exact shape already ate `slip_closes` silently for a week (see s44).
    A wiped zone is worse than a wiped close, because the fallback is a perfectly
    valid zone: everything keeps running, on the wrong clock, and the only
    symptom is a push at 3am in Chennai. So the assertion that earns its keep is
    the round-trip through an update, not the parse."""
    print("\n56. The timezone is one dial in learner.json (2026-08-09)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    si = importlib.import_module("state_io")
    learner_path = sb / "progress" / "learner.json"
    saved = learner_path.read_bytes()

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[],
                    # This section is not testing the commission gate, and by the
                    # time it runs the sandbox carries live uncommissioned slips
                    # from earlier sections — which refuse the close (exit 2).
                    no_commission="smoke: zone round-trip, not a real close")

    try:
        # The trip zone, set the way Andrew will set it: edit the one field.
        learner = read_json(learner_path)
        learner["timezone"] = "Asia/Kolkata"
        write_json(learner_path, learner)

        check("the profile carries the zone", si._resolve_local_tz().key == "Asia/Kolkata",
              f"got {si._resolve_local_tz()}")

        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, "debrief": "landed"}))
        check("...and it SURVIVES the update that follows (write_thin_learner whitelist)",
              read_json(learner_path).get("timezone") == "Asia/Kolkata",
              f"got {read_json(learner_path).get('timezone')!r} — the whitelist ate the zone")

        # Silence is the home zone: a fork, or a clone that never set the field.
        learner = read_json(learner_path)
        del learner["timezone"]
        write_json(learner_path, learner)
        check("a profile with no zone falls back to home",
              si._resolve_local_tz().key == si.DEFAULT_TZ, f"got {si._resolve_local_tz()}")

        # A typo must not take the unattended lanes down with it — the knock cron,
        # the queue and the studio all import this module at start-up.
        learner["timezone"] = "Nowhere/Atlantis"
        write_json(learner_path, learner)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            tz = si._resolve_local_tz()
        check("a bad zone falls back instead of crashing every lane",
              tz.key == si.DEFAULT_TZ, f"got {tz}")
        check("...and says so on stderr", "Nowhere/Atlantis" in err.getvalue(),
              f"silent fallback: {err.getvalue()!r}")
    finally:
        learner_path.write_bytes(saved)


def s48_drill_answer_key_lint(sb: Path):
    """The drill lane had no answer-key validation (2026-08-01): the 08-01 tape
    shipped இடது பக்கம்ல where the oblique பக்கத்துல is right — a wrong case
    form repeated aloud ten times, on the tape commissioned to fix the top
    slip. The lint applies the studio contract: grade every answer against its
    cue, ANY fail stops the run, and a grader that errors or miscounts is
    fail-CLOSED — an unverified sheet must not ship.

    Gate 7.2 — the silent no-op is a lint that always passes (a parse bug reads
    every verdict as PASS), so the case feeds a FAIL and asserts the run STOPS,
    and feeds a miscounted verdict list and asserts the raise."""
    print("\n48. The drill answer key is linted; a fail stops the run (2026-08-01)")
    import contextlib, io
    rd = importlib.import_module("render_drill")
    sheet = {"title": "T", "intro": "i", "outro": "o",
             "items": [{"cue": "ask for tea", "answer_ta": "டீ குடுங்க"},
                       {"cue": "say: next to the temple", "answer_ta": "இடது பக்கம்ல"}]}
    real_ask = rd.ask_json
    try:
        rd.ask_json = lambda *a, **k: {"verdicts": [
            {"n": 1, "verdict": "PASS", "reason": ""},
            {"n": 2, "verdict": "FAIL", "reason": "needs the oblique stem"}]}
        fails = rd.lint_sheet(sheet)
        check("a failing answer is caught, naming the line and the why",
              len(fails) == 1 and "பக்கம்ல" in fails[0] and "oblique" in fails[0],
              f"got {fails}")

        rd.ask_json = lambda *a, **k: {"verdicts": [
            {"n": 1, "verdict": "PASS"}, {"n": 2, "verdict": "PASS"}]}
        check("an all-pass sheet returns no failures", rd.lint_sheet(sheet) == [])

        rd.ask_json = lambda *a, **k: {"verdicts": [{"n": 1, "verdict": "PASS"}]}
        try:
            rd.lint_sheet(sheet)
            miscount = False
        except ValueError:
            miscount = True
        check("a miscounted verdict list fails CLOSED, never open", miscount)

        check("an empty sheet needs no grader call",
              rd.lint_sheet({"items": []}) == [])

        # main() must ACT on the verdict — stub the writer to return the bad
        # sheet and assert the run stops before anything renders.
        real = (rd.write_sheet, rd.drill_brief, rd.deck_due_payload, sys.argv)
        rd.ask_json = lambda *a, **k: {"verdicts": [
            {"n": 1, "verdict": "FAIL", "reason": "wrong case"},
            {"n": 2, "verdict": "PASS", "reason": ""}]}
        try:
            rd.write_sheet = lambda *a, **k: sheet
            rd.drill_brief = lambda: (None, [])
            rd.deck_due_payload = lambda n: [{"word": "X", "gloss": "", "kind": "chunk"}]
            sys.argv = ["render_drill.py", "--dry-run"]
            stopped = False
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    rd.main()
                except SystemExit as e:
                    stopped = bool(e.code)
            check("main() stops on a lint fail — nothing renders", stopped)
        finally:
            rd.write_sheet, rd.drill_brief, rd.deck_due_payload, sys.argv = real
    finally:
        rd.ask_json = real_ask


def s57_longhaul_tape(sb: Path):
    """The fourth audio lane (2026-08-10) — a 40-60 minute press-once tape for the
    flight, where the other three channels' 10-15 minute dose is the wrong shape:
    ~50 press-plays at a median 2.7 min is fifty context switches on a 20-hour leg.

    Gate 7.2, answered out loud. EVERY failure mode of this lane ends with an mp3
    on the feed and a console that says `done`:

      · forty-five minutes of six items looping   → coverage never happened
      · a scene using a word the tape never taught → he loses the thread and stops
      · two identical shapes side by side          → the grating this exists to escape
      · a longhaul_*.mp3 the RSS filter drops      → it never reaches the phone he
        is holding at 35,000 feet, with no way to fetch it
      · a payload the lane ignores                 → the 07-23 re-dispatch loop

    So nothing here asserts that a step RAN. It asserts coverage, the
    taught-before-used ordering, the cadence invariant *including the wrap*, a real
    feed round-trip, and a clock that actually stops the tape."""
    print("\n57. The long-haul tape — coverage, cadence, the clock, and the feed (2026-08-10)")
    rl = importlib.import_module("render_longhaul")

    # ── The cadence law. Two of a kind side by side is the complaint itself, and
    # the WRAP matters as much as the middle: he plays these two or three times
    # through, so the last shape butts against the first on every repeat.
    for spine, cad in rl.CADENCES.items():
        pairs = [(cad[i], cad[(i + 1) % len(cad)]) for i in range(len(cad))]
        clash = [f"{a}->{b}" for a, b in pairs if a == b]
        check(f"cadence '{spine}' never repeats a shape, wrap included", not clash,
              f"adjacent duplicates: {clash}")
        check(f"cadence '{spine}' uses at least three shapes", len(set(cad)) >= 3)
        check(f"cadence '{spine}' has a non-recall shape to teach from",
              any(s not in rl.RECALL_SHAPES for s in cad))
        # Slot 1 cannot be a recall shape: there is nothing yet to recall. The
        # `room` cadence shipped this way and its first plan opened on an empty
        # scene — visible in one --plan-only run, invisible to every assertion
        # the suite had, because an empty movement renders and publishes fine.
        check(f"cadence '{spine}' opens on a shape that teaches",
              cad[0] not in rl.RECALL_SHAPES, f"opens on '{cad[0]}' with nothing taught")
    check("every shape in every cadence has a rhythm and an item count",
          all(s in rl.RHYTHM and s in rl.ITEMS
              for cad in rl.CADENCES.values() for s in cad))

    # ── A pool with a known shape, so coverage is checkable rather than plausible.
    lex = {f"சொல்{i}": {"gloss": f"word {i}", "production": "none",
                        "recognition": "struggled", "deck": "trip", "type": "chunk"}
           for i in range(40)}
    lex["நாள்"] = {"gloss": "day", "production": "cold", "type": "chunk"}
    lex["நாளைக்கு"] = {"gloss": "tomorrow", "production": "cold", "type": "chunk"}
    lex["ரொம்ப நாளாச்சு"] = {"gloss": "long time", "production": "none", "type": "chunk"}
    # PATTERNS, because the machines spine now draws only on what it can run as a
    # machine (2026-08-10). This fixture was all chunks, so that spine's pool came
    # out EMPTY and its movements rendered as bare frame lines — the filter working
    # correctly against a fixture that predated it.
    lex.update({f"frame:இயந்திரம்-{i}": {"gloss": f"machine {i}", "production": "none",
                                         "type": "pattern"} for i in range(16)})
    write_json(sb / "progress" / "lexicon.json", lex)

    for spine in rl.CADENCES:
        pool = rl.build_pool(spine, [])
        count = rl.movements_for(spine, len(pool))
        plan = rl.plan_movements(pool, spine, count)

        # THE POOL IS THE SPINE'S OWN MATERIAL, never padded out to hit a length.
        # Reaching past it is how a 45-minute ask bought 42 rootless "inventory"
        # movements (2026-08-10) — items the shape has nothing to do with.
        unusable = [i["word"] for i in pool if not rl.SPINE_QUALIFIES[spine](i)]
        check(f"[{spine}] every pooled item is one this spine can teach from",
              not unusable, f"cannot be used by {spine}: {unusable[:6]}")

        # COVERAGE — the whole point of a long tape. A 45-minute loop over six
        # items is the silent no-op, and it reads as success from the console.
        heard = {i["word"] for mv in plan for i in mv["items"]}
        missing = [i["word"] for i in pool if i["word"] not in heard]
        check(f"[{spine}] every pooled item is aired at least once ({len(pool)} items)",
              not missing, f"never aired: {missing[:6]}")

        # ...and sized SHORT of the plan on purpose: the render stops on the
        # measured clock, so a tape whose speech ran long drops its last movement.
        # That movement must be a repeat, never a word's only airing.
        short = rl.plan_movements(pool, spine, count - 1)
        heard_short = {i["word"] for mv in short for i in mv["items"]}
        check(f"[{spine}] coverage survives losing the last movement to the clock",
              not [i for i in pool if i["word"] not in heard_short])

        # TAUGHT BEFORE USED — the mechanism behind "I can mostly understand".
        # A scene that reaches for an untaught word is where the thread drops.
        taught, violations = set(), []
        for mv in plan:
            if mv["shape"] in rl.RECALL_SHAPES:
                violations += [i["word"] for i in mv["items"] if i["word"] not in taught]
            else:
                taught |= {i["word"] for i in mv["items"]}
        check(f"[{spine}] no recall movement reaches for an untaught word",
              not violations, f"used before taught: {violations[:6]}")
        # ...and no movement is EMPTY. An empty movement renders as a single Anna
        # line and publishes without complaint — success, with a hole in it.
        check(f"[{spine}] no movement is empty",
              all(mv["items"] for mv in plan),
              f"empty at {[n for n, mv in enumerate(plan, 1) if not mv['items']]}")

        # RECURRENCE — a soak, not a list. Wrapping the cursor is what makes the
        # tape a loop; a plan that never revisits anything is a glossary read aloud.
        longer = rl.plan_movements(pool, spine, count * 2)
        airings = [i["word"] for mv in longer for i in mv["items"]]
        check(f"[{spine}] a longer tape revisits items rather than starving",
              len(airings) > len(set(airings)))

    # ── `--minutes` IS A CEILING, NOT A TARGET (Andrew, 2026-08-10). The first tape
    # planned 15 movements for a 45-minute ask, ran out at 23.8, and warned that it
    # had "come up short" — the plan, not the tape, was wrong. A spine now runs to
    # the length of its material and stops there without apology.
    for spine in rl.CADENCES:
        pool = rl.build_pool(spine, [])
        natural = rl.movements_for(spine, len(pool))
        check(f"[{spine}] every pooled item still fits inside the natural plan",
              rl.pool_size(spine, natural) >= len(pool),
              f"{rl.pool_size(spine, natural)} slots for {len(pool)} items")
        # A bigger ceiling must never invent movements the material cannot fill —
        # the whole point of the 08-10 change. Fixture-independent: whatever this
        # spine's material is, an enormous ceiling returns exactly that much tape.
        check(f"[{spine}] raising the ceiling does not stretch the tape",
              min(natural, rl.movement_count(9999) + 2) == natural, f"natural={natural}")

    # ...and the ceiling must still BIND when the material outruns it, or --minutes
    # means nothing. Asserted on the arithmetic rather than on a spine, because the
    # sandbox lexicon is deliberately small and its natural plans sit under the
    # floor `movement_count` imposes — a fixture fact, not a behaviour.
    for minutes in (8, 20, 45):
        cap = rl.movement_count(minutes) + 2
        check(f"a {minutes}-minute ceiling caps a spine with more material than that",
              min(9999, cap) == cap, f"cap={cap}")
    check("a longer ceiling always allows a longer tape",
          rl.movement_count(8) < rl.movement_count(45) < rl.movement_count(90))
    check("the ceiling is measured in the same minutes the render measures",
          rl.expected_min(rl.movement_count(45)) <= 45 + rl.MOVEMENT_MIN,
          f"{rl.expected_min(rl.movement_count(45)):.1f} min planned for a 45 min ceiling")

    check("the length prediction is anchored to the measured per-movement figure",
          abs(rl.expected_min(15) - (15 * rl.MOVEMENT_MIN + rl.CLOSING_LAP_MIN)) < 1e-9)
    # 3.5 was a guess and was 3x the truth. Guard the calibration itself: a figure
    # this far off is what silently truncated a 45-minute ask to 23.8.
    check("MOVEMENT_MIN is in the range a real movement measured",
          0.8 <= rl.MOVEMENT_MIN <= 2.0, f"got {rl.MOVEMENT_MIN}")

    # ── The commissioned payload LEADS, whatever the ordering turned up. A lane
    # that ignores its payload can never satisfy the order that dispatched it, and
    # re-dispatches forever (M72/M73/M74 in one evening, 2026-07-23).
    pool = rl.build_pool("machines", ["ரொம்ப நாளாச்சு"])
    check("a commissioned payload word leads the pool",
          pool and pool[0]["word"] == "ரொம்ப நாளாச்சு", f"got {pool[0]['word'] if pool else None}")
    # ...INCLUDING one the spine would otherwise refuse. "ரொம்ப நாளாச்சு" is a chunk,
    # not a pattern, so the machines filter drops it — but an order outranks the
    # shape's preference, or the lane silently declines the work it was sent.
    check("the payload is never dropped for being outside the ordering",
          "ரொம்ப நாளாச்சு" in {i["word"] for i in pool})

    # ── The order is only ours when it is addressed to us; and once consumed it
    # must be declared spent, or the session-open drain dispatches a second dose.
    learner = sb / "progress" / "learner.json"
    base = read_json(learner)
    write_json(learner, {**base, "soak_order": {"channel": "soak", "payload": ["x"]}})
    check("an order addressed to another lane is not claimed", rl.longhaul_brief() == (None, []))
    write_json(learner, {**base, "soak_order": {"channel": "longhaul", "payload": ["x"],
                                                "focus": "the -aachu tail"}})
    focus, payload = rl.longhaul_brief()
    check("an order addressed to this lane is read", focus == "the -aachu tail" and payload == ["x"])
    sync = importlib.import_module("sync_state")
    check("this lane can declare its order spent", sync.mark_soak_delivered("longhaul") is True)
    check("...and the declaration round-trips to disk",
          (read_json(learner).get("soak_order") or {}).get("delivered", {}).get("channel") == "longhaul")

    # ── Inventory candidates are PROPOSED by substring and must be marked as
    # unsafe: the same technique logged நீ at 17 reps because it sits inside
    # நீங்க (probe_hit, 2026-07-26). The sheet-writer is the one that disposes.
    # The match is on the PULLI-STRIPPED stem. A citation form ends in ் (நாள்);
    # inside a longer word that consonant takes another vowel sign instead
    # (நாளைக்கு, ரொம்ப நாளாச்சு), so plain substring matching finds NEITHER of the
    # two phrases the 08-09 session was actually about. Measured: 1 host of 3.
    hosts = rl.inventory_hosts(lex)
    found = set(hosts.get("நாள்") or [])
    check("the inventory root reaches its hosts across the vowel change",
          {"நாளைக்கு", "ரொம்ப நாளாச்சு"} <= found,
          f"got {found} — a bare substring test misses exactly the finding's examples")
    check("the mandate tells the writer to drop coincidental hosts",
          "coincidence" in rl.SHAPE_CLAUSES["inventory"].lower())
    check("no mandate ever asks the listener for anything",
          "never ask him" in rl.BASE_MANDATE.lower())
    # Constitution rule 6 — no meta-narration. This lane is the one most likely to
    # break it: the mandate TELLS the writer he is on a plane, which is exactly the
    # kind of context that leaks into a spoken line ("rest your eyes", "we're
    # halfway"). An earlier draft of the outro said "sleep if you can".
    check("the mandate forbids narrating where he is or what he is doing",
          "meta-narration" in rl.BASE_MANDATE.lower(),
          "the model is told he is on a flight; without the ban that lands in the audio")
    fixed = inspect.getsource(rl.render)
    spoken_asides = re.findall(r'tape\.add\("([^"]+)"', fixed)
    banned = re.compile(r"\b(sleep|walk|tired|rest|eyes|flight|plane|seat|halfway)\b", re.I)
    check("...and the lane's own hard-coded lines obey it too",
          not [s for s in spoken_asides if banned.search(s)],
          f"meta-narrating asides: {[s for s in spoken_asides if banned.search(s)]}")

    # ── THE CLOCK GOVERNS. `--minutes` is the dial he sets; if the render ignores
    # it he gets a 20-minute file he has to re-press mid-flight. Stub the TTS with
    # real silence frames so the frame scan measures an honest stream, no network.
    real = (rl.generate_segment_google, rl.get_raw_mp3_frames)
    sheet = {"frame": "the -aachu tail", "beats": [
        {"ta": f"வாக்கியம் {n}", "en": f"line {n}", "who": "a"} for n in range(5)]}

    async def fake_tts(text, voice, index, tmp):
        p = os.path.join(tmp, f"{index}.mp3")
        open(p, "wb").close()
        return p
    try:
        rl.generate_segment_google = fake_tts
        rl.get_raw_mp3_frames = lambda f: rl.SILENCE_FRAME * 60   # ~1.4s of "speech"
        plan = rl.plan_movements(rl.build_pool("machines", []), "machines", 40)
        out = sb / "clock.mp3"
        short_min, short_played, _, short_sheets = asyncio.run(
            rl.render(plan, "machines", out, 1.0, writer=lambda mv, s: sheet))
        long_min, long_played, spoken, sheets = asyncio.run(
            rl.render(plan, "machines", out, 4.0, writer=lambda mv, s: sheet))
        check("the tape reaches the minutes it was asked for",
              short_min >= 1.0 and long_min >= 4.0, f"got {short_min:.2f} / {long_min:.2f}")
        check("...and STOPS there rather than rendering the whole plan",
              short_played < len(plan), f"played {short_played}/{len(plan)}")
        check("a longer target renders strictly more of the plan",
              long_played > short_played, f"{long_played} vs {short_played}")
        check("the clock is measured from the file, not estimated from bytes",
              "audio_duration" in inspect.getsource(rl.Tape.minutes))
        check("only lines that actually played are claimed as delivered",
              spoken and all(isinstance(s, str) for s in spoken))

        # ── THE WRITTEN STORY. Three tapes shipped as audio only (2026-08-10): the
        # sheets were handed to the renderer and dropped, so the source text sent to
        # the TTS existed nowhere — not on disk, not in a log. Unrecoverable.
        check("the sheets that played come back out of the render",
              len(sheets) == long_played, f"{len(sheets)} sheets for {long_played} played")
        check("...and a tape cut short by the clock returns only what it aired",
              len(short_sheets) == short_played < len(sheets))
        real_scripts = rl.SCRIPTS_DIR
        rl.SCRIPTS_DIR = sb / "content" / "scripts"
        try:
            written = rl.write_script(sb / "longhaul_machines_2026-08-11_0930.mp3",
                                      "machines", long_min, sheets, spoken)
            body = written.read_text(encoding="utf-8")
        finally:
            rl.SCRIPTS_DIR = real_scripts
        check("the script is saved beside the audio, named for it",
              written.name == "longhaul_machines_2026-08-11_0930.md", written.name)
        check("...and carries the Tamil actually sent to the TTS",
              all(b["ta"] in body for b in sheet["beats"]), body[:160])
        check("...the measured length and the audio it belongs to",
              f"{long_min:.1f} min" in body and ".mp3" in body)
        check("...one section per movement that played",
              body.count("\n## ") == long_played + (1 if spoken else 0),
              f"{body.count(chr(10) + '## ')} sections for {long_played} movements")
        check("...and the closing lap, which is a third of the audio",
              "closing lap" in body and all(l in body for l in spoken))
        # The script rides the SAME commit as the mp3, or the pair drifts apart.
        pub = inspect.getsource(rl.main)
        check("the script is committed with the tape, not left behind",
              "commit_and_push([mp3, script" in pub)

        # ── THE DELIVERY SEAM, at the level each item actually exists at. The
        # machines tape taught 26 frames and stamped 0 (2026-08-10): a frame is a
        # label for a pattern realised across beats, so it is in the audio exactly
        # never, and substring-matching the spoken lines could only ever return
        # nothing. The ledger booked a 28-minute tape as having delivered zero.
        frame_mv = {"shape": "machine", "items": [{"word": "frame:quote-nu"},
                                                  {"word": "வந்துட்டேன்"}]}
        pool_x = [{"word": "frame:quote-nu"}, {"word": "வந்துட்டேன்"},
                  {"word": "frame:never-aired"}, {"word": "சொல்லல"}]
        got = rl.audible(pool_x, ["வந்துட்டேன் இப்போ"],
                         [(frame_mv, {"beats": [{"ta": "நான் வந்துட்டேனு சொன்னாங்க"}]})])
        check("a frame is claimed when its movement played and made beats",
              "frame:quote-nu" in got, str(got))
        check("...a chunk still has to be literally spoken", "வந்துட்டேன்" in got)
        check("...a frame from a movement that never played is NOT claimed",
              "frame:never-aired" not in got, str(got))
        check("...and an unspoken chunk is not claimed either", "சொல்லல" not in got)
        check("a movement that produced no beats claims nothing",
              rl.audible([{"word": "frame:quote-nu"}], [], [(frame_mv, {"beats": []})]) == [])
        check("the publish path claims through audible(), not a bare substring",
              "audible(pool, spoken, sheets)" in pub and "in blob]" not in pub)
        check("...and written before the publish gate, so --no-publish keeps it",
              pub.index("write_script(") < pub.index("if args.no_publish"))
    finally:
        rl.generate_segment_google, rl.get_raw_mp3_frames = real

    # ── THE FEED ROUND-TRIP. Three separate places drop an unknown prefix: the
    # filter, the sort key, and the title. Each fails silently and differently —
    # missing, buried at (0,0) below every episode, or titled as a raw filename.
    rr = importlib.import_module("rebuild_rss")
    name = "longhaul_inventory_2026-08-11_0930.mp3"
    title = rr.clean_title(name.replace(".mp3", ""), name)
    check("a long-haul tape gets a real title", title.startswith("Long-haul — inventory"),
          f"got {title!r}")
    check("the title says which spine, for a one-handed lock-screen choice",
          "inventory" in title and "2026-08-11" in title, f"got {title!r}")
    check("the title carries no raw filename", ".mp3" not in title and "_" not in title)
    # The title shipped "press once, 45 min" on a MEASURED 00:23:45 tape (2026-08-10).
    # A title is prose, but a duration inside it is still a duration, and the only
    # length a listener may be shown is the one that was measured off the file.
    check("the title states no length — itunes:duration is the measured authority",
          not re.search(r"\d+\s*(min|minute|hour|hr)", title, re.I), f"got {title!r}")

    audio = sb / "published_audio"
    audio.mkdir(exist_ok=True)
    (audio / name).write_bytes(rl.SILENCE_FRAME * 400)   # real frames, real duration
    cwd = os.getcwd()
    try:
        os.chdir(sb)
        rr.generate_rss()
        feed = (sb / "rss.xml").read_text(encoding="utf-8")
    finally:
        os.chdir(cwd)
    check("the tape actually lands in the feed he downloads before boarding",
          name in feed, "rendered, committed, and invisible — the worst failure "
                        "this lane has, because he cannot fetch it from the air")
    check("...under its real title, not its filename", "Long-haul — inventory" in feed)
    sort_src = inspect.getsource(rr.generate_rss)
    check("the sort key knows the longhaul prefix", "longhaul" in sort_src,
          "an unmatched prefix still SORTS — at (0,0), silently below every episode")

    # ── Duration honesty (same diff): `except: return 3.0` stamped every episode
    # on an ffprobe-less host as exactly 3.0 min. M78-M85 all carry it; their real
    # lengths are 1.7-3.5. He judges an episode partly by the number his player
    # shows him (2026-07-23), and a 45-minute tape registered as 3.0 is worse.
    # Read the AST, not the text: the first cut of this case grepped for the old
    # line and failed against the DOCSTRING that quotes it. A source-text assertion
    # tests the prose; this one tests the code.
    ra = ast.parse((REAL_BASE / "scripts" / "render_audio.py").read_text(encoding="utf-8"))
    fn = next((n for n in ast.walk(ra)
               if isinstance(n, ast.FunctionDef) and n.name == "get_duration"), None)
    check("render_audio still measures episode duration", fn is not None)
    returns = [ast.unparse(r.value) for r in ast.walk(fn) if isinstance(r, ast.Return) and r.value]
    check("no episode is stamped with a plausible fiction",
          "3.0" not in returns,
          f"returns {returns} — a fabricated 3.0 is invisible precisely BECAUSE it is "
          f"plausible; M78-M85 all carry it against real lengths of 1.7-3.5")
    check("...and it measures with the authority rebuild_rss already uses",
          any("audio_duration" in r for r in returns), f"returns {returns}")
    check("an unmeasurable file reports a visible zero, never a guess", "0.0" in returns)


def s43_sidecar_callback_never_drops_silently(sb: Path):
    """An unregisterable sidecar word is reported, never swallowed (2026-07-31).

    M78's sidecar filed இருந்துச்சு under `callbacks_used`, but the word had never
    entered the lexicon — Anna had recast it in chat three times and never
    registered it. Only `new_words_landed` may CREATE a record, so the branch fell
    through in total silence: the episode shipped with three real exposures of the
    one word Andrew had been asking for since 07-25, and the ledger held no trace
    of it. Unschedulable, uncollectable, invisible to suggest_targets — and
    indistinguishable from success in the log.

    Creating it here would be the wrong fix: a callback CLAIMS the word already
    exists, so an unresolvable one is far more likely a variant of a real record,
    and inventing a duplicate poisons the axes. The frame branch above had the
    right answer all along — report and skip. Silence is the only thing ruled out.

    Also covers the standalone renderer's .env gap found the same hour: a render
    inside run_studio always had credentials because IT loaded .env, while the
    same command run by hand reported 'this host cannot produce audio'."""
    print("\n43. A sidecar callback that resolves to nothing is loud (2026-07-31)")
    import contextlib, io, inspect
    ra = importlib.import_module("render_audio")

    script = sb / "content" / "scripts" / "tier2_mission97.md"
    script.parent.mkdir(parents=True, exist_ok=True)
    # A word the lexicon cannot possibly hold — இருந்துச்சு itself was registered
    # the day this case was written, and a fixture that drifts into existence
    # turns a regression test green for the wrong reason.
    ghost = "ஸ்மோக்பூதம்"
    script.write_text(f"# Tier 2, Mission 97 — Smoke\n\n**Anna:** {ghost}.\n",
                      encoding="utf-8")
    (script.with_suffix(".tags.json")).write_text(json.dumps({
        "callbacks_used": {ghost: 3},      # never registered — the bug
        "new_words_landed": {},
    }, ensure_ascii=False), encoding="utf-8")

    lex_path = sb / "progress" / "lexicon.json"
    saved_lex = lex_path.read_bytes()
    # No mp3 is written: register_mission_in_state's nested get_duration swallows
    # a missing file and returns its 3.0 default, so duration is not under test here.
    #
    # The day-zero fixture is an EMPTY lexicon, and the exposure block is guarded
    # by a bare `if lexicon:` — so on the fixture as shipped this whole code path
    # is skipped and every assertion below would pass vacuously. Seed one row.
    # (Worth knowing on its own: a genuinely blank day-zero clone registers no
    # words from its first episode at all. Left alone here — day-zero behaviour
    # is BOOTSTRAP's question, not this case's.)
    try:
        lex = read_json(lex_path)
        lex["ஸ்மோக்ஆங்கர்"] = {"gloss": "anchor", "phonetic": [], "recognition": "solid",
                               "production": "none", "seen_in": []}
        write_json(lex_path, lex)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ra.register_mission_in_state(script, sb / "published_audio" / "tier2_mission97.mp3")
        text = out.getvalue()
        lex = read_json(lex_path)

        check("an unresolvable callback is NOT invented as a lexicon record",
              ghost not in lex, "a duplicate record was created")
        check("...and the drop is reported, not silent",
              "resolve to no lexicon word" in text, f"got {text[:300]!r}")
        check("...naming the word so the operator can re-file it",
              ghost in text, f"got {text[:300]!r}")
        check("...and saying what to do about it",
              "new_words_landed" in text, f"got {text[:300]!r}")

        # The control: filed correctly, it registers and stops warning.
        (script.with_suffix(".tags.json")).write_text(json.dumps({
            "callbacks_used": {},
            "new_words_landed": {ghost: 3},
        }, ensure_ascii=False), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ra.register_mission_in_state(script, sb / "published_audio" / "tier2_mission97.mp3")
        lex = read_json(lex_path)
        check("the same word filed as NEW does enter the lexicon",
              ghost in lex, "still absent")
        check("...and nothing is reported unresolved",
              "resolve to no lexicon word" not in out.getvalue())

        # Found by this very case on its first run: the state paths were
        # CWD-relative, so importing the sandbox module without chdir'ing wrote
        # a fake mission into the REAL progress/ files. Assert the containment,
        # not just the behaviour — a test that mutates live state is worse than none.
        real_lex = read_json(REAL_BASE / "progress" / "lexicon.json")
        real_eps = read_json(REAL_BASE / "progress" / "episodes.json")
        check("the render's state writes stay inside the sandbox",
              ghost not in real_lex, "the smoke run wrote into the real lexicon")
        check("...including the episode registry",
              "97" not in real_eps, "the smoke run wrote into the real episodes.json")
    finally:
        lex_path.write_bytes(saved_lex)

    src = inspect.getsource(ra.main)
    check("the standalone renderer loads .env, like run_studio does before it",
          "load_env" in src, "a hand-run render still cannot find GCP_SA_KEY")


def s45_concurrent_appends_merge(mk, sb: Path):
    """Two writers appending to one state array must BOTH survive (2026-07-31).

    The 20:56 Anna tick died on `git pull --rebase` with a conflict in
    push_queue.json: Anna had queued a 20:30 collect while another lane pushed a
    queue entry during the LLM step. `check=True` raised, the whole tick's work
    was lost — decision, log row and queued dose — and CI went red. The two
    appends never disagreed; git only saw adjacent edits to one JSON array.

    TEETH IN THE DIRECTION THAT FAILS SILENTLY (Gate 7.2): the dangerous outcome
    is not a crash, it is resolving the conflict the WRONG WAY and dropping the
    other writer's row — during a rebase, stage :2 is upstream and :3 is ours, so
    a plausible-looking implementation loses exactly one entry and looks fine. So
    these assert the EFFECT on the pushed file, per writer, not that it ran.
    """
    print("\n45. Concurrent appends to one state array (both writers survive)")
    import subprocess as sp
    # A FRESH module object, not the shared `mk`: earlier cases replace
    # mk.commit_and_push with a Recorder stub, and the first draft of this case
    # spent a run testing that stub. It "passed" the survives-a-conflict check
    # because a no-op never raises. Gate 7.2 in miniature — the execution
    # assertion was green on a dead function; only the effect assertion caught it.
    spec = importlib.util.spec_from_file_location("mk_live", mk.__file__)
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)
    check("the case holds the REAL writer, not a stub",
          not isinstance(live.commit_and_push, Recorder)
          and callable(getattr(live, "_union_conflict", None)))
    root = sb / "gitlab"
    root.mkdir(exist_ok=True)
    origin, runner, other = root / "origin.git", root / "runner", root / "other"

    def git(cwd, *a, **kw):
        return sp.run(["git", *a], cwd=cwd, capture_output=True, text=True, **kw)

    sp.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    sp.run(["git", "clone", "-q", str(origin), str(runner)], check=True)
    for c in (runner,):
        git(c, "config", "user.email", "a@b.c"); git(c, "config", "user.name", "t")
    (runner / "progress").mkdir()
    qp = runner / "progress" / "push_queue.json"
    qp.write_text("[]", encoding="utf-8")
    git(runner, "add", "-A"); git(runner, "commit", "-qm", "base")
    git(runner, "push", "-q", "origin", "HEAD:main")
    sp.run(["git", "clone", "-q", str(origin), str(other)], check=True)
    git(other, "config", "user.email", "a@b.c"); git(other, "config", "user.name", "t")

    # THE OTHER WRITER lands first (a laptop session, or a second lane).
    theirs = {"id": "qTHEIRS", "due": "2026-07-31T22:00:00+00:00", "body": "theirs"}
    (other / "progress" / "push_queue.json").write_text(
        json.dumps([theirs], ensure_ascii=False, indent=2), encoding="utf-8")
    git(other, "add", "-A"); git(other, "commit", "-qm", "other writer")
    git(other, "push", "-q", "origin", "HEAD:main")

    # THE RUNNER, still on the stale base, appends its own and commits+pushes.
    mine = {"id": "qMINE", "due": "2026-07-31T21:00:00+00:00", "body": "mine"}
    qp.write_text(json.dumps([mine], ensure_ascii=False, indent=2), encoding="utf-8")
    live.BASE = runner
    try:
        live.commit_and_push([qp], "Anna: silence")
        crashed = ""
    except Exception as e:
        crashed = f"{type(e).__name__}: {e}"

    check("the tick survives a concurrent append", not crashed, crashed)
    pushed = json.loads(git(origin, "show", "main:progress/push_queue.json").stdout or "[]")
    ids = [e.get("id") for e in pushed]
    check("OUR entry reached main", "qMINE" in ids, str(ids))
    check("...and the OTHER writer's entry was not dropped (rebase :2/:3 inversion)",
          "qTHEIRS" in ids, str(ids))
    check("no row is duplicated", len(ids) == len(set(ids)), str(ids))
    check("the queue stays ordered by due", ids == sorted(ids, key=lambda i:
          {"qMINE": "21", "qTHEIRS": "22"}[i]), str(ids))
    check("nothing is left mid-rebase", not (runner / ".git" / "rebase-merge").exists()
          and not (runner / ".git" / "rebase-apply").exists())

    # A conflict OUTSIDE the unionable set must still be loud, not merged.
    check("only true append-arrays are auto-resolvable",
          set(live.UNIONABLE) == {"progress/push_queue.json", "progress/knock_log.json"},
          f"{sorted(live.UNIONABLE)} — session_log merges same-day rows by rule and "
          "feedback_log has no key; a conflict in either is a real disagreement")


def s52_andrew_is_family_already(sb: Path):
    """The standing fact reaches every role that can invent a first meeting
    (2026-08-04, Andrew).

    M81 opened at the iron gate with sisters-in-law he "recognised from the old
    photos." He has met them a dozen times over ten years. No protocol file
    said so, so each generator filled the blank with the newcomer-integrating
    story — and it read as a stranger's arrival to the one person it is about.

    The silent no-op: if this prose is dropped in a later edit, nothing breaks,
    nothing warns, and the episodes quietly go back to writing him as a guest.
    So the fact is asserted where each role actually reads. The three surfaces
    are not redundant — they are three separate readers: Anna and every Python
    dose inline `persona.md` and never see the constitution; the Architect reads
    the constitution; the Director read NEITHER, which is why the brief invented
    "the expected chaotic joy of a first meeting."
    """
    print("\n52. Andrew is ten years into this family, not arriving (2026-08-04)")
    # Flattened: the prose is hard-wrapped, so a phrase can straddle a newline.
    canon = " ".join((sb / "protocol" / "constitution.md")
                     .read_text(encoding="utf-8").split())
    check("the constitution owns the standing fact",
          "Family Already, Language Not Yet" in canon and "ten years" in canon)
    check("...and forbids the first-meeting framing outright",
          "not a first meeting" in canon and "stranger arriving" in canon)

    # persona.md is the ONLY protocol file morning_knock / knock_reply /
    # render_drill / render_soak inline, so a pointer here would reach nothing.
    persona = (sb / "protocol" / "persona.md").read_text(encoding="utf-8")
    check("persona.md states it in full, not as a cross-reference",
          "not new to this family" in persona and "auditioning for entry" in persona,
          "the doses inline persona.md alone — a pointer to the constitution is a "
          "dangling reference at knock time")
    check("...and the Heist no longer says he is earning his PLACE",
          "earning his place at the table" not in persona,
          "the place is his; the respect for the language is what's earned")

    # The Director writes Scenario Context — the field the first-meeting framing
    # was actually invented in — and its Reads-from list is its whole context.
    director = (sb / "protocol" / "studio" / "director.md").read_text(encoding="utf-8")
    head = director.split("**Goal:**")[0]
    check("the Director's Reads-from now includes the constitution",
          "constitution.md" in head,
          "Scenario Context invents the framing; without this line the Director "
          "reads only profile.md + learner.json and cannot know")


def s51_derived_files_are_rerendered_not_merged(mk, sb: Path):
    """A conflict in a DERIVED file must never sink the rebase (2026-08-04).

    The live failure: run 30865736387. Two replies 31s apart, judged fine, and
    the second lost its whole exchange to `RuntimeError: rebase onto origin/main
    needs a human`. Two files conflicted — knock_log.json, which union-resolves,
    and chat.md, which did not, so `any(f not in UNIONABLE)` refused BOTH. But
    chat.md holds no state at all: render_chat builds it from knock_log.json.
    There was nothing to reconcile and nothing to lose; the file that blocked the
    landing could have been regenerated from the file that landed cleanly.

    TEETH IN THE DIRECTION THAT FAILS SILENTLY: the dangerous outcome is not the
    crash, it is a "resolution" that git-adds a chat.md still carrying <<<<<<<
    markers, or one rendered from the pre-merge log — both look green and both
    corrupt the record Andrew reads. So this asserts the CONTENT pushed to main
    matches a fresh render of the MERGED log, not that the rebase exited 0.
    """
    print("\n51. Derived files re-render through a conflict (chat.md)")
    import subprocess as sp
    # The REAL modules, not the shared/stubbed ones — same reason as case 45.
    spec = importlib.util.spec_from_file_location("mk_live2", mk.__file__)
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)
    rc_spec = importlib.util.spec_from_file_location(
        "rc_live", str(Path(mk.__file__).parent / "render_chat.py"))
    rc = importlib.util.module_from_spec(rc_spec)
    rc_spec.loader.exec_module(rc)
    check("the case holds the REAL renderer, not a stub",
          callable(getattr(rc, "render_chat", None))
          and "progress/chat.md" in live.DERIVED)

    root = sb / "gitlab_derived"
    root.mkdir(exist_ok=True)
    origin, runner, other = root / "origin.git", root / "runner", root / "other"

    def git(cwd, *a):
        return sp.run(["git", *a], cwd=cwd, capture_output=True, text=True)

    def knock(ts, body):
        return {"timestamp": ts, "date": ts[:10], "acted": True, "body": body,
                "modality": "text", "move": "melt"}

    def write(clone, entries):
        (clone / "progress" / "knock_log.json").write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        rc.KNOCK_LOG_PATH = clone / "progress" / "knock_log.json"
        rc.CHAT_PATH = clone / "progress" / "chat.md"
        rc.render_chat()

    sp.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    sp.run(["git", "clone", "-q", str(origin), str(runner)], check=True)
    git(runner, "config", "user.email", "a@b.c"); git(runner, "config", "user.name", "t")
    (runner / "progress").mkdir()
    base = [knock("2026-08-04T00:02:48+00:00", "the melt line, one more time")]
    write(runner, base)
    git(runner, "add", "-A"); git(runner, "commit", "-qm", "base")
    git(runner, "push", "-q", "origin", "HEAD:main")
    sp.run(["git", "clone", "-q", str(origin), str(other)], check=True)
    git(other, "config", "user.email", "a@b.c"); git(other, "config", "user.name", "t")

    # THE OTHER LANE lands first — a reply to the OTHER open thread.
    theirs = knock("2026-08-04T00:29:41+00:00", "theirs: the volley reply")
    write(other, base + [theirs])
    git(other, "add", "-A"); git(other, "commit", "-qm", "other writer")
    git(other, "push", "-q", "origin", "HEAD:main")

    # THE RUNNER, on the stale checkout, appends its own and lands it.
    mine = knock("2026-08-04T00:29:12+00:00", "mine: the scenario reply")
    write(runner, base + [mine])
    live.BASE = runner
    live.DERIVED = {"progress/chat.md": rc.render_chat}
    rc.KNOCK_LOG_PATH = runner / "progress" / "knock_log.json"
    rc.CHAT_PATH = runner / "progress" / "chat.md"
    try:
        live.commit_and_push([runner / "progress" / "knock_log.json",
                              runner / "progress" / "chat.md"], "Knock reply: chat")
        crashed = ""
    except Exception as e:
        crashed = f"{type(e).__name__}: {e}"

    check("the reply survives a chat.md + knock_log.json conflict", not crashed, crashed)
    pushed = json.loads(git(origin, "show", "main:progress/knock_log.json").stdout or "[]")
    stamps = [e.get("timestamp") for e in pushed]
    check("OUR exchange reached main", mine["timestamp"] in stamps, str(stamps))
    check("...and the OTHER lane's was not dropped", theirs["timestamp"] in stamps, str(stamps))

    chat = git(origin, "show", "main:progress/chat.md").stdout
    check("chat.md carries NO conflict markers",
          "<<<<<<<" not in chat and ">>>>>>>" not in chat and "=======" not in chat)
    # The claim that matters: it is a render of the MERGED log, not of either side.
    rc.KNOCK_LOG_PATH = runner / "progress" / "knock_log.json"
    rc.CHAT_PATH = runner / "progress" / "chat_expected.md"
    (runner / "progress" / "knock_log.json").write_text(
        json.dumps(pushed, ensure_ascii=False, indent=2), encoding="utf-8")
    rc.render_chat()
    check("chat.md on main == a fresh render of the merged log",
          chat == (runner / "progress" / "chat_expected.md").read_text(encoding="utf-8"))
    check("both bodies are actually in it",
          "mine: the scenario reply" in chat and "theirs: the volley reply" in chat)
    check("nothing is left mid-rebase", not (runner / ".git" / "rebase-merge").exists()
          and not (runner / ".git" / "rebase-apply").exists())

    # A renderer pointed anywhere but BASE must REFUSE, not git-add the markers.
    rc.CHAT_PATH = runner / "progress" / "elsewhere.md"
    check("a renderer that writes outside BASE is refused, not trusted",
          not live._rerender_derived("progress/chat.md"))


def s49_thread_continuity(mk, kr, sb: Path):
    """The reply thread must carry what Anna DID, across knocks (2026-08-02).

    The live failure: Andrew asked from his phone for an audio greeting for a
    third party. Turn 2 composed it, rendered it, and pushed it — but the
    exchange record stored only `reply` and `reply_line`, so turn 3 could not
    see the artefact existed. It read "he's an anglophone who doesn't know any
    Tamil" against a two-field transcript, resolved "he" to Andrew, and
    lectured him about his own name; turn 4 then called a delivered file "still
    pending". The window was also `knock["exchanges"][-4:]` — one knock — so a
    reply to the NEXT knock started from nothing at all.

    Gate: the write records the action, the read carries it across knocks, and
    the wider window never touches cold-fire accounting.
    """
    print("\n49. Reply thread carries actions, across knocks (2026-08-02)")
    prog = sb / "progress"
    klog_path = prog / "knock_log.json"
    lex_path = prog / "lexicon.json"
    saved_lex, saved_log = lex_path.read_bytes(), klog_path.read_bytes()
    try:
        now = datetime.now(timezone.utc)
        stamp = lambda mins: (now - timedelta(minutes=mins)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # An OLDER knock, still inside the window, with a turn of its own; and a
        # third knock old enough to have fallen out of it entirely.
        stale = {"date": (now - timedelta(days=3)).date().isoformat(),
                 "timestamp": (now - timedelta(days=3)).isoformat(),
                 "acted": True, "modality": "text", "move": "ancient history",
                 "body": "long gone",
                 "exchanges": [{"at": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "reply": "FORGOTTEN", "reply_line": "old news"}]}
        earlier = {"date": now.date().isoformat(),
                   "timestamp": (now - timedelta(minutes=90)).isoformat(),
                   "acted": True, "modality": "text", "move": "lore: feeding as greeting",
                   "body": "saapitteenga?",
                   "exchanges": [{"at": stamp(80), "reply": "I need this phonetic in text",
                                  "reply_line": "fair — saapitteenga?"}]}
        current = {"date": now.date().isoformat(), "timestamp": now.isoformat(),
                   "acted": True, "modality": "text", "move": "smoke continuity",
                   "body": "anything", "expected_target": "", "target_revealed": False}
        write_json(klog_path, [stale, earlier, current])

        # --- the window itself (pure function, no LLM) ---
        klog = read_json(klog_path)
        win = kr.recent_exchanges(klog, klog[-1])
        said = [r["andrew_said"] for r in win]
        check("a turn from an EARLIER knock is in the thread",
              "I need this phonetic in text" in said, str(said))
        check("...tagged as belonging to another thread",
              any(r.get("earlier_thread") for r in win if
                  r["andrew_said"] == "I need this phonetic in text"))
        check("a turn older than the window is dropped", "FORGOTTEN" not in said, str(said))
        check("the field is anna_said, not anna_recast — a logistics turn is "
              "not a Tamil correction", all("anna_recast" not in r for r in win)
              and all("anna_said" in r for r in win))

        # --- the write: a voice reply must leave a trace on its own exchange ---
        kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
        kr.refresh_feed = lambda: None
        real_render = kr.render_memo

        async def fake_render(script, out_path, voice):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"ID3fake")

        kr.render_memo = fake_render
        try:
            v = canned_verdict([], reply_line="On it — check audio shortly.")
            v["voice_reply"] = "வணக்கம் Doodah"
            kr.judge = lambda k, r, t, h=None, rr=None, **kw: v
            sys.argv = ["knock_reply.py", "an audio greeting for Doodah please"]
            kr.main()
        finally:
            kr.render_memo = real_render

        entry = read_json(klog_path)[-1]
        ex = entry["exchanges"][-1]
        check("the exchange records that Anna SPOKE, and what he said",
              ex.get("spoke") == "வணக்கம் Doodah", str(ex.get("spoke")))
        check("...and the URL of what was delivered",
              (ex.get("audio_url") or "").endswith(".mp3"), str(ex.get("audio_url")))

        # --- the read: the NEXT turn must know the artefact exists ---
        klog = read_json(klog_path)
        win = kr.recent_exchanges(klog, klog[-1])
        sent = [r for r in win if r.get("anna_sent_audio")]
        check("the next turn sees the audio already went out",
              len(sent) == 1 and sent[0]["anna_sent_audio"] == "வணக்கம் Doodah", str(win))
        check("a turn with no artefact carries no claim of one",
              all("anna_sent_audio" not in r for r in win
                  if r["andrew_said"] == "I need this phonetic in text"))

        # The mandate has to tell the model what the fields MEAN, or they are
        # just unexplained keys in a JSON blob.
        check("the mandate reads absence as fact, not as silence",
              "anna_sent_audio" in kr.THREAD_MANDATE and "anna_queued_push" in kr.THREAD_MANDATE)
        check("...and scopes the 3-hour decay to the SCENE, not the record",
              "THE SCENE DECAYS; THE RECORD NEVER DOES" in kr.THREAD_MANDATE)
        # Both judges must be handed it: the catch lane hit this same bug on
        # 2026-07-25 and a rule only one judge reads is half a rule.
        src = (REAL_BASE / "scripts" / "knock_reply.py").read_text(encoding="utf-8")
        check("both judges are handed the thread mandate",
              src.count('+ "\\n" + THREAD_MANDATE') == 2,
              f"{src.count(chr(43) + chr(32) + 'THREAD_MANDATE')} assembly sites")

        # The load-bearing safety property: this window is continuity ONLY.
        # No grading field may ride into the judge's view of history, or the
        # thread could start minting or denying colds — that evidence belongs
        # to revealed_recently()/shown_in_knock(), which are Python-owned.
        allowed = {"andrew_said", "anna_said", "earlier_thread",
                   "anna_sent_audio", "anna_queued_push"}
        leaked = {k for r in win for k in r} - allowed
        check("no grading field leaks into the thread — continuity can never "
              "mint or deny a cold", not leaked, f"leaked {leaked}")
    finally:
        lex_path.write_bytes(saved_lex)
        klog_path.write_bytes(saved_log)


def s50_read_surfaces_are_phonetic(mk, kr, sb: Path):
    """Tamil script never reaches a surface Andrew READS (2026-08-03).

    23 of 95 knock bodies carried script between 06-30 and 08-03 and he reported
    it three times in two days. The rule was never missing — it was stated four
    different ways, three of them scoped to "chat", and mandates.py enumerated
    "text/challenge/grace" so an AUDIO knock's body was never covered at all:
    7 of the 23 came through that hole. The fix is one question asked by SURFACE
    (which sense receives it?) instead of four phrasings keyed to modality.

    The composer transliterates its own line, so Andrew's colloquial
    contractions survive — a lexicon-substitution version was built and retired
    the same morning for flattening நல்லாருக்கு into the dictionary key's
    "nalla irukku" (Andrew: "brittle, and it violates my colloquial
    contractions"). Leftovers warn and ship: he reads enough for contextual
    clues, so a leaked word is cheaper than a lost dose.
    """
    print("\n50. Read surfaces are phonetic; spoken surfaces keep script (2026-08-03)")

    # The rule is asked by surface, and no longer enumerates modalities.
    from mandates import OUTREACH_MANDATE
    check("the mandate rules the body on EVERY modality, not a lane list",
          "text/challenge/grace body" not in OUTREACH_MANDATE
          and "audio and volley included" in OUTREACH_MANDATE)
    check("the reply push-back is mandatory, not 'fine'",
          "Phonetic Tamil is fine here" not in kr.JUDGE_MANDATE
          and "ENGLISH PHONETICS" in kr.JUDGE_MANDATE)
    canon = (REAL_BASE / "protocol" / "constitution.md").read_text(encoding="utf-8")
    for f in ("protocol/persona.md", ".claude/skills/anna/SKILL.md"):
        txt = (REAL_BASE / f).read_text(encoding="utf-8")
        check(f"{f} states the SAME surface rule, not a 'chat' paraphrase",
              "surface" in txt.lower() and "voice" in txt.lower(), f)
    check("the constitution asks which sense receives it",
          "which SENSE receives it" in canon)

    # The transform itself: composer-driven, so contractions survive.
    seen = []
    mk.rephrase_phonetic = lambda b: (seen.append(b), "romba nallarukku — the melt line")[1]
    out = mk.to_phonetic("ரொம்ப நல்லாருக்கு — the melt line")
    check("script goes to the composer, which keeps his contraction",
          out == "romba nallarukku — the melt line" and "nalla irukku" not in out, out)
    check("...and it was handed the original line", seen == ["ரொம்ப நல்லாருக்கு — the melt line"])

    seen.clear()
    clean = "romba nallarukku — say it"
    check("a body with no Tamil never calls the model at all",
          mk.to_phonetic(clean) == clean and not seen)

    mk.rephrase_phonetic = lambda b: b          # composer ignores the ask
    check("a surviving leak warns and SHIPS — a lost dose costs him more",
          mk.to_phonetic("try கிடைக்கும் today") == "try கிடைக்கும் today")

    # End to end: what he was sent is what got logged.
    klog_path = sb / "progress" / "knock_log.json"
    pushes = Recorder()
    mk.push_to_phone, mk.commit_and_push = pushes, Recorder()
    mk.rephrase_phonetic = lambda b: "today's line — romba nallarukku"
    d = {"act": True, "modality": "audio", "move": "smoke script", "rationale": "smoke",
         "notification_body": "today's line — ரொம்ப நல்லாருக்கு",
         "memo_script": "ரொம்ப நல்லாருக்கு", "expected_target": "",
         "target_revealed": False, "schedule": None, "next_check_hours": 4}
    mk.decide = lambda digest, vt=None: dict(d)
    rendered = []
    async def fake_render(script, out_path, voice):
        rendered.append(script)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"ID3fake")
    real_render, mk.render_memo = mk.render_memo, fake_render
    mk.refresh_feed = lambda: None
    try:
        sys.argv = ["morning_knock.py"]
        mk.main()
    finally:
        mk.render_memo = real_render
    entry = read_json(klog_path)[-1]
    check("an AUDIO knock's body is transformed too — the hole that leaked 7",
          "romba nallarukku" in (entry.get("body") or "")
          and "ரொம்ப" not in (entry.get("body") or ""), str(entry.get("body")))
    check("...the log records what he was sent, not the draft",
          pushes and "romba nallarukku" in str(pushes[-1]), str(pushes[-1] if pushes else None))
    check("...and the SPOKEN memo keeps its script — a Tamil voice needs it",
          rendered == ["ரொம்ப நல்லாருக்கு"], str(rendered))

    # No call site may ever feed the spoken surfaces through the transform.
    for f in ("morning_knock.py", "knock_reply.py"):
        calls = re.findall(r"to_phonetic\((.{0,80})",
                           (REAL_BASE / "scripts" / f).read_text(encoding="utf-8"), re.S)
        check(f"{f}: only read surfaces are transformed",
              calls and all("memo_script" not in c and "voice_reply" not in c for c in calls),
              str(calls))


def s58_a_sheet_survives_a_model_thinking_out_loud(sb: Path):
    """The reply parser, for every shape a real reply comes in (2026-08-10).

    THE FAILURE THIS BLOCK EXISTS TO PREVENT, because it already happened: the
    first 45-minute long-haul render died at movement 5 of 15 with
    `Expecting value: line 1 column 1 (char 0)`. Nothing was wrong with the
    model's answer — it had simply written "Looking at the hosts carefully
    before building:" above a perfectly good object, and the parse only ever
    looked at character 0. Four movements of TTS were already paid for and the
    tape was lost whole.

    IT IS THE MANDATE THAT INVITES IT. The `inventory` clause orders the writer
    to DROP coincidental hosts — a judgement per host — so it shows its work.
    Measured: 3 of 6 identical calls came back prose-prefixed. That is a coin
    flip per call, and a long-haul tape makes ~15 calls in a row.

    The negatives matter as much: a reply with NO object must still raise, or a
    lane silently ships a sheet-shaped blank instead of stopping.

    THE STRUCTURAL POINT, and the reason this block is not just three more parser
    cases: `parse_llm_json` had ALREADY fixed this family (07-04 empty text, 07-07
    single quotes, 07-13 prose-before-a-fence). `ask_json` simply never called it
    and re-earned the bug from scratch. So the last assertions here are that the
    lanes share ONE parser — a second one is how a fixed bug comes back."""
    print("\n58. A sheet survives a model that thinks out loud first (2026-08-10)")
    rd = importlib.import_module("render_drill")
    mk = importlib.import_module("morning_knock")
    sheet = '{"frame": "roots", "beats": [{"ta": "x", "en": "y", "who": "anna"}]}'

    for name, text in [
            ("a bare object", sheet),
            ("a ```json fence", f"```json\n{sheet}\n```"),
            ("an unlabelled fence", f"```\n{sheet}\n```"),
            ("REASONING PROSE, then a bare object — the render-killer",
             f"Looking at the hosts carefully before building:\n\n- real\n\n{sheet}"),
            ("reasoning prose, then a fence",
             f"Checking each host:\n\n```json\n{sheet}\n```"),
            ("prose that mentions a brace before the real object",
             f"I considered {{a, b}} and then wrote:\n\n```json\n{sheet}\n```"),
            ("an object with prose trailing after it",
             f"{sheet}\n\nI dropped one coincidental host.")]:
        try:
            got = mk.parse_llm_json(text)
        except Exception as e:                                  # noqa: BLE001
            got = {"frame": f"<raised {type(e).__name__}: {e}>"}
        check(f"the sheet is recovered from {name}", got.get("frame") == "roots",
              str(got.get("frame")))

    check("a multi-beat sheet keeps every beat, not just the first",
          len(mk.parse_llm_json(
              'prose\n{"frame": "f", "beats": [{"ta": "1"}, {"ta": "2"}, {"ta": "3"}]}'
          )["beats"]) == 3)

    # A reply carrying no object must STOP the lane, never yield a blank sheet.
    for name, text in [("an empty completion", ""), ("only whitespace", "   \n "),
                       ("a refusal with no object", "I cannot do that.")]:
        raised = False
        try:
            mk.parse_llm_json(text)
        except (ValueError, json.JSONDecodeError):
            raised = True
        check(f"{name} raises rather than returning a blank sheet", raised)

    # ONE parser, not two. The drill lane owning a private brace-slice is exactly
    # how 07-13 came back on 08-10; the long-haul lane borrows this one in turn.
    drill_src = (REAL_BASE / "scripts" / "render_drill.py").read_text(encoding="utf-8")
    check("ask_json parses through the shared parser, not a private one",
          "parse_llm_response(resp)" in drill_src, "ask_json re-implemented the parse")
    # MECHANISM ONLY — the docstring above quotes the retired parse verbatim, and a
    # raw-text search matches its own explanation. Same trap s57 hit reading source.
    drill_code = "\n".join(l for i, l in enumerate(drill_src.splitlines(), 1)
                           if i in code_line_numbers(drill_src))
    check("...and no private brace-slice survives in the drill lane",
          'find("{")' not in drill_code and 'startswith("```")' not in drill_code,
          "a second parser is how 07-13 came back on 08-10")
    check("the long-haul lane borrows ask_json rather than rolling its own",
          "from render_drill import ask_json" in
          (REAL_BASE / "scripts" / "render_longhaul.py").read_text(encoding="utf-8"))

    # The retry is what makes a 15-call lane survivable; the LAST failure must
    # still surface, or a tape ends silently short instead of stopping loudly.
    src = inspect.getsource(rd.ask_json)
    check("ask_json retries rather than dying on one bad draw",
          "for attempt in range" in src and "tries" in src, src[:200])
    check("...and re-raises the final failure instead of swallowing it",
          "raise" in src, src[:200])

    calls = 0

    def _client(bodies, finish="stop"):
        """A stand-in OpenAI client yielding `bodies` in turn (last one repeats)."""
        def create(**kw):
            nonlocal calls
            calls += 1
            return types.SimpleNamespace(choices=[types.SimpleNamespace(
                finish_reason=finish,
                message=types.SimpleNamespace(
                    content=bodies[min(calls - 1, len(bodies) - 1)]))])
        return lambda **kw: types.SimpleNamespace(
            chat=types.SimpleNamespace(
                completions=types.SimpleNamespace(create=create)))

    real_client, real_key = rd.OpenAI, os.environ.get("OPENROUTER_API_KEY")
    os.environ["OPENROUTER_API_KEY"] = "test"
    try:
        rd.OpenAI = _client(["Thinking about it...", "Still thinking...", sheet])
        got = rd.ask_json("sys", "usr")
        check("a lane recovers from two bad draws in a row",
              got.get("frame") == "roots" and calls == 3, f"{got} after {calls} calls")

        calls = 0
        rd.OpenAI = _client(["no object here"])
        stopped = False
        try:
            rd.ask_json("sys", "usr")
        except (ValueError, json.JSONDecodeError):
            stopped = True
        check("...but a lane that never gets a sheet stops loudly", stopped)
        check("...after re-rolling, not on the first bad draw", calls == 3, f"{calls} calls")

        # A blown ceiling is NOT a bad draw. Re-rolling it burns three renders'
        # worth of tokens to hit the same wall — the 08-05 guard's whole point.
        calls = 0
        rd.OpenAI = _client(["deliberating at length", sheet], finish="length")
        truncated = False
        try:
            rd.ask_json("sys", "usr")
        except ValueError as e:
            truncated = "TRUNCATED" in str(e)
        check("a truncation fails loudly instead of being re-rolled blind",
              truncated and calls == 1, f"truncated={truncated} after {calls} calls")
    finally:
        rd.OpenAI = real_client
        if real_key is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = real_key


def main():
    with tempfile.TemporaryDirectory(prefix="tamil-smoke-") as tmp:
        sb = make_sandbox(Path(tmp))
        print(f"sandbox: {sb}")
        mk, kr, pq = load_modules(sb)
        s1_parse_llm_json(mk)
        s2_rails_gate(mk, sb / "progress" / "knock_log.json")
        s15_push_retry(mk)   # needs the real push_to_phone — s3+ stub it out
        s35_quiet_hours_chokepoint(sb)   # ditto: asserts on the real function
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
        s18_size_budgets(mk, kr, sb)
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
        s33_catch_response_pairs(mk, sb)
        s34_focus_and_background(sb)
        s36_soak_order_carries_shape(sb)
        s37_repair_earns_the_dose(sb)
        s38_teach_enters_the_lexicon(sb)
        s39_ticket_carries_the_commission(sb)
        s40_drill_consumes_its_commission(sb)
        s41_slip_ledger(kr, sb)
        s42_session_log_one_row_per_day(sb)
        s43_sidecar_callback_never_drops_silently(sb)
        s44_a_commission_can_discharge_the_flag(sb)
        s45_concurrent_appends_merge(mk, sb)
        s46_the_commission_gate_blocks_the_close(sb)
        s47_hinted_retest_block(sb)
        s53_prune_duplicate_lexicon_rows(sb)
        s54_two_eras_not_a_deadline(sb)
        s55_demotion_survives_the_close(sb)
        s56_timezone_is_one_dial(sb)
        s48_drill_answer_key_lint(sb)
        s57_longhaul_tape(sb)
        s58_a_sheet_survives_a_model_thinking_out_loud(sb)
        s49_thread_continuity(mk, kr, sb)
        s50_read_surfaces_are_phonetic(mk, kr, sb)
        s51_derived_files_are_rerendered_not_merged(mk, sb)
        s52_andrew_is_family_already(sb)

    print(f"\n{'ALL GREEN' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
