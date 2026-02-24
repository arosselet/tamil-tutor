# Mission Rotation Engine (Rolling Style Rotation)

**Purpose:** Prevent fatigue by rotating the *delivery style* per mission while covering the **same** target vocabulary from the current Tier bucket. Every mission features target words from the Tier, but the pedagogical angle changes.

## The Rolling Rotation

Instead of being tied to specific days, the rotation follows a fixed sequence. When a new mission is generated, the Director selects the next style in the sequence.

| Order | Style | Focus |
|:---|:---|:---|
| **1** | **The Narrative (The Story)** | A cohesive "Boss Fight" story. High immersion, sensory-rich, low-frequency drilling. |
| **2** | **The Mechanics (The Drill)** | High-frequency "Workout." Rapid-fire repetition, phonetic spotlights, "Toggle" training. |
| **3** | **The Cultural Deep-Dive** | Explaining *why* we say things. Social etiquette, "Kongu" vs. "Formal" comparisons, slang context. |
| **4** | **The Remix (Cumulative)** | Interleaving *this* level's words with "Zingers" and "Glue" from previous levels. |
| **5** | **The Speed-Dating** | 10-12 short, 1-minute situational vignettes (ATM, ordering coffee, calling an auto). |

## How It Maps to Tiers

Each Tier contains dozens of potential missions. The rotation determines the **style** of each mission, not the vocabulary. The Director assigns the style when creating the Beat Sheet by looking at the previous mission's style.

## The Weaving Protocol (CRITICAL)

The Director and Architect must weave vocabulary status into the assigned style:
- **TEACH**: Introduce `target_vocab` naturally within the style (e.g., as part of a Speed-Dating vignette).
- **USE**: Use `comfortable_words` ambiently in Tamil scripts without translation.
- **CALLBACK**: Insert `struggled_words` into low-stakes moments to keep them fresh.

## The 10-12 Minute Standard

- **Target Length:** 2,000-2,500 words per script.
- **Target Audio:** 10-12 minutes.
- **Storytelling Pacing:** Every episode must follow the "Slow Beats / Fast Explosions" model.
- **Word Refraction:** Every target word must appear in at least 3 distinct "Context Refractions" (Intro, Banter, Scenario).

## Mission Naming

`content/scripts/tier{N}_mission{M}.md` where N = tier number, M = cumulative mission number for that learner.
