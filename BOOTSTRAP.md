# Bootstrap Guide: Start Your Tamil Heist

Welcome to the Tamil Learning System. This guide initializes your own persistent tutor, learner profile, and progress tracking in a single session.

## Prerequisites
- **Python 3.10+**
- **An LLM Agent** (Claude Code, Gemini CLI, or similar)
- **TTS Access**:
  - *Edge-TTS* (Free, no setup)
  - *Google Cloud TTS* (Requires `gcloud auth login`)

---

## One-Prompt Setup

Clone the repo, then paste this into your LLM agent:

> "I want to bootstrap a new Tamil learning environment. Please act as `@build` (the engineer working *on* the system).
> 1. Read `BOOTSTRAP.md` for the setup protocol.
> 2. Ask me for my name, my preferred tutor's name/personality (e.g., elder brother, strict coach, casual friend), and my TTS preference (Edge or Google).
> 3. Initialize progress files from the `.example` templates.
> 4. Customize `protocol/persona.md` based on the tutor personality I choose.
> 5. Guide me through setting up my own git remote.
> 6. Start our first `/anna` session."

---

## The Bootstrap Protocol (Agent Instructions)

If you are the agent performing this bootstrap, follow these steps exactly:

### 1. Identify the Learner
Ask the user:
- **Learner Name**: (e.g., "Andrew")
- **Tutor Name & Persona**: (e.g., "Anna, the elder brother from Coimbatore")
- **Heist Framing**: What is the "secret goal"? (e.g., "Surprise my wife at a wedding")
- **TTS Provider**: `edge` or `google`.

### 2. Initialize State
Copy each `.example` file to its live counterpart and fill in the user's data:

| Template | Live file | Purpose |
|---|---|---|
| `progress/learner.json.example` | `progress/learner.json` | Continuity: running story (debrief), soak order, status |
| `progress/lexicon.json.example` | `progress/lexicon.json` | The word brain (starts empty — `sync_state.py` populates it) |
| `progress/episodes.json.example` | `progress/episodes.json` | Audio episode registry (starts empty) |
| `progress/session_log.json.example` | `progress/session_log.json` | Append-only momentum log (starts empty) |
| `progress/profile.md.example` | `progress/profile.md` | Teacher's notebook — fill in learner name, goal, initial assessment |

In `learner.json`, replace `"Your Name"` with the learner's name.

### 3. Codify the Persona
Rewrite `protocol/persona.md` to reflect the chosen tutor's voice based on the `persona.md.example` template.
- Ensure the **"What [Tutor] Never Does"** list is intact.
- The tutor is the single interactive front door — they drive the pedagogy and can commission audio when it serves the goal.

### 4. Git Remote Setup
Remind the user to set up their own private repository:
```bash
git remote remove origin
git remote add origin [their-private-repo-url]
git push -u origin main
```

### 5. Start the Loop
Run the first `/anna` session using the fresh state.

---

## Repository Structure for Portability
- `protocol/` — The generative logic (persona, daily session, audio pipeline roles).
- `progress/` — Your personal state (gitignored JSON managed by Python + LLM-maintained profile).
- `curriculum/` — `word_pool.json` (suggestion list of words; Anna picks from it) plus optional curated deck files (e.g. a finite sprint deck like `trip_deck.json`) loaded via `sync_state.py seed-deck`.
- `scripts/` — Python engine: `sync_state.py` owns all state writes; `suggest_targets.py` computes the session ticket; `render_audio.py`, `show_status.py`, `generate_callbacks.py`, `build_playlist.py` for audio and spaced repetition; `morning_knock.py` / `knock_reply.py` / `push_queue.py` for the optional phone-outreach loop.

### What Generalizes (the layer map)

This repo is a **reference implementation, not a framework** — the goal here is learning Tamil, not maintaining a template (settled: `docs/DECISIONS.md`). But the pedagogy is general, and these are the clues for anyone re-instantiating it. Four layers, from portable to personal:

**Layer 0 — the pedagogy (fully general).** The viability floor (recognition × production axes), forced cold output, engines over word lists, invisible assessment, recast-never-lecture, momentum design (contact time > completion, self-contained doses, the coach reaches first), continuity as prose memory. Nothing Tamil about any of it; it lives in `protocol/constitution.md`, `protocol/daily_session.md`, and `docs/DECISIONS.md`, written with Tamil examples inline.

**Layer 1 — the machinery (mostly general, with a known port surface).** The Python engine, state schema, and daily-loop choreography carry over unchanged, *except*:

- **LLM prompts embedded in the Python.** `morning_knock.py` (the outreach-decision prompt), `knock_reply.py` (the judge prompt), and `render_drill.py` (the drill-script prompt) state Tamil-specific rules in prose — Tamil script vs. phonetic, Woven Thanglish. This is the port surface a swap-the-`.md`-files pass will miss.
- **Constants.** The script-detection regex (`TAMIL_RE` in `sync_state.py` — canonical lexicon keys must be Tamil script), the pinned TTS voice IDs (`ta-IN-…` in `morning_knock.py` / `render_audio.py`), and the repo URL used for CDN links.

**Layer 2 — the language pack (swap these files):**

| File | Holds | Swap to |
|---|---|---|
| `protocol/persona.md` | The tutor's identity, voice, dialect tics | Your tutor in the new language/region |
| `protocol/studio/hosts.md` | The podcast cast (names + regional identity) | New cast names and regional voice |
| `protocol/studio/dialect.md` | Spoken-register rules (verb collapse, fusion, slang) | The target dialect's spoken rules |
| `protocol/constitution.md` | Mostly universal — but the dialect *examples* are Tamil | Edit the inline examples to the new language |
| `curriculum/word_pool.json` | The glue-word suggestion pool | The new language's high-frequency glue |

Two constitution rules are language-*culture* dependent, not universal. **Woven Thanglish / the Noun Shortcut** works because code-switched English is native to spoken Coimbatore Tamil; for another language, keep the underlying rule — *target the register natives actually speak, and use the learner's L1 as scaffolding however that register permits* — and re-derive the letter. Likewise the **phonetic/script modality split** collapses for Latin-script languages and mutates for others (e.g. pinyin + tones).

**Layer 3 — the learner pack (re-instantiate, don't copy).** The heist, the Oracle, field missions, the masks, and the knock cadence are not decoration — they are the **fuel for the momentum system**, tuned to one learner archetype (married into the language, native speaker at home). A different learner supplies their own equivalents rather than deleting them: a **stake** (a reveal, a trip, an exam — the thing mastery climaxes into), an **informant policy** (who the native resource is, and what they must never become — an examiner), and an **outreach contract** (rails and a social contract that fit their life).

### Day Zero (how the first session sounds)

The blank templates boot a coherent state: `sync_state.py status` runs fine and reports *floor 0/0 (0%), story: "System initialized."* On day zero there are no floor-gaps, no callbacks, no engines — the ticket's only meaningful section is *new candidates by cluster* from the word pool. So the first session inverts the usual ratio: instead of forcing known words cold with 1–2 new ones as a treat, the tutor seeds one or two survival clusters inside a single scene built from the profile's goal (`profile.md` → "What's Needed Next" *is* the day-zero story), and the first Close & Log writes the first real debrief and soak order. The loop is self-priming: session two already has floor-gaps to force.

*(Known wart: `suggest_targets.py` currently treats an **empty** lexicon as **missing** and refuses to print a ticket — logged in `docs/feature_inbox.md`. Until that lands, day zero runs off the profile and word pool directly.)*

*Keep your `progress/` folder synced to a private Git repository so your tutor remembers you across devices.*
