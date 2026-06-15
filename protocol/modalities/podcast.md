# Modality: Podcast

> **Input:** `content/lessons/tierX_missionY_brief.md` (Master Lesson Plan)
> **Output:** `content/scripts/tierX_missionY.md` (TTS-ready script)

This modality transforms the Master Lesson Plan into a high-fidelity, two-voice Coimbatore Tamil podcast episode.

## Execution Pipeline

### 1. The Architect Pass
Invoke the **Architect** (`protocol/roles/architect.md`) to write the two-voice script. 
- **Adaptation:** The Architect reads the "Scenario Context" from the Lesson Plan and expands it into a full scene per the **Episode Form** — Intercept always; Breakdown when the form calls for it.
- **Density Calibration:** Since the Master Lesson Plan is density-agnostic, the Architect must choose appropriate Tamil density based on the `learner.json` level (e.g., 0.65-0.80 for mid-progress).

### 2. The Producer Pass
Invoke the **Producer** (`protocol/roles/producer.md`) to perform the dialect pass.
- **Dialect Rewrite:** Transform Architect's Tamil into spoken Coimbatore register (`protocol/dialect.md`).
- **Integrity Check:** Ensure Tamil script, gender tags, and no artifacts.
- **Metadata:** Write `content/scripts/tierX_missionY.tags.json` sidecar.

### 3. Audio Generation
Run `python scripts/render_audio.py` on the final script.

---

## Canonical Constraints (Podcast Specific)

1. **Host Integrity**: Follow `protocol/hosts.md` strictly for the four voices.
2. **Breakdown (form-dependent)**: When the Episode Form includes a Breakdown, it must be a second Tamil exposure, NotebookLM-style — not a translation pass. See the Architect role.
3. **SFX**: Use `[SFX: ...]` to establish the scenario context physically.
