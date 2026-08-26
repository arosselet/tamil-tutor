"""L3 — composition: what the model is asked, and what comes back.

The parse layer (prose-wrapped JSON, code fences, single-quoted dicts, a
response truncated mid-word), the request layer (JSON mode actually reaching
the wire), and the choice of executor — agent or raw client — by host.

These are the cases that guard the seam between this system and a model, which
is the seam that fails quietly: a parse that raises looks the same as a budget
that ran out, and a stub that stops intercepting reaches the real agent.
"""
import importlib
import json
import os
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
    flip per call, and a long-haul tape makes ~15 calls in a row.

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
    sheet = '{"frame": "roots", "beats": [{"ta": "x", "en": "y", "who": "anna"}]}'

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
              'prose\n{"frame": "f", "beats": [{"ta": "1"}, {"ta": "2"}, {"ta": "3"}]}'
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
    # how 07-13 came back on 08-10; the long-haul lane borrows this one in turn.
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
    _lh = mechanism((REAL_BASE / "scripts" / "render_longhaul.py").read_text(encoding="utf-8"))
    check("the long-haul lane borrows ask_json rather than rolling its own",
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
    long-haul lane measured 3 of 6 identical calls coming back prose-prefixed —
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
        # and every long-haul movement (2026-08-23). Those four lanes used to
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

    `render_soak`, `render_drill` and `render_longhaul` each opened an OpenRouter
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
        stdout = _json.dumps({"output": _json.dumps({"beats": [{"ta": "x"}]}),
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
                                    "beats": [{"ta": "x"}]})
        ok = writer._agent_json("system", "user", SHAPE)
        check("...but a real artifact with an object-valued key passes through",
              ok.get("beats") == [{"ta": "x"}], f"got {ok}")
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
                        ("render_longhaul.py", "MOVEMENT_SCHEMA")):
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

    for name in ("render_soak.py", "render_drill.py", "render_longhaul.py"):
        src = mechanism((sb / "scripts" / name).read_text(encoding="utf-8"))
        check(f"{name} takes its executor from writer",
              "from writer import" in src, "imports ask_json from somewhere else")

    # ── THE PORT SURFACE IS ONE LINE, OR IT IS NOT A PORT SURFACE (2026-08-24).
    # `state_io` carries the comment "a fork to another language replaces this
    # regex" and, until today, three other files carried the same character range
    # anyway: an exact duplicate in `run_studio`, an inline `re.findall` twelve
    # lines below it, and `writer.TAMIL_RUN`. A forked repo would have changed the
    # labelled one, passed every test, and kept matching Tamil in three places.
    #
    # The needle is READ OFF `state_io` rather than written here, so this case
    # cannot itself become the fifth copy, and mechanism-only so the paragraph
    # above may quote what it forbids.
    needle = fx.si.TAMIL_RE.pattern
    copies = []
    for f in sorted((sb / "scripts").glob("*.py")):
        if f.name == "state_io.py":
            continue
        fsrc = f.read_text(encoding="utf-8")
        mech = code_line_numbers(fsrc)   # once per FILE — it re-parses the source
        if any(needle in ln for i, ln in enumerate(fsrc.splitlines(), 1)
               if i in mech):
            copies.append(f.name)
    check("the Tamil script range is declared ONCE, in the file labelled PORT SURFACE",
          not copies, f"a second copy lives in {', '.join(copies)} — import "
                      f"TAMIL_RE / TAMIL_RUN from state_io instead")

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
