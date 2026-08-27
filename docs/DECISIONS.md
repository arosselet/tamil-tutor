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

- **Input first; production is the probe, not the outcome** (2026-08-25, Andrew). His words:
  *"my goal has really been input first. First I need to understand, then I can work on
  responding… Production is a goal yes, but it came to be of such importance in our system
  because that's easy to measure."* So: the ear leads the session, ~3 cold fires replace the
  8–12 Gauntlet, and Ear Day is the volume shape. **Production is not demoted — it is
  re-labelled.** A typed fire probes a *pattern* that generalizes and does not prove a reflex
  at a table; the fires exist to feed the slip ledger, which is the session's primary output.
  Replaces `daily_session.md` invariant 2 ("Honest cold volume") and the Gauntlet's "volume
  day" framing.

- **The ear's pool is not the catch tag** (2026-08-25). `direction: "catch"` answers a
  production question — never force this to fire — and was also the ear queue's membership
  test, so a row had to be *forbidden* from production to be *eligible* for ear work.
  Measured that day: 21 of 26 machines fire cold, 3 are solid on the ear, 5 carried the tag.
  The axis status prints as PRIMARY STEER could reach the ticket with 5 of its 26 rows. Same
  failure `generate_callbacks` fixed on 08-17, one lane over. `ear_targets` now pools catch
  rows *and* machines with reserved seats; `ear_only` rides each row so the catch law stays
  a property of the row. Ticket block renamed EAR-ONLY → THE EAR.

- **Native media is ungated — Phase 2 runs alongside Phase 1** (2026-08-25, Andrew:
  *"reaching a point where I can start more enjoying Tamil movies would be a huge unlock"*).
  It was gated behind the viability floor clearing, which made comprehension wait on the
  production odometer — backwards once the threshold became the ear (08-16). The system
  generates ~1.3 min of Tamil a day; volume cannot come from a boutique. **Films are the
  destination, not the on-ramp:** vlogs and cooking channels re-watched, then serials, then
  films. It replaces nothing and is owed nothing — a week without it is not a lapse.

- **A number never leaves Anna's mouth** (2026-08-25, Andrew: *"the number isn't what makes
  me feel progress… the words and sentences I can now understand really demonstrate the
  progress"*). Retires the small-denominator narration ("this week's 12: 7 down") and step
  7's "campaign's meter". Anna names what he can do now and could not before. Meters stay in
  `sync_state status` for *targeting*; they are engineering numbers, and the ticket's ear
  block dropped its ratio for the same reason — a menu that carries a score gets read as
  progress.

- **The wild line is read back into the session** (2026-08-25). What Andrew hears out there
  and cannot place is the highest-yield input the system gets — "apora wandete" (08-19) had
  both words already in the lexicon, one at `comfortable` after 22 sessions, and diagnosed
  the segmentation gap *and* the stale phonetics. The channel existed (`feedback`); nothing
  read it back until now. Convention, not schema: `feedback "[heard] …"` surfaces on the next
  brief; `feedback "[heard-worked] …"` closes it. Anna DECODES it, never grades it.

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
- **Cloud never renders episodes** (2026-06-15; amended 2026-07-03; **SUPERSEDED
  2026-07-24 — see "Cloud produces episodes" below**). No TTS in cloud for
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
- **All audio lands on the podcast feed** (2026-07-05). A push notification is ephemeral —
  dismissing it must not lose the dose. `rebuild_rss.py` now includes `published_audio/knocks/`
  (titled from the knock log's move), and an audio knock rebuilds `rss.xml` in its own CI
  commit (`refresh_feed()`, failure-tolerant: feed polish never kills a knock). Convenience
  beats feed purity; knocks mingling with episodes is accepted. Replaces the
  notification-only life of knock audio; knocks stay read-only on session state.
- **CI git identity is `github-actions[bot]`** (2026-07-01) — never a noreply alias that
  credits a real GitHub user. (History was rewritten for this; pre-2026-07-02 commit SHAs
  cited in old notes are stale.)
- ~~**Cross-agent access is symlinks**~~ (2026-07-06) — **SUPERSEDED 2026-08-20, see
  "Cross-agent access is prose" below.** The symlinks did not survive a Windows checkout.
- **The judge caps a cold only against computed evidence** (2026-07-06). "LLM writes,
  Python is the brain" applied to reveals: `revealed_recently()` lists what knock traffic
  actually showed in 48h; the judge may deny a cold as "recently handed" only from that
  list (model memory hallucinated a reveal and denied a real cold). Same audit: chains
  move a `pinned_target` (never `expected_target` — the log records the original ask),
  and the deck menu demotes recently-asked items so ripest-first can't farm the same
  headliner into a permanent hinted. Root causes in `/debug` → KF-6.
- **language-tutor syncs by milestone re-extraction, never per-fix backports**
  (2026-07-06). The template is an agent *elaboration* of Tamil@`0c684ef` (tagged
  `template-v1-source`), not a file copy — fixes can't port as patches, and per-fix
  backporting into a mid-QA moving target is recurring manual work. Let it drift; re-run
  the extraction wholesale once Anna 1.0 QA settles (or before actively sharing the
  template). Honors "no fork maintenance" from the portability entry above.
- **First milestone re-sync executed; the seam law is mechanism/dial/personal**
  (2026-07-10). language-tutor now elaborates Tamil@`template-v2-source` (this tag):
  every engine fix since v1 re-applied semantically in the template's config-driven
  idiom. The seam that made it cheap: *mechanisms* port as code (capped lane, chain pin,
  grounded reveals, volley walk, eavesdrop lane), *Anna's choices* port as config dials
  (`outreach.volley_size`, `tts.eavesdrop_voice` — empty = modality off), *personal
  state/studio-local automation* never ports. Confirms the 2026-07-06 entry over the
  alternative (shared-engine packaging), which was considered and rejected: Anna's
  weekly API churn would freeze the wrong abstraction.
- **Machinery commits name their port surface** (2026-07-10). The "Port surface:"
  paragraph the knock-loop commits already carry is what made the re-sync enumerable —
  keep writing it; it is the cheap end of the milestone-re-extraction contract.
- **The @build skill library travels with any extraction** (2026-07-10, Andrew). The
  skills are the guard rails against bloat/drift, so the template gets them generalized:
  repo-canon discipline (structure freeze, surgical routing, smoke-case contract,
  safe/mutating inventory) ports; Andrew-specific collaboration prose generalizes to
  "the repo owner." Replaces treating the skills as Tamil-local tooling.
- **Pedagogy verdict — the ideas held; dose and meters lagged them** (2026-07-08).
  Full learning-science review, endorsed by Andrew on all fronts: retrieval volume ran
  ~5× under the sprint math because the highest-yield tool (the deck blitz) was locked
  inside the rarest event (the laptop session), and the anti-drill aesthetic had
  inverted the delight/volume ratio. "Contact > completion" stays motivation policy but
  never again sets the dose. The philosophy itself — forced cold retrieval,
  chunks/frames, transfer-specific rehearsal, the heist — is confirmed; don't
  re-litigate it.
- **The volley knock — the deck blitz un-caged** (2026-07-08). Most sprint days one
  knock is a 3-item volley: Python's target picks are **binding** (Anna's taste farmed
  six headliners while 50+ deck items sat untouched), Anna writes the English
  situations, each reply's push-back hands the next item, miss = recast-and-move.
  Deliberately narrows "Python computes the menu; Anna makes the choice" for volley
  *items* only — whether/when to fire stays Anna's. Replaces improvised one-item knocks
  as the deck's volume channel.
- **Capped fires graduate cross-day** (2026-07-08). A cold-quality fire blocked only by
  the reveal window is logged `capped`; capped fires on 2 distinct local days graduate
  the word to cold. Rejects the reveal-cap as a permanent bar — a daily-knocked word
  could never reach cold through the very channel drilling it ('oru maasam iruppom'
  fired correctly across days and sat at hinted). KF-6 now audits both directions: a
  shown "cold" downgrades to capped, an unverifiable "capped" upgrades to cold.
- **The Contrast Beat — a recast may carry one clause of why** (2026-07-08). Recast-only
  feedback under-notices (Engines 0/19 after weeks of pure recasts); one clause, by
  example, never terminology — two clauses is a lecture. Loosens "recast, never lecture"
  the way lore loosened the scenario monoculture; "No Academic Terms" untouched.
- **agy/Gemini is the default studio writer; the Claude subagent is the fallback**
  (2026-07-09). `scripts/run_studio.py` runs Director → Architect → Producer as three
  sandboxed **print-only** agy calls — Gemini never writes a file or sees git; Python
  persists, lints, and renders (the writer-only split, tightened). Chosen for Gemini token
  headroom + long-context writing. The evidence trail: collapsing the passes into one shot
  corrupted anchor lines twice (a semantic inversion, then a -ங்க mutation) — reaffirming
  "the studio's three passes are earned complexity" — and each failure became a permanent
  lint rule (deck-payload verbatim fidelity, Woven-Thanglish density tripwire, self-insert
  fourth-wall labels). Falling back on any lint failure is the contract, not an error.
- **Foundation over performance pieces** (2026-07-09). The goal is generative capacity to
  connect — "I don't need Tamil to survive; I'm doing it to connect" — not memorized set
  pieces for appreciation. Rejects the greenfield review's dress-rehearsal idea (drilling
  the known trip scenarios whole, at speed): frames/engines stay the spine, scenarios stay
  disposable pegs. Also corrects that review's dinner-table framing — the table is one venue
  of a standing relationship, never the goal's center.
- **The studio's three passes are earned complexity** (2026-07-09). Deliberate machinery for
  the hard problem of synthesizing spoken colloquial Tamil, not accretion — reaffirms
  "Producer owns the dialect transformation"; the greenfield review mis-read it as cruft and
  Andrew corrected.
- **The constitution's goal line stands — the dual goal is confirmed** (2026-07-09).
  Stealth-foreigner in public AND family connection are both true and neither edits the
  other: understanding-when-nobody-expects-it (the zinger) is the dopamine engine, and with
  the English-fluent in-laws the visible *trying* is itself the connection win. Rejects the
  "goal drift" concern from the 07-09 review; no canon edit.
- **Push-led weeks are a valid mode, not a lapse** (2026-07-09). A busy week carried
  entirely by knocks and memos still progressed — every memo heard multiple times, "a
  weight lifted" vs the old episode grind. A session gap during an engaged reply streak is
  channel-shift, not fade; refines "a fade is palatability data" — never point
  accountability at session cadence while replies are flowing.
- **The eavesdrop dose — catch gets its own phone channel** (2026-07-09). Catch sat 0/10
  with its only training locked inside the laptop session (the volley disease, untreated on
  the listening side); a knock modality now plays a one-sided phone-call tape in a pinned
  aunty voice and asks one English drift question, and a separate drift-judge lane moves the
  ear-only item's recognition one rung per catch (upgrades only; solid = the deck win).
  Production meters untouched; rides the knock-memo render carve-out and the gossip-tape
  coverage carve-out. Replaces the session-only eavesdrop drill as catch's sole channel.
- **Volley size 3→4; deck tiering rejected** (2026-07-09). Pace ran ~1.5 cold/day vs the
  1.8 the meter demands; Andrew chose a bigger volley over a tiered "core deck" headline —
  the deck is small enough to clear whole and he wants no item deprioritized. Amends the
  07-08 three-item spec; next lever if pace still trails is a second daily volley.
- **The wife channel stays opportunistic** (2026-07-09). Daily/scheduled micro field-missions
  rejected; Anna hands a home fire only when a deck item is ripe and the moment is obvious
  (the 'suvaiya irukku' pattern). The Oracle protections stand unchanged.
- **Speech-in is parked on evidence, not desire** (2026-07-09). Andrew's block is confidence
  that models parse spoken Thanglish, not friction — he does the spoken drills as rendered;
  de-risk with a spike (a few real voice notes through an audio-capable model) before any
  machinery. Rejects building the voice loop straight from the inbox item.
- **Session engagement redesign — pull over push** (2026-07-11). Andrew stopped looking forward to sessions because the protocol optimized for production velocity (reps/minute) at the expense of intrinsic pull. Root cause: the session opened cold into a quiz, had no delight moment built in, and its progress was metered but not narrated. Four protocol changes to `daily_session.md`: (1) warm open with field mission collect + trip countdown before the first rep; (2) mandatory delight beat per scene (mask moment / zinger / lore tangent — structural, not optional); (3) in-session win narration ("adhu dhaan — that one froze you last week"); (4) session closes with one concrete "what moved" sentence and a specific field mission assignment, collected at the next open. Session duration softened to 8–15 min; deck volume stays with the volleys — the session's job is story, engines, and one delight beat. Rejects making more drills the answer to a palatability problem.
- **Notifications stack; replies correlate by knock_id** (2026-07-11). The fixed HA tag
  ("self-replacing — one knock at a time") was a deliberate fence guarding last-fired
  reply judging, and it was eating doses — today's volley logged "no-tap" because the
  lore memo replaced it on the lock screen. Every push now carries its log timestamp as
  `knock_id` (via the notification's `action_data`, the field iOS round-trips); judge and
  ack target that entry, last-fired only as fallback. Replaces the one-knock-at-a-time
  design; `push_queue`'s one-per-tick cap survives as pacing, no longer as the only
  safety. Root-cause trail: `/debug` → KF-9. HA-side YAML must be re-pasted from the
  mirrors.
- **The trailer — recruit the session with unlearned curriculum; discipline stays Andrew's**
  (2026-07-11). The sprint's real bottleneck is upstream: 64 of 71 pending deck items are
  UNSEEN, which the push channel may not quiz (teach-first law) — the pipeline is
  session-teaches → push-drills → cold, and nine push-led days starved it (volley pool: 7
  items; the lore takeover was partly Anna running out of legal asks). The system cannot
  install discipline and stops pretending to: it owns *activation energy and open loops*.
  New no-ask knock move, the **trailer** — pitch ONE unseen item's payoff ("the past-tense
  switch — one letter, and elders notice"), never deliver it in the notification; the next
  session opens by paying it off; one open loop at a time (an unpaid trailer changes the
  bait, never the volume). Replaces thread-nostalgia pulls ("the aunties are waiting") and
  redirects the lore hook's energy from destination to door. **Amends Trip Sprint
  (2026-06-30):** daily terminal session until touchdown, Andrew's own mandate — a finite
  block for a date-certain event chosen while replies flow, NOT accountability machinery
  answering a fade (that stays banned). "Push-led weeks are a valid mode" (2026-07-09)
  stays true in steady state and is suspended for the sprint by the 64/7 arithmetic.
- **Formats drift like content — engagement is evidence, not a mandate** (2026-07-11).
  Engagement with a dose proves its *properties* (surprise, connection, timing), never
  that its format should repeat: the lore memo fired four days running (07-07→10), every
  one a frame etymology — fresh sentences, templated shape. Three-part cause (no
  format-family guard in the variety law; the prompt's own "prefer a deck word's story"
  line funneling the vein; OUTREACH MEMORY reward framing closing the loop) in `/debug`
  → KF-8. Fresh Execution now covers formats; `last_lore()`/7-day cooldown rides the
  `demand_streak` seam (Python counts, the mandate owns the rule); the preference line
  is deleted — vein rotation in its place. Extends "variety is structural" (2026-06-20)
  to the knock channel's format families.
- **A mechanism proposed before diagnosis is a symptom cap** (2026-07-11). The first
  answer to the lore drift was a quota, offered before anyone read the file — the log
  and one prompt line held the real cause, and the better half of the fix was a
  *deletion* only reading the plumbing could find. Exploring a problem includes the
  plumbing; never hand Andrew a choice between mechanisms the evidence hasn't earned.
  Encoded in `/extend` Gate 3 and `/debug` doctrine; refines "explore before
  implementing" and generalizes "fix the tool, not the personality" to proposals.
- **The touchdown bar is two tiers — survival first, delight second, dessert last**
  (2026-07-13). Andrew's own framing the day the trip date went firm (30 days out,
  trailing pace 0.4/day vs 2.0 flat-bar): fast speech *aimed at him* — follow it, repair
  it, transact (antifreeze / public / frames; a fired repair line is a PASS) — outranks
  the visible-trying wins at the family table (faq / mil-table / social); zingers and
  gossip are dessert and soak. Tier ordering + the touchdown bar only — nothing leaves
  the deck. **Supersedes "deck tiering rejected" (2026-07-09)**, which was decided at
  pace 1.5 vs 1.8 with no firm date; the accepted tradeoff: lower-tier items see fewer
  reps until survival ripens. `suggest_targets.py` orders ticket and volley by tier.
- **The daily session's home is the lunch break** (2026-07-13, Andrew's commitment).
  Gives the 07-11 daily-session mandate a fixed slot; knock policy tees up a
  late-morning session bell (trailer / no-ask) and moves collection asks — volley
  included — to the afternoon. Amends the 07-08 "volley's best slot is the day's first
  reach."
- **Respond-under-speed is a session move, not new machinery** (2026-07-13). Directed
  fast speech (an instruction or question fired AT Andrew) is a distinct skill from
  eavesdrop drift; drill it as mask-work at full pace where an antifreeze repair line
  counts as a pass out loud. Rejects a new drill script or meter — parameterizes
  existing mask-work; lives as a profile.md sprint bullet.
- **Scaffold beside the audio, not inside it — the captioned soak** (2026-07-13,
  Andrew's discovery). Listening while reading a glossed transcript snaps
  heard-but-shallow words into form-meaning pairs the ear can't map alone at speed;
  the recurring "too dense — add more English" pressure was pointing at the wrong
  dial. Every episode now ships a caption sheet (`content/captions/<ep>.md` — Tamil ·
  phonetic · gloss, written by the studio from the final script) linked in the feed
  item's show notes. Pass structure: captioned listens until it snaps, then blind —
  blind is the win. Captions are a companion, never a gate (a failed sheet doesn't
  block an episode). The density dial is UNCHANGED pending blind-pass evidence —
  captions do not yet license hotter episodes. *Amended same day after first live use:*
  sheets are **two rows — sound · meaning, no Tamil script** (Andrew: script can't be
  read at follow-along speed; script belongs to TTS, per the standing modality split).
- **TTS text gets defanged at the renderer, not by prompt discipline** (2026-07-07).
  Google TTS voices a hyphen glued to a word as "minus" ("-இட்டு" → "minus ittu",
  done-ittu memo, Andrew's report): `defang_hyphens()` in `render_audio.py` now guards
  all three audio paths (episodes/drills via `clean_for_tts`, knock memos directly —
  memos skip full `clean_for_tts` because it strips sentence periods and would wreck
  memo pacing). Rejects "tell the generator to avoid hyphens": prompt rules drift, the
  renderer is the one chokepoint. Same audit: the unprompted lore-memo knock move is
  validated (9/10 from Andrew) — keep it in rotation under the existing rails.
- **The studio's stray-write tripwire polices only `content/`** (2026-07-13).
  Session-open dispatch + session-close state writes *guarantee* legitimate mid-run
  `progress/` churn, and the whole-tree baseline diff aborted a good episode (M60) over
  it. agy can only plausibly misbehave in the studio's own domain. Replaces the
  whole-tree stray check in `run_studio.py`'s lint.
- **The `lexicon.json` concurrent-write race is known and deferred** (2026-07-13,
  Andrew). `sync_state.py` and `render_audio.py` both read-modify-write it; a session
  close landing inside a render's load→save window is silently lost (last-writer-wins).
  A `flock` over both writers was proposed and deferred, not rejected — revisit when
  sessions and renders actually overlap, or on first evidence of a lost write.
- **Pull before read, push after write — the clone is one of many writers**
  (2026-07-15, Andrew: "more than a best practice, it's mandatory in our design").
  Cloud Anna commits knocks, judged replies, and scheduled pushes to `main` many
  times a day; any laptop session that reads `progress/` without syncing reads
  yesterday's story (a session 14 commits behind re-collected a paid field mission
  and missed the morning trailer — the trip-sprint's laptop-switching makes this
  routine, not exotic). Enforced in the tool, not agent memory: `sync_state.py
  status` fetches and prints a ⛔ STALE banner above everything else; the digest
  also carries the knock thread since the last session, the unpaid-trailer flag,
  and a computed produced-✓/NOT-YET-PRODUCED verdict on the soak order — replacing
  the agent-remembered knock_log read, trailer rule, and drain-check comparison.
  Same audit: UNSEEN teach-first flags now come from one `is_unseen()` definition
  shared by ticket, knock menu, and volley picker.
- **Payload fidelity bends the sidecar, never the script** (2026-07-13; **AMENDED
  2026-08-18 — see "Payload fidelity: verbatim for chunks" below; a plain word now
  matches on its stem, so the repair below is owed only for chunks**). The verbatim
  lint is lemma-literal and false-flags correct inflections (M61 claimed தூக்கு; the
  script's தூக்க முடியல is right Tamil). Repair = drop the sidecar's over-claim; forcing
  a lemma verbatim into a natural line corrupts the rep to satisfy bookkeeping.
- **The Teach Beat — teaching is a defined move, and every medium may teach**
  (2026-07-17, Andrew endorsed the diagnosis by name). The system prescribed drilling
  exquisitely and teaching not at all: first-contact had no shape anywhere in the
  protocol, so it happened as improvised asides — the direct cause of both the
  drip-fed feel Andrew reported and the pace shortfall (63 UNSEEN deck items queued
  behind ~2 sessions/week at 26 days out). First contact now has a canonical shape
  (constitution → The Teach Beat: payoff, one hook clause, 2–3 living contexts, one
  scaffolded rep = SEEN), and the latent machinery becomes doctrine: **seed episodes**
  teach 2–4 unseen deck items (the render's `seen_in` stamp already unlocked them —
  the soak-order may now point forward; studio.md), **knock show doses** teach one
  (`introduces`, built 07-16), sessions teach generously on campaign teach days.
  Supersedes the "unseen deck items are session-only" premise of the 07-11 trailer
  arithmetic. Amends the trailer: unpaid at evening, the knock pays it off itself as
  a show dose ("trailer payoff") — the open loop recruits the session, it never
  withholds the curriculum overnight.
- **The Campaign — the week ahead is Andrew's move, planned in chat, visible in prose**
  (2026-07-17). Continuity was entirely backward-looking (debrief = what happened,
  soak = what just strained); nothing in the system said *what's coming*, and
  anticipation was the cheapest engagement lever it had none of. A campaign = a
  one-week unit from the deck's tiers — name, ~10–14 items, which days teach/drill/
  soak, what each medium carries — **born only in a live session on Andrew's ask**,
  drafted by Anna in chat, adjusted by Andrew, written to `profile.md` → "The
  Campaign — This Week" at close. All mediums steer by it (the knock digest carries
  the block; trailers pitch its next chapter; seed episodes soak its next batch).
  Calendar/cron-driven planning explicitly rejected (Andrew: it must happen in the
  main agent, not a GitHub Action) — cloud Anna reads, never writes. Supersedes the
  "second daily volley" as the named next pace lever (2026-07-09): volley threads
  stall after the first exchange, and the bottleneck was teach bandwidth, not ask
  volume. Also replaces the trailer's random-unseen-item bait with next-chapter bait.
- **Session shapes — the liturgy demoted to a palette** (2026-07-17). The 07-11
  engagement redesign fixed content but froze form: its fixes accreted as MUSTs
  until a 10-minute session carried ~eleven mandated beats — re-creating, as a
  fixed daily liturgy, the sameness it set out to cure ("formats drift like
  content" covered scenes, episodes, and knock formats; never the session's own
  shape). Now three invariants (open on the thread/trailer; honest cold volume;
  Close & Log with one forward hook) plus a rotating named shape — Gauntlet /
  Teach Day / Story / Deep-Dive / Table Rehearsal — no shape twice running, the
  campaign naming tomorrow's so Andrew knows what he's sitting down to. The
  mandatory delight beat is absorbed by the shapes (a Deep-Dive IS the delight);
  the blitz becomes shape-weighted instead of unconditional.
- **Anna narrates the campaign's denominators, never the global deficit**
  (2026-07-17). "Need 2.4/day, trailing 0.7" recited at every touch is guilt
  machinery in a warm voice — a 3.4× deficit demotivates where a small unit
  denominator ("this week's 12: 7 down") activates. The burn rate stays on the
  status line as an engineering number; it leaves Anna's mouth. Refines the
  07-13 touchdown-bar narration; the Enjoyment Clause applies to meters too.
- **Protocol prose is budgeted — subtraction is a mechanism, not a value**
  (2026-07-16). Every incident since April landed as prose, and prose only
  accumulates; "every addition must earn its place" demonstrably did not enforce
  itself (not on the 07-11 redesign, not on the 07-17 walk build). The four prose
  surfaces — `persona.md`, `constitution.md`, `daily_session.md`, the outreach
  mandate — now carry word budgets asserted by smoke case s18 (`PROSE_BUDGETS`,
  the industry size-budget/ratchet pattern): growth past budget is a red run; a
  budget raise must ride the same diff as the growth and the commit names the
  lines it retired; a file that keeps hitting its ceiling is carrying crud or
  doing two jobs — a split-or-retire signal (Andrew). Replaces the unenforced
  prose form of "earn its place" for protocol files (`/extend` Gate 4 carries it).
- **The minimum-law restructure — trust the persona, mandate only invariants**
  (2026-07-16). Over-prescription is a symptom of not trusting the persona:
  pile up mandated beats and you get checklist execution — the bookkeeper voice
  Anna was built to kill. The behavior contract is persona + constitution +
  campaign + ticket, with `daily_session.md` cut 176→~60 lines (invariants,
  shapes, campaign contract, close mechanics; the numbered choreography deleted)
  and the outreach mandate cut ~2360→~1560 words — every incident-hardened rule
  surviving as one operative line, the narrative justifications living here and
  in git history, not in the prompt. Teach-first now has one home (constitution →
  The Teach Beat); other surfaces carry a pointer, plus the compressed operative
  echo the self-contained cloud prompt needs. Completes the 07-17 shapes entry —
  this is its deletion-first half.
- **session_tools.md deleted** (2026-07-16). Five pre-Anna menu formats: roleplay,
  vocab recall, and pattern drill were absorbed by the living scene, the blitz,
  and the Teach Beat; the two survivors — script-reading (kept occasional —
  secondary to the audio-comprehension goals, Andrew) and zinger-crafting — folded
  into `daily_session.md` as one-line moves any shape may reach for.
- **Specials are feed-only — never scene-rotation** (2026-07-17). A `special_*`
  reference tape's sidecar carries a string mission; `load_recent_sidecars()` now
  admits integer missions only. Root cause of the day the ticket and studio dispatch
  went down (the landscape tape's sidecar crashed the sort); a reference tape also
  must not consume a divergence-window slot.
- **The sidecar must claim the soak payload — Python injects it, never trusts the
  whim** (2026-07-17; diagnosed, then fixed same evening under Andrew's discretion
  grant). Registration already resolves canonically (`canonical()` in
  `render_audio.py`), but a frame key is *unrecoverable* from the surface forms the
  Producer writes — so whether the payload reached the sidecar rode LLM whim (M63/M66
  yes, M65/M67 no). Symptoms: seed episodes failed to stamp their frame payloads
  `seen_in` (the Teach Beat's unlock), frame-payload soak orders never showed
  produced-✓ (double-dispatch at session open), duplicate records got born. Fix at the
  correct seam: `run_studio.py` `claim_payload()` after lint — frames inject
  unconditionally (verbatim-exempt), non-frames only when verbatim in the script, an
  absent one is reported, never invented. Tonight's dupes (`-லாமா`/`-ங்க`) merged into
  their frames while stateless; both campaign engines now legally SEEN via their seed
  episodes. Extends "payload fidelity bends the sidecar, never the script" (2026-07-13)
  from over-claims to under-claims.
- **The session is a break first — the day owns the dose** (2026-07-17, Andrew).
  Third felt-signal on the same axis (07-11 "stopped looking forward", 07-17 "starved
  of teaching", now "it's a chore — midday I need a break more"): the session leaned
  extractive at the lowest-energy point of the day. Now canon in `daily_session.md`:
  give-first open (no cold demand until the break has happened), cold volume owned by
  session + volley together, the espresso floor (payoff, three fires, out) is a full
  session, every shape offers a low-power listening twin (catch is the starving axis).
  **Session demotion (phone-loop-as-spine) explored and rejected** — Andrew: the knock
  channel is structurally too thin (volley threads stall after one exchange); the
  daily session stays. Content/delight redesigns of the session are saturated; the
  remaining engagement axis is energy cost, not attractiveness.
- **Felt experience is the primary diagnostic; the ledger is its sensor; @build goes
  evidence-only** (2026-07-17, Andrew). The teach-starvation hole was found not by
  analysis but by Andrew saying out loud "I feel starved of teaching and drilled on
  things you've not told me" — top-down reviews had walked past it. A named feeling,
  however vague, is the system's highest-value signal, and Andrew's returns to @build
  with one are harvest, not procrastination. Wired accordingly: the session's Close &
  Log now banks named feelings verbatim into the feedback ledger (the knock judge's
  meta_note already did — the session was the only channel without the sensor);
  diagnosis.md joins the protocol map; the reply-judge prompts join PROSE_BUDGETS.
  Standing state from here: **the machinery has converged — Andrew drives, Anna
  coaches; new engineering starts only from a reproduced ledger signal or a breakage**
  (the diagnosis bar: one data point is noise, twice is signal), never from another
  top-down pass. *(Amended 2026-07-18 — original read "the machinery is done";
  Andrew: done is observed, never declared — see the 07-18 entry.)*
- **Production is self-healing — the watchdog owns undone studio work** (2026-07-18,
  Andrew-commissioned from the setup audit; **CORRECTED in two later entries:** the local
  cron was paused 07-23 ("The watchdog's premise stands…") and RETIRED 07-24 ("Autonomous
  production lives in the knock tick"), and "cloud-never-renders" was dropped 07-24
  ("Cloud produces episodes") — `studio_watchdog.py` survives as a manual command only).
  Original entry: `scripts/studio_watchdog.py` (hourly local
  cron, awake-check semantics, cloud-never-renders intact) notices a scripted-but-
  unrendered episode (re-lints first; a lint-failing script stops for inspection, never
  renders) or an unproduced soak order, and runs the *existing* dispatch. `.studio.lock`
  is shared with `run_studio.py` so a tick and a session-open dispatch can never stack.
  Ships the parked "self-healing production" inbox item (M65 sat scripted 9 h; two
  session-open dispatches died silently in background). Replaces the human as the only
  retry path.
- **`/anna` opens with an intent gate** (2026-07-18). An engineering-shaped opener routes
  to @build with no persona/protocol load; ambiguous asks get one clarifying line first.
  Three sessions (07-01, 07-16, 07-17) paid the full session boot for zero lesson.
- **`flags.md` is the single owner of command safety** (2026-07-18). The safe/mutating
  inventory and all dry-run semantics live in `/verify` → `references/flags.md` alone;
  `/validate` §3 and `/verify` §4 are pointers. The `morning_knock --dry-run`
  writes-an-MP3 quirk was being maintained in three places.
- **`/recalibrate` bounds pedagogy re-litigation** (2026-07-18). Felt signal captured
  verbatim → settled-check against DECISIONS + ledger → read-only evidence sweep → at
  most one move (diagnosis.md law: dial / prune / gated proposal; default = change
  nothing). ~10 from-scratch re-derivations of "the system isn't landing" across
  June–July earned it. Replaces the unscoped top-down review session.
- **`/backport` codifies milestone re-extraction** (2026-07-18). Last `template-v*-source`
  tag → delta → seam-law buckets (mechanism / dial / language slot / never-ports) →
  apply in the template with smoke → new tag, distill in both repos. Replaces the
  by-hand diff walk of 07-16.
- **The survival tier is the narrated headline** (2026-07-18, Andrew — refines the
  07-13 touchdown bar, which ordered the ticket but left the meter counting the whole
  inventory). 6/69 at a needed 2.5/day read as failure inside a winning sprint;
  6/33 survival at 1.1/day is winnable at the actual trailing pace, and survival is
  the tier that decides freezing at the table. Nothing leaves the deck; the full-deck
  count stays on the status line; delight is the celebration lane as survival clears.
- **Every campaign names catch targets; eavesdrop is normal rotation** (2026-07-18).
  Catch starved structurally (0/12 solid, one tape ever cut) because campaigns only
  named fire targets and the mandate framed the eavesdrop dose as exotic. Campaign
  contract + mandate now carry the bias; the Ask-Machine block gained its catch line
  (quote-nu, hearsay-aam).
- **Drills stay opportunistic; voice-IN stays parked** (2026-07-18, Andrew). The
  Thanglish-mangling fear belongs to the parked voice-IN spike — the drill track
  hears nothing (speech-OUT only), so it was never blocked by it. Anna cuts one when
  the deck's due list runs fat; never a daily obligation (the chore signal governs).
  Typed cold proves retrieval; the drill is where articulation catches up.
- **The content surfaces audited clean — the gaps were delivery, not law**
  (2026-07-18 pristine-pass audit). persona/constitution/daily_session/studio prose
  is coherent, cited, and budget-policed; the three real repairs (survival headline,
  catch bias, drill usage) were all delivery of machinery already built. Reinforces
  07-17: no more top-down prose passes — the ledger steers.
- **"Done" is observed, never declared** (2026-07-18, Andrew). The 07-17 entry's "the
  machinery is done" overstated the ruling: the system is maybe 80% converged, and
  things that sound off — technical and pedagogical both — will keep surfacing for
  weeks. Converging toward no-more-engineering is a trailing sign of maturity, not a
  call anyone makes in advance. The operational bar is unchanged (reproduced ledger
  signal or breakage; never a top-down pass); what changed is the posture: expect
  bugs, keep the discovery channels warm, and never treat a quiet week as proof.
- **The fielding dose — the stimulus half of the exchange gets a channel** (2026-07-18,
  Andrew, commissioned from the blank-slate exercise). Every production channel handed
  him an ENGLISH situation; the table hands him a TAMIL question at speed, and nothing
  trained heard-question → produced-answer. New knock modality "fielding": one short
  question in the family voice (audio — the 95% rule applies: parse it, don't drift it),
  lock-screen body carries the question in English phonetics (Andrew reads phonetics at
  speed, Tamil script not at all — his note, mid-build), reply graded by the normal
  production judge, and a fired repair line is a PASS, never a miss. One mechanism
  feeds both starved sides: ear training with a production payoff. Smoke: s20. The
  sibling finding (the trip-as-harvest arc) parked in the inbox with trip context.
- **Respect loud, jaw-drop quiet** (2026-07-18, Andrew — noticed while writing the
  public journey piece). The motive hierarchy is connection and earning respect at
  her family's table; the reveal/zinger dopamine is dessert, never the meal.
  persona.md's Heist and the constitution's goal line re-anchored; the touchdown
  tiers had already voted this way (delight = the visible trying; zingers capped at
  "five is greed"). The heist mechanics — secrecy, the safe room, field missions —
  stand unchanged; only the stated why moved.
- **Python re-presents what Python tracks — the volley surface is plumbing** (2026-07-18,
  KF-11; root cause corrected same day on Andrew's catch). The initiating defect was
  code, not judge discipline: `judge()` passed a body frozen at ask 1 while the pin
  walked, so the KF-3 coherence safety net *lawfully voided the pin* from item 2 onward.
  Now `volley_open_ask()` is the single owner of the current ask — the judge grades
  against it, chat verdicts re-present it, `volley_done` closes the chain, and the
  mandate forbids improvising the surface. Extends the 2026-07-06 "grounded verdicts"
  law from state to surface: whatever Python tracks, Python says — to the judge too.
- **The menu is open — invention is inside Anna's authority** (2026-07-18). Content
  space is zero-blast-radius (purged, meterless; no rep moves without a judged reply),
  so a one-off dose or episode shape needs no new machinery and no permission — the
  named formats become precedents, not a closed list, and the variety law owns an
  invention the moment it repeats. Replaces the implicit closed-menu reading of the
  modality and form lists; extends "Formats drift like content" (2026-07-11) from
  guarding repetition to licensing invention.
- **The narrated drama is a real form** (2026-07-18, Andrew — by ear, on the M68
  "Midnight Suitcase" experiment). It succeeded where the months-ago attempt failed;
  what changed is the substrate (fence + soak-order + scene spec + unified memory), so
  the format rides the system now instead of replacing it. Long-form is the
  **batch-soak channel**: ~15–25 items bought with minutes, tiered teach-first /
  cold-engine / ear-only. Commissioned by Anna via soak order (`form:
  "narrated_drama"`, `scale: "long"`); **not** in the rotation gate until several
  episodes prove it. Deck/meter accounting is normal — `seen_in` already handles a
  batch episode like any other; no special-casing.
- **Narration obeys Tamil-script-only** (2026-07-18). The M68 demo's Latin phonetics
  were a pipeline bypass, not a style: every ta-IN voice reads Latin as English
  orthography. The `hosts.md` rule already covers this; the drama form adds no
  exception — the dialect pass stays dialogue-only, narration takes the integrity
  checks (`producer.md`).
- **A re-render bumps the filename; SFX cues render as air** (2026-07-18). RSS guid =
  audio URL, so an in-place audio replace serves cached bad audio (April's cache war) —
  a fix re-renders to `_vN`, deletes the old mp3, and the feed resolves `_vN` back to
  the base script for title/captions (mission parse reads the *script* name, so state
  registration is untouched; the watchdog counts a `_vN` file as rendered — its
  exact-name check resurrected the old-guid mp3 within the hour of the first bump). And
  `[SFX]` lines, which the renderer silently dropped,
  now become a 1.5 s beat (smoke #8) — a cue buys air, never silence-vanishes; a real
  SFX library stays unbuilt.
- **Second milestone re-sync — `template-v3-source`** (2026-07-16; recorded 2026-07-19,
  backfilled — the sync pre-dated `/backport`'s distill contract). language-tutor now
  elaborates Tamil@`3e6c12e`: the knock-loop engine advance since v2 re-applied
  semantically — knock_id reply correlation (KF-9), fenced-JSON parse fallback (KF-10),
  lore/eavesdrop cooldown guards, teach-first `introduces` + shared `is_unseen()`,
  pull-before-read status banner, delivery retry, deck-tier ordering. The seam law held
  and produced one template-side correction, recorded there: "learner-dependent surfaces
  are setup-time elaborations" (deck tiers ride `config` + SETUP.md, never hardcoded).
- **One declared play — setup-and-payoff across surfaces, no new machinery**
  (2026-07-18). Anna may hold ONE play — a planted setup one surface pays off on
  another — declared as a sentence in the debrief, closed or abandoned on evidence;
  it is an open loop and shares the trailer's one-open-loop law. Generalizes the
  trailer (2026-07-11) into the play's simplest form; continuity stays prose
  (no schema, per 2026-06 continuity decision). Third grant in this family —
  proposal authority (Anna drafting protocol diffs for the diagnosis pass) —
  deliberately deferred to post-trip.
- **The year's LLM-systems doctrine is promoted to `~/.agents/AGENT.md`**
  (2026-07-19, wrap-up session). Six rules that generalize beyond this repo —
  writer/brain split, prompt separation-of-concerns, mechanism-and-test over prose,
  the felt-signal ledger discipline, structural variety, honest meters — now live in
  the cross-agent global canon, each condensed to one operative line with this repo's
  DECISIONS/JOURNEY as the evidence trail. Replaces re-deriving them per repo; the
  full narratives stay here. (`~/.agents` is not under version control — noted to
  Andrew as a gap.)
- **Third milestone re-sync — `template-v4-source`** (2026-07-19, run on Andrew's
  ask ahead of the public post — the sync policy's own "before actively sharing"
  trigger). language-tutor now elaborates Tamil@this tag: fielding dose, KF-11
  volley surface, campaign (block + digest + seed orders), mandate subtraction
  (including the KF-8 lore-preference deletion the v3 sync missed), Teach Beat +
  Play canon, minimum-law daily_session (session_tools deleted), narrated_drama,
  tier-0 deck headline, SFX beat, _vN feed resolution, ticket crash guard,
  /recalibrate + intent gate + one-owner flags + KF-9/10, prose budgets
  (template-measured), and smoke parity s14–s23 — the v3 sync had shipped
  mechanisms without their regression cases; that gap is closed. Deliberately
  left behind: `claim_payload()` as code (no deterministic seam in the
  agent-dispatched template studio — it landed as producer.md prose, flagged as
  a known gap in the template's DECISIONS), the watchdog + lunch anchor
  (learner/local pack), /backport (this side of the sync).
- **The constitution reads operative-only** (2026-07-19, Andrew-commissioned wrap-up).
  Crisping pass ahead of daily driving by Opus/Sonnet: narrative justifications retired
  to this file's existing entries (each named in commit 31a87e2), dates moved into rule
  headers, headroom 24→81 words. Completes the 07-16 subtraction law for the
  constitution; `daily_session.md` (12 words free) and the outreach mandate (12 words
  free) are the next ceiling-huggers — split-or-retire is *their* next move, not a
  budget bump.
- **`clean_for_tts` no longer strips sentence periods** (2026-07-21). The strip
  flattened multi-sentence TTS lines into one breathless run-on and swallowed the tails
  of short sentences (surfaced in the Anna-intro demo: "He's strict... The arrangement
  works" cut off). Fixed at the source in `render_audio.py`, so it heals the real
  episode and drill paths too, not just the demo. Supersedes the period half of the
  2026-07-07 memo note: memos still use their own `clean_memo_for_tts` (it also skips
  paren/bracket and JSON/CLI handling), but no longer *need* to on account of periods.
  Deleted the `clean_keep_periods` workaround that render_demo.py carried for one day —
  root fix retires it.
- **Capacity routes the audio channel; the curriculum only fills it** (2026-07-23,
  Andrew's felt signal). Exhausted after a day of paperwork he asked for "a longer drill
  to listen to at the park — repetitions, iterating over words and endings, mental
  autopilot" and received a dense 10-minute two-voice scene: `scene_spec()`'s only input
  is divergence from the last 3 episodes, and Anna's skill routed *every* audio ask to the
  studio. The soak order decides what a dose carries; what his attention is free to do now
  decides which channel carries it (`protocol/audio_channels.md`). Explicitly does NOT
  reopen "variety is structural" (2026-06-20) — capacity picks the channel, divergence
  still picks within the episode. The routing was **split** into its own file rather than
  bumping `daily_session.md`'s budget, per that file's own 07-19 ruling ("split-or-retire
  is *their* next move, not a budget bump"); it came out 22 words leaner than before.
- **The soak loop is the third audio channel** (2026-07-23). The episode demands
  comprehension and the drill demands speech; neither serves an ear on autopilot in
  company, which is most of when Andrew actually has headphones in. `render_soak.py`:
  Python owns the rhythm (Tamil → gloss once → Tamil → Tamil, then a Tamil-only echo of
  the whole thread), the model only clusters this week's surfaced items by shared ending
  and glosses them. Replaces "stretch an episode when he wants something longer" — the one
  lever that responded to the park brief, and the one that widened the mismatch.
- **A clock-bound request must produce a queue entry, never an acknowledgement**
  (2026-07-23). The 9am greeting was never scheduled, and the runner was not at fault:
  it had `contents: write`, both secrets, and a working `maybe_enqueue_schedule` path. The
  judge mandate called scheduling "optional … null to skip, which is usual" and routed
  system-direction into `meta_note` — a ledger note for a human to read later. Anna
  followed her instructions exactly. The mandate now makes a clock-bound ask MANDATORY and
  `wants_scheduled_push()` forces one re-ask when Python catches the contradiction; prose
  had already failed here once, so the detector is the mechanism.
- **The cloud cannot render bespoke audio, and Anna must say so out loud** (2026-07-23;
  **CORRECTED then RETIRED 2026-07-24 — see "One runner, every capability"**). Original claim: the audio ask was
  "unfulfillable end-to-end by design (cloud-never-renders)." False — the knock workflow
  renders audio in the cloud *every day* with `GCP_SA_KEY`. The real limit is a WIRING gap:
  `push-queue.yml` was never given the TTS secret or a render step, and `maybe_enqueue_schedule`
  is text-only. So audio-at-a-scheduled-time is entirely achievable in the cloud; it just
  isn't wired. Anna's "I can't render bespoke audio" line is therefore PROVISIONAL — relax it
  once the schedule lane carries the renderer (inbox: the 9am-audio lane). See "Cloud produces
  episodes" below.
- **An unattended production trigger must be verifiable, and capped regardless**
  (2026-07-23). A soak payload of `avasaram` can never match the lexicon key
  `அவசரம் இருக்கு`, so the produced-check stayed False forever and the hourly cron shipped
  M72, M73 and M74 in one evening — three episodes nobody asked for, while Andrew was out.
  `split_payload()` resolves headword→chunk and drops genuinely unverifiable tokens (Tamil
  script and `frame:` keys still pass: a brand-new payload word is legitimately
  pre-lexicon). `MAX_UNATTENDED_PER_DAY = 1` bounds the rate whatever the next stuck
  trigger turns out to be — rate is now a rail, not a hope.
- **Feed durations are measured, never estimated** (2026-07-23). The 07-22 frame-scan fix
  was wrong in *both* directions — M69 +40%, M73 +37%, M72 +32%, M74 −16% — because one
  bad header desyncs the walk and it resyncs a byte at a time, recounting. M72 was
  announced to the feed as 13:12 for a 10:04 episode, and Andrew judged the episode partly
  by the number his podcast player showed him. `rebuild_rss` now uses ffprobe — the same
  authority `episodes.json` already used — with the scan as fallback. Honest meters or none.
- **Concurrent renders are safe by construction; a commit carries only its own episode**
  (2026-07-23). `temp_audio_segments/` was a fixed relative path shared by every render, so
  whichever finished first `rmdir`'d it out from under the other; that raced the watchdog
  mid-render and cost a draft episode, which `git add content/captions/` had already swept
  into an unrelated commit. Now: per-run `mkdtemp` with `try/finally`, the state tail under
  `.studio.lock` with `STUDIO_LOCK_HELD` inheritance so a child never deadlocks on its
  parent, and staging by explicit filename. `.studio.lock` had only ever guarded
  *dispatches* — the renderer is the thing that mutates state.
- **The watchdog's premise stands; its 07-18 reliability claim does not** (2026-07-23,
  Andrew: it "snuck in"). Provenance: parked in the inbox's unendorsed `## Ideas` tier on
  07-17, shipped the next day inside four-feature audit-night commit `4fe6017`. Five days,
  four actions: two clean, one needing a same-day patch (`_vN` resurrection put a stale
  GUID back in the feed), one outright failure that destroyed a draft. Local-not-CI is
  right and the session-open drain stays primary. The cron is **paused** pending Andrew's
  call; it now preflights, caps its rate, and skips cleanly on a host without secrets.
  Amends — does not replace — "Production is self-healing" (2026-07-18); that entry's
  mechanism survives, its "replaces the human as the only retry path" does not.
- **Cloud produces episodes — the "never renders" rule is dropped** (2026-07-24, Andrew).
  The 2026-06-15 rule was misnamed: the cloud renders knock memos daily, and the real
  reason episodes stayed local was the *writer* (`agy`, a local CLI absent from any GitHub
  runner), never the renderer. With the writer made executor-agnostic, the cloud can
  write → render → publish. Supersedes "Cloud never renders episodes" (2026-06-15). The
  foundation shipped this session; the autonomous trigger is the remaining build (inbox).
- **The studio writer is executor-agnostic; the cloud writer is a single-shot call with
  Python-inlined canon** (2026-07-24). `agy` locally (Andrew's standing Gemini quota),
  OpenRouter → `google/gemini-3-flash-preview` in the cloud. Chosen over putting a real
  agent in the runner because it is the exact pattern Anna's knocks already run on — a
  single `chat.completions` call with Python inlining `persona.md` + state — and it is
  ~100× cheaper than agent-loop token volumes. The key realization: **Anna is a single
  concatenated prompt, not a file-reading agent** — he "knows the canon" because Python
  reads the files and bakes them in. `inline_canon()` does the same for the studio, using
  each pass's own `protocol/…md` references as the manifest so prompt and files never
  drift. Rejects: installing/authing an agent CLI in the runner ("feels more authentic"
  lost to the code — the single-shot is correct and cheaper).
- **Autonomous production lives in the knock tick; Anna (he) chooses when, Python caps it**
  (2026-07-24, Andrew — two explicit choices: "inside the knock tick" and "Anna decides,
  capped"). Not a second scheduler, not a fixed cadence. The local watchdog cron is
  RETIRED; the cloud knock tick (already `github-actions[bot]`, already waking-hours +
  daily-cap aware) gains an `episode` move gated by `soak_pending()` +
  `MAX_UNATTENDED_PER_DAY`. Replaces the local-cron approach whole. Build steps in the inbox.
- **Machine commits masquerading as Andrew are acceptable for now** (2026-07-24, Andrew's
  ruling). The ambiguity is automated-vs-human-initiated, not laptop-vs-cloud: cloud commits
  already self-label `github-actions[bot]`; only the (now-retiring) local cron ever committed
  as Andrew unattended, and retiring it mostly dissolves the issue. Closes the "should machine
  commits carry a machine identity?" question — no self-labeling machinery to build.
- **CI tests stay hermetic — never depend on ambient credentials** (2026-07-24). The smoke
  runner carries no secrets by design; a test that only passed with real GCP credentials went
  red on CI — the very credential-less host the graceful-skip feature exists for. Tests mock
  credential presence/absence (`google.auth.default`), never require live keys. Root cause of
  the 2026-07-24 red build.
- **One runner, every capability — the three workflows are one** (2026-07-24, Andrew).
  `morning-knock.yml` + `log-knock-response.yml` + `push-queue.yml` → `anna.yml`, with
  job-level `env` carrying every secret to every lane. The three grew separately and each
  got exactly the secrets its first job needed (knock: GCP + OpenRouter; reply: OpenRouter;
  drain: neither), so *what Anna could do depended on which event woke him* — an accident
  of file layout, not a design. Andrew's framing: "these are first-class tools regardless
  of what was the input waking Anna up." Consolidation makes the capability structural
  instead of remembered — you cannot forget to wire a lane that does not exist. Rejected: a
  composite action for the shared setup (composite actions **cannot read the `secrets`
  context**; each caller must pass them in, so the forgot-to-wire bug survives) and a
  `workflow_call` reusable workflow with three thin callers (correct, but ceremony for a
  solo-operator repo).
- **The drain runs first on every wake-up; one hourly cron** (2026-07-24, Andrew). The
  queue drain is no longer a lane, it is the opening step of every Anna wake-up — hourly
  tick, lock-screen reply, manual dispatch. Ordering is load-bearing: the drain logs its
  fire into `knock_log.json` and `rails_gate` counts today's reaches, so a scheduled push
  correctly suppresses an ambient knock in the same tick (drain-LAST would double-push).
  Three cron expressions across two files (`0 12,14,16,18,20,22` + `0 0` + `*/30`) collapse
  to a single `0 * * * *`: the rails already do the DST-correct waking-hours filtering and
  skip a tick with no LLM call, so the cron only has to be frequent enough to filter. The
  lost delivery precision (30 min → 60 min worst case) is more than repaid by replies and
  dispatches also draining.
- **A scheduled dose may carry voice; TTS runs at fire time, not add time** (2026-07-24).
  `memo_script` on a queue entry makes it a voice dose; the drain renders it and fills
  `audio_url` itself. Composed-at-add-time was never the same law as rendered-at-add-time —
  `push_queue.py`'s invariant is *no LLM at fire-time*, and TTS is not an LLM. Rendering in
  the reply lane instead was rejected on latency: Andrew is standing at the lock screen
  waiting for the recast, and TTS + commit + CDN pre-warm is a minute-plus on the one
  channel that must feel instant. The mp3 is committed in its OWN commit before the
  notification fires (jsDelivr can only serve what is already on `main`), which also keeps
  the drain's retry property — a failed push leaves the entry queued.
- **A dropped rule must be hunted through code, prompts, skills and tests** (2026-07-24).
  "Cloud never renders" was marked SUPERSEDED in this file at 09:55 and Anna went on
  refusing bespoke audio until 21:00, because the rule also lived in `JUDGE_MANDATE`, in
  `FORCE_SCHEDULE_ADDENDUM`, in `/extend` Gate 6, in `routing.md`, in `subsystems.md` — and
  as a smoke assertion that *required* the refusal text (`"cloud-never-renders" in
  JUDGE_MANDATE`). A guard that outlives its rule enforces the rule. Correcting DECISIONS is
  the start of retiring a rule, never the end.
- **The clock-request detector's verb list is deliberately wide** (2026-07-24). "Schedule a
  push and say hello" — the most literal possible phrasing — matched the clock and missed
  the verb, because `schedule` was absent from `ASK_RE`. The backstop built the day before
  for exactly this failure never fired, and an 8pm greeting was silently dropped for the
  second day running. A false positive costs one re-ask; a false negative costs Andrew a
  push he asked for and never got. Widen on sight.
- **Anna answers aloud; the agentic loop closes** (2026-07-24, Andrew). Both reply paths in
  `knock_reply.py` called `push_to_phone(body, None, ...)` — `audio_url` hard-coded — so
  Anna could speak TO Andrew on a knock but never BACK on a reply. The renderer was never
  the blocker; the reply workflow simply had no TTS secret until the workflows merged, so
  this landed as ~30 lines on top of that. The judge may now return `voice_reply` and Python
  renders it into the same push-back. **Rationed by prose, on purpose:** TTS + commit + CDN
  pre-warm costs ~90s while Andrew stands at the lock screen, so the mandate reserves it for
  answers where the SOUND is the answer (pronunciation, a greeting for someone in the room)
  and keeps ordinary recasts instant. Andrew accepted the latency explicitly ("it doesn't
  need to be faster, that's not the purpose"). A TTS failure still delivers the text —
  silence is the one unacceptable outcome. The catch (eavesdrop) lane stays text-only; its
  smaller mandate is deliberately separate.
- **A mandate at its ceiling gets split, not raised** (2026-07-24). `JUDGE_MANDATE` sat at
  1498/1500 words when the voice-reply rules needed to land. Rather than bump the number,
  the three paragraphs about reaching *beyond the text line* (schedule a future push, speak
  back now) moved to `REACH_MANDATE` with its own budget — the same move
  `protocol/audio_channels.md` made on `daily_session.md` (2026-07-23). The judge sees both
  concatenated, so the model's prompt is unchanged in substance; the budget now guards two
  concerns separately instead of one blurred one. JUDGE_MANDATE fell to 1388 while GAINING
  a capability, which is the test a split should pass.
- **Every pushed dose lands in the feed, and the feed carries only playable audio**
  (2026-07-24, Andrew — extends "All audio lands on the podcast feed", 2026-07-05). His
  ruling in full: *"all audio you push me should go in the feed… if I dismiss something I
  want to be able to go and easily play it back"* — the lock screen is ephemeral, the feed
  is the archive. Feed pollution is accepted explicitly (he is the only consumer and this
  is an experiment); **unplayable entries are not** — a dead item he taps is worse than a
  missing one, so `rebuild_rss` now enforces a size floor rather than trusting the `.mp3`
  extension (a truncated render or an lfs pointer passes the extension test). This settles
  the open question about whether short spoken replies belong on the feed: they do.
- **The feed learned the two new audio producers** (2026-07-24). `published_audio/knocks/`
  now has three writers — `knock_` (ambient), `queued_q<id>_` (a scheduled dose rendered at
  fire time) and `reply_` (Anna answering aloud) — but `rebuild_rss` only ever knew
  `knock_`, so the two new kinds titled as their raw filename and sorted to `(0, 0)`, below
  every episode in the feed. Titles now name the kind; the move label resolves from `mp3`
  OR `audio_url` (the knock lane logs a repo path, the drain and reply judge log only the
  CDN url they pushed). Found by auditing the day's own diff — the shipping sessions never
  looked downstream of the filenames they invented.
- **Feed order is a function of the library, not of `os.listdir()`** (2026-07-24). The two
  `special_` files both score `(10, 0)`; ties fell through to filesystem order, so a
  rebuild on a different machine silently swapped them and produced a feed diff that looked
  like a real change and wasn't. Filename now breaks the tie. Latent since the specials
  were added; surfaced by rebuilding in a cloud container instead of on the laptop.
- **A published item's title is part of its identity — Apple Podcasts forks on a retitle,
  stable guid or not** (2026-07-25, confirmed against Andrew's client). The 8pm dose of
  07-24 arrived correctly and then appeared TWICE: one copy `Scheduled — 2026-07-24 23:56`,
  one `… · welcome james`. Same guid, same enclosure, same pubDate, one `<item>` in the
  feed at every moment — the fork happened entirely inside the client, 4h16m after
  publication, when an unrelated lane rebuilt `rss.xml` and picked up a move label the
  original write couldn't see. So the feed invariant is not "one item per dose", it is
  **an item is immutable once published**; `existing_pub_dates()` had been enforcing the
  weak half of this since the pubDate-reset bug, one field early. Rejected as the fix: a
  title freeze in `rebuild_rss` mirroring `existing_pub_dates()` — it guards the class but
  adds a second mechanism for a bug whose only cause is known and cheaper to remove, and it
  would make a legitimate title correction impossible. Logged as a residual instead.
- **A published feed item is measured once and frozen — duration joins pubDate**
  (2026-07-25, Andrew: *"the exact number isn't important anyway and the oscillation needs
  to stop"*). Duration described bytes that never change, yet was re-derived on every
  rebuild from whatever tool the host had. The laptop has ffprobe; the CI container does
  not, so `audio_duration` fell through to its pure-python frame scan — which on these
  files (TTS segments concatenated with `SILENCE_FRAME` copies, where one bad header
  desyncs the walk) misreads by **up to 40%, in both directions**: 68 files, median error
  4.8%, only 35 within 5%. Proven in the feed's own history: the 07-23 ffprobe fix landed
  correct numbers from the laptop at 23:27, and the very next cloud rebuild (`91c5d0f`,
  07-24 22:56 — an agent commit) reverted the library wholesale. M72 announced 13:12 for a
  10:02 episode for two days. Andrew's framing is the one that generalises: **the estimator
  was never the bug — recomputing a published value was.** So `existing_pub_dates()` becomes
  `existing_items()` and carries both fields; a rebuild republishes what was published. This
  is the same immutable-once-published rule that the Apple retitle fork settled, applied to
  the field that was still moving. Safe because a corrected render takes a new `_vN`
  filename, hence a new guid and a fresh measurement — in-place edits aren't a thing here.
  ffmpeg is now installed in `anna.yml` so a NEW item's first measurement is honest (the
  runner-images manifest confirms ubuntu-24.04 ships none; MediaInfo is the only media tool
  present), but it is deliberately `continue-on-error`: with the freeze it only has to be
  right once per file, and it must never cost Andrew a knock. Verified by rebuilding with
  `ffprobe_duration` stubbed to `None` — the exact CI condition — and diffing: byte-identical.
  **Not installed on `repository_dispatch`** — that is the lock-screen lane, and ~20s of apt
  in front of a recast would have re-broken the latency constraint that already keeps
  rendering out of the reply path. Caught as a self-inflicted regression the same night it
  shipped. The accepted cost: a voice reply's duration is first measured by the frame scan
  and frozen there — a few seconds on a ~19s clip, on the one lane nobody browses by length.
- **The feed is stamped in Andrew's zone, never the host's** (2026-07-25). `rebuild_rss`
  used `formatdate(localtime=True)`, so the offset was a property of the rebuilding machine:
  the laptop wrote `-0400`, the CI container `+0000`, and the feed carried two faces for one
  listener in one timezone. Nothing was ever *wrong* — the instants agree — but a dose should
  be announced in the zone it is heard in, and `LOCAL_TZ` was already canonical in
  `sync_state.py` for exactly this. Both stamp sites (episodes and the demo item) now use
  `format_datetime(fromtimestamp(mtime, LOCAL_TZ))`. Existing entries are NOT restamped:
  `saved_dates` short-circuits first, so a rebuild changes zero published pubDates (verified —
  the only lines a local rebuild touches are durations, see below). Smoke asserts the stamp
  under a forced-UTC host.
- **Andrew's timezone is a field in `learner.json`, not a constant in source** (2026-08-09).
  `LOCAL_TZ` was already the one definition every clock-facing rule read, but it sat in the
  state layer as `ZoneInfo("America/New_York")` — making the switch on landing day a code
  edit from an airport. It now reads `learner.json.timezone` via `_resolve_local_tz()`;
  `DEFAULT_TZ` covers a silent profile. The read was four lines; the work was three silent
  New-York assumptions elsewhere: `write_thin_learner`'s delete-on-omit whitelist (omitted
  there, the first update after landing restores the home clock — the trap that ate
  `slip_closes`), smoke's quiet-hours case built from a frozen UTC instant, and a pubDate
  guard hardcoding `-0400`. A bad zone falls back with a stderr complaint rather than
  crashing every unattended lane; that fallback being a valid zone is why `session_brief`
  now names the live one. **Not built:** travel days still read as fades — scoped out.
- **`anna.yml` must not run on push; the gap it leaves is closed by linting, not by running**
  (2026-07-25, Andrew asked whether it could be closed). A push-triggered Anna would drain the
  queue, judge replies and notify Andrew's phone on every commit — a side effect, not a test.
  So the file is exercised by nothing until its next hourly cron, which is how it sat
  unrunnable through four pushes on 07-24 while `smoke.yml` went green beside it. The residual
  gap is narrow: `smoke_test.py` already covers script-level regressions at push time against
  sandboxed copies, so the only thing uncovered was *the workflow file being unrunnable*.
  `actionlint` (pinned 1.7.7, release tarball, not a `curl|bash` of a moving branch) now runs
  in `smoke.yml` and closes exactly that, statically and without side effects. Verified against
  the real broken file: it flags the `runner` context at line 65 with the same legal-context
  list the hand-rolled guard hard-coded. **Retires** that guard (the s29 context whitelist);
  s29 now asserts only that the linter is still wired, since this suite also runs locally where
  actionlint may be absent.
- **The drain rebuilds the feed AFTER the knock log, like every other lane** (2026-07-25).
  Root cause of the fork above. `rebuild_rss` titles a dose from `knock_log.json`, and the
  drain called `refresh_feed()` in its mp3 commit — three lines before the log entry exists
  — so it published a label-less title and never wrote the real one at all; the correction
  waited for whichever lane rebuilt next. `morning_knock` (`:900`→`:909`) and `knock_reply`
  (`:843`→`:864`) already ordered it log→feed→commit; the drain was the sole violator, and
  only because its legitimate two-commit split (mp3 first, so jsDelivr can serve the CDN
  pre-warm) swept the rebuild along with the mp3. Restoring the invariant moves one call and
  adds no state. The mp3-first commit and the retry property are untouched. Smoke s29 now
  records the log's contents at rebuild time, so a rebuild-before-log is red.
- **The catch judge grades the thread, not the turn** (2026-07-25). Root cause of two false
  `half-caught` verdicts on the 07-25 tape: the drift judge saw only the latest reply, so it
  could not know turn 1 had already caught the drift, and it graded a reply carrying *a catch
  plus a hint question* as one blended weak answer. The production judge has had per-element
  grading since 2026-07-03 ("one shaky word must not drag down a clean one") and
  `prior_exchanges` since 07-06; the catch lane inherited neither when it was split out on
  07-09. Now it gets both: once caught, the drift stays caught, and a question never lowers a
  grade. **Retires** the mandate clause that classified "a question" as `chat`.
- **A request to be taught is a first-class reply, on the phone too** (2026-07-25). Andrew
  asked for a line-by-line breakdown of a tape and the judge answered "that's a system note,
  not a drift answer" — the mandate's `No lecture, no replay-homework` rule made refusing
  correct. Answering a hint/translation/breakdown request is now explicit, narrowing that rule
  to replay-homework only. Extends profile.md's "meta is curriculum" preference (2026-07-15)
  from the session to the knock channel, where it had never been stated.
- **An eavesdrop tape must name its subject in the opening, or it isn't a dose** (2026-07-25;
  **the degrade-to-text remedy SUPERSEDED 2026-08-01 — a defective eavesdrop is now refused,
  see below**).
  Gossip grammar hides the referent by design — an unnamed respectful `அவங்க` plus the `-ஆம்`
  hearsay tail is *how* you talk about people without naming them — so a tape built that way
  cannot be asked "what's the drift?" and Andrew's "who came?" was the correct question with no
  answer in the audio. `frame:youknow-la` ("நம்ம X இருக்காங்கல…") is the opener that exists to
  plant it. Python now degrades a referent-less tape to a text dose rather than push an
  unanswerable one; the window is the opening two paragraphs, because a real call greets first
  and because a whole-tape check passes the exact defective tape (it says `அக்கா` in paragraph
  four — as the *source*, not the subject). A lost dose is cheaper than a wrong verdict.
- **When Andrew's account contradicts a logged verdict, the verdict is the suspect**
  (2026-07-25). Both the profile's "-aam watch, three misses" and this session's first summary
  came from reading `reply_verdict` instead of `reply` — the learner's own words were sitting in
  the log saying he had caught it. A judge verdict is *evidence*, generated by a model with a
  known failure mode; the learner is the court of appeal (already the rule for state, now the
  rule for reading history too). The 07-16 and 07-19 "misses" are flagged as suspect for the
  same reason: both tapes also named nobody in their opening.
- **Deck selection is coverage-first within a tier; the meter reports coverage beside
  progress** (2026-07-25, Andrew's felt signal: "my worry is we are still starving some of
  these"). `deck_status` ordered by tier → ripeness → **alphabetical**, with no staleness
  term, so the head of every tier was frozen: 16 frames took 51 of the deck's 74 lifetime
  reps and cleared 14/16, while 50 of 70 fire items had never been worked at all (45 of them
  never even appearing as an ask in any log) and the two survival registers that decide
  freezing at the table sat at antifreeze 1/10, public 1/8.
  Ripeness-first is rich-get-richer — an item becomes `hinted` only by being worked, which
  promotes it again — and the alphabetical tiebreak sorted ASCII `frame:` keys ahead of
  every Tamil-script chunk. **Fourth recurrence of one failure:** KF-6 (2026-07-06) added a
  3-day ask demotion, the binding volley picks (2026-07-08) moved the farming from Anna's
  taste to the sort key, and `render_drill.deck_due_payload` had already hand-interleaved
  frames and chunks around it — each a local patch in the channel where it was noticed,
  because "no item starves" was never expressed as a property of the shared selector. Now
  `deck_status` sorts least-recently-worked first *within* a tier (the same `-staleness`
  law `floor_gap_targets` has always had; `last_surfaced` is the shared definition), ripeness
  demoted to a tiebreak, catch_pending under the same law — every channel that reads the
  selector is fixed at once. The tier prefix is untouched: **survival still outranks delight,
  and delight/dessert starvation remains the accepted 07-13 touchdown-bar tradeoff**, not a
  bug. Teach-first is untouched — rotation lifts UNSEEN items onto the *ticket* to be taught,
  and `volley_targets` still excludes them from cold quizzes. `recent_ask_counts` **stays**:
  an ask with no reply never sets `last_surfaced`, so it guards a genuinely different gap.
  Second half, the meter: every meter counted `cold/total` and none counted `worked/total`,
  so the headline read 15/34 survival at 3.4 cold/day against a needed 1.1 — a won sprint —
  while most of the deck had never been touched. `deck_coverage()` reports worked/total per
  tier and per register on the ticket, and `compute_deck` carries the count onto the status
  line, the update summary, and the dashboard. Refines "the survival tier is the narrated
  headline" (2026-07-18): that entry fixed a demoralizing denominator and the new one hid a
  distribution — honest meters must show both. Smoke `s32` (registry #12) guards the ordering
  law and the coverage split; it goes red on the old sort key (verified).
- **One selector, one ordering law — the predecessors are retired, not stacked**
  (2026-07-25, Andrew: "if we've tried to fix the bug before and it hasn't worked out, we
  should identify the right fix and retire the previous [patch]"). Applied to the four
  prior attempts at deck starvation. **`recent_ask_counts` moves from `morning_knock` into
  `suggest_targets`** and becomes the third term of the one sort key —
  `tier → -staleness → asks → ripeness → key`. The knock module's two copies of
  `sorted(pending, key=asked)` are **deleted**, which also repairs a defect they carried:
  a stable re-sort by ask count alone made it the OUTERMOST key, so an asked-once
  *survival* item fell below an unasked *dessert* one. The move is down a layer —
  outreach may depend on selection, never the reverse; `suggest_targets` must stay
  importable without the OpenAI/TTS stack, since it is what opens every session. The
  ticket had no ask-demotion at all before this and now inherits it for free. Ask-count
  is what breaks the tie staleness cannot: 50 items sit together at `NEVER_SURFACED`,
  and an ask that got no reply never sets `last_surfaced`, so a missed item would
  otherwise be re-asked forever (the original KF-6 symptom). Same audit fixed the count
  itself: **a volley's items 2..n were never counted as asked** — `expected_target` names
  only item 1 — while the volley is the deck's main volume channel, so the demotion was
  blind to most of the asking. First measured effect: yesterday's two volley frames left
  the head of the queue and the volley reached four never-asked antifreeze/public chunks
  for the first time. **`render_drill.deck_due_payload`'s frame/chunk interleave is kept
  but re-justified** — its stated reason (ASCII `frame:` keys sorting ahead of Tamil
  script) is dead; a plain top-6 now measures 2 frames / 4 chunks. It survives only as a
  pedagogy choice (a drill wants alternating slot-fill and said-whole work) and its
  docstring now says so, with the deletion condition named. Keeping a workaround whose
  comment describes a bug that no longer exists is how a file becomes untouchable.
  **Known and left alone:** `recent_ask_counts` matches phonetics by substring, so
  1–2 character lexicon keys (`ல`, `ஆ`, `அவ`) collect false hits — inert here, because
  only deck members are read from the counts and none are that short. Revisit if a short
  deck item is ever seeded. *(Superseded 2026-07-26 — `rep_counts` reads the whole
  lexicon, which made it live; see below.)*

- **A cooldown is not a coverage term — the 07-25 fix reached one selector and was the
  wrong term anyway** (2026-07-26, Andrew: *"I don't think the 'last 3 days' fixes the
  problem… then there's a big list of 1's"*). Two defects, one entry, because the second
  is only visible once the first is fixed. **(a)** The 07-25 law landed in `deck_status`
  alone; `floor_gap_targets` — the other 235 words, the "larger goal" the deck was accused
  of starving — never got it, and 7 of its top 14 targets had been asked within 3 days.
  **(b)** Adding the same 3-day term there fixes almost nothing: the window *forgets*, so
  on day 4 a word's count resets to zero and it rejoins the head of the alphabet. Simulated
  over 30 days at 8 targets/day it reaches **24 of 134 words**, spending 100 of 240 asks on
  ten of them; 110 words are unreachable. **Lifetime reps** reach 121 of 134 with nothing
  asked more than twice. So `recent_ask_counts` is demoted to what it was always for — a
  cooldown, applied *inside* the focus set — and `rep_counts` is the coverage number.
  Rejected: pseudorandom selection (Andrew's suggestion) — it gives coupon-collector
  behaviour, cannot distinguish a starved word from an unlucky one, and a counter is
  inspectable where a die roll is not; randomness survives only as `stable_jitter`, the
  final tiebreak, replacing alphabetical. **`coverage_key` is now the single definition**
  both selectors read (the deck prefixes tier and then defers) — the 07-25 entry's "one
  ordering law" was true as prose and false as structure, since it was two hand-copied
  sort keys in two files. That is what let it drift in a day. **Reps need a real counter:**
  `last_surfaced` is one overwritten date and can say *when* but never *how many*, and the
  session log records outcomes, not attempts — so `reps` becomes a lexicon field written by
  `sync_state.touch`, summed with the knock-log count in `rep_counts` and nowhere else.
  Fixing the substring probe above was a **prerequisite**, not a bonus: counting the whole
  lexicon made the latent false-hit bug live, and it had `நீ` at 17 reps against a true 7.

- **Two budgets, because coverage and depth genuinely conflict** (2026-07-26, Andrew:
  *"10-15 getting most reps until they fire cold… the remaining on a slow guaranteed
  background"*, and *"we need to make sure everything goes into the rotation without
  starving the dense learning of a current week"*). One ranked list can be broad or deep,
  never both: pure coverage touches 134 words once a month and graduates nothing; dense
  repetition graduates words and rots the tail. So the floor splits — a **focus set** of
  `FOCUS_SIZE` (12) words in dense rotation with sticky membership (the cohort advances and
  graduates together rather than churning), and a **background** that is *exposure only* —
  soak candidates that keep a word warm and are never forced to fire. **Graduation is
  production going cold, and it is final**: a cold word is never drilled again, it is just
  used, never re-tested (Andrew: *"never tested just assumed"*). Simulated over 60 days: 66
  graduate, 132 of 134 touched, no word drilled more than 5×. The background rotation is
  guaranteed only because exposure writes `last_surfaced`, which moves a word to the back
  of its own queue — without that write the same two words are exposed forever, so the
  smoke case models the write rather than the intent. **Stuck words are flagged, never
  evicted** (`STUCK_REPS` = 10, twice the p90 of the 33 words that have actually gone cold —
  median 2, max 15): past that, the *approach* is what needs changing, and Anna is told so.
  Deliberately not an eviction rule — 33 data points cannot justify giving up on a word,
  and a silently parked word is exactly the starvation this change exists to end.
  **Rejected: retiring `word_pool.json`** (proposed by the assistant, overruled by Andrew:
  *"if it's being ignored, then we should be fixing that"*). Deleting the only planned
  vocabulary-intake path because nobody used it treats the symptom; the file is not broken,
  it is queued.

- **`pairs_with` — catch-and-response is a relation, and the schema now carries it**
  (2026-07-26, from the curriculum audit). Andrew names catch-and-response as a first-class
  curriculum kind; the schema had `direction: catch` but no way to say *hear X → say Y*, so
  the pairing lived as English prose in `note`/`gloss` and nothing could drill a pair as a
  pair. Concrete casualty: the maami's இன்னும் கொஞ்சம் சாப்பிடுங்க kept its deck slot while
  its refusal வேண்டாம்மா, வயிறு நிறைஞ்சிடுச்சு was dropped from the deck file, and nothing
  noticed. One field, on the **catch** side (the direction of the drill), **validated to
  resolve inside the same deck file** — so a split pair is now a loud seed-time error rather
  than a silent one. **The curriculum is two surfaces, not four or five**: `type` is
  `chunk` | `frame` and that is the whole taxonomy; `direction` and `register` are
  attributes of those two, not kinds beside them. **Left open, needs Oracle content:** five
  of six `faq` answers name their prompt only as romanised English inside the gloss
  (*"eppo vandheenga?"*, *"enna velai?"*, *"enga irukkeenga?"*, *"evlo naal irupeenga?"*) —
  the questions Andrew will actually be asked exist nowhere in the repo, so he has the
  answers to questions he cannot recognise. Not guessable; it goes to the Oracle.

- **Quiet hours belong to `push_to_phone`, not to each lane** (2026-07-26, after a drill
  reached Andrew's phone at 23:42). The rails (08:00–21:00 local) were correct and were
  enforced **four** separate times — `rails_gate` for knocks, `in_waking_window` in the
  push queue, and a hand-rolled `WAKING_START_HOUR <= hour` compare in both `run_studio`
  and `render_soak` — while `render_drill` had none at all. Four copies and one gap, and
  the gap is the lane that fired. Same shape as the ordering-law drift found the same day,
  which is the argument for the same remedy: **one owner**. The guard moves into
  `push_to_phone`, the single chokepoint every lane already goes through, and all four
  copies are deleted; `in_waking_window` moves to `morning_knock` beside the constants it
  reads. `requested=True` is the one exemption — a reply to Andrew's own tap is not an
  interruption, and the rails exist to stop *unrequested* reaches (`knock_reply`'s two
  pushes and the queue's `force` entries). The queue keeps its own deferral check because
  it does something different with the answer: it re-queues rather than dropping.
  **Honest scope:** no CI lane was ever ungated — `anna.yml` runs only the queue drain and
  `morning_knock`, both gated — so Anna in a runner could not have done this; the exposure
  was laptop-only and would have become real the day an evening drill was scheduled.

- **The rephrase state-loss hazard is real but has cost nothing — no mechanism**
  (2026-07-26). `seed-deck` un-tags departed items but leaves `type`, stranding rows, and
  the audit proposed a `supersedes` field so a re-worded phrase migrates its learning
  state. All four superseded pairs were checked: **`seen_in` empty and `last_surfaced` null
  on both spellings, in every case**. Nothing was ever lost, so a migration field would be
  machinery for zero rows. The 9 remaining orphan chunks are inert (none reach the floor
  denominator). Revisit only if a *soaked* phrase is ever re-worded.

- **The word ledger is declared events, never text forensics — rep, exposure, and spend
  are three different things** (2026-07-26, Andrew's ruling on the from-scratch review).
  A **rep** is Andrew producing the word, fully or partially — "you heard it from me"
  (the session's `touch`, the judge's per-word `fired` list — both already declared).
  An **exposure** is the word going out the door in any dose, written at render/push
  time: confirmed-listen is unreliable by his own account, the counter's job is rotation
  fairness rather than truth, and his side of the contract is consuming what ships and
  feeding back. An unanswered **ask** is spend — it feeds the 3-day cooldown and nothing
  else; ignoring the phone must not advance the curriculum. Python declares all three at
  the seam where it assembles or grades the dose; probe/substring mining leaves the
  counting path and survives only in the reveal-cooldown, where Anna's free prose
  genuinely is the only source. **Supersedes the rep half of the coverage entry above**:
  `rep_counts`' knock-side sum counted words *printed in Anna's own text* as reps, and
  the same-day audit measured the damage — the session `reps` field was still empty, so
  100% of live "reps" were mentions (`டீ`/"tea" at 21, `ல`/"la" at 22 — the whole-token
  fix missed English-collision phonetics and romanized suffix tokens), என்ன? carried a
  false STUCK flag having never been drilled, and focus seats were allocated by mention
  frequency. The two-budgets architecture itself is untouched; this corrects its input.
- **The focus cohort is stored state, not an emergent sort** (2026-07-26, Andrew: "the
  alternative sounds more reliable"). The ≤12 names live as explicit Python-owned state;
  a word enters when a seat opens and leaves only on graduation. Derived-from-counters
  stickiness is only as sticky as the noisiest counter — membership becomes a fact
  readable in a file, immune to counting bugs by construction. Same inspectability
  argument that rejected pseudorandom selection.
- **Deck and floor share one ledger and one law; they differ only in dosing and
  promotion** (2026-07-26, Andrew). Same counters, same `coverage_key`; the deck keeps
  its tier prefix and deadline policy, the floor keeps focus/background. Decided
  explicitly so the next selector drift has no ambiguity to grow from.
- **The background exposure loop must close at the delivery seam** (2026-07-26, from
  the same review). "Guaranteed background rotation" was prose: the only `last_surfaced`
  writers were `--listened` (unused — zero listens logged in weeks, per the
  stop-chasing-listens policy) and `--mark-seen`, while episode delivery wrote `seen_in`
  only — and `seen_in` raises `soaked`, which `coverage_key` sorts *earlier*, so
  unlogged exposure was a positive feedback loop (the exposed get more exposed). The
  delivery-time exposure write above is the closing mechanism; smoke s34, which
  hand-modeled the write inside its own loop, must assert the real seam once built.
- **Rep backfill from judged replies only** (2026-07-26, Andrew's yes at build time).
  The ledger build seeded the new counters by replaying the knock log's declared
  `fired` lists — 49 reps onto 26 words; 19 historical fired-words resolving to no
  record stayed unscored, exactly as the judge left them at the time. Rejects any
  backfill from targeted asks or text matches — that is the pollution the build removed.
- **The deck sort carries the ask-cooldown as an explicit term** (2026-07-26, found by
  smoke while deleting the rep miner). The miner had been providing KF-6 protection by
  accident — a targeted ask counted as a lifetime "rep" and pushed the item back; with
  reps declared-only, a hidden-target ask would sit at the queue head and re-fire
  forever. The 3-day cooldown now rides between tier and `coverage_key`, the same term
  the floor already applies inside its focus set. Replaces an accidental mechanism with
  the explicit one; "deck and floor share one law" is why it is the *same* term.
- **An eavesdrop's target is an exposure despite `target_revealed: false`** (2026-07-26,
  @build's reading of the ledger law — flag if wrong). The tape *speaks* the word; the
  flag is false only because the ask is comprehension, not because the Tamil was hidden.
  A hidden production target remains spend-only. Declared at the knock seam
  (`knock_exposures`), never mined from the memo text.
- **The campaign keeps its story and loses its paperwork** (2026-07-26, Andrew: "keep the
  story, drop the paperwork"). The 07-17 campaign was built when nothing named what was
  coming *and* nothing ranked the curriculum; it took both jobs. The 07-25/07-26 selector
  work took the second one back — the focus set is a stored ≤12 cohort that graduates on
  cold, `catch_pending` ranks the ear axis by the same law and resolves each pair, and the
  deck sort carries tier + ask-cooldown + `coverage_key`. So three of the campaign's four
  clauses (its ~10–14 item list, its catch targets, its denominator) had become a
  hand-maintained second selector, and by "one selector, one ordering law — the
  predecessors are retired, not stacked" (07-25) it was the last un-retired predecessor,
  sitting outside the law instead of inside it. **Supersedes the item-list, catch-target,
  and day-grid clauses of "The Campaign — the week ahead" (2026-07-17); supersedes "Every
  campaign names catch targets" (2026-07-18) — the EAR-ONLY block names them now; retires
  the co-authoring contract** (kick-off → draft → adjust → agree), which failed on the
  evidence: two campaigns in ten days, the second never agreed after being put to Andrew
  twice in one session, and it ran unagreed anyway and worked (catch 1/12 → 3/12).
  What survives is the one job nothing else can do — the **through-line**, the sentence
  that makes a week's items one thing rather than a list ("verb + -nga is one machine" is
  why the Ask-Machine Week won). Five lines, Anna writes it at close, Andrew overrides at
  will, the ticket owns which items. Cost: `daily_session.md` 1220 → 1180 words, the
  profile block 130 lines → 8. The narrated-denominator rule (07-17) survives unchanged;
  only its source moves to the ticket's focus set.
- **One campaign heading, always — a finished week is overwritten, not archived**
  (2026-07-26, found while auditing the above). `campaign_block()` parses `profile.md` by
  an exact heading string, so the 07-24 close — which kept the won Ask-Machine week under
  that heading and put the live one under "## The Campaign — PITCHED …" — silently
  orphaned the live campaign. **Three days of knocks steered by a won-and-closed
  campaign**, truncated to 1500 chars of victory lap, while the Overhear Week was invisible
  to every automated medium. s17 tested the parser on synthetic prose and could not see
  it; it now asserts the real `profile.md` carries exactly one `## The Campaign` heading.
  The five-line rewrite removes the failure mode by construction — there is no longer a
  record to archive in the file, because git is the record.
- **language-tutor already carries the domain-independent doctrine and its mechanisms;
  what it does not carry is domain-independent *bindings*** (2026-07-27, correcting
  @build's wrong claim earlier the same session that the template held the doctrine only
  incidentally — the claim was asserted without reading the repo). Verified in
  `../language-tutor`: `docs/DECISIONS.md` opens with the "How to work on this system"
  doctrine section (LLM-writer/Python-brain, every addition earns its place, surgical
  edits, fix the tool not the personality, structure freeze, fade-is-data), and the
  enforcing mechanisms came with it — `PROSE_BUDGETS` + `s18_prose_budgets`, 23 of
  Tamil's 34 smoke cases, the feedback ledger in `sync_state.py` / `diagnosis.md`. The
  residual: those budgets bind tutor-shaped filenames, so the immune system is extracted
  one level (Tamil → any language) and not two (language tutor → any recurring-generative
  system). **Rejects extracting that second level now** — there is no second consumer,
  and the Dutch cold-elaboration precedent (template DECISIONS, 2026-07-19) is that an
  extraction gets validated against a real second case, never guessed from one.
- **The phone lane's trustworthiness is pre-registration, not the separate judge — so the
  chat lane must not copy the split** (2026-07-27, @build's reading; Andrew asked whether
  the separate mandate was better or worse and has not ruled). The `knock_reply.py` split
  was *forced*, not chosen: the reply lands asynchronously in another process with no
  conversational context, so independence came free. In chat it costs the Contrast Beat
  (recast-with-one-clause **is** the grading act, in voice), costs the grading context a
  transcript loses, and buys nothing — a post-hoc judge reads the record Anna authored,
  including how the situation was framed and what was on screen, so it audits the writer
  using the writer's own notes. What actually makes the phone grade meaningful is
  `expected_target` pinned with `target_revealed: false` **before** the dose ships; chat
  has no equivalent. Rejects porting the split; names pre-registration as the transferable
  property if the hole is ever evidenced. No evidence yet that the chat floor is inflated
  — the argument is structural, and one theoretical hole is noise by the diagnosis gate.
- **The post-trip horizon gap is adherence infrastructure, not curriculum** (2026-07-27,
  diagnosis only — Andrew asked what to propose and has not ruled on the response). The
  Trip Deck does three jobs and only one survives 2026-08-12: *selecting what to work*
  lives on (the 07-26 selector took it back — deck and floor share one ledger and one
  law), but the **winnable denominator** (15/34 survival cold → 31/164 floor) and the
  **deadline** both die at touchdown with no successor. May faded with no deadline;
  June–July surged with one. The failure to avoid is arriving home on 2026-08-20 with
  nothing on the status line that can be won — the corrosion "honest meters or none"
  already names. Explicitly **not** a call to build a post-trip planner: the campaign's
  co-authoring contract was retired on evidence nine days earlier (07-26), and a planning
  ceremony with a longer horizon is the same rejected object.
- **A fire must be verified against what Andrew typed — credit belongs to the word he
  produced, never the target the judge wanted** (2026-07-27, Andrew's ask: "if it's still
  valid in context, then I should get credit against the word I did use"). Root cause of a
  phantom cold on the 07-27 antifreeze volley: `shown_in_knock` is asymmetric — it can only
  *demote* a fire the knock revealed, and nothing ever checked that a fired word appeared in
  the reply. Reply "Oru nimsham" fired கொஞ்சம் + நில்லுங்க, Python derived a COLD headline and
  pushed back "நில்லுங்க fired cold 🔥"; meanwhile his two real substitutions were deck items
  that scored nothing (புரியல — whose phonetic list already carried "puriyila" — and
  ஒரு நிமிஷம், both produced unaided). The axis stayed honest only by luck: நில்லுங்க is not a
  lexicon key. Each `fired` entry now carries `said`, the span of the reply that produced it;
  Python drops any fire whose span is not literally in the reply and the headline re-derives.
  **Rejects a deterministic phonetic match on the Python side** — he types "nimsham" where
  the lexicon stores "nimisham", so matching in code strips real credit, the opposite and
  worse failure. The model owns the morphology, Python owns "did he type it." Extends
  "the verdict is the suspect" (07-25) from reading history to scoring it.
- **A target he substitutes away from is signal to teach, not a miss to punish**
  (2026-07-27, Andrew's framing: "enna sonneenga may go starved on catch if I don't reach for
  it, but that's signal that you can use to teach me"). A socially coherent substitute is a
  real rep — the target was never tested, so it stays where it is and the substitute scores on
  its own merits. What the starvation earns is one Contrast Beat about *what each line buys*
  (புரியல closes the conversation, என்ன சொன்னீங்க? reopens it), never a re-drill of the target
  as though he had failed it. Generalizes the existing `VALID ALTERNATIVE ≠ MISS` rule from
  "don't call it a miss" to "route the credit."
- **A word from muscle memory arrives in one frozen form; a word from drilling arrives with
  its paradigm** (2026-07-27, diagnostic reading — the பேச case is unconfirmed pending the
  Oracle). Andrew produced `pesa` unprompted, a verb the system never taught (12 சொல் records
  in the lexicon, 2 பேசு, neither produced) — and produced it as the bare *infinitive*, the
  form that lives inside frozen high-frequency frames (`தமிழ் பேச தெரியுமா?`). The tell matters
  because it reframes the `-ங்க` gap: he cannot inflect a chunk that was never a verb to him,
  so five honorific imperatives sitting at recognition-solid/production-none are **one lever,
  not five words**. Rejects reading the gap as carelessness, and rejects drilling the five as
  vocabulary.
- **The second-level extraction may only go toward more domains, never more users**
  (2026-07-27, @build's analysis; Andrew asked what is novel and portable here and has not
  ruled). What makes this system unusual is three co-occurring properties — a months-long
  horizon, an n=1 audience, and an agent that initiates — and two of its mechanisms are
  load-bearing *because* of n=1: the felt-signal ledger ("twice is signal, default verdict
  change nothing") degrades into ordinary analytics the moment there is a population to A/B,
  and git-as-runtime breaks on commit contention and Actions minutes the moment there are
  tenants. So a validating second consumer must be **one human, months-long,
  adherence-metered, with the system controlling the stimulus** (pre-registration has no
  purchase on open-ended chat — the 07-27 chat-lane entry above) and a gradeable response
  coming back; instrument practice is the closest non-language twin, rehab and strength
  programming the next. Sharpens the "no second consumer, don't extract" rejection above by
  naming what would clear it, and rules out the multi-tenant reading of "more general."
- **Fourth milestone re-sync — `template-v5-source`, the selection/ledger overhaul**
  (2026-07-27, Andrew's ask: "anything salient to back port or not yet?"). The
  delta since v4 was 149 commits and four milestone-sized stories; this sync
  carried exactly one of them, because the template was not merely behind on it —
  it shipped the *defects* the 07-25/07-26 work fixed. Verified before porting,
  not assumed: `-soaked` sorting the already-heard earlier (the anti-coverage
  feedback loop), alphabetical as the final tiebreak (every tie group's head
  frozen), `recent_ask_counts` still in `morning_knock` with both
  `sorted(pending, key=asked)` re-sorts intact (ask count as the OUTERMOST key),
  and no `reps`/`exposures`/`focus_cohort` anywhere. Ported: `coverage_key` as the
  one shared law, the two-budget floor with a stored cohort, the three-event
  ledger declared at four delivery seams, `deck_coverage`, `pairs_with` with a
  split-pair seed refusal, and smoke s25–s27 (55 checks) from Tamil's s32–s34.
  **Deliberately left behind:** the soak-lane exposure seam (the template has no
  soak lane — it rides with the studio driver), feed hardening, the judge
  corrections, and the one-runner consolidation. Those are v6, and splitting them
  out is what kept this milestone legible.
- **A milestone re-extraction is scoped by where the template is WRONG, not by
  what is newest** (2026-07-27, from running the v5 sync). Four stories qualified
  on size; the selection overhaul was taken first because the template was
  actively shipping the bugs, while the other three were merely absent. Absence is
  a gap a user never sees; a shipped defect silently starves their curriculum.
  Sharpens the milestone-re-extraction policy (2026-07-06/07-10), which said *when*
  to sync but not *what to take first* when a delta holds several milestones.
- **The template's generalizations outrank the reference implementation's
  originals** (2026-07-27, found mid-port). Tamil hardcodes `DECK_TIERS`/`TIER_NAMES`
  with its own register names and defaults an unlisted register to tier 1;
  language-tutor derives both from `config.deck.tiers` and sinks unlisted registers
  below every configured tier. A port that copies Tamil's version faithfully would
  have REGRESSED the template. The rule: where the template already solved a seam
  more generally, the port adapts to the template and Tamil's literal is the thing
  discarded. Rejects "port verbatim, then generalize" as the working order.
- **One serialised CI lane, held open by `queue: max`** (2026-07-28, Andrew).
  `anna.yml` keyed its concurrency group by `knock_id`, so every reply got its own
  lane and two replies could run in parallel. On 07-28 a reply to a *stale*
  notification (the 07-27 volley, still on the lock screen) raced the reply to that
  morning's knock; both appended to the tail of the `feedback_log.json` array,
  `git pull --rebase` hit a content conflict, and `commit_and_push` died mid-rebase
  under `check=True`. The cost was not the red run — it was a **judged exchange
  lost**: verdict, fires and ledger note all computed, then discarded with the
  commit. Now `group: anna` for every trigger.
  **What the old keying actually protected was delivery, not latency.** Its comment
  claimed "a reply must NEVER queue behind a knock render" — a preference written as
  an invariant. The real property was that GitHub cancels a *pending* run when a
  newer one joins its group (default queue depth 1), so a naive shared group would
  have silently eaten the middle of a reply burst — six dispatches inside six
  minutes that same morning. That failure is quiet and frequent; the conflict was
  loud and rare, so the naive fix was strictly worse. `queue: max` (GitHub
  changelog 2026-05-07) holds 100 pending FIFO and buys both properties at once.
  Andrew accepted the tradeoff — a reply may now wait behind a render — because it
  removes the race structurally rather than retrying around it.
  **Honest scope:** this closes CI-vs-CI only. The laptop is a third writer outside
  every group and still relies on "pull before read, push after write" (2026-07-15).
  A conflict-aware `commit_and_push` (re-apply the mutation against fresh state) and
  JSONL append-safe logs were both explored and **deferred, not rejected** — revisit
  if a laptop-vs-cloud conflict ever actually bites. Related but distinct: the
  `lexicon.json` last-writer-wins race (2026-07-13) is in-process, not git-level, and
  is untouched by this.
  **Linter lag, not a waiver:** `queue:` postdates actionlint's newest release
  (v1.7.12, 2026-03-30), which rejects the key as a syntax error, so `smoke.yml`
  carries a message-exact `-ignore`. Verified against 1.7.7 and 1.7.12 that the
  suppression is narrow — the `runner`-in-job-env outage the lint step exists for is
  still caught. Delete the flag when actionlint learns the key.
  **Supersedes the per-`knock_id` group** introduced silently in `38e7275`
  (2026-07-24), which never had a DECISIONS entry — its whole justification lived in
  a code comment, which is how an unexamined preference got to read as a law.
- **The tick returns to `*/30`; "hourly" was never hourly** (2026-07-28, Andrew).
  Reopens the 07-24 collapse to a single `0 * * * *`, which was costed on the
  assumption that the lost precision was "30 min → 60 min worst case." Measured over
  the last 20 scheduled runs, the gaps are **62–232 minutes, median ~2h** — all of it
  predating any change to this file. GitHub deprioritises and silently drops scheduled
  ticks under load, so an hourly expression bought a roughly two-hourly heartbeat and
  the number the decision was argued against did not exist. **This is new evidence, not
  a re-litigation:** the collapse of three expressions into ONE still holds (that was
  the real point), and the rails still own the schedule — the cron only has to be
  frequent enough for the rails to have something to filter. `*/30` does not promise 30
  minutes either; it buys twice the chances, which is the only lever this end owns.
  **Interaction with the serialised group** (same day, above): ticks now enter that one
  lane twice as often. A skipped tick is cheap — the rails exit before any LLM call —
  and `queue: max` absorbs the pile-up, but a reply can wait behind a tick more often
  than before. That is the tradeoff already accepted when the group was serialised.
  **Method note worth keeping:** this was found by measuring the actual run history
  while verifying an unrelated change, not by reasoning about the cron expression. The
  07-24 entry reasoned correctly from a premise nobody had checked.
  **AMENDMENT (2026-07-29, first day of data): the predicted benefit did not appear.**
  Measured over the first 8 scheduled gaps under `*/30`: **median 158.5 min, mean 148**
  — against **median 106.5, mean 114** over the preceding 46 gaps under `0 * * * *`.
  Gaps were 88–223 min. So doubling the expression's frequency did not shorten the
  heartbeat and may have lengthened it; GitHub appears to drop proportionally more of a
  denser schedule, which makes "it buys twice the chances" — the claim the entry above
  rests on — **unsupported**. Left in place rather than reverted for now: n=8 against
  n=46, and the sample is mostly overnight, so this cannot yet separate "worse" from
  noise. **The honest status is: the change is unproven, not vindicated.** Revisit with a
  full day of daylight data; reverting to hourly costs nothing if the gap holds, and
  hourly is cheaper in runner minutes for identical delivery.
  Noted against ourselves: the entry above criticised the 07-24 decision for reasoning
  from an unchecked premise, and then asserted its own unchecked premise in the same
  breath. The measurement discipline has to survive contact with our own proposals.
  **RESOLVED — reverted to `0 * * * *` (2026-07-30, Andrew), on the day of daylight data
  the amendment asked for.** 75 scheduled runs, n=24 post-change against n=50 before,
  compared slice-to-matched-slice rather than against a pooled baseline — median minutes
  between scheduled runs: all hours **108.7 hourly / 108.9 `*/30`**; daylight **135.6 /
  149.9**; overnight **69.2 / 88.9**. So `*/30` is identical at best and mildly worse in
  both matched slices, at twice the runner minutes — and the amendment's alarming
  158.5-vs-106.5 was an artefact of an n=8 overnight-heavy sample, not a real regression.
  Both readings of the 07-28 claim are now dead: doubling the expression neither shortened
  the heartbeat (the claim) nor lengthened it (the amendment's worry). GitHub drops
  proportionally more of a denser schedule, so the extra ticks evaporate.
  **The standing conclusion: cadence is not a lever this end owns.** The scheduled
  heartbeat is ~2-hourly whatever expression we write; the levers that actually fire
  off-clock are `repository_dispatch` and the reply path, both already wired. Do not
  re-open the cron expression without new data — the three prior rounds (07-24 collapse,
  07-28 reopen, 07-29 amendment) all argued from a premise about GitHub's behaviour that
  only measurement could settle, and this is the measurement.
- **The local notify hop fails behind work TLS inspection; accepted, not a bug**
  (2026-07-28, Andrew: "it's a work machine on a work network so it's their
  prerogative. Let's let it be."). `push_to_phone` raises
  `CERTIFICATE_VERIFY_FAILED` from the laptop because `ykf.duckdns.org:4444`
  presents `CN=FGT80FTK23007353, O=Fortinet` — a FortiGate appliance's factory
  self-signed CA substituted mid-handshake, not Home Assistant's own certificate.
  Verified it is environmental and not a Python config gap: the Windows system
  store AND certifi's full Mozilla bundle both reject it, and no Fortinet CA
  exists in `LocalMachine\Root`, `LocalMachine\CA` or `CurrentUser\Root`. **CI is
  unaffected** — GitHub's runners are not behind that interface, which is why the
  knock lane has never missed a push. **Rejected: disabling verification** for that
  call (trusting whatever answers on the port). **Deferred, not rejected:** routing
  local renders' notifications through `push_queue` so the cloud drain delivers
  them — architecturally the better answer (it removes the laptop from the delivery
  path entirely), revisit if local renders ever need to reach the phone.
  **The real cost is a reporting bug, not the cert.** A local render publishes the
  tape, commits, pushes and rebuilds the feed — and *then* raises at the notify
  step, so a fully successful run exits non-zero with a traceback as its last
  output. On 07-28 that read as total failure, the render was re-run, and a second
  soak tape published against an order the first run had already consumed. The
  honest fix is for the notify step to be best-effort like the drain
  (`continue-on-error` in spirit) and for the run to report what it actually did.

- **The 10–15 minute dose is the right dose, and adherence is why** (2026-07-28, Andrew's
  spoken testimony — learner-side confirmation of the density-low/lore-high pattern the
  debrief had already observed four sessions running). Verbatim: *"It's feeling about the
  right length… if it only takes me ten, fifteen minutes to go through the whole thing,
  that's a bit better than a longer session."* The mechanism he names is **adherence, not
  comfort**: a short dose means *"I'm more likely to push through and get the dopamine of
  having finished it than have an open session when I get distracted or have to switch to
  another task"* — he interleaves sessions into his workday as a break from other work, and
  a session he can finish is a session he starts tomorrow. He is explicitly torn (a longer
  session *"feels necessary"*) and lands on short anyway; the felt pull toward length is
  **not** a mandate to lengthen. Paired signal, same breath: *"the coffee before scenario
  idea is a success, and I genuinely enjoy that little dose of lore I'm getting each day —
  lore in this way is high density learning."* **Consequences, both directions:** the
  break-first contract and the lore tangent are load-bearing for daily adherence and must
  not be traded for reps; and the espresso floor is a real full session, not a shortfall.
  **Do not raise the dose or lengthen the session to solve an unrelated complaint** — the
  07-28 audio-commissioning signal arrived in the very same conversation and is explicitly
  *not* a volume ask.
- **A miss is data Andrew wants; grade honestly** (2026-07-28, his own words, settling the
  softening question for good). *"The cold axis where I produce it unprompted is the most
  honest… I'm trying my best to mumble through the sentences and trust that where I get it
  wrong, it will help me identify HOW I get it wrong, and reflect the teaching I need back
  at me. I would rather get it wrong than make a false signal that I've learned something
  that I haven't."* The recast-and-move contract and honest grading have the learner's
  explicit blessing — a generous grade is not a kindness, it is a corrupted meter he has
  asked us not to hand him. The second clause is the load-bearing one and is currently
  **unhonoured**: *"reflect the teaching I need back at me"* means the error is supposed to
  steer what gets taught and dosed next. That is the contract the audio side does not yet
  keep (feature_inbox: "THE REPAIR EARNS THE DOSE"). **Open and unanswered:** he doubts the
  HINTED tier retains — *"I just worry how much is going in and out"* — and he is right that
  the system has no answer, since cold is a one-way door with no re-test (inbox: "Cold decay
  / re-test dates", deferred past the trip) and hinted has no follow-up path at all.

- **The repair earns the dose — audio is commissioned off his errors, backward before
  forward** (2026-07-28, Andrew's spoken felt signal, diagnosed via `/recalibrate` and
  built the same session on his "fix this now"). His words: *"I don't feel like Anna is
  commissioning enough audio, and specifically audio to close the gap in the mistakes I'm
  making… I shouldn't have to beg for a soak or an episode… the plumbing isn't lacking.
  It's the prompt instruction."* **His diagnosis was correct and it was prompt-side.** The
  system had a channel-ROUTING law (`audio_channels.md`) and a PRODUCTION law
  (`studio.md`) and **no COMMISSIONING law** — nothing said which gaps earn a dose, or
  that an error earned one at all. The whole content policy was one clause in Close & Log
  step 2 (*"payload… **may** be a seed order"*), a menu rather than a priority, so the
  campaign's forward-teaching pull outranked the backward repair need by default.

  **CORRECTED same day, after reading the history: this was a REGRESSION, not an
  oversight — and the word-budget pass is what caused it.** Andrew's surprise
  (*"I thought commissioning was part of the point"*) was justified; he wrote the rule
  himself on **2026-06-16** (`4666c58`, titled "close the chat↔audio loop"): *"**Set the
  Soak Order:** IF THE SESSION REVEALED A SPECIFIC STRUGGLE (a `hinted` word, a floor-gap
  word, a missed recast), Anna names it as the structured soak order… the audio pipeline
  soaks exactly what chat just strained, not a separate curriculum."* Same rule, same
  population. **2026-07-16** (`92e95a4`, the subtraction pass) compressed it to *"payload
  (what chat strained)"* — the **conditional** and the **qualifying list** collapsed into a
  parenthetical gloss, turning an instruction about what to put in the field into a
  description of the field. **2026-07-17** (`9b97cc3`) added the seed order beside a rule
  disarmed the day before, so the two read co-equal; **07-26**'s campaign rewrite then gave
  forward a name, a through-line and a `profile.md` block while backward still had a
  parenthetical. Forward never won a fair fight.
  **The general hazard, and the reason this is worth writing down: prose compression is
  lossy in one direction — it keeps nouns and drops conditionals.** *"If X, do Y"* becomes
  *"Y (X)"*, which reads fine and instructs nothing. `92e95a4` rewrote all of
  `daily_session.md`; **other conditionals may have gone the same way and nobody has
  looked.** Note also that `studio.md` never lost it — its contract still reads *"what Anna
  just strained in chat… the other half of the loop"* — so the CONSUMER kept faith while the
  WRITER stopped handing it repairs, which is exactly why nothing looked broken for five
  days: episodes kept arriving on time and well-made, about the wrong thing. The June rule
  had no regression net; today's has `s37`, which is the actual difference.
  **The fix:** the payload is drawn *first* from the day's unclosed repairs — hinted,
  recast, or corrected-and-still-wrong — and points forward as a seed order only when the
  day leaves none. A collision that survived its correction earns its **own** order, not a
  slot in a mixed one (07-28's own method finding: *contrast explains a collision, a chunk
  fires it*). The seed order is **not** demoted — it still teaches the campaign's next page;
  it just no longer outranks a mistake he is still making, which is a refinement of the
  07-17/07-26 seed-order calls, not a reversal. **Evidence it was structural, not taste:**
  six instances in five days, *every one of them Andrew commissioning* (07-24 believing
  Anna could produce audio unaided · 07-25 ×2 asking for இருந்துச்சு and இன்னொரு/தடவ
  drilling · 07-27 commissioning pakkam-vs-paakkalaam by name · 07-28am the unacted
  eavesdrop-needs-real-audio verdict · 07-28pm this), well past the `/recalibrate`
  third-strike bar. The exhibit: the 07-28 debrief concluded *"assembly loses to retrieval
  under load"* — a diagnosis whose remedy is `render_soak.py`'s literal job — and பக்கத்துல
  reached the order as one item of three, still open that evening. **Housed in
  `audio_channels.md`, not `daily_session.md`** — that file always framed itself as two
  questions (what a dose carries, which channel carries it) and owned only the second;
  Close & Log keeps a firing pointer and came out leaner. Same split move that file made in
  07-23 and `JUDGE_MANDATE` made in 07-24: **a ceiling is a split signal.** Its budget went
  400 → 550 in the same diff, which is the exception the word-budget rule allows (growth and
  raise together, naming what moved) rather than the bump-the-number reflex — the first
  attempt put the law in `daily_session.md`, hit 1244/1250, and the mechanism correctly
  refused it. Smoke case `s37` is the regression net, per the 07-24 lesson that a rule must
  be planted in code, prompts, skills *and* tests: it lints the law, the Close & Log
  pointer, and the glossary. **NOT the ask — volume**: he wants *targeted* audio, and this
  is explicitly not a session-length change (see the same-day dose-size entry).
- **`MAX_UNATTENDED_PER_DAY` raised 1 → 3; the rail is that it is finite, not that it is
  small** (2026-07-28, Andrew: *"guardrails to a problem that was temporary — remove it or
  raise it"*). Amends "An unattended production trigger must be verifiable, and capped
  regardless" (2026-07-23); the **verifiable** half stands untouched. He is right that 1 was
  sized to a fixed bug — `split_payload()` closed the stuck produced-check that shipped
  M72/M73/M74 in one evening. It also became *binding* under repair-first commissioning:
  when each unclosed repair can earn its own order, one dose a day is the constraint that
  starves the fix. **Raised rather than removed** (his instruction allowed either): the cap
  never guarded that one bug — it bounds whatever the next stuck predicate turns out to be,
  and the blast radius is unattended, firing renders, feed entries and phone pushes while
  he is out. Smoke asserts the cap is finite and under 10, so a future "just remove it" has
  to argue with a test. **Latent today:** the local watchdog cron is retired (07-24), so
  this constant currently gates only a manual `studio_watchdog.py` run and the unbuilt
  `episode` move in the knock tick. What actually delivers more targeted audio right now is
  the commissioning law plus the session-open auto-drain, which is attended and works.
  Fixed alongside: Anna's skill promised *"`studio_watchdog.py` (hourly local cron) retries
  any miss"* — false since 07-24, and a retry that does not exist is worse than none because
  it makes a dropped dose look covered.
- **A commission reaches the episode lane as computed context, never as an agentic read**
  (2026-07-28 evening, found on the first real exercise of the law above and fixed in the
  retrospective the next turn). `frame:youknow-la` was commissioned as an episode and the
  FIRST M77 attempt came back dramatising the computed `FOCUS SET` — a 28-item sidecar with
  the commissioned payload absent. (The retry landed: the shipped M77 opens
  நம்ம தம்பி இருக்கான்ல… and carries the frame. It succeeded because the `scene_seed` was
  hand-sharpened until the frame *was* the whole scene, which is exactly the manual step the
  law was written to remove.) The ticket had
  **no commission section at all**: the order reached the Director only through one prose
  clause in `DIRECTOR` (*"read the soak-order in `progress/learner.json`"*), competing with
  a code-assembled list headed *"DRILL these until they fire cold"* — and lost. The same run
  is the control: the commissioned `form: phone_call` landed perfectly because it arrived
  through `scene_spec()`/`claim_spec()` as computed context. **This is the repo's own
  doctrine failing in the direction it predicts** — code-assembled context beats an agentic
  read when the invariant is known — so the payload now arrives the way the form does:
  `suggest_targets` prints section **0. THE COMMISSION** (payload, focus, scene_seed, the
  date and the "this outranks every list below" heading) ahead of everything it computes,
  and the FOCUS SET says out loud that it is outranked. **What it replaces:** the prose
  clause in `DIRECTOR` is no longer load-bearing, and `episode_commission()` is now the one
  predicate for "is there a live commission for this lane", with `commissioned_form()`
  delegating to it. That fixes a second, quieter bug in the same read: `commissioned_form()`
  asked only *"is the order routed here"*, never *"is it still owed"* — so a FILLED order
  went on pinning the next episode's form for ever. `frame:youknow-la` shipped in M77 and
  the gate was still locked to `phone_call` afterwards, an axis of the variety gate held
  shut by a debt already paid. Owed now reads BOTH seams, which disagree by design: the
  episode lane clears itself by registering the payload (`soak_pending()`), the soak and
  drill lanes stamp `delivered` because they have nothing to register. To read both,
  `soak_pending()` moved from `studio_watchdog` down into `sync_state` — the ticket needs
  the answer and cannot import the studio without pulling the whole render stack — and the
  watchdog re-exports it. One definition, three readers. Smoke case `s39`. **Still open, deliberately** — `claim_payload()` (`run_studio.py:418`) injects any
  `frame:` key into `new_words_landed` unconditionally, because a slot template is
  verbatim-exempt, so a frame commission can stamp *delivered* with no evidence it was ever
  audible. Verifying a frame needs a pattern the frame record itself carries, which is
  schema-adjacent; it stays in the inbox under the structure freeze. **Consequence while it
  stays open: a `frame:` order can read PAID when it was not**, so a frame commission is the
  one case where the ledger cannot be trusted without listening.
- **Scope and format are two questions; a collision only answers the first** (2026-07-28
  evening, Andrew, AMENDING the same-day commissioning law above). The rule shipped that
  afternoon read *"a collision that survived its correction earns its own order — contrast
  explains a collision, **a chunk fires it**."* The first half is scope and is right. The
  second half names a FORMAT — a chunk is what `render_soak.py` makes — so the rule as
  written told Anna that every mix-up gets the loop. Andrew, hours later: *"when I'm
  struggling to hear the difference between two words, it shouldn't just be a slow
  repetitive loop… using them in context can be very effective for sticking in my brain."*
  **He is right on the evidence, and it is his own:** the 07-28 deep-dive gave him the full
  minimal-pair contrast and ninety seconds later, under production load, he still said
  *"temple-ku pakkalam."* His ear was never the broken part — repetition in a quiet room
  does not train the seam that failed, and what fixed it inside one exchange was the chunk
  carrying load. **The fix:** the scope bullet now says out loud that it sets scope and not
  format, and the channel section gains *"capacity vetoes; the ERROR chooses"* — can't hear
  them apart → soak; hears them fine but the mouth takes the wrong one → episode; has it and
  is slow → drill. Plus an escalation rule that did not exist: **the same mistake twice
  through one format is that format's answer — change format, never loop harder.** Capacity
  is untouched and still vetoes (07-23 stands): the error picks among what his attention
  allows, it does not overrule it. **Budget:** 550 → 640 in the same diff, the SECOND raise
  in one day, flagged as such at the constant. Retired to pay for it: the `chunk fires it`
  clause, the *"route by the situation"* bullet (its veto half is now the table's opening
  line), and the 07-23 story compressed — 33 words back. **A third raise is refused in
  advance**; the next growth splits "what it carries" from "which format carries it".
  Smoke `s37` extended: it now asserts the format clause is *gone* and cannot grow back.
- **The drill lane consumes its commission; ear-only is refused, not demanded**
  (2026-07-28 evening, Andrew: *"let's fix drill now then"*). `--soak-channel drill` was a
  DEAD VALUE — `sync_state` accepted and stored it, `render_drill` never read it, and no
  lane stamped it delivered. Three silent consequences: the repair became an ordinary deck
  drill, the order stayed pending, and the session-open auto-drain then dispatched an
  EPISODE for it, the one lane he had explicitly not chosen. So of the three channels the
  routing table advertises, only two worked, and the third failed by quietly substituting
  the most expensive one. Found while answering his question about which formats belong on
  the commissioning menu — the honest answer was *fewer than the table claims*.
  **LEAD, not replace** (his call, taken on the recommendation): the commissioned item leads
  the tape and the writer is told to give it THREE cues in three different situations, same
  target; the due deck fills out the rest and keeps its normal shape. A tape built entirely
  from one item is the slow repetitive loop this lane was commissioned to escape — the same
  reasoning as the format amendment above, applied one layer down. Mirrors `render_soak`'s
  `soak_brief`/`with_payload` exactly, so the two lanes now read the order the same way.
  **The ear-only refusal is the load-bearing part.** A drill's silence is a production
  demand and `direction: catch` items are never forced to fire (deck law). A catch item
  routed here is a mis-route, so `drill_brief()` reports it and leaves the order standing
  for the soak or episode lane rather than turning it into a demand he cannot meet — the
  failure would have been invisible, because a refused word and a drilled word both produce
  a tape. `frame:youknow-la` is exactly such an item and was live on the order today.
  **Also:** the lane now stamps `mark_soak_delivered("drill")`, closing the pending-forever
  path, and a commission still gets a tape on a day the deck has nothing due (the old
  early-return killed the run before the order was ever read). Smoke case `s40`, including
  a stubbed-LLM run of `main()` itself — the pieces are only worth having if the entry
  point calls them.
- **Mistakes are a ledger, not prose — errors accumulate, cross lanes, and steer selection**
  (2026-07-30, Andrew's ask: *"make very, very sure that these mistakes are used as direct
  signal to direct subsequent lessons"*). **Evidence, not a felt signal:** `romba nalla
  irukku` → `irundhuchu` was pushed back on **07-08, 07-25 and 07-30**, near-verbatim; the
  1pl `-ōm` ending was corrected on 07-25 twice (`poganum`→`ponoom`, `sappiten`→`saapittoom`)
  and again on 07-30 (`ponnam`→`ponnom`); `venum`-for-`kudunga` on 07-08 and 07-13. Well past
  the `/recalibrate` bar, and none of it was visible to any selector. **Three holes, one per
  direction of the loop:** (1) CAPTURE — the diagnosis existed only as free prose in
  `knock_log`'s `reply_line`; the synthesis lived in `learner.last_debrief`, a single string
  **overwritten every close**, so an error survived exactly as long as Anna retyped it, and
  `daily_session.md` drew repairs from *"the day's"* chat session so a phone correction was
  never in the draw at all. (2) CREDIT — `apply_verdict` is upgrade-only on the phone, and the
  07-30 volley scored ரொம்ப நல்லா இருக்கு as a hinted **fire** off a reply whose own recast
  corrected its tense: a wrong answer moved the production axis and took a rep. (3) RESURFACE
  — `reply_line` was read back only by the reveal-window and deck-coverage scans, so
  `sync_state status` showed *"replied (hinted)"* with no hint of what was wrong, and the
  ticket could only ever say an item was **due**, never **how it keeps failing**. Selection
  therefore re-offered the item and the scene re-asked it the same way, which is precisely
  how one recast shipped three times in three weeks looking like normal progress.
  **The fix:** `progress/slip_log.json`, append-only, written by the judge that saw the
  mistake and by `update --slip` at close; `SLIP_MANDATE` (split out of `JUDGE_MANDATE`,
  which the contract took to 1764/1500) makes the judge name the *pattern*, not the
  instance; Python drops any fire matching a slip's `want`; and one renderer feeds all three
  reader surfaces (status, the knock digest, the ticket) with per-row annotations hung off
  the deck and floor-gap items themselves.
  **Explicitly NOT a reversal of "continuity is prose memory, not a schema" (2026-06-17).**
  What was rejected there was `threads.json` *with due-ness scoring* — a schema that would
  make the **choice**. This makes none: it counts and groups, and Anna reads the group and
  decides. That decision's own second sentence is the argument for this one — *Python computes
  the menu; Anna makes the choice and the meaning* — and Python was computing no menu for
  errors at all, leaving the meaning to a string that gets overwritten nightly. `last_debrief`
  is untouched and still the running story.
  **What it replaces:** Anna hand-retyping error memory into the debrief each close (lossy,
  and it never covered the phone); and it supplies the missing counter for a law that shipped
  two days earlier and had been dead prose since — *"the same mistake twice through one format
  is that format's answer"* (`audio_channels.md`, 07-28) had nothing counting formats. That
  law now distinguishes **NEVER COMMISSIONED** (corrected in passing, no dose ever built —
  the state all three live patterns were actually in) from **ESCALATE** (a dose was built and
  he slipped anyway); telling him to "change format" when no format was ever tried is advice
  for a problem he does not have. `STUCK_REPS = 10` stands on its own evidence but fires late
  and only says *this isn't working*; a slip fires at 2 and says *what*.
  **Paid for in the same diff, per the word-budget rule:** `audio_channels.md` 659 → 633
  (retired the enumerated repair population, now the ledger's definition, and compressed the
  07-28 origin story) against its unchanged 640 ceiling — the split its constant demands is
  still owed, not taken here. `JUDGE_MANDATE` split rather than raised, for the third time
  that file has paid that way. Ledger seeded from the 13 corrections recoverable from
  `knock_log`, each verified against the reply that produced it before writing; substitutions
  excluded on the 07-27 law. Smoke case `s41`.
  **Residual, deliberate:** tags are free strings the judge coins, not an enum — an enum would
  force every new error into a pre-imagined bucket and mislabel exactly the ones worth seeing.
  The cost is drift (two slugs for one pattern); the guard is that the judge is shown the tags
  already in use, and drift is visible in `sync_state.py slips` and cheap to merge. Also: a
  slip's `want` resolves to a lexicon key only when the phonetic data supports it, and several
  records carry empty `phonetic` lists, so ending-shaped slips often hang off no row — the tag
  carries the meaning there, and the ticket annotation is best-effort by design.
- **A slip retires, it never disappears — and a close is a dated observation, not a verdict**
  (2026-07-30, Andrew: *"words shouldn't disappear into the aether. They should be retired
  and then come back... re-eligible after a few weeks"*). The ledger shipped the same day
  with two ways for a pattern to go silent, and **both lost information**. (1) `--close`
  wrote a **bare tag** to `learner.slips_closed`, and `live` was `not closed and ...` — so a
  closed tag could never be live again, at any distance, no matter how many times he missed
  it. That silenced the single most informative event the ledger can record: *a pattern you
  believed had landed, coming back*. (2) The 21-day quiet window looked correct and was the
  same bug on a timer: `days_quiet` counts **days since he last failed**, which has two
  causes the code could not tell apart — he learned it, or **nothing ever asked him**. All
  three live slips were flagged NEVER COMMISSIONED, i.e. squarely the second case, so the
  window was on course to convert *"we never checked"* into *"gone"* without anyone acting.
  **The fix, one mechanism replacing two broken halves:** a quiet tag now RETIRES to
  `unverified` and surfaces as a re-eligible **check** ("never confirmed landed — test it"),
  passive by design — it asks for a scene, it never earns a commission (Andrew's call; the
  alternative, letting rechecks compete for the soak order, would crowd out new ground).
  Closing moved to `record_slip_test` — `--slip-tested tag:landed|missed` — which stores a
  **date**, so a slip dated after its close voids it and returns `reopened`, history intact.
  `missed` appends a slip row rather than a parallel record: a failed test *is* a recurrence.
  **Why Anna reports rather than code observing it:** word-anchored slips could close off the
  lexicon going cold, but the ending-shaped ones (`1pl-past-om`, `past-tense` — two of the
  three live) hang off no lexicon row, and nothing observes "this scene created a chance to
  get the ending wrong." Two close paths with different guarantees is worse than one honest
  one, so both go through the report and the protocol says out loud that it asserts an
  **observation, not a verdict**. Residual, named: it leans on Anna reporting honestly.
  **Also fixed in the same pass:** `slip_patterns` took `last` as *last-seen* rather than
  `max` while `first` already took a proper min — latent, because `append_slips(when=…)`
  exists precisely to backdate and the 07-30 seed backfilled three weeks in one write; an
  out-of-order pair read span 0d/quiet 6d instead of 5d/quiet 1d, which can retire a slip
  that is still live. `SLIP_QUIET_DAYS` → `SLIP_RETIRE_DAYS`, pinned to
  `generate_callbacks.INTERVAL_DAYS["cold"]` so patterns and cold words age on one clock.
  The judge is now shown retired tags too — a return is only visible if it reuses the old
  tag instead of coining a synonym. Paid for in the same diff: `daily_session.md` holds at
  1250/1250 (retired the duplicated commissioning law, now a pointer to `audio_channels.md`,
  plus three restating clauses) — the close half was added without a budget raise. Smoke
  `s41` grew the full lifecycle: retire → unverified → landed → **recurs → live again**.
- **Python is budgeted too — the ratchet moves one layer down** (2026-07-31, Andrew's
  call, from the engineering-vs-learning audit). Evidence that opened it: through July the
  word budget held prose FLAT (8866 words 07-01 → 11511 on 07-15 → 10671 on 07-31, a net
  deletion in one of those weeks) while production Python went 2566 → 6032 lines at a ~10%
  deletion rate, +1207/−115 in the final week alone. **April's failure mode did not die; it
  moved to the surface with no ceiling.** `CODE_BUDGETS` + the completeness guard in `s18`
  (renamed `s18_size_budgets` — one case, one law, two units, rather than a second parallel
  mechanism) now bind every `scripts/*.py` on exactly the terms `PROSE_BUDGETS` already
  carries: growth past budget is a red run, a raise rides the same diff as the growth and
  names what it retired, and a file that keeps hitting its ceiling is doing two jobs —
  split-or-retire, never bump-the-number.
  **The unit is CODE LINES — blanks, comments and docstrings are free.** A third of this
  codebase (33%) is comment, and that third is the diagnosis layer; the 07-31 silent-failure
  family was findable only because the "why" sits beside the mechanism. Taxing explanation
  would buy smaller files by deleting what makes them debuggable. `code_lines()` strips
  comments via `tokenize` and docstrings via `ast`, so a comment-only diff cannot move the
  number and a mechanism-only diff cannot hide from it (both proved before commit).
  **`smoke_test.py` is exempt, deliberately:** `/extend` Gate 7 requires a new case the day
  a bug is fixed, so budgeting the regression net would put two mechanisms in conflict and
  the budget would win — a fixed bug would arrive with a reason not to pin it. Test volume
  is the one growth this system wants unbounded. The completeness guard is what stops the
  exemption becoming a hiding place: a `scripts/*.py` with no budget is itself a red run,
  because adding a file is the obvious way past a ceiling.
  **Budgets set at the 07-31 census, rounded up to the next 25 with a 25-line minimum
  headroom** — tight enough to bind within weeks at a normal pace, loose enough that one
  ordinary repair lands without ceremony. Headroom is room to repair, not an allowance to
  spend. Replaces nothing; it extends the 2026-07-16 prose-budget law to the surface that
  never had it, and retires the informal expectation that `/extend` Gate 4 alone would hold
  Python back — the same expectation that demonstrably failed for prose before 07-16.
  Port surface: none — no prompts, no `TAMIL_RE`, no voice IDs, no `REPO`. Same residual
  `PROSE_BUDGETS` already carries: the table binds this repo's filenames, so a port inherits
  the mechanism and must re-census the numbers.
- **The silent no-op test — meters must measure effect, not execution** (2026-07-31,
  distilled from Andrew's engineering-vs-learning audit). He asked whether the deep bugs of
  the past fortnight were placeholders, under-described features, or true regressions.
  Answer: **all three are present** — commissioning was a real regression (worked from
  `4666c58` 06-16, killed by the `92e95a4` 07-16 compression pass), deck starvation was
  *never built* (the sort had no staleness term; prose said rotation, code said
  alphabetical), the sidecar callback branch was a **placeholder whose partiality was never
  recorded**, and the `session_log` append was simply wrong from the start. But that cut
  does not explain them. **The unifying property does: every one was a state
  indistinguishable from success.** The instruments were present and confirmed success —
  they measured that a step RAN, never that its PURPOSE was served. Soak order *set* vs.
  *contains the day's repair*; item *surfaced* vs. *coverage across the deck*; callback *in
  the script* vs. *lexicon record exists*; close *written* vs. *close survives the write*.
  **The evidence that settles it:** `70ee737` (07-30) shipped `slip_closes` with a DECISIONS
  entry AND a smoke case, and the feature was dead on arrival for a full day — `s41` tested
  the judge-side slip logic, never called `cmd_update`, never re-read `learner.json`. Green
  suite, dead feature, correct process. The root cause wearing best practice as camouflage.
  **Now canon as `/extend` Gate 7.2** (and cross-referenced from `/debug` §5): before the
  case is written, answer *"what does this look like when it silently does nothing, and can
  the system tell that apart from success?"* — assert the effect not the execution, round-trip
  through the writer and re-read the state file, make the absence loud. If the honest answer
  is "exactly like success", the bug is still in the diff. Replaces nothing; it sharpens Gate
  7.1, which mandated a case per fixed bug and never said what the case must bite.
- **The quiet class is a promotion, not decay — and it is load-gated** (2026-07-31). KF-1
  through KF-11 are LOUD (crashes, parse failures, clobbered notifications, visible desync):
  found because something broke in front of him. Everything since 07-24 is QUIET: nothing
  fails, the dose is merely about the wrong thing. That transition is caused by **usage**,
  not rot — the system crossed from "does it run" into "does it do what it claims", and only
  a user can sense the second. **Four of the seven were load-dependent, not
  contact-dependent:** `session_log` needed multi-call closes, the CWD-path bug needed a
  second caller, the callback gap needed a word-shaped callback, starvation needed the deck
  to outgrow its frozen head. At 2 session-days in 19 these were unreachable at any level of
  care. **Therefore the honest convergence metric is not the defect rate** — that tracks
  rising load and should keep producing hits while load rises — **it is repeat felt-signal on
  an already-diagnosed axis.** The record holds exactly one 3-peat (07-11 "stopped looking
  forward" → 07-17 "starved of teaching" → 07-17 "it's a chore"), and it terminated properly
  in a structural change plus an explicit rejection. A fourth complaint on a diagnosed axis is
  the signal to reopen the complexity question; nothing has produced one.
- **The ratio inverted, measured, and it moved the outcome** (2026-07-31, the audit's
  numbers — recorded so the question is not re-derived from feel). Engineering commits per
  learning session, with share of days carrying a real session: **June 11.3/session at 10% of
  days; Jul 1-12 30.0/session at 17%** (nine of twelve days engineering-only — the peak of
  the failure mode, and it is behind him); **Jul 13-17 7.7 at 60%; Jul 18-24 7.0 at 71%; Jul
  25-31 8.7 at 86%**, one engineering-only day in seven. Absolute engineering volume barely
  fell — it stopped *replacing* sessions and started *attaching* to them. **`floor_pct` is the
  proof it was not whack-a-mole:** flat 15.3 → 16.2 across the 28 days 06-24→07-22
  (0.03pp/day), then 16.2 → 23.8 in nine days (0.84pp/day), a ~26x slope change; cold fires
  per session 1.6 → 3.2. Whack-a-mole holds the outcome flat while the commit count climbs.
  **The prose budget is the mechanism that held:** protocol words 8866 (07-01) → 11511
  (07-15) → 10671 (07-31), flat for three weeks with a net deletion in one of them, having
  refused the commissioning law twice and forced it into Python on the third. That is the
  precedent `CODE_BUDGETS` was extended from, the same day.
- **The commission gate blocks the close** (2026-08-01, Andrew — chose the hard gate over
  auto-commission and advisory-print). A close over a live NEVER-COMMISSIONED slip pattern
  is refused before any write; `--slip-commissioned` pays the debt, `--slip-tested :landed`
  discharges it, `--no-commission '<why>'` overrides with the reason on the record. Python
  stays the detector, never the chooser. Ships "the flag needs teeth" (07-31). Smoke s46.
- **Hinted gets a follow-up path — the retest block** (2026-08-01). `coverage_key`'s
  fewest-reps-first buries a repped-but-stale hinted item behind never-worked ones for
  ever (the three FAQ answers, 22–28d silent); the ticket now surfaces hinted items silent
  ≥14d for a cold retest in a scene. A session move, never a commission — the parked
  cold-decay item stays parked. Smoke s47.
- **The drill answer key is linted — any fail stops the run, and a broken grader is a fail**
  (2026-08-01). The 08-01 tape rehearsed இடது பக்கம்ல for பக்கத்துல ×10 on the tape fixing
  the top slip; a second single-shot grader now checks every answer against its cue, on the
  studio's stop-for-inspection contract. Smoke s48.
- **A defective eavesdrop is refused, never degraded to text** (2026-08-01). Supersedes the
  07-25 degrade-to-text remedy: the body is a drift question about a tape, so a text
  degrade IS the broken audio promise reported twice on 07-28. A lost dose is cheaper than
  a broken one; fielding keeps its degrade (its body is a self-contained phonetic question).
- **The audio_channels split was taken — `commissioning.md` owns "what it carries"**
  (2026-08-01). The third raise refused in advance (07-28) came due: audio_channels keeps
  routing + format, commissioning.md carries the repair-first law, each pointing at the
  other; daily_session's Close & Log pointer re-aimed. s37 asserts the seam.
- **A ceiling split re-censuses the budget DOWN** (2026-08-01). OUTREACH_MANDATE →
  `mandates.py` took morning_knock 699/700 → 598/625, the first down-census. A split that
  leaves the old ceiling standing converts the freed room into an allowance — the
  bump-the-number reflex through the back door.
- **The decision log gets a forward entry cap; no retro pass** (2026-08-01, Andrew).
  Entries dated 2026-08-02+ lint at ≤150 words (s18): this file's own contract is "the
  index of the conclusions" and July ran it to 22k words — the accumulation pattern the
  budgets killed everywhere else, on a surface that had none. Narrative belongs in the
  commit message; the July archive stays as written, git owns it.
- **The work-TLS notify failure is a quiet accept, not an error** (2026-08-01, Andrew:
  "not worth engineering around"). `push_to_phone` returns False on
  CERTIFICATE_VERIFY_FAILED with the known-cause line, so a successful local render no
  longer exits non-zero (the 07-28 duplicate-tape cause). Rejects the deferred
  route-via-queue alternative outright — the feed is the delivery guarantee.
- **The lexicon flock stays deferred — fcntl cannot guard the machine at risk**
  (2026-08-01). The 07-13 revisit condition fired (session-open renders made overlap
  structural), but the trip's primary machine is the Windows work laptop where fcntl does
  not exist, and no lost write has ever been observed. Revisit on first evidence, with a
  portable lock.
- **Reference docs anchor to function names, never line numbers** (2026-08-01). flags.md's
  numbers drifted by hundreds twice under a "stable as of this commit" policy; names
  survive edits and grep finds the spot. The resync ritual is retired, not repeated.
- **A dose that fails twice indicts the diagnosis before the channel** (2026-08-02).
  `1pl-past-om` (6×) and `past-tense` (5×) were tagged as a failing person-tail; Andrew
  had the -ஓம் tail all along and was hanging it on the wrong verb body (போறேன் / போகணும் /
  போனேன் are three bodies, and nobody had shown him the body is a *choice*). Episode 07-31,
  memo 08-01 and drill 08-01 all soaked whole past *words*, so audio_channels' escalate-the-
  format law ran three times against the wrong target. One teach — pick the body, then the
  tail — closed both slips and `it-tail-uchu` within the hour. Refines, does not reverse,
  "change the format, never loop harder": re-read what the slip tag actually names first.
  Cold retest owed 2–3 days out; one fire an hour after the teach is not proof.
- **The knock reply thread carries actions, not just words** (2026-08-02). The exchange
  record kept only `reply`/`reply_line` and the window was one knock's last four turns, so
  Anna rendered and delivered an audio greeting, called it "still pending" a turn later, and
  resolved "he's an anglophone" to Andrew himself. `spoke`/`audio_url`/`scheduled` now land
  on the exchange, and `recent_exchanges()` spans knocks by time (24h, 8 turns). Safe to
  widen because cold-fire evidence stays with `revealed_recently()`/`shown_in_knock()` —
  s49 asserts no grading field can reach the thread. THREAD_MANDATE is JUDGE_MANDATE's
  fourth split; knock_reply.py's code budget took a 775→785 raise with a standing note to
  refuse the next one and move the mandates to `mandates.py` instead.
- **"Audience before artifact" rejected — continuity is the fix** (2026-08-02, Andrew). A
  rule forcing Anna to name an artefact's audience before composing was cut: "less dense
  Tamil" is an ordinary correction Andrew makes on the next turn, and it only failed
  because the thread had nowhere to keep it. Encoding one conversational correction as a
  named mechanism buys a rule and leaves the cause standing. Rejected in the same pass:
  re-injecting `meta_note` as standing direction (his words already ride in `andrew_said`)
  and the unkept-promise guard (redundant once the record is honest).
- **Gift audio renders outside the mission pipeline** (2026-08-02). The Mum-and-Doodah
  greeting went through `render_demo.py` + `rebuild_rss.py`, never `run_studio.py`: a piece
  for third parties must not burn a mission number, stamp `seen_in`, or move Andrew's
  recognition axis. `special_` scripts are the standing lane for feed-worthy artefacts that
  are not doses.
- **CI checks out the branch tip, and derived files are re-rendered, never merged**
  (2026-08-04). Run 30865736387 lost a judged reply to "rebase needs a human". The
  concurrency gate was *working* — the job waited for the run ahead of it — but
  `actions/checkout` fetches `github.sha`, pinned when the dispatch is **received**, so
  serialising only widened the gap between pinning and checkout and *guaranteed* a stale
  tree. The two fixes were fighting. `ref: main` closes it; the rebase drops back to being
  the net for the laptop. Second cause: `chat.md` renders from `knock_log.json` and holds
  no state, yet a conflict in it refused the whole rebase — derived files now rebuild from
  the merged source. The tap lane's hand-rolled push moved into `sync_state.py`, so every
  lane lands through `commit_and_push`.
- **Andrew is family already; only the Tamil is new** (2026-08-04, Andrew). M81 opened at
  the iron gate with sisters-in-law he "recognised from the old photos" — the Director's
  Scenario Context had invented a first meeting. He is ten years with his wife, nearly ten
  married, a dozen visits in; the welcome was warm from the start, and he began at year
  nine not for want of will but because the language looked impossible to attempt until
  agents made it tractable. No file owned this, so every generator filled the blank with
  the newcomer-integrating story. Now canon in `constitution.md` ("Family Already, Language
  Not Yet"), embodied in `persona.md` ("Ten Years In" — the Python doses inline persona
  only), and pointed at from `director.md`'s Reads-from, which read neither. Never write him
  auditioning for entry.
- **The tier prefix belongs to the shared ordering law, not to each caller** (2026-08-04).
  `retest_targets` (08-01) sorted on staleness alone with no deck term and a five-item cut,
  so the three hinted FAQ answers — the day-one aunt questions, 25–31 days silent — sat
  below the line behind ordinary vocabulary, and the top slot went to a bootstrap artefact.
  `deck_rank()` owns the prefix now and the hand-copies in `pending`/`untouched` are
  retired. Fifth recurrence of one failure; extends "one selector, one ordering law"
  (07-25) instead of stacking a sixth patch. The touchdown bar is untouched — survival
  still outranks delight in the sort.
- **A capped list's failure mode is the cut, not the order** (2026-08-04). Smoke s47
  asserted the retest block's ordering at `max_n=100`, where nothing can fall off, so it
  never tested the one place the block can fail — and the block returned five confident
  wrong rows for four weeks while green. A case for a truncated list must make the wanted
  rows *less* attractive on the sort's secondary axis and still require them to survive a
  cut too small to hold everything.
- **A never-surfaced item is excluded from a retest, never featured in one** (2026-08-04).
  There is no prior test for a *re*-test to repeat, and `coverage_key` leads with
  fewest-reps, so such an item already sits at the head of the main ticket. The old code
  ranked it first on sentinel staleness and printed "worth asking why", spending a scarce
  slot on a grade nobody set.
- **The duplicate signal is the phonetic plus strict domination, never the key**
  (2026-08-04). Rejects key normalisation — the obvious fix, and a destructive one:
  `எங்க` is "our (exclusive)" and `எங்க?` is "Where?", two lemmas one character apart,
  because punctuation is load-bearing identity in this lexicon. `prune-duplicates` drops
  only rows that share a phonetic and are poorer on every axis, `frame:` keys exempt (a
  frame legitimately shares its exemplar chunk's phonetic). `ஃப்ரீ-யா`/`ஃப்ரீ-யா?` has no
  phonetic on one side and no automatic signal reaches it — left standing rather than
  contorting the rule to catch it.
- **The trip is two eras, not a deadline** (2026-08-04, Andrew: "think of it as pre-trip
  and during-trip eras"). `TRIP_DATE` was modelled as a terminus, so from the day he lands
  the scoreboard read "-20 days to touchdown · need 8.0 cold/day" forever —
  `burn_rate`'s `max(days_left, 1)` clamp froze the ask at its final day's value. The
  countdown hands over to "in country, day N" and the burn ask is dropped at the boundary,
  guarded inside `burn_rate` because `show_status` reads it directly too. In country the
  table sets the pace: never narrate a deficit there.
- **The last week buys coverage, not clearance — and scope is not cut** (2026-08-04,
  Andrew: "this final week should be not less aggressive"). Rejects triaging delight to a
  winnable subset. He has laptop, phone and a month at that house, so touchdown is a
  handover and every delight line is situationally cued three times a day. An item never
  seen cannot be triggered by a situation; one seen once can. All 33 untouched items get
  first contact before the plane; the month buys the firing. Does not reopen the touchdown
  bar — the selector still leads with survival.
- **Audio seeds, chat fires, knocks ambush** (2026-08-04). Thirty-three first contacts
  cannot enter through the lunch session: Calibration caps chat at ≤1–2 new word types and
  says outright that chat is production, not soak, while audio takes 4–5. First contact is
  an episode's job; the next day's chat fires what it seeded. Where an item is already
  `hinted` it fires rather than seeds.
- **sync_state split three ways, and the import direction is one-way** (2026-08-04,
  Andrew: "1250 is a smell not a hard limit"). Mapping the file for a split surfaced a
  mis-shape older than the size problem: ten scripts imported `load_json` and
  `LEXICON_PATH` *from the state brain*. `state_io` (paths, IO, resolve) imports nothing
  from `scripts/`; `slips` imports it; `sync_state` imports both; `session_brief` sits
  above all three, reached by a deferred import at `main`'s dispatch. 1250 → 766 lines.
- **Static clean is the ratchet's fourth surface, budget zero** (2026-08-04, Andrew). The
  suite proves only what it executes, and Python resolves globals at call time, so a
  dropped `DEMOTE` table passed 53 green cases while any `--stuck-word` close would have
  raised NameError. pyflakes found it without running anything — the `actionlint` argument
  one language over. Zero is not tunable: pyflakes has no severity levels by design, so
  every finding is a defect or dead code. An absent linter fails rather than skips.
- **A suppression directive standing in for legible code is how a load-bearing line comes
  to read as dead** (2026-08-04). `run_studio`'s dispatch lock was a local carrying
  `# noqa: F841 — held until exit`; it holds the flock's file object, so deleting the
  "unused" binding would have released the lock. Now a module global with the reason in a
  comment. `studio_watchdog` held the mirror case — `# noqa: F401 — re-exported` for names
  nothing imports, and the directive itself had been silently lost in a rewrite.
- **The payload IS the scale — `scale` deleted** (2026-08-05, Andrew: *"it should be
  deleted and ideally it then functions as an n-item payload"*). The 2026-07-18
  narrated_drama decision named a `scale: "long"` commissioning key that was never built:
  no writer (`cmd_update` takes payload/seed/focus/channel/form), no reader, and its only
  appearance in the suite was a fixture proving unknown keys survive — which read as
  evidence it was real. Redundant twice over anyway: the form already states ~12–18 min,
  and "buy items with minutes" already ties length to item count. So item count is the
  only dial, and a 2-item payload commissions a 2-item episode whatever the label says —
  which is what M81 was. Replaces the form+scale pair with form alone. Same diff:
  `narrated_drama` joins the Breakdown-omitted list; it was absent from that rule, so one
  got appended by default, and the Narrator has already glossed inside the scene.
- **The long-haul tape — a fourth audio lane, for a capacity the other three cannot serve**
  (2026-08-10, Andrew, two days before the plane). Twenty hours against ~50 doses at a
  median **2.7 min** is fifty press-plays and fifty format switches; he predicted he would
  not do it. The other three lanes are all sized for a 10-15 min workday slot where
  ADHERENCE binds; the flight inverts every term — unlimited time, no mouth, no screen,
  near-zero executive function. `render_longhaul.py`:
  Python owns the clock and the rotation, the model writes one small sheet per MOVEMENT,
  and the tape renders until a MEASURED target. The movement, not the line, is the unit of
  language mix; recall movements may only use what earlier movements taught. **Replaces**
  `render_soak.py --passes N` as the answer to "give me something longer". Does **not**
  reopen the 07-28 dose ruling, which is about the session.
- **A duration fallback must be visible, not plausible** (2026-08-10). `render_audio`'s
  `get_duration` was `except: return 3.0`, so on an ffprobe-less host every episode
  registered as exactly 3.0 min — M78-M85 all carry it, against real lengths of 1.7-3.5.
  It was invisible precisely because 3.0 is plausible for a short episode, and he judges an
  episode partly by the number his player shows him. Now measured through
  `rebuild_rss.audio_duration` (ffprobe, then the frame scan), reporting 0.0 with a warning
  when it genuinely cannot. Extends "feed durations are measured, never estimated"
  (2026-07-23) to the registry the feed reads from. Existing 3.0 stamps stand until each
  episode is next rendered.
- **One JSON parser, and a serial lane retries** (2026-08-10). The first 45-minute tape
  died at movement 5 of 15 — `Expecting value: char 0` — holding a good object under two
  lines of the model's own reasoning. `ask_json` had a private parse that only looked at
  character 0; `parse_llm_json` had already fixed that family (07-04, 07-07, 07-13's
  *prose before a fence*) and this lane never called it, so it re-earned the bug. The
  mandate invites the prose: the `inventory` clause orders a judgement per host, so the
  writer shows its work — **measured 3 of 6 calls**. **Replaces** that parse with
  `parse_llm_response`, plus a 3-try loop: a coin-flip parse is survivable where a lane
  asks once and fatal where it asks fifteen times. Truncation still fails loudly rather
  than re-rolling (the 08-05 guard). The rule: **a second parser is how a fixed bug
  comes back.**
- **A cue is a beat inside a line, never a replacement for it** (2026-08-10). `parse_script`
  ran `PAUSE_RE.search` before the speaker check, so any spoken line carrying an inline
  `[Pause: 1 sec]` became silence and **its dialogue was discarded** — 56 lines across 13
  episodes, eighteen in M74, whose analysts teach almost entirely in inline-paused lines.
  Invisible by construction: the render succeeds and is merely shorter. **The missed half
  of the 07-18 SFX audit** — same file, same failure mode. **Replaces**
  the pause-before-speaker ordering with one path: speech is recognised first and split
  around its cues, rendering speech-pause-speech in written order. The regex stopped
  being three dialects (`[Pause: 1 sec]`, fractional, bare `[pause]`), and `[^\]]*` replaces
  a greedy `.*\]` that swallowed the text between two pauses. M74 re-rendered to `_v2`;
  the other twelve stand. `s22` grew a **corpus guard** — fixtures prove the parser, only
  the corpus proves the tank.
- **Fail forwards: a renderer fix does not oblige a backfill** (2026-08-10, Andrew, on the
  inline-pause bug). Fix the machine, add the guard, re-render only what is still
  load-bearing — the rest of the tank stands as shipped. A published episode is a spent
  dose, not a record to keep true: its words have already moved through the lexicon, and
  re-rendering a month of audio costs quota and feed churn to improve doses nobody will
  play again. Applies to every derived artifact the pipeline emits, not just audio. The
  question to ask is *"is this one still being used?"* — M74 was (live deck material, two
  days out), the other twelve were not. Do not re-ask this per bug.
- **The transit bit — one date in `learner.json`, enforced by the rails** (2026-08-10, Andrew).
  Apple queues exactly ONE push for an unreachable phone, so a 20-hour flight turns every dose
  after the first into an overwrite — and the unanswered fires feed `outcome_memory`'s
  ignore-streak, which at 3 tells Anna her approach "isn't converting", days after landing.
  **Supersedes the standing-order version taken and reverted the same afternoon**: debrief prose
  is read by *every* tick, so a note about tomorrow's flight steers today's knocks — Andrew's
  objection, and correct. **Rejected: pausing the cron** (fails unsafe). **Taken:**
  `--quiet-until YYYY-MM-DD`, read
  first in `rails_gate`, which returns before the LLM and writes nothing — so the held stretch
  leaves no rows to be misread as fading. Deliberately deletable: three lines in the gate, one
  whitelist key, one CLI flag. Status prints ⏸ when held; clearing accepts `""`/`off`/`none`.
- **The campaign block matches the heading, never its title** (2026-08-10). `campaign_block()`
  required the exact string `## The Campaign — This Week`; the 08-04 rewrite renamed it *The
  Last Week Before, and the Month During*, and the digest carried **no campaign for six days**,
  silently — while `s17`'s heading-count assertion stayed green, because the heading existed
  and only its TITLE had moved. **Replaces** the exact-string match with a prefix match: the
  title is Anna's prose and she renames it every campaign. The 07-26 one-heading invariant is
  untouched. `s17` grew the assertion that was missing — run the extractor against the REAL
  `profile.md` and require a non-empty block. Fixtures prove the extractor; only the real file
  proves the digest. Same lesson as `s22`'s corpus guard, the same morning.
- **Every subprocess decode is pinned to UTF-8** (2026-08-10). `subprocess.run(text=True)` with
  no `encoding=` decodes with the *locale* codec — UTF-8 on the Linux runners, cp1252 on the
  Windows laptop. Every one of the seven sites reads git output or our own scripts' stdout,
  which is always UTF-8 and routinely Tamil, so the same code was correct in CI and broken on
  the machine that renders. It cost a full day of misreadings: `morning_knock.build_digest`
  could not run locally at all, and `s51`'s chat.md equality failed with mojibake that read
  first as a content bug, then as a CRLF artifact. **Replaces** the locale guess with
  `encoding="utf-8"` at all seven. `render_chat` also pins `newline="\n"`, since chat.md is a
  tracked derived file both CI and the laptop regenerate and byte equality is its contract.
  A green CI is not proof the code is portable — it is proof of one locale.
- **The two travel dials have different owners: the zone is standing, `quiet_until` is Andrew's
  toggle** (2026-08-13, Andrew, on landing in India). **Adds the ownership rule the 08-09 and
  08-10 entries left implicit** — each built a dial, neither said who turns it, so the first real
  trip had an agent offering to arm the pause on his behalf. `learner.json.timezone` is *where he
  is*: standing until he says otherwise, never inferred from a debrief, a calendar, or a flight
  time in prose. `quiet_until` is *when the teacher is paused*: his toggle, for vacation and
  transit, armed and cleared on his word alone. Neither is an agent's call — offering once is
  help, arming is overreach.
- **A lexicon record is born reachable — the phonetic is taken at the mint, never "later"**
  (2026-08-14, Andrew). `resolve()` is exact-match on a record's `phonetic` list, and three mint
  sites wrote `[]` under a "backfill later" note. Later never came: 96 of 313 word records had
  none, 88 `production: none`, and 5 of the 12 items on that day's focus set were unloggable —
  the ticket named targets the logger then refused. A deletion, not a detector: two paths
  already demanded Tamil script and discarded the phonetic Anna held, while `add-word
  --phonetic` took it properly. **Replaces** those three comments with a `|phonetic` tail on
  mint specs, refused on a new word, ignored on a known one. Andrew's ruling: refuse at the
  interactive mint AND ratchet the debt (`s59`, ceiling 96), since `render_audio` mints
  unattended. No backfill; the ceiling may only fall.
- **The headline is the ear, not the mouth** (2026-08-16, Andrew, in country: "we stop counting
  what comes out of your mouth and start counting what you can hear"). His lexicon: of 26 frames
  he PRODUCES 20 cold and RECOGNISES 3 as solid — ten machines he can fire unaided still pass him
  unheard at speed, which is the felt complaint ("2 words in a fast sentence does
  almost nothing"). "Engines online: 19/21" led the line for a year and is a *production*
  number; the recognition axis was tracked on every pattern record and surfaced on no meter
  (`session_brief` skips patterns, `compute_engines` reads `production` only). `Machines heard`
  **replaces** the Trip Deck as the scoreboard's lead — the 07-27 horizon gap's
  successor, early — and demotes Engines. **Nothing was built to score it**:
  `apply_catch_verdict` already walks the ladder, `resolve()` already returns `frame:` keys.
  Denominator includes `direction: catch`. Smoke: `s60`.
- **Meters steer Python; Anna never recites a number** (2026-08-17, Andrew). Achievement-goal
  framing, not taste. The mechanism first written here — withdrawal "when progress is slow" —
  was wrong, and Andrew corrected it: *"'moving slowly' isn't a reason to quit. Feeling that
  the mountain is too big or we're no further than we were is the factor."* The trigger is
  perceived distance *covered*, not pace, and a large denominator reports only the remainder.
  The 07-17 law guarded one line while `catch_meter` pushed "Catch 3/12 · 12d" to his lock
  screen after every eavesdrop reply. **Deleted**, not softened; `persona.md`'s "never shames
  the pace" bullet absorbs the rule (no fraction, percentage, countdown or streak), the brief
  labels the block ENGINEERING NUMBERS, and the positive half is canon in `constitution.md` →
  Ground Covered, Not Ground Remaining. The numbers stay, for selection. Smoke `s61`.
- **The return clock is keyed to the ear, and returns only what was met** (2026-08-17, Andrew).
  `generate_callbacks.py` was already a real spaced-repetition selector; two exclusions gutted
  it — patterns skipped ("tracked engines, not soak words") and struggled rows skipped ("audio
  doesn't fix cold-production gaps"). Both were right under a production headline and both
  removed exactly what a recognition headline lives on: the 26 machines, and the 144 struggled
  rows that are the cheapest inventory to recover. `INTERVAL_DAYS` re-keyed to recognition,
  same 21/10/5 shape. **Third fix, found only by running it on real data:** never-surfaced rows
  entered at the sentinel and outranked every overdue row, so all eight live slots read "never
  surfaced" — the clock had never returned anything while looking like it worked. Excluded, per
  `retest_targets` 2026-08-04. Smoke `s62`.
- **The threshold is comprehension; production is the engine** (2026-08-17, Andrew: *"what's
  measured, what's selected, what's taught should be cohesive and clear, not a bunch of knobs
  to twiddle"*). The three entries above are consequences of one sentence nobody had written
  down — which is how a felt signal became three dials. Now canon in `constitution.md`: the
  Learner crosses *the threshold where the room stops being noise*, and **Ground Covered, Not
  Ground Remaining** supplies the positive half the 07-17 meter law lacked. **Does not reopen
  "Absorption-first, then production-as-accelerant"** (04-09/06-07) — forced output is still
  the engine, still daily. What ended is reading its odometer as the map: production won every
  meter because it was *countable*, never because it was the goal. `PATTERN_SLOTS` (smoke
  `s63`) fixes the hollow third consequence — patterns were eligible but sat at rank 59 of 100
  due rows. `director.md`, `profile.md` and the `/orient` glossary re-pointed.

- **The ask cooldown is 7 days, and the session lane can see it** (2026-08-18, Andrew: *"the
  pushes have been trying to repeatedly teach me innoru thadava sollunga"*). That line reached six
  surfaces in eight days under four move names. Two holes. **The window was shorter than his reply
  latency:** 3 days, against re-asks at 3- and 4-day gaps and a 4-of-14 reply rate. **The session
  lane was blind:** `session_brief` — where Anna writes the soak order, campaign mission and slip
  medicine — never imported the selector, so three of the six came from there.
  `ASK_COOLDOWN_DAYS = 7` now owns every mention of the window; the brief prints ALREADY ASKED and
  flags unanswered rows, since a reply-less ask never sets `last_surfaced` and so makes an item
  *more* eligible. KF-6 through the door KF-6 left open. Advisory on Anna's prose lanes — no Python
  choke point exists there. Smoke `s64`.

- **Retire the Trip Deck** (2026-08-18, Andrew: *"deletion, cleanup should ease a lot of the other
  symptoms, instead of a dozen patchwork fixes"*). Decided here; executed against
  `docs/deck_retirement.md` (retired 2026-08-26; in git). The deck is a **container** whose reason expired at touchdown; the
  tiers are an **ordering** that is durable. Retire the first, keep the second. Evidence: the
  ticket runs 361 lines over 9 pools with **three** sections claiming primacy (deck, slip ledger,
  machines heard), and every insight since July added a pool without retiring one — the
  accumulation mode `JOURNEY.md` names, in selection surfaces rather than prose. The deck is also a
  production meter, so it optimises the axis demoted 08-16. **The trap:** `register`, which tiers
  are computed from, lives in `curriculum/trip_deck.json` and on **0 of 339 lexicon rows** —
  removing the deck naively deletes the ordering silently. Migrate first. `deck` tags and
  `seed-deck` are kept as provenance.

- **`register` is a lexicon row field** (2026-08-18, Andrew, commissioned in the deck-retirement
  work order, since retired
  — a deliberate Gate 2 schema change during the structure freeze). It is the ordering the retired
  deck left behind: antifreeze/public/frame → survival, faq/mil-table/social → delight,
  gossip/zinger → dessert. It **replaces** the menu-time join of `curriculum/trip_deck.json` keyed on
  `deck` membership (`deck_registers` + `deck_rank`, both deleted). A join keyed on a tag we were
  deleting fails *silently* — the selector keeps returning rows, merely unordered — so the migration
  had to lead. `sync_state seed-deck` is the only writer; 83 of 339 rows carry one and the rest
  degrade to delight, unordered but not unreachable. Classifying the other 256 is a curriculum
  project, not this one. Smoke `s65`.

- **One pool, no primacy** (2026-08-18, executing the deck retirement). `floor_gap_targets` **replaces**
  `deck_status` + itself + `retest_targets`: nine ticket selectors became five, and "force these
  before the general floor" is gone. Going-dark is a rule plus a `RETEST_SLOTS`
  reservation — a floor, never a ceiling. The knock menu, the volley and the drill
  tape read one view (`drill_menu`), so no lane re-sorts. `TRIP_DATE`, `burn_rate` and `compute_deck`
  are deleted: a countdown has an entry and no exit, and a required pace without a deadline is a
  guess. `compute_ear` is what survives — the one axis nothing else counts. A stored focus cohort can
  now go stale against the ORDERING, which `reconcile_focus` cannot fix (it only fills seats as
  they open), so `sync_state reseed-focus` re-derives it — a command, never automatic, because
  rebuilding membership is the churn stored membership exists to prevent. Smoke `s54`, `s32`,
  `s47`, `s65`.

- **Structured output on every JSON lane** (2026-08-18, Andrew). All five lanes that ask for an
  object now send `response_format={"type": "json_object"}` — `JSON_MODE`, defined once in
  `morning_knock`. It **replaces** prompting-for-JSON-and-hoping: the mandates always said
  "return ONLY a JSON object" and models wrapped it anyway, which is why `parse_llm_json` grew a
  five-strategy fallback chain across four incidents and why the long-haul lane measured 3 of 6
  identical calls coming back prose-prefixed, killing a render at movement 5 of 15. Retired in
  the same diff: `render_soak`'s private parse — the THIRD copy of the char-0 `json.loads` +
  fence-strip, after `render_drill`'s on 08-10 — which also never had the 08-05 truncation guard.
  The text lanes (`rephrase_phonetic`, the studio's prose writers) must NOT send it; smoke `s66`
  asserts both directions, because adding a parameter that gets dropped is itself a silent no-op.

- **The executor is the host's, for every lane** (2026-08-23, Andrew). **Replaces** the
  half-applied 08-18 split. `render_soak`, `render_drill` and `render_longhaul` opened an
  OpenRouter client unconditionally, and none has ever had a cloud caller — so every soak,
  drill and long-haul was billed to the API from a laptop holding a paid subscription.
  Measured per run: ~$0.06, ~$0.09, ~$0.84. All three now $0 locally. New `scripts/writer.py`
  owns the choice and makes it by asking which BINARY exists, never by a flag a lane must
  remember; `render_drill.ask_json` moved there and `render_soak`'s private client (the fourth
  copy of that idiom, the first that cost money rather than correctness) is gone. The cloud
  branch stays live — the routing rule is policy, not a missing capability — so it is tested by
  forcing, never deleted. Smoke `s70`.

- **A `--json-schema` must describe a SHAPE** (2026-08-23). `claude -p` carries the agent-side
  equivalent of `JSON_MODE`, which is what made the split safe — but handed `{"type": "object"}`
  it answers in an envelope: `{"output": "<the sheet as a JSON STRING>", "clusters": []}`.
  MEASURED on the first live soak. That parses, carries the key the lane reads, filters to zero
  clusters and renders an empty tape — every instrument green, the artifact a shell. So `schema`
  is a **required positional** argument of `ask_json` (a default reintroduces the exact failure
  it exists to prevent), each lane declares its own shape beside itself, and `_agent_json`
  refuses an envelope by name. Nested item shapes are declared too: unconstrained, an array of
  `{ta, en}` returns an array of strings. Smoke `s70`.

- **Anna's cloud lanes run on `google/gemini-3.7-flash` — TRIAL, revisit ~2026-08-27**
  (2026-08-23, Andrew: *"Gemini seems suited to the task"*). Replaces `claude-sonnet-5` on
  `decide()`, both judges and the phonetic rewrite — after the split above, all that still costs
  cash. Not a cost decision (~$0.0094 vs ~$0.050 per decide-shaped call). Verified: the slug
  advertises `response_format` and `structured_outputs`, its 65,536-token ceiling clears the
  largest `budget()` call, and a forced live call returned schema-clean JSON. **On trial is the
  Tamil, not the plumbing** — `MODEL` grades replies and grading writes the production axis, and
  smoke stubs the LLM. First signal, one live sample: JSON perfect, Tamil not — `நாங்` for "I",
  `-ுங்க` on `போனேன்`, and an intro naming the grammar rule the mandate forbids. Watch it;
  `knock_log.json` is the A/B corpus.

- **Two constants, because one executor is Claude-only** (2026-08-23). **Replaces** "one model,
  two executors" (2026-08-18) and its `f"anthropic/{MODEL}"` derivation, which assumed both
  executors can run one model. `claude -p` cannot run a Gemini slug. What that rule defends is
  kept: the model is STATED, once per executor, never derived. `MODEL` is cloud Anna;
  `AGENT_MODEL` is `claude -p`, and must be a slug the CLI accepts — MEASURED, `--model
  claude-sonnet-4.6` prints "may not exist" **and returns 0**, silently routing every laptop lane
  to the paid API. `claude-sonnet-5` verified. Smoke `s70` asserts the two shapes so they cannot
  be swapped.

- **Sonnet 5's $2/$10 was an introductory price** (2026-08-23, correcting the 08-18 note below).
  It expires 2026-08-31; from 09-01 sonnet-5 is $3/$15 — identical to the 4.6 it replaced, while
  emitting ~4x the output tokens, because reasoning bills as output and this system measured
  1,624–2,974 reasoning tokens per call. The 08-18 swap was argued partly on price; that half was
  never true beyond August. Recorded so the next model decision starts from the real number.

- **Anna runs on `anthropic/claude-sonnet-5`** (2026-08-18, Andrew: *"maybe it'll be more reliable
  or efficient"*). Replaces `claude-sonnet-4.6`. A newer generation at a **lower** price on
  OpenRouter ($2/$10 per M tok vs $3/$15), same 1M context, same structured-output support — so
  the switch stands on the generation, not the invoice: this lane runs ~4 calls/day (the rails
  gate returns before `decide()`, so gated ticks cost nothing) and totals a few dollars a month
  either way. **The risk is the judge, not the composer.** `MODEL` also grades replies, and
  grading writes the production axis, so a generation change re-calibrates the learning record
  silently; nothing in smoke catches it, since the tests stub the LLM. The 63 graded replies in
  `knock_log.json` are the A/B corpus if it ever looks off. Andrew owns that call.

- **One model, two executors** (2026-08-18, Andrew). `MODEL` is stated ONCE as a bare slug
  (`claude-sonnet-5`), with `OPENROUTER_MODEL` derived beside it; the studio writer is `claude -p`
  locally, the OpenRouter API in Actions. **Replaces** `agy` (Gemini 3.1 Pro) and the studio's
  separate `CLOUD_WRITER_MODEL` (gemini-3-flash). agy was retired for running **nowhere** — absent
  from the laptop, never in a runner — which left `openrouter_pass`, written for a cloud that has
  never invoked it, as the only writer executing anywhere; the canon-carrying bug fixed the same
  day lived in that gap. The local pass runs `--allowedTools Read Glob Grep`, enforcing the
  print-only contract that agy needed `--dangerously-skip-permissions` to fake. The host may
  differ; the model may not.

- **The routing rule: cloud sends, the laptop produces** (2026-08-18, Andrew). Actions produces
  text knocks and short memos only; every rendered format — episode, drill, soak, longhaul — is
  produced on the laptop, where `claude -p` spends a subscription instead of cash (measured: an
  episode is ~83k input tokens, ~$0.35 through the API, $0 through the subscription).
  **Lane-level, not length-level** — thresholds need tuning and drift; lanes are already the
  routing unit. Cloud Anna does not commission, so `soak_order` stays single-writer and there is
  no clobber to guard. The capability is capped by **policy, not deletion**: `openrouter_pass` and
  `inline_canon` stay, tested, with no default caller and comments saying so. A branch is safe to
  keep when nobody can mistake it for live.

- **Thinking is part of the budget** (2026-08-18). Sonnet 5 reasons before it answers and
  OpenRouter bills that inside `max_tokens`. Six hours after the model swap, `decide()` — the
  largest prompt in the system against a 1600 ceiling — returned zero characters three times
  and took cloud Anna's knock lane down (run 32121449441); the drill sheet died the same way
  locally at 1624-2974 reasoning tokens. **Replaces** eight hand-tuned `max_tokens` literals
  across five modules: a call site declares what its ARTIFACT needs and `budget()` adds
  `REASONING_HEADROOM` once, beside `MODEL`, because reasoning cost belongs to the model and
  not to the lane. Second occurrence — `knock_reply` was patched in isolation on 08-05, which
  left every other lane mis-calibrated until it happened to run, the drill lane for 17 days. A
  ceiling is not a spend, so headroom is free insurance and a truncation is a dead lane. Smoke
  `s66`.

- **Payload fidelity: verbatim for chunks, stem-tolerant for words** (2026-08-18). **Replaces**
  the flat substring test, and amends "Payload fidelity bends the sidecar, never the script"
  (2026-07-13) — the manual sidecar repair is no longer owed for a plain word. A verb stem can
  essentially never appear uninflected in natural speech: a script said தூக்கறேன், the sidecar
  honestly claimed தூக்கு, and the episode was rejected. The lexicon already draws the
  distinction — a `chunk` is drilled WHOLE and keeps zero tolerance (both incidents that earned
  this rule were chunk mutations), while a plain word matches on its stem, the item minus one
  trailing vowel sign or pulli. Deliberately narrow: தூக்கு→தூக்க admits தூக்கறேன், வேணும் still
  refuses the literary வேண்டும், and a stem under three characters falls back to verbatim. The
  check had no coverage at all before. Smoke `s28`.

- **The ALREADY ASKED block is bounded** (2026-08-18, Andrew, hours after the block shipped).
  The first cut printed every row in the window — 50 on live state, 27 of them single mentions —
  because the surface was added and the window widened 3d→7d in one commit, unmeasured. **Replaces** the unbounded print with `ASK_BLOCK_CAP = 8` and
  `ASK_REPEAT_FLOOR = 2`, sized to its siblings (`knocks_since` at 6, the knock menu at 6 fire +
  2 catch). Ties break unanswered-first, because a cap has to cut somewhere and count alone
  leaves 15 rows level. One mention is not a repeat — it is the case the cooldown permits. Only the
  READING is trimmed: `recent_ask_counts` still sees every row, so the selector's demotion is
  untouched. A guard nobody reads guards nothing, which is the silent no-op one layer up — the
  mechanism fires and the human doesn't. Smoke `s64`.

- **A shared lane must fail fast — `timeout-minutes` on the job and on apt** (2026-08-19,
  Andrew). **Replaces** GitHub's 6h default as the only bound on `anna.yml`, and widens what
  `continue-on-error` promises: it covered a step that FAILS, and this step's failure mode is
  that it never returns. The apt mirror hung twice, silently under `-qq` — 57 min on 08-17
  (run 32070415338, recovered, unnoticed) and unbounded on 08-18 (run 32165026119, killed at
  the ceiling). The cost is the LANE, not the runner minutes: `concurrency: group: anna` is
  one serialised FIFO queue, so one wedged job held two replies and five scheduled ticks for
  six hours, and the Actions tab reported their WAIT as duration. Job 20 min against a
  measured worst honest run of 8m37s; apt 3 min against a ~20s install, expiring into the
  documented frame-scan fallback. Smoke `s29`.

- **The notification tag is identity, not correlation — unique per MESSAGE** (2026-08-19,
  Andrew). **Replaces** the per-knock tag of "Notifications stack; replies correlate by
  knock_id" (2026-07-11); that entry's correlation half stands. One field did two jobs
  wanting opposite keys: correlation STABLE per knock so the judge grades the right entry,
  identity UNIQUE per message or iOS replaces a notification with its successor. They
  collided once two replies landed on one knock — both via the Shortcut, which carries no
  knock_id, so both fell back to `last_fired_knock` and minted the same tag. 43 seconds
  apart, a test message ate the answer to "inge poringe" — judged, committed `cd2f5e8`,
  HTTP 200, never seen. Textbook silent no-op: green run, correct `chat.md`, observable only
  on the wire. Minted in `push_to_phone` now, which came out a line shorter. Smoke `s67`.

- **Cross-agent access is prose, not symlinks** (2026-08-20). **Replaces** "Cross-agent
  access is symlinks" (2026-07-06). `git config core.symlinks=false` on Windows checks
  `AGENTS.md` and `.agents/skills` out as plain text files holding a path string, so an
  AGENTS.md-reading agent got a 9-byte file containing `CLAUDE.md` and Antigravity found
  zero skills — on the only machine that reads them, with `git status` clean and CI
  (Linux) never affected. `AGENTS.md` is now a real file and the canonical router;
  `CLAUDE.md` is a pointer plus Claude-only invocation syntax, so there is still one
  source. The `.claude/skills/*/SKILL.md` files are host-neutral markdown — any agent
  reads them directly, which is the whole portability contract and needs no mirror.
  `.gemini/` retired the same day: `agy` was installed on no host and the shells had
  drifted 5–8 weeks. Portability that is broken is worse than portability never claimed.

- **Commissioning nothing is a first-class outcome** (2026-08-20, Andrew). **Replaces**
  the close-refusing half of "the repair earns the dose" (2026-08-01). A dose is earned by
  a genuinely recurring failure pattern or something real to teach — never by a counter
  reaching two, and never collected by Python. The close NAMES a live pattern carrying no
  dose and completes; `--slip-commissioned` books one, `--no-commission` puts the
  reasoning on the record. Found because the gate had never once fired: `slip_patterns`
  fed each slip's `dose_channel` — which records that *some* order was standing, for some
  other payload — into `channels`, so `uncommissioned` could not be true and `escalate`'s
  one-channel test could not match. 0 of 22 live patterns could trip either. Repairing the
  detection made the refusal real for the first time, and it was ruled out immediately.
  The 24-day venum-for-kudunga gap was a VISIBILITY failure; visibility is the fix. Smoke
  `s46`, `s68`.

- **The episode's public name is the script's first line** (2026-08-20).
  `rebuild_rss.get_title_from_md` reads exactly one line and falls back to the filename;
  `architect.md` never asked for an H1, so the title was produced by accident and 30 of the
  first 90 episodes shipped to the public feed titled `Tier2 Mission90`. Now stated in the
  Architect prompt and the role file, and linted on the exact line the reader reads. Fixed
  forward per "a renderer fix does not oblige a backfill" (2026-08-10) — the 30 existing
  titles are a separate content call. Smoke `s68`.

- **Every publishing lane uses the shared rebase net** (2026-08-20). `render_audio` ran a
  raw `git add`/`commit`/`push` — no pull, no rebase — inside a bare `except` that printed
  a warning and exited 0, so `run_studio` reported "rendered and published" for an episode
  that never landed. Actions commits to main hourly, so a laptop render races a cloud knock
  by construction. Now routes through `commit_and_push` (`_rebase_onto_main`) like drill,
  soak, longhaul and every knock lane, and a failed publish is loud. The "nothing staged"
  branch is kept so an unchanged re-render stays a no-op rather than becoming a crash.
  Smoke `s68`.

- **Staleness is scored on Andrew's clock everywhere** (2026-08-20). `suggest_targets` and
  `generate_callbacks` still used `date.today()` while `last_surfaced` is stamped with
  `local_today()` — the seam `state_io` exists to close, with these two callers missed in
  the original sweep. On a UTC runner every staleness, retest and callback interval was off
  by one for a US-evening or India-morning session. One owner, no host clocks. Smoke `s68`.

- **`target_revealed` defaults conservative, in one place** (2026-08-20). Three defaults in
  one file — CLI `store_true` gave False, `enqueue()` and the drain fallback gave True — so
  a CLI-queued dose silently meant "not revealed" and its reply could score COLD off a body
  that had handed the Tamil over, moving the production axis on an inflated fire. Now
  `BooleanOptionalAction` defaulting True across all three; `--no-target-revealed` is the
  explicit withhold. Smoke `s68`.

- **Hearing is not knowing — a rating nobody earned is not evidence** (2026-08-23, Andrew).
  The lexicon's first populated commit already held 153 rows at solid:93 / comfortable:54 — a
  day-one self-estimate written into the field evidence writes into. The ticket then served a
  June guess as a known word, and Anna demanded four words he had never met in one session.
  **Rejected: a ticket warning label** — *"that builds a feature to patch a data integrity
  bug."* **Rejected: a provenance field** — `reps` already counts declared events only, so
  `reps == 0` with production `none` IS the signal, and no schema moved. The repair is
  `sync_state unverify`: drop those rows to `struggled`, leave `reps` and `last_surfaced`
  alone — `--stuck-word` would have reached `touch()` and destroyed the signal that finds
  them. Retires `prune-duplicates`, as that retired `migrate-session-log`. Re-earning needs no
  new machinery: a caught eavesdrop already promotes recognition. Smoke `s53`.

- **Imports point one way, down the stack** (2026-08-23, the spine refactor). Stated twice
  before for single module pairs (`state_io` docstring 08-04; 07-25's "outreach may
  depend on selection, never the reverse"), now true of the graph: a lower layer never
  imports a higher one, and **a channel never owns an invariant more than one channel
  obeys**. L0
  `state_io` -> L1 selection -> L2 policy -> L3 `writer` (model config, parsers, executor)
  -> L4 `publish` (feed, commit, push) -> L5 the lanes. **Retires as a class the 23 prior
  entries** — 10% of this ledger, accelerating — that are one bug: *a law that should have
  been one component's property was written into every lane, and one lane missed it.*
  Budgets re-censused DOWN in-diff: `morning_knock` 637 -> 450, `sync_state` -45;
  paying for `writer` 175, `publish` 150, `state_io` 110. Smoke: 70 cases, no assertion
  changed, 26 ADDRESSES moved. Detail: `docs/spine_refactor.md` (retired 2026-08-26).

- **A case is isolated by scoping its stubs, not by splitting the file**
  (2026-08-24). **Replaces** §4b Q2's premise that "a case cannot be run in
  isolation", and the per-layer file split as the fix. MEASURED first: 68 of 70
  cases already passed alone against a fresh sandbox. The stub inheritance — 59
  assignments, none ever put back — was not load-bearing, it was LATENT, which is
  worse: the failure mode is a stub that stops intercepting and a test that reaches
  real git or a real phone. Every case now runs through `run()`, which restores
  each module's namespace after it; `smoke_test.py s41` runs one case in its own
  sandbox. All 71 pass alone, the four cases hoisted out of numeric order are back,
  and a case states its own preconditions. Guarded by `s72`, mutation-tested
  because with teardown dead the suite is still green. The split is optional now.

- **A lane declares what is different; its FAMILY shares the tail** (2026-08-24, Q1).
  The seven lanes are three families, measured — write → render → publish, decide/judge →
  maybe render, and pure delivery (`push_queue`: zero model calls at fire time) — so never
  one `run_lane()`. `lanes.deliver_rendered` holds the first family's tail (exposure →
  soak stamp → commit → notify), written out three times before. **`commit` and `notify`
  are keyword-only arguments with no defaults**, which answers §4b's import-style question
  with neither of its options: a name resolved inside `lanes` would not see a lane's stub,
  so both styles coexist and lanes migrate one at a time. Also landed: 13 mandates in
  `mandates.py` (`knock_reply` 785 → 570); `chat.md` re-rendered inside `publish()`, a
  derived file following its source; `push_queue`'s "no writer" read off SOURCE by `s70`.
  Open: no decide/judge runner, and `run_studio` is not on this tail.

- **The port surface is one line, or it is not a port surface** (2026-08-24). `state_io`
  carried *"a fork to another language replaces this regex"* from 2026-08-04 while three
  copies of the range outlived the spine refactor: `run_studio`'s duplicate, an inline
  `re.findall` beside it, and `writer.TAMIL_RUN`. A fork would have changed the labelled
  one and gone on matching Tamil in three places. Both forms live in L0 now — `TAMIL_RE`
  (any script present) and `TAMIL_RUN` (where the spans are). Guarded by `s70`, which
  reads the needle off `state_io.TAMIL_RE.pattern` so the case cannot become the fifth
  copy; mutation-tested. The same pass tightened that case's client allowlist, which
  still named `morning_knock` and `knock_reply` after Step 4 stopped them building
  clients — **an allowlist that outlives what it allowed is not a guard.**

- **The smoke suite is split by layer; the ORDER is not** (2026-08-25, §10). 73 cases
  re-homed from one 7,975-line file into `scripts/smoke/{state,compose,publish,knock,
  render,queue,ratchets}.py` over a shared harness, `_fixtures.py`. **Replaces** locating
  a case by scrolling. Not size — measured, the file was dense, not padded — but
  *locality*: every layer's changes landed in one file and collided. Proved pure by
  pinning the 1,009 assertion NAMES, sorted: green is not sufficient when the suite is
  both instrument and subject. Two of §10's own instructions were wrong and were
  overruled with evidence: per-file sandboxes (they re-import modules, which breaks stub
  teardown) and per-module `run_all()` (it reorders cases, and the sandbox tree is shared
  and never reset — s74 seeds `knock_log.json`, s3 asserts on a clean one). `smoke_test.py`
  keeps its name, its CLI and its 73-line ordered list. Open: s74 does not put back what
  it writes.
- **The law gets a lock, and the exception list can only shrink** (2026-08-25). The spine
  refactor installed *"imports point one way, down the stack"* (08-23) and nothing checked
  it. Every other law it landed is guarded per incident — `s35` for the waking-hour
  compare, `s70` for the script range — so a NEW upward edge or cycle read green.
  **Replaces** four prose statements of the law and the hand AST extraction that was the
  only way to see the graph. `s75` declares 23 layers, 2
  upward edges and 2 cycles, each exception carrying its reason. An exception whose edge is
  deleted — or *repaired*, so it no longer points up — is itself a failure, so landing a fix
  means handing the licence back (*"an allowlist that outlives what it allowed is not a
  guard"*, 08-24). Teeth on the walk, since an empty one passes vacuously.

- **`listens` retired — a counter nobody wrote read as measurement** (2026-08-27, Andrew:
  *"it keeps reporting dishonest numbers and confusing our sessions"*). Its only writers were
  two self-report paths plus a `render_audio.py` seed of `0`. **Stop chasing listens**
  (2026-06-30) retired the ritual that fed them, so the counter went blind that day and kept
  publishing — 84 self-reported listens, 47 rows at zero — and in 2026-08 was read as audience
  data, producing a "62% never heard" finding it could not support. **Deletes** the counter, both
  bumps, the seed, and `cmd_update`'s `save_json(EPISODES_PATH)` — which, once the bump left,
  rewrote the file byte-identical every close. Surfacing is untouched and is the job: `--listened` writes `last_surfaced` into the LEXICON, which the background rotation
  depends on. `credit_latest_episode_listen` → `surface_latest_episode_words`. Proved by the
  silent-no-op test, not by green: probe words re-dated 3/3 through the real writer,
  `episodes.json` byte-identical across the call. Replacement: `feature_inbox.md`.
- **The soak rating lane — replacing a count nobody wrote** (2026-08-27, Andrew). Takes the
  slot `listens` vacated today. A Shortcut sends `episode-rating` with two whole picker rows;
  `rate-episode` reads each leading integer and appends ONE dated note to `feedback_log.json`
  — the book the Diagnosis pass already reads. No new file, no schema change. **Its own
  dispatch type on purpose:** `cmd_knock_response` marks a knock *landed*, which lets the
  nudge gate back off, and a rating has no knock behind it. **Found while wiring it:** both
  knock guards tested only `client_payload.response`, which a rating does not carry — so
  `!= 'reply'` was TRUE for one and would have marked a knock landed off an event that was
  never a knock. Both now name `github.event.action`. Parsing sits in Python because the phone
  cannot be tested; every refusal exits non-zero and files nothing (`s79`).
- **The rating picker reads the FEED, not the episode registry** (2026-08-27, Andrew: *"why do
  I see tier2 mission 90 at the top and not this afternoon's soak?"*). `episodes.json` is the
  *lesson* pipeline's book — only numbered Missions get a row — so **16 of 28 published files
  were unrateable**, every soak and drill among them, and the picker offered the one format he had
  stopped listening to. Same mistake as `listens` hours earlier: the convenient
  population, not the right one. `feed_items()` reads `rss.xml`, so picker and podcast app agree
  by construction; sorted by pubDate, NOT the feed's own `sort_key`, which pins specials at the
  top forever. Knock micro-doses excluded — a one-line dose is not rateable. **`recent_missions`
  → `recent_audio`** (retired key, swept by merge-write), and the note carries the FORMAT so
  soaks can be compared against drills. Lives in `rebuild_rss`, which owns the feed. Missions
  are dormant, not retired.
