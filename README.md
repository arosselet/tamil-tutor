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
3. **The morning knock.** A scheduled job (GitHub Actions) in which Anna, *unprompted*, leaves a short audio nudge on your phone each day — written fresh from your real state, rendered to MP3, served over a CDN, and delivered as a notification. It attacks the hardest problem in self-study: not the reps, but the cold start of beginning them. One knock a day, no nagging, no guilt.

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
.github/workflows/   → Morning Knock — the daily cron that pushes an audio nudge to your phone
protocol/            → Anna (persona + daily_session + session_tools + diagnosis) and studio/ (the isolated production crew: Director, Architect, Producer)
curriculum/
    └── word_pool.json → Suggestion list of words to learn someday (Anna picks from it)
content/
    ├── lessons/     → Director's planning docs (mission briefs)
    └── scripts/     → Generated podcast scripts (Markdown)
audio/               → Private MP3 output (gitignored scratch)
published_audio/     → Public MP3s served over RSS/CDN; knocks/ holds the daily morning-knock audio
progress/            → lexicon.json (word brain) + learner.json (continuity) + episodes.json + session_log.json + feedback_log.json (calibration) + knock_log.json (Anna's outreach memory)
scripts/             → Python tools (state, render, status, RSS, morning_knock)
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

### The Morning Knock (Anna's between-session reach)

The reps aren't the chore — the cold start is. So Anna doesn't wait to be opened: once a day a GitHub Actions cron runs `scripts/morning_knock.py`, which reads your state, has Anna write a fresh ~60–90s memo (English logistics, Tamil-script payload), renders it in his pinned voice, commits the MP3 (served inline via jsDelivr), and fires it to your phone through a Home Assistant webhook. The contract is deliberately gentle: **one knock a day, no nag, self-replacing, and the target phrase sits in the notification text** so even an un-tapped push lands a 2-second rep. Anna logs each knock (`progress/knock_log.json`) so the chat can cash in on it later ("caught the one I sent?"). Read-only on the learning brain — the knock observes, it never fakes reps.

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

*Contact time > completion. One listen is better than zero.*
