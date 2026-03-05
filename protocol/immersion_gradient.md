# The Immersion Gradient

## Principle: Teach New, Use Known

As the learner acquires vocabulary, the lessons must **compound**. Words that have been learned stop being taught and start being *used* — in drills, in scene-setting, in character speech — without translation. The learner's brain must shift from "recall on demand" to "parse in real-time."

## The Three Word Modes

Every word the learner has encountered falls into one of three modes. These are derived from `progress/learner.json`.

| Mode | Source | Writer Behavior |
|---|---|---|
| **TEACH** | Current episode's `target_vocab` | Full introduction: English meaning → Tamil word → drill repetition |
| **USE** | `comfortable_words` + `mastered_words` | Used freely in Tamil **without translation** — in character lines, transitions, scene-setting. Never gloss them. |
| **CALLBACK** | `struggled_words` | Quick Tamil drop into a sentence, beat for the learner to process. Brief reminder if needed, then move on. No full re-teach. |

### Rules

1. **TEACH** words get the full treatment: context, meaning, repetition, drilling.
2. **USE** words appear naturally — scene-setting, praise, transitions. Never translate them. If the script says "சரி, let's move on" there is no "(Okay, let's move on)."
3. **CALLBACK** words get a quick challenge. Drop them into a sentence, give the learner a beat to process. One-line reminder if they struggle, then move on.

---

## The Gradient: Tamil % by Tier and Episode Type

Two thresholds per tier — one for the **Intercept** (scene/dialogue), one for the **Instruction** (breakdown/analysis).

| Tier | Focus | Intercept (Tamil %) | Instruction (Tamil %) |
|---|---|---|---|
| **Tier 1** | Survival | 30% | 10% |
| **Tier 2** | Comfort | 60% | 20% |
| **Tier 3** | Embedded | 85% | 50% |

**Intercept** = the scene. Characters speak as they naturally would. Tamil carries commands, emotion, and local flavour; English fills logistics and filler. As the tier rises, English filler disappears.

**Instruction** = the breakdown/analysis. The writer explains, frames, and teaches. Tamil appears only in quotes, drills, and call-and-response beats. Kept low deliberately — the learner's brain is working hard enough decoding the Intercept.

> **These are targets, not word counts.** Read the draft aloud. If it feels too heavy to follow, pull back the Tamil. If it feels too easy, push it.

---

## The Word Status Sheet

Before writing a Beat Sheet, the Director generates a **Word Status Sheet** — a quick-reference categorization of the learner's vocabulary.

### How to Generate It

1. Read `progress/learner.json`
2. Read `curriculum/tiers/tier_X.json` for the target mission
3. Categorize:

```
=== WORD STATUS SHEET: Tier X, Mission Y ===

TEACH (new this episode):
  - அதுக்கு அப்புறம் → After that
  - முன்னாடி → Before
  - ...

USE (comfortable — use freely, no translation):
  - சரி, ஆமா, இல்ல, வணக்கம், இருக்கு, போதும், ...
  - எனக்கு, உனக்கு, கொஞ்சம், நிறைய, ...
  - சாப்பிட்டேன், குடிச்சேன், தூங்கினேன், ...

CALLBACK (struggled — quick challenge, no re-teach):
  - அஞ்சு, கம்மி, கிட்ட, ...
```

4. Attach this sheet to the top of the Beat Sheet as a reference for the Architect.

---

## Application Examples (Tier 2)

**Intercept — Thanglish code-switching (60% Tamil target):**
- Character says "அண்ணா, idhu எவ்ளோ?" not "How much does this cost?"
- Commands and reactions in Tamil: "எடு", "வை", "சரி சரி".
- Logistics and filler in English: "Let me check", "Wait, I think..."

**Instruction — English-led with Tamil anchors (20% Tamil target):**
- Transitions: "சரி, next word." / "செம்ம! Now let's try something harder."
- Drills: "Say it. முடியாது. One more time — முடியாது."
- Replays quote the Intercept verbatim in Tamil; analysis wraps it in English.

### What NOT to Do

- ❌ Glossing a USE word mid-script: "சரி (which means 'okay')" — just say it and move on.
- ❌ Dropping Tamil entirely in the Intercept because the scene is complex — that's the point.
- ❌ Heavy Tamil in the Instruction section — the learner is already cognitively loaded from the Intercept.
