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
    check, code_lines, lex_row, mechanism, ONLY, RAN, raw_source, REAL_BASE,
    Recorder, run,
)


# Word budgets for the protocol's prose surfaces (2026-07-16): every incident since
# April landed as a paragraph, and prose only accumulates — "earn its place" didn't
# enforce itself. Growth past a budget is a red run; raising a budget must ride the
# same diff as the growth, and the commit names the lines it retired (/extend Gate 4).
PROSE_BUDGETS = {
    # Set at the 2026-09-02 census (577) rounded up plus headroom, on the day this
    # file stopped being studio craft. It had NO ceiling for its whole life because
    # it was filed under `studio/` and the budgets were written for protocol law —
    # the same misfiling that left it with one reader. It is now read by every lane
    # that sends Tamil to a voice, and its Word Fusion section is the part we expect
    # to grow: three Producer runs over one tape gave three different answers, and
    # the suspected cause is that two examples do not constrain a model. So the
    # growth is FORESEEN, which is exactly when a ceiling is worth having — a fusion
    # table that outgrows this wants to be data the seam applies, not more prose for
    # a model to interpret.
    "protocol/dialect.md": 625,
    # 2000 -> 1750 (2026-09-03). A CEILING COMING DOWN, which is the direction
    # this table has never once moved before today. RETIRED IN THIS DIFF: "The
    # Toolbelt (his reach)", 392 words and this file's largest section, to
    # `protocol/toolbelt.md`. The trigger was the 07-16 law read literally —
    # persona.md stood at 1970/2000, thirty words of headroom, and the law says a
    # file at its ceiling is carrying crud or DOING TWO JOBS. It was doing two
    # jobs: `voice_canon()` ships this file to seven call sites across six lanes,
    # and not one of them can invoke a tool. Re-censused at 1650 (the header
    # gained the reader note the old one lacked), so the budget is the census
    # plus ~6%, the same headroom dialect.md took on 09-02. A budget that does
    # not fall when content leaves is a licence nothing revokes.
    "protocol/persona.md": 1750,
    # NEW FILE, budgeted in the same diff that creates it (2026-09-03) — the
    # prose half of the law CODE_BUDGETS has enforced since 2026-08-23. Census
    # 545, +10%: it is small, and the one growth foreseen is a tool gaining an
    # option, which is a line not a section.
    "protocol/toolbelt.md": 600,
    # Budgeted 2026-09-03, not because it grew but because the completeness
    # sweep added below demanded it: this file has been unbudgeted since it was
    # written, and nothing could see that. Census 353, +13% — it is the smallest
    # law file and the healing loop is evidence-gated, so growth here should be
    # rare. Exempting it instead would have been a licence granted for no reason.
    "protocol/diagnosis.md": 400,
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
    # 300 -> 333 (2026-08-31, Andrew). THE GROWTH IS A JOB THIS PROMPT DID NOT
    # HAVE: the judge saw every Tamil word Andrew picked out of the tape and kept
    # none of them, because the lane scores one declared `expected_target`. The
    # eavesdrop runs below the 95% coverage floor ON PURPOSE, so a partial catch
    # is the designed outcome and its evidence was being discarded — the ear moved
    # 8 times to the mouth's 79 over 07-25 -> 08-31. "heard" records the word he
    # named, guarded in Python by `apply_heard_words`.
    #
    # RETIRED IN THE SAME DIFF, and done FIRST — this number moved only for the 33
    # words the trimming could not honestly find: "English expected; Tamil a bonus,
    # not graded" (superseded — Tamil he names is now recorded, though still not
    # graded), the reply_line block's "when he asks to be TAUGHT … teaching is
    # never a detour" (the same rule as "answer the request, let the asking cost
    # him nothing", two blocks above), and the meta_note field gloss that restated
    # META-DIRECTION on the line before it.
    #
    # NOTE FOR THE NEXT RAISE: refuse it. This prompt now carries two jobs — grade
    # the drift, rule on the words he named — and a third is the split signal.
    "CATCH_JUDGE_MANDATE": 333,
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
    # 560 -> 563 (2026-09-05). RETIRED IN THIS DIFF: the six KNOWN_GAPS licences
    # that stood in for `schedule` on this schema, and with them the outage they
    # were describing — undeclared meant DELETED on the agent path, so every
    # scheduled push this judge composed was dropped before Python saw it. Three
    # lines to declare a key the mandate has always asked for.
    #
    # FLAGGED, NOT HIDDEN: at 563 this is the largest entry in the table, and the
    # budget law says a file that keeps meeting its ceiling wants a split rather
    # than a bigger number. This raise buys a correction, not room to grow; the
    # next one should be a split.
    "scripts/knock_reply.py": 563,
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
    # 450 → 400 (2026-09-04): RE-CENSUSED DOWN, not raised — the same move
    # `knock_reply` made on 08-24 and this file made on 08-01. It sat at 442/450
    # with 8 lines of headroom and now sits at 391, because four things that were
    # never knock-shaped left in one diff: the reach budget to `rails.py`,
    # `render_memo` to `memo.py`, `maybe_enqueue_schedule` to the queue it
    # writes, and `load_json` / `KNOCK_LOG_PATH` / `is_fire` / `local_date` home
    # to `state_io`. Nothing about the knock got smaller; the file stopped being
    # four other things. Nine lines of headroom, which is what it had before.
    # 400 -> 402 (2026-09-05). RETIRED IN THIS DIFF: the two KNOWN_GAPS licences
    # for `schedule` and `volley_asks` on DECIDE_SCHEMA, and the false premise in
    # the comment above it — "undeclared keys still pass through untouched", true
    # of the API path and false of the agent path, which is why both keys were
    # being deleted rather than passed.
    "scripts/morning_knock.py": 402,
    # The mandate as a module: almost entirely prompt string (word-budgeted as
    # OUTREACH_MANDATE in PROSE_BUDGETS above), so its code budget exists only
    # to satisfy the every-file-is-budgeted guard and to catch machinery
    # sneaking into a prose module.
    # 150 → 200 (2026-08-10) for the long-haul BASE_MANDATE and its five
    # SHAPE_CLAUSES, moved out of render_rotation.py when THAT file hit 340/340 —
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
    # render_rotation 08-10, and knock_reply's own budget note had been asking for
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
    # written out three times, in render_soak, render_drill and render_rotation —
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
    # NEW FILE, budgeted in the same diff that creates it (2026-09-04). THE REACH
    # BUDGET — when Anna may reach Andrew, and how often. WHAT IT RETIRES: one
    # concept split across two files at two layers. `publish.py` held the waking
    # window; `morning_knock.py` held the daily cap, the min gap and the counter.
    # Both lanes that reach him obey both halves, so `push_queue` imported half
    # its budget from a FOUNDATION and half from a PEER LANE — and three more
    # modules (`knock_reply`, `knock_message`, `reply_common`) were importing
    # from that lane too. It also ends the `fires_today` collision: this file's
    # counter is `reaches_today`, so `sync_state.fires_today` (words ANDREW
    # fired) is the only `fires_today` left. Chosen over folding the counts into
    # `publish.py` because that file measured 148/150 — a file at its ceiling
    # wants a split, not a raise, and the ceiling picked the boundary the
    # concerns already wanted.
    "scripts/rails.py": 26,
    # NEW FILE, budgeted in the same diff that creates it (2026-09-04). The
    # voice-memo renderer. WHAT IT RETIRES: `render_memo` in `morning_knock.py`,
    # the LAST thing that made a lane a foundation for its peers — the queue's
    # drain and both reply lanes called it there. Not `lanes.py`, whose header
    # says the three families are not one shape and these callers span two of
    # them; not `publish.py`, which would have had to grow the TTS stack at
    # 148/150 lines; not `render_audio.py`, which would have made the episode
    # renderer answer to three lanes that never render episodes.
    "scripts/memo.py": 28,
    # 350 -> 355 (2026-09-01): A TRANSFER, NOT GROWTH, and the sync_state entry
    # below is re-censused DOWN by the same 5 in this same diff — the two ceilings
    # sum to what they summed to yesterday. `compute_recent_audio` and the
    # `RECENT_AUDIO_PATH.write_text` block moved here from `write_thin_learner`,
    # which is what the change IS: the rating picker's list is derived from
    # `rss.xml`, and it was being rewritten on the SESSION clock while its source
    # moved on the PUBLISH clock. Two clocks over one derivation is not a race —
    # it is wrong by default for every dose published between two state writes,
    # and the 09-01 soak was missing from the picker minutes after it landed. A
    # derived file follows its source (2026-08-24), so the writer follows too.
    # NOTE FOR THE NEXT RAISE: this file has now sat at 2 lines of headroom twice
    # (348/350 on 08-29, 353/355 today), and the next number is a SPLIT, not a
    # bump. It builds the feed AND reads it back — `generate_rss` and the item
    # tables are one job, `feed_items`/`knock_meta`/`write_recent_audio` are the
    # readers the picker lane needs, and only the second group has other callers.
    "scripts/rebuild_rss.py": 355,
    # New surface, budgeted in the diff that creates it (2026-09-01). It is also
    # the SPLIT the note above demanded rather than a second raise: naming was
    # about to cost rebuild_rss another 9 lines, and "what a dose is called" is
    # not the same job as "assemble the feed". `LANE_WORD`, the recorded-name
    # lookup and the collision rule live with the map they read; rebuild_rss kept
    # only the two lines that ASK. Set at the census plus normal headroom.
    "scripts/audio_titles.py": 80,
    # 500 → 495 (2026-08-28): re-censused DOWN. The two PINNED voices left for
    # `language.py`. Small in lines and exact in concern: this file owns the TTS
    # STACK and the episode voice POOLS (one reader, one file), and no longer
    # owns an identity fact that six other modules imported through it.
    "scripts/render_audio.py": 495,
    "scripts/render_chat.py": 100,
    "scripts/render_demo.py": 100,
    # 225 → 235 (2026-08-10). RETIRED IN THIS DIFF: `ask_json`'s private parse —
    # the char-0 `json.loads` and the `startswith("```")` fence-strip — replaced by
    # the `parse_llm_response` every other lane already used. That is a deletion;
    # the growth is the retry loop around it, which is mechanism and is the point:
    # a coin-flip parse is survivable in a lane that asks ONCE and fatal in one that
    # asks fifteen times, and the rotation tape died at movement 5 of 15 proving it.
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
    "scripts/render_rotation.py": 325,
    # 275 -> 265 (2026-08-23, Andrew): re-censused DOWN. Its private OpenRouter
    # client — the FOURTH copy, and the first that cost money rather than
    # correctness — became one `writer.ask_json` call.
    # 265 → 210 (2026-08-24): re-censused DOWN — SOAK_MANDATE left for
    # mandates.py with the drill lane's two and the judge's six.
    # 210 → 195 (2026-08-24): re-censused DOWN — SOAK_MANDATE left on 08-24 and the delivery tail left with it.
    "scripts/render_soak.py": 195,
    # Budgeted in the diff that created it (2026-09-05) — a new file with no
    # entry here is a red run, because adding one is the obvious way past a
    # ceiling. Census 224, +7%: 17 of those lines are PAYOFF_BRIEF, which
    # `code_lines` counts as mechanism, so the real mechanism is ~200 and the
    # headroom is one guard, not a feature. NOTE FOR THE NEXT RAISE: refuse it.
    # The brief belongs in `mandates.py` the day this lane stops being the only
    # reader of it — the move `render_drill` and `render_soak` both made — and
    # the walk's rhythm is `render_soak`'s, which is where a second copy would
    # be the thing to retire.
    "scripts/render_payoff.py": 240,
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
    # 110 → 105 (2026-08-28): re-censused DOWN. The script range, the stem tail
    # and `is_tamil` left for `language.py`. The label PORT SURFACE left with
    # them, and that is the point — this file carried the label from 2026-08-04
    # while two more port values (the pinned voices, the repo identity) could
    # never live beside a paths-and-clock module. A label is not a boundary.
    # 105 → 112 (2026-09-04): `local_date` and `is_fire` came home. Both were in
    # `morning_knock.py` — a clock helper and a read-only state predicate, living
    # in a LANE because it needed them first. This file's charter already names
    # that shape ("`local_today`", "the read-only predicates `is_unseen` /
    # `soak_pending`"); they are the third and fourth of exactly those. What the
    # raise retires, in this same diff: `morning_knock`'s duplicate `load_json`,
    # and FOUR independent spellings of `KNOCK_LOG_PATH` (here, `morning_knock`,
    # `render_chat`, `suggest_targets`) of which three are now deleted — plus the
    # two import authorities that grew on top of them, half the lanes asking this
    # file for the path and half asking the knock lane.
    "scripts/state_io.py": 112,
    # NEW FILE, budgeted in the same diff that creates it (2026-08-28, Andrew).
    # THE LANGUAGE PACK — every value a fork to another language replaces, and
    # nothing else. WHAT IT RETIRES: the port surface being a prose list in
    # `BOOTSTRAP.md` cross-checked against four files by hand. Concretely it
    # ends three drifts — `run_studio`'s TAMIL_TAIL_RE (a SECOND script range,
    # invisible to the 08-24 guard because that guard needles only the first),
    # `render_audio` re-exporting the pinned voices to six lanes, and the repo
    # identity spelled out three times across `publish` and `rebuild_rss`.
    # 20, not 11: the headroom is for a port ADDING a value, and every value
    # added here is one subtracted from somewhere it was hiding. If this file
    # ever needs a function longer than `is_tamil`, that is mechanism leaking
    # into a pack and the answer is to put it back, not to raise this.
    # 20 -> 35 (2026-09-03). A TRANSFER, NOT GROWTH — the pack got bigger because
    # five lanes got smaller, and every one of them is under its own ceiling with
    # more headroom than before (morning_knock 448 -> 442, and it was at 448/450).
    # RETIRED IN THIS DIFF, all of it a language fact living outside the file that
    # claims to hold them: `render_audio`'s TWO character-comparison copies of the
    # script range (`any('..' <= c <= '..')` — functionally `is_tamil`, invisible
    # to the 08-28 needle because it shares no spelling with the pattern) and its
    # pinned `language_code="ta-IN"`; `render_demo.lang_of`; `render_rotation`'s
    # pulli literal; `morning_knock.REFERENT_NOUNS`, 26 rows of kinship culture in
    # L5; and `rebuild_rss`'s feed title, summary and caption columns.
    #
    # The ceiling was 20 because the file was six values and a predicate. It is
    # now the port surface it always claimed to be, and `s91` is what keeps the
    # claim honest — the needle guard proves a DECLARED value has one home, and
    # could never have found any of the six above.
    "scripts/language.py": 35,
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
    # 800 -> 795 (2026-09-01): RE-CENSUSED DOWN, not held. The 5 lines are the
    # ones that arrived in rebuild_rss above — `compute_recent_audio` and the
    # picker write inside `write_thin_learner` — and holding 800 after they left
    # would have converted a move into 5 lines of free allowance. Headroom is
    # unchanged at 13 on purpose: a transfer must not loosen either end.
    "scripts/sync_state.py": 795,
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

    # THE SAME LAW, ONE DIRECTORY OVER (2026-09-03). The check above has said
    # since 2026-08-23 that "a new file is the obvious way past a ceiling, so an
    # unbudgeted one is a red run rather than a silent exemption" — and prose is
    # where this system's ceilings actually bind: `constitution.md` sits at
    # 1789/1790 and `daily_session.md` at 1320/1320 as this lands. Yet the prose
    # half of the ratchet had no completeness guard at all, so `PROSE_BUDGETS`
    # policed only the files that had already volunteered.
    #
    # Found while splitting `toolbelt.md` out of `persona.md` — i.e. by doing the
    # exact move the code-side comment describes. Splitting to escape a ceiling
    # is the SANCTIONED move here (daily_session -> audio_channels 2026-07-23;
    # audio_channels -> commissioning 2026-08-01; JUDGE_MANDATE four times), and
    # every one of those splits could have landed its new file unbudgeted with
    # the suite green.
    #
    # GATE 7.2 — WHAT DOES THIS LOOK LIKE WHEN IT SILENTLY DOES NOTHING? Like a
    # passing suite, forever, which is what it did look like. So the first
    # assertion is teeth on the SET, not on the law: a glob that matches nothing
    # would satisfy the emptiness check below while proving nothing at all.
    #
    # TOP LEVEL ONLY, and the boundary is deliberate. `protocol/studio/` is the
    # production crew's craft prose, five files under a different regime that has
    # never been budgeted; sweeping them in here would be a structure decision
    # riding a split's coattails. Routed to `docs/feature_inbox.md` instead.
    prose_on_disk = {p.relative_to(REAL_BASE).as_posix()
                     for p in (REAL_BASE / "protocol").glob("*.md")}
    check(f"the prose sweep sees the protocol surface ({len(prose_on_disk)} files)",
          len(prose_on_disk) >= 8 and "protocol/persona.md" in prose_on_disk,
          f"got {sorted(prose_on_disk)} — a sweep that matches nothing passes the "
          f"assertion below while checking zero files")
    prose_unbudgeted = sorted(prose_on_disk - set(PROSE_BUDGETS))
    check("every top-level protocol file carries a prose budget",
          not prose_unbudgeted,
          f"unbudgeted: {', '.join(prose_unbudgeted)} — add each to PROSE_BUDGETS "
          f"in the same diff that adds the file")


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
    # Below the substrate: the language pack imports NOTHING, not even state_io,
    # which imports it (2026-08-28). It is numbered under L0 rather than beside
    # it so that a future edge pointing the other way — the pack reaching for a
    # path, a clock, or a lexicon — reads as an upward edge and fails here. A
    # pack that can read state is a pack that can grow mechanism.
    "language":          -1,
    "state_io":           0,      # L0 substrate — imports only the pack

    # Between the substrate and the renderers (2026-09-01): it imports only L0,
    # and it is READ by rebuild_rss (L1) and WRITTEN by lanes (L5). Numbered here
    # rather than beside rebuild_rss so that the day it reaches sideways for a
    # renderer — or upward for a lane — the edge reads as upward and fails here.
    # A map of names that can read the feed is a map that can grow opinions.
    "audio_titles":       0.5,

    "render_chat":        1,      # L1 pure renderers over one source of truth
    "rebuild_rss":        1,
    "generate_callbacks": 1,
    "slips":              1,
    "suggest_targets":    1.5,    # selection — reads L1, read by the lanes
    "sync_state":         2,      # beside L1 — the one writer

    # L2 policy — the reach budget (2026-09-04). Imports only L0, and is read by
    # `publish` (L4) AND by both lanes that reach Andrew. That second fact is the
    # whole reason it is a file: the map's L2 line says policy "lives with the
    # lanes that read them", which holds for a policy ONE lane reads and cannot
    # hold for a rail two channels obey. It sat half in `publish` and half in
    # `morning_knock` until this number existed to forbid that.
    "rails":              2,

    "mandates":           3,      # L3 compose — prompt canon, imports nothing
    "writer":             3,      # L3 compose — executor, model, budget, parsers

    "publish":            4,      # L4 delivery — the ordering, the net, the push
    "render_audio":       4.5,    # a producer FOR L4 — TTS, register, commit

    # Above the TTS primitives it composes, below every lane that speaks
    # (2026-09-04). Three lanes call `render_memo` — the knock, the queue's drain
    # and the reply lanes — and they span two of the three families in
    # `lanes.py`, so it is nobody's family and everybody's. Numbered here so the
    # day it reaches sideways for a lane's state, the edge reads as upward.
    "memo":               4.7,

    "lanes":              5,      # L5 what a family shares
    "morning_knock":      5.5,    # L5 the lanes themselves
    "reply_common":       5.6,    # what both inbound lanes share
    "knock_message":      5.7,    # the message lane, above what it reuses
    "knock_reply":        5.8,    # grading + the routing that picks the lane
    "push_queue":         5.5,
    "render_soak":        5.5,
    "render_payoff":      5.5,
    "render_drill":       5.5,
    "render_rotation":    5.5,
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
    # RETIRED 2026-09-04 — morning_knock <-> push_queue. The note that stood here
    # named its own death condition ("Dies with the L0 residue push_queue still
    # takes through morning_knock — KNOCK_LOG_PATH, LOCAL_TZ, load_json"), and
    # that is exactly what happened: the L0 residue went home to `state_io`, the
    # rails went to `rails.py`, `render_memo` went to `memo.py`, and
    # `maybe_enqueue_schedule` went to the queue it writes. The edge is one-way
    # now — the knock calls the queue's public API and the queue calls nothing of
    # the knock's. Handing the licence back is part of landing the fix.
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
    # The probe moved from ("morning_knock", "push_queue") on 2026-09-04, because
    # that edge stopped being deferred — `maybe_enqueue_schedule` moved into the
    # queue it writes, so the knock now imports it at module level and the cycle
    # is gone. A walk-teeth probe must name an edge that is STILL deferred, or it
    # goes green on a broken walk. `sync_state -> session_brief` is the remaining
    # one, deferred in main() because a read surface must not be imported at
    # module level; it is declared in both UP_EXCEPTIONS and CYCLE_EXCEPTIONS.
    check("...and it still tells a call-time import from a load-time one",
          edges.get(("sync_state", "session_brief")) == "deferred",
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


def s92_the_knock_lane_is_not_a_foundation():
    """`morning_knock` has no importers, and that is the whole assertion (2026-09-04).

    WHAT IT CAUGHT. Four peer lanes imported from it — `knock_reply`,
    `knock_message`, `reply_common` and `push_queue` — taking seven names between
    them: `MAX_REACHES_PER_DAY` and `fires_today` (the reach budget, which the
    queue obeys too), `render_memo` (TTS), `maybe_enqueue_schedule` (which writes
    the queue), and `KNOCK_LOG_PATH` / `LOCAL_TZ` / `load_json`, all three of
    which already had a home in `state_io`. None of it was knock-shaped. It was
    in that file because the knock needed it first, and `publish.py`'s header
    records the one time this shape already bit: `render_audio` had to defer
    `from morning_knock import commit_and_push` to dodge a cycle.

    WHY `s75` DOES NOT COVER IT. The stack guard catches an edge pointing to a
    strictly HIGHER layer, and a declared cycle. Three of those four borrows were
    neither: `knock_message` (5.7), `knock_reply` (5.8) and `reply_common` (5.6)
    all sit ABOVE `morning_knock` (5.5), so importing down from them is legal and
    silent. That is precisely how the erosion happened without a red run — the
    law being broken was the OTHER one, "a channel never owns an invariant that
    more than one channel obeys", and nothing had teeth on it.

    WHY THIS NAMES ONE MODULE AND NOT A GENERAL LAW. Some lanes SHOULD be
    imported: `push_queue` is a store with a public API, and `reply_common` and
    `memo` exist to be shared. What separates them from `morning_knock` is intent
    that no walk can read, so the honest guard is the specific fact this diff
    established rather than a rule invented to generalise it. If a second lane
    ever earns the same treatment, this becomes a list.

    THE SILENT NO-OP, answered: a guard that looks up a module by string passes
    vacuously the day that module is renamed or deleted — it would find no
    importers and report green. So the walk is proved first: `morning_knock` must
    still be a module the walk reached, and the walk must still be finding real
    edges, before the absence below means anything.
    """
    print("\n92. The knock lane is not a foundation (2026-09-04)")
    edges, mods = _import_edges(REAL_BASE / "scripts")

    check("the walk still sees morning_knock, and still sees real edges",
          "morning_knock" in mods and edges.get(("morning_knock", "push_queue")) == "module",
          "a floor, not a target: if the module were renamed or the walk broke, "
          "the emptiness asserted below would be free and would mean nothing")

    importers = sorted(a for (a, b) in edges if b == "morning_knock")
    check("no module imports morning_knock",
          not importers,
          f"{', '.join(importers)} import(s) the knock lane — a lane cannot be a "
          f"foundation for its peers. The name wanted belongs in `state_io` (a "
          f"path, a clock, a predicate), `rails` (a reach budget), `memo` (the "
          f"voice renderer) or `push_queue` (the queue's own API), not here.")

    # The positive control — a guard nothing can fail is not a guard.
    synthetic = {("render_soak", "morning_knock"): "module"}
    check("...and the check would actually fail if one appeared",
          [a for (a, b) in synthetic if b == "morning_knock"] == ["render_soak"],
          "the assertion above cannot detect a borrow, so its green means nothing")


def s85_the_fixture_record_tracks_the_minted_one(sb: Path):
    """The suite's lexicon record cannot drift from the one production mints
    (2026-08-29).

    `_fixtures.lex_row` replaced 64 hand-written record literals and the five
    competing `row` lambdas that had grown inside `state.py` alone — three of
    which defaulted neither `recognition` nor `production`. Deduplication on its
    own would have been a lateral move: one stale shape instead of sixty-four.

    GATE 7.2 — WHAT DOES THIS LOOK LIKE WHEN IT SILENTLY DOES NOTHING? It looks
    like ALL GREEN. A fixture is a claim about a shape the production code
    writes, and nothing in the suite ever checked that claim. Add a seventh core
    field to the minted record and every case here goes on exercising the old
    six-field shape: the selection cases still rank, the ledger cases still
    close, and not one of them is testing the record the system now stores. The
    same class as the dropped DEMOTE table — the test tested the function, the
    bug was in the round trip.

    So the guard reads the real mint sites out of `sync_state` by AST and pins
    the builder's defaults to their INTERSECTION. Intersection, not union, is
    the load-bearing choice: a field present at every mint site is part of what
    a record IS, while one present at a single site (`deck`, `direction`,
    `type`) is that caller's elaboration and must stay optional — defaulting it
    would hand every fixture a deck membership it never joined."""
    print("\n85. The fixture's lexicon record tracks the minted one (2026-08-29)")

    def mint_cores(src: str) -> list[set]:
        """Every `lexicon[<key>] = {...}` literal's field set, by AST.

        Reads `raw_source`, not `mechanism`: this file is consumed as a PROGRAM,
        and a parser needs the comments' line numbers to be honest."""
        out = []
        for node in ast.walk(ast.parse(src)):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target = node.targets[0]
            if (isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "lexicon"
                    and isinstance(node.value, ast.Dict)):
                out.append({k.value for k in node.value.keys
                            if isinstance(k, ast.Constant)})
        return out

    sites = mint_cores(raw_source(REAL_BASE / "scripts" / "sync_state.py"))

    # AN ABSENCE MUST BE LOUD. A needle list that comes back empty — the walk
    # broken by a refactor that mints records some other way — would make every
    # assertion below vacuously true, which is this case's own silent no-op.
    check(f"the walk reached real mint sites ({len(sites)} found)",
          len(sites) >= 4,
          f"got {len(sites)} — if minting moved out of `lexicon[k] = {{...}}` "
          f"literals, this guard is reading nothing and must be re-pointed")
    if not sites:
        # Report and stop. `set.intersection(*[])` raises, and a case that ABORTS
        # the run takes the other 82 down with it — found by mutation-testing this
        # very check (2026-08-29). A dead needle must be loud, not fatal.
        return

    core = set.intersection(*sites)
    defaults = set(lex_row())
    check("the builder's defaults ARE the minted core, exactly",
          defaults == core,
          f"builder has {sorted(defaults)}; sync_state mints {sorted(core)} at "
          f"every site — the difference is {sorted(defaults ^ core)}")

    # The optional half stays optional, and the assertion names WHY: these are
    # single-caller elaborations, not part of what a record is.
    optional = set().union(*sites) - core
    check(f"...and the per-caller elaborations stay absent ({sorted(optional)})",
          not (optional & defaults),
          f"leaked into the defaults: {sorted(optional & defaults)}")

    # `heard_on` IS THE ONE THAT MATTERS. It is absent from every mint site on
    # purpose — "minting is Anna DECLARING a level, not observing one" — so
    # solid-by-assertion stays a DERIVED property. It therefore never reaches
    # `core`, but assert it by name: a future mint site that added it would slide
    # it into the intersection, and the sentence above would quietly stop being
    # true while this case stayed green.
    check("`heard_on` is not defaulted — assertion stays derived, not stored",
          "heard_on" not in defaults and "heard_on" not in core,
          "a fixture handed ear-evidence it never earned retires s53's distinction")

    # ── The builder's own contract.
    check("a caller's field wins over the default",
          lex_row(recognition="solid")["recognition"] == "solid")
    check("...and an optional field is added, not rejected",
          lex_row(type="pattern")["type"] == "pattern")

    a, b = lex_row(), lex_row()
    a["seen_in"].append(1)
    a["phonetic"].append("p")
    check("two rows never share a mutable default",
          b["seen_in"] == [] and b["phonetic"] == [],
          f"got seen_in={b['seen_in']}, phonetic={b['phonetic']} — a module-level "
          f"literal would let one case's append leak into the next")

    # ── MUTATION TEST: prove the guard can go red. A schema check that cannot
    # fail is the thing it was written to prevent.
    grown = mint_cores(
        'lexicon[a] = {"gloss": "", "phonetic": [], "recognition": r,\n'
        '              "production": "none", "seen_in": [], "last_surfaced": t,\n'
        '              "confidence": 0}\n'
        'lexicon[b] = {"gloss": "", "phonetic": [], "recognition": r,\n'
        '              "production": "none", "seen_in": [], "last_surfaced": t,\n'
        '              "confidence": 0, "deck": d}\n')
    check("a seventh core field would fail this case, not pass it",
          set.intersection(*grown) - defaults == {"confidence"},
          f"the extractor did not see the added field: {sorted(set.intersection(*grown))}")
    check("...while a single-site field still would not",
          "deck" not in set.intersection(*grown))


def s90_the_toolbelt_left_the_voice_canon(sb: Path):
    """A section that leaves `persona.md` must still reach the session
    (2026-09-03, Andrew — Move 1 of the persona split).

    WHY THE SPLIT. `writer.voice_canon()` ships `persona.md` + `dialect.md` to
    seven call sites across six lanes: the knock decision, both reply judges, and
    the soak / drill / rotation sheet writers. "The Toolbelt" was that file's
    largest section — 392 of 1970 words — and it is a catalogue of scripts
    (`sync_state`, `suggest_targets`, `push_queue`, the studio) that not one of
    those six lanes can invoke. Six generators reasoned every run against a page
    of material they had no way to act on. `persona.md` also stood at 1970/2000,
    thirty words of headroom, and the 2026-07-16 budget law calls a file at its
    ceiling one that is carrying crud or DOING TWO JOBS. It was the latter.

    THE SILENT NO-OP, answered out loud, and it is the reason this case exists
    rather than a diff review. If `.claude/skills/anna/SKILL.md` is never updated
    to load the new file, **Anna still runs a flawless session** — same voice,
    same register, same close, every instrument green — and simply stops reaching
    for `push_queue` and commissioning, because he no longer knows they exist.
    Nothing crashes. Nothing warns. It is indistinguishable from a session that
    had no cause to schedule a push. That is the exact failure family of
    2026-07-24→31 (the meters measured that a step RAN, never that its PURPOSE
    was served), so the teeth below are on the ROUTING, not on the file existing.

    CONSERVATION IS ASSERTED IN BOTH DIRECTIONS. A copy that never deleted leaves
    the tokens in the canon and reads green on "the new file exists"; a delete
    that never copied loses the tools and reads green on "the canon shrank".
    Exactly one of the two files carries the catalogue, and the case says which.
    """
    print("\n90. The Toolbelt left the voice canon and still reaches Anna (2026-09-03)")
    persona = (sb / "protocol" / "persona.md").read_text(encoding="utf-8")
    toolbelt_path = sb / "protocol" / "toolbelt.md"

    # A pointer to a file that is not there is the dangling reference s52 warns
    # about — the doses inline persona.md and resolve nothing for themselves.
    check("persona.md's pointer to the toolbelt resolves",
          "toolbelt.md" in persona and toolbelt_path.exists(),
          "persona.md names protocol/toolbelt.md but the file is missing")
    toolbelt = toolbelt_path.read_text(encoding="utf-8")

    # ── CONSERVATION. The needle is the section's own opening claim; it is prose
    # a rewrite would keep, and it appears nowhere else in the repo.
    NEEDLE = "Anna acts through tools, not vibes"
    check("the catalogue lives in toolbelt.md", NEEDLE in toolbelt)
    check("...and no longer in persona.md", NEEDLE not in persona,
          "a copy that never deleted — the canon still ships the tool catalogue")

    # ── THE POINT OF THE CHANGE, asserted on the real seam rather than on the
    # file. `voice_canon()` is what six lanes actually receive.
    import writer as w
    canon = w.voice_canon()
    check("the voice canon no longer carries the tool catalogue",
          NEEDLE not in canon and "push_queue.py" not in canon,
          "voice_canon still ships tools no voice lane can invoke")
    check("...and still carries the register law and the standing fact",
          "Word Fusion" in canon and "not new to this family" in canon,
          "the split took something the voice lanes need with it")

    # ── THE TEETH: the routing, which is the half that fails silently.
    shim = (sb / ".claude" / "skills" / "anna" / "SKILL.md").read_text(encoding="utf-8")
    check("the session shim loads BOTH halves of the persona",
          "persona.md" in shim and "toolbelt.md" in shim,
          "Anna boots without his tools and the session looks perfect — he just "
          "never schedules a push or commissions audio again")

    # ── AN ABSENCE MUST BE LOUD. A tool quietly dropped from the catalogue is a
    # capability Anna stops reaching for, and a session that never needed it
    # looks identical. Every script the toolbelt claims to give him is named.
    TOOLS = ("sync_state.py", "suggest_targets.py", "generate_callbacks.py",
             "morning_knock.py", "push_queue.py")
    missing = [t for t in TOOLS if t not in toolbelt]
    check(f"the toolbelt still hands Anna every tool it claims ({len(TOOLS)})",
          not missing,
          f"dropped: {', '.join(missing)} — a capability Anna stops reaching for "
          f"is indistinguishable from a day he did not need it")
