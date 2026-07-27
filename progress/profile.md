# Learner Profile: Andrew

> **Maintained by:** Anna, rewritten (not appended) every ~5 sessions.
> **Read by:** `protocol/studio/director.md` and `protocol/daily_session.md` before picking targets.
> **Purpose:** A teacher's living *judgment* of Andrew — not counts. The hard numbers (recognition buckets, production axis, viability floor) live in `progress/lexicon.json`; read them with `python scripts/sync_state.py status`. This file says what they *mean* and where to point next.
>
> **Last updated:** 2026-07-13

---

## The Goal

**Clear the viability floor in Coimbatore Tamil — production as the accelerant.** Andrew has soaked in a recognition base (~100 word families by his own estimate) but plateaued: he recognizes the sounds yet freezes when it's his turn to speak. The breakthrough is *forced output* — converting soaked recognition into reflex so he stops being a deer in headlights. Near-term marker: **the India trip (week of 2026-08-12)** — respond without freezing in casual family exchanges; the Trip Sprint below is the concrete form of this.

**Phase model:** Phase 1 (the base) — *narrow and deepen*: force cold production of words he already recognizes; resist widening vocabulary. **Phase 1.5 (NOW — the Trip Sprint, see below)** interrupts the floor climb until the trip. Phase 2 (post-floor) — native media (films) becomes the vocabulary engine, because the floor finally makes acquisition-from-context work.

---

## Phase 1.5 — The Trip Sprint (ACTIVE — overrides the floor climb)

**Deadline:** Andrew is in India the **week of 2026-08-12** (~6 weeks out as of 2026-06-30). This is the first time the goal has a face and a date: don't freeze when his mother-in-law speaks to him across the table; catch the drift of family gossip; survive public/transaction settings. The countdown is motivation — but Anna narrates the **campaign's denominators** ("ask-machine week: 7 of 12"), never the global need-per-day deficit; the burn rate is an engineering number on the status line, not session narration (2026-07-17).

**The pivot:** pause the abstract "800-lemma" climb. Deepen a **finite, visible Trip Deck** of survival phrases instead. Andrew already has food / kitchen / domestic; the glue to accelerate is the *social-public* register.

- **The survival tier is the headline meter (2026-07-18 — refines 07-13; the narrated number must be winnable).** ~80 chunks/frames tagged `deck:"trip"` in `lexicon.json`; `sync_state.py status` and `suggest_targets.py` surface it first. During the sprint Anna reports **X/N survival cold** as the number that matters — the tier that decides freezing at the table, at a pace (~1.1/day) his actual trailing pace can win. The full deck stays in rotation and on the status line; delight is the lane he graduates into (and celebrates) as survival clears. The viability floor is secondary (and will dip as deck entries land recognized-not-cold; that's expected, not regression).
- **Phrases are first-class.** The unit of the deck is the *chunk* (fixed formulaic phrase deployed whole — `saapta?`, `paravaayilla`, `enna aachu`) and the *frame* (a slot template — `___ venum`, `___ enga?`, `enna ___ panren` — an Engine). Not isolated words. This is the constitution's "Glue Over Vocabulary" / "Pattern Over List" finally made the curriculum spine.
- **Fire vs. catch (2026-07-01 redesign).** Every deck item carries a `direction`: **fire** (force to cold production) or **catch** (ear-only — the win is solid recognition via eavesdrop drills and soak; *never* force these to fire). The gossip register is mostly catch: the decoders `frame:quote-nu` (…-னு சொன்னாங்க, reported speech) and `frame:hearsay-aam` (…-ஆம், hearsay) are the comprehension unlock for overheard family talk. The meter reads both sides: `X/N fire cold · Y/M catch solid`.
- **The touchdown bar — two tiers, Andrew's own (2026-07-13; supersedes the 07-09 "no tiering" call and the older respond-first order — re-decided at trailing pace 0.4/day, 30 days out).** Production stays the north star; these tiers say what gets forced *first* and what must be true at touchdown — ordering only, nothing leaves the deck. **(1) Survival** — someone walks up speaking fast: follow it, or repair it, and get his own wants/needs across. The antifreeze kit (a fired `konjam medhuva sollunga` is a PASS — freezing is the only fail), the public/transactional chunks (he pays **cash**, accompanied 9/10 times), and the frames (each engine online is fifty sentences never memorized). **(2) Delight** — the sisters-in-law seeing how much he's trying: the faq interrogation script (his facts: one-month stay, software work, lives in Canada), mil-table (`romba nallarukku` is THE melt line), social greetings. **Dessert** — zingers (1–2 land the reveal; five is greed) and the gossip registers (the eavesdrop knock channel owns catch; in-session it's soak, never the headline). `suggest_targets.py` orders the ticket and the volley menu by these tiers.
- **Respond-under-speed is a session move, not a new meter.** The survival tier's real test is *directed* fast speech — an instruction or question fired AT him, which is a different skill from overheard-gossip drift. Drill it as mask-work at full speed: one in-register line at Andrew; win = act/answer, OR fire a repair line from the antifreeze kit. Repair counts as a pass out loud, every time — that reflex IS the not-deer-in-headlights goal.
- **The lunch anchor (2026-07-13, Andrew's commitment).** The daily terminal session (the 07-11 mandate) now has a home: his workday lunch break, wherever it lands that day. Knock policy tees it up late morning (trailer / session bell) and saves collection asks for after the session's slot.
- **Engines are the daily non-negotiable.** Every session forces **two novel instantiations of one frame** before/inside scene work — one frame online beats five chunks memorized. `frame:polite-nga` (verb+ங்க) and `frame:we-om` ({I-form}+ஓம் — the trip is a "we" trip) collapse already-known forms into machines; log with `--produced-cold 'frame:…'` only on a *novel* slot-fill.
- **Competent > local, for THIS sprint.** Optimize clear, correct, understood-and-understanding Tamil over hyper-local Kongu markers. Standard Coimbatore-colloquial is the target register; don't reach for native-mimicry flourishes to "pass as a local" — that heist is the long game (`persona.md`), not the trip goal. Andrew would rather be *competent* in a month than sound native.
- **Target registers for the deck:** mother-in-law table-talk and deference; overheard family gossip (comprehension-first — catch it, needn't produce it); public survival (auto/shop/directions/transactions); and a couple of warm zingers to delight the in-laws.
- **Register default (Oracle-confirmed 2026-07-02):** **neenga/-nga for everyone, including younger relatives.** Nee is reserved for very close friends, close cousins, and siblings only. When in doubt, -nga — the safe register is also the correct one in this family. (Masks and scenes should reflect this: the "cousin banter" nee-register applies only to genuinely close cousins.)
- **Sourcing:** Anna drafts the deck into `curriculum/trip_deck.json`; the Oracle (wife) does 60-second vibe-checks; `python scripts/sync_state.py seed-deck curriculum/trip_deck.json` lands the vetted set. Re-runnable as it grows.
- **After the trip:** clear the sprint — the deck entries become ordinary vocabulary and the floor climb (Phase 1 → 2) resumes. Revert this section then.

---

## The Campaign — This Week

> **Contract:** `protocol/daily_session.md` → "The Campaign". Anna writes it at close; Andrew overrides at will. One block, five lines — the ticket owns *which* items.

**🎯 The Auto Ride Week** (written 2026-07-26). Through-line: **the `public` register is one scene, not six phrases** — a whole transaction with a stranger, curb to change (நேரா போங்க → இங்க நிறுத்துங்க → எவ்ளோ ஆகும்? → ரொம்ப அதிகம் → சில்லறை இருக்கா?). The antifreeze kit rides *inside* the ride: a moving auto is exactly where கொஞ்சம் மெதுவா சொல்லுங்க and என்ன சொன்னீங்க? earn their keep. Catch stays ambient in the tapes, never a second headline — `frame:youknow-la` is still uncaught and still load-bearing. The trailer pitches the fare haggle.

**Standing catch order (renewable):** one word overheard off the sisters.

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
- **Minimal pair: நாள் (naal, day) vs. நாலு (naalu, four)** — live confusion on the phone (2026-07-04, answering the how-long-staying question). Worth one lore-flavored contrast beat + fresh-context fires of both ("naalu vaaram" / "oru maasam" both valid duration answers; never graded against one fixed phrasing).
- **Give-me vs. want (giveme-noun frame) — 2026-07-15.** Andrew's mouth defaults to வேணும் (*announce a need*, points at self) where the family move is குடுங்க (*ask them to pass it*, points at them). At a family table the softer குடுங்க wins. kudunga is still fresh in his ear; keep resurfacing it in fresh table contexts until it fires cold without the venum detour. Don't chase it in one session.
- **The floor gap broadly:** the recognized-but-not-cold pool. These don't need re-teaching — they need to be *fired*, cold, from English, in new situations.

---

## What's Needed Next

> **During the Trip Sprint (Phase 1.5), the Trip Deck is the priority set** — its curated social-public chunks/frames override the "priority-1 floor only" guidance below, which resumes after the trip. The *deepen, don't widen* discipline still holds *within* the deck: force its members cold, don't sprawl past it.

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

## Session Conduct — Andrew's Stated Preferences

Learner-specific preferences for how Anna runs the live session. These live here (not in any agent's local memory) so every agent and device applies them identically.

- **Meta is curriculum; weave Tamil freely (2026-07-15, Andrew's words).** The exploratory/meta thread — *why that ending, where a word comes from, why Google Translate chokes on it* — is "as important to my journey as the subject at hand… so I can explore, not just checklist." Let Tamil live throughout the whole conversation (sign-offs, asides, mutters), and treat *anything* Anna drops as fair game for Andrew to stop and poke at — that poking **is** the lesson, never a detour from "real work." Do **not** frame Anna's own Tamil as a "slip" he "caught" — it's the persona, not an error. Use the dictionary-vs-living-register gap as a feature: colloquial Kongu (completive tails *poidu/poachu*, clitics, dropped endings) is exactly what machine translators mangle — reframe that as proof he's learning the real spoken register, with Anna as the Kongu dictionary. This is the constitution's "tangent is a tool" / "stories are curriculum" made a standing preference for Andrew.
- **Field missions must be organic (2026-07-15).** A mission that needs a *specific moment to show up* (e.g. the old "ok-na, book pannu" waiting on her to book flights) is weak — Andrew called it "a bit contrived." Half the time the moment never comes and the line dies unfired. Build missions that ride something guaranteed to happen within ~24h (the dinner offer of seconds, the auto ride, the "did you eat?" greeting), so there's always a slot to fire it. Shapes the knock/mission policy, not just one session.
- **Density low, lore high while the overwhelm signal holds (2026-07-24, his words).** He named *overwhelm* and *progress* in the same breath. Keep the dose small and the meta/lore thread rich until that changes — on 07-24 and again on 07-26, two fires plus one gossip tape produced more than any gauntlet had.

## Calibration Notes — explicit generation parameters

These are **hard dials**, read by the Director/Architect. They live here (not in any agent's memory) so every agent and device applies the same calibration — change the number, not a prompt.

- **Live coverage target: ~95%+ known words in the Intercept *as heard*** — the listening-comprehension floor (Nation's lexical-coverage research). Comprehension must hold live.
- **Gossip-tape carve-out (the ONE exception to 95%).** "Catch the drift" is a skill drilled on input Andrew *doesn't* fully understand: a clearly-marked eavesdrop segment (in-session eavesdrop drill, or a short tagged episode segment) may run native-speed with well below 95% coverage. The win condition is different — who/what/mood, not full comprehension — and it exists to train the deck's `catch` items (quote-னு, hearsay-ஆம், the maami's predictable lines). Everything else keeps the 95% rule.
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
