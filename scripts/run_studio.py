#!/usr/bin/env python3
"""
Studio dispatch — the writer passes + the local Python renderer.

The writer-only split (Andrew, 2026-07-09), tightened same day: the writer runs
each studio pass as a READ-ONLY, PRINT-ONLY call — Director → Architect →
Producer, one invocation per pass, exactly the pipeline the protocol prescribes
(collapsing the three passes into one shot produced flat, off-canon scripts;
the isolated-pass probe was good). The writer never writes a file, never runs a
command, never sees git: Python captures each pass's stdout, writes the three
artifacts, LINTS them deterministically, and hands the script to
render_audio.py — which owns TTS, registration, lexicon seeding, the feed,
and the commit exactly as in any other production run.

TWO EXECUTORS, ONE MODEL (2026-08-18): `claude -p` where an agent exists (the
laptop — no cash cost, reads canon off disk), the OpenRouter API where one does
not (GitHub Actions — `inline_canon` carries the canon instead). Both run
morning_knock.MODEL. This REPLACES agy/Gemini, retired the same day for running
on neither host.

Exit 0 = episode rendered and published. Any other exit = the caller falls
back to the Claude studio subagent (.claude/agents/studio.md) — the
default/fallback contract. Failed artifacts stay in place, untracked, for
inspection (git clean removes them).

  python scripts/run_studio.py            # full: three passes, lint, render, publish
  python scripts/run_studio.py --dry-run  # passes + lint only; no render

Needs: claude on PATH (or OPENROUTER_API_KEY), GCP ADC for the render step.
"""
import argparse
import json
import os
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

# Cross-process contract, mirrored in render_audio.py and read by
# studio_watchdog.py: "this host lacks the secrets" — skip, never retry.
EXIT_NOT_CONFIGURED = 3

SCRIPTS_DIR = BASE / "content" / "scripts"
LESSONS_DIR = BASE / "content" / "lessons"
CAPTIONS_DIR = BASE / "content" / "captions"
AUDIO_DIR = BASE / "published_audio"

PASS_TIMEOUT_S = 900   # 15 min per pass — each is one print turn

# THE WRITER IS `claude -p`, AND THE MODEL IS THE ONE EVERY LANE USES
# (2026-08-18, Andrew — replaces agy/Gemini 3.1 Pro locally and
# google/gemini-3-flash-preview in the cloud).
#
# WHY agy WENT: it was introduced as a cost saving that spent Andrew's standing
# Gemini quota. On 2026-08-18 it was not installed on the laptop and not
# authenticated, and a GitHub runner never had the binary — so it ran NOWHERE, and
# `openrouter_pass`, written for a cloud that has never invoked it, had silently
# become the only writer executing anywhere. A branch with no live user is not a
# fallback, it is a second thing to keep correct; the canon-carrying bug fixed
# earlier today lived in exactly that gap.
#
# WHY `claude -p`: the laptop has an agent with a filesystem and a subscription
# already paid for, so a local pass costs no cash and reads its canon off disk the
# way agy did. A runner has neither, so it keeps the API. One model across both
# (morning_knock.MODEL) — a host difference, never a model difference.
#
# READ-ONLY BY CONSTRUCTION: the PREAMBLE tells each pass it is print-only;
# `--allowedTools` now enforces it. A pass can read the canon and nothing else —
# no writes, no commands, no git. Python remains the only thing that touches disk.
WRITER_TOOLS = ["Read", "Glob", "Grep"]
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

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

PRINT the full episode script and nothing else. The VERY FIRST LINE must be
the title as an H1 — `# Tier 2, Mission {n} — <Title>` — because the feed reads
the episode's public name off that one line and nothing else. Then speaker
lines as `**Name:** text`, with [SFX] / [Pause] craft per the role file.
"""

PRODUCER = PREAMBLE + """
THIS PASS: the PRODUCER. Read protocol/studio/producer.md,
protocol/studio/dialect.md and protocol/constitution.md and follow them exactly:
dialect transformation, integrity checks (send-backs become fixes you make
yourself here), and the sidecar. Two hard rules the dialect pass must not violate:
- PAYLOAD FIDELITY: a CHUNK the sidecar claims must appear EXACTLY as seeded
  — the learner drills these precise forms and a mutated anchor poisons the
  rep. A single WORD may carry the sentence's own inflection, but its stem
  must survive (Python rejects the script on either failure).
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


def claude_print(label: str, prompt: str) -> str | None:
    """One read-only, print-only pass on the local agent. Returns stdout, or None
    on failure. Runs in BASE so the pass can read the canon off disk — no
    `inline_canon` needed here, which is the whole reason a filesystem-having
    writer is worth preferring."""
    from morning_knock import MODEL
    print(f"   [{label}] claude ({MODEL})…")
    try:
        r = subprocess.run(
            ["claude", "-p", "--model", MODEL,
             "--allowedTools", *WRITER_TOOLS, "--", prompt],
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


CANON_REF_RE = re.compile(r"(?:protocol|progress)/[\w/-]+\.(?:md|json)")
# WIDENED from `protocol/[\w/]+\.md` (2026-08-18). The old pattern could only see
# protocol markdown, so the Director's own instruction — "Read progress/profile.md
# — its Calibration Notes are LAW — and the soak-order in progress/learner.json" —
# inlined NEITHER, silently. The pass that sets density and new-word counts was
# told its dials were law and never handed them.
CANON_SKIP = {
    # 114 KB of raw rows that `suggest_targets.py` already distills into the
    # ticket every pass receives. Inlining it would quadruple every prompt to
    # re-send what the ticket has already chosen from. Skipped LOUDLY below.
    "progress/lexicon.json",
}
CANON_DEPTH = 2   # the prompt names a file; that file names its canon. No further.


def newest_tags_sample() -> str | None:
    """The freshest real sidecar, as the schema example for the cloud Producer."""
    tags = sorted(SCRIPTS_DIR.glob("tier2_mission*.tags.json"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return tags[0].read_text(encoding="utf-8").strip() if tags else None


def inline_canon(prompt: str) -> str:
    """Carry the protocol INTO the prompt for the filesystem-less cloud writer.

    A writer with a filesystem reads 'protocol/studio/producer.md' off disk; a
    single-shot API call can't, so every file a pass says to 'Read' must ride in
    the prompt — exactly how morning_knock inlines persona.md. The prompt's OWN
    file references are the manifest: whatever a pass names, Python inlines, so
    the two never drift (2026-07-24 — the thin slice caught the cloud writer
    inventing a schema it had no way to see).

    IT NOW FOLLOWS REFERENCES TRANSITIVELY (2026-08-18), because the manifest was
    only ever read one level deep. `director.md` and `architect.md` both say to
    read `protocol/constitution.md` — Woven Thanglish, the Noun Shortcut, No
    Academic Terms, Phonetic Acceptance, Fresh Execution — and the constitution
    was inlined NOWHERE. A filesystem-having writer (agy) followed those
    references itself, so the gap was invisible for as long as agy was the local
    writer; when it stopped being installed, `openrouter_pass` became the only
    writer running anywhere and every episode since was written without the canon
    it is judged against. Depth-limited and deduped: the role files cite each
    other, so an unbounded walk would cycle.

    REPLACES a silent gap with a loud one: anything referenced and NOT carried is
    now printed, so the next blind spot announces itself instead of waiting for
    someone to diff a prompt against a protocol file."""
    seen, blocks, queue, skipped = [], [], list(CANON_REF_RE.findall(prompt)), []
    for _ in range(CANON_DEPTH):
        nxt = []
        for ref in queue:
            if ref in seen:
                continue
            seen.append(ref)
            if ref in CANON_SKIP:
                skipped.append(ref)
                continue
            p = BASE / ref
            if not p.exists():
                blocks.append(f"===== {ref} (referenced but missing) =====")
                continue
            text = p.read_text(encoding="utf-8").strip()
            blocks.append(f"===== {ref} =====\n{text}")
            nxt.extend(CANON_REF_RE.findall(text))
        queue = nxt
    if skipped:
        print(f"   [canon] referenced but NOT carried: {', '.join(skipped)}")
    if ".tags.json" in prompt:
        sample = newest_tags_sample()
        if sample:
            blocks.append("===== EXAMPLE .tags.json — match THIS schema exactly "
                          f"(your content, its keys) =====\n{sample}")
    if not blocks:
        return prompt
    return ("CANON — the files this pass refers to, inlined because you have no "
            "filesystem. Follow them exactly:\n\n"
            + "\n\n".join(blocks)
            + "\n\n===== YOUR TASK =====\n" + prompt)


def openrouter_pass(label: str, prompt: str) -> str | None:
    """One writer pass through the OpenRouter API — the executor for a host with
    no agent, which means GitHub Actions. Same contract as `claude_print`: prompt
    in, printed artifact out, or None on failure. The prompts are identical;
    `inline_canon` supplies the files a filesystem-having writer would have read,
    so only the executor differs — never the pipeline, and since 2026-08-18 never
    the model either."""
    from openai import OpenAI
    from morning_knock import OPENROUTER_MODEL, budget
    print(f"   [{label}] openrouter ({OPENROUTER_MODEL})…")
    try:
        client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
        resp = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            max_tokens=budget(8000),
            messages=[{"role": "user", "content": inline_canon(prompt)}],
            timeout=PASS_TIMEOUT_S,
        )
        out = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"   ✗ {label}: {type(e).__name__}: {str(e)[:200]}")
        return None
    if len(out) < 200:
        print(f"   ✗ {label}: {len(out)} chars — too short")
        return None
    print(f"   [{label}] {len(out)} chars")
    return out


def resolve_writer(prefer: str = "auto"):
    """Pick the pass executor. 'auto' prefers the local agent — no cash cost, and
    it reads the canon off disk instead of relying on `inline_canon` being right —
    and falls back to OpenRouter where no agent binary exists, which is every cloud
    runner. 'claude'/'openrouter' force one, for the A/B."""
    if prefer == "claude":
        return claude_print
    if prefer == "openrouter":
        return openrouter_pass
    return claude_print if shutil.which("claude") else openrouter_pass


# Tamil vowel signs + the pulli — exactly what inflection replaces on a stem.
TAMIL_TAIL_RE = re.compile(r"[ா-்]$")


def payload_present(word: str, script: str, lexicon: dict) -> bool:
    """Is a claimed payload item really in the script?

    VERBATIM FOR CHUNKS, STEM-TOLERANT FOR WORDS (2026-08-18). The rule was a flat
    substring test, which a VERB STEM can essentially never satisfy in natural
    speech: on 2026-08-18 a script said தூக்கறேன் — the word used correctly and
    conjugated — while the sidecar honestly claimed தூக்கு, and the episode was
    rejected. Every verb in the pool had the same problem waiting.

    The lexicon already draws the distinction the rule needs. A `chunk` is a fixed
    phrase the learner drills WHOLE, and both incidents that earned this check were
    chunk mutations (ஒரு மாசம் இருப்போம் inverted, then bent to இருப்போங்க) — so
    chunks keep zero tolerance. A plain word is a lexical item the sentence around
    it inflects, so it is matched on its stem: the item minus one trailing vowel
    sign or pulli.

    The tolerance stays narrow on purpose. தூக்கு → தூக்க admits தூக்கறேன் and
    தூக்குங்க and nothing that is not that verb; வேணும் → வேணும still refuses
    வேண்டும், which is the literary form the dialect pass exists to remove. A stem
    under 3 characters is no evidence at all (வை → வ), so those fall back to
    verbatim — harmless, because inflection APPENDS to a short stem anyway."""
    if word in script:
        return True
    if " " in word or (lexicon.get(word) or {}).get("type") == "chunk":
        return False
    stem = TAMIL_TAIL_RE.sub("", word)
    return len(stem) >= 3 and stem in script


def fenced_block(text: str, lang: str) -> str | None:
    m = re.findall(rf"```{lang}\s*\n(.*?)```", text, re.DOTALL)
    return m[-1].strip() if m else None


def write_episode(n: int, write_pass=claude_print) -> bool:
    """Run the three passes; persist the three artifacts. Python is the only
    thing that touches disk. `write_pass` is the executor (claude or OpenRouter) —
    same prompts, same contract, either environment."""
    # --fence: the Director copies the Vocabulary Fence into the brief verbatim
    # (director.md), and the Architect builds every scene out of it. Anna's bare
    # invocation drops it — it was 65% of his session load and none of his job.
    ticket = subprocess.run([sys.executable, str(BASE / "scripts" / "suggest_targets.py"), "--fence"],
                            capture_output=True, encoding="utf-8", errors="replace",
                            cwd=BASE, check=True).stdout
    plan = write_pass("Director", DIRECTOR.format(ticket=ticket))
    if not plan:
        return False
    draft = write_pass("Architect", ARCHITECT.format(plan=plan, n=n))
    if not draft:
        return False
    final = write_pass("Producer", PRODUCER.format(draft=draft, n=n))
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
    sheet_out = write_pass("Captions", CAPTIONS.format(n=n, script=script))
    sheet = fenced_block(sheet_out, "markdown") if sheet_out else None
    if sheet:
        paths["captions"].parent.mkdir(parents=True, exist_ok=True)
        paths["captions"].write_text(sheet + "\n", encoding="utf-8")
    else:
        print("   ⚠ caption sheet pass failed — episode ships without captions")
    return True


def git_dirty() -> set[str]:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=BASE,
                         capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
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
    # THE PUBLIC NAME OF THE EPISODE (2026-08-20). rebuild_rss.get_title_from_md
    # reads ONE line — `f.readline()` — and falls back to the filename, so an
    # H1 on line 3 is as absent as no H1 at all. The Architect was never told to
    # emit one, produced it by accident, and 30 of 76 episodes shipped to the
    # public feed titled `Tier2 Mission90`. Assert the exact thing the reader
    # does, on the exact line it reads.
    if not script.splitlines()[0].strip().startswith("# "):
        problems.append(
            "script's FIRST line is not an H1 title — the feed would fall back "
            f"to the filename (got: {script.splitlines()[0][:60]!r})")
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
                   if w in lexicon and not w.startswith("frame:")
                   and not payload_present(w, script, lexicon)]
        if mutated:
            problems.append(f"payload infidelity — claimed but not in the script: {mutated}")

    # Nothing beyond the three artifacts may have appeared — measured against
    # the PRE-RUN tree (a clean-tree assumption false-flagged the operator's
    # own uncommitted work on the first run). Print-only passes make this a
    # tripwire for writer misbehaviour, not an expected failure. Scoped to
    # content/ (2026-07-13): a writer can only plausibly misbehave in the studio's
    # own domain; progress/ churn is other agents legitimately writing state
    # mid-run (the session-open dispatch guarantees that overlap) and aborted
    # a good episode once.
    # as_posix, not str(): `git status --porcelain` always prints forward
    # slashes, but str(Path) on Windows yields 'content\scripts\…' — so the
    # set difference subtracted nothing and the episode's OWN four artifacts
    # were reported as strays, failing every local run on this box
    # (2026-07-31). Same normalisation on both sides or the check is a coin
    # flip on the operating system.
    allowed = {p.relative_to(BASE).as_posix() for p in paths.values()}
    stray = {p for p in git_dirty() - (baseline or set()) - allowed
             if p.startswith("content/")}
    if stray:
        problems.append(f"stray writes outside the episode files: {sorted(stray)}")
    return problems


def claim_payload(n: int) -> None:
    """Deterministic sidecar repair ('bends the sidecar', pointed forward): the
    soak order this dispatch consumed must be CLAIMED by the sidecar, or the
    render never stamps the payload seen_in (the Teach Beat's unlock) and the
    produced-verdict can't clear — a frame key is unrecoverable from surface
    forms downstream. Frames inject unconditionally (verbatim-exempt slot
    templates); a non-frame key injects only when the script carries it — an
    absent one is reported, never invented.

    IT SHARES `payload_present` WITH THE LINT (2026-08-18, the day's lint pass).
    Both sides ask the same question about the same script and must not answer it
    differently: this path kept the flat substring test for the few hours after
    the lint learned the stem, so an inflected-but-correct word passed the gate
    and was then refused the claim — reported as missing, and the render never
    stamped its `seen_in`."""
    paths = episode_paths(n)
    try:
        soak = (json.loads((BASE / "progress" / "learner.json").read_text(encoding="utf-8"))
                .get("soak_order") or {})
        lex = json.loads((BASE / "progress" / "lexicon.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    payload = [w for w in soak.get("payload", []) if w]
    if not payload:
        return
    tags = json.loads(paths["tags"].read_text(encoding="utf-8"))
    script = paths["script"].read_text(encoding="utf-8")
    strip = lambda w: re.sub(r"\s*\([^)]*\)\s*$", "", w).strip()
    claimed = {strip(w) for w in
               set(tags.get("new_words_landed", {})) | set(tags.get("callbacks_used", {}))}
    added = []
    for key in payload:
        if key in claimed:
            continue
        if key.startswith("frame:") or payload_present(key, script, lex):
            tags.setdefault("new_words_landed", {})[key] = 0
            added.append(key)
        else:
            print(f"   ⚠ soak payload '{key}' neither claimed by the sidecar nor in the script")
    if added:
        paths["tags"].write_text(json.dumps(tags, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        print(f"   payload claimed into sidecar: {', '.join(added)}")


def claim_spec(n: int) -> None:
    """Python stamps the scene spec into the sidecar; the writer only obeys it.

    Same seam and same reasoning as claim_payload: the spec was decided by
    `scene_spec()`, then travelled as PROSE through Director → Architect →
    Producer and came back as a label the writer chose for itself. The thin
    slice caught Flash filing a `vignette` as `classic` — script right, label
    wrong — and the label is not cosmetic: `pick_divergent` reads these
    sidecars, so a mislabelled episode corrupts the next three choices.

    It matters more now that a form can be COMMISSIONED. An unstamped
    narrated_drama that reports itself `classic` would leave the divergence
    gate believing a form it never rolled had just been used.

    Never invents: an absent spec (no sidecar, unreadable) is left alone."""
    sys.path.insert(0, str(BASE / "scripts"))
    from suggest_targets import commissioned_form, load_recent_sidecars, scene_spec
    paths = episode_paths(n)
    try:
        tags = json.loads(paths["tags"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    # Recomputed, not re-read: pick_divergent is a pure function of the sidecars,
    # and the dispatch lock means they cannot move mid-run — so this is the same
    # spec the ticket printed, without threading it through a subprocess boundary.
    spec = scene_spec(load_recent_sidecars(), commissioned_form())
    stamped = {"register": spec["register"], "episode_form": spec["form"],
               "dramatic_ingredient": spec["ingredient"]}
    drifted = {k: (tags.get(k), v) for k, v in stamped.items() if tags.get(k) != v}
    if not drifted:
        return
    tags.update(stamped)
    paths["tags"].write_text(json.dumps(tags, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    for k, (was, now) in drifted.items():
        print(f"   spec stamped: {k} {was!r} → {now!r} (Python decides, the writer obeys)")


def renderer_preflight() -> str | None:
    """None when this host can RENDER (TTS credentials + deps), else the reason.
    Separate from the writer check because rendering an already-written script
    needs no writer — the watchdog's re-render path must not be blocked by it."""
    sys.path.insert(0, str(BASE / "scripts"))
    try:
        from render_audio import google_credentials_ready
    except ImportError as e:
        return f"the renderer's dependencies are not installed ({e.name})"
    return google_credentials_ready()


def writer_preflight(prefer: str = "auto") -> str | None:
    """None when a writer is available for `prefer`, else the reason. claude needs
    the binary; openrouter needs the API key; auto is happy with either."""
    have_claude = bool(shutil.which("claude"))
    have_or = bool(os.environ.get("OPENROUTER_API_KEY"))
    if prefer == "claude" and not have_claude:
        return "claude is not on PATH (the local agent writer)"
    if prefer == "openrouter" and not have_or:
        return "OPENROUTER_API_KEY is not set (the cloud writer)"
    if prefer == "auto" and not (have_claude or have_or):
        return "no writer available — need claude on PATH or OPENROUTER_API_KEY"
    return None


def preflight(prefer: str = "auto") -> str | None:
    """None when this host can produce an episode END TO END (write + render),
    else the reason. Checked BEFORE any expensive pass so a machine without the
    secrets says so in a second — Andrew runs lessons on two laptops and only
    one carries the credentials (2026-07-23). Local and cheap: no network, no
    writer invocation."""
    return writer_preflight(prefer) or renderer_preflight()


_DISPATCH_LOCK = None  # held for the process lifetime; see main()


def acquire_dispatch_lock():
    """One dispatch at a time — studio_watchdog.py shares this lock, so a
    session-open dispatch and a watchdog tick can never stack. Held for the
    process lifetime; no-op where fcntl is missing (Windows)."""
    try:
        import fcntl
    except ImportError:
        return None
    fd = open(BASE / ".studio.lock", "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("✗ another studio dispatch holds .studio.lock — not stacking a second run.")
        sys.exit(1)
    return fd


def main():
    ap = argparse.ArgumentParser(description="Studio dispatch — claude (local) or OpenRouter (cloud) writer + Python renderer")
    ap.add_argument("--dry-run", action="store_true",
                    help="passes + lint only; no render, no state, no commit")
    ap.add_argument("--writer", choices=["auto", "claude", "openrouter"], default="auto",
                    help="pass executor: auto (claude if present, else OpenRouter), or force one (A/B)")
    args = ap.parse_args()

    # Load .env for the OpenRouter writer key (local); in the cloud the workflow
    # sets it directly, so a missing .env is fine. claude authenticates separately.
    sys.path.insert(0, str(BASE / "scripts"))
    from morning_knock import load_env
    load_env(BASE / ".env")

    # Module global, not a local: the flock releases when its file object is
    # collected, so the reference has to outlive main()'s frame. As a local it
    # read as dead code — it was carrying a `# noqa: F841` for a linter this
    # repo does not run, which is how an unused-looking binding that is load
    # bearing survives review (2026-08-04).
    global _DISPATCH_LOCK
    _DISPATCH_LOCK = acquire_dispatch_lock()

    # Preflight — fail fast and legibly. The caller should read one line, not a
    # WinError traceback (2026-07-15). A MISSING CREDENTIAL is not a failure:
    # it exits EXIT_NOT_CONFIGURED so the watchdog skips instead of retrying an
    # absent secret every tick.
    reason = preflight(args.writer)
    if reason:
        print(f"⏭️  Not a studio host — {reason}.\n"
              f"    Copy the credentials over, or produce on a configured host.")
        sys.exit(EXIT_NOT_CONFIGURED)

    write_pass = resolve_writer(args.writer)
    n = next_mission()
    print(f"Mission {n} — three-pass print-only dispatch ({write_pass.__name__})")
    baseline = git_dirty()
    print("1. passes…")
    if not write_episode(n, write_pass):
        sys.exit(1)

    print("2. lint…")
    problems = lint(n, baseline)
    for p in problems:
        print(f"   ✗ {p}")
    if problems:
        print("   artifacts left in place for inspection — falling back is safe")
        sys.exit(1)
    print("   all checks pass")
    claim_payload(n)
    claim_spec(n)

    if args.dry_run:
        print(f"[dry-run] would render: tier2_mission{n}.mp3 — stopping before state.")
        return

    print("3. render + publish (render_audio.py owns state and the commit)…")
    script = episode_paths(n)["script"]
    mp3 = AUDIO_DIR / f"tier2_mission{n}.mp3"
    # STUDIO_LOCK_HELD: we already hold .studio.lock for this process's lifetime,
    # so the child inherits it rather than blocking on its own parent.
    r = subprocess.run([sys.executable, str(BASE / "scripts" / "render_audio.py"),
                        str(script), str(mp3)], cwd=BASE,
                       env={**os.environ, "STUDIO_LOCK_HELD": "1"})
    if r.returncode == EXIT_NOT_CONFIGURED:
        print("   ⏭️  render skipped — this host lacks the TTS credentials.")
        sys.exit(EXIT_NOT_CONFIGURED)
    if r.returncode != 0:
        print(f"   ✗ render failed (exit {r.returncode})")
        sys.exit(1)

    # Tell him it exists. The drill and the soak loop both push to the phone on
    # publish; the episode channel never did, so a commissioned episode landed
    # silently on the feed and Andrew had no way to know (2026-07-23: he asked
    # for audio to take to the park and never learned it was ready). Quiet hours
    # are the knock rails' window — an overnight render waits for morning.
    try:
        sys.path.insert(0, str(BASE / "scripts"))
        from morning_knock import push_to_phone, jsdelivr_url
        title = episode_paths(n)["script"].stem
        # Quiet hours are the chokepoint's job now — this lane's hand-rolled hour
        # compare was one of three copies, and two other lanes had none (2026-07-26).
        if push_to_phone(f"new episode's up — {title} 🎧", jsdelivr_url(mp3)):
            print("   phone: notified.")
    except Exception as e:
        print(f"   ⚠ publish notification failed (episode is still live): {e}")

    print(f"done — Mission {n} rendered and published.")


if __name__ == "__main__":
    main()
