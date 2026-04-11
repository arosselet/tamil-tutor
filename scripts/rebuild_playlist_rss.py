#!/usr/bin/env python3
"""
Rebuild the playlist RSS feed from published_playlists/.

Mirrors rebuild_rss.py but for the separate playlist podcast feed.
Each playlist is one "episode" — a concatenation of under-listened missions.

Usage:
    python scripts/rebuild_playlist_rss.py
"""

import os
import re
import email.utils
from mutagen.mp3 import MP3

BASE_URL = "https://raw.githubusercontent.com/arosselet/tamil-tutor/main"
SITE_URL = "https://github.com/arosselet/tamil-tutor"
AUDIO_DIR = "published_playlists"
RSS_FILE = "playlist_rss.xml"
AUTHOR = "Andrew R &amp; Gemini"

RSS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
    xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Coimbatore Mappillai — Playlists</title>
    <link>{site_url}</link>
    <language>en-us</language>
    <itunes:author>{author}</itunes:author>
    <itunes:summary>Daily re-listen playlists for Tamil immersion. Spaced repetition at the episode level.</itunes:summary>
    <description>Daily re-listen playlists for Tamil immersion. Spaced repetition at the episode level.</description>
    <itunes:owner>
      <itunes:name>{author}</itunes:name>
    </itunes:owner>
    <itunes:explicit>no</itunes:explicit>
    <itunes:category text="Education">
      <itunes:category text="Language Courses"/>
    </itunes:category>
    <itunes:image href="{base_url}/logo.jpg"/>
    <itunes:type>episodic</itunes:type>
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
      <guid>{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:duration>{duration}</itunes:duration>
    </item>
"""


def generate_rss():
    items = []
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
        print(f"Created {AUDIO_DIR}/")

    audio_files = sorted(
        [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")],
        reverse=True,  # newest first
    )

    for filename in audio_files:
        audio_path = os.path.join(AUDIO_DIR, filename)
        size = os.path.getsize(audio_path)
        mtime = os.path.getmtime(audio_path)
        pub_date = email.utils.formatdate(mtime, localtime=True)
        audio_url = f"{BASE_URL}/{AUDIO_DIR}/{filename}"
        # Add timestamp to GUID to force refresh on re-publish
        guid = f"{audio_url}?t={int(mtime)}"

        # Extract date from filename: playlist_2026-04-10.mp3
        date_match = re.search(r"playlist_(\d{4}-\d{2}-\d{2})", filename)
        date_str = date_match.group(1) if date_match else "unknown"
        title = f"Playlist — {date_str}"

        try:
            audio = MP3(audio_path)
            total_seconds = int(audio.info.length)
            minutes = total_seconds // 60
            duration = f"00:{minutes:02d}:{total_seconds % 60:02d}"
            summary = f"Re-listen playlist for {date_str} ({minutes} min)"
        except Exception:
            duration = "00:20:00"
            summary = f"Re-listen playlist for {date_str}"

        items.append(ITEM_TEMPLATE.format(
            title=title,
            author=AUTHOR,
            summary=summary,
            audio_url=audio_url,
            size=size,
            guid=guid,
            pub_date=pub_date,
            duration=duration,
        ))

    rss_content = RSS_TEMPLATE.format(
        base_url=BASE_URL,
        site_url=SITE_URL,
        author=AUTHOR,
        items="".join(items),
    )

    with open(RSS_FILE, "w") as f:
        f.write(rss_content)
    print(f"Generated {RSS_FILE} with {len(items)} playlists.")


if __name__ == "__main__":
    generate_rss()
