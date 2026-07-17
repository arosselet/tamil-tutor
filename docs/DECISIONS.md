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
