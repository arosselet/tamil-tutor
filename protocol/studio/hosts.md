# Protocol: Cast & Voices

> **Read by:** `protocol/studio/architect.md`, `protocol/studio/producer.md`, `protocol/studio/director.md`
> **Defines:** All speaking roles across every episode.
> **Language-specific:** The names Maya and Raj and the Coimbatore identity are Tamil-specific. Swap this file when teaching a different language.

Two episode segments. Four voices. Each segment has its own pair.

---

## The Intercept — the household (2026-09-19)

**The Intercept is performed by the household cast.** `content/household.md` is
the canon: who they are, how each one talks, and the TTS voice pinned to each.
The learner is an observer of their world, never an addressee.

**Tagging convention:** the character's name plus a gender marker —
`**Paati (F):**`, `**Karthi (M):**`. The gender tag is always present; the
renderer requires it.

**Do not write a Voice Map.** Python reads the pins out of the canon and injects
the block itself (`scripts/household.py`). A voice table retyped each episode is
a table that drifts, and the ear tracks a *speaker* before it tracks a word.

**The register differences are the teaching instrument**, and they live in the
canon rather than here: Paati's older Kongu forms, Mama's terseness, Athai's
speed, Karthi swallowing every ending. Two characters who sound interchangeable
is a defect.

**What retired here, and why.** This file used to specify two unnamed hosts and
the rule *"This is not theater with a cast — it is two hosts who act bits out."*
That rule, and the 2026-06-20 / 06-28 decisions behind it, were guarding against
invented stakes and a plot the learner is asked to care about. The guard was
right; its premise was that *"the one true narrative is my own progress"*, which
held only while the trip was the story. What replaces it is a **world, not an
arc** — a fixed cast and geography where things happen and nothing resolves. The
variety half of 06-20 is untouched: the divergence gate still governs every
episode.

---

## The Breakdown Analysts

Two named analysts who appear in every Breakdown segment — and who **lead the `lore` form end-to-end** (their deep-dive *is* the episode: a payload word's history, kinship, myth, culture). In a Breakdown they talk **to each other** about the Intercept they just heard — playing back snippets, joking about the characters' decisions, unpacking the NEW words in context. Think NotebookLM deep-dives.

- **Analyst Maya (F):** Sharp, pattern-focused. Loves the "why" behind the language. Finds structure and rule-patterns satisfying.
- **Analyst Raj (M):** Warmer, story-focused. Obsessed with Coimbatore local flavor. Connects language to place and people.

**Tagging convention:** `**Analyst Maya (F):**` and `**Analyst Raj (M):**`

---

## The Drama Cast (`narrated_drama` only)

One **Narrator** plus up to 2–3 in-scene character voices, every line gender-tagged like
all cast. The Narrator speaks English scaffolding in second person, present tense — and
his "you" addresses the **protagonist inside the story**, never the listener: "you
squint at the screen" is in-world narration; "you learned this last week" is a
fourth-wall break and a send-back. The Tamil-script-only rule binds the Narrator's
embedded Tamil with no exception.

---

## Rules That Apply to All Four Voices

- **Fourth wall stays up.** No "you," no addressing the listener, no meta-narration about the learner's state or activity. The podcast exists in its own world. **Canonical here** — this is a production-only rule; the constitution deliberately excludes it (it doesn't govern Anna's chat).
- **Tamil script only.** No English phonetics (e.g., "Vanakkam"). Every Tamil word in Tamil script in every context. **Canonical here** — production-only, same as above (Anna's chat is phonetic by design).
- **Gender tag on every speaker line.** `(F)` or `(M)` always present — required by the TTS renderer.
