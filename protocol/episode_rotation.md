# Episode Rotation Engine (Rolling Style Rotation)

**Purpose:** Prevent fatigue by rotating the *delivery style* per episode while covering the **same** target vocabulary from the current level. Every episode features all target words, but the pedagogical angle changes.

## The Rolling Rotation

Instead of being tied to specific days, the rotation follows a fixed sequence. When a new episode is generated, the Director selects the next style in the sequence.

| Order | Style | Focus |
|:---|:---|:---|
| **1** | **The Narrative (The Story)** | A cohesive "Boss Fight" story. High immersion, sensory-rich, low-frequency drilling. |
| **2** | **The Mechanics (The Drill)** | High-frequency "Workout." Rapid-fire repetition, phonetic spotlights, "Toggle" training. |
| **3** | **The Cultural Deep-Dive** | Explaining *why* we say things. Social etiquette, "Kongu" vs. "Formal" comparisons, slang context. |
| **4** | **The Remix (Cumulative)** | Interleaving *this* level's words with "Zingers" and "Glue" from previous levels. |
| **5** | **The Speed-Dating** | 10-12 short, 1-minute situational vignettes (ATM, ordering coffee, calling an auto). |

## How It Maps to Levels

Each level contains multiple episodes (typically 10-20). The rotation determines the **style** of each episode, not the vocabulary. The Director assigns the style when creating the Beat Sheet by looking at the previous episode's style.

## The Weaving Protocol (CRITICAL)

The Director and Architect must weave vocabulary status into the assigned style:
- **TEACH**: Introduce `target_vocab` naturally within the style (e.g., as part of a Speed-Dating vignette).
- **USE**: Use `comfortable_words` ambiently in Tamil scripts without translation.
- **CALLBACK**: Insert `struggled_words` into low-stakes moments to keep them fresh.

## The 15-Minute Volume Rule

- **Target Length:** 2,000-2,500 words per script.
- **Target Audio:** ~15 minutes.
- **The Rule of Threes:** Generate in 3 Acts of ~5 minutes each to prevent LLM drift, then stitch.

## Episode Naming

`content/scripts/level{N}_ep{M}.md` where N = level number, M = episode number within that level.
