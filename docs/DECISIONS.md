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
- **Cross-agent access is symlinks; `CLAUDE.md` / `.claude/skills/` stay canon**
  (2026-07-06). Root `AGENTS.md → CLAUDE.md` and `.agents/skills → .claude/skills` give
  Antigravity and any AGENTS.md-reading tool the router and skill library with zero
  duplication. Replaces the hand-copied `.agents/AGENTS.md` (a drift trap that rode in on
  a lesson commit). Same pattern globally: `~/.agents/AGENT.md` is cross-agent canon —
  imported by `~/.claude/CLAUDE.md`, symlinked from `~/.gemini/AGENTS.md` (verified:
  `agy` 1.0.16 reads global config from `~/.gemini/`, not `~/.agents/`).
- **The judge caps a cold only against computed evidence** (2026-07-06). "LLM writes,
  Python is the brain" applied to reveals: `revealed_recently()` lists what knock traffic
  actually showed in 48h; the judge may deny a cold as "recently handed" only from that
  list (model memory hallucinated a reveal and denied a real cold). Same audit: chains
  move a `pinned_target` (never `expected_target` — the log records the original ask),
  and the deck menu demotes recently-asked items so ripest-first can't farm the same
  headliner into a permanent hinted. Root causes in `/debug` → KF-6.
- **language-tutor syncs by milestone re-extraction, never per-fix backports**
  (2026-07-06). The template is an agent *elaboration* of Tamil@`1691c34` (tagged
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
- **Payload fidelity bends the sidecar, never the script** (2026-07-13). The verbatim
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
  Andrew-commissioned from the setup audit). `scripts/studio_watchdog.py` (hourly local
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
  elaborates Tamil@`2b752fb`: the knock-loop engine advance since v2 re-applied
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
  07-17, shipped the next day inside four-feature audit-night commit `4003b6b`. Five days,
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
  correct numbers from the laptop at 23:27, and the very next cloud rebuild (`f5de185`,
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
- **An eavesdrop tape must name its subject in the opening, or it isn't a dose** (2026-07-25).
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
