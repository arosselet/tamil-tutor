# From Gem to Anna

*A year of building my own Tamil tutor — what I dreamed, what I built, what it taught me about engineering with LLMs. — Andrew Rosselet, July 2026*

---

My wife is a native Tamil speaker from Coimbatore. The dream, from the beginning, was specific: to one day answer back in clean Kongu Tamil at a family gathering — the ginger fella nobody expected. Everything below exists in service of that jaw-drop.

This is the story of the machine I built to get there, told honestly — including the parts where it fell apart.

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

## Chapter 1 — The Gem

It started as a protocol document pasted into a Gemini gem: a four-phase lesson structure, a `[Tamil Lesson]` trigger, and eight weeks of curriculum I wrote ahead of time in a Google Doc. Every session, I'd pick a week, load it into the machine, and copy the generated scripts into a TTS tool by hand. I was the curriculum author, the renderer, the delivery pipeline, and the progress tracker.

Two things from that document survived everything since. The first was audio as the reinforcement medium. The second was a paragraph I called the **Enjoyment Clause**: *"This rule is paramount. If any part of a lesson feels tedious, frustrating, or ineffective, you must use the override command: 'This isn't working.'"* I knew before lesson one what would actually kill this project, and it wasn't grammar.

The failure mode of the gem era was one every engineer of that period will recognize: the monolith prompt had no modularity. Every edit degraded something somewhere else, because the model *was* the architecture. The frontier models I was using simply couldn't hold it all coherently in one place. Lesson extracted: **a system's invariants have to live somewhere the model can't smear them.**

## Chapter 2 — The NotebookLM hinge

Then I discovered NotebookLM, and really played with it. The two-voice deep-dive format was *exactly* the reinforcement medium I'd been hand-cranking through a TTS box. I genuinely tried to make it produce Thanglish — the woven English-carries-logistics, Tamil-carries-payload register that Coimbatore actually speaks.

It couldn't.

So I built it myself. That decision is the hinge of the whole year. Everything that exists now — the two hosts, the analyst pair, the three-pass studio — is my fork of a product that refused my dialect.

## Chapter 3 — The coverage engineer (February)

The repo's first commit is February 17: *"Madras Mappillai v2"* (v1 never made it into git). Within eight days, three formative events:

- **The dialect awakening.** Feb 20: rebrand to *Coimbatore* Mappillai, then "purge all remaining Chennai/Madras references project-wide." I realized my target wasn't Tamil — it was *her family's* Tamil.
- **The two hats.** Feb 23: "make it clear whether we are in engineering mode vs tutor mode." That one-line commit is the great-grandparent of today's tutor-persona / build-mode split.
- **A death and a birth on the same day.** Feb 25: I purged my "mobile wall hack" — a Rube Goldberg sync where phone-Gemini generated a JSON blob I'd share to a webhook, park in Home Assistant, and hope my laptop picked up. Too brittle, too heavy — but it was the right dream (*my buddy needs state to teach me effectively*) with the wrong transport. Hours later: "implement public podcast RSS feed via GitHub Pages." Traded a private tunnel for a public standard. That feed is still the only feed.

But my philosophy was still *coverage*: "expand from 8 to 20 levels, 173 → 383 unique lemmas." February-me measured progress in lemma counts. The next four months beat that out of me.

## Chapter 4 — The soup (March–April)

By late March the inspiration had curdled into what I came to call **uniform soup**: words weren't moving, lessons were contriving scenarios to re-teach the same few words, and I was thrashing on the "immersion gradient" — trying to make episodes simultaneously challenging enough to be interesting and comprehensible enough to follow.

The commits confess it in real time. March 22: *"simplify protocols to resolve narrative uniformity and over-tuning."* Then the oscillation, textbook: March 25 **loosen** constraints → April 4 **tighten** them → April 10 **flip the entire philosophy** (production-first to absorption-first). April 1, the worst week: I installed a format-rotation system, micro-debriefs, and a cumulative NOT-list — three accumulation mechanisms in seven days, every one a symptom cap bolted on without a diagnosis. I fought drift by adding rules. The rules became part of the soup.

April 10 also holds my favorite cautionary artifact: **eight consecutive commits fighting a podcast app's cache** — GUID refreshes, v2 renames, a "total reset of playlist feed." A full day of my life against cache invalidation. (Months later the fix turned out to be `git rm` — the playlist shouldn't have existed.)

One April decision was a keeper, though, and it's the one that saved everything after: April 15, *"separate concerns into config files."* I refactored the prompts the way I'd refactor bad code — SOLID, one role per file, each comprehensible in isolation. Director, Architect, Producer; dialect quarantined from narrative, cast quarantined from persona. From then on, a crisis meant editing one file, not rewriting a monolith.

## Chapter 5 — Nine commits (May)

May is nine commits. Mostly automated playlist publishes. The repo equivalent of a flat EKG.

I faded. And the most important thing the project ever learned is written into its law *about* that fade: **"a fade is palatability data, not a discipline failure."** I hadn't stopped wanting to learn Tamil. The episodes had become grating — too dense, too contrived, same scenario re-run — and my silence was the highest-bandwidth signal the system ever received. Everything built since June is, one way or another, the answer to May.

## Chapter 6 — Anna (June)

The revival inverted the core relationship. Instead of me summoning a tutor and feeding it a plan, I built **Anna** — a persistent persona (Tamil for "elder brother") who *drives*. He knows where I am, decides what's next, opens every session by handing me a pre-loaded rep, and never asks "what do you want to do today?"

June's decisions read like a purge of my own earlier instincts: the serialized story arc — rejected ("no novelist is behind it; the one true narrative is my own arc"). Chasing listen-counts — rejected ("every dose is self-contained"). Continuity as a tracking schema — rejected in favor of one running prose debrief the persona rewrites himself. And at the end of June, the piece the wall hack had been groping toward for months: an **agentic outreach loop**. A GitHub Actions cron wakes Anna a few times a day; *he* decides whether to knock, what to send, which modality; my typed Tamil replies get judged by an LLM judge and scored into per-word state — with git as the synchronization bus between phone, cloud, and laptop. The wall hack, grown up.

## Chapter 7 — The institution (July)

July is 294 commits, and roughly **half were authored by the machine itself** — knocks fired, replies judged, episodes registered, queues drained. The system now runs itself between my sessions.

But the July change that matters most isn't a feature. The repo became *self-governing*:

- **A decision log** (`docs/DECISIONS.md`) — every settled question, every rejected approach with its why, so nothing gets re-litigated from scratch.
- **A known-failures archive** — ten named incidents (KF-1 through KF-10), each traced from symptom to root cause, each permanently guarded by a regression case in a sandboxed smoke test that runs on every push.
- **Word budgets** — the protocol's prose surfaces have CI-enforced word caps. Growth past budget is a red build. Adding a rule now *costs something*, which is the only reliable defense against the April failure mode.
- **A feedback ledger** — my own frustrations, logged verbatim the moment I say them, treated as the primary diagnostic. The Enjoyment Clause, finally with machinery behind it.
- **Self-healing production** — a watchdog that notices undone work and runs the pipeline without waiting for human hands.

## What a year taught me

1. **LLM is the writer; Python is the brain.** Push every invariant into deterministic code; keep the model's surface small. The model narrates state — it never owns it.
2. **Separation of concerns applies to prompts.** The April refactor did more for reliability than any model upgrade.
3. **The repo is the memory.** Decisions, failures, budgets, state — versioned, model-agnostic, portable. I've run this system under three different vendors' agents without it changing personality.
4. **Evidence before mechanism.** Every fix proposed before reading the logs was a symptom cap. The best fixes were usually *deletions*, and only reading the plumbing finds those.
5. **Meters can lie, and unwinnable meters corrode.** I've rebuilt my headline metric three times. The honest one is always smaller than the ambitious one.
6. **Formats drift like content.** A format that converts is a bet that paid off, not a mandate to repeat it. Uniformity is the thermodynamics of generative systems — you don't cure it, you build an immune system for it.
7. **A fade is data.** When a solo project goes quiet, the silence is telling you something about palatability. Read it before you build accountability machinery.

Have I tamed it, or just given the problems new names? Honest answer: I tamed what the code enforces, and I renamed what prose merely requests — the history is unambiguous that prose-only fixes recur until they grow a mechanism and a test. What I actually built is the conveyor between those states: felt signal → ledger → evidence → mechanism → regression case. A year ago, a failure meant weeks of thrash and a rewrite. Now it means a ledger entry, a diagnosis, and usually a one-line deletion with a test behind it.

That's not the absence of the beast. That's a working leash.

---

*The system itself is open: [tamil-tutor](https://github.com/arosselet/tamil-tutor) is the living reference implementation, and [language-tutor](https://github.com/arosselet/language-tutor) is the generalized template if you want to build your own — any language, any dialect some frontier product refuses to speak.*

*In three weeks I'll be at that family table in Coimbatore. The machine's part is done for now; the reps are mine.*
