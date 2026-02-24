# The Master Learning Loop

## Philosophy: Hybrid Immersion
Balance active cognitive learning (interactive sessions) with passive muscle-memory building (audio). It's **"Lesson First, Audio Forever."**

## The 5-Phase Cycle

```
Phase 1: Checkpoint    → Review mastery of previous content and update learner.json
Phase 2: Download      → Generate new audio/script if advancing (Triggers Director)
Phase 3: Interactive   → Active session with Gemini (the "Sandwich")
Phase 4: Passive       → Listen to audio during dead time (walk, commute, chores)
Phase 5: Broadcasting  → Quiet muttering at physical thresholds (doorways, stairs)
```

---

## Phase 1: The Checkpoint (MANDATORY ENTRY POINT)
- **Trigger:** Start of any new `@tutor` session.
- **Action:** 
  - AI Tutor conducts a comprehensive retrospective of the *last* mission.
  - Ask the user about their comfort level within the current Tier.
  - Wait for feedback, update `progress/learner.json` accordingly.
- **Goal:** Never advance until the learner is fully caught up and comfortable. This phase decides if we move to Phase 2 (Generate New Mission) or jump to Phase 3 (Review existing vocabulary).

## Phase 2: The Download (Mission Generation)
- **Trigger:** Ready for a new mission within the Tier.
- **Action:** 
  1. Update `active_mission` in `learner.json`.
  2. **Generate Script:** Director (Beats) → Architect (Script) → Producer (Polished Markdown).
  3. **Generate Audio:** Run `python scripts/render_audio.py content/scripts/tierX_missionY.md audio/tierX_missionY.mp3`

## Phase 3: The Interactive Session (The "Sandwich")

The core daily session with Gemini. Structured in 4 layers:

1. **The Intel Briefing (The "Why")**
   - Mission context. Why does this matter for the Agent's survival?
   - Sensory-rich scene setting (smells, sounds, textures).

2. **The Refraction Loop (Pattern + Vocab)**
   - Every word must be introduced via **Story Context**, then used in **Banter**, and finally applied as a **Payoff**.
   - **Pronunciation Spotlight:** Mini-drills for challenging phonemes (e.g., ழ retroflex L).

3. **The Simulation (Cumulative Chaos)**
   - Short roleplay combining **today's** new words with **previous levels'** concepts.
   - **Boss Fight/Pressure Test:** End with a high-stakes scenario. Provide immediate feedback.
   - **Zinger highlight:** The one phrase to mutter at doorways (Phase 5).

### Dynamic Pacing (The "Focus Meter")
Monitor engagement. If overwhelmed or bored:
- Switch drill types immediately
- Suggest a 1-minute "Audio Break"
- Offer to drop to LOW energy mode

## Phase 4: The Passive Workout
- **Context:** Asynchronous (commute, chores, walking).
- **Action:** Listen to the Level Podcast.
- **Technique:** Internal Shadowing (muttering along).
- **Strategy:**
  - *New Level:* Listen to the whole file to prime.
  - *Mid Level:* Scrub to specific segments for deep drilling.
  - *Late Level:* Full file for review.

## Phase 5: Quiet Broadcasting
- **Action:** Pick the day's **Zinger** — one high-dopamine phrase.
- **Technique:** Mutter it 3 times whenever you cross a **physical threshold** (doorway, stairs, car door).
- **Purpose:** Bridges the gap between passive listening and spoken output.

---

## Safety Nets

### The Enjoyment Clause (The Override)
If a day is missed, there is **no makeup work**. Restart immediately where you left off. But more importantly: if any part of a session feels tedious, the learner simply says **"This isn't working."** The system immediately pauses and pivots to a different tactic (e.g., from high-energy drilling to passive "Stream" mode). The goal is momentum, not compliance.

### Environment Anchoring
Layer audio learning onto **"Dead Time"** (commute, dishes, coffee). Protect your **Rest Time** (gaming, reading). Never study during rest.
