# Coimbatore Mappillai — From Recognition to Reflex

[![Smoke Test](https://github.com/arosselet/tamil-tutor/actions/workflows/smoke.yml/badge.svg)](https://github.com/arosselet/tamil-tutor/actions/workflows/smoke.yml)
[![Anna](https://github.com/arosselet/tamil-tutor/actions/workflows/anna.yml/badge.svg)](https://github.com/arosselet/tamil-tutor/actions/workflows/anna.yml)
[![Last commit](https://img.shields.io/github/last-commit/arosselet/tamil-tutor)](https://github.com/arosselet/tamil-tutor/commits/main)
[![License: MIT](https://img.shields.io/github/license/arosselet/tamil-tutor)](LICENSE)

<video src="https://github.com/user-attachments/assets/9ee437bb-593b-498a-ba2c-4d340471c5fd" controls width="240" height="240"></video>

A persistent, stateful language coach powered by LLMs. Built for Coimbatore Tamil; the pedagogy and the architecture are portable to any language. The system meters two things, in this order: can you catch what the room is saying, and of the words you recognize, how many can you fire cold.

> **Want one of these for yourself?** This repo is the reference implementation — one
> learner, one language, months of daily state. To bootstrap your *own* tutor (any
> language, any dialect, your starting level), start from
> [**Sollu**](https://github.com/arosselet/language-tutor) (சொல்லு — "say it!"): clone
> it, open your coding agent, and say *"set up my tutor."*

### 🎧 Subscribe

[**Apple Podcasts**](https://podcasts.apple.com/us/podcast/coimbatore-mappillai/id1880268803)

[**RSS Feed Link**](https://raw.githubusercontent.com/arosselet/tamil-tutor/main/rss.xml)


---

## What This Is

Not a chatbot you quiz, and not a flashcard app with an AI skin. **Anna** (Tamil for "elder brother") is a persistent, stateful coach with one charge: *install a reflex in your brain*. He already knows where you are, decides what's next, produces the material, and reaches you first. He drives; he doesn't wait to be summoned. One continuous relationship across every surface (chat, podcast feed, lock screen), all sharing one brain: Python-managed state plus a teacher's-notebook profile.

## If You're Not Here for Tamil

Most of this isn't about Tamil, and the parts that travel are the parts most likely to be
useful. The build separates into six components, which fail differently and are useful on
their own:

- **The motivation engine** — getting a person back tomorrow when nothing makes them
- **The learner model** — what the system believes about you, and how it picks what's next
- **The loop and the rails** — reaching you where you are, and getting your answer back scored
- **The studio** — producing content that ships with no human editor in the loop
- **The language pack** — correcting a model that is fluent in the wrong register
- **The governance kit** — keeping a weekly-changing system compounding instead of churning

Only the language pack is domain-locked: it needs a native speaker and gets rewritten from
scratch. The other five port. Each has a standalone write-up, not yet published.

## The Pedagogy

The theory the whole machine serves:

- **Comprehension is the threshold; production is the engine.** The destination is the room ceasing to be noise — *"come back this time next year and catch most of what is said."* But pure comprehensible input builds a passive vocabulary that then stalls, so the engine is *forced cold output*: an English situation in, the target language out, no multiple choice, no warm-up. Production is the easier half to count, never the destination. Two meters, in that order: the **ear meter** (of the items tested by ear, how many came back) and the **viability floor** (of the words you recognize, the share that fires cold). A meter counts what was *tested*, never what was merely delivered — an untested denominator reports ignorance as failure.
- **The reps aren't the chore; the cold start is.** The hardest problem in self-study isn't doing the work, it's beginning it. So every touch is engineered for momentum: contact time beats completion, one rep beats zero, a partial session counts, and the coach initiates contact instead of waiting. No streaks, no guilt, no makeup work.
- **Engines, not word lists.** High-utility verbs are taught as generative patterns (the tense matrix, the person toggle, the obligation frame) and tested by demanding a *novel* instance: a verb never drilled in that frame. When it comes back cold, that pattern is metered as an **engine online**. The goal is a conjugation engine in the head, not a dictionary.
- **Glue over vocabulary.** Verbs, connectors, pronouns, particles: the high-frequency words that carry most of spoken connectivity. Know the glue and you can slot any English noun into the sentence and be understood. Modern spoken Coimbatore Tamil is heavily Thanglish; pure-Tamil nouns mark you as a scholar, not a local.
- **Register-first, ruthlessly.** The dialect people actually speak: போறேன் ("poren"), never the textbook போகிறேன் ("pogiren"). Literary Tamil is ignored entirely. The measure is operational capacity: navigate an auto ride, survive dinner with the in-laws, land a zinger. Not debate philosophy.
- **Assessment is invisible; correction is a recast.** No quizzes, no debrief forms, no "dative case." When you're off, Anna says it the natural way and moves on, the way a real elder brother mutters the fix across the table, and quietly updates state with what fired cold, what needed a hint, what missed.
- **The only narrative is yours.** Scenes are disposable one-use pegs for a word, then dropped: no serialized saga, no manufactured suspense. The story with real stakes is the learner's own arc, floor climbing toward the reveal. Climax = mastery.

## The Learning Modes

One brain, many surfaces. Every mode below reads and writes the same `progress/` state, so a word strained in chat, soaked in a podcast, and fired on a lock screen moves the same meter.

### The daily session (the primary driver)

A ~10–15 minute forced-output chat. Only three things are true of every one.

**It opens by giving.** The first minutes are pure receiving — the story so far, the trailer Anna left on your phone yesterday, a tangent, a tape. No cold demand until the break has happened, and never "what do you want to do today?" **Then about three honest cold fires**, as moves inside whatever the day is: an English situation in, Tamil back. Instant = cold, hesitation = hinted, miss = recast-and-move. Three honest attempts beat twelve, and ambiguous is never scored as cold — Anna asks rather than take the flattering reading. **Then the close**, which is where the real output is.

Everything else is the day's **shape**, never the same twice running: *Ear Day* (eavesdrop, tapes, machines by ear), *Gauntlet* (6–8 rapid fires, minimal scene — earned by a good week, never the default), *Teach Day*, *Story Day*, *Deep-Dive*, *Table Rehearsal*. Each is offered at the door beside a low-power twin, so a wiped-out day still counts as a session. Anna also plays the table: **mask-work** (he becomes the mother-in-law demanding deference forms, or the cousin bantering at full speed, then steps out and recasts as himself) and the **eavesdrop drill** (two voices gossiping *past* you, then: *enna sonnaanga?* What did you catch?).

At close, the **slip ledger is the session's primary output** — not the wrong word but the pattern under it: the tense reached for, the right word wearing the wrong ending. One is noise; twice is a live pattern, and a live pattern is what commissions the next audio dose. Anna then rewrites the running story, sets the soak-order, names where the meters moved, and hands you tonight's field mission.

### The audio channels (capacity routes; the error chooses)

Four listening channels. What your attention is free to do picks between them *before* content enters the question:

- **Episode** (`run_studio.py`) — sitting down, ready to be taught. The most expensive and most demanding dose there is.
- **Drill track** (`render_drill.py`) — alone in the car, dishes, a solo walk: an English cue, silence while you say the Tamil out loud, then the answer, twice. The silence is the demand, so it needs a free mouth. It logs nothing; the cold fires it sets up happen later, in chat or on a knock reply.
- **Soak loop** (`render_soak.py`) — with family, driving with someone, wiped out: nothing is asked at all. The sounds repeat and iterate past an ear on autopilot.
- **Rotation tape** (`render_rotation.py`) — a flight: forty-five minutes on one press of play, structured recurrence, no screen. The only lane allowed to be long.

Inside what capacity allows, the *error* picks the format: can't hear two words apart → soak; hears them fine but the mouth grabs the wrong one → episode; has it and is just slow → drill. The same mistake twice through one format is that format's answer — change format, never loop harder. ("Longer" is not a channel: a tired ear asking for longer wants more repetition, not more scene.)

The episode is where the **studio** runs — an isolated three-role crew Anna commissions end-to-end: the **Director** turns the soak-order and your progress into a lesson plan, the **Architect** writes a two-voice script (a slice-of-life Intercept plus a Breakdown by two analysts), and the **Producer** applies the Coimbatore dialect pass and TTS-fidelity scrub. `render_audio.py` renders the MP3 and publishes to the RSS feed. What chat just strained is exactly what the next episode soaks: one conversation, two surfaces.

### The knock loop (Anna reaches first)

An hourly CI tick wakes `morning_knock.py`; a cheap deterministic **rails gate** (waking hours 8:00–21:00, ≤5 reaches/day, ≥3h apart) skips most ticks for free. Only when a reach is genuinely possible does Anna decide whether to fire or stay silent, and in which modality: a one-line **text micro-dose**, a ~60–90s **audio memo** in his pinned voice, a **challenge** with stakes, a **volley** (the rapid blitz as a knock — where most of the day's production volume lives), or **grace** after a lapse. Two modalities feed the ear instead of the mouth: an **eavesdrop** tape you answer a drift-question about, and **fielding** — one question fired *at* you in the family voice, the only place a heard question has to become a produced answer. A **trailer** asks for nothing at all and pitches what the next session will pay off. Silence is a first-class choice, and "I'm busy" is a real answer that widens the gap. Presence, never pestering. Every dose is self-contained: the Tamil sits in the notification text, so even an un-tapped push lands a 2-second rep.

**The reply is the rep.** Type phonetic Tamil straight into the notification and `knock_reply.py` judges it against what the knock asked for, moves the production axis, and pushes back Anna's one-line recast. Cold credit is reserved for unaided production: if the knock showed you the Tamil, Python caps the verdict at *hinted*, deterministically. A scored reply can chain one follow-up micro-ask, so a hot moment becomes two or three reps. Anna can also plant a **scheduled push** at a precise time ("ping me at 8:30 to collect the debrief") via `push_queue.py`. Outreach never fakes reps; only a judged reply moves the axis.

### Field missions (live fire)

A covert drop assigned for tonight: one line, deployed at home, unprompted. *"'suvaiya irukku' at dinner, when she isn't expecting it. Debrief tomorrow."* Next contact, Anna collects: did it land, what came back. A line that survives live fire is the strongest cold-fire evidence there is. All other production happens in the safe room at zero stakes; the live moment is always the learner's to pick.

### The feedback loop (heals the tools, not the soul)

`sync_state.py feedback "…"` captures what lands and what grates; a periodic **diagnosis** pass (`protocol/diagnosis.md`) proposes a dial-twist or a prune from *reproduced* patterns, never one-offs. When something's off, it reshapes the tools and the protocol, not just one chat.

## The System Design

The engineering theses, as deliberate as the pedagogy (the full ledger of settled decisions lives in [`docs/DECISIONS.md`](./docs/DECISIONS.md)):

- **LLM is the writer, Python is the brain.** All reasoning that can be deterministic is: state writes go through `sync_state.py` (never hand-edited), the session ticket is computed by `suggest_targets.py`, the knock rails and reply-verdict caps are enforced in code. Python computes the *menu*; the LLM makes the *choice and the meaning*.
- **Two halves, one interface.** Conversation (Anna) and production (the studio) are isolated and meet at exactly one contract, the **soak-order**: the words chat just strained plus a one-line scene seed. Anna hands meaning; the studio owns craft.
- **Continuity is prose memory, not a schema.** The running story is one cumulative debrief Anna rewrites at every close (carry what matters, prune what resolved). A thread-tracking schema with due-ness scoring was built, tried, and rejected: curation at inference beats bookkeeping.
- **Fresh execution, structural variety.** No templating: past scripts are never reused as models. Every session and episode generates fresh from protocol files and live state, and variety is enforced by a deterministic scene-spec gate, not by taste (taste is how the drift crept back).
- **Fix the tool, not the personality.** When the coach seems dumb, forgetful, or pushy, the answer is in the plumbing (logs and timestamps), not in thickening the persona. Anna's soul stays lean; his power grows through his tools.
- **Every addition must earn its place.** Before any new file, field, rule, or script: what does it replace or simplify? The system's worst moments were accumulation; its best moves were separations. Structure is frozen at Anna 1.0: rows of data are free, schema changes wait.

## Repository Map

```
.github/workflows/   → anna.yml, the hourly tick (knock decisions, push-queue drain, reply judging, taps, ratings); smoke.yml, the suite
protocol/            → constitution.md (the philosophy, canonical), Anna (persona + daily_session + diagnosis), commissioning.md + audio_channels.md (which dose, and which channel carries it), studio/ (the isolated production crew: Director, Architect, Producer)
docs/                → Engineer's references: PROTOCOL_MAP.md (architecture), DECISIONS.md (settled decisions), feature_inbox.md (where build-itches park under the structure freeze), comprehension_plan.md (the one-year goal, still open), shortcuts/ (the iOS Shortcuts that drive the phone loop)
.claude/skills/      → The @build playbooks: orient, debug, extend, verify, validate, recalibrate, backport
curriculum/
    ├── word_pool.json → Suggestion list of words to learn someday (Anna picks from it)
    └── trip_deck.json → The trip deck, retired whole 2026-08-18 when its deadline passed; the rows keep the tag as provenance, and sync_state.py seed-deck survives as the writer for any curated set
content/
    ├── lessons/     → Director's planning docs (mission briefs)
    ├── scripts/     → Generated podcast scripts (Markdown)
    ├── captions/    → Per-episode caption copy
    └── articles/    → Write-ups of the portable components
audio/               → Private MP3 output (gitignored scratch)
published_audio/     → Public MP3s served over RSS/CDN; knocks/ holds the daily morning-knock audio
progress/            → lexicon.json (word brain) + learner.json (continuity) + slip_log.json (how the reps keep failing) + profile.md (the calibration dials) + episodes.json + session_log.json + feedback_log.json + knock_log.json (Anna's outreach memory) + chat.md (the readable phone transcript) + push_queue.json
scripts/             → Python tools, layered: language.py holds the entire port surface in one file; state_io + sync_state own every write; publish.py owns the delivery tail; the lanes (morning_knock, knock_reply, run_studio, render_*) sit on top
```

*Storage: old MP3s are pruned **by hand, periodically** — nothing in `scripts/` or the workflows enforces a retention count, and this line used to claim a "last 8 episodes" rule that no code has ever implemented (corrected 2026-08-30). The Markdown scripts and briefs remain as the permanent record. We move forward, not archive.*

## Getting Started

To start your own learning journey, follow the **[BOOTSTRAP.md](./BOOTSTRAP.md)** guide, a one-prompt setup that initializes your own tutor, learner profile, and progress tracking. This repo is a *reference implementation, not a framework*, but the pedagogy generalizes: BOOTSTRAP's **"What Generalizes"** section maps the four layers (pedagogy / machinery / language pack / learner pack), the honest port surface, and how the first session sounds from a blank state.

### Two Modes

One persistent persona runs by default; one explicit hat is for working *on* the system.

| Mode | Role | Use For |
|---------|------|---------|
| **Anna** (default, no keyword) | The coach who drives the learning | Daily sessions, drills, roleplay, commissioning podcasts, tracking progress |
| `@build` | Engineer | Editing protocols, writing scripts, refining the curriculum |

Or jump straight into a daily session with the **`/anna`** skill in Claude Code — or, on any other agent, just read `.claude/skills/anna/SKILL.md` and follow it; it is plain markdown with no host-specific syntax, which is the whole portability contract. For a podcast episode from the current soak-order, run **`python scripts/run_studio.py`**, or just ask Anna and he commissions it end-to-end.

### On Your Laptop (The Factory)

Prompt the agent:

- *"Show my status"* pulls the progress dashboard
- *"I'm ready for the next episode"* generates a new lesson
- *"I'm struggling with past tense verbs"* and the system adapts
- *"This isn't working"* and the system shifts gears, no guilt attached

### On Your Phone

The repo syncs via GitHub, so Anna runs from your phone with full state, no laptop required. Open the **Code** tab in the Claude mobile app (or **[claude.ai/code](https://claude.ai/code)**), select this GitHub repo, and run `/anna`. State commits straight back to GitHub.

---

*Contact time > completion. One rep is better than zero.*
