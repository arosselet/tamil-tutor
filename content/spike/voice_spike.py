#!/usr/bin/env python3
"""
The voice-in spike — can a machine hear Andrew? A measurement, not a lane.

Usage:
    python content/spike/voice_spike.py refs      # Anna's reference renders, once
    python content/spike/voice_spike.py serve     # the recording sheet on localhost
    python content/spike/voice_spike.py grade     # every clip x four ears (PAID API)
    python content/spike/voice_spike.py report    # the evidence for the Oct 31 cut

A ONE-OFF, kept out of scripts/ on purpose (2026-10-23, Andrew): no budget, no
layer, no smoke case. It borrows a few helpers from scripts/ and owns nothing there.

WHY THIS EXISTS (2026-10-23, inbox drain, Andrew's ruling): the 07-09 decision parked
speech-in "on evidence, not desire" and asked for a spike before any machinery. The
July write-up of that spike was never found (not in the tree, not in an artifact, and
the transcripts before 09-20 are gone), so this is Rio's 10-21 reconstruction with the
two amendments on record: Andrew's play-button collection step and Rio's 10-22 grading
design, which Andrew approved.

THE TWO JOBS, two bars. CONVERSATION HEARING: recover what he MEANT from code-mixed
learner speech — this alone gates a live-Anna front end. COACHING HEARING: against a
known target, name what deviated — precision over recall, because a false flag on a
good take teaches him to ignore the coach. The test is of PRONUNCIATION, not his
grammar slips.

THE GROUND TRUTH IS WHAT HE DID (2026-10-23, Andrew). Every target row carries a guide
for the natural Coimbatore take and one or more WRONG variants, each with its own guide
and recorded as its own take; a variant's label is what the ear is judged against. The
variants come from the charter (protocol/dialect.md), her 07-31 ruling and the 09-01
"book Tamil" report, not from a quota. One consequence is worth knowing before reading
a report: natives mostly do not make the ல/ள and ர/ற distinctions, so a HARD trilled ற
is a wrong variant here (the "uncanny" sound) and Anna's reference over-articulates it.
On those rows he follows the written guide, not her voice.

THE CORPUS IS HIS VOICE. Each phrase plays Anna's correct render above its record
button; he records the natural take, then each wrong variant in his own mouth. Anna is never asked to fake a mispronunciation and no ear
is ever tested on a generated voice. Clips live under audio/spike/ — gitignored, on
purpose: a voice corpus does not belong in a public repo.

THE FAILURE THE WRONG TAKES EXIST TO CATCH — LAUNDERING. If a deliberately wrong take
transcribes identical to the good one, the ear is normalising him toward the target,
and nothing it writes can be treated as evidence of what he said. `report` checks every
variant against the good take, per condition, and says so loudly.

THE SILENT NO-OP, answered: a grade run that found no clips, or a condition that never
ran, would print an empty report that reads like "nothing went wrong". `report` lists
every clip the sheet expects and every (clip, condition) with no grade, so absence is
visible, and it refuses to call a laundering check passed on a pair with a take missing.

The API path is the only one: `claude -p` cannot take audio, so `hear` calls the
writer's OpenRouter model itself, on any host. 54 takes x 4 conditions is ~216 flash
calls — cents, and announced before it starts.
"""

import argparse
import base64
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from language import ANNA_VOICE

SHEET, PAGE = HERE / "voice_in.json", HERE / "recorder.html"
OUT = BASE / "audio" / "spike"
REFS, CLIPS, GRADES = OUT / "ref", OUT / "clips", OUT / "grades.jsonl"
PORT = 8765

# The ear (Rio's 10-22 grading design, Andrew approved). One base and four
# conditions, so the PROMPT is the variable under test. COLD is the control;
# nothing live would ever listen that way.
SPIKE_EAR_MANDATE = """You will hear one short voice clip from Andrew, an adult English speaker learning spoken Coimbatore (Kongu) colloquial Tamil, who code-mixes English into it.
{condition}
Return ONLY JSON: {{"transcript": "<what was SAID, Tamil in Tamil script, English in English>", "romanized": "<the same line in English phonetics>", "meaning": "<what he meant, in English>", "deviations": ["<each sound that departed from natural Kongu speech, as heard>"], "confidence": "high|medium|low"}}"""

SPIKE_CONDITIONS = {
    "cold": "Transcribe exactly what you hear.",
    "learner": "Write down his errors exactly as spoken — a mispronounced word stays mispronounced in the transcript, even where you can guess the word he wanted.",
    "target": "He was trying to say: {say} ({roman}, \"{en}\"). Write what he actually said, then name every sound that deviated from that target. A take with no deviation gets an empty list.",
    "context": "This is a lesson. Anna just asked him: \"{ask}\". Write what he said and what he meant by it.",
}


def takes(p: dict) -> list[str]:
    """A target row is its good take plus EVERY wrong variant — the laundering check
    compares each variant against the good one, so a row needs all of them."""
    return ["good"] + [w["id"] for w in p["wrong"]] if p["kind"] == "target" else ["said"]


def truth(p: dict, take: str) -> str:
    """What he actually did on this take — the ground truth an ear is judged against."""
    return {w["id"]: w["label"] for w in p.get("wrong", [])}.get(take, "natural, as guided")


def load_sheet(path: Path = SHEET) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["phrases"]


def expected_clips(sheet: list[dict]) -> list[str]:
    return [f"{p['id']}.{t}" for p in sheet for t in takes(p)]


def condition_prompt(phrase: dict, condition: str) -> str:
    return SPIKE_EAR_MANDATE.format(condition=SPIKE_CONDITIONS[condition].format(**phrase))


# ── refs ─────────────────────────────────────────────────────────────────────

def cmd_refs(_args):
    from render_demo import synth   # lazy: the Google client is only for this command
    REFS.mkdir(parents=True, exist_ok=True)
    for p in load_sheet():
        out, said = REFS / f"{p['id']}.mp3", REFS / f"{p['id']}.txt"
        # A row whose words changed keeps its id, so the render is keyed on the TEXT.
        if not out.exists() or not said.exists() or said.read_text(encoding="utf-8") != p["say"]:
            out.write_bytes(synth(p["say"], ANNA_VOICE))
            said.write_text(p["say"], encoding="utf-8")
            print(f"   rendered {out.name}  {p['roman']}")
    print(f"✅ references in {REFS}")


# ── serve ────────────────────────────────────────────────────────────────────

class Sheet(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes = b"", kind: str = "text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.path = self.path.split("?")[0]   # the page cache-busts its replays
        if self.path == "/":
            return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if self.path == "/sheet":
            have = sorted(f.stem for f in CLIPS.glob("*.wav")) if CLIPS.exists() else []
            body = {"phrases": [{**p, "takes": takes(p)} for p in load_sheet()], "have": have}
            return self._send(200, json.dumps(body, ensure_ascii=False).encode(), "application/json")
        m = re.fullmatch(r"/(ref|clip)/([\w.]+)\.(mp3|wav)", self.path)
        f = m and (REFS if m[1] == "ref" else CLIPS) / f"{m[2]}.{m[3]}"
        if f and f.exists():
            return self._send(200, f.read_bytes(), "audio/mpeg" if m[3] == "mp3" else "audio/wav")
        self._send(404, b"not found")

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        m = re.fullmatch(r"/(clip|meant)/(\w+)(?:/(\w+))?", self.path)
        rows = {p["id"]: p for p in load_sheet()}
        if not m or m[2] not in rows:
            return self._send(400, b"unknown phrase")
        CLIPS.mkdir(parents=True, exist_ok=True)
        if m[1] == "meant":
            (CLIPS / f"{m[2]}.meant.txt").write_bytes(body)
        elif m[3] in takes(rows[m[2]]) and body[:4] == b"RIFF":
            (CLIPS / f"{m[2]}.{m[3]}.wav").write_bytes(body)
        else:
            return self._send(400, b"wrong take for this row, or not a WAV")
        print(f"   saved {self.path}")
        self._send(200, b"ok")


def cmd_serve(_args):
    missing = [p["id"] for p in load_sheet() if not (REFS / f"{p['id']}.mp3").exists()]
    if missing:
        print(f"   ⚠ no reference render for {', '.join(missing)} — run `refs` first; "
              f"those rows will have nothing to play")
    print(f"🎙  open http://localhost:{PORT}/ — clips land in {CLIPS}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Sheet).serve_forever()


# ── grade ────────────────────────────────────────────────────────────────────

def hear(wav: bytes, prompt: str) -> dict:
    from openai import OpenAI
    from writer import (JSON_MODE, OPENROUTER_BASE, OPENROUTER_MODEL,
                        REASONING_BUDGET, budget, parse_llm_response)
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=OPENROUTER_MODEL, max_tokens=budget(600), response_format=JSON_MODE,
        extra_body=REASONING_BUDGET,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "input_audio", "input_audio": {
                "data": base64.b64encode(wav).decode(), "format": "wav"}}]}])
    return parse_llm_response(resp)


def load_grades(path: Path | None = None) -> list[dict]:
    path = path or GRADES   # read at call time, never bound at def time
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_grade(args):
    from publish import load_env
    from writer import OPENROUTER_MODEL
    load_env(BASE / ".env")
    rows = {p["id"]: p for p in load_sheet()}
    done = {(g["clip"], g["condition"]) for g in load_grades()}
    todo = [(c, cond) for c in expected_clips(rows.values()) for cond in SPIKE_CONDITIONS
            if (CLIPS / f"{c}.wav").exists() and (c, cond) not in done]
    print(f"   {len(todo)} calls on {OPENROUTER_MODEL} (PAID API — claude -p cannot hear)")
    with GRADES.open("a", encoding="utf-8") as log:
        for clip, cond in todo[:args.limit or None]:
            try:
                got = hear((CLIPS / f"{clip}.wav").read_bytes(),
                           condition_prompt(rows[clip.split(".")[0]], cond))
            except Exception as e:   # one bad call is a row, not a dead run
                got = {"error": f"{type(e).__name__}: {e}"[:300]}
            log.write(json.dumps({"clip": clip, "condition": cond,
                                  "model": OPENROUTER_MODEL, **got}, ensure_ascii=False) + "\n")
            log.flush()
            print(f"   {clip:9} {cond:8} {got.get('transcript') or got.get('error')}")


# ── report ───────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"[\s\W_]+", "", (s or "").lower())


def findings(sheet: list[dict], grades: list[dict]) -> dict:
    """The report's judgements, pure. `laundered`: (clip, condition) where a wrong
    take reads identical to the good one. `flagged` / `missed`: wrong takes the
    TARGET ear did / did not flag — whether what it named MATCHES the variant is read
    against `truth`, by a person, in the per-clip section. `false_flags`: good takes
    it flagged anyway. `ungraded`: (clip, condition) with no usable row."""
    by = {(g["clip"], g["condition"]): g for g in grades if not g.get("error")}
    out = {k: [] for k in ("laundered", "flagged", "missed", "false_flags", "ungraded")}
    for clip in expected_clips(sheet):
        out["ungraded"] += [(clip, c) for c in SPIKE_CONDITIONS if (clip, c) not in by]
    for p in (p for p in sheet if p["kind"] == "target"):
        good = f"{p['id']}.good"
        for w in p["wrong"]:
            wrong = f"{p['id']}.{w['id']}"
            for c in SPIKE_CONDITIONS:
                g, b = by.get((good, c)), by.get((wrong, c))
                if g and b and _norm(g.get("transcript")) == _norm(b.get("transcript")):
                    out["laundered"].append((wrong, c))
            if (b := by.get((wrong, "target"))):
                out["flagged" if b.get("deviations") else "missed"].append(wrong)
        if (g := by.get((good, "target"))) and g.get("deviations"):
            out["false_flags"].append(good)
    return out


def cmd_report(_args):
    sheet, grades = load_sheet(), load_grades()
    f = findings(sheet, grades)
    by = {(g["clip"], g["condition"]): g for g in grades if not g.get("error")}
    have = {c for c in expected_clips(sheet) if (CLIPS / f"{c}.wav").exists()}
    absent = [c for c in expected_clips(sheet) if c not in have]
    lines = [f"# Voice-in spike — evidence ({len(grades)} grade rows)", "",
             f"**Clips recorded:** {len(have)} of {len(have) + len(absent)}"
             + (f" — missing: {', '.join(absent)}" if absent else ""),
             f"**Ungraded (clip, condition):** {len(f['ungraded'])}", "",
             "## Laundering (a wrong take reads identical to the good one)",
             ", ".join(f"{k}/{c}" for k, c in f["laundered"]) or "none seen", "",
             "## Coaching ear (TARGET condition) — qualitative, never a percentage",
             f"- wrong takes it flagged: {', '.join(f['flagged']) or '—'}",
             f"- wrong takes it passed: {', '.join(f['missed']) or '—'}",
             f"- good takes it flagged anyway: {', '.join(f['false_flags']) or '—'}",
             "- whether a flag names the RIGHT deviation: read each against its truth below", "",
             "## Every clip, every ear", ""]
    for p in sheet:
        meant = CLIPS / f"{p['id']}.meant.txt"
        intent = meant.read_text(encoding="utf-8").strip() if meant.exists() else p["en"]
        lines.append(f"### {p['id']} · {p['roman']} — meant: {intent}")
        for take in takes(p):
            lines.append(f"**{take}** — truth: {truth(p, take)}")
            for c in SPIKE_CONDITIONS:
                g = by.get((f"{p['id']}.{take}", c))
                lines.append(f"- {c}: " + (
                    f"{g.get('transcript')} · \"{g.get('meaning')}\" · "
                    f"{'; '.join(g.get('deviations') or []) or 'no deviations'} "
                    f"({g.get('confidence')})" if g else "**NOT GRADED**"))
        lines.append("")
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:15]))
    print(f"\n✅ full report: {OUT / 'report.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The voice-in spike — measurement only")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refs"); sub.add_parser("serve"); sub.add_parser("report")
    g = sub.add_parser("grade")
    g.add_argument("--limit", type=int, default=0, help="stop after N calls (a probe)")
    a = ap.parse_args()
    {"refs": cmd_refs, "serve": cmd_serve, "grade": cmd_grade, "report": cmd_report}[a.cmd](a)
