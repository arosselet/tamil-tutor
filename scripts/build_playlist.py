#!/usr/bin/env python3
"""
Build a daily re-listen playlist from existing episodes.

Selects episodes due for re-listening based on listen counts, concatenates
them into a single MP3 with brief silence between episodes.

Usage:
    python scripts/build_playlist.py                    # build playlist
    python scripts/build_playlist.py --target-min 25    # target 25 minutes
    python scripts/build_playlist.py --dry-run           # show plan without building

Spaced repetition at the episode level:
    - 0 listens: overdue (shouldn't happen, but include first)
    - 1 listen: due for re-listen
    - 2 listens: due soon
    - 3+ listens: graduated, only used as filler
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent.parent
VOCAB_STATE_PATH = BASE / "progress" / "vocab_state.json"
AUDIO_DIR = BASE / "audio"
OUTPUT_DIR = BASE / "audio" / "playlists"
PUBLISH_DIR = BASE / "published_playlists"


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_duration(mp3_path: Path) -> float | None:
    """Get duration in minutes."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", str(mp3_path)],
            capture_output=True, text=True
        )
        d = json.loads(result.stdout)
        return float(d["format"]["duration"]) / 60
    except Exception:
        return None


def select_episodes(vocab_state: dict, target_min: float) -> list[dict]:
    """Select episodes for the playlist, prioritizing under-listened ones."""
    episodes = vocab_state.get("episodes", {})
    candidates = []

    for mission_str, ep in episodes.items():
        mission = int(mission_str)
        listens = ep.get("listens", 0)
        mp3_path = AUDIO_DIR / f"tier2_mission{mission}.mp3"
        if not mp3_path.exists():
            continue

        duration = ep.get("duration_min") or get_duration(mp3_path) or 3.0

        # Priority: fewer listens = higher priority
        # Within same listen count, newer episodes first
        priority = -listens * 1000 + mission

        candidates.append({
            "mission": mission,
            "listens": listens,
            "duration": duration,
            "priority": priority,
            "path": mp3_path,
        })

    # Sort by priority (highest first = fewest listens, then newest)
    candidates.sort(key=lambda c: c["priority"], reverse=True)

    # Fill playlist up to target duration
    playlist = []
    total = 0.0
    for c in candidates:
        if total + c["duration"] > target_min and playlist:
            break
        playlist.append(c)
        total += c["duration"]

    # Sort final playlist by mission number for listening order
    playlist.sort(key=lambda c: c["mission"])
    return playlist


def _get_announcement_path(mission: int) -> Path:
    """Generate or get an 'Episode X' announcement MP3."""
    announcement_dir = AUDIO_DIR / "announcements"
    announcement_dir.mkdir(parents=True, exist_ok=True)
    path = announcement_dir / f"episode_{mission}.mp3"
    
    if not path.exists():
        text = f"Episode {mission}"
        # Using a reliable edge-tts voice for announcements
        voice = "en-US-EmmaNeural"
        print(f"Generating announcement: '{text}'")
        subprocess.run(
            ["edge-tts", "--voice", voice, "--text", text, "--write-media", str(path)],
            capture_output=True
        )
    return path


def concatenate_mp3s(playlist: list[dict], output_path: Path):
    """Concatenate MP3 files with announcements and silences."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for i, ep in enumerate(playlist):
            # Announcement first
            f.write(f"file '{_get_announcement_path(ep['mission'])}'\n")
            # 1s pause after announcement
            f.write(f"file '{_get_silence_path(1)}'\n")
            # The episode itself
            f.write(f"file '{ep['path']}'\n")
            
            if i < len(playlist) - 1:
                # Add 3 seconds of silence between episodes
                f.write(f"file '{_get_silence_path(3)}'\n")
        filelist = f.name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
         "-c", "copy", str(output_path)],
        capture_output=True
    )
    Path(filelist).unlink()


def _get_silence_path(duration: int = 2) -> Path:
    """Generate a silence MP3 of specified duration if it doesn't exist."""
    silence = AUDIO_DIR / "playlists" / f"_silence_{duration}s.mp3"
    if not silence.exists():
        silence.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
             "-t", str(duration), "-q:a", "9", str(silence)],
            capture_output=True
        )
    return silence


def main():
    parser = argparse.ArgumentParser(description="Build a daily re-listen playlist")
    parser.add_argument("--target-min", type=float, default=15,
                        help="Target playlist duration in minutes (default: 15)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without building audio")
    parser.add_argument("--output", type=str, default=None,
                        help="Output path (default: audio/playlists/playlist_YYYY-MM-DD.mp3)")
    parser.add_argument("--publish", action="store_true",
                        help="Copy to published_playlists/ and rebuild playlist RSS feed")
    args = parser.parse_args()

    vocab_state = load_json(VOCAB_STATE_PATH)
    if not vocab_state:
        print("Error: No vocab_state.json found. Run 'sync_state.py migrate' first.")
        sys.exit(1)

    playlist = select_episodes(vocab_state, args.target_min)

    if not playlist:
        print("No episodes available for playlist.")
        return

    total_min = sum(ep["duration"] for ep in playlist)
    print(f"Playlist: {len(playlist)} episodes, ~{total_min:.0f} min")
    print("-" * 50)
    for ep in playlist:
        status = "NEW" if ep["listens"] == 0 else f"{ep['listens']}x"
        print(f"  M{ep['mission']:>2}  ({ep['duration']:.1f} min)  listened: {status}")
    print("-" * 50)
    print(f"  Total: ~{total_min:.0f} min")

    if args.dry_run:
        return

    output = Path(args.output) if args.output else (
        OUTPUT_DIR / f"playlist_{date.today().isoformat()}.mp3"
    )

    print(f"\nBuilding {output.name}...")
    concatenate_mp3s(playlist, output)
    print(f"Done: {output}")

    if args.publish:
        # Copy to published directory, then rebuild RSS
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        dest = PUBLISH_DIR / output.name
        shutil.copy2(output, dest)
        print(f"Published: {dest}")

        rss_script = BASE / "scripts" / "rebuild_playlist_rss.py"
        subprocess.run([sys.executable, str(rss_script)], cwd=str(BASE))
        print(f"\nPlaylist feed: playlist_rss.xml")
        print(f"Subscribe URL: https://raw.githubusercontent.com/arosselet/tamil-tutor/main/playlist_rss.xml")


if __name__ == "__main__":
    main()
