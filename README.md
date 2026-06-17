# Coimbatore Mappillai — From Recognition to Reflex

<video src="https://github.com/user-attachments/assets/f347ef0f-1fe5-46d8-aaad-f323cf665cc8" controls width="480"></video>

A persistent, stateful language coach powered by LLMs. Built for Coimbatore Tamil; the architecture is portable to any language. The system tracks one number: of everything you've heard and recognized, how much can you actually fire cold.

### 🎧 Subscribe

[**Apple Podcasts**](https://podcasts.apple.com/us/podcast/coimbatore-mappillai/id1880268803)

[**RSS Feed Link**](https://raw.githubusercontent.com/arosselet/tamil-tutor/main/rss.xml)


---

## What This Is

An LLM-driven Tamil learning system with two pillars that share one brain — a Python-managed state file plus a teacher's-notebook profile:

1. **Anna — the daily tutor.** A persistent, stateful Coimbatore-Tamil coach you chat with for ~10–15 minutes a day. Anna runs a *forced-output* loop — he drops you into a situation and makes you produce, cold — to turn passive recognition into speaking reflex. This is the primary driver.
2. **The audio pipeline.** On-demand dual-voice Tamil podcast episodes for immersion during dead time (commute, dishes, walking). An LLM reads protocol files defining three production roles (Director, Architect, Producer), pulls from a word pool, and renders a script to MP3 via Google Cloud TTS or Edge-TTS.

Both feed and read the same progress state, so a word produced in chat and a word heard in a podcast move the same meter.

### Design Principles

- **Operational capacity over fluency.** Navigate an auto ride, survive dinner with the in-laws, handle a phone call. Not debate philosophy.
- **Coimbatore Tamil only.** Colloquial Kongu dialect. `போறேன்` not `போகிறேன்`. We ignore literary Tamil entirely.
- **Glue over vocabulary.** Verbs, connectors, pronouns, particles. The 800 high-frequency words that make up 80% of spoken connectivity. If you know the glue, you can stick any English noun into the sentence and be understood.
- **Production as the accelerant.** Recognition plateaus; forced output breaks through. The system tracks a *viability floor* — of the words you recognize, how many you can fire *cold* — and converts recognition into reflex before widening vocabulary.
- **Two pathways, one state.** Listening (the audio pipeline) builds recognition; speaking (Anna) builds production. Both compound into the same progress meter.
- **No guilt.** No streaks, no makeup work. If a lesson isn't working, say "this isn't working" and the system shifts gears.
- **Fail Forward Storage.** The repository only maintains the **last 8 episodes** and playlists. We don't archive old audio; we move forward. The markdown scripts and briefs remain as the permanent record.

## How It Works

```
protocol/            → LLM instructions: Anna (persona + daily_session) + production roles (Director, Architect, Producer)
curriculum/
    └── word_pool.json → Suggestion list of words to learn someday (Anna picks from it)
content/
    ├── lessons/     → Director's planning docs (mission briefs)
    └── scripts/     → Generated podcast scripts (Markdown)
audio/               → Private MP3 output
published_audio/     → Public MP3s (served via RSS)
progress/            → lexicon.json (word brain: recognition + production per word) + learner.json (continuity) + episodes.json + session_log.json
scripts/             → Python tools (state, render, status, RSS)
```

### The Production Pipeline

1. **Director** reads your progress and the word pool, writes a Beat Sheet with the vocabulary payload (NEW words + spaced-repetition callbacks) and a scene seed.
2. **Architect** turns the Beat Sheet into an engaging dual-voice script — an Intercept (slice-of-life scene) plus a Breakdown (two analysts unpacking it).
3. **Producer** applies the Coimbatore dialect pass (verb forms, Sandhi, Kongu layer), enforces Tamil script for every Tamil word, and runs a final scrubbing pass for TTS fidelity.
4. `render_audio.py` generates the MP3 with randomized voice assignments.

### The Daily Loop (Anna)

```
Warm callback → One living scene (cold fires as moves) → Recast (never lecture) → Log → Field kit
```

Anna's daily session is the default. He loads your state, targets words you *recognize but can't yet produce*, and forces you to say them cold. Misses get recast naturally — no grammar lectures. Each session updates the **production axis** and reports where the **viability floor** moved. The audio pipeline is the opt-in immersion layer alongside it.

## Getting Started

If you are new to the repository and want to start your own Tamil learning journey, please follow the **[BOOTSTRAP.md](./BOOTSTRAP.md)** guide. It will walk you through a one-prompt setup to initialize your own tutor, learner profile, and progress tracking.

### Two Modes

One persistent persona runs by default; one explicit hat is for working *on* the system.

| Mode | Role | Use For |
|---------|------|---------|
| **Anna** (default, no keyword) | The coach who drives the learning | Daily sessions, drills, roleplay, commissioning podcasts, tracking progress |
| `@build` | Engineer | Editing protocols, writing scripts, refining the curriculum |

Or jump straight into a daily session with the **`/anna`** skill (Claude Code) or **`/anna`** command (Gemini CLI).

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
