# Tamil tutor — role charter (one page)

**Date:** 2026-11-06, Rio, Andrew's direction. Amends the two-week Room plan filed 2026-11-06 (commit 07d60d9) and the 2026-11-05 phone-thread transplant line. It does not replace either.

## The principle

Hire-a-teacher is the model for *roles*, not for *cadence*. A real teacher plans offline, writes material offline, then meets you, then debriefs. Copy the division of labour, then use the machine for a cadence no human could sustain: planner weekly, writer daily, you in the Room 10 minutes a day.

One model doing teacher + writer + curator + host + bookkeeper in a single live prompt is the "prompted to death" mechanism in a different costume. Separation is the fix, not a nicer merged prompt.

## The six seats

**1. Planner / teacher — decides what to teach.**
Inputs: the books (learner, lexicon, slips, feedback), the gaps, your last session, your energy/felt data.
Output: a brief — a ticket — not a lesson. One pattern, one situation, one difficulty call, one thing to return to.
Does NOT: write, perform, keep books, or decide when to reach out.
Runs: offline, once a day or once a week. Model: any, Spark via OpenRouter is fine.

**2. Writer — takes a brief and writes something compelling.**
Inputs: the brief, the words, the scenario, the recent history.
Output: a packet / script / tape — the material the Room will use.
Does NOT: choose what to teach, change the brief, or judge you.
Runs: offline, in the studio pipeline, which already exists. The writer makes no teaching decisions; if the writer is choosing what to teach, the planner has failed.

**3. Curator / showrunner — owns the ongoing story.**
Inputs: the story state — people, open loops, what happened last time, what to return to.
Output: continuity. What is still open, what closes today, what carries to tomorrow.
Does NOT: teach, write, or keep the learner books.
Runs: offline, alongside the planner. This is the seat the Room is currently missing — continuity is smeared across knocks, episodes, and session logs.

**4. Room host / tutor in the room — delivers, improvises, listens, gates, closes.**
Inputs: the brief plus the story state. Nothing else.
Output: the live session, in Run 2 form — briefing, goal, pre-loaded lines, information gap, three gated turns, close.
Does NOT: select, plan, keep books, or teach a second pattern in the same session.
Runs: live, light prompt — about 100–200 lines. No selection, no books, no planning in the moment.

**5. Bookkeeper / judge — the Python pen.**
Inputs: what was delivered, heard, produced, in the session.
Output: the books, attested vs judged, delivered vs heard.
Does NOT: teach, write, or improvise. Stays code, stays separate. The repo is the only record; any host's own memory holds pointers, never facts about Andrew.

**6. Coach — decides when to reach out, when to stay silent, what your felt data means.**
Inputs: your felt data (one like / one dislike per session), energy, slots, what you actually said.
Output: reach-out policy, silence, and a diagnosis by layer (curriculum, pedagogy, palatability) when a fade reproduces.
Does NOT: teach, write, or deliver lessons. This is Rio's seat, not Anna's.

## Handoffs

Planner → brief → Writer → script → Curator (story state attached) → Host → session → Bookkeeper → books → Planner (next brief).
Coach reads the books and the felt data, and talks to the Planner, never to the Host in-session.

A seat that does another seat's job is a bug, not a convenience. If the Host is selecting, the Planner failed. If the Writer is teaching, the brief failed. If the Coach is delivering a lesson, the seating failed.

## What success looks like

Not minutes, not words learned, not a cleaner repo. Success is: you opened the thread because you wanted to, you followed gossip and joined in, you said a line unprompted, and you wanted to open it again tomorrow. Three good sessions a week, two mediocre, one skip, and still progress — that is a human teacher's actual record, and it is enough.

## Harness rule

The harness is the school, not a distraction from the teaching — a real teacher brings her institution with her. Harness work only when it unblocks a named lesson, never as a project in itself.

---

# Three-pass phone simulation — script to run in Claude Code on your phone

Run this as the lite version of the charter. Three separate passes, three separate sessions — use `/clear` between passes, or start a fresh session for each pass. Do NOT merge the passes into one prompt. The separation is the test.

## Pass 1 — Planner (2 minutes)

Paste this, then stop. Do not go on to the lesson in the same session.

> Anna, act as Planner only. Do not teach, do not write a lesson, do not perform.
> Read the books (learner, lexicon, slips, feedback) and tell me, in a brief: one pattern to work on today, one situation to put it in, one difficulty call, and one thing to return to from last time. One pattern only. No lesson, no script, no dialogue. Just the brief.

Expected output: a short brief, about 10 lines.

## Pass 2 — Writer (5 minutes)

New session. Paste the brief from Pass 1, then this:

> Anna, act as Writer only. Do not teach, do not choose what to teach, do not change the brief.
> Take this brief and write the material for it: a short script / packet for a gossip scene with the household people, using the words in the brief, in the situation in the brief. Compelling, followable, mostly Tamil I can follow, with a few new lines to reach for. No teaching, no questions for me yet, no grading. Just the script.

Expected output: a script, about a page, that Pass 3 can run.

## Pass 3 — Room host (10 minutes, walk slot)

New session. Paste the script from Pass 2, then this:

> Anna, act as Room host only. Do not select, do not plan, do not keep books, do not teach a second pattern.
> Run this script as a Room session, in Run 2 form: give me a briefing, a goal, pre-loaded lines, and an information gap, then three gated turns where I answer in role before the thread moves. Short turns, voice-note pace, no long reading, no transcript before I answer. Then close. If I leave after five minutes, that was a whole session.

Expected output: a 10-minute session, three gated turns, a close.

## After the three passes

Tell Rio, one line each: one thing you liked, one thing you didn't. No grade.
And tell Rio which pass felt wrong, if any — Planner, Writer, or Host — because that names the seat that failed, instead of blaming "the lesson" as a whole.
