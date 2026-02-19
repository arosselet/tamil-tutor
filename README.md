# Madras Mappillai — The Audio Architect Protocol

A multi-modal Tamil learning system designed for **Operational Capacity** in Chennai. Audio-first, feedback-driven, and designed for high-utility survival.

## The Philosophy

Traditional language learning focuses on academic literacy. This protocol focuses on **Social Survival** and breaking the "Ghost at the Dinner Table" phenomenon.

*   **Audio First:** Prioritizing "flow", "attitude", and colloquialisms over textbook grammar.
*   **The 800 Lemmas:** Focusing on the high-frequency "glue" words needed to navigate daily life (Autos, Dining, Family).
*   **Low Friction:** Designed to fit into "dead time" (commuting, chores) via generated audio episodes. No streaks, no guilt.

## Architecture

*   **The Code Paradox:** The core logic (Director, Producer) is written in English Markdown, but the output is a culturally-nuanced Tamil reflex.
*   **The Producer:** A dedicated sub-agent that filters lesson plans to ensure colloquial authenticity (e.g., *Madras Bashai* over *Senthamil*).
*   **Dynamic Synthesis:** Episodes are generated on-demand based on your `learner.json` progress state.

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Build the vocabulary index
python scripts/build_vocab_index.py

# 3. Generate your first episode
python scripts/generate_episode.py content/scripts/level1_ep1.md audio/level1_ep1.mp3

# 4. Check your progress
python scripts/show_status.py
```

## Practical Usage

You don't need to know "what's next." The system tracks your state. You just show up and declare your energy level.

**Scenario 1: Low Energy**
> "I have low energy today. Just give me a light review."
> *System generates a "Rest and Reps" audit session.*

**Scenario 2: Specific Struggle**
> "I keep mixing up 'Iru' and 'Illai'."
> *System generates a disambiguation lesson focusing on existence vs. non-existence.*

**Scenario 3: Targeted Topic**
> "I am struggling with the future tense."
> *System pulls the "Future Intent" module from Tier 3.*

**Scenario 4: Default (No input)**
> "Generate my daily lesson."
> *System checks `learner.json`, identifies your next logical step, and builds a balanced episode.*

## Structure

```
protocol/           → LLM instructions for Gemini (Director/Producer roles)
curriculum/         → levels.json + vocabulary_index.json (The Roadmap)
content/scripts/    → Podcast scripts (Markdown)
audio/              → Generated MP3 files
progress/           → learner.json (your state)
scripts/            → Python tools for synthesis and packing
```

## The Learning Loop

1. **Download** — Generate audio for your current level
2. **Interactive** — `[Tamil Lesson]` with Gemini for active learning
3. **Passive** — Listen to audio during commute/chores
4. **Broadcasting** — Mutter the daily "Zinger" at every doorway
5. **Checkpoint** — Review mastery, level up

## Mobile Sync (iOS Workflow)

1. **Pack**: `python scripts/pack_mobile.py` (Creates `mobile_bundle.zip`)
2. **Transfer**: Upload `mobile_bundle.zip` to Gemini on your phone.
3. **Session**: Trigger with `[Tamil Lesson]`. Gemini will see all individual protocol files.
4. **Sync**: Share the generated JSON progress blob to your Home Assistant webhook.
5. **Ingest**: Back at your laptop, paste the JSON updates to Gemini and say "Sync these updates."

## Tier Goals

| Tier | Levels | Goal |
|---|---|---|
| **Survival** | 1-3 | Navigate autos, survive meals, basic greetings |
| **Comfortable** | 4-5 | Family gossip, past tense narrative, social connectivity |
| **Embedded** | 6-8 | Future planning, slang, humor, conflict resolution |
