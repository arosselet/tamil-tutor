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

**First, read the chat.** Anna's daily sessions are the other half of this loop: the podcast is the *input soak* that feeds what Anna forces Andrew to *produce*. Before picking words, read `progress/vocab_state.json` (the production axis — `cold` / `hinted`) and the `last_debrief` in `progress/profile.md`, and let them bias the payload:
- **Fired `cold` recently** → *consolidate.* Let these appear in rich, fast, natural contexts — a reward. He owns them; let him catch them in the wild.
- **`hinted` / wobbling** → *soak.* Give a pressure-free second exposure. Hearing it used naturally is the safety net for what chat just strained.
- **The `last_debrief` thread** → when it fits, echo the situation Anna just played in chat. Tuesday's fumble becomes Thursday's scene.

This is what makes an episode feel alive — it tracks his real week, not an abstract coverage counter.

Pull from the full curriculum word pool (`curriculum/tiers/*.json`). There is no tier gate — progress is measured by absolute word count (`progress.known_words / progress.target` in `learner.json`), not by tier percentage.

Every payload has two active parts:

**NEW (4–5 words or phrases):** Fresh items the learner hasn't met. Select by **cluster coverage** — look at the last 5 episode briefs and pick a cluster that hasn't been the focus recently. Within that cluster, pick the highest-frequency, most household-relevant items first. Phrases and chunks are as valid as single words — prefer them when they're more useful than the sum of their parts. Skip anything already in `vocab_state.json` mastered/comfortable/struggled lists.

**CALLBACKS (3–5 words):** Run `python scripts/generate_callbacks.py` to get the list. The script uses spaced repetition to pick words that are due for resurfacing — struggled words, overdue words, and words that have never appeared in a script. Treat them as a **soft target: aim to land 2–3; the script leads and the quota follows.** Don't bend the scene to force every one — a callback that won't fit naturally waits for next time (this also keeps any single word from over-rotating). Prefer callbacks that are `hinted` in chat: soaking them here is exactly the safety net.

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
