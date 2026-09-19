#!/usr/bin/env python3
"""THE HOUSEHOLD CANON — the reader and the one appender for `content/household.md`.

WHY THIS IS A FILE AND NOT SIX LINES IN `run_studio`. That module was at 459/459
on the day this was written, and Gate 4 reads a file at its ceiling as a
split-or-retire signal rather than a bump. More to the point, the canon has two
consumers with opposite jobs — the Director READS it to place the next scene, and
the render APPENDS a beat to it afterwards — so the concern was never
studio-dispatch-shaped to begin with.

WHAT THE CANON IS FOR. Continuity. Disposable scenes cannot teach shared context
by construction, and shared context is most of what makes a real family table
hard: who Chitra is, why Mama is sulking, what happened last Deepavali. A
recurring household teaches exactly that, and following the fictional family IS
the adopted goal in miniature (`docs/comprehension_plan.md` §5).

THE VOICES ARE PINNED IN THE CANON, AND PYTHON COPIES THEM — the writer never
transcribes them. A voice table retyped by a model every episode is a table that
drifts, and a character whose voice drifts is the one thing ear-training cannot
survive: the ear tracks a SPEAKER before it tracks a word, so Paati sounding like
someone else in month three quietly undoes month two. The model writes the scene;
Python writes the Voice Map.

WHAT THIS FILE DOES NOT OWN: what happens in the household (Anna writes the arc
premise; the Architect writes the scene), which words a scene carries (the
ticket), or whether a canon is any good (Andrew).
"""
import re
from datetime import date

from state_io import BASE, local_today


CANON_PATH = BASE / "content" / "household.md"

# A cast row: `| **Paati** (பாட்டி) | … | `ta-IN-Chirp3-HD-Gacrux` |`
# The name is the first bold span, its TAMIL spelling the parenthesised span
# right after it, and the voice the last backticked span. All anchored to the
# row so a paragraph mentioning a name cannot mint a character.
_ROW_RE = re.compile(
    r"^\|\s*\*\*(?P<name>[^*|]+?)\*\*\s*(?:\((?P<tamil>[^)|]+)\))?.*?"
    r"`(?P<voice>[\w-]+)`\s*\|\s*$", re.MULTILINE)
_BEAT_HEAD = "### Beat log"
_EMPTY = "*(empty)*"


def load() -> str:
    """The canon's text, or "" when there is none."""
    return CANON_PATH.read_text(encoding="utf-8") if CANON_PATH.exists() else ""


def cast(text: str | None = None) -> dict[str, str]:
    """name -> pinned TTS voice, read off the cast table.

    Returns {} when the canon is missing or has no table — and every caller
    treats that as LOUD (see `problem`), never as "no pins needed". A silently
    empty cast is the whole failure this build has to avoid: episodes keep
    rendering, voices get assigned at random per episode, and the feed sounds
    almost right for a month."""
    return {m["name"].strip(): m["voice"] for m in _ROW_RE.finditer(text or load())}


def names(text: str | None = None) -> set[str]:
    """Every string that names a cast member — English and Tamil both.

    THE TAMIL HALF IS LOAD-BEARING. An eavesdrop tape is refused unless its
    opening names who it is about (`morning_knock.tape_names_a_referent`), and
    the tape is Tamil script. Four of the seven are kinship terms the language
    pack already knows (பாட்டி, மாமா, அத்தை); the other three are proper names
    it cannot know and must never be taught — a cast list is a fact about
    Andrew's learner pack, not about Tamil, and `language.py` is the one file a
    fork replaces wholesale. So the knock lane asks HERE instead."""
    out = set()
    for m in _ROW_RE.finditer(text or load()):
        out.add(m["name"].strip())
        if m["tamil"]:
            out.add(m["tamil"].strip())
    return out


def problem(text: str | None = None) -> str:
    """Why the canon cannot be used, in one sentence, or "" when it can.

    /extend Gate 7.2. Each failure below produces a system indistinguishable
    from success: the studio goes on making episodes, they are simply set
    nowhere and remembered by nothing."""
    text = load() if text is None else text
    if not text.strip():
        return f"no canon at {CANON_PATH.relative_to(BASE)} — the studio has nowhere to set a scene"
    if not cast(text):
        return "the canon has no cast table — no character has a pinned voice"
    if _BEAT_HEAD not in text:
        return f"the canon has no `{_BEAT_HEAD}` section — a rendered beat has nowhere to land"
    return ""


def voice_map(script: str, text: str | None = None) -> dict[str, str]:
    """The Voice Map for one script: SPEAKER TAG -> pinned voice.

    Keyed the way `render_audio.parse_script` looks names up — uppercased, and
    matching the whole speaker tag including its `(F)`/`(M)` marker, because
    that is the string the renderer holds. A cast member who does not speak in
    this episode contributes nothing."""
    out = {}
    for tag in set(re.findall(r"^\s*(?:\*\s*)?\*\*\s*([^:]+?)\s*:", script, re.MULTILINE)):
        for name, voice in cast(text).items():
            if re.match(rf"{re.escape(name)}\b", tag, re.IGNORECASE):
                out[tag.upper()] = voice
    return out


def render_voice_map(vmap: dict[str, str]) -> str:
    """The block `render_audio.VOICE_MAP_RE` reads, as an HTML comment so it is
    invisible in the script's own markdown."""
    import json
    return f"<!-- Voice Map: {json.dumps(vmap, ensure_ascii=False)} -->"


def arc_name(text: str | None = None) -> str:
    """This month's arc, as the canon's `## 4. This arc` heading states it, or ""
    when Anna has not cut one yet."""
    body = (text or load()).split("## 4. This arc", 1)
    if len(body) < 2:
        return ""
    head = body[1].split(_BEAT_HEAD, 1)[0]
    m = re.search(r"^\s*\*\*(.+?)\*\*", head, re.MULTILINE)
    return m.group(1).strip() if m else ""


def append_beat(mission: int, beat: str, today: date | None = None) -> bool:
    """Append ONE beat line to the log. Returns False if it could not land.

    THE APPEND IS PYTHON'S, not the writer's. The Producer says what happened in
    its sidecar; this puts it in the canon, so the continuity Andrew perceives
    is a fact about what actually rendered rather than about what a model
    intended. A render that does not grow the beat log is a red run — otherwise
    the household accumulates episodes and remembers none of them, and reads
    exactly like a household that is working."""
    text = load()
    if not text or _BEAT_HEAD not in text or not beat.strip():
        return False
    line = f"- {(today or local_today()).isoformat()} · M{mission} — {beat.strip()}"
    head, tail = text.split(_BEAT_HEAD, 1)
    tail = tail.replace(_EMPTY, line, 1) if _EMPTY in tail else _insert(tail, line)
    CANON_PATH.write_text(head + _BEAT_HEAD + tail, encoding="utf-8", newline="\n")
    return True


def _insert(tail: str, line: str) -> str:
    """Put `line` at the END of the beat log — after the last existing beat,
    before whatever section follows. Appending to the end of the FILE would put
    the log's newest entry under `## 5. Past arcs`, which reads fine and is
    wrong."""
    stop = next((i for i, ln in enumerate(tail.splitlines())
                 if ln.startswith("---") or ln.startswith("## ")), None)
    lines = tail.splitlines()
    at = len(lines) if stop is None else stop
    while at and not lines[at - 1].strip():
        at -= 1
    return "\n".join(lines[:at] + [line] + lines[at:]) + ("\n" if tail.endswith("\n") else "")
