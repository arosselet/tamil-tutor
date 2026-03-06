# Mission Rotation Engine (Intel Narrative Styles)

**Purpose:** Maintain engagement by rotating the *narrative lens* per mission. Every mission contains an **Intercept** (Raw Feed) and a **Breakdown** (Analysis), but the scenario type changes.

## The Narrative Rotation

The Director selects the style based on the current `current_location` and the next semantic word chunk. The intel/spy framing is one *available* lens, not the mandatory lens. Any style below can be framed in its natural genre — domestic comedy, street chaos, family drama — if the scenario carries its own dramatic weight.

| Order | Style | Focus |
|:---|:---|:---|
| **1** | **The Eavesdrop** | Listening to a public conversation (Market, Station). High noun density, directional verbs. |
| **2** | **The Heated Dispute** | High-stakes conflict (An argument with a driver, a family dispute). Verb tenses and attitude particles. |
| **3** | **The Surveillance** | Monitoring a phone call or a private meeting. Focus on "Say/Ask" matrices and reported speech. |
| **4** | **The Transaction** | A pure commerce scenario (Buying, Bribing, Negotiating). Numbers and object manipulation verbs. |
| **5** | **The Field Test** | A culmination where the "Breakdown" prepares the learner to perform a specific action in the story. |

## The Weaving Protocol (CRITICAL)

The Director must pull 10-15 semantic target words (The Payload) from the current Tier JSON.
- **TEACH (The Keys)**: 2-3 critical structural words that "unlock" the meaning of the Intercept.
- **EXPOSE (The Signal)**: 8-12 contextually relevant words that appear in the Intercept but are only briefly mentioned in the Breakdown. (See Wire Rule in `roles/director.md`.)
- **USE**: Use `mastered_words` ambiently in the Intercept without translation.
- **CALLBACK**: Weave in 2-3 `struggled_words` into the transition banter.

### CALLBACK Rule: Thematic Embedding (No Naked Drills)

Do NOT surface CALLBACK words as explicit drills ("Now let's revisit the word for 'under'..."). Instead, **embed them through actions native to the scene's logic.** The word should appear multiple times because the *scene requires it*, not because it's being practiced.

- Spatial/prepositional struggled words (`கீழ`, `முன்னாடி`, `மேல`, `உள்ள`, etc.) belong in stage movement, location disputes, and object placement — a porter describing where a bag is, a character scanning a crowd.
- Temporal struggled words (`முதல்ல`, `அப்புறம்`, etc.) belong in the natural sequencing of events in the narrative.

The learner should encounter the word 2-3 times through the scene's own logic before the Breakdown ever names it.

## The Dual-Track Standard

- **The Intercept:** 3 - 5 minutes (~500-750 words). Pure Tamil/Thanglish. Long enough to get lost in, loop, and discover on relisten. Should have a beginning, middle, and end.
- **The Breakdown:** 6 - 8 minutes (~900-1,200 words). Reaction-style analysis.
- **Script Naming:** 
  - `content/scripts/tier{N}_mission{M}_intercept.md`
  - `content/scripts/tier{N}_mission{M}_breakdown.md`
