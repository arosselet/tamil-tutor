# From Gem to Anna

*A year of building my own Tamil tutor: what I dreamed, what I built, and what it taught me about engineering with LLMs. Andrew Rosselet, July 2026.*

---

My wife is a native Tamil speaker from Coimbatore. The dream was always specific: to sit at a family gathering and answer back in her family's own Kongu Tamil. Not as a party trick. It's about connection and respect: meeting her people in their language. Everything below serves that.

This is the story of the machine I built to get there, including the parts where it fell apart.

```
Commits per month, 2026:

Feb  ██████████████ 53
Mar  ██████████████ 53
Apr  ███████████ 42
May  ██ 9
Jun  ██████████████████ 69
Jul  ████████████████████████████████████████████████████████████████████████ 294
```

That histogram is the whole plot. Keep it in view.

## Chapter 1: The Gem

It started as a protocol document pasted into a Gemini gem. Four lesson phases, a `[Tamil Lesson]` trigger, and eight weeks of curriculum written ahead of time in a Google Doc. To run a lesson, I picked a week and loaded it into the machine, then copied the generated scripts into a TTS tool to listen. I was the author, the renderer, the delivery pipeline, and the progress tracker.

Two things from that document survived everything since. Audio as the reinforcement medium is one. The other is a paragraph I called the **Enjoyment Clause**: *"This rule is paramount. If any part of a lesson feels tedious, frustrating, or ineffective, you must use the override command: 'This isn't working.'"* That paragraph outlasted every curriculum decision written around it.

The failure mode of the gem era was one every engineer of that period will recognize: the monolith prompt had no modularity. Every edit degraded something somewhere else, because the model *was* the architecture. The frontier models I was using simply couldn't hold it all coherently in one place. The lesson: a system's invariants have to live somewhere the model can't smear them.

## Chapter 2: NotebookLM

Then I discovered NotebookLM and really played with it. The insight wasn't the technology. It was the format: a host and a guest bantering are far more palatable to listen to than a grammar teacher delivering a monologue. I wanted that, but in Thanglish, the woven register Coimbatore actually speaks, where English carries the logistics and Tamil carries the payload.

NotebookLM couldn't produce it. So I built it myself. That piece of inspiration carried me for months, and everything audio in the current system descends from it: the two unnamed hosts, the analyst pair, the three-pass studio.

## Chapter 3: The coverage era (February)

The repo's first commit is February 17: *"Madras Mappillai v2"* (v1 never made it into git). Within eight days, three formative events.

- **The dialect awakening.** Feb 20: rebrand to *Coimbatore* Mappillai, then "purge all remaining Chennai/Madras references project-wide." My target wasn't Tamil. It was her family's Tamil.
- **The two hats.** Feb 23: "make it clear whether we are in engineering mode vs tutor mode." That one-line commit is the great-grandparent of today's split between the tutor persona and build mode.
- **A death and a birth on the same day.** Feb 25: I purged my "mobile wall hack," a contraption where phone-Gemini generated a JSON blob that I shared to a webhook, parked as a text entity in Home Assistant, and hoped my laptop would eventually pick up and sync. Too brittle, too heavy. But it was the right dream (my buddy needs state to teach me effectively) with the wrong transport. Hours later: "implement public podcast RSS feed via GitHub Pages." A private tunnel traded for a public standard. That feed is still the only feed.

The philosophy was still coverage, though: "expand from 8 to 20 levels, 173 → 383 unique lemmas." I was measuring progress in lemma counts. The next four months changed my mind.

## Chapter 4: The soup (March and April)

By late March the inspiration had curdled into what I came to call uniform soup. Words weren't moving. Lessons were contriving scenarios to re-teach the same few words. And I thrashed on the immersion gradient, trying to keep episodes challenging enough to be interesting and comprehensible enough to follow.

The commits confess it in real time. March 22: *"simplify protocols to resolve narrative uniformity and over-tuning."* Then the oscillation: March 25, loosen constraints ("accelerate vocab throughput"). April 4, tighten them ("deeper acquisition"). April 10, flip the entire philosophy (production-first to absorption-first). April 1 was the worst week: a format-rotation system, micro-debriefs, and a cumulative NOT-list, three accumulation mechanisms in seven days, every one a symptom cap bolted on without a diagnosis. I fought drift by adding rules. The rules became part of the soup.

April 10 also holds a cautionary artifact: eight consecutive commits fighting a podcast app's cache. GUID refreshes, v2 renames, a "total reset of playlist feed." A full day against cache invalidation. Months later the real fix turned out to be `git rm`; the playlist shouldn't have existed.

One April decision was a keeper, and it saved everything after: April 15, *"separate concerns into config files."* I refactored the prompts the way I'd refactor bad code. One role per file, each comprehensible in isolation: Director, Architect, Producer; dialect quarantined from narrative, cast quarantined from persona. From then on, a crisis meant editing one file instead of rewriting a monolith.

## Chapter 5: Nine commits (May)

May is nine commits, most of them automated playlist publishes. I faded.

The lesson the project eventually wrote into its own law: *"a fade is palatability data, not a discipline failure."* I hadn't stopped wanting Tamil. The episodes had become grating: too dense, too contrived, the same scenario re-run. My silence was the most information-dense signal the system ever received, and most of what got built in June was built in answer to it.

## Chapter 6: Anna (June)

The revival inverted the core relationship. Instead of me summoning a tutor and feeding it a plan, I built **Anna** (Tamil for "elder brother"), a persistent persona who drives. He knows where I am, decides what's next, opens every session by handing me a pre-loaded rep, and never asks "what do you want to do today?"

June's decisions read like a purge of my own earlier instincts. The serialized story arc: rejected (no novelist is behind it; the one true narrative is my own progress). Chasing listen counts: rejected (every dose is self-contained). Continuity as a tracking schema: rejected, in favor of one running prose debrief the persona rewrites himself.

And at the end of June, the piece the wall hack had been groping toward: an agentic outreach loop. A GitHub Actions cron wakes Anna a few times a day. He decides whether to knock, what to send, and in which modality. My typed Tamil replies get judged and scored into per-word state, with git as the synchronization bus between phone, cloud, and laptop. The wall hack, grown up.

## Chapter 7: The institution (July)

July is 294 commits, and roughly half were authored by the machine itself: knocks fired, replies judged, episodes registered, queues drained. The system runs itself between my sessions.

But the July change that matters most isn't a feature. The repo became self-governing:

- **A decision log** (`docs/DECISIONS.md`): every settled question, every rejected approach with its why, so nothing gets re-litigated from scratch.
- **A known-failures archive**: ten named incidents, each traced from symptom to root cause, each permanently guarded by a regression case in a sandboxed smoke test that runs on every push.
- **Word budgets**: the protocol's prose surfaces have CI-enforced word caps, and growth past budget is a red build. Adding a rule now costs something, which is the only defense against the April failure mode that has actually held.
- **A feedback ledger**: my own frustrations, logged verbatim the moment I say them, treated as the primary diagnostic. The Enjoyment Clause, finally with machinery behind it.
- **Self-healing production**: a watchdog that notices undone work and runs the pipeline without waiting for human hands.

## What a year taught me

1. **LLM is the writer; Python is the brain.** Push every invariant into deterministic code and keep the model's surface small. The model narrates state; it never owns it.
2. **Separation of concerns applies to prompts.** The April refactor did more for reliability than any model upgrade.
3. **The repo is the memory.** Decisions, failures, budgets, and state live in version control, model-agnostic and portable. I've run this system under three different vendors' agents without it changing personality.
4. **Evidence before mechanism.** Every fix proposed before reading the logs was a symptom cap. The best fixes were usually deletions, and only reading the plumbing finds those.
5. **Meters can lie, and unwinnable meters corrode.** I've rebuilt my headline metric three times. The honest one is always smaller than the ambitious one.
6. **Formats drift like content.** A format that converts is a bet that paid off, not a mandate to repeat it. Uniformity is the thermodynamics of generative systems. You don't cure it; you build an immune system for it.
7. **A fade is data.** When a solo project goes quiet, the silence is telling you something about palatability. Read it before you build accountability machinery.

Have I tamed it, or just given the problems new names? Honest answer: I tamed what the code enforces, and I renamed what prose merely requests. The history is unambiguous that prose-only fixes recur until they grow a mechanism and a test. What I actually built is the conveyor between those two states: felt signal → ledger → evidence → mechanism → regression case. A year ago, a failure meant weeks of thrash and a rewrite. Now it means a ledger entry, a diagnosis, and usually a one-line deletion with a test behind it.

That's not the absence of the beast. That's a working leash.

---

*The system is open: [tamil-tutor](https://github.com/arosselet/tamil-tutor) is the living reference implementation, and [language-tutor](https://github.com/arosselet/language-tutor) is the generalized template if you want to build your own.*

*In three weeks I'll be at that family table in Coimbatore. The machine will keep changing as real lessons expose what's off. The reps are mine.*
