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
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from render_chat import render_chat
from morning_knock import KNOCK_LOG_PATH, maybe_enqueue_schedule, render_memo
from publish import (KNOCKS_DIR, commit_and_push, jsdelivr_url, load_env,
                     push_to_phone, refresh_feed)
from render_audio import ANNA_VOICE
from writer import BOOL, STR, arr, ask_json, executor_name, obj, to_phonetic

# Each judge declares its OWN top-level shape, beside itself (2026-08-23) —
# never a shared or generic one, which is how `claude -p` came back with an
# envelope and a lane rendered a shell with every instrument green. Keys mirror
# the mandates below. `schedule` is absent because the mandate declares it
# nullable and `obj()` requires whatever it names; undeclared keys still pass.
JUDGE_SCHEMA = obj(verdict=STR, fired=arr(word=STR, said=STR, verdict=STR),
                   reply_line=STR, follow_up_ask=STR, follow_up_target=STR,
                   follow_up_target_revealed=BOOL, meta_note=STR, rationale=STR)
CATCH_SCHEMA = obj(verdict=STR, reply_line=STR, meta_note=STR, rationale=STR)
from state_io import FEEDBACK_LOG_PATH, LEARNER_PATH, LEXICON_PATH, SLIP_LOG_PATH, build_phonetic_index, load_json, local_today, resolve, save_json
from slips import append_slips, slip_patterns
from sync_state import fires_today

PRODUCTION_RANK = {"none": 0, "hinted": 1, "cold": 2}
VERDICTS = {"cold", "hinted", "miss", "chat"}
CHAIN_CAP = 3  # max chained follow-up asks per knock — momentum, not a treadmill

JUDGE_MANDATE = """\
You are Anna, judging ONE phone reply from Andrew against the knock you sent him. \
This is the recast across the table, not an exam — generous in spirit, honest on the axis.

GRADES (per word — a multi-word reply is judged word by word, never as one lump; \
one shaky word must not drag down a clean one, and one clean word must not carry a \
scaffolded one):
- "cold"   — THAT word/chunk/frame is real Tamil the notification did NOT show him, \
produced unaided. Phonetic spelling is fine and expected ("poren" IS போறேன்); judge \
the Tamil, not the spelling.
- "hinted" — real Tamil, but it needed the knock's scaffold, or it's partially off \
but would land.
- "capped" — cold-QUALITY (clean, unaided THIS exchange) but the reveal window blocks \
cold: this knock/chain printed it, or it is on revealed_recently. Use it INSTEAD of \
"hinted" when the ONLY thing between the word and cold is the reveal. Python verifies \
every capped claim against the computed evidence and counts capped fires across days — \
enough distinct days graduates the word to cold (a word he keeps firing unaided across \
sleeps IS installed; without this lane the words knocked on daily could never escape \
hinted through the very channel drilling them).

"fired": one entry per Tamil word/chunk/frame the reply genuinely produced, each \
graded on its OWN merits: [{"word": ..., "said": ..., "verdict": "cold"|"capped"|"hinted"}, ...]. \
"word" in CANONICAL Tamil script — copy the expected-target record's exact script when \
it matches — or the frame:... key for a frame. Empty list when nothing creditable fired.

"verdict" — the reply as a whole (for the log and your reply_line's tone):
- "cold" / "hinted" — something fired; set it to the best word's grade (a capped word \
counts as hinted here; Python re-derives this from "fired" regardless).
- "miss" — he tried, but it's off enough that nothing would land at the table. Empty fired.
- "chat" — he did not engage the ask AT ALL (English chat, a question, logistics). Empty fired. No state moves. Decide this by RELATION to expected_target, never by the reply's SHAPE: \
a short backchannel that IS the target ("ama ama", "seri seri") is a rep, not chatter, and an answer buried in a complaint is still an answer — grade it. MID-VOLLEY "chat" FREEZES the item and re-presents it, so a wrong "chat" spends his rep and asks the same question twice.

HARD RULE: if the knock revealed the target Tamil (target_revealed=true), that word \
scores at most "hinted". Same for anything your own recast handed him in the \
prior_exchanges on this knock — echoing it back is a read-back, not a fire. Cold is \
unaided production only. (Python re-checks this per word.) The context's \
"revealed_recently" lists the Tamil ACTUALLY shown to him in the last 48h of knock \
traffic — computed from the log, not from memory. You may deny a cold as "I handed \
him that recently" ONLY when the word is on that list (or revealed by this knock / \
its prior_exchanges). If it is not listed and he produced it unaided, it is COLD — \
never invent a reveal.

CONTINUITY: how to read the thread you are in — THREAD_MANDATE, below.

COHERENCE SAFETY NET: if the knock's body asks one thing but expected_target names \
something that is not a natural answer to that body (a mis-targeted knock), the target \
is VOID — judge the reply against the body's own natural answers, and say so in \
rationale so the log shows the knock was malformed.

META-DIRECTION IS A FIRST-CLASS REPLY: hints, corrections, steering, and testimony \
("4 weeks instead of 1 month — was I right?", "this one's old muscle memory", "less of \
the aunty thing") are Andrew directing the SYSTEM, not failing a rep. Acknowledge in \
reply_line, APPLY it in this exchange (answer the actual question, adjust or drop the \
target/scenario, don't re-print a word he claimed), and write the one-line takeaway to \
"meta_note" so it lands in the feedback ledger for the diagnosis pass. Never answer \
direction with a grade alone. Testimony still never changes a grade — cold needs an \
unaided fire — so the honest path for a claimed word is an unrevealed ask in a FRESH \
context later: plant one via "schedule" a day or two out, or leave it to the wild.

CREDIT WHAT HE SAID, NOT WHAT YOU WANTED (2026-07-27): fire the lexicon key HIS OWN \
words produced, never the target he routed around. A socially coherent substitute is a \
real rep — "puriyala" for "enna sonneenga?", "oru nimisham" for "konjam nillunga", "ama, \
saapitten" while maama piles food: credit புரியல / ஒரு நிமிஷம் on their own merits, leave \
the untested target where it is, skip the lesson. Every fired entry carries "said" — the \
exact span of his reply that produced it, copied verbatim from andrew_reply. Python drops \
any fire whose "said" is not literally in his reply, so a word he never typed can never \
score. If you re-ask, pin the MEANING in English ("wave it off — 'enough!'") without \
showing the Tamil; a word you print can never fire cold this exchange.

"reply_line": the one line Anna pushes back. If he's off — recast the natural way and \
move on, no lecture ("close — we'd say 'poren'. adhu dhaan next time"); when the miss \
has a PATTERN behind it, the recast may carry ONE clause of why, by example, never \
terminology ("-nga — she's your elder") — one clause is a beat, two is a lecture (the \
Contrast Beat). If cold — celebrate, short ("adhu dhaan! 🔥"). He READS this, so every \
Tamil word in it is ENGLISH PHONETICS — never script (constitution.md's surface split; \
voice_reply is the spoken surface and keeps its script). Do NOT append any score — \
Python adds the deck line.

MOMENTUM CHAIN: if (and ONLY if) the verdict is "cold" or "hinted", you MAY ride the \
momentum with ONE follow-up micro-ask ("follow_up_ask"): a single short line handing \
the NEXT rep — an English situation that wants one Tamil line back, never re-asking \
what he just fired. Pin the situation to ONE natural answer (give the English meaning, \
not an open "what do you say?"). Leave the Tamil to him (follow_up_target_revealed=false is the \
strong form; a shown target caps at hinted). NEVER chain an ask for Tamil this exchange \
just revealed (your recast or the knock body) — it can only score hinted; that's a \
treadmill, not a rep. On "miss" or "chat" NO chain — the recast is the whole dose. \
Skipping the chain (empty strings) is often right; he replies when he replies. \
LOCK-SCREEN BUDGET: when you chain, reply_line is ONE short clause; reply_line + \
follow_up_ask together stay under ~200 chars (the scoreboard is appended after them) — \
a chained ask that gets cut off is an ask he never saw, and the next reply gets judged \
against a ghost.

VOLLEY KNOCK: when the knock context carries volley_in_progress, this is the daily \
deck blitz — one item per exchange, recast-and-move, no teaching between reps. Grade \
the current line only. Do NOT write follow_up_ask (Python appends the next volley item \
to your recast itself); keep reply_line to ONE short clause so the appended ask still \
fits the lock screen.

VOLLEY discipline (KF-11, 2026-07-18): grade ONLY against the current pinned item. On \
a miss, your recast reveals THAT item's answer — never a previous exchange's \
(prior_exchanges are context, not the subject). Never re-ask an earlier item, never \
declare the volley finished, and never claim a score your returned verdict doesn't \
produce — Python owns the chain and re-presents the open ask itself.

FIELDING dose (modality "fielding", 2026-07-18): the heard memo_script was a question \
fired AT him; grade the reply as its ANSWER — parsing the question is half the rep. A \
repair line back (புரியல, மெதுவா சொல்லுங்க) is a legitimate creditable fire: grade THAT \
production, never a miss.

Return ONLY a JSON object, no prose around it:
{
  "verdict": "cold" | "hinted" | "miss" | "chat",
  "fired": [{"word": "<canonical Tamil script or frame:... key>", "said": "<the exact span of andrew_reply that produced it>", "verdict": "cold" | "capped" | "hinted"}, ...],
  "reply_line": "<one line>",
  "follow_up_ask": "<one line chaining the next rep; empty string to stop>",
  "follow_up_target": "<the one word/chunk/frame it asks for (Tamil script or frame:... key); empty if no chain>",
  "follow_up_target_revealed": true | false,
  "slips": [{"tag": "<stable pattern name>", "said": "<his form>", "want": "<the right form>", "note": "<one clause>"}, ...],
  "meta_note": "<one line ONLY when the reply carried direction/correction/testimony for the system — it lands in the feedback ledger; empty string otherwise>",
  "voice_reply": "<spoken words when this answer wants to be HEARD; empty string otherwise — see REACH>",
  "schedule": {"at_local": "YYYY-MM-DDTHH:MM", "body": "<the full dose>", "memo_script": "<spoken words for a VOICE dose; empty for text>","expected_target": "<or empty>", "target_revealed": true | false, "move": "<2-4 words>"} | null,
  "rationale": "<one line, for the log>"
}
"""


# Split out of JUDGE_MANDATE (2026-08-02), the fourth time that file has paid for
# growth by splitting rather than raising: reading the conversation you are in is
# its own concern from grading a reply, and both judges — production and catch —
# need it identically. Provenance lives here, in a comment, not in the string: the
# model is not the audience for a changelog, and comments are budget-free.
THREAD_MANDATE = """\
--- THE THREAD: what continuity means, and what it does not ---

THE SCENE DECAYS; THE RECORD NEVER DOES. Past ~3 hours (hours_since_last_exchange) the \
scenario that knock was running is EXPIRED in his head: do not hold him to the chained \
ask, grade whatever Tamil fired as an open rep, and chain FRESH if you chain.

But prior_exchanges — the recent thread, ACROSS knocks — stays FACT, however old. Read \
it as one conversation. Resolve his pronouns and requests against it before anything \
else: "he doesn't know any Tamil", right after he asked you for something for someone \
else, is about THAT person, not about Andrew. Never re-introduce yourself, and never \
re-ask what he already told you, in a thread already running.

WHAT YOU DID IS ON THE RECORD — NEVER GUESS AT IT. A turn carrying "anna_sent_audio" \
means that audio was rendered and delivered, to his phone and his feed: do not call it \
pending, do not promise it again, and when he is correcting it ("too dense", "he can't \
read that"), fix it and send the NEW one. "anna_queued_push" means a push is really \
queued. Their ABSENCE is equally factual — an earlier turn that promised something and \
carries neither field delivered nothing, so say that plainly and do it now.
"""


SLIP_MANDATE = """\
--- SLIPS: the error record that outlives this exchange ---

Whenever you recast — ANY verdict, including a "hinted" that mostly landed — also return \
the mistake in "slips". The recast repairs this instance; the slip is what lets the \
system teach the thing underneath it later.

"tag" names the machine that failed, not this instance, and must stay STABLE across \
instances — Python counts recurrences by that exact string. `1pl-om` covers both \
"ponnam"→"ponnom" and "sappiten"→"saapittoom"; `past-tense` covers "irukku"→"irundhuchu"; \
`stranger-nga` covers "pesa"→"pesunga". The context lists tags already on the ledger — \
reuse one rather than coining a synonym. "said"/"want" are the two FORMS, not sentences; \
"note" is one clause, no terminology.

Return [] when nothing was wrong, when the miss is pure vocabulary never taught, or when \
he substituted a line that works — a substitution is signal to teach, not a slip (07-27). \
A wrong ENDING on a right word is always a slip: that is the gap this exists for.

A CORRECTED ITEM IS NOT A FIRE — a word you recast does not also go in "fired". Python \
drops any fire matching a slip's "want" (07-30: ரொம்ப நல்லா இருக்கு scored a hinted fire \
while the same line corrected its tense, so a wrong answer moved the axis and took a rep). \
Credit what landed; slip what didn't.
"""


REACH_MANDATE = """\
--- REACH: what this reply can do BEYOND the text line ---

SCHEDULING: you may plant ONE future push at a precise local time via "schedule" — a \
fully-composed dose that fires as-is later. Unprompted, null-to-skip is usual.

A CLOCK-BOUND REQUEST IS MANDATORY. Asked for something at a time ("send me X at 9am"), \
you MUST return a schedule object, composing the body NOW as it \
should read when it fires. "Noted, I'll do it" with schedule:null is a promise the machine \
cannot keep, and he waits for a push nobody queued (2026-07-23). Python re-asks you once.

A SCHEDULED DOSE MAY CARRY VOICE: put the spoken words in the schedule's "memo_script" and \
the drain renders them at fire time. Nothing composes at fire time — what you write now is \
exactly what speaks then.

SPEAK BACK, NOW ("voice_reply"): when the answer wants to be HEARD rather than read, put \
the spoken words here and Python renders them into this very push-back. Reach for it when \
the SOUND is the answer — he asked how something is pronounced, asked you to say or sing \
something, or there is someone in the room he wants to hear you. Everything else stays \
text: rendering costs him ~90 seconds of waiting at the lock screen, so a recast he could \
have read in two is a worse dose for being spoken. Never both explain in text and repeat \
it in voice — the text line stays the short recast; the voice carries what only sound can. \
Same rules as an audio memo: Tamil payload in Tamil SCRIPT (a Tamil voice speaks it), \
paragraphs separated by ONE blank line. Empty string is the normal answer.
"""


CATCH_VERDICTS = {"caught", "half-caught", "missed", "chat"}
RECOGNITION_NEXT = {"struggled": "comfortable", "comfortable": "solid"}

CATCH_JUDGE_MANDATE = """\
You are Anna, judging Andrew's reply to an EAVESDROP dose: he heard a tape (memo_script) \
and one English drift question. This grades COMPREHENSION (the catch axis), never \
production: did he catch who/what/mood?

GRADE THE THREAD, NOT THE TURN. prior_exchanges are part of his answer — once caught, the \
drift STAYS caught: never re-ask, never re-grade down.

A QUESTION IS NOT A WEAK ANSWER. One reply can carry both ("someone said there's a \
problem. Can I have a hint") — grade the catch, answer the request, let the asking cost \
him nothing. If he hunts a detail the tape never encoded (an unnamed subject is ordinary \
Tamil), the gap is the TAPE's, not his — say so.

GRADES:
- "caught"      — he got the drift (who / what / mood — the gist, never a transcript). \
English expected; Tamil a bonus, not graded.
- "half-caught" — partial: the who but not the what, the mood but not the news.
- "missed"      — the tape didn't land.
- "chat"        — no account of the tape at all (logistics, meta-direction).

Never grade wording or completeness — the win condition is the DRIFT.

"reply_line": the one line Anna pushes back — celebrate a catch short ("adhu dhaan — you \
caught it 🎧"), or hand the missed gist in ONE clause (you may quote the tape's key Tamil \
line). When he asks to be TAUGHT — a hint, a breakdown — answer it; teaching is never a \
detour. Otherwise no replay-homework.

META-DIRECTION: corrections and steering land in "meta_note", as in chat replies.

Return ONLY a JSON object, no prose around it:
{
  "verdict": "caught" | "half-caught" | "missed" | "chat",
  "reply_line": "<one line>",
  "meta_note": "<one line ONLY when the reply carried direction/correction for the system; empty string otherwise>",
  "rationale": "<one line, for the log>"
}
"""


RECENT_WINDOW_HOURS = 24.0
RECENT_WINDOW_TURNS = 8


def _ts(raw: str | None) -> datetime | None:
    """A log timestamp as an aware datetime, or None if it is unparseable.
    Three functions parsed this inline (revealed_recently, capped_fire_days,
    and this file's window); one copy, so a naive stamp can never sneak past
    only two of them."""
    try:
        dt = datetime.fromisoformat((raw or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def recent_exchanges(klog: list, knock: dict,
                     hours: float = RECENT_WINDOW_HOURS,
                     limit: int = RECENT_WINDOW_TURNS) -> list[dict]:
    """The conversation Anna is actually in — across knocks, not just this one.

    Before 2026-08-02 this was `knock["exchanges"][-4:]`: one knock, four turns,
    and a reply to a NEW knock started from nothing. It also carried only two
    fields — what Andrew typed and what Anna wrote — so nothing on the record
    said what Anna *did*. He composed and sent a whole audio greeting on one
    turn, and told Andrew it was "still pending" on the next, because the record
    only ever showed the promise. Same gap ate a referent: "he's an anglophone"
    resolved to Andrew, because the turn that introduced the third party had
    been reduced to a line of text.

    Safe to widen: cold-fire accounting does NOT read this window.
    `revealed_recently()` owns the evidence of what Tamil was shown (Python-owned,
    48h, whole log) and `shown_in_knock()` stays scoped to its own knock. This is
    continuity only — it can never mint or deny a cold.

    The current knock's own tail is always carried, however old, so this can
    never show less than the per-knock view it replaces.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    keep = {id(x) for x in (knock.get("exchanges") or [])[-4:]}   # never regress
    sources = list(klog) + ([] if any(k is knock for k in klog) else [knock])
    rows, seen = [], set()
    for k in sources:
        for x in k.get("exchanges", []):
            at = _ts(x.get("at"))
            if at is None or id(x) in seen or (at < cutoff and id(x) not in keep):
                continue
            seen.add(id(x))
            rows.append((at, k, x))
    rows.sort(key=lambda r: r[0])
    out = []
    for _, k, x in rows[-limit:]:
        row = {"andrew_said": x.get("reply", ""),
               "anna_said": x.get("reply_line", "")}
        if k is not knock:
            row["earlier_thread"] = k.get("move", "") or k.get("modality", "")
        # What Anna DID. Absent means he did not do it — a promise with no
        # matching field here was never kept.
        row.update({out_key: x[src_key] for src_key, out_key in
                    (("spoke", "anna_sent_audio"), ("scheduled", "anna_queued_push"))
                    if x.get(src_key)})
        out.append(row)

    if not out and knock.get("reply"):
        # Legacy knock: replies predating the `exchanges` list live at top level.
        out = [{"andrew_said": knock["reply"],
                "anna_said": knock.get("reply_line", "")}]
    return out


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


def judge_catch(knock: dict, reply_text: str, klog: list | None = None) -> dict:
    """The comprehension judge for an eavesdrop dose — a deliberately separate,
    smaller mandate so the production judge's rules (reveal caps, chains,
    per-word grades) never leak into a drift grade."""
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    context = catch_context(knock, reply_text, klog)
    print(f"   [catch judge] {executor_name()}")
    d = ask_json(persona + "\n\n---\n\n" + CATCH_JUDGE_MANDATE + "\n" + THREAD_MANDATE,
                 json.dumps(context, ensure_ascii=False, indent=2),
                 CATCH_SCHEMA, answer_tokens=400)
    if d.get("verdict") not in CATCH_VERDICTS:
        d["verdict"] = "chat"
    d["reply_line"] = (d.get("reply_line") or "").strip()
    d["meta_note"] = (d.get("meta_note") or "").strip()
    return d


def apply_catch_verdict(verdict: dict, knock: dict, lexicon: dict) -> list[str]:
    """Move the RECOGNITION axis for the dose's ear-only target — one rung per
    full catch (struggled → comfortable → solid), upgrades only, mirroring the
    production judge's never-demote rule. 'solid' on a catch item is the deck's
    win condition; production is never touched from here."""
    if verdict["verdict"] != "caught":
        return [f"no axis move ({verdict['verdict']})"]
    key = resolve(knock.get("expected_target", ""), lexicon, build_phonetic_index(lexicon))
    if key is None:
        return [f"! eavesdrop target {knock.get('expected_target')!r} resolves to no lexicon record — not scored"]
    rec = lexicon[key]
    cur = rec.get("recognition", "struggled")
    nxt = RECOGNITION_NEXT.get(cur)
    rec["last_surfaced"] = local_today().isoformat()
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


def handle_catch_reply(knock: dict, reply_text: str, klog: list,
                       lexicon: dict, dry_run: bool):
    """The eavesdrop counterpart of the production flow below: judge the drift,
    move recognition, log the exchange in the same shape (chat.md and the
    outcome memory read it unchanged), push one line back. No chains, no
    volley, no production meters."""
    print(f"1. judging DRIFT reply against eavesdrop knock {knock.get('timestamp', '?')[:16]}…")
    verdict = judge_catch(knock, reply_text, klog)
    print(f"   → {verdict['verdict']} | {verdict.get('rationale', '')}")

    if dry_run:
        print(f"[dry-run] would apply, then push: {verdict['reply_line']}")
        return

    print("2. state…")
    for line in apply_catch_verdict(verdict, knock, lexicon):
        print(f"   {line}")

    knock["response"] = "reply"
    knock["reply"] = reply_text
    knock["reply_verdict"] = verdict["verdict"]
    knock["reply_line"] = verdict["reply_line"]
    knock["reply_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    knock.setdefault("exchanges", []).append({
        "at": knock["reply_at"], "reply": reply_text,
        "verdict": verdict["verdict"], "fired": [],
        "reply_line": knock["reply_line"],
    })
    save_json(LEXICON_PATH, lexicon)
    save_json(KNOCK_LOG_PATH, klog)

    print("3. commit + push…")
    commit_paths = [LEXICON_PATH, KNOCK_LOG_PATH, render_chat()]
    if verdict["meta_note"]:
        flog = load_json(FEEDBACK_LOG_PATH) or []
        flog.append({"date": local_today().isoformat(), "note": f"[phone] {verdict['meta_note']}"})
        save_json(FEEDBACK_LOG_PATH, flog)
        commit_paths.append(FEEDBACK_LOG_PATH)
        print(f"   meta → ledger: {verdict['meta_note']}")
    commit_and_push(commit_paths, f"Knock reply: {verdict['verdict']} (eavesdrop)")

    print("4. push back…")
    body = verdict["reply_line"]  # the line only — no meter tail (see catch_meter's grave)
    # requested: he replied to a knock — answering him is not an interruption,
    # so the quiet-hours chokepoint must not swallow it (2026-07-26).
    push_to_phone(body, None, knock_id=knock.get("timestamp", ""), requested=True)
    print("done — drift judged, catch axis scored, answered.")


def last_fired_knock(klog: list) -> dict | None:
    fired = [k for k in klog if k.get("acted", True)]
    return fired[-1] if fired else None


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


# A clock in Andrew's own words. Deliberately generous: a false positive costs
# one re-ask, a false negative costs him a push he asked for and never got.
TIME_REQUEST_RE = re.compile(
    r"\b("
    r"\d{1,2}\s*(?::\d{2})?\s*(?:am|pm)"          # 9am, 9:15 pm
    r"|(?:at|by|around)\s+\d{1,2}(?::\d{2})?\b"   # at 9, by 9:15
    r"|in\s+(?:an?\s+)?(?:half\s+an?\s+)?(?:hour|minute|min)s?"
    r"|tomorrow|tonight|this\s+(?:morning|afternoon|evening)"
    r"|later\s+today|before\s+bed|first\s+thing"
    r")\b", re.I)

ASK_RE = re.compile(
    r"\b(send|ping|knock|remind|message|text|call|wake|greet\w*|give|do"
    r"|schedul\w*|queue|push|play|say|speak|sing|record|tell|wish)\b", re.I)


def wants_scheduled_push(text: str) -> bool:
    """True when Andrew's reply reads as 'do something for me at <time>'.

    The mandate says a clock-bound request MUST produce a schedule; this is the
    mechanism that makes the rule real. A prose rule with no enforcement is how
    the 2026-07-23 9am greeting got acknowledged and then silently dropped —
    the judge is steered toward meta_note (a ledger note for later) when what
    Andrew wanted was a queue entry.

    The verb list is deliberately WIDE (2026-07-24). "Schedule a push and say
    hello" — the most literal possible phrasing of the request — matched the
    clock and missed the verb, so the backstop built the day before to catch
    exactly this never fired and the 8pm greeting was dropped a second time.
    A false positive costs one re-ask; a false negative costs Andrew a push he
    asked for and never got. Widen on sight."""
    return bool(TIME_REQUEST_RE.search(text) and ASK_RE.search(text))


FORCE_SCHEDULE_ADDENDUM = """\

OVERRIDE — THIS REPLY CARRIES A TIME-BOUND REQUEST. Python detected a clock in what \
Andrew asked for and your previous answer returned schedule:null. You MUST return a \
non-null "schedule" object now: pick the exact local time he named, and compose "body" \
in full as the dose that fires at that moment. If what he wants is AUDIO, put the spoken \
words in "memo_script" — the drain renders it at fire time. \
Do not acknowledge without scheduling."""


def judge(knock: dict, reply_text: str, target_record: dict | None,
          hours_since: float | None = None,
          revealed_recent: list | None = None,
          force_schedule: bool = False,
          klog: list | None = None) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
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
               + "\n" + THREAD_MANDATE
               + (FORCE_SCHEDULE_ADDENDUM if force_schedule else ""))
    # 1600 is what the ARTIFACT needs — an 11-key schema plus a slip-ledger tag
    # match — and nothing else. The thinking room is added by `budget()`, inside
    # `ask_json`. This number was 800 until 2026-08-05, when the call spent ~750
    # tokens deliberating in prose and was cut off mid-word before its first
    # brace. The fix then was to raise this one literal, which was right for this
    # lane and left every other one wrong: on 2026-08-18 the same failure took
    # the knock lane and the drill sheet down together. Reasoning cost belongs to
    # the model, so it lives with the model (`writer.budget`).
    print(f"   [judge] {executor_name()}")
    d = ask_json(persona + "\n\n---\n\n" + mandate,
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


def render_voice_reply(spoken: str) -> tuple[Path | None, str | None]:
    """Render Anna's spoken answer for THIS push-back. Returns (mp3, url).

    The other half of the loop (2026-07-24): the knock lane could always speak
    TO Andrew, but the reply lane pushed `audio_url=None` hard-coded, so Anna
    could never speak BACK — a lock-screen ask for "how does that sound?" could
    only ever be answered in writing. The renderer was never the blocker; the
    reply workflow simply had no TTS secret until the workflows were merged.

    Deliberately best-effort: a TTS failure must still deliver the text recast.
    Costs ~60-90s while Andrew waits at the lock screen, which is why the
    mandate rations it to answers where the sound IS the answer."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    mp3 = KNOCKS_DIR / f"reply_{stamp}.mp3"
    try:
        asyncio.run(render_memo(spoken, mp3, ANNA_VOICE))
    except Exception as exc:                       # noqa: BLE001 — text must still land
        print(f"   ⚠ voice reply failed to render ({exc}) — pushing the text alone")
        return None, None
    return mp3, jsdelivr_url(mp3)


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
    voice_url, vmp3 = None, None
    if verdict.get("voice_reply"):
        print("2b. render voice reply…")
        vmp3, voice_url = render_voice_reply(verdict["voice_reply"])
        # onto the exchange too: the top-level field is the LATEST view, overwritten
        # by the next voice reply, so only the per-exchange copy survives as thread
        # history. reply_memo_script retired here — nothing ever read it, and
        # `spoke` on the exchange is the copy that gets used. On a render failure,
        # clear `spoke`: better a silent record than one claiming audio he never got.
        if voice_url:
            knock["reply_audio_url"] = voice_url
            knock["exchanges"][-1].update(audio_url=voice_url)
            save_json(KNOCK_LOG_PATH, klog)
        else:
            knock["exchanges"][-1].update(spoke="", audio_failed=True)

    print("3. commit + push…")
    commit_paths = [LEXICON_PATH, KNOCK_LOG_PATH, render_chat()]
    if cohort_changed:
        commit_paths.append(LEARNER_PATH)
    # The ledger is written on the runner; unpushed it dies with the container,
    # and the accumulation this whole mechanism exists for never happens.
    if verdict.get("slips"):
        commit_paths.append(SLIP_LOG_PATH)
    if voice_url:
        commit_paths.insert(0, vmp3)
        rss = refresh_feed()   # all audio lands on the feed (2026-07-05)
        if rss:
            commit_paths.append(rss)
    # Meta-direction lands in the feedback ledger — the diagnosis pass reads it.
    if verdict["meta_note"]:
        flog = load_json(FEEDBACK_LOG_PATH) or []
        flog.append({"date": local_today().isoformat(), "note": f"[phone] {verdict['meta_note']}"})
        save_json(FEEDBACK_LOG_PATH, flog)
        commit_paths.append(FEEDBACK_LOG_PATH)
        print(f"   meta → ledger: {verdict['meta_note']}")
    qp = maybe_enqueue_schedule(verdict)
    if qp:
        commit_paths.append(qp)
    commit_and_push(commit_paths,
                    f"Knock reply: {verdict['verdict']} ({', '.join(fired_words) or 'no fire'})")

    print("4. push back…")
    score = scoreboard(lexicon)
    body = " · ".join(p for p in (knock["reply_line"], score) if p)
    if len(body) > 240:
        print(f"   ⚠ push-back is {len(body)} chars — the lock screen will cut the tail (chained ask at risk)")
    # the chain's own id: a reply to this push-back correlates to the same knock entry
    push_to_phone(body, voice_url, knock_id=knock.get("timestamp", ""), requested=True)
    print(f"done — reply judged, scored, answered{' (aloud 🎧)' if voice_url else ''}.")


if __name__ == "__main__":
    main()
