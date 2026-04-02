# Tamil Tutor System: Holistic Analysis

**Date:** 2026-04-01  
**Status:** Under Review  
**Focus:** Clarity, Separated Concerns, Connection Logic

---

## I. CURRENT STATE: What Works

### The Philosophy Layer (Strong)
- **Core Principle:** Operational Capacity, not fluency
- **Dialect:** Coimbatore Tamil only (colloquial, never literary)
- **Core Constraint:** Zero fourth-wall breaking (learner is never a character)
- **Learning Philosophy:** Contact time > completion; enjoyment drives momentum

**Assessment:** Clear, consistent, and actionable. This layer has integrity.

---

### The Role System (Partially Clear)
Three roles exist but have overlapping/unclear responsibilities:

| Role | Current Purpose | Clarity |
|:---|:---|:---|
| **Director** | Word payload + scene seed + negative constraints | ✓ Clear |
| **Architect** | Turn brief into script with creative freedom | ⚠️ Vague on "creative freedom" boundaries |
| **Producer** | TTS quality control, register audit, casting | ✓ Clear but rarely executed |

**Problem:** There's no clear "approval gate" between Architect and Producer. Scripts go directly to TTS without a register audit, leading to brittle Tamil when the model struggles.

---

### The Format System (Unstable)
**Current State:** System pivoted from Intercept-only → Intercept+Breakdown (to add variety) → Now back to Intercept-only with format rotation.

**Successful Episodes (by duration):**
- Mission 31 (Wrong Number, Right Stall): **4:19** — Intercept + Breakdown, strong character interactions
- Mission 32 (House Hunt): **1:48** — Intercept-only, too sparse
- Mission 30: **2:43** — Intercept-only

**Pattern:** Episodes with strong character stakes and dialogue length (4-5 min range) perform better. Breakdown adds padding but also adds repetitive analyst commentary.

**New Direction:** Format rotation without Breakdown may reduce uniformity but loses the depth-dive analysis that Mission 31 got right.

---

### The Debrief System (Recently Redesigned)
- **Old:** Sessions table in learner.json, never filled
- **New:** Micro-debrief (3 questions) integrated into @tutor Step 2
- **Status:** Just implemented; untested

**Assessment:** Simplification is good, but debrief → format selection connection is *implied*, not explicit in the prompts.

---

## II. PROBLEMS IDENTIFIED

### A. Script Generation Fragility
**Issue:** When a model writes longer narrative/dialogue (4-5+ min), Tamil script integrity degrades. Gibberish and character mixing appear partway through. This happened with Mission 33.

**Root Cause:** 
1. Multi-language context (English nouns + Tamil verbs + dialogue markers + SFX)
2. Long passages increase probability of character corruption
3. No "Producer" gate to catch and fix degradation before TTS

**Current Workaround:** Fall back to human review or switch models (Opus, Gemini).

**Better Solution:** Build explicit Producer prompt that does a "Register & Script Audit" pass before sending to TTS.

---

### B. Format Rotation Is Underspecified
**Issue:** Debrief data (Clarity, Stuck Word, Pace) should inform format choice, but the connection is vague.

**Current Brief:** "Format: narrative_driven" appears in learner.json but there's no decision tree:
- When should we choose Intercept-only?
- When should we choose Narrative-driven?
- When should we choose Interview-style?
- What does each format teach *differently*?

**Missing:** A **Format Selection Protocol** that maps debrief patterns → format choice.

---

### C. Word Weaving Rules Are Not Enforced
**Issue:** The Immersion Gradient defines NEW/USE/STRUGGLED modes, but:
1. The Director brief doesn't explicitly flag which words are which
2. The Architect doesn't have a checklist to verify weaving
3. No way to know if a NEW word appears enough times or STRUGGLED words are forced

**Current State:** Architect trusts instinct; sometimes NEW words are glossed in dialogues (which breaks the no-gloss rule).

---

### D. Listenability Test Is Aspirational, Not Actionable
**Philosophy Rule:** "If someone who doesn't care about Tamil wouldn't enjoy this, it needs more conflict."

**Problem:** This is a vague standard. What constitutes "conflict"? How does the Architect know if they've passed the test?

**Example (Mission 32):** No dramatic tension, just rapid vendor-hopping. Failed the test but was published anyway.

---

### E. Episode Length Is Unclear
**Current Expectation:** 8-10 minutes (stated in protocols)  
**Actual Success Range:** 4-5 minutes (Mission 31 model)  
**Recent Attempt (M33):** 1:53 (too short)

**Issue:** No target duration is specified anywhere. Should vary by format? Should intercept-only be shorter than intercept+breakdown?

---

## III. SEPARATE CONCERNS (What's Mixed)

### Currently Entangled:
1. **Scene Design** (seed + characters + conflict) mixed into **Word Payload** (NEW/USE/STRUGGLED)
2. **Narrative Pacing** mixed into **Format Selection**
3. **Casting/Voices** mixed into **Script Content** (character dialogue)
4. **Register Audit** (spoken Tamil) mixed into **Script Drafting** (should be separate pass)

### Ideal Separation:

```
Direction Phase:
  ├─ Scene Design (Director role): Seed + Characters + Tone + Conflict
  ├─ Word Payload (Director role): NEW/USE/STRUGGLED lists
  ├─ Format Selection (debrief patterns): Intercept-only vs Narrative vs Interview
  └─ Episode Length Target: 4-5 min for this format
        ↓
Script Generation Phase:
  ├─ Narrative Draft (Architect): Turn scene + words into dialogue
  ├─ Register Audit Pass (Producer): Fix Tamil script, spoken register, dialect
  └─ Casting Pass (Producer): Add gender tags, voice assignments
        ↓
Audio Rendering Phase:
  └─ TTS generation (automated via render_audio.py)
```

---

## IV. CLARITY ISSUES IN CURRENT PROMPTS

### Director Role (`protocol/roles/director.md`)
**Current State:** Clear on inputs (payload, seed, constraints).  
**Missing:**
- Explicit connection to last debrief data
- Format selection decision tree
- Target duration for this format
- Listenability checklist (what makes this scene interesting?)

### Architect Role (`protocol/roles/architect.md`)
**Current State:** High creative freedom, but boundaries vague.  
**Missing:**
- Word weaving checklist (how many times should NEW appear?)
- Register guidelines (reference: use Mission 31 as the model)
- Conflict/stakes audit (does this scene have dramatic tension?)
- Format-specific guidance:
  - Intercept-only: How much dialogue? How much narrator?
  - Narrative-driven: What kind of narrator voice? How much direct speech?
  - Interview-style: Question structure? Response patterns?

### Producer Role (`protocol/roles/producer.md`)
**Current State:** Detailed register rules, but rarely executed.  
**Missing:**
- Explicit "gate" in the protocol (when does Producer review happen?)
- Checklist format (pass/fail criteria for each rule)
- Clear instruction: What to do if register audit fails? (Fix vs. escalate)

### @tutor Protocol (`protocol/session_protocol.md`)
**Current State:** Updated with micro-debrief, but connection vague.  
**Missing:**
- Step 2.5: Debrief → Format Selection logic
- How does "clarity: mostly_clear" map to format choice?
- What if debrief says "pace too fast"? → What changes in next script?

---

## V. CONNECTIONS THAT NEED TO BE EXPLICIT

### 1. Debrief Patterns → Format Selection
Currently implied, should be explicit:

```
If "pace: too_fast" → Next episode uses Narrative-driven (narrator controls pacing)
If "clarity: struggled" → Next episode uses Interview-style (fewer speakers, clear Q&A)
If "stuck_word: [word]" → Word is added to STRUGGLED list OR new scene uses it in different context
```

### 2. Scene Design ↔ Word Weaving
Currently disconnected:

```
Director says: "Market scene, Andrew buys vegetables"
Architect gets: Word payload (தேடு, வாங்கு, விலை, etc.)
Problem: Architect doesn't know whether the scene naturally supports these words
Better: Director brief includes "Scene naturally supports [verb cluster]" or rejects scene as poor fit
```

### 3. Format → Dialogue Structure
Currently vague:

```
Intercept-only: Dialogue-heavy, minimal narration, rapid exchanges
Narrative-driven: Narrator sets context, dialogue supports observation
Interview-style: Q&A structure, one interviewer, multiple respondents
```

Currently, Architect gets "Format: narrative-driven" but no guidance on what that means structurally.

---

## VI. RECOMMENDED CHANGES

### Immediate (High Impact, Low Effort):

1. **Clarify Episode Length Target**
   - Replace "8-10 min" with "**4-5 min target**" across all protocols
   - Note: This includes Intercept + any breakdown/analysis

2. **Add Format Selection Decision Tree**
   - Create `protocol/format_selection.md` with explicit mappings:
     - Debrief pattern → format choice
     - Example: "clarity: struggled with speed" → Narrative-driven (narrator paces)

3. **Create Producer Gate in Protocol**
   - Add Step 3.5 to @tutor: "Before audio generation, Producer audits script"
   - Make it explicit when Producer can fix vs. when to escalate

4. **Add Word Weaving Checklist to Architect Role**
   - Every NEW word must appear 2-3x in natural context
   - STRUGGLED words optional, never forced
   - No glossing unless absolutely necessary

---

### Medium (Higher Effort, More Clarity):

5. **Separate Scene Design from Word Payload**
   - Director creates two documents:
     - `content/beats/tierX_missionY_scene.md` (narrative setup, characters, conflict, tone)
     - `content/beats/tierX_missionY_words.md` (payload: NEW/USE/STRUGGLED, word frequency targets)

6. **Format-Specific Architect Guidance**
   - Create `protocol/formats/intercept_only.md` (dialogue structure, narrator ratio)
   - Create `protocol/formats/narrative_driven.md` (pacing, narrator voice, scene observation)
   - Create `protocol/formats/interview_style.md` (Q&A structure, question types, response patterns)

7. **Listenability Checklist for Director**
   - Before approving a brief:
     - Does the scene have a clear problem or tension?
     - Would someone without learning goals find this interesting?
     - Is there a reason these characters are speaking (not just a vocab dump)?

---

### Later (Refinement):

8. **Explicit Register Model**
   - Document Mission 31 as the "Register Gold Standard"
   - Include 3-4 examples of colloquial Tamil from M31 as reference
   - Architect + Producer compare against these

9. **Debrief Data Feedback Loop**
   - Track debrief patterns over time (e.g., "struggled with pace" 3x in a row)
   - Trigger protocol adjustment (e.g., "Switch to Narrative-driven for next 2 missions")

---

## VII. PROPOSED NEW PROMPT HIERARCHY

### For the Director:
```
1. Read last debrief data
2. Choose format based on debrief patterns
3. Design scene with **clear tension/stakes** (not just vocab opportunity)
4. List NEW/USE/STRUGGLED words and note where each should appear
5. Present brief + listenability reasoning
6. Wait for approval
```

### For the Architect:
```
1. Read Director brief (scene, format, words)
2. Follow format-specific guidance (dialogue ratio, narrator voice, etc.)
3. Draft script ensuring:
   - Each NEW word appears 2-3x in natural context
   - Coimbatore Tamil (use M31 as reference)
   - Clear dramatic arc (problem → resolution or observation)
4. Pass to Producer
```

### For the Producer:
```
1. Receive Architect script
2. Audit register: Does it sound like a Coimbatore native talking?
3. Audit formatting: Tamil script integrity, no gibberish, clean speaker tags
4. Fix issues OR escalate if substantial rewrite needed
5. Approve for TTS rendering
```

---

## VIII. SUMMARY

**Strengths:**
- Clear philosophy and core constraints
- Role structure exists
- Debrief system is now lightweight

**Weaknesses:**
- Format rotation underspecified
- Word weaving rules not enforced
- Register audit is optional/informal
- Episode length target is unclear
- No Producer gate in protocol
- Scene design mixed with word payload

**Quick Fixes:**
1. Reduce episode length target to 4-5 min
2. Add format selection decision tree
3. Make Producer gate explicit in @tutor protocol
4. Add word weaving checklist to Architect role

**Larger Improvements:**
- Separate scene design from word payload
- Create format-specific guidance docs
- Document register model (reference M31)
- Add listenability checklist

---

## IX. NEXT STEP FOR MISSION 33

**Given current fragility with long Tamil narrative:**

Option A: Provide a **very tight, format-specific brief** that specifies:
- Target duration: **4-5 minutes**
- Format: **Intercept-only** (dialogue-heavy, minimal narration)
- Scene: Market morning, 2-3 speakers only, single location
- Word structure: 2-3 NEW words that appear 2-3x each in natural dialogue
- Register model: Use Mission 31 (tea stall) as reference for tone/pacing

Option B: Have another model (Opus/Gemini) write the script, then I do the protocol review.

Which would be more useful to proceed?
