# Mission Rotation Engine (Intel Narrative Styles)

**Purpose:** Maintain engagement by rotating the *narrative lens* per mission. Every mission contains an **Intercept** (Raw Feed) and a **Breakdown** (Analysis), but the scenario type changes.

## The Narrative Rotation

The Director selects the style based on the current `current_location` and the next semantic word chunk.

| Order | Style | Focus |
|:---|:---|:---|
| **1** | **The Eavesdrop** | Listening to a public conversation (Market, Station). High noun density, directional verbs. |
| **2** | **The Heated Dispute** | High-stakes conflict (An argument with a driver, a family dispute). Verb tenses and attitude particles. |
| **3** | **The Surveillance** | Monitoring a phone call or a private meeting. Focus on "Say/Ask" matrices and reported speech. |
| **4** | **The Transaction** | A pure commerce scenario (Buying, Bribing, Negotiating). Numbers and object manipulation verbs. |
| **5** | **The Field Test** | A culmination where the "Breakdown" prepares the learner to perform a specific action in the story. |

## The Weaving Protocol (CRITICAL)

The Director must pull 8-12 semantic target words (The Payload) from the current Tier JSON.
- **TEACH (The Keys)**: 3-5 critical structural words that "unlock" the meaning of the Intercept.
- **EXPOSE (The Signal)**: 5-8 contextually relevant words that appear in the Intercept but are only briefly mentioned in the Breakdown. (See Wire Rule in `roles/director.md`.)
- **USE**: Use `mastered_words` ambiently in the Intercept without translation.
- **CALLBACK**: Weave in 2-3 `struggled_words` into the transition banter.

### CALLBACK Rule: Thematic Embedding (No Naked Drills)

Do NOT surface CALLBACK words as explicit drills ("Now let's revisit the word for 'under'..."). Instead, **embed them through actions native to the scene's logic.** The word should appear multiple times because the *scene requires it*, not because it's being practiced.

- Spatial/prepositional struggled words (`கீழ`, `முன்னாடி`, `மேல`, `உள்ள`, etc.) belong in stage movement, location disputes, and object placement — a porter describing where a bag is, a character scanning a crowd.
- Temporal struggled words (`முதல்ல`, `அப்புறம்`, etc.) belong in the natural sequencing of events in the narrative.

The learner should encounter the word 2-3 times through the scene's own logic before the Breakdown ever names it.

## The Dual-Track Standard

- **The Intercept:** 1.5 - 2.5 minutes (~250-350 words). Pure Tamil/Thanglish.
- **The Breakdown:** 8 - 10 minutes (~1,200-1,500 words). Structured analysis.
- **Script Naming:** 
  - `content/scripts/tier{N}_mission{M}_intercept.md`
  - `content/scripts/tier{N}_mission{M}_breakdown.md`
