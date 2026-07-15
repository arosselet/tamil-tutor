#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime
import email.utils
from mutagen.mp3 import MP3

# Configuration
BASE_URL = "https://raw.githubusercontent.com/arosselet/tamil-tutor/main"
SITE_URL = "https://github.com/arosselet/tamil-tutor"
AUDIO_DIR = "published_audio"
SCRIPTS_DIR = "content/scripts"
CAPTIONS_DIR = "content/captions"  # follow-along sheets; GitHub blob URL renders the md
RSS_FILE = "rss.xml"
AUTHOR = "Andrew R &amp; Gemini"

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

    # Detect episode type from filename
    ep_type = None
    if re.search(r"_intercept", filename, re.IGNORECASE):
        ep_type = "Intercept"
    elif re.search(r"_breakdown", filename, re.IGNORECASE):
        ep_type = "Breakdown"

    # Try to extract tier, mission, and subtitle from the raw title
    match = re.match(
        r"Tier\s+(\d+)\s+Mission\s+(\d+):\s*(.+)", raw_title, re.IGNORECASE
    )
    if match:
        mission = match.group(2)
        subtitle = match.group(3).strip()
        # Strip parenthetical style labels like "(The Remix)", "(Cultural Deep-Dive)"
        subtitle = re.sub(r"\s*\(.*?\)\s*$", "", subtitle).strip()
        base = f"Ep {mission} — {subtitle}"
        return f"{base} · {ep_type}" if ep_type else base

    # Fallback: use filename without extension
    return filename.replace(".mp3", "").replace("_", " ").title()


def knock_move_labels():
    """Map an mp3 path relative to AUDIO_DIR ("knocks/knock_….mp3") -> Anna's move
    label from the knock log, so feed titles say what the memo was, not just when."""
    try:
        with open("progress/knock_log.json", encoding="utf-8") as f:
            entries = json.load(f)
        return {e["mp3"].split(f"{AUDIO_DIR}/", 1)[-1]: e.get("move") or ""
                for e in entries if e.get("mp3")}
    except Exception:
        return {}


def knock_title(filename: str, moves: dict) -> str:
    """"knocks/knock_2026-07-05T22-58.mp3" -> "Knock — 2026-07-05 22:58 · <move>"."""
    base = os.path.basename(filename)
    m = re.match(r"knock_(\d{4}-\d{2}-\d{2})(?:T(\d{2})-(\d{2}))?", base)
    when = base.replace(".mp3", "")
    if m:
        when = f"{m.group(1)} {m.group(2)}:{m.group(3)}" if m.group(2) else m.group(1)
    move = moves.get(filename, "")
    return f"Knock — {when} · {move}" if move else f"Knock — {when}"


def get_title_from_md(md_path):
    if not os.path.exists(md_path):
        return None
    with open(md_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line.startswith('#'):
            return first_line.lstrip('#').strip()
    return os.path.basename(md_path)


def existing_pub_dates():
    """Return {guid_url: pubDate} from the current rss.xml so rebuilds don't clobber old dates."""
    if not os.path.exists(RSS_FILE):
        return {}
    try:
        import xml.etree.ElementTree as ET
        root = ET.parse(RSS_FILE).getroot()
        result = {}
        for item in root.iter("item"):
            guid = item.findtext("guid")
            pub_date = item.findtext("pubDate")
            if guid and pub_date:
                result[guid] = pub_date
        return result
    except Exception:
        return {}


def generate_rss():
    saved_dates = existing_pub_dates()
    items = []
    if not os.path.exists(AUDIO_DIR):
        print(f"❌ {AUDIO_DIR} not found!")
        return

    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]

    # Filter: tier-based episodes + drill tracks (skip legacy level4_*, demos, tests, and standalone intercepts)
    episodes = [f for f in audio_files
                if (f.startswith('tier') or f.startswith('drill_')) and not f.endswith('_intercept.mp3')]

    # Knock memos are feed-worthy too (2026-07-05): the push notification is
    # ephemeral; the feed is where a dismissed audio dose can be found again.
    knocks_dir = os.path.join(AUDIO_DIR, "knocks")
    if os.path.isdir(knocks_dir):
        episodes += [f"knocks/{f}" for f in os.listdir(knocks_dir) if f.endswith('.mp3')]
    knock_moves = knock_move_labels()

    # Sort by mission number descending (newest first); drills sort above by date/time
    def sort_key(filename):
        match = re.search(r"tier(\d+)_mission(\d+)", filename)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        match = re.search(r"drill_(\d{4})-(\d{2})-(\d{2})(?:_(\d{4}))?", filename)
        if match:
            return (9, int("".join(g or "0" for g in match.groups())))
        match = re.search(r"knock_(\d{4})-(\d{2})-(\d{2})(?:T(\d{2})-(\d{2}))?", filename)
        if match:
            return (8, int("".join(g or "0" for g in match.groups())))
        return (0, 0)

    episodes.sort(key=sort_key, reverse=True)

    for filename in episodes:
        audio_path = os.path.join(AUDIO_DIR, filename)
        # Try to find matching script — strip _intercept/_breakdown suffix so we find the base script
        base_name = re.sub(r"_(intercept|breakdown)\.mp3$", ".md", filename, flags=re.IGNORECASE)
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
        pub_date = saved_dates.get(audio_url) or email.utils.formatdate(
            os.path.getmtime(audio_path), localtime=True
        )

        # Calculate real duration from the MP3 file
        try:
            audio = MP3(audio_path)
            total_seconds = int(audio.info.length)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception:
            duration = "00:05:00"  # Fallback

        items.append(ITEM_TEMPLATE.format(
            title=title,
            author=AUTHOR,
            summary=title,
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
        try:
            demo_audio = MP3(demo_path)
            ds = int(demo_audio.info.length)
            demo_duration = f"{ds // 3600:02d}:{(ds % 3600) // 60:02d}:{ds % 60:02d}"
        except Exception:
            demo_duration = "00:03:30"
        items.append(ITEM_TEMPLATE.format(
            title="Welcome — What Is This?",
            author=AUTHOR,
            summary="An introduction to the Coimbatore Mappillai project and how it works.",
            caption_block="",
            audio_url=demo_url,
            size=demo_size,
            pub_date=saved_dates.get(demo_url) or email.utils.formatdate(
                os.path.getmtime(demo_path), localtime=True
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
