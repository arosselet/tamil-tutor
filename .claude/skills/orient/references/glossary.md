# Project Glossary

Every jargon term a newcomer will hit in this repo, in alphabetical order.
Each entry: 1–2 line definition, plus the file where the term is canonically defined.

---

## Breakdown

The second half of a `classic` or `story` episode: Analyst Maya and Raj (in character, in Tamil) react to the Intercept — replaying one or two interesting beats, never inventorying the whole payload. Goal is **colour and a second soak**, not a glossary; a Breakdown that enumerates every new word has failed its brief. Omitted in `vignette` form.

Defined: `protocol/studio/architect.md` — "The Two-Voice Breakdown"

---

## callbacks

Words scheduled for spaced-repetition resurfacing. `scripts/generate_callbacks.py` computes what's due; `scripts/suggest_targets.py` folds them into the session ticket. Anna weaves them into the scene where they fit naturally — they are a soft target, not a quota.

Defined: `protocol/daily_session.md` — Targeting section; `docs/PROTOCOL_MAP.md` — Python brain

---

## cold (fire cold)

A word fires **cold** when the learner produces it from an English situation with no prompt, no warm-up, no multiple choice — instant recall, no hesitation. Cold production is the currency that moves the viability floor. Contrast: **hinted** (produced after a nudge) and **stuck** (demotes recognition one level). Anna logs these via `sync_state.py update --produced-cold / --produced-hinted / --stuck-word`.

Defined: `protocol/daily_session.md` — The Loop and Close & Log sections

---

## deck

A tagged sprint subset of `progress/lexicon.json`. During the Trip Sprint, ~65 chunks and frames are tagged `deck:"trip"`; `suggest_targets.py` surfaces them first and the session ticker reports **Trip Deck: X/N fire cold** as the headline meter. Each deck item carries a `direction` field: **fire** or **catch** (see those entries).

Defined: `docs/DECISIONS.md` — "Trip Sprint"; `progress/profile.md` — "Phase 1.5 — The Trip Sprint"

---

## dose

A self-contained learning unit — one knock memo, one episode, one push — that requires no prerequisite and carries its own complete rep. The learner should be able to engage with it in whatever gap they have without needing to recall the previous dose. Each dose is complete in itself; there is no listening-reconciliation ritual.

Defined: `docs/DECISIONS.md` — "Stop chasing listens (2026-06-30)"

---

## engines

Generative structural patterns — verb frames the learner internalizes as a machine, not a memorized line. Examples: the present/future toggle, the obligation frame, the can't-frame. An engine is **online** when the learner can fill a novel slot cold. "One engine online beats five chunks memorized." Logged with `--produced-cold 'frame:…'` only on a novel slot-fill, not a repeat.

Defined: `protocol/daily_session.md` — Targeting section ("Engines to fire"); `protocol/constitution.md` — "Pattern Over List (The Verb Engine)"

---

## field missions

A covert assignment Anna gives at the end of a session: one line, deployed at home tonight, unprompted — e.g., *"'suvaiya irukku' at dinner; debrief tomorrow."* The wife stays the unwitting audience, never the examiner. A line that survives live fire is the strongest cold-fire evidence the system has.

Defined: `protocol/persona.md` — "The Heist"

---

## fire / catch (axes)

Every deck item carries a `direction` field. **Fire** items target cold production — the learner must generate them under pressure. **Catch** items are ear-only — the win is solid recognition via eavesdrop drills and soak; these are never forced to fire. The meter reads both sides: `X/N fire cold · Y/M catch solid`.

Defined: `progress/profile.md` — "Fire vs. catch (2026-07-01 redesign)"; `docs/PROTOCOL_MAP.md` — `lexicon.json` row

---

## floor-gap

A word the learner recognizes (comfortable or solid) but cannot yet produce cold. Floor-gap targets are **what to force in a session** — they do not need re-teaching, they need cold dispatch in fresh English situations. The gap between recognition and production is the work.

Defined: `protocol/daily_session.md` — Targeting section ("Floor-gap targets")

---

## heist

The secret project: Andrew learning Coimbatore Tamil without his native-speaking wife knowing, culminating in a surprise reveal at a family gathering. The secrecy is structural — it is what makes the reveal land. Anna is the safe room where Andrew fails at zero stakes. The heist is never revealed to the wife by Anna; she stays the unwitting audience of field missions.

Defined: `protocol/persona.md` — "The Heist (the secret is the point)"

---

## Intercept

The main dialogue scene in a podcast episode — two Tamil speakers (Host A and Host B) in a real situation, carrying the payload words naturally. In `classic` form, the Intercept is followed by the Breakdown; in `vignette` form, the Intercept stands alone. In `lore` form, an optional short Intercept vignette opens as the specimen the analysts then dissect.

Defined: `protocol/studio/architect.md` — "The Episode Form" (the `classic` definition and `vignette` contrast)

---

## knock

The agentic phone-outreach system. `scripts/morning_knock.py` runs on a CI cron, checks the rails gate (waking hours, ≤5/day, ≥3 h apart), then Anna decides fire or silence and which modality — the valid set is `text`, `audio`, `challenge`, `grace`, `silence` (`morning_knock.py:66`, `MODALITIES`; anything else falls back to `text`). A knock memo is a self-contained dose. Andrew's typed Tamil reply is judged by `scripts/knock_reply.py`, which moves the production axis.

Defined: `docs/PROTOCOL_MAP.md` — Python brain and knock_log.json rows; `docs/DECISIONS.md` — "Outreach policy is Anna's"

---

## lore

Language stories deployed as first-class input: etymology, cross-language kinship (what English took from Tamil — *catamaran*, *curry*, *mango*), myth, and cultural logic behind a word or register. Lore is not decoration — a word with a story has more retrieval hooks than a word with a scene. Lore never creates production debt (no deck item, no floor gap) and never takes over the feed rotation.

Defined: `protocol/constitution.md` — "Stories Are Curriculum (the lore rule)"; `docs/DECISIONS.md` — "Stories are curriculum — the lore pivot (2026-07-03)"

---

## masks

Anna impersonating a family member (mother-in-law, banter-speed cousin, gossiping auntie) for one beat in-register, then stepping out to recast as himself. Masks force the register the deck needs — deference for the mother-in-law (`-nga` forms), speed for the cousin, gossip idiom for the auntie. One beat, then dropped; the one continuous relationship stays Anna.

Defined: `protocol/persona.md` — "The Masks (Anna Plays the Table)"

---

## the Oracle

Andrew's wife — a native Coimbatore Tamil speaker used as a 60-second vibe-check resource, not a teacher or examiner. Her form always beats the system's draft. She does not know the heist is happening and must never be turned into a progress check. During the Trip Sprint, the Oracle vets the trip deck.

Defined: `protocol/constitution.md` — "The Wife (The Oracle)"; `progress/profile.md` — Trip Sprint sourcing note

---

## recast

Anna's correction method: when the learner is off, say it the natural way and move on — no grammar tables, no case names, no lecture. The way an older brother mutters the fix across the table. Phonetic is fine ("poren" is போறேன் — `knock_reply.py` judge mandate). Recast is the only permitted form of correction; "recast, never lecture" is a canonical rule.

Defined: `protocol/constitution.md` — "Canonical Rules"; `protocol/daily_session.md` — The Loop step 4

---

## scene spec

The three-axis structural selector Python hands the Director for each episode: **register** (emotional tone: dread, tenderness, mischief…), **form** (classic / vignette / story / phone_call / lore), and **dramatic ingredient** (subtext / turn / character / stakes / genre). Computed by `scripts/suggest_targets.py` from the last 3 `*.tags.json` sidecars (`DIVERGENCE_WINDOW = 3`, `suggest_targets.py:48`) to guarantee anti-sameness. It is a gate, not a suggestion — overriding it is how variety drift came back.

Defined: `protocol/studio/director.md` — "Step 1: Take the Scene Spec"; `docs/PROTOCOL_MAP.md` — `suggest_targets.py` row; `docs/DECISIONS.md` — "Serialization / recurring audio cast rejected; variety is structural"

---

## soak-order

The handoff from the chat session to the studio. Anna writes it at Close & Log into `progress/learner.json` → `soak_order`: two fields — **`payload`** (the words chat just strained) and **`scene_seed`** (one line situating the next beat of the running story). The studio consumes it as its only input from the conversation half; everything else the Director derives. This is the only interface between the two halves of the system.

Defined: `docs/PROTOCOL_MAP.md` — "The interface: the soak-order"; `protocol/daily_session.md` — Close & Log step 3

---

## ticket

The output of `python scripts/suggest_targets.py` — the structured session brief Anna picks from. Five sections: (1) floor-gap targets to force cold, (1b) engines to fire (with a novel slot), (2) due callbacks to weave in, (3) new candidates grouped by cluster coverage, (4) the vocabulary fence. Anna picks from the ticket; he does not re-derive targets by eye.

Defined: `protocol/daily_session.md` — "Targeting — Narrow and Deepen"

---

## Trip Sprint

The finite skill sprint before Andrew's India trip (week of 2026-08-12). Pauses the abstract viability-floor climb and substitutes a finite Trip Deck of survival chunks and frames — social-public register, deference forms, antifreeze repair moves. Oracle-vetted via 60-second vibe-checks. Daily win = one phone rep; full session = 2–3×/week. Resumes the floor climb after the trip.

Defined: `docs/DECISIONS.md` — "Trip Sprint (2026-06-30)"; `progress/profile.md` — "Phase 1.5 — The Trip Sprint"

---

## viability floor

The threshold of words and frames firing cold that stops the freeze response — enough operational capacity to navigate Coimbatore without going blank. `scripts/sync_state.py status` reports it as `Viability floor: X/Y recognized words fire cold (Z%)` (`sync_state.py:559`). Production counts (cold fires) move the floor; recognition without production does not. The floor is the headline metric for Phase 1.

Defined: `docs/DECISIONS.md` — "Absorption-first, then production-as-accelerant"; `protocol/persona.md` — "The Charge"; `progress/profile.md` — "Current Position"

---

## Woven Thanglish

The core register rule: English carries the logistics (scene-setting, "why we are here," complex plot movement); Tamil carries the payload (the load-bearing action word). Example: *"I told you to **வை** it here!"* — the English carries the context; the Tamil carries the meaning. This matches how Coimbatore native speakers actually talk and is the system's anti-over-correction against forcing pure Tamil that sounds foreign.

Defined: `protocol/constitution.md` — "Woven Thanglish (The Scaffolding)"; `protocol/persona.md` — "How Anna Talks"
