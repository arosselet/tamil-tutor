"""The smoke suite's harness — everything the per-layer case files share.

Split out of `scripts/smoke_test.py` on 2026-08-25 (spine plan §10) so that a
change to one layer's cases lands in that layer's file instead of colliding with
every other layer in one 8,000-line module. Nothing here changed in the move.

HOW CASE FILES MUST REACH THIS MODULE. `load_modules` binds `pb`, `wr` and `si`
with `global`, at RUN time — long after every case file has been imported. So:

    from ._fixtures import check, write_json     # fine: never rebound
    from . import _fixtures as fx
    fx.pb.refresh_feed = fake                    # patches what the lane resolves

and never `from ._fixtures import pb`, which binds a COPY of `None` at import
time and, worse, installs stubs on an object no lane will ever look at. This is
the same rule that keeps `from X import name` off the lane seams, for the same
reason: a stub that stops intercepting means a test reaches the real network and
a real phone.

`FAILURES` has the identical hazard and is handled by everyone calling the ONE
`check` defined here, which appends to the one list. `smoke_test.py` reads the
tally back through `fx.FAILURES` so it can never report ALL GREEN over another
file's failures.
"""
import ast
import importlib
import io
import json
import shutil
import subprocess
import sys
import textwrap
import tokenize
from pathlib import Path

# scripts/smoke/_fixtures.py -> the repo root is three parents up, not two.
REAL_BASE = Path(__file__).resolve().parent.parent.parent
FAILURES: list[str] = []
# Case filter: `python scripts/smoke_test.py s41 s58` runs those two alone.
# CI passes nothing and gets the whole suite (smoke.yml's contract).
ONLY: list[str] = [a for a in sys.argv[1:] if not a.startswith("-")]
RAN: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    print(f"  [{'ok' if cond else 'FAIL'}] {name}" + ("" if cond else f" — {detail}"))
    if not cond:
        FAILURES.append(name)


class Recorder(list):
    """Stub for push_to_phone / commit_and_push — records instead of acting."""
    def __call__(self, *args, **kwargs):
        self.append(args)


# ── Sandbox ───────────────────────────────────────────────────────────────────

def make_sandbox(tmp: Path) -> Path:
    """Copy the repo (minus git/audio/secrets) and reset progress/ to day-zero
    fixtures — the .example files finally earn their keep as test fixtures."""
    sb = tmp / "repo"
    shutil.copytree(REAL_BASE, sb, ignore=shutil.ignore_patterns(
        ".git", ".env", "__pycache__", "audio", "published_audio",
        "*.mp3", "*.mp4", "*.ipynb", "*.jpg"))
    prog = sb / "progress"
    for ex in prog.glob("*.example"):
        shutil.copy(ex, prog / ex.name[: -len(".example")])
    (prog / "knock_log.json").write_text("[]", encoding="utf-8")
    (prog / "push_queue.json").write_text("[]", encoding="utf-8")
    return sb


def load_modules(sb: Path):
    """Import the SANDBOX copies of the scripts — their BASE resolves to the
    sandbox, so every path constant lands there without patching."""
    real_scripts = str(REAL_BASE / "scripts")
    sys.path = [p for p in sys.path if p != real_scripts]
    sys.path.insert(0, str(sb / "scripts"))
    mk = importlib.import_module("morning_knock")
    kr = importlib.import_module("knock_reply")
    pq = importlib.import_module("push_queue")
    # L2, L3 and L4, bound as module globals rather than threaded through 70 case
    # signatures. Cases reach them by ADDRESS for the same two reasons they ever
    # reached `mk` that way: to read a constant, and to patch a name a moved
    # function resolves through its OWN globals (`pb.in_waking_window` is the
    # load-bearing one -- patching it anywhere else stops intercepting, and a
    # stub that stops intercepting means a test hits the real phone).
    #
    # THE TWO ARE NOW DIFFERENT ADDRESSES (2026-09-04). Patch the FUNCTION on the
    # module whose code calls it -- `pb.in_waking_window`, because `push_to_phone`
    # resolves it through publish's globals. Set the CONSTANTS on `rl`, because
    # the real `in_waking_window` lives in `rails` and reads rails' globals; a
    # case that sets `pb.WAKING_START_HOUR` now changes a name nothing reads.
    global pb, wr, si, lang, rl
    pb = importlib.import_module("publish")
    wr = importlib.import_module("writer")
    rl = importlib.import_module("rails")      # L2 — the reach budget
    si = importlib.import_module("state_io")   # L0
    lang = importlib.import_module("language") # below L0 — the port surface
    check("modules imported from sandbox", mk.__file__.startswith(str(sb)),
          f"morning_knock loaded from {mk.__file__}")
    return mk, kr, pq


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ── The lexicon record ───────────────────────────────────────────────────────
# WHAT THIS REPLACES: 64 hand-written record literals across four case files, and
# the FIVE competing `row` lambdas that had already grown inside `state.py` alone
# — three of which omitted `recognition` and `production` entirely and leaned on
# every call site to remember them. No file stated what a lexicon record IS, so
# each case restated it, slightly differently.
#
# THE SILENT NO-OP THIS CLOSES (Gate 7.2). A fixture is a claim about a shape the
# production code writes. When `sync_state` mints a seventh core field, 64 literals
# go on asserting behaviour over a record shape nothing produces any more: every
# case still passes, and it passes for the wrong reason — the same class as the
# dropped DEMOTE table, where the test tested the function and the bug was in the
# round trip. Deduplication alone would not fix that; it would centralise the
# staleness. So the defaults below are GUARDED against the real mint sites by
# `s85`, which reads them out of `sync_state` by AST: this builder cannot drift
# from the thing it stands in for without a red run.
#
# `heard_on` IS DELIBERATELY ABSENT and must stay absent. `sync_state` omits it at
# every mint site on purpose ("minting is Anna DECLARING a level, not observing
# one"), which is what makes solid-by-assertion a DERIVED property rather than a
# stored flag. A default here would hand every fixture ear-evidence it never
# earned and quietly retire the distinction `s53` exists to prove.

def lex_row(**kw) -> dict:
    """One lexicon record in the shape `sync_state` actually mints.

    Pass only what the case is ABOUT — the defaults are the boring rest:

        lex_row(recognition="solid", production="cold")
        lex_row(type="pattern", heard_on="2026-07-26", direction="catch")

    Optional fields (`type`, `deck`, `direction`, `register`, `reps`,
    `pairs_with`, `heard_on`) are absent unless asked for, exactly as in the
    minted record."""
    return {"gloss": "x", "phonetic": [], "recognition": "struggled",
            "production": "none", "seen_in": [], "last_surfaced": None, **kw}

def code_lines(src: str) -> int:
    """Executable lines: everything that is not blank, a comment, or a docstring."""
    return len(code_line_numbers(src))


def code_line_numbers(src: str) -> set[int]:
    """Which lines are mechanism. Split out of `code_lines` (2026-08-10) so a
    source-text assertion can search MECHANISM without matching the prose that
    explains it — a docstring quoting the code it retired otherwise fails the very
    check that proves the code is gone."""
    doc: set[int] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                doc.update(range(body[0].lineno, body[0].end_lineno + 1))
    comment = {tok.start[0] for tok in
               tokenize.generate_tokens(io.StringIO(src).readline)
               if tok.type == tokenize.COMMENT}
    out: set[int] = set()
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if not stripped or i in doc:
            continue
        if i in comment and stripped.startswith("#"):
            continue
        out.add(i)
    return out


def raw_source(path: Path) -> str:
    """Source read as TEXT, prose and all — the one legitimate way past
    `mechanism()`, and named so the exemption is a decision rather than an
    oversight. Correct only when the file is about to be consumed as a PROGRAM
    (`ast.parse`) rather than grepped: a parser needs the comments' line numbers
    to report positions the reader can find. Grepping this is the bug `mechanism`
    exists to prevent — if you are looking for a substring, you want that."""
    return path.read_text(encoding="utf-8")


def mechanism(src: str, after: str | None = None) -> str:
    """The source with its PROSE removed — comments and docstrings gone, code kept.

    WHY EVERY SOURCE-TEXT ASSERTION GOES THROUGH THIS (2026-08-24). A check that
    greps raw source is satisfied by the paragraph EXPLAINING the code exactly as
    readily as by the code. Not theoretical: `s57`'s "ask_json re-raises the final
    failure instead of swallowing it" was measured passing with the re-raise
    deleted, because the word "raise" appears in `ask_json`'s docstring. The
    assertion was a decoration; a different case caught the mutation, and this one
    would have gone on reading green forever.

    The rule was already known and already written down — `code_line_numbers` was
    split out of `code_lines` on 2026-08-10 with a docstring saying exactly this —
    and it had reached 3 of the 23 places that read Python source. That is the
    shape this repo keeps finding: a law stated once and applied where whoever
    wrote it happened to be standing.

    `after` slices from the first line carrying that marker, for a check that
    anchors on a section heading; the slice is taken on mechanism lines, so the
    heading itself is gone by the time the needle is looked for.
    """
    src = textwrap.dedent(src)
    keep = code_line_numbers(src)
    lines = src.splitlines()
    start = 1
    if after is not None:
        start = next(i for i, ln in enumerate(lines, 1) if after in ln)
    return "\n".join(ln for i, ln in enumerate(lines, 1) if i in keep and i >= start)


# ── The one boundary that is not credential-gated ───────────────────────────
# Every other outside-world call in this system needs a secret the test
# environment does not have, so an un-stubbed one dies with a KeyError and the
# case goes red. `claude -p` needs no secret: the CLI carries its own auth, and
# on Andrew's laptop the binary is on PATH. So a missed stub there does not
# crash — it really spawns the agent, waits, and may come back with a plausible
# answer that turns the case GREEN for the wrong reason. Slow, nondeterministic,
# and invisible.
#
# It got worse on 2026-08-23: before the executor pass, `decide` and both judges
# opened raw OpenRouter clients gated on OPENROUTER_API_KEY, so a missed stub was
# LOUD. Routing them through `writer.ask_json` — which prefers the agent — turned
# three loud boundaries into silent ones on the laptop. That is a real cost of
# that change and this is the guard that pays it back.
#
# The refusal lives HERE, in the harness, not in writer.py: production code
# should not carry test scaffolding, and there is no honest reason for the lane
# to know it is being tested. Only `claude` is refused — the sandbox's real git
# calls are load-bearing for s45/s51 and must still run.
_REAL_RUN = subprocess.run


def _no_agent_spawn(cmd, *a, **kw):
    argv0 = str(cmd[0]) if isinstance(cmd, (list, tuple)) and cmd else str(cmd)
    if Path(argv0).stem == "claude":
        raise AssertionError(
            "a test tried to SPAWN THE REAL AGENT (`claude -p`). Nothing in this "
            "suite may: it is slow, it is nondeterministic, and unlike every other "
            "boundary here it needs no credential, so it would have succeeded and "
            "turned this case green for the wrong reason.\n"
            "     Stub the lane's entry point (kr.judge / mk.decide), or "
            "writer.ask_json / writer.ask_text, or writer._agent_json for the "
            "executor cases.\n"
            f"     argv was: {cmd}")
    return _REAL_RUN(cmd, *a, **kw)


subprocess.run = _no_agent_spawn

# ── Running ONE case ────────────────────────────────────────────────────────
# Every case goes through `run`, and the reason is stub teardown. The suite
# stubs by module attribute — `mk.push_to_phone = Recorder()`, `kr.judge = ...`
# — 59 times, and until 2026-08-24 not one of them was ever put back. Case N
# inherited every stub case N-1 installed, so what a case actually exercised
# depended on its position in a hand-maintained list. Four cases were hoisted
# above `s3` purely to reach the REAL function before something stubbed it, each
# carrying a comment saying so.
#
# MEASURED before this was built (2026-08-24): 68 of the 70 cases already pass
# alone against a fresh sandbox with no inherited stubs at all. The inheritance
# was not load-bearing — it was a latent hazard, which is worse, because the
# failure mode is a stub that quietly stops intercepting and a test that reaches
# real git or a real phone. `restore` closes it for good.
#
# What is NOT reset is the sandbox tree. State on disk is shared on purpose:
# `s50` and `s69` read a knock log and a lexicon that earlier cases populated,
# which is a legitimate end-to-end dependency and the only one that survived
# measurement. Per-case sandboxes are a separate question from per-case stubs.
_PRISTINE: dict = {}


def snapshot(*mods):
    """Record each module's namespace so `run` can put it back after a case."""
    _PRISTINE.clear()
    _PRISTINE.update({m.__name__: (m, dict(m.__dict__)) for m in mods})


def restore():
    """Undo every module-attribute stub the last case installed."""
    for _, (mod, pristine) in _PRISTINE.items():
        for k in [k for k in mod.__dict__ if k not in pristine]:
            delattr(mod, k)
        for k, v in pristine.items():
            if mod.__dict__.get(k) is not v:
                setattr(mod, k, v)


def run(fn, *args):
    """Run one case, then hand the next one clean modules.

    `ONLY` (argv) narrows a run to one case or a prefix — the point of the whole
    exercise: a failure reproduces on its own, without its forty predecessors.
    """
    # A bare token is the case NUMBER and must match exactly — `s6` selects s6 and
    # not s69, which a plain startswith quietly did. A token carrying an
    # underscore is a name prefix (`s41_slip`), where startswith is the point.
    if ONLY and not any(fn.__name__.startswith(o) if "_" in o
                        else fn.__name__.split("_")[0] == o for o in ONLY):
        return
    RAN.append(fn.__name__)
    try:
        fn(*args)
    finally:
        restore()
