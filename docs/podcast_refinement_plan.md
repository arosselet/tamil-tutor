# Podcast Refinement — Working Plan (2026-07-19)

> **Status:** working doc for the `claude/tamil-podcast-refinement` branch. Andrew's
> walk-ramble verdict (2026-07-19) + @build's read of the code. Execute together at the
> laptop, then fold the settled parts into `docs/DECISIONS.md` and delete this file.

## The verdict (Andrew, 2026-07-19)

**The M68 drama experiment ("The Midnight Suitcase") is a success.** A story with real
stakes — the 3 AM call, the uncle at the door, the suitcase — didn't feel contrived, and
sixteen minutes was *listenable*. The English narration interleave ("audio captions")
helped rather than grated: the Tamil line buys a second to process, the immediate gloss
closes the gap on half-known words. The same shape was tried months ago and was a
disaster; it isn't one now — the difference is the system underneath it (fence, soak-order,
scene spec, the unified memory), not the format alone.

Two flaws, both production artifacts, not format flaws:

1. **Pronunciation breaks on the English lines.** The demo skipped the Producer pass, so
   narration carried Tamil in *Latin phonetics* (`*'Medhuva ponga'*`). Every voice is
   `ta-IN` Chirp; Latin script gets read as English orthography → the jarring wrongness.
   The fix is already canon (`hosts.md` → Tamil script only, every context): embedded
   Tamil in English narration goes in Tamil script and the ta-IN voice code-switches
   authentically (proven deliberately by `english_demo`).
2. **Sound continuity.** `render_audio.py` silently **drops** `[SFX: ...]` lines (only
   `[Pause: N sec]` and bare `---` render, as silence). The script's cinematic SFX cues
   never reached the audio.

## Checklist

### Done on this branch (review me)

- [x] **M68 script cleaned** — all ~60 phonetic-Latin narration mentions converted to
      Tamil script (`content/scripts/tier2_mission68.md`). Captions untouched —
      phonetics *belong* there (captions are for eyes, script is for TTS).
- [x] **Polyglot v4 drafted** — `content/scripts/polyglot_demo_v4.md`. v3.2's tone
      (understatement, intellectual honesty), plus the two missing acts: the structural
      machinery of Tamil for an English/French ear (verb-final person-tails, question
      -ஆ, hearsay -ஆம், quotative -னு, audible respect -ங்க), and the honest account of
      an LLM tutor's default failure modes (textbook register, cheap praise, flattering
      meters) with what's built around each. Old v1 stays archived.
- [x] This plan.

### Needs the laptop (render/publish + Andrew's judgement)

- [ ] **Re-render M68** from the cleaned script: `python scripts/render_audio.py
      content/scripts/tier2_mission68.md`. Registration is idempotent (update path
      exists; `seen_in` dedupes) — safe. **Gotcha:** RSS guid = audio URL and pubDate is
      preserved, so an in-place replace keeps the guid — the podcast app may serve the
      cached bad audio (April's cache war). Decide: force re-download in the app, or
      bump the filename (new guid, but check the mission-number parse before renaming).
- [ ] **Listen-check M68 v2** — the walk verdict wants "a couple of touch-ups for the
      sound": confirm the code-switched narration flows, and decide whether dropped SFX
      cues should become short pauses (cheap: treat `[SFX]` like a 1–2 s pause in
      `render_audio.py`) or stay silent.
- [ ] **Review + render polyglot v4** (same render config as v3), publish next to v3.
- [ ] **Producer-pass sanity on M68's narration lines** (dialect pass is for Tamil
      dialogue; narration needs only the integrity checks — script-only Tamil, no stray
      markdown, pacing).
- [ ] **Write the DECISIONS entries** (drafts below) and move the feature from this doc
      into canon; update `suggest_targets.py`/protocol per "Formalizing" below.
- [ ] **LinkedIn post** — see below; Andrew edits voice, then posts.

## Formalizing the format (proposal — the "move forward" part)

Name it **`narrated_drama`** and make it a real episode form with its own discipline:

- **Shape:** multi-scene story with stakes, ~12–18 min. A single narrator (second-person,
  present-tense — "you squint at the screen") carries scaffolding in English; characters
  live entirely in Tamil. The narrator's embedded Tamil is Tamil script, always.
- **Payload scale:** this is the *batch-soak* channel — ~15–25 items per episode vs the
  usual ~5, allocated in tiers exactly as the M68 brief did: Teach-First (unseen, glossed
  in context) / Cold-Fire Engines (one novel instance each) / Ear-Only catch (natural
  speed, unglossed) / New Cluster / Callbacks & floor-gaps. Buy items with minutes, not
  density — the 95% fence-coverage law holds *inside every scene*.
- **Commissioned, not rotated (for now).** Don't add it to `FORMS` in
  `suggest_targets.py` yet — the divergence gate would start rotating into it blind.
  Instead Anna commissions it through the soak-order (e.g. `"scale": "long"` or
  `"form": "narrated_drama"` in `soak_order`) when he reads the week as ready for a
  batch soak — energy, backlog of hinted/ear-only items, a story worth telling. This is
  the new axis Andrew named: Anna senses density/energy and reaches for the long form.
  After a few commissioned episodes prove it (the system's own "prove the format by
  hand" rule), *then* consider gate rotation.
- **Protocol touches** (small, one file each): `director.md` — form definition + the
  tiered payload allocation template; `architect.md` — narrator craft (second person,
  gloss *after* the Tamil beat, never before; give the line a second of air);
  `producer.md` — integrity rule for mixed-language narration + `episode_form:
  "narrated_drama"` in the sidecar; `hosts.md` — a drama cast note (narrator + up to
  2–3 in-scene character voices) and an explicit fourth-wall carve-out: the narrator's
  "you" addresses the *protagonist*, never the learner's state. That carve-out must be
  written precisely or the Producer will correctly bounce every drama script.

### Open questions for Andrew (decide at the laptop)

1. Form name and soak-order field shape (`narrated_drama` + `scale: long`?).
2. M68 re-publish: same guid + forced re-download, or filename bump?
3. SFX: silent drop, pause-substitute, or (later) a tiny real SFX library?
4. Does the drama form count normally against deck/meter accounting, or is a batch-soak
   episode stamped like any other (my read: like any other — `seen_in` already handles it)?

### Draft DECISIONS entries (for Andrew to bless verbatim or edit)

- **The narrated drama is a real form** (2026-07-19, Andrew — by ear). The M68
  experiment succeeded where the months-ago attempt failed; what changed is the
  substrate (fence + soak-order + scene spec + unified memory), so the format rides the
  system now instead of replacing it. Long-form is the batch-soak channel: ~20 items
  bought with minutes, tiered teach-first / cold-engine / ear-only. Commissioned by Anna
  via soak-order; **not** in the rotation gate until several episodes prove it.
- **Narration obeys Tamil-script-only** (2026-07-19). The M68 demo's Latin phonetics
  were a pipeline bypass, not a style: every ta-IN voice reads Latin as English. The
  hosts.md rule already covers this; the drama form adds no exception.

## LinkedIn (and HN) — feedback + draft

**Go.** LinkedIn first is the right call — this story is exactly the "refreshing amid
the corporate back-scratching" post: personal stakes (the dinner table), real
engineering (a year of it), open source, and a date (the trip) that gives it an ending.
Your professional network is warmer than HN's front page and can't flag/bury you. HN is
complementary, not either/or — a **Show HN** later, with `docs/JOURNEY.md` as the
write-up (it is already, nearly verbatim, an HN post). Mechanics: links in the first
comment, not the body (LinkedIn suppresses outbound-link posts); post a weekday morning.

**Draft (Andrew's voice to edit):**

> My in-laws speak Tamil. At their dinner table I've been the ghost — smiling at jokes I
> didn't catch.
>
> So I spent a year building myself a tutor. Not an app — a persistent AI coach with one
> student, living in a git repo. It texts me a challenge at breakfast, judges my typed
> Tamil word by word, and then produces a private podcast that evening that soaks exactly
> what I fumbled that morning. One brain, continuous across every channel; git is its
> save state.
>
> A year of building it solo taught me more about agentic engineering than any work
> project:
>
> 1. LLM is the writer; Python is the brain. Every invariant lives in deterministic
>    code. The model narrates state — it never owns it.
> 2. Separation of concerns applies to prompts. Refactoring one prompt-monolith into
>    single-role files did more for reliability than any model upgrade.
> 3. Meters lie. I rebuilt my headline metric three times; the honest number is always
>    smaller. "Words I can say cold, out loud" outlived every vanity count.
> 4. When a solo project goes quiet, the silence is data. The month I stopped listening
>    was the most information-dense signal the system ever received.
>
> In three weeks I'll be at that table in Coimbatore. The tutor is open source — a Tamil
> reference implementation and a bring-your-own-language template — links in the
> comments.
>
> If you've ever wanted your computer to teach you your family's language: it can. But
> only if you make it honest first.
