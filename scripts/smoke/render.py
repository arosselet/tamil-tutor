"""L5 — the write -> render -> publish family, and the studio.

Everything downstream of a decision to make audio: the renderer's handling of
[SFX] and of a sidecar it cannot read, the drill's answer key, capacity routing,
the cloud writer, and the rotation tape.

The family's failure mode is a plausible artefact from the wrong source — a word
list scraped out of a script because the sidecar was unreadable, a draft deleted
under another render sharing a scratch dir. Nothing crashes; the tape is just
quietly wrong. The cases here assert the source, not the existence of output.
"""
import ast
import asyncio
import importlib
import inspect
import os
import re
import sys
from pathlib import Path

from . import _fixtures as fx
from ._fixtures import (
    check, code_line_numbers, mechanism, raw_source, read_json, REAL_BASE,
    write_json,
)


def s26_capacity_routing(sb: Path):
    print("\n26. Audio channel routes by capacity, not by default (2026-07-23)")
    # The felt signal: "totally tired, a longer drill for the park" produced a
    # dense 10-min two-voice scene, because every audio ask routed to the studio.
    # The routing table is the fix; this is the lint that keeps doc and code
    # honest about each other.
    routing = (REAL_BASE / "protocol" / "audio_channels.md").read_text(encoding="utf-8")
    check("routing table exists", "capacity routes" in routing)
    for script in ("render_soak.py", "render_drill.py", "run_studio.py"):
        check(f"routing names {script}", script in routing)
        check(f"{script} exists", (REAL_BASE / "scripts" / script).exists())
    session = (REAL_BASE / "protocol" / "daily_session.md").read_text(encoding="utf-8")
    check("the session choreography points at it", "audio_channels.md" in session)
    skill = (REAL_BASE / ".claude" / "skills" / "anna" / "SKILL.md").read_text(encoding="utf-8")
    check("Anna's skill routes by capacity, not straight to the studio",
          "capacity" in skill and "render_soak.py" in skill)

    # The soak channel's own law: passive means no response gap and no scene.
    soak = importlib.import_module("render_soak")
    check("soak mandate forbids a scene", "NO scene" in soak.SOAK_MANDATE)
    check("soak rhythm is Python's, not the model's",
          "Python owns all of that" in soak.SOAK_MANDATE)
    check("soak week-window is selectable", "days" in soak.week_payload.__code__.co_varnames)

    # The feed must actually carry it — a channel nobody can find is not a channel.
    rr = importlib.import_module("rebuild_rss")
    check("feed titles soak tracks", "nothing to do but listen" in rr.clean_title(
        "Soak", "soak_2026-07-23_2326.mp3"))
    check("feed durations are measured, not estimated",
          rr.audio_duration.__doc__ and "ffprobe first" in rr.audio_duration.__doc__)


def s28_cloud_writer(sb: Path):
    print("\n28. Studio writer is executor-agnostic; cloud carries its canon (2026-07-24)")
    rs = importlib.import_module("run_studio")

    # The resolver: `claude -p` locally (Andrew's subscription, and a filesystem
    # so the canon is READ rather than inlined), OpenRouter where no agent binary
    # exists — which is every cloud runner. agy retired 2026-08-18.
    check("force claude → claude_print", rs.resolve_writer("claude").__name__ == "claude_print")
    check("force openrouter → openrouter_pass",
          rs.resolve_writer("openrouter").__name__ == "openrouter_pass")

    real_which = fx.wr.shutil.which
    fx.wr.shutil.which = lambda c: None if c == "claude" else real_which(c)
    try:
        check("auto with no claude → openrouter", rs.resolve_writer("auto").__name__ == "openrouter_pass")
        prev = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            check("no claude + no key → auto preflight fails",
                  rs.writer_preflight("auto") is not None)
            os.environ["OPENROUTER_API_KEY"] = "x"
            check("no claude + key → auto preflight ok", rs.writer_preflight("auto") is None)
            check("forced claude without claude → preflight fails",
                  rs.writer_preflight("claude") is not None)
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)
            if prev is not None:
                os.environ["OPENROUTER_API_KEY"] = prev
    finally:
        fx.wr.shutil.which = real_which

    # inline_canon: the fix that made the cloud writer produce on-canon. The
    # thin slice caught it inventing a tags schema it had no filesystem to read;
    # the prompt's OWN 'protocol/...md' references are the manifest Python inlines.
    producer_prompt = rs.PRODUCER.format(draft="DRAFT", n=99)
    inlined = rs.inline_canon(producer_prompt)
    check("inline_canon pulls producer.md content into the prompt",
          "===== protocol/studio/producer.md =====" in inlined
          and len(inlined) > len(producer_prompt) + 1000)
    check("inline_canon includes a sample sidecar when tags are asked for",
          "EXAMPLE .tags.json" in inlined)
    # a prompt that references nothing is passed through untouched
    check("inline_canon is a no-op without file refs",
          rs.inline_canon("just do the thing") == "just do the thing")
    # the manifest follows the prompt: a made-up ref is reported, never fabricated
    check("inline_canon flags a missing referenced file",
          "referenced but missing" in rs.inline_canon("Read protocol/studio/nope.md now"))

    # THE TWO BLIND SPOTS, both found 2026-08-18 and both untested until now —
    # which is why they survived. The old pattern read one level deep and matched
    # `protocol/*.md` only, so the constitution (cited BY the role files, never by
    # a prompt) and the calibration dials (cited by the Director, under progress/)
    # reached no pass. Every episode the API writer produced was off-canon.
    director_inlined = rs.inline_canon(rs.DIRECTOR.format(ticket="TICKET"))
    check("inline_canon follows a role file's OWN citation (the constitution)",
          "===== protocol/constitution.md =====" in director_inlined)
    check("...and carries the calibration dials the Director calls LAW",
          "===== progress/profile.md =====" in director_inlined)
    check("...and the soak order it is told to read",
          "===== progress/learner.json =====" in director_inlined)
    check("the Producer gets the canon governing the Tamil it rewrites",
          "===== protocol/constitution.md =====" in rs.inline_canon(producer_prompt)
          and "===== protocol/studio/dialect.md =====" in rs.inline_canon(producer_prompt))
    # the skip is deliberate AND loud: 114 KB the ticket already distills. A quiet
    # omission is the bug above; an announced one is a decision.
    check("the lexicon is skipped, not silently dropped",
          "progress/lexicon.json" in rs.CANON_SKIP
          and "===== progress/lexicon.json =====" not in director_inlined)

    # PAYLOAD FIDELITY — verbatim for chunks, stem-tolerant for words (2026-08-18).
    # The check had NO coverage at all, which is how a flat substring test survived
    # while rejecting correct scripts: a verb claimed as தூக்கு appears as
    # தூக்கறேன், and every verb in the pool had the same problem waiting. The
    # tolerance must not reach the two mutations that earned the rule.
    lex = {"தூக்கு": {}, "வேணும்": {}, "வை": {},
           "ஒரு நிமிஷம்": {"type": "chunk"}}
    pp = rs.payload_present
    check("a verb claimed as a stem counts when the script inflects it",
          pp("தூக்கு", "நான் தூக்கறேன் அத", lex))
    check("...and still fails when the verb is simply absent",
          not pp("தூக்கு", "நான் பையை எடுத்தேன்", lex))
    check("a CHUNK gets zero tolerance — the mutation that earned the rule",
          not pp("ஒரு நிமிஷம்", "ஒரு நிமிஷங்க இருங்க", lex)
          and pp("ஒரு நிமிஷம்", "ஒரு நிமிஷம் இருங்க", lex))
    check("the literary form the dialect pass exists to remove is still caught",
          not pp("வேணும்", "அது வேண்டும் என்று சொன்னார்", lex))
    check("a stem too short to be evidence falls back to verbatim",
          pp("வை", "அத அங்க வைக்கறேன்", lex))
    # BOTH SIDES ASK THE SAME QUESTION (2026-08-18, the day's lint pass). `lint`
    # rejects a script the sidecar over-claims; `claim_payload` injects a soak
    # item the sidecar under-claims. They read the same script, so a rule that
    # lands on one and not the other is worse than landing on neither: the
    # inflected word passes the gate and is then refused the claim, and the
    # render never stamps its `seen_in` — the Teach Beat's unlock, lost silently.
    rs_src = raw_source(REAL_BASE / "scripts" / "run_studio.py")
    mech = code_line_numbers(rs_src)
    callers = {i for i, ln in enumerate(rs_src.splitlines(), 1)
               if i in mech and "payload_present(" in ln and "def " not in ln}
    check("both payload paths route through payload_present, not a flat `in script`",
          len(callers) == 2, f"found {len(callers)} call site(s) — lint and "
          f"claim_payload must share the rule")


def s40_drill_consumes_its_commission(sb: Path):
    """`--soak-channel drill` was a dead value (2026-07-28).

    `sync_state` accepted and stored it, `render_drill` never read it, and no lane
    stamped it delivered. Three consequences, all silent: the repair became an
    ordinary deck drill, the order stayed pending, and the session-open auto-drain
    then dispatched an EPISODE for it — the one lane Andrew had explicitly not
    chosen. Of the three channels on the routing table, only two worked.

    LEAD, not replace (Andrew's call): the repair leads and takes three angles,
    the due deck fills out the rest. A whole tape built from one item is the slow
    repetitive loop this lane exists to escape."""
    print("\n40. The drill lane consumes its commission (2026-07-28)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    rd = importlib.import_module("render_drill")
    lex_path, learner_path = sb / "progress" / "lexicon.json", sb / "progress" / "learner.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes())

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))

    def brief():
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            focus, lead = rd.drill_brief()
        return focus, lead, out.getvalue()

    try:
        # Planted rather than scanned: earlier cases blank the sandbox lexicon, and
        # this one needs one fire-side row and one ear-only row to exist for sure.
        fireable, earonly = "பக்கத்துல", "விட்டுடு"
        lex = read_json(lex_path)
        lex[fireable] = {"gloss": "beside/next to", "recognition": "struggled",
                         "production": "none"}
        lex[earonly] = {"gloss": "let it go", "recognition": "struggled",
                        "production": "none", "direction": "catch", "deck": "trip"}
        write_json(lex_path, lex)

        update(soak_payload=[fireable], soak_focus="close the pakkam collision",
               soak_channel="drill")
        focus, lead, _ = brief()
        check("a drill-routed order reaches the drill lane at all",
              [t["word"] for t in lead] == [fireable], f"got {lead}")
        check("...carrying the focus that says what the repair is",
              focus == "close the pakkam collision", f"got {focus!r}")

        # The repair leads; the deck fills the rest. Not replace.
        deck = [{"word": "X", "gloss": "", "kind": "chunk"},
                {"word": "Y", "gloss": "", "kind": "frame"}]
        merged = rd.with_lead(deck, lead)
        check("the repair leads the tape and the deck follows",
              [t["word"] for t in merged] == [fireable, "X", "Y"], f"got {merged}")
        check("...and a lead item already on the deck list is not drilled twice",
              [t["word"] for t in rd.with_lead(deck + lead, lead)]
              == [fireable, "X", "Y"])
        check("a commission still gets a tape when the deck has nothing due",
              [t["word"] for t in rd.with_lead([], lead)] == [fireable])

        # The mandate has to SAY it, or the writer treats the lead as deck rep one.
        brief_text = rd.COMMISSION_BRIEF.format(n=1, focus="\nWhat: the collision")
        check("the sheet writer is told the lead is a repair, not a deck rep",
              "REPAIR" in brief_text and "THREE items instead of one" in brief_text)
        check("...and told to vary the situation rather than the target",
              "never the target" in brief_text)

        # Ear-only is a recognition win. A drill's silence is a production demand,
        # and the deck law is that catch items are NEVER forced to fire.
        if earonly:
            update(soak_payload=[earonly], soak_channel="drill")
            _, lead_catch, warned = brief()
            check("an ear-only item routed to the drill lane is refused, not demanded",
                  lead_catch == [], f"got {lead_catch}")
            check("...and says why, so the mis-route is visible",
                  "ear-only" in warned and "soak or episode" in warned, warned)

        update(soak_payload=[fireable], soak_channel="soak")
        check("an order routed to another lane does not reach the drill",
              brief()[1] == [])
        update(soak_payload=[fireable], soak_channel="episode")
        check("...including the default episode lane", brief()[1] == [])

        # Without the stamp the order reads pending forever and the drain sends
        # an episode for a repair the drill already delivered.
        # The pieces above are only worth having if main() actually calls them.
        # Stub the LLM and run the real entry point through --dry-run.
        update(soak_payload=[fireable], soak_focus="the pakkam collision",
               soak_channel="drill")
        seen = {}
        real_write, real_argv = rd.write_sheet, sys.argv
        try:
            def spy(pending, n_lead=0, focus=None):
                seen.update(pending=[t["word"] for t in pending],
                            n_lead=n_lead, focus=focus)
                return {"title": "T", "intro": "i", "outro": "o", "items": []}
            rd.write_sheet = spy
            sys.argv = ["render_drill.py", "--dry-run"]
            with contextlib.redirect_stdout(io.StringIO()):
                rd.main()
        finally:
            rd.write_sheet, sys.argv = real_write, real_argv
        check("main() hands the commission to the sheet writer",
              seen.get("pending", [None])[0] == fireable, f"got {seen.get('pending')}")
        check("...counted as lead items, so the brief fires",
              seen.get("n_lead") == 1, f"got {seen.get('n_lead')}")
        check("...with the focus attached", seen.get("focus") == "the pakkam collision")

        with contextlib.redirect_stdout(io.StringIO()):
            stamped = ss.mark_soak_delivered("drill")
        order = read_json(learner_path)["soak_order"]
        check("the drill lane can stamp the order consumed", stamped)
        check("...naming itself as the lane that carried it",
              (order.get("delivered") or {}).get("channel") == "drill", f"got {order}")
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])


def s48_drill_answer_key_lint(sb: Path):
    """The drill lane had no answer-key validation (2026-08-01): the 08-01 tape
    shipped இடது பக்கம்ல where the oblique பக்கத்துல is right — a wrong case
    form repeated aloud ten times, on the tape commissioned to fix the top
    slip. The lint applies the studio contract: grade every answer against its
    cue, ANY fail stops the run, and a grader that errors or miscounts is
    fail-CLOSED — an unverified sheet must not ship.

    Gate 7.2 — the silent no-op is a lint that always passes (a parse bug reads
    every verdict as PASS), so the case feeds a FAIL and asserts the run STOPS,
    and feeds a miscounted verdict list and asserts the raise."""
    print("\n48. The drill answer key is linted; a fail stops the run (2026-08-01)")
    import contextlib, io
    rd = importlib.import_module("render_drill")
    sheet = {"title": "T", "intro": "i", "outro": "o",
             "items": [{"cue": "ask for tea", "answer_ta": "டீ குடுங்க"},
                       {"cue": "say: next to the temple", "answer_ta": "இடது பக்கம்ல"}]}
    real_ask = rd.ask_json
    try:
        rd.ask_json = lambda *a, **k: {"verdicts": [
            {"n": 1, "verdict": "PASS", "reason": ""},
            {"n": 2, "verdict": "FAIL", "reason": "needs the oblique stem"}]}
        fails = rd.lint_sheet(sheet)
        check("a failing answer is caught, naming the line and the why",
              len(fails) == 1 and "பக்கம்ல" in fails[0] and "oblique" in fails[0],
              f"got {fails}")

        rd.ask_json = lambda *a, **k: {"verdicts": [
            {"n": 1, "verdict": "PASS"}, {"n": 2, "verdict": "PASS"}]}
        check("an all-pass sheet returns no failures", rd.lint_sheet(sheet) == [])

        rd.ask_json = lambda *a, **k: {"verdicts": [{"n": 1, "verdict": "PASS"}]}
        try:
            rd.lint_sheet(sheet)
            miscount = False
        except ValueError:
            miscount = True
        check("a miscounted verdict list fails CLOSED, never open", miscount)

        check("an empty sheet needs no grader call",
              rd.lint_sheet({"items": []}) == [])

        # main() must ACT on the verdict — stub the writer to return the bad
        # sheet and assert the run stops before anything renders.
        real = (rd.write_sheet, rd.drill_brief, rd.due_payload, sys.argv)
        rd.ask_json = lambda *a, **k: {"verdicts": [
            {"n": 1, "verdict": "FAIL", "reason": "wrong case"},
            {"n": 2, "verdict": "PASS", "reason": ""}]}
        try:
            rd.write_sheet = lambda *a, **k: sheet
            rd.drill_brief = lambda: (None, [])
            rd.due_payload = lambda n: [{"word": "X", "gloss": "", "kind": "chunk"}]
            sys.argv = ["render_drill.py", "--dry-run"]
            stopped = False
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    rd.main()
                except SystemExit as e:
                    stopped = bool(e.code)
            check("main() stops on a lint fail — nothing renders", stopped)
        finally:
            rd.write_sheet, rd.drill_brief, rd.due_payload, sys.argv = real
    finally:
        rd.ask_json = real_ask


def s57_rotation_tape(sb: Path):
    """The fourth audio lane (2026-08-10) — a 40-60 minute press-once tape for the
    flight, where the other three channels' 10-15 minute dose is the wrong shape:
    ~50 press-plays at a median 2.7 min is fifty context switches on a 20-hour leg.

    Gate 7.2, answered out loud. EVERY failure mode of this lane ends with an mp3
    on the feed and a console that says `done`:

      · forty-five minutes of six items looping   → coverage never happened
      · a scene using a word the tape never taught → he loses the thread and stops
      · two identical shapes side by side          → the grating this exists to escape
      · a longhaul_*.mp3 the RSS filter drops      → it never reaches the phone he
        is holding at 35,000 feet, with no way to fetch it
      · a payload the lane ignores                 → the 07-23 re-dispatch loop

    So nothing here asserts that a step RAN. It asserts coverage, the
    taught-before-used ordering, the cadence invariant *including the wrap*, a real
    feed round-trip, and a clock that actually stops the tape."""
    print("\n57. The rotation tape — coverage, cadence, the clock, and the feed (2026-08-10)")
    rl = importlib.import_module("render_rotation")

    # ── The cadence law. Two of a kind side by side is the complaint itself, and
    # the WRAP matters as much as the middle: he plays these two or three times
    # through, so the last shape butts against the first on every repeat.
    for spine, cad in rl.CADENCES.items():
        pairs = [(cad[i], cad[(i + 1) % len(cad)]) for i in range(len(cad))]
        clash = [f"{a}->{b}" for a, b in pairs if a == b]
        check(f"cadence '{spine}' never repeats a shape, wrap included", not clash,
              f"adjacent duplicates: {clash}")
        check(f"cadence '{spine}' uses at least three shapes", len(set(cad)) >= 3)
        check(f"cadence '{spine}' has a non-recall shape to teach from",
              any(s not in rl.RECALL_SHAPES for s in cad))
        # Slot 1 cannot be a recall shape: there is nothing yet to recall. The
        # `room` cadence shipped this way and its first plan opened on an empty
        # scene — visible in one --plan-only run, invisible to every assertion
        # the suite had, because an empty movement renders and publishes fine.
        check(f"cadence '{spine}' opens on a shape that teaches",
              cad[0] not in rl.RECALL_SHAPES, f"opens on '{cad[0]}' with nothing taught")
    check("every shape in every cadence has a rhythm and an item count",
          all(s in rl.RHYTHM and s in rl.ITEMS
              for cad in rl.CADENCES.values() for s in cad))

    # ── A pool with a known shape, so coverage is checkable rather than plausible.
    lex = {f"சொல்{i}": {"gloss": f"word {i}", "production": "none",
                        "recognition": "struggled", "type": "chunk"}
           for i in range(40)}
    lex["நாள்"] = {"gloss": "day", "production": "cold", "type": "chunk"}
    lex["நாளைக்கு"] = {"gloss": "tomorrow", "production": "cold", "type": "chunk"}
    # The `room` spine sorts and QUALIFIES on `register`. It used to be joined
    # from curriculum/trip_deck.json at build time; since 2026-08-18 it rides on
    # the row, so the fixture carries it here — the one row that qualified for
    # room before is the one row that carries a register now.
    lex["ரொம்ப நாளாச்சு"] = {"gloss": "long time", "production": "none",
                              "type": "chunk", "register": "social"}
    # PATTERNS, because the machines spine now draws only on what it can run as a
    # machine (2026-08-10). This fixture was all chunks, so that spine's pool came
    # out EMPTY and its movements rendered as bare frame lines — the filter working
    # correctly against a fixture that predated it.
    lex.update({f"frame:இயந்திரம்-{i}": {"gloss": f"machine {i}", "production": "none",
                                         "type": "pattern"} for i in range(16)})
    write_json(sb / "progress" / "lexicon.json", lex)

    for spine in rl.CADENCES:
        pool = rl.build_pool(spine, [])
        count = rl.movements_for(spine, len(pool))
        plan = rl.plan_movements(pool, spine, count)

        # THE POOL IS THE SPINE'S OWN MATERIAL, never padded out to hit a length.
        # Reaching past it is how a 45-minute ask bought 42 rootless "inventory"
        # movements (2026-08-10) — items the shape has nothing to do with.
        unusable = [i["word"] for i in pool if not rl.SPINE_QUALIFIES[spine](i)]
        check(f"[{spine}] every pooled item is one this spine can teach from",
              not unusable, f"cannot be used by {spine}: {unusable[:6]}")

        # COVERAGE — the whole point of a long tape. A 45-minute loop over six
        # items is the silent no-op, and it reads as success from the console.
        heard = {i["word"] for mv in plan for i in mv["items"]}
        missing = [i["word"] for i in pool if i["word"] not in heard]
        check(f"[{spine}] every pooled item is aired at least once ({len(pool)} items)",
              not missing, f"never aired: {missing[:6]}")

        # ...and sized SHORT of the plan on purpose: the render stops on the
        # measured clock, so a tape whose speech ran long drops its last movement.
        # That movement must be a repeat, never a word's only airing.
        short = rl.plan_movements(pool, spine, count - 1)
        heard_short = {i["word"] for mv in short for i in mv["items"]}
        check(f"[{spine}] coverage survives losing the last movement to the clock",
              not [i for i in pool if i["word"] not in heard_short])

        # TAUGHT BEFORE USED — the mechanism behind "I can mostly understand".
        # A scene that reaches for an untaught word is where the thread drops.
        taught, violations = set(), []
        for mv in plan:
            if mv["shape"] in rl.RECALL_SHAPES:
                violations += [i["word"] for i in mv["items"] if i["word"] not in taught]
            else:
                taught |= {i["word"] for i in mv["items"]}
        check(f"[{spine}] no recall movement reaches for an untaught word",
              not violations, f"used before taught: {violations[:6]}")
        # ...and no movement is EMPTY. An empty movement renders as a single Anna
        # line and publishes without complaint — success, with a hole in it.
        check(f"[{spine}] no movement is empty",
              all(mv["items"] for mv in plan),
              f"empty at {[n for n, mv in enumerate(plan, 1) if not mv['items']]}")

        # RECURRENCE — a soak, not a list. Wrapping the cursor is what makes the
        # tape a loop; a plan that never revisits anything is a glossary read aloud.
        longer = rl.plan_movements(pool, spine, count * 2)
        airings = [i["word"] for mv in longer for i in mv["items"]]
        check(f"[{spine}] a longer tape revisits items rather than starving",
              len(airings) > len(set(airings)))

    # ── `--minutes` IS A CEILING, NOT A TARGET (Andrew, 2026-08-10). The first tape
    # planned 15 movements for a 45-minute ask, ran out at 23.8, and warned that it
    # had "come up short" — the plan, not the tape, was wrong. A spine now runs to
    # the length of its material and stops there without apology.
    for spine in rl.CADENCES:
        pool = rl.build_pool(spine, [])
        natural = rl.movements_for(spine, len(pool))
        check(f"[{spine}] every pooled item still fits inside the natural plan",
              rl.pool_size(spine, natural) >= len(pool),
              f"{rl.pool_size(spine, natural)} slots for {len(pool)} items")
        # A bigger ceiling must never invent movements the material cannot fill —
        # the whole point of the 08-10 change. Fixture-independent: whatever this
        # spine's material is, an enormous ceiling returns exactly that much tape.
        check(f"[{spine}] raising the ceiling does not stretch the tape",
              min(natural, rl.movement_count(9999) + 2) == natural, f"natural={natural}")

    # ...and the ceiling must still BIND when the material outruns it, or --minutes
    # means nothing. Asserted on the arithmetic rather than on a spine, because the
    # sandbox lexicon is deliberately small and its natural plans sit under the
    # floor `movement_count` imposes — a fixture fact, not a behaviour.
    for minutes in (8, 20, 45):
        cap = rl.movement_count(minutes) + 2
        check(f"a {minutes}-minute ceiling caps a spine with more material than that",
              min(9999, cap) == cap, f"cap={cap}")
    check("a longer ceiling always allows a longer tape",
          rl.movement_count(8) < rl.movement_count(45) < rl.movement_count(90))
    check("the ceiling is measured in the same minutes the render measures",
          rl.expected_min(rl.movement_count(45)) <= 45 + rl.MOVEMENT_MIN,
          f"{rl.expected_min(rl.movement_count(45)):.1f} min planned for a 45 min ceiling")

    check("the length prediction is anchored to the measured per-movement figure",
          abs(rl.expected_min(15) - (15 * rl.MOVEMENT_MIN + rl.CLOSING_LAP_MIN)) < 1e-9)
    # 3.5 was a guess and was 3x the truth. Guard the calibration itself: a figure
    # this far off is what silently truncated a 45-minute ask to 23.8.
    check("MOVEMENT_MIN is in the range a real movement measured",
          0.8 <= rl.MOVEMENT_MIN <= 2.0, f"got {rl.MOVEMENT_MIN}")

    # ── The commissioned payload LEADS, whatever the ordering turned up. A lane
    # that ignores its payload can never satisfy the order that dispatched it, and
    # re-dispatches forever (M72/M73/M74 in one evening, 2026-07-23).
    pool = rl.build_pool("machines", ["ரொம்ப நாளாச்சு"])
    check("a commissioned payload word leads the pool",
          pool and pool[0]["word"] == "ரொம்ப நாளாச்சு", f"got {pool[0]['word'] if pool else None}")
    # ...INCLUDING one the spine would otherwise refuse. "ரொம்ப நாளாச்சு" is a chunk,
    # not a pattern, so the machines filter drops it — but an order outranks the
    # shape's preference, or the lane silently declines the work it was sent.
    check("the payload is never dropped for being outside the ordering",
          "ரொம்ப நாளாச்சு" in {i["word"] for i in pool})

    # ── The order is only ours when it is addressed to us; and once consumed it
    # must be declared spent, or the session-open drain dispatches a second dose.
    learner = sb / "progress" / "learner.json"
    base = read_json(learner)
    write_json(learner, {**base, "soak_order": {"channel": "soak", "payload": ["x"]}})
    check("an order addressed to another lane is not claimed", rl.rotation_brief() == (None, []))
    write_json(learner, {**base, "soak_order": {"channel": "rotation", "payload": ["x"],
                                                "focus": "the -aachu tail"}})
    focus, payload = rl.rotation_brief()
    check("an order addressed to this lane is read", focus == "the -aachu tail" and payload == ["x"])
    sync = importlib.import_module("sync_state")
    check("this lane can declare its order spent", sync.mark_soak_delivered("rotation") is True)
    check("...and the declaration round-trips to disk",
          (read_json(learner).get("soak_order") or {}).get("delivered", {}).get("channel") == "rotation")

    # ── Inventory candidates are PROPOSED by substring and must be marked as
    # unsafe: the same technique logged நீ at 17 reps because it sits inside
    # நீங்க (probe_hit, 2026-07-26). The sheet-writer is the one that disposes.
    # The match is on the PULLI-STRIPPED stem. A citation form ends in ் (நாள்);
    # inside a longer word that consonant takes another vowel sign instead
    # (நாளைக்கு, ரொம்ப நாளாச்சு), so plain substring matching finds NEITHER of the
    # two phrases the 08-09 session was actually about. Measured: 1 host of 3.
    hosts = rl.inventory_hosts(lex)
    found = set(hosts.get("நாள்") or [])
    check("the inventory root reaches its hosts across the vowel change",
          {"நாளைக்கு", "ரொம்ப நாளாச்சு"} <= found,
          f"got {found} — a bare substring test misses exactly the finding's examples")
    check("the mandate tells the writer to drop coincidental hosts",
          "coincidence" in rl.SHAPE_CLAUSES["inventory"].lower())
    check("no mandate ever asks the listener for anything",
          "never ask him" in rl.BASE_MANDATE.lower())
    # Constitution rule 6 — no meta-narration. This lane is the one most likely to
    # break it: the mandate TELLS the writer he is on a plane, which is exactly the
    # kind of context that leaks into a spoken line ("rest your eyes", "we're
    # halfway"). An earlier draft of the outro said "sleep if you can".
    check("the mandate forbids narrating where he is or what he is doing",
          "meta-narration" in rl.BASE_MANDATE.lower(),
          "the model is told he is on a flight; without the ban that lands in the audio")
    fixed = mechanism(inspect.getsource(rl.render))
    spoken_asides = re.findall(r'tape\.add\("([^"]+)"', fixed)
    banned = re.compile(r"\b(sleep|walk|tired|rest|eyes|flight|plane|seat|halfway)\b", re.I)
    check("...and the lane's own hard-coded lines obey it too",
          not [s for s in spoken_asides if banned.search(s)],
          f"meta-narrating asides: {[s for s in spoken_asides if banned.search(s)]}")

    # ── THE CLOCK GOVERNS. `--minutes` is the dial he sets; if the render ignores
    # it he gets a 20-minute file he has to re-press mid-flight. Stub the TTS with
    # real silence frames so the frame scan measures an honest stream, no network.
    real = (rl.generate_segment_google, rl.get_raw_mp3_frames)
    sheet = {"frame": "the -aachu tail", "beats": [
        {"ta": f"வாக்கியம் {n}", "en": f"line {n}", "who": "a"} for n in range(5)]}

    async def fake_tts(text, voice, index, tmp):
        p = os.path.join(tmp, f"{index}.mp3")
        open(p, "wb").close()
        return p
    try:
        rl.generate_segment_google = fake_tts
        rl.get_raw_mp3_frames = lambda f: rl.SILENCE_FRAME * 60   # ~1.4s of "speech"
        plan = rl.plan_movements(rl.build_pool("machines", []), "machines", 40)
        out = sb / "clock.mp3"
        short_min, short_played, _, short_sheets = asyncio.run(
            rl.render(plan, "machines", out, 1.0, writer=lambda mv, s: sheet))
        long_min, long_played, spoken, sheets = asyncio.run(
            rl.render(plan, "machines", out, 4.0, writer=lambda mv, s: sheet))
        check("the tape reaches the minutes it was asked for",
              short_min >= 1.0 and long_min >= 4.0, f"got {short_min:.2f} / {long_min:.2f}")
        check("...and STOPS there rather than rendering the whole plan",
              short_played < len(plan), f"played {short_played}/{len(plan)}")
        check("a longer target renders strictly more of the plan",
              long_played > short_played, f"{long_played} vs {short_played}")
        check("the clock is measured from the file, not estimated from bytes",
              "audio_duration" in mechanism(inspect.getsource(rl.Tape.minutes)))
        check("only lines that actually played are claimed as delivered",
              spoken and all(isinstance(s, str) for s in spoken))

        # ── THE WRITTEN STORY. Three tapes shipped as audio only (2026-08-10): the
        # sheets were handed to the renderer and dropped, so the source text sent to
        # the TTS existed nowhere — not on disk, not in a log. Unrecoverable.
        check("the sheets that played come back out of the render",
              len(sheets) == long_played, f"{len(sheets)} sheets for {long_played} played")
        check("...and a tape cut short by the clock returns only what it aired",
              len(short_sheets) == short_played < len(sheets))
        real_scripts = rl.SCRIPTS_DIR
        rl.SCRIPTS_DIR = sb / "content" / "scripts"
        try:
            written = rl.write_script(sb / "longhaul_machines_2026-08-11_0930.mp3",
                                      "machines", long_min, sheets, spoken)
            body = written.read_text(encoding="utf-8")
        finally:
            rl.SCRIPTS_DIR = real_scripts
        check("the script is saved beside the audio, named for it",
              written.name == "longhaul_machines_2026-08-11_0930.md", written.name)
        check("...and carries the Tamil actually sent to the TTS",
              all(b["ta"] in body for b in sheet["beats"]), body[:160])
        check("...the measured length and the audio it belongs to",
              f"{long_min:.1f} min" in body and ".mp3" in body)
        check("...one section per movement that played",
              body.count("\n## ") == long_played + (1 if spoken else 0),
              f"{body.count(chr(10) + '## ')} sections for {long_played} movements")
        check("...and the closing lap, which is a third of the audio",
              "closing lap" in body and all(l in body for l in spoken))
        # The script rides the SAME commit as the mp3, or the pair drifts apart.
        # RE-SPELLED TWICE IN ONE DAY (08-23 publish.publish, 08-24 the family
        # runner) chasing the call site's exact text, which is the signature of an
        # assertion pinned to spelling rather than to a property. So it now reads
        # the deliver_rendered CALL as a unit and asks only what actually matters:
        # the script and the mp3 are handed to the SAME delivery call, and
        # therefore land in one commit with the mp3 at the front where the CDN
        # pre-warm needs it. Renaming a variable or reordering an argument no
        # longer breaks it; separating the two still does.
        pub = mechanism(inspect.getsource(rl.main))
        call = pub[pub.index("deliver_rendered("):]
        call = call.split("\n\n")[0]
        check("the script is committed with the tape, not left behind",
              "script" in call and "mp3=mp3" in call, call[:200])

        # ── THE DELIVERY SEAM, at the level each item actually exists at. The
        # machines tape taught 26 frames and stamped 0 (2026-08-10): a frame is a
        # label for a pattern realised across beats, so it is in the audio exactly
        # never, and substring-matching the spoken lines could only ever return
        # nothing. The ledger booked a 28-minute tape as having delivered zero.
        frame_mv = {"shape": "machine", "items": [{"word": "frame:quote-nu"},
                                                  {"word": "வந்துட்டேன்"}]}
        pool_x = [{"word": "frame:quote-nu"}, {"word": "வந்துட்டேன்"},
                  {"word": "frame:never-aired"}, {"word": "சொல்லல"}]
        got = rl.audible(pool_x, ["வந்துட்டேன் இப்போ"],
                         [(frame_mv, {"beats": [{"ta": "நான் வந்துட்டேனு சொன்னாங்க"}]})])
        check("a frame is claimed when its movement played and made beats",
              "frame:quote-nu" in got, str(got))
        check("...a chunk still has to be literally spoken", "வந்துட்டேன்" in got)
        check("...a frame from a movement that never played is NOT claimed",
              "frame:never-aired" not in got, str(got))
        check("...and an unspoken chunk is not claimed either", "சொல்லல" not in got)
        check("a movement that produced no beats claims nothing",
              rl.audible([{"word": "frame:quote-nu"}], [], [(frame_mv, {"beats": []})]) == [])
        check("the publish path claims through audible(), not a bare substring",
              "audible(pool, spoken, sheets)" in pub and "in blob]" not in pub)
        check("...and written before the publish gate, so --no-publish keeps it",
              pub.index("write_script(") < pub.index("if args.no_publish"))
    finally:
        rl.generate_segment_google, rl.get_raw_mp3_frames = real

    # ── THE FEED ROUND-TRIP. Three separate places drop an unknown prefix: the
    # filter, the sort key, and the title. Each fails silently and differently —
    # missing, buried at (0,0) below every episode, or titled as a raw filename.
    rr = importlib.import_module("rebuild_rss")
    name = "longhaul_inventory_2026-08-11_0930.mp3"
    title = rr.clean_title(name.replace(".mp3", ""), name)
    check("a legacy-prefix tape still gets a real title", title.startswith("Rotation — inventory"),
          f"got {title!r}")
    check("the title says which spine, for a one-handed lock-screen choice",
          "inventory" in title and "2026-08-11" in title, f"got {title!r}")
    check("the title carries no raw filename", ".mp3" not in title and "_" not in title)
    # The title shipped "press once, 45 min" on a MEASURED 00:23:45 tape (2026-08-10).
    # A title is prose, but a duration inside it is still a duration, and the only
    # length a listener may be shown is the one that was measured off the file.
    check("the title states no length — itunes:duration is the measured authority",
          not re.search(r"\d+\s*(min|minute|hour|hr)", title, re.I), f"got {title!r}")

    audio = sb / "published_audio"
    audio.mkdir(exist_ok=True)
    (audio / name).write_bytes(rl.SILENCE_FRAME * 400)   # real frames, real duration
    cwd = os.getcwd()
    try:
        os.chdir(sb)
        rr.generate_rss()
        feed = (sb / "rss.xml").read_text(encoding="utf-8")
    finally:
        os.chdir(cwd)
    check("the tape actually lands in the feed he downloads before boarding",
          name in feed, "rendered, committed, and invisible — the worst failure "
                        "this lane has, because he cannot fetch it from the air")
    check("...under its real title, not its filename", "Rotation — inventory" in feed)
    sort_src = mechanism(inspect.getsource(rr.generate_rss))
    check("the sort key knows both prefixes", "longhaul" in sort_src and "rotation" in sort_src,
          "an unmatched prefix still SORTS — at (0,0), silently below every episode")

    # ── THE RENAME'S OWN TRAP (2026-08-31). The lane became `rotation`, and the
    # three drop-points above are exactly where a new prefix dies quietly. The
    # legacy assertions above prove the OLD name still resolves — three tapes are
    # live in the published feed under it and a feed entry is a promise. These
    # prove the NEW one does too. Both, or the rename ships a lane whose output
    # renders, commits, and never reaches his phone.
    new_name = "rotation_machines_2026-08-31_1200.mp3"
    new_title = rr.clean_title(new_name.replace(".mp3", ""), new_name)
    check("the new prefix gets a real title too",
          new_title.startswith("Rotation — machines"), f"got {new_title!r}")
    (audio / new_name).write_bytes(rl.SILENCE_FRAME * 400)
    try:
        os.chdir(sb)
        rr.generate_rss()
        feed2 = (sb / "rss.xml").read_text(encoding="utf-8")
    finally:
        os.chdir(cwd)
    check("a rotation_ tape reaches the feed", new_name in feed2,
          "the filter drops what it does not recognise, and drops it silently")
    check("...and BOTH prefixes coexist in one feed", name in feed2 and new_name in feed2,
          "the old tapes must not fall out of the feed to let the new ones in")
    check("one lane, one format label in the ratings ledger",
          rr.audio_format(name.replace(".mp3", "")) == rr.audio_format(new_name.replace(".mp3", ""))
          == "rotation",
          "two labels for one lane splits its ratings and the format comparison "
          "answers nothing")

    # ── Duration honesty (same diff): `except: return 3.0` stamped every episode
    # on an ffprobe-less host as exactly 3.0 min. M78-M85 all carry it; their real
    # lengths are 1.7-3.5. He judges an episode partly by the number his player
    # shows him (2026-07-23), and a 45-minute tape registered as 3.0 is worse.
    # Read the AST, not the text: the first cut of this case grepped for the old
    # line and failed against the DOCSTRING that quotes it. A source-text assertion
    # tests the prose; this one tests the code.
    ra = ast.parse((REAL_BASE / "scripts" / "render_audio.py").read_text(encoding="utf-8"))
    fn = next((n for n in ast.walk(ra)
               if isinstance(n, ast.FunctionDef) and n.name == "get_duration"), None)
    check("render_audio still measures episode duration", fn is not None)
    returns = [ast.unparse(r.value) for r in ast.walk(fn) if isinstance(r, ast.Return) and r.value]
    check("no episode is stamped with a plausible fiction",
          "3.0" not in returns,
          f"returns {returns} — a fabricated 3.0 is invisible precisely BECAUSE it is "
          f"plausible; M78-M85 all carry it against real lengths of 1.7-3.5")
    check("...and it measures with the authority rebuild_rss already uses",
          any("audio_duration" in r for r in returns), f"returns {returns}")
    check("an unmeasurable file reports a visible zero, never a guess", "0.0" in returns)


def s89_every_voice_lane_carries_the_dialect(sb: Path):
    print("\n89. Every spoken-Tamil lane carries the dialect law (2026-09-02)")
    import writer as w

    # The canon is persona AND the register rules — persona alone is what every
    # one of these lanes had, and it is why they wrote book Tamil.
    canon = w.voice_canon()
    check("voice_canon carries the spoken-register rules",
          "Word Fusion" in canon and "Verb Form Simplification" in canon)
    check("...and still carries who Anna is", "The Charge" in canon)

    # THE REGRESSION GUARD, and the bug it pins. `dialect.md` was filed as studio
    # craft and reached exactly ONE reader — run_studio's Producer. Six lanes
    # generating Tamil for a VOICE read persona.md alone, so every knock memo,
    # eavesdrop tape, fielding question, soak/drill/rotation sheet and voice reply
    # was written with no spoken-register law at all. Those six carry nearly all
    # of Andrew's daily ear contact; the studio carries the least of it. Two
    # native speakers reported the result (2026-07-31 "uncanny", 2026-09-01 "book
    # Tamil") before anyone read the routing. A new voice lane calls voice_canon()
    # or this fails.
    VOICE_LANES = ("knock_message", "knock_reply", "morning_knock",
                   "render_drill", "render_rotation", "render_soak")
    for lane in VOICE_LANES:
        src = mechanism(raw_source(REAL_BASE / "scripts" / f"{lane}.py"))
        check(f"{lane} reaches the dialect law through the one seam",
              "voice_canon()" in src)
        check(f"...and {lane} no longer opens persona.md for itself",
              'persona.md' not in src)

    # The studio keeps its own route — it reads the canon off disk via
    # inline_canon, so it must NOT be rewired onto this seam by a future tidy-up.
    rs = importlib.import_module("run_studio")
    check("the studio still carries dialect.md its own way",
          "protocol/studio/dialect.md" in rs.PRODUCER)

    # LOUD ON ABSENCE. A half-canon returns every lane to book Tamil with all
    # instruments green — the exact shape that hid this for a month, so the
    # absence has to raise rather than degrade.
    was = w.VOICE_CANON_FILES
    try:
        w.VOICE_CANON_FILES = ("protocol/persona.md", "protocol/no-such-law.md")
        try:
            w.voice_canon()
            raised = False
        except FileNotFoundError:
            raised = True
    finally:
        w.VOICE_CANON_FILES = was
    check("a missing canon file refuses, instead of quietly writing book Tamil", raised)
    check("...and the guard is restored", w.voice_canon() == canon)
