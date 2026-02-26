#!/usr/bin/env python3
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
      <itunes:summary>{summary}</itunes:summary>
      <enclosure url="{audio_url}" length="{size}" type="audio/mpeg"/>
      <guid>{audio_url}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:duration>{duration}</itunes:duration>
    </item>
"""


def clean_title(raw_title: str, filename: str) -> str:
    """
    Convert a raw script title into a clean, consistent episode title.
    
    Input:  "Tier 2 Mission 10: The Big Review (The Remix)"
    Output: "Ep 10 — The Big Review"
    """
    # Try to extract tier, mission, and subtitle from the raw title
    match = re.match(
        r"Tier\s+(\d+)\s+Mission\s+(\d+):\s*(.+)", raw_title, re.IGNORECASE
    )
    if match:
        mission = match.group(2)
        subtitle = match.group(3).strip()
        # Strip parenthetical style labels like "(The Remix)", "(Cultural Deep-Dive)"
        subtitle = re.sub(r"\s*\(.*?\)\s*$", "", subtitle).strip()
        return f"Ep {mission} — {subtitle}"

    # Fallback: use filename without extension
    return filename.replace(".mp3", "").replace("_", " ").title()


def get_title_from_md(md_path):
    if not os.path.exists(md_path):
        return None
    with open(md_path, 'r') as f:
        first_line = f.readline().strip()
        if first_line.startswith('#'):
            return first_line.lstrip('#').strip()
    return os.path.basename(md_path)


def generate_rss():
    items = []
    if not os.path.exists(AUDIO_DIR):
        print(f"❌ {AUDIO_DIR} not found!")
        return

    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]

    # Filter: only tier-based episodes (skip legacy level4_*, demos, tests)
    episodes = [f for f in audio_files if f.startswith('tier')]

    # Sort by mission number descending (newest first)
    def sort_key(filename):
        match = re.search(r"tier(\d+)_mission(\d+)", filename)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (0, 0)

    episodes.sort(key=sort_key, reverse=True)

    for filename in episodes:
        audio_path = os.path.join(AUDIO_DIR, filename)
        # Try to find matching script
        script_name = filename.replace('.mp3', '.md')
        script_path = os.path.join(SCRIPTS_DIR, script_name)

        raw_title = get_title_from_md(script_path) or filename
        title = clean_title(raw_title, filename)
        size = os.path.getsize(audio_path)
        mtime = os.path.getmtime(audio_path)
        pub_date = email.utils.formatdate(mtime, localtime=True)
        audio_url = f"{BASE_URL}/{AUDIO_DIR}/{filename}"

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
            audio_url=demo_url,
            size=demo_size,
            pub_date=email.utils.formatdate(os.path.getmtime(demo_path), localtime=True),
            duration=demo_duration
        ))

    rss_content = RSS_TEMPLATE.format(
        base_url=BASE_URL,
        site_url=SITE_URL,
        author=AUTHOR,
        items="".join(items)
    )

    with open(RSS_FILE, 'w') as f:
        f.write(rss_content)
    print(f"✅ Generated {RSS_FILE} with {len(items)} episodes.")


if __name__ == "__main__":
    generate_rss()
