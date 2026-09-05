#!/usr/bin/env python3
"""The payoff — the tape he already heard, handed back with its meaning attached.

WHY THIS EXISTS (2026-09-05, Andrew, on the town-bank eavesdrop): *"it was almost
incomprehensible to me… I hear it a couple of times, it's mostly noise, I guess
at the answer."* The measurement behind the felt signal: eighteen eavesdrop tapes
have fired since 2026-07-16, four got a graded answer — and `target_revealed` is
false on every single one. Nothing in this system has ever told him what a tape
SAID. The drift judge grades whether he caught the gist and the tape is then
spent, so the one lane `docs/comprehension_plan.md` calls the ear's only live
input channel has never once closed its own loop.

WHAT IT REPLACES: the raw tape's RESIDENCY IN THE FEED. A knock memo has been a
feed item since 2026-07-05 ("all audio you push me should go in the feed" — a
dismissed notification must stay replayable), and for a tape he cannot parse that
item is noise he scrolls past. The payoff takes its place: `rebuild_rss` drops
`knock_<ts>.mp3` from the feed exactly when `payoff_<ts>.mp3` is standing there
to replace it. The mp3 is never deleted — it stays in the repo, on the CDN, and
in the log's `audio_url`, so nothing already pointing at it breaks.

IT AMENDS ONE SETTLED DECISION, for this lane only. *"A published episode is a
spent dose, not a record to keep true"* (2026-08-10) is why a renderer fix
obliges no backfill. An eavesdrop tape is the exception Andrew named, and the
reason is in the ledger's own words: an episode's dose is spent because "its
words have already moved through the lexicon". A tape he could not parse moved
nothing. Episodes are untouched by this; do not generalise it.

WHY IT IS NOT AN INLINE OVERWRITE, which is what he asked for first. The guid is
the enclosure url is the filename. Rewriting `knock_<ts>.mp3` in place leaves a
podcast client with an episode it has already downloaded: no refetch, no new
item, the payoff never reaches the ear it was made for — and a published title
moving under a stable guid is the exact shape that forked one dose into two
episodes on 2026-07-24. So a payoff is a NEW file under a new name, which is
already this repo's convention for a re-render (`_vN`, `rebuild_rss.md_name`).

WHEN IT FIRES: when the tape's rep is CLOSED — he answered, or the window ran
out. Not "once he replies", which is what the itch first asked for: eleven of the
eighteen tapes got no reply at all, and those are precisely the ones whose
meaning he never got. Publishing earlier would hand him the answer key to a drift
question he has not been asked yet.

THE RHYTHM IS PYTHON'S, never the model's — the law `render_soak` states:

    line · meaning · line       the soak rhythm, once per line
    the tape, at speed          blind — "captioned until it snaps, then blind;
                                blind is the win" (2026-07-13)

ONE SPEED PASS, AT THE END. The dose opened on the tape too until 2026-09-05,
when Andrew heard the first two: *"this feels like a bookend within a bookend…
the inner bookend is probably more useful."* He is right, and the reason the
front pass looked obligatory is that it was inherited from `render_soak`, where
the opening pass is the learner's FIRST hearing. A payoff's is not. The knock
already played him this tape at speed — days ago, on his phone — and it is
precisely because he could not parse it then that this file exists. Playing it
again before a single meaning is attached is a third hearing of an unparseable
thing, and it cost ~20s of a 2:30 dose.

The CLOSING pass keeps its place, and it carries the whole argument the pair
used to share: it is the only place the tape is heard CONNECTED, at speed, with
the meanings already in his head. The walk's own repeats are per line, so they
never test the joins — and "ticket book aayidum" is a join. Drop this one and
the lane has no blind pass at all, which is the instrument, not the packaging.

That speed pass is the ORIGINAL mp3's frames, not a re-render: it costs no
TTS, and it guarantees the thing he re-hears is the thing he heard.

THE MODEL NEVER RETYPES THE TAMIL. It is handed numbered lines and returns a
meaning per number; Python holds the tape throughout. A gloss pass that re-emits
its source is a transcription pass wearing a translation's name, and the answer
key of a comprehension lane is the last text in this repo that should round-trip
through a generator. Alignment is checked BY NUMBER, so a model that returns the
right quantity of misaligned glosses is refused rather than rendered.

    python scripts/render_payoff.py --dry-run    # sheet only, no TTS
    python scripts/render_payoff.py              # sheet -> render -> feed + push
    python scripts/render_payoff.py --knock-id <timestamp>   # one tape, now

Secrets: OPENROUTER_API_KEY or `claude -p` (the sheet), GCP ADC (TTS),
ANNA_PUSH_WEBHOOK_URL (the push).
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from lanes import deliver_rendered
from language import ANNA_VOICE, EAVESDROP_VOICE, TAMIL_RE
from publish import (KNOCKS_DIR, commit_and_push, load_env, publish,
                     push_to_phone)
from rebuild_rss import MIN_PLAYABLE_BYTES
from render_audio import (EXIT_NOT_CONFIGURED, SILENCE_FRAME, clean_for_tts,
                          clean_memo_for_tts, generate_segment_google,
                          get_raw_mp3_frames, google_credentials_ready)
from state_io import (FEEDBACK_LOG_PATH, KNOCK_LOG_PATH, load_json, local_today,
                      save_json)
from writer import INT, STR, arr, ask_json, executor_name, obj, voice_canon

# Frames per second, matching render_soak/render_audio.
SILENCE_PER_SEC = 41.666
# An unanswered tape closes after this. It is not a guess at his attention span:
# the eavesdrop cadence is one tape every three days (EAVESDROP_CADENCE_DAYS), so
# a day is long enough that no live rep is ever spoiled and short enough that the
# meaning arrives while he can still remember hearing the thing.
HOLD_HOURS = 24
# The lane this evidence names, and only it. An `audio` memo is Anna talking to
# him in a voice he has been trained on; a `fielding` prompt is one line. The
# eavesdrop tape is the dose deliberately pitched below the coverage floor — the
# one he is MEANT to half-miss — which is what makes an unglossed one worthless
# afterwards. Widening this to another modality is a decision, not a constant.
TAPE_MODALITY = "eavesdrop"
# Two failed sheets and the tape is left alone. A retry that can never succeed
# spends a model call and writes a ledger line every wake-up forever, which is
# the "warning that cannot be discharged" this repo already refuses to ship.
MAX_TRIES = 2
# A refusal still commits — see `refuse`. `publish()` rebuilds no feed for it
# (nothing was rendered) and appends the log's derived page for us.
REFUSED = "Payoff: refused (logged)"

# One sentence per line — the unit a gloss aligns to. Script-neutral on purpose:
# sentence-final punctuation is not a language fact, so this is not pack surface.
SENTENCE = re.compile(r"[^.!?…]+[.!?…]*")

# NOT PORT SURFACE, and `s93` is told so in PROMPT_AGNOSTIC: this prompt names no
# language, no script, and no morphology. It asks for plain English meanings of
# numbered lines, which is the same request in any fork. The Tamil-specific
# canon a port rewrites lives in `mandates.py`; nothing of it is needed here.
PAYOFF_BRIEF = """\
THE PAYOFF SHEET. Andrew heard this tape on his phone and could not parse it. \
You are giving it back to him with its meaning attached, so he can play it again \
and actually follow it. This is not a rep: nothing is graded and nothing is \
withheld — he has already answered, or the moment has passed.

The tape's lines are numbered below. Return ONE gloss per number: `n` is the \
line's number exactly as given, `en` is what that line MEANS in natural spoken \
English — what the speaker is saying, not a word-by-word decoding. One sentence \
each. No commentary, and never quote the original line back inside `en`.

`opener` — one short spoken English line naming what he is about to hear (who is \
talking, what the call is about) and telling him the meaning comes after each \
line. `closer` — one short spoken English line giving \
the answer to the question he was asked about this tape, plainly, so the thing \
he was listening for is named out loud before the last playthrough.
"""

# `n` is what makes the alignment checkable — see `align`. Everything obj() names
# is REQUIRED, which is the point: a sheet missing `opener` is a broken dose.
PAYOFF_SHEET = obj(opener=STR, closer=STR, glosses=arr(n=INT, en=STR))


def _ts(raw: str | None) -> datetime | None:
    """A log timestamp as an aware datetime, or None. Both spellings occur in
    `knock_log.json` — the knock lane writes `+00:00`, the exchange rows `Z`."""
    try:
        when = datetime.fromisoformat((raw or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def stem_of(entry: dict) -> str:
    """The raw tape's filename stem — the join key between a knock, its payoff
    and the feed. Same read `rebuild_rss.knock_meta` makes: the knock lane
    records a repo-relative `mp3`, the drain and reply lanes only the CDN url."""
    ref = entry.get("mp3") or entry.get("audio_url") or ""
    return os.path.basename(ref).removesuffix(".mp3") if ".mp3" in ref else ""


def payoff_path(stem: str) -> Path:
    """`knock_2026-09-05T05-08` -> `…/knocks/payoff_2026-09-05T05-08.mp3`. The
    timestamp is carried over verbatim: it is what pairs the two in the feed, and
    `rebuild_rss` re-derives the pairing from these two names alone."""
    return KNOCKS_DIR / f"payoff_{stem.split('_', 1)[-1]}.mp3"


def tape_lines(memo_script: str) -> list[str]:
    """The tape as spoken lines. Paragraphs are the breath the memo was rendered
    with; sentences inside them are what a gloss can actually be attached to."""
    lines = []
    for para in (memo_script or "").split("\n\n"):
        lines += [m.group(0).strip() for m in SENTENCE.finditer(para.replace("\n", " "))
                  if m.group(0).strip()]
    return lines


def is_closed(entry: dict, now: datetime) -> bool:
    """Is this tape's rep over? Answered, or its window ran out."""
    if entry.get("response") or entry.get("reply_verdict"):
        return True
    when = _ts(entry.get("timestamp"))
    return bool(when and (now - when).total_seconds() >= HOLD_HOURS * 3600)


def pending(klog: list, now: datetime) -> list[dict]:
    """Closed tapes with no payoff yet, NEWEST FIRST — the tape he can still
    remember hearing is worth more than the one that has waited longest.

    Oldest-first is the obvious ordering and it is wrong here: on the day this
    shipped thirteen tapes were waiting, and draining them in order would have
    put the payoff for the tape he answered that morning thirteen wake-ups
    behind an eavesdrop from five weeks earlier. A stale tape's payoff is the
    weakest one in the queue; it goes last, and nothing starves — a tape closes
    every few days and this lane runs on every wake-up.

    A tape whose mp3 is not on disk is skipped rather than re-rendered: the
    payoff's first and last passes ARE that file, and a re-synthesised
    approximation of what he heard is a different tape wearing its name."""
    out = []
    for e in klog:
        stem = stem_of(e)
        if e.get("modality") != TAPE_MODALITY or not e.get("acted") or not stem:
            continue
        if e.get("payoff_mp3") or e.get("payoff_tries", 0) >= MAX_TRIES:
            continue
        if not (e.get("memo_script") or "").strip() or not is_closed(e, now):
            continue
        if (KNOCKS_DIR / f"{stem}.mp3").exists():
            out.append(e)
    return sorted(out, key=lambda e: e.get("timestamp") or "", reverse=True)


def write_sheet(entry: dict, lines: list[str]) -> dict:
    """The gloss pass. The tape goes down numbered; only meanings come back."""
    numbered = "\n".join(f"{i}. {ln}" for i, ln in enumerate(lines, 1))
    context = (f"THE TAPE ({entry.get('move', '')}):\n{numbered}\n\n"
               f"WHAT HE WAS ASKED ABOUT IT: {entry.get('body', '')}\n"
               f"WHAT HE ANSWERED: {entry.get('reply') or '— he never replied —'}")
    print(f"   [payoff sheet] {executor_name()}")
    return ask_json(voice_canon() + "\n\n---\n\n" + PAYOFF_BRIEF, context,
                    PAYOFF_SHEET, answer_tokens=900)


def align(lines: list[str], sheet: dict) -> tuple[list[str], str]:
    """Glosses in tape order, or ([], why-not).

    BY NUMBER, NOT BY COUNT, and that is the whole function. The failure this
    lane can have that looks exactly like success is a rendered payoff whose
    meanings sit against the wrong lines — every instrument green, an artifact
    that teaches him the tape wrong. A count check passes that; an index does
    not. The second refusal catches the other shape: a model that "glosses" a
    line by echoing it back, which renders as the tape said twice and explained
    never."""
    by_n: dict[int, str] = {}
    for g in sheet.get("glosses") or []:
        try:
            n = int(g.get("n"))
        except (TypeError, ValueError):
            continue
        en = " ".join((g.get("en") or "").split())
        if en and 1 <= n <= len(lines) and n not in by_n:
            by_n[n] = en
    missing = [i for i in range(1, len(lines) + 1) if i not in by_n]
    if missing:
        return [], f"no meaning for line {missing[:6]} of {len(lines)}"
    echoed = sorted(n for n, en in by_n.items() if TAMIL_RE.search(en))
    if echoed:
        return [], f"line {echoed[:6]} came back in the tape's own script, unglossed"
    return [by_n[i] for i in range(1, len(lines) + 1)], ""


def silence(seconds: float) -> bytes:
    return SILENCE_FRAME * int(seconds * SILENCE_PER_SEC)


async def render(tape: bytes, lines: list[str], glosses: list[str],
                 sheet: dict, out_path: Path):
    """Anna's frame, the walk, the answer, then the tape blind."""
    audio = bytearray()
    tmp = tempfile.mkdtemp(prefix="payoff_segments_")
    idx = 0
    cache: dict[tuple, bytes] = {}

    async def say(text: str, voice: str) -> bytes:
        """One segment, cached: a line is spoken twice in the walk alone, and
        re-synthesising it is money and latency for identical bytes. The aunty's
        lines take the memo cleaner they were first rendered with; Anna's take
        the dialogue one."""
        nonlocal idx
        key = (voice, text)
        if key not in cache:
            idx += 1
            clean = clean_memo_for_tts if voice == EAVESDROP_VOICE else clean_for_tts
            seg = await generate_segment_google(clean(text), voice, idx, tmp)
            cache[key] = get_raw_mp3_frames(seg)
            os.remove(seg)
        return cache[key]

    try:
        audio.extend(await say(sheet["opener"], ANNA_VOICE))
        audio.extend(silence(1.4))
        # NO TAPE HERE — see the rhythm note above. The knock was the at-speed
        # hearing; the walk starts straight after Anna's frame.
        for line, en in zip(lines, glosses):
            print(f"   [walk] {en[:56]}")
            spoken = await say(line, EAVESDROP_VOICE)
            audio.extend(spoken)                            # sound first
            audio.extend(silence(0.8))
            audio.extend(await say(en, ANNA_VOICE))         # meaning, once
            audio.extend(silence(0.6))
            audio.extend(spoken)                            # and settle
            audio.extend(silence(1.4))
        audio.extend(silence(0.8))
        audio.extend(await say(sheet["closer"], ANNA_VOICE))
        audio.extend(silence(1.8))
        audio.extend(tape)                                  # blind, the win
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    from rebuild_rss import audio_duration        # measured, never estimated
    secs = audio_duration(str(out_path)) or 0
    print(f"   rendered -> {out_path} ({len(audio)/1024:.0f} KB, {secs/60:.1f} min, "
          f"{idx} segments)")


def refuse(entry: dict, klog: list, why: str):
    """A payoff that cannot be made says so where the diagnosis pass reads, and
    counts its own attempts so the saying is bounded.

    The ledger line is written on the LAST try, not on every one: a note that
    reappears each wake-up is walked past for mechanical reasons rather than
    inattention, and a note that never appears at all leaves a tape silently
    unglossed forever. The count is stamped either way, and it is committed —
    an uncommitted count in a cloud runner is no count at all."""
    entry["payoff_tries"] = entry.get("payoff_tries", 0) + 1
    print(f"   ⚠ no payoff for {stem_of(entry)}: {why} "
          f"(try {entry['payoff_tries']}/{MAX_TRIES})")
    paths = [KNOCK_LOG_PATH]
    if entry["payoff_tries"] >= MAX_TRIES:
        flog = load_json(FEEDBACK_LOG_PATH) or []
        flog.append({"date": local_today().isoformat(),
                     "note": f"[payoff] the {entry.get('date')} tape "
                             f"({entry.get('move')}) has no payoff and will not be "
                             f"retried — {why}. He heard it and never got its meaning."})
        save_json(FEEDBACK_LOG_PATH, flog)
        paths.append(FEEDBACK_LOG_PATH)
    save_json(KNOCK_LOG_PATH, klog)
    return paths


def main():
    ap = argparse.ArgumentParser(description="Re-cut a heard tape with its meaning")
    ap.add_argument("--knock-id", help="one tape by its log timestamp, closed or not")
    ap.add_argument("--dry-run", action="store_true", help="sheet only; no TTS, no publish")
    ap.add_argument("--no-publish", action="store_true", help="render only; no feed/commit/push")
    args = ap.parse_args()

    load_env(BASE / ".env")
    klog = load_json(KNOCK_LOG_PATH) or []
    now = datetime.now(timezone.utc)
    if args.knock_id:
        due = [e for e in klog if e.get("timestamp") == args.knock_id]
    else:
        due = pending(klog, now)
    if not due:
        print("No closed tape is waiting for a payoff.")
        return
    # ONE PER RUN, freshest first. Thirteen tapes were waiting the day this shipped;
    # minting them in one tick would be eleven notifications, eleven commits and
    # a feed that turns over in a minute. The backlog drains at the rate he can
    # actually listen, and every wake-up carries a lane that can mint one.
    entry = due[0]
    stem = stem_of(entry)
    lines = tape_lines(entry.get("memo_script", ""))
    print(f"1. sheet… ({entry.get('date')} · {entry.get('move')} · {len(lines)} lines)")
    if not lines:
        commit_and_push(*publish(refuse(entry, klog, "the tape has no lines"), REFUSED))
        return

    sheet = write_sheet(entry, lines)
    glosses, why = align(lines, sheet)
    if why:
        commit_and_push(*publish(refuse(entry, klog, why), REFUSED))
        return
    if args.dry_run:
        print(json.dumps({"opener": sheet["opener"], "closer": sheet["closer"],
                          "walk": list(zip(lines, glosses))},
                         ensure_ascii=False, indent=2))
        return

    reason = google_credentials_ready()
    if reason:
        print(f"⏭️  Skipping render — {reason}. This host cannot produce audio.")
        sys.exit(EXIT_NOT_CONFIGURED)

    mp3 = payoff_path(stem)
    print("2. render…")
    tape = get_raw_mp3_frames(str(KNOCKS_DIR / f"{stem}.mp3"))
    asyncio.run(render(tape, lines, glosses, sheet, mp3))
    if args.no_publish:
        return
    # THE STAMP FOLLOWS THE ARTIFACT, never the intention. `rebuild_rss` decides
    # what the feed shows from the FILES, so this field is bookkeeping and the
    # audit trail — but a stamp written over a render that did not survive would
    # retire a tape whose payoff nobody can play.
    if not (mp3.exists() and mp3.stat().st_size >= MIN_PLAYABLE_BYTES):
        commit_and_push(*publish(refuse(entry, klog, "the render produced nothing playable"),
                                 REFUSED))
        return
    entry["payoff_mp3"] = mp3.relative_to(BASE).as_posix()
    save_json(KNOCK_LOG_PATH, klog)

    print("3. publish…")
    # `delivered` is EMPTY and that is the law, not an omission: an eavesdrop's
    # exposures are declared at the knock seam (`knock_exposures`, 2026-07-26) and
    # were already stamped when the tape went out. Mining them again here would
    # double-count the one ledger that picks tomorrow's targets. `claimed` is
    # False for the same reason — a payoff answers no soak order.
    deliver_rendered(
        mp3=mp3, lane="payoff", delivered=[], claimed=False,
        extra_paths=[KNOCK_LOG_PATH],
        message=f"Payoff: {entry.get('date')} tape ({entry.get('move')})",
        title=entry.get("move", ""),
        copy=f"🎧 that tape from {entry.get('date')} — same call, with the meaning "
             f"after every line.",
        noun="payoff", commit=commit_and_push, notify=push_to_phone)


if __name__ == "__main__":
    main()
