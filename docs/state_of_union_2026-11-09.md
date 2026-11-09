# State of the union — Tamil tutor, 2026-11-09

Andrew + Rio, design-review thread. Not a request, not a proposal. A snapshot of where the project is, what is tense, and what is still buggy, so the next drain does not have to reconstruct it.

## Goal, as it stands

Comfort and participation in a family room next summer — feeling at home, blending in, joining the conversation. Not minutes, not words learned, not a cleaner repo. Gossip is the most likely use, and the entry, not the destination. The broader frame is family time, in Tamil, in whatever form that takes: gossip is one mode inside the Room, alongside telling a story, asking a question, doing something together, watching a movie or listening to a song together and reacting to it. Music / movies / podcasts are receptive and do not bootstrap speaking the way gossip does — they have no real-time, social pressure to respond — so they are input, not a replacement frame.

## Where we are (2026-11-06 to 2026-11-09)

- Room: a continuing spoken room, patterned, mostly-followable gossip input, brief focus on form inside meaning, pushed short in-role output, spaced pattern retrieval in new gossip. Nov 5 demo verdict (DECISIONS 11-05): a task beats a scene; the Room is a partial answer — the gap is phone and walk time.
- Phone thread: the whole rotation in one continuous phone thread (Telegram first, Twilio WhatsApp second, Meta third), voice notes both ways, short turns, no long reading; laptop is a second door into the same thread and books. Lite version: a Claude Code simulation on his phone (tests feel only).
- Gated rotation: three gated turns, close, push. Gating is a property of a turn, not a lane.
- Six seats, not one Anna (docs/role_charter.md, 2026-11-06): (1) Planner/teacher, (2) Writer, (3) Curator/showrunner, (4) Room host, (5) Bookkeeper/judge (Python pen), (6) Coach (Rio). A seat doing another seat's job is a bug.
- Two-week plan Nov 6-20 (inbox, commit 07d60d9): Week 1 bake-off, Week 2 live primary, host decision Sat Nov 14, review Thu Nov 19 (not Fri Nov 20, lunch and learn).
- Spark via OpenRouter (inbox, 2026-11-06, verified): meta/muse-spark-1.3-contributor, $0.10/M in, $0.20/M out, 1M context, tool calling + structured outputs. The Cloud Run thin host can call Spark, so Spark-in-harness IS a clean single-variable test (same host/pen/judge/books, swap model only); the Muse-host test is a separate host test. Contributor tier: prompts/outputs may be used to improve Meta's products.
- One code change only, now not at the month cut: a word taught/exposed 3x without cold production goes silent a week and returns only in new gossip.

## History — the pattern that keeps repeating

Every burst came from a concrete example in the wild, and every fade came from turning that example into a system. Gemini (possible), a podcast script pasted into Google Translate (mobile, spoken), NotebookLM banter (two voices, more engaging than a monologue), OpenClaw magic (continuous), Opus (governance). Each time: example -> excitement -> generalise into prompts/rules/mandates/lanes -> uniform soup -> fade. The abstraction bursts lasted longer than the format bursts: refactoring the single prompt into distinct roles, demoting audio to a tool and sharing one brain across text and audio, governance / skills / regression tests / ratchets. Durable work is abstraction; motivational work is format; tuning layer by layer chases last month's bottleneck, because each burst solved a different one (possibility, mobility, coherence, engagement, variety, continuity, maintainability).

## Tension 1 — fictional stakes: why care about the scooter?

The Room's drama, as written, is external plot: who has the scooter keys, whose birthday, who said what on the phone. Andrew does not care, and he is right not to. If the drama is plot, Tamil becomes incidental to progress in the journey — a narrated murder mystery with Tamil subtitles. Transplanting onto real people would be worse (real stakes, privacy, hurt feelings), not better. The stake that works in fiction is social, not plot: did Mama understand you, did Deepa laugh, did you get teased and tease back, were you included or left behind for a second? Fiction allows cheap failure in public, in the room, and a return tomorrow. The test for a Room session is not "was the plot interesting?" but "did you feel in a social situation, with people who reacted to you, in Tamil, in a way that felt personal?" If not, the fix is better people — more specific, more distinct, more reactive to you — and smaller stakes, not a bigger plot.

## Tension 2 — surface vs structure: why do hosts need names?

NotebookLM banter was copied as surface (two voices, back-and-forth) without its structure, because the structure was invisible until replication failed. In mid/late April the hosts had to become specific, named, distinct in personality, voice, background, and continuity, or the output collapsed to soup. A name / background / relationship is not decoration: it is a compression of a thousand micro-decisions about language — register, dialect, code-switching, slang, speed, interruptions, jokes. "40% Tamil" is a density knob; it says how much Tamil, not which Tamil or why this person would say it this way. Without a persona the model defaults to the most probable, most generic, most textbook line. Banter IS a relationship, performed in language; remove the relationship and you get two monologues alternating. The rule for the next golden example: ask what would break if you removed a piece of it. Structure is the set of decisions that produced the output, not the characteristics of the output.

## Tension 3 — resident: why, and what it has to fix

Residence is justified by rehydration latency, not by magic presence. A long-running back-and-forth, rehydrated from disk every turn, will be too frustratingly slow in its current form. But rehydration from disk is cheap if the state is small: the books are JSON. What is expensive is rehydrating the prose — hundreds of lines of prompt, mandates, constitution — every turn. Resident alone does not fix it if the resident still reloads 500 lines per turn. The fix is resident PLUS a slim host prompt (~100-200 lines, brief + story state only) PLUS a small, hot story state that stays warm between turns.

## Current bugs, named by layer

- Curriculum — selection starvation / same words again: words not eligible because not yet taught, channel starved, narrower set, no explanation why.
- Pedagogy — level is an impossible constraint set: mostly-Tamil too fast and incomprehensible vs known + ~6 new, predictable/contrived vs English with a Tamil word swapped in.
- Pedagogy — ear vs read conflated: hearing a sentence and recognising it by ear is a different skill from reading it, thinking, and typing back; they are tested as one.
- Continuity — re-entry / cold-call knocks: ephemeral container, no "we left off here", knocks as new scenarios instead of resumptions.
- Palatability / coach — feedback collected, not acted on: the loop from felt data (one like / one dislike) to the next selection is too slow, gated by the month cut; the system does the same thing again after being told what was wrong.
- Pedagogy — prompted to death: density of NEVERs (constitution 24 in 152 lines, daily_session 23 in 87, mandates 69 in 715) — one prompt trying to do curriculum, pedagogy, performance, and bookkeeping at once.
- Pedagogy — gated narrowness risk: a gate that becomes a quiz (one right answer, immediate grade, continuous questions) is the Oct 26 failure; the gate must be an information gap, not an exam.
- Books — delivered != heard, taught != attended; soak delivered Oct 31 as a soak, not the ordered episode, with no heard evidence yet; pre-registered ear-test verdict still pending (fresh verbs, by ear, in new sentences, next day).
- Host — hardest barriers for a Muse host: shadow learner memory (Muse's automatic curation will try to save Tamil facts outside the repo, violating pointers-only) and no inbound webhook (a Cloud Run bridge still has to wake it). Spark via OpenRouter removes the model barrier for Cloud Run; it does not remove the host barriers for Muse.

## Open decisions

- October finale: mark a late finale from M95-M98, or retire the October-baseline claim explicitly. Rio's view: retire — a late mark would not be a clean October baseline. Still unanswered.
- Host decision Sat Nov 14, on the bake-off (Tamil, voice, clean commit through the scripts, unprompted check-in next day).
- Two-week plan review Thu Nov 19.
- Next test: one golden episode — 15 min, multi-voice, gossip-driven, ear-first, with a cliffhanger, built in three passes (Planner -> Writer -> Host). The only question that matters: do you want episode 2 tomorrow?

## What not to do

No new host build before the bake-off, no prompt prune as a project, no transplant as a driver, no new lanes, no harness work except when it unblocks a named lesson. The harness is the school, not a distraction from the teaching.
