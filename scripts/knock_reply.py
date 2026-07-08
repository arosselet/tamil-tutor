#!/usr/bin/env python3
"""
The reply half of the knock loop — the micro-session on the lock screen.

Andrew types phonetic Tamil straight into the knock notification; Home Assistant
routes it here (via repository_dispatch → log-knock-response.yml). Anna judges the
reply against what that knock asked for, moves the production axis, and pushes one
line back — the recast (or the celebration) plus the deck scoreboard.

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

Secrets: OPENROUTER_API_KEY (the judge), ANNA_PUSH_WEBHOOK_URL (the push-back).
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from render_chat import render_chat
from morning_knock import (OPENROUTER_BASE, MODEL, KNOCK_LOG_PATH, parse_llm_json,
                           load_env, push_to_phone, commit_and_push,
                           maybe_enqueue_schedule)
from sync_state import (LEXICON_PATH, FEEDBACK_LOG_PATH, TRIP_DATE, load_json,
                        save_json, build_phonetic_index, resolve, compute_deck,
                        fires_today)

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
graded on its OWN merits: [{"word": ..., "verdict": "cold"|"capped"|"hinted"}, ...]. \
"word" in CANONICAL Tamil script — copy the expected-target record's exact script when \
it matches — or the frame:... key for a frame. Empty list when nothing creditable fired.

"verdict" — the reply as a whole (for the log and your reply_line's tone):
- "cold" / "hinted" — something fired; set it to the best word's grade (a capped word \
counts as hinted here; Python re-derives this from "fired" regardless).
- "miss" — he tried, but it's off enough that nothing would land at the table. Empty fired.
- "chat" — not a rep at all (English chat, a question, logistics). Empty fired. No state moves.

HARD RULE: if the knock revealed the target Tamil (target_revealed=true), that word \
scores at most "hinted". Same for anything your own recast handed him in the \
prior_exchanges on this knock — echoing it back is a read-back, not a fire. Cold is \
unaided production only. (Python re-checks this per word.) The context's \
"revealed_recently" lists the Tamil ACTUALLY shown to him in the last 48h of knock \
traffic — computed from the log, not from memory. You may deny a cold as "I handed \
him that recently" ONLY when the word is on that list (or revealed by this knock / \
its prior_exchanges). If it is not listed and he produced it unaided, it is COLD — \
never invent a reveal.

CONTINUITY DECAYS: the context carries hours_since_last_exchange. Past ~3 hours, the \
scenario that knock was running is EXPIRED in his head — he is answering a lock-screen \
line cold, not continuing your scene. Do not hold the reply to the chained ask or the \
scene's script; grade whatever real Tamil fired on its own merits as an open rep, answer \
what he actually said, and if you chain, open FRESH (name the situation again in one \
clause — never assume he remembers who was asking what).

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

VALID ALTERNATIVE ≠ MISS: when the ask was an open situation and his reply is a socially \
coherent move that just isn't the word you had in mind ("ama, saapitten" while maama piles \
food), the target was never really tested — grade what fired on its own merits, skip the \
lesson, and if you re-ask, pin the MEANING in English ("wave it off — 'enough!'") without \
showing the Tamil; a word you print can never fire cold this exchange.

"reply_line": the one line Anna pushes back. If he's off — recast the natural way and \
move on, no lecture ("close — we'd say 'poren'. adhu dhaan next time"). If cold — \
celebrate, short ("adhu dhaan! 🔥"). Phonetic Tamil is fine here (it's a text \
notification). Do NOT append any score — Python adds the deck line.

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

SCHEDULING (optional): you may also plant ONE future push at a precise local time via \
"schedule" — a fully-composed dose that fires as-is later (collect tonight's field \
mission tomorrow morning; resurface today's wobble at 19:00). Use the exchange itself \
to pick the moment; null to skip, which is usual.

Return ONLY a JSON object, no prose around it:
{
  "verdict": "cold" | "hinted" | "miss" | "chat",
  "fired": [{"word": "<canonical Tamil script or frame:... key>", "verdict": "cold" | "capped" | "hinted"}, ...],
  "reply_line": "<one line>",
  "follow_up_ask": "<one line chaining the next rep; empty string to stop>",
  "follow_up_target": "<the one word/chunk/frame it asks for (Tamil script or frame:... key); empty if no chain>",
  "follow_up_target_revealed": true | false,
  "meta_note": "<one line ONLY when the reply carried direction/correction/testimony for the system — it lands in the feedback ledger; empty string otherwise>",
  "schedule": {"at_local": "YYYY-MM-DDTHH:MM", "body": "<the full dose>", "expected_target": "<or empty>", "target_revealed": true | false, "move": "<2-4 words>"} | null,
  "rationale": "<one line, for the log>"
}
"""


def last_fired_knock(klog: list) -> dict | None:
    fired = [k for k in klog if k.get("acted", True)]
    return fired[-1] if fired else None


def scoreboard(lexicon: dict) -> str:
    """The one score, appended to every push-back: deck cleared + days to touchdown
    + the fast per-day reward (fires today, live from the logs)."""
    deck = compute_deck(lexicon)
    if not deck["total"]:
        return ""
    days = (TRIP_DATE - date.today()).days
    n = fires_today()
    fires = f" · {n} fired today" if n else ""
    return f"Deck {deck['cleared']}/{deck['total']} · {days}d{fires}"


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


def judge(knock: dict, reply_text: str, target_record: dict | None,
          hours_since: float | None = None,
          revealed_recent: list | None = None) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    pin, pin_revealed = current_pin(knock)
    context = {
        "knock": {
            "modality": knock.get("modality"),
            "move": knock.get("move"),
            "notification_body": knock.get("body", ""),
            "memo_script": knock.get("memo_script", ""),
            "expected_target": pin,
            "target_revealed": pin_revealed,
        },
        "hours_since_last_exchange": round(hours_since, 1) if hours_since is not None else None,
        "expected_target_lexicon_record": target_record,
        "revealed_recently": revealed_recent or [],
        "andrew_reply": reply_text,
    }
    if knock.get("volley"):
        context["knock"]["volley_in_progress"] = (
            f"item {min(knock.get('volley_next', 1), len(knock['volley']))} of {len(knock['volley'])}")
    # A later reply to the same knock is judged knowing the whole chain —
    # Tamil that Anna's recasts already handed him is a read-back, not a cold fire.
    if knock.get("exchanges"):
        context["prior_exchanges"] = [
            {"andrew_said": x.get("reply", ""), "anna_recast": x.get("reply_line", "")}
            for x in knock["exchanges"][-4:]]
    elif knock.get("reply"):
        context["prior_exchanges"] = [{"andrew_said": knock["reply"],
                                       "anna_recast": knock.get("reply_line", "")}]
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=800,
        messages=[
            {"role": "system", "content": persona + "\n\n---\n\n" + JUDGE_MANDATE},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
        ],
    )
    return normalize_verdict(parse_llm_json(resp.choices[0].message.content))


def normalize_verdict(d: dict) -> dict:
    """Guard the judge's JSON into the shape Python relies on. Per-word verdicts
    (2026-07-03): each fired item carries its own cold/hinted grade — one flat
    grade flattened multi-word replies. The reply's overall verdict is DERIVED
    (best word wins) so the log and chain never contradict the axis; a scored
    verdict with no fired words degrades to "miss" (nothing creditable, no chain
    padding — fires_today and the burn rate count reply_fired)."""
    if d.get("verdict") not in VERDICTS:
        d["verdict"] = "chat"
    fired = []
    for item in d.get("fired", []):
        if isinstance(item, str):  # tolerate the pre-per-word flat shape
            item = {"word": item, "verdict": d["verdict"]}
        if not isinstance(item, dict):
            continue
        w = (item.get("word") or "").strip()
        if w:
            v = item.get("verdict") if item.get("verdict") in ("cold", "capped") else "hinted"
            fired.append({"word": w, "verdict": v})
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
        try:
            ts = datetime.fromisoformat((k.get("timestamp") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff:
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
    from sync_state import LOCAL_TZ
    days = set()
    for k in klog:
        for x in k.get("exchanges", []):
            if key not in x.get("fired_capped", []):
                continue
            try:
                dt = datetime.fromisoformat((x.get("at") or "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
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
    from sync_state import LOCAL_TZ
    phon_index = build_phonetic_index(lexicon)
    today = date.today().isoformat()
    today_local = datetime.now(timezone.utc).astimezone(LOCAL_TZ).date()
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
    knock = last_fired_knock(klog)
    if knock is None:
        print("No fired knock to judge a reply against — logging nothing.")
        return

    lexicon = load_json(LEXICON_PATH) or {}
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
    verdict = judge(knock, reply_text, target_record, hours, revealed)
    fired_str = ", ".join(f"{i['word']}:{i['verdict']}" for i in verdict["fired"]) or "—"
    print(f"   → {verdict['verdict']} | fired: {fired_str} | {verdict.get('rationale', '')}")

    # Momentum chain: on a scored reply, the push-back may carry the NEXT micro-ask.
    # The knock's expected target moves to the chained one, so the next reply is
    # judged against what was actually asked (prior_exchange covers the recast).
    # A VOLLEY knock chains DETERMINISTICALLY instead: Python hands the next deck
    # item on ANY judged verdict (miss = recast-and-move, the blitz law) and the
    # judge's own follow_up is ignored — finite by construction, no CHAIN_CAP.
    follow, volley_pin = "", None
    vq = knock.get("volley")
    if vq:
        if verdict["verdict"] != "chat":
            nxt = knock.get("volley_next", 1)
            if nxt < len(vq):
                volley_pin = vq[nxt]
                follow = f"{nxt + 1}/{len(vq)} — {volley_pin['ask']}"
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
    knock["reply_line"] = " · ".join(p for p in (verdict["reply_line"], follow) if p)
    knock["reply_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    knock.setdefault("exchanges", []).append({
        "at": knock["reply_at"], "reply": reply_text,
        "verdict": verdict["verdict"], "fired": fired_words,
        "fired_cold": cold_credited, "fired_capped": capped_keys,
        "graduated": graduated, "reply_line": knock["reply_line"],
    })
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

    print("3. commit + push…")
    commit_paths = [LEXICON_PATH, KNOCK_LOG_PATH, render_chat()]
    # Meta-direction lands in the feedback ledger — the diagnosis pass reads it.
    if verdict["meta_note"]:
        flog = load_json(FEEDBACK_LOG_PATH) or []
        flog.append({"date": date.today().isoformat(), "note": f"[phone] {verdict['meta_note']}"})
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
    push_to_phone(body, None)
    print("done — reply judged, scored, answered.")


if __name__ == "__main__":
    main()
