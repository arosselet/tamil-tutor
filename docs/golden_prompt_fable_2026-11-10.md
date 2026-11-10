# Golden prompt for Fable 5.2 — Tamil tutor, 2026-11-10

Andrew has a week of access to Fable 5.2, with a limited weekly Claude quota and an assignment due. This prompt is the whole brief, in one session. Read it, read the code, return artifacts, not opinions. Do not build yet.

## What we want, in plain words

Andrew is learning spoken Coimbatore Tamil, alone, to be comfortable and take part in a family room next summer — feeling at home, blending in, joining the conversation. Not minutes, not words learned, not a cleaner repo.

Gossip with family is the most likely use, and the entry, not the destination. The broader frame is family time, in Tamil, in whatever form that takes: gossip is one thing that happens in the room, alongside telling a story, asking a question, doing something together, watching a film or listening to a song together and reacting to it. Music, films, and podcasts are input, not a replacement — they are mostly one-way and do not make you speak back, in real time, to people who know you.

He has learned a lot of words, but the move from a pile of words to fluency is the gap. He does not reliably show up for chat lessons. Short push messages are microdoses that do not replace real learning.

## Where we think we are

Read first, in order: docs/state_of_union_2026-11-09.md, docs/role_charter.md, docs/fable_reply_2026-11-09.md, docs/rio_reply_fable_2026-11-09.md, docs/fable_reply_2_2026-11-09.md, docs/DECISIONS.md, docs/feature_inbox.md.

Then read the code at HEAD, not the prose about the code.

What is working well:
- The record book can be trusted. Every observation is written once, by one piece of code, in one place. Fable could re-count it and trust it.
- The live chat already separates the jobs: Python picks what to work on, names what each turn is for, the model only talks, and Python writes the record at the end.
- Five builds landed Nov 9 (Andrew said go, drain commit 6a4df2b, each with a DECISIONS line):
  1. A silent line is now visible: `line_silence` watches for five pushes and five days with nothing coming back from his phone, and says "the line may be down" instead of reading it as a quiet learner. Replayed against the real log, trips Nov 4. Not exercised live yet.
  2. October's baseline is retired, and the month cut is retired as a gate. The Oct 31 cut never ran and nothing owned it; a late mark would not have been comparable. November opens as "The upstairs room", closing Nov 30.
  3. The phone's word pool has a floor: from one word (`ulla`) to three, topped up from words explicitly taught in the last 21 days. A second supply, not an endless one — with no sessions for three weeks it empties again.
  4. Andrew has a seat in the house: a visitor in the upstairs room, a friend of Priya's husband, and the canon now says how each of the seven people treats him. That reaches the push and live prompts on the next call.
  5. A live scene now has a brief and leaves a beat: Python names one person and what they want from him — gossip, errand, question, story: four briefs on one clock. The gate is that person waiting on him, not "say the target back". The model's one-sentence beat rides to the next scene as `last_time`. No new file, no new lane. One real open was run on the laptop and discarded: Athai turned to him by name with news. Not verified: a full real session with gates, and whether `last_time` is picked up well. The beat is live-only; pushes and episodes do not read it yet.

What is not working, clear and fixable:
- The beat is live-only. Pushes and episodes do not read it yet.
- The studio prompts and the mandates still describe overheard scenes. The first push, live session, and episode under the new canon are the test — and they have not happened yet.
- The push message still does all three jobs in one call: decides whether to reach out, picks the thread, and writes the line. That is the knock-tick seam, not built.
- The laptop session still holds every loop that stopped — slip tests, the month cut — and no slip test has been reported in eleven sessions since Sep 3. Reporting duties have not been moved to Python yet. Not built.
- Ear tests: 3 in seven weeks, versus 123 by reading. You cannot prove "following a new spoken exchange without captions" either way on that supply.
- Reply rates are contaminated by blackouts (reply token expired Oct 28, twelve days of taps died, seven pushes booked as unanswered). Jul 52% -> Oct 30%, audio 14% — mark them unknown until recomputed with both blackout windows removed.
- A turn still takes 39 seconds, cold: 5 queue/setup, 5 checkout, 12 pip install, 13 model call, 4 everything else. Warm process for the bridge is not built. The cost is the runner, not the prose — prose is under one second of the 13.

What is not working, vague — these are questions, not code bugs:
- Do scenes where someone addresses Andrew actually get more replies and longer sessions than overheard scenes? That is the drift test for the seat, and it has not run.
- Does the Room feel like family time, or still like a lesson with gossip wallpaper?
- Does a separated host feel better? The three-pass test (Planner -> Writer -> Host, three separate Claude Code sessions, /clear between) has not run, and only Andrew can run it.
- Is variety, difficulty, and availability actually solved, or just moved?

## What we want you to do

Do the deep exploration and analysis in the codebase, in this order. Do not build yet. Return artifacts, not opinions. Every claim must carry file and line evidence, or be marked UNKNOWN.

### Job A — Verify the five builds. Do not opine, verify. (First, highest priority)

For each of the five builds above, say pass, fail, or unverified, with the log, session, or test that proves it:
1. Line check — does `line_silence` trip correctly, and what would the first real notice look like?
2. Month cut retired — is October closed cleanly, is November open as "The upstairs room", and is anything still gated on the old cut?
3. Thread floor — does the pool actually go from one to three on today's books, and what empties it?
4. Seat in the household — does the canon reach the push and live prompts, and do the studio prompts / mandates still describe overheard scenes?
5. Live brief and beat — does a full real session run with gates, does `last_time` get picked up in the next session, and what breaks when a scene is never answered?
Artifact: a pass/fail table, one row per build, with evidence. Decision it unlocks: whether we move on, or whether one of the five needs a repair before anything else.

### Job B — Turn the vague defects into tests. (Second)

For each vague defect above, write the smallest test that would settle it, with the pass/fail written down BEFORE Andrew runs it:
- Addressed vs overheard scenes (seat drift test).
- Three-pass host test (which pass felt wrong, if any).
- Ear supply (how many ear tests, in what time, would prove or disprove the constitution claim?).
Artifact: three pre-registered tests, each with what to measure, what counts as a pass, and what we would do if it fails. Decision it unlocks: whether the seat, the separation, and the ear are actually working, or whether we are convincing ourselves they are.

### Job C — What is now the binding constraint? (Third, only after A and B)

Re-audit at the new HEAD, with the same evidence discipline — files, lines, counts — and name ONE thing, not five, that is now the bottleneck. Name what is working well that should not be touched, and what is the one thing you would change first, with theory, evidence, and a drift test (what would show it worked, what would show it made things worse).
Artifact: one paragraph, one file/line, one number, one proposal. Decision it unlocks: what the next build is, if any — and whether the next step is even a build, or a test Andrew runs.

## What to look for, and what to prioritise

- Look for seams, not features. A seam is where one piece of code does another piece's job, or where a loop dies because nobody owns reporting it. The live lane is the template: Python picks, Python names the job, the model only talks, Python books at close.
- Look for what is claimed but not measured. Delivered is not heard. Taught is not attended. A push sent is not a push answered. A scene opened is not a scene finished.
- Look for what changed on Nov 9 and what did not. The seat, the brief, and the beat are in the canon and the live lane. The studio prompts, the mandates, the knock tick, and the laptop session's reporting duties did not change. Say so, plainly.
- Prioritise verification over new design. Do not propose a new host, a new lane, a prompt prune, or a model swap. The model was never the bottleneck. The Spark swap, the 3x-silence rule, and "prose as the latency cost" are retracted — do not re-propose them without new evidence.
- Prioritise one clear thing over five vague ones. If you can only answer one job in this session, answer Job A.

## How to return your advice

In plain words first, as if explaining it to someone technically competent who has not followed the jargon: what you noticed, what you decided, what happens next — before any detail. Then, for each proposal, write it as a doc in docs/ with a pointer-only line in docs/feature_inbox.md (one line, doc path only, no restatement — the inbox budget is 1500, and long restatement lines have broken it three times). Andrew will relay rejections back to Rio; do not silently half-comply — if you disagree with a proposal, say why, with evidence, and let Andrew decide.

## Constraints — do not violate these

- Only the goal is sacred. Large deletions / complete refactors: proposals first (theory, evidence, drift test), to talk about with Andrew, never silent changes. Do not build yet.
- The repo stays the only record. One writer per model. Never write learner state directly from a host prompt — always through the Python pen, which validates every write.
- Never re-propose audio via repository_dispatch (a 1-second recording was too big for the dispatch call — dead). Never re-propose text chat as sufficient for the speaking goal. Text is a bridge/stopgap; the destination is an on-demand live spoken tutor.
- Never pretend to be a business, invent business details, or submit fake verification for WhatsApp. Do not retry the Meta claim while the restriction holds.
- If you cannot explain something simply, you do not understand it well enough. If a section is dense with prose or jargon, rewrite it in plain words, with an example, before you file it.
