# Coimbatore Mappillai — From Recognition to Reflex

<video src="https://github.com/user-attachments/assets/9ee437bb-593b-498a-ba2c-4d340471c5fd" controls width="240" height="240"></video>

**A language tutor built for exactly one learner. It turned into six separable pieces of engineering, and only one of them is about teaching.**

Built for Coimbatore Tamil; the pedagogy and most of the machinery port to any language. The system tracks one number: of everything you've heard and recognized, how much can you actually fire cold.

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

A persistent, stateful coach — **Anna** (Tamil for "elder brother") — who already knows where you are, decides what's next, produces the material, and reaches you first. He drives; he doesn't wait to be summoned. One continuous relationship across every surface (chat, podcast feed, lock screen), all sharing one brain.

Underneath that relationship are six components. They fail differently, are debugged differently, and are useful on their own:

| | Component | What it does |
|---|---|---|
| 1 | [The motivation engine](#the-motivation-engine) | Gets you back tomorrow when nothing makes you |
| 2 | [The learner model](#the-learner-model) | Knows what you can hear versus what you can say, and picks what's next |
| 3 | [The loop and the rails](#the-loop-and-the-rails) | Reaches you where you are, and gets your answer back scored |
| 4 | [The studio](#the-studio) | Produces hours of audio with no human editor in the loop |
| 5 | [The language pack](#the-language-pack) | Corrects a model that is fluent in the wrong register |
| 6 | [The governance kit](#the-governance-kit) | Keeps a weekly-changing system compounding instead of churning |

One rule runs through all six: **the LLM is the writer, Python is the brain.** Every reasoning step that can be deterministic is — state writes go through `sync_state.py` (never hand-edited), the session ticket is computed by `suggest_targets.py`, the outreach rails and reply-verdict caps are enforced in code. Python computes the *menu*; the LLM makes the *choice and the meaning*.

**The evidence for the cut:** fourteen failures have been root-caused and pinned with regression tests over the first year ([the archive](./.claude/skills/debug/SKILL.md)). Essentially every one sat on a *seam between two components*, never inside one. That is why the interfaces are specified rather than assumed.

## If You're Not Here for Tamil

Most of this is not about Tamil, and the parts that travel are the parts most likely to be useful:

- **The learner model** and **the governance kit** contain nothing language-specific at all.
- **The studio** is a general pattern for any pipeline where an agent's output ships without review.
- **The loop and the rails** is the proactive-agent problem: when to reach out, on which channel, and how the reply finds its way home.
- **The motivation engine** applies to any long-horizon solo pursuit — an instrument, a training plan, a manuscript — where nothing external requires you to continue.
- **The language pack** is the one that does not travel. It needs a native speaker and gets rewritten from scratch.

[`BOOTSTRAP.md`](./BOOTSTRAP.md) → *What Generalizes* maps the four porting layers and the honest port surface — including the domain-specific rules hiding inside Python that a swap-the-Markdown-files pass will miss.

## The Pedagogy

The theory the whole machine serves:

- **Recognition plateaus; production breaks through.** Pure comprehensible input builds a big passive vocabulary, then stalls. The engine is *forced cold output*: an English situation in, the target language out, no multiple choice, no warm-up. Narrow and deepen before widening.
- **Engines, not word lists.** High-utility verbs are taught as generative patterns — the tense matrix, the person toggle, the obligation frame — and tested by demanding a *novel* instance: a verb never drilled in that frame. A conjugation engine in the head, not a dictionary.
- **Glue over vocabulary.** Verbs, connectors, pronouns, particles: the high-frequency words that carry most of spoken connectivity. Know the glue and you can slot any English noun into the sentence and be understood.
- **Assessment is invisible; correction is a recast.** No quizzes, no debrief forms, no "dative case." When you're off, Anna says it the natural way and moves on, the way a real elder brother mutters the fix across the table, and quietly updates state with what fired cold, what needed a hint, what missed.
- **The only narrative is yours.** Scenes are disposable one-use pegs for a word, then dropped: no serialized saga, no manufactured suspense. The story with real stakes is the learner's own arc, floor climbing toward the reveal. Climax = mastery.

## The Six Components

### The motivation engine

Nobody is waiting for your Tamil. There is no deadline, no cohort, and nothing that gets worse if you skip today — which makes stopping, not difficulty, the real failure mode. A dissertation gets finished on a decade of sunk identity and the prospect of public failure. This has neither, so the system supplies the pull itself.

**The reps aren't the chore; the cold start is.** Every touch is engineered for momentum: contact time beats completion, one rep beats zero, a partial session counts, and the coach initiates instead of waiting. No streaks, no guilt, no makeup work.

The devices exist to make a distant payoff feel present-tense. A **heist framing** carries the reward inside every rep. **Field missions** are live fire: a covert drop assigned for tonight — one line, deployed at home, unprompted (*"'suvaiya irukku' at dinner, when she isn't expecting it. Debrief tomorrow"*) — collected at the next contact. A line that survives live fire is the strongest cold-fire evidence there is. Sessions **end mid-thread** on purpose, because a conversation that closes cleanly is one you don't return to. And progress is **narrated out loud** when it moves, because a single session emits no signal you can feel.

The boundary is drawn honestly: software substitutes for deciding to start, choosing what to work on, remembering where you were, and making progress visible. It does not substitute for consequence or desire, and it stops pretending to.

### The learner model

Every tracked item carries **two independent grades**, because recognizing a word and producing it cold are different states that decay at different rates. **Recognition** runs struggled → comfortable → solid. **Production** runs none → hinted → cold. Collapsing them into one score reports a learner who knows three hundred words and hides that they can say forty. The gap between the two *is* adult language learning.

Three kinds of thing share the store: **words**, **chunks** (fixed phrases deployed whole), and **patterns** (slot templates like `frame:present-future-toggle`, metered separately as engines). Items also carry a **direction** — *fire* (produce it) or *catch* (ear-only, where the win is comprehension and forcing production is the wrong ask). Catch items are excluded from the production meter, or the meter lies.

**One ordering law**, defined once in `suggest_targets.py` and read by every channel: fewest lifetime reps → least recently worked → ripeness → least exposed → stable tiebreak. Reps lead because coverage fails silently. It is a shared function rather than a convention because it started as hand-copied sort keys, and the copies drifted.

**Two kinds of number.** The headline meter is the **viability floor** — of the words you recognize, the share that fire cold. When a real deadline exists, a finite curated deck (`curriculum/trip_deck.json`, seeded via `sync_state.py seed-deck`) takes over as the headline and burns down against the date. Whatever is narrated has to be winnable at the pace you're actually managing; the unflattering steering numbers stay in the engine and never reach the learner.

**Continuity is prose memory, not a schema.** The running story is one cumulative debrief Anna rewrites at every close — carry what matters, prune what resolved. A thread-tracking schema with due-ness scoring was built, tried, and rejected: curation at inference beats bookkeeping.

**An error ledger** records the *pattern* you keep repeating rather than each wrong answer, retires patterns rather than deleting them, and reopens them intact on recurrence — because a mistake you believed was fixed coming back is the most informative event the ledger can record.

### The loop and the rails

**The daily session** (~10–15 min) is the primary driver. Anna opens by cashing in the running story's open thread, putting a cold dispatch in your hands before you've settled in. Never "what do you want to do today?" A **deck blitz** volleys due items (instant = cold, hesitation = hinted, miss = recast-and-move), then **one living scene** — a single situation that naturally demands the words you recognize but can't yet produce. Anna also plays the table: **mask-work** (he becomes the mother-in-law demanding deference forms, or the cousin bantering at full speed, then steps out and recasts as himself) and the **eavesdrop drill** (two voices gossiping *past* you, then: *enna sonnaanga?* What did you catch?).

**The knock loop.** A CI tick wakes `morning_knock.py` every couple of hours; a deterministic **rails gate** (waking hours 8:00–21:00, ≤5 reaches/day, ≥3h apart) skips most ticks for free. Only when a reach is genuinely possible does Anna decide whether to fire or stay silent, and in which modality: a one-line **text micro-dose**, a ~60–90s **audio memo** in his pinned voice, a **challenge** with stakes, or **grace** after a lapse. Silence is a first-class choice, and "I'm busy" is a real answer that widens the gap and is never re-litigated on the next tick. Every dose is self-contained: the Tamil sits in the notification text, so even an un-tapped push lands a 2-second rep.

**The reply is the rep.** Type phonetic Tamil straight into the notification and `knock_reply.py` judges it against what the knock asked for, moves the production axis, and pushes back Anna's one-line recast. Cold credit is reserved for unaided production: if the knock showed you the Tamil, Python caps the verdict at *hinted*, deterministically. Anna can also plant a **scheduled push** at a precise time ("ping me at 8:30 to collect the debrief") via `push_queue.py`. Outreach never fakes reps; only a judged reply moves the axis.

**The authority split is the point.** The model decides whether, how and when to reach out. Code holds the waking hours, the daily cap and the minimum gap — and nothing else.

**Channel by capacity, not by request.** Driving with family, walking alone and sitting at a desk are three different products; "make it longer" from a tired listener means more repetition, not more scene.

### The studio

Dual-voice podcast episodes for dead time, plus spoken drill tracks for hands-free mouth reps. Twelve minutes of scripted bilingual audio every few days, built around the words you got wrong this week, with nobody available to proofread it — and a learner who cannot catch an error either, which is the whole reason the episode exists.

**Three narrow passes, not one prompt.** The **Director** turns the soak-order and your progress into a lesson plan; the **Architect** writes the two-voice script; the **Producer** applies the Coimbatore dialect pass, runs integrity checks and emits the metadata sidecar. Collapsing them into a single generation corrupted the material twice, in two different ways, and both outputs read fluently.

**The writer gets no filesystem.** All passes run sandboxed and print-only — no file writes, no version control, no publishing. A deterministic layer receives the text, saves it, lints it, and decides whether it ships. Every lint exists because something specific went wrong once: payload fidelity (a claimed phrase must appear verbatim), a minimum-English tripwire, a fourth-wall check, sidecar schema, stray writes. Any failure stops the run. On the drill track, where a wrong answer gets rehearsed directly, a second model call grades every answer against its cue before anything renders, and fails closed.

**Two halves, one interface.** Conversation and production are isolated and meet at exactly one contract, the **soak-order**: the words chat just strained plus a one-line scene seed. Anna hands meaning; the studio owns craft. What chat strained is what the next episode soaks.

**Fresh execution, structural variety.** Past scripts are never reused as models. Register, form and dramatic ingredient are chosen by a deterministic divergence gate before any generation begins, forbidden from repeating a value used in the last three episodes — because a generator asked repeatedly for a fresh scene converges, and taste is the thing that converged.

### The language pack

Ask a model for Tamil and you get the literary register — roughly like teaching English out of Chaucer. Spoken Coimbatore Tamil collapses verb endings, drops English nouns into Tamil sentences without embarrassment, and skips distinctions the written script marks. போறேன் (*poren*), never the textbook போகிறேன் (*pogiren*). Literary Tamil is ignored entirely.

This component is the curated, natively vetted delta: the dialect transforms (`protocol/studio/dialect.md`), the **Thanglish weave** where English carries a sentence's logistics and Tamil carries the meaning-bearing verb, the caption glosses, and the pronunciation fixes applied at the audio renderer — where they are guaranteed — rather than requested in a prompt.

It also holds the **informant policy**: who the native speaker is, how they're consulted (60-second vibe checks on specific phrasings, never grammar lessons), and what they must never be turned into. Turning a family member into an examiner would cost more than it buys.

### The governance kit

The system changes weekly, largely through AI-assisted coding, and the person changing it is also its only user. Nothing about that arrangement naturally prevents drift.

**Fix the tool, not the personality.** When the coach seems dumb, forgetful, or pushy, the answer is in the plumbing — logs and timestamps — not in thickening the persona. Anna's soul stays lean; his power grows through his tools. `sync_state.py feedback "…"` captures what lands and what grates verbatim, and a periodic **diagnosis** pass (`protocol/diagnosis.md`) proposes a dial-twist or a prune from *reproduced* patterns, never one-offs.

**Every addition must earn its place.** Before any new file, field, rule, or script: what does it replace or simplify? The system's worst moments were accumulation; its best moves were separations. Structure is frozen at Anna 1.0 — rows of data are free, schema changes wait in [`docs/feature_inbox.md`](./docs/feature_inbox.md).

**A decision log that refuses.** [`docs/DECISIONS.md`](./docs/DECISIONS.md) records what was decided *against*, and why. A fresh model context cannot distinguish "we tried this and it failed" from "nobody has tried this," so it will re-propose a killed idea persuasively — and so will you, six months later.

**Budgets with teeth.** Protocol prose, every Python file, and static-analysis findings all carry CI-enforced ceilings. Growth past budget is a red build; a raise must ride in the same commit as the growth and name what it retired. A file that keeps hitting its ceiling is doing two jobs.

**Procedures with stop conditions.** [`.claude/skills/`](./.claude/skills/) holds the `@build` playbooks, each with explicit conditions for stopping rather than proceeding.

## Repository Map

```
.github/workflows/   → The outreach ticks: knock decisions, hourly push-queue drain, reply judging
protocol/            → Anna (persona + daily_session + diagnosis) and studio/ (the isolated production crew: Director, Architect, Producer)
docs/                → Engineer's references: PROTOCOL_MAP.md (architecture), DECISIONS.md (settled decisions)
.claude/skills/      → The @build playbooks: orient, debug, extend, verify, validate, recalibrate
curriculum/
    ├── word_pool.json → Suggestion list of words to learn someday (Anna picks from it)
    └── trip_deck.json → A curated, deadline-driven deck (chunks + frames, fire/catch) seeded via sync_state.py seed-deck
content/
    ├── lessons/     → Director's planning docs (mission briefs)
    └── scripts/     → Generated podcast scripts (Markdown)
audio/               → Private MP3 output (gitignored scratch)
published_audio/     → Public MP3s served over RSS/CDN; knocks/ holds the daily morning-knock audio
progress/            → lexicon.json (word brain) + learner.json (continuity) + episodes.json + session_log.json + feedback_log.json (calibration) + knock_log.json (Anna's outreach memory) + push_queue.json (scheduled pushes)
scripts/             → Python tools (state, targets, render, drills, status, RSS, morning_knock, knock_reply, push_queue)
```

*Storage: the repo keeps only the **last 8 episodes**; old MP3s are purged as new ones land. The Markdown scripts and briefs remain as the permanent record. We move forward, not archive.*

## Getting Started

To start your own learning journey, follow the **[BOOTSTRAP.md](./BOOTSTRAP.md)** guide, a one-prompt setup that initializes your own tutor, learner profile, and progress tracking. This repo is a *reference implementation, not a framework*, but five of the six components generalize; BOOTSTRAP's **"What Generalizes"** section maps the four layers (pedagogy / machinery / language pack / learner pack), the honest port surface, and how the first session sounds from a blank state.

### Two Modes

One persistent persona runs by default; one explicit hat is for working *on* the system.

| Mode | Role | Use For |
|---------|------|---------|
| **Anna** (default, no keyword) | The coach who drives the learning | Daily sessions, drills, roleplay, commissioning podcasts, tracking progress |
| `@build` | Engineer | Editing protocols, writing scripts, refining the curriculum |

Or jump straight into a daily session with the **`/anna`** skill (Claude Code) or **`/anna`** command (Gemini CLI). Run **`/studio`** to produce a podcast episode from the current soak-order, or just ask Anna for one and he commissions it end-to-end.

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
