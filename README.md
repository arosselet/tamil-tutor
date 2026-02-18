# Madras Mappillai — The Audio Architect Protocol

A multi-modal Tamil learning system designed for **Operational Capacity** in Chennai. Audio-first, feedback-driven, ADHD-friendly.

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

## Structure

```
protocol/           → LLM instructions for Gemini
curriculum/          → levels.json + vocabulary_index.json
content/scripts/     → Podcast scripts (Markdown)
audio/               → Generated MP3 files
progress/            → learner.json (your state)
scripts/             → Python tools
```

## The Learning Loop

1. **Download** — Generate audio for your current level
2. **Interactive** — `[Tamil Lesson]` with Gemini for active learning
3. **Passive** — Listen to audio during commute/chores
4. **Broadcasting** — Mutter the daily "Zinger" at every doorway
5. **Checkpoint** — Review mastery, level up

## Progress Tracking

Tell Gemini: *"I listened to Level 1 Episode 3 and struggled with வேணும் and வேண்டாம்."*

Gemini updates `progress/learner.json` automatically.

## Mobile Sync

For learning on the go with Gemini on iOS:

1. **Pack**: `python scripts/pack_mobile.py` (or just `git commit`)
2. **Transfer**: Upload `mobile_bundle.zip` to Gemini on your phone.
3. **Session**: Trigger with `[Tamil Lesson]`. Gemini will use `MASTER_PROTOCOL.md`.
4. **Sync**: Share the generated JSON progress blob to your Home Assistant webhook.
5. **Ingest**: Back at your laptop, paste the JSON updates to Gemini and say "Sync these updates."

## Tier Goals


| Tier | Levels | Goal |
|---|---|---|
| **Survival** | 1-3 | Navigate autos, survive meals, basic greetings |
| **Comfortable** | 4-5 | Family gossip, past tense narrative, social connectivity |
| **Embedded** | 6-8 | Future planning, slang, humor, conflict resolution |
