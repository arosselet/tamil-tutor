# Coimbatore Mappillai — The Audio Architect Protocol

<video src="https://github.com/user-attachments/assets/8a9e4c38-9074-4cc5-b0aa-f0a6812108bf" controls="controls"></video>

A framework for language learning using LLMs. Built to acquire working Tamil for daily life in Coimbatore.

### 🎧 Subscribe

[**Apple Podcasts**](https://podcasts.apple.com/us/podcast/coimbatore-mappillai/id1880268803)

[**RSS Feed Link**](https://raw.githubusercontent.com/arosselet/tamil-tutor/main/rss.xml)


---

## What This Is

An LLM-driven Tamil learning system with two pillars that share one brain — a Python-managed state file plus a teacher's-notebook profile:

1. **Anna — the daily tutor.** A persistent, stateful Coimbatore-Tamil coach you chat with for ~10–15 minutes a day. Anna runs a *forced-output* loop — he drops you into a situation and makes you produce, cold — to turn passive recognition into speaking reflex. This is the primary driver.
2. **The audio pipeline.** On-demand dual-voice Tamil podcast episodes for immersion during dead time (commute, dishes, walking). An LLM reads protocol files defining three production roles (Director, Architect, Producer), pulls from a tiered curriculum, and renders a script to MP3 via Google Cloud TTS or Edge-TTS.

Both feed and read the same progress state, so a word produced in chat and a word heard in a podcast move the same meter.

### Design Principles

- **Operational capacity over fluency.** Navigate an auto ride, survive dinner with the in-laws, handle a phone call. Not debate philosophy.
- **Coimbatore Tamil only.** Colloquial Kongu dialect. `போறேன்` not `போகிறேன்`. We ignore literary Tamil entirely.
- **Glue over vocabulary.** Verbs, connectors, pronouns, particles. The 800 high-frequency words that make up 80% of spoken connectivity. If you know the glue, you can stick any English noun into the sentence and be understood.
- **Production as the accelerant.** Recognition plateaus; forced output breaks through. The system tracks a *viability floor* — of the words you recognize, how many you can fire *cold* — and converts recognition into reflex before widening vocabulary.
- **Two pathways, one state.** Listening (the audio pipeline) builds recognition; speaking (Anna) builds production. Both compound into the same progress meter.
- **No guilt.** No streaks, no makeup work. If a lesson isn't working, say "this isn't working" and the system shifts gears.

## How It Works

```
protocol/            → LLM instructions: Anna (persona + daily_session) + production roles (Director, Architect, Producer)
curriculum/
    ├── index.json   → Tier manifest
    └── tiers/       → Vocabulary buckets (Survival → Comfort → Embedded)
content/
    ├── beats/       → Director's planning docs
    └── scripts/     → Generated podcast scripts (Markdown)
audio/               → Private MP3 output
published_audio/     → Public MP3s (served via RSS)
progress/            → learner.json + vocab_state.json (recognition + production axis)
scripts/             → Python tools (render, status, compress, RSS)
```

### The Production Pipeline

1. **Director** reads your progress and the curriculum, writes a Beat Sheet with the vocabulary payload (NEW words + spaced-repetition callbacks) and a scene seed.
2. **Architect** turns the Beat Sheet into an engaging dual-voice script — an Intercept (slice-of-life scene) plus a Breakdown (two analysts unpacking it).
3. **Producer** applies the Coimbatore dialect pass (verb forms, Sandhi, Kongu layer), enforces Tamil script for every Tamil word, and runs a final scrubbing pass for TTS fidelity.
4. `render_audio.py` generates the MP3 with randomized voice assignments.

### The Daily Loop (Anna)

```
Warm callback → Cold dispatch → Recast (never lecture) → Log → Field kit
```

Anna's daily session is the default. He loads your state, targets words you *recognize but can't yet produce*, and forces you to say them cold. Misses get recast naturally — no grammar lectures. Each session updates the **production axis** and reports where the **viability floor** moved. The audio pipeline is the opt-in immersion layer alongside it.

## Getting Started

### Prerequisites

- Python 3.10+
- An LLM agent ([Gemini CLI](https://github.com/google-gemini/gemini-cli), Antigravity, or similar)
- TTS authentication:
  - **Edge-TTS:** No setup required.
  - **Google Cloud TTS (default):** `gcloud auth login`

```bash
pip install -r requirements.txt
```

### Two Modes

| Keyword | Role | Use For |
|---------|------|---------|
| `@tutor` (default) | Showrunner & Tutor | Generating lessons, running sessions, tracking progress |
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
