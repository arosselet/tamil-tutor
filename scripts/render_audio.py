#!/usr/bin/env python3
"""
Generate multi-voice Tamil podcast audio from a markdown script.

Usage:
    python scripts/render_audio.py <input_script.md> <output.mp3>

Example:
    python scripts/render_audio.py content/scripts/tier1_mission1.md audio/tier1_mission1.mp3

Reads dialogues prefixed with **Speaker Name:**, generates TTS audio
segments using edge-tts or Google Chirp, and stitches them into a single MP3.
Supports a # Voice Map block in markdown comments for explicit voice assignment.
"""

import re
import os
import asyncio
import argparse
import base64
import random
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import ssl as _ssl

BASE = Path(__file__).parent.parent

# This host is not a studio host — a missing credential, not a failure. Callers
# (run_studio.py) reads this code as "skip, don't retry":
# retrying an absent secret hourly just fills the log (2026-07-23, work laptop).
EXIT_NOT_CONFIGURED = 3

from publish import commit_and_push
from language import is_tamil, voice_locale

import edge_tts
import edge_tts.communicate as _edge_comm

# Remote environments use SSL inspection with self-signed certs.
# Patch edge_tts's SSL context to skip cert verification.
_no_verify_ctx = _ssl.create_default_context()
_no_verify_ctx.check_hostname = False
_no_verify_ctx.verify_mode = _ssl.CERT_NONE
_edge_comm._SSL_CTX = _no_verify_ctx
try:
    from google.cloud import texttospeech
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


def materialize_sa_key() -> str | None:
    """GCP_SA_KEY (the CI secret's own name) → a file ADC can resolve.

    `anna.yml` writes the secret to a path and points GOOGLE_APPLICATION_CREDENTIALS
    at it; a laptop had no equivalent, so a clone whose .env carried the very same
    secret still reported "this host cannot produce audio" (2026-07-27). One
    chokepoint, because every audio lane already calls google_credentials_ready().

    Accepts raw JSON or base64 — a .env value has to survive on ONE line, and the
    line-based parser silently keeps only the first line of a pasted document.
    Written outside the repo at 0600 so a credential can never be committed;
    an existing GOOGLE_APPLICATION_CREDENTIALS always wins.

    Returns the path written, or None when there is nothing usable to write.
    Never logs the secret — only whether it parsed."""
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return None
    raw = (os.environ.get("GCP_SA_KEY") or "").strip()
    if not raw:
        return None
    doc = None
    try:
        doc = json.loads(raw)
    except ValueError:
        try:
            doc = json.loads(base64.b64decode(raw))
        except Exception:
            doc = None
    if not isinstance(doc, dict) or "private_key" not in doc:
        print(f"   ⚠ GCP_SA_KEY is set ({len(raw)} chars) but is not a service-account "
              f"key — expected JSON (or base64 of it) carrying private_key. Ignoring it.")
        return None
    path = Path(tempfile.gettempdir()) / "anna-gcp.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass          # best-effort; Windows ACLs don't map onto POSIX modes
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
    return str(path)


def google_credentials_ready() -> str | None:
    """None when Google TTS can authenticate, else the reason. Local and cheap
    (no network) — google.auth.default() just resolves ADC. Checked ONCE before
    the render loop so a credential-less host skips in a second instead of
    burning five backoff retries on segment 0 (2026-07-23)."""
    if not HAS_GOOGLE:
        return "google-cloud-texttospeech is not installed"
    materialize_sa_key()
    try:
        import google.auth
        google.auth.default()
    except Exception as e:
        return f"no Google application-default credentials ({type(e).__name__})"
    return None


def is_auth_error(e: Exception) -> bool:
    """Credential/permission failures are permanent — backing off five times
    cannot fix an absent secret. Everything else stays retryable."""
    name = type(e).__name__
    if name in ("DefaultCredentialsError", "Unauthenticated", "PermissionDenied",
                "Forbidden", "RefreshError"):
        return True
    return any(s in str(e).lower() for s in
               ("credential", "unauthenticated", "permission denied", "api key"))


def new_scratch_dir() -> str:
    """A fresh TTS scratch dir per render. Named (not inlined) so the smoke test
    can assert the invariant that actually broke: two concurrent renders must
    never share one."""
    return tempfile.mkdtemp(prefix="tts_segments_")


def acquire_state_lock():
    """Serialize the state tail (episodes.json → rss.xml → commit/push) against
    any other studio process. Shares `.studio.lock` with run_studio.py and
    run_studio.py; when a parent already holds it we inherit rather than
    deadlock against our own spawner (STUDIO_LOCK_HELD). The render itself is
    NOT covered — per-run temp dirs make concurrent renders safe, and holding a
    lock across ten minutes of TTS would serialize the slow part for nothing."""
    if os.environ.get("STUDIO_LOCK_HELD") == "1":
        return None
    try:
        import fcntl
    except ImportError:
        return None
    fd = open(BASE / ".studio.lock", "w")
    for attempt in range(60):  # up to ~60s: the tail is seconds long, not minutes
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            if attempt == 0:
                print("   ⏳ another studio process holds .studio.lock — waiting to publish…")
            time.sleep(1)
    fd.close()
    print("   ⚠️ gave up waiting for .studio.lock — publishing without it")
    return None

# THE PINNED SINGLE VOICES are no longer declared here (2026-08-28) — import
# them from `language`. They arrived in this file on 2026-08-23 on the reasoning
# that they belong with neither of the six lanes that read them, which was right;
# the pack is a better answer to the same question, because a pinned voice is a
# value a PORT replaces and this file is not where a port looks.
#
# Voice POOLS — Indian Tamil, 30+ Chirp voices. These stay: they are a
# CATALOGUE with one reader, and the pinned voices above are a choice from it
# (which is why `s70` carries a declared exemption for the two overlaps).

_CHIRP_POOL_MALE = [
    "ta-IN-Chirp3-HD-Achird", "ta-IN-Chirp3-HD-Algenib", "ta-IN-Chirp3-HD-Algieba",
    "ta-IN-Chirp3-HD-Alnilam", "ta-IN-Chirp3-HD-Charon", "ta-IN-Chirp3-HD-Enceladus",
    "ta-IN-Chirp3-HD-Fenrir", "ta-IN-Chirp3-HD-Iapetus", "ta-IN-Chirp3-HD-Orus",
    "ta-IN-Chirp3-HD-Puck", "ta-IN-Chirp3-HD-Rasalgethi", "ta-IN-Chirp3-HD-Sadachbia",
    "ta-IN-Chirp3-HD-Sadaltager", "ta-IN-Chirp3-HD-Schedar", "ta-IN-Chirp3-HD-Umbriel",
    "ta-IN-Chirp3-HD-Zubenelgenubi"
]

_CHIRP_POOL_FEMALE = [
    "ta-IN-Chirp3-HD-Achernar", "ta-IN-Chirp3-HD-Aoede", "ta-IN-Chirp3-HD-Autonoe",
    "ta-IN-Chirp3-HD-Callirrhoe", "ta-IN-Chirp3-HD-Despina", "ta-IN-Chirp3-HD-Erinome",
    "ta-IN-Chirp3-HD-Gacrux", "ta-IN-Chirp3-HD-Kore", "ta-IN-Chirp3-HD-Laomedeia",
    "ta-IN-Chirp3-HD-Leda", "ta-IN-Chirp3-HD-Pulcherrima", "ta-IN-Chirp3-HD-Sulafat",
    "ta-IN-Chirp3-HD-Vindemiatrix", "ta-IN-Chirp3-HD-Zephyr"
]

_CHIRP_POOL = _CHIRP_POOL_MALE + _CHIRP_POOL_FEMALE

_WAVENET_POOL_MALE = ["ta-IN-Wavenet-B", "ta-IN-Wavenet-D"]
_WAVENET_POOL_FEMALE = ["ta-IN-Wavenet-A", "ta-IN-Wavenet-C"]
_WAVENET_POOL = _WAVENET_POOL_MALE + _WAVENET_POOL_FEMALE

_EDGE_POOL_MALE = ["ta-IN-ValluvarNeural"]
_EDGE_POOL_FEMALE = ["ta-IN-PallaviNeural"]
_EDGE_POOL = _EDGE_POOL_MALE + _EDGE_POOL_FEMALE

# Voice tuning for distinctiveness (Edge only)
EDGE_VOICE_OPTS = {
    "ta-IN-PallaviNeural": {"rate": "+0%", "pitch": "-5Hz"},
    "ta-IN-ValluvarNeural": {"rate": "+0%", "pitch": "-5Hz"},
}

# Regex: matches "**Speaker:** text"
SPEAKER_RE = re.compile(
    r"^\s*(?:\*\s*)?\*\*\s*([^:]+)\s*:\s*(?:\*\*\s*)?(.*)", re.IGNORECASE
)
# Every pause dialect the scripts actually use: "[Pause: 1 sec]", the fractional
# "[Pause: 0.5 sec]", and the bare "[pause]" (defaults to a 1-second beat).
# `[^\]]*` and not `.*` on purpose — a greedy tail swallows the text BETWEEN two
# pauses on the same line, which is most of how M74 was written.
PAUSE_RE = re.compile(
    r"\[pause(?::\s*(\d+(?:\.\d+)?)\s*sec[^\]]*)?\]", re.IGNORECASE
)
SFX_RE = re.compile(r"^\[SFX\b", re.IGNORECASE)
EMBED_RE = re.compile(r"\[Intercept (audio )?plays\]", re.IGNORECASE)
VOICE_MAP_RE = re.compile(r"Voice Map\s*:\s*(\{.*?\})", re.DOTALL | re.IGNORECASE)

def pause_seconds(match: re.Match) -> float:
    """Seconds for a matched pause cue; a bare '[pause]' is one beat."""
    return float(match.group(1)) if match.group(1) else 1.0


def split_on_pauses(speaker: str, text: str) -> list[dict]:
    """Split one spoken line into speech / pause / speech in written order.

    A pause written INSIDE a line is a beat WITHIN that line, never a
    replacement for it. Returns a single speech item when the line holds no
    pause, so this is the one path every speaker line takes.
    """
    items: list[dict] = []
    cursor = 0
    for match in PAUSE_RE.finditer(text):
        head = text[cursor:match.start()].strip()
        if head:
            items.append({"speaker": speaker, "text": head})
        items.append({"speaker": "PAUSE", "seconds": pause_seconds(match)})
        cursor = match.end()
    tail = text[cursor:].strip()
    if tail:
        items.append({"speaker": speaker, "text": tail})
    return items


def parse_script(file_path: str) -> tuple[list[dict], dict]:
    """Parse a markdown script for dialogue lines, pauses, and voice mapping."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract Voice Map from comments if present
    voice_map = {}
    map_match = VOICE_MAP_RE.search(content)
    if map_match:
        try:
            voice_map = json.loads(map_match.group(1))
            print(f"✅ Found explicit Voice Map: {voice_map}")
        except json.JSONDecodeError:
            print("⚠️ Warning: Failed to parse Voice Map JSON.")

    lines = content.splitlines()
    dialogue = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if SFX_RE.match(line):
            # No sound library — an SFX cue becomes a beat of air, never silence-dropped
            dialogue.append({"speaker": "PAUSE", "seconds": 1.5})
            continue

        if EMBED_RE.search(line):
            dialogue.append({"speaker": "EMBED_INTERCEPT"})
            continue

        if line == "---":
            dialogue.append({"speaker": "PAUSE", "seconds": 1})
            continue

        # The speaker question is asked BEFORE the pause question, and this
        # ordering is the whole bug: the old code ran PAUSE_RE.search() first,
        # so any spoken line merely CONTAINING a pause became silence and its
        # dialogue was discarded — 56 lines across 13 episodes, 18 of them in
        # M74, with nothing in the render output to show for it.
        match = SPEAKER_RE.match(line)
        if match:
            speaker = match.group(1).strip().upper()
            dialogue.extend(split_on_pauses(speaker, match.group(2).strip()))
            continue

        # Not speech, but it carries a pause cue: the line IS the pause.
        pause_match = PAUSE_RE.search(line)
        if pause_match:
            dialogue.append({"speaker": "PAUSE", "seconds": pause_seconds(pause_match)})

    # Coalesce consecutive pauses
    final_dialogue = []
    for item in dialogue:
        if item["speaker"] == "PAUSE":
            if final_dialogue and final_dialogue[-1]["speaker"] == "PAUSE":
                final_dialogue[-1]["seconds"] += item["seconds"]
            else:
                final_dialogue.append(item)
        else:
            final_dialogue.append(item)

    return final_dialogue, voice_map


def defang_hyphens(text: str) -> str:
    """TTS voices a hyphen glued to a word as 'minus' ('-இட்டு' → 'minus ittu')."""
    return re.sub(r"-(?=\w)|(?<=\w)-", " ", text)


def clean_memo_for_tts(text: str) -> str:
    """Clean an English-narrated memo paragraph for TTS.

    Preserves Tamil script (the Tamil voice renders it correctly) and preserves periods
    (memo prose needs them). Strips markdown formatting and collapses internal newlines
    (single-\\n example lists from the LLM land in one TTS call and confuse the voice).
    """
    # Detach hyphens glued to words — '-இட்டு' was voiced as 'minus ittu'
    text = defang_hyphens(text)
    # Markdown bold/italic/code — asterisks get voiced or disrupt TTS parsing
    text = re.sub(r"[*_#`]", "", text)
    # Collapse internal newlines (single-\n within a paragraph) to spaces
    text = text.replace("\n", " ")
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def clean_for_tts(text: str) -> str:
    """Clean a script dialogue line for TTS consumption.

    Preserves periods: they are the sentence breaks Chirp3-HD needs for prosody.
    Stripping them (the old behaviour) flattened multi-sentence lines into one
    breathless run-on and swallowed the tails of short sentences (the memo path
    already routed around this, DECISIONS 2026-07-07; now fixed at the source).
    """
    text = re.sub(r"\s*\(.*?\)\s*", " ", text)
    text = re.sub(r"\s*\[.*?\]\s*", " ", text)
    replacements = {"JSON": "jay-son", "CLI": "C-L-I"}
    for word, phonetic in replacements.items():
        text = re.sub(rf"\b{word}\b", phonetic, text, flags=re.IGNORECASE)
    text = re.sub(r"[*_#`]", "", text)
    text = defang_hyphens(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def generate_segment_edge(text: str, voice: str, index: int, temp_dir: str) -> str:
    """Generate a single audio segment using edge-tts."""
    import aiohttp as _aiohttp
    opts = EDGE_VOICE_OPTS.get(voice, {"rate": "+0%", "pitch": "+0Hz"})
    connector = _aiohttp.TCPConnector(ssl=False)
    communicate = edge_tts.Communicate(text, voice, rate=opts["rate"], pitch=opts["pitch"], connector=connector)
    filename = os.path.join(temp_dir, f"segment_{index:04d}.mp3")
    await communicate.save(filename)
    await connector.close()
    return filename


async def generate_segment_google(text: str, voice: str, index: int, temp_dir: str, max_retries: int = 5) -> str:
    """Generate a single audio segment using Google Cloud TTS with exponential backoff."""
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=voice_locale(voice), name=voice)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, sample_rate_hertz=24000)
    for attempt in range(max_retries):
        try:
            response = client.synthesize_speech(input=input_text, voice=voice_params, audio_config=audio_config)
            filename = os.path.join(temp_dir, f"segment_{index:04d}.mp3")
            with open(filename, "wb") as out:
                out.write(response.audio_content)
            return filename
        except Exception as e:
            if is_auth_error(e):
                raise  # permanent — no amount of backoff conjures a credential
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt + random.random()
            print(f"   ⚠️ Retry {attempt+1}/{max_retries} after {wait:.1f}s — {e}")
            time.sleep(wait)


def get_raw_mp3_frames(filepath: str) -> bytes:
    """Extract raw MPEG audio chunk."""
    with open(filepath, "rb") as f:
        data = f.read()
    offset = 0
    if data.startswith(b"ID3"):
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        offset = 10 + size
    if offset < len(data) - 1 and data[offset] == 0xFF and (data[offset+1] & 0xE0) == 0xE0:
        padding = (data[offset+2] & 0x02) >> 1
        frame_len = 144 + padding
        frame_data = data[offset:offset+frame_len]
        if b"Xing" in frame_data or b"Info" in frame_data:
            offset += frame_len
    end_offset = len(data)
    if end_offset >= 128 and data[-128:].startswith(b"TAG"):
        end_offset -= 128
    return data[offset:end_offset]


SILENCE_FRAME_B64 ="//NkxJoiPA4Vgc1AAVXPcXO05CbzflKqdX8LXO/PQy7v6mbnkYz3BsVdxH7xI1psbFEYzt6Fxl0w17Szht3EmOWRKhJANxpojDXhk+E+3qNp+0+oomHuYca0xPxKUOihtdfcvPB+yzd2o2Sbh5zuLHVDDK9juB8rHhbq9lYT0XEdvYWKCGEeTvz8YP2XWipB"
SILENCE_FRAME = base64.b64decode(SILENCE_FRAME_B64)

def assign_voices(dialogue, voice_map, provider, voice_type):
    """
    Assign voices to speakers. 
    Uses a random selection from the pool for each name encountered.
    Supports (M) or (F) in the speaker name for explicit gender casting.
    """
    speakers = set(d["speaker"] for d in dialogue if d["speaker"] != "PAUSE" and d["speaker"] != "EMBED_INTERCEPT")
    
    assigned = {}
    
    # 1. Respect explicit map (overrides)
    for speaker, voice in voice_map.items():
        assigned[speaker.upper()] = voice

    # 2. Select pool
    if provider == "google":
        pool_male = list(_CHIRP_POOL_MALE if voice_type == "chirp" else _WAVENET_POOL_MALE)
        pool_female = list(_CHIRP_POOL_FEMALE if voice_type == "chirp" else _WAVENET_POOL_FEMALE)
        pool_any = list(_CHIRP_POOL if voice_type == "chirp" else _WAVENET_POOL)
    else:
        pool_male = list(_EDGE_POOL_MALE)
        pool_female = list(_EDGE_POOL_FEMALE)
        pool_any = list(_EDGE_POOL)

    available_male = [v for v in pool_male if v not in assigned.values()]
    if not available_male: available_male = list(pool_male)
    random.shuffle(available_male)

    available_female = [v for v in pool_female if v not in assigned.values()]
    if not available_female: available_female = list(pool_female)
    random.shuffle(available_female)

    available_any = [v for v in pool_any if v not in assigned.values()]
    if not available_any: available_any = list(pool_any)
    random.shuffle(available_any)
    
    for s in sorted(list(speakers)):
        s_upper = s.upper()
        if s_upper not in assigned:
            if "(M)" in s_upper or "(MALE)" in s_upper:
                assigned[s_upper] = available_male.pop() if available_male else random.choice(pool_male)
            elif "(F)" in s_upper or "(FEMALE)" in s_upper:
                assigned[s_upper] = available_female.pop() if available_female else random.choice(pool_female)
            else:
                assigned[s_upper] = available_any.pop() if available_any else random.choice(pool_any)

    return assigned

def register_mission_in_state(script_path: Path, mp3_path: Path):
    """
    Registers a new mission in progress/episodes.json.
    """
    from pathlib import Path
    # Absolute, off BASE — these were CWD-relative, so the state this function
    # writes landed wherever the caller happened to be standing. Production hid
    # it (run_studio shells out with cwd=BASE), but the smoke suite imports the
    # SANDBOX copy without chdir'ing, so a test run wrote a fake mission and its
    # words straight into the real progress/ files (2026-07-31, caught by s43 on
    # its first run). A test that mutates live state is worse than no test.
    EPISODES_PATH = BASE / "progress" / "episodes.json"
    LEXICON_PATH = BASE / "progress" / "lexicon.json"
    
    def load_json(path: Path):
        if not path.exists(): return {}
        with open(path, "r", encoding="utf-8") as f: return json.load(f)

    def save_json(path: Path, data):
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

    def get_duration(p: Path) -> float:
        """Measured, or LOUD — never a plausible fiction (2026-08-10).

        This was `except: return 3.0`, and on a host without ffprobe every
        episode registered as exactly 3.0 minutes. M78-M85 are all stamped 3.0 in
        episodes.json; their real lengths are 1.7-3.5, and the fallback was
        invisible because the number it invents is the number a short episode
        plausibly has. Andrew judges an episode partly by the length his player
        shows him (the reason durations became measured at all, 2026-07-23), so a
        silently-invented one corrupts exactly the meter that ruling protected.

        `audio_duration` is the authority rebuild_rss already uses: ffprobe when
        it exists, a pure-python frame scan when it does not. The scan is
        imperfect on a bad header; it is not fiction. 0.0 with a warning is the
        honest floor — a zero is visible, and 3.0 was not."""
        from rebuild_rss import audio_duration
        try:
            return (audio_duration(str(p)) or 0) / 60
        except Exception as e:
            print(f"   ⚠ could not measure {p.name} ({e}) — registering 0.0, not a guess")
            return 0.0

    # Extract title and words from script
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    title_match = re.search(r"^# Tier 2, Mission \d+ — (.*)$", content, re.M)
    title = title_match.group(1) if title_match else f"Mission {script_path.stem}"
    # Prefer the structured .tags.json sidecar (canonical vocab: new words +
    # callbacks). The markdown doesn't bold its vocab, so scraping bold tokens
    # only ever caught English speaker labels. Fall back to that scrape only
    # when no sidecar exists.
    # Canonical-at-write, same law as sync_state: every key that lands in
    # episodes.json / seen_in must resolve to a lexicon record, or be a genuinely
    # new Tamil-script payload word. A Producer annotation like
    # "frame:want-noun (வேணும்)" must credit frame:want-noun — not spawn a ghost.
    lexicon = load_json(LEXICON_PATH)
    phon = {p: w for w, r in lexicon.items() for p in r.get("phonetic", [])}

    def canonical(w: str) -> str | None:
        """Resolve a sidecar key to its lexicon key, tolerating a trailing
        ' (…)' annotation. None if nothing resolves."""
        for cand in (w, re.sub(r"\s*\([^)]*\)\s*$", "", w).strip()):
            if cand in lexicon:
                return cand
            if cand in phon:
                return phon[cand]
        return None

    cleaned_words = []
    new_word_keys = set()
    tags_path = script_path.with_suffix(".tags.json")
    sidecar_broken = False
    if tags_path.exists():
        try:
            tags = json.loads(tags_path.read_text(encoding="utf-8"))
            for bucket in ("new_words_landed", "callbacks_used"):
                for w in tags.get(bucket, {}):
                    key = canonical(w)
                    if key is None:
                        base = re.sub(r"\s*\([^)]*\)\s*$", "", w).strip()
                        if base.startswith("frame:"):
                            # Frames are seeded via add-pattern / seed-deck, never
                            # born in a render — an unresolvable one is a sidecar
                            # typo, and creating it would poison the word axes.
                            print(f"   ! sidecar frame '{w}' resolves to no lexicon pattern — skipped")
                            continue
                        key = base  # may be a brand-new payload word (created below)
                    if key not in cleaned_words:
                        cleaned_words.append(key)
                        if bucket == "new_words_landed":
                            new_word_keys.add(key)
        except (json.JSONDecodeError, OSError) as e:
            # LOUD, AND IT REFUSES THE FALLBACK (2026-08-24). This was `pass`.
            # A sidecar that EXISTS but cannot be parsed is a BROKEN file, not a
            # missing one — and the scrape below would then build a plausible
            # word list from the wrong source entirely: bold tokens in the
            # markdown, which is not where the vocab is written. episodes.json
            # and every row's `seen_in` would record words the episode never
            # taught, the render would succeed, and every instrument would read
            # green. That is the artifact-shaped nothing this codebase keeps
            # finding: a state indistinguishable from success.
            #
            # So it says so, and it does NOT fall through. An empty word list
            # under-claims; the scrape INVENTS, and the ledger's own law is that
            # it under-claims rather than invents (the claim_payload rule,
            # 2026-07-17). A warning nobody can act on is noise; this one names
            # the file, the error, and what to do.
            sidecar_broken = True
            print(f"   ! {tags_path.name} EXISTS BUT COULD NOT BE READ "
                  f"({type(e).__name__}: {e})")
            print("     Not scraping the script instead — that would credit words "
                  "this episode never taught. Fix the sidecar and re-run.")
    if not cleaned_words and not sidecar_broken:
        for w in re.findall(r"\*\*([^\*]+)\*\*", content):
            tamil = re.split(r"[\(\s]", w)[0]
            if tamil and is_tamil(tamil) and tamil not in cleaned_words:
                cleaned_words.append(tamil)

    mission_match = re.search(r"mission(\d+)", script_path.name)
    if not mission_match: return
    mission_num = mission_match.group(1)
    
    episodes = load_json(EPISODES_PATH)
    duration = get_duration(mp3_path)

    if mission_num not in episodes:
        episodes[mission_num] = {
            "title": title, "words": cleaned_words, "duration_min": duration,
            # produced-on date: the unattended-production cap counts these, so a
            # stuck trigger can never flood the feed again (2026-07-23).
            "produced": date.today().isoformat(),
        }
        print(f"✅ Registered Mission {mission_num} in episodes.json")
    else:
        episodes[mission_num].update({
            "title": title, "words": cleaned_words, "duration_min": duration
        })
        print(f"✅ Updated Mission {mission_num} metadata in episodes.json")

    save_json(EPISODES_PATH, episodes)

    # Delivery seam (2026-07-26 ledger law): the episode going out the door IS
    # the exposure — stamped here at registration, not on a confirmed listen
    # (confirmed-listen is unreliable by Andrew's own account; the counter's job
    # is rotation fairness). seen_in stays pure provenance alongside it.
    # (lexicon + phon were loaded above; cleaned_words are already canonical.)
    if lexicon:
        from sync_state import mark_exposed
        mnum = int(mission_num)
        today = date.today().isoformat()
        tagged = 0
        created = 0
        unresolved = []
        for w in cleaned_words:
            key = w if w in lexicon else phon.get(w)
            if key is None and w in new_word_keys and is_tamil(w):
                # Brand-new payload word: introduce it at the bottom of the
                # recognition ladder — heard, not yet known, so it stays below
                # the fence until Anna observes recognition. gloss/phonetic
                # backfill later, the same as sync_state's set_recognition.
                lexicon[w] = {
                    "gloss": "", "phonetic": [], "recognition": "struggled",
                    "production": "none", "seen_in": [mnum],
                    "last_surfaced": today, "exposures": 1,
                }
                created += 1
                continue
            if key:
                # TAUGHT IS NOT APPEARED (2026-09-01, Andrew). Only
                # `new_words_landed` stamps seen_in. A callback is a word riding
                # PAST in a scene, and the constitution grants an appearance no
                # teaching authority — yet BOTH buckets stamped this field, so
                # every episode credited itself with teaching each word it
                # merely reused. That is how தெரியும் reached the cold-quiz
                # pool: *"you haven't taught me theriyum so I haven't known to
                # reach for it"* (ledger, 08-29).
                #
                # The split needs NO SCHEMA: seen_in is TAUGHT, and the
                # exposures / last_surfaced that mark_exposed writes below are
                # APPEARED. Both already existed; one write site conflated them,
                # which is why the comment above ("seen_in stays pure
                # provenance") described an intent the code did not keep.
                #
                # Second half of "A tape is not a teacher" (08-31) — that pass
                # fixed is_unseen, the READER, and left this WRITER minting the
                # very rows it was reading. Callbacks keep their exposure stamp;
                # they lose only the teaching claim they never earned.
                if key in new_word_keys:
                    seen = lexicon[key].setdefault("seen_in", [])
                    if mnum not in seen:
                        seen.append(mnum)
                        seen.sort()
                mark_exposed(lexicon, [key], phon_index=phon, today=today)
                tagged += 1
            else:
                # A callbacks_used key that resolves to nothing used to fall out
                # here in silence: only new_words_landed may CREATE a record, so
                # the word shipped with real exposures on the tape and no trace
                # in the ledger — unschedulable, uncollectable, invisible to
                # suggest_targets (2026-07-31: இருந்துச்சு, the very word Andrew
                # had asked for). Creating it here is wrong — a callback claims
                # the word already exists, so an unresolvable one is far more
                # likely a variant of a real record, and inventing a duplicate
                # poisons the axes (the same reasoning as the frame branch
                # above). So: report it, exactly as the frame case does, and let
                # the operator re-file it. A silent drop is the only thing ruled out.
                unresolved.append(w)
        if unresolved:
            print(f"   ! sidecar callback(s) resolve to no lexicon word — NOT registered, "
                  f"NOT exposed: {unresolved}")
            print(f"     → if one is genuinely new, move it to new_words_landed in "
                  f"{tags_path.name} and re-run; if it is a variant, fix the sidecar spelling.")
        if tagged or created:
            save_json(LEXICON_PATH, lexicon)
            msg = f"   ↳ exposed {tagged} lexicon words via M{mnum} (seen_in + delivery stamp)"
            if created:
                msg += f"; +{created} NEW words registered (recognition=struggled, gloss empty — backfill later)"
            print(msg)

async def main():
    parser = argparse.ArgumentParser(description="Generate Multi-Voice Tamil Podcast Audio")
    parser.add_argument("input_file", help="Input markdown script")
    parser.add_argument("output_file", help="Output MP3 file")
    parser.add_argument("--provider", choices=["edge", "google"], default="google", help="TTS provider (default: google)")
    parser.add_argument("--voice-type", choices=["chirp", "wavenet"], default="chirp", help="Google voice tier (default: chirp)")
    args = parser.parse_args()

    # Load .env for GCP_SA_KEY (local). run_studio.py did this before shelling
    # out here, so a render inside the studio always had credentials while the
    # SAME command run by hand reported "this host cannot produce audio"
    # (2026-07-31) — the standalone entry point was the only lane without it.
    # Kept inside main(): this module is imported by the cloud knock/dose lanes,
    # which get their secrets from the workflow, and an import-time side effect
    # would reach them too. load_env uses setdefault, so a real env always wins.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from publish import load_env
    load_env(Path(__file__).resolve().parent.parent / ".env")

    print(f"📖 Parsing {args.input_file}...")
    dialogue, voice_map = parse_script(args.input_file)
    if not dialogue:
        print("❌ No dialogue lines found!")
        return

    if args.provider == "google":
        reason = google_credentials_ready()
        if reason:
            print(f"⏭️  Skipping render — {reason}.\n"
                  f"    This host is not set up to produce audio; copy the credentials over "
                  f"(see task: studio secrets) or render on the personal laptop.")
            sys.exit(EXIT_NOT_CONFIGURED)

    speaker_assignments = assign_voices(dialogue, voice_map, args.provider, args.voice_type)
    print("🎭 Cast Assignments:")
    for s, v in speaker_assignments.items():
        print(f"   - {s}: {v}")

    # Per-run scratch dir. Was a fixed "temp_audio_segments" shared by every
    # render on the machine, so whichever finished first rmdir'd it out from
    # under the other — that raced the watchdog into a FileNotFoundError and
    # cost a draft episode (2026-07-23). Concurrency is now safe by construction.
    temp_dir = new_scratch_dir()
    os.makedirs(os.path.dirname(args.output_file) or ".", exist_ok=True)

    print("🎙️ Generating audio segments...")
    final_audio_data = bytearray()

    try:
        for i, line in enumerate(dialogue):
            speaker = line["speaker"]
            if speaker == "PAUSE":
                seconds = line.get("seconds", 1)
                final_audio_data.extend(SILENCE_FRAME * int(seconds * 41.666))
                continue

            if speaker == "EMBED_INTERCEPT":
                print(f"   [{i+1}/{len(dialogue)}] ⚠️ Skipping [Intercept audio plays] — deprecated in single-script mode")
                continue

            voice = speaker_assignments.get(speaker)
            clean_text = clean_for_tts(line["text"])
            if not clean_text: continue

            print(f"   [{i+1}/{len(dialogue)}] {speaker} ({voice}): {clean_text[:40]}...")

            if args.provider == "google":
                seg_file = await generate_segment_google(clean_text, voice, i, temp_dir)
            else:
                seg_file = await generate_segment_edge(clean_text, voice, i, temp_dir)

            final_audio_data.extend(get_raw_mp3_frames(seg_file))
            final_audio_data.extend(SILENCE_FRAME * 21) # ~500ms breath between lines
            os.remove(seg_file)
    finally:
        # try/finally so a crashed render stops leaking scratch dirs
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Save outputs
    for folder in ["audio", "published_audio"]:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, os.path.basename(args.output_file))
        with open(path, "wb") as f:
            f.write(final_audio_data)
        print(f"💾 Saved → {path}")

    print(f"✅ Success! ({len(final_audio_data)/(1024*1024):.1f} MB)")

    # Lifecycle hooks — state + publish. Held under .studio.lock so two studio
    # processes can never interleave episodes.json / rss.xml / the commit.
    # `commit_and_push` is imported at module level (2026-08-23). It used to be
    # deferred to this line because it lived in `morning_knock`, which imports
    # FROM this module — a genuine cycle. `publish.py` imports nothing here, so
    # the dodge is retired rather than inherited.

    lock = acquire_state_lock()
    try:
        # Register the mission in episodes.json + stamp seen_in into the lexicon
        register_mission_in_state(Path(args.input_file), Path(args.output_file))

        subprocess.run([sys.executable, str(BASE / "scripts" / "rebuild_rss.py")],
                       cwd=BASE, check=True)

        # Stage THIS mission's files by name. Staging whole content/ directories
        # swept a concurrently-written draft episode into this commit, which was
        # then deleted as a stray (2026-07-23) — a commit must only ever carry
        # the episode it rendered.
        stem = Path(args.input_file).stem
        candidates = [
            Path("rss.xml"),
            Path("progress/episodes.json"),
            Path("progress/lexicon.json"),
            Path("published_audio") / os.path.basename(args.output_file),
            Path("content/lessons") / f"{stem}_brief.md",
            Path("content/captions") / f"{stem}.md",
            Path(args.input_file),
            Path(args.input_file).with_suffix(".tags.json"),
        ]
        paths = [BASE / p for p in candidates if (BASE / p).exists()]

        # Publish through the SAME net every other writer uses (2026-08-20).
        # This lane used to run a raw add/commit/push with no pull and no
        # rebase — weaker than the hand-rolled `git pull --rebase` that was
        # removed from anna.yml's tap step on 2026-08-04 for exactly this
        # reason. Actions commits to main hourly, so a laptop render races a
        # cloud knock by construction; commit_and_push carries
        # _rebase_onto_main (union-merge for append-only arrays, re-render for
        # derived files, loud abort otherwise).
        # Keep the old "nothing staged" branch: commit_and_push commits
        # unconditionally, and a re-render that changed no bytes must not turn
        # into a crash where it used to be a no-op line.
        subprocess.run(["git", "add", "--", *[str(p.relative_to(BASE)) for p in paths]],
                       cwd=BASE, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=BASE).returncode == 0:
            print("   nothing staged — no commit")
        else:
            commit_and_push(
                paths,
                f"Add lesson: {os.path.basename(args.output_file)} and update state")

    finally:
        if lock is not None:
            lock.close()

if __name__ == "__main__":
    asyncio.run(main())
