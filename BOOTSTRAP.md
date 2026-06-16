# Bootstrap Guide: Start Your Tamil Heist

Welcome to the Tamil Learning System. This guide will help you set up your own persistent tutor, define your learner profile, and begin your immersion journey in a single session.

## Prerequisites
- **Python 3.10+**
- **An LLM Agent** (Gemini CLI, Claude Code, or similar)
- **TTS Access**:
  - *Edge-TTS* (Free, no setup)
  - *Google Cloud TTS* (Requires `gcloud auth login`)

---

## 🚀 One-Prompt Setup

Once you have cloned this repository, paste the following prompt into your LLM agent to initialize your environment:

> "I want to bootstrap a new Tamil learning environment. Please act as the System Architect.
> 1. Read `BOOTSTRAP.md` for the setup protocol.
> 2. Ask me for my name, my preferred tutor's name/personality (e.g., elder brother, strict coach, casual friend), and my TTS preference (Edge or Google).
> 3. Initialize `progress/learner.json` and `progress/profile.md` from the templates.
> 4. Customize `protocol/persona.md` based on the tutor personality I choose.
> 5. Guide me through setting up my own git remote.
> 6. Start our first `/anna` session."

---

## The Bootstrap Protocol (Agent Instructions)

If you are the agent performing this bootstrap, follow these steps exactly:

### 1. Identify the Learner
Ask the user:
- **Learner Name**: (e.g., "Andrew")
- **Tutor Name & Persona**: (e.g., "Anna, the elder brother from Coimbatore")
- **Heist Framing**: What is the "secret goal"? (e.g., "Surprise my wife at a wedding")
- **TTS Provider**: `edge` or `google`.

### 2. Initialize State
Initialize the following files by copying their `.example` counterparts and filling in the user's data:

- `progress/learner.json` (from `progress/learner.json.example`)
- `progress/profile.md` (from `progress/profile.md.example`)
- `progress/vocab_state.json` (from `progress/vocab_state.json.example`)
- `protocol/persona.md` (from `protocol/persona.md.example`)

### 3. Codify the Persona
Rewrite `protocol/persona.md` to reflect the chosen tutor's voice based on the `persona.md.example` template.
- Ensure the **"What [Tutor] Never Does"** list is intact.
- Maintain the **Showrunner** responsibility (Anna is in charge of the pedagogy and audio pipeline).

### 4. Git Remote Setup
Remind the user to set up their own private repository:
```bash
git remote remove origin
git remote add origin [their-private-repo-url]
git push -u origin main
```

### 5. Start the Loop
Run the first `/anna` session using the fresh state.

---

## Repository Structure for Portability
- `protocol/` - The brains (Persona, Daily Session, Audio Pipeline).
- `progress/` - Your personal state (NOT to be shared if you want to keep the heist secret).
- `curriculum/` - The shared Tamil vocabulary pool.
- `scripts/` - The Python engine for state and audio.

*Note: For the best experience, keep your `progress/` folder and `published_audio/` synced to a private Git repository so your tutor remembers you across devices.*
