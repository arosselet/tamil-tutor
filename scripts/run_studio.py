#!/usr/bin/env python3
"""
Studio dispatch — the agy (Gemini) writer + the local Python renderer.

The writer-only split (Andrew, 2026-07-09), tightened same day: agy runs each
studio pass as a SANDBOXED, PRINT-ONLY call — Director → Architect → Producer,
one agy invocation per pass, exactly the pipeline the protocol prescribes
(collapsing the three passes into one shot produced flat, off-canon scripts;
the isolated-pass probe was good). Gemini never writes a file, never runs a
command, never sees git: Python captures each pass's stdout, writes the three
artifacts, LINTS them deterministically, and hands the script to
render_audio.py — which owns TTS, registration, lexicon seeding, the feed,
and the commit exactly as in any other production run.

Exit 0 = episode rendered and published. Any other exit = the caller falls
back to the Claude studio subagent (.claude/agents/studio.md) — the
default/fallback contract. Failed artifacts stay in place, untracked, for
inspection (git clean removes them).

  python scripts/run_studio.py            # full: three passes, lint, render, publish
  python scripts/run_studio.py --dry-run  # passes + lint only; no render

Needs: agy on PATH (authenticated), GCP ADC for the render step.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows consoles and pipes default to cp1252, which can't carry Tamil — both
# this script's own prints and every captured subprocess stream (2026-07-15: the
# ticket capture crashed the reader thread before agy was even reached).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
SCRIPTS_DIR = BASE / "content" / "scripts"
LESSONS_DIR = BASE / "content" / "lessons"
CAPTIONS_DIR = BASE / "content" / "captions"
AUDIO_DIR = BASE / "published_audio"

AGY_MODEL = "Gemini 3.1 Pro (High)"   # pinned: the long-context writer
PASS_TIMEOUT_S = 900                  # 15 min per pass — each is one print turn

TAMIL_RE = re.compile(r"[஀-௿]")
SPEAKER_RE = re.compile(r"^\s*(?:\*\s*)?\*\*[^:]+:")
REQUIRED_TAGS = {"mission", "register", "dramatic_ingredient", "episode_form",
                 "new_words_landed"}

PREAMBLE = """\
You are ONE pass of the Studio pipeline (protocol/studio/studio.md) for the
Tamil learning repo in the current directory. You are print-only: PRINT your
artifact as your response. Write NO files, run NO commands, touch NO git —
Python persists your output and runs the next pass. You never address the
learner; the fourth wall stays up (protocol/studio/hosts.md).
"""

DIRECTOR = PREAMBLE + """
THIS PASS: the DIRECTOR. Read protocol/studio/director.md and follow it
exactly. Read progress/profile.md — its Calibration Notes are LAW — and the
soak-order in progress/learner.json. The ticket + scene spec below are
already computed; the spec is a GATE, not a suggestion.

{ticket}

PRINT the complete Master Lesson Plan and nothing else.
"""

ARCHITECT = PREAMBLE + """
THIS PASS: the ARCHITECT. Read protocol/studio/architect.md and follow it
exactly (including the Listenability Gate). Calibration from
progress/profile.md is LAW — Woven Thanglish: ENGLISH carries logistics and
scene-setting, Tamil carries the payload; density is an OUTPUT of the 95%
known-word coverage rule, never a target. Here is the Master Lesson Plan:

{plan}

PRINT the full episode script and nothing else — speaker lines as
`**Name:** text`, with [SFX] / [Pause] craft per the role file.
"""

PRODUCER = PREAMBLE + """
THIS PASS: the PRODUCER. Read protocol/studio/producer.md and
protocol/studio/dialect.md and follow them exactly: dialect transformation,
integrity checks (send-backs become fixes you make yourself here), and the
sidecar. Two hard rules the dialect pass must not violate:
- PAYLOAD IS VERBATIM: every deck/payload item the sidecar claims must appear
  in the script EXACTLY as seeded — the learner drills these precise forms;
  a mutated anchor line poisons the rep (Python rejects the script on any
  mismatch).
- The polite -ங்க attaches to imperatives and second person only — NEVER to
  first-person statements (இருக்கேன், இருப்போம் stay unchanged).
Here is the Architect's draft:

{draft}

PRINT exactly two fenced blocks and nothing else:
1. a ```markdown fence with the final production script
2. a ```json fence with the .tags.json sidecar — "mission": {n}, schema per
   the existing content/scripts/*.tags.json files
"""

CAPTIONS = PREAMBLE + """
THIS PASS: the CAPTION SHEET (captioned soak — the follow-along the learner
reads while listening; see protocol/studio/studio.md step 4). Below is the
FINAL production script. Transcribe it into a markdown sheet:
- Open with `# Captions — Ep {n} · <title>` and this blockquote how-to:
  "**Follow-along sheet** — the line as *sound* · what it means." /
  "Passes 1–2: listen with this open. Pass 3+: put it away — **blind is the
  win.**"
- Then ONE blockquote per spoken line, two `<br>`-separated rows:
  `**<speaker letter/name>:** *<the full line as SOUND — English words as
  written, Tamil words in English phonetic; NO Tamil script anywhere>*`
  then the plain-English meaning.
- Skip the meaning row when a line is already mostly English.
- Keep [SFX]/[Pause] as short italic position cues between blockquotes.

{script}

PRINT one ```markdown fence with the caption sheet and nothing else.
"""


def next_mission() -> int:
    nums = [int(m.group(1)) for p in SCRIPTS_DIR.glob("tier2_mission*.md")
            if (m := re.match(r"tier2_mission(\d+)\.md$", p.name))]
    return max(nums, default=0) + 1


def episode_paths(n: int) -> dict[str, Path]:
    return {"brief": LESSONS_DIR / f"tier2_mission{n}_brief.md",
            "script": SCRIPTS_DIR / f"tier2_mission{n}.md",
            "tags": SCRIPTS_DIR / f"tier2_mission{n}.tags.json",
            "captions": CAPTIONS_DIR / f"tier2_mission{n}.md"}


def agy_print(label: str, prompt: str) -> str | None:
    """One sandboxed, print-only pass. Returns stdout, or None on failure."""
    print(f"   [{label}] agy ({AGY_MODEL})…")
    try:
        r = subprocess.run(
            ["agy", "--model", AGY_MODEL, "--sandbox", "--dangerously-skip-permissions",
             "--print-timeout", "14m", "--print", prompt],
            cwd=BASE, timeout=PASS_TIMEOUT_S, capture_output=True,
            encoding="utf-8", errors="replace")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"   ✗ {label}: {e}")
        return None
    out = (r.stdout or "").strip()
    if r.returncode != 0 or len(out) < 200:
        print(f"   ✗ {label}: exit {r.returncode}, {len(out)} chars — "
              f"{(r.stderr or out)[-200:]}")
        return None
    print(f"   [{label}] {len(out)} chars")
    return out


def fenced_block(text: str, lang: str) -> str | None:
    m = re.findall(rf"```{lang}\s*\n(.*?)```", text, re.DOTALL)
    return m[-1].strip() if m else None


def write_episode(n: int) -> bool:
    """Run the three passes; persist the three artifacts. Python is the only
    thing that touches disk."""
    ticket = subprocess.run([sys.executable, str(BASE / "scripts" / "suggest_targets.py")],
                            capture_output=True, encoding="utf-8", errors="replace",
                            cwd=BASE, check=True).stdout
    plan = agy_print("Director", DIRECTOR.format(ticket=ticket))
    if not plan:
        return False
    draft = agy_print("Architect", ARCHITECT.format(plan=plan))
    if not draft:
        return False
    final = agy_print("Producer", PRODUCER.format(draft=draft, n=n))
    if not final:
        return False

    script = fenced_block(final, "markdown")
    tags = fenced_block(final, "json")
    if not script or not tags:
        print("   ✗ Producer output missing the markdown/json fences")
        return False
    paths = episode_paths(n)
    paths["brief"].parent.mkdir(parents=True, exist_ok=True)
    paths["brief"].write_text(plan + "\n", encoding="utf-8")
    paths["script"].write_text(script + "\n", encoding="utf-8")
    paths["tags"].write_text(tags + "\n", encoding="utf-8")

    # Caption sheet — companion, never a gate: a failed pass warns and the
    # episode still ships (the feed simply carries no caption link for it).
    sheet_out = agy_print("Captions", CAPTIONS.format(n=n, script=script))
    sheet = fenced_block(sheet_out, "markdown") if sheet_out else None
    if sheet:
        paths["captions"].parent.mkdir(parents=True, exist_ok=True)
        paths["captions"].write_text(sheet + "\n", encoding="utf-8")
    else:
        print("   ⚠ caption sheet pass failed — episode ships without captions")
    return True


def git_dirty() -> set[str]:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=BASE,
                         capture_output=True, text=True).stdout.splitlines()
    return {ln[3:].strip() for ln in out if ln[3:].strip()}


def intercept_english_share(script: str) -> float:
    """Latin-word share of the spoken lines — the Woven-Thanglish tripwire.
    Density is an OUTPUT, never a target (profile.md), so this is not a dial:
    it only trips on the observed failure mode (2026-07-09 one-shot sample:
    near-pure-Tamil dialogue, which violates 'avoid pure Tamil blocks' and
    can't be holding 95% live comprehension)."""
    spoken = "\n".join(ln for ln in script.splitlines() if SPEAKER_RE.match(ln))
    latin = len(re.findall(r"[A-Za-z]+", spoken))
    tamil = len(re.findall(r"[஀-௿]+", spoken))
    return latin / (latin + tamil) if latin + tamil else 0.0


MIN_ENGLISH_SHARE = 0.15  # tripwire, not a dial — well under every healthy episode


def lint(n: int, baseline: set[str] | None = None) -> list[str]:
    """Deterministic post-checks — every rule here earned its place from an
    observed failure mode (2026-07-09: the probe broke the fourth wall by
    naming the learner; the one-shot sample wrote near-pure Tamil)."""
    problems = []
    paths = episode_paths(n)
    for kind, p in paths.items():
        if not p.exists() or p.stat().st_size == 0:
            problems.append(f"{kind} missing or empty: {p.relative_to(BASE)}")
    if problems:
        return problems

    try:
        tags = json.loads(paths["tags"].read_text(encoding="utf-8"))
        missing = REQUIRED_TAGS - set(tags)
        if missing:
            problems.append(f"tags.json missing keys: {sorted(missing)}")
        elif tags.get("mission") != n:
            problems.append(f"tags.json mission {tags.get('mission')} != {n}")
    except json.JSONDecodeError as e:
        problems.append(f"tags.json unparseable: {e}")

    script = paths["script"].read_text(encoding="utf-8")
    if len(script) < 1000:
        problems.append(f"script suspiciously short ({len(script)} chars)")
    if not TAMIL_RE.search(script):
        problems.append("script contains no Tamil script (payload must be Tamil-script)")
    if not any(SPEAKER_RE.match(ln) for ln in script.splitlines()):
        problems.append("script has no **Speaker:** lines — renderer can't voice it")
    else:
        share = intercept_english_share(script)
        if share < MIN_ENGLISH_SHARE:
            problems.append(
                f"Woven-Thanglish tripwire: only {share:.0%} English in spoken lines "
                f"(floor {MIN_ENGLISH_SHARE:.0%}) — near-pure Tamil can't hold live comprehension")
    learner = (json.loads((BASE / "progress" / "learner.json").read_text(encoding="utf-8"))
               .get("learner") or "")
    if learner and re.search(rf"\b{re.escape(learner)}\b", script, re.IGNORECASE):
        problems.append(f"fourth wall: script names the learner ({learner})")
    if re.search(r"^\s*(?:\*\s*)?\*\*\s*(?:the\s+)?(?:learner|student)\b", script,
                 re.IGNORECASE | re.MULTILINE):
        problems.append("fourth wall: a speaker is labeled LEARNER/STUDENT — "
                        "self-insert characters break the podcast's own world")

    # Payload fidelity — the check both 2026-07-09 bad samples earned: every
    # lexicon item the sidecar claims must appear in the script VERBATIM
    # (frame:… keys are slot templates and exempt). One sample inverted the
    # meaning of ஒரு மாசம் இருப்போம்; the next mutated it to இருப்போங்க —
    # an episode that rehearses a corrupted anchor line poisons the rep.
    if not problems:
        lexicon = json.loads((BASE / "progress" / "lexicon.json").read_text(encoding="utf-8"))
        claimed = set(tags.get("new_words_landed", {})) | set(tags.get("callbacks_used", {}))
        mutated = [w for w in claimed
                   if w in lexicon and not w.startswith("frame:") and w not in script]
        if mutated:
            problems.append(f"payload infidelity — claimed but not verbatim in script: {mutated}")

    # Nothing beyond the three artifacts may have appeared — measured against
    # the PRE-RUN tree (a clean-tree assumption false-flagged the operator's
    # own uncommitted work on the first run). Print-only passes make this a
    # tripwire for agy misbehaviour, not an expected failure. Scoped to
    # content/ (2026-07-13): agy can only plausibly misbehave in the studio's
    # own domain; progress/ churn is other agents legitimately writing state
    # mid-run (the session-open dispatch guarantees that overlap) and aborted
    # a good episode once.
    allowed = {str(p.relative_to(BASE)) for p in paths.values()}
    stray = {p for p in git_dirty() - (baseline or set()) - allowed
             if p.startswith("content/")}
    if stray:
        problems.append(f"stray writes outside the episode files: {sorted(stray)}")
    return problems


def main():
    ap = argparse.ArgumentParser(description="agy-writer studio dispatch (Claude subagent is the fallback)")
    ap.add_argument("--dry-run", action="store_true",
                    help="passes + lint only; no render, no state, no commit")
    args = ap.parse_args()

    # Preflight — fail fast and legibly. Exit 1 IS the fallback contract; the
    # caller should read this one line, not a WinError traceback (2026-07-15).
    if not shutil.which("agy"):
        print("✗ agy is not on PATH — dispatch the Claude studio subagent instead "
              "(.claude/agents/studio.md), or install/authenticate agy.")
        sys.exit(1)

    n = next_mission()
    print(f"Mission {n} — three-pass print-only dispatch")
    baseline = git_dirty()
    print("1. passes…")
    if not write_episode(n):
        sys.exit(1)

    print("2. lint…")
    problems = lint(n, baseline)
    for p in problems:
        print(f"   ✗ {p}")
    if problems:
        print("   artifacts left in place for inspection — falling back is safe")
        sys.exit(1)
    print("   all checks pass")

    if args.dry_run:
        print(f"[dry-run] would render: tier2_mission{n}.mp3 — stopping before state.")
        return

    print("3. render + publish (render_audio.py owns state and the commit)…")
    script = episode_paths(n)["script"]
    mp3 = AUDIO_DIR / f"tier2_mission{n}.mp3"
    r = subprocess.run([sys.executable, str(BASE / "scripts" / "render_audio.py"),
                        str(script), str(mp3)], cwd=BASE)
    if r.returncode != 0:
        print(f"   ✗ render failed (exit {r.returncode})")
        sys.exit(1)
    print(f"done — Mission {n} rendered and published.")


if __name__ == "__main__":
    main()
