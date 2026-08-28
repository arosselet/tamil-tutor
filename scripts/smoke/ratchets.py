"""The ratchets — the budgets, the linters, and the harness's own self-test.

Every surface this system bounds is asserted here: prose words, Python code
lines, pyflakes findings (budget zero), DECISIONS entry length, the
name-never-line-number rule for docs and skills, and the guard that keeps a
source assertion reading MECHANISM rather than the prose explaining it.

`s72` and `s75` are the odd ones and belong here for the same reason: they
police the machine's own shape rather than a lane's behaviour. `s72` proves
`run`'s teardown actually puts a stubbed name back; `s75` proves the import
graph still points one way, down the stack. A suite whose teardown silently did
nothing, or a stack that quietly grew an upward edge, would still print ALL GREEN.
"""
import ast
import io
import re
import sys
from pathlib import Path

from ._fixtures import (
    check, code_lines, mechanism, ONLY, RAN, raw_source, REAL_BASE, Recorder, run,
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
    # 1250 -> 1320 (2026-08-25, Andrew). THE GROWTH IS A LAW THE FILE DID NOT HAVE:
    # invariant 2 said "Honest cold volume" and named the Gauntlet the volume day,
    # which made the session PRODUCTION-shaped. Andrew's correction that day: "my
    # goal has really been input first… Production is a goal yes, but it came to be
    # of such importance in our system because that's easy to measure." The ear now
    # leads the session, ~3 fires are the probe that feeds the slip ledger, Ear Day
    # is the volume shape, and a heard-in-the-wild line opens the session.
    #
    # RETIRED IN THE SAME DIFF, and the retirement was done FIRST — this number
    # moved only for the 55 words the trimming could not honestly find: the
    # small-denominator narration ("this week's 12: 7 down" — Andrew, same day: "the
    # number isn't what makes me feel progress"), step 7's "campaign's meter", the
    # campaign block's retelling of what profile.md already holds, and four
    # parenthetical glosses that restated the rule they hung off.
    #
    # NOTE FOR THE NEXT RAISE: refuse it and split. The shapes list is ~140 words of
    # a distinct concern — WHICH SHAPE TODAY — and audio_channels.md was cut out of
    # this same file on 07-23 for exactly that reason. A ceiling is a split signal.
    "protocol/daily_session.md": 1320,
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
    # 300 -> 150 (2026-08-27): re-censused DOWN — the SPEAK BACK section left
    # for VOICE_MANDATE, which both judges compose. 280 words -> 134.
    "REACH_MANDATE": 150,
    # New surface, budgeted in the diff that creates it (census 161). It is
    # not net growth: 146 of its words are REACH_MANDATE's, moved so the
    # catch judge stops being mute.
    "VOICE_MANDATE": 175,
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
    "MESSAGE_MANDATE": 230,
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
    # 570 -> 610 (2026-08-27): the reply lane gained a voice rail — the
    # AUDIO_RE detector, ensure_voice's one-forced-re-ask backstop, and a
    # shared speak() body. It RETIRED the inline render block in the
    # production flow and the hard-coded `audio_url=None` in the catch flow,
    # which is why a whole capability cost 36 lines and not 70. This file is
    # now the largest in the tree and has taken three raises: the next one
    # should be a split, not a number (the judges and the lanes are already
    # two jobs living in one file).
    # 610 -> 560 (2026-08-28): re-censused DOWN. The lane-neutral half —
    # detectors, speak(), ensure_voice, record_meta_note, the thread window —
    # left for reply_common.py so the MESSAGE lane could have it without
    # importing the grading lane. This file is grading and routing now.
    "scripts/knock_reply.py": 560,
    # New surfaces, budgeted in the diff that creates them. reply_common is the
    # split the 08-27 raise said was coming; knock_message is the lane that
    # forced it.
    "scripts/reply_common.py": 120,
    "scripts/knock_message.py": 130,
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
    # 470 -> 500 (2026-08-28): MESSAGE_MANDATE landed — the first mandate in
    # this file that only ACTS instead of grading. Growth here is the design:
    # this file exists so a lane's prose lives beside every other lane's, and
    # the alternative was a fourth copy of the speak/schedule rules inside
    # knock_message.py. Prose stays ratcheted per-mandate in PROSE_BUDGETS.
    "scripts/mandates.py": 500,
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
# a hiding place: every OTHER script under scripts/ must carry a budget.
#
# Widened from the one file to the package when the suite was split by layer
# (2026-08-25, §10.4). The exemption is for TEST volume, so it has to name
# wherever the tests now live — and the completeness guard below has to see into
# that directory, or a new production file could hide inside smoke/ unbudgeted.
CODE_BUDGET_EXEMPT = {"scripts/smoke_test.py"}
SUITE = "scripts/smoke/"


def s18_size_budgets(mk, kr, sb: Path):
    print("\n18. Size budgets — prose (words) + Python (code lines) + static clean (0)")
    strings = {"OUTREACH_MANDATE": mk.OUTREACH_MANDATE,
               "JUDGE_MANDATE": kr.JUDGE_MANDATE,
               "REACH_MANDATE": kr.REACH_MANDATE,
               "SLIP_MANDATE": kr.SLIP_MANDATE,
               "THREAD_MANDATE": kr.THREAD_MANDATE,
               "CATCH_JUDGE_MANDATE": kr.CATCH_JUDGE_MANDATE,
               "VOICE_MANDATE": kr.VOICE_MANDATE,
               # reached through the lane that owns it, the same way the
               # knock cases reach reply_common — no re-export just for a test
               "MESSAGE_MANDATE":
                   sys.modules[kr.handle_message.__module__].MESSAGE_MANDATE}
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
        # rglob, not glob: a non-recursive sweep stopped covering the suite
        # the moment it became a package, and proved it — an unused import
        # rode into smoke/queue.py past a green run (2026-08-25).
        found = sum(checkPath(py, Reporter(report, report))
                    for py in sorted((REAL_BASE / "scripts").rglob("*.py")))
        check(f"pyflakes: {found}/0 findings across scripts/", found == 0,
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
    on_disk = {p.relative_to(REAL_BASE).as_posix()
               for p in (REAL_BASE / "scripts").rglob("*.py")}
    unbudgeted = sorted(p for p in on_disk - set(CODE_BUDGETS) - CODE_BUDGET_EXEMPT
                        if not p.startswith(SUITE))
    check(f"every script under scripts/ carries a code budget "
          f"({len(on_disk)} files)",
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


def s52_andrew_is_family_already(sb: Path):
    """The standing fact reaches every role that can invent a first meeting
    (2026-08-04, Andrew).

    M81 opened at the iron gate with sisters-in-law he "recognised from the old
    photos." He has met them a dozen times over ten years. No protocol file
    said so, so each generator filled the blank with the newcomer-integrating
    story — and it read as a stranger's arrival to the one person it is about.

    The silent no-op: if this prose is dropped in a later edit, nothing breaks,
    nothing warns, and the episodes quietly go back to writing him as a guest.
    So the fact is asserted where each role actually reads. The three surfaces
    are not redundant — they are three separate readers: Anna and every Python
    dose inline `persona.md` and never see the constitution; the Architect reads
    the constitution; the Director read NEITHER, which is why the brief invented
    "the expected chaotic joy of a first meeting."
    """
    print("\n52. Andrew is ten years into this family, not arriving (2026-08-04)")
    # Flattened: the prose is hard-wrapped, so a phrase can straddle a newline.
    canon = " ".join((sb / "protocol" / "constitution.md")
                     .read_text(encoding="utf-8").split())
    check("the constitution owns the standing fact",
          "Family Already, Language Not Yet" in canon and "ten years" in canon)
    check("...and forbids the first-meeting framing outright",
          "not a first meeting" in canon and "stranger arriving" in canon)

    # persona.md is the ONLY protocol file morning_knock / knock_reply /
    # render_drill / render_soak inline, so a pointer here would reach nothing.
    persona = (sb / "protocol" / "persona.md").read_text(encoding="utf-8")
    check("persona.md states it in full, not as a cross-reference",
          "not new to this family" in persona and "auditioning for entry" in persona,
          "the doses inline persona.md alone — a pointer to the constitution is a "
          "dangling reference at knock time")
    check("...and the Heist no longer says he is earning his PLACE",
          "earning his place at the table" not in persona,
          "the place is his; the respect for the language is what's earned")

    # The Director writes Scenario Context — the field the first-meeting framing
    # was actually invented in — and its Reads-from list is its whole context.
    director = (sb / "protocol" / "studio" / "director.md").read_text(encoding="utf-8")
    head = director.split("**Goal:**")[0]
    check("the Director's Reads-from now includes the constitution",
          "constitution.md" in head,
          "Scenario Context invents the framing; without this line the Director "
          "reads only profile.md + learner.json and cannot know")


def s78_the_open_gives_before_it_takes(sb: Path):
    """The break contract survives a busy month (2026-08-18, Andrew).

    For a week after touchdown the session opened on collects and traps, and he
    named it himself: "what happened to the coffee & lore at the start of our
    sessions? they disappeared without warning."

    NOTHING WAS CONTRADICTED — that is the whole point of this case. Invariant 1
    listed "field-mission collect" among its own PURE RECEIVING moves, and a
    collect asks him to report. So when the campaign block inverted the channel
    law for the stay ("chat's job is no longer first contact — it is
    decomposition on demand and ambushes"), Anna obeyed both files exactly and
    picked the one gift on the list that was really a demand. A precedence rule
    would have found no conflict to resolve; a payload budget would have found
    no growth. The law had a taker mislabelled as a giver.

    THE SILENT NO-OP that earns the case. The 08-18 repair went into the
    campaign block in `profile.md` and nowhere else — a file whose own header
    says it is "rewritten (not appended) every ~5 sessions", and whose campaign
    block is overwritten whenever the week turns. Measured: 5,968 words on 08-10
    down to 3,383 on 08-14. The fix was scheduled for deletion by design, the
    hole in invariant 1 stayed open, and the day the block was next rewritten
    the coffee would have gone again with every instrument green. So the rule is
    asserted where it is LAW, not where it was noticed.
    """
    print("\n78. The open gives before it takes — the break contract (2026-08-18)")
    # Flattened: the prose is hard-wrapped, so a phrase can straddle a newline.
    law = " ".join((sb / "protocol" / "daily_session.md")
                   .read_text(encoding="utf-8").split())

    head = "1. **Open by giving — the break contract.**"
    check("daily_session.md still declares invariant 1", head in law,
          "the break contract is the one invariant Andrew has personally "
          "reported losing; it may not leave the law silently")
    inv = law.split(head, 1)[1].split("2. **", 1)[0] if head in law else ""

    # The bug lived inside the invariant's OWN enumeration of receiving moves,
    # so that list is what gets read — not the file, where the word "collect"
    # appears legitimately (Close & Log assigns the next field mission).
    bounded = "pure receiving:" in inv and "— Anna performs" in inv
    check("...and its receiving list is still bounded by its two markers", bounded,
          "the enumeration moved or was reworded — this case cannot see the "
          "list any more and fails closed rather than reporting green on a "
          "surface it stopped reading")
    gifts = (inv.split("pure receiving:", 1)[1].split("— Anna performs", 1)[0]
             if bounded else "")
    check("no collect hides in the list of gifts", bounded and "collect" not in gifts,
          "a field-mission collect asks him to report — it is a demand wearing "
          "a gift's clothes, and listing it here is exactly how the open was "
          "lost for a week in August")
    check("...and the law itself defers it until after the performance",
          "waits until Anna has performed" in inv,
          "the deferral lived only in profile.md's campaign block, which is "
          "overwritten every few sessions — if it is not here it is not law")

    # ONE VOICE AT THE DOOR. The brief is Python, so it outranks prose in
    # practice: Anna reads it every open. It printed "open the session on one of
    # these" for the heard-in-the-wild block four lines below the unpaid
    # trailer's "its promised teach OPENS the session" — two claims on one slot,
    # neither of them the law, nothing ordering them.
    brief = mechanism((REAL_BASE / "scripts" / "session_brief.py")
                      .read_text(encoding="utf-8"))
    check("the heard-in-the-wild block does not claim the open",
          "open the session on" not in brief,
          "a wild line is ear work (invariant 2); the brief may route it into "
          "the session, never to the door")
    check("...while the unpaid trailer still does, alone",
          "OPENS the session" in brief,
          "invariant 1 names the trailer payoff as an opening beat — this is "
          "the one Python voice entitled to the slot")


# ── THE STACK, DECLARED (2026-08-25) ─────────────────────────────────────────
# The spine refactor installed one law — "imports point one way, down the stack"
# (DECISIONS 2026-08-23) — and nothing in this suite checked it. Every OTHER law
# it installed is guarded per incident: `s35` reads four named files for a
# hand-rolled waking-hour compare, `s70` reads the Tamil range off `state_io` so
# a fifth copy cannot hide in the case itself. Those close doors a specific bug
# walked through. The law itself had no lock, so a NEW upward edge or a NEW cycle
# landed green — which is exactly how the previous shape accumulated. The
# 23-entry drift class the refactor retired was never one bug repeated; it was
# one missing test repeated.
#
# Fractional rungs where a real dependency forces an order INSIDE a layer:
# `publish` imports `render_chat`, so the derived renderer sits below it; the
# render lanes import `lanes.deliver_rendered`, so the shared tail sits below
# them. `render_audio` is a PRODUCER for L4 — it makes the artifact `publish`
# delivers — so it sits above it and its import is not a violation.
LAYERS = {
    "state_io":           0,      # L0 substrate — imports nothing in scripts/

    "render_chat":        1,      # L1 pure renderers over one source of truth
    "rebuild_rss":        1,
    "generate_callbacks": 1,
    "slips":              1,
    "suggest_targets":    1.5,    # selection — reads L1, read by the lanes
    "sync_state":         2,      # beside L1 — the one writer

    "mandates":           3,      # L3 compose — prompt canon, imports nothing
    "writer":             3,      # L3 compose — executor, model, budget, parsers

    "publish":            4,      # L4 delivery — the ordering, the net, the push
    "render_audio":       4.5,    # a producer FOR L4 — TTS, register, commit

    "lanes":              5,      # L5 what a family shares
    "morning_knock":      5.5,    # L5 the lanes themselves
    "reply_common":       5.6,    # what both inbound lanes share
    "knock_message":      5.7,    # the message lane, above what it reuses
    "knock_reply":        5.8,    # grading + the routing that picks the lane
    "push_queue":         5.5,
    "render_soak":        5.5,
    "render_drill":       5.5,
    "render_longhaul":    5.5,
    "run_studio":         5.5,
    "render_demo":        5.5,

    "session_brief":      6,      # read surfaces, above everything
    "show_status":        6,
}

# An edge that points the wrong way and is allowed to. Each carries WHY, so the
# next one is an argument someone has to write down rather than a merge nobody
# noticed — the same mechanism PROSE_BUDGETS and CODE_BUDGETS already run on.
# This list shrinking is the measure of the next pass; it must never grow
# quietly.
UP_EXCEPTIONS = {
    ("sync_state", "publish"):
        "sync_state hosts the knock-response tap lane, which needs the delivery "
        "tail like any other lane. Retires when the tap becomes a lane of its own.",
    ("sync_state", "session_brief"):
        "the `status` subcommand is a CLI facade over the read surface; deferred, "
        "because a read surface must not be imported at module level.",
}

CYCLE_EXCEPTIONS = {
    frozenset({"morning_knock", "push_queue"}):
        "the queue drains knock memos and the knock enqueues schedules; broken by "
        "a deferred import in maybe_enqueue_schedule. Dies with the L0 residue "
        "push_queue still takes through morning_knock (KNOCK_LOG_PATH, LOCAL_TZ, "
        "load_json).",
    frozenset({"sync_state", "session_brief"}):
        "the `status` CLI facade above; broken by a deferred import in main().",
}


def _import_edges(scripts: Path) -> dict:
    """{(importer, imported): "module" | "deferred"} for intra-repo imports.

    `smoke_test.py` and the `smoke/` package are excluded: the suite imports
    every layer by design and is exempt from the budgets for the same reason.
    A module-level edge outranks a deferred one — a name imported both ways is
    loaded at import time, so the deferral buys nothing.
    """
    mods = {p.stem for p in scripts.glob("*.py")} - {"smoke_test"}
    edges: dict = {}
    for path in sorted(scripts.glob("*.py")):
        if path.stem == "smoke_test":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        deferred_nodes = set()
        for fn in [n for n in ast.walk(tree)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            for n in ast.walk(fn):
                deferred_nodes.add(id(n))
        for n in ast.walk(tree):
            if not isinstance(n, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(n, ast.ImportFrom) and n.level:
                continue
            name = (n.module if isinstance(n, ast.ImportFrom)
                    else n.names[0].name) or ""
            target = name.split(".")[0]
            if target in mods and target != path.stem:
                kind = "deferred" if id(n) in deferred_nodes else "module"
                if edges.get((path.stem, target)) != "module":
                    edges[(path.stem, target)] = kind
    return edges, mods


def _breaks(edges: dict, layers: dict) -> tuple[list, set]:
    """(edges that point strictly UP, cycles) — pure, so the positive control at
    the foot of `s75` can drive it with a synthetic graph. A guard nothing can
    make fail is not a guard; this is what lets the case prove it can."""
    up = sorted((a, b) for (a, b) in edges
                if a in layers and b in layers and layers[a] < layers[b])
    cycles = {frozenset({a, b}) for (a, b) in edges if (b, a) in edges}
    return up, cycles


def s75_the_stack_is_one_way():
    """The law gets a lock, and the exception list gets one too (2026-08-25).

    THE SILENT NO-OP, answered out loud: a graph walk that finds NOTHING passes
    every assertion below vacuously and prints four green lines. That is not
    hypothetical here — `s35` shipped naming the scripts directory through
    `__file__` and had to be corrected to an absolute path DURING this same
    refactor, and a walk pointed at the wrong tree fails exactly that way. So the
    first assertions are teeth on the WALK, not on the law: a known module-level
    edge and a known deferred edge must both come back, which fails if the walk
    breaks, if the directory moves, or if the module/deferred split stops working.

    The second silent no-op is the exception list. An exception whose edge is
    deleted, or whose edge gets REPAIRED so it no longer points up, is a licence
    to break the law that nothing revokes — the shape of "an allowlist that
    outlives what it allowed is not a guard" (2026-08-24), which was written
    after `s70`'s client allowlist went on naming two modules that had stopped
    building clients. So the list can only shrink: handing the licence back is
    part of landing the fix.
    """
    print("\n75. The stack is one way, and every exception is declared (2026-08-25)")
    edges, mods = _import_edges(REAL_BASE / "scripts")

    # ── teeth on the walk itself, before any conclusion is drawn from it ──
    check(f"the walk reached the real tree ({len(mods)} modules, {len(edges)} edges)",
          len(mods) >= 20 and edges.get(("lanes", "publish")) == "module",
          "a floor, not a target: an empty or mis-pointed walk makes every "
          "assertion below pass while checking nothing")
    check("...and it still tells a call-time import from a load-time one",
          edges.get(("morning_knock", "push_queue")) == "deferred",
          "the deferred/module split is what makes a declared cycle legible; "
          "if this collapses, the cycle assertions stop meaning anything")

    # ── 1. no hiding place ──
    unlayered = sorted(mods - set(LAYERS))
    check(f"every module under scripts/ carries a layer ({len(LAYERS)} declared)",
          not unlayered,
          f"unlayered: {', '.join(unlayered)} — add each to LAYERS, which is the "
          f"conversation this guard exists to force")

    # ── 2. the law, and 3. its corollary ──
    up, cycles = _breaks(edges, LAYERS)
    undeclared_up = [p for p in up if p not in UP_EXCEPTIONS]
    check(f"no module imports a strictly higher layer ({len(up)} declared upward)",
          not undeclared_up,
          "upward: " + "; ".join(f"{a}(L{LAYERS[a]}) -> {b}(L{LAYERS[b]})"
                                 for a, b in undeclared_up)
          + " — move the code down, or declare it in UP_EXCEPTIONS with a reason")
    undeclared_cy = sorted(cycles - set(CYCLE_EXCEPTIONS), key=sorted)
    check(f"no undeclared import cycle ({len(cycles)} declared)",
          not undeclared_cy,
          "cycles: " + "; ".join(" <-> ".join(sorted(c)) for c in undeclared_cy)
          + " — a function-local import hides a cycle from Python, never from this")

    # ── 4. the guard's own guard: a licence handed back when the fix lands ──
    gone = sorted(p for p in UP_EXCEPTIONS if p not in edges)
    check("every declared upward exception still describes a real edge",
          not gone,
          "the edge is gone at " + "; ".join(f"{a} -> {b}" for a, b in gone)
          + " — delete the exception with it (2026-08-24)")
    repaired = sorted(p for p in UP_EXCEPTIONS if p in edges and p not in set(up))
    check("...and still describes an edge that actually points UP",
          not repaired,
          "no longer upward: " + "; ".join(f"{a} -> {b}" for a, b in repaired)
          + " — the layering was fixed; the licence to break it should have gone too")
    stale_cy = sorted((c for c in CYCLE_EXCEPTIONS if c not in cycles), key=sorted)
    check("every declared cycle exception still describes a real cycle",
          not stale_cy,
          "the cycle is broken at " + "; ".join(" <-> ".join(sorted(c)) for c in stale_cy)
          + " — delete the exception; that is the win being recorded")

    # ── the positive control — a guard nothing can fail is not a guard ──
    # Driven with a synthetic graph rather than by mutating the tree, so the
    # proof lives in the suite permanently instead of in one session's notes.
    toy_layers = {"low": 0, "mid": 1, "high": 2}
    toy_edges = {("high", "low"): "module",     # legal, downward
                 ("low", "high"): "module",     # illegal: upward AND a cycle
                 ("mid", "high"): "deferred"}   # illegal: upward
    toy_up, toy_cycles = _breaks(toy_edges, toy_layers)
    check("the checker reports an upward edge when one exists",
          toy_up == [("low", "high"), ("mid", "high")], toy_up)
    check("...and reports a cycle when one exists",
          toy_cycles == {frozenset({"low", "high"})}, toy_cycles)
    check("...and reports neither on a graph that only points down",
          _breaks({("high", "low"): "module", ("mid", "low"): "deferred"},
                  toy_layers) == ([], set()),
          "a checker that never fires would read green on every tree")
