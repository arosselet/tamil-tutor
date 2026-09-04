#!/usr/bin/env python3
"""The voice-memo renderer — a script in, an mp3 out, for any lane that speaks.

WHAT THIS REPLACES (2026-09-04): `render_memo` living in `morning_knock.py`, the
last thing that made a LANE a foundation for its peers. Three modules called it
there — the knock that first needed it, `push_queue` (a scheduled dose may be a
voice dose, rendered by the drain at fire time, 2026-07-24) and `reply_common`
(answering him aloud, 2026-08-28). Nothing about paragraph-splitting and frame
concatenation is knock-shaped; it was only ever in that file because the knock
needed it first.

WHY ITS OWN FILE, and not one of the homes already standing:

  `lanes.py` is what a FAMILY shares, and its header says the three families are
  not one shape. These three callers span two of them — decide/judge and pure
  delivery — so this is not a family's, it is everyone-who-speaks'.

  `publish.py` is the delivery tail and would have had to grow the Google TTS
  stack to hold this. It also sat at 148/150 code lines; a file at its ceiling
  takes a split, not a passenger.

  `render_audio.py` owns the TTS primitives this composes (and is imported here,
  downward). Composing them into a MEMO — the paragraph breath, the flat
  concatenation, no cast and no script — is a different job from rendering an
  episode, and putting it there would have made the episode renderer answer to
  three lanes that never render episodes.

Imports `render_audio` and the language pack, nothing else and no lane, so every
lane may import it.
"""
import os
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from language import ANNA_VOICE
from render_audio import (SILENCE_FRAME, clean_memo_for_tts,
                          generate_segment_google, get_raw_mp3_frames)


async def render_memo(memo_script: str, out_path: Path, voice: str = ANNA_VOICE):
    """Speak a memo script to one mp3 — one TTS segment per paragraph, joined by
    a breath. Flat by design: a memo is one voice talking, so there is no cast to
    assign and no script structure to honour, which is the whole difference
    between this and `render_audio`'s episode path."""
    paras = [p.strip() for p in memo_script.split("\n\n") if p.strip()]
    audio = bytearray()
    tmp = tempfile.mkdtemp()
    for i, para in enumerate(paras):
        seg = await generate_segment_google(clean_memo_for_tts(para), voice, i, tmp)
        audio.extend(get_raw_mp3_frames(seg))
        audio.extend(SILENCE_FRAME * 25)  # ~0.6s breath between paragraphs
        os.remove(seg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    print(f"   rendered -> {out_path} ({len(audio)/1024:.0f} KB)")
