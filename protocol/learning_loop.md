# The Master Learning Loop

## Philosophy: Podcast First
The default mode of learning is **Audio-On-The-Go**. We prioritize generating high-quality, listenable podcasts over text-based chat sessions. Interactive sessions are powerful but are treated as **Opt-In**.

## The Energy Protocol (The Signal)
When the learner states their energy level, it dictates the **Audio Style**, not an interactive chat mode.

| Signal | Meaning | Audio Style |
|---|---|---|
| **"High Energy"** | Ready to sweat. | **The Drill / The Boss Fight.** Rapid-fire, high-rep, intense focus. |
| **"Medium Energy"** | Commuting/Chore mode. | **The Narrative / The Cultural Deep-Dive.** Strong story, steady pacing, immersive. |
| **"Low Energy"** | Just want to listen. | **The Stream / The Remix.** Passive listening, music-heavy, low cognitive load. |

*Unless the learner explicitly says "Let's do a chat lesson" or "Interactive mode", assume they want an audio file generated.*

## The 5-Phase Cycle

```
Phase 1: Checkpoint    → Review mastery and decide next mission.
Phase 2: Production    → Generate the Audio Podcast (The Default Deliverable).
Phase 3: Passive       → Learner listens during dead time (The Primary Workout).
Phase 4: Broadcasting  → Quiet muttering at physical thresholds.
Phase 5: Interactive   → (OPTIONAL) Active text-based roleplay only if requested.
```

---

## Phase 1: The Debrief (Entry Point)
- **Trigger:** Start of any new `@tutor` session.
- **Action:** 
  - Conduct a comprehensive retrospective of the *last* mission.
  - Ask for the **Energy Signal** for the *next* mission.
  - Update `progress/learner.json` based on feedback.

## Phase 2: Production (The Default)
- **Trigger:** Energy Signal received.
- **Action:** 
  1. Update `active_mission` in `learner.json`.
  2. **Generate Script:** Director (Beats) → Architect (Script) → Producer (Polished Markdown).
  3. **Generate Audio:** Run `python scripts/render_audio.py content/scripts/tierX_missionY.md audio/tierX_missionY.mp3`
  4. **Deliver:** Provide the audio file path and a brief summary.

## Phase 3: The Passive Workout (The Core)
- **Context:** Asynchronous (commute, chores, walking).
- **Action:** Learner listens to the generated podcast.
- **Technique:** Internal Shadowing (muttering along).

## Phase 4: Quiet Broadcasting
- **Action:** Pick the day's **Zinger** from the podcast.
- **Technique:** Mutter it 3 times at physical thresholds.

## Phase 5: The Interactive Session (Opt-In)
- **Trigger:** Explicit request: "Let's roleplay" or "Quiz me".
- **Action:**
  - **The Intel Briefing:** Scene setting.
  - **The Refraction Loop:** Banter and usage.
  - **The Simulation:** Text-based roleplay.
  - **Boss Fight:** High-stakes scenario.

---

## Safety Nets

### The Enjoyment Clause (The Override)
If a day is missed, there is **no makeup work**. Restart immediately where you left off. But more importantly: if any part of a session feels tedious, the learner simply says **"This isn't working."** The system immediately pauses and pivots to a different tactic. The goal is momentum, not compliance.

### Environment Anchoring
Layer audio learning onto **"Dead Time"** (commute, dishes, coffee). Protect your **Rest Time** (gaming, reading). Never study during rest.
