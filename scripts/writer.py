#!/usr/bin/env python3
"""WHO MAKES THE CALL — the one place that chooses an executor for a JSON lane.

THE RULE (2026-08-23, Andrew): the laptop has an agent with a subscription already
paid for; a GitHub runner has neither. So a lane running on the laptop spends
tokens Andrew has already bought, and a lane running in Actions spends cash. That
is a HOST difference, decided HERE, once, by asking whether the binary exists —
never by a lane, never by a flag someone has to remember to pass.

WHAT THIS REPLACES: three lanes that never chose at all. `render_soak`,
`render_drill` and `render_rotation` each opened an OpenRouter client
unconditionally, on every host — and none of them has ever had a cloud caller
(`anna.yml` invokes exactly four scripts: `push_queue`, `knock_reply`,
`sync_state`, `morning_knock`). Every soak, drill and long-haul since the lanes
were written has been billed to the API from a machine sitting on an unused
subscription. `run_studio` got this split on 2026-08-18 and got it right; the
mistake was reading it as a rule about EPISODES. It was always a rule about hosts.
Measured at the time of the fix, per run: soak ~$0.06, drill ~$0.09, long-haul
~$0.84 (15 sequential movement calls). All three go to $0 on the laptop.

THE CLOUD PATH IS DORMANT, NOT DEAD (Andrew, 2026-08-23). Nothing prohibits or
lacks an implementation for a render in the cloud — the 08-18 routing rule is
POLICY, and policy can be changed by editing a workflow. So `_api_json` below is
a first-class branch that must keep working, not an error path: it is what runs
the day a render is routed to Actions. Test it by forcing it, never by deleting
it.

STRUCTURED OUTPUT SURVIVES THE CROSSING, which is the reason this split was
safe to make at all. The five JSON lanes depend on `JSON_MODE`
(`response_format: json_object`), added 2026-08-18 to make prose-wrapped JSON
impossible at the API instead of survivable at the parser. `claude -p` has the
same capability under a different name — `--json-schema` — and it is strictly
stronger: `json_object` guarantees only that the bytes parse, a schema
constrains the shape. VERIFIED before this landed: with a schema the CLI emits a
bare object on stdout, no fence and no preamble. A generic `{"type": "object"}`
is used rather than a per-lane schema so the two executors carry the SAME
contract — anything narrower would make the agent path reject payloads the API
path accepts, which is a model difference wearing a host difference's clothes.

THE PROMPT GOES DOWN STDIN, not argv. Windows caps a command line near 32,767
characters and these prompts inline `persona.md` (~11.7 KB) before their own
mandate and menu — a rotation movement lands around 14 KB, close enough that a
persona edit could push a lane over it and produce a failure that looks like the
agent being unavailable. Stdin has no such ceiling.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# MODULE-LEVEL ON PURPOSE, not tidied into `_api_json`. Smoke `s58` swaps this
# name for a stub client to prove the five-strategy parser recovery still works
# end to end; a function-local import would leave that case with nothing to
# grab. The seam moved here with `ask_json` (2026-08-23) and must stay reachable.
from openai import OpenAI

from language import TAMIL_RUN
from mandates import PHONETIC_REWRITE

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
OPENROUTER_BASE = "https://openrouter.ai/api/v1"   # OpenAI-compatible; one key, many models
MODEL = "google/gemini-3.8-flash"   # cloud Anna. A full slug — nothing derives it.
OPENROUTER_MODEL = MODEL            # kept as a name because five lanes import it
AGENT_MODEL = "claude-sonnet-5"     # what `claude -p` runs on the laptop

# ONE MODEL PER EXECUTOR (2026-08-23, Andrew). REPLACES "one model, two
# executors" (2026-08-18) and its `f"anthropic/{MODEL}"` derivation. That rule
# said the host may differ but the model may not, and it was right for a world
# with one vendor in it. `claude -p` is Claude-only by construction, so the
# moment the API side leaves Anthropic the two CANNOT be the same string. What
# the 08-18 rule actually defends is kept: the model is STATED, once per
# executor, never derived and never re-guessed at a call site.
#
# `MODEL`/`OPENROUTER_MODEL` is now CLOUD ANNA ONLY — decide, both judges, the
# phonetic rewrite. Every other lane runs on the laptop and takes `AGENT_MODEL`
# through `writer.ask_json`, which costs no cash. The seam is the BINARY making
# the call, so it cannot rot the way a hand-kept per-lane list would.
#
# `AGENT_MODEL` MUST BE A SLUG THE CLI ACCEPTS, and that is a smaller set than
# OpenRouter's. MEASURED 2026-08-23: `claude -p --model claude-sonnet-4.6` prints
# "It may not exist or you may not have access" AND RETURNS 0 — so a wrong value
# here does not crash, it silently routes the lane to the paid API. Smoke `s67`
# asserts the shape; `writer._agent_json` treats empty stdout as failure for the
# same reason. Verified working: `claude-sonnet-5`.
#
# WHY GEMINI ON THE CLOUD SIDE (Andrew, 2026-08-23): "Gemini seems suited to the
# task" — Indic coverage on the lanes that read, compose and grade Tamil. A
# TRIAL, revisit ~08-27. Not a cost decision, though the invoice moves: ~$0.0094
# per decide-shaped call against ~$0.050 on sonnet-5. Verified before the swap —
# the slug advertises `response_format` AND `structured_outputs` on OpenRouter,
# so JSON_MODE holds, and its 65,536-token completion ceiling clears the largest
# `budget()` call twenty-fold.
#
# WATCH THE JUDGE, NOT THE COMPOSER. `MODEL` grades Andrew's replies
# (knock_reply), and grading writes the production axis, so a VENDOR change
# recalibrates the learning record silently — the 08-18 risk one step further
# out. Nothing in smoke catches it; the tests stub the LLM. The graded replies in
# `knock_log.json` are the A/B corpus. Andrew judges the drift; reverting is this
# one constant.
#
# ON THE PRICE IT LEFT (measured 2026-08-23, and why this got looked at at all):
# sonnet-5's $2/$10 was Anthropic's INTRODUCTORY rate, expiring 2026-08-31 — the
# 08-18 note recorded it as the standing price. From 09-01 sonnet-5 is $3/$15,
# identical to the 4.6 it replaced, while emitting ~4x the output tokens.

# THINKING IS PART OF THE BUDGET, and only the MODEL knows what it costs
# (2026-08-18, hours after the swap above). Sonnet 5 reasons before it answers and
# OpenRouter counts those tokens against `max_tokens`. MEASURED the same day:
# 1624–2974 reasoning tokens on a studio-sized prompt, and enough on `decide()` —
# the largest prompt in the system against a 1600 ceiling — to leave zero
# characters of artifact. That took cloud Anna's knock lane down completely (run
# 32121449441, three retries, all truncated) and killed the drill sheet locally.
#
# THIS IS THE SECOND TIME, WHICH IS THE WHOLE POINT. On 2026-08-05 the reply judge
# hit exactly this and was fixed by raising exactly that one literal to 1600 — see
# the comment still sitting at that call site. A per-lane patch for a per-MODEL
# property leaves every other lane silently mis-calibrated until it happens to run;
# the drill lane then went 17 days before anyone found out.
#
# So a call site declares what its ANSWER needs — which is what it actually knows —
# and the thinking room is added HERE, once. Swap the model, change one number.
# A ceiling is not a spend: unused headroom is billed at nothing, so headroom is
# free insurance and a truncation is a dead lane.
# REPLACES: eight hand-tuned `max_tokens` literals across five modules.
REASONING_HEADROOM = 4000


def budget(answer_tokens: int) -> int:
    """The ceiling for one call: what the artifact needs, plus this model's room to
    think. Call sites pass the former; never a raw `max_tokens` on a `MODEL` call."""
    return answer_tokens + REASONING_HEADROOM

# STRUCTURED OUTPUT, one definition (2026-08-18). Every JSON lane sends this; the
# text lanes (`rephrase_phonetic` here, the studio's prose writers) must NOT.
#
# It replaces PROMPTING for JSON and hoping. The mandates always said "return ONLY
# a JSON object" and models kept wrapping it anyway — `parse_llm_json` carries a
# five-strategy fallback chain built from four dated incidents (a leading fence, a
# fence with prose in front of it, single-quoted Python dicts, a brace-slice fooled
# by a literal `{noun}` in the prose), and the rotation lane MEASURED 3 of 6
# identical calls coming back prose-prefixed — which killed a 45-minute render at
# movement 5 of 15, after paying for four movements of TTS.
#
# json_object makes that whole class impossible at the API instead of survivable at
# the parser. It requires the word "JSON" in the prompt, which every mandate here
# already satisfies (verified across all five lanes before this landed).
JSON_MODE = {"type": "json_object"}

def parse_llm_json(text: str) -> dict:
    """The mandates say 'return ONLY a JSON object', but models occasionally
    wrap it in a code fence, prose, or a Python-style dict (2026-07-04: empty
    text killed a knock; 2026-07-07: single-quoted keys bypassed the {..} slice
    fallback — 'Expecting property name enclosed in double quotes: char 1';
    2026-07-13: prose BEFORE a ```json fence, with a literal `{noun}` frame
    gloss in the prose — the startswith fence-strip never fired and the {..}
    slice bit on `{noun}`).
    Strategy: strip a leading fence → json.loads → fenced block ANYWHERE
    (last one wins — it's the artifact) → {..} slice + json.loads →
    ast.literal_eval (handles single quotes + Python True/False/None).
    Print the raw text before any re-raise so the Action log shows WHAT came back.

    A BACKSTOP SINCE 2026-08-18, NOT THE PRIMARY PATH. Every lane that reaches
    here now sends `JSON_MODE`, so in principle none of these fallbacks can fire:
    the API guarantees the shape the mandates were only asking for politely.
    Kept anyway, deliberately, and the reason is `judge()` — it has NO retry loop
    (see `parse_llm_response`), so a single wrapped reply is a reply Andrew sent
    and got nothing back for, which is the one failure here he actually feels.
    `decide()` re-rolls three times and a dead tick is invisible; a dead judge is
    not. OpenRouter also routes across providers, and `response_format` support is
    a per-model claim in its catalogue rather than a promise we control.

    RETIRE IT ON EVIDENCE, not on principle: once the Action logs show a stretch
    with no "unparseable LLM response" line and no fallback hit, this collapses to
    a bare `json.loads` and takes ~15 lines of this file's budget with it. Until
    then it costs nothing that matters — the ratchet counts it, but it is already
    written, already tested, and the failure it catches is the user-visible one."""
    import ast as _ast
    import re as _re
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        for block in reversed(_re.findall(r"```(?:json)?\s*\n(.*?)```", text, _re.DOTALL)):
            try:
                return json.loads(block.strip(), strict=False)
            except json.JSONDecodeError:
                continue
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            print(f"--- unparseable LLM response (no braces) ---\n{text}\n---")
            raise
        slice_ = text[start : end + 1]
        try:
            return json.loads(slice_, strict=False)
        except json.JSONDecodeError:
            # Python-style dict: single-quoted keys, True/False/None literals
            try:
                result = _ast.literal_eval(slice_)
                if isinstance(result, dict):
                    return result
            except (ValueError, SyntaxError):
                pass
            print(f"--- unparseable LLM response (all fallbacks failed) ---\n{text}\n---")
            raise


def parse_llm_response(resp) -> dict:
    """`parse_llm_json` for a raw API response — plus the one check the text
    alone CANNOT make.

    2026-08-05: the judge spent all 800 of its tokens deliberating in prose
    (which slip tag to reuse) and was cut off mid-word, before it had emitted a
    single brace. `parse_llm_json` did its job — "no braces", JSONDecodeError at
    char 0 — but that is byte-identical to the KF-7/KF-10 signature, where the
    JSON existed and the PARSER missed it. Those two failures want opposite
    fixes: a parser gap wants another fallback, a truncation wants a bigger
    budget, and adding a fallback for a truncation is pure motion. Only
    `finish_reason` can tell them apart, and it lives on the response, not the
    text — so the check has to sit here.

    Raised as ValueError so `decide()`'s retry loop re-rolls it (a second draft
    may simply be terser); `judge()` has no retry, so it surfaces at once."""
    c = resp.choices[0]
    if getattr(c, "finish_reason", None) == "length":
        raise ValueError(f"LLM response TRUNCATED at the max_tokens ceiling "
                         f"({len(c.message.content or '')} chars emitted, no JSON reached) "
                         f"— raise the budget at the CALL SITE; this is not a parser "
                         f"gap.\n--- truncated response ---\n{c.message.content}\n---")
    return parse_llm_json(c.message.content)

# ── The phonetic rewrite — the one TEXT lane on this module ──────────────────
# It sits with the JSON lanes because the thing they share is the CLIENT, not the
# response shape: same model, same base URL, same budget(). What it must never
# share is JSON_MODE — forcing an object out of a call that asks for a
# transliteration breaks it as silently as omitting it breaks the others (s69).
#
# It moved here from morning_knock on 2026-08-23 because it is not a knock: it is
# reachable from BOTH morning_knock.main and knock_reply's push-backs, and it runs
# on every knock body and every reply line that carries script.
#
# `TAMIL_RUN` is imported, not declared: the range itself is L0's PORT SURFACE and
# this module only USES it (2026-08-24). Dropping the copy took `import re` with
# it — the parser's own regex is function-local on purpose, so it can be deleted
# in one piece the day the fallback retires.


def rephrase_phonetic(body: str) -> str:
    """Ask the composer to transliterate its own body. The lexicon backstop below
    only resolves 8 of the 23 bodies this has historically hit — colloquial
    contractions (நல்லாருக்கு) are not keys — so the model, which knows how it
    spelt the thing, does the work and the lexicon only catches what it misses."""
    return ask_text(PHONETIC_REWRITE, body, answer_tokens=300)


def to_phonetic(text: str, label: str = "body") -> str:
    """Transliterate a surface Andrew READS, if the composer left script on it.

    The composer does the work, not a lookup table: it knows how it spelt the
    thing, so ரொம்ப நல்லாருக்கு comes back "romba nallarukku" with the colloquial
    contraction intact. A lexicon substitution was tried first (2026-08-03) and
    retired the same morning — it resolved 8 of 23 real bodies, and on the ones
    it did hit it swapped Andrew's contraction for the dictionary key's
    phonetic, flattening exactly the Kongu register the constitution exists to
    protect. Andrew: "brittle, and it violates my colloquial contractions."

    Leftovers WARN and ship. He reads enough script to take contextual clues, so
    a leaked word costs him far less than a dose he never gets — the opposite of
    the eavesdrop case, where the whole dose was the broken part.
    """
    if not TAMIL_RUN.search(text):
        return text
    print(f"   ✎ {label} carries Tamil script — asking for phonetics…")
    out = rephrase_phonetic(text) or text
    if TAMIL_RUN.search(out):
        # ONE re-ask before the warning (2026-08-23, when the host rule took this
        # lane over). MEASURED that day on the agent executor: 1 of 3 identical
        # calls came back with the script KEPT and the phonetics appended in
        # brackets — "ரொம்ப நல்லாருக்கு (romba nallarukku)" — which is a different
        # failure from the API path's and puts Tamil script on the lock screen,
        # the one surface this whole function exists to keep clear.
        #
        # The condition was already computed here and thrown away. A re-roll costs
        # nothing on the subscription and the SHIPPED line is what Andrew actually
        # reads. If the second draw leaks too it still warns and ships — that
        # trade is unchanged and deliberate.
        out = rephrase_phonetic(text) or out
    if TAMIL_RUN.search(out):
        print(f"   ⚠ script survived the rewrite: {' '.join(TAMIL_RUN.findall(out))}")
    return out


# A SCHEMA MUST DESCRIBE A SHAPE. `{"type": "object"}` is not enough and fails in
# the worst available way — MEASURED 2026-08-23 on the first live soak through
# this module. Handed a schema with no `properties`, the CLI has nothing to aim
# at, so it answers in an envelope: {"output": "<the entire real sheet, as a JSON
# STRING>", "clusters": []}. That parses. It has the key the lane reads. The lane
# filtered zero clusters out of it, printed "0 threads, 0 items", and carried on
# to render an empty tape. Every instrument green, the artifact a shell.
#
# So every lane declares its own top-level shape and the agent aims at it. These
# three lines are the whole vocabulary needed — the mandates still carry the
# craft, the schema only has to stop the envelope.
STR = {"type": "string"}
INT = {"type": "integer"}
BOOL = {"type": "boolean"}


def obj(**props) -> dict:
    """A top-level object schema. Everything declared is required: these keys are
    what the lane will actually read, and a missing one is a broken dose, not a
    tolerable omission.

    UNDECLARED KEYS ARE NOT SAFE, whatever this docstring said until 2026-08-28.
    It is executor-dependent, which is the worst possible shape for a rule:

      - API path (`response_format: json_object`) — constrains the BYTES to
        parseable JSON and nothing more, so an undeclared key survives.
      - Agent path (`claude -p --json-schema`) — constrains the SHAPE, and
        silently drops any key this function did not name.

    `claude -p` became the writer on 2026-08-18 and `voice_reply` was declared
    only in prose, so every local judgement lost it from that day — the model
    wrote the field, the schema ate it, and the answer went out in text looking
    exactly like a choice. Two executors disagreeing about a key is invisible
    until the one that drops it is the one you are running.

    The rule this leaves: if a mandate names a key, name it here too."""
    return {"type": "object", "properties": props, "required": list(props)}


def arr(**props) -> dict:
    """An array of objects with `props`. Item shape is declared, not implied —
    left unconstrained, an array of {ta, en} comes back as an array of strings
    (measured the same day)."""
    return {"type": "array", "items": obj(**props)}


# The envelope's fingerprint. Narrow on purpose: an `output` key holding a STRING
# is never a shape any lane here asks for, so this cannot fire on real work.
ENVELOPE_KEY = "output"
# Matches run_studio.PASS_TIMEOUT_S. A `claude -p` call starts a whole session,
# so it is seconds slower than an API call before it writes anything; Andrew
# accepted that cost explicitly (2026-08-23) for lanes that already render audio.
AGENT_TIMEOUT_S = 900


def have_agent() -> bool:
    """Is there a local agent to spend the subscription on? The whole host test."""
    return shutil.which("claude") is not None


def _agent_json(system: str, user: str, schema: dict) -> dict:
    """One print-only pass on the local agent. Raises on any failure so the
    caller can decide — this function never silently returns the API's work."""
    r = subprocess.run(
        ["claude", "-p", "--model", AGENT_MODEL,
         "--json-schema", json.dumps(schema, ensure_ascii=False)],
        input=f"{system}\n\n---\n\n{user}", cwd=BASE, timeout=AGENT_TIMEOUT_S,
        capture_output=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "").strip()
    # THE CLI EXITS 0 ON A BAD MODEL STRING. Measured 2026-08-23: `--model
    # claude-sonnet-4.6` printed "It may not exist or you may not have access"
    # and returned 0. Returncode alone is not a health check here, so an empty
    # or non-JSON stdout is treated as failure too — `parse_llm_json` raising is
    # the real gate.
    if r.returncode != 0 or not out:
        raise RuntimeError(f"claude -p exit {r.returncode}: {(r.stderr or out)[-300:]}")
    got = parse_llm_json(out)
    # THE ENVELOPE GUARD. See the note beside `obj` — this shape parses cleanly
    # and reads as an empty artifact downstream, so it has to die here, where the
    # cause is still legible. It means the schema did not describe a shape.
    if isinstance(got.get(ENVELOPE_KEY), str):
        raise RuntimeError(
            "claude -p returned an {'output': '<json string>'} ENVELOPE, not the "
            "artifact — the schema handed to it did not describe a shape. The "
            "lane would have rendered an empty dose. Schema was: "
            f"{json.dumps(schema, ensure_ascii=False)[:200]}")
    return got


def _api_json(system: str, user: str, answer_tokens: int) -> dict:
    """One pass through OpenRouter — the executor for a host with no agent, and
    the live path for any lane routed to Actions. Same prompt, same contract."""
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=OPENROUTER_MODEL, max_tokens=budget(answer_tokens),
        response_format=JSON_MODE,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return parse_llm_response(resp)


def ask_json(system: str, user: str, schema: dict, answer_tokens: int = 2400,
             tries: int = 3, prefer: str = "auto") -> dict:
    """One LLM call -> parsed JSON, on whichever executor this host has.

    `schema` is REQUIRED and positional, so a new lane cannot forget it. A
    default would be worse than no parameter at all: the agent path would take a
    permissive schema, return an envelope, and the lane would render a shell —
    which is precisely the failure this signature exists to make impossible. The
    API path does not use it (`JSON_MODE` already forbids prose there); wiring
    OpenRouter's `json_schema` response_format is a real improvement and belongs
    in the inbox, not in a diff that is already changing the model.

    `answer_tokens` is what the ARTIFACT needs; the API path adds this model's
    thinking room via `budget()`. The agent path takes no ceiling — `claude -p`
    manages its own, which is why a truncation guard exists on one branch only.

    RETRIED for the reason `render_drill.ask_json` was (2026-08-10): a coin-flip
    parse is survivable where a lane asks once and lethal where it asks fifteen
    times in a row, and the rotation lane MEASURED 3 of 6 identical calls coming
    back prose-prefixed. A truncation is NOT re-rolled — `parse_llm_response`
    raises it as its own ValueError naming the ceiling, and re-rolling that is
    the "pure motion" the 08-05 guard exists to prevent.

    `prefer` forces one executor ('agent'/'api') for an A/B or a test; 'auto' is
    the host rule and is what every lane passes.
    """
    use_agent = have_agent() if prefer == "auto" else (prefer == "agent")
    for attempt in range(1, tries + 1):
        try:
            if use_agent:
                return _agent_json(system, user, schema)
            return _api_json(system, user, answer_tokens)
        except (subprocess.SubprocessError, RuntimeError, OSError) as e:
            # THE FALLBACK IS LOUD, ON PURPOSE. This is the silent-no-op of this
            # change: the agent is present but broken (expired auth, a bad model
            # string, a rate limit), the lane quietly bills the API instead, and
            # every instrument reads green because the artifact arrived. The
            # subscription path can then be dead for weeks — which is exactly how
            # the three lanes this module replaces went unnoticed. A degrade that
            # costs money announces itself.
            if not use_agent:
                raise
            print(f"   ⚠ LOCAL AGENT FAILED — falling back to the PAID API. "
                  f"This run costs money and the subscription path is broken; "
                  f"fix it, do not ignore it.\n     {type(e).__name__}: {e}")
            use_agent = False
        except ValueError as e:
            # No JSON in the reply. Re-roll unless the ceiling was the problem
            # (parse_llm_response says so) or we are out of attempts.
            if attempt == tries or "TRUNCATED" in str(e):
                raise
            print(f"   ⚠ no JSON in the reply ({str(e)[:120]}) — "
                  f"retry {attempt + 1}/{tries}")
    raise RuntimeError("ask_json: retries exhausted without a result or an error")


def _agent_text(system: str, user: str) -> str:
    """One print-only pass on the local agent, no schema — the TEXT sibling of
    `_agent_json`. Raises on any failure so `ask_text` can decide; this function
    never silently returns the API's work.

    No `--json-schema`, deliberately: a schema is what makes the CLI emit a bare
    object, and an object is the one thing a transliteration must not be."""
    r = subprocess.run(
        ["claude", "-p", "--model", AGENT_MODEL],
        input=f"{system}\n\n---\n\n{user}", cwd=BASE, timeout=AGENT_TIMEOUT_S,
        capture_output=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "").strip()
    # Same reason as `_agent_json`: the CLI exits 0 on a bad model string, so an
    # empty stdout is treated as failure rather than as an empty answer.
    if r.returncode != 0 or not out:
        raise RuntimeError(f"claude -p exit {r.returncode}: {(r.stderr or out)[-300:]}")
    return out


def _api_text(system: str, user: str, answer_tokens: int) -> str:
    """One pass through OpenRouter for a PROSE answer. `JSON_MODE` is absent on
    purpose and must stay absent: forcing an object out of a call that asks for a
    transliteration breaks it exactly as silently as omitting it breaks a JSON
    lane, one direction over (s69)."""
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=os.environ["OPENROUTER_API_KEY"])
    resp = client.chat.completions.create(
        model=OPENROUTER_MODEL, max_tokens=budget(answer_tokens),
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return (resp.choices[0].message.content or "").strip()


def ask_text(system: str, user: str, answer_tokens: int = 300,
             prefer: str = "auto") -> str:
    """One LLM call -> a LINE, on whichever executor this host has.

    The text sibling of `ask_json`, and separate from it for one reason: there is
    no parse to re-roll, so there is no retry loop here. `ask_json` retries
    because a coin-flip parse is lethal to a lane that asks fifteen times; a
    transliteration either comes back or raises, and a re-roll would just buy the
    same answer twice.

    WHAT THIS REPLACES: the last raw `OpenAI(...)` client outside this module.
    `rephrase_phonetic` is a TEXT lane, so the JSON-only framing of the 2026-08-23
    executor rule left it out — and it is the leak that cost the most, because it
    is reachable from BOTH the knock and the reply push-back and runs on every
    body and every reply line that carries script. On the laptop it billed cash,
    every time, against a subscription already paid for.
    """
    use_agent = have_agent() if prefer == "auto" else (prefer == "agent")
    if use_agent:
        try:
            return _agent_text(system, user)
        except (subprocess.SubprocessError, RuntimeError, OSError) as e:
            # LOUD, for the reason `ask_json` is loud: a broken-but-present agent
            # degrades to the PAID API with the artifact still arriving, so every
            # instrument reads green while the subscription path is dead.
            print(f"   ⚠ LOCAL AGENT FAILED — falling back to the PAID API. "
                  f"This run costs money and the subscription path is broken; "
                  f"fix it, do not ignore it.\n     {type(e).__name__}: {e}")
    return _api_text(system, user, answer_tokens)


def executor_name() -> str:
    """What this host will actually use — for a lane's opening print, so a run
    that quietly costs money is legible in the log before it starts."""
    return f"claude -p ({AGENT_MODEL}, subscription)" if have_agent() \
        else f"openrouter ({OPENROUTER_MODEL}, PAID)"


# ── THE VOICE CANON — one owner for every pass that writes Tamil aloud ───────
VOICE_CANON_FILES = ("protocol/persona.md", "protocol/dialect.md")


def voice_canon() -> str:
    """Who Anna is, plus the spoken-register law — for any pass that can emit
    Tamil a VOICE will speak.

    WHAT THIS REPLACES (2026-09-02): five copies of
    `(BASE / "protocol" / "persona.md").read_text(...)` — `morning_knock`,
    `render_soak`, `render_drill`, and both `knock_reply` judges — none of which
    carried `dialect.md`. The spoken-register rules were filed as studio craft
    and reached exactly ONE reader, `run_studio`'s Producer pass, so every knock
    memo, eavesdrop tape, fielding question, soak sheet, drill sheet and voice
    reply was written with no dialect law at all. Those lanes carry nearly all of
    Andrew's daily ear contact; the studio carries the least.

    HOW IT SURFACED, and why it took two natives to see it. 2026-07-31, his wife:
    the ல/ள and ர/ற distinctions are over-articulated, "uncanny" — logged as a
    TTS/medium finding, which is where the trail went cold, because a medium
    finding has no script owner. 2026-09-01, his nephew, on an 18-second eavesdrop
    tape: it is book Tamil, and following it cost him enough that he lost the
    start of it. Same defect, and the second report was functional rather than
    aesthetic. Neither ear was wrong about the sound; the tape had simply never
    been through the pass that exists to fix it.

    Costs no extra model call and no second prompt: every one of these lanes
    already sends `persona.md` in this exact position, and `dialect.md` is ~3.5 KB
    beside it.

    LOUD ON ABSENCE, deliberately. A missing canon file raises here rather than
    returning what it could find — a half-canon would put every lane straight
    back to book Tamil with every instrument green, which is the failure mode
    that hid this bug for a month.
    """
    parts = []
    for rel in VOICE_CANON_FILES:
        p = BASE / rel
        if not p.exists():
            raise FileNotFoundError(
                f"voice canon missing: {rel} — every spoken-Tamil lane reads it; "
                f"refusing to generate Tamil without the register law")
        parts.append(p.read_text(encoding="utf-8").strip())
    return "\n\n---\n\n".join(parts)
