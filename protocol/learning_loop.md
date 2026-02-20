# The Master Learning Loop

## Philosophy: Hybrid Immersion
Balance active cognitive learning (interactive sessions) with passive muscle-memory building (audio). It's **"Lesson First, Audio Forever."**

## The 5-Phase Cycle

```
Phase 1: Download     → Get new audio content for the current level
Phase 2: Interactive   → Active session with Gemini (the "Sandwich")
Phase 3: Passive       → Listen to audio during dead time (walk, commute, chores)
Phase 4: Broadcasting  → Quiet muttering at physical thresholds (doorways, stairs)
Phase 5: Checkpoint    → Mastery review, promote words, unlock next level
```

---

## Phase 1: The Download
- **Trigger:** Start of a new Level.
- **Action:** Generate the **Level Podcast** (audio file covering all lemmas in the level).
- **Command:** `python scripts/generate_episode.py content/scripts/levelX_epY.md audio/levelX_epY.mp3`

## Phase 2: The Interactive Session (The "Sandwich")

The core daily session with Gemini. Structured in 4 layers:

1. **The Hook (The "Why")**
   - Cultural context. Why does this matter in Coimbatore?
   - Sensory-rich scene setting (smells, sounds, textures).

2. **The Mechanics (Pattern + Vocab)**
   - Introduce target vocabulary from the current level.
   - **Pronunciation Spotlight:** Mini-drills for challenging phonemes (e.g., ழ retroflex L).
   - **Pattern-Based Grammar:** Show-by-example, never academic terms.

3. **The Drill (Active Recall)**
   - Rapid-fire translation and manipulation.
   - Rotate: sentence completion, scenario dialogues, error ID, rapid-fire recognition.

4. **The Simulation (Cumulative Chaos)**
   - Short roleplay combining **today's** new words with **previous levels'** concepts.
   - **Boss Fight:** End with a high-stakes scenario. Provide immediate feedback.
   - **Zinger highlight:** The one phrase to mutter at doorways (Phase 4).

### Dynamic Pacing (The "Focus Meter")
Monitor engagement. If overwhelmed or bored:
- Switch drill types immediately
- Suggest a 1-minute "Audio Break"
- Offer to drop to LOW energy mode

## Phase 3: The Passive Workout
- **Context:** Asynchronous (commute, chores, walking).
- **Action:** Listen to the Level Podcast.
- **Technique:** Internal Shadowing (muttering along).
- **Strategy:**
  - *New Level:* Listen to the whole file to prime.
  - *Mid Level:* Scrub to specific segments for deep drilling.
  - *Late Level:* Full file for review.

## Phase 4: Quiet Broadcasting
- **Action:** Pick the day's **Zinger** — one high-dopamine phrase.
- **Technique:** Mutter it 3 times whenever you cross a **physical threshold** (doorway, stairs, car door).
- **Purpose:** Bridges the gap between passive listening and spoken output.

## Phase 5: Mastery Checkpoint
- **Frequency:** After completing all episodes in a level.
- **Action:** Review mastery. Gemini reads `learner.json`, identifies struggled words, runs a targeted drill.
- **Outcome:** Words move from `struggled` → `comfortable`. Level unlocks.

---

## Safety Nets

### The Enjoyment Clause (The Override)
If a day is missed, there is **no makeup work**. Restart immediately where you left off. But more importantly: if any part of a session feels tedious, the learner simply says **"This isn't working."** The system immediately pauses and pivots to a different tactic (e.g., from high-energy drilling to passive "Stream" mode). The goal is momentum, not compliance.

### Environment Anchoring
Layer audio learning onto **"Dead Time"** (commute, dishes, coffee). Protect your **Rest Time** (gaming, reading). Never study during rest.

### The Enjoyment Clause
Override command: **"This isn't working."** System immediately pauses and switches tactics.
