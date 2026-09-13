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
    """stem -> {"title": str, "words": [str]}. A missing or unreadable file is an
    empty map, never a raise: a feed rebuild must not die because a sidecar is
    new or malformed — the lanes fall back to their dated titles and the feed
    still builds.

    THE VALUE GREW A WORDS LIST (2026-09-13) so the audio lanes can TEACH. The
    teach gate stopped trusting render stamps (s105), so a Teach Beat opens only
    when a tap proves he heard it — and the tap could only resolve words for
    numbered missions, because `episodes.json` is the one place an artifact's
    words were written down. Rotation, soak, drill and payoff had none, which
    left the lane about to become the standing carrier unable to open a single
    word. `delivered` — the audible set — is already computed at the one shared
    seam; it just was not kept.

    Legacy rows are bare strings and are read as a title with no words: the file
    predates this and a migration pass would be a second writer for a shape the
    reader can absorb in one line."""
    try:
        with open(AUDIO_TITLES_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    out = {}
    for k, v in data.items():
        row = {"title": v, "words": []} if isinstance(v, str) else dict(v or {})
        if isinstance(row.get("title"), str) and row["title"].strip():
            out[k] = {"title": row["title"], "words": list(row.get("words") or [])}
    return out


def record(stem: str, title: str, words=()) -> bool:
    """Name one dose, and record which words it actually AIRED. MERGE-WRITE, per
    the 2026-08-23 law: read, overlay one key, leave every other row alone — a
    rebuild-from-scratch here would drop every dose the running copy had not
    heard of. Returns whether anything changed, so the caller only commits a file
    it actually wrote.

    `words` is the lane's `delivered` — what is AUDIBLE in the finished artifact,
    never what was planned. The distinction is the claim_payload rule (2026-07-17)
    and it matters more now than it did: these words are what a tap opens."""
    title = clean(title)
    if not stem or not title:
        return False
    names = load()
    row = {"title": title, "words": [w for w in words if w]}
    if names.get(stem) == row:
        return False
    names[stem] = row
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
    row = load().get(os.path.basename(filename).removesuffix(".mp3")) or {}
    named = row.get("title", "")
    return f"{LANE_WORD[m.group(1)]} — {named}" if m and named else ""


def words_for(stem: str) -> list:
    """What this artifact aired — the set a tap on it may open. Empty for a dose
    recorded before the words list existed, which opens nothing: silently
    guessing at an old tape's contents is how a teach gate gets re-mined."""
    return (load().get(stem) or {}).get("words", [])


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


def dose_minutes(days: int = 7, today=None) -> dict:
    """MINUTES ATTENDED over a trailing window — the honest denominator.

    Counts what he PLAYED, never what was commissioned. A meter that counts
    renders is one the system can satisfy by writing more files, which is the
    "honest meters or none" rule failing in its most literal form.

    Each play row froze its own `minutes` at tap time, so this is a sum and not
    a join. A row without `minutes` predates the meter and counts as a play with
    zero time rather than being dropped — under-reporting contact is the safe
    direction, and a dropped row would silently flatter the average.

    `plays` is the re-listen count per artifact, which is also the quality
    meter: under the standing-tape cadence a tape played four times was good and
    a tape played once was not. It costs no extra tap.
    """
    from datetime import timedelta
    from state_io import FEEDBACK_LOG_PATH, load_json, local_today
    start = ((today or local_today()) - timedelta(days=days - 1)).isoformat()
    plays: dict[str, int] = {}
    total = 0.0
    for row in load_json(FEEDBACK_LOG_PATH) or []:
        if "[audio rating]" not in row.get("note", "") or row.get("date", "") < start:
            continue
        total += float(row.get("minutes") or 0.0)
        key = row.get("id") or "(before the meter)"
        plays[key] = plays.get(key, 0) + 1
    taps = sum(plays.values())
    return {"minutes": total, "per_day": total / days, "days": days,
            "plays": plays, "taps": taps,
            # AN ABSENCE MUST BE LOUD. Taps with no minutes behind them is the
            # one failure that reads as its own opposite: the meter says 0.0/day
            # and a reader concludes he stopped listening, when in fact he
            # pressed play and the duration never reached the row. Named here so
            # both surfaces can say which of the two it is.
            "unmeasured": bool(taps) and not total}
