# Interactive Session Protocol

> **NOTE:** This protocol is exclusively for **Phase 5 (Opt-In Interactive Sessions)**.
> For the default Podcast Generation workflow, refer to `protocol/learning_loop.md`.

## The Trigger

When the learner explicitly requests an interactive session (e.g., "Let's chat", "Quiz me", "Roleplay"), begin this protocol.

## Step 1: Read Learner State

Read `progress/learner.json` to determine:
- Current level and episode
- Struggled words (these need extra drilling)
- Comfortable words (these can be used in context but don't need focus)
- Streak data (acknowledge streaks, encourage continuation)
- Recent session history

## Step 2: Run the Session

Use vocabulary from the current tier in `curriculum/tiers/tier_X.json`, prioritizing words that fit the chosen mission arc. Weave in struggled words from `learner.json` for extra reps.

### The 12-Minute Standard (Interactive Equivalent)
To ensure the brain has time to "soak" in the language:
1. **Target Word Count:** 2,000 - 2,500 words (User + AI combined).
2. **Target Duration:** 10-12 minutes.
3. **Pacing:** Balance "Slow Beats" (context, culture, storytelling) with "Fast Explosions" (dense drills, high-stakes roleplay).

## Step 3: Session Debrief

At the end of the session:
1. Identify the **Threshold Zinger** (one phrase to mutter at doorways).
2. Ask: "What felt hard today?" — note struggled words.
3. Ask: "What clicked?" — note words that moved to comfortable.

## Step 4: Update Learner State

### If you have file access (Desktop/CLI):
Write back to `progress/learner.json`:
- Append a new entry to `sessions[]`:
  ```json
  {
    "date": "2026-02-17",
    "tier": 1,
    "mission": 1,
    "energy": "HIGH",
    "struggled": ["வேணும்", "வேண்டாம்"],
    "comfortable": ["வணக்கம்", "ஆமா"],
    "zinger": "சரி",
    "notes": "Interactive session: Nailed the greeting pattern"
  }
  ```
- Move words between `struggled_words` and `comfortable_words` as appropriate.
- Update `current_tier` if advancing.
- Update streak (increment if consecutive day, reset if gap).

### If you have NO file access (Mobile):
Emit a JSON progress blob per `protocol/mobile_sync.md`. Display it in a code block and say **"Tap Share to sync this to your system."**

---

## Handling Progress Updates (Non-Session)

When the learner says something like "I listened to Tier 1 Mission 3 and struggled with வேணும் and வேண்டாம்":

**Desktop:** Read → update → write `progress/learner.json`.

**Mobile:** Emit a `listen` or `feedback` type JSON blob per `protocol/mobile_sync.md`.

---

## Handling "Show My Progress"

When the learner asks about their progress:

1. Read `progress/learner.json` and `curriculum/index.json`
2. Report:
   - **Current Tier:** X of 3
   - **Tier Progress:** Tier 1: M/T mastered, Tier 2: M/T, Tier 3: M/T
   - **Streak:** Current X days, Best Y days
   - **Top Struggled Words:** List with count of times struggled
   - **Recommendation:** Next mission, or review if too many struggled words

> **Note:** On mobile, progress data comes from the curriculum files in the uploaded bundle. It may be stale if updates haven't been synced recently.
