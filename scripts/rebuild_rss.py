#!/usr/bin/env python3
import os
import re
from datetime import datetime
import email.utils

# Configuration
BASE_URL = "https://raw.githubusercontent.com/arosselet/tamil-tutor/main"
AUDIO_DIR = "published_audio"
SCRIPTS_DIR = "content/scripts"
RSS_FILE = "rss.xml"

RSS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
    xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Coimbatore Mappilai</title>
    <link>{base_url}</link>
    <language>en-us</language>
    <itunes:author>Andrew Rosselet</itunes:author>
    <itunes:summary>Interactive Tamil language learning sessions from Coimbatore.</itunes:summary>
    <description>Tamil learning through dialogue and culture, recorded in Coimbatore.</description>
    <itunes:owner>
      <itunes:name>Andrew Rosselet</itunes:name>
    </itunes:owner>
    <itunes:explicit>no</itunes:explicit>
    <itunes:category text="Education">
      <itunes:category text="Language Courses"/>
    </itunes:category>
    <itunes:image href="{base_url}/logo.png"/>
    {items}
  </channel>
</rss>
"""

ITEM_TEMPLATE = """
    <item>
      <title>{title}</title>
      <itunes:author>Andrew Rosselet</itunes:author>
      <itunes:summary>{summary}</itunes:summary>
      <enclosure url="{audio_url}" length="{size}" type="audio/mpeg"/>
      <guid>{audio_url}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:duration>{duration}</itunes:duration>
    </item>
"""

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
    # Get all mp3 files in audio/
    if not os.path.exists(AUDIO_DIR):
        print(f"❌ {AUDIO_DIR} not found!")
        return
    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]
    # Sort mp3 files: episodes (level/tier) at the top, others (demos) at the bottom.
    # Each group is sorted by modification time (newest first).
    episodes = [f for f in audio_files if f.startswith('level') or f.startswith('tier')]
    others = [f for f in audio_files if f not in episodes and not f.startswith(('test_', 'silence_'))]
    
    episodes.sort(key=lambda x: os.path.getmtime(os.path.join(AUDIO_DIR, x)), reverse=True)
    others.sort(key=lambda x: os.path.getmtime(os.path.join(AUDIO_DIR, x)), reverse=True)
    
    sorted_files = episodes + others

    for filename in sorted_files:
        audio_path = os.path.join(AUDIO_DIR, filename)
        # Try to find matching script
        script_name = filename.replace('.mp3', '.md')
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        
        title = get_title_from_md(script_path) or filename
        size = os.path.getsize(audio_path)
        mtime = os.path.getmtime(audio_path)
        pub_date = email.utils.formatdate(mtime, localtime=True)
        audio_url = f"{BASE_URL}/{AUDIO_DIR}/{filename}"
        
        # Duration is hard to get without external libs, so we'll omit or put dummy
        items.append(ITEM_TEMPLATE.format(
            title=title,
            summary=f"Lesson: {title}",
            audio_url=audio_url,
            size=size,
            pub_date=pub_date,
            duration="00:05:00" # Placeholder
        ))

    rss_content = RSS_TEMPLATE.format(
        base_url=BASE_URL,
        items="".join(items)
    )

    with open(RSS_FILE, 'w') as f:
        f.write(rss_content)
    print(f"✅ Generated {RSS_FILE} with {len(items)} episodes.")

if __name__ == "__main__":
    generate_rss()
