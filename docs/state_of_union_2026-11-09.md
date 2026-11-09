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

## Layers / subsystems, and known bugs in each

Audit at HEAD e0ff3c3, 2026-11-05 (141,235 lines on disk, 484 files; Python 37,099 lines in 57 files; prose on disk ~11,000 lines that could load; per-turn loads are ~150-620 lines, the bloat is density, not length). Roughly ~15 files / ~10,000 lines do most of the work — Andrew's 10%-does-80% guess was roughly right. What follows is the load-bearing map, with the bug that lives in each layer.

**1. Observation ledger + fold — the books' writer.**
observations.py, lexicon_view.py, state_io.py. Single writer, atomic writes, CorruptBook. Event-sourced: every observation is one `word`-keyed event (2,229 observations at last count, 2,314 events in observations.json). This holds.
Bugs: the ledger is word-keyed, the goal is a conversation. 427 lexicon rows, 237 (56%) never taught, 282 (66%) never recognition-tested, 117 episode-born rows never taught. Slip closure recorded nothing since 2026-09-03 (15 closes ever, 47 tags; `past-tense` closed 2026-09-03 then recurred 4 times). The only connected-speech instrument, eavesdrop, had 10 tested observations in ~8 months. Delivered != heard is unmeasurable by construction — episodes.json has no heard field.

**2. Selection / ticket — Python chooses, model does not.**
suggest_targets.py (1,265 lines), threads.py (446), slips.py (525), generate_callbacks, ladder. This is the seat that decides what to teach next, by bucket, by recency, by slip.
Bugs: selection starvation — words not eligible because not yet taught, so the teaching channel starves and serves a narrower set, with no explanation why; selection logic required bucket after bucket. Level is an impossible constraint set: mostly-Tamil too fast and incomprehensible vs known + ~6 new, predictable/contrived vs English with a Tamil word swapped in. Episodes birth lexicon rows, so unknown-word density is structural, not a tuning error.

**3. Provenance / judge — attested vs judged.**
provenance.py (319 lines), review_queue.json. Attested forms are free; novel inflections go through a judge (the other model family); unsure holds.
Bugs: the judge seat is the least exercised seat in the system — most content is attested by construction, so the judge rarely bites, and when it does, its verdicts are not surfaced to Andrew in a usable form. The two-pen graft (learner records + Tamil content itself) is not yet in code; it is a design proposal, not a mechanism.

**4. Booking / claim rules — delivered != heard, taught != attended.**
lanes.py (audible etc.), the lane renderers. Booking is what turns a delivery into a claim about Andrew.
Bugs: booking is where the system most often lies to itself, politely. A soak delivered is booked as delivered, not heard. A word taught in a scenario is booked as taught, not attended. The Oct 31 soak (vaangina paradigm) was delivered as a soak, not the ordered episode, with no heard evidence yet — delivered is not heard, and the pre-registered ear-test verdict is still pending.

**5. Outreach rails + policy — the knock tick.**
rails.py (180 lines, but rails as a system are distributed across morning_knock.py, push_queue.py, reflect/policy.py, publish.py), morning_knock.py (796), push_queue.py (433). Cap 3/day, gap, quiet hours at the single delivery chokepoint, weekly policy learning on Andrew's approval.
Bugs: reach is decaying — chat sessions Aug 20 -> Sep 10 -> Oct 5/month; knock reply rate Jul 52% -> Oct 30%; audio knock replies 14%. The tick wakes, responds, and dies; every turn is rehydrated from zero, so there is no "we left off here". HA knock PAT `ha-anna-knock` expired ~Oct 29, 2026; renewal status unknown. The 24-hour WhatsApp window / template problem is unsolved: free-form sends only within 24h of Andrew's last message, otherwise pre-approved template only.

**6. Household canon + dialect + persona — the world the Room lives in.**
content/household.md, protocol/dialect.md (83 lines), persona.md (74), user.md (16), protocol/constitution.md (152). This is the smallest prose in the system, and the most load-bearing.
Bugs: the canon is real-calendar, festivals, Coimbatore news, his projects, but the household people are fictionalised / renamed, and the situations are real — that split is a design decision (Oct 19, built), not a bug, but it is where the fictional-stakes tension lives (see Tension 1). Density is an OUTPUT, never a target, but a density-band filing is still open, and "soak" means three things in the same channel table.

**7. Studio pipeline — the writer.**
run_studio.py (897), writer.py (701), render_audio.py (938), rebuild_rss.py (857). Three print-only writer passes, deterministic lint, TTS. Studio and conversation meet at exactly one interface, the soak-order, per docs/PROTOCOL_MAP.md.
Bugs: seven render_* lanes, ~3,900 lines total, with low exact-line duplication (only 21 lines >50 chars repeated >3x) but high conceptual duplication — each format re-implements cue/silence/answer, booking, judging, commit/notify with its own prompt. That is why a format change feels like a rewrite, and why the "prompted to death" density lives here: constitution 24 NEVERs in 152 lines, daily_session 23 in 87, persona 16 in 74, mandates 69 NEVERs in 715 lines.

**8. Channels / lanes — where Andrew actually meets Anna.**
Knock (push), live (`scripts/live.py`, 351 lines, walk-paced gated rotation), chat session (Claude Code, light start ~150 lines, deep session ~480 lines + ticket), episode / soak / drill, eavesdrop, message lane (`hear.py`, 138 lines, built and wired, "THERE IS NOTHING TO GRADE").
Bugs: the lanes are separate, not modes inside one thread — formats exist in separate lanes, so variety is locked behind gates Andrew does not open. Message lane works as live conversation core, not a whole live tutor: context thin (8 turns / 24h), stateless per turn, nothing teaches in it by design. Live Anna must preserve arbitrary messages, open conversation as default, teaching modes as on-demand activities inside it, never a lock-in — that was Andrew's Oct 25 correction, and it is still not fully honoured in the lanes.

**9. Surfaces / bridge — the phone.**
bridge/whatsapp/main.py (120 lines), Cloud Run bridge (deployed, passes handshake, refuses wrong tokens; three repo secrets set). Meta WhatsApp: dev-tools error 2494067 "Business WABA limit reached" cleared by deleting the empty Test WhatsApp Account, then error 2655121 "Account restricted" — Meta direct is a dead end for now, do not create new portfolios/WABAs to bypass while the restriction/appeal is open, do not add a payment method for the WhatsApp claim. Twilio Sandbox remains the parallel bypass, unchosen since Oct 29. Telegram is the viable phone surface (no Meta claim, bot token + webhook to the existing bridge).
Bugs: no inbound webhook for a Muse host — Telegram/WhatsApp messages need a Cloud Run bridge to receive and wake Muse, so a Muse-hosted Anna is still tick-based / polling / dispatch, not live. Audio via repository_dispatch is dead (a 1-second recording was too big for the dispatch call) — never re-propose it.

**10. Model layer — the synthesis engine.**
Claude Code on the laptop (`claude -p`), OpenRouter API in Actions, Gemini-flash ear (blind, Tanglish transcript). Spark via OpenRouter now available (see above): meta/muse-spark-1.3-contributor.
Bugs: model quality was never the bottleneck — per-session quality was never the binding constraint (KF-1 to KF-14, fourteen named incidents in a year, not one about what the model wrote; every one is state, plumbing, continuity, or the seam). The model will always produce a plausible lesson, even when it does not know Andrew's level, so output quality cannot tell you whether the pedagogy worked. Lossy compaction of a Muse chat context is a real risk if Anna is hosted on Muse: mitigation is re-reading repo state every turn, never trusting chat memory — discipline, not a code gate; the code gate bites only at commit time, via the scripts.

**11. Smoke / governance — the fossil.**
Smoke suite 17,713 lines, 9 files (state.py 5,869; knock.py 3,696; render.py 2,544; ratchets.py 1,827; compose.py 1,461; publish.py 1,329) — almost half of all Python. Governance: DECISIONS.md, failure archive (KF-1 to KF-14), budgets, ledgers, the seam.
Bugs: the smoke suite is a governance fossil — it fossilises rules that may no longer hold, and it costs nothing in a model's context window (it does not load per turn) but a lot in maintainability. Andrew's correction, Nov 5: he does not care about the cost of unit tests, and mostly does not care about Python lines — what he is measuring for bloat is lines of prose. The prose that does load is dense, not long (see layer 7).

**12. Coach — Rio, outside the repo.**
This thread, twice-weekly check (Tue/Fri ~8:15 PM Toronto), silent unless a pattern reproduces with evidence, at most one finding per run. Reads Anna's state, never writes it; never teaches; never writes DECISIONS.md.
Bugs (in the coach, honestly): Rio keeps reaching for the experiment lever, and for the host/audit lever, when Andrew's momentum has always come from restructures and new discoveries, not from tests. The Oct 31 pass was over-prompted and felt lost; the Nov 2 correction stands — experiments only count if they form a clear junction for changing / what to build.

## Open decisions

- October finale: mark a late finale from M95-M98, or retire the October-baseline claim explicitly. Rio's view: retire — a late mark would not be a clean October baseline. Still unanswered.
- Host decision Sat Nov 14, on the bake-off (Tamil, voice, clean commit through the scripts, unprompted check-in next day).
- Two-week plan review Thu Nov 19.
- Next test: one golden episode — 15 min, multi-voice, gossip-driven, ear-first, with a cliffhanger, built in three passes (Planner -> Writer -> Host). The only question that matters: do you want episode 2 tomorrow?

## What not to do

No new host build before the bake-off, no prompt prune as a project, no transplant as a driver, no new lanes, no harness work except when it unblocks a named lesson. The harness is the school, not a distraction from the teaching.
