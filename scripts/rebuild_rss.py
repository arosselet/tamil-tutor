#!/usr/bin/env python3
import json
import os
import re
import subprocess
from datetime import datetime
import email.utils
from xml.sax.saxutils import escape as xml_escape

from state_io import LOCAL_TZ  # Andrew's clock, canonical there

# Configuration
BASE_URL = "https://raw.githubusercontent.com/arosselet/tamil-tutor/main"
SITE_URL = "https://github.com/arosselet/tamil-tutor"
AUDIO_DIR = "published_audio"
SCRIPTS_DIR = "content/scripts"
# Below this, a .mp3 is a stub, a truncated write, or an lfs pointer — not audio.
# The shortest real dose in the library is a knock memo at ~100 KB.
MIN_PLAYABLE_BYTES = 2048
CAPTIONS_DIR = "content/captions"  # follow-along sheets; GitHub blob URL renders the md
RSS_FILE = "rss.xml"
AUTHOR = "Andrew &amp; Claude"   # 2026-07-27, Andrew's call. Note: `agy`/Gemini still
                                # writes the episodes (run_studio); Claude writes the
                                # knock/drill/soak/reply lanes (morning_knock.MODEL).
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


def knock_move_labels():
    """Map an mp3 path relative to AUDIO_DIR ("knocks/knock_….mp3") -> Anna's move
    label from the knock log, so feed titles say what the memo was, not just when.

    Reads `mp3` OR `audio_url`: the knock lane records a repo-relative path, while
    the drain and the reply judge record only the CDN url they pushed. Both end in
    the same basename, which is all this mapping needs."""
    try:
        with open("progress/knock_log.json", encoding="utf-8") as f:
            entries = json.load(f)
    except Exception:
        return {}
    labels = {}
    for e in entries:
        ref = e.get("mp3") or e.get("audio_url") or e.get("reply_audio_url") or ""
        if ".mp3" not in ref:
            continue
        labels[f"knocks/{os.path.basename(ref)}"] = e.get("move") or ""
    return labels


def knock_title(filename: str, moves: dict) -> str:
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
    move = moves.get(filename, "")
    return f"{kind} — {when} · {move}" if move else f"{kind} — {when}"


def get_title_from_md(md_path):
    if not os.path.exists(md_path):
        return None
    with open(md_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line.startswith('#'):
            return first_line.lstrip('#').strip()
    return os.path.basename(md_path)


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
    episodes = [f for f in audio_files
                if (f.startswith('tier') or f.startswith('drill_')
                    or f.startswith('soak_') or f.startswith('special_'))
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
    knock_moves = knock_move_labels()

    # Sort by mission number descending (newest first); drills sort above by date/time;
    # specials sort at the very top (10, ordinal) so they're visible when published.
    def sort_key(filename):
        match = re.search(r"tier(\d+)_mission(\d+)", filename)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        # drills and soak loops are both dated tracks — one band, chronological
        match = re.search(r"(?:drill|soak)_(\d{4})-(\d{2})-(\d{2})(?:_(\d{4}))?", filename)
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
            title = knock_title(filename, knock_moves)
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


if __name__ == "__main__":
    generate_rss()
