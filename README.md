# Coimbatore Mappillai — The Audio Architect Protocol

<video src="https://github.com/user-attachments/assets/8a9e4c38-9074-4cc5-b0aa-f0a6812108bf" controls="controls"></video>

A framework for language learning using LLMs. Built to acquire working Tamil for daily life in Coimbatore.

### 🎧 Subscribe

New episodes drop into your podcast app as they're generated. Add this feed in Apple Podcasts, Overcast, or any RSS reader:

```
https://raw.githubusercontent.com/arosselet/tamil-tutor/main/rss.xml
```

---

## What This Is

An audio-first learning system that generates dual-voice Tamil podcast episodes on demand. An LLM reads a set of protocol files that define three production roles (Director, Architect, Producer), pulls vocabulary from a tiered curriculum, checks the learner's progress, and writes a script. That script is rendered to MP3 via Google Cloud TTS or Edge-TTS.

The learner listens during dead time (commute, dishes, walking), gives feedback, and the system adapts.

### Design Principles

- **Operational capacity over fluency.** Navigate an auto ride, survive dinner with the in-laws, handle a phone call. Not debate philosophy.
- **Coimbatore Tamil only.** Colloquial Kongu dialect. `போறேன்` not `போகிறேன்`. We ignore literary Tamil entirely.
- **Glue over vocabulary.** Verbs, connectors, pronouns, particles. The 800 high-frequency words that make up 80% of spoken connectivity. If you know the glue, you can stick any English noun into the sentence and be understood.
- **Audio first.** Language acquisition happens through listening. Episodes are generated, not handwritten. The system compounds: words you've learned stop being taught and start being *used* without translation.
- **No guilt.** No streaks, no makeup work. If a lesson isn't working, say "this isn't working" and the system shifts gears.

## How It Works

```
protocol/            → LLM instructions (Director, Architect, Producer roles)
curriculum/
    ├── index.json   → Tier manifest
    └── tiers/       → Vocabulary buckets (Survival → Comfort → Embedded)
content/
    ├── beats/       → Director's planning docs
    └── scripts/     → Generated podcast scripts (Markdown)
audio/               → Private MP3 output
published_audio/     → Public MP3s (served via RSS)
progress/            → learner.json (your state)
scripts/             → Python tools (render, status, compress, RSS)
```

### The Production Pipeline

1. **Director** reads your progress and the curriculum, writes a Beat Sheet with vocabulary assignments and a rotation style (Narrative, Drill, Deep-Dive, Remix, or Speed-Dating).
2. **Architect** turns the Beat Sheet into an engaging dual-voice script following the immersion gradient (Tier 1: ~90% English → Tier 3: ~70% Tamil).
3. **Producer** enforces Tamil script for all Tamil words, converts to colloquial Kongu forms, and runs a final scrubbing pass for TTS fidelity.
4. `render_audio.py` generates the MP3 with randomized voice assignments.

### The Learning Loop

```
Debrief → Production → Passive Listening → Quiet Broadcasting → Interactive (opt-in)
```

The default output is a podcast episode. Interactive chat sessions are available but opt-in.

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

### On Your Laptop (The Factory)

Prompt the agent:

- *"Show my status"* — progress dashboard
- *"I'm ready for the next episode"* — generates a new lesson
- *"Medium energy"* — sets the audio style (narrative pacing)
- *"I'm struggling with past tense verbs"* — the system adapts

### On Your Phone (Interactive)

Upload `mobile_bundle.zip` to a Gemini session and type `[Tamil Lesson]`. Set your energy level and go. Progress is captured as JSON blobs you paste back into a desktop Debrief.

---

*Contact time > completion. One listen is better than zero.*
