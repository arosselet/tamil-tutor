"""The ratchets — the budgets, the linters, and the harness's own self-test.

Every surface this system bounds is asserted here: prose words, Python code
lines, pyflakes findings (budget zero), DECISIONS entry length, the
name-never-line-number rule for docs and skills, and the guard that keeps a
source assertion reading MECHANISM rather than the prose explaining it.

`s72` is the odd one and belongs here for the same reason: it polices the
harness itself, proving that `run`'s teardown actually puts a stubbed name back.
A suite whose teardown silently did nothing would still print ALL GREEN.
"""
import ast
import io
import re
from pathlib import Path

from ._fixtures import (
    check, code_lines, ONLY, RAN, raw_source, REAL_BASE, Recorder, run,
)


# Word budgets for the protocol's prose surfaces (2026-07-16): every incident since
# April landed as a paragraph, and prose only accumulates — "earn its place" didn't
# enforce itself. Growth past a budget is a red run; raising a budget must ride the
# same diff as the growth, and the commit names the lines it retired (/extend Gate 4).
PROSE_BUDGETS = {
    "protocol/persona.md": 2000,
    # 1750 -> 1790 (2026-08-04): FIRST raise of this ceiling, and the growth is a
    # class of content no protocol file owned — a standing fact about the learner's
    # life, not a rule. M81 opened at the iron gate with sisters-in-law "recognised
    # from the old photos"; nothing said Andrew is ten years into this family, so
    # every generator filled the blank with the newcomer story. Retired in the same
    # diff (17 words back): the 08-03 leak clause compressed to its evidence, and
    # the zinger line's "surprise … that delight locals and in-laws". A second raise
    # is the split signal — the Core Philosophy's learner facts would leave first.
    "protocol/constitution.md": 1790,
    "protocol/daily_session.md": 1250,
    # Split out of daily_session.md (2026-07-23) rather than raise its budget:
    # channel routing is its own concern and Anna loads it only when choosing.
    # 400 -> 550 (2026-07-28): the file's JOB doubled by deliberate split, not by
    # crud. It always framed itself as two questions — what a dose carries, and
    # which channel carries it — and owned only the second; the commissioning law
    # ("the repair earns the dose") moved IN from daily_session.md Close & Log,
    # which kept a pointer and came out 43 words leaner. Same move audio_channels
    # itself made in 07-23 and JUDGE_MANDATE in 07-24: a ceiling is a split
    # signal. Raising this is the exception the rule allows — growth and raise in
    # one diff, naming what it retired — not the bump-the-number reflex.
    # 550 -> 640 (2026-07-28 evening, SECOND raise in one day — flagged as such).
    # The growth is a law the file did not have: capacity said WHEN a channel is
    # usable and nothing said WHICH format an error deserves, so "a chunk fires a
    # collision" was the only format guidance and it pointed at the loop for every
    # mix-up. Retired in the same diff: that clause, the "route by the situation"
    # bullet (its veto half is now the table's opening line), and the 07-23 story
    # compressed — 33 words back. THIS IS THE CEILING'S SECOND WARNING. A third
    # raise is not allowed: split "what it carries" from "which format carries it".
    # 640 -> 475 (2026-08-01): THE SPLIT WAS TAKEN, as the line above demanded —
    # "what it carries" left for commissioning.md; this file keeps only routing
    # and format, re-censused down with headroom.
    "protocol/audio_channels.md": 475,
    # Split out of audio_channels.md (2026-08-01) — the commissioning law
    # ("the repair earns the dose") is its own concern from channel routing,
    # and the parent had a third raise refused in advance.
    "protocol/commissioning.md": 300,
    "OUTREACH_MANDATE": 2000,
    "JUDGE_MANDATE": 1500,
    # Split out of JUDGE_MANDATE (2026-07-24) rather than raise its budget, the
    # same move audio_channels.md made on daily_session.md: "what this reply can
    # do beyond the text line" (schedule a push, speak back) is its own concern,
    # and the mandate was at 1498/1500 — a ceiling is a split signal, not a
    # bump-the-number signal.
    "REACH_MANDATE": 300,
    # Split out of JUDGE_MANDATE (2026-07-30) for the third time that file has
    # paid for growth by splitting rather than raising. The slip contract landed
    # it at 1764/1500; recording an error is its own concern from grading one
    # (the judge can grade without it, and a port swapping the Tamil examples
    # touches only this string), so it left as REACH_MANDATE and
    # CATCH_JUDGE_MANDATE did. JUDGE_MANDATE keeps only the JSON key.
    "SLIP_MANDATE": 250,
    # Split out of JUDGE_MANDATE (2026-08-02), the FOURTH time that file has paid
    # for growth by splitting instead of raising. Thread continuity — the 3-hour
    # scene decay, plus reading prior_exchanges across knocks as fact about what
    # Anna already sent — is its own concern from grading a reply, and both the
    # production judge and the catch judge need it identically. The retired lines
    # are JUDGE_MANDATE's old standalone "CONTINUITY DECAYS" paragraph, folded in.
    "THREAD_MANDATE": 250,
    "CATCH_JUDGE_MANDATE": 300,
}


# Words allowed per NEW docs/DECISIONS.md entry (dated 2026-08-02 or later).
# The log's own header has promised "the index of the conclusions — details
# live in git history" since April; July's entries ran 300-600 words of
# narrative each and the file reached 22k words, the accumulation pattern the
# word budgets killed everywhere else (2026-08-01, Andrew's forward cap). The
# archive is deliberately untouched: git owns the narratives already written.
DECISION_ENTRY_BUDGET = 150


# Code budgets for the Python surfaces (2026-07-31): the same ratchet, one layer
# down. The word budget held prose FLAT through July's build-out (8866 words on
# 07-01, 10671 on 07-31) while production Python went 2566 -> 6032 lines with a
# ~10% deletion rate — so April's "fight drift by adding" failure mode simply
# moved to the surface that had no ceiling. Growth past a budget is a red run,
# on the same terms as PROSE_BUDGETS: a raise rides the same diff as the growth
# and the commit names what it retired; a file that keeps hitting its ceiling is
# doing two jobs — split-or-retire, never the bump-the-number reflex.
#
# THE UNIT IS CODE LINES — blanks, comments and docstrings are NOT counted. A
# third of this codebase is comment, and that third is the diagnosis layer: the
# 07-31 silent-failure family was findable only because the "why" sits next to
# the mechanism. A budget that taxed explanation would buy smaller files by
# deleting the thing that makes them debuggable. This bounds mechanism only.
#
# Budgets were set at the 07-31 census rounded up to the next 25 with a minimum
# of 25 lines of headroom — tight enough to bind within weeks at a normal pace,
# loose enough that one ordinary bug fix does not trip it. Headroom is not an
# allowance to spend; it is the room to land a repair without ceremony.
CODE_BUDGETS = {
    "scripts/generate_callbacks.py": 100,
    # 775 -> 785 (2026-08-02) for the thread-continuity window. Retired in the
    # same diff: three inlined ISO-timestamp parsers collapsed into _ts(), the
    # two duplicated per-knock context builders replaced by one recent_exchanges,
    # and the dead reply_memo_script write (nothing ever read it). That paid for
    # most of the feature; these 10 are the remainder.
    # NOTE for the next raise: REFUSE it and split instead. ~150 of this file's
    # lines are prompt strings (JUDGE/SLIP/REACH/THREAD/CATCH mandates), which
    # code_lines counts as mechanism. mandates.py already exists as the home for
    # prompt canon — morning_knock.py made exactly this move on 2026-08-01 and
    # was re-censused DOWN afterwards. This file should follow, not grow again.
    # 785 → 570 (2026-08-24): IT FOLLOWED. RE-CENSUSED DOWN, not raised — the six
    # mandates left for mandates.py exactly as the note above prescribed, 237 lines
    # and 31% of the file. It sat at 758/785 with 27 lines of headroom; it now sits
    # at 556 with real room to take a feature. The note above is discharged, and
    # the next raise on THIS number is about mechanism, with no prose left to blame.
    "scripts/knock_reply.py": 570,
    # 700 -> 625 (2026-08-01): re-censused DOWN after OUTREACH_MANDATE moved to
    # mandates.py — the file sat at 699/700, one mechanical fix from a red build.
    # The split is the ceiling law working, not an allowance: prompt canon and
    # dispatch machinery are two concerns, and only one of them is code.
    # 625 → 632 (2026-08-05, Andrew): `parse_llm_response`, the finish_reason
    # guard. What it replaces is an IDIOM, not lines — the bare
    # `parse_llm_json(resp.choices[0].message.content)` repeated at all three
    # call sites, each of which reported a blown token ceiling as a parse error.
    # Stated plainly because the ratchet asks: this is +7 with nothing deleted,
    # the diagnosis layer growing, not mechanism. If this file trips again on
    # mechanism, that is the split-or-retire signal — not this.
    # 632 → 635 (2026-08-10, Andrew): the transit rail — a `quiet_until` date in
    # learner.json that holds every knock, read first in rails_gate so a held
    # tick returns before the LLM and writes nothing. Stated plainly because the
    # ratchet asks: this is +3 with NOTHING deleted. It buys a rail that did not
    # exist, and deleting those three lines removes the feature whole — which is
    # the point, it was commissioned to be easily removable. The 08-01 split note
    # still stands as the answer to the next raise.
    # 635 → 636 (2026-08-18, Andrew): `budget()` and its REASONING_HEADROOM. Stated
    # plainly because the ratchet asks: this is +1 with nothing deleted here, and
    # nothing deleted elsewhere either — seven `max_tokens` literals became seven
    # `budget(N)` calls. What it replaces is an IDIOM, like the 08-05 raise above:
    # each call site guessing a ceiling that had to cover BOTH its artifact and the
    # model's thinking. Reasoning cost is a property of MODEL, so it lives beside
    # MODEL; the alternative is what actually happened — the reply judge patched in
    # isolation on 08-05 and the same bug taking the knock lane and the drill sheet
    # down together on 08-18. One line, and a model swap can no longer half-land.
    # 636 → 637 (2026-08-18, Andrew): OPENROUTER_MODEL, derived from MODEL. +1 with
    # nothing deleted, and it buys the invariant Andrew asked for by name — the
    # model is STATED once and the two executors (claude -p local, API in Actions)
    # can only differ in slug shape, never in generation. The line it replaces was
    # a hardcoded vendor-prefixed slug that made "one model everywhere"
    # unenforceable; the studio had quietly been running a different one.
    # 637 → 475 (2026-08-23, the spine refactor). RE-CENSUSED DOWN, not raised —
    # this file sat at exactly 637/637, zero headroom, and 36% of it was not a
    # knock. The delivery tail (load_env, the rebase net, commit_and_push,
    # refresh_feed, jsdelivr_url, the waking window, push_to_phone) went to the
    # new publish.py; the model constants, budget() and both parsers went to
    # writer.py; the two pinned voices went to render_audio.py, which owns TTS.
    # Nine of the twenty-one other modules imported this file and almost none of
    # them wanted the knock. Same move it made on 2026-08-01 for OUTREACH_MANDATE,
    # and the same law: a mandate at its ceiling gets split, not raised.
    "scripts/morning_knock.py": 450,
    # The mandate as a module: almost entirely prompt string (word-budgeted as
    # OUTREACH_MANDATE in PROSE_BUDGETS above), so its code budget exists only
    # to satisfy the every-file-is-budgeted guard and to catch machinery
    # sneaking into a prose module.
    # 150 → 200 (2026-08-10) for the long-haul BASE_MANDATE and its five
    # SHAPE_CLAUSES, moved out of render_longhaul.py when THAT file hit 340/340 —
    # the split its own budget note prescribed, and the one morning_knock made on
    # 08-01. This is the ceiling law working as designed: the growth landed in the
    # prose module instead of the lane. Raising it here is cheap precisely because
    # this budget is a machinery TRAP, not a size limit — every line it now counts
    # is prompt string, and prompt strings are word-budgeted in PROSE_BUDGETS above.
    # What must still trip it is a def, a loop, or an import sneaking in.
    # 200 → 470 (2026-08-24). The other NINE prompt constants arrived: the reply
    # judge's six from knock_reply.py, the drill lane's two, the soak lane's one.
    # Ten of the repo's thirteen lived in a lane; all thirteen live here now.
    # This is the third time this move has been made — morning_knock 08-01,
    # render_longhaul 08-10, and knock_reply's own budget note had been asking for
    # it in writing since 08-02 ("REFUSE the next raise and split instead").
    # Cheap for the same reason the 08-10 raise was: this budget is a machinery
    # TRAP, not a size limit. Every line it counts is prompt string, and prompt
    # strings are word-budgeted individually in PROSE_BUDGETS above — JUDGE_MANDATE
    # 1500, REACH 300, SLIP 250, THREAD 250, CATCH_JUDGE 300, OUTREACH 2000. The
    # ceiling that actually binds this prose did not move an inch.
    "scripts/mandates.py": 470,
    # NEW FILE, budgeted in the diff that creates it (2026-08-24, Q1's first
    # family). What it retires: the exposure -> stamp -> commit -> notify tail
    # written out three times, in render_soak, render_drill and render_longhaul —
    # and about to be written a fourth and fifth time by the media-ingestion and
    # daily-catch lanes. Deliberately TINY, and it stays tiny: the seven lanes are
    # three families, not one shape, so this holds a thin runner per family and
    # never a single run_lane(). If it starts growing, something lane-specific has
    # leaked in — most likely push_queue, which makes zero LLM calls at fire time
    # by design and must never be given a writer stage.
    "scripts/lanes.py": 60,
    # NEW FILE, budgeted in the same diff that creates it (2026-08-23, the spine
    # refactor). What it retires: `morning_knock.py` owning the delivery tail for
    # seven lanes, 26 hand-built commit-path lists, and two import cycles that
    # forced `render_audio` and `sync_state` to defer their imports to function
    # scope. L4 has one owner now; a lane hands over what it produced and does not
    # own the ordering, the quiet-hours check, or the commit list.
    "scripts/publish.py": 150,
    "scripts/push_queue.py": 250,
    "scripts/rebuild_rss.py": 350,
    "scripts/render_audio.py": 500,
    "scripts/render_chat.py": 100,
    "scripts/render_demo.py": 100,
    # 225 → 235 (2026-08-10). RETIRED IN THIS DIFF: `ask_json`'s private parse —
    # the char-0 `json.loads` and the `startswith("```")` fence-strip — replaced by
    # the `parse_llm_response` every other lane already used. That is a deletion;
    # the growth is the retry loop around it, which is mechanism and is the point:
    # a coin-flip parse is survivable in a lane that asks ONCE and fatal in one that
    # asks fifteen times, and the long-haul tape died at movement 5 of 15 proving it.
    # NOTE for the next raise: this file now holds a drill lane AND the LLM-call
    # helper three lanes import. That is the two-jobs smell, and the split is
    # already named — ask_json belongs beside parse_llm_json, not here.
    # 235 -> 220 (2026-08-23, Andrew): re-censused DOWN, the 08-01 move again.
    # `ask_json` left for writer.py, taking the executor choice with it — this
    # file owns drills, not how every lane talks to a model. The ratchet working,
    # not an allowance.
    # 220 → 195 (2026-08-24): re-censused DOWN — DRILL_MANDATE and LINT_MANDATE
    # left for mandates.py. This lane had THREE lines of headroom.
    # 195 → 185 (2026-08-24): re-censused DOWN — DRILL/LINT mandates left on 08-24 and the delivery tail left with it.
    "scripts/render_drill.py": 185,
    # New file 2026-08-10 at 318 lines — the fourth audio lane. ~45 of those are
    # BASE_MANDATE + the five SHAPE_CLAUSES, which code_lines counts as mechanism
    # (prompt strings always do). Budgeted at 340 rather than 400: the headroom is
    # for diagnosis, not for a sixth shape. If this trips, the move is the one
    # morning_knock made on 08-01 and knock_reply was told to make — the mandates
    # go to mandates.py, prompt canon and dispatch machinery being two concerns —
    # NOT a bumped number.
    # 340 → 325 (2026-08-24): re-censused DOWN — the delivery tail left for lanes.py on 08-24.
    "scripts/render_longhaul.py": 325,
    # 275 -> 265 (2026-08-23, Andrew): re-censused DOWN. Its private OpenRouter
    # client — the FOURTH copy, and the first that cost money rather than
    # correctness — became one `writer.ask_json` call.
    # 265 → 210 (2026-08-24): re-censused DOWN — SOAK_MANDATE left for
    # mandates.py with the drill lane's two and the judge's six.
    # 210 → 195 (2026-08-24): re-censused DOWN — SOAK_MANDATE left on 08-24 and the delivery tail left with it.
    "scripts/render_soak.py": 195,
    # 425 → 429 (2026-08-20): the first-line H1 lint. It retires the accidental
    # episode title — the Architect was never told to emit one, so 30 of the
    # first 90 episodes shipped to the PUBLIC feed named `Tier2 Mission90`
    # (rebuild_rss.get_title_from_md reads one line and falls back to the
    # filename). Four lines to stop a defect that was public and compounding.
    #
    # HONEST NOTE, per this table's own rule — a file at its ceiling is a
    # split-or-retire signal, not a bump: this file WAS at exactly 425/425, and
    # it is carrying real crud. `openrouter_pass` + `inline_canon` +
    # `resolve_writer` + the `--writer` flag are ~111 lines maintained for
    # "GitHub Actions", which never invokes run_studio.py at all (anna.yml has
    # no studio step). Retiring that branch is the actual answer and it is
    # Andrew's call, not a bump this diff gets to make for him — and this raise
    # does not make it: 429 → 430 (2026-08-23, Step 4 of the spine refactor) is
    # +1 for a CONSOLIDATION, not for mechanism. RETIRED IN THIS DIFF: this
    # file's own `shutil.which("claude")` host test — a second implementation of
    # `writer.have_agent()` — in both `resolve_writer` and `writer_preflight`,
    # and the `import shutil` that served only them. Two deferred imports of one
    # shared test cost one line more than two copies of the test; that is the
    # whole delta. The split note above still stands, unpaid.
    # NEW FILE, budgeted in the same diff that creates it (2026-08-23, Andrew).
    # What it retires: three lanes that opened an OpenRouter client
    # unconditionally on a host with a paid subscription, plus render_drill's
    # `ask_json`. One place decides who makes a JSON call, and it decides by
    # asking which BINARY exists — never by a flag a lane has to remember.
    # 150 → 175 (2026-08-23, Step 4 of the spine refactor). RETIRED IN THIS DIFF:
    # the LAST raw `OpenAI(...)` client outside this module. `ask_text` is what
    # `rephrase_phonetic` needed and never had — a host choice for a TEXT lane,
    # which the JSON-only framing of the 08-23 rule left out. That lane is
    # reachable from both the knock and the reply push-back and ran on every body
    # carrying script, billing cash on a laptop with a subscription already paid
    # for. Three lanes stopped building clients for these lines; the count moved
    # here because the mechanism did.
    # 75 → 150 (2026-08-23, the spine refactor). RETIRED IN THIS DIFF: this
    # module's upward import of `morning_knock` — a leaf lane — for the model
    # constants, `budget()` and both JSON parsers. L3 cannot borrow its own
    # vocabulary from L5; that import was the clearest single instance of the
    # law this refactor installs. The block did not grow, it moved: every line
    # counted here left morning_knock.py in the same commit, which is re-censused
    # DOWN by 165 for it. Growth paid for by a reduction, not an allowance.
    "scripts/writer.py": 175,
    "scripts/run_studio.py": 430,
    "scripts/show_status.py": 125,
    # The state layer's shared vocabulary, split out of sync_state 2026-08-04:
    # paths, load/save, and token->canonical-key resolution. Ten scripts were
    # importing these FROM the state brain. Deliberately tiny and dependency-free
    # — if this file starts growing, something that mutates state has leaked in.
    # 60 → 110 (2026-08-23, the spine refactor's last step). RETIRED IN THIS DIFF:
    # the sync_state <-> suggest_targets import cycle, and the deferred import
    # that patched it ("lazy: suggest_targets imports us"). `soak_pending`,
    # `is_unseen` and the payload resolvers `soak_pending` depends on came DOWN
    # here; `reconcile_focus`, which WRITES, stayed up in sync_state. The test
    # above still holds and is the reason the split is legible: nothing that
    # mutates state moved: these four read and decide, and they land beside
    # `resolve`/`is_tamil`, which is the same job one rung narrower.
    "scripts/state_io.py": 110,
    # The slip ledger, split out of sync_state 2026-08-04. Always a subsystem
    # in a file about something else: it owns progress/slip_log.json outright
    # and is reached from three call sites. Imports state_io only — never
    # sync_state, which imports FROM here.
    "scripts/slips.py": 300,
    # The agent-facing session load, split out of sync_state 2026-08-04. A READ
    # surface: it renders state and never mutates it, which is why it no longer
    # lives inside the writer. Sits ABOVE sync_state in the import graph.
    "scripts/session_brief.py": 250,
    "scripts/studio_watchdog.py": 125,
    "scripts/suggest_targets.py": 575,
    # 1250 -> 1254 (2026-08-04): the tap lane's stage/commit/pull/push moved IN
    # from the "Log tap" step of anna.yml, where it was a hand-rolled
    # `git pull --rebase` with no union resolution and no derived re-render —
    # the one writing lane with no net under it. Nothing in THIS file was
    # retired, so this is a real raise, not a re-census: 5 lines of unbudgeted
    # YAML became 7 of budgeted Python. That is the ceiling law noticing
    # machinery migrate into a file that counts it from a file that doesn't, and
    # the alternative was leaving the gap open to keep a number flat.
    # 1254 -> 800 (2026-08-04): re-censused DOWN after the three-way split, the
    # same move morning_knock made on 08-01. The raise above still stands on its
    # own terms — the tap lane's 7 lines are still here, in cmd_knock_response —
    # but ~480 lines left for state_io, slips and session_brief, so a 1254
    # ceiling would have stopped measuring anything. The new number is the
    # post-split file plus normal headroom, not a target to grow into.
    "scripts/sync_state.py": 800,
}


# EXEMPT, deliberately: /extend Gate 7 requires a new case here the day a bug is
# fixed. Budgeting the file that carries the regression net would put the two
# mechanisms in direct conflict and the budget would win — a fixed bug would
# arrive with a reason not to pin it. Test volume is the one growth this system
# wants unbounded. The completeness guard below is what keeps this from becoming
# a hiding place: every OTHER scripts/*.py must carry a budget.
CODE_BUDGET_EXEMPT = {"scripts/smoke_test.py"}


def s18_size_budgets(mk, kr, sb: Path):
    print("\n18. Size budgets — prose (words) + Python (code lines) + static clean (0)")
    strings = {"OUTREACH_MANDATE": mk.OUTREACH_MANDATE,
               "JUDGE_MANDATE": kr.JUDGE_MANDATE,
               "REACH_MANDATE": kr.REACH_MANDATE,
               "SLIP_MANDATE": kr.SLIP_MANDATE,
               "THREAD_MANDATE": kr.THREAD_MANDATE,
               "CATCH_JUDGE_MANDATE": kr.CATCH_JUDGE_MANDATE}
    for rel, budget in PROSE_BUDGETS.items():
        words = (len(strings[rel].split()) if rel in strings
                 else len((sb / rel).read_text(encoding="utf-8").split()))
        check(f"{rel}: {words}/{budget} words", words <= budget,
              f"over by {words - budget} — retire lines, or raise the budget in this "
              f"same diff and name what it retired")

    # Read the real tree, not the sandbox: the budget binds the source as
    # committed, and the sandbox omits files by ignore-pattern.
    for rel, budget in CODE_BUDGETS.items():
        lines = code_lines((REAL_BASE / rel).read_text(encoding="utf-8"))
        check(f"{rel}: {lines}/{budget} code lines", lines <= budget,
              f"over by {lines - budget} — retire code, or raise the budget in this "
              f"same diff and name what it retired (comments and docstrings are "
              f"free; this counts mechanism only)")

    # STATIC CLEAN — the ratchet's fourth unit, budget zero (2026-08-04).
    #
    # The suite above proves BEHAVIOUR, and it can only prove what it executes.
    # Python resolves module globals at call time, so a name that no longer
    # exists is invisible until some test happens to run that exact line. On
    # 2026-08-04 the state_io extraction dropped the DEMOTE table; sync_state
    # still imported, every CLI path still ran, and 53 cases reported ALL GREEN
    # on a `--stuck-word` close that would have raised NameError — because
    # nothing demoted a word. pyflakes found it without running anything.
    #
    # This is the actionlint argument one language over. That linter was added
    # after a workflow that was valid YAML but rejected by GitHub sat unrunnable
    # through four pushes while this very suite went green beside it: "a file
    # that parses is not a workflow that runs" (smoke.yml). A file that imports
    # is not a file that runs either.
    #
    # Zero, not a number to tune. pyflakes has no severity levels and no
    # suppression pragma by design — it reports only what is nearly always a
    # bug, so the honest budget is none. A finding is either a defect or dead
    # code, and both get FIXED rather than allowed. When something must stay
    # that looks unused, make its purpose legible in code (run_studio's dispatch
    # lock became a module global with a comment) rather than parked behind a
    # directive this repo does not read.
    try:
        from pyflakes.api import checkPath
        from pyflakes.reporter import Reporter
    except ImportError:
        check("pyflakes is installed (declared in requirements.txt)", False,
              "pip install -r requirements.txt — the static gate cannot be "
              "skipped quietly; an absent linter reported as a pass is the "
              "silent no-op this rule exists to prevent")
    else:
        report = io.StringIO()
        found = sum(checkPath(py, Reporter(report, report))
                    for py in sorted((REAL_BASE / "scripts").glob("*.py")))
        check(f"pyflakes: {found}/0 findings across scripts/*.py", found == 0,
              f"undefined names, unused imports and dead locals are all defects "
              f"or dead code — fix them, never budget for them:\n{report.getvalue()}")

    # The decision log's forward entry cap — same law, third unit. Only entries
    # dated on/after 2026-08-02 are bound; a long conclusion goes in the commit
    # message, where the header says details live.
    entries, cur = [], None
    for line in (REAL_BASE / "docs" / "DECISIONS.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("- **"):
            cur = [line]
            entries.append(cur)
        elif cur is not None and (line.startswith("  ") or not line.strip()):
            cur.append(line)
        else:
            cur = None
    over = []
    for e in entries:
        m = re.search(r"\((\d{4}-\d{2}-\d{2})", " ".join(e[:2]))
        if m and m.group(1) >= "2026-08-02":
            words = sum(len(ln.split()) for ln in e)
            if words > DECISION_ENTRY_BUDGET:
                over.append(f"“{e[0][4:50]}…” at {words}")
    check(f"new DECISIONS entries stay ≤{DECISION_ENTRY_BUDGET} words "
          f"({len(entries)} entries scanned)", not over,
          "; ".join(over) + " — the log is an index of conclusions; the "
          "narrative belongs in the commit message (2026-08-01)")

    # ── NAME, NEVER LINE NUMBER (2026-08-01, and §9 of the spine plan repeats
    # it). A pointer like "`state_io.py` line 54" is wrong the moment anything
    # above it moves, and it fails SILENTLY: the reader lands on an unrelated
    # line and believes it. The spine refactor moved three of these out from
    # under their pointers in one day — `ANNA_VOICE` to `render_audio`, the
    # waking window and `REPO` to `publish` — and every routing table still sent
    # a reader to `morning_knock.py`, which no longer had them.
    #
    # Narrow on purpose: a line number ONLY counts as a pointer when a `.py`
    # file is named just before it, so `/debug`'s real JSON errors ("Expecting
    # value: line 1 column 1") are untouched. Prose is exempt from a lot here;
    # an address that rots without saying so is not prose.
    stale = []
    for root in (REAL_BASE / ".claude" / "skills", REAL_BASE / "docs"):
        for f in sorted(root.rglob("*.md")):
            for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                m = re.search(r"\.py`?[^|\n]{0,60}?\blines?\s+\d+", ln, re.I)
                if m:
                    stale.append(f"{f.relative_to(REAL_BASE)}:{i} ({m.group(0)[-40:]})")
    check(f"docs and skills address code by NAME, not line number "
          f"({len(stale)} stale pointers)", not stale,
          "; ".join(stale) + " — name the function or constant instead; a line "
          "number is wrong the next time anything above it moves, and it rots "
          "without saying so (2026-08-01)")

    # ── A SOURCE ASSERTION READS MECHANISM, NEVER RAW (2026-08-24). Checked on
    # this file itself, because this file is the only one that reads other files'
    # source in order to assert on it.
    #
    # The failure is silent in the worst direction: a grep for `X in src` is
    # satisfied by the COMMENT explaining X as readily as by X, so a check can go
    # on reading green after the thing it guards is deleted. Measured, not feared
    # — `s57` asserted "ask_json re-raises the final failure" and passed with the
    # re-raise removed, because "raise" is in the docstring; and the watchdog's
    # "uses the shared resolver" matched a comment naming a function that lane has
    # never called. The rule was already written down twice: `code_line_numbers`
    # was split out for it on 2026-08-10, and `s57` rolled a local copy the same
    # day. It had reached 3 of 23 sites. Now there is one door, and this is the
    # lock on it.
    #
    # `ast.parse` and the line counters are legitimate raw readers: they consume
    # the whole file as a program, not as text to grep.
    # WIDENED to the whole suite when smoke/ was created (2026-08-25, §10.4).
    # The counters this guard polices moved to smoke/_fixtures.py, and the cases
    # that call them are moving to smoke/*.py behind them. A scan still naming
    # only smoke_test.py would keep passing while covering less and less of what
    # it exists to police — the guard's own silent no-op.
    suite = [REAL_BASE / "scripts" / "smoke_test.py",
             *sorted((REAL_BASE / "scripts" / "smoke").glob("*.py"))]
    wrapped, raw = [], []
    for sm_path in suite:
        sm_src = raw_source(sm_path)
        sm_tree = ast.parse(sm_src)
        here, here_raw = [], []
        for node in ast.walk(sm_tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("mechanism", "code_lines", "code_line_numbers",
                                     "raw_source")):
                continue
            for a in node.args:
                here.append((a.lineno, a.end_lineno))
        for node in ast.walk(sm_tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("read_text", "getsource")):
                continue
            seg = ast.get_source_segment(sm_src, node) or ""
            if node.func.attr == "read_text" and ".py" not in seg:
                continue          # prose files are read raw on purpose
            if any(a <= node.lineno and node.end_lineno <= b for a, b in here):
                continue
            here_raw.append(node.lineno)
        # `ast.parse(...)` consumers, resolved the same way as the wrappers above.
        for node in ast.walk(sm_tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "parse" and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "ast"):
                for a in node.args:
                    here_raw = [ln for ln in here_raw
                                if not (a.lineno <= ln <= a.end_lineno)]
        wrapped += here
        raw += [f"{sm_path.name}:{ln}" for ln in here_raw]
    check(f"every Python-source assertion reads MECHANISM, not raw text "
          f"({len(wrapped)} wrapped)", not raw,
          f"raw reads at {', '.join(raw)} — wrap in mechanism(); a grep "
          f"over raw source is satisfied by the comment explaining the code")

    # A new file is the obvious way past a ceiling, so an unbudgeted one is a
    # red run rather than a silent exemption.
    on_disk = {f"scripts/{p.name}" for p in (REAL_BASE / "scripts").glob("*.py")}
    unbudgeted = sorted(on_disk - set(CODE_BUDGETS) - CODE_BUDGET_EXEMPT)
    check(f"every scripts/*.py carries a code budget ({len(on_disk)} files)",
          not unbudgeted,
          f"unbudgeted: {', '.join(unbudgeted)} — add each to CODE_BUDGETS in "
          f"the same diff that adds the file")


def s72_a_stub_never_outlives_its_case(mk, kr):
    """A stub that outlives its case is how a test comes to exercise something it
    never meant to (2026-08-24).

    THE SILENT NO-OP, answered out loud: if `restore()` did nothing whatever,
    this suite would still print ALL GREEN. Measured the day it was built — 68 of
    the 70 cases pass alone against a fresh sandbox with no inherited stubs at
    all — so teardown cannot be verified by the suite passing. It has to be
    asserted in the dimension it actually fails: a name still bound to a stub
    after the case that installed it has returned.

    The bug it closes was live, not hypothetical. `s50` reached `decide()` only
    because `s3`, forty cases earlier, stubbed `rails_gate` out and never put it
    back; reorder the list and the case silently stopped testing its own subject
    while staying green. Four more cases carried "needs the real X — s3+ stubs it
    out" comments and had been hoisted above `s3` by hand to dodge the same
    thing. Those four are back in numeric order because this holds.
    """
    print("\n72. A stub never outlives its case (2026-08-24)")
    real_push, real_judge = mk.push_to_phone, kr.judge
    sentinel = Recorder()

    def _s72_probe():
        mk.push_to_phone = sentinel
        kr.judge = sentinel
        mk.a_name_no_module_has = sentinel

    def _s72_probe_that_raises():
        mk.push_to_phone = sentinel
        raise RuntimeError("a case may fail; the next one still gets clean modules")

    # `run` filters on ONLY, and the probes must run even when the suite was
    # narrowed to this one case. Clear it around them, and keep them out of the
    # RAN report — they are apparatus, not cases.
    saved, ONLY[:] = list(ONLY), []
    try:
        run(_s72_probe)
        check("a replaced name is put back", mk.push_to_phone is real_push,
              f"got {mk.push_to_phone!r}")
        check("...on every module the case touched", kr.judge is real_judge,
              f"got {kr.judge!r}")
        check("...and a name the case INVENTED is removed, not left behind",
              not hasattr(mk, "a_name_no_module_has"))

        raised = False
        try:
            run(_s72_probe_that_raises)
        except RuntimeError:
            raised = True
        check("a raising case still surfaces its error", raised)
        check("...and the modules are clean anyway — teardown is in a finally",
              mk.push_to_phone is real_push, f"got {mk.push_to_phone!r}")
    finally:
        ONLY[:] = saved
        RAN[:] = [r for r in RAN if not r.startswith("_s72_probe")]

    # The property the four un-hoisted cases now rely on: nothing in the list
    # before them can have replaced what they assert against.
    check("the real push_to_phone is a function, not a Recorder",
          callable(real_push) and not isinstance(real_push, Recorder))


def run_all(mk, kr, pq, sb):
    run(s18_size_budgets, mk, kr, sb)
    run(s72_a_stub_never_outlives_its_case, mk, kr)
