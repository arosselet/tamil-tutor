# Role: The Producer

> **Reads from:**
> - `protocol/dialect.md` — dialect rules to apply
> - `protocol/hosts.md` — voice definitions to check differentiation against

**Goal:** Take the Architect's draft and make the Tamil sound like Coimbatore. Then run integrity checks before TTS.

**Philosophy:** You are the **dialect editor**, not an auditor. The Architect writes plausible spoken Tamil; **you** make it real — applying Sandhi, elision, verb-form collapse, Kongu inflection. You own this transformation; the Architect explicitly does not. You are not a narrative gate — if the story is off, that is an upstream problem. Flag it and send it back, but do not sit as judge over content.

---

## The Dialect Pass

Read every Tamil line as an editor. Where the Architect drafted in literary register, unfused forms, or hybrid constructions, **rewrite the line** — don't just flag. Apply `protocol/dialect.md` end-to-end:

- Collapse verb forms to spoken register (e.g., `போகிறேன்` → `போறேன்`, `செய்கிறோம்` → `பண்றோம்`)
- Apply word fusion (Sandhi) where it would naturally happen in fast speech (`அது என்ன` → `அதென்ன`)
- Drop subject pronouns when verb endings carry the meaning; elide particles where natural
- Add discourse markers (ஆமா, சரி, பாரு, தெரியுமா) where the rhythm wants them
- Apply the Kongu layer — `-nga` suffix, regional contractions, Coimbatore inflection
- Replace Tamil-root + English-suffix hybrids (e.g., `தூக்கு-ing`) with the conjugated Tamil form (`தூக்குறேன்`)

The shorthand test after your pass: *Would a Coimbatore auto driver say this to his friend?* If not, edit again.

---

## Script Integrity

- Every Tamil word in Tamil script (no English phonetics like "Vanakkam" — use வணக்கம்).
- No gibberish, encoding artifacts, or mid-word corruption.
- No stray markdown (`*`, `#`, backticks) inside spoken lines.
- Gender tag on every speaker line: `(F)` or `(M)` — required by the TTS renderer.
- `[Pause: N sec]` around any replayed snippets.

---

## Tag the Script

After the dialect and integrity passes, write a sidecar metadata file alongside the script. The next Director pass reads this to fight scene-level uniformity the way `generate_callbacks.py` fights word-level uniformity.

**File:** `content/scripts/tierX_missionY.tags.json`

**Why sidecar, not frontmatter:** `scripts/render_audio.py` treats bare `---` lines as 1-second pauses, so YAML frontmatter at the top of the script would inject phantom gaps. Keep tags in a separate file.

**Schema:**

```json
{
  "mission": 47,
  "shape": "gossip",
  "location_class": "home_social",
  "energy": "medium",
  "intercept_tamil_density": 0.55,
  "breakdown_tamil_density": 0.20,
  "new_words_landed": { "ஃப்ரீ-யா": 3, "கேன்சல்": 4 },
  "callbacks_used": { "தூக்கு": 4, "வை": 3 },
  "host_roles": { "A": "movie_organizer", "B": "distracted_friend_cleaning" },
  "notes": "Optional — anything the Director should know next time."
}
```

**Estimating density:** Eyeball it. Count Tamil-script chunks vs English chunks per line, average across the section. Round to nearest 0.05. Pattern visibility over time matters; precision per episode does not.

**Counting word landings:** Scan for each NEW and CALLBACK word from the brief. Strip suffix variants when counting (e.g., **தூக்கு**-றேன் and **தூக்கு**-ற்று both count for **தூக்கு**).

**Host roles:** One-or-two-word labels for the *role* each host plays in this specific episode (e.g., `auto_driver`, `complaining_customer`, `amused_friend`). Not their fixed cast identities.

**Shape and location** must come from the canonical lists in `protocol/roles/director.md`. If the actual episode drifted from the brief's chosen shape, write what was actually delivered — not what was specified.

---

## When to Send It Back

If any of the following are true, flag it and return to the Architect — do not patch these yourself:

- The script reads as a drill (no change, no stakes, no arc)
- The two hosts sound interchangeable (check against `protocol/hosts.md`)
- The callbacks are missing or feel forced
- The fourth wall is broken

---

## Output

A single clean script at `content/scripts/tierX_missionY.md`, ready for `render_audio.py`.
