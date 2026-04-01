# Interactive Session Protocol (@tutor)

> **NOTE:** This protocol is triggered whenever the learner uses the **@tutor** handle or requests an interactive session.

## The @tutor Pipeline

When triggered, you MUST follow this sequence. Do not skip steps. Do not jump to script generation until Step 4 is complete.

### Step 1: Read & Sync (The State Check)
Read `progress/learner.json` and `curriculum/tiers/tier_X.json`. 
- **Identify:** Last mission completed, Struggled Words, and Streak.
- **Acknowledge:** Start the response by acknowledging their streak and last episode they listened to.

### Step 2: The Micro-Debrief (Close the Loop)
If the `last_mission` in `learner.json` has audio rendered but no debrief data, ask these three quick questions:

**Ask (in conversational tone, not a form):**
1. **Clarity** — When speakers talked, how easy was it to follow? (Was anyone particularly fast, unclear, or easy to understand?)
2. **One word that stuck** — Any word from the episode that surprised you or stayed with you?
3. **Pace** — Did the scene feel rushed, steady, or slow?

**Update:** Write answers into `learner.json.last_mission.debrief`.

**Infer patterns:** Based on answers, note:
- Speaker clarity preferences
- Weak/strong patterns (present tense? fast speech? accent?)
- Recommended pacing and format for next episode

### Step 3: Mission Briefing (The Strategy)
Once debrief is complete, design the next mission:
1. **Apply Contrast:** Check last mission's location, tone, and word domain. Next episode should differ.
2. **Choose Format:** Rotate through formats (intercept_only → narrative_driven → interview_style → dual_scene → back to intercept). Format choice should address debrief patterns.
3. **Create the Brief:** Write a new file in `content/beats/tierX_missionY_brief.md` using the Director template.
4. **Present Brief:** Show the brief to the user. **Stop here** unless they say "Proceed" or "I'm ready."

### Step 4: Execution (The Act)
Only after the Brief is approved:
1. **Script:** Write the script in `content/scripts/`, using the chosen format.
2. **Audio:** Run `scripts/render_audio.py`.
3. **RSS:** Run `scripts/rebuild_rss.py`.
4. **Update State:** Set the new `active_mission` in `learner.json`, record format choice.

## The 12-Minute Standard
To ensure the brain has time to "soak" in the language:
1. **Target Word Count:** 2,000 - 2,500 words (User + AI combined).
2. **Target Duration:** 10-12 minutes.
3. **Pacing:** Balance "Slow Beats" (context, culture, storytelling) with "Fast Explosions" (dense drills, high-stakes roleplay).

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
