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
can score at most "hinted"; "cold" is reserved for unaided production. Andrew
stays the court of appeal: every verdict is visible in the push-back and in
knock_log.json, and chat sessions can always correct state.

  python scripts/knock_reply.py "naan poren"            # judge, write state, commit+push, notify
  python scripts/knock_reply.py --dry-run "naan poren"  # judge + print only (no writes)

Secrets: OPENROUTER_API_KEY (the judge), ANNA_PUSH_WEBHOOK_URL (the push-back).
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from render_chat import render_chat
from morning_knock import (OPENROUTER_BASE, MODEL, KNOCK_LOG_PATH,
                           load_env, push_to_phone, commit_and_push,
                           maybe_enqueue_schedule)
from sync_state import (LEXICON_PATH, TRIP_DATE, load_json, save_json,
                        build_phonetic_index, resolve, compute_deck, fires_today)

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
- "hinted" — real Tamil, but the knock showed that word to him (reading back is not \
firing), or it needed the knock's scaffold, or it's partially off but would land.

"fired": one entry per Tamil word/chunk/frame the reply genuinely produced, each \
graded on its OWN merits: [{"word": ..., "verdict": "cold"|"hinted"}, ...]. "word" \
in CANONICAL Tamil script — copy the expected-target record's exact script when it \
matches — or the frame:... key for a frame. Empty list when nothing creditable fired.

"verdict" — the reply as a whole (for the log and your reply_line's tone):
- "cold" / "hinted" — something fired; set it to the best word's grade (Python \
re-derives this from "fired" regardless).
- "miss" — he tried, but it's off enough that nothing would land at the table. Empty fired.
- "chat" — not a rep at all (English chat, a question, logistics). Empty fired. No state moves.

HARD RULE: if the knock revealed the target Tamil (target_revealed=true), that word \
scores at most "hinted". Same for anything your own recast handed him in a \
prior_exchange on this knock — echoing it back is a read-back, not a fire. Cold is \
unaided production only. (Python re-checks this per word.)

"reply_line": the one line Anna pushes back. If he's off — recast the natural way and \
move on, no lecture ("close — we'd say 'poren'. adhu dhaan next time"). If cold — \
celebrate, short ("adhu dhaan! 🔥"). Phonetic Tamil is fine here (it's a text \
notification). Do NOT append any score — Python adds the deck line.

MOMENTUM CHAIN: if (and ONLY if) the verdict is "cold" or "hinted", you MAY ride the \
momentum with ONE follow-up micro-ask ("follow_up_ask"): a single short line handing \
the NEXT rep — an English situation that wants one Tamil line back, never re-asking \
what he just fired. Leave the Tamil to him (follow_up_target_revealed=false is the \
strong form; a shown target caps at hinted). On "miss" or "chat" NO chain — the recast \
is the whole dose. Skipping the chain (empty strings) is often right; he replies when \
he replies.

SCHEDULING (optional): you may also plant ONE future push at a precise local time via \
"schedule" — a fully-composed dose that fires as-is later (collect tonight's field \
mission tomorrow morning; resurface today's wobble at 19:00). Use the exchange itself \
to pick the moment; null to skip, which is usual.

Return ONLY a JSON object, no prose around it:
{
  "verdict": "cold" | "hinted" | "miss" | "chat",
  "fired": [{"word": "<canonical Tamil script or frame:... key>", "verdict": "cold" | "hinted"}, ...],
  "reply_line": "<one line>",
  "follow_up_ask": "<one line chaining the next rep; empty string to stop>",
  "follow_up_target": "<the one word/chunk/frame it asks for (Tamil script or frame:... key); empty if no chain>",
  "follow_up_target_revealed": true | false,
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


def judge(knock: dict, reply_text: str, target_record: dict | None) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    context = {
        "knock": {
            "modality": knock.get("modality"),
            "move": knock.get("move"),
            "notification_body": knock.get("body", ""),
            "memo_script": knock.get("memo_script", ""),
            "expected_target": knock.get("expected_target", ""),
            "target_revealed": knock.get("target_revealed", True),
        },
        "expected_target_lexicon_record": target_record,
        "andrew_reply": reply_text,
    }
    # A second reply to the same knock is judged knowing the first exchange —
    # Tamil that Anna's recast already handed him is a read-back, not a cold fire.
    if knock.get("reply"):
        context["prior_exchange"] = {"andrew_said": knock["reply"],
                                     "anna_recast": knock.get("reply_line", "")}
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=800,
        messages=[
            {"role": "system", "content": persona + "\n\n---\n\n" + JUDGE_MANDATE},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
        ],
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    return normalize_verdict(json.loads(text, strict=False))


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
            v = item.get("verdict") if item.get("verdict") == "cold" else "hinted"
            fired.append({"word": w, "verdict": v})
    d["fired"] = fired if d["verdict"] in ("cold", "hinted") else []
    if d["fired"]:
        d["verdict"] = ("cold" if any(i["verdict"] == "cold" for i in d["fired"])
                        else "hinted")
    elif d["verdict"] in ("cold", "hinted"):
        d["verdict"] = "miss"
    d["reply_line"] = (d.get("reply_line") or "").strip()
    d["follow_up_ask"] = (d.get("follow_up_ask") or "").strip()
    d["follow_up_target"] = (d.get("follow_up_target") or "").strip()
    d["follow_up_target_revealed"] = bool(d.get("follow_up_target_revealed", True))
    d["schedule"] = d.get("schedule") if isinstance(d.get("schedule"), dict) else None
    return d


def shown_in_knock(key: str, rec: dict, knock: dict) -> bool:
    """Deterministic check of the hard rule: did the knock's own text — or a
    recast Anna already pushed back on an earlier reply — show this Tamil
    (script or any known phonetic)? Shown ⇒ the reply caps at 'hinted'."""
    shown = (f"{knock.get('body', '')} {knock.get('memo_script', '')} "
             f"{knock.get('reply_line', '')}").lower()
    if key.lower() in shown:
        return True
    return any(p.lower() in shown for p in rec.get("phonetic", []) if p)


def apply_verdict(verdict: dict, knock: dict, lexicon: dict) -> tuple[list[str], list[str]]:
    """Move the production axis for what fired — each word on its OWN grade
    (per-word verdicts, 2026-07-03). Upgrades only — a phone rep never demotes
    (chat sessions own corrections). Returns (summary lines, the words whose
    EFFECTIVE grade was cold after the revealed-cap — the pace meters read these)."""
    phon_index = build_phonetic_index(lexicon)
    today = date.today().isoformat()
    revealed_key = (resolve(knock.get("expected_target", ""), lexicon, phon_index)
                    if knock.get("target_revealed", True) else None)
    summary, cold_credited = [], []
    for item in verdict["fired"]:
        key = resolve(item["word"], lexicon, phon_index)
        if key is None:
            summary.append(f"! '{item['word']}' resolves to no lexicon record — not scored")
            continue
        rec = lexicon[key]
        target = item["verdict"]
        if target == "cold" and (key == revealed_key or shown_in_knock(key, rec, knock)):
            target = "hinted"  # the hard rule, enforced deterministically per word
        if target == "cold":
            cold_credited.append(key)  # a re-fire of an already-cold word still counts as pace
        cur = rec.get("production", "none")
        if PRODUCTION_RANK[target] > PRODUCTION_RANK.get(cur, 0):
            rec["production"] = target
            summary.append(f"{key} → {target.upper()}")
        else:
            summary.append(f"{key} already {cur} — kept ({target} fire)")
        rec["last_surfaced"] = today
    return summary, cold_credited


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
    target = knock.get("expected_target", "")
    target_key = resolve(target, lexicon, phon_index) if target else None
    target_record = None
    if target_key:
        r = lexicon[target_key]
        target_record = {"script": target_key, "gloss": r.get("gloss", ""),
                         "phonetic": r.get("phonetic", [])}

    print(f"1. judging reply against knock {knock.get('timestamp', '?')[:16]} "
          f"({knock.get('modality')}/{knock.get('move')})…")
    verdict = judge(knock, reply_text, target_record)
    fired_str = ", ".join(f"{i['word']}:{i['verdict']}" for i in verdict["fired"]) or "—"
    print(f"   → {verdict['verdict']} | fired: {fired_str} | {verdict.get('rationale', '')}")

    # Momentum chain: on a scored reply, the push-back may carry the NEXT micro-ask.
    # The knock's expected target moves to the chained one, so the next reply is
    # judged against what was actually asked (prior_exchange covers the recast).
    follow = ""
    if (verdict["verdict"] in ("cold", "hinted") and verdict["follow_up_ask"]
            and knock.get("chained", 0) < CHAIN_CAP):
        follow = verdict["follow_up_ask"]

    if args.dry_run:
        chain_str = f" ↪ chain: {follow}" if follow else ""
        print(f"[dry-run] would apply, then push: {verdict['reply_line']} · {scoreboard(lexicon)}{chain_str}")
        return

    print("2. state…")
    summary, cold_credited = apply_verdict(verdict, knock, lexicon)
    for line in summary:
        print(f"   {line}")

    knock["response"] = "reply"  # the strongest "landed" signal there is
    knock["reply"] = reply_text
    knock["reply_verdict"] = verdict["verdict"]
    # accumulate across a chain — fires_today reads reply_fired (every scored
    # word); the cold pace meter reads reply_fired_cold (effective grade after
    # the revealed-cap, per word)
    fired_words = [i["word"] for i in verdict["fired"]]
    knock["reply_fired"] = knock.get("reply_fired", []) + fired_words
    knock["reply_fired_cold"] = knock.get("reply_fired_cold", []) + cold_credited
    # store the FULL push-back (recast + chained ask): the next judge call reads it
    # as prior_exchange, and shown_in_knock scans it for revealed Tamil
    knock["reply_line"] = " · ".join(p for p in (verdict["reply_line"], follow) if p)
    knock["reply_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if follow:
        knock["chained"] = knock.get("chained", 0) + 1
        knock["expected_target"] = verdict["follow_up_target"]
        knock["target_revealed"] = verdict["follow_up_target_revealed"]

    save_json(LEXICON_PATH, lexicon)
    save_json(KNOCK_LOG_PATH, klog)

    print("3. commit + push…")
    commit_paths = [LEXICON_PATH, KNOCK_LOG_PATH, render_chat()]
    qp = maybe_enqueue_schedule(verdict)
    if qp:
        commit_paths.append(qp)
    commit_and_push(commit_paths,
                    f"Knock reply: {verdict['verdict']} ({', '.join(fired_words) or 'no fire'})")

    print("4. push back…")
    score = scoreboard(lexicon)
    body = " · ".join(p for p in (knock["reply_line"], score) if p)
    push_to_phone(body, None)
    print("done — reply judged, scored, answered.")


if __name__ == "__main__":
    main()
