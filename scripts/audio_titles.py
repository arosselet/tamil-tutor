#!/usr/bin/env python3
"""The audio lanes' public names — what a soak, drill or rotation is CALLED.

WHY A FILE AND NOT A DERIVATION. A mission's name is its script's first line
(2026-08-20) and a knock's is its move out of `knock_log.json`; both lanes leave
a written artifact the feed can read back. The audio lanes leave only an mp3 —
`render_soak` writes no script and no caption — so the one moment the name
exists is the moment the sheet is written, and if nobody records it there it is
gone. This is the same stem-keyed join `knock_meta` already makes, against the
one book the audio lanes had no equivalent of.

WHY NOT `episodes.json`: that is the LESSON pipeline's registry, and the picker
was deliberately moved OFF it on 2026-08-27 because only numbered Missions get a
row there. Filing soaks in it would re-open that decision from the other end.

ONE WRITER — `lanes.deliver_rendered`, the tail all three audio lanes already
pass through — and one reader, `rebuild_rss`. Written where the derived-file law
(2026-08-24) puts it: beside the dose it names, in the dose's own commit.
"""
import json
import os
import re

from state_io import AUDIO_TITLES_PATH

# A feed row is read one-handed on a lock screen. Long enough for "கேட்கு vs
# சொல்லு — the pull/push pair", short enough that the player does not ellipsis
# it away. The mandates ask for 3-5 words; this is the backstop, not the target.
TITLE_CAP = 60


def clean(title: str) -> str:
    """One line, trimmed, capped. A model that returns a paragraph gets a title,
    not a broken feed — and never an empty string dressed as a name."""
    one = " ".join((title or "").split())
    return one[:TITLE_CAP].rstrip(" -—·,") if one else ""


def load() -> dict:
    """stem -> title. A missing or unreadable file is an empty map, never a
    raise: a feed rebuild must not die because a sidecar is new or malformed —
    the lanes fall back to their dated titles and the feed still builds."""
    try:
        with open(AUDIO_TITLES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str) and v.strip()}
    except Exception:
        return {}


def record(stem: str, title: str) -> bool:
    """Name one dose. MERGE-WRITE, per the 2026-08-23 law: read, overlay one key,
    leave every other name alone — a rebuild-from-scratch here would drop every
    dose the running copy had not heard of. Returns whether anything changed, so
    the caller only commits a file it actually wrote."""
    title = clean(title)
    if not stem or not title:
        return False
    names = load()
    if names.get(stem) == title:
        return False
    names[stem] = title
    AUDIO_TITLES_PATH.write_text(
        json.dumps(dict(sorted(names.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return True


# The word a named dose leads with, and the prefixes that earn one. `longhaul`
# and `rotation` are ONE lane under two prefixes (renamed 2026-08-31) and both
# read "Rotation": three tapes are live in the feed under the old name, and a
# published entry is a promise to a player that already downloaded it.
LANE_WORD = {"drill": "Drill", "soak": "Soak",
             "rotation": "Rotation", "longhaul": "Rotation"}
LANE_RE = re.compile(r"(drill|soak|rotation|longhaul)_")
# The date, and the time only when the date does not separate them either — both
# 08-30 soaks carry 2026-08-30, so a date alone would have left Andrew where he
# started. Read off the FILENAME: the stem is what the picker resolves on, it is
# stable for the life of the item, and it cannot drift the way a re-derived date
# once did.
STAMP_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})(?:_(\d{2})(\d{2}))?")


def lane_title(filename: str) -> str:
    """"soak_2026-08-30_2004.mp3" -> "Soak — கேட்கு vs சொல்லு · pull and push",
    or "" when this dose has no recorded name and the feed should fall back.

    THE RECORDED NAME WINS (2026-09-01, Andrew: *"the title, nothing to do but
    listen, is being carried by every single soak … there are two of them and I
    can't tell which is which"*). The dated fallbacks in `rebuild_rss` say what a
    dose IS — the CONTRACT, "nothing to do but listen" — which is identical for
    every member of a lane by construction, so a lane could only ever be as
    distinguishable as its dates. This says what it is ABOUT."""
    m = LANE_RE.match(os.path.basename(filename))
    named = load().get(os.path.basename(filename).removesuffix(".mp3"), "")
    return f"{LANE_WORD[m.group(1)]} — {named}" if m and named else ""


def disambiguator(filename: str) -> str:
    """What to add to a name two doses share. Empty when the filename carries no
    date — an absence that leaves the collision visible rather than papering it
    over with a counter nobody can interpret."""
    m = STAMP_RE.search(os.path.basename(filename))
    if not m:
        return ""
    return f"{m.group(1)} {m.group(2)}:{m.group(3)}" if m.group(2) else m.group(1)


def distinct(titles: dict) -> dict:
    """Guarantee what Andrew actually asked for: *"in the feed and in the rating,
    they are distinct and ideally recognizable"* (2026-09-01).

    Recognisable is the writer's job and it can fail — two soaks a fortnight
    apart can honestly earn the same 4-word name, and before this the whole lane
    shared ONE name, which is how two 08-30 soaks became unrateable. So
    distinctness is not left to the model: any title claimed by more than one
    stem gets its own timestamp appended, and only those do.

    THAT IS WHY THE DATE IS CONDITIONAL, not dropped (Andrew: *"the date in the
    title is optional"*). Optional means earned — it appears exactly where a name
    is not enough on its own, and a unique name never pays for it.

    Keyed on the filename, so an item that shares a name gets a mark and an item
    that does not is left exactly as the writer named it."""
    seen = {}
    for stem, title in titles.items():
        seen.setdefault(title, []).append(stem)
    out = dict(titles)
    for title, stems in seen.items():
        if len(stems) < 2:
            continue
        for stem in stems:
            mark = disambiguator(stem)
            if mark:
                out[stem] = f"{title} · {mark}"
    return out
