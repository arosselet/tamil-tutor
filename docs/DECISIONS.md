# Settled Decisions (`@build` reference)

Questions that were explored, decided, and closed. **Don't re-litigate these** — if new
evidence genuinely reopens one, take it to Andrew with the evidence; never silently drift.
Details live in git history; this is the index of the *conclusions*.

## How to work on this system

- **LLM is the writer, Python is the brain** (2026-04-09). Push reasoning into
  deterministic code; keep the LLM's input surface small. Never hand-edit Python-owned JSON.
- **Every addition must earn its place.** Before adding a file, field, rule, or script,
  state what it replaces or simplifies — addition that doesn't simplify something else is
  suspect. The system's worst moments were accumulation (NOT-lists, format rotation,
  micro-debriefs, all in one week); its best moves were separations.
- **Surgical edits to the relevant file** (2026-04-15). Concerns are separated on purpose:
  dialect problem → `dialect.md`, voice problem → `hosts.md`, word selection →
  `suggest_targets.py`, variety → the scene spec. Never rewrite role files for a one-off.
- **Fix the tool, not the personality.** When Anna seems dumb, forgetful, or pushy, read
  the plumbing first — `gh run` logs, `knock_log.json` timestamps — before touching persona
  or prompts. (2026-07-03: "Anna had no knowledge of my reply" was a same-tick multi-fire
  collision in the push queue, 100% plumbing.)
- **Structure freeze — Anna 1.0.** Rows of data are free; schema changes wait. Route
  build-itches to `docs/feature_inbox.md`. (Canonical in `docs/PROTOCOL_MAP.md`.)
- **Lightweight triggers for lightweight actions** (2026-07-02). When a request is "fire
  the existing automation with one value," wire a Shortcut/webhook one-liner — don't route
  it through a full chat session.
- **Explore before implementing.** Andrew is an architect; when he names a problem he wants
  the shape and tradeoffs explored together first. Write code only after he signals
  alignment. Long rambly questions want a sharp restatement of the real situation, not a
  bullet-pointed action plan.
- **Calibration dials live in `progress/profile.md` → Calibration Notes** — coverage %,
  new-word counts, pacing. Change the parameter; never encode a dial's value in protocol
  prose or assistant memory.
- **A fade is palatability data, not a discipline failure** (2026-07-04). Contact is king
  *only when the input is palatable and reliably varying* — the Apr–May fade wasn't
  absence, it was episodes grating (too dense, too contrived, same scenario re-run) and
  the fade-era refactors were a search for the fix. When contact drops: diagnose the
  grating first; never answer a fade with accountability machinery. A build-itch during a
  fade carries the diagnosis — mine it before parking it.

## Settled design decisions

- **Absorption-first, then production-as-accelerant** (2026-04-09 / 2026-06-07). Pure
  comprehensible input plateaued; forced cold output toward the **viability floor** is the
  engine. Narrow and deepen; widen only after the floor.
- **Anna is the single interactive front door** (2026-06-15). One persistent persona
  (he/him — "elder brother"), default mode, no keyword. Text modalities are tools he
  deploys; the old `@tutor` orchestrator is retired.
- **Continuity is prose memory, not a schema** (2026-06-17). One running story carried in
  `learner.json`'s `last_debrief`/`soak_order`, rewritten cumulatively by Anna. A
  thread-tracking schema (`threads.json`, due-ness scoring) was **rejected**. Python
  computes the *menu*; Anna makes the *choice and the meaning*.
- **Narrative-saga continuity rejected** (2026-06-28). Serialized fictional plot rings
  hollow and fights "fresh situations, not repetition." Scenes are disposable one-use pegs.
  The one true narrative is Andrew's own arc; **climax = mastery**.
- **Serialization / recurring audio cast rejected; variety is structural** (2026-06-20).
  Python's scene spec (register / form / dramatic ingredient, divergence window 3) is a
  **gate, not a suggestion** — taste-based variety is how the drift crept back. The
  Breakdown is **colour, not coverage** (never a glossary).
- **Producer owns the dialect transformation** (2026-05-04). The Architect writes plausible
  spoken register only; dialect rules never go in `architect.md` (rule-budget crowding made
  episodes drill-shaped).
- **Stop chasing listens** (2026-06-30). The knock and each episode is a **self-contained
  dose**; no listen-reconciliation ritual, no "press play" nudges. The low-friction chat/
  phone rep is the loop; audio is the immersion tank Anna commissions.
- **Competent over local** (2026-06-30). For the trip sprint, favor clear, correct standard
  colloquial over hyper-local Kongu markers. "Pass as a local" stays the long game.
- **Trip Sprint** (2026-06-30 → India trip, week of 2026-08-12). The finite Trip Deck
  (chunks/frames, Oracle-vetted) is the headline meter; the abstract floor climb resumes
  after the trip. Daily win = one phone rep; full session = 2–3×/week.
- **Knocks are read-only on session state.** They write only `knock_log.json`; learning
  state advances only through interactive reps (sessions, judged replies).
- **Outreach policy is Anna's; Python holds only the rails** (2026-07-01). Waking hours,
  daily cap, min gap = deterministic gate; whether/how/when = Anna's decision, optimized
  for Andrew *showing up*, never taps. The busy/back-off social contract is real signal.
- **Cloud never renders episodes** (2026-06-15; amended 2026-07-03). No TTS in cloud for
  episode production — cloud writes append-only to `main`; local renders and
  publishes. **Exception, superseded in practice 2026-06-29 by the knock system:** knock
  memos are one-shot, self-contained doses that `morning_knock.py` renders in CI with its
  own service-account secret; that carve-out is deliberate and stays.
- **Playlist retired** (2026-07-03). Built to chain short episodes so Andrew didn't have to
  press play repeatedly; his listening changed to pick-one-and-repeat, and the playlist's
  selection signal (listen counts) went blind the day the stop-chasing-listens pivot stopped
  feeding it. It also masked the feed: a stale concatenation got mistaken for the newest
  episode. Removed whole: `build_playlist.py`, `rebuild_playlist_rss.py`, `playlist_rss.xml`,
  `published_playlists/`, and the render lifecycle hook. `rss.xml` is the only feed.
- **Stories are curriculum — the lore pivot** (2026-07-03). The anti-teacher bans
  over-corrected into a scenario monoculture; language-lore (etymology / culture / myth /
  cross-language kinship) is now first-class *input*: a `lore` episode form in the palette,
  a persona-native tangent in chat, and a no-ask lore dose in the knock repertoire. Loosens
  the implicit everything-is-a-scenario rule. Guardrails: the scene-spec gate rotates lore
  like any form (it may not take over the feed the way soak did); production (deck / floor)
  stays the engine and gains no debt from lore; "No Academic Terms" still bans terminology —
  it never banned stories. Lore is one of Anna's skills, not a new persona.
- **Portability is documented, not engineered** (2026-07-03). The pedagogy generalizes;
  this repo stays a *reference implementation* of it — no framework extraction, no
  language-pack config layer, no fork maintenance for an n-of-1 system. The clues live in
  one place: `BOOTSTRAP.md` → "What Generalizes" (the four-layer map: pedagogy / machinery
  + its port surface / language pack / learner pack) and "Day Zero" (blank-template
  behavior). Replaces the thinner "To Teach a Different Language" table.
- **CI git identity is `github-actions[bot]`** (2026-07-01) — never a noreply alias that
  credits a real GitHub user. (History was rewritten for this; pre-2026-07-02 commit SHAs
  cited in old notes are stale.)
