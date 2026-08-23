#!/usr/bin/env python3
"""WHO MAKES THE CALL — the one place that chooses an executor for a JSON lane.

THE RULE (2026-08-23, Andrew): the laptop has an agent with a subscription already
paid for; a GitHub runner has neither. So a lane running on the laptop spends
tokens Andrew has already bought, and a lane running in Actions spends cash. That
is a HOST difference, decided HERE, once, by asking whether the binary exists —
never by a lane, never by a flag someone has to remember to pass.

WHAT THIS REPLACES: three lanes that never chose at all. `render_soak`,
`render_drill` and `render_longhaul` each opened an OpenRouter client
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
mandate and menu — a long-haul movement lands around 14 KB, close enough that a
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

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from morning_knock import (AGENT_MODEL, JSON_MODE, OPENROUTER_BASE, OPENROUTER_MODEL,
                           budget, parse_llm_json, parse_llm_response)

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


def obj(**props) -> dict:
    """A top-level object schema. Everything declared is required: these keys are
    what the lane will actually read, and a missing one is a broken dose, not a
    tolerable omission. Undeclared keys are still allowed through."""
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
    times in a row, and the long-haul lane MEASURED 3 of 6 identical calls coming
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


def executor_name() -> str:
    """What this host will actually use — for a lane's opening print, so a run
    that quietly costs money is legible in the log before it starts."""
    return f"claude -p ({AGENT_MODEL}, subscription)" if have_agent() \
        else f"openrouter ({OPENROUTER_MODEL}, PAID)"
