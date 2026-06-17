# Bootstrap Guide: Start Your Tamil Heist

Welcome to the Tamil Learning System. This guide initializes your own persistent tutor, learner profile, and progress tracking in a single session.

## Prerequisites
- **Python 3.10+**
- **An LLM Agent** (Claude Code, Gemini CLI, or similar)
- **TTS Access**:
  - *Edge-TTS* (Free, no setup)
  - *Google Cloud TTS* (Requires `gcloud auth login`)

---

## One-Prompt Setup

Clone the repo, then paste this into your LLM agent:

> "I want to bootstrap a new Tamil learning environment. Please act as the System Architect.
> 1. Read `BOOTSTRAP.md` for the setup protocol.
> 2. Ask me for my name, my preferred tutor's name/personality (e.g., elder brother, strict coach, casual friend), and my TTS preference (Edge or Google).
> 3. Initialize progress files from the `.example` templates.
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
Copy each `.example` file to its live counterpart and fill in the user's data:

| Template | Live file | Purpose |
|---|---|---|
| `progress/learner.json.example` | `progress/learner.json` | Continuity: streak, debrief, soak order, status |
| `progress/lexicon.json.example` | `progress/lexicon.json` | The word brain (starts empty — `sync_state.py` populates it) |
| `progress/episodes.json.example` | `progress/episodes.json` | Audio episode registry (starts empty) |
| `progress/session_log.json.example` | `progress/session_log.json` | Append-only momentum log (starts empty) |
| `progress/profile.md.example` | `progress/profile.md` | Teacher's notebook — fill in learner name, goal, initial assessment |

In `learner.json`, replace `"Your Name"` with the learner's name.

### 3. Codify the Persona
Rewrite `protocol/persona.md` to reflect the chosen tutor's voice based on the `persona.md.example` template.
- Ensure the **"What [Tutor] Never Does"** list is intact.
- The tutor is the single interactive front door — they drive the pedagogy and can commission audio when it serves the goal.

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
- `protocol/` — The generative logic (persona, daily session, audio pipeline roles).
- `progress/` — Your personal state (gitignored JSON managed by Python + LLM-maintained profile).
- `curriculum/` — The shared Tamil vocabulary pool.
- `scripts/` — Python engine: `sync_state.py` owns all state writes; `render_audio.py`, `show_status.py`, `generate_callbacks.py`, `build_playlist.py` for audio and spaced repetition.

*Keep your `progress/` folder synced to a private Git repository so your tutor remembers you across devices.*
