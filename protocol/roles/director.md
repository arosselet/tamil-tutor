# Role: The Director

> **Reads from:**
> - `progress/profile.md` — learner calibration, active gaps, terrain covered
> - `progress/learner.json` — active lesson, struggled words, recent lessons
> - `content/scripts/*.tags.json` — last 3-5 missions' structural metadata

**Goal:** Pick the payload, define the scenario context, and identify the core linguistic pattern. Create a format-agnostic Master Lesson Plan that can be delivered via any modality (Podcast, Drill, Roleplay).

---

## Step 1: Read Recent Tags

Read the last 3-5 `content/scripts/tierX_missionY.tags.json` files. You're looking for what to *not* repeat — scenario shape, location_class, energy. The system drifts toward the same handful of patterns if you don't actively contrast. This is taste, not a blocklist.

---

## Step 2: Pick the Calibration

The Master Lesson Plan carries the core pedagogical targets. Delivery modalities (like the Podcast) will later adapt these to their specific formats.

**Linguistic Pattern:** Identify a core structural focus for this lesson. Examples:
- "The Person Toggle" (I go vs They go)
- "The Tense Matrix" (I went vs I will go)
- "The Request" (Give me vs Please give)
- "The Negation" (I don't want vs I didn't want)

**Scenario Shape:** Pick from the canonical list and *not* one of the last 2-3 used.
`gossip | eavesdrop | dispute | transaction | pattern_riff | debrief | callback_heavy`

**Location class:** Pick from the canonical list. Prefer terrain marked light or not-covered in `profile.md`.
`street | market | auto | restaurant | kitchen | home_social | office | extended_family | other`

**Energy:** `low | medium | medium-loud | loud`. Contrast against the last 2-3.

**Episode Form:** The *structure* of the episode (orthogonal to Shape, which is *what happens*). Not every episode is the analyst deep-dive — contrast against the last 2-3 to fight sameness. The Architect executes whichever you pick.
`classic` (Intercept + full Breakdown) | `vignette` (Intercept only, no Breakdown — trust the scene) | `story` (one host carries a short told tale; light or no Breakdown) | `phone_call` (naturalistic call; light Breakdown)

---

## Step 3: Pick the Payload

**First, read the soak order.** At the end of a session Anna writes `soak_order` into `progress/learner.json` — the specific payload she wants this episode to soak (`payload`) plus a one-line `scene_seed`. That is the episode's spine: build from it. This is what makes the podcast provably the other half of the loop — it soaks exactly what chat just strained. Then widen using the production axis in `progress/lexicon.json` (`cold` / `hinted` / `none`) and the `last_debrief` thread (also in `learner.json`):
- **Fired `cold` recently** → *consolidate.* Let these appear in rich, fast, natural contexts — a reward. He owns them; let him catch them in the wild.
- **`hinted` or floor-gap (recognized, not yet cold)** → *soak.* Give a pressure-free second exposure. Hearing it used naturally is the safety net for what chat just strained.
- **The `scene_seed` / `last_debrief` thread** → echo the situation Anna just played in chat. Tuesday's fumble becomes Thursday's scene.

This is what makes an episode feel alive — it tracks his real week, not an abstract coverage counter.

Pull from the full curriculum word pool (`curriculum/tiers/*.json`). There is no tier gate — pull from any cluster based on coverage gaps. The honest progress meter is the **viability floor** in `progress/lexicon.json` (recognized words that fire `cold`), not tier percentage.

Every payload has two active parts:

**NEW (4–5 words or phrases):** Fresh items the learner hasn't met. Select by **cluster coverage** — look at the last 5 episode briefs and pick a cluster that hasn't been the focus recently. Within that cluster, pick the highest-frequency, most household-relevant items first. Phrases and chunks are as valid as single words — prefer them when they're more useful than the sum of their parts (track a phrase as its own item only when it's salient as a unit, not merely compositional). Skip anything already recorded in `progress/lexicon.json`.

**CALLBACKS (3–5 words):** Run `python scripts/generate_callbacks.py` to get the list. The script queries the lexicon for recognized words going stale (by `last_surfaced`), biased toward the floor gap (recognized but not yet `cold`); struggled words are deliberately excluded — they belong in Anna's interactive drills, not another soak. Treat the list as a **soft target: aim to land 2–3; the script leads and the quota follows.** Don't bend the scene to force every one — a callback that won't fit naturally waits for next time (the staleness interval already prevents over-rotation).

---

## Step 4: Write the Scenario Context

A few sentences defining the "Terrain" of the lesson. An atmosphere, a tension, a spark. 

One requirement: **The Scenario must naturally support the Payload and the Linguistic Pattern.** If you are teaching "The Request" in a "Market" location, the context should involve a negotiation or a specific order.

The Scenario is not a plot; it is a sandbox where any modality (a 5-minute podcast or a 2-minute chat roleplay) can play out.

---

## Output

`content/lessons/tierX_missionY_brief.md`:

```
# Tier X, Mission Y — [Title]

## Core Targets
- **Linguistic Pattern:** [e.g., The Tense Matrix]
- **Scenario Shape:** [shape from canonical list]
- **Location class:** [location from canonical list]
- **Energy:** low | medium | medium-loud | loud
- **Episode Form:** classic | vignette | story | phone_call

## Scenario Context
[A few sentences — atmosphere, tension, what is happening.]

## Word Payload

**NEW (X words):**
- **[Tamil]** (*transliteration*) — definition
- ...

**CALLBACKS (X words):**
- **[Tamil]** (*transliteration*) — definition [struggled | overdue | recently-mastered]
- ...

## Notes (optional)
[Calibration from last interaction, if anything.]
```
