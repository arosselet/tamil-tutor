#!/usr/bin/env python3
"""
The drill track — a hands-free SPOKEN production volley from the pool's due list.

Everything else in the system is typed chat or listen-only immersion; the trip is
spoken. This closes that gap Pimsleur-style: Anna speaks an English cue, silence
while Andrew SAYS THE TAMIL OUT LOUD, then the answer lands (twice). Built straight
from the due fire-side items, so a walk or the dishes becomes real reps.

Same one-shot family as the knock: the LLM writes the sheet (cues + answers),
Python owns the menu (the due list), the render, and the publish. Listening
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
import sys
import tempfile
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from lanes import deliver_rendered
from publish import commit_and_push, load_env, push_to_phone
from language import ANNA_VOICE
# THE EXECUTOR CHOICE LEFT THIS FILE (2026-08-23). `ask_json` used to live here
# and open an OpenRouter client unconditionally — on a laptop that has an agent
# and a paid subscription. `writer.ask_json` is the same contract plus the host
# test; `render_rotation` now imports it from there too, so the "four lanes share
# it" note this file used to carry is still true, one level up.
from writer import INT, STR, arr, ask_json, executor_name, obj

# The two shapes this lane asks for (see writer.obj).
DRILL_SCHEMA = obj(intro=STR, outro=STR, items=arr(cue=STR, answer_ta=STR))
LINT_SCHEMA = obj(verdicts=arr(n=INT, verdict=STR))
from render_audio import generate_segment_google, get_raw_mp3_frames, SILENCE_FRAME, clean_for_tts
from suggest_targets import drill_menu
from mandates import DRILL_MANDATE, LINT_MANDATE
from state_io import LEXICON_PATH, load_json
from state_io import canon_payload

DRILLS_DIR = BASE / "published_audio"   # feed root — rebuild_rss picks up drill_*.mp3
SILENCE_PER_SEC = 41.666                # frames per second (matches render_audio)

# Appended when the standing order routed a REPAIR to this lane. The commissioned
# item leads and gets three angles; the pool fills the rest of the tape. LEAD, not
# replace (2026-07-28, Andrew's call): a whole drill built from one item is the
# slow repetitive loop this lane was commissioned to escape.
COMMISSION_BRIEF = """

THE COMMISSION — the FIRST {n} item(s) of the DUE list are a REPAIR, not routine \
mouth reps. Give each of them THREE items instead of one: three different cues, three \
different everyday situations, the same target every time. Vary the situation, never the \
target — using it in context is the whole point of drilling it again. Everything after \
them is the ordinary drill and keeps its normal shape (one item per chunk, two per \
frame).{focus}
"""


def due_payload(max_entries: int) -> list[dict]:
    """The selector's order, but interleaved frame/chunk — a drill is mouth-reps,
    and a slot-fill and a said-whole phrase are different work, so a run of six
    frames is a worse drill than an alternating six.

    That is now the ONLY reason. Until 2026-07-25 this also worked around a
    starving sort: the selector broke ties alphabetically and ASCII 'frame:' keys
    sorted ahead of every Tamil-script chunk, so a straight head-slice was all
    frames. The selector is coverage-first now (a plain top-6 measures 2 frames /
    4 chunks), so this is a pedagogy choice and no longer a guard — delete it the
    day that stops being true.

    Reads `drill_menu` since 2026-08-18 (was `deck_status`): the same order over
    the whole pool rather than over the 83-row container that retired with the
    trip."""
    menu = drill_menu(load_json(LEXICON_PATH) or {}, max_n=max(max_entries * 2, 12))
    if not menu:
        return []
    frames = [t for t in menu if t["kind"] == "frame"]
    chunks = [t for t in menu if t["kind"] != "frame"]
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
    a repair routed here silently became an ordinary drill, the order stayed
    pending, and the next session-open auto-drain dispatched an EPISODE for it —
    the one lane Andrew had explicitly not chosen.

    EAR-ONLY items are REFUSED, never demanded. `direction: catch` means the win is
    recognition, and a drill's silence is a production demand — the standing law is that
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
    """The commissioned repair leads the tape; the due menu fills out the rest.
    A lead item already on the menu is not drilled twice."""
    if not lead:
        return pending
    have = {t["word"] for t in lead}
    return lead + [t for t in pending if t["word"] not in have]


def write_sheet(pending: list[dict], n_lead: int = 0, focus: str | None = None) -> dict:
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    menu = "\n".join(f"- [{t['kind']}] {t['word']} — {t['gloss'] or '[no gloss]'}"
                     for t in pending)
    mandate = DRILL_MANDATE
    if n_lead:
        mandate += COMMISSION_BRIEF.format(
            n=n_lead, focus=f"\nWhat the repair is about: {focus}" if focus else "")
    print(f"   [drill sheet] {executor_name()}")
    sheet = ask_json(persona + "\n\n---\n\n" + mandate, f"DUE:\n{menu}",
                     DRILL_SCHEMA)
    sheet["items"] = [i for i in sheet.get("items", [])
                      if i.get("cue", "").strip() and i.get("answer_ta", "").strip()]
    return sheet


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
    verdicts = ask_json(LINT_MANDATE, listing, LINT_SCHEMA,
                        answer_tokens=1200).get("verdicts", [])
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
    ap = argparse.ArgumentParser(description="Spoken production drill from the pool's due list")
    ap.add_argument("--entries", type=int, default=8,
                    help="menu entries to drill (frames expand to 2 items; default 8)")
    ap.add_argument("--gap", type=float, default=3.5,
                    help="seconds of silence for Andrew's out-loud attempt (default 3.5)")
    ap.add_argument("--dry-run", action="store_true", help="write + print the sheet; no TTS or publish")
    ap.add_argument("--no-publish", action="store_true", help="render only; skip RSS/commit/push/notify")
    args = ap.parse_args()

    load_env(BASE / ".env")

    # The commission is read FIRST: a repair routed here must still get its tape
    # on a day the pool happens to have nothing due.
    focus, lead = drill_brief()
    pending = with_lead(due_payload(args.entries), lead)
    if not pending:
        print("No due fire-side items — nothing to drill.")
        return

    print(f"1. sheet… ({len(pending)} menu entries"
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
    # The tail belongs to the family (2026-08-24). Everything the DRILL lane knows
    # that the others do not stays here: the due menu it put on the sheet is what
    # went out the door, so that is its `delivered`.
    deliver_rendered(
        mp3=mp3, lane="drill", delivered=[t["word"] for t in pending],
        claimed=bool(focus or lead),
        message=f"Drill track: {sheet.get('title', mp3.stem)}",
        copy=f"drill's up — {len(sheet['items'])} out loud, gaps are yours 🎧",
        noun="drill", commit=commit_and_push, notify=push_to_phone)


if __name__ == "__main__":
    main()
