# The Immersion Gradient

## Principle: Teach New, Use Known

As the learner acquires vocabulary, the lessons must **compound**. Words that have been learned stop being taught and start being *used* — by the Host, in drills, in scene-setting — without translation. The learner's brain must shift from "recall on demand" to "parse in real-time."

## The Three Word Modes

Every word the learner has encountered falls into one of three modes. These are derived from `progress/learner.json`.

| Mode | Source | Host Behavior |
|---|---|---|
| **TEACH** | Current episode's `target_vocab` | Full introduction: English meaning → Tamil word → drill repetition |
| **USE** | `comfortable_words` + `mastered_words` | Used freely in Tamil **without translation**. The Host speaks them as if the learner already knows them. |
| **CALLBACK** | `struggled_words` | Quick Tamil prompt ("Do you remember this one?"), brief pause, then move on. No full re-teach. |

### Rules

1. **TEACH** words get the full treatment: context, meaning, repetition, drilling.
2. **USE** words appear naturally in Host lines — scene-setting, praise, instructions, transitions. Never translate them. If the Host says "சரி, let's move on" — there is no "(Okay, let's move on)."
3. **CALLBACK** words get a quick challenge. The Host drops them into a sentence and gives the learner a beat to process. If they struggle, a one-line reminder, then move on.

---

## The Gradient: Host Language Ratio by Tier

The Host's language shifts from mostly-English to mostly-Tamil as the learner progresses through tiers.

| Tier | Levels | Host Ratio | What It Feels Like |
|---|---|---|---|
| **Tier 1** | 1–3 (Survival) | ~90% English, 10% Tamil | English explanation with Tamil target words |
| **Tier 2** | 4–6 (Comfortable) | ~60% English, 40% Tamil | Bilingual conversation; known Tamil woven throughout |
| **Tier 3** | 7–9 (Embedded) | ~30% English, 70% Tamil | Tamil-dominant; English only for new concepts and complex explanations |

> **These are vibes, not metrics.** Don't count words. The ratio is a guide for tone and intention. At Tier 2, the Host *thinks* in English but *seasons* heavily with Tamil. At Tier 3, the Host *thinks* in Tamil and drops to English only when introducing something new.

---

## The Word Status Sheet

Before writing a Beat Sheet, the Director generates a **Word Status Sheet** — a quick-reference categorization of the learner's vocabulary.

### How to Generate It

1. Read `progress/learner.json`
2. Read `curriculum/levels.json` for the target episode
3. Categorize:

```
=== WORD STATUS SHEET: Level X, Episode Y ===

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

## Application Examples

### Tier 2 Host Lines (Level 4+)

**Transitions:**
- "சரி, next word."
- "செம்ம! Now let's try something harder."
- "நல்லா இருக்கு. But can you do it faster?"

**Scene-setting:**
- "நேத்து, you learned the consumption verbs. இன்னைக்கு, we connect them."
- "Imagine you வந்தேன் home. Wife asks என்ன பண்ணீங்க?"

**Praise / feedback:**
- "சூப்பர்!" (not "Super!")
- "ஆமா, exactly."
- "பரவாயில்லை, close enough."

**Instructions:**
- "சொல்லுங்க — say it."
- "இன்னொரு தடவை" (One more time — when the learner is ready for it)

### What NOT to Do

- ❌ "Very good. சரி means 'Okay'. Let's continue." — Re-teaching a USE word.
- ❌ Using Tamil the learner has never seen without context — that's confusion, not immersion.
- ❌ Dropping the gradient entirely because it's "easier" — the discomfort is the point.
