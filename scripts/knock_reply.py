#!/usr/bin/env python3
"""
The reply half of the knock loop — the micro-session on the lock screen.

Andrew types phonetic Tamil straight into the knock notification; Home Assistant
routes it here (via repository_dispatch → log-knock-response.yml). Anna judges the
reply against what that knock asked for, moves the production axis, and pushes one
line back — the recast (or the celebration) plus the deck scoreboard.

Judge philosophy: this is the recast across the table, not an exam. Anna is
generous in spirit but honest on the axis — and Python re-enforces the one hard
rule: Tamil the notification SHOWED him can score at most "hinted"; "cold" is
reserved for unaided production. Andrew stays the court of appeal: every verdict
is visible in the push-back and in knock_log.json, and chat sessions can always
correct state.

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
from morning_knock import (OPENROUTER_BASE, MODEL, KNOCK_LOG_PATH,
                           load_env, push_to_phone, commit_and_push)
from sync_state import (LEXICON_PATH, TRIP_DATE, load_json, save_json,
                        build_phonetic_index, resolve, compute_deck)

PRODUCTION_RANK = {"none": 0, "hinted": 1, "cold": 2}
VERDICTS = {"cold", "hinted", "miss", "chat"}

JUDGE_MANDATE = """\
You are Anna, judging ONE phone reply from Andrew against the knock you sent him. \
This is the recast across the table, not an exam — generous in spirit, honest on the axis.

VERDICTS:
- "cold"   — the reply fires real Tamil the notification did NOT show him. Phonetic \
spelling is fine and expected ("poren" IS போறேன்); judge the Tamil, not the spelling.
- "hinted" — real Tamil, but the knock showed it to him (reading back is not firing), \
or it needed the knock's scaffold, or it's partially off but would land.
- "miss"   — he tried, but it's off enough that it wouldn't land at the table.
- "chat"   — not a rep at all (English chat, a question, logistics). No state moves.

HARD RULE: if the knock revealed the target Tamil (target_revealed=true), that word \
scores at most "hinted". Same for anything your own recast handed him in a \
prior_exchange on this knock — echoing it back is a read-back, not a fire. Cold is \
unaided production only. (Python re-checks this.)

"fired": every Tamil word/chunk/frame the reply genuinely produced, in CANONICAL Tamil \
script — copy the expected-target record's exact script when it matches — or the \
frame:... key for a frame. Empty list for miss/chat.

"reply_line": the one line Anna pushes back. If he's off — recast the natural way and \
move on, no lecture ("close — we'd say 'poren'. adhu dhaan next time"). If cold — \
celebrate, short ("adhu dhaan! 🔥"). Phonetic Tamil is fine here (it's a text \
notification). Do NOT append any score — Python adds the deck line.

Return ONLY a JSON object, no prose around it:
{
  "verdict": "cold" | "hinted" | "miss" | "chat",
  "fired": ["<canonical Tamil script or frame:... key>", ...],
  "reply_line": "<one line>",
  "rationale": "<one line, for the log>"
}
"""


def last_fired_knock(klog: list) -> dict | None:
    fired = [k for k in klog if k.get("acted", True)]
    return fired[-1] if fired else None


def scoreboard(lexicon: dict) -> str:
    """The one score, appended to every push-back: deck cleared + days to touchdown."""
    deck = compute_deck(lexicon)
    if not deck["total"]:
        return ""
    days = (TRIP_DATE - date.today()).days
    return f"Deck {deck['cleared']}/{deck['total']} · {days}d"


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
    d = json.loads(text, strict=False)
    if d.get("verdict") not in VERDICTS:
        d["verdict"] = "chat"
    d["fired"] = [w for w in d.get("fired", []) if isinstance(w, str) and w.strip()]
    d["reply_line"] = (d.get("reply_line") or "").strip()
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


def apply_verdict(verdict: dict, knock: dict, lexicon: dict) -> list[str]:
    """Move the production axis for what fired. Upgrades only — a phone rep never
    demotes (chat sessions own corrections). Returns a summary line per word."""
    phon_index = build_phonetic_index(lexicon)
    today = date.today().isoformat()
    level = verdict["verdict"] if verdict["verdict"] in ("cold", "hinted") else None
    revealed_key = (resolve(knock.get("expected_target", ""), lexicon, phon_index)
                    if knock.get("target_revealed", True) else None)
    summary = []
    for w in verdict["fired"]:
        key = resolve(w, lexicon, phon_index)
        if key is None:
            summary.append(f"! '{w}' resolves to no lexicon record — not scored")
            continue
        rec = lexicon[key]
        target = level
        if target == "cold" and (key == revealed_key or shown_in_knock(key, rec, knock)):
            target = "hinted"  # the hard rule, enforced deterministically
        if target is None:
            continue
        cur = rec.get("production", "none")
        if PRODUCTION_RANK[target] > PRODUCTION_RANK.get(cur, 0):
            rec["production"] = target
            summary.append(f"{key} → {target.upper()}")
        else:
            summary.append(f"{key} already {cur} — kept")
        rec["last_surfaced"] = today
    return summary


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
    print(f"   → {verdict['verdict']} | fired={verdict['fired']} | {verdict.get('rationale', '')}")

    if args.dry_run:
        print(f"[dry-run] would apply, then push: {verdict['reply_line']} · {scoreboard(lexicon)}")
        return

    print("2. state…")
    for line in apply_verdict(verdict, knock, lexicon):
        print(f"   {line}")

    knock["response"] = "reply"  # the strongest "landed" signal there is
    knock["reply"] = reply_text
    knock["reply_verdict"] = verdict["verdict"]
    knock["reply_fired"] = verdict["fired"]
    knock["reply_line"] = verdict["reply_line"]
    knock["reply_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    save_json(LEXICON_PATH, lexicon)
    save_json(KNOCK_LOG_PATH, klog)

    print("3. commit + push…")
    commit_and_push([LEXICON_PATH, KNOCK_LOG_PATH],
                    f"Knock reply: {verdict['verdict']} ({', '.join(verdict['fired']) or 'no fire'})")

    print("4. push back…")
    score = scoreboard(lexicon)
    body = f"{verdict['reply_line']} · {score}" if score else verdict["reply_line"]
    push_to_phone(body, None)
    print("done — reply judged, scored, answered.")


if __name__ == "__main__":
    main()
