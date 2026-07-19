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

Laptop pass executed 2026-07-18 (evening). All four open questions settled by Andrew:
filename bump / SFX-as-pause (1.5 s) / `narrated_drama` + `scale: long` / normal accounting.

- [x] **Re-render M68** — rendered to `tier2_mission68_v2.mp3` (filename bump = new
      guid; old mp3 deleted; mission parse reads the *script* name, so registration
      untouched). `rebuild_rss.py` now resolves a `_vN` suffix back to the base script
      for title + captions, and its dead Ep-title regex was fixed in passing (scripts'
      real H1 convention "Tier 2, Mission N — X" never matched — every mission sat on
      the filename fallback). M68 got its missing H1: "The Midnight Suitcase".
- [ ] **Listen-check M68 v2** — ANDREW. SFX cues now render as a 1.5 s beat (smoke
      #8/s22). Narrator pinned to Charon (english_demo's proven code-switch voice) via
      Voice Map in the script.
- [x] **Polyglot v4 rendered** — one-off renderer (v3's was never committed and its
      exact cast is unrecoverable from transcripts; cast reuses the welcome-demo family:
      en-US-Leda host, fr-CA-Leda/Puck French, ta-IN Orus/Fenrir). EAR CHECK pending —
      v3 voice continuity not guaranteed.
- [x] **Producer-pass sanity on M68 narration** — one leftover Latin phonetic found and
      fixed (`*-ndhaa*` → -த்தா, line 278); sweep otherwise clean.
- [x] **DECISIONS entries written** (three: form, script-only narration, re-render/SFX
      policy) and protocol touched — director/architect/producer/hosts, one small block
      each. `suggest_targets.py` deliberately untouched (commissioned, not rotated);
      verified an unknown `episode_form` in a sidecar can't trip the divergence gate.
- [ ] **LinkedIn post** — ANDREW edits voice, then posts (draft below).
- [ ] **Merge this branch + delete this file** — after the two listen-checks pass.

Note: the pending soak order in `learner.json` (maama's-house week-arc, "Long-form,
multi-scene") is this form's first commission — it predates the field convention; Anna
can carry `form`/`scale` explicitly from the next commission on.

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
