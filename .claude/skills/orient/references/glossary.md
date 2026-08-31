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

## deck (RETIRED 2026-08-18)

A tagged subset of `progress/lexicon.json` — 83 chunks and frames tagged `deck:"trip"` — that `suggest_targets.py` surfaced ahead of everything else, metered as **Trip Deck: X/N fire cold**. A *container*: bounded, deadline-driven, and its reason expired at touchdown (2026-08-12). Retired whole; what it carried moved out first (see *register*, *tier*). The 83 rows keep the tag as **provenance** — the record of where they came from — and nothing reads it. `sync_state seed-deck` survives as the writer path for any curated set.

Defined: `docs/DECISIONS.md` — "Retire the trip deck"; `progress/profile.md` — "Phase 1.5 — The Trip Sprint (RETIRED)"

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

A lexicon row may carry a `direction` field. **Fire** (the default) targets cold production — the learner must generate it under pressure. **Catch** is ear-only — the win is solid recognition via eavesdrop drills and soak; these are never forced to fire. The two are selected by different functions (`floor_gap_targets` vs `ear_targets`), because they are different axes, not rival pools. `direction` was always the discriminator, never the retired `deck` tag, so the split outlived the deck: `compute_ear` meters the catch side as `Y/M solid`.

Defined: `progress/profile.md` — "Fire vs. catch (2026-07-01 redesign)"; `docs/PROTOCOL_MAP.md` — `lexicon.json` row

---

## floor-gap

A word the learner recognizes (comfortable or solid) but cannot yet produce cold — they do not need re-teaching, they need cold dispatch in fresh English situations. The gap between recognition and production is the work, and `compute_floor` meters it as the viability floor.

It is no longer the whole selectable population: since 2026-08-18 the **pool** admits any row not yet firing cold, `struggled` ones included, because the retired deck's rows were 31/35 struggled and a recognition gate would have made the ordering it left behind unreachable. Teach-first still guards those (`is_unseen`).

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

The agentic phone-outreach system. `scripts/morning_knock.py` runs on a CI cron, checks the rails gate (waking hours, ≤5/day, ≥3 h apart), then Anna decides fire or silence and which modality — the valid set is `text`, `audio`, `challenge`, `volley`, `eavesdrop`, `fielding`, `grace`, `silence` (`MODALITIES` in `morning_knock.py`; anything else falls back to `text`). A knock memo is a self-contained dose. Andrew's typed Tamil reply is judged by `scripts/knock_reply.py`, which moves the production axis.

Defined: `docs/PROTOCOL_MAP.md` — Python brain and knock_log.json rows; `docs/DECISIONS.md` — "Outreach policy is Anna's"

---

## lore

Language stories deployed as first-class input: etymology, cross-language kinship (what English took from Tamil — *catamaran*, *curry*, *mango*), myth, and cultural logic behind a word or register. Lore is not decoration — a word with a story has more retrieval hooks than a word with a scene. Lore never creates production debt (no drill target, no floor gap) and never takes over the feed.

**Where it rides (all four, and it is thin if any one carries it alone):** the chat tangent (`persona.md`), the no-ask knock dose (`mandates.py`, rails-guarded at both ends since 2026-08-31 — a 7-day cooldown AND a 10-day cadence), the `lore` episode form in the scene spec, and a `lore` movement in every **rotation** cadence. The two audio homes are the fragile ones: both were high-attention lanes, so a month of low-capacity days routed correctly to soak and drill and silently took all audio lore with it (2026-08).

Defined: `protocol/constitution.md` — "Stories Are Curriculum (the lore rule)"; `docs/DECISIONS.md` — "Stories are curriculum — the lore pivot (2026-07-03)" and "A lane named for an occasion is unreachable (2026-08-31)"

---

## machines heard

The headline meter since 2026-08-16: of the ~26 patterns (frames/machines) in the lexicon, how many are `solid` on **recognition** — can he *hear* the machine at speed, not merely fire it. `session_brief.py` prints it as `Machines heard: X/N`; `sync_state.compute_status` leads the one-line scoreboard with it. It replaced production meters (the retired Trip Deck, Engines, viability floor) as the lead because those measure the engine and this measures the destination — the evidence being that Andrew produced 20 of 26 machines cold while hearing 3, which is exactly why two words landing in a fast sentence felt like nothing. Ear-only (`direction: catch`) patterns are inside its denominator; **engines** excludes them, so this is the one meter that sees the whole set. Like every meter it steers Python and is never recited to him.

Defined: `docs/DECISIONS.md` — "The headline is the ear, not the mouth"; `protocol/constitution.md` — "The Learner" mission

---

## masks

Anna impersonating a family member (mother-in-law, banter-speed cousin, gossiping auntie) for one beat in-register, then stepping out to recast as himself. Masks force the register the table needs — deference for the mother-in-law (`-nga` forms), speed for the cousin, gossip idiom for the auntie. One beat, then dropped; the one continuous relationship stays Anna.

Defined: `protocol/persona.md` — "The Masks (Anna Plays the Table)"

---

## the Oracle

Andrew's wife — a native Coimbatore Tamil speaker used as a 60-second vibe-check resource, not a teacher or examiner. Her form always beats the system's draft. She does not know the heist is happening and must never be turned into a progress check. The Oracle vets any curated set before `seed-deck` lands it.

Defined: `protocol/constitution.md` — "The Wife (The Oracle)"; `progress/profile.md` — curated-set sourcing note

---

## pool

The single ordered selector (`suggest_targets.floor_gap_targets`): every row not yet firing cold, tier-first, split into **focus** (≤`FOCUS_SIZE`, stored membership in `learner.json`, drilled) and **background** (exposure only, never forced). `drill_menu` is the flat view of its head plus the engines, and it is what the knock menu, the volley and the drill tape all pick from — one owner, so no lane re-sorts.

It replaced three rival sections on 2026-08-18: the deck, the focus set, and "hinted, going dark". Two of them claimed primacy in their own words on a 361-line ticket, so the day's session was decided by whichever one Anna weighted that morning. The going-dark block became a *rule* (`is_going_dark`) plus a reservation of `RETEST_SLOTS` seats — a floor, never a ceiling.

Defined: `scripts/suggest_targets.py` — `floor_gap_targets`, `drill_menu`

---

## recast

Anna's correction method: when the learner is off, say it the natural way and move on — no grammar tables, no case names, no lecture. The way an older brother mutters the fix across the table. Phonetic is fine ("poren" is போறேன் — `knock_reply.py` judge mandate). Recast is the only permitted form of correction; "recast, never lecture" is a canonical rule.

Defined: `protocol/constitution.md` — "Canonical Rules"; `protocol/daily_session.md` — The Loop step 4

---

## register / tier

The **ordering** the retired deck left behind. Each lexicon row may carry a `register` — `antifreeze`, `public`, `frame` (→ **survival**); `faq`, `mil-table`, `social` (→ **delight**); `gossip`, `zinger` (→ **dessert**). `suggest_targets.tier_rank` reads it off the row and every selector prefixes it, so survival — fast speech aimed at him, which he must repair or transact rather than freeze at — is forced before delight, and delight before dessert.

It is durable knowledge about which failures cost most at a table, which is why it survived the container it arrived in. Before 2026-08-18 it was joined at menu time from `curriculum/trip_deck.json`, keyed on deck membership; migrating it onto the row is what made retiring the deck safe, because a join keyed on a deleted tag fails *silently* — the selector keeps returning rows, merely unordered. 83 of 339 rows carry one; the rest degrade to delight (unordered, not unreachable). `sync_state seed-deck` is the only writer.

Defined: `scripts/suggest_targets.py` — `REGISTER_TIERS`, `tier_rank`; `docs/DECISIONS.md` — "Retire the trip deck"

---

## rotation

The fourth audio lane: **movements on a Python-planned cadence**, where the recurrence schedule *is* the pedagogical payload. Each movement (`machine`, `inventory`, `scene`, `eavesdrop`, `lore`) is one small just-in-time sheet, ~1–2 min, on a cycle that never places two of a kind side by side. Not an episode — the episode is three LLM passes writing a *scene*, and stretching one is banned ("never answer a length ask by stretching another"). Not a soak either: soak is flat repetition, rotation is shaped, and they share a capacity row so the choice between them is a curriculum question.

**Was `longhaul` until 2026-08-31**, and the rename was the fix: every sibling lane names its function (soak, drill, episode) while this one named an *occasion* — a twenty-hour flight. That cost it its `audio_channels.md` row ("a flight or a long haul") and a 45-minute default, so it was unreachable on ordinary ears-only days and ran twice in its life. `--minutes` was always a ceiling: a flight is `--minutes 45`, the default is 15. Published tapes keep the `longhaul_` prefix (a feed entry is a promise); new ones write `rotation_`.

Defined: `scripts/render_rotation.py`; `protocol/audio_channels.md`; `docs/DECISIONS.md` — "A lane named for an occasion is unreachable (2026-08-31)"

---

## scene spec

The three-axis structural selector Python hands the Director for each episode: **register** (emotional tone: dread, tenderness, mischief…), **form** (classic / vignette / story / phone_call / lore), and **dramatic ingredient** (subtext / turn / character / stakes / genre). Computed by `scripts/suggest_targets.py` from the last 3 `*.tags.json` sidecars (`DIVERGENCE_WINDOW = 3`, `suggest_targets.py:48`) to guarantee anti-sameness. It is a gate, not a suggestion — overriding it is how variety drift came back.

Defined: `protocol/studio/director.md` — "Step 1: Take the Scene Spec"; `docs/PROTOCOL_MAP.md` — `suggest_targets.py` row; `docs/DECISIONS.md` — "Serialization / recurring audio cast rejected; variety is structural"

---

## soak-order

The handoff from the chat session to the studio. Anna writes it at Close & Log into `progress/learner.json` → `soak_order`: **`payload`** (what the dose carries), **`scene_seed`** (one line situating the next beat of the running story), plus optional `focus`, `channel` and `form`. The studio consumes it as its only input from the conversation half; everything else the Director derives. This is the only interface between the two halves of the system.

**The payload has a priority, not a menu (2026-07-28): the repair earns the dose.** It is drawn *first* from the day's unclosed repairs — hinted, recast, or corrected-and-still-wrong — and points forward as a **seed order** of unseen items only when the day leaves no repair owing. Backward beats forward; a collision that survived its correction earns its own order rather than a share of a mixed one.

Defined: `docs/PROTOCOL_MAP.md` — "The interface: the soak-order"; `protocol/daily_session.md` — Close & Log step 2

---

## ticket

The output of `python scripts/suggest_targets.py` — the structured session brief Anna picks from. The slip ledger rides on top (how he is failing); then (1) the **pool**, tier-ordered, with the ear (1a), the background (1b), coverage (1c) and the engines (1d) as views of the same population, (2) due callbacks to weave in, (3) new candidates grouped by cluster coverage, (4) the vocabulary fence. Anna picks from the ticket; he does not re-derive targets by eye. It was nine selectors until 2026-08-18, three of which claimed primacy in their own words; none does now.

Defined: `protocol/daily_session.md` — "Targeting — Narrow and Deepen"

---

## Trip Sprint (CLOSED 2026-08-18)

The finite skill sprint before Andrew's India trip (week of 2026-08-12). Paused the abstract viability-floor climb and substituted a finite deck of survival chunks and frames — social-public register, deference forms, antifreeze repair moves, Oracle-vetted. **It worked**: survival went 15/34 (07-25) → 30/34 (08-18), the best conversion this project has produced, and the lesson kept is that a finite, visible, ordered set beats an undifferentiated 339-row ledger. Closed at touchdown by its own instruction; the floor climb resumed, under the **machines heard** headline.

Defined: `docs/DECISIONS.md` — "Retire the trip deck"; `progress/profile.md` — "Phase 1.5 — The Trip Sprint (RETIRED)"

---

## viability floor

The threshold of words and frames firing cold that stops the freeze response — enough operational capacity to navigate Coimbatore without going blank. `scripts/sync_state.py status` reports it as `Viability floor: X/Y recognized words fire cold (Z%)` (`sync_state.py:559`). Production counts (cold fires) move the floor; recognition without production does not. It led Phase 1 and no longer leads anything (2026-08-16): production is the *engine*, not the destination, so the floor measures how hard the engine is running — **machines heard** measures whether he has arrived. Both still print; only one is the headline.

Defined: `docs/DECISIONS.md` — "Absorption-first, then production-as-accelerant"; `protocol/persona.md` — "The Charge"; `progress/profile.md` — "Current Position"

---

## Woven Thanglish

The core register rule: English carries the logistics (scene-setting, "why we are here," complex plot movement); Tamil carries the payload (the load-bearing action word). Example: *"I told you to **வை** it here!"* — the English carries the context; the Tamil carries the meaning. This matches how Coimbatore native speakers actually talk and is the system's anti-over-correction against forcing pure Tamil that sounds foreign.

Defined: `protocol/constitution.md` — "Woven Thanglish (The Scaffolding)"; `protocol/persona.md` — "How Anna Talks"
