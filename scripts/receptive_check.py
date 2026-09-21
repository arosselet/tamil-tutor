"""Recognition recording for monthly checks and ordinary lessons.

Extracted from sync_state.cmd_check rather than growing that command router.
Lesson observations reuse the existing channel, medium, source and note fields:
the clip and answer survive, and an ordinary lesson cannot reset the monthly cue.
Supported understanding belongs in the debrief, not in independent recognition
grades. Rendering or replaying a clip never calls this writer.
"""
import hashlib
import random

import lexicon_view
from state_io import (LEXICON_PATH, build_phonetic_index, load_json, local_today,
                      resolve, save_json)


def run(args):
    """Return (exit status, state changed); the CLI refreshes its thin summary."""
    session = getattr(args, "session", False)
    source = (getattr(args, "source", "") or "").strip()
    note = (getattr(args, "note", "") or "").strip()
    if session and (args.draw or not source or not note):
        print("  ! --session needs --source and --note (actual reply and support); "
              "it cannot draw a monthly sample. Nothing recorded.")
        return 1, False
    lexicon = load_json(LEXICON_PATH) or {}
    phon_index = build_phonetic_index(lexicon)
    today = local_today().isoformat()
    if args.draw:
        never = sorted(k for k, v in lexicon.items()
                       if not v.get("heard_on") and v.get("production", "none") in ("none", None))
        seed = f"check-{today[:7]}"
        pick = sorted(random.Random(seed).sample(never, min(args.draw, len(never))))
        digest = hashlib.sha256("\n".join(pick).encode()).hexdigest()[:16]
        print(f"RECEPTIVE CHECK — {len(pick)} of {len(never)} never-tested rows, seed {seed}, "
              f"sample {digest}. Recognition only; one item at a time, in the flow; never show the list.")
        for k in pick:
            print(f"  {k}  [{', '.join(lexicon[k].get('phonetic') or []) or 'no phonetic'}] "
                  f"— {lexicon[k].get('gloss', '')}")
        print("Record with: sync_state.py check --heard WORD:right (by ear) "
              "| --read WORD:right (on the page)")
        return 0, False
    events, bad = [], []
    for spec, medium in [(s, "audio") for s in args.heard] + [(s, "text") for s in args.read]:
        word, _, res = spec.rpartition(":")
        key = resolve(word.strip(), lexicon, phon_index)
        if key is None or res not in ("right", "wrong", "partial"):
            bad.append(spec)
            continue
        events.append(dict(word=key, channel="session" if session else "check",
                           kind="tested", axis="recognition", result=res, medium=medium,
                           source=source or f"check:{today}",
                           note=note or f"receptive check ({medium})"))
    for spec in bad:
        print(f"  ! {spec!r} — expected WORD:right|wrong|partial with a word "
              "the lexicon knows. Skipped.")
    if events:
        lexicon_view.observe(events, lexicon=lexicon)
        save_json(LEXICON_PATH, lexicon)
        right = sum(1 for e in events if e["result"] == "right")
        by_ear = sum(1 for e in events if e["medium"] == "audio")
        label = "Lesson recognition" if session else "Receptive check"
        print(f"  {label}: {len(events)} items recorded ({by_ear} by ear, "
              f"{len(events) - by_ear} on the page), {right} known outright. "
              "Engineering number — steers the pool; never recited.")
        if session or not by_ear:
            print("  Monthly check cue unchanged by ordinary lessons or page-only checks.")
    return (1 if bad else 0), bool(events)
