"""L3 — composition: what the model is asked, and what comes back.

The parse layer (prose-wrapped JSON, code fences, single-quoted dicts, a
response truncated mid-word), the request layer (JSON mode actually reaching
the wire), and the choice of executor — agent or raw client — by host.

These are the cases that guard the seam between this system and a model, which
is the seam that fails quietly: a parse that raises looks the same as a budget
that ran out, and a stub that stops intercepting reaches the real agent.
"""
import ast
import importlib
import json
import os
import re
import types
from pathlib import Path

from . import _fixtures as fx
from ._fixtures import (
    check, code_line_numbers, mechanism, REAL_BASE,
)


def s1_parse_llm_json(mk):
    print("\n1. LLM response parsing (regression #2)")
    p = fx.wr.parse_llm_json
    check("clean object", p('{"a": 1}') == {"a": 1})
    check("code fence", p('```json\n{"a": 1}\n```') == {"a": 1})
    check("prose-wrapped", p('My decision:\n{"a": {"b": 2}}\nHope that helps!')
          == {"a": {"b": 2}})
    # 2026-07-07: model returned single-quoted Python dict; {..} slice fallback found
    # braces but json.loads rejected single quotes → crash. ast.literal_eval now catches it.
    check("single-quoted keys", p("{'act': True, 'modality': 'text'}")
          == {"act": True, "modality": "text"})
    check("python-dict in prose", p("Here ya go: {'a': 1, 'b': False}")
          == {"a": 1, "b": False})
    # 2026-07-13: judge narrated its reasoning — including a literal `{noun}` frame
    # gloss — BEFORE its ```json fence; startswith fence-strip never fired and the
    # {..} slice bit on `{noun}` → crash, and a real cold fire was lost. Fenced
    # block anywhere in the text now wins.
    check("prose with {braces} before a json fence",
          p('The `{noun} kudunga` frame applies.\n```json\n{"verdict": "cold"}\n```')
          == {"verdict": "cold"})
    check("last fence wins when prose precedes multiple fences",
          p('thinking…\n```json\n{"draft": 1}\n```\nrevised:\n```json\n{"final": 2}\n```')
          == {"final": 2})
    try:
        p("no json here")
        check("garbage raises", False, "did not raise")
    except (json.JSONDecodeError, ValueError):
        check("garbage raises", True)

    # 2026-08-05: the judge burned all 800 tokens reasoning in prose and was cut
    # off mid-word before its first brace. parse_llm_json correctly said "no
    # braces" and raised JSONDecodeError — indistinguishable from KF-7/KF-10,
    # where the JSON existed and the PARSER missed it. The two want opposite
    # fixes (bigger budget vs. another fallback), so the teeth here are on
    # TELLING THEM APART, not on raising: a truncation that merely raises the
    # old error is the silent no-op this guard exists to prevent.
    pr = fx.wr.parse_llm_response
    fake = lambda text, reason: type("R", (), {"choices": [type("C", (), {
        "finish_reason": reason,
        "message": type("M", (), {"content": text})()})()]})()
    truncated = "Looking at this: the target is முடிஞ்சா, so the tag might be"
    try:
        pr(fake(truncated, "length"))
        check("truncation raises", False, "did not raise")
    except json.JSONDecodeError:
        check("truncation is NOT reported as a parse error", False,
              "raised JSONDecodeError — the old, ambiguous signal")
    except ValueError as exc:
        check("truncation is NOT reported as a parse error", True)
        check("truncation names itself", "TRUNCATED" in str(exc), str(exc)[:60])
        # The raw text is the recovery payload — losing it costs a re-run.
        check("truncation dump carries the partial text", truncated in str(exc))
    # No false positives: a complete response still parses, fence and all.
    check("finish_reason=stop parses normally",
          pr(fake('```json\n{"verdict": "cold"}\n```', "stop")) == {"verdict": "cold"})
    check("absent finish_reason parses normally",
          pr(fake('{"verdict": "miss"}', None)) == {"verdict": "miss"})


def s58_a_sheet_survives_a_model_thinking_out_loud(sb: Path):
    """The reply parser, for every shape a real reply comes in (2026-08-10).

    THE FAILURE THIS BLOCK EXISTS TO PREVENT, because it already happened: the
    first 45-minute long-haul render died at movement 5 of 15 with
    `Expecting value: line 1 column 1 (char 0)`. Nothing was wrong with the
    model's answer — it had simply written "Looking at the hosts carefully
    before building:" above a perfectly good object, and the parse only ever
    looked at character 0. Four movements of TTS were already paid for and the
    tape was lost whole.

    IT IS THE MANDATE THAT INVITES IT. The `inventory` clause orders the writer
    to DROP coincidental hosts — a judgement per host — so it shows its work.
    Measured: 3 of 6 identical calls came back prose-prefixed. That is a coin
    flip per call, and a rotation tape makes ~15 calls in a row.

    The negatives matter as much: a reply with NO object must still raise, or a
    lane silently ships a sheet-shaped blank instead of stopping.

    THE STRUCTURAL POINT, and the reason this block is not just three more parser
    cases: `parse_llm_json` had ALREADY fixed this family (07-04 empty text, 07-07
    single quotes, 07-13 prose-before-a-fence). `ask_json` simply never called it
    and re-earned the bug from scratch. So the last assertions here are that the
    lanes share ONE parser — a second one is how a fixed bug comes back."""
    print("\n58. A sheet survives a model that thinks out loud first (2026-08-10)")
    w = importlib.import_module("writer")
    # Any real shape will do here — this case is about the PARSER, and the API
    # path ignores the schema (JSON_MODE already forbids prose there).
    _SCHEMA = w.obj(frame=w.STR)
    sheet = '{"frame": "roots", "beats": [{"say": "x", "en": "y", "who": "anna"}]}'

    for name, text in [
            ("a bare object", sheet),
            ("a ```json fence", f"```json\n{sheet}\n```"),
            ("an unlabelled fence", f"```\n{sheet}\n```"),
            ("REASONING PROSE, then a bare object — the render-killer",
             f"Looking at the hosts carefully before building:\n\n- real\n\n{sheet}"),
            ("reasoning prose, then a fence",
             f"Checking each host:\n\n```json\n{sheet}\n```"),
            ("prose that mentions a brace before the real object",
             f"I considered {{a, b}} and then wrote:\n\n```json\n{sheet}\n```"),
            ("an object with prose trailing after it",
             f"{sheet}\n\nI dropped one coincidental host.")]:
        try:
            got = fx.wr.parse_llm_json(text)
        except Exception as e:                                  # noqa: BLE001
            got = {"frame": f"<raised {type(e).__name__}: {e}>"}
        check(f"the sheet is recovered from {name}", got.get("frame") == "roots",
              str(got.get("frame")))

    check("a multi-beat sheet keeps every beat, not just the first",
          len(fx.wr.parse_llm_json(
              'prose\n{"frame": "f", "beats": [{"say": "1"}, {"say": "2"}, {"say": "3"}]}'
          )["beats"]) == 3)

    # A reply carrying no object must STOP the lane, never yield a blank sheet.
    for name, text in [("an empty completion", ""), ("only whitespace", "   \n "),
                       ("a refusal with no object", "I cannot do that.")]:
        raised = False
        try:
            fx.wr.parse_llm_json(text)
        except (ValueError, json.JSONDecodeError):
            raised = True
        check(f"{name} raises rather than returning a blank sheet", raised)

    # ONE parser, not two. The drill lane owning a private brace-slice is exactly
    # how 07-13 came back on 08-10; the rotation lane borrows this one in turn.
    # ask_json MOVED to writer.py on 2026-08-23 with the executor split; the
    # assertions follow it rather than being deleted — the parser gap this case
    # exists for is a property of the function, not of the file it sat in.
    # MECHANISM ONLY, via the shared helper. This case rolled its own filter here
    # on 2026-08-10 after the docstring below quoted the retired parse verbatim and
    # satisfied the very check meant to prove it was gone. That fix stayed local for
    # two weeks while twenty other source reads went on grepping prose (2026-08-24).
    drill_code = mechanism((REAL_BASE / "scripts" / "writer.py").read_text(encoding="utf-8"))
    check("ask_json parses through the shared parser, not a private one",
          "parse_llm_response(resp)" in drill_code, "ask_json re-implemented the parse")
    # SCARCITY, NOT ABSENCE (2026-08-23, the spine refactor). This used to assert
    # the brace-slice appeared NOWHERE in writer.py, which was right while this
    # module only CALLED the parser. `parse_llm_json` moved here from
    # morning_knock — L3 owns composing and parsing — so "nowhere" now reads as
    # "the parser must not exist". The property 07-13 and 08-10 actually violated
    # was never absence: it was a SECOND implementation growing beside the shared
    # one. Exactly one is the invariant, and it is the one with teeth.
    check("...and no private brace-slice survives beside the shared parser",
          drill_code.count('find("{")') == 1 and drill_code.count('startswith("```")') == 1,
          "a second parser is how 07-13 came back on 08-10")
    # Matched loosely on purpose: the import line also carries the schema helpers
    # since 2026-08-23, and an exact-string check would fail on a tidy-up that
    # changed nothing about where ask_json comes from.
    _lh = mechanism((REAL_BASE / "scripts" / "render_rotation.py").read_text(encoding="utf-8"))
    check("the rotation lane borrows ask_json rather than rolling its own",
          any(ln.startswith("from writer import") and "ask_json" in ln
              for ln in _lh.splitlines()), "ask_json comes from somewhere else")

    # The retry is what makes a 15-call lane survivable; the LAST failure must
    # still surface, or a tape ends silently short instead of stopping loudly.
    #
    # TWO SOURCE GREPS RETIRED HERE (2026-08-24), and what makes them dead sits
    # forty lines below: "a lane that never gets a sheet stops loudly" drives a
    # client that always fails and asserts `ask_json` RAISES, and "...after
    # re-rolling, not on the first bad draw" pins calls == 3. That is the retry and
    # the re-raise, observed rather than described.
    #
    # What they did instead was ask whether the words "for attempt in range",
    # "tries" and "raise" appeared in the function's text. "raise" was MEASURED
    # passing with the re-raise deleted — it is in the docstring — and it stayed
    # green even read as mechanism, because a bare `raise` in an unrelated except
    # handler satisfies it too. A test that names the shape of the code is weaker
    # than one that runs it AND is broken by every rewrite that changes nothing.
    # Where both exist, the grep is decoration; keep the one with teeth.

    calls = 0

    def _client(bodies, finish="stop"):
        """A stand-in OpenAI client yielding `bodies` in turn (last one repeats)."""
        def create(**kw):
            nonlocal calls
            calls += 1
            return types.SimpleNamespace(choices=[types.SimpleNamespace(
                finish_reason=finish,
                message=types.SimpleNamespace(
                    content=bodies[min(calls - 1, len(bodies) - 1)]))])
        return lambda **kw: types.SimpleNamespace(
            chat=types.SimpleNamespace(
                completions=types.SimpleNamespace(create=create)))

    real_client, real_key = w.OpenAI, os.environ.get("OPENROUTER_API_KEY")
    os.environ["OPENROUTER_API_KEY"] = "test"
    try:
        w.OpenAI = _client(["Thinking about it...", "Still thinking...", sheet])
        got = w.ask_json("sys", "usr", _SCHEMA, prefer="api")
        check("a lane recovers from two bad draws in a row",
              got.get("frame") == "roots" and calls == 3, f"{got} after {calls} calls")

        calls = 0
        w.OpenAI = _client(["no object here"])
        stopped = False
        try:
            w.ask_json("sys", "usr", _SCHEMA, prefer="api")
        except (ValueError, json.JSONDecodeError):
            stopped = True
        check("...but a lane that never gets a sheet stops loudly", stopped)
        check("...after re-rolling, not on the first bad draw", calls == 3, f"{calls} calls")

        # A blown ceiling is NOT a bad draw. Re-rolling it burns three renders'
        # worth of tokens to hit the same wall — the 08-05 guard's whole point.
        calls = 0
        w.OpenAI = _client(["deliberating at length", sheet], finish="length")
        truncated = False
        try:
            w.ask_json("sys", "usr", _SCHEMA, prefer="api")
        except ValueError as e:
            truncated = "TRUNCATED" in str(e)
        check("a truncation fails loudly instead of being re-rolled blind",
              truncated and calls == 1, f"truncated={truncated} after {calls} calls")
    finally:
        w.OpenAI = real_client
        if real_key is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = real_key


def s66_json_mode_is_actually_sent(mk, kr, sb: Path):
    """Structured output, and the reason it needs a case at all (2026-08-18).

    Every JSON lane used to PROMPT for JSON and hope. The mandates always said
    "return ONLY a JSON object" and models wrapped it anyway, so `parse_llm_json`
    grew a five-strategy fallback chain out of four dated incidents, and the
    rotation lane measured 3 of 6 identical calls coming back prose-prefixed —
    which killed a 45-minute render at movement 5 of 15. `response_format`
    moves that from survivable-at-the-parser to impossible-at-the-API.

    Gate 7.2 — ADDING A PARAMETER IS ITSELF A SILENT NO-OP. If `response_format`
    is dropped, misspelled, or quietly removed in a refactor, every lane keeps
    working exactly as before: the model usually returns clean JSON anyway, the
    fallback chain catches the rest, and nothing fails. The regression would only
    show up as a render dying mid-tape weeks later. So the assertions are on what
    the REQUEST carries, not on what comes back.

    THE OTHER HALF is the text lanes. `rephrase_phonetic` asks for a
    transliteration, not an object, and the studio's writers return prose — a
    blanket sweep that forced JSON mode onto those would break them just as
    silently, in the other direction.

    THE CEILING RIDES ALONG (added 2026-08-18, the day's lint pass). `budget()`
    landed hours after `JSON_MODE` with the same silent-no-op shape and no guard
    at all — so the tail of this case asserts the other thing every MODEL request
    must carry. Same scan, same reason: a lane added later is caught without a
    test exercising it."""
    print("\n66. JSON mode is sent where it belongs — and every ceiling is budget() (2026-08-18)")
    import importlib.util

    # A PRISTINE copy of the module, not the shared one: `s3` replaces
    # `mk.decide` with a canned lambda and that stub is still standing this far
    # down the run, so the shared object would answer without ever reaching a
    # request. Loading the sandbox file again gives the real function bodies
    # without disturbing any stub the rest of the suite relies on.
    spec = importlib.util.spec_from_file_location("mk_pristine", mk.__file__)
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    # A pristine L3 too, for the TEXT half and for exactly the same reason: s57
    # stubs `wr.rephrase_phonetic` to a lambda and nothing tears it down, so the
    # shared object would answer without ever building a request. `fresh.decide`
    # is NOT covered by this — its `from writer import ask_json` resolves the
    # shared module out of sys.modules, so the JSON half is observed on `wr`.
    w_spec = importlib.util.spec_from_file_location(
        "wr_pristine", str(Path(mk.__file__).parent / "writer.py"))
    fresh_w = importlib.util.module_from_spec(w_spec)
    w_spec.loader.exec_module(fresh_w)

    # ── A client that records the request instead of making one. ─────────────
    calls = []

    def fake_client(*a, **kw):
        def create(**kwargs):
            calls.append(kwargs)
            body = '{"act": false, "modality": "silence", "move": "smoke", ' \
                   '"rationale": "smoke", "next_check_hours": 3, ' \
                   '"notification_body": "", "expected_target": "", ' \
                   '"target_revealed": false, "schedule": null}'
            msg = types.SimpleNamespace(content=body)
            choice = types.SimpleNamespace(message=msg, finish_reason="stop")
            return types.SimpleNamespace(choices=[choice])
        return types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))

    # THE OBSERVATION POINT MOVED WITH THE EXECUTOR (2026-08-23, Step 4 of the
    # spine refactor). Every JSON lane now asks through `writer.ask_json`, so the
    # client lives in writer and the fake has to be installed there — patching
    # morning_knock's namespace would watch a call site that no longer exists and
    # report green on nothing. Restored in the finally, exactly as s70 does.
    #
    # THE API BRANCH IS FORCED, and that is not a workaround: this case asserts
    # what the API REQUEST carries, and on a host with `claude` on PATH the agent
    # branch never builds a request at all. `have_agent()` is False on every cloud
    # runner, which is where this lane actually runs.
    real_env = os.environ.get("OPENROUTER_API_KEY")
    orig_openai, orig_which = fx.wr.OpenAI, fx.wr.shutil.which
    try:
        fx.wr.OpenAI = fresh_w.OpenAI = fake_client
        fx.wr.shutil.which = lambda n: None   # `shutil` is shared; this reaches both
        os.environ["OPENROUTER_API_KEY"] = "smoke"
        fresh.decide("smoke digest", [])
        check("the composer's request carries JSON mode",
              calls and calls[-1].get("response_format") == fx.wr.JSON_MODE,
              f"got {calls[-1].get('response_format') if calls else 'no call'}")
        check("...and it is the json_object form the lanes agreed on",
              fx.wr.JSON_MODE == {"type": "json_object"}, f"got {fx.wr.JSON_MODE}")

        # The text lane must stay text. Forcing an object out of a call that asks
        # for a transliteration is the same defect pointing the other way — and
        # since Step 4 it has its own executor (`ask_text`), whose whole job is to
        # carry the host rule WITHOUT carrying JSON_MODE.
        calls.clear()
        fresh_w.rephrase_phonetic("ரொம்ப நல்லாருக்கு")
        check("the phonetic rewrite does NOT ask for JSON — it returns a line",
              calls and "response_format" not in calls[-1], f"got {calls[-1] if calls else None}")
    finally:
        fx.wr.OpenAI, fx.wr.shutil.which = orig_openai, orig_which
        if real_env is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = real_env

    # ── Coverage across lanes, read off the SOURCE, so a lane added later
    # without JSON mode is caught even though no test exercises it. Mechanism
    # lines only (`code_line_numbers`), so a docstring quoting a call cannot
    # satisfy or break this.
    lanes = {
        # ZERO, and that is the assertion (2026-08-23, Step 4). These two lanes
        # held three of the five raw clients in the repo — decide(), the
        # production judge and the catch judge — each correct in Actions and each
        # billing cash on a local run. They ask through `writer.ask_json` now, so
        # "how many of this lane's create() calls send JSON mode" has become "this
        # lane does not make one", which is the stronger claim and the one the
        # executor rule is actually about.
        "scripts/morning_knock.py": 0,
        "scripts/knock_reply.py": 0,
        # ONE call now serves the soak sheet, the drill sheet, the drill lint
        # and every rotation movement (2026-08-23). Those four lanes used to
        # carry their own `create()`; they call `writer.ask_json` instead, so
        # this is where JSON mode has to be — and a lane that goes back to
        # rolling its own client is caught by s70, not here.
        "scripts/writer.py": 1,
    }
    for rel, want in lanes.items():
        src = (REAL_BASE / rel).read_text(encoding="utf-8")
        mech = code_line_numbers(src)
        lines = src.splitlines()
        creates = [i for i, ln in enumerate(lines, 1)
                   if "chat.completions.create" in ln and i in mech]
        # the call's kwargs run to the closing paren; scan the next few lines
        with_mode = 0
        for i in creates:
            window = "".join(lines[i - 1:i + 6])
            if "response_format" in window:
                with_mode += 1
        check(f"{rel}: {with_mode}/{len(creates)} JSON call(s) send response_format",
              with_mode == want, f"expected {want} of {len(creates)} create() calls")

    # The studio writers return PROSE on a different model — sweeping JSON mode
    # across every create() in the tree would have broken them.
    studio = mechanism((REAL_BASE / "scripts" / "run_studio.py")
                       .read_text(encoding="utf-8"))
    check("the studio's prose writer is left alone",
          "response_format" not in studio, "run_studio started asking for JSON")

    # ── THE CEILING LAW, THE SAME SCAN (2026-08-18, added in the lint pass that
    # closed the day). `budget()` and `JSON_MODE` landed hours apart with the
    # SAME failure shape, and only one of them got a guard. A raw `max_tokens`
    # on a MODEL call is a silent no-op in the most expensive way: the lane keeps
    # working until the model's reasoning happens to outgrow the literal, and
    # then it returns zero characters. That is exactly how the reply judge was
    # patched alone on 08-05 while the drill lane stayed wrong for 17 days.
    #
    # Read off the SOURCE for the same reason as above — a lane added later, or
    # a `budget()` quietly unwrapped in a refactor, is caught with no test
    # exercising it. Mechanism lines only, so the docstrings that QUOTE the
    # retired literals cannot satisfy or break this.
    ceiling_lanes = ["scripts/morning_knock.py", "scripts/knock_reply.py",
                     "scripts/render_drill.py", "scripts/render_soak.py",
                     "scripts/run_studio.py"]
    raw = []
    for rel in ceiling_lanes:
        lines = (REAL_BASE / rel).read_text(encoding="utf-8").splitlines()
        mech = code_line_numbers("\n".join(lines))
        for i, ln in enumerate(lines, 1):
            if i in mech and "max_tokens=" in ln and "max_tokens=budget(" not in ln:
                raw.append(f"{rel}:{i}")
    check(f"every MODEL call takes its ceiling from budget() ({len(ceiling_lanes)} lanes)",
          not raw,
          f"raw max_tokens at {', '.join(raw)} — a call site declares what its "
          f"ARTIFACT needs; REASONING_HEADROOM is the model's, added once")
    check("...and the headroom is big enough for the reasoning that was measured",
          fx.wr.REASONING_HEADROOM >= 3000, f"got {fx.wr.REASONING_HEADROOM}")


def s70_the_executor_is_chosen_by_the_host(sb: Path):
    """WHO PAYS, and the silent no-op that hid it for weeks (2026-08-23, Andrew).

    `render_soak`, `render_drill` and `render_rotation` each opened an OpenRouter
    client unconditionally. None of them has ever had a cloud caller — `anna.yml`
    invokes exactly four scripts — so every soak, drill and long-haul ran on the
    laptop and billed the API anyway, next to a subscription already paid for.
    Nothing failed. The artifact arrived every time. The only symptom was an
    invoice, which is not an instrument anything in this repo reads.

    Gate 7.2 — WHAT DOES THIS LOOK LIKE WHEN IT SILENTLY DOES NOTHING? It looks
    like success, twice over. (a) A lane that never asks which host it is on
    still produces a perfect sheet. (b) A lane that DOES ask, on a machine where
    the agent is present but broken — expired auth, a bad model string, a rate
    limit — falls back to the API and still produces a perfect sheet. Case (b) is
    the one this change introduces, so most of the teeth below are there: a
    degrade that costs money has to SAY it costs money, or the subscription path
    can be dead for a month and read green the whole time.

    THE CLOUD PATH IS DORMANT, NOT DEAD (Andrew, 2026-08-23) — the 08-18 routing
    rule is policy, not a missing capability. So these assertions prove the API
    branch still RUNS and is reachable; they never prove it is unused."""
    print("\n70. The executor is the host's, and a degrade to the paid API is loud (2026-08-23)")
    import contextlib
    import importlib
    import io
    import json as _json

    writer = importlib.import_module("writer")
    orig_which, orig_agent, orig_api = writer.shutil.which, writer._agent_json, writer._api_json
    ran = {}
    SHAPE = writer.obj(frame=writer.STR)

    def fake_agent(system, user, schema):
        ran["agent"] = True
        return {"ok": "agent"}

    def fake_api(system, user, answer_tokens):
        ran["api"] = True
        return {"ok": "api"}

    try:
        writer._agent_json, writer._api_json = fake_agent, fake_api

        # ── The host test decides, and it decides BOTH ways. Asserting only the
        # laptop branch would pass just as well on a module hardwired to it.
        writer.shutil.which = lambda n: r"C:\fake\claude.exe" if n == "claude" else None
        ran.clear()
        writer.ask_json("system", "user", SHAPE)
        check("an agent on PATH -> the subscription executor runs",
              ran == {"agent": True}, f"ran {ran}")

        writer.shutil.which = lambda n: None
        ran.clear()
        writer.ask_json("system", "user", SHAPE)
        check("no agent (every cloud runner) -> the API executor runs",
              ran == {"api": True}, f"ran {ran}")

        # ── THE TEETH. A present-but-broken agent must still deliver the
        # artifact AND announce what it just cost. Assert the effect (the money
        # warning reached stdout), not the execution (that a fallback happened).
        writer.shutil.which = lambda n: r"C:\fake\claude.exe"
        writer._agent_json = lambda system, user, schema: (_ for _ in ()).throw(
            RuntimeError("claude -p exit 1: credentials expired"))
        ran.clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = writer.ask_json("system", "user", SHAPE)
        said = buf.getvalue()
        check("a broken agent still returns the artifact",
              out == {"ok": "api"} and ran == {"api": True}, f"got {out}, ran {ran}")
        check("...and the degrade says, out loud, that this run costs money",
              "PAID" in said and "money" in said.lower(), f"said: {said[:200]!r}")
        check("...and names the underlying failure, not just the fallback",
              "credentials expired" in said, f"said: {said[:200]!r}")
    finally:
        writer.shutil.which, writer._agent_json, writer._api_json = orig_which, orig_agent, orig_api

    # ── THE ENVELOPE, and why `schema` is a required positional argument.
    # MEASURED 2026-08-23 on the first live soak through this module: handed a
    # schema with no `properties`, `claude -p` answered
    # {"output": "<the whole real sheet as a JSON string>", "clusters": []}.
    # That parses. It carries the key the lane reads. render_soak filtered zero
    # clusters from it, printed "0 threads, 0 items", and would have rendered an
    # empty tape — the artifact-shaped nothing this suite exists to catch.
    class _Proc:
        returncode, stderr = 0, ""
        stdout = _json.dumps({"output": _json.dumps({"beats": [{"say": "x"}]}),
                              "beats": []})
    orig_run = writer.subprocess.run
    try:
        writer.subprocess.run = lambda *a, **k: _Proc()
        raised = ""
        try:
            writer._agent_json("system", "user", SHAPE)
        except RuntimeError as e:
            raised = str(e)
        check("an {'output': '<json string>'} envelope is REFUSED, not returned",
              "ENVELOPE" in raised, f"got {raised[:160]!r}")
        check("...and the refusal names the schema as the cause",
              "schema" in raised.lower(), f"got {raised[:160]!r}")

        # The guard must not fire on real work: an `output` key holding an
        # OBJECT is a legitimate artifact, not an envelope.
        _Proc.stdout = _json.dumps({"output": {"real": True},
                                    "beats": [{"say": "x"}]})
        ok = writer._agent_json("system", "user", SHAPE)
        check("...but a real artifact with an object-valued key passes through",
              ok.get("beats") == [{"say": "x"}], f"got {ok}")
    finally:
        writer.subprocess.run = orig_run

    # ── THE ONE BOUNDARY THAT IS NOT CREDENTIAL-GATED (2026-08-24) ──────────
    # Every other outside-world call here needs a secret the test environment
    # does not have, so a missed stub dies with a KeyError and the case goes red.
    # `claude -p` needs none — the CLI carries its own auth — so a missed stub
    # would really spawn the agent and could return a plausible answer that turns
    # the case GREEN for the wrong reason. The harness refuses that spawn; this
    # asserts the refusal fires, because a guard that never fires is
    # indistinguishable from no guard.
    raised = ""
    try:
        writer._agent_json("system", "user", SHAPE)   # the REAL subprocess.run
    except AssertionError as e:
        raised = str(e)
    check("an un-stubbed agent spawn is REFUSED, never run",
          "SPAWN THE REAL AGENT" in raised, f"got {raised[:150]!r}")
    check("...and the refusal names what to stub instead",
          "writer.ask_json" in raised, f"got {raised[:250]!r}")

    # And it must survive `ask_json`'s degrade-to-API fallback. That handler
    # catches SubprocessError/RuntimeError/OSError and quietly switches to the
    # paid path — exactly the shape that would turn this refusal back into a
    # silent no-op, one layer up.
    orig_which2 = writer.shutil.which
    try:
        writer.shutil.which = lambda n: r"C:\fake\claude.exe"
        swallowed = True
        try:
            writer.ask_json("system", "user", SHAPE)
        except AssertionError:
            swallowed = False
        check("...and ask_json's fallback does not swallow it into a paid run",
              not swallowed, "the refusal was caught and the lane degraded silently")
    finally:
        writer.shutil.which = orig_which2

    # ── Every lane declares a SHAPE, not a bare object — the schema is the only
    # thing standing between the agent path and an envelope.
    for name, const in (("render_soak.py", "SOAK_SCHEMA"),
                        ("render_drill.py", "DRILL_SCHEMA"),
                        ("render_rotation.py", "MOVEMENT_SCHEMA")):
        shape = getattr(importlib.import_module(name[:-3]), const, None)
        check(f"{const} declares properties, not a bare object",
              bool((shape or {}).get("properties")), f"got {shape}")

    # ── The two constants cannot be swapped. `claude -p --model` takes a BARE
    # slug; handed a vendor-qualified one it prints "may not exist" and RETURNS
    # 0 (measured 2026-08-23 with claude-sonnet-4.6), so the wrong value here
    # does not crash — it silently routes every laptop lane to the paid API.
    check("OPENROUTER_MODEL is a vendor-qualified slug (the API's shape)",
          "/" in fx.wr.OPENROUTER_MODEL, f"OPENROUTER_MODEL={fx.wr.OPENROUTER_MODEL}")
    check("AGENT_MODEL is a bare slug (the claude CLI's shape)",
          "/" not in fx.wr.AGENT_MODEL, f"AGENT_MODEL={fx.wr.AGENT_MODEL}")

    # ── No lane may re-earn its own client. This is the regression that started
    # it: four independent call sites, three of which never chose a host at all.
    # smoke_test.py builds stub clients by the dozen — that is its job, and it is
    # already CODE_BUDGET_EXEMPT for the same reason.
    #
    # TIGHTENED 2026-08-24. This list was written before Step 4 and still named
    # `morning_knock` and `knock_reply`, which stopped building clients IN that
    # step — so the two daily-driver lanes were free to regrow the exact defect
    # this case exists to catch, and it would have read green. An allowlist that
    # outlives what it allowed is not a guard. `run_studio` stays and is the only
    # one: its cloud pass wants PROSE, and `writer` offers `ask_json`/`ask_text`
    # over a chat-completions shape it does not use — but its HOST choice is
    # `writer.have_agent()` now, which is the part that was duplicated.
    may_build = {"writer.py", "run_studio.py", "smoke_test.py"}
    offenders = sorted(f.name for f in (sb / "scripts").glob("*.py")
                       if f.name not in may_build
                       and "OpenAI(" in f.read_text(encoding="utf-8"))
    check("no lane builds its own OpenRouter client",
          not offenders, f"{', '.join(offenders)} — call writer.ask_json instead")

    for name in ("render_soak.py", "render_drill.py", "render_rotation.py"):
        src = mechanism((sb / "scripts" / name).read_text(encoding="utf-8"))
        check(f"{name} takes its executor from writer",
              "from writer import" in src, "imports ask_json from somewhere else")

    # ── THE PORT SURFACE IS ONE FILE, OR IT IS NOT A PORT SURFACE ───────────
    #
    # 2026-08-24 said "one LINE" and guarded the script range: `state_io`
    # carried the comment "a fork to another language replaces this regex" while
    # three other files carried the same character range anyway. That guard
    # worked and is kept. What it could not see is the shape of its own needle.
    #
    # 2026-08-28: `run_studio.TAMIL_TAIL_RE` — Tamil vowel signs plus the pulli,
    # for stem-tolerant payload matching — is a SECOND script range, sharing no
    # characters with the first. It landed 2026-08-18, sat through the 08-24
    # sweep, and passed this case every run, because a guard that needles one
    # value proves one value. A port that changed the labelled range would have
    # gone on stemming Tamil. Two more values were in the same position and
    # nothing was looking at all: the pinned voices (declared in `render_audio`,
    # re-exported to six lanes) and the repo identity (spelled out three times
    # across `publish` and `rebuild_rss`).
    #
    # So the needle list is no longer written here — it is READ OFF the pack, one
    # needle per public value. Adding a value to `language.py` arms this case for
    # it automatically, which is the property the 08-24 version lacked and the
    # only reason that drift was possible.
    #
    # GATE 7.2 — WHAT DOES THIS LOOK LIKE WHEN IT SILENTLY DOES NOTHING? It looks
    # like every green run this case has ever had. An empty needle list, a pack
    # that failed to import, a glob that matched nothing: all of them pass every
    # assertion below while checking zero values. So the first check is teeth on
    # the NEEDLES, not on the law.
    def pack_needles(mod):
        """{NAME: the literal a fork replaces} for every public value in the
        pack. A compiled regex contributes its pattern; a str contributes
        itself. Anything else is mechanism and does not belong here."""
        out = {}
        for n in dir(mod):
            if not n.isupper():
                continue
            v = getattr(mod, n)
            if hasattr(v, "pattern"):
                out[n] = v.pattern
            elif isinstance(v, str):
                out[n] = v
        return out

    def second_homes(needles, files):
        """[(NAME, filename)] for every needle found in a file's MECHANISM lines
        — comments and docstrings are free, so the paragraph above may quote what
        it forbids. `files` is [(name, source)]."""
        found = []
        for fname, fsrc in files:
            mech = code_line_numbers(fsrc)   # once per FILE — it re-parses
            body = [ln for i, ln in enumerate(fsrc.splitlines(), 1) if i in mech]
            for name, needle in needles.items():
                if any(needle in ln for ln in body):
                    found.append((name, fname))
        return found

    needles = pack_needles(fx.lang)
    check(f"the pack yielded needles to check ({len(needles)} values)",
          len(needles) >= 6 and "TAMIL_TAIL_RE" in needles,
          f"got {sorted(needles)} — a needle list that comes back empty or short "
          f"makes every assertion below pass while proving nothing; the count is "
          f"a floor, not a target")

    # An occurrence that is allowed to exist, each carrying WHY — the same
    # mechanism UP_EXCEPTIONS runs on, and the same law: it may only shrink.
    PACK_EXEMPTIONS = {
        ("ANNA_VOICE", "render_audio.py"):
            "the episode voice POOLS are a catalogue and the pinned voice is a "
            "choice FROM it — `_CHIRP_POOL_MALE` legitimately lists Orus among "
            "sixteen. A catalogue entry is not a second declaration of the pin.",
        ("EAVESDROP_VOICE", "render_audio.py"):
            "same: `_CHIRP_POOL_FEMALE` lists Kore among fourteen.",
    }

    others = [(f.name, f.read_text(encoding="utf-8"))
              for f in sorted((sb / "scripts").glob("*.py"))
              if f.name != "language.py"]
    found = second_homes(needles, others)
    copies = sorted(f"{n} in {f}" for n, f in found if (n, f) not in PACK_EXEMPTIONS)
    check("every language value is declared ONCE, in the pack",
          not copies, f"a second home for {', '.join(copies)} — import it from "
                      f"`language` instead, or declare an exemption with a reason")

    # The guard's own guard: an exemption whose occurrence is gone is a licence
    # nothing revokes ("an allowlist that outlives what it allowed is not a
    # guard", 2026-08-24). Handing it back is part of landing the fix.
    stale = sorted(k for k in PACK_EXEMPTIONS if k not in set(found))
    check("every declared pack exemption still describes a real occurrence",
          not stale, "gone: " + "; ".join(f"{n} in {f}" for n, f in stale)
                     + " — delete the exemption with it")

    # THE POSITIVE CONTROL — a sweep that can never fire reads green on a tree
    # that has drifted. Driven on a synthetic file, so the proof lives in the
    # suite permanently instead of in one session's notes.
    # The prose exemption is WHOLE-LINE comments and docstrings only — a needle
    # in a trailing comment still counts, and that asymmetry is deliberate:
    # `code_line_numbers` filters by LINE, so the conservative direction is the
    # safe one (a copy cannot hide behind a trailing `#`), while the paragraphs
    # above this case — which quote every value they forbid — sit on lines of
    # their own and are free. Asserting all three, because the first version of
    # this control asserted the trailing case backwards and went red.
    planted = second_homes(
        {"PIN": "zz-QQ-Sentinel"},
        [("copy_lane.py", 'PIN = "zz-QQ-Sentinel"\n'),
         ("trailing_lane.py", 'X = 1  # zz-QQ-Sentinel\n'),
         ("prose_lane.py", '"""zz-QQ-Sentinel in a docstring."""\n'
                           '# zz-QQ-Sentinel in a comment\n'
                           'X = 1\n')])
    check("the sweep finds a planted second home",
          ("PIN", "copy_lane.py") in planted,
          f"{planted} — a sweep that cannot find a planted copy reads green on "
          f"a tree that has already drifted")
    check("...and prose that quotes a value is free, while a trailing # is not",
          ("PIN", "prose_lane.py") not in planted
          and ("PIN", "trailing_lane.py") in planted,
          f"{planted} — if the docstring counted, this case's own paragraphs "
          f"would fail it; if the trailing comment did not, a copy could hide")

    # ── THE THIRD FAMILY'S WHOLE DECLARATION (2026-08-24) ────────────────────
    # `push_queue` is pure delivery: ZERO model calls at fire time, by design.
    # What it fires was composed at ADD time and is only RENDERED at fire time
    # (2026-07-24) — that is the property that keeps the lock screen fast, and
    # the retired spine-refactor plan stated it as a hard constraint on Q1: "push_queue
    # must never be given a writer stage" (docs/spine_refactor.md §4b, deleted 2026-08-26
    # once executed; recover it from git if the reasoning is needed).
    #
    # It was stated and never enforced. The client check above only catches
    # `OpenAI(`, so this lane could have grown `from writer import ask_json` and
    # called it while Andrew waited at the lock screen, and nothing here would
    # have noticed. Read off the SOURCE, mechanism lines only, so the docstring
    # that explains the rule cannot satisfy or break it.
    pq_code = mechanism((sb / "scripts" / "push_queue.py").read_text(encoding="utf-8"))
    called = sorted(w for w in ("ask_json", "ask_text", "OpenAI(", "have_agent")
                    if w in pq_code)
    check("the delivery lane makes NO model call — composed at add time, "
          "rendered at fire time",
          not called, f"push_queue.py reaches for {', '.join(called)} — a writer "
                      f"stage here puts a model call between Andrew's tap and his "
                      f"lock screen, and the dose was already written")


# Files allowed to carry target-script characters on a MECHANISM line, each with
# a ceiling and a reason. A ratchet, not an allowlist: the count may fall, never
# rise, and an owner that drops to zero has lost its claim and must hand the
# entry back (the same law `PACK_EXEMPTIONS` runs on).
SCRIPT_OWNERS = {
    "mandates.py": (11,
        "LLM PROMPT PROSE — the declared irreducible half of an extraction. "
        "`BOOTSTRAP.md` and `/extend` Gate 6 have said since 2026-07 that a port "
        "REWRITES these worked examples rather than substituting a constant into "
        "them: the -ōm ending, the honorific -nga, `புரியல` as a creditable "
        "repair. There is no seam that makes this cheaper and pretending "
        "otherwise would hide the real cost of a port."),
    "run_studio.py": (2,
        "The PRODUCER pass's dialect rule, same class as `mandates` — it states "
        "where the polite -ங்க may attach, inside the prompt that enforces it. "
        "It sits here rather than in `mandates` because `run_studio`'s three "
        "writer prompts are the studio's own canon (s70 asserts the studio is "
        "left alone by the JSON sweep for the same reason)."),
    "sync_state.py": (6,
        "Five rows are the ONE-SHOT REPAIR SLOT (`cmd_untaught`, 2026-09-01, "
        "driven by s88) — a migration payload, not a port value, and it is "
        "replaced wholesale by the next repair rather than edited. The sixth is "
        "`add-word`'s help text, where the example MUST be script because the "
        "argument is the canonical key: a phonetic example there would advertise "
        "an input `is_tamil` refuses."),
}


def s91_the_pack_is_complete_not_just_unique(sb: Path):
    """A language fact outside the pack is invisible to the needle guard
    (2026-09-03, Andrew — tier 1 of the narrow-extraction scope).

    WHAT THE 08-28 GUARD PROVES, AND WHAT IT CANNOT. `pack_needles` reads every
    public value off `language.py` and fails the build if one acquires a second
    home. That is a UNIQUENESS proof, and it is airtight: a declared value has
    one declaration. It says nothing whatever about a language fact that was
    never declared in the pack at all — the needle list is read off the pack, so
    a fact the pack has never heard of contributes no needle to look for.

    FOUR LIVED THERE, and one was a defect rather than a filing error:

      - `render_audio` classified Tamil with `any('...' <= c <= '...' for c in w)`
        at TWO sites and imported NOTHING from `language`. Functionally
        `is_tamil`, spelled as a character comparison, so the needle — which
        looks for the literal pattern text — could not match it. That is the
        08-28 finding repeating exactly: "a guard that needles one value proves
        one value." A port that edited `language.py` would have gone on
        classifying Tamil in the renderer.
      - `morning_knock.REFERENT_NOUNS` — 26 rows of Tamil kinship culture in L5.
      - `render_rotation` stripped the pulli with a literal.
      - `rebuild_rss` held the feed's name and pitch, each with exactly ONE home,
        which is why the 08-28 duplicate-hunt walked past them. A port surface is
        what a fork must CHANGE, not what happens to be duplicated twice.

    GATE 7.2 — WHAT DOES THIS LOOK LIKE WHEN IT SILENTLY DOES NOTHING? Like a
    green suite and a Korean tutor that titles its feed "Coimbatore Mappillai",
    matches Tamil aunties in its tapes, and stems Tamil in its rotation — every
    instrument reading green, because nothing was ever asserted about facts
    nobody had declared. So the FIRST check is teeth on the sweep itself: a glob
    that matches nothing, or a scan that finds script nowhere, satisfies every
    assertion below while proving zero.
    """
    print("\n91. The pack is complete, not merely unique (2026-09-03)")
    SCRIPT = fx.lang.TAMIL_RE

    def script_lines(src: str) -> list[int]:
        mech = code_line_numbers(src)
        return [i for i, ln in enumerate(src.splitlines(), 1)
                if i in mech and SCRIPT.search(ln)]

    files = {p.name: p.read_text(encoding="utf-8")
             for p in sorted((sb / "scripts").glob("*.py"))
             if p.name != "language.py"}          # the pack IS the declared home
    found = {name: script_lines(src) for name, src in files.items()}
    found = {name: lines for name, lines in found.items() if lines}

    # ── TEETH ON THE SWEEP, before any law is asserted on its output.
    check(f"the sweep read the lane files ({len(files)} scanned)",
          len(files) >= 20 and "morning_knock.py" in files,
          f"got {len(files)} files — a glob that matches nothing passes "
          f"everything below while checking zero lanes")
    check("...and it can still SEE script where script legitimately lives",
          "mandates.py" in found and len(found["mandates.py"]) >= 5,
          f"found {sorted(found)} — a scan that detects script nowhere is not a "
          f"clean tree, it is a broken detector")

    # ── THE LAW. Any file that is not a declared owner must carry none.
    trespass = sorted(f"{n} ({len(l)} lines: {l[:4]})"
                      for n, l in found.items() if n not in SCRIPT_OWNERS)
    check("no lane declares a language fact of its own",
          not trespass,
          f"{'; '.join(trespass)} — move the value into `language.py` and import "
          f"it, or add a SCRIPT_OWNERS entry with a reason it cannot move")

    # ── THE RATCHET. An owner may shrink; it may never grow.
    over = sorted(f"{n}: {len(found.get(n, []))}/{cap}"
                  for n, (cap, _) in SCRIPT_OWNERS.items()
                  if len(found.get(n, [])) > cap)
    check("no declared owner grew past its ceiling",
          not over,
          f"{', '.join(over)} — a new language fact went into a file that already "
          f"had a reason for its old ones; the reason does not cover the new line")

    # ── THE GUARD'S OWN GUARD. A licence that outlives what it licensed is a
    # licence nothing revokes (2026-08-24).
    stale = sorted(n for n in SCRIPT_OWNERS if not found.get(n))
    check("every declared script owner still holds script",
          not stale,
          f"gone: {', '.join(stale)} — hand the SCRIPT_OWNERS entry back in the "
          f"diff that emptied the file")

    # ── POSITIVE CONTROL, driven on synthetic sources so the proof lives in the
    # suite rather than in one session's notes. Prose is free; mechanism is not.
    planted = script_lines('X = "வை"\n')
    free = script_lines('"""வை in a docstring."""\n'
                        '# வை in a comment\nX = 1\n')
    check("the sweep finds script planted on a mechanism line", planted == [1],
          f"got {planted} — a sweep that cannot find a planted fact reads green "
          f"on a tree that has already drifted")
    check("...and prose that quotes script is free",
          free == [],
          f"got {free} — if the docstring counted, this case's own paragraphs "
          f"and every port note in the tree would fail it")


# Where LLM prompt canon lives, and therefore what a port must REWRITE. Named in
# `BOOTSTRAP.md` -> Layer 1 and in `/extend` Gate 6; `s93` holds those two prose
# lists to this dict, in both directions.
PROMPT_HOMES = {
    "mandates.py":
        "the fourteen mandates and addenda. Prompt canon, split out of "
        "`morning_knock` on 2026-08-01 and `knock_reply` on 2026-08-24, both "
        "times because the lane hit its code-line ceiling.",
    "run_studio.py":
        "the studio's own DIRECTOR / ARCHITECT / PRODUCER. They stay out of "
        "`mandates` because the studio's canon is its own — the same reason "
        "`s70` leaves the studio alone in its JSON sweep.",
}

# Prompt-shaped, and NOT port surface: a big prompt string is not automatically a
# language fact. Each entry states why a fork changes nothing here. This list can
# only shrink -- `s93` hands the licence back when a file stops matching.
PROMPT_AGNOSTIC = {
    "render_drill.py":
        "COMMISSION_BRIEF — repair-vs-routine dosing (three cues per repaired "
        "item, vary the situation never the target). Pure pedagogy; names no "
        "language. The DRILL prompt itself is in `mandates`.",
    "render_soak.py":
        "FOCUS_BRIEF — the carousel shape (one root or one ending per cluster, "
        "contrast is the lesson). True of any inflecting language.",
    "render_payoff.py":
        "PAYOFF_BRIEF — numbered lines in, one plain-English meaning per number "
        "out. It names no language, no script and no morphology, because the "
        "lane hands the model the tape rather than asking it to write one: a "
        "fork changes the tape and changes nothing here.",
    "rebuild_rss.py":
        "RSS_TEMPLATE / ITEM_TEMPLATE — XML scaffolding, not a prompt at all. "
        "The feed's NAME and pitch are language facts and already live in the "
        "pack (`s91`, 2026-09-03).",
}

PORT_PROSE = (
    ("BOOTSTRAP.md", "**LLM prompts embedded in the Python.**"),
    (".claude/skills/extend/SKILL.md", "| LLM prompts with Tamil-specific prose rules"),
)


def _prompt_constants(src: str) -> list[str]:
    """Module-level ALL-CAPS names bound to a long multi-line string literal —
    the shape of an LLM prompt. Deliberately structural rather than name-matching
    on `*_MANDATE`: the studio's prompts are DIRECTOR / ARCHITECT / PRODUCER and
    would walk straight past a name rule."""
    out = []
    for node in ast.parse(src).body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
        if not (isinstance(target, ast.Name) and target.id.isupper()):
            continue
        if any(isinstance(d, ast.Constant) and isinstance(d.value, str)
               and len(d.value) > 200 and "\n" in d.value for d in ast.walk(node)):
            out.append(target.id)
    return out


def s93_the_port_surface_list_names_the_real_files(sb: Path):
    """The prose port-surface list is held to the tree (2026-09-04).

    WHAT IT CAUGHT. `BOOTSTRAP.md` -> Layer 1, `/extend` Gate 6 and
    `extend/references/routing.md` all named `morning_knock.py`,
    `knock_reply.py` and `render_drill.py` as the homes of the Tamil-specific
    LLM prompts. Every one of those prompts had left: `morning_knock`'s went to
    `mandates.py` on 2026-08-01 and `knock_reply`'s six followed on 2026-08-24,
    so all three carry `from mandates import ...` and no prompt prose at all. The
    list stayed wrong for a month. `BOOTSTRAP.md` is the file a FORK reads, so
    the cost was not cosmetic: a porter following it rewrote three files that
    hold nothing and never opened the one that holds everything.

    WHY `s91` COULD NOT CATCH IT. That guard sweeps for Tamil SCRIPT on a
    mechanism line and its `SCRIPT_OWNERS` ratchet is correct and current. But
    half of what makes these prompts port surface is written in ROMAN letters —
    the `-ōm` ending, the honorific `-nga`, "Woven Thanglish", the
    script-vs-phonetic rule. A script sweep is structurally blind to a fact about
    Tamil spelled in English, which is exactly why the prose list has to exist.
    This guard therefore checks the FILE NAMES, which are checkable, and makes no
    claim about the rules, which are not.

    WHY NOT KEY ON `*_MANDATE`. Because the studio's three prompts are not named
    that, and a name rule would have declared `run_studio.py` clean. The scan is
    structural — an ALL-CAPS module global bound to a long multi-line string —
    which also means it finds prompt constants that are NOT language facts, so
    every prompt-bearing file must be classified either a home or an exemption
    with a reason. `render_drill.COMMISSION_BRIEF` and `render_soak.FOCUS_BRIEF`
    are the live proof that "big prompt string" and "port surface" are different
    questions.

    GATE 7.2 — WHAT DOES THIS LOOK LIKE SILENTLY DOING NOTHING? Like a green
    suite and a fork whose tutor still says `-nga`. A scan that parses no files,
    or an anchor that matches no line, satisfies every assertion below while
    proving zero — so the teeth come first.
    """
    print("\n93. The port-surface list names the files that hold the prompts (2026-09-04)")
    found = {p.name: _prompt_constants(p.read_text(encoding="utf-8"))
             for p in sorted((sb / "scripts").glob("*.py"))}
    found = {n: c for n, c in found.items() if c}

    # ── TEETH ON THE SCAN, before any law is asserted on its output.
    check(f"the scan parsed the lanes and found prompt canon ({len(found)} files)",
          len(found) >= 4 and len(found.get("mandates.py", [])) >= 10,
          f"got {({n: len(c) for n, c in found.items()})} — a scan that finds no "
          f"prompts passes every assertion below while checking nothing")

    # ── 1. every prompt-bearing file is classified, one way or the other.
    unclassified = sorted(set(found) - set(PROMPT_HOMES) - set(PROMPT_AGNOSTIC))
    check("every file holding a prompt is declared a home or an exemption",
          not unclassified,
          f"{', '.join(unclassified)} — add it to PROMPT_HOMES and name it in the "
          f"port-surface prose, or to PROMPT_AGNOSTIC with a reason a fork "
          f"changes nothing in it")

    # ── 2. the guard's own guard: a licence that outlives what it licensed.
    stale = sorted(n for n in (*PROMPT_HOMES, *PROMPT_AGNOSTIC) if n not in found)
    check("every declared prompt file still holds a prompt",
          not stale,
          f"gone: {', '.join(stale)} — hand the entry back in the diff that "
          f"emptied the file, and fix the prose that still names it")

    # ── 3. THE LAW, in both directions, against the prose a porter actually reads.
    for rel, anchor in PORT_PROSE:
        text = (sb / rel).read_text(encoding="utf-8")
        line = next((ln for ln in text.splitlines() if anchor in ln), None)
        check(f"{rel}: the port-surface passage is still there",
              line is not None,
              f"no line contains {anchor!r} — the anchor moved, so the two "
              f"assertions below would pass on an empty string")
        if line is None:
            continue
        named = set(re.findall(r"([a-z_]+\.py)", line))
        check(f"{rel}: names every file that holds prompt canon",
              set(PROMPT_HOMES) <= named,
              f"missing {sorted(set(PROMPT_HOMES) - named)} — a fork reads this "
              f"line and rewrites what it names")
        check(f"{rel}: names no file that holds none",
              not (named - set(PROMPT_HOMES)),
              f"{sorted(named - set(PROMPT_HOMES))} hold no prompt canon — this "
              f"is the 2026-08-01/08-24 rot exactly: the prompts moved and the "
              f"list did not")

    # ── POSITIVE CONTROL, on a synthetic line so the proof lives in the suite.
    rotted = set(re.findall(r"([a-z_]+\.py)", "prompts live in `scripts/render_drill.py`"))
    check("...and the check would actually fail on a stale line",
          bool(rotted - set(PROMPT_HOMES)),
          "the extraction cannot see a filename, so its green means nothing")
