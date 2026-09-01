#!/usr/bin/env python3
import json
import os
import re
import subprocess
from datetime import datetime
import email.utils
from xml.sax.saxutils import escape as xml_escape

from language import RAW_BASE_URL, SITE_URL
# LOCAL_TZ is Andrew's clock, canonical there; RECENT_AUDIO_PATH is the rating
# picker's list, which this module writes because this module writes its source.
from state_io import LOCAL_TZ, RECENT_AUDIO_PATH

# Configuration
# Derived from language.REPO, with SITE_URL (2026-08-28). One repo identity had
# three spellings — this file wrote two of them out in full — and a fork updated
# whichever it happened to find.
BASE_URL = RAW_BASE_URL
AUDIO_DIR = "published_audio"
SCRIPTS_DIR = "content/scripts"
# Below this, a .mp3 is a stub, a truncated write, or an lfs pointer — not audio.
# The shortest real dose in the library is a knock memo at ~100 KB.
MIN_PLAYABLE_BYTES = 2048
CAPTIONS_DIR = "content/captions"  # follow-along sheets; GitHub blob URL renders the md
RSS_FILE = "rss.xml"
AUTHOR = "Andrew &amp; Claude"   # 2026-07-27, Andrew's call. Every lane writes on
                                # morning_knock.MODEL since 2026-08-18 (agy retired), so
                                # the single line is now literally true end to end.
                                # Per-item attribution is possible — rebuild_rss already
                                # knows each item's lane — if the single line ever stops
                                # being the credit Andrew wants.

RSS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
    xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Coimbatore Mappillai</title>
    <link>{site_url}</link>
    <language>en-us</language>
    <itunes:author>{author}</itunes:author>
    <itunes:summary>AI-generated Tamil lessons. Colloquial Kongu dialect, dual-voice audio, built for daily life.</itunes:summary>
    <description>AI-generated Tamil lessons. Colloquial Kongu dialect, dual-voice audio, built for daily life.</description>
    <itunes:owner>
      <itunes:name>{author}</itunes:name>
    </itunes:owner>
    <itunes:explicit>no</itunes:explicit>
    <itunes:category text="Education">
      <itunes:category text="Language Courses"/>
    </itunes:category>
    <itunes:image href="{base_url}/logo.jpg"/>
    <itunes:type>episodic</itunes:type>
    <itunes:new-feed-url>{base_url}/rss.xml</itunes:new-feed-url>
    {items}
  </channel>
</rss>
"""

ITEM_TEMPLATE = """
    <item>
      <title>{title}</title>
      <itunes:author>{author}</itunes:author>
      <itunes:summary>{summary}</itunes:summary>{caption_block}
      <enclosure url="{audio_url}" length="{size}" type="audio/mpeg"/>
      <guid>{audio_url}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:duration>{duration}</itunes:duration>
    </item>
"""

# Show-notes block for episodes that ship a follow-along caption sheet
# (captioned soak, 2026-07-13). <link> + an anchor in <description> — podcast
# apps render one or the other; either way the sheet is one tap from the player.
CAPTION_BLOCK = """
      <link>{caption_url}</link>
      <description><![CDATA[\U0001F4D6 <a href="{caption_url}">Captions — follow along (Tamil · phonetic · English)</a>]]></description>"""


def caption_block_for(script_md_name: str) -> str:
    """Non-empty show-notes block iff a caption sheet exists for this episode's
    script name (e.g. "tier2_mission58.md")."""
    if not os.path.exists(os.path.join(CAPTIONS_DIR, script_md_name)):
        return ""
    return CAPTION_BLOCK.format(
        caption_url=f"{SITE_URL}/blob/main/{CAPTIONS_DIR}/{script_md_name}")


def clean_title(raw_title: str, filename: str) -> str:
    """
    Convert a raw script title into a clean, consistent episode title.
    Detects intercept/breakdown suffix in filename and appends episode type label.
    
    Input:  "Tier 2 Mission 15: The Overheard Argument", "tier2_mission15_intercept.mp3"
    Output: "Ep 15 — The Overheard Argument · Intercept"
    """
    # Drill tracks (spoken production volleys) carry their date, not a mission number
    drill = re.match(r"drill_(\d{4}-\d{2}-\d{2})", filename)
    if drill:
        return f"Drill — {drill.group(1)} · say it out loud"

    # Soak loops (passive repetition) — the title says the contract out loud, so
    # a tired ear scrolling the feed can tell it from a drill at a glance.
    soak = re.match(r"soak_(\d{4}-\d{2}-\d{2})", filename)
    if soak:
        return f"Soak — {soak.group(1)} · nothing to do but listen"

    # Rotation tapes carry their spine as well as their date: three of them ride
    # the feed at once for the flight, and "which one is the machines tape" has to
    # be answerable from the lock screen, one-handed, without reading show notes.
    #
    # NO MINUTE FIGURE (2026-08-10). This said "press once, 45 min" for every tape
    # regardless of length, and the first one shipped titled 45 min against a
    # MEASURED 00:23:45 — a title is not exempt from "durations are measured, never
    # estimated" (2026-07-23) just because it is prose. The figure is dropped rather
    # than corrected: `<itunes:duration>` already carries the measured length and is
    # what his player displays, so a second copy in the title is a maintenance
    # burden that can only ever drift. Andrew's own ruling on the same problem in
    # the Institution-of-One close — drop the figure and the line stays true across
    # any future cut. What the title must promise is the CONTRACT, not the length:
    # press once and nothing is asked of you.
    # BOTH PREFIXES, DELIBERATELY (2026-08-31). The lane renamed longhaul ->
    # rotation; three tapes were already published under the old prefix and are
    # live in rss.xml. A feed entry is a promise to a player that has already
    # downloaded it, so the old prefix stays READABLE forever while only new
    # tapes are written as rotation_. Renaming the files instead would have
    # orphaned three entries to save one regex branch.
    rotation = re.match(r"(?:rotation|longhaul)_([a-z]+)_(\d{4}-\d{2}-\d{2})", filename)
    if rotation:
        return (f"Rotation — {rotation.group(1)} · {rotation.group(2)} "
                f"· press once, nothing asked")

    # Detect episode type from filename
    ep_type = None
    if re.search(r"_intercept", filename, re.IGNORECASE):
        ep_type = "Intercept"
    elif re.search(r"_breakdown", filename, re.IGNORECASE):
        ep_type = "Breakdown"

    # Try to extract tier, mission, and subtitle from the raw title
    match = re.match(
        r"Tier\s+(\d+),?\s+Mission\s+(\d+)\s*[:—-]\s*(.+)", raw_title, re.IGNORECASE
    )
    if match:
        mission = match.group(2)
        subtitle = match.group(3).strip()
        # Strip parenthetical style labels like "(The Remix)", "(Cultural Deep-Dive)"
        subtitle = re.sub(r"\s*\(.*?\)\s*$", "", subtitle).strip()
        base = f"Ep {mission} — {subtitle}"
        return f"{base} · {ep_type}" if ep_type else base

    # Special reference episodes: use the script's H1 title if it's meaningful
    if filename.startswith("special_") and raw_title and raw_title != filename:
        return raw_title

    # Fallback: use filename without extension
    return filename.replace(".mp3", "").replace("_", " ").title()


# Every mp3 Anna pushes lands in `published_audio/knocks/`, whatever sent it
# (Andrew, 2026-07-24: "all audio you push me should go in the feed" — a
# dismissed notification must stay replayable, and the lock screen is
# ephemeral). Three producers write there, each with its own prefix:
#   knock_<ts>              — morning_knock.py, the ambient dose
#   queued_q<id>_<ts>       — push_queue.py, a scheduled dose rendered at fire time
#   reply_<ts>              — knock_reply.py, Anna answering a lock-screen reply aloud
# Only `knock_` existed when this file was written, so the other two titled as
# their raw filename and sorted to the very bottom of the feed.
KNOCK_AUDIO_RE = re.compile(
    r"^(knock|queued|reply)_(?:q\d+_)?(\d{4})-(\d{2})-(\d{2})(?:T(\d{2})-(\d{2}))?")

KNOCK_KIND = {"knock": "Knock", "queued": "Scheduled", "reply": "Reply"}


def knock_meta():
    """Map an mp3 STEM ("knock_2026-08-27T02-46") -> (move, modality) from the
    knock log: what the memo was, and which kind of dose Anna sent.

    Reads `mp3` OR `audio_url`: the knock lane records a repo-relative path, while
    the drain and the reply judge record only the CDN url they pushed. Both end in
    the same basename, which is all this mapping needs.

    KEYED ON THE STEM, not the "knocks/….mp3" path it used to carry, because its
    second reader is now `feed_items`, which has already split that stem out of
    the enclosure url. One key, two readers, no second basename split.

    The MODALITY is why this returns a pair rather than a label. It is the only
    record of whether a knock was a scripted dose or a one-line prompt, and the
    feed itself cannot say: an eavesdrop memo runs 16-40s and a fielding prompt
    2-16s, so the two OVERLAP and no duration threshold could separate them
    honestly (measured across the 26 published knocks, 2026-08-29)."""
    try:
        with open("progress/knock_log.json", encoding="utf-8") as f:
            entries = json.load(f)
    except Exception:
        return {}
    meta = {}
    for e in entries:
        ref = e.get("mp3") or e.get("audio_url") or e.get("reply_audio_url") or ""
        if ".mp3" not in ref:
            continue
        stem = os.path.basename(ref).removesuffix(".mp3")
        meta[stem] = (e.get("move") or "", e.get("modality") or "")
    return meta


def knock_title(filename: str, meta: dict) -> str:
    """"knocks/knock_2026-07-05T22-58.mp3" -> "Knock — 2026-07-05 22:58 · <move>".
    Scheduled doses and spoken replies get their own word, same shape."""
    base = os.path.basename(filename)
    m = KNOCK_AUDIO_RE.match(base)
    when = base.replace(".mp3", "")
    kind = "Knock"
    if m:
        kind = KNOCK_KIND.get(m.group(1), "Knock")
        when = f"{m.group(2)}-{m.group(3)}-{m.group(4)}"
        if m.group(5):
            when += f" {m.group(5)}:{m.group(6)}"
    move = meta.get(base.removesuffix(".mp3"), ("", ""))[0]
    return f"{kind} — {when} · {move}" if move else f"{kind} — {when}"


def get_title_from_md(md_path):
    if not os.path.exists(md_path):
        return None
    with open(md_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line.startswith('#'):
            return first_line.lstrip('#').strip()
    return os.path.basename(md_path)


def audio_format(stem: str) -> str:
    """Which production lane made this feed item. The rating ledger carries it so
    the Diagnosis pass can compare formats — "do drills land better than soaks" is
    the question the audio lane exists to answer, and a rating that only says 5/5
    cannot answer it."""
    # rotation_ and longhaul_ are ONE lane under two prefixes (renamed
    # 2026-08-31); the ledger must aggregate them or the format comparison
    # splits one lane's ratings across two names and answers nothing.
    for prefix, name in (("soak_", "soak"), ("drill_", "drill"),
                         ("longhaul_", "rotation"), ("rotation_", "rotation"),
                         ("special_", "special")):
        if stem.startswith(prefix):
            return name
    return "mission" if stem.startswith("tier") else "episode"


# Which knock doses the rating picker will NOT offer. A DENYLIST, not an
# allowlist, on purpose: an allowlist's failure mode is a new modality silently
# missing from the picker, which is precisely the bug this replaces, one modality
# later. The 08-27 law said "a one-line dose is not something you sit down and
# rate" and then keyed itself on the DELIVERY CHANNEL, which swept the whole knock
# lane with it. `fielding` is the modality that actually is one line -- a single
# Tamil sentence asking for an answer, 2-16s across the 10 published, against
# eavesdrop's 16-40s and audio's 25-102s. Spoken REPLIES are excluded by stem
# instead: a reply is Andrew's own half of an exchange, not a dose Anna sent him.
UNRATEABLE_FORMATS = {"knock/fielding"}


def feed_items():
    """Everything in the feed, newest first — `[{id, title, format}]`.

    THE FEED IS THE SOURCE for "what audio reached Andrew", not episodes.json and
    not a directory glob. The registry is the *lesson* pipeline's book: only
    numbered Missions get a row, so 16 of 28 published files had none, and a
    picker built on it could not name the soak he had listened to an hour earlier
    (2026-08-27, his catch). Reading rss.xml means the picker and his podcast app
    agree by construction — and if the feed is stale, both are stale together,
    which is correct rather than a bug.

    Sorted by pubDate, deliberately NOT by this module's own `sort_key`: that one
    pins specials at the top forever, which is the same complaint in a new hat.
    Knock doses are offered as `knock/<modality>` (Andrew, 2026-08-29: he sat down
    with the 08-27 eavesdrop and wanted to rate it). The 08-27 exclusion was right
    about one-line doses and wrong about where to key it — see
    `UNRATEABLE_FORMATS`. The label carries the modality because comparing an
    eavesdrop against a soak is the pedagogy question this ledger exists to
    answer, and `[knock]` alone could not.

    Lives here rather than in `state_io` because this module owns the feed, and
    because L0 was 25 lines over its budget the moment it tried to."""
    import xml.etree.ElementTree as ET
    if not os.path.exists(RSS_FILE):
        return []
    try:
        root = ET.parse(RSS_FILE).getroot()
    except ET.ParseError:
        print("  ⚠ rss.xml did not parse — no feed items to offer")
        return []
    meta = knock_meta()
    out = []
    for item in root.findall("./channel/item"):
        enc = item.find("enclosure")
        url = (enc.get("url") if enc is not None else "") or ""
        stem = url.rsplit("/", 1)[-1].removesuffix(".mp3")
        fmt = audio_format(stem)
        if "/knocks/" in url:
            # An unlogged knock resolves to `knock/dose` and IS OFFERED, not
            # dropped. That direction is deliberate: a stray row in the picker is
            # visible and one tap to ignore, while a dose that silently never
            # appears is the failure this whole change exists to end.
            fmt = "knock/" + (meta.get(stem, ("", ""))[1] or "dose")
            if stem.startswith("reply_") or fmt in UNRATEABLE_FORMATS:
                continue
        title = (item.findtext("title") or "").strip()
        if not stem or not title:
            continue
        try:
            when = email.utils.parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        out.append({"id": stem, "title": title, "format": fmt, "at": when})
    out.sort(key=lambda d: d["at"], reverse=True)
    for d in out:
        d.pop("at")
    return out


# Six rows, the 08-27 number, moved here with the writer rather than re-derived:
# a picker is a thing you scroll on a lock screen, and the row he wants is at the
# top by construction.
def write_recent_audio(n: int = 6):
    """Publish the rating picker's list — the last n feed titles, newest first.

    A DERIVED FILE FOLLOWS ITS SOURCE (2026-08-24), and this one did not. It was
    written by `sync_state.write_thin_learner`, which runs on the SESSION clock,
    while its only source — `rss.xml` — is written here, on the PUBLISH clock.
    Andrew listened to the 09-01 soak minutes after it landed and it was not on
    the picker: the feed had it, and the file had not been rewritten since the
    previous evening's session — 24 hours behind its own source, with nothing
    broken enough to notice. Two clocks over one derivation is not a
    race that sometimes loses — it loses by default for every dose published
    between two state writes, which is most of them.

    So the derivation moves to the source's owner. Called at the end of
    `generate_rss`, it cannot run at a different time from the feed because it
    runs in the same function: whoever rebuilds the feed republishes the picker,
    including the bare `rebuild_rss.py` recovery run `/debug` prescribes.

    Flat strings, because the iOS picker reads this straight into a list and
    Shortcuts cannot render dictionaries as pickable rows. Titles are the feed's
    own, so a row reads exactly as it does in his podcast app — which is also how
    `cmd_rate_episode` resolves the tap back to an item.

    PLAIN TEXT, not JSON: raw.githubusercontent.com serves every raw file as
    text/plain with nosniff, so Shortcuts never parses one — a .json arrived as a
    single opaque blob and the picker drew one unpickable row (2026-08-27)."""
    RECENT_AUDIO_PATH.write_text(
        "\n".join(d["title"] for d in feed_items()[:n]) + "\n",
        encoding="utf-8", newline="\n")


def existing_items():
    """Return {guid_url: {"pubDate": …, "duration": …}} from the current rss.xml, so a
    rebuild republishes what was published rather than re-deriving it.

    MEASURE ONCE, THEN FREEZE. Both fields describe an mp3 that never changes after
    publication (a fix re-renders to `_vN` under a new filename, so it gets a new guid
    and a fresh measurement — in-place edits are not a thing here). Re-deriving them on
    every rebuild bought nothing and cost twice:

    - pubDate fell through to the file's mtime, which on a fresh clone is the CHECKOUT
      time, collapsing the whole feed to a single "now".
    - duration fell through to whatever measuring tool the rebuilding host happened to
      have. The laptop has ffprobe and the CI container does not, so every cloud rebuild
      silently reverted the library to the frame-scan estimate — M72 announced as 13:12
      for a 10:02 episode, for two days, undoing the 2026-07-23 ffprobe fix (2026-07-25).

    Preservation must NOT depend on the feed being well-formed XML. A single unescaped
    character in one episode title once wiped every saved date: the strict parse threw,
    this returned {}, and everything fell through to the mtime fallback. So we parse
    strictly when we can, and fall back to a tolerant text scan that survives malformed
    markup.
    """
    if not os.path.exists(RSS_FILE):
        return {}
    with open(RSS_FILE, encoding="utf-8") as f:
        raw = f.read()

    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(raw)
        result = {}
        for item in root.iter("item"):
            guid = item.findtext("guid")
            pub_date = item.findtext("pubDate")
            if guid and pub_date:
                dur = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
                result[guid.strip()] = {"pubDate": pub_date.strip(),
                                        "duration": (dur or "").strip()}
        if result:
            return result
    except ET.ParseError as e:
        print(f"⚠️  rss.xml is not well-formed ({e}); recovering published values via text scan.")

    # Tolerant fallback: pull the fields out of each <item> block by text, so one bad
    # character can never again reset every episode.
    result = {}
    for block in re.findall(r"<item>(.*?)</item>", raw, re.S):
        g = re.search(r"<guid>(.*?)</guid>", block, re.S)
        p = re.search(r"<pubDate>(.*?)</pubDate>", block, re.S)
        d = re.search(r"<itunes:duration>(.*?)</itunes:duration>", block, re.S)
        if g and p:
            result[g.group(1).strip()] = {"pubDate": p.group(1).strip(),
                                          "duration": d.group(1).strip() if d else ""}
    return result


# MPEG audio frame tables, Layer III only (everything here is TTS mp3).
_BITRATES = {  # kb/s, indexed by the header's 4-bit bitrate index
    1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],  # MPEG 1
    2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],      # MPEG 2 / 2.5
}
_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def mp3_duration(path):
    """Exact seconds, by summing every frame header. None if the file won't parse.

    Why not mutagen: these files are raw frame concatenations (TTS segments plus
    SILENCE_FRAME copies for pauses), so they carry no Xing/VBR header. Without one,
    mutagen falls back to filesize x 8 / first-frame-bitrate — it assumes the first
    frame's rate holds for the whole file. Google's frames average higher than that
    32 kb/s opener, so every episode came out 3-5% long (a 4:50 piece announced as
    5:04). Each frame header states its own bitrate, so adding up frame durations is
    exact and needs no decoding.
    """
    with open(path, "rb") as f:
        data = f.read()

    i = 0
    if data[:3] == b"ID3":  # skip the tag: its size is 4 syncsafe bytes at offset 6
        i = 10 + int.from_bytes(bytes(b & 0x7F for b in data[6:10]), "big")
        if data[5] & 0x10:  # footer present
            i += 10

    seconds = 0.0
    end = len(data)
    while i + 4 <= end:
        if data[i] != 0xFF or (data[i + 1] & 0xE0) != 0xE0:
            i += 1  # not a sync word (ID3v1 trailer, junk between segments)
            continue
        h = data[i + 1:i + 4]
        version = (h[0] >> 3) & 0x03           # 3=MPEG1, 2=MPEG2, 0=MPEG2.5
        layer = (h[0] >> 1) & 0x03             # 1 = Layer III
        bitrate_idx = (h[1] >> 4) & 0x0F
        rate_idx = (h[1] >> 2) & 0x03
        if layer != 1 or version == 1 or rate_idx == 3 or bitrate_idx in (0, 15):
            i += 1
            continue
        rate = _RATES[version][rate_idx]
        bitrate = _BITRATES[1 if version == 3 else 2][bitrate_idx] * 1000
        samples = 1152 if version == 3 else 576
        length = (samples // 8) * bitrate // rate + ((h[1] >> 1) & 0x01)
        if length <= 0:
            i += 1
            continue
        seconds += samples / rate
        i += length

    return seconds or None


def ffprobe_duration(path):
    """Seconds by decoding the real stream — the SAME authority episodes.json
    uses (render_audio.register_mission_in_state). None if ffprobe is absent."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip()) or None
    except Exception:
        return None


def audio_duration(path):
    """Seconds for the feed. ffprobe first, frame scan as the pure-python
    fallback.

    The scan alone was wrong in BOTH directions — measured 2026-07-23 against
    ffprobe: M69 +40%, M73 +37%, M72 +32%, M74 -16%, M70/M71 -8%. These files
    are raw frame concatenations (TTS segments plus SILENCE_FRAME copies), and
    a single bad header desyncs the walk: it either skips frames or resyncs a
    byte at a time and recounts. M72 was announced to the feed as 13:12 for a
    10:04 episode — Andrew read the wrong number off his podcast player and
    judged the episode by it. Honest meters or none.
    """
    return ffprobe_duration(path) or mp3_duration(path)


def duration_hms(path, fallback):
    """"HH:MM:SS" for the feed."""
    try:
        total = int(audio_duration(path))
    except Exception:
        return fallback
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def generate_rss():
    published = existing_items()
    items = []
    if not os.path.exists(AUDIO_DIR):
        print(f"❌ {AUDIO_DIR} not found!")
        return

    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]

    # Filter: tier-based episodes + drill tracks + soak loops + special reference
    # episodes (skip legacy level4_*, demos, tests, and standalone intercepts)
    # One tuple, not six chained startswith calls — `str.startswith` takes a
    # tuple, and the chain was already the place a new prefix got forgotten.
    episodes = [f for f in audio_files
                if f.startswith(('tier', 'drill_', 'soak_', 'longhaul_',
                                 'rotation_', 'special_'))
                and not f.endswith('_intercept.mp3')]

    # Knock memos are feed-worthy too (2026-07-05): the push notification is
    # ephemeral; the feed is where a dismissed audio dose can be found again.
    knocks_dir = os.path.join(AUDIO_DIR, "knocks")
    if os.path.isdir(knocks_dir):
        episodes += [f"knocks/{f}" for f in os.listdir(knocks_dir) if f.endswith('.mp3')]

    # The feed carries only things the podcast player can actually PLAY (Andrew,
    # 2026-07-24). Extension alone isn't proof: a render that dies mid-write, or
    # a git-lfs pointer on a fresh clone, leaves a .mp3 that is not audio. An
    # unplayable item is worse than a missing one — it's a dead entry he taps.
    playable, skipped = [], []
    for f in episodes:
        p = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(p) and os.path.getsize(p) >= MIN_PLAYABLE_BYTES:
            playable.append(f)
        else:
            skipped.append(f)
    if skipped:
        print(f"⚠ skipping {len(skipped)} unplayable file(s): {', '.join(skipped[:5])}")
    episodes = playable
    knock_metadata = knock_meta()

    # Sort by mission number descending (newest first); drills sort above by date/time;
    # specials sort at the very top (10, ordinal) so they're visible when published.
    def sort_key(filename):
        match = re.search(r"tier(\d+)_mission(\d+)", filename)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        # drills, soak loops and rotation tapes are all dated tracks — one band,
        # chronological. A prefix missing from this regex still SORTS, at (0, 0),
        # i.e. silently below every episode: the feed carries it and he never
        # scrolls that far. Add the prefix here and to the filter above together.
        match = re.search(r"(?:drill|soak|(?:longhaul|rotation)_[a-z]+)_(\d{4})-(\d{2})-(\d{2})(?:_(\d{4}))?",
                          filename)
        if match:
            return (9, int("".join(g or "0" for g in match.groups())))
        # every pushed dose — knock, scheduled, spoken reply — is one dated band,
        # newest first; matching only `knock_` dumped the other two at (0, 0),
        # i.e. below every episode in the feed
        match = KNOCK_AUDIO_RE.match(os.path.basename(filename))
        if match:
            return (8, int("".join(g or "0" for g in match.groups()[1:])))
        if filename.startswith("special_"):
            return (10, 0)
        return (0, 0)

    # Filename breaks ties so the order is a function of the library, not of the
    # host's os.listdir(). The two special_ files both score (10, 0), so a rebuild
    # on a different machine silently swapped them and produced a feed diff that
    # looked like a real change and wasn't.
    episodes.sort(key=lambda f: (sort_key(f), f), reverse=True)

    for filename in episodes:
        audio_path = os.path.join(AUDIO_DIR, filename)
        # Try to find matching script — strip _intercept/_breakdown suffix so we find the base script
        base_name = re.sub(r"_(intercept|breakdown|v\d+)\.mp3$", ".md", filename, flags=re.IGNORECASE)
        if not base_name.endswith(".md"):
            base_name = filename.replace('.mp3', '.md')
        # Also try specific intercept/breakdown script files
        specific_name = filename.replace('.mp3', '.md')
        specific_path = os.path.join(SCRIPTS_DIR, specific_name)
        base_path = os.path.join(SCRIPTS_DIR, base_name)
        script_path = specific_path if os.path.exists(specific_path) else base_path

        raw_title = get_title_from_md(script_path) or filename
        if filename.startswith("knocks/"):
            title = knock_title(filename, knock_metadata)
        else:
            title = clean_title(raw_title, filename)
        size = os.path.getsize(audio_path)
        audio_url = f"{BASE_URL}/{AUDIO_DIR}/{filename}"
        # Andrew's clock, never the host's. `localtime=True` stamped whatever zone
        # the rebuilding machine happened to be in — the laptop wrote -0400, the
        # CI container +0000 — so the feed carried two offsets for one listener in
        # one timezone. Same instant either way (nothing was ever wrong), but the
        # zone a dose is announced in should be the zone he hears it in.
        # Preserved dates short-circuit first: an already-published item is never
        # restamped, per the immutable-once-published rule.
        prior = published.get(audio_url, {})
        pub_date = prior.get("pubDate") or email.utils.format_datetime(
            datetime.fromtimestamp(os.path.getmtime(audio_path), LOCAL_TZ)
        )
        # Measured once, at first publication, by whatever tool this host has.
        # Never re-derived — see existing_items().
        duration = prior.get("duration") or duration_hms(audio_path, "00:05:00")

        # Escape titles/summaries: episode titles carry Tamil script and arbitrary
        # punctuation (e.g. a raw "&" from a script H1), which is illegal as bare
        # element text and would make the whole feed unparseable if emitted directly.
        items.append(ITEM_TEMPLATE.format(
            title=xml_escape(title),
            author=AUTHOR,
            summary=xml_escape(title),
            caption_block=caption_block_for(base_name),
            audio_url=audio_url,
            size=size,
            pub_date=pub_date,
            duration=duration
        ))

    # Append the welcome/trailer episode as the oldest item
    demo_path = os.path.join(AUDIO_DIR, "polyglot_demo.mp3")
    if os.path.exists(demo_path):
        demo_size = os.path.getsize(demo_path)
        demo_url = f"{BASE_URL}/{AUDIO_DIR}/polyglot_demo.mp3"
        demo_prior = published.get(demo_url, {})
        demo_duration = demo_prior.get("duration") or duration_hms(demo_path, "00:03:30")
        items.append(ITEM_TEMPLATE.format(
            title=xml_escape("Welcome — What Is This?"),
            author=AUTHOR,
            summary=xml_escape("An introduction to the Coimbatore Mappillai project and how it works."),
            caption_block="",
            audio_url=demo_url,
            size=demo_size,
            pub_date=demo_prior.get("pubDate") or email.utils.format_datetime(
                datetime.fromtimestamp(os.path.getmtime(demo_path), LOCAL_TZ)
            ),
            duration=demo_duration
        ))

    rss_content = RSS_TEMPLATE.format(
        base_url=BASE_URL,
        site_url=SITE_URL,
        author=AUTHOR,
        items="".join(items)
    )

    with open(RSS_FILE, 'w', encoding='utf-8') as f:
        f.write(rss_content)
    print(f"✅ Generated {RSS_FILE} with {len(items)} episodes.")
    # The picker list is derived from the feed we just wrote, so it is written
    # here — one function, one clock. See `write_recent_audio`.
    write_recent_audio()


if __name__ == "__main__":
    generate_rss()
