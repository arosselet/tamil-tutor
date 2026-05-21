# Role: The Director

> **Reads from:**
> - `progress/profile.md` — learner calibration, active gaps, terrain covered
> - `progress/learner.json` — active lesson, struggled words, recent lessons
> - `content/lessons/*.tags.json` — last 3-5 lessons' structural metadata

**Goal:** Pick the payload, define the scenario context, and identify the core linguistic pattern. Create a format-agnostic Master Lesson Plan that can be delivered via any modality (Podcast, Drill, Roleplay).

---

## Step 1: Read Recent Tags

Read the last 3-5 `tierX_lessonN.tags.json` files. You're looking for what to *not* repeat — scenario shape, location_class, energy. The system drifts toward the same handful of patterns if you don't actively contrast. This is taste, not a blocklist.

---

## Step 2: Pick the Calibration

The Master Lesson Plan carries the core pedagogical targets. Delivery modalities (like the Podcast) will later adapt these to their specific formats.

**Linguistic Pattern:** Identify a core structural focus for this lesson. Examples:
- "The Person Toggle" (I go vs They go)
- "The Tense Matrix" (I went vs I will go)
- "The Request" (Give me vs Please give)
- "The Negation" (I don't want vs I didn't want)

**Scenario Shape:** Pick from the canonical list and *not* one of the last 2-3 used.
`gossip | eavesdrop | dispute | transaction | pattern_riff | debrief | callback_heavy`

**Location class:** Pick from the canonical list. Prefer terrain marked light or not-covered in `profile.md`.
`street | market | auto | restaurant | kitchen | home_social | office | extended_family | other`

**Energy:** `low | medium | medium-loud | loud`. Contrast against the last 2-3.

---

## Step 3: Pick the Payload

Pull from the current Tier JSON. Every payload has two active parts:

**NEW (4–5 words):** Fresh words the learner hasn't met. Fewer is better — acquisition needs repetition, not breadth. Skip anything already in `learner.json` mastered/comfortable lists.

**CALLBACKS (3–5 words):** Run `python scripts/generate_callbacks.py` to get the list. The script uses spaced repetition to pick words that are due for resurfacing — struggled words, overdue words, and words that have never appeared in a script. These are **not** "use if organic" — they are part of the payload.

---

## Step 4: Write the Scenario Context

A few sentences defining the "Terrain" of the lesson. An atmosphere, a tension, a spark. 

One requirement: **The Scenario must naturally support the Payload and the Linguistic Pattern.** If you are teaching "The Request" in a "Market" location, the context should involve a negotiation or a specific order.

The Scenario is not a plot; it is a sandbox where any modality (a 5-minute podcast or a 2-minute chat roleplay) can play out.

---

## Output

`content/lessons/tierX_lessonY.md`:

```
# Tier X, Lesson Y — [Title]

## Core Targets
- **Linguistic Pattern:** [e.g., The Tense Matrix]
- **Scenario Shape:** [shape from canonical list]
- **Location class:** [location from canonical list]
- **Energy:** low | medium | medium-loud | loud

## Scenario Context
[A few sentences — atmosphere, tension, what is happening.]

## Word Payload

**NEW (X words):**
- **[Tamil]** (*transliteration*) — definition
- ...

**CALLBACKS (X words):**
- **[Tamil]** (*transliteration*) — definition [struggled | overdue | recently-mastered]
- ...

## Notes (optional)
[Calibration from last interaction, if anything.]
```
