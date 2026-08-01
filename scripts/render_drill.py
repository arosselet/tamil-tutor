#!/usr/bin/env python3
"""
The drill track — a hands-free SPOKEN production volley from the deck's due list.

Everything else in the system is typed chat or listen-only immersion; the trip is
spoken. This closes that gap Pimsleur-style: Anna speaks an English cue, silence
while Andrew SAYS THE TAMIL OUT LOUD, then the answer lands (twice). Built straight
from the due fire-side deck items, so a walk or the dishes becomes deck reps.

Same one-shot family as the knock: the LLM writes the sheet (cues + answers),
Python owns the menu (deck due list), the render, and the publish. Listening
isn't producing — NO reps are logged; publishing stamps a declared EXPOSURE on
the drilled items (the 2026-07-26 ledger law: exposure = it went out the door).
The cold fires happen later, in chat or on a knock reply, where a judge hears them.

  python scripts/render_drill.py --dry-run     # write + print the sheet only
  python scripts/render_drill.py               # sheet → render → RSS + commit/push + phone push
  python scripts/render_drill.py --no-publish  # render to published_audio/ only

Secrets: OPENROUTER_API_KEY (the sheet), GCP ADC (TTS), ANNA_PUSH_WEBHOOK_URL (the push).
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from morning_knock import (OPENROUTER_BASE, MODEL, ANNA_VOICE, load_env,
                           push_to_phone, commit_and_push, jsdelivr_url)
from render_audio import generate_segment_google, get_raw_mp3_frames, SILENCE_FRAME, clean_for_tts
from suggest_targets import deck_status
from sync_state import (LEXICON_PATH, canon_payload, load_json,
                        mark_soak_delivered, record_exposure)

DRILLS_DIR = BASE / "published_audio"   # feed root — rebuild_rss picks up drill_*.mp3
SILENCE_PER_SEC = 41.666                # frames per second (matches render_audio)

DRILL_MANDATE = """\
You are Anna, writing a DRILL SHEET — a hands-free spoken production drill Andrew \
runs while driving or doing dishes. The rhythm per item: you speak a short English \
cue, then silence while HE SAYS THE TAMIL OUT LOUD, then you give the answer (it \
plays twice). Your job is only the sheet: the cues and the answers.

RULES:
- Items come from the DECK DUE list below, in the order given. A chunk's answer is \
the chunk itself, said whole. A frame becomes TWO consecutive items, each a \
different NOVEL slot-fill using everyday trip nouns/verbs (tea, auto, temple, \
bathroom, eat, sit, come...).
- The cue is a compact English situation or meaning ("ask your maama for a coffee", \
"tell her: we went to the temple, it was great"). NEVER put any Tamil in the cue — \
the silence is where he produces it unaided. Cues stay under ~12 words.
- The answer is natural standard Coimbatore colloquial in TAMIL SCRIPT ONLY (a \
Tamil voice speaks it). Polite -nga register by default; nee only where the deck \
item itself is nee-form.
- "intro": one short Anna line in his own voice setting the contract — out loud, \
before the answer comes, no mumbling. "outro": one short warm line, no homework.
- No grammar talk, no numbering, no meta-narration.

Return ONLY a JSON object, no prose around it:
{
  "title": "<3-5 word label for the feed>",
  "intro": "<one spoken line>",
  "items": [{"cue": "<English>", "answer_ta": "<Tamil script>"}, ...],
  "outro": "<one spoken line>"
}
"""

# Appended when the standing order routed a REPAIR to this lane. The commissioned
# item leads and gets three angles; the deck fills the rest of the tape. LEAD, not
# replace (2026-07-28, Andrew's call): a whole drill built from one item is the
# slow repetitive loop this lane was commissioned to escape.
COMMISSION_BRIEF = """

THE COMMISSION — the FIRST {n} item(s) of the DECK DUE list are a REPAIR, not routine \
deck reps. Give each of them THREE items instead of one: three different cues, three \
different everyday situations, the same target every time. Vary the situation, never the \
target — using it in context is the whole point of drilling it again. Everything after \
them is the ordinary drill and keeps its normal shape (one item per chunk, two per \
frame).{focus}
"""


def deck_due_payload(max_entries: int) -> list[dict]:
    """The selector's order, but interleaved frame/chunk — a drill is mouth-reps,
    and a slot-fill and a said-whole phrase are different work, so a run of six
    frames is a worse drill than an alternating six.

    That is now the ONLY reason. Until 2026-07-25 this also worked around a
    starving sort: `deck_status` broke ties alphabetically and ASCII 'frame:'
    keys sorted ahead of every Tamil-script chunk, so a straight head-slice was
    all frames. The selector is coverage-first now (a plain top-6 measures 2
    frames / 4 chunks), so this is a pedagogy choice and no longer a guard —
    delete it the day that stops being true."""
    deck = deck_status(load_json(LEXICON_PATH) or {})
    if not deck or not deck["pending"]:
        return []
    frames = [t for t in deck["pending"] if t["kind"] == "frame"]
    chunks = [t for t in deck["pending"] if t["kind"] != "frame"]
    out = []
    while len(out) < max_entries and (frames or chunks):
        if frames:
            out.append(frames.pop(0))
        if chunks and len(out) < max_entries:
            out.append(chunks.pop(0))
    return out


def drill_brief() -> tuple[str | None, list[dict]]:
    """The standing soak order, when it is addressed to THIS lane → (focus, lead items).

    Until 2026-07-28 `--soak-channel drill` was a dead value: `sync_state` accepted
    and stored it, this module never read it, and no lane stamped it delivered. So
    a repair routed here silently became an ordinary deck drill, the order stayed
    pending, and the next session-open auto-drain dispatched an EPISODE for it —
    the one lane Andrew had explicitly not chosen.

    EAR-ONLY items are REFUSED, never demanded. `direction: catch` means the win is
    recognition, and a drill's silence is a production demand — the deck law is that
    these are never forced to fire. A catch commission routed here is a mis-route,
    so it is reported and left standing for the soak or episode lane rather than
    quietly turned into a demand the learner cannot meet."""
    order = (load_json(BASE / "progress" / "learner.json") or {}).get("soak_order") or {}
    if (order.get("channel") or "episode") != "drill":
        return None, []
    focus = (order.get("focus") or "").strip() or None
    lexicon = load_json(LEXICON_PATH) or {}
    lead = []
    for w in canon_payload(order.get("payload") or []):
        rec = lexicon.get(w) or {}
        if rec.get("direction") == "catch":
            print(f"   ⚠ '{w}' is ear-only (direction: catch) — a drill demands "
                  f"production, so it is NOT drilled. Route it to soak or episode.")
            continue
        lead.append({
            "word": w, "gloss": rec.get("gloss", ""),
            "kind": "frame" if w.startswith("frame:") or rec.get("type") == "pattern"
                    else "chunk"})
    return focus, lead


def with_lead(pending: list[dict], lead: list[dict]) -> list[dict]:
    """The commissioned repair leads the tape; the due deck fills out the rest.
    A lead item already on the deck list is not drilled twice."""
    if not lead:
        return pending
    have = {t["word"] for t in lead}
    return lead + [t for t in pending if t["word"] not in have]


def ask_json(system: str, user: str, max_tokens: int = 2400) -> dict:
    """One single-shot LLM call → parsed JSON (fenced or bare). Shared by the
    sheet writer and the answer-key lint so the fence handling lives once."""
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    return json.loads(text, strict=False)


def write_sheet(pending: list[dict], n_lead: int = 0, focus: str | None = None) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    menu = "\n".join(f"- [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}"
                     for t in pending)
    mandate = DRILL_MANDATE
    if n_lead:
        mandate += COMMISSION_BRIEF.format(
            n=n_lead, focus=f"\nWhat the repair is about: {focus}" if focus else "")
    sheet = ask_json(persona + "\n\n---\n\n" + mandate, f"DECK DUE:\n{menu}")
    sheet["items"] = [i for i in sheet.get("items", [])
                      if i.get("cue", "").strip() and i.get("answer_ta", "").strip()]
    return sheet


LINT_MANDATE = """\
You are a strict checker of spoken Coimbatore colloquial Tamil. Each numbered item \
pairs an English cue with the Tamil answer a learner will repeat aloud ten times. \
FAIL any answer a native speaker would flag as wrong: a wrong case suffix (locative \
-ல where dative -க்கு is needed; பக்கம்ல for the oblique பக்கத்துல), a wrong tense or \
person ending, or an unnatural form for the cue's meaning. Colloquial contractions, \
register variation and Thanglish loanwords are FINE — this is spoken language, not \
textbook Tamil. When genuinely unsure, PASS.
Return ONLY JSON: {"verdicts": [{"n": 1, "verdict": "PASS|FAIL", "reason": "<one clause>"}]} \
— exactly one verdict per item."""


def lint_sheet(sheet: dict) -> list[str]:
    """Answer-key gate — the studio's lint contract on the drill lane (2026-08-01).

    The 08-01 tape shipped இடது பக்கம்ல where the oblique பக்கத்துல is right — a
    wrong case form repeated aloud ten times, on the very tape commissioned to fix
    the top slip. A drill answer is load-bearing in a way a chat line is not: it
    IS the model he rehearses. So a second single-shot call grades every answer
    against its cue, and the caller stops the run on ANY fail — never ships.
    Raises (rather than passing) when the grader itself misbehaves: an errored or
    miscounted verdict list is an UNVERIFIED sheet, and unverified wrong forms
    ×10 are worse than a late drill (fail-closed)."""
    items = sheet.get("items", [])
    if not items:
        return []
    listing = "\n".join(f"{n}. cue: {i['cue']}\n   answer: {i['answer_ta']}"
                        for n, i in enumerate(items, 1))
    verdicts = ask_json(LINT_MANDATE, listing, max_tokens=1200).get("verdicts", [])
    if len(verdicts) != len(items):
        raise ValueError(f"lint returned {len(verdicts)} verdicts for {len(items)} items")
    fails = []
    for v in verdicts:
        if str(v.get("verdict", "")).strip().upper() != "PASS":
            n = v.get("n")
            ans = items[n - 1]["answer_ta"] if isinstance(n, int) and 1 <= n <= len(items) else "?"
            fails.append(f"item {n}: {ans} — {v.get('reason', '') or 'no reason given'}")
    return fails


def silence(seconds: float) -> bytes:
    return SILENCE_FRAME * int(seconds * SILENCE_PER_SEC)


async def render(sheet: dict, out_path: Path, gap: float):
    """Anna's one pinned voice throughout (cue in English, answer in Tamil script) —
    the drill should sound like the same someone as the knocks."""
    audio = bytearray()
    tmp = tempfile.mkdtemp()
    idx = 0

    async def seg(text: str) -> bytes:
        nonlocal idx
        idx += 1
        f = await generate_segment_google(clean_for_tts(text), ANNA_VOICE, idx, tmp)
        frames = get_raw_mp3_frames(f)
        os.remove(f)
        return frames

    print(f"   intro: {sheet['intro'][:60]}")
    audio.extend(await seg(sheet["intro"]))
    audio.extend(silence(1.5))
    for n, item in enumerate(sheet["items"], 1):
        print(f"   [{n}/{len(sheet['items'])}] {item['cue'][:40]} → {item['answer_ta'][:30]}")
        audio.extend(await seg(item["cue"]))
        audio.extend(silence(gap))              # his turn — out loud
        answer = await seg(item["answer_ta"])
        audio.extend(answer)
        audio.extend(silence(0.9))
        audio.extend(answer)                    # the echo sets it
        audio.extend(silence(1.4))
    audio.extend(await seg(sheet["outro"]))
    os.rmdir(tmp)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    print(f"   rendered -> {out_path} ({len(audio)/1024:.0f} KB)")


def main():
    ap = argparse.ArgumentParser(description="Spoken production drill from the deck's due list")
    ap.add_argument("--entries", type=int, default=8,
                    help="deck entries to drill (frames expand to 2 items; default 8)")
    ap.add_argument("--gap", type=float, default=3.5,
                    help="seconds of silence for Andrew's out-loud attempt (default 3.5)")
    ap.add_argument("--dry-run", action="store_true", help="write + print the sheet; no TTS or publish")
    ap.add_argument("--no-publish", action="store_true", help="render only; skip RSS/commit/push/notify")
    args = ap.parse_args()

    load_env(BASE / ".env")

    # The commission is read FIRST: a repair routed here must still get its tape
    # on a day the deck happens to have nothing due.
    focus, lead = drill_brief()
    pending = with_lead(deck_due_payload(args.entries), lead)
    if not pending:
        print("No due fire-side deck items — nothing to drill.")
        return

    print(f"1. sheet… ({len(pending)} deck entries"
          f"{f' · {len(lead)} COMMISSIONED, leading' if lead else ''}"
          f"{' · FOCUS: ' + focus if focus else ''})")
    sheet = write_sheet(pending, len(lead), focus)
    print(f"   → '{sheet.get('title', 'Drill')}' · {len(sheet['items'])} items")

    # Lint before the dry-run gate on purpose: the sheet a dry run prints should
    # carry the same verdict the real run would act on.
    try:
        fails = lint_sheet(sheet)
    except Exception as e:
        sys.exit(f"✗ answer-key lint could not run ({e}) — unverified sheet; not rendering.")
    if fails:
        for line in fails:
            print(f"   ✗ {line}")
        sys.exit("✗ answer key failed lint — stopped for inspection, nothing rendered. "
                 "Re-run for a fresh sheet.")
    if sheet["items"]:
        print(f"   ✓ lint: {len(sheet['items'])} answers pass")

    if args.dry_run:
        print(json.dumps(sheet, ensure_ascii=False, indent=2))
        return

    now = datetime.now()
    mp3 = DRILLS_DIR / f"drill_{now.strftime('%Y-%m-%d_%H%M')}.mp3"
    print("2. render…")
    asyncio.run(render(sheet, mp3, args.gap))

    if args.no_publish:
        return

    print("3. publish…")
    # Delivery seam (2026-07-26 ledger law): the due items Python put on the
    # sheet went out the door — declared exposure, stamped at publish.
    exposed = record_exposure([t["word"] for t in pending])
    # The order this run consumed is spent — declare it, or the session-open drain
    # sees an unfilled order and dispatches an EPISODE for a repair already drilled.
    stamped = mark_soak_delivered("drill") if (focus or lead) else False
    subprocess.run([sys.executable, str(BASE / "scripts" / "rebuild_rss.py")], cwd=BASE, check=True)
    commit_and_push([mp3, BASE / "rss.xml"] + ([LEXICON_PATH] if exposed else [])
                    + ([BASE / "progress" / "learner.json"] if stamped else []),
                    f"Drill track: {sheet.get('title', mp3.stem)}")
    # This lane had NO quiet-hours check at all and pushed a drill at 23:42
    # (2026-07-26). The guard lives in push_to_phone now, so every lane —
    # including ones not written yet — inherits it.
    print("4. notify…")
    pushed = push_to_phone(f"drill's up — {len(sheet['items'])} out loud, gaps are yours 🎧",
                           jsdelivr_url(mp3))
    print(f"done — drill on the feed{' and the lock screen' if pushed else ''}.")


if __name__ == "__main__":
    main()
