#!/usr/bin/env python3
"""
The long-haul tape — one press of play, forty-five minutes, nothing asked.

The FOURTH audio channel, and the one the trip exposed. The other three are all
sized for the same capacity regime: a 10-15 minute slot interleaved into a
workday, where the binding constraint is ADHERENCE — will he finish it (the
2026-07-28 dose ruling, which this does not reopen: it is about that regime).
A twenty-hour flight inverts every term. Time is unlimited, executive function
is near zero, the mouth is unavailable (a stranger in the next seat), and the
screen is a cost. Measured against that, the back catalogue is ~50 press-plays
at a median 2.7 minutes each — fifty context switches, which is the plan he
correctly predicted he would not carry out (2026-08-10, Andrew: "frequently
pressing play and interacting with my phone... is not the kind of energy level
I imagine having on the journey").

WHAT THIS REPLACES: `render_soak.py --passes N` as the system's answer to "give
me something longer". That dial makes the same ten minutes play four times,
which is `audio_channels.md`'s own "never loop harder" failure wearing a length
costume. This lane is that file's rule -- *a tired ear asking for longer wants
more repetition, not more scene* -- taken to its conclusion: a long stretch of
structured recurrence, not a stretched episode.

THE RHYTHM IS PYTHON'S, AND THE CLOCK IS MEASURED, NOT GUESSED. No model is
asked for a forty-five minute script; if one could write it, what it would
produce is a LIST, and the repetition schedule is the entire pedagogical
payload. Instead: one small sheet per MOVEMENT, written just-in-time, rendered,
and measured.

A TAPE IS AS LONG AS ITS MATERIAL, and `--minutes` is a CEILING (Andrew,
2026-08-10, asked to choose and choosing the honest length over padding to a
round number). Each spine draws only on items its lead shape can actually teach
from — a root with no hosts is nothing to inventory — so the spines come out at
different lengths and that is the honest answer, not a shortfall: on the
2026-08-10 lexicon, `inventory` ~25 min, `machines` ~20, `room` capped at 45.
Growing a tape means growing its material, not lowering the bar for an item.

WHAT KEEPS A LONG TAPE OFF THE NERVES is one decision: the MOVEMENT, not the
line, is the unit of language mix (Andrew, same conversation: "I want it to be
not forty minutes of, like, Tamil English Tamil English"). Movements run ~1-2
minutes with distinct centres of gravity, on a cadence that never places two of
a kind side by side -- and `scene` and `eavesdrop` movements draw ONLY on items
the preceding movements already taught, so comprehension is structural rather
than hoped for.

  python scripts/render_longhaul.py --plan-only   # the movement plan; no network at all
  python scripts/render_longhaul.py --dry-run     # plan + the first sheets; no TTS, no publish
  python scripts/render_longhaul.py               # render -> RSS + commit + push + notify
  python scripts/render_longhaul.py --no-publish  # render locally, nothing leaves the machine

Secrets: OPENROUTER_API_KEY (the sheets), GCP ADC (TTS), ANNA_PUSH_WEBHOOK_URL (the push).
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from publish import commit_and_push, jsdelivr_url, load_env, push_to_phone
from render_audio import (ANNA_VOICE, EAVESDROP_VOICE,
                          generate_segment_google, get_raw_mp3_frames, SILENCE_FRAME,
                          clean_for_tts, google_credentials_ready, EXIT_NOT_CONFIGURED,
                          _CHIRP_POOL_MALE, _CHIRP_POOL_FEMALE)
# Reused rather than re-implemented: one single-shot call -> parsed JSON, fence
# handling, the blown-ceiling guard and — since 2026-08-23 — the executor choice.
# Moved out of render_drill so the lane that owns drills does not also own how
# every other lane talks to a model.
from writer import STR, arr, ask_json, obj

# What one movement IS, for the executor that can be told (see writer.obj).
MOVEMENT_SCHEMA = obj(frame=STR, beats=arr(ta=STR, en=STR))
from state_io import LEXICON_PATH, load_json
from sync_state import canon_payload, mark_soak_delivered, record_exposure

LONGHAUL_DIR = BASE / "published_audio"   # feed root — rebuild_rss picks up longhaul_*.mp3
SILENCE_PER_SEC = 41.666                  # frames per second (matches render_audio)

# ── The rotation law ────────────────────────────────────────────────────────
# Variety on a fixed cycle, not variety by taste. Each spine names its own lead
# shape; `scene` and `eavesdrop` are the RECALL shapes and consume no new items.
# INVARIANT (asserted in smoke s57): no cadence places two identical shapes
# adjacently, INCLUDING across the wrap — a repeat listen must not butt two of a
# kind together at the seam either, and he intends to play these two or three
# times through.
# A cadence must also OPEN on a teaching shape: a recall movement in slot 1 has
# nothing to recall, and the `room` spine shipped its first plan opening on an
# empty scene (caught by reading a --plan-only run, not by the suite — s57 now
# asserts it).
CADENCES = {
    "machines":  ("machine", "scene", "machine", "lore", "machine", "eavesdrop"),
    "inventory": ("inventory", "scene", "inventory", "lore", "inventory", "eavesdrop"),
    "room":      ("machine", "scene", "inventory", "eavesdrop", "scene", "lore"),
}
RECALL_SHAPES = {"scene", "eavesdrop"}
# How many pool items each shape is handed. Recall shapes re-use what the
# preceding movements taught, so their count is a look-back depth, not an appetite.
ITEMS = {"machine": 4, "inventory": 3, "scene": 6, "eavesdrop": 5, "lore": 2}
# Planning estimate ONLY — the render measures the real clock and stops there.
# Used to size the item pool so coverage lands inside the minutes he asked for.
# MEASURED 2026-08-10 off the first real tape: 15 movements ran 17.1 min before the
# closing lap, i.e. 1.14 each. The 3.5 here was a guess and was 3x high, so a
# 45-minute ask planned 15 movements and the tape stopped at 23.8 with the plan
# exhausted. Re-measure when the RHYTHM table or the beat counts change; this is a
# property of those, not of the tape.
MOVEMENT_MIN = 1.15
# The closing lap replays every unique Tamil line the tape spoke, so it grows with
# the material rather than sitting at a fixed cost. ~5.5 min on the 22-item tape.
CLOSING_LAP_MIN = 5.5
# Rhythm per shape: (air after a Tamil line, air after its gloss, air after the beat).
# Teaching shapes breathe; scenes run at something closer to speed.
RHYTHM = {
    "machine":   (0.9, 0.7, 1.4),
    "inventory": (1.0, 0.8, 1.6),
    "scene":     (0.6, 0.0, 0.9),
    "eavesdrop": (0.7, 0.0, 1.1),
    "lore":      (0.8, 0.0, 1.0),
}
# The visit in the order he will live it — the `room` spine's ordering, and the
# same order as the campaign table in progress/profile.md.
REGISTER_ORDER = ["social", "faq", "mil-table", "antifreeze", "public", "gossip", "zinger"]


# ── Item selection: the ranked set and beyond ───────────────────────────────


def inventory_hosts(lexicon: dict) -> dict:
    """root -> the phrases that appear to contain it. THE 2026-08-09 FINDING as a
    selector: his gap is not vocabulary and not reps, it is INVENTORY — he holds
    parts and does not know they are parts (வாழ்த்துக்கள் owned for two years and
    read as one phrase; நாள் sitting unnoticed inside நாளைக்கு).

    THE MATCH IS ON THE PULLI-STRIPPED STEM, not the bare key, and that is the
    whole difference between a working detector and a decorative one. A citation
    form ends in the pulli (நாள்); inside a longer word the same consonant takes a
    different vowel sign instead (நாளைக்கு, ரொம்ப நாளாச்சு), so a plain substring
    test matches NEITHER. Measured on the finding's own three examples, naive
    matching finds 1 of 3 hosts for நாள் — it misses the exact two phrases the
    session was about. Stripping the trailing ் finds all three.

    Substring matching is PROPOSAL ONLY and over-fires in the other direction: the
    same technique logged நீ at 17 reps because it is inside நீங்க (`probe_hit`,
    2026-07-26); டீ inside சாப்டீங்களா? is the same accident, and stemming widens
    the net rather than narrowing it. So Python offers candidates and the
    sheet-writer is told to DROP the coincidences — mechanism proposes, meaning
    disposes. A false candidate costs one dropped beat; a missed one costs the
    lesson."""
    singles = [k for k in lexicon
               if " " not in k and not k.startswith("frame:") and len(k) >= 3]
    out = {}
    for root in singles:
        stem = root.rstrip("்")          # ் — the vowel-less marker
        hosts = [k for k in lexicon
                 if k != root and stem in k and not k.startswith("frame:")]
        if len(hosts) >= 2:
            out[root] = hosts[:5]
    return out


def _rank(spine: str, hosts: dict):
    """Ordering per spine. Lower sorts first. Every spine puts the items he
    cannot yet fire ahead of the ones already cold — a cold word is not drilled
    again, it is just used (FOCUS_SIZE law, suggest_targets.py)."""
    unfired = {"none": 0, "hinted": 1, "cold": 2}

    def key(r):
        prod = unfired.get(r["production"], 3)
        if spine == "machines":
            return (0 if r["type"] == "pattern" else 1, 0 if r["register"] else 1, prod)
        if spine == "inventory":
            return (0 if r["word"] in hosts else 1, -len(hosts.get(r["word"], [])), prod)
        reg = r["register"]
        return (0 if reg else 1,
                REGISTER_ORDER.index(reg) if reg in REGISTER_ORDER else len(REGISTER_ORDER),
                prod)
    return key


def build_pool(spine: str, payload: list[str]) -> list[dict]:
    """The whole lexicon is in scope, not a seven-day window. `render_soak`'s
    `week_payload` asks "what did he touch this week" — the right question for a
    ten-minute loop and the wrong one for a tape that has to carry the ranked set
    AND beyond it ("everything in our deck and beyond somewhere in that",
    2026-08-10 — said of the deck, and the ranked registers are what it left).

    IN SCOPE IS NOT THE SAME AS USABLE, and this takes only what the spine's shape
    can actually teach from (`SPINE_QUALIFIES`). It used to take a requested SIZE
    instead, computed backwards from `--minutes`, which meant a longer ask silently
    bought worse items: at 45 minutes the inventory spine wanted 69 roots and the
    lexicon holds 27 with hosts, so 42 movements would have inventoried words with
    nothing inside them. The length now falls out of the material."""
    lexicon = load_json(LEXICON_PATH) or {}
    hosts = inventory_hosts(lexicon)
    rows = [{"word": k,
             "gloss": rec.get("gloss", ""),
             "production": rec.get("production", "none"),
             "direction": rec.get("direction", ""),
             "type": rec.get("type", ""),
             "register": rec.get("register", ""),
             "hosts": hosts.get(k, [])}
            for k, rec in lexicon.items()]
    rows.sort(key=_rank(spine, hosts))
    # The commissioned words lead whatever the ordering turned up — a payload the
    # lane ignores can never satisfy the order that dispatched it, and re-dispatches
    # forever (the 2026-07-23 M72/M73/M74 loop). A commissioned word is aired even if
    # it does not qualify: the order outranks the shape's preference.
    want = canon_payload(payload)
    fits = SPINE_QUALIFIES[spine]
    head = [r for r in rows if r["word"] in want]
    return head + [r for r in rows if r["word"] not in want and fits(r)]


# ── The plan ────────────────────────────────────────────────────────────────

def movement_count(minutes: float) -> int:
    """The CEILING `--minutes` implies — how many movements could fit, not how
    many there are. The material decides the second number (`movements_for`)."""
    return max(4, round((minutes - CLOSING_LAP_MIN) / MOVEMENT_MIN))


def pool_size(spine: str, count: int) -> int:
    """Items needed to cover `count` movements — deliberately sized for one
    movement FEWER than planned. The render stops on the measured clock, so a
    tape whose speech ran long drops its last movement; sizing short means that
    movement was a repeat, never a word's only airing."""
    cad = CADENCES[spine]
    return sum(ITEMS[cad[i % len(cad)]] for i in range(max(1, count - 1))
               if cad[i % len(cad)] not in RECALL_SHAPES)


def movements_for(spine: str, items: int) -> int:
    """The movements it takes to air `items` once — `pool_size` run backwards.
    A TAPE IS AS LONG AS ITS MATERIAL (Andrew, 2026-08-10, choosing this over
    padding to a round number). `--minutes` caps this; it never inflates it.
    The +1 airs the last slot, which `pool_size` deliberately sizes short of."""
    return next((c for c in range(4, 200) if pool_size(spine, c) >= items), 200) + 1


# What each spine's LEAD SHAPE actually needs of an item, which is what bounds an
# honest tape. Sorting alone does not bound it: `_rank` puts the qualifying items
# first but the pool then takes whatever fills the requested size, so asking for a
# longer tape used to reach past the material into items the shape cannot use — a
# root with no hosts is nothing to inventory, a chunk is no machine to run. These
# predicates are the same conditions `_rank` sorts on, read as a floor.
SPINE_QUALIFIES = {"inventory": lambda r: bool(r["hosts"]),
                   "machines": lambda r: (r["type"] == "pattern"
                                          or r["word"].startswith("frame:")),
                   "room": lambda r: bool(r["register"])}


def plan_movements(pool: list[dict], spine: str, count: int) -> list[dict]:
    """Round-robin the pool through the cadence: coverage first, recurrence
    second. The cursor wraps, so movements past the pool's length revisit early
    items instead of starving — that is the soak, and it is why this reads as a
    loop rather than a list.

    INVARIANT (smoke s57): a recall movement only ever names items that an
    earlier movement already taught. That is the mechanism behind "I can mostly
    understand" — a scene cannot reach for a word the tape has not yet given him."""
    cad = CADENCES[spine]
    plan: list[dict] = []
    taught: list[dict] = []
    cursor = 0
    for i in range(count):
        shape = cad[i % len(cad)]
        n = ITEMS[shape]
        if shape in RECALL_SHAPES:
            items = taught[-n:] if taught else []
        else:
            items = [pool[(cursor + j) % len(pool)] for j in range(min(n, len(pool)))]
            cursor += n
            taught.extend(items)
        plan.append({"shape": shape, "items": items})
    return plan


# ── The sheets: one small call per movement ─────────────────────────────────

# The movement mandates live in mandates.py (2026-08-10) — prompt canon, not lane
# machinery. Re-exported here so every existing reader keeps its import path.
from mandates import BASE_MANDATE, SHAPE_CLAUSES  # noqa: E402



def write_movement(mv: dict, spine: str) -> dict:
    """One movement, one small call. The whole tape is never in a model's context —
    twelve 600-token calls succeed where one 15,000-token script does not."""
    persona = (BASE / "protocol" / "persona.md").read_text(encoding="utf-8")
    menu = "\n".join(
        f"- {i['word']} — {i['gloss'] or '[no gloss]'}"
        + (f"  HOSTS: {', '.join(i['hosts'])}" if i["hosts"] else "")
        for i in mv["items"])
    mandate = f"{BASE_MANDATE}\n{SHAPE_CLAUSES[mv['shape']]}"
    sheet = ask_json(f"{persona}\n\n---\n\n{mandate}",
                     f"THE TAPE'S SPINE: {spine}\n\nITEMS FOR THIS MOVEMENT:\n{menu}",
                     MOVEMENT_SCHEMA)
    sheet["beats"] = [b for b in sheet.get("beats", [])
                      if (b.get("ta") or "").strip() or (b.get("en") or "").strip()]
    return sheet


# ── The render: Python owns every second ────────────────────────────────────

def silence(seconds: float) -> bytes:
    return SILENCE_FRAME * int(seconds * SILENCE_PER_SEC)


def movement_voices(n: int) -> tuple[str, str]:
    """Two fresh character voices per movement, alternating which gender leads.
    Anna and the eavesdrop aunty stay pinned (an ear tracks a speaker); everyone
    else rotates, because thirty voices are free and sameness is the complaint."""
    male = _CHIRP_POOL_MALE[n % len(_CHIRP_POOL_MALE)]
    female = _CHIRP_POOL_FEMALE[n % len(_CHIRP_POOL_FEMALE)]
    return (female, male) if n % 2 else (male, female)


class Tape:
    """The accumulating tape, and the only thing that knows what time it is."""

    def __init__(self, tmp: str):
        self.audio = bytearray()
        self.tmp = tmp
        self.cache: dict[tuple[str, str], bytes] = {}
        self.idx = 0
        self.spoken: list[str] = []      # every Tamil line that actually played

    async def say(self, text: str, voice: str) -> bytes:
        """Cached per (line, voice) — a long-haul tape repeats lines by design, and
        re-synthesising an identical segment is money and latency for one result."""
        key = (text, voice)
        if key not in self.cache:
            self.idx += 1
            f = await generate_segment_google(clean_for_tts(text), voice, self.idx, self.tmp)
            self.cache[key] = get_raw_mp3_frames(f)
            os.remove(f)
        return self.cache[key]

    async def add(self, text: str, voice: str, gap: float, tamil: bool = False):
        self.audio.extend(await self.say(text, voice))
        if tamil:
            self.spoken.append(text)
        self.audio.extend(silence(gap))

    def minutes(self, path: Path) -> float:
        """MEASURED, never estimated from byte count: speech frames are far larger
        than SILENCE_FRAME, so a byte-ratio guess reads ~30% short (2026-07-23)."""
        path.write_bytes(self.audio)
        from rebuild_rss import audio_duration
        return (audio_duration(str(path)) or 0) / 60


SCRIPTS_DIR = BASE / "content" / "scripts"
# Who each beat is voiced by, for the written page. The tape knows this as a voice
# id; a reader needs the ROLE, and "a"/"b" on the page is not a story.
WHO = {"a": "FIRST", "b": "SECOND"}


def write_script(mp3: Path, spine: str, measured: float, sheets: list[tuple],
                 spoken: list[str]) -> Path:
    """The written story, saved beside the audio (2026-08-10, Andrew: "I want the
    scripts stored in github").

    THE SHEETS USED TO BE THROWN AWAY. `write_movement` handed each one to the
    renderer and dropped it, so a finished tape existed only as an mp3 and the
    source text sent to the TTS was unrecoverable — not in a log, not on disk.
    Three tapes shipped that way before anyone looked for the words. Every other
    lane keeps its script; this one publishes prose nobody can read, quote, correct,
    or diff against the next render.

    WRITTEN FROM THE SHEETS THAT ACTUALLY PLAYED, not from the plan: the tape stops
    on the measured clock, so the tail of a plan may never have been rendered, and a
    script naming movements that never aired is the same lie in reverse. The closing
    lap is written out too — it is a third of the audio."""
    lines = [f"# Long-haul — {spine} · {datetime.now():%Y-%m-%d}", "",
             "<!-- GENERATED by scripts/render_longhaul.py — this is the source text",
             "     sent to the TTS, not a transcript. It is the story as written.",
             f"     AUDIO: published_audio/{mp3.name}",
             f"     MEASURED {measured:.1f} min over {len(sheets)} movements. -->", ""]
    for n, (mv, sheet) in enumerate(sheets, 1):
        lines += [f"## {n}. {mv['shape']} — {sheet.get('frame') or '(no frame line)'}", ""]
        if sheet.get("frame"):
            lines += [f"**ANNA:** {sheet['frame']}", ""]
        for beat in sheet["beats"]:
            ta, en = (beat.get("ta") or "").strip(), (beat.get("en") or "").strip()
            who = WHO.get(beat.get("who"), "ANNA") if mv["shape"] == "scene" else \
                ("AUNTY" if mv["shape"] == "eavesdrop" else "ANNA")
            if ta:
                lines.append(f"**{who}:** {ta}")
            if en:
                lines.append(f"> {en}" if ta else f"**{who}:** {en}")
            lines.append("")
    if spoken:
        lines += ["## closing lap — same sounds, one more lap", ""]
        lines += [f"**ANNA:** {l}" for l in dict.fromkeys(spoken)] + [""]
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SCRIPTS_DIR / f"{mp3.stem}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def render_movement(tape: Tape, mv: dict, sheet: dict, n: int):
    """The soak law on the teaching shapes — Tamil FIRST (the sound before the
    meaning), the gloss once, then Tamil again to settle. Scenes and eavesdrops
    get none of that: they run once, at speed, because their whole job is that he
    follows something he was handed five minutes ago."""
    after_ta, after_en, after_beat = RHYTHM[mv["shape"]]
    voice_a, voice_b = movement_voices(n)
    if sheet.get("frame"):
        await tape.add(sheet["frame"], ANNA_VOICE, 1.2)
    for beat in sheet["beats"]:
        ta, en = (beat.get("ta") or "").strip(), (beat.get("en") or "").strip()
        if mv["shape"] == "lore":
            if en:
                await tape.add(en, ANNA_VOICE, after_ta if ta else after_beat)
            if ta:
                await tape.add(ta, ANNA_VOICE, after_beat, tamil=True)
            continue
        if mv["shape"] == "eavesdrop":
            await tape.add(ta, EAVESDROP_VOICE, after_beat, tamil=True)
            continue
        if mv["shape"] == "scene":
            await tape.add(ta, voice_b if beat.get("who") == "b" else voice_a,
                           after_beat, tamil=True)
            continue
        # machine / inventory — the soak rhythm
        await tape.add(ta, ANNA_VOICE, after_ta, tamil=True)
        if en:
            await tape.add(en, ANNA_VOICE, after_en)
        await tape.add(ta, ANNA_VOICE, after_ta)
        await tape.add(ta, ANNA_VOICE, after_beat)


async def render(plan: list[dict], spine: str, out: Path, minutes: float,
                 writer=write_movement) -> tuple[float, int, list[str], list[tuple]]:
    """Sheets are written JUST IN TIME, one movement ahead of the tape head, and
    the tape stops when the measured clock reaches the target. Nothing is written
    that does not play.

    The played sheets come back out (2026-08-10) so the written story can be saved
    beside the audio. They used to be dropped where they were used, which is why
    three tapes shipped with no readable source text anywhere."""
    tmp = tempfile.mkdtemp(prefix="longhaul_")
    tape = Tape(tmp)
    sheets: list[tuple] = []
    try:
        for n, mv in enumerate(plan):
            elapsed = tape.minutes(out)
            if elapsed >= minutes:
                break
            print(f"   [{n+1}/{len(plan)}] {mv['shape']:<9} "
                  f"({elapsed:.1f}/{minutes:.0f} min)")
            sheet = writer(mv, spine)
            await render_movement(tape, mv, sheet, n)
            sheets.append((mv, sheet))
        # The closing lap: the tape's own spine, Tamil only, no glosses, one pass.
        # It is the pay-off of a third listen AND the bridge back to the top when
        # the file loops. A bare Tamil run brushes against "No Standalone Lists"
        # (constitution rule 4) and is allowed for the same reason the soak loop's
        # cluster echo is: these lines were all placed in context earlier on this
        # same tape, so it is a recap, not a list taught from cold.
        #
        # Both spoken lines stay clear of rule 6 — nothing about where he is, what
        # he is doing, or how tired he might be. An earlier draft signed off with
        # "sleep if you can", which is precisely the ban.
        if tape.spoken:
            await tape.add("Same sounds, one more lap.", ANNA_VOICE, 1.5)
            for line in dict.fromkeys(tape.spoken):
                await tape.add(line, ANNA_VOICE, 1.0)
        await tape.add("That's the lot.", ANNA_VOICE, 0.5)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return tape.minutes(out), len(sheets), tape.spoken, sheets


# ── CLI ─────────────────────────────────────────────────────────────────────

def audible(pool: list[dict], spoken: list[str], sheets: list[tuple]) -> list[str]:
    """What this tape actually delivered (2026-07-26 ledger law: only what was
    AUDIBLE is claimed). The tape stops on the clock, so the tail of a plan may
    never have played, and stamping the whole pool would book words never spoken.

    A FRAME IS NEVER ITS OWN NAME. Substring-matching `spoken` is right for a
    chunk — வந்துட்டேன் is said, so it is in the audio — and structurally impossible
    for `frame:quote-nu`, which is a label for a PATTERN realised across a
    movement's beats and appears in the audio exactly never. The machines tape
    taught 26 frames and stamped 0 (2026-08-10), so the ledger recorded a
    28-minute tape as having delivered nothing and the drain would re-dispatch
    every one of them.

    So a frame is claimed when the movement holding it PLAYED and produced beats —
    which is the same evidence, read at the level the item actually exists at. Not
    the plan: `sheets` carries only movements that rendered."""
    blob = " ".join(spoken)
    ran = {i["word"] for mv, sheet in sheets if sheet.get("beats") for i in mv["items"]}
    return [i["word"] for i in pool
            if (i["word"] in ran if i["word"].startswith("frame:") else i["word"] in blob)]


def longhaul_brief() -> tuple[str | None, list[str]]:
    """The standing soak order, when it is addressed to THIS lane -> (focus, payload).
    Same contract every lane keeps: read the order, stamp it delivered, or the
    session-open drain dispatches a second dose for work already done."""
    order = (load_json(BASE / "progress" / "learner.json") or {}).get("soak_order") or {}
    if (order.get("channel") or "episode") != "longhaul":
        return None, []
    return (order.get("focus") or "").strip() or None, [w for w in order.get("payload") or [] if w]


def expected_min(count: int) -> float:
    """What `count` movements should measure, from the calibrated per-movement
    figure. A PREDICTION, printed so the measured number has something to be
    checked against — the render still stops on the real clock."""
    return count * MOVEMENT_MIN + CLOSING_LAP_MIN


def describe(plan: list[dict], pool: list[dict], minutes: float):
    est = expected_min(len(plan))
    capped = est > minutes
    print(f"\nPLAN — {len(plan)} movements, ~{est:.0f} min expected"
          + (f", CAPPED at the {minutes:.0f} min ceiling" if capped
             else f" (under the {minutes:.0f} min ceiling — this spine's material)"))
    for n, mv in enumerate(plan, 1):
        words = ", ".join(i["word"] for i in mv["items"]) or "(nothing taught yet)"
        print(f"  {n:>2}. {mv['shape']:<9} {words[:88]}")
    print(f"\nPOOL — {len(pool)} items"
          f" · {sum(1 for i in pool if i['register'])} ranked"
          f" · {sum(1 for i in pool if i['production'] == 'none')} never fired"
          f" · {sum(1 for i in pool if i['hosts'])} with inventory hosts")


def main():
    ap = argparse.ArgumentParser(description="A 40-60 minute press-once listening tape")
    ap.add_argument("--spine", choices=sorted(CADENCES), default="inventory",
                    help="the tape's centre of gravity (default: inventory)")
    ap.add_argument("--minutes", type=float, default=45,
                    help="CEILING on measured length; a spine with less material stops sooner (default 45)")
    ap.add_argument("--plan-only", action="store_true",
                    help="print the movement plan and stop — no network at all")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan + write the first sheet; no TTS, no publish")
    ap.add_argument("--no-publish", action="store_true",
                    help="render only; skip RSS/commit/push/notify")
    args = ap.parse_args()

    load_env(BASE / ".env")
    focus, payload = longhaul_brief()
    pool = build_pool(args.spine, payload)
    if not pool:
        sys.exit(f"No material for the '{args.spine}' spine — nothing to build a tape from.")
    # THE MATERIAL SETS THE LENGTH AND `--minutes` ONLY CAPS IT (Andrew, 2026-08-10,
    # asked to choose and chose the honest length over padding to a round number).
    # +2 of slack so the measured clock, not an exhausted plan, is what ends a tape
    # that is genuinely long enough.
    count = min(movements_for(args.spine, len(pool)), movement_count(args.minutes) + 2)
    plan = plan_movements(pool, args.spine, count)
    print(f"1. plan… (spine: {args.spine}"
          f"{f' · {len(payload)} commissioned' if payload else ''}"
          f"{' · FOCUS: ' + focus if focus else ''})")
    describe(plan, pool, args.minutes)

    if args.plan_only:
        return
    if args.dry_run:
        print("\n2. first sheet…")
        print(json.dumps(write_movement(plan[0], args.spine), ensure_ascii=False, indent=2))
        return

    reason = google_credentials_ready()
    if reason:
        print(f"⏭️  Skipping render — {reason}. This host cannot produce audio.")
        sys.exit(EXIT_NOT_CONFIGURED)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    mp3 = LONGHAUL_DIR / f"longhaul_{args.spine}_{stamp}.mp3"
    mp3.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n2. render… (target {args.minutes:.0f} min)")
    measured, played, spoken, sheets = asyncio.run(
        render(plan, args.spine, mp3, args.minutes))
    print(f"   rendered -> {mp3} ({measured:.1f} min, {played} movements)")
    # Written BEFORE the publish gate, so `--no-publish` still leaves the story on
    # disk: a local render is exactly when you want to read what it said.
    script = write_script(mp3, args.spine, measured, sheets, spoken)
    print(f"   script   -> {script}")
    # NOT a warning for stopping under `--minutes` — that is the honest length of
    # this spine's material and is the intended outcome. What is worth flagging is
    # the CALIBRATION drifting: the tape missing what its own movement count
    # predicted means MOVEMENT_MIN no longer describes the rhythm table.
    predicted = expected_min(played)
    if played and abs(measured - predicted) > max(3.0, predicted * 0.25):
        print(f"   ⚠ {measured:.1f} min against {predicted:.1f} predicted for {played} "
              f"movements — MOVEMENT_MIN ({MOVEMENT_MIN}) has drifted from the rhythm "
              f"table. Re-measure it; the tape itself is fine.")

    if args.no_publish:
        return

    print("3. publish…")
    delivered = audible(pool, spoken, sheets)
    print(f"   {len(delivered)}/{len(pool)} pool items audible on the tape")
    exposed = record_exposure(delivered)
    stamped = mark_soak_delivered("longhaul") if (focus or payload) else False
    subprocess.run([sys.executable, str(BASE / "scripts" / "rebuild_rss.py")],
                   cwd=BASE, check=True)
    commit_and_push([mp3, script, BASE / "rss.xml"]
                    + ([LEXICON_PATH] if exposed else [])
                    + ([BASE / "progress" / "learner.json"] if stamped else []),
                    f"Long-haul tape: {args.spine} ({measured:.0f} min)")
    print("4. notify…")
    pushed = push_to_phone(
        f"long-haul tape's up — {measured:.0f} min, {args.spine}. press once 🎧",
        jsdelivr_url(mp3))
    print(f"done — tape on the feed{' and the lock screen' if pushed else ''}.")


if __name__ == "__main__":
    main()
