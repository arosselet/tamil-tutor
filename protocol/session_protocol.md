# Interactive Session Protocol (@tutor)

> **NOTE:** This protocol is triggered whenever the learner uses the **@tutor** handle or requests an interactive session.

## The @tutor Pipeline

When triggered, you MUST follow this sequence. Do not skip steps. Do not jump to script generation until Step 4 is complete.

### Step 1: Read & Sync (The State Check)
Read `progress/learner.json`. It's a thin file — current mission, streak, recent missions with listen counts, and a status line.
- **Acknowledge:** Greet the learner, mention their streak and last episode.
- **Read the status line.** It tells you whether to recommend a re-listen playlist or proceed to new production.

### Step 2: The Debrief (Close the Loop)

**Ask (conversational, not a form):**
1. **Listens** — How many times have you re-listened since we last talked?
2. **Clarity** — How easy was it to follow? Anyone too fast or unclear?
3. **Stuck word** — Any word that tripped you up or surprised you?
4. **Pace** — Rushed, steady, or slow?

**Then run:** `python scripts/sync_state.py update --listens N` (with `--stuck-word "word"` and `--debrief "note"` as applicable). This updates vocab_state.json and recomputes the status line in learner.json.

**Re-read learner.json** after the update to see the new status.

**Calibrate for next episode:**
- Clarity struggled → Reduce NEW words to 3-4, shorter exchanges
- Clarity good → Full 4-5 NEW words, standard density
- Pace too fast → More natural pauses, slower rhythm
- Pace too slow → Tighter dialogue, more rapid exchanges
- Stuck word → sync_state.py handles adding it to struggled list

### Step 3: Act on the Status Line

**If status says "re-listen playlist recommended":**
- Run `python scripts/build_playlist.py` to build a concatenated MP3
- Tell the learner: "Here's your playlist — X episodes, Y minutes. Listen to this before we make something new."
- Stop here. Don't produce a new episode.

**If status says "Ready for new episode" (or learner overrides):**
- Proceed to Step 4.

### Step 4: Mission Briefing (The Strategy)
1. **Generate Callbacks:** Run `python scripts/generate_callbacks.py`
2. **Contrast:** Check the last 2-3 scripts. Don't repeat locations, topics, or energy.
3. **Create the Brief:** Director role writes `content/beats/tierX_missionY_brief.md`:
   - Scene seed with clear stakes or tension
   - Word payload (4-5 NEW, plus CALLBACKS from generate_callbacks output)
   - Debrief calibration notes if applicable
   - Target duration: 5-8 minutes total (Intercept + Breakdown combined)
4. **Present Brief** to learner. **Stop here** unless they say "Proceed" or "I'm ready."

### Step 4.5: Producer Audit (The Vibe Check)
After the Architect submits the script, **before audio generation**, the Producer audits:

1. **The Riff Test.** Does the Breakdown feel like two friends riffing, not a narrator listing words?
2. **Tamil script integrity.** No gibberish, no character corruption.
3. **The Coimbatore Test.** Would a Coimbatore native say this?

**If any check fails:** Fix or send back. Do NOT proceed to audio.

### Step 5: Execution (The Act)
Only after Brief approved AND Producer audit passes:
1. **Audio:** Run `scripts/render_audio.py`.
2. **RSS:** Run `scripts/rebuild_rss.py`.
3. **Publish:** Commit script + audio to git, push to GitHub.
4. **Update State:** Run `python scripts/sync_state.py update --debrief "summary"` to set the new active mission.

## Target Episode Duration
1. **Target Duration:** 5-8 minutes total (Intercept + Breakdown combined).
2. **Conversation is Key:** A 2-minute Intercept followed by a 4-6 minute NotebookLM-style Breakdown is the ideal structure.
3. **Reference Model:** Mission 31 (Wrong Number, Right Stall) is the gold standard for pacing and depth.

---

## Handling Progress Updates (Non-Session)

When the learner reports listening or struggling with words:

Run `python scripts/sync_state.py update` with the appropriate flags.

---

## Handling "Show My Progress"

Run `python scripts/sync_state.py status` and report the output.
