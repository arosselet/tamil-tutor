"""L5 — the knock and reply lanes: the decide/judge half of the loop.

The rails gate, the fire and silence paths, verdict normalization, the
production axis, chains and volleys, eavesdrop and fielding doses, thread
continuity, and the rule that every read surface is phonetic.

This is the lane Andrew actually meets, so its silent failures are the ones that
read as Anna being dumb rather than as plumbing: a fire credited for a word he
never typed, a catch re-asked after it already landed, an open ask lost to a
meta reply. The cases here check credit against his actual reply text.
"""
import importlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import _fixtures as fx
from ._fixtures import (
    check, mechanism, read_json, REAL_BASE, Recorder, write_json,
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
