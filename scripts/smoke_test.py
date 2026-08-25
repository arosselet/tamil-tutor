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
import inspect
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path

# The harness lives in scripts/smoke/_fixtures.py (spine plan §10). Names that
# are never rebound come across directly — and MUST, for `mechanism` and the
# line counters: s18's guard matches them as bare calls, so reaching them
# through the module would make that guard silently stop counting these cases.
# The three that ARE rebound at run time — pb, wr, si — are reached through
# `fx` and nowhere else. See the module docstring for why.
from smoke import _fixtures as fx
from smoke import compose
from smoke import queue
from smoke import ratchets
from smoke import render
from smoke._fixtures import (
    check, load_modules, make_sandbox, mechanism, read_json, REAL_BASE,
    Recorder, run, snapshot, write_json,
)


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
    # The waking window lives in publish.py now — one owner, read by the rails,
    # this queue, and push_to_phone's backstop. Patch where it lives: `mk` holds
    # an import-time COPY, so patching there reaches morning_knock's rails and
    # nothing else. `in_waking_window` reads publish's binding.
    saved = (fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY)
    now = datetime.now(timezone.utc)

    def q_entry(qid: str, due_hours: float, force: bool = False) -> dict:
        return {"id": qid, "due": (now + timedelta(hours=due_hours)).isoformat(),
                "body": f"dose {qid}", "expected_target": "", "target_revealed": True,
                "audio_url": None, "move": "smoke", "force": force,
                "queued_at": now.isoformat()}

    args = argparse.Namespace(dry_run=False, no_commit=False)
    try:
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 99
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
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR = 0, 0
        write_json(q_path, [q_entry("qQUIET", -1), q_entry("qFORCE", -1, force=True)])
        pq.cmd_drain(args)
        check("quiet hours defers non-forced, fires forced",
              len(pushes) == 3 and pushes[2][0] == "dose qFORCE"
              and [e["id"] for e in read_json(q_path)] == ["qQUIET"])

        # daily cap defers non-forced; forced ignores it
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 0
        write_json(q_path, [q_entry("qCAP", -1), q_entry("qFORCE2", -1, force=True)])
        pq.cmd_drain(args)
        check("cap defers non-forced, fires forced",
              len(pushes) == 4 and pushes[3][0] == "dose qFORCE2"
              and [e["id"] for e in read_json(q_path)] == ["qCAP"])
    finally:
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = saved


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

    # ── THE SEQUENCE PROPERTY — what the incident actually was ──────────────
    # The two assertions above are POINTWISE: lore one day old says SPENT, lore
    # LORE_COOLDOWN_DAYS+2 old says vein. The 2026-07-11 bug was neither. It was
    # FOUR frame-etymology memos on FOUR CONSECUTIVE DAYS — a run, and a rails
    # line that only covered "yesterday" would pass both checks above and still
    # let days 2, 3 and 4 through. So walk the whole window instead of sampling
    # two points in it, and walk one day past the far edge.
    for d in range(mk.LORE_COOLDOWN_DAYS):
        one = [{"acted": True, "move": "lore memo: -aachu frame",
                "timestamp": (now - timedelta(days=d)).isoformat()}]
        if "SPENT" not in mk.remaining_room(one, now):
            check(f"lore is SPENT on every day of the cooldown (day {d} leaked)", False,
                  mk.remaining_room(one, now))
            break
    else:
        check(f"lore reads SPENT on ALL {mk.LORE_COOLDOWN_DAYS} days of the window, "
              f"not just yesterday", True)
    edge = [{"acted": True, "move": "lore memo: -aachu frame",
             "timestamp": (now - timedelta(days=mk.LORE_COOLDOWN_DAYS)).isoformat()}]
    check("...and the window ENDS on schedule — the format is not locked out forever",
          "different vein" in mk.remaining_room(edge, now), mk.remaining_room(edge, now))

    # The incident's own shape: a run of them. The rails must read the LATEST
    # fire, so four consecutive days still says SPENT rather than aging out on
    # the oldest entry in the log.
    run_of_four = [{"acted": True, "move": "lore memo: -aachu frame",
                    "timestamp": (now - timedelta(days=d)).isoformat()}
                   for d in (9, 8, 7, 1)]
    check("a RUN of lore memos is judged on the most recent, not the oldest",
          "SPENT" in mk.remaining_room(run_of_four, now),
          mk.remaining_room(run_of_four, now))

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

    # never-soaked items are flagged UNSEEN on the menu (teach before quiz)
    lex_path = sb / "progress" / "lexicon.json"
    write_json(lex_path, {
        "வணக்கம்": {"gloss": "hello", "phonetic": ["vanakkam"], "recognition": "struggled",
                     "production": "none", "seen_in": [], "last_surfaced": None,
                     "register": "antifreeze", "direction": "fire"},
    })
    menu = mk.due_menu_block()
    check("never-soaked item flagged UNSEEN", "UNSEEN" in menu, menu)
    lex = read_json(lex_path)
    lex["வணக்கம்"]["last_surfaced"] = "2026-07-01"
    write_json(lex_path, lex)
    check("soaked item loses the UNSEEN flag", "UNSEEN" not in mk.due_menu_block())


def s14_reply_correlation(kr):
    """2026-07-11 (KF-9): notifications stack; taps and replies carry the knock's
    log timestamp back as knock_id. find_knock targets the exact entry; a
    missing/stale/empty id returns None so callers fall back to last-fired
    (pre-migration notifications stay judgeable).

    This case owns CORRELATION only. The tag was also unique-per-knock until
    2026-08-19 — s67 owns notification IDENTITY now, and explains why the two
    could not keep sharing a key."""
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


    # ── The cadence prompt, which lives behind a bare `except: pass` ──────────
    #
    # `remaining_room` warns Anna when catch items are pending and no eavesdrop
    # has fired inside EAVESDROP_CADENCE_DAYS — "this is the highest-value move
    # right now". Catch advances through THIS DOSE AND NO OTHER, so the warning
    # is the only thing standing between a starved ear and a quiet rotation.
    #
    # It is wrapped in `try/except Exception: pass` on purpose (a cadence check
    # must never kill a reach), which makes it a Gate 7.2 shape: if its data
    # source raises, the warning vanishes and the digest still renders perfectly.
    # Nothing covered it until 2026-08-18, when the deck retirement repointed it
    # from `deck_status(...)["catch_pending"]` to `ear_targets(...)["pending"]` —
    # a swap that would have failed exactly this silently.
    real_last = mk.last_eavesdrop
    try:
        lex_path = sb / "progress" / "lexicon.json"
        saved_lex = lex_path.read_bytes()
        now_local = datetime.now(timezone.utc).astimezone()
        write_json(lex_path, {
            "smoke:cad-ear": {"gloss": "pending catch", "type": "chunk",
                              "direction": "catch", "recognition": "struggled",
                              "production": "none", "seen_in": [], "last_surfaced": None},
        })
        mk.last_eavesdrop = lambda klog: None
        room = mk.remaining_room([], now_local)
        check("a pending catch item with NO eavesdrop ever fired is called out",
              "Eavesdrop:" in room and "NEVER fired" in room, room)
        check("...and the count comes from the ear selector, not a stale reader",
              "1 catch item(s)" in room, room)

        # A recent eavesdrop silences it; a lapsed one brings it back. The clock
        # is the constant, never a literal.
        def fired(days_ago):
            ts = (now_local - timedelta(days=days_ago)).isoformat()
            return lambda klog: {"timestamp": ts}

        mk.last_eavesdrop = fired(0)
        check("a fresh eavesdrop silences the prompt",
              "Eavesdrop:" not in mk.remaining_room([], now_local),
              mk.remaining_room([], now_local))
        mk.last_eavesdrop = fired(mk.EAVESDROP_CADENCE_DAYS + 1)
        lapsed = mk.remaining_room([], now_local)
        check("a lapsed cadence brings it back", "Eavesdrop:" in lapsed, lapsed)

        # THE SILENT-NO-OP GUARD ITSELF. The `except` must swallow a crash — that
        # is its job — but the case has to prove the block is doing work at all,
        # or a broken data source reads exactly like a healthy quiet day.
        write_json(lex_path, {"smoke:cad-fire": {
            "gloss": "no catch anywhere", "type": "chunk", "direction": "fire",
            "recognition": "solid", "production": "none", "seen_in": [1],
            "last_surfaced": None}})
        mk.last_eavesdrop = lambda klog: None
        check("no catch pending, no prompt — quiet is earned, not accidental",
              "Eavesdrop:" not in mk.remaining_room([], now_local))
    finally:
        mk.last_eavesdrop = real_last
        lex_path.write_bytes(saved_lex)


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
    real_urlopen, real_sleep = fx.pb.urllib.request.urlopen, fx.pb.time.sleep
    os.environ["ANNA_PUSH_WEBHOOK_URL"] = "https://smoke.invalid/hook"
    try:
        fx.pb.time.sleep = sleeps.append

        def flaky(req, *a, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise urllib.error.URLError(OSError("Temporary failure in name resolution"))
            return FakeResp()
        fx.pb.urllib.request.urlopen = flaky
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
        fx.pb.urllib.request.urlopen = dead
        try:
            mk.push_to_phone("smoke", None, knock_id="smoke", requested=True)
            check("unreachable webhook still raises", False, "did not raise")
        except OSError:
            check("unreachable webhook still raises", True)
        check("gave up after 3 attempts", calls["n"] == 3, f"{calls['n']} calls")
    finally:
        fx.pb.urllib.request.urlopen, fx.pb.time.sleep = real_urlopen, real_sleep
        os.environ.pop("ANNA_PUSH_WEBHOOK_URL", None)


def s67_two_replies_to_one_knock_both_survive(mk):
    """2026-08-18: Andrew asked what 'inge poringe' means, then sent a test message.
    He got the test answer and never saw the Tamil one. Nothing failed — the reply
    was judged, committed (e1fa4ea), and delivered HTTP 200. Both replies arrived
    via the Shortcut, which sends no knock_id, so both fell back to
    last_fired_knock, both resolved knock 2026-08-18T10:21, and both carried
    tag "anna-2026-08-18T10:21". iOS replaces a notification whose tag is already
    on the lock screen, so the second ate the first 43 seconds later.

    THE SILENT NO-OP: this is invisible from inside. The run is green, the push
    returns 200, chat.md holds both exchanges, the knock log is correct. The ONLY
    place the collision is observable is the tag on the wire — so that is what
    this asserts, off the real Request, not off the function's return value."""
    print("\n67. Two replies to one knock both reach the lock screen (2026-08-18)")
    import os

    class FakeResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    sent = []
    real_urlopen = fx.pb.urllib.request.urlopen
    os.environ["ANNA_PUSH_WEBHOOK_URL"] = "https://smoke.invalid/hook"
    try:
        def capture(req, *a, **kw):
            sent.append(json.loads(req.data.decode()))
            return FakeResp()
        fx.pb.urllib.request.urlopen = capture
        # The exact 08-18 shape: two DIFFERENT messages, ONE resolved knock.
        # requested=True so the quiet-hours chokepoint can't short-circuit the
        # case when the suite runs late (same reason as s15).
        knock = "2026-08-18T10:21:00+00:00"
        mk.push_to_phone("inge poringe = go here…", None, knock_id=knock, requested=True)
        mk.push_to_phone("loud and clear da 👂", None, knock_id=knock, requested=True)
        check("both pushes left the building", len(sent) == 2, f"{len(sent)} sent")
        first, second = sent
        # THE ASSERTION THAT WOULD HAVE CAUGHT IT. Identity must differ...
        check("two messages on one knock get DIFFERENT notification tags",
              first["tag"] != second["tag"], f"both tagged {first['tag']!r}")
        # ...while correlation must NOT, or the judge grades the wrong entry.
        check("both still correlate to the same knock for judging",
              first["knock_id"] == second["knock_id"] == knock)
        check("the tag still names its knock (legible in HA's log)",
              first["tag"].startswith(f"anna-{knock}"), first["tag"])
        # An id-less push (Shortcut reply before last-fired resolves, ad-hoc dose)
        # must not collapse every such notification onto one shared tag.
        sent.clear()
        mk.push_to_phone("a", None, requested=True)
        mk.push_to_phone("b", None, requested=True)
        check("id-less pushes don't all share the 'anna-knock' tag",
              sent[0]["tag"] != sent[1]["tag"], f"both tagged {sent[0]['tag']!r}")
    finally:
        fx.pb.urllib.request.urlopen = real_urlopen
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

    check("no record → unseen", fx.si.is_unseen({}))
    check("surfaced → not unseen", not fx.si.is_unseen({"last_surfaced": "2026-07-01"}))
    check("in an episode → not unseen", not fx.si.is_unseen({"seen_in": ["M60"]}))

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

    # 2026-08-10, THE EFFECT AND NOT THE SHAPE. The count above stayed green for
    # the whole six days this block was empty: the heading was there, its TITLE
    # had changed, and an exact-string match returned "" with nothing anywhere to
    # say so. Every fixture above proves the extractor against prose the test
    # wrote itself — only the real file proves the digest.
    saved, mk.BASE = mk.BASE, REAL_BASE
    try:
        real_block = mk.campaign_block()
    finally:
        mk.BASE = saved
    check("the REAL profile.md yields a campaign, not silence",
          real_block.startswith("CAMPAIGN") and len(real_block) > 200,
          f"{len(real_block)} chars — cloud Anna would steer with no campaign")


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


def s59_transit_bit(mk, sb: Path):
    """The transit bit: a date Andrew sets, the rails enforce (2026-08-10).

    Deliberately three checks, not ten (Andrew called the longer version
    overkill and he is right — he will not forget to clear it; he lands wanting
    to carry on). Each one here maps to a failure that is SILENT and costs him
    the exact thing the bit exists to buy:

      set → eaten   `quiet_until` lives in learner.json, whose writer is a
                    whitelist that DELETES unlisted keys — how every
                    --slip-tested close was erased for a day (s41). He sets it,
                    a session close wipes it, and he gets knocked all flight.
                    So this round-trips the real writer and re-reads the file.
      set → ignored the rail never fires and the flight fills with overwrites.
      cleared → stuck  he lands, clears it, and the channel stays dead."""
    print("\n59. The transit bit — Andrew sets a date, the rails hold (2026-08-10)")
    sync = importlib.import_module("sync_state")

    def set_bit(value):
        sys.argv = ["sync_state.py", "update", "--quiet-until", value]
        try:
            sync.main()
        except SystemExit:
            pass
        return json.loads((sb / "progress" / "learner.json").read_text(encoding="utf-8"))

    noon = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)

    check("the bit survives the learner whitelist's round trip",
          set_bit("2026-08-12").get("quiet_until") == "2026-08-12",
          "a key missing from write_thin_learner is deleted, not left stale")
    ok, why = mk.rails_gate(False, now=noon)
    check("a tick inside the window is held, and says transit not fade",
          not ok and "transit" in why, why)
    set_bit("")
    check("clearing it re-opens the gate on the next tick",
          "transit" not in mk.rails_gate(False, now=noon)[1])


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
        src = mechanism(Path(ra.__file__).read_text(encoding="utf-8"))
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

        # Re-rendering an existing script needs TTS only. Gating it on the WRITER
        # would strand a scripted-but-unrendered episode on a host that can render.
        # (ADC still mocked-present here, so this isolates the writer axis.)
        rs = importlib.import_module("run_studio")
        real_which = fx.wr.shutil.which
        fx.wr.shutil.which = lambda cmd: None if cmd == "claude" else real_which(cmd)
        try:
            check("no writer → render path still allowed", rs.renderer_preflight() is None)
            check("no writer → fresh-episode path blocked", rs.preflight() is not None)
        finally:
            fx.wr.shutil.which = real_which
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
    lex = {"அவசரம் இருக்கு": {"phonetic": ["avasaram irukku"], "gloss": "hurry"},
           "frame:needtogo-place": {"phonetic": [], "gloss": "must go to X"}}
    resolved, unresolved = fx.si.split_payload(["avasaram", "frame:needtogo-place"], lex)
    check("bare headword resolves to its chunk key",
          "அவசரம் இருக்கு" in resolved, f"got {resolved}")
    check("no false unresolved", unresolved == [], f"got {unresolved}")
    junk_r, junk_u = fx.si.split_payload(["definitely-not-a-word"], lex)
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
    status_src = mechanism((REAL_BASE / "scripts" / "session_brief.py")
                           .read_text(encoding="utf-8"))
    check("the status drain-check uses the shared resolver",
          "split_payload(soak.get" in status_src)
    # THIS ONE WAS A DECORATION (found 2026-08-24, when the raw-source read here
    # became a `mechanism` read and it went red). `split_payload` appears in
    # studio_watchdog.py exactly once, in a COMMENT explaining what the root
    # cause had been — the watchdog has never called it. It asks `soak_pending()`
    # instead, which is the shared resolver one rung further down, so the LAW
    # held the whole time and the assertion proving it was reading prose. Assert
    # what the watchdog actually does, and that it does not grow its own copy.
    wd_src = mechanism((REAL_BASE / "scripts" / "studio_watchdog.py")
                       .read_text(encoding="utf-8"))
    check("the watchdog drain-check uses the shared resolver",
          "from state_io import soak_pending" in wd_src and "soak_pending()" in wd_src,
          "the watchdog re-derives 'is a soak still owed' instead of asking L0")
    check("...and never re-derives the payload itself",
          "split_payload" not in wd_src, "a second copy of the resolver is back")

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


def s30_anna_speaks_back(mk, kr, sb: Path):
    print("\n30. Anna can answer ALOUD from the lock screen (2026-07-24)")

    # The loop was three-quarters closed: audio out on the knock, text in from
    # the phone, cloud judgment, text back. push_to_phone(body, None, ...) was
    # hard-coded in BOTH reply paths, so Anna could never speak back.
    src = mechanism((REAL_BASE / "scripts" / "knock_reply.py").read_text(encoding="utf-8"))
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
    src = mechanism((REAL_BASE / "scripts" / "rebuild_rss.py").read_text(encoding="utf-8"))
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


def s32_pool_rotation_and_coverage(mk, sb: Path):
    """Starvation (2026-07-25 audit). The selector ordered by tier -> ripeness ->
    alphabetical, with no staleness term — so the head of each tier was frozen
    and the tail never surfaced: 16 frames took 51 of 74 lifetime reps while 45
    of 70 fire items had never been asked once, and `cold/total` reported a
    winning sprint throughout because it counts progress and cannot see
    distribution. Ripeness-first was rich-get-richer (an item only becomes
    `hinted` by being worked, which promoted it again).

    Two mechanisms, both proven here: least-recently-worked sorts first WITHIN a
    tier (the tier prefix itself is the touchdown bar and must survive), and
    `register_coverage` counts worked/total so the tail is legible.

    REWRITTEN 2026-08-18 for the deck retirement. Every assertion below survives
    it — what changed is that `register` rides on the row instead of being joined
    from `curriculum/trip_deck.json` on `deck` membership, and one pool replaces
    the deck/floor pair. The fixture therefore carries NO `deck` tag: that is the
    point of the retirement, and a tier assertion that still needed one would be
    testing the container, not the ordering it left behind."""
    print("\n32. Pool rotation + coverage: the tail is not starved (2026-07-25)")
    st = importlib.import_module("suggest_targets")
    ss = importlib.import_module("sync_state")
    today = date_cls.today()

    def ago(n):
        return (today - timedelta(days=n)).isoformat()

    def item(reg, **kw):
        base = {"register": reg, "gloss": "x", "phonetic": [], "type": "chunk",
                "recognition": "struggled", "production": "none",
                "seen_in": [1], "last_surfaced": None}
        base.update(kw)
        return base

    lex = {
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
    # The UNREGISTERED population (2026-07-26): rows with no register, which
    # degrade to delight. Both never-surfaced and identical on every other term,
    # so the ask count is the only thing that can separate them — and `-a` sorts
    # first alphabetically, which is what the old key fell through to.
    lex.update({
        "smoke:floor-a": {"gloss": "asked outside the cooldown", "phonetic": [], "type": "chunk",
                          "recognition": "comfortable", "production": "none",
                          "seen_in": [1], "last_surfaced": None},
        "smoke:floor-b": {"gloss": "never asked", "phonetic": [], "type": "chunk",
                          "recognition": "comfortable", "production": "none",
                          "seen_in": [1], "last_surfaced": None},
    })
    lex_path = sb / "progress" / "lexicon.json"
    klog_path = sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())
    # Yesterday's volley asked surv-tail as its SECOND item — `expected_target`
    # names only item 1, so items 2..n were invisible to the ask count while the
    # volley is the main volume channel.
    recent_ts = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
    # Derived from the constant, never a literal: this was `days=5`, which sat
    # outside the 3-day cooldown and INSIDE the 7-day one (2026-08-18), so
    # widening the window silently flipped an assertion about lifetime reps.
    old_ts = (datetime.now(timezone.utc)
              - timedelta(days=st.ASK_COOLDOWN_DAYS + 2)).isoformat()
    klog = [{"acted": True, "timestamp": recent_ts, "modality": "volley",
             "expected_target": "smoke:surv-mid", "body": "volley 1/2",
             "volley": [{"target": "smoke:surv-mid", "ask": "a"},
                        {"target": "smoke:surv-tail", "ask": "b"}]},
            {"acted": True, "timestamp": old_ts, "modality": "knock",
             "expected_target": "smoke:floor-a", "body": "the floor ask"}]
    try:
        write_json(lex_path, lex)
        write_json(klog_path, klog)

        asked = st.recent_ask_counts(klog, lex)
        check("a volley's later items count as asked, not just item 1",
              asked.get("smoke:surv-tail") == 1, f"got {asked}")
        check("the volley's opening item still counts",
              asked.get("smoke:surv-mid") == 1, f"got {asked}")

        # Ask-count breaks the tie the never-worked cohort sits in: surv-tail and
        # surv-unseen are both NEVER_SURFACED, and tail was asked.
        focus, _bg = st.floor_gap_targets(lex, today, 20, asked=asked, cohort=[])
        order = [t["word"] for t in focus]
        check("within the never-worked cohort, least-asked leads (not alphabetical)",
              order.index("smoke:surv-unseen") < order.index("smoke:surv-tail"), f"got {order}")
        check("ask-count stays subordinate to tier: an asked survival item still "
              "outranks an unasked dessert one",
              order.index("smoke:surv-tail") < order.index("smoke:dessert-new"), f"got {order}")
        # ── THE DISTRIBUTION PROPERTY — what the incident actually was ──────
        # Every assertion above is POINTWISE: one call, one pair compared. KF-12
        # was not a pair in the wrong order. It was 45 of 70 fire items never
        # asked once, across weeks, while cold/total reported a winning sprint —
        # and a selector can satisfy every ordering rule above and still starve
        # its tail, because starvation is a property of the SEQUENCE, not of any
        # single call. `s34` already tests its own ordering this way (its
        # `range(40)` loop); this is that shape, applied to the bug it was
        # written for. Feeding `asked` back in is what closes the loop: being
        # asked must move an item to the back of its own queue, or the head
        # freezes and the tail is never reached.
        #
        # WITHIN A TIER, deliberately. Tier order is the touchdown bar and must
        # survive — a dessert item legitimately waits while survival work is
        # outstanding, so a cross-tier fairness assertion would be testing the
        # opposite of the design. The starvation was always inside a tier: the
        # head frozen by ripeness-first (an item became `hinted` by being worked,
        # which promoted it again), the tail never surfacing.
        tier = ["smoke:surv-mid", "smoke:surv-tail", "smoke:surv-unseen"]
        turns = {}
        for _ in range(40):
            f, _b = st.floor_gap_targets(lex, today, 20, asked=dict(turns), cohort=[])
            for t in f[:2]:
                turns[t["word"]] = turns.get(t["word"], 0) + 1
        starved = [w for w in tier if not turns.get(w)]
        check("over 40 selections every item in the tier is reached — no starved tail",
              not starved, f"never asked once: {starved} (turns={turns})")
        hi, lo = max(turns.get(w, 0) for w in tier), min(turns.get(w, 0) for w in tier)
        check("...and the tier's turns are SHARED, not taken by its head",
              lo and hi <= lo * 1.5,
              f"head took {hi}, tail took {lo} — rich-get-richer is back ({turns})")

        check("the ask count rides on the item for the menu's warning",
              [t["asks"] for t in focus if t["word"] == "smoke:surv-tail"] == [1],
              f"got {focus}")
        check("the knock menu names the recent ask",
              "asked/shown 1×" in mk.due_menu_block(), f"got {mk.due_menu_block()}")
        # One owner: the knock channel no longer re-sorts, so its picks must be
        # the selector's own order.
        vt = [t["target"] for t in mk.volley_targets(n=4)]
        menu = [t["word"] for t in st.drill_menu(lex, today=today, asked=asked)]
        check("the volley reads the selector's order, it does not re-sort",
              [w for w in menu if w in vt] == vt, f"volley={vt} menu={menu}")
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
        check("coverage counts LIFETIME reps, not the ask cooldown",
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
        # One law, one definition: the pool prefixes tier and then defers.
        check("the pool prefixes tier and then defers to the shared law",
              st.coverage_key({"word": "x", "reps": 0}) < st.coverage_key({"word": "x", "reps": 1})
              and st.pool_key({"word": "x", "reps": 0, "tier_rank": 0})
              < st.pool_key({"word": "x", "reps": 0, "tier_rank": 1}),
              "coverage_key does not lead with reps, or pool_key does not lead with tier")

        # Re-run the ordering laws with an empty log, so the coverage assertions
        # below read the same fixture the rest of the case was written against.
        write_json(klog_path, [])
        focus, _bg = st.floor_gap_targets(lex, today, 20, asked={}, cohort=[])
        order = [t["word"] for t in focus]

        # The regression: under the old key the ripe, recently-worked headliner
        # led its tier forever. Least-recently-worked now leads.
        check("a never-worked item outranks the ripe recently-worked headliner",
              order[0] == "smoke:surv-tail", f"got {order}")
        # Asserted on `drill_menu`, not the pool: surv-hot is a PATTERN, and the
        # pool has never held those (they are forced by producing a novel
        # instance, which is the Engines block's job). The menu is where the two
        # views meet, so it is where the two rows are comparable at all — and
        # dropping the assertion because the row moved would retire the
        # regression it exists for.
        hot = [t["word"] for t in st.drill_menu(lex, today=today, asked={})]
        check("the worked headliner falls behind the starved row of its tier",
              hot.index("smoke:surv-mid") < hot.index("smoke:surv-hot"), f"got {hot}")
        check("staleness beats ripeness, not tier: survival still precedes delight",
              order.index("smoke:surv-unseen") < order.index("smoke:delight-new"), f"got {order}")
        check("the touchdown bar survives: delight still precedes dessert",
              order.index("smoke:delight-new") < order.index("smoke:dessert-new"), f"got {order}")
        check("a cold item leaves the pending queue", "smoke:surv-done" not in order)

        # The ear starved worst of all (1 of 12 ever touched) — same law applies.
        ear = st.ear_targets(lex, today=today)
        catch_order = [t["word"] for t in ear["pending"]]
        check("the ear rotates too: the never-worked catch item leads",
              catch_order[0] == "smoke:ear-stale", f"got {catch_order}")
        check("the ear is never in the fire pool — a different axis, not a rival",
              not any(w.startswith("smoke:ear") for w in order), f"got {order}")

        # Rotation must not smuggle an UNSEEN item into a cold quiz (teach-first).
        vt = [t["target"] for t in mk.volley_targets(n=4)]
        check("rotation respects teach-first: UNSEEN stays out of the volley",
              "smoke:surv-unseen" not in vt, f"got {vt}")
        check("a never-worked but soaked item IS volley-eligible",
              "smoke:surv-tail" in vt, f"got {vt}")

        cov = st.register_coverage(lex, today=today)
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
        # GENERALISED off the deck: unregistered rows get their own bucket rather
        # than swelling the tier they degrade into, where 256 of 339 would hide
        # exactly the distribution this block exists to show.
        check("unregistered rows are counted apart, not folded into delight",
              cov["unregistered"]["total"] == 2 and delight["total"] == 1,
              f"got unregistered={cov['unregistered']} delight={delight}")
        never = {u["word"] for u in cov["untouched"]}
        check("every never-worked ranked item is named",
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
        # THE RETIREMENT ITSELF: no section may claim to outrank the others any
        # more. That primacy claim, times three, is what made a 361-line ticket
        # depend on which section Anna weighted that day.
        check("no pool claims primacy on the ticket",
              "force these before the general floor" not in out.getvalue()
              and "TRIP DECK" not in out.getvalue(), "a primacy headline survived")

        # The ear meter carries its own coverage count, so a green headline can
        # never again hide a starved ear.
        ce = ss.compute_ear(lex)
        check("the status meter carries the ear's coverage count",
              (ce["caught"], ce["total"], ce["untouched"]) == (0, 2, 1), f"got {ce}")
    finally:
        lex_path.write_bytes(saved[0])
        klog_path.write_bytes(saved[1])


def s33_catch_response_pairs(mk, sb: Path):
    """Catch-and-response is a first-class curriculum kind, and the schema had no
    way to say it (2026-07-26 audit). The pairing lived as English prose in
    `note`/`gloss` — "the maami's line at the table" — so nothing could drill a
    pair as a pair, and nothing noticed when `seed-deck` dropped the response
    while its prompt kept its slot. `pairs_with` is the one relation the schema
    carries; it must resolve inside the seed file, ride onto the lexicon, and
    reach both surfaces that show catch items.

    `seed-deck` outlived the trip deck (2026-08-18): curated-set seeding is
    useful for any future set, and only the *trip* framing retired. So this case
    keeps exercising it — and now also guards the field the retirement added,
    `register`, whose writer path this command is."""
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
         "register": "mil-table", "pairs_with": answer},
        {"tamil": answer, "gloss": "no thanks, I'm full", "type": "chunk",
         "recognition": "struggled", "phonetic": ["vendaamma"],
         "register": "antifreeze"},
    ]
    try:
        write_json(lex_path, {})
        out, lex = seed(paired)
        check("the pair rides from the deck file onto the lexicon",
              lex[prompt].get("pairs_with") == answer, f"got {lex.get(prompt)}")
        check("the answer is a FIRE item — the catch half alone is not the win",
              lex[answer].get("direction") == "fire", f"got {lex.get(answer)}")
        # THE MIGRATION'S WRITER PATH (2026-08-18). The tier ordering outlived the
        # deck only because `register` reaches the ROW; if it stopped at the
        # curriculum file the ordering would be joined off a container that no
        # longer exists, which is the silent no-op the retirement was written to
        # avoid. `progress/*.json` is never hand-edited, so this command is the
        # only way that field can legitimately land.
        check("seed-deck lands the register on the lexicon row, not just the tag",
              lex[answer].get("register") == "antifreeze"
              and lex[prompt].get("register") == "mil-table", f"got {lex.get(answer)}")
        check("...and the ordering reads it back as the survival tier",
              st.tier_rank(lex[answer]) == 0 and st.tier_rank(lex[prompt]) == 1,
              f"got {st.tier_rank(lex[answer])}/{st.tier_rank(lex[prompt])}")

        ear = st.ear_targets(lex, today=date_cls.today())
        cp = [t for t in ear["pending"] if t["word"] == prompt]
        check("ear_targets resolves the pair for the drill",
              cp and cp[0]["pairs_with"] == answer and cp[0]["response_gloss"] == "no thanks, I'm full",
              f"got {cp}")
        check("the ticket names the answer under the line he'll hear",
              "he answers:" in ticket_text(), "the ear-only block hid the pair")
        check("the knock menu marks a paired item so Anna plays HER line",
              "[pair]" in mk.due_menu_block() and "never quiz the catch half alone" in mk.due_menu_block(),
              f"got {mk.due_menu_block()}")

        # THE regression: the response was dropped from the seed file while its
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
        check("a refused seed writes NOTHING — no half-landed set",
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
    # The scripts directory, named absolutely rather than relative to THIS file:
    # this case is about to move into smoke/, where `__file__.parent` would
    # quietly become the test package and every source read below would miss.
    src_dir = REAL_BASE / "scripts"

    real_urlopen = fx.pb.urllib.request.urlopen
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
        fx.pb.urllib.request.urlopen = fake_urlopen
        os.environ["ANNA_PUSH_WEBHOOK_URL"] = "http://smoke.invalid/push"
        check("the waking window has ONE definition",
              fx.pb.in_waking_window(noon) and not fx.pb.in_waking_window(night),
              "in_waking_window disagrees with the rails")

        real_now = fx.pb.in_waking_window
        fx.pb.in_waking_window = lambda now=None: False
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
            fx.pb.in_waking_window = real_now
    finally:
        fx.pb.urllib.request.urlopen = real_urlopen
        if real_env is None:
            os.environ.pop("ANNA_PUSH_WEBHOOK_URL", None)
        else:
            os.environ["ANNA_PUSH_WEBHOOK_URL"] = real_env

    # No lane may re-implement the rule; every push must go through the chokepoint.
    for name in ("run_studio.py", "push_queue.py", "render_drill.py", "render_soak.py"):
        src = mechanism((src_dir / name).read_text(encoding="utf-8"))
        check(f"{name} does not hand-roll the waking-hour compare",
              "WAKING_START_HOUR <=" not in src, f"{name} carries its own copy")
    check("in_waking_window has one home",
          "def in_waking_window" not in mechanism((src_dir / "push_queue.py")
                                                  .read_text(encoding="utf-8")),
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
        res, unres = fx.si.split_payload(["நிறைஞ்சிடுச்சு"], read_json(lex_path))
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
        # The |phonetic tail became mandatory on a NEW word 2026-08-14 (s59) —
        # a record minted without one can never be logged from chat again.
        word = "பக்கத்துல"
        lex, _ = update(teach=[f"{word}=beside/next to|pakkathula"])
        rec = lex.get(word)
        check("a taught word is created", rec is not None, "still absent")
        check("...at struggled recognition, not solid",
              rec and rec["recognition"] == "struggled", f"got {rec}")
        check("...with production unset, so the floor cannot inflate",
              rec and rec["production"] == "none", f"got {rec}")
        check("...carrying the gloss", rec and rec["gloss"] == "beside/next to")
        check("...and seen today", rec and rec["last_surfaced"] == ss.local_today().isoformat())

        # Teaching runs before the axes, so teach-then-fire in ONE close resolves.
        lex, _ = update(teach=["ஆச்சு=it happened / it's done|aachu"], produced_cold=["ஆச்சு"])
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
    #
    # FIXTURE CORRECTED 2026-08-20. This used to express "a dose was
    # commissioned" as `dose_channel="soak"` on the slip row. That is a
    # different fact — dose_channel records that SOME order was standing when
    # the slip happened, for some other payload — and feeding it into
    # `channels` is the bug that disarmed both gates for three weeks. The
    # assertion below was always right; the way it staged the world was not.
    # "A dose was commissioned for THIS tag" has exactly one spelling:
    sl.record_slip_commission(["past-tense"],
                              {"channel": "soak", "payload": ["irundhuchu"]},
                              today="2026-07-29")
    sl.append_slips([{"tag": "past-tense", "said": "irukku", "want": "irundhuchu"}],
                    lane="knock", when="2026-07-30")
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

    src = mechanism((REAL_BASE / "scripts" / "session_brief.py").read_text(encoding="utf-8"))
    check("the session digest shows what Anna CORRECTED on the phone",
          "corrected: " in src)
    # The string this used to grep for — `commit_paths.append(SLIP_LOG_PATH)` —
    # was one of the twenty-six hand-built commit lists that publish.publish
    # retired (2026-08-23). The PROPERTY is untouched and is what is asserted:
    # the reply lane names the slip ledger among the paths it hands to the
    # commit, conditioned on the verdict actually carrying slips.
    check("the knock reply commits the ledger — an unpushed slip dies with the runner",
          'SLIP_LOG_PATH if verdict.get("slips")' in
          mechanism((REAL_BASE / "scripts" / "knock_reply.py").read_text(encoding="utf-8")))

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


def s53_unverify_rows_nothing_ever_tested(sb: Path):
    """A recognition rating nobody ever earned (2026-08-23, Andrew).

    Replaces the prune-duplicates case with its own command. The lexicon's first
    populated commit already held 153 rows at solid:93 / comfortable:54 — a
    day-one self-estimate written into the field evidence writes into. Nothing
    downstream could tell the two apart, so the ticket offered a June guess as a
    known word and Anna demanded four words he had never met in one session.
    Andrew's ruling: repair the data, do not build a label around it.

    Gate 7.2 — the honest answer is nasty, because this tool has TWO silent
    failures pointing opposite ways. (a) A wrong predicate selects nothing and
    prints "every recognized one has been worked" — which is also exactly what a
    correct run prints once the migration has landed, forever after. So the case
    must prove it FINDS rows in a fixture that has them; a green "no-op" proves
    nothing. (b) An over-broad predicate silently wipes recognition off rows that
    were earned, and no meter would show it as anything but a lower floor. So
    every row below that carries evidence — a rep, a cold fire, or both — is
    asserted to survive untouched.

    And the third teeth: `reps` and `last_surfaced` must come through the write
    unchanged. Demoting via `--stuck-word` would have reached `touch()` and
    bumped both, destroying the signal that identifies these rows and faking a
    working date for callback due-ness. That is a round-trip assertion — re-read
    the file, never trust the dict the command was handed."""
    print("\n53. Recognition nobody ever tested is dropped to struggled (2026-08-23)")
    import contextlib, io, argparse as _ap
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    try:
        row = lambda **kw: {"gloss": "x", "phonetic": [], "recognition": "struggled",
                            "production": "none", "seen_in": [], "last_surfaced": None, **kw}
        lex = {
            # THE POPULATION: rated recognized, never worked by any channel.
            "அது": row(recognition="solid"),
            "இது": row(recognition="comfortable", seen_in=[3, 7], last_surfaced=None),
            # EVIDENCE, three ways — each of these must survive at its rating.
            "வா": row(recognition="solid", reps=4, last_surfaced="2026-08-01"),
            "போ": row(recognition="comfortable", production="cold"),
            "வை": row(recognition="solid", reps=1, production="hinted",
                      last_surfaced="2026-08-19"),
            # already at the floor — nothing to do, and it must not churn
            "சரி": row(recognition="struggled"),
        }
        write_json(lex_path, lex)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ss.cmd_unverify(_ap.Namespace(apply=False))
        check("a dry run writes nothing", read_json(lex_path) == lex, "the preview mutated the file")
        check("...and says so", "DRY RUN" in out.getvalue())
        # (a) The no-op that reads as success: prove it SEES them.
        check("the preview names every untested row", "2 rated without evidence" in out.getvalue(),
              f"got {out.getvalue()!r}")

        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_unverify(_ap.Namespace(apply=True))
        after = read_json(lex_path)
        check("an unearned 'solid' drops to struggled",
              after["அது"]["recognition"] == "struggled", f"got {after['அது']}")
        check("an unearned 'comfortable' drops too",
              after["இது"]["recognition"] == "struggled", f"got {after['இது']}")
        # (b) The opposite failure — silently wiping ratings that were earned.
        check("a row with reps survives at its rating",
              after["வா"]["recognition"] == "solid", f"got {after['வா']}")
        check("a row that has FIRED survives even with no reps",
              after["போ"]["recognition"] == "comfortable", f"got {after['போ']}")
        check("a hinted row with a rep survives",
              after["வை"]["recognition"] == "solid", f"got {after['வை']}")
        # The signal has to survive its own repair, or the rows stop being findable.
        check("reps is never bumped by the repair",
              all(after[w].get("reps", 0) == lex[w].get("reps", 0) for w in lex),
              f"reps moved: {[(w, after[w].get('reps')) for w in lex]}")
        check("last_surfaced is never stamped by the repair",
              all(after[w].get("last_surfaced") == lex[w].get("last_surfaced") for w in lex),
              f"dates moved: {[(w, after[w].get('last_surfaced')) for w in lex]}")
        check("nothing is added or dropped", sorted(after) == sorted(lex), f"got {sorted(after)}")

        with contextlib.redirect_stdout(out := io.StringIO()):
            ss.cmd_unverify(_ap.Namespace(apply=True))
        check("re-running on repaired data is a no-op",
              read_json(lex_path) == after and "every recognized one has been worked" in out.getvalue(),
              f"got {out.getvalue()!r}")
    finally:
        lex_path.write_bytes(saved)


def s54_no_deadline_reaches_any_surface(sb: Path):
    """The trip was modelled as a terminus, and a terminus has to be maintained
    forever. `TRIP_DATE` had an entry and no exit: `compute_status` counted down
    past zero, and `burn_rate`'s `max(days_left, 1)` clamp froze the required
    pace at its final day's value and reported it forever — on 2026-09-01 the
    scoreboard read "-20 days to touchdown · need 8.0 cold/day", during the month
    in country, which is the era the whole deck existed to serve.

    2026-08-04 answered that with a SECOND era (pre-trip, during-trip). There was
    never a third, so after he flew home the line would have read "in country,
    day 32", then 33, forever — the same defect one era further along.

    2026-08-18 answered it by deletion. The deadline is what expired; a required
    pace with no deadline is not a number, it is a guess; and a winnable countdown
    is the motivational device the 08-17 no-numbers rule banned outright.

    Gate 7.2 — this failure never looked like nothing happening. It printed a
    confident, well-formed, wrong line every day, and it was the line Anna
    narrates from. So the checks are on the SHAPE of what every surface emits, not
    on the absence of one constant: a countdown re-added under another name, or a
    quota composed inline from some other date, must fail here."""
    print("\n54. No deadline reaches any surface (2026-08-18)")
    ss = importlib.import_module("sync_state")
    kr = importlib.import_module("knock_reply")
    sbf = importlib.import_module("session_brief")
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    try:
        # The population the countdown used to hang off: a live set with items
        # still open, which is what put `compute_status` on the deck branch.
        write_json(lex_path, {f"smoke:era{i}": {
            "gloss": "x", "phonetic": [], "type": "chunk", "recognition": "comfortable",
            "production": "cold" if i < 2 else "none", "seen_in": [],
            "last_surfaced": None, "register": "antifreeze"} for i in range(10)})
        lex = read_json(lex_path)

        check("the deadline constant is gone, not merely unused",
              not hasattr(ss, "TRIP_DATE"), "TRIP_DATE survived")
        check("...and so is the meter that was computed against it",
              not hasattr(ss, "compute_deck") and not hasattr(ss, "burn_rate"),
              "compute_deck or burn_rate survived")

        line = ss.compute_status()
        check("the scoreboard still leads with the ear", line.startswith("Machines heard"), line)
        check("no countdown reaches it", "touchdown" not in line and "in country" not in line, line)
        check("no required pace reaches it — a quota needs a terminus",
              "need " not in line, line)
        check("no day count of any spelling reaches it",
              not re.search(r"\bday -?\d|\b-?\d+\s*d(ays)?\b", line), line)

        # The trailing pace is the half that was always true — it measures what
        # happened, not what is owed — so it must survive, and say only that.
        pace = ss.trailing_pace()
        check("the trailing pace survives", "trailing" in pace and "pace" in pace, pace)
        check("...and states no requirement", "need" not in pace, pace)

        # The phone. `catch_meter` was deleted on 08-17 for pushing a fraction and
        # a countdown to the lock screen; the production path kept composing the
        # same thing from `compute_deck` until this retirement.
        score = kr.scoreboard(lex)
        check("the push-back carries no fraction",
              re.search(r"\d+\s*/\s*\d+", score) is None, repr(score))
        check("...and no countdown", "d" != score[-1:] and "touchdown" not in score, repr(score))

        # Every surface, not just the one-liner — a countdown that survived in the
        # dashboard or the session load would still be read aloud.
        import contextlib, io
        sbf.git_sync_counts = lambda: (0, 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sbf.cmd_status(None)
        text = out.getvalue()
        check("the session load names no deadline",
              "touchdown" not in text and "in country" not in text
              and "Trip Deck" not in text, "a deadline survived in session_brief")
    finally:
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


def s46_the_commission_notice_names_the_debt(sb: Path):
    """A live slip pattern with no dose is NAMED at the close (2026-08-01;
    demoted from a refusal 2026-08-20, Andrew).

    The original complaint is real and still the reason this case exists:
    NEVER COMMISSIONED got walked past for mechanical reasons — venum-for-kudunga
    sat 24 days between first slip and first dose while the ticket warned daily
    ("the flag needs teeth", feedback 07-31).

    The 08-01 answer was a hard refusal. It never fired once: `uncommissioned`
    was disarmed the same week by the dose_channel conflation in slips.py, so
    for three weeks this case was green against a gate that could not trip. When
    the detection was repaired on 08-20 the refusal became real for the first
    time, and Andrew ruled it out immediately — commissioning nothing is a
    first-class outcome; a dose is earned by a genuinely recurring pattern or
    something real to teach, never by a counter reaching two.

    Gate 7.2 — the silent no-op here is a notice that never prints, which looks
    exactly like a clean close. So the case asserts the EFFECT in both
    directions: the debt is named in the output, AND the close still applies in
    full (rep, cold, debrief, slip row) — a notice that eats the session would
    be the worse bug. Then each door: the override echoing its reason, a
    commission covering the debt in the same close, and a landed test
    discharging its own tag."""
    print("\n46. The commission notice names the debt (2026-08-01; advisory 2026-08-20)")
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

        # ADVISORY, NOT A GATE (Andrew, 2026-08-20). These two cases used to
        # assert `code == 2` and a byte-identical tree — the close refused, and
        # nothing was written. That contract is retired: commissioning nothing
        # is a first-class outcome, so an uncommissioned debt is NAMED and the
        # close completes. The property worth keeping is that the notice cannot
        # eat the close — a debt must never cost Andrew his debrief.
        code, out = update(produced_cold=["கேட்வேர்ட்"], debrief="a close over a debt")
        check("an uncommissioned debt is named out loud",
              "gate-tag" in out, out[:200])
        check("...and the close still completes — the notice never eats the session",
              code == 0, f"exit {code}")
        check("...and the whole close applied: the rep, the cold, the debrief",
              read_json(lex_path)["கேட்வேர்ட்"]["production"] == "cold"
              and read_json(learner_path).get("last_debrief") == "a close over a debt")

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
        check("a second occurrence landing IN the close is named the same day",
              code == 0 and "gate-tag3" in out, f"exit {code}: {out[:200]}")
        check("...and the slip row it names was still written",
              len(read_json(slip_path)) == n_rows + 1,
              "the notice swallowed the row it was warning about")

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


def s47_hinted_retest_rule(sb: Path):
    """Hinted had no follow-up path ("open and unanswered", DECISIONS 07-28;
    built 2026-08-01). `coverage_key` leads with fewest-reps, so a
    repped-but-stale hinted item sorts behind every never-worked item in its
    tier FOREVER — the three FAQ answers sat hinted 22–28 days silent at 11
    days to touchdown.

    Gate 7.2 — the silent no-op is an empty block reading as "nothing stale",
    so the case asserts presence, ordering, the fresh and ear-only exclusions,
    and that the real ticket entry point surfaces it at all.

    EXTENDED 2026-08-04, after the block spent four weeks working for the wrong
    five items. The 08-01 case asserted ordering at `max_n=100` — where nothing
    can fall off — so it never tested the CUT, which is the only place this can
    fail silently. It still returned five rows and still read as success while
    the deck's three hinted FAQ answers sat below the line behind ordinary
    vocabulary that happened to be staler, and while the top slot went to a
    bootstrap artifact (hinted, zero reps, never surfaced).

    FOLDED IN 2026-08-18. "HINTED, GOING DARK" was its own ticket section — a
    rival pool on a ticket that had nine of them — when it is a RULE
    (`RETEST_DAYS`), not a population. It is now `is_going_dark` plus a
    reservation inside the pool's focus set. The fold-in had to cost nothing:
    every assertion below is the 08-01/08-04 assertion re-aimed at the pool, and
    the cut it survives is now FOCUS_SIZE seats rather than a five-item list. A
    flag on a row nothing selects would have been the same silent no-op in a new
    costume, which is why the reservation exists and why the cut is tested."""
    print("\n47. Hinted items going dark are retested, inside the pool (2026-08-01)")
    import contextlib, io
    st = importlib.import_module("suggest_targets")
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    today = date_cls.today()
    try:
        lex = {}
        mk_day = lambda d: (today - timedelta(days=d)).isoformat()
        dark = lambda d: mk_day(st.RETEST_DAYS + d)
        lex["ரீடெஸ்ட்1"] = {"gloss": "stale hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(6), "reps": 5}
        lex["ரீடெஸ்ட்2"] = {"gloss": "staler hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(16), "reps": 2}
        lex["ரீடெஸ்ட்3"] = {"gloss": "fresh hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(3), "reps": 1}
        lex["ரீடெஸ்ட்4"] = {"gloss": "stale but ear-only", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(16),
                           "direction": "catch", "reps": 0}
        # RANKED rows, deliberately FRESHER than the unranked ones above: only a
        # tier prefix can float them — staleness alone sinks both.
        lex["ரீடெஸ்ட்5"] = {"gloss": "survival, antifreeze", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(2),
                           "reps": 5, "register": "antifreeze"}
        lex["ரீடெஸ்ட்6"] = {"gloss": "survival, public", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(1),
                           "reps": 3, "register": "public"}
        # The bootstrap artifact: a hinted grade with no work behind it. There is
        # no prior test for a RE-test to repeat, and it is already at the head of
        # the pool (coverage_key leads with fewest-reps), so it must not spend a
        # reserved seat here.
        lex["ரீடெஸ்ட்7"] = {"gloss": "hinted, never surfaced", "production": "hinted",
                           "recognition": "struggled", "last_surfaced": None, "reps": 0}

        # --- the RULE, on its own ---
        def gd(w):
            r = lex[w]
            return st.is_going_dark(r, st.days_since(r["last_surfaced"], today))

        check("a hinted item silent past RETEST_DAYS is going dark", gd("ரீடெஸ்ட்1"))
        check("a recently-worked hinted item is not", not gd("ரீடெஸ்ட்3"))
        check("ear-only items are excluded — a retest is a production move",
              not gd("ரீடெஸ்ட்4"))
        check("a hinted grade with no work behind it is excluded — nothing to re-test",
              not gd("ரீடெஸ்ட்7"))
        check("the boundary is the constant, not a literal",
              not st.is_going_dark({"production": "hinted"}, st.RETEST_DAYS - 1)
              and st.is_going_dark({"production": "hinted"}, st.RETEST_DAYS))

        # --- the RULE, reaching the pool ---
        write_json(lex_path, lex)
        focus, _bg = st.floor_gap_targets(lex, today, st.FOCUS_SIZE, asked={}, cohort=[])
        words = [t["word"] for t in focus if t["retest"]]
        check("the dark rows reach the pool and are flagged there",
              set(words) == {"ரீடெஸ்ட்1", "ரீடெஸ்ட்2", "ரீடெஸ்ட்5", "ரீடெஸ்ட்6"},
              f"got {words}")
        check("...most-stale first within a tier",
              words.index("ரீடெஸ்ட்2") < words.index("ரீடெஸ்ட்1"), f"got {words}")
        check("the never-surfaced bootstrap row is never flagged for retest",
              not any(t["retest"] for t in focus if t["word"] == "ரீடெஸ்ட்7"),
              f"got {focus}")

        # THE 2026-08-04 defect, re-aimed. A staleness-only sort passes every
        # check above and fails both of these: the ranked rows are the two
        # FRESHEST candidates and must still lead on the tier prefix alone.
        check("the ranked items lead, even when unranked rows are staler",
              words[:2] == ["ரீடெஸ்ட்6", "ரீடெஸ்ட்5"], f"got {words}")
        # THE RESERVATION, on the only fixture that can test it. The two ranked
        # rows above win seats on the tier prefix alone, so they prove ordering,
        # not reachability. Drop them and the survivors are UNRANKED, repped and
        # stale — precisely the shape `coverage_key` buries behind every
        # never-worked row forever, and precisely the incident: the FAQ answers
        # sat 22-28 days silent while the ticket kept offering fresh ground.
        crowd = {w: r for w, r in lex.items() if w not in ("ரீடெஸ்ட்5", "ரீடெஸ்ட்6")}
        crowd.update({f"smoke:crowd{i}": {"gloss": "never worked", "production": "none",
                                          "recognition": "comfortable",
                                          "last_surfaced": None, "reps": 0}
                      for i in range(40)})
        # A held cohort, so this runs the LIVE path (a stored membership) rather
        # than the day-zero seed derivation, which fills from reps and would let
        # a repped row in through a door the reservation is not being asked about.
        held = ["smoke:crowd0"]
        focus, _bg = st.floor_gap_targets(crowd, today, st.FOCUS_SIZE, asked={}, cohort=held)
        cut = [t["word"] for t in focus if t["retest"]]
        check("a dark row survives a wall of never-worked rows — reachability is "
              "the whole reason this was ever a block",
              "ரீடெஸ்ட்2" in cut, f"got {cut} of {[t['word'] for t in focus]}")
        check("...staler first among them", cut[:1] == ["ரீடெஸ்ட்2"], f"got {cut}")
        # A FLOOR, NEVER A CEILING: no dark row wins a seat on the ordering in
        # this fixture (reps 2 and 5 against forty at zero), so anything above
        # the reservation would be the retest rule flooding the set — which is
        # how it earned its own section, and its own primacy, the first time.
        check("...and the reservation tops up without taking over",
              0 < len(cut) <= st.RETEST_SLOTS, f"{len(cut)} of {len(focus)} seats: {cut}")

        out, real_argv = io.StringIO(), sys.argv
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = real_argv
        text = out.getvalue()
        check("the ticket marks the going-dark rows — the rule is only worth "
              "having if the entry point says so", "GOING DARK" in text, text[-800:])
        check("...and it is no longer a rival section with its own headline",
              "★ HINTED, GOING DARK" not in text, "the block survived the fold-in")
    finally:
        lex_path.write_bytes(saved)


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

        # ── A BROKEN SIDECAR IS NOT A MISSING ONE (2026-08-24) ──────────────
        # The block above proves an UNRESOLVABLE key is reported. This proves the
        # worse case one level up: a sidecar that exists and cannot be PARSED.
        # It used to be `except (json.JSONDecodeError, OSError): pass`, and the
        # code then fell through to scraping `**bold**` tokens out of the
        # markdown — which is not where an episode's vocab is written. The result
        # was a PLAUSIBLE word list from the wrong source: episodes.json and every
        # row's `seen_in` crediting words the episode never taught, the render
        # succeeding, and every instrument green.
        #
        # THE SILENT NO-OP, stated: a swallowed parse error and a sidecar with no
        # callbacks look identical from outside. So this asserts the two things
        # that tell them apart — the failure is NAMED, and the wrong-source
        # fallback does NOT run. Under-claiming is the ledger's own law
        # (claim_payload, 2026-07-17); inventing is the defect.
        bold = "ஸ்மோக்பொல்ட்"
        script.write_text(f"# Tier 2, Mission 97 — Smoke\n\n**{bold}** is bold.\n",
                          encoding="utf-8")
        (script.with_suffix(".tags.json")).write_text("{ this is not json",
                                                      encoding="utf-8")
        eps_path = sb / "progress" / "episodes.json"
        write_json(eps_path, {})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ra.register_mission_in_state(script, sb / "published_audio" / "tier2_mission97.mp3")
        text = out.getvalue()
        check("an UNREADABLE sidecar is reported, not swallowed",
              "COULD NOT BE READ" in text, f"got {text[:300]!r}")
        check("...naming the file and the parse error",
              "tier2_mission97.tags.json" in text and "JSONDecodeError" in text,
              f"got {text[:300]!r}")
        check("...and saying what to do about it",
              "Fix the sidecar" in text, f"got {text[:300]!r}")
        words = (read_json(eps_path).get("97") or {}).get("words", [])
        check("...and the bold-scrape fallback does NOT run — a plausible word "
              "list from the wrong source is worse than none",
              bold not in words, f"the scrape credited {words}")
        check("...so the episode under-claims rather than invents", words == [],
              f"got {words}")

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

    src = mechanism(inspect.getsource(ra.main))
    check("the standalone renderer loads .env, like run_studio does before it",
          "load_env" in src, "a hand-run render still cannot find GCP_SA_KEY")


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
    spec = importlib.util.spec_from_file_location(
        "pb_live2", str(Path(mk.__file__).parent / "publish.py"))
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
        return sp.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8")

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
    # An equality check with no detail tells you nothing on the day it breaks —
    # this one read as a content bug for hours and was a newline translation
    # (Windows write_text emits CRLF; git show hands back LF). Say which.
    expected = (runner / "progress" / "chat_expected.md").read_text(encoding="utf-8")
    why = ""
    if chat != expected:
        if chat.replace("\r\n", "\n") == expected.replace("\r\n", "\n"):
            why = "line endings differ, not content"
        else:
            i = next((n for n, (a, b) in enumerate(zip(chat, expected)) if a != b),
                     min(len(chat), len(expected)))
            why = (f"content differs at char {i}: on main {chat[i:i+40]!r} · "
                   f"fresh render {expected[i:i+40]!r}")
    check("chat.md on main == a fresh render of the merged log", chat == expected, why)
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
        fx.pb.refresh_feed = lambda: None
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
        src = mechanism((REAL_BASE / "scripts" / "knock_reply.py")
                        .read_text(encoding="utf-8"))
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
    fx.wr.rephrase_phonetic = lambda b: (seen.append(b), "romba nallarukku — the melt line")[1]
    out = mk.to_phonetic("ரொம்ப நல்லாருக்கு — the melt line")
    check("script goes to the composer, which keeps his contraction",
          out == "romba nallarukku — the melt line" and "nalla irukku" not in out, out)
    check("...and it was handed the original line", seen == ["ரொம்ப நல்லாருக்கு — the melt line"])

    seen.clear()
    clean = "romba nallarukku — say it"
    check("a body with no Tamil never calls the model at all",
          mk.to_phonetic(clean) == clean and not seen)

    fx.wr.rephrase_phonetic = lambda b: b          # composer ignores the ask
    check("a surviving leak warns and SHIPS — a lost dose costs him more",
          mk.to_phonetic("try கிடைக்கும் today") == "try கிடைக்கும் today")

    # End to end: what he was sent is what got logged.
    klog_path = sb / "progress" / "knock_log.json"
    pushes = Recorder()
    mk.push_to_phone, mk.commit_and_push = pushes, Recorder()
    fx.wr.rephrase_phonetic = lambda b: "today's line — romba nallarukku"
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
    fx.pb.refresh_feed = lambda: None
    try:
        # `--force` states this case's precondition instead of inheriting it.
        # Until 2026-08-24 this line read `["morning_knock.py"]` and the run only
        # reached `decide` because `s3`, forty cases earlier, had stubbed
        # `rails_gate` out and never put it back. The dependency was invisible and
        # positional: reorder the suite and this case silently stops testing the
        # transform at all. What it is actually about is the BODY, not the gate.
        sys.argv = ["morning_knock.py", "--force"]
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
                           mechanism((REAL_BASE / "scripts" / f)
                                     .read_text(encoding="utf-8")), re.S)
        check(f"{f}: only read surfaces are transformed",
              calls and all("memo_script" not in c and "voice_reply" not in c for c in calls),
              str(calls))


DEBT_CEILING_NO_PHONETIC = 96


def s71_a_new_record_is_born_reachable(sb: Path):
    """A minted record must carry its sounds-like form (2026-08-14, Andrew).

    Found live at a session close: `--produced-hinted ukkarunga` bounced, so did
    `ukkaarunga`, and the rep only landed by falling back to Tamil script through
    a UTF-8 shell. `resolve()` is exact-match against each record's `phonetic`
    list, and three mint sites wrote `[]` under a "backfill later" note — 96 of
    313 word records had none by that day, 88 of them `production: none`, and 5
    of the 12 items on that session's own focus set were unloggable phonetically.
    The ticket was naming targets the logger would refuse.

    Gate 7.2 — a guard that never fires looks exactly like a clean close, and a
    guard that fires but stores nothing useful looks exactly like a fixed bug. So
    this asserts the EFFECT in the dimension that actually failed: not "the mint
    was refused" alone, but that a word taught WITH its phonetic can afterwards be
    logged BY that phonetic, round-tripped through the real command and re-read
    from disk. That round trip is the whole purpose; everything else is ceremony.

    The ratchet is the second half of Andrew's call: `render_audio` mints records
    unattended and cannot be blocked without killing renders, so the debt is
    capped instead. Existing records are grandfathered — no backfill, by his
    decision. The number may only ever fall; lower it when a tranche is vetted."""
    print("\n71. A new record is born reachable (2026-08-14)")
    import argparse as _ap
    import contextlib
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    slip_path = sb / "progress" / "slip_log.json"
    saved = (lex_path.read_bytes(),
             slip_path.read_bytes() if slip_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None,
                    soak_focus=None, soak_channel=None, soak_form=None,
                    mastered_word=[], comfortable_word=[], stuck_word=[],
                    produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[], no_commission=None, quiet_until=None)

    def update(**kw):
        out, code = io.StringIO(), 0
        try:
            with contextlib.redirect_stdout(out):
                ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        except SystemExit as e:
            code = e.code
        return code, out.getvalue()

    try:
        # An empty ledger so the commission gate can't refuse these closes for
        # reasons of its own (s46 owns that behaviour).
        slip_path.write_text("[]", encoding="utf-8")

        # 1. The refusal — teaching without a phonetic must NOT mint a record.
        word = "ஸ்மோக்வார்த்தை"
        _, out = update(teach=[f"{word}=smoke word"])
        check("teach without a phonetic is refused, naming the word",
              word in out and "Skipped" in out, out.strip()[-160:])
        check("...and nothing was written for it",
              word not in read_json(lex_path),
              "a record was minted anyway — the guard is decorative")

        # 2. The same refusal on the recognition mint path.
        _, out = update(comfortable_word=[word])
        check("--comfortable-word without a phonetic is refused too",
              word not in read_json(lex_path), "recognition path still mints holes")

        # 3. The legal door — taught WITH its sounds-like form.
        _, _ = update(teach=[f"{word}=smoke word|smokevaarthai"])
        rec = read_json(lex_path).get(word)
        check("teach with a phonetic mints the record",
              rec is not None, "the legal form was refused as well")
        check("...and the phonetic is stored on it",
              bool(rec) and rec.get("phonetic") == ["smokevaarthai"],
              f"phonetic={rec.get('phonetic') if rec else None}")

        # 4. THE POINT — round-trip: the word is now loggable BY its phonetic,
        #    which is the exact operation that failed live.
        _, out = update(produced_cold=["smokevaarthai"])
        check("the phonetic now resolves for a later production log",
              read_json(lex_path)[word].get("production") == "cold",
              f"still unreachable from phonetics: {out.strip()[-160:]}")

        # 5. The ratchet — real tree, not the sandbox: the debt binds the
        #    lexicon as committed. Frames are exempt (addressed by `frame:` key).
        real_lex = read_json(REAL_BASE / "progress" / "lexicon.json") or {}
        debt = sum(1 for k, v in real_lex.items()
                   if not k.startswith("frame:") and not v.get("phonetic"))
        check(f"records with no phonetic: {debt}/{DEBT_CEILING_NO_PHONETIC}",
              debt <= DEBT_CEILING_NO_PHONETIC,
              f"{debt - DEBT_CEILING_NO_PHONETIC} new unreachable record(s) — give "
              f"them a phonetic, or lower the ceiling in this same diff if you "
              f"vetted a tranche. It may never be raised.")
    finally:
        lex_path.write_bytes(saved[0])
        if saved[1] is not None:
            slip_path.write_bytes(saved[1])


def s60_the_ear_meter(kr, sb: Path):
    """Machines heard — the recognition axis gets a meter (2026-08-16, Andrew).

    The pivot: "we stop counting what comes out of your mouth and start counting
    what you can hear." The evidence that earned it is in his own lexicon — of 26
    frames he PRODUCES 20 cold and RECOGNISES only 3 as solid, so ten machines he
    can fire unaided still go past him unheard in a fast sentence. That is why two
    content words in native-speed gossip felt like nothing: the tails carry the
    skeleton, and the skeleton was inaudible. Meanwhile the status line reported
    "Engines online: 19/21 (90%)" — a PRODUCTION number, read for a year as though
    it were mastery.

    Nothing new scores this. `apply_catch_verdict` already walks the ladder one
    rung per catch (struggled → comfortable → solid, upgrades only, s6 proves it)
    and `resolve()` already returns `frame:` keys unchanged — 20 eavesdrop knocks
    have targeted frames. The whole defect was that the number was never PRINTED.

    Gate 7.2 — what does this look like when it silently does nothing? It prints
    a plausible fraction that never moves, which is indistinguishable from Andrew
    not improving, and it is the headline, so nobody would question it. Two ways
    to be silently wrong, and a check for each:

      1. The DENOMINATOR quietly shrinks. Reusing the Engines filter would drop
         `direction: catch` patterns and report 3/21 — still plausible, wrong set,
         and it would hide precisely the ear-only machines this meter exists for.
      2. The NUMERATOR cannot move. If a catch could not reach a `frame:` key the
         count would freeze at its birth value forever.

    So this asserts the effect in the dimension that can actually fail: the ear-only
    pattern is inside the denominator, `comfortable` does NOT count as heard, and a
    real catch driven through `knock_reply.main()` moves the number the render
    prints — round-tripped through the writer and re-read off the status surface,
    never off the function that computes it."""
    print("\n60. Machines heard — the ear meter (2026-08-16)")
    import contextlib
    sbf = importlib.import_module("session_brief")
    lex_path = sb / "progress" / "lexicon.json"
    klog_path = sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())

    def status() -> str:
        sbf.git_sync_counts = lambda: (0, 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sbf.cmd_status(None)
        return out.getvalue()

    def meter(text: str) -> str:
        for line in text.splitlines():
            if line.startswith("Machines heard:"):
                return line
        return ""

    ear = "frame:ear-only"
    write_json(lex_path, {
        # fires cold, still deaf — in BOTH denominators
        "frame:fire-only": {"gloss": "-om", "phonetic": ["om"], "type": "pattern",
                            "recognition": "struggled", "production": "cold", "seen_in": []},
        # ear-only: Engines excludes it by design, this meter must not
        ear: {"gloss": "-aam hearsay", "phonetic": ["aam"], "type": "pattern",
              "direction": "catch", "recognition": "comfortable", "production": "none",
              "seen_in": [], "last_surfaced": "2026-07-01"},
        # the one already heard
        "frame:heard": {"gloss": "-nu quotative", "phonetic": ["nu"], "type": "pattern",
                        "recognition": "solid", "production": "none", "seen_in": []},
        # a WORD at solid — must not touch a pattern meter
        "வணக்கம்": {"gloss": "hello", "phonetic": ["vanakkam"], "type": "chunk",
                    "recognition": "solid", "production": "cold", "seen_in": []},
    })

    line = meter(status())
    check("the ear meter is printed at all", line != "", "no 'Machines heard:' line in status")
    check("ear-only patterns are INSIDE the denominator (3, not 2)",
          "1/3" in line, line)
    check("comfortable is not heard — only solid counts", line.startswith("Machines heard: 1/"), line)
    check("it is labelled the primary steer", "PRIMARY STEER" in line, line)
    check("the deck no longer claims the headline",
          "sprint headline" not in status())

    # The one-line scoreboard is the surface Anna narrates from and the digest
    # carries to the phone — a meter that moved only in the long status block
    # would leave every OTHER channel still reciting production at him.
    #
    # There used to be TWO branches here, and this case asserted the ear led both
    # — the deck one for the trip, the floor one for the era after it. The deck
    # branch retired on 2026-08-18 and the horizon it left open is now the only
    # era there is, so the assertion is that ONE line leads with the ear no
    # matter what the lexicon carries. A second branch reappearing behind some
    # other tag is the regression; `s54` guards the deadline half of it.
    ss = importlib.import_module("sync_state")
    check("the scoreboard line LEADS with the ear",
          ss.compute_status().startswith("Machines heard 1/3 · viability floor"),
          ss.compute_status())
    lex = read_json(lex_path)
    lex["வணக்கம்"]["register"] = "antifreeze"
    write_json(lex_path, lex)
    check("...and a ranked row does not buy itself a rival headline",
          ss.compute_status().startswith("Machines heard 1/3 · viability floor"),
          ss.compute_status())

    # --- the round trip: a real catch on a FRAME must move the printed number ---
    kr.push_to_phone, kr.commit_and_push = Recorder(), Recorder()
    kr.judge_catch = lambda k, r, *a, **kw: {"verdict": "caught", "reply_line": "adhu dhaan 🎧",
                                             "meta_note": "", "rationale": "smoke"}
    now = datetime.now(timezone.utc)
    log = read_json(klog_path)
    log.append({"date": now.date().isoformat(), "timestamp": now.isoformat(),
                "acted": True, "modality": "eavesdrop", "move": "gossip tape",
                "body": "who's the news about?", "memo_script": "அவங்க பொண்ணு-ஆம்!",
                "expected_target": ear, "target_revealed": False})
    write_json(klog_path, log)
    sys.argv = ["knock_reply.py", "someone said her daughter — I heard it, not saw it"]
    kr.main()

    check("a catch on a frame reaches solid",
          read_json(lex_path)[ear]["recognition"] == "solid")
    check("and the METER the session reads has moved 1/3 → 2/3",
          "2/3" in meter(status()), meter(status()))

    write_json(lex_path, json.loads(saved[0].decode("utf-8")))
    write_json(klog_path, json.loads(saved[1].decode("utf-8")))


def s61_no_number_is_recited_at_him(kr, sb: Path):
    """Meters steer Python; they are never read aloud (2026-08-17, Andrew).

    Achievement-goal framing is the mechanism here, not taste. Andrew is
    mastery-driven by his own account — every surge he has had came from an
    insight or a new capability, never from hitting a number — and a performance
    scoreboard attached to a learner like that predicts withdrawal exactly when
    progress is slow. That is the 08-16 signal in one sentence ("a handful of
    marbles against a swimming pool"), and the instrumentation was manufacturing
    part of it. The 07-17 law already said a global deficit recited in a warm
    voice is guilt machinery; it guarded ONE line while `catch_meter` was pushing
    "Catch 3/12 · 12d" to his lock screen after every eavesdrop reply — a fraction
    and a countdown, on the surface he cannot look away from.

    Gate 7.2 — the silent no-op: a meter tail is one ` · ` join, so a re-add would
    look like an ordinary formatting change and nothing would fail. The assertion
    is therefore on the SHAPE of what reaches the phone, not on the absence of one
    function: no `n/m` may appear in a pushed body, whatever composes it."""
    print("\n61. No number is recited at him (2026-08-17)")
    lex_path = sb / "progress" / "lexicon.json"
    klog_path = sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())

    check("catch_meter is gone, not merely unused", not hasattr(kr, "catch_meter"))
    persona = (REAL_BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    check("persona.md forbids reciting a number",
          "recites a number at him" in persona and "countdown" in persona)
    brief = mechanism((REAL_BASE / "scripts" / "session_brief.py")
                      .read_text(encoding="utf-8"))
    check("the meter block is labelled steering data, not narration",
          "ENGINEERING NUMBERS" in brief)

    # The real push path, driven end to end: a catch reply must reach the phone
    # carrying the reply line and nothing else.
    w = "frame:smoke-ear"
    write_json(lex_path, {w: {"gloss": "-aam", "phonetic": ["aam"], "type": "pattern",
                              "deck": "trip", "direction": "catch", "recognition": "struggled",
                              "production": "none", "seen_in": [], "last_surfaced": "2026-07-01"}})
    pushed = Recorder()
    kr.push_to_phone, kr.commit_and_push = pushed, Recorder()
    kr.judge_catch = lambda k, r, *a, **kw: {"verdict": "caught", "reply_line": "adhu dhaan 🎧",
                                             "meta_note": "", "rationale": "smoke"}
    now = datetime.now(timezone.utc)
    log = read_json(klog_path)
    log.append({"date": now.date().isoformat(), "timestamp": now.isoformat(),
                "acted": True, "modality": "eavesdrop", "move": "gossip tape",
                "body": "who's the news about?", "memo_script": "அவங்க பொண்ணு-ஆம்!",
                "expected_target": w, "target_revealed": False})
    write_json(klog_path, log)
    sys.argv = ["knock_reply.py", "someone said her daughter"]
    kr.main()

    body = str(pushed[-1][0]) if pushed else ""  # Recorder is a list of arg tuples
    check("the pushed body is the reply line alone", body == "adhu dhaan 🎧", repr(body))
    check("no fraction reached the phone", re.search(r"\d+\s*/\s*\d+", body) is None, repr(body))

    write_json(lex_path, json.loads(saved[0].decode("utf-8")))
    write_json(klog_path, json.loads(saved[1].decode("utf-8")))


def s62_the_return_clock_is_keyed_to_the_ear(sb: Path):
    """Decayed items come back, and due-ness reads the recognition axis (2026-08-17).

    The spacing effect is the shape memory has, not a technique, and the system
    had a real spaced-repetition selector all along — `generate_callbacks.py`,
    intervals on `last_surfaced`. Two exclusions gutted it for the ear: patterns
    were skipped ("tracked engines, not soak words") and struggled rows were
    skipped ("repeated audio exposure doesn't fix cold-production gaps"). Both
    were right for a production headline. Both removed precisely the inventory a
    recognition headline lives on — the 26 machines, and the 144 struggled rows
    that are the cheapest material in the ledger to recover.

    Gate 7.2 — the silent no-op is severe here and reads as good news: a clock
    that selects nothing prints "(nothing due — the recognized set is fresh)",
    which looks like a healthy ledger rather than a dead selector. So the checks
    assert that specific rows COME BACK, and that due-ness moves when the
    recognition axis moves and not when production does."""
    print("\n62. The return clock is keyed to the ear (2026-08-17)")
    gc = importlib.import_module("generate_callbacks")
    today = date_cls(2026, 8, 17)
    row = lambda **kw: {"gloss": "g", "phonetic": ["p"], "seen_in": [], **kw}
    lex = {
        # struggled pattern, 6 days stale — the exact row both old rules dropped
        "frame:struggled": row(type="pattern", recognition="struggled",
                               production="cold", last_surfaced="2026-08-11"),
        # solid, same staleness — retained, not yet due at 21 days
        "solid-fresh": row(recognition="solid", production="cold",
                           last_surfaced="2026-08-11"),
        # comfortable at 12 days — past its 10-day interval
        "comfortable-due": row(recognition="comfortable", production="none",
                               last_surfaced="2026-08-05"),
    }
    due = {c["word"]: c for c in gc.due_callbacks(lex, today, 10)}

    check("a struggled PATTERN is due — both old exclusions lifted",
          "frame:struggled" in due, str(sorted(due)))
    check("a solid row at 6 days is NOT due (21-day interval)",
          "solid-fresh" not in due, str(sorted(due)))
    check("a comfortable row at 12 days IS due (10-day interval)",
          "comfortable-due" in due, str(sorted(due)))
    # Overdue-ness leads the sort; RECOGNITION_RANK only breaks ties. Equal
    # overdue (both 1 day past their own interval) is where it shows.
    tie = {"a-solid": row(recognition="solid", production="cold", last_surfaced="2026-07-26"),
           "b-struggled": row(recognition="struggled", production="cold", last_surfaced="2026-08-11")}
    order = [c["word"] for c in gc.due_callbacks(tie, today, 10)]
    check("on equal overdue the weaker trace comes back first",
          order[0] == "b-struggled", str(order))

    # Due-ness must follow the EAR. Flipping production alone changes nothing;
    # flipping recognition to solid must retire the row from today's list.
    lex["frame:struggled"]["production"] = "none"
    check("production no longer drives due-ness",
          "frame:struggled" in {c["word"] for c in gc.due_callbacks(lex, today, 10)})
    lex["frame:struggled"]["recognition"] = "solid"
    check("...and recognition does",
          "frame:struggled" not in {c["word"] for c in gc.due_callbacks(lex, today, 10)})

    # The failure the green suite missed: with the sentinel in play, EVERY slot
    # on the live ticket read "(last: never surfaced)" — the clock had never
    # returned a single decayed row, and it looked like a working selector
    # because it was producing output. A return clock returns what was met.
    lex["never-worked"] = row(recognition="struggled", production="none")
    picked = [c["word"] for c in gc.due_callbacks(lex, today, 10)]
    check("a never-surfaced row is not 'due' — it is new ground, not decay",
          "never-worked" not in picked, str(picked))
    check("...and the decayed rows still come back",
          "comfortable-due" in picked, str(picked))


def s63_the_machines_reach_the_ticket():
    """Patterns are reachable, not merely eligible (2026-08-17).

    Letting patterns into the pool (s62) made them ELIGIBLE. It did not make them
    REACHABLE: on the live ledger 100 rows came back due, the first pattern sat at
    rank 59, and the five-slot ticket therefore returned words only. The 26
    machines — the set the comprehension threshold rides on, since the tails carry
    the sentence skeleton — had a return path in principle and none in fact. Words
    outnumber patterns ~12:1 and decay on the same clock, so the majority pool
    takes every seat on staleness alone, forever.

    Gate 7.2 — what does this look like when it silently does nothing? A ticket of
    five genuinely-overdue words, which is indistinguishable from a healthy
    selection: nothing errors, every row is real and really due, and the absence of
    a machine is invisible unless something asserts it. That is exactly how the
    original defect survived a green suite — s62 proved eligibility against a
    three-row lexicon, a shape in which the bug cannot appear.

    So this reproduces the LIVE shape — many ancient words against a few
    less-ancient patterns — and asserts the machines are on the ticket anyway,
    that the reservation is a floor and never a ceiling, and that it can never
    grow to starve the words."""
    print("\n63. The machines reach the ticket (2026-08-17)")
    gc = importlib.import_module("generate_callbacks")
    today = date_cls(2026, 8, 17)
    row = lambda **kw: {"gloss": "g", "phonetic": ["p"], "seen_in": [], **kw}
    # The live distribution: words far more overdue than any pattern.
    lex = {f"word{i}": row(recognition="struggled", production="cold",
                           last_surfaced="2026-06-24") for i in range(40)}
    lex.update({f"frame:m{i}": row(type="pattern", recognition="struggled",
                                   production="cold", last_surfaced="2026-08-05")
                for i in range(3)})

    picked = gc.due_callbacks(lex, today, 5)
    pats = [c for c in picked if c["pattern"]]
    check("the ticket is still full", len(picked) == 5, str(len(picked)))
    check("machines are on it despite losing on staleness",
          len(pats) == gc.PATTERN_SLOTS, f"{len(pats)} of {[c['word'] for c in picked]}")
    check("...and the words keep the majority of the seats",
          len(picked) - len(pats) == 3, str(len(picked) - len(pats)))

    # A FLOOR, NOT A CEILING: when patterns are the most decayed rows in the
    # ledger, the reservation must not cap them back down to two.
    flip = {f"word{i}": row(recognition="struggled", production="cold",
                            last_surfaced="2026-08-05") for i in range(40)}
    flip.update({f"frame:m{i}": row(type="pattern", recognition="struggled",
                                    production="cold", last_surfaced="2026-06-24")
                 for i in range(4)})
    won = [c for c in gc.due_callbacks(flip, today, 5) if c["pattern"]]
    check("machines that win on merit are not capped at the reservation",
          len(won) == 4, f"{len(won)} patterns won seats")

    # The reservation may never take the whole ticket.
    one = gc.due_callbacks(lex, today, 1)
    check("a single-slot ticket is not handed to the reservation",
          not one[0]["pattern"], one[0]["word"])
    check("half is the hard cap on a two-slot ticket",
          sum(1 for c in gc.due_callbacks(lex, today, 2) if c["pattern"]) == 1)

    # And the pool is unchanged — no pattern arrives that was never met.
    lex["frame:unmet"] = row(type="pattern", recognition="struggled", production="none")
    check("the reservation cannot smuggle in a never-surfaced row",
          "frame:unmet" not in {c["word"] for c in gc.due_callbacks(lex, today, 5)})


def s64_the_ask_cooldown_covers_the_session_lane(sb: Path):
    """One item, six surfaces, four move names (2026-08-18, Andrew).

    `இன்னொரு தடவ சொல்லுங்க` was pushed on 08-09 (fielding), 08-12 (volley 3/4),
    08-15 (slip medicine + soak order + campaign mission) and 08-16 (challenge)
    until Andrew asked why he was being taught the same line for a week. Two
    independent holes, both closed here:

      1. THE WINDOW WAS SHORTER THAN HIS REPLY LATENCY. Gaps of exactly 3 and 4
         days against a 3-day cooldown, so every re-ask landed just outside it.
         He answered 4 of 14 knocks that week — a guard that expires in 3 days
         cannot hold an item that takes 4-7 to get answered.
      2. THE SESSION LANE COULD NOT SEE THE COOLDOWN AT ALL. The knock menu
         warns the knock decider, but the soak order, the campaign mission and
         the slip medicine are written by Anna off `session_brief`, which never
         imported the selector. Three of the six surfaces came from there.

    This is KF-6 returning through the door KF-6 left open: its fix counted asks
    for the deck menu and assumed one menu.

    Gate 7.2 — the silent no-op: a cooldown that suppresses nothing renders as a
    perfectly healthy ticket. Every row is real, every row is genuinely due, and
    the only evidence of failure is a repeat a week later that no instrument
    reports. So the assertions are on the EFFECT at both surfaces — the count
    itself, and the text the session surface actually prints, re-read off
    `cmd_status` rather than off the function that computes it."""
    print("\n64. The ask cooldown covers the session lane (2026-08-18)")
    import contextlib
    st = importlib.import_module("suggest_targets")
    sbf = importlib.import_module("session_brief")
    lex_path, klog_path = sb / "progress" / "lexicon.json", sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())
    now = datetime.now(timezone.utc)
    ago = lambda d: (now - timedelta(days=d)).isoformat()
    w, other = "இன்னொரு தடவ சொல்லுங்க", "smoke:answered"

    check("the window exceeds the observed reply latency (4-7d)",
          st.ASK_COOLDOWN_DAYS >= 7, f"got {st.ASK_COOLDOWN_DAYS}")

    write_json(lex_path, {
        w: {"gloss": "say it once more", "phonetic": ["innoru thadava sollunga"],
            "type": "chunk", "recognition": "struggled", "production": "hinted",
            "deck": "trip", "direction": "fire", "seen_in": []},
        other: {"gloss": "x", "phonetic": ["x"], "type": "chunk", "recognition": "struggled",
                "production": "hinted", "seen_in": []},
        # `recent_ask_counts` walks the LEXICON and probes the log, so a filler
        # target with no row is invisible to it. Distinct phonetics, and bodies
        # below that share no token with them — otherwise a probe matches another
        # row's body and the counts stop meaning what the assertions say.
        "smoke:once": {"gloss": "asked once", "phonetic": ["onlyoncehere"],
                       "type": "chunk", "recognition": "struggled",
                       "production": "hinted", "seen_in": []},
        **{f"smoke:filler{i}": {"gloss": "f", "phonetic": [f"fillerword{i}"],
                               "type": "chunk", "recognition": "struggled",
                               "production": "hinted", "seen_in": []}
           for i in range(9)},
    })
    # The real sequence: gaps of 3 then 4 days, none answered.
    klog = [{"acted": True, "timestamp": ago(6), "modality": "fielding",
             "move": "fielding: innoru thada", "expected_target": w, "body": "answer her"},
            {"acted": True, "timestamp": ago(3), "modality": "volley",
             "move": "volley: sprint burn 3/4", "expected_target": w, "body": "ask her again"},
            # answered, and inside the window — must NOT be marked unanswered.
            # TWICE, because one mention is below `ASK_REPEAT_FLOOR` and the block
            # is a repeat-detector: a single ask is the case it exists to permit.
            {"acted": True, "timestamp": ago(4), "modality": "text", "move": "collect",
             "expected_target": other, "body": "x", "reply": "aama", "reply_verdict": "cold"},
            {"acted": True, "timestamp": ago(3), "modality": "text", "move": "collect",
             "expected_target": other, "body": "x", "reply": "seri", "reply_verdict": "cold"},
            {"acted": True, "timestamp": ago(2), "modality": "text", "move": "collect",
             "expected_target": other, "body": "x", "reply": "sari", "reply_verdict": "cold"},
            # The third surface, and the one that named the session lane: the
            # 08-15 soak order PRINTED the item as prose rather than targeting
            # it, which `recent_ask_counts` catches through the body probe. Kept
            # outside 3 days like the other two — the retired guard has to see
            # NOTHING here, which is the reproduction this case is built on.
            {"acted": True, "timestamp": ago(5), "modality": "text", "move": "soak order",
             "expected_target": "", "body": f"today we soak {w}"},
            {"acted": True, "timestamp": ago(2), "modality": "text", "move": "one-off",
             "expected_target": "smoke:once", "body": "situation only"},
            # long past the window — must age out entirely
            {"acted": True, "timestamp": ago(30), "modality": "text", "move": "old",
             "expected_target": "smoke:ancient", "body": "x"}]
    # Enough repeats to make the CAP bind. Without these the fixture has two
    # qualifying rows and a cap of 99 would pass the assertion below — a guard
    # that cannot fail is the thing this whole case exists to argue against.
    ASK_FILLER = 9
    for i in range(ASK_FILLER):
        for d in (5, 3):
            klog.append({"acted": True, "timestamp": ago(d), "modality": "text",
                         "move": f"filler {i}", "expected_target": f"smoke:filler{i}",
                         "body": "situation only"})
    write_json(klog_path, klog)

    lex_now = read_json(lex_path)
    # THE DELTA IS THE PROOF, not an absolute count: under the retired 3-day
    # guard this exact sequence was invisible, which is why it fired three times.
    old = st.recent_ask_counts(klog, lex_now, days=3)
    asked = st.recent_ask_counts(klog, lex_now)
    check("the retired 3-day guard saw NOTHING here — this is the bug, reproduced",
          not old.get(w), f"got {old}")
    check("the widened window catches both re-asks and the prose mention",
          asked.get(w) == 3, f"got {asked}")
    check("an ANSWERED repeat outranks unanswered ties only on count, not on being read",
          asked.get(other) == 3, f"got {asked}")
    check("an ask well outside the window still ages out",
          "smoke:ancient" not in asked, f"got {asked}")

    sbf.git_sync_counts = lambda: (0, 0)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sbf.cmd_status(None)
    text = out.getvalue()

    check("the session surface prints the cooldown at all", "ALREADY ASKED" in text)
    check("...and names the over-asked item", w in text.split("ALREADY ASKED")[1][:400])
    check("an unanswered ask is called out — silence must not read as a reason to re-ask",
          "UNANSWERED" in text.split("ALREADY ASKED")[1][:400])
    body = [ln for ln in text.splitlines() if ln.strip().startswith(f"- {other}")]
    check("an ANSWERED ask is listed without the unanswered warning",
          body and "UNANSWERED" not in body[0], f"got {body}")

    # THE BLOCK IS BOUNDED (2026-08-18, Andrew, hours after the block shipped).
    # The first cut printed every row in the window — 50 on live state, 27 of
    # them single mentions — so the 6× and 5× rows that caused the incident sat
    # at the top of a wall. A guard nobody reads guards nothing, which is the
    # same silent-no-op family one layer up: the mechanism fires, the human
    # doesn't. Both terms are asserted because both can rot quietly — a cap that
    # stops capping just gets long again, and a floor that creeps to 3 hides a
    # genuine second surface.
    lines = [ln for ln in text.split("ALREADY ASKED")[1].splitlines()
             if ln.strip().startswith("- ")]
    check("the block is capped, not the whole window",
          len(lines) == sbf.ASK_BLOCK_CAP,
          f"printed {len(lines)} of {2 + ASK_FILLER} qualifying rows, "
          f"cap is {sbf.ASK_BLOCK_CAP}")
    check("...and the remainder is counted, never silently dropped",
          f"{2 + ASK_FILLER - sbf.ASK_BLOCK_CAP} more" in text, "no overflow line")
    check("a single mention is not a repeat and stays out of the block",
          sbf.ASK_REPEAT_FLOOR >= 2 and "smoke:once" not in text)
    # THE SAME ROW, THE OTHER SIDE. The demotion the SELECTOR does is a different
    # question from what the brief prints, and trimming the reading must not trim
    # it: a 1× row still rides the cooldown inside `floor_gap_targets`. Asserted
    # on the row the block just hid, so the two cannot drift apart quietly.
    check("...while the selector still counts it — only the reading is trimmed",
          st.recent_ask_counts(klog, lex_now).get("smoke:once") == 1,
          f"got {st.recent_ask_counts(klog, lex_now).get('smoke:once')}")

    write_json(lex_path, json.loads(saved[0].decode("utf-8")))
    write_json(klog_path, json.loads(saved[1].decode("utf-8")))


def s69_two_readers_two_tickets(sb: Path):
    """The ticket is split by audience (2026-08-21). Anna's load was measured at
    25.8k tokens before he spoke, and the ticket was 8.3k of it — of which the
    Vocabulary Fence alone was 65%, a studio input no protocol file asks Anna to
    read, and the SLIP LEDGER was a verbatim second copy of what `status`
    already gave him that same session.

    THE SILENT NO-OP, and it runs in the expensive direction: if the fence stops
    reaching the DIRECTOR, nothing raises. The studio still writes an episode,
    still lints, still renders, still publishes — it just quietly stops building
    dialogue from words Andrew knows, and comprehension-as-heard drifts down
    over a run of episodes with every instrument green. So this asserts the
    fence is PRESENT for the studio path, not merely absent from Anna's.

    The mirror failure is the ledger going missing from BOTH surfaces at once,
    which would silently end slip-steered teaching. `status` is the one that
    keeps it — the knock lane reads that digest too."""
    print("\n69. Two readers, two tickets (2026-08-21)")
    import subprocess as _sp

    # THIS CASE DECLARES ITS OWN DATA (2026-08-24). Three of its assertions —
    # COVERAGE, ENGINES TO FIRE, and the slip ledger on `status` — are about
    # blocks that only PRINT when there is something to print, and the day-zero
    # fixtures are empty. Until now it read whatever the forty cases ahead of it
    # happened to leave in the sandbox, which made it the last case in the suite
    # that could not be reproduced alone. What it seeds is the minimum each block
    # needs and nothing else: a registered fire word (coverage), a pattern not
    # yet cold (an engine), and a tag slipped twice (a REPEATED slip — once is
    # not a pattern, and the ledger says so).
    lex_path, slip_path = sb / "progress" / "lexicon.json", sb / "progress" / "slip_log.json"
    lex = read_json(lex_path)
    lex.setdefault("ஸ்மோக்வார்த்தை", {
        "gloss": "smoke word", "phonetic": ["smoke vaarthai"], "register": "survival",
        "recognition": "comfortable", "production": "hinted", "reps": 2})
    lex.setdefault("frame:smoke-engine", {
        "gloss": "the smoke frame", "phonetic": [], "type": "pattern",
        "recognition": "comfortable", "production": "hinted", "reps": 1})
    write_json(lex_path, lex)
    slips_now = read_json(slip_path)
    for n in (1, 2):   # twice — a slip is REPEATED or it is not on this list
        slips_now.append({"date": date_cls.today().isoformat(), "tag": "smoke-repeat",
                          "said": f"wrong-{n}", "want": "right", "lane": "chat",
                          "note": "seeded by s69 so the ledger has something to report"})
    write_json(slip_path, slips_now)

    def ticket(*args):
        return _sp.run([sys.executable, str(sb / "scripts" / "suggest_targets.py"), *args],
                       cwd=sb, capture_output=True, encoding="utf-8",
                       errors="replace").stdout

    anna, director = ticket(), ticket("--fence")
    check("Anna's ticket drops the Architect's fence", "VOCABULARY FENCE" not in anna)
    # The assertion that matters — the expensive direction.
    check("...and the Director still gets it, or scripts drift off-fence silently",
          "VOCABULARY FENCE" in director, director[-300:])
    check("...so the studio's copy is the strictly larger one",
          len(director) > len(anna), f"anna={len(anna)} director={len(director)}")
    # NOT a size ratio. The first draft asserted anna < director/2, which is true
    # of the live lexicon (2,160 vs 7,614 tokens) and false in a sandbox seeded
    # from the near-empty .example fixtures — a property of the DATA masquerading
    # as a property of the code. What is fixture-independent: the Director's
    # surplus is exactly the fence block and nothing else.
    head = director.index("4. VOCABULARY FENCE")
    check("the Director's extra content IS the fence — the split adds nothing else",
          director[:head].rstrip() == anna.rstrip(),
          "the two tickets diverge somewhere other than the fence")

    # The blocks Andrew kept, and the one he cut (2026-08-21).
    for keep in ("FOCUS SET", "COVERAGE", "NEW CANDIDATES", "ENGINES TO FIRE"):
        check(f"Anna keeps {keep}", keep in anna, anna[:200])
    check("BACKGROUND is not printed to either reader",
          "1b. BACKGROUND" not in anna and "1b. BACKGROUND" not in director)

    # The ledger: exactly one of Anna's two session inputs carries it.
    status = _sp.run([sys.executable, str(sb / "scripts" / "sync_state.py"), "status"],
                     cwd=sb, capture_output=True, encoding="utf-8",
                     errors="replace").stdout
    in_status, in_ticket = "REPEATED SLIPS" in status, "REPEATED SLIPS" in anna
    check("the slip ledger survives — it is still on a surface Anna loads",
          in_status, "the ledger vanished from BOTH inputs")
    check("...and it is not also repeated by the ticket",
          not in_ticket, "the duplicate is back")


def s68_the_convergence_audit_fixes(sb: Path):
    """The 2026-08-20 audit's live defects, each asserted where it can actually
    fail. Every one of these was a state INDISTINGUISHABLE FROM SUCCESS — the
    reason a holistic pass found them and seven weeks of green runs did not.

    1. THE COMMISSION DETECTION. `dose_channel` records that SOME soak order was
       standing when a slip was made, for some other payload. slip_patterns fed
       it into `channels`, so every slip inherited one, `uncommissioned` could
       never be true and `escalate`'s one-channel test could never match. Both
       gates were dead from 2026-07-31; on live state 0 of 22 patterns could
       trip either. Silent no-op: a debt ledger that always reads "nothing
       owed" looks exactly like a system with no debts.

    2. THE CLOCK. suggest_targets and generate_callbacks scored staleness on
       date.today() — the HOST's clock — while last_surfaced is stamped with
       local_today(). state_io names this seam and these two callers were
       missed. Silent no-op: an off-by-one due date is invisible; the menu is
       still full, the items are just the wrong ones on a UTC runner.

    3. TARGET_REVEALED. Three defaults in one file: the CLI store_true gave
       False, enqueue() and the drain fallback gave True. A CLI-queued dose
       silently meant "not revealed", so its reply could score COLD off a body
       that had handed the Tamil over. Silent no-op: an inflated cold fire is
       indistinguishable from a real one, and it moves the production axis.

    4. THE PUBLISH NET. render_audio ran a raw add/commit/push with no rebase,
       wrapped in a bare `except` that printed a warning and exited 0 — so
       run_studio then printed "rendered and published" for an episode that
       never landed. Asserted structurally: the lane must route through
       commit_and_push (which carries _rebase_onto_main) and must NOT swallow.

    5. THE EPISODE TITLE. The Architect was never told to emit an H1, so
       rebuild_rss.get_title_from_md — which reads exactly one line — fell back
       to the filename for 30 of 90 episodes on the PUBLIC feed. Asserted
       against the real reader, on the real line it reads.

    6. THE AGENT CONTRACT. AGENTS.md was a symlink; a Windows checkout writes
       that as a 9-byte text file containing "CLAUDE.md", so an AGENTS.md-reading
       agent got no instructions and git status stayed clean."""
    print("\n68. The convergence-audit fixes (2026-08-20)")
    import contextlib
    import subprocess as _sp
    sl = importlib.import_module("slips")
    st = importlib.import_module("suggest_targets")
    gc_ = importlib.import_module("generate_callbacks")
    pq = importlib.import_module("push_queue")
    sio = importlib.import_module("state_io")

    # --- 1. the commission detection, on the exact shape that disarmed it ----
    slip_path = sb / "progress" / "slip_log.json"
    learner_path = sb / "progress" / "learner.json"
    keep = (slip_path.read_bytes(), learner_path.read_bytes())
    try:
        slip_path.write_text("[]", encoding="utf-8")
        learner = read_json(learner_path)
        for k in ("slip_closes", "slip_commissions"):
            learner.pop(k, None)
        write_json(learner_path, learner)
        with contextlib.redirect_stdout(io.StringIO()):
            # TWO slips, BOTH carrying a dose_channel — the shape every real
            # slip has, because sync_state stamps the standing order on all of
            # them. Before the fix this pattern read as fully commissioned.
            sl.append_slips([{"tag": "audit-tag", "said": "a", "want": "b"}],
                            lane="chat", dose_channel="episode", when="2026-08-01")
            sl.append_slips([{"tag": "audit-tag", "said": "a", "want": "b"}],
                            lane="chat", dose_channel="drill",
                            when=sio.local_today().isoformat())
        p = {x["tag"]: x for x in sl.slip_patterns()}["audit-tag"]
        check("a live pattern with dose_channel stamps is still a real pattern",
              p["pattern"] and p["live"], p)
        # THE ASSERTION THAT WOULD HAVE CAUGHT IT.
        check("...and an unrelated standing order does NOT count as its dose",
              p["channels"] == [], f"inherited {p['channels']}")
        check("...so the debt is visible — this read False for three weeks",
              p["uncommissioned"], "the detection is disarmed again")
        check("...and it is not told to change a format nothing ever tried",
              not p["escalate"], "escalated off a phantom dose")
        # Declaring one is the ONLY thing that fills channels.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.record_slip_commission(["audit-tag"], {"channel": "soak"},
                                      today="2026-08-02")
        p = {x["tag"]: x for x in sl.slip_patterns()}["audit-tag"]
        check("a DECLARED commission is what discharges the debt",
              p["channels"] == ["soak"] and not p["uncommissioned"], p["channels"])
    finally:
        slip_path.write_bytes(keep[0])
        learner_path.write_bytes(keep[1])

    # --- 2. the clock: both selectors must read ANDREW's day -----------------
    for mod, name in ((st, "suggest_targets"), (gc_, "generate_callbacks")):
        src = mechanism((sb / "scripts" / f"{name}.py").read_text(encoding="utf-8"))
        check(f"{name} scores staleness on the learner's clock, not the host's",
              "date.today()" not in src, "date.today() is back — UTC runners drift a day")
        check(f"...and {name} takes it from the one owner",
              "local_today" in src and hasattr(mod, "local_today"), name)

    # --- 3. one field, one default -------------------------------------------
    # Drive the real CLI, because the default that was wrong was the PARSER's —
    # reading the function signature alone is what let the three disagree.
    pq_src = mechanism((sb / "scripts" / "push_queue.py").read_text(encoding="utf-8"))
    cli_default = _sp.run([sys.executable, str(sb / "scripts" / "push_queue.py"),
                           "add", "--help"], capture_output=True,
                          encoding="utf-8", errors="replace").stdout
    check("the CLI exposes both directions instead of a one-way store_true",
          "--no-target-revealed" in cli_default, cli_default[-300:])
    enqueue_default = inspect.signature(pq.enqueue).parameters["target_revealed"].default
    check("enqueue() defaults to the conservative end — never over-credit a cold fire",
          enqueue_default is True, enqueue_default)
    check("...and the drain falls back the same way, so all three agree",
          '"target_revealed", True' in pq_src,
          "the drain fallback drifted from the other two")

    # --- 4. the publish net --------------------------------------------------
    tail = mechanism((sb / "scripts" / "render_audio.py").read_text(encoding="utf-8"),
                     after="Lifecycle hooks")
    check("the episode lane publishes through the shared rebase net",
          "commit_and_push(" in tail, "raw git push is back — no rebase under it")
    check("...and a failed publish is LOUD, not a printed warning over exit 0",
          "Lifecycle hooks failed" not in tail, "the bare except is back")

    # --- 5. the episode's public name ----------------------------------------
    rr = importlib.import_module("rebuild_rss")
    tmp = sb / "content" / "scripts" / "smoke_title_probe.md"
    try:
        tmp.write_text("[SFX: chairs scraping]\n\n# Tier 2, Mission 91 — The Real Name\n",
                       encoding="utf-8")
        check("an H1 below the first line is as absent as no H1 — the reader sees one line",
              rr.get_title_from_md(str(tmp)) == "smoke_title_probe.md",
              rr.get_title_from_md(str(tmp)))
        tmp.write_text("# Tier 2, Mission 91 — The Real Name\n\n[SFX: chairs]\n",
                       encoding="utf-8")
        check("...and a first-line H1 becomes the feed's title",
              rr.get_title_from_md(str(tmp)) == "Tier 2, Mission 91 — The Real Name",
              rr.get_title_from_md(str(tmp)))
    finally:
        tmp.unlink(missing_ok=True)
    rs_src = mechanism((sb / "scripts" / "run_studio.py").read_text(encoding="utf-8"))
    check("the lint refuses a script whose FIRST line is not an H1",
          'splitlines()[0].strip().startswith("# ")' in rs_src, "the title lint is gone")
    check("...and the Architect is actually told to write one",
          "VERY FIRST LINE" in rs_src
          and "first line" in (sb / "protocol" / "studio" / "architect.md")
          .read_text(encoding="utf-8").lower(),
          "the prompt or the role file lost the rule")

    # --- 6. the agent contract is a real file --------------------------------
    agents = sb / "AGENTS.md"
    check("AGENTS.md carries real instructions, not a symlink's path text",
          agents.stat().st_size > 500, f"{agents.stat().st_size} bytes")
    mode = _sp.run(["git", "ls-files", "-s", "AGENTS.md"], cwd=REAL_BASE,
                   capture_output=True, encoding="utf-8").stdout.split()
    check("...and git stores it as a regular file, so a Windows clone gets it",
          mode and mode[0] == "100644", mode[0] if mode else "untracked")


def s65_the_ordering_outlives_the_deck(sb: Path):
    """The deck retirement's load-bearing case (2026-08-18). The container
    expired at touchdown; the ORDERING — survival > delight > dessert — is
    durable knowledge about which failures cost most at a table, and retiring
    the one must not delete the other.

    THE TRAP, and why this case was written before a line was removed: tiers
    were computed by joining `curriculum/trip_deck.json` at menu time, keyed on
    `deck == "trip"` membership. 0 of 339 lexicon rows carried a `register`.
    Delete the deck without migrating and the ordering vanishes SILENTLY — the
    selector keeps returning rows, they are simply no longer tier-ordered.
    Nothing raises, no list is empty, every instrument reads green. That is the
    exact silent-no-op class Gate 7.2 exists for, so the assertions below are on
    rows that carry a `register` and NO `deck` tag at all: the shape every row
    has after retirement, and the shape that had no test before it."""
    print("\n65. The ordering outlives the deck (2026-08-18)")
    st = importlib.import_module("suggest_targets")
    today = date_cls.today()
    ago = lambda n: (today - timedelta(days=n)).isoformat()

    def row(**kw):
        base = {"gloss": "x", "phonetic": [], "type": "chunk",
                "recognition": "comfortable", "production": "none",
                "seen_in": [1], "last_surfaced": ago(10), "reps": 1}
        base.update(kw)
        return base

    # No `deck` key anywhere in this fixture. Equal staleness, equal reps: the
    # register is the ONLY thing that can separate these.
    lex = {
        "smoke:ord-dessert": row(register="zinger"),
        "smoke:ord-survival": row(register="antifreeze"),
        "smoke:ord-delight": row(register="social"),
        "smoke:ord-plain": row(),                      # no register at all
    }
    focus, _bg = st.floor_gap_targets(lex, today, 12, asked={}, cohort=["smoke:ord-plain"])
    order = [t["word"] for t in focus]
    check("a survival-register row leads, with no deck tag in sight",
          order[0] == "smoke:ord-survival", f"got {order}")
    check("...and dessert still sorts last — the whole bar survives",
          order[-1] == "smoke:ord-dessert", f"got {order}")
    check("an unregistered row degrades to delight, not to unreachable",
          "smoke:ord-plain" in order
          and order.index("smoke:ord-delight") < order.index("smoke:ord-dessert"),
          f"got {order}")

    # THE MIGRATION ITSELF: the tier must be read off the row, never joined from
    # a curriculum file. A rank that still needed the deck file would score every
    # row here at the non-member fallback and the ordering would be flat.
    check("the tier is read off the lexicon row, not joined from a deck file",
          st.tier_rank(lex["smoke:ord-survival"]) == 0
          and st.tier_rank(lex["smoke:ord-dessert"]) == 2
          and st.tier_rank(lex["smoke:ord-plain"]) == 1,
          "tier_rank does not read `register`")
    check("the curriculum join is gone — no reader is left to drift",
          not hasattr(st, "deck_registers") and not hasattr(st, "deck_rank"),
          "a deck-keyed reader survived the retirement")

    # THE INVARIANT, stated as the work order stated it: retiring the container
    # must not delete the ordering. A survival row with no deck tag outranks an
    # ordinary row of EQUAL staleness — equal, so nothing but the bar can do it.
    plain, surv = lex["smoke:ord-plain"], lex["smoke:ord-survival"]
    check("survival outranks an ordinary row of equal staleness",
          st.pool_key({"word": "a", "reps": 1, "tier_rank": st.tier_rank(surv)})
          < st.pool_key({"word": "a", "reps": 1, "tier_rank": st.tier_rank(plain)}),
          "the bar does not survive in pool_key")

    # ONE POOL, not three. The deck, the focus set and the going-dark block were
    # separate sections, and the first two claimed primacy in their own words.
    check("the rival selectors are gone, not merely unused",
          not any(hasattr(st, n) for n in ("deck_status", "deck_coverage", "retest_targets")),
          "a retired pool survived")
    check("the knock lane and the session lane read the SAME pool",
          st.drill_menu.__module__ == st.floor_gap_targets.__module__,
          "the menu drifted out of the selector")

    # THE STALE-COHORT HOLE, and why `reseed-focus` exists. Stored membership is
    # the point ("held seats stand regardless of what any counter says") and it
    # is right — but a counter is not the only thing that can change. When the
    # ORDERING changes, a cohort seeded under the old one holds seats the new one
    # would never grant, and `reconcile_focus` cannot fix it: it only fills seats
    # as they OPEN. On 2026-08-18 all twelve were held by unregistered rows
    # seeded before the tier bar existed, so no survival row could enter a pool
    # that ranks them first. Migrating `register` was necessary and not
    # sufficient — this is the other half, and without it the whole retirement is
    # inert in exactly the way Gate 7.2 describes: green, ordered, and unable to
    # act on its own order.
    import contextlib, io
    ss = importlib.import_module("sync_state")
    lex_path, learner_path = sb / "progress" / "lexicon.json", sb / "progress" / "learner.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes())
    try:
        stale = dict(lex)
        stale.update({f"smoke:ord-held{i}": row() for i in range(st.FOCUS_SIZE)})
        write_json(lex_path, stale)
        learner = read_json(learner_path)
        learner["focus_cohort"] = [f"smoke:ord-held{i}" for i in range(st.FOCUS_SIZE)]
        write_json(learner_path, learner)

        focus, _bg = st.floor_gap_targets(stale, today, st.FOCUS_SIZE,
                                          asked={}, cohort=learner["focus_cohort"])
        check("a stale cohort locks the ordering out — the hole, reproduced",
              "smoke:ord-survival" not in [t["word"] for t in focus],
              "the fixture does not reproduce the stale-cohort hole")

        class A:
            dry_run = True
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ss.cmd_reseed_focus(A())
        check("a dry run writes nothing",
              read_json(learner_path)["focus_cohort"] == learner["focus_cohort"],
              "reseed-focus wrote on a dry run")
        check("...and says what it would do",
              "smoke:ord-survival" in out.getvalue() and "dry run" in out.getvalue(),
              out.getvalue())

        A.dry_run = False
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_reseed_focus(A())
        seated = read_json(learner_path)["focus_cohort"]
        check("the reseed lets the ordering take its seats",
              "smoke:ord-survival" in seated, f"got {seated}")
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_reseed_focus(A())
        check("...and it is idempotent — re-running is not churn",
              read_json(learner_path)["focus_cohort"] == seated,
              "a second reseed moved the cohort")
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])


def s73_one_tail_for_the_render_family(sb: Path):
    """The write -> render -> publish family's shared tail (2026-08-24, Q1).

    UNTESTED UNTIL NOW, by anything. Both existing drives of a render lane's
    `main()` pass `--dry-run`, which returns before the tail, and the only other
    coverage was a source-grep of one call site. So the sequence that records
    exposure, stamps a soak order, builds the commit and reaches the phone — for
    three lanes, soon five — had never been executed by a test.

    THE SILENT NO-OP, answered: if this function did nothing at all, every lane
    would still print "done", still exit 0, and still look exactly like a
    successful dose. Nothing downstream raises. So the assertions are on the
    EFFECT — what reached the commit and what reached the phone — never on the
    fact that it ran.

    The last block is the one that protects the design rather than the behaviour.
    `commit` and `notify` are passed IN so that a lane's own binding is what gets
    called, which is what keeps the suite's 59 module-attribute stubs
    intercepting once a shared runner does the work (hazard H1). If this function
    ever reaches for `publish.push_to_phone` directly instead of the argument, all
    of them silently stop intercepting and a test hits real git and a real phone.
    That regression would be invisible in every other assertion here, so it gets
    its own: the module-level names are booby-trapped, and must never fire.
    """
    print("\n73. One tail for the write→render→publish family (2026-08-24)")
    import contextlib
    lanes = importlib.import_module("lanes")

    mp3 = sb / "published_audio" / "smoke_family.mp3"
    mp3.parent.mkdir(parents=True, exist_ok=True)
    mp3.write_bytes(b"ID3fake")
    script = sb / "content" / "scripts" / "smoke_family.md"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("the tape's story", encoding="utf-8")

    fx.pb.refresh_feed = lambda: None          # the feed has its own cases (s31)
    commits, pushes = [], []

    def drive(*, delivered=("ஸ்மோக்"), claimed=False, extra=(), exposed=True,
              stamped=True, notified=True):
        lanes.record_exposure = lambda words: exposed and bool(words)
        lanes.mark_soak_delivered = lambda lane: stamped
        commits.clear(); pushes.clear()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            got = lanes.deliver_rendered(
                mp3=mp3, lane="soak", delivered=list(delivered), claimed=claimed,
                message="Soak loop: smoke", copy="soak loop's up 🎧",
                noun="soak loop", extra_paths=list(extra),
                commit=lambda paths, msg: commits.append((list(paths), msg)),
                notify=lambda copy, url: (pushes.append((copy, url)), notified)[1])
        return got, out.getvalue()

    # ── THE DESIGN, before anything else, so its diagnosis arrives BEFORE the
    # crash it exists to prevent. `commit` and `notify` are ARGUMENTS: a lane
    # passes its own binding, which is what keeps this suite's 59
    # module-attribute stubs intercepting once a shared runner does the work
    # (hazard H1). The failure mode is silent by nature — the tail would just
    # start calling the real thing — so it is asserted structurally, twice:
    # nothing boundary-shaped is bound into this module at all, and a booby trap
    # on the owner's names never fires. Measured: with the import form restored,
    # the first check goes red naming the binding; without it the case dies in a
    # git subprocess, which is safe but unreadable.
    def boom(*a, **kw):
        raise AssertionError(
            "deliver_rendered reached for a module-level boundary instead of the "
            "`commit`/`notify` it was handed. Every lane-level stub here stops "
            "intercepting the moment it does that, and a test then writes real "
            "git history and pushes to a real phone.")
    fx.pb.commit_and_push, fx.pb.push_to_phone = boom, boom
    for seam in ("commit_and_push", "push_to_phone"):
        bound = getattr(lanes, seam, None)
        check(f"the tail binds no {seam} of its own — the seam is the argument",
              bound is None, f"lanes.{seam} = {bound!r}")

    # ── the mp3 leads the commit, or the CDN has nothing to serve ────────────
    drive(claimed=True, extra=[script])
    paths, msg = commits[0]
    check("the mp3 is FIRST in the commit — push_to_phone pre-warms the CDN and "
          "jsDelivr can only serve what is already on main",
          paths[0] == mp3, f"got {[Path(p).name for p in paths]}")
    check("...and the lane's own extra paths ride the SAME commit",
          script in paths, f"got {[Path(p).name for p in paths]}")
    check("...under the lane's message", msg == "Soak loop: smoke", msg)

    # ── the two conditional state paths, both directions ────────────────────
    check("a recorded exposure puts the lexicon in the commit",
          fx.si.LEXICON_PATH in commits[0][0])
    check("a stamped order puts learner.json in the commit",
          fx.si.LEARNER_PATH in commits[0][0])
    drive(claimed=True, exposed=False, stamped=False)
    check("nothing exposed -> the lexicon is NOT committed",
          fx.si.LEXICON_PATH not in commits[0][0], f"got {commits[0][0]}")
    check("nothing stamped -> learner.json is NOT committed",
          fx.si.LEARNER_PATH not in commits[0][0], f"got {commits[0][0]}")

    # ── the stamp claims a debt is PAID; it must follow the lane's own test ──
    stamped_for = []
    lanes.mark_soak_delivered = lambda lane: stamped_for.append(lane) or True
    drive(claimed=False)
    check("claimed=False never stamps — a wrong stamp buries an owed dose",
          not stamped_for, f"stamped {stamped_for}")

    # ── what reaches the phone ──────────────────────────────────────────────
    got, said = drive()
    copy, url = pushes[0]
    check("the notification carries the lane's copy", copy == "soak loop's up 🎧", copy)
    check("...and the jsDelivr URL for THIS mp3",
          url.startswith("https://cdn.jsdelivr.net/gh/") and mp3.name in url, url)
    check("...and the return says it landed", got is True)
    check("...and the closing line names the lane's noun",
          "done — soak loop on the feed and the lock screen" in said, said.strip())
    got, said = drive(notified=False)
    check("quiet hours propagate — the tail reports NOT on the lock screen",
          got is False and "and the lock screen" not in said, said.strip())

    # Every drive above ran with `pb.commit_and_push` / `pb.push_to_phone`
    # booby-trapped. Reaching either would have raised out of this case.
    check("...and no drive ever touched the owner's names directly",
          len(commits) == 1 and len(pushes) == 1,
          f"commits={len(commits)} pushes={len(pushes)}")


def s74_a_derived_file_follows_its_source(sb: Path):
    """chat.md is a pure render of knock_log.json (2026-08-24).

    `render_chat` reads the log and nothing else, so a commit that carries the log
    without a fresh render publishes a page that is already stale — and it stays
    stale until some later lane happens to rebuild it. That is precisely what the
    old "Log tap" step did: a tap's "👍 acked" sat unrendered for hours
    (2026-08-04).

    Five lanes obeyed the rule by hand, each calling render_chat() while building
    its own commit list: morning_knock's fire AND its silence tick, both
    knock_reply judges, the queue drain, and sync_state's knock-response. Five
    copies of one rule is the shape this refactor exists to retire, and it is a
    rule with no natural home in any of them.

    THE SILENT NO-OP: a stale chat.md raises nothing. The commit succeeds, the
    push succeeds, every instrument reads green, and the only symptom is that the
    page Andrew opens on his phone is missing the exchange he just had. So the
    teeth are on the CONTENT, not on the path list — appending the path without
    rebuilding the file would satisfy a membership check and still ship the stale
    page.
    """
    print("\n74. A derived file follows its source (2026-08-24)")
    klog_path = sb / "progress" / "knock_log.json"
    chat_path = sb / "progress" / "chat.md"
    fx.pb.refresh_feed = lambda: None          # the feed has its own cases (s31)

    marker = "ஸ்மோக்டெரைவ்டு"
    write_json(klog_path, [{"acted": True, "date": "2026-08-24",
                            "timestamp": "2026-08-24T09:00:00+00:00",
                            "body": marker, "modality": "text", "move": "smoke"}])
    chat_path.write_text("STALE — written before that log entry existed\n",
                         encoding="utf-8")

    paths, _ = fx.pb.publish([klog_path], "smoke", feed=False)
    names = [Path(q).name for q in paths]
    check("a commit carrying the knock log also carries chat.md",
          "chat.md" in names, f"got {names}")
    check("...and the page was RE-RENDERED, not merely listed",
          marker in chat_path.read_text(encoding="utf-8"),
          "chat.md rode the commit while still holding the stale text")

    # It must not fire on a commit that has nothing to do with the log — the feed
    # rebuild is already conditional and this must be too, or every soak render
    # rewrites a page it did not touch.
    lex_only, _ = fx.pb.publish([sb / "progress" / "lexicon.json"], "smoke", feed=False)
    check("a commit without the log does NOT drag chat.md in",
          "chat.md" not in [Path(q).name for q in lex_only],
          f"got {[Path(q).name for q in lex_only]}")

    # And a lane that still passes it explicitly must not get it twice — a
    # duplicate path is a `git add` of the same file, harmless but a sign the
    # rule has two owners again.
    twice, _ = fx.pb.publish([klog_path, chat_path], "smoke", feed=False)
    check("...and a lane passing it explicitly does not get it twice",
          [Path(q).name for q in twice].count("chat.md") == 1,
          f"got {[Path(q).name for q in twice]}")


def main():
    """Dispatch. One sandbox and one set of module objects for the whole run:
    the cases are being re-homed, not re-scoped, and a per-file sandbox would
    hand each file its own re-imported `mk` — the one thing §10.7 says not to
    do, since every stub and its teardown are keyed to a module object."""
    with tempfile.TemporaryDirectory(prefix="tamil-smoke-") as tmp:
        sb = make_sandbox(Path(tmp))
        print(f"sandbox: {sb}")
        mk, kr, pq = load_modules(sb)
        snapshot(mk, kr, pq, fx.pb, fx.wr, fx.si)
        compose.run_all(mk, kr, pq, sb)
        run(s2_rails_gate, mk, sb / "progress" / "knock_log.json")
        run(s15_push_retry, mk)
        run(s67_two_replies_to_one_knock_both_survive, mk)
        run(s35_quiet_hours_chokepoint, sb)
        run(s59_transit_bit, mk, sb)
        run(s3_knock_paths, mk, sb)
        run(s4_normalize, kr)
        run(s5_reply_judge, mk, kr, sb)
        run(s6_queue_drain, mk, pq, sb)
        run(s7_integrity, sb)
        run(s8_variety_and_decay, mk, kr, sb)
        run(s9_audio_knock_feed, mk, sb)
        run(s10_chain_history, mk, kr, sb)
        run(s11_capped_graduation, kr, sb)
        run(s12_volley, mk, kr, sb)
        run(s13_eavesdrop, mk, kr, sb)
        run(s14_reply_correlation, kr)
        run(s16_stale_clone_gates, sb)
        run(s17_campaign_digest, mk, sb)
        ratchets.run_all(mk, kr, pq, sb)
        render.run_all(mk, kr, pq, sb)
        run(s20_fielding, mk, kr, sb)
        run(s21_volley_represent, kr, sb)
        run(s22_sfx_pause, sb)
        run(s23_ticket_end_to_end, sb)
        run(s25_studio_concurrency_and_secrets, sb)
        run(s27_schedule_and_soak_guards, sb)
        queue.run_all(mk, kr, pq, sb)
        run(s30_anna_speaks_back, mk, kr, sb)
        run(s31_feed_carries_every_pushed_dose, sb)
        run(s32_pool_rotation_and_coverage, mk, sb)
        run(s33_catch_response_pairs, mk, sb)
        run(s34_focus_and_background, sb)
        run(s36_soak_order_carries_shape, sb)
        run(s37_repair_earns_the_dose, sb)
        run(s38_teach_enters_the_lexicon, sb)
        run(s39_ticket_carries_the_commission, sb)
        run(s41_slip_ledger, kr, sb)
        run(s42_session_log_one_row_per_day, sb)
        run(s43_sidecar_callback_never_drops_silently, sb)
        run(s44_a_commission_can_discharge_the_flag, sb)
        run(s46_the_commission_notice_names_the_debt, sb)
        run(s47_hinted_retest_rule, sb)
        run(s53_unverify_rows_nothing_ever_tested, sb)
        run(s54_no_deadline_reaches_any_surface, sb)
        run(s55_demotion_survives_the_close, sb)
        run(s56_timezone_is_one_dial, sb)
        run(s49_thread_continuity, mk, kr, sb)
        run(s50_read_surfaces_are_phonetic, mk, kr, sb)
        run(s51_derived_files_are_rerendered_not_merged, mk, sb)
        run(s71_a_new_record_is_born_reachable, sb)
        run(s60_the_ear_meter, kr, sb)
        run(s61_no_number_is_recited_at_him, kr, sb)
        run(s62_the_return_clock_is_keyed_to_the_ear, sb)
        run(s63_the_machines_reach_the_ticket)
        run(s64_the_ask_cooldown_covers_the_session_lane, sb)
        run(s65_the_ordering_outlives_the_deck, sb)
        run(s68_the_convergence_audit_fixes, sb)
        run(s69_two_readers_two_tickets, sb)
        run(s73_one_tail_for_the_render_family, sb)
        run(s74_a_derived_file_follows_its_source, sb)

    if fx.ONLY and not fx.RAN:
        sys.exit(f"no case matched {fx.ONLY} — name a case (s41) or a prefix (s41_slip)")
    scope = (f"{len(fx.RAN)} case(s): {', '.join(fx.RAN)}" if fx.ONLY
             else f"{len(fx.RAN)} cases")
    print(f"\n{scope}")
    print(f"{'ALL GREEN' if not fx.FAILURES else 'FAILURES: ' + ', '.join(fx.FAILURES)}")
    sys.exit(1 if fx.FAILURES else 0)


if __name__ == "__main__":
    main()
