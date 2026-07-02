# Coimbatore Mappillai — From Recognition to Reflex

<video src="https://github.com/user-attachments/assets/f347ef0f-1fe5-46d8-aaad-f323cf665cc8" controls width="480"></video>

A persistent, stateful language coach powered by LLMs. Built for Coimbatore Tamil; the architecture is portable to any language. The system tracks one number: of everything you've heard and recognized, how much can you actually fire cold.

### 🎧 Subscribe

[**Apple Podcasts**](https://podcasts.apple.com/us/podcast/coimbatore-mappillai/id1880268803)

[**RSS Feed Link**](https://raw.githubusercontent.com/arosselet/tamil-tutor/main/rss.xml)


---

## What This Is

An LLM-driven Tamil learning system. Anna — a persistent, stateful coach with one charge, *install a reflex in your brain* — is the single continuous relationship, and he reaches you across three surfaces that share one brain (a Python-managed state file plus a teacher's-notebook profile):

1. **Anna — the daily tutor.** A Coimbatore-Tamil coach you chat with for ~10–15 minutes a day. Anna runs a *forced-output* loop — he drops you into a situation and makes you produce, cold — to turn passive recognition into speaking reflex. This is the primary driver.
2. **The audio pipeline.** On-demand dual-voice Tamil podcast episodes for immersion during dead time (commute, dishes, walking). An LLM reads protocol files defining three production roles (Director, Architect, Producer), pulls from a word pool, and renders a script to MP3 via Google Cloud TTS or Edge-TTS.
3. **The knock loop.** Anna reaches your phone between sessions — *unprompted*, written fresh from your real state — and the notification is a two-way rep: type phonetic Tamil straight into the reply and a judge scores it, moves your production axis, and pushes Anna's recast back. It attacks the hardest problem in self-study: not the reps, but the cold start of beginning them. Hard rails (waking hours, a daily cap, minimum spacing) keep presence from becoming pestering — and silence is a first-class choice Anna makes freely.

All three feed and read the same progress state, so a word produced in chat and a word heard in a podcast move the same meter.

### Design Principles

- **Operational capacity over fluency.** Navigate an auto ride, survive dinner with the in-laws, handle a phone call. Not debate philosophy.
- **Coimbatore Tamil only.** Colloquial Kongu dialect. `போறேன்` not `போகிறேன்`. We ignore literary Tamil entirely.
- **Glue over vocabulary.** Verbs, connectors, pronouns, particles. The 800 high-frequency words that make up 80% of spoken connectivity. If you know the glue, you can stick any English noun into the sentence and be understood.
- **Production as the accelerant.** Recognition plateaus; forced output breaks through. The system tracks a *viability floor* — of the words you recognize, how many you can fire *cold* — and converts recognition into reflex before widening vocabulary.
- **Two pathways, one state.** Listening (the audio pipeline) builds recognition; speaking (Anna) builds production. Both compound into the same progress meter.
- **No guilt.** No streaks, no makeup work. If a lesson isn't working, say "this isn't working" and the system shifts gears.

## How It Works

```
.github/workflows/   → The outreach ticks: knock decisions, hourly push-queue drain, reply judging
protocol/            → Anna (persona + daily_session + session_tools + diagnosis) and studio/ (the isolated production crew: Director, Architect, Producer)
curriculum/
    ├── word_pool.json → Suggestion list of words to learn someday (Anna picks from it)
    └── trip_deck.json → A curated, deadline-driven deck (chunks + frames, fire/catch) seeded via sync_state.py seed-deck
content/
    ├── lessons/     → Director's planning docs (mission briefs)
    └── scripts/     → Generated podcast scripts (Markdown)
audio/               → Private MP3 output (gitignored scratch)
published_audio/     → Public MP3s served over RSS/CDN; knocks/ holds the daily morning-knock audio
progress/            → lexicon.json (word brain) + learner.json (continuity) + episodes.json + session_log.json + feedback_log.json (calibration) + knock_log.json (Anna's outreach memory) + push_queue.json (scheduled pushes)
scripts/             → Python tools (state, targets, render, status, RSS, morning_knock, knock_reply, push_queue)
```

*Storage: the repo keeps only the **last 8 episodes** and playlists — old MP3s are purged as new ones land. The Markdown scripts and briefs remain as the permanent record; we move forward, not archive.*

### The Studio (Production Pipeline)

The studio is an isolated crew Anna commissions end-to-end (or you run with `/studio`). It takes the **soak-order** Anna set in chat and runs four passes:

1. **Director** reads your progress and the word pool, writes a Master Lesson Plan with the vocabulary payload (NEW words + spaced-repetition callbacks) and a scene seed.
2. **Architect** turns the Master Lesson Plan into an engaging dual-voice script — an Intercept (slice-of-life scene) plus a Breakdown (two analysts unpacking it).
3. **Producer** applies the Coimbatore dialect pass (verb forms, Sandhi, Kongu layer), enforces Tamil script for every Tamil word, and runs a final scrubbing pass for TTS fidelity.
4. `render_audio.py` generates the MP3 with randomized voice assignments.

### The Daily Loop (Anna)

```
Open on the running story (hand over a rep cold) → One living scene (cold fires as moves) → Recast (never lecture) → Close & log → Report the floor
```

Anna's daily session is the default. He loads your state, targets words you *recognize but can't yet produce*, and forces you to say them cold. Misses get recast naturally — no grammar lectures. Each session updates the **production axis** and reports where the **viability floor** moved. The audio pipeline is the opt-in immersion layer alongside it.

### The Knock Loop (Anna's between-session reach)

The reps aren't the chore — the cold start is. So Anna doesn't wait to be opened. A GitHub Actions tick wakes `scripts/morning_knock.py` every couple of hours; a cheap Python **rails gate** (waking hours, ≤3 reaches/day, ≥3h apart, plus Anna's own self-set next-check) skips most ticks for free, and only when a reach is genuinely possible does Anna decide — fire or silence, and in which modality: a one-line **text micro-dose**, a ~60–90s **audio memo** in his pinned voice (rendered, committed, served via jsDelivr), a **challenge** with stakes (including field missions), or **grace** after a lapse. Every dose is self-contained: the Tamil sits in the notification text, so even an un-tapped push lands a 2-second rep.

**The reply is the rep.** Type phonetic Tamil straight into the notification and `scripts/knock_reply.py` judges it against what the knock asked for — *cold* only for unaided production (Tamil the knock showed you caps at *hinted*; Python enforces that deterministically) — moves the production axis, and pushes back Anna's one-line recast plus the deck score. A scored reply can chain one follow-up micro-ask, so a hot moment becomes two or three reps. Anna can also plant a **scheduled push** at a precise time ("ping me at 8:30 to collect the field-mission debrief") via `scripts/push_queue.py`; an hourly CI drain delivers it, and the rails count it like any reach. Outreach itself never fakes reps — only a judged reply moves the axis.

Feedback heals the tools, not the soul: `sync_state.py feedback "…"` captures what you react to, and a periodic **diagnosis** pass (`protocol/diagnosis.md`) proposes a dial-twist or a prune from *reproduced* patterns — never one-offs — keeping the system focused instead of diffuse.

## Getting Started

If you are new to the repository and want to start your own Tamil learning journey, please follow the **[BOOTSTRAP.md](./BOOTSTRAP.md)** guide. It will walk you through a one-prompt setup to initialize your own tutor, learner profile, and progress tracking.

### Two Modes

One persistent persona runs by default; one explicit hat is for working *on* the system.

| Mode | Role | Use For |
|---------|------|---------|
| **Anna** (default, no keyword) | The coach who drives the learning | Daily sessions, drills, roleplay, commissioning podcasts, tracking progress |
| `@build` | Engineer | Editing protocols, writing scripts, refining the curriculum |

Or jump straight into a daily session with the **`/anna`** skill (Claude Code) or **`/anna`** command (Gemini CLI). Run **`/studio`** to produce a podcast episode from the current soak-order — or just ask Anna for one, and he commissions it end-to-end.

### On Your Laptop (The Factory)

Prompt the agent:

- *"Show my status"* — progress dashboard
- *"I'm ready for the next episode"* — generates a new lesson
- *"Medium energy"* — sets the audio style (narrative pacing)
- *"I'm struggling with past tense verbs"* — the system adapts

### On Your Phone

The repo syncs via GitHub, so Anna runs from your phone with full state — no laptop required. Open the **Code** tab in the Claude mobile app (or **[claude.ai/code](https://claude.ai/code)**), select this GitHub repo, and run `/anna`. State commits straight back to GitHub.

---

*Contact time > completion. One rep is better than zero.*
