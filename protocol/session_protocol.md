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

**Infer and calibrate:** Based on answers, adjust the *next mission's difficulty* — not its format:
- Clarity struggled → Reduce NEW words to 3-4, use shorter exchanges in next Intercept
- Clarity good → Full 4-5 NEW words, standard density
- Pace too fast → More natural pauses, slower dialogue rhythm (Director notes this in brief)
- Pace too slow → Tighter dialogue, more rapid exchanges, fewer SFX pauses
- Stuck word → Add to STRUGGLED list if not already there, or note as strength if recalled correctly

### Step 3: Mission Briefing (The Strategy)
Once debrief is complete, design the next mission:
1. **Apply the Contrast Principle:** Check the last 3 missions (read their briefs or scripts). The Director brief MUST include a specific NOT list naming those missions. Example: *"Mission 31 was a tea stall phone mix-up. Mission 32 was house hunting with a landlady. Do NOT write a phone scene, a real estate scene, or a tea stall scene."*
2. **Create the Brief:** Director role writes `content/beats/tierX_missionY_brief.md` including:
   - Scene seed with **clear stakes or tension** (not just a vocab opportunity)
   - Word payload (4-5 NEW, plus STRUGGLED for organic use)
   - Specific NOT list referencing the last 3 missions by name and topic
   - Debrief calibration notes (e.g., "learner found last episode too fast — use shorter exchanges")
   - Target duration: 4-5 minutes total (Intercept + Breakdown combined)
3. **Present Brief:** Show brief to learner. **Stop here** unless they say "Proceed" or "I'm ready."

### Step 3.5: Producer Audit (Blocking Gate)
After the Architect submits the script, **before audio generation**, the Producer MUST audit the script. This step is **mandatory and blocking** — no script goes to TTS without passing.

The Producer checks exactly three things:

1. **No inline glossing.** No `**word** (English)` patterns anywhere in the Intercept. If a word needs context, the Breakdown handles it. If you find inline glossing, strip it and verify the dialogue still reads naturally.
2. **Tamil script integrity.** No gibberish, no character corruption, no mixed-encoding artifacts. Read every Tamil line. If anything looks garbled, flag it and send back to Architect.
3. **The Outsider Test.** Read the Intercept dialogue and ask: would a Coimbatore auto driver say this to his friend? If any line sounds like a textbook or a translation, rewrite it using the spoken register rules in `protocol/roles/producer.md` (Rules 3a-3e).

**If any check fails:** Fix the issue or send back to Architect for rewrite. Do NOT proceed to audio.
**If all pass:** Approve for rendering.

### Step 4: Execution (The Act)
Only after the Brief is approved AND Producer audit passes:
1. **Audio:** Run `scripts/render_audio.py`.
2. **RSS:** Run `scripts/rebuild_rss.py`.
3. **Publish:** Commit script + audio to git, push to GitHub.
4. **Update State:** Set `active_mission` in `learner.json`.

## Target Episode Duration
1. **Target Duration:** 4-5 minutes total (Intercept + Breakdown combined).
2. **Quality Over Length:** A focused 4-minute scene with clear stakes beats a padded 10-minute episode.
3. **Reference Model:** Mission 31 (Wrong Number, Right Stall) at 4:19 is the gold standard for pacing and density.

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
