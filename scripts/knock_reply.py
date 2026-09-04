#!/usr/bin/env python3
"""
The reply half of the knock loop — the micro-session on the lock screen.

Andrew types phonetic Tamil straight into the knock notification; Home Assistant
routes it here (via repository_dispatch → anna.yml). Anna judges the
reply against what that knock asked for, moves the production axis, and pushes one
line back — the recast (or the celebration) plus the deck scoreboard. An EAVESDROP
knock takes a separate lane (2026-07-09): the reply is an English drift answer,
judged for comprehension on its own small mandate, and moves the RECOGNITION axis
of the dose's ear-only deck item — the catch half of the sprint meter.

Judge philosophy: this is the recast across the table, not an exam. Anna is
generous in spirit but honest on the axis — each fired word is graded on its OWN
merits (per-word verdicts: one shaky word must not drag down a clean one) — and
Python re-enforces the one hard rule per word: Tamil the notification SHOWED him
can score at most "hinted"; "cold" is reserved for unaided production. The one
release valve (2026-07-08): a cold-QUALITY fire the reveal window blocks is
recorded CAPPED, and capped fires on GRADUATION_DAYS distinct local days
graduate the word to cold — otherwise a daily-knocked word could never escape
hinted through the very channel drilling it. Andrew stays the court of appeal:
every verdict is visible in the push-back and in knock_log.json, and chat
sessions can always correct state.

  python scripts/knock_reply.py "naan poren"            # judge, write state, commit+push, notify
  python scripts/knock_reply.py --dry-run "naan poren"  # judge + print only (no writes)

Anna may answer ALOUD (2026-07-24): when the sound IS the answer — how a line is
pronounced, a greeting for someone standing in the room — the judge returns
`voice_reply` and Python renders it into this same push-back. Rationed by the
mandate, because the render costs ~90s while Andrew waits at the lock screen.

Secrets: OPENROUTER_API_KEY (the judge), ANNA_PUSH_WEBHOOK_URL (the push-back),
GCP TTS auth (only when Anna answers aloud).
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from knock_message import handle_message
from push_queue import maybe_enqueue_schedule
from publish import commit_and_push, load_env, publish, push_to_phone
# The lane-neutral half of answering him — detectors, the voice backstop, the
# render, and the one ledger writer. Split out 2026-08-28 so the MESSAGE lane
# could have them without importing the grading lane (reply_common.py).
from reply_common import (_ts, ensure_voice, recent_exchanges,
                          record_meta_note, speak, wants_scheduled_push)
from writer import BOOL, STR, arr, ask_json, executor_name, obj, to_phonetic, voice_canon

# Each judge declares its OWN top-level shape, beside itself (2026-08-23) —
# never a shared or generic one, which is how `claude -p` came back with an
# envelope and a lane rendered a shell with every instrument green. Keys mirror
# the mandates below.
#
# "undeclared keys still pass" — WRONG, and it cost a day (2026-08-28). It is
# true of the API path (`json_object` constrains bytes, not shape) and FALSE of
# the agent path: `claude -p --json-schema` constrains the output to the declared
# shape and DROPS anything else. `claude -p` became the writer on 2026-08-18, and
# `voice_reply` — declared by VOICE_MANDATE, absent from this tuple — has been
# stripped from every local judgement since. Anna stopped being able to speak on
# that date and nothing reported it: the model wrote the field, the schema ate
# it, and the reply_line went out alone looking exactly like a decision not to.
# Measured on 2026-08-28: declaring it made the same prompt speak on the first
# pass, with no forced re-ask.
#
# So: if a mandate names a key, the schema MUST name it too. `schedule` is the
# one still missing — it is nullable and obj() has no nullable — and it is
# therefore still being dropped on the agent path (docs/feature_inbox.md).
JUDGE_SCHEMA = obj(verdict=STR, fired=arr(word=STR, said=STR, verdict=STR),
                   reply_line=STR, follow_up_ask=STR, follow_up_target=STR,
                   follow_up_target_revealed=BOOL, meta_note=STR, rationale=STR,
                   voice_reply=STR,
                   # SLIP_MANDATE has asked for this since it was split out, and
                   # the schema never named it — so the agent path has been eating
                   # every knock-lane slip since 2026-08-18. An empty list is a
                   # real answer here (unlike `schedule`), so it declares cleanly.
                   slips=arr(tag=STR, said=STR, want=STR, note=STR))
CATCH_SCHEMA = obj(verdict=STR, reply_line=STR, meta_note=STR, rationale=STR,
                   voice_reply=STR,
                   # Same shape as JUDGE_SCHEMA's `fired` on purpose: the mouth
                   # and the ear each name a key, quote the span, and rule on it.
                   # Declared here because an undeclared key is DROPPED on the
                   # agent path and survives on the API path (obj's 2026-08-28
                   # law) — the smoke suite caught this one before it shipped.
                   heard=arr(key=STR, said=STR, verdict=STR))
from state_io import FEEDBACK_LOG_PATH, KNOCK_LOG_PATH, LEARNER_PATH, LEXICON_PATH, SLIP_LOG_PATH, build_phonetic_index, load_json, local_today, resolve, save_json
from slips import append_slips, slip_patterns
from sync_state import fires_today

from mandates import (CATCH_JUDGE_MANDATE, FORCE_SCHEDULE_ADDENDUM, JUDGE_MANDATE,
                      FORCE_VOICE_ADDENDUM, REACH_MANDATE, SLIP_MANDATE,
                      THREAD_MANDATE, VOICE_MANDATE)

PRODUCTION_RANK = {"none": 0, "hinted": 1, "cold": 2}
VERDICTS = {"cold", "hinted", "miss", "chat"}
CHAIN_CAP = 3  # max chained follow-up asks per knock — momentum, not a treadmill

CATCH_VERDICTS = {"caught", "half-caught", "missed", "chat"}
RECOGNITION_NEXT = {"struggled": "comfortable", "comfortable": "solid"}







def catch_context(knock: dict, reply_text: str, klog: list | None = None) -> dict:
    """What the drift judge is shown. Split out of judge_catch (2026-07-25) so the
    thread it sees is testable without the LLM call — the smoke test stubs
    judge_catch wholesale, so an inline context build is never exercised.

    prior_exchanges is the port the production judge got (see judge()) and this
    lane never did when it was split out: without it turn 3 cannot know turn 1
    already caught the drift, so a hint request re-asks a question Andrew answered
    six minutes earlier (the 07-25 tape, three turns, two false half-caughts)."""
    context = {
        "tape_memo_script": knock.get("memo_script", ""),
        "drift_question": knock.get("body", ""),
        "ear_only_target": knock.get("expected_target", ""),
        "andrew_reply": reply_text,
    }
    prior = recent_exchanges(klog if klog is not None else [knock], knock)
    if prior:
        context["prior_exchanges"] = prior
    return context


def judge_catch(knock: dict, reply_text: str, klog: list | None = None,
                force_voice: bool = False) -> dict:
    """The comprehension judge for an eavesdrop dose — a deliberately separate,
    smaller mandate so the production judge's rules (reveal caps, chains,
    per-word grades) never leak into a drift grade."""
    canon = voice_canon()
    context = catch_context(knock, reply_text, klog)
    print(f"   [catch judge] {executor_name()}")
    # VOICE_MANDATE joins here (2026-08-27). Until it did, WHICH judge ran —
    # decided by the modality of the newest open knock, never by what Andrew
    # asked for — decided whether Anna could answer in sound at all.
    d = ask_json(canon + "\n\n---\n\n" + CATCH_JUDGE_MANDATE + "\n" + THREAD_MANDATE
                 + "\n" + VOICE_MANDATE + (FORCE_VOICE_ADDENDUM if force_voice else ""),
                 json.dumps(context, ensure_ascii=False, indent=2),
                 CATCH_SCHEMA, answer_tokens=700 if force_voice else 550)
    if d.get("verdict") not in CATCH_VERDICTS:
        d["verdict"] = "chat"
    d["reply_line"] = (d.get("reply_line") or "").strip()
    d["meta_note"] = (d.get("meta_note") or "").strip()
    d["voice_reply"] = (d.get("voice_reply") or "").strip()
    return d


def apply_catch_verdict(verdict: dict, knock: dict, lexicon: dict) -> list[str]:
    """Move the RECOGNITION axis for the dose's ear-only target — one rung per
    full catch (struggled → comfortable → solid), upgrades only, mirroring the
    production judge's never-demote rule. 'solid' on a catch item is the deck's
    win condition; production is never touched from here."""
    key = resolve(knock.get("expected_target", ""), lexicon, build_phonetic_index(lexicon))
    if key is None:
        return [f"! eavesdrop target {knock.get('expected_target')!r} resolves to no lexicon record — not scored"]
    rec = lexicon[key]
    today = local_today().isoformat()
    # EVERY JUDGED CATCH IS EAR EVIDENCE, caught or missed (2026-08-27). This
    # block used to return before resolving whenever the verdict was not "caught",
    # so the one instrument that tests recognition recorded nothing on a miss —
    # and on a catch it moved the level while stamping no evidence at all. The
    # mouth judge has bumped `reps` at its own seam since 2026-07-26; the ear
    # judge simply never did, and `unverify` then read that silence as "never
    # tested" and demoted the single genuine catch this ledger had (சும்மா
    # சொல்றாங்க: caught 08-09, demoted 08-23). Stamp first, move the level second.
    rec["last_surfaced"] = today
    rec["heard_on"] = today
    rec["reps"] = rec.get("reps", 0) + 1
    if verdict["verdict"] != "caught":
        return [f"{key} tested by ear — no axis move ({verdict['verdict']}), heard_on {today}"]
    cur = rec.get("recognition", "struggled")
    nxt = RECOGNITION_NEXT.get(cur)
    if nxt is None:
        return [f"{key} already {cur} — kept (caught)"]
    rec["recognition"] = nxt
    return [f"{key} recognition → {nxt.upper()} (caught)"]


# catch_meter() lived here until 2026-08-17. It appended "Catch 3/12 · 12d" to the
# line pushed to Andrew's phone after every eavesdrop reply — a fraction AND a
# countdown, recited at him, on the one surface he cannot look away from. The
# 07-17 law already forbade a global deficit narrated in a warm voice; this was
# the same object with a friendlier font. Deleted, not softened: the meters are
# engineering numbers that steer what Python picks, and Andrew is mastery-driven
# — a scoreboard attached to a learner like that manufactures withdrawal when the
# number moves slowly, which is exactly what it did (2026-08-16 → 08-17).


def apply_heard_words(verdict: dict, knock: dict, lexicon: dict,
                      reply_text: str) -> list[str]:
    """THE WORDS HE PICKS OUT OF THE TAPE, which this lane used to throw away
    (2026-08-31, Andrew: "it's frustrating that it can't recognize/record when I
    am reliably recognizing a word").

    The eavesdrop runs BELOW the 95% coverage floor on purpose — profile.md's
    gossip-tape carve-out, the one exception in the Calibration Notes — so
    catching two words out of eight is the DESIGNED outcome, not a failure.
    Until now those two vanished: `apply_catch_verdict` scores the single
    declared `expected_target` and every other word he named was discarded,
    which is a large part of why the ear moved 8 times to the mouth's 79 over
    07-25 -> 08-31.

    THIS DOES NOT WIDEN THE GRADE. The verdict is still the drift and only the
    drift — "Never grade wording or completeness" stays law in the mandate.
    Scoring N declared items off one gist verdict would INVENT evidence, which
    is the defect the 08-24 purge dropped 108 rows to remove. What is recorded
    here is narrower and real: a word HE named, that the tape actually spoke.

    THREE GUARDS, none optional. Credit requires that
      (1) the judge named a key that resolves to a real lexicon row,
      (2) the span it quotes is ACTUALLY in his reply — `said_in_reply`'s law,
          "Python owns the honesty check, not the matching",
      (3) the key's Tamil is ACTUALLY in the tape. A word the tape never spoke
          cannot be ear evidence however confidently it is named.

    A MISREAD IS WORTH AS MUCH AS A CATCH, and is the half this ledger has never
    had. Reading கேட்கல as "said" stamps the evidence and withholds the
    promotion — the only downward pressure recognition gets, in a ledger whose
    demotions ran 3 in 37 days outside the one purge."""
    today = local_today().isoformat()
    tape = json.dumps(knock.get("memo_script", ""), ensure_ascii=False)
    index = build_phonetic_index(lexicon)
    declared = resolve((knock.get("expected_target") or ""), lexicon, index)
    lines = []
    for item in (verdict.get("heard") or []):
        if not isinstance(item, dict):
            continue
        named = (item.get("key") or "").strip()
        said = (item.get("said") or "").strip()
        key = resolve(named, lexicon, index)
        if key is None:
            lines.append(f"! heard {named!r} resolves to no lexicon record — not scored")
            continue
        if key == declared:
            continue  # apply_catch_verdict already owns the declared target
        if not said_in_reply(said, reply_text):
            lines.append(f"! {key}: judge quoted {said!r}, which is not in his reply — not scored")
            continue
        if key not in tape:
            lines.append(f"! {key}: the tape never said it — not scored")
            continue
        rec = lexicon[key]
        rec["last_surfaced"] = today
        rec["heard_on"] = today
        rec["reps"] = rec.get("reps", 0) + 1
        if (item.get("verdict") or "").strip().casefold() != "right":
            lines.append(f"{key} named but MISREAD — evidence stamped, no promotion")
            continue
        nxt = RECOGNITION_NEXT.get(rec.get("recognition", "struggled"))
        if nxt is None:
            lines.append(f"{key} heard in the tape — already solid, kept")
            continue
        rec["recognition"] = nxt
        lines.append(f"{key} heard unprompted → {nxt.upper()}")
    return lines


def handle_catch_reply(knock: dict, reply_text: str, klog: list,
                       lexicon: dict, dry_run: bool):
    """The eavesdrop counterpart of the production flow below: judge the drift,
    move recognition, log the exchange in the same shape (chat.md and the
    outcome memory read it unchanged), push one line back. No chains, no
    volley, no production meters."""
    print(f"1. judging DRIFT reply against eavesdrop knock {knock.get('timestamp', '?')[:16]}…")
    verdict = judge_catch(knock, reply_text, klog)
    print(f"   → {verdict['verdict']} | {verdict.get('rationale', '')}")
    verdict = ensure_voice(verdict, reply_text, lambda: judge_catch(
        knock, reply_text, klog, force_voice=True))

    if dry_run:
        print(f"[dry-run] would apply, then push: {verdict['reply_line']}")
        return

    print("2. state…")
    for line in apply_catch_verdict(verdict, knock, lexicon):
        print(f"   {line}")
    for line in apply_heard_words(verdict, knock, lexicon, reply_text):
        print(f"   {line}")

    knock["response"] = "reply"
    knock["reply"] = reply_text
    knock["reply_verdict"] = verdict["verdict"]
    # SAME READ-SURFACE LAW AS EVERY OTHER PUSH-BACK (2026-09-02). This path — the
    # eavesdrop/catch reply — pushed the judge's raw line to the lock screen while
    # the main reply path (below) transformed its own. Andrew cannot read Tamil
    # script in a notification; he reported it twice on 2026-08-02, and `s59`
    # guards the knock lane's body for exactly that reason. The gap survived
    # because no case asserted the CATCH path, and it stopped being theoretical
    # when `voice_canon` began handing this judge a dialect file written in Tamil
    # script immediately before asking it for a line Andrew reads.
    knock["reply_line"] = to_phonetic(verdict["reply_line"], label="catch push-back")
    knock["reply_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    knock.setdefault("exchanges", []).append({
        "at": knock["reply_at"], "reply": reply_text,
        "verdict": verdict["verdict"], "fired": [],
        "reply_line": knock["reply_line"],
    })
    save_json(LEXICON_PATH, lexicon)
    save_json(KNOCK_LOG_PATH, klog)

    voice_url, vmp3 = speak(verdict, knock, klog)
    meta = record_meta_note(verdict)

    print("3. commit + push…")
    # the line only — no meter tail (see catch_meter's grave). `requested`: he
    # replied to a knock, so answering him is not an interruption and the
    # quiet-hours chokepoint must not swallow it (2026-07-26).
    commit_and_push(*publish(
        [LEXICON_PATH, KNOCK_LOG_PATH, FEEDBACK_LOG_PATH if meta else None],
        f"Knock reply: {verdict['verdict']} (eavesdrop)",
        mp3=vmp3 if voice_url else None))
    print("4. push back…")
    # the LOGGED line, not the draft — the log must record what he was actually
    # sent (`s59`), and pushing `verdict[...]` here would have re-introduced the
    # raw script one line after it was transformed.
    push_to_phone(knock["reply_line"], voice_url,
                  knock_id=knock.get("timestamp", ""), requested=True)
    print(f"done — drift judged, catch axis scored, "
          f"answered{' (aloud 🎧)' if voice_url else ''}.")


def last_fired_knock(klog: list) -> dict | None:
    fired = [k for k in klog if k.get("acted", True)]
    return fired[-1] if fired else None


def answers_the_open_ask(text: str, knock: dict, lexicon: dict) -> bool:
    """Does this line contain the thing the open knock actually asked for?

    The escalation net under the intent tag: a tagless line that answers the open
    ask is a REP whichever button he pressed, so it goes to a judge rather than
    to the message lane. Substring match against the lexicon's OWN phonetic forms
    — Python-owned, no model, no inference. It is deliberately narrow: it can
    only ever pull something back INTO grading, never push a request out of it."""
    target, _ = current_pin(knock)
    key = resolve(target, lexicon, build_phonetic_index(lexicon)) if target else None
    if not key:
        return False
    forms = [key] + list((lexicon.get(key) or {}).get("phonetic") or [])
    low = text.lower()
    return any(f and f.lower() in low for f in forms)


def is_message(knock_id: str, intent: str, text: str,
               knock: dict | None, lexicon: dict) -> bool:
    """Reply to be judged, or message to be acted on? Deterministic, from the tag.

    The phone supplies the one bit no machine can infer, at the moment Andrew
    already knows it (docs/home_assistant_knock_buttons.md §8.5):

      knock_id present   → a reply to THAT knock          (notification Reply)
      intent == "reply"  → a reply to the last fired knock (Shortcut → Reply)
      otherwise          → a MESSAGE

    An untagged arrival is a message, not a reply. That default is deliberate and
    it is the safe one: grading a request costs a refusal and a corrupted ledger
    row, while treating a rep as a message costs one uncredited cold fire, which
    the net above mostly recovers anyway. It is also LOUD — a silent changeover
    that quietly stopped grading his reps would be the original bug wearing new
    clothes (2026-08-28)."""
    if knock_id or intent == "reply":
        return False
    if not intent:
        print("   ⚠ no intent tag — assuming message (Shortcut changeover 2026-08-28)")
    if knock and answers_the_open_ask(text, knock, lexicon):
        print("   ↩ it answers the open ask — grading it as a reply")
        return False
    return True


def find_knock(klog: list, knock_id: str) -> dict | None:
    """The knock a reply belongs to, by its log timestamp (= the notification's
    action_data.knock_id, round-tripped through HA). Notifications stack since
    2026-07-11, so answering an older one is legal — last-fired is only the
    fallback for id-less events (pre-migration notifications, manual runs)."""
    if not knock_id:
        return None
    for k in reversed(klog):
        if k.get("acted", True) and k.get("timestamp") == knock_id:
            return k
    return None


def scoreboard(lexicon: dict) -> str:
    """The fast per-day reward appended to a push-back: fires today, live from
    the logs. A COUNT OF WHAT HE DID, never a fraction of what is left.

    It read "Deck 36/71 · -6d" until 2026-08-18 — a deficit fraction and a
    countdown, on the one surface he cannot look away from. That is the object
    `catch_meter` was deleted for on 08-17 (see the note above `handle_catch_reply`),
    still live on the production path because that path composed it from
    `compute_deck` instead. Both are gone now: the deck retired, and what stays is
    the half that is not a scoreboard — a mastery-driven learner can be told he
    fired four things today without being told how far he is from an end."""
    n = fires_today()
    return f"{n} fired today" if n else ""


def hours_since_exchange(knock: dict, now: datetime) -> float | None:
    """Hours since this knock last spoke to Andrew — the later of the knock
    itself and the last judged exchange on it. The judge reads this to decay
    scenario continuity: past ~3h he's answering a lock-screen line cold, not
    continuing the scene (2026-07-05 feedback)."""
    ts = knock.get("reply_at") or knock.get("timestamp")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 3600


def volley_open_ask(knock: dict) -> str | None:
    """The CURRENT volley ask as 'N/M — <ask>', or None outside a volley.
    Python owns this string everywhere it surfaces (judge context, chat
    re-presents). KF-11 root cause lived here: the logged body stays frozen at
    ask 1 while the pin walks, so handing the raw body to the judge made every
    later item read as a KF-3 mis-target — and the coherence safety net then
    LAWFULLY voided the pin and recast item 1's answer."""
    vq = knock.get("volley")
    if not vq:
        return None
    cur = min(knock.get("volley_next", 1), len(vq))
    return f"{cur}/{len(vq)} — {vq[cur - 1]['ask']}"


# one re-ask, a false negative costs him a push he asked for and never got.









def judge(knock: dict, reply_text: str, target_record: dict | None,
          hours_since: float | None = None,
          revealed_recent: list | None = None,
          force_schedule: bool = False,
          force_voice: bool = False,
          klog: list | None = None) -> dict:
    canon = voice_canon()
    pin, pin_revealed = current_pin(knock)
    open_ask = volley_open_ask(knock)
    context = {
        "knock": {
            "modality": knock.get("modality"),
            "move": knock.get("move"),
            "notification_body": f"volley {open_ask}" if open_ask else knock.get("body", ""),
            "memo_script": knock.get("memo_script", ""),
            "expected_target": pin,
            "target_revealed": pin_revealed,
        },
        "hours_since_last_exchange": round(hours_since, 1) if hours_since is not None else None,
        "expected_target_lexicon_record": target_record,
        "revealed_recently": revealed_recent or [],
        "andrew_reply": reply_text,
        # Tags already on the ledger, so the judge matches an existing pattern
        # instead of coining a synonym for it. Counting is by exact string, so
        # `past-tense` and `wrong-tense` as two rows would hide the very
        # recurrence the ledger exists to expose — this is the cheap guard, and
        # it costs nothing when the ledger is empty.
        # Live AND retired-unverified tags. The retired ones matter most: a
        # pattern coming back after going quiet is the single most informative
        # event the ledger records, and it is only visible if the judge reuses
        # the old tag instead of coining a synonym for it — a new slug would
        # file the return as a brand-new one-off and hide the whole recurrence.
        "slip_tags_in_use": [
            {"tag": p["tag"], "seen": p["count"], "means": p["notes"][-1] if p["notes"] else "",
             "state": "live" if p["live"] else "retired — reuse this tag if it returns"}
            for p in slip_patterns() if p["live"] or p["unverified"]][:12],
    }
    if knock.get("volley"):
        context["knock"]["volley_in_progress"] = (
            f"item {min(knock.get('volley_next', 1), len(knock['volley']))} of {len(knock['volley'])}")
    # The recent thread across knocks, carrying what Anna DID and not only what
    # he wrote (recent_exchanges). Tamil already handed to him is still a
    # read-back rather than a cold fire — but that judgment belongs to
    # revealed_recent/shown_in_knock, which are Python-owned and unchanged.
    prior = recent_exchanges(klog if klog is not None else [knock], knock)
    if prior:
        context["prior_exchanges"] = prior
    mandate = (JUDGE_MANDATE + "\n" + SLIP_MANDATE + "\n" + REACH_MANDATE
               + "\n" + THREAD_MANDATE + "\n" + VOICE_MANDATE
               + (FORCE_SCHEDULE_ADDENDUM if force_schedule else "")
               + (FORCE_VOICE_ADDENDUM if force_voice else ""))
    # 1600 is what the ARTIFACT needs — an 11-key schema plus a slip-ledger tag
    # match — and nothing else. The thinking room is added by `budget()`, inside
    # `ask_json`. This number was 800 until 2026-08-05, when the call spent ~750
    # tokens deliberating in prose and was cut off mid-word before its first
    # brace. The fix then was to raise this one literal, which was right for this
    # lane and left every other one wrong: on 2026-08-18 the same failure took
    # the knock lane and the drill sheet down together. Reasoning cost belongs to
    # the model, so it lives with the model (`writer.budget`).
    print(f"   [judge] {executor_name()}")
    d = ask_json(canon + "\n\n---\n\n" + mandate,
                 json.dumps(context, ensure_ascii=False, indent=2),
                 JUDGE_SCHEMA, answer_tokens=1600)
    return normalize_verdict(d, reply_text)


_FLATTEN_RE = re.compile(r"[^\w]+", re.UNICODE)


def flatten_for_match(s: str) -> str:
    """Casefold, punctuation → space, runs collapsed. Loose enough that quoting
    'Oru nimsham.' matches 'oru nimsham' in his reply; strict enough that the
    letters must actually be there."""
    return _FLATTEN_RE.sub(" ", (s or "").casefold()).strip()


def said_in_reply(said: str, reply_text: str) -> bool:
    """Did Andrew actually type this? The credit-side twin of shown_in_knock.

    That guard is asymmetric — it can only DEMOTE a fire the knock revealed.
    Nothing checked that a fired word appeared in his reply at all, so the judge
    was free to credit the target it wanted. 2026-07-27 volley: reply "Oru
    nimsham" fired கொஞ்சம் + நில்லுங்க — a phrase containing neither — and Python
    derived a COLD headline from it, pushing back "நில்லுங்க fired cold 🔥" for a
    word he never said, while his real substitution (ஒரு நிமிஷம், production
    'none') scored nothing. Credit belongs to the word he used.

    Python owns the honesty check, not the matching: he types 'nimsham' where the
    lexicon stores 'nimisham', so a deterministic phonetic match would strip
    legitimate credit. The judge names the canonical key AND quotes the span; this
    verifies the span is his."""
    flat_reply = flatten_for_match(reply_text)
    flat_said = flatten_for_match(said)
    return bool(flat_said) and bool(flat_reply) and flat_said in flat_reply



def normalize_verdict(d: dict, reply_text: str = "") -> dict:
    """Guard the judge's JSON into the shape Python relies on. Per-word verdicts
    (2026-07-03): each fired item carries its own cold/hinted grade — one flat
    grade flattened multi-word replies. The reply's overall verdict is DERIVED
    (best word wins) so the log and chain never contradict the axis; a scored
    verdict with no fired words degrades to "miss" (nothing creditable, no chain
    padding — fires_today and the burn rate count reply_fired).

    Credit is verified against his reply (2026-07-27): a fired word whose "said"
    span is not literally in reply_text is DROPPED, not scored — see
    said_in_reply(). The word itself is accepted as its own evidence (he replied
    in script, or the judge quoted nothing), so a judge that forgets the field
    still credits an on-the-nose Tamil reply. Dropped fires land on
    d["unverified"] so the failure is loud in the run log, never silent."""
    if d.get("verdict") not in VERDICTS:
        d["verdict"] = "chat"
    fired, unverified = [], []
    for item in d.get("fired", []):
        if isinstance(item, str):  # tolerate the pre-per-word flat shape
            item = {"word": item, "verdict": d["verdict"]}
        if not isinstance(item, dict):
            continue
        w = (item.get("word") or "").strip()
        if not w:
            continue
        said = (item.get("said") or "").strip()
        if reply_text and not (said_in_reply(said, reply_text)
                               or said_in_reply(w, reply_text)):
            unverified.append(f"{w} (claimed {said!r})" if said else f"{w} (no span)")
            continue
        v = item.get("verdict") if item.get("verdict") in ("cold", "capped") else "hinted"
        fired.append({"word": w, "said": said or w, "verdict": v})
    # Slips: the structured error record. Guard the shape here so a judge that
    # returns junk cannot poison the ledger — a tag is mandatory (Python counts
    # by it), everything else is best-effort prose.
    slips = []
    for s in d.get("slips", []) or []:
        if not isinstance(s, dict):
            continue
        tag = (s.get("tag") or "").strip()
        if not tag:
            continue
        slips.append({"tag": tag, "said": (s.get("said") or "").strip(),
                      "want": (s.get("want") or "").strip(),
                      "note": (s.get("note") or "").strip()})
    d["slips"] = slips

    # A word the judge corrected cannot also be a word it credited. The mandate
    # says so; Python enforces it, because the mandate said "credit what he said"
    # since 07-27 and the 07-30 volley still fired ரொம்ப நல்லா இருக்கு off a reply
    # whose own recast fixed its tense. Matching is on the flattened `want` —
    # against both the fired key and the span he typed, so it catches the case
    # where the judge names the canonical key and quotes his phonetic attempt.
    corrected = {flatten_for_match(s["want"]) for s in slips if s["want"]}
    if corrected:
        kept = []
        for item in fired:
            hit = next((c for c in corrected
                        if c and (c == flatten_for_match(item["word"])
                                  or c == flatten_for_match(item["said"]))), None)
            if hit:
                unverified.append(f"{item['word']} (corrected in the same breath — "
                                  f"slipped, not fired)")
                continue
            kept.append(item)
        fired = kept

    d["unverified"] = unverified
    d["fired"] = fired if d["verdict"] in ("cold", "hinted") else []
    if d["fired"]:
        d["verdict"] = ("cold" if any(i["verdict"] == "cold" for i in d["fired"])
                        else "hinted")
    elif d["verdict"] in ("cold", "hinted"):
        d["verdict"] = "miss"
    d["reply_line"] = (d.get("reply_line") or "").strip()
    d["meta_note"] = (d.get("meta_note") or "").strip()
    d["follow_up_ask"] = (d.get("follow_up_ask") or "").strip()
    d["follow_up_target"] = (d.get("follow_up_target") or "").strip()
    d["follow_up_target_revealed"] = bool(d.get("follow_up_target_revealed", True))
    d["voice_reply"] = (d.get("voice_reply") or "").strip()
    d["schedule"] = d.get("schedule") if isinstance(d.get("schedule"), dict) else None
    return d


def shown_in_knock(key: str, rec: dict, knock: dict) -> bool:
    """Deterministic check of the hard rule: did the knock's own text — or a
    recast Anna already pushed back on an earlier reply — show this Tamil
    (script or any known phonetic)? Shown ⇒ the reply caps at 'hinted'.
    Scans the WHOLE chain, not just the last recast."""
    parts = [knock.get("body", ""), knock.get("memo_script", ""),
             knock.get("reply_line", "")]
    parts += [x.get("reply_line", "") for x in knock.get("exchanges", [])]
    shown = " ".join(p for p in parts if p).lower()
    if key.lower() in shown:
        return True
    return any(p.lower() in shown for p in rec.get("phonetic", []) if p)


def current_pin(knock: dict) -> tuple[str, bool]:
    """What this knock is asking for RIGHT NOW: the chained follow-up pin when
    one exists, else the original ask. A chain moves the pin without touching
    expected_target — the original ask stays on record (before 2026-07-06 the
    chain overwrote it, which made the log unreadable for audits)."""
    if knock.get("pinned_target") is not None:
        return knock["pinned_target"], bool(knock.get("pinned_revealed", True))
    return knock.get("expected_target", ""), bool(knock.get("target_revealed", True))


def revealed_recently(klog: list, lexicon: dict, hours: float = 48.0) -> list[str]:
    """Lexicon keys whose Tamil (script or any phonetic) actually appeared in
    the last `hours` of knock traffic — bodies, memo scripts, recasts, whole
    chains. The judge may deny a cold as "recently handed to him" ONLY for
    words on this list: Python owns the evidence of what was shown; trusting
    the model's memory denied a real cold (the 2026-07-04 'podhum' case)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    texts = []
    for k in klog:
        ts = _ts(k.get("timestamp"))
        if ts is None or ts < cutoff:
            continue
        texts += [k.get("body", ""), k.get("memo_script", ""), k.get("reply_line", "")]
        texts += [x.get("reply_line", "") for x in k.get("exchanges", [])]
    blob = " ".join(t for t in texts if t).lower()
    if not blob:
        return []
    out = []
    for key, rec in lexicon.items():
        probes = [key] + [p for p in rec.get("phonetic", []) if p]
        if any(p.lower() in blob for p in probes):
            out.append(key)
    return sorted(out)


GRADUATION_DAYS = 2  # distinct local days of capped-quality fires that prove a word cold


def capped_fire_days(key: str, klog: list) -> set:
    """Local dates on which `key` fired CAPPED (cold-quality, reveal-blocked) in
    judged knock traffic — the graduation evidence, computed from the log the
    same way revealed_recently() computes reveals (never from model memory)."""
    from state_io import LOCAL_TZ
    days = set()
    for k in klog:
        for x in k.get("exchanges", []):
            dt = _ts(x.get("at")) if key in x.get("fired_capped", []) else None
            if dt is not None:
                days.add(dt.astimezone(LOCAL_TZ).date())
    return days


def apply_verdict(verdict: dict, knock: dict, lexicon: dict, klog: list,
                  revealed_recent: list | None = None,
                  ) -> tuple[list[str], list[str], list[str], list[str]]:
    """Move the production axis for what fired — each word on its OWN grade
    (per-word verdicts, 2026-07-03). Upgrades only — a phone rep never demotes
    (chat sessions own corrections).

    The capped lane (2026-07-08): a cold-quality fire the reveal window blocks
    is recorded CAPPED instead of flattened into hinted, and Python resolves
    every capped/cold grade against the computed reveal evidence (KF-6): a
    shown "cold" downgrades to capped; a "capped" with no reveal on record
    upgrades to cold. Capped fires on GRADUATION_DAYS distinct local days
    graduate the word to cold — repeated unaided production across sleeps is
    exactly the evidence the reveal window exists to demand; without this, a
    daily-knocked word could never escape hinted through the very channel
    drilling it.

    Returns (summary lines, cold-credited keys — true colds plus graduations,
    the pace meters read these —, capped keys, graduated keys)."""
    phon_index = build_phonetic_index(lexicon)
    today = local_today().isoformat()
    today_local = local_today()
    pin, pin_revealed = current_pin(knock)
    revealed_key = resolve(pin, lexicon, phon_index) if pin_revealed else None
    revealed_recent = revealed_recent or []
    summary, cold_credited, capped_keys, graduated = [], [], [], []
    for item in verdict["fired"]:
        key = resolve(item["word"], lexicon, phon_index)
        if key is None:
            summary.append(f"! '{item['word']}' resolves to no lexicon record — not scored")
            continue
        rec = lexicon[key]
        grade = item["verdict"]
        shown = key == revealed_key or shown_in_knock(key, rec, knock)
        if grade == "cold" and shown:
            grade = "capped"  # the hard rule, enforced deterministically per word
        elif grade == "capped" and not (shown or key in revealed_recent):
            grade = "cold"  # the judge invented a reveal — the computed evidence says unaided
        target = grade
        if grade == "capped":
            capped_keys.append(key)
            days = capped_fire_days(key, klog) | {today_local}
            if len(days) >= GRADUATION_DAYS:
                target = "cold"  # graduation: unaided-quality fires across distinct days
                if rec.get("production") != "cold":
                    graduated.append(key)
            else:
                target = "hinted"  # capped rides the hinted rung until it graduates
        if target == "cold":
            cold_credited.append(key)  # a re-fire of an already-cold word still counts as pace
        cur = rec.get("production", "none")
        if PRODUCTION_RANK[target] > PRODUCTION_RANK.get(cur, 0):
            rec["production"] = target
            grad = " 🎓 graduated — capped fires on ≥2 days" if key in graduated else ""
            summary.append(f"{key} → {target.upper()}{grad}")
        else:
            summary.append(f"{key} already {cur} — kept ({grade} fire)")
        rec["last_surfaced"] = today
        # The knock half of the rep ledger (2026-07-26): every word in a judged
        # reply's fired list is a DECLARED production — any verdict, partial
        # counts. This counter replaced mining Anna's prose for mentions.
        rec["reps"] = rec.get("reps", 0) + 1
    return summary, cold_credited, capped_keys, graduated






def main():
    ap = argparse.ArgumentParser(description="Judge a phone reply to the last knock")
    ap.add_argument("reply", help="Andrew's reply text (phonetic Tamil, from the notification)")
    ap.add_argument("--dry-run", action="store_true",
                    help="judge + print only; no state writes, commit, or push-back")
    args = ap.parse_args()

    load_env(BASE / ".env")
    reply_text = args.reply.strip()
    if not reply_text:
        print("Empty reply — nothing to judge.")
        return

    klog = load_json(KNOCK_LOG_PATH) or []
    knock_id = os.environ.get("REPLY_KNOCK_ID", "").strip()
    knock = find_knock(klog, knock_id) or last_fired_knock(klog)
    if knock is None:
        print("No fired knock to judge a reply against — logging nothing.")
        return
    if knock_id and knock.get("timestamp") != knock_id:
        print(f"   ⚠ knock_id {knock_id!r} not in the log — falling back to last fired")

    lexicon = load_json(LEXICON_PATH) or {}

    if is_message(knock_id, os.environ.get("REPLY_INTENT", "").strip().lower(),
                  reply_text, knock, lexicon):
        handle_message(reply_text, knock, klog, args.dry_run)
        return

    if knock.get("modality") == "eavesdrop":
        # Comprehension dose — the reply grades the CATCH axis, on its own
        # smaller mandate; nothing below (reveal caps, chains, volley walk,
        # production meters) applies to a drift answer.
        handle_catch_reply(knock, reply_text, klog, lexicon, args.dry_run)
        return

    phon_index = build_phonetic_index(lexicon)
    target, _ = current_pin(knock)
    target_key = resolve(target, lexicon, phon_index) if target else None
    target_record = None
    if target_key:
        r = lexicon[target_key]
        target_record = {"script": target_key, "gloss": r.get("gloss", ""),
                         "phonetic": r.get("phonetic", [])}

    hours = hours_since_exchange(knock, datetime.now(timezone.utc))
    hours_str = f", {hours:.1f}h since last exchange" if hours is not None else ""
    print(f"1. judging reply against knock {knock.get('timestamp', '?')[:16]} "
          f"({knock.get('modality')}/{knock.get('move')}{hours_str})…")
    revealed = revealed_recently(klog, lexicon)
    verdict = judge(knock, reply_text, target_record, hours, revealed, klog=klog)
    fired_str = ", ".join(f"{i['word']}:{i['verdict']}" for i in verdict["fired"]) or "—"
    print(f"   → {verdict['verdict']} | fired: {fired_str} | {verdict.get('rationale', '')}")
    for claim in verdict.get("unverified", []):
        print(f"   ⚠ dropped — not in his reply: {claim}")

    # The clock-request backstop: a time-bound ask that came back with no
    # schedule gets exactly one forced re-ask. Cheap (one call, rare) and it
    # closes the gap that swallowed the 9am greeting — the mandate alone had
    # already told Anna scheduling was "usual to skip", so prose could not fix
    # prose here.
    if wants_scheduled_push(reply_text) and not verdict.get("schedule"):
        print("   ⏰ time-bound request with no schedule — re-asking once, forced…")
        forced = judge(knock, reply_text, target_record, hours, revealed,
                       force_schedule=True, klog=klog)
        if forced.get("schedule"):
            verdict = forced
            print(f"   → scheduled: {forced['schedule'].get('at_local')} "
                  f"· {forced['schedule'].get('body', '')[:60]}")
        else:
            print("   ⚠ still no schedule — logging the miss to the ledger")
            verdict["meta_note"] = (verdict.get("meta_note") or "").strip() or (
                f"MISSED SCHEDULE: Andrew asked for something at a time "
                f"({reply_text[:80]!r}) and no push was queued — the judge "
                f"declined twice. Check the schedule lane.")

    verdict = ensure_voice(verdict, reply_text, lambda: judge(
        knock, reply_text, target_record, hours, revealed,
        force_voice=True, klog=klog))

    # Momentum chain: on a scored reply, the push-back may carry the NEXT micro-ask.
    # The knock's expected target moves to the chained one, so the next reply is
    # judged against what was actually asked (prior_exchange covers the recast).
    # A VOLLEY knock chains DETERMINISTICALLY instead: Python hands the next deck
    # item on ANY judged verdict (miss = recast-and-move, the blitz law) and the
    # judge's own follow_up is ignored — finite by construction, no CHAIN_CAP.
    follow, volley_pin = "", None
    vq = knock.get("volley")
    # `represent` — KF-11: deterministic re-present of the still-open ask.
    # `held` — KF-13 (2026-08-04): "chat" is the ONLY verdict that holds the pin, so a
    # single mislabelled answer re-presents the same item for ever. The 08-04 backchannel
    # volley died that way: "ama ama" WAS item 1's target, came back "chat", and Andrew
    # burned six exchanges seeing 1/4 and 3/4 again while item 4 was never reached. The
    # mandate now defines "chat" relationally, but a wording fix cannot be the only guard
    # on a deadlock — so cap the hold at one re-present, whatever the judge decides.
    # Read off `exchanges` rather than a counter field (KF-6's rule: Python computes from
    # the log, never from model memory). The marker is Python's OWN "still open · " prefix
    # (written at the reply_line join below), not the verdict — a capped advance is itself
    # still a "chat", so keying on the verdict would make every later chat advance again
    # and the freshly-pinned item would never get its own re-present. This exchange is not
    # appended until further below, so [-1] is genuinely the prior turn.
    represent, held = None, "still open · " in ((knock.get("exchanges") or [{}])[-1].get("reply_line") or "")
    if vq:
        # A capped advance keeps the "chat" verdict: nothing is credited and no state
        # moves — it only refuses to ask the same question a third time.
        if verdict["verdict"] != "chat" or held:
            nxt = knock.get("volley_next", 1)
            if nxt < len(vq):
                volley_pin = vq[nxt]
                follow = f"{nxt + 1}/{len(vq)} — {volley_pin['ask']}"
            else:
                knock["volley_done"] = True  # last item judged — chain closed
        elif not knock.get("volley_done"):
            # KF-11 (2026-07-18): a chat/meta reply mid-volley must never let the
            # open ask vanish from the surface. Python owns the chain; Python
            # re-presents it (same owner as the judge's context: volley_open_ask).
            represent = f"still open · {volley_open_ask(knock)}"
    elif (verdict["verdict"] in ("cold", "hinted") and verdict["follow_up_ask"]
            and knock.get("chained", 0) < CHAIN_CAP):
        follow = verdict["follow_up_ask"]

    if args.dry_run:
        chain_str = f" ↪ chain: {follow}" if follow else ""
        print(f"[dry-run] would apply, then push: {verdict['reply_line']} · {scoreboard(lexicon)}{chain_str}")
        return

    print("2. state…")
    summary, cold_credited, capped_keys, graduated = apply_verdict(
        verdict, knock, lexicon, klog, revealed)
    for line in summary:
        print(f"   {line}")

    # Top-level reply fields are the LATEST-exchange view (outcome memory and
    # legacy renders read them); the full history lives in `exchanges` below.
    knock["response"] = "reply"  # the strongest "landed" signal there is
    knock["reply"] = reply_text
    knock["reply_verdict"] = verdict["verdict"]
    # accumulate across a chain — fires_today reads reply_fired (every scored
    # word); the cold pace meter reads reply_fired_cold (effective grade after
    # the revealed-cap, per word)
    fired_words = [i["word"] for i in verdict["fired"]]
    knock["reply_fired"] = knock.get("reply_fired", []) + fired_words
    knock["reply_fired_cold"] = knock.get("reply_fired_cold", []) + cold_credited
    knock["reply_fired_capped"] = knock.get("reply_fired_capped", []) + capped_keys
    # store the FULL push-back (recast + chained ask): the next judge call reads it
    # as a prior exchange, and shown_in_knock scans it for revealed Tamil
    # Same read-surface law as a knock body (2026-08-03) — covers the chained ask
    # and the volley re-present too, both of which carry deck Tamil.
    knock["reply_line"] = to_phonetic(
        " · ".join(p for p in (verdict["reply_line"], follow or represent) if p),
        label="push-back")
    knock["reply_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sched = verdict.get("schedule") or {}
    knock.setdefault("exchanges", []).append({
        "at": knock["reply_at"], "reply": reply_text,
        "verdict": verdict["verdict"], "fired": fired_words,
        "fired_cold": cold_credited, "fired_capped": capped_keys,
        "graduated": graduated, "reply_line": knock["reply_line"],
        "slips": [s["tag"] for s in verdict.get("slips") or []],
        # What Anna DID this turn, not just what he wrote (2026-08-02). The
        # record used to hold words only, so the next turn could not tell a
        # delivered artefact from a promise to deliver one — Anna sent a whole
        # audio greeting and called it "still pending" sixty seconds later.
        # `audio_url` is backfilled below, after the render actually succeeds.
        "spoke": verdict.get("voice_reply") or "",
        "scheduled": " · ".join(v for v in (sched.get("at_local", ""),
                                            sched.get("move", "")) if v),
    })

    # The slip ledger — the phone lane's half. This is the seam that did not
    # exist: knock corrections lived only as prose in reply_line, which nothing
    # read as error signal, so a mistake made on the phone could never reach the
    # next lesson's selection. Written through sync_state because sync_state owns
    # every write to progress/ (LLM is the writer, Python is the brain).
    if verdict.get("slips"):
        learner_now = load_json(LEARNER_PATH) or {}
        from state_io import LOCAL_TZ
        written = append_slips(
            verdict["slips"], lane="knock", modality=knock.get("modality", ""),
            dose_channel=(learner_now.get("soak_order") or {}).get("channel", ""),
            when=datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().isoformat())
        for row in written:
            print(f"   slip: {row['tag']} — “{row['said']}” → “{row['want']}”")
        repeated = {p["tag"]: p for p in slip_patterns() if p["pattern"] and p["live"]}
        for row in written:
            p = repeated.get(row["tag"])
            if p:
                print(f"   ⚠ {p['tag']} is {p['count']}× over {p['span_days']}d "
                      f"— pattern, not a one-off"
                      + ("; NEVER COMMISSIONED" if p["uncommissioned"]
                         else f"; ESCALATE past {p['channels'][0]}" if p["escalate"]
                         else ""))
    if volley_pin is not None:
        # Volley advance is Python's: the pin walks the queue Python composed;
        # expected_target stays the original first ask (auditable, 2026-07-06 law).
        knock["chained"] = knock.get("chained", 0) + 1
        knock["volley_next"] = knock.get("volley_next", 1) + 1
        knock["pinned_target"] = volley_pin["target"]
        knock["pinned_revealed"] = False
    elif follow:
        # The chain moves the PIN; expected_target stays the original ask so the
        # log stays auditable (overwriting it here was the 2026-07-06 bug).
        knock["chained"] = knock.get("chained", 0) + 1
        knock["pinned_target"] = verdict["follow_up_target"]
        knock["pinned_revealed"] = verdict["follow_up_target_revealed"]

    save_json(LEXICON_PATH, lexicon)
    save_json(KNOCK_LOG_PATH, klog)

    # A phone graduation opens a focus seat — reconcile the stored cohort at
    # this write seam exactly as cmd_update does at the session seam.
    from suggest_targets import reconcile_focus  # lazy: keeps module import light
    learner = load_json(LEARNER_PATH) or {}
    new_cohort = reconcile_focus(lexicon, learner.get("focus_cohort", []))
    cohort_changed = set(new_cohort) != set(learner.get("focus_cohort", []))
    if cohort_changed:
        learner["focus_cohort"] = new_cohort
        save_json(LEARNER_PATH, learner)
        print(f"   focus cohort reconciled ({len(new_cohort)} seats held)")

    # Anna may answer ALOUD. Rendered before the commit below because
    # push_to_phone pre-warms the jsDelivr URL and the CDN can only serve a path
    # already on main — knock_reply already commits before it notifies, so the
    # mp3 just rides the existing commit.
    # .get, not [], so any caller that hands us an un-normalised verdict (the
    # smoke harness stubs judge() directly) simply gets a silent text reply.
    voice_url, vmp3 = speak(verdict, knock, klog)

    # Meta-direction lands in the feedback ledger — the diagnosis pass reads it.
    meta = record_meta_note(verdict)

    print("3. commit + push…")
    score = scoreboard(lexicon)
    body = " · ".join(p for p in (knock["reply_line"], score) if p)
    if len(body) > 240:
        print(f"   ⚠ push-back is {len(body)} chars — the lock screen will cut the tail (chained ask at risk)")
    # The slip ledger is written on the runner; unpushed it dies with the
    # container and the accumulation this whole mechanism exists for never
    # happens. `knock_id` is the chain's own: a reply to this push-back
    # correlates to the same knock entry.
    commit_and_push(*publish(
        [LEXICON_PATH, KNOCK_LOG_PATH,
         LEARNER_PATH if cohort_changed else None,
         SLIP_LOG_PATH if verdict.get("slips") else None,
         FEEDBACK_LOG_PATH if meta else None,
         maybe_enqueue_schedule(verdict)],
        f"Knock reply: {verdict['verdict']} ({', '.join(fired_words) or 'no fire'})",
        mp3=vmp3 if voice_url else None))
    print("4. push back…")
    push_to_phone(body, voice_url, knock_id=knock.get("timestamp", ""), requested=True)
    print(f"done — reply judged, scored, answered{' (aloud 🎧)' if voice_url else ''}.")


if __name__ == "__main__":
    main()
