# Handover to Fable 5.2 — Tamil tutor, 2026-11-09

Andrew has access to Fable 5.2 for a limited time on his subscription. This is a handover, not a build order. Read the repo deep, give advice from inside the codebase, and return proposals — do not build yet.

## How to use this handover

1. Read, in order: `docs/state_of_union_2026-11-09.md` (goal, tensions, layers/subsystems, known bugs), `docs/role_charter.md` (six seats), `docs/feature_inbox.md` (current Inbox, newest first), `docs/DECISIONS.md` (what has already been ruled).
2. Then read the code, not the prose about the code: `protocol/`, `.claude/skills/anna/SKILL.md`, `scripts/suggest_targets.py`, `scripts/threads.py`, `scripts/slips.py`, `scripts/provenance.py`, `scripts/morning_knock.py`, `scripts/push_queue.py`, `scripts/live.py`, `scripts/hear.py`, `scripts/run_studio.py`, `scripts/render_*.py`, `progress/learner.json`, `progress/lexicon.json`, `content/household.md`, `protocol/dialect.md`, `protocol/persona.md`.
3. Answer the questions below, in plain words first, with file and line evidence for every claim. If a claim cannot be evidenced from the code, mark it UNKNOWN.
4. Prioritise: questions 1-3 first, then 4-6, then 7-8 if time remains. Access is limited — a sharp answer to the first three is worth more than a shallow answer to all eight.

## Context in one paragraph

Andrew is learning spoken Coimbatore/Kongu Tamil, alone, to be comfortable and participate in a family room next summer — feeling at home, blending in, joining the conversation. Gossip is the entry and one mode inside the Room, not the destination; the broader frame is family time, in Tamil, in whatever form that takes. He has learned a lot of vocabulary, but the move from a pile of words to fluency is the gap. He does not reliably show up for chat lessons; knocks are microdoses that do not replace substantial learning. The system is "LLM is the writer, Python is the brain" — deterministic, event-sourced state, Python chooses, model writes. The repo is the only record; any host's own memory holds pointers, never facts about Andrew.

## Current direction (do not re-litigate, advise on it)

- Room: a continuing spoken room, with continuity, situational continuity, and a long-running thread on his phone. Nov 5 demo verdict: a task beats a scene; the Room is a partial answer — the gap is phone and walk time.
- Phone thread: whole rotation in one continuous phone thread (Telegram first, Twilio WhatsApp second, Meta third), voice notes both ways, short turns, no long reading; laptop is a second door. Lite version: a Claude Code simulation on his phone (tests feel only).
- Gated rotation: three gated turns, close, push. Gating is a property of a turn, not a lane. The gate must be an information gap, not a quiz.
- Six seats, not one Anna (docs/role_charter.md): (1) Planner/teacher, (2) Writer, (3) Curator/showrunner, (4) Room host, (5) Bookkeeper/judge (Python pen), (6) Coach (Rio, outside the repo).
- Two-week plan Nov 6-20: Week 1 bake-off, Week 2 live primary, host decision Sat Nov 14, review Thu Nov 19.
- Spark via OpenRouter, verified 2026-11-06: meta/muse-spark-1.3-contributor, $0.10/M in, $0.20/M out, 1M context, tool calling + structured outputs. Cloud Run thin host can call Spark, so Spark-in-harness is a clean single-variable test (same host/pen/judge/books, swap model only).
- One code change only, now not at the month cut: a word taught/exposed 3x without cold production goes silent a week and returns only in new gossip.
- October finale decision still open: mark a late finale from M95-M98, or retire the October-baseline claim explicitly. Rio's view: retire.

## Questions to answer, from deep in the codebase

**1. Where are the six seats conflated today?**
For each seat, cite the files/lines where it does another seat's job today. Where does the Host select or plan? Where does the Writer choose what to teach? Where does the Planner perform? Name the three worst conflations, with evidence, and what the minimal separation would be — not a rewrite, a seam.

**2. Room as family time, with modes — what would that actually change in code?**
Gossip, telling a story, asking a question, doing something together, watching a movie or listening to a song together — as modes inside one Room, not separate lanes. What in the code today makes that hard? What can be reused as-is (which lanes, which renderers, which books)? What is the smallest change that turns lanes into modes?

**3. Resident / rehydration — measure it, do not assert it.**
Rio's claim (2026-11-07): residence is justified by rehydration latency, not magic presence; the cost is prose, not books. Verify from the code: what loads per turn, in each lane (knock tick, live session, chat session, Room host)? How many lines of prose, which files, in what order? What could be slimmed or cached, and what would a resident host actually save, in concrete terms? If the claim is wrong, say so, with numbers.

**4. Selection starvation and the level problem — where is the constraint set?**
In suggest_targets.py / threads.py / slips.py, where is the eligibility / bucket logic that starves the channel, and where is the difficulty / density logic that creates the impossible constraint set (mostly-Tamil too fast vs known + ~6 new, contrived vs English with a Tamil word swapped in)? What is the minimal change — one rule, one parameter, one bucket — that would break the starvation loop, and what would it break in return?

**5. Ear vs read — where are they conflated in booking and judging?**
Hearing a sentence and recognising it by ear is a different skill from reading it and typing back. Where in the code (lanes, booking, provenance, hear.py, knock_reply.py) are hearing and reading tested as one, or booked as one? What would it take to book them separately, honestly, without a rewrite?

**6. Spark via OpenRouter — what would swapping the model touch?**
Where is the model called (OpenRouter API in Actions, `claude -p` on the laptop, Gemini-flash ear)? What would calling meta/muse-spark-1.3-contributor touch, file by file? What are the risks — tool calling, structured outputs, prompt density, cost, the contributor-tier data-use note — and what is the smallest safe way to try it (one lane, one turn, with a fallback)?

**7. Fictional stakes — how specific are the people, really?**
In content/household.md, protocol/persona.md, protocol/dialect.md, and the episode / script corpus, how specific, named, and distinct are the household people — their backgrounds, relationships, registers, code-switching? Where does the Room's drama come from today (plot objects: scooter keys, birthdays, phone calls), and where, if anywhere, does it come from social stakes (being understood, teased, included)? What would make the characters more reactive to Andrew, specifically, without inventing a bigger plot?

**8. What would you change first, and what would you NOT touch?**
One thing, first, with theory, evidence, and a drift test (what would show it worked, what would show it made things worse). And one thing you would explicitly not touch, and why — the load-bearing part that looks like bloat but is not.

## Constraints — do not violate these

- Andrew is not the language / teaching / pedagogy / Tamil expert and should not govern palatability, repetition, honest measurement, or words-vs-phrases. He gives goal + felt data (enjoyment, frustration, energy, slots, what he actually said). You lead with expert judgment, including telling him when his named problem or fix is wrong. Only the goal is sacred.
- Large deletions / complete refactors: proposals first (theory, evidence, drift test), to talk about with Andrew, never silent changes. Do not build yet — return proposals.
- Features wait for the month cut (Oct 19 law) unless Andrew overrides. Fixes land same-day.
- The repo stays the only record. One writer per model. Never write learner state directly from a host prompt — always through the Python pen, which validates every write.
- Never re-propose audio via repository_dispatch (a 1-second recording was too big for the dispatch call — dead). Never re-propose text chat as sufficient for the speaking goal. Text is a bridge/stopgap; the destination is an on-demand live spoken tutor.
- Never pretend to be a business, invent business details, or submit fake verification for WhatsApp. Do not retry the Meta claim while the restriction holds. Do not create new portfolios/WABAs to bypass a restriction.
- Rio reads Anna's state, never writes it; Rio never teaches; Rio never writes DECISIONS.md. You are the Claude in the repo — your context is the artifact. Do not answer design questions from inside the accreted compromises without naming that you are doing so.
- Per-session quality was never the binding constraint (KF-1 to KF-14). Do not propose a better prompt as the driver. Research/design from literature is the driver; experiments only count if they form a clear junction for changing / what to build.

## How to return your advice

In the Claude Code session with Andrew, in plain words first: what you noticed, what you decided, what happens next — before any detail. Then, for each proposal, file it as an Inbox line in docs/feature_inbox.md (one line per idea, newest first, reasoning in the commit message, never in the line), or as a proposal doc in docs/ with an Inbox line pointing to it, as was done for docs/role_charter.md and docs/state_of_union_2026-11-09.md. Andrew will relay rejections back to Rio; do not silently half-comply — if you disagree with a proposal, say why, with evidence, and let Andrew decide.
