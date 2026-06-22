# Learner Profile: Andrew

> **Maintained by:** Anna, rewritten (not appended) every ~5 sessions.
> **Read by:** `protocol/studio/director.md` and `protocol/daily_session.md` before picking targets.
> **Purpose:** A teacher's living *judgment* of Andrew — not counts. The hard numbers (recognition buckets, production axis, viability floor) live in `progress/lexicon.json`; read them with `python scripts/sync_state.py status`. This file says what they *mean* and where to point next.
>
> **Last updated:** 2026-06-21

---

## The Goal

**Clear the viability floor in Coimbatore Tamil — production as the accelerant.** Andrew has soaked in a recognition base (~100 word families by his own estimate) but plateaued: he recognizes the sounds yet freezes when it's his turn to speak. The breakthrough is *forced output* — converting soaked recognition into reflex so he stops being a deer in headlights. Near-term marker: by **[confirm target date]**, respond without freezing in casual family exchanges and clear the floor on the core glue + phrase set.

**Phase model:** Phase 1 (now) — *narrow and deepen*: force cold production of words he already recognizes; resist widening vocabulary. Phase 2 (post-floor) — native media (films) becomes the vocabulary engine, because the floor finally makes acquisition-from-context work.

---

## Current Position

The honest meter is the **viability floor** (`sync_state.py status`), not the recognition buckets — those were filled from passive exposure and over-count what Andrew can actually *fire*. Today a large majority of recognized words still don't fire cold; that gap **is** the work. Expect Anna's sessions to demote some over-counted "solid" words as they fail under cold recall — that's the meter getting honest, not regression.

- Consistent daily engagement; no completion anxiety. Low friction is non-negotiable (automation over manual steps).
- Can sound out தமிழ் script; basic decoding works.

---

## Strengths

- **Social and family vocabulary** is solid: directional words (அங்க, இங்க, வலது), family titles (மாமா, அக்கா, தங்கச்சி, அத்தை), pronouns and quantity words.
- **Discourse glue** is well-established: சரி, ஆனா, இல்ல, அதனால, கொஞ்சம் — the connective tissue of a sentence.
- **Comfortable with English-scaffolded (Thanglish) input; decodes Tamil script.** Comprehension is fragile to *unknown* words — needs ~95% known-word coverage live (see Calibration).

---

## Active Gaps

The production-reflex gaps that matter most right now:

- **High-frequency placement verbs:** வை (put/place) and தூக்கு (lift/carry) — recognition slow under speed, production shaky. Need natural repetition in fresh in-scene contexts, then cold dispatch.
- **Verb aspect (present vs. future):** கேட்குறேன் (I'm hearing/asking) vs. கேட்பேன் (I will hear/ask) — inconsistent under speed. Surface present/future contrasts in natural dialogue.
- **The floor gap broadly:** the recognized-but-not-cold pool. These don't need re-teaching — they need to be *fired*, cold, from English, in new situations.

---

## What's Needed Next

Phase 1 is *deepen, don't widen.* For the next stretch of sessions and episodes:

1. **Force production.** Keep converting recognized words to cold via cold dispatch — the chat session is the engine. This is the floor moving.
2. **Re-strain the same pool in fresh situations.** Deepening is not repetition: re-hearing a word is boring, being made to produce it somewhere new is not. One running story that carries the current payload across chat and audio (the soak handoff) is how a word earns a second, third, fourth life without feeling drilled.
3. **Reinforce the struggled items** (வை, தூக்கு, the present/future aspect contrast) in fresh contexts until they fire cold.
4. **Vary the scene *form*, not the curriculum.** Fight sameness by rotating shape / energy / location / episode form (the Director's `*.tags.json` machinery tracks this). Keep new vocabulary inside **priority-1** (the operational floor) and always embedded in a situation — never an expansion-cluster grab-bag. (New-word *counts* differ by modality — see Calibration.)

**Avoid:** reaching into **priority-2 expansion** clusters or new registers (news, journalistic) while the priority-1 floor still has gaps; and the over-trodden setting reflexes — another straight kitchen scene, another morning sprint.

**On the horizon (Phase 2, not now):** native Tamil media (YouTube, films) as the volume engine — but that on-ramp only works *after* the floor clears, so it's a reward to steer toward, not a current task.

---

## Coverage / Variety Note

Mechanical anti-sameness (scene shape, location, energy, episode form) is owned by the Director via the `content/scripts/*.tags.json` sidecars, which contrast each new episode against the last few. This file only flags the qualitative drift: recent episodes lean **domestic two-voice dialogue**, so bias the next few toward different *forms* (story / monologue-led, phone_call, vignette) to keep the ear fresh — while keeping the *vocabulary* narrow per the deepen thesis.

---

## Calibration Notes — explicit generation parameters

These are **hard dials**, read by the Director/Architect. They live here (not in any agent's memory) so every agent and device applies the same calibration — change the number, not a prompt.

- **Live coverage target: ~95%+ known words in the Intercept *as heard*** — the listening-comprehension floor (Nation's lexical-coverage research). Comprehension must hold live.
- **Density is an OUTPUT, never a target.** It falls out of (fence size × the 95% coverage target). With a small fence, episodes lean heavily on English scaffolding — correct, not watering down. Do not dial a Tamil ratio.
- **NEW word types: 4–5 (audio) / ≤1–2 (chat).** Each appears 2–3× in answering context. They are *seeds*, not taught to mastery — the chat fires them cold later. Chat is *production*, not soak.
- **Unfenced strangers (neither known nor payload): ≈0.** Hard cap 2, and only if the context answers them in the same beat. More is a Producer send-back.
- **Naturalness comes from register, not unknown words** — real spoken Kongu rhythm/idiom built from known vocabulary. Never reach for unknown words to sound "real."
- **Pacing:** one thought per line; ≥1 `[Pause]` per 6–8 Intercept lines; no run of >5 unbroken lines (the Listenability Gate — see `architect.md`).
- **Breakdown:** a Tamil-leaning second soak for colour, not a glossary.
- **Debrief:** casual, no quiz — ask how words are landing in his life.

---

## Receptive Growth Log

Monthly entries from the Receptive Check. One line per check: date, source, % caught without subtitles, brief observation.

_(pending — first check not yet logged)_
