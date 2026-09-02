# Protocol: Spoken Tamil — Coimbatore Dialect

> **Read by:** **every pass that can emit Tamil a voice will speak** — the knock lane
> (audio memos, eavesdrop tapes, fielding questions), the soak, drill and rotation sheets,
> both reply judges' voice replies, and `protocol/studio/producer.md`. The first six reach
> it through `writer.voice_canon()`, which is the single owner; the studio Producer reads it
> directly as part of its own canon. The Architect still does not read it — Producer rewrites
> Architect drafts to this register before TTS.
>
> **It reached only the studio until 2026-09-02**, because it was filed as studio craft —
> it lived at `protocol/studio/dialect.md`, and a repo-wide language law filed under one
> role's folder is how it acquired one reader. Moved to `protocol/` the same week. Six
> lanes carrying nearly all of Andrew's daily ear contact generated Tamil with no
> spoken-register law at all, and two native speakers reported the result — 2026-07-31 as
> "uncanny", 2026-09-01 as "book Tamil" that cost a native effort to follow. Neither report
> was a TTS problem. **If a new lane sends Tamil to a voice, it calls `voice_canon()`** —
> `smoke/render.py` fails the build if one of them stops.
>
> **Language-specific:** This file is Tamil/Coimbatore-specific. To teach a different language or dialect, replace this file. The roles that reference it do not change.

The test for every Tamil line: *Would a Coimbatore auto driver say this to his friend?* If it sounds like a textbook or a 1950s TV anchor, it needs work.

---

## Code-Switching Register

This is Coimbatore Tamil — not Chennai Tamil, not literary Tamil. English appears where a native would naturally reach for it: phone, office, tech, urban nouns, emphatic reactions. Not as scaffolding holding up isolated Tamil words.

- **Switching happens at clause boundaries**, driven by emotion or register shift, not by pedagogy. A full Tamil clause can stand on its own; an English clause can follow as a reaction or pivot.
- **No Tamil-root + English-suffix hybrids.** Forms like `தூக்கு-ing` or `திற-ed` do not exist in real speech. Use the conjugated Tamil form (`தூக்குறேன்`, `திறக்குறேன்`) — or restructure the line entirely.

---

## Verb Form Simplification

Spoken Tamil collapses verb endings. Written forms must become spoken forms.

| Written (literary) | Spoken (Coimbatore) |
|--------------------|---------------------|
| போகிறேன் | போறேன் |
| இருக்கிறார் | இருக்காரு / இருக்காங்க |
| செய்கிறோம் | பண்றோம் |
| வருகிறாயா? | வருவியா? / வர்றியா? |

---

## Word Fusion (Sandhi)

Tamil words fuse in fast speech. If a line reads like independently-pronounced dictionary words, it is written Tamil, not spoken.

- "என்ன ஆச்சு" → "என்னாச்சு"
- "அது என்ன" → "அதென்ன"

---

## Pronoun and Particle Elision

Spoken Tamil drops subject pronouns when the verb ending already carries the meaning.
- நான் போகிறேன் → போறேன்

Particles like `-ஐ` are frequently elided in natural flow.

---

## Discourse Markers

Real spoken Tamil has rhythm and filler. Repetition for emphasis is natural and signals a real person, not a script.

Common markers: ஆமா, சரி, இல்ல, பாரு, கேளு, தெரியுமா, சொல்லு

Repetition: "சரி சரி", "ஆமா ஆமா" — these are not errors, they are speech rhythm.

---

## The Kongu Layer

The `-nga` suffix, phonetic contractions specific to the Coimbatore/Kongu region, and regional expressions. The episode must sound like Coimbatore, not Chennai. Raj (see `protocol/studio/hosts.md`) is the reference ear for this layer — if he would not say it, it is not Kongu enough.
