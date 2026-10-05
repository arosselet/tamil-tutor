#!/usr/bin/env python3
"""
The sort tape — the Receptive Check, moved onto the channel he actually uses.

WHY IT EXISTS (2026-10-03, Andrew). The felt complaint was "80% words I already
know, 20% never taught", and the lexicon explains the first half exactly: 356 of
392 rows read `struggled` — including the commonest words in the language — so
every planner treats a word he has known since February as filler it must keep
re-airing. The ledger held 1,193 `taught` events about the MACHINE and 27
`attended` events about HIM. The instrument that fixes that already existed:
the monthly Receptive Check (`receptive_check.py`). It fired once, because it
lived in a chat session, and chat is the one thing a tired evening never opens.

So this is that check, delivered as a tape: ~20 numbered lines, each spoken
twice, a pause, then the meaning. He keeps count on a walk and replies once —
"missed 4, 9, 13" or "got them all" — from the lock screen or the Shortcut.
Every line becomes one `tested` / recognition / audio event on the `check`
channel, which is what a by-ear Receptive Check already writes.

WHAT THIS REPLACES: the chat-only delivery of the Receptive Check. It adds no
field, no meter and no rung rule — the fold climbs one rung per `right` and
falls one per `wrong`, exactly as it does for every other watched test.

THE DRAW. Every `untested` row, taught or not (2026-10-05, Andrew: "all you had
to do was ask"). Asking is not teaching and a miss costs nothing: it lands on
`struggled` and the row still waits for its Teach Beat; a right answer proves
first contact and opens the gate (`lexicon_view.derive`). Most-aired first:
the rows the tapes keep re-teaching are the ones most likely to be known, and
clearing them is what frees the next tapes for new words. A wrong answer stamps
`heard_on` too, so a tape never re-draws its own lines; a missed word goes back
to the lanes that teach, not to the next sort tape.

THE REPLY (`claim_reply` / `handle_reply`, called from `knock_reply.main`). The
parse is Python's, deterministic, no model: a sort reply is numbers. An answer
that parses to nothing records NOTHING and says so on the lock screen — the
silent no-op this lane must never have is a reply that looked accepted.
`commit` and `notify` are passed in by the caller (the `lanes.py` seam law), so
knock_reply's stubs intercept this half exactly as they intercept its own.

  python scripts/render_sort.py --plan-only    # print the draw; no network
  python scripts/render_sort.py --no-publish   # render locally, nothing leaves
  python scripts/render_sort.py                # render -> feed + knock log + push
"""
import argparse
import asyncio
import os
import random
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import lexicon_view
import writer
from language import ANNA_VOICE, TAMIL_RE
from publish import commit_and_push, jsdelivr_url, load_env, publish, push_to_phone
from state_io import (KNOCK_LOG_PATH, LEXICON_PATH, RECOGNITION_DEFAULT, load_json,
                      local_today, save_json)

KNOCK_DIR = BASE / "published_audio" / "knocks"
MODALITY = "sort"
SIZE = 20
REPLY_WINDOW = timedelta(days=4)   # an id-less "missed 4, 9" finds a tape this recent
FRAMES_PER_SEC = 41.666            # matches render_audio's SILENCE_FRAME
THINK = 3.0                        # the one spliced silence: between the sayings and the meaning
# Every call carries the previous meaning, a number and the word twice — several
# seconds of speech. A clip under this floor is the voice returning nothing.
MIN_CALL_SECS = 1.0

INTRO = ("Sort tape. {n} lines, numbered. Each one twice, a pause, then the meaning. "
         "Keep count of the numbers you didn't get before the meaning came. "
         "At the end, just tell me the numbers you missed. Or: got them all.")
OUTRO = "That's the lot. Tell me the numbers you missed, or got them all."
COPY = "Sort tape — {n} lines 🎧 Reply with the numbers you missed, or 'got them all'."


def pool(lexicon: dict) -> list[str]:
    """Rows a sort tape may test, most-aired first: rung `untested`, taught or
    not (the teach gate guards drills, not questions, 2026-10-05) — no watched
    recognition test in EITHER medium (2026-10-04, Andrew: "if I recognize it,
    it applies whether I read or listen"). This replaced an ear-only `heard_on`
    filter that re-drew words he had just answered on the page; a sort tape is
    single words, not speech at speed, so it adds nothing a page answer lacks."""
    keys = [k for k, r in lexicon.items()
            if TAMIL_RE.search(k) and not k.startswith("frame:") and len(k) > 1
            and r.get("recognition") == RECOGNITION_DEFAULT]
    return sorted(keys, key=lambda k: (-(len(lexicon[k].get("seen_in") or [])
                                         + (lexicon[k].get("exposures") or 0)), k))


def draw(lexicon: dict, n: int = SIZE, seed: str = "") -> list[str]:
    """The top `n` of the pool, in a shuffled order — most-aired is the PICK,
    never the running order, or every tape would open on its easiest line."""
    pick = pool(lexicon)[:n]
    random.Random(seed).shuffle(pick)
    return pick


def _sentence(text: str) -> str:
    return (t := text.strip()) and (t if t[-1] in ".!?" else t + ".")


def script(items: list[str], lexicon: dict) -> list[tuple[str, float]]:
    """(text, silence after) in speaking order — ONE TTS call per item, and the
    word is never sent alone. The transcript is this, joined.

    Why one call per item (2026-10-03): the first tape sent every number, word
    and meaning as its own call — 82 calls, 40 of them a bare word — and
    Chirp3-HD answers a one- or two-syllable input with ~0.3 s of silence, not
    reliably. சரி and அது played as dead air both times, ஆமா once, and the
    meaning "No" once. So each call is: the previous item's meaning, the next
    number, the word twice; the full stops pace those short gaps. The thinking
    pause is the only silence spliced in, because it is the only one whose
    length the test depends on. 21 calls for 20 lines, none of them short."""
    lead, out = INTRO.format(n=len(items)), []
    for i, key in enumerate(items, 1):
        out.append((f"{lead} {i}. {_sentence(key)} {_sentence(key)}", THINK))
        lead = _sentence(lexicon[key].get("gloss") or "")
    return out + [(f"{lead} {OUTRO}".strip(), 0.5)]


async def render(lines: list[tuple[str, float]], out: Path):
    """Raises before writing anything if a call comes back as silence: a tape
    with dead air must never reach the feed (the file-exists check after this
    cannot see it — the 2026-10-03 tape was full length with six silent clips)."""
    from rebuild_rss import audio_duration
    from render_audio import (SILENCE_FRAME, clean_memo_for_tts,
                              generate_segment_google, get_raw_mp3_frames)
    audio = bytearray()
    tmp = tempfile.mkdtemp()
    for i, (text, gap) in enumerate(lines):
        seg = await generate_segment_google(clean_memo_for_tts(text), ANNA_VOICE, i, tmp)
        if (secs := audio_duration(seg) or 0.0) < MIN_CALL_SECS:
            raise RuntimeError(f"call {i + 1} came back as {secs:.2f}s of audio: {text!r}")
        audio.extend(get_raw_mp3_frames(seg))
        audio.extend(SILENCE_FRAME * int(gap * FRAMES_PER_SEC))
        os.remove(seg)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)


# ── The reply half ──────────────────────────────────────────────────────────

_UNITS = ("zero one two three four five six seven eight nine ten eleven twelve "
          "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = {"twenty": 20, "thirty": 30}
_HITS = re.compile(r"\b(got|knew|caught|heard)\b")
_ALL_MISSED = re.compile(r"\bmissed (them )?all\b|\bmissed everything\b|\bgot none\b|\bnone of them\b")
_NONE_MISSED = re.compile(r"\b(missed|miss) (none|nothing|zero)\b|\bnone missed\b|"
                          r"\b(got|knew|caught|heard) (them |it )?all\b|\ball of them\b|\beverything\b")


def numbers(text: str) -> list[int]:
    """Digits or spoken numbers up to 39 — dictation writes either."""
    out, toks = [], re.findall(r"[a-z]+|\d+", text.lower())
    for i, t in enumerate(toks):
        if t.isdigit():
            out.append(int(t))
        elif t in _TENS:
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            out.append(_TENS[t] + (_UNITS.index(nxt) if nxt in _UNITS[1:10] else 0))
        elif t in _UNITS[1:] and not (i and toks[i - 1] in _TENS and t in _UNITS[1:10]):
            out.append(_UNITS.index(t))
    return out


def parse_reply(text: str, n: int) -> set | None:
    """The 1-based numbers he MISSED, or None when the reply says nothing
    countable. Numbers name misses unless he said got/knew and never 'miss'."""
    t = text.lower()
    nums = {x for x in numbers(t) if 1 <= x <= n}
    if nums:
        hits = _HITS.search(t) and not re.search(r"miss|\bbut\b|\bexcept\b", t)
        return set(range(1, n + 1)) - nums if hits else nums
    if _ALL_MISSED.search(t):
        return set(range(1, n + 1))
    if _NONE_MISSED.search(t):
        return set()
    return None


def claim_reply(klog: list, knock_id: str, text: str) -> dict | None:
    """The sort knock this reply answers, or None to leave it to the other lanes.
    A tagged reply belongs to its knock. An untagged one is claimed only when it
    parses as a sort answer AND a recent sort tape is still unanswered — another
    knock may well have fired between the walk and the reply."""
    if knock_id:
        k = next((k for k in reversed(klog) if k.get("timestamp") == knock_id), None)
        return k if k and k.get("modality") == MODALITY else None
    open_tapes = [k for k in klog if k.get("modality") == MODALITY and not k.get("sorted_at")]
    if not open_tapes or parse_reply(text, len(open_tapes[-1].get("items") or [])) is None:
        return None
    k = open_tapes[-1]
    age = datetime.now(timezone.utc) - datetime.fromisoformat(k["timestamp"])
    return k if age <= REPLY_WINDOW else None


def _label(key: str, lexicon: dict) -> str:
    """How a word is named in the push-back: its key and meaning. The key is
    script, so the finished line goes through `writer.to_phonetic` before he
    reads it — phonetics are generated for display, never stored (DECISIONS
    2026-09-13). This read a stored `phonetic` list until 2026-10-05, and printed
    the gloss alone for the third of the lexicon that had none."""
    return f"{key} '{lexicon.get(key, {}).get('gloss', '')}'"


def handle_reply(knock: dict, text: str, klog: list, lexicon: dict, dry_run: bool,
                 *, commit, notify):
    items = knock.get("items") or []
    missed = None if knock.get("sorted_at") else parse_reply(text, len(items))
    events, lines = [], []
    if knock.get("sorted_at"):
        line = "Already logged that one — the next sort tape brings fresh lines."
    elif missed is None:
        line = "Didn't catch any numbers — reply like 'missed 4, 9' or 'got them all'. Nothing logged."
    else:
        for i, key in enumerate(items, 1):
            if key not in lexicon:
                lines.append(f"! #{i} {key!r} is no longer in the lexicon — not scored")
                continue
            events.append(dict(word=key, channel="check", kind="tested", axis="recognition",
                               result="wrong" if i in missed else "right", medium="audio",
                               source=f"sort:{knock['timestamp']}", note=f"sort tape #{i}"))
        misses = [f"#{i} {_label(items[i - 1], lexicon)}" for i in sorted(missed)]
        line = ("Logged. Back to teaching for: " + " · ".join(misses)) if misses \
            else "Logged — all of them. Next tape draws fresh lines."
    for msg in lines:
        print(f"   {msg}")
    print(f"   sort reply → {len(events)} events | {line}")
    if dry_run:
        return
    line_script, line = line, writer.to_phonetic(line, label="sort push-back")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    verdict = "sorted" if events else "unparsed"
    if events:
        # The scored reply owns the knock's top-level fields; a later "already
        # logged" or unparsed reply is an exchange row, never an overwrite.
        lexicon_view.observe(events, lexicon=lexicon)
        save_json(LEXICON_PATH, lexicon)
        knock.update(sorted_at=now, response="reply", reply=text, reply_at=now,
                     reply_line=line, reply_line_script=line_script, reply_verdict=verdict)
    knock.setdefault("exchanges", []).append({
        "at": now, "reply": text, "verdict": verdict, "fired": [],
        "reply_line": line, "reply_line_script": line_script})
    save_json(KNOCK_LOG_PATH, klog)
    commit(*publish([LEXICON_PATH if events else None, KNOCK_LOG_PATH],
                    f"Knock reply: {verdict} (sort tape)"))
    notify(line, None, knock_id=knock.get("timestamp", ""), requested=True)


# ── The render half ─────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render and deliver one sort tape")
    ap.add_argument("--size", type=int, default=SIZE)
    ap.add_argument("--plan-only", action="store_true", help="print the draw; no network")
    ap.add_argument("--no-publish", action="store_true", help="render locally only")
    args = ap.parse_args(argv)

    lexicon = load_json(LEXICON_PATH) or {}
    now = datetime.now(timezone.utc)
    items = draw(lexicon, args.size, seed=now.isoformat())
    print(f"SORT TAPE — {len(items)} of {len(pool(lexicon))} untested rows, taught or not")
    for i, k in enumerate(items, 1):
        print(f"  {i:>2}. {k} — {lexicon[k].get('gloss', '')}")
    if not items:
        print("  ! nothing to sort: every row has been tested. Nothing rendered.")
        return 1
    if args.plan_only:
        return 0

    load_env(BASE / ".env")
    lines = script(items, lexicon)
    stamp = now.astimezone().strftime("%Y-%m-%dT%H-%M")
    out = KNOCK_DIR / f"knock_{stamp}.mp3"
    if out.exists():
        print(f"  ! {out.name} already exists — one sort tape a minute. Nothing rendered.")
        return 1
    asyncio.run(render(lines, out))   # a silent call raises here: nothing written, logged or pushed
    if not out.is_file() or out.stat().st_size == 0:
        print("  ! the render produced nothing playable. Nothing logged.")
        return 1
    print(f"  rendered -> {out}")
    if args.no_publish:
        return 0

    copy = COPY.format(n=len(items))
    klog = load_json(KNOCK_LOG_PATH) or []
    klog.append({"date": local_today().isoformat(), "timestamp": now.isoformat(),
                 "acted": True, "modality": MODALITY, "move": "Sort tape",
                 "rationale": "Receptive Check by ear: untested rows, taught or not, most-aired first.",
                 "body": copy, "items": items,
                 "memo_script": "\n\n".join(t for t, _ in lines),
                 "mp3": out.relative_to(BASE).as_posix(), "audio_url": jsdelivr_url(out)})
    save_json(KNOCK_LOG_PATH, klog)
    commit_and_push(*publish([KNOCK_LOG_PATH], f"Sort tape: {len(items)} lines", mp3=out))
    pushed = push_to_phone(copy, jsdelivr_url(out), knock_id=now.isoformat())
    print(f"done — sort tape on the feed{' and the lock screen' if pushed else ''}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
