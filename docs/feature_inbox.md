# Feature Inbox

Build-itches land here instead of in the codebase. The structure is frozen at **Anna 1.0**; when the urge to re-engineer strikes mid-session, write it here in one line and keep learning. Review deliberately, later — never in the moment. Adding a row of data is learning; changing a schema waits.

## Ideas

- **MULTI-TARGET EAVESDROP SCORING — proposed and WITHDRAWN in the same session
  (2026-08-31), because the obvious version manufactures the exact rows the 08-24 purge
  had just deleted.** Filed as a negative result so the next pass starts from the answer
  instead of the itch. **The problem behind it is real and measured:** recognition has one
  live test instrument, and `knock_reply.apply_catch_verdict` scores a single
  `expected_target` per tape — **0.32 ear-tests/day against the mouth's ~2-3**, which very
  nearly explains the 10x gap in upgrades (79 production to 8 recognition, 07-25 → 08-31,
  measured row-by-row from git).
  **RESOLVED 2026-08-31, and by neither of the two mechanisms proposed here.** A cadence
  raise (`EAVESDROP_CADENCE_DAYS` 3 → 1) was built and **reverted the same session** —
  Andrew: *"I don't like this listening test density idea. Listening tests should be in a
  rotation."* He is right and it is measurable: 2.83 knocks/day across eight modalities, so
  a daily tape is ~35% of everything he receives and it eats the text lane. **What shipped
  instead is his own proposal, and it is better than both:** the tape is deliberately pitched
  below the 95% coverage floor, so he catches a word or two of eight and the lane was
  discarding every one that was not the declared target. `apply_heard_words` now records the
  words HE names, guarded three ways (see below) — **more evidence per tape, same rotation,
  no extra tapes.** The rest of this entry stands as the reason the obvious version is wrong.
  **WHY SCORING N ITEMS OFF ONE VERDICT IS WRONG, and this is the whole entry:** the catch
  judge returns ONE verdict for the tape and grades the DRIFT. `CATCH_JUDGE_MANDATE` says
  it in its own words — *"Never grade wording or completeness — the win condition is the
  DRIFT"* — and "the catch judge grades the thread, not the turn" is settled (07-25). A
  single who/what/mood answer is **not evidence that five specific lexical items were
  heard.** Promoting five off it writes unearned `solid` rows into the one ledger that
  picks tomorrow's targets — the same defect the 08-24 purge dropped 108 rows to remove,
  and the same class as DECISIONS' *"an invented win is worse than a missed correction"*.
  **THE HONEST VERSION, if it is ever built: the drift question's answer must REQUIRE every
  item scored.** *"Who is coming, and when?"* genuinely demands the person-word and the
  time-word; a gist question demands neither. That makes it a **commissioning** constraint
  rather than a judging one, which fits the standing law that an eavesdrop's exposures are
  *declared at the knock seam* (`knock_exposures`), never mined from the memo text (07-26).
  It is also not a new idea: the same 07-26 audit found *"a volley's items 2..n were never
  counted as asked — `expected_target` names only item 1"*, and fixed it for volleys only.
  **MEASURE BEFORE BUILDING:** re-read the last 16 tapes and count how many already carried
  a drift question whose answer required more than one item. If the answer is "almost
  none", the change is upstream in commissioning and the scoring change is downstream of
  it. **Price it first:** `expected_target` str → list is a schema change to Python-owned
  JSON (Gate 2), `CATCH_JUDGE_MANDATE` sits at a 300-word budget, and `knock_reply.py` and
  `morning_knock.py` both carry code budgets. A real build, not the one-liner the cadence
  half turned out to be.

- **A THIRD-PARTY NAME GUARD ON THE PHONE-RECORD LANE — and the reason the obvious
  version cannot be built** (2026-08-30, proposed, NOT built; Gate 2 parks it — it is a
  new smoke case, which is exempt from budgets, but it needs a data surface that does
  not exist yet). **The evidence is a two-day recurrence, both ends in git.** `09ccc8e`
  (08-27) cleared a family name from four state files by hand; `a576ea8` (08-30) cleared
  a *different* one that entered `knock_log.json` on **08-29** through the same lane, plus
  the four `trip_deck.json` notes `09ccc8e`'s own body had named and skipped. Prose fix,
  no mechanism, no case — refilled in 48 hours. This is the `/debug` KF pattern and the
  DECISIONS law ("a fixed bug becomes a test case the day it's fixed") failing on the one
  lane where the cost is somebody else's privacy, not Andrew's meter.
  **WHY THE OBVIOUS MECHANISM IS WRONG, and this is the whole entry:** the natural guard
  is a deny-list of family first names asserted against the tracked state files. In a
  PUBLIC repo that list **is** the leak — it publishes, in one convenient place, exactly
  the set it exists to protect, and it is useless against the next name, which is always
  the one that actually leaks. Hashing the list only moves the problem (a first-name
  dictionary breaks it in seconds).
  **THE SHAPE THAT WORKS IS INVERTED — allow, don't deny.** Flag any capitalised
  non-Tamil token appearing in `knock_log.json` / `chat.md` that is not in an allow-list
  of known project nouns (Anna, Andrew, Tamil, Coimbatore, the weekday and month names,
  the mission/lane vocabulary). It stays fully public, it catches names never seen before,
  and its failure mode is a false positive Andrew clears by adding a word — the right
  direction for a guard whose miss costs a person's privacy. **What it replaces:** the
  manual sweep, which has now been run twice and missed something both times.
  **Open question before any build:** the allow-list is a new data surface and every
  English proper noun in a scene is a false positive, so measure the noise on the existing
  169-entry log FIRST. If it cries on every run it will be walked past, and a warning that
  cannot be discharged is noise by construction (Gate 7).

- **DO NOT MAKE `resolve()` FUZZY — measured 2026-08-26, and the answer is no.** Filed as a
  negative result so the next pass does not spend the same afternoon on it. Chasing the 84
  unreachable floor-gap words (entry below), the obvious fix is to stop exact-matching the
  phonetic index and normalise both sides instead. **It collides on exactly the pairs the
  curriculum exists to teach.**
  Normalising the distinctions the stored data does not hold consistently (aa/a, ee/i, oo/u,
  dh/th, ch/sh/s, zh/l, and any doubled letter to a single) over all 272 stored spellings
  produces **10 collisions**, including:
  `அண்ணா` / `ஆனா` → *ana* · `அம்மா` / `ஆமா` → *ama* · `நம்ம` / `நாம` → *nama* ·
  `பத்து` / `பாட்டு` → *patu* · `என்ன?` / `ஏன்னா` → *ena* · `இப்ப` / `இப்போ` → *ipo*.
  Vowel length and gemination are phonemic in Tamil; collapsing them turns *mother* into
  *yes* and *ten* into *song*. A fuzzy resolver would return a key rather than refuse, so the
  failure would be **silent and would write the wrong record** — strictly worse than today's
  loud refusal. **The current exact-match is correct and should stay.**
  **WHAT THE SAME MEASUREMENT DID FIND, and it is the useful half.** A rule-based romaniser
  derived from the 231 records that already carry a phonetic reproduces a stored spelling for
  only **55% of single-word records exactly, 77% allowing ~40 plausible variants** — and the
  ceiling is not the rules, it is that **the stored spellings disagree with each other**.
  `பத்து` is stored *pathu* while `அத்தை` is stored *atthai*; the same த்த, romanised two
  ways. **13 of the 45 records that carry more than one spelling carry them only to paper over
  this** (*enakku*/*enaku*, *keten*/*ketten*, *soodu*/*sudu*). So the hand-maintained variant
  list is already a workaround for exact-match, quietly, and nothing counts it.
  **THEREFORE the cheap fix already filed under "`--mark-seen` and `--produced-cold` disagree
  about what a word is" is worth more than it looked, and it is the one to build:** on a MISS,
  don't just refuse — name the near-matches. That single change serves three entries at once
  (this one, the `--mark-seen` split, and the 84 unreachable words, which a near-match search
  can reach through their gloss even with no phonetic stored). **What it replaces:** the
  reflex to loosen the resolver, now closed with evidence; and, if the suggestions are good
  enough, some of the 45 hand-maintained variant lists.
  **The 84-word backfill still needs a human ruling** — 55% exact is not good enough to write
  unattended, and this is the lexicon that picks tomorrow's targets. The romaniser is worth
  keeping only as a *suggestion* source for that ruling session, never as a writer.

- **THREE READERS, THREE DIFFERENT IDEAS OF WHAT AN EPISODE TITLE IS** (2026-08-26, found
  while measuring episode length; **the worst case is already guarded, the seam is not**).
  The same script is read for its public name by three places that do not agree:
  - `run_studio.lint` (the gate, added 2026-08-20) requires only that **line 1 starts with
    `# `**.
  - `rebuild_rss.get_title_from_md` reads **line 1 only** (`f.readline()`) and takes whatever
    follows the hashes — any H1 satisfies it.
  - `render_audio` registers `episodes.json` off `^# Tier 2, Mission \d+ — (.*)$` with
    `re.M` — **a stricter pattern** (comma after "Tier 2", em-dash separator) searched over
    the whole file, falling back to `f"Mission {script_path.stem}"`.
  **The reachable gap:** a script whose line 1 is `# The Family That Never Decides` passes the
  lint, gives the feed a correct title, and still registers in `episodes.json` as
  `Mission tier2_missionNN`. `sync_state` surfaces that stored title to Anna, so **Anna would
  name the episode differently from the name in Andrew's player.** The Architect prompt does
  ask for the strict form, so this needs a writer that half-complies — not yet observed, which
  is why this is filed and not fixed.
  **Already happened, in the other direction, and it is on the public feed now.** M87–M90
  (08-14 → 08-19, before the lint landed) open with `[SFX: …]`, so all three readers fell back:
  they are titled `Tier2 Mission87`…`Tier2 Mission90` in the feed and
  `Mission tier2_mission87`… in `episodes.json`. The lint prevents new ones; **nothing
  repairs these four, and repairing them is blocked by our own law** — Apple treats a retitle
  of a published item as a new episode (DECISIONS 07-25; the "Published feed titles could
  still be mutated by any writer" entry below). So the honest options are: leave four ugly
  titles on the feed permanently, or accept four duplicate episodes in Andrew's player. **This
  is the concrete cost the `existing_titles()` freeze was proposed to prevent, arriving from
  the side nobody was watching — not a writer mutating a good title, but four bad titles that
  can never be corrected.**
  **What it would replace:** one regex. The cheap version is to make the three readers share
  a single title function in `state_io`, which retires two ad-hoc patterns rather than adding
  a fourth. That is a real simplification, and it is the only part of this worth building.

- **THREE STATE ROWS EXIST ONLY ON DELETED BRANCHES — a backfill decision, not a bug**
  (2026-08-26, found by the consolidation pass; **needs Andrew's call before anything is
  written**). Eleven local `claude/*` branches were checked against `main` file by file.
  Nine carried nothing `main` did not already have, in better form, and were deleted. **Two
  carried real observations that never landed**, and they are held undeleted until this is
  decided:
  - `claude/first-flight-i57pzu` (`c47569f`, 2026-08-11) — a **`session_log.json` row for
    2026-08-11** that is absent from `main`: three cold fires (எவ்ளோ ஆகும், வலது பக்கம்
    திரும்புங்க, இன்னொரு தடவ சொல்லுங்க), `floor_pct` 26.8, `engines_pct` 90.5, and the
    on-the-plane send-off debrief. The log jumps 08-10 → 08-14. It also carries lexicon
    movements for those three rows.
  - `claude/language-learning-reflection-vyzp91` (`e2e6bfb`, `eb10626`, 2026-08-13) — **two
    `feedback_log.json` rows for 2026-08-13**, day 1 in country. The first is the
    first-contact field report; the second explicitly *"REVISES SIGNAL 3 OF THE ENTRY ABOVE
    AND RESETS WHAT THE TRIP IS FOR"*. `main` has an 08-11 feedback row and then nothing
    until 08-14, so the reframe that reset the trip's purpose is not in the ledger the
    recalibration passes read.
  **WHY THIS IS NOT JUST "MERGE THE BRANCHES".** Both branches also carry `lexicon.json` and
  `learner.json` as they stood on 08-11/08-13, and `main` has moved through the deck
  retirement (08-18) since. Merging either would clobber live state. The salvage is
  row-level, not commit-level.
  **AND THERE IS NO WRITER FOR IT.** `sync_state.py update` stamps `local_today()`; nothing
  accepts a back-date, and hand-editing Python-owned JSON is out of bounds by standing rule.
  So the three real options are: **(a)** leave the gap and note it — the honest reading is
  that 08-11 and 08-13 have no rows, and a reader can find them at the SHAs above;
  **(b)** add a `--as-of DATE` to `update` and `feedback`, which is a CLI change on a
  Python-owned surface and wants Gate 2; **(c)** one-off backfill under Andrew's explicit
  waiver, appending the three rows verbatim and re-sorting by date.
  **The recommendation is (a) plus this entry**, unless the 08-13 reframe is load-bearing for
  the next `/recalibrate` — in which case (c) for that one row only, because a signal that
  *"resets what the trip is for"* missing from the feedback ledger is the kind of absence
  that silently steers the next pass. **What it would replace:** nothing, which is the
  argument for (a).

<!-- SALVAGED 2026-08-26. The two entries below were written on local branches that
were never merged and are now deleted; they were recovered from the commits named in
each. Both had already been re-derived on main in thinner form — that re-derivation is
what the consolidation pass found, and it is the reason the branches are gone now
rather than still waiting. Recovery SHAs are recorded so the originals stay reachable.

BRANCH RETIREMENT LEDGER, 2026-08-26. Origin carries only `main`; all eleven of these were
local-only. Each was compared against `main` file by file before deletion — nine carried
nothing `main` did not already have in equal or better form. Tip SHAs, deleted:
  0597ca0  claude/audio-augment-main-article-f2cfsq   (patch-equivalent in main)
  c6b4c65  claude/episode-format-language-h2neyl      (superseded by the spine refactor)
  6aed2ad  claude/india-trip-motivation-xidzr9        (inbox entry salvaged below)
  6877b13  claude/institution-one-sharpening-mr58fr   (main's article is newer, 08-09)
  27b2059  claude/learning-feedback-mistakes-7grsmo   (re-landed; main is ahead)
  e0d7036  claude/learning-wife-language-zhq0pd       (patch-equivalent in main)
  14f193f  claude/tamil-dialect-clarifications-fzd60t (main's article is newer, 08-09)
  cfbd6d2  claude/tutor-architecture-patterns-x05txa  (patch-equivalent in main)
  f04ff3b  smoke-per-layer                            (fully merged, 0 ahead)
HELD, NOT DELETED — they carry state `main` never received; see the state-rows entry above:
  c47569f  claude/first-flight-i57pzu
  ee30c4d  claude/language-learning-reflection-vyzp91
-->

- **⏳ THE WINDOW IS STILL OPEN — READ THIS BEFORE THE OTHER EAVESDROP ENTRIES**
  (salvaged 2026-08-26 from commit `ee30c4d`, written 2026-08-13 on
  `claude/language-learning-reflection-vyzp91`, never merged). **This entry contains the
  sentence "This entry exists so it stops being rediscovered every three weeks", and it was
  then rediscovered on 2026-08-25 as "CAPTURE THE ROOM" below, thinner, because it was
  stranded on a branch nobody read.** That is the whole cost of the branch problem in one
  artefact.
  **THE PART THAT IS TIME-CRITICAL.** Its "WHY NOW, AND ONLY NOW" argument turns on Andrew
  being in the same house as both the supply of real Kongu speech and the people who can
  rule on what it says. Checked 2026-08-26: `learner.json.timezone` is `Asia/Kolkata`, the
  live campaign block is *The Month In Country* with a standing catch order for "one word
  overheard off the sisters", and touchdown was 08-12. **He is still in it, with roughly two
  weeks left.** Thirteen days of that window were spent with this analysis unreachable.
  The recommended first step below costs no code and no schema — it is consent, a handful of
  clips, a native-ruled transcript, and ONE dose by hand. **That is the decision in front of
  Andrew, and it expires on the return flight.**
  Original entry, verbatim:

- **HARVEST REAL EAVESDROP AUDIO WHILE THE SUPPLY AND THE RULING AUTHORITY ARE IN THE SAME
  ROOM** (2026-08-13, Andrew's day-1 field report from Coimbatore, proposed by @build and
  approved for write-up only — **no build authorised**). The standing verdict *"wire real
  audio or do not run them"* (07-28am) has sat unacted through two `/recalibrate` passes and
  is item 5 of the 6-in-5-days third-strike count that produced the commissioning law. This
  entry exists so it stops being rediscovered every three weeks.

  **The evidence is no longer only internal.** Catch is **3/12 solid** — the weakest meter in
  the system, and the campaign block's own words are *"the one lane going backwards."* On
  day 1 in country Andrew independently produced the matching field reading: *"instead of
  recognizing nothing in a sentence, I'll pick up a word or two, but I still don't know what
  the sentence means"*, plus *"the way people slur things is more intense than I was
  expecting"* and the deck-level version — *"the version we're teaching is still not as
  rounded off as our target"* (`valadhu pakkam thirumbunga` is a citation form; the street
  form is faster and more reduced). That is the third strike on the over-articulation axis
  opened 07-31 by the native-ear verdict, and it now lands on the DECK, not only on TTS.

  **WHY THIS HAS NEVER BEEN A MODALITY SWAP — the finding that should stop the next attempt
  from underestimating it.** The eavesdrop lane is closed-loop *because Anna authors the
  tape*: `memo_script` (`mandates.py` §eavesdrop) is simultaneously (1) the render input for
  `EAVESDROP_VOICE` (`morning_knock.py:56`), (2) the answer key the deliberately separate
  comprehension judge scores the drift reply against (`knock_reply.py:401-492`), and (3) the
  basis for the `expected_target` exposure declared at the knock seam (DECISIONS 07-26).
  Real audio breaks all three at once. **The unit of harvest is therefore not a clip — it is
  clip + native-ruled transcript + one drift question**, and a bare recording is worthless
  to this lane. That is the actual reason six weeks of "just wire real audio" produced
  nothing.

  **WHY NOW, AND ONLY NOW.** The blocker was never the recording; it was the transcript
  authority. For one month the supply of real Kongu speech and the people who can rule on
  what it says are in the same house, and Andrew has idle hours. Outside this window he has
  the clips and no ruling authority at hand. **The window is the asset — the build is not.**

  **CONTROL FLOW INVERTS, and the lane must be told so.** Today Anna commissions a tape *for*
  a pending catch item. Harvested speech will not contain the item on request, so selection
  runs backwards: harvest, rule the transcript, then see which catch item the clip happens to
  carry. Any build must treat harvested audio as a *pool to match against*, never a lane that
  can be ordered from — and the authored tape stays, unreplaced, as the on-demand half. **This
  adds a second source to one lane; it replaces nothing.**

  **HAZARDS — all four are blocking, and the first is not an engineering matter.**
  1. **Consent, from a family, not a corpus.** Non-negotiable and asked in advance. Andrew is
     already planning to show the project to his father-in-law, which makes the ask a natural
     part of that conversation rather than a strange one — but the reveal is not the consent.
  2. **THIS REPO IS PUBLIC AND `published_audio/` IS THE FEED.** `.gitignore` says it in
     Andrew's own words: *"repo is public, never commit."* Recorded family conversation must
     never reach the repo, the RSS feed, or a commit — not once, not "temporarily". Any build
     needs a private local path plus a `.gitignore` entry written BEFORE the first clip
     exists, and the harvested lane must be structurally incapable of reaching
     `rebuild_rss.py`. Treat a leak here as the highest-severity failure in the proposal.
  3. **The refusal law applies unchanged.** DECISIONS 07-25/08-01: a tape whose opening does
     not name its subject is refused, never degraded to text. Real conversation frequently
     names nobody, so **expect a low yield** — most clips will be unusable, and that is the
     law working, not a reason to relax it for harvested audio.
  4. **No autonomy, same as the deferred cloud-episode item.** Nothing here touches the knock
     tick, `MAX_UNATTENDED_PER_DAY`, or the mission-number/lock hazards parked above.

  **RECOMMENDED FIRST STEP — costs no code and no schema.** With consent, collect a handful
  of clips; have a native speaker rule the transcripts; store them privately; then run ONE
  dose BY HAND and check the only two things that matter — is the drift question answerable
  from the audio, and does the existing judge return a sane verdict against a transcript it
  did not author. Same discipline as the deferred `workflow_dispatch` episode step: hear
  whether it holds up before anything is wired. **If the manual dose works, it has earned a
  build; if it does not, this entry records why and the next pass starts from the answer
  instead of the itch.**

- **THE ORIGINAL OF THE BUDGET ARGUMENT, AND IT NAMED THE RIGHT FILE** (salvaged
  2026-08-26 from commit `6aed2ad`, written 2026-08-11 on
  `claude/india-trip-motivation-xidzr9`, never merged). Main re-derived this on 2026-08-26 as
  "`docs/` IS THE SURFACE WITH NO CEILING", fifteen days later, arguing from PADF instead of
  from our own measurements — **and landing on the colder of the two surfaces.** This
  original went straight at `progress/profile.md`, which is the one in the session-open
  payload. Independently re-measured 2026-08-26: `profile.md` is 5,278 words against a
  ~9,215-word open (persona 1,970 + daily_session 1,308 + Anna SKILL 659 + profile 5,278), so
  it is **57% of everything Anna reads at open** and the only file in that payload with no
  ceiling. It grew ~172 words/day through August while every budgeted prose file sat pressed
  against its number (persona 1970/2000, constitution 1789/1790, daily_session 1308/1320,
  audio_channels 474/475, commissioning 287/300).
  **Its "DELIBERATELY NOT ARMED" caveat still holds and is the reason this is not a one-line
  fix:** a `PROSE_BUDGETS` row for `profile.md` goes red the moment it is added, on a file
  only a live session can rewrite. Arm it in the same diff as the first close that rewrites
  the campaign block to fit — per the standing rule that a raise rides its own growth.
  **One dangling reference:** it cites `docs/THE_PACK_BOUNDARY.md`, which was created on the
  same unmerged branch and has never existed on main. Read that citation as unreachable.
  Original entry, verbatim:

- **THE ONE PROSE SURFACE WITH NO CEILING IS THE ONE THAT ACCUMULATES** (2026-08-11).
  Measured, not felt: `last_debrief` is **670 words** and stable, because its rule is
  *rewrite cumulatively, prune what resolved* — a compression pass that actually runs every
  close. The campaign block is specified in `daily_session.md` as **"Five lines, no more,
  and only ever one block (a finished week is overwritten; git holds the record)"** and is
  currently **2,886 words over 69 lines**, carrying seven stacked dated appendices
  (08-04 … 08-10). `profile.md` as a whole is **5,819 words and is the only prose surface
  in the repo outside `PROSE_BUDGETS`** — every `protocol/*.md` is ratcheted; the file that
  grows by habit is not. The two rules produce exactly the two outcomes you would predict.
  **This is drift, not a bug:** each appendix was worth writing on the day, and the block is
  still read by sessions, the studio and the digest, so the cost is paid on every read.
  **The shape when it comes off the shelf:** a `PROSE_BUDGETS` row for `profile.md`, which
  is one config row, not a schema change. **DELIBERATELY NOT ARMED 08-11** — a budget added
  now goes red instantly on a file only a live session can rewrite, and Andrew was an hour
  from a flight. Arm it in the same diff as the first rewrite that fits it, per the rule
  that a raise rides its own growth. **The general lesson is the reusable one** (see
  `docs/THE_PACK_BOUNDARY.md`, and the 07-31 slip-ledger entry in DECISIONS): a compression
  pass only holds if something *counts* the thing being compressed. Prose that is rewritten
  stays small; prose that is appended grows until a reader pays for it, and nothing in the
  system notices, because narrative has no natural unit to ratchet.

- **THE TICKET NAMES TARGETS THE LOGGER WON'T ACCEPT — 84 floor-gap words are still
  unreachable from the surface Anna writes in** (filed 2026-08-14, **deleted from this file
  the same day by the commit that fixed only half of it**, reinstated 2026-08-26 with fresh
  numbers). `state_io.resolve()` is exact-match against `build_phonetic_index`, which is
  built purely from each record's hand-maintained `phonetic` list, so a record with
  `"phonetic": []` can only ever be addressed in Tamil script — while the constitution's
  surface split requires Anna to think and write in phonetics.
  **What actually shipped on 08-14** (`2c4c3a9`, "a new lexicon record is born with its
  phonetic, or not at all") was a **forward guard only**: new records cannot be created
  without a phonetic. It did nothing about the records already holed, and it removed this
  entry — 32 lines — in the same diff.
  **Measured again 2026-08-26:** 95 of 352 non-frame records still carry an empty phonetic
  list, and **84 of those are `production: none`** — very nearly the floor-gap pool itself,
  the exact words the conversion work exists to move. Sample: கல்யாணம், அழகான, சொன்னாங்க,
  நேரா, சொல்லுங்க. Anna still cannot log any of them with `--produced-cold` or
  `--mark-seen` without falling back to script through a UTF-8 shell.
  **The remaining work is a backfill, not a mechanism** — one pass that writes a phonetic
  onto 95 existing rows, which is rows of data and therefore free under the structure
  freeze. It needs Andrew or the Oracle to rule the transliterations; that is the only
  reason it is filed rather than done.
  **THE FILING LESSON, which is why this entry is worth its space twice:** it was retired on
  the mechanism instead of on the effect, and deleted instead of struck through and moved to
  `## Shipped`, so the file lost all memory of the 84 words. A shipped entry gets a strike
  and a move; it never gets a delete.


- **`PROSE_BUDGETS` HAS NO COMPLETENESS GUARD — `CODE_BUDGETS` DOES** (2026-08-26, proposed,
  NOT built — six lines inside `s18_size_budgets`, no new file, so Gate 2 does not park it).
  The bottom of `s18` already asserts *"every script under `scripts/` carries a code budget"*,
  with its own reason attached: *"a new file is the obvious way past a ceiling, so an
  unbudgeted one is a red run rather than a silent exemption."* **That law was never applied
  to prose.** `PROSE_BUDGETS` is a hand-written table over five `protocol/*.md` files plus
  six mandate strings, and **seven `protocol/*.md` files on disk carry no number at all**:
  `studio/architect.md` 1,926, `studio/director.md` 1,596, `studio/producer.md` 893,
  `studio/studio.md` 744, `studio/hosts.md` 461, `studio/dialect.md` 402, `diagnosis.md` 353
  — **6,375 words**, of which 6,022 are studio prompt that `run_studio.py` names on **every
  render**. They were split out of budgeted files and grew without ever touching a ceiling.
  **Why this outranks the two entries below:** those bound cold surfaces (`docs/`, read by
  no runtime path) or sum surfaces already bound (the payload). This one reaches prompts
  that ship. **What it would replace:** nothing — honest Gate 4: it is a ratchet, and it
  subsumes the useful half of the payload entry rather than standing beside it.
  **THE REAL COST, named up front.** `architect.md` is where *"variation is structural"* and
  the scene-spec gate live, and `constitution.md` → Fresh Execution bans reading past scripts
  as models — so those prompts are the whole anti-templating defence. Squeezing them is how
  the feed goes samey, which `/debug` already treats as a plumbing symptom. Set each number
  at census + generous headroom, and write the split-signal note into the table the way
  `daily_session.md`'s entry does: for `architect.md` the next raise splits the scene-spec
  gate out, it never squeezes it.
  **DECIDE THE COMMENT QUESTION IN THE SAME DIFF.** `CODE_BUDGETS` exempts comments and
  docstrings on the record — *"a budget that taxed explanation would buy smaller files by
  deleting the thing that makes them debuggable"* — which is `Stories Are Curriculum` one
  layer down. `PROSE_BUDGETS` counts every word including the why, and the 08-25
  `daily_session` raise shows where that pressure lands (it retired *"four parenthetical
  glosses"*). Those cuts were fair, but the two ratchets disagree on principle and nothing
  has noticed. Either prose gets the same exemption, or the table says out loud why
  prompt-prose is different.

- **`docs/` IS THE SURFACE WITH NO CEILING** — **RE-DERIVATION of the salvaged 2026-08-11
  entry at the top of this file, which named `progress/profile.md` instead and was right to
  (2026-08-26).** Both can stand; the payload one goes first because it is hot and this one
  is cold by its own admission. (2026-08-26, proposed, NOT built — a new
  archive tree plus a budget table, so Gate 2 parks it). Found reading PADF, Kavish's
  governance kit, against this repo. `PROSE_BUDGETS` covers `protocol/*.md` and the six
  mandates; `CODE_BUDGETS` covers every `scripts/*.py`. `docs/` has neither — only the
  150-word *forward* per-entry cap on DECISIONS. Measured 2026-08-26 (pre-consolidation):
  `docs/` totalled 60,894 words — `DECISIONS.md` 30,948, this file 12,031,
  `spine_refactor.md` 7,107. **Re-measured after the same-day consolidation pass: 56,098**,
  with `spine_refactor.md` and `deck_retirement.md` retired (both executed whole) and this
  file up to 15,712 by the salvage. So the pass bought ~8,500 words back and this file spent
  ~3,000 of them — which is the honest shape of it: retiring finished work orders is cheap
  and repeatable, and it did not touch the two files that actually grow. **This is the
  CODE_BUDGETS argument one directory over**, in its own words: the word budget held prose flat through July while Python went
  2566 → 6032 lines, because "April's 'fight drift by adding' failure mode simply moved to
  the surface that had no ceiling." It moved again, and this file is one of the two places
  it landed. **What PADF has that we don't:** the cap binds the *live* file, and complete
  inactive blocks move to `<NAME>-<YYYY>.md` behind an archive index rather than
  accumulating in place. That is the piece the 08-01 forward cap deliberately left out
  ("the archive is untouched: git owns the narratives already written") — which was right
  for the entries already written and does nothing about the file's total. **What it would
  replace:** the per-entry cap becomes one case of a general rule instead of a special one.
  **THE PRIORITY CORRECTION (2026-08-26, on assessment against the constitution):** this is
  a COLD surface. Traced the tree — nothing under `scripts/`, `protocol/` or the Anna skill
  reads `docs/` at runtime; three matches exist and all three are citations inside comments.
  `orient/SKILL.md` already says it: *"Anna does not load `PROTOCOL_MAP.md`, `DECISIONS.md`,
  or `BOOTSTRAP.md`. Those are the engineer's map."* So the 60,894 words cost `@build` its
  reading time and cost Andrew nothing — real housekeeping, no pedagogical stake, and it
  ranks BELOW the prose-completeness guard below, which binds prompts that ship.

- **THE BUDGET THAT MATTERS IS THE SUM AT THE LOAD POINT** (2026-08-26, proposed, NOT
  built — one more assertion in `s18`, no new file, so this is the cheapest of the four).
  From PADF's memory protocol, which bounds not just each file but the *session-start
  payload* — the total of everything read at session open — and reports `STARTUP PAYLOAD
  OVER BUDGET` as a loud failure rather than truncating. Five files each under budget can
  still double the payload between them, and nothing would say so. **What it would
  replace:** nothing — it is a ratchet, and a new ratchet is the one addition this system
  takes on purpose. But it is honest to say it adds rather than retires, and Gate 4 wants
  that said out loud.

  **THE CENSUS WAS WRONG AND IT BREAKS THE PROPOSAL (corrected 2026-08-26).** This entry
  filed the open at `persona` + `constitution` + `daily_session` = 5,110 words. Measured on
  disk, the open is **~9,300**: persona 1,970 + daily_session 1,304 + SKILL 659 +
  **`progress/profile.md` 5,320** — which the skill's step 3 and the protocol's Load step 3
  both read, and which is larger than the three protocol files combined. It was missed
  because it is the one file in the payload with **no budget**, so a sum over the *named,
  budgeted* set would bound the 3,063 words already individually bound and leave the 5,320
  outside it. The payload could double through `profile.md` with this check green — the
  silent no-op, in the mechanism proposed to prevent it.
  **And `profile.md` must not be the fix.** Charted in git: it ramps ~200 words/day and is
  cut hard by its own "rewritten, not appended, every ~5 sessions" rule — 5,968 words on
  08-10 → 3,383 on 08-14, a 43% cut with no ratchet involved. A word cap would fire
  mid-ramp and force a rewrite at an arbitrary moment; worse, the file is where "Ground
  Covered, Not Ground Remaining" lives, and that section is *supposed* to accumulate
  between compactions. The health signal is the TROUGH (3,302 → 3,383, flat), never the
  peak. **Superseded by** the prose-completeness guard below, which reaches the actual
  unbudgeted surfaces instead of summing the bounded ones.

- **MAP FRESHNESS COULD BE COMPUTED INSTEAD OF REMEMBERED** (2026-08-26, proposed, NOT
  built — the biggest of the four; a frontmatter schema on doc files, so Gate 2 parks it
  firmly). `docs/PROTOCOL_MAP.md` and `extend/references/routing.md` are hand-maintained
  and rot silently — which is exactly why the name-never-line-number lint exists ("an
  address that rots without saying so is not prose"). PADF's `core/codebase-map.md` is the
  general form of that lint: each doc note carries `paths:` globs and an `as-of:` commit,
  and staleness is *computed* from a four-layer union — commits since baseline, index vs
  HEAD, worktree vs index, untracked — with `--no-renames` load-bearing because each layer
  reports a rename as delete + add. Every failure mode returns STALE, never "probably
  fine". **Why it is our idiom exactly:** keeping the layers separate is what makes a
  staged edit reversed in the worktree stay visible even though the final bytes match the
  baseline — the silent no-op test, applied to documentation. **The honest objection:** we
  have three map-ish files, not thirty, and a schema on them may cost more than the rot.
  Worth a conversation before it is worth a build.

- **A GUARANTEE-VOCABULARY LINT FOR OUR OWN PROSE** (2026-08-26, proposed, NOT built —
  and the weakest of the four on Gate 4 grounds: **I cannot name what it retires**, which
  is the signal to stop). PADF's `doctor.py` → `check_guarantees` scans its public docs for
  unqualified claim language ("guarantee", "idempotent", "safe to re-run", "equivalent")
  with a real qualifier-proximity analysis rather than a naive grep, and its PR template
  requires that check green. It is the same family as our two existing prose lints — a
  check on an assertion that rots — and it would fit `s18` as a fourth prose unit. Filed
  for completeness; on this system's own rules it does not yet earn its place.

- **THE BENCHMARK TAPE — felt progress without a meter** (2026-08-25, proposed, NOT built —
  it is a new artefact plus a frozen number, so Gate 2 parks it). Andrew's own account of how
  he reads progress: *"the number isn't what makes me feel progress… 'where I am now compared
  to where I was a few months ago' is the progress, not the # of machines or vocabulary that
  are now cold."* A meter cannot deliver that and three redefinitions in three months have
  made the series unreadable anyway. **The shape:** ninety seconds of real Coimbatore speech at
  full speed, filed once, re-listened every few months. Not scored, not a test, no ledger
  writes. The progress is the difference between the two experiences, felt directly. Costs one
  file and never changes. **The design constraint if it is ever built:** honesty and continuity
  trade off — every fix to a meter's honesty destroys its trend line, which is exactly what
  happened to the viability floor (30.1% → 84.5% between two sessions, from the `unverify`
  sweep shrinking the denominator, not from learning). The escape is TWO numbers with different
  rules: one frozen forever and crude, for morale; one improvable, for targeting. One number
  cannot do both jobs, and this system has been asking one to.

- **CAPTURE THE ROOM — spike first, and it may not survive the spike** — **RE-DERIVATION;
  read the salvaged 2026-08-13 entry at the top of this file first (2026-08-26).** That one
  is strictly richer: it names why six weeks of "just wire real audio" produced nothing
  (`memo_script` is render input, judge answer key and `expected_target` declaration at
  once), it carries the four blocking hazards including the public-repo one, and it inverts
  the control flow. Kept below for the spike framing it adds. (2026-08-25, proposed
  and explicitly NOT adopted). The idea: record real family speech, transcribe it, and let it
  supply items instead of `curriculum/word_pool.json` (333 hand-curated rows that cannot scale
  to the 1,500–2,500 families `comprehension_plan.md` scopes). **Andrew's objection is the
  finding and it is not resolved:** *"I don't know what to do with recordings of what I hear…
  I can imagine telling you things I heard or things I recognised but the conversion ratio will
  be really low. It's easier just to heads down do my daily lesson."* He is right that a
  capture mechanism without a consumption loop is dead weight, and the spike has not been run —
  nobody knows whether a multimodal model segments Coimbatore family speech at all.
  **What shipped instead** is the cheap half: the `[heard]` line (DECISIONS 08-25), ten seconds,
  no pipeline, and it works from a phone in Canada as well as a kitchen in Coimbatore. Treat
  recording as an UPGRADE to that loop if the spike succeeds, never a prerequisite. Cost note
  if it is ever run: local Whisper large-v3 is free and keeps family audio off a cloud; Google
  STT is more accurate at roughly USD 0.006–0.02/min — 10 min/day is USD 2–6/mo against a
  standing budget of USD 5–10.

- **THE KNOCK LANE MEASURES THE AXIS THAT IS NO LONGER THE GOAL** (2026-08-25, raised, NOT
  actioned — a deletion this size is Andrew's call and he has not made it). Measured: 143 acted
  knocks, 86 replies, and of those **7 judged cold and 20 hinted — 38 came back as `chat`**.
  The verdict machinery, the caps, the chaining and the demand streaks are among the most
  complex code in the repo (`knock_reply.py` 553 lines, `JUDGE_MANDATE` ~1500 words) and two
  months of it produced 7 cold credits on the axis that 08-25 re-labelled a probe. **The reach
  is not in question** — presence works, and the reply rate ran 67–76% weekly before the
  travel. The question is whether outreach should keep trying to be a *measurement* instrument
  at all. If it should not, the saving is not a feature but a permanent reduction in how often
  this system asks to be engineered — which is the stated goal (Andrew, 2026-08-25: *"I want my
  rate of engineering to slow down in this system… find some kind of convergence on the shape
  and reliability I want"*).

- **`docs/DECISIONS.md` IS 30,000 WORDS AND EVERY CHANGE READS IT** (2026-08-25). Gate 1 of
  `/extend` says read it before touching anything; it is now longer than most of the code it
  governs, and `feature_inbox.md` adds another 10,000. The corpus was worth writing — it is why
  a 2026-04 decision can still be checked — but maintaining it is a standing tax on the
  engineering rate. **Proposal, not a decision:** split into a live rulebook of ~2,000 words
  (the rules that actually gate a change) and `HISTORY.md` (everything settled, archived, never
  read by a gate). Nothing is deleted; one of the two stops being on the critical path.

- **THE AUTO-DRAIN'S FALLBACK RULE IS ONE PIPE AWAY FROM BEING DEAD** (2026-08-14, self-
  inflicted, worth a line anyway). The `anna` skill says dispatch `run_studio.py` in the
  background and "fall back to the `studio` subagent only if it exits non-zero". `run_studio.py`
  is correct — a lint failure prints, leaves artifacts, and `sys.exit(1)` (line 575). But the
  obvious way to keep a background job's output readable is `python scripts/run_studio.py 2>&1
  | tail -40`, and a shell pipeline returns the *last* command's status, so `tail` reports 0
  and the documented fallback can never fire. That happened at session open today: M87 failed
  the fourth-wall lint, the harness reported success, and the drain only recovered because the
  failure was legible in the captured text. **Nothing in the repo is wrong; the instruction is
  just fragile against a habit every agent has.** Cheapest fix is a wording change where the
  dispatch is specified (run it unpiped, or read the exit code explicitly — not `| tail`);
  `set -o pipefail` also works but only in the Bash lane. Filed rather than fixed because it
  touches the skill's dispatch contract, which is behaviour, not data.

- **THE REPLY PATH CAN DIE AND THE SYSTEM READS IT AS "HE DIDN'T ANSWER"** (2026-07-31,
  found live — Andrew replied twice, to the 17:22 volley and the 22:04 resend, and neither
  produced a `repository_dispatch`). **The dead-token diagnosis is in the session notes; this
  entry is about the part that is ours.** Nothing in the repo failed and nothing warned:
  `knock_log.json` simply carries `reply: null` on those knocks, which is byte-identical to
  a knock he ignored. Downstream, silence is not neutral — it is *data*: `demand_streak`
  counts trailing asks, `recent_ask_counts` demotes items that "got no reply", the deck's
  staleness term reads unanswered asks, and the slip ledger never gets the fires he actually
  made. **So an outage on the inbound leg does not merely lose replies; it writes a false
  portrait of a non-responsive learner into the state that steers selection.** Textbook Gate
  7.2: absence indistinguishable from success, except here the absence is indistinguishable
  from a *learner behaviour* the system then acts on.
  **The asymmetry that makes this cheap to detect:** outbound and inbound both traverse the
  same Home Assistant, so a knock landing on the phone PROVES the middle is alive. Anna
  already computes `hours_since_exchange`. The shape when it comes off the shelf is a
  liveness check, not a new meter — *N consecutive knocks carrying an `expected_target`,
  every one with no inbound event of ANY kind (no ack, no tap, no reply), while knocks are
  still being delivered* is not a quiet learner, it is a broken return path, and it should
  say so on the status line rather than deepening the demand streak. Deliberately NOT built
  tonight: it is a new detector (Gate 2) and the immediate fix is a credential rotation.
  **Second, smaller:** `docs/home_assistant_knock_buttons.md` §1 says "set an expiry you'll
  rotate" and nothing anywhere records WHICH expiry was chosen or when the token was minted.
  A dated line in that doc at rotation time costs nothing and turns a silent outage into a
  calendar entry.

- **RE-RENDER THE ANDREW INTRO AT v8 — next laptop session** (2026-07-31, Andrew).
  The script is v8 (register pass, "state the fact and stop" retired for the Tamil lane);
  the mp3 on the feed is still v7, because the cloud session that wrote v8 has no Google
  credentials (`google_credentials_ready` -> `DefaultCredentialsError`). One command on a
  host that has them:
  `python scripts/render_demo.py content/scripts/special_andrew_intro.md <out>.mp3`
  (never `render_audio.py` — the special_ lane must touch no state and reach no feed).
  **Then the test, which is the actual point:** she has heard v7, so play v8 without
  saying what changed and ask *"does anything sound wrong now"* rather than "is it
  better" — the nine comma-joins are the risk (over-joining trades staccato for the
  breathless run-on of the 2026-07-07 finding), and change #10, the native quotative
  reorder, is the one expected to move the needle. The unruled sheet is in the brief,
  one row per change, ready for the same Oracle sitting as the ல/ள–ர/ற audio A/B.

- **THE TTS OVER-ARTICULATES — a corpus-wide finding wearing a demo's clothes** (2026-07-31,
  Andrew's wife, Coimbatore native, on the rendered Andrew intro: natives mostly do not
  pronounce the ல/ள and ர/ற distinctions, the voice does, and that is what reads as uncanny).
  **Scope first: this is not about the demo.** Episodes, drills, soaks and knock memos all
  route through one `clean_for_tts` in `render_audio.py` and the same Chirp3-HD voices, so
  whatever the fix is, it lands once and covers everything. The pedagogy question it opens is
  bigger than the artefact: Andrew has been training his ear — and his mouth — on a register
  no one at the table speaks, which is the same class of problem as the fridge
  (`குளிர்சாதனப்பெட்டி`), one layer down from the words into the phonemes.
  **The concentration measured on this script, which makes the experiment cheap:** the ழ
  inventory is essentially TWO roots (`தமிழ்`, `எழுது-`) plus `செவ்வாய்க்கிழமை` — 23 tokens,
  3 lemmas. Roughly two-thirds of the ற tokens are ONE morpheme: the present/relative
  participle `-ற-` (`சொல்றேன்`, `பேசுற`, `இருக்கற`, `வர்றதுக்கு`), which recurs every other
  sentence and is a light tap in Coimbatore speech. So the uncanny surface is not diffuse —
  it is one high-frequency suffix and two lemmas.
  **DO NOT respell blind, and do not treat this as settled.** Non-standard orthography
  (`சொல்ரேன்`) may make Chirp3 worse, not better, and no one here can hear the output. The
  cheap honest path is an A/B: render one paragraph all three ways at the `clean_for_tts` seam
  behind a flag, and let the Oracle judge — a dialect-realisation call is hers by the same
  law that gave her `சாத்து`. Second lever worth pricing in the same experiment: a different
  voice may already do this, in which case the fix is a constant, not a transform.
  **THIRD ARM, added 2026-08-07** (from a Gemini critique of the Pillar V article — a model,
  not the Oracle. It carries zero dialect authority and is logged here as an *engineering*
  argument only). Instead of substituting the letter, insert the vowel the mouth already
  inserts: `சொல்லுறேன்` / `பண்ணுறேன்` rather than `சொல்ரேன்` / `பண்ரேன்`. The claim worth
  testing is not which is more Kongu — that is the Oracle's call and nobody on this side gets
  a vote — it is that `சொல்லுறேன்` is an attested spoken form people do write down, so Chirp3
  has plausibly read it, whereas `சொல்ரேன்` is orthography nothing was ever trained on. That
  is precisely the objection two lines up, and this arm may not carry it. Cost: one more
  render at the same seam, same sitting.
  **Rejected from that same critique, recorded so it is not re-proposed:** the Kongu vowel
  shifts (`முடிஞ்சது`→`மொடிஞ்சுது`, `உட்காரு`→`ஒக்காரு`, `இடம்`→`எடம்`) reopen *Competent over
  local* (DECISIONS 06-30) without stating what they replace; a blanket `-ச்சு`→`-து` rule
  would overwrite the Oracle's own `பழகிப்போச்சு`; and `வர்றீங்க` was offered as a first-person
  form, which it is not. The `-ங்க` softener it proposed is already `dialect.md`'s Kongu Layer
  and the `ஃப்ரீயா விடுங்க` ruling.

- **THE STACCATO IS OURS, NOT THE MODEL'S — why the Tamil reads "composed"** (2026-07-31,
  second half of the native-ear verdict: "sentence structures are mostly good, although they
  are evidently composed by not a native speaker"). **Measured on `special_andrew_intro.md`:
  121 sentences, median 4 words, mean 4.1, 67% at four words or shorter, longest 11.** Clause
  chaining is nearly absent (`-ட்டு` 11, `-னா` 7, `-றப்ப` 0, `-ும்போது` 2) and so are the
  discourse particles a Coimbatore speaker leans on (`ஆமா` 0, `இல்ல?` 0, `தெரியுமா` 0,
  `ஏன்னா` 0, `அதான்` 0). Uniformly short, unchained, unhedged declaratives — which is a very
  good description of "composed by a non-native".
  **The finding is that this is enforced, not emergent.** The script's own banned list says
  *"State the fact and stop"*, no announcing clauses, no `X, not Y` antithesis, no em-dashes.
  Those rules were written to kill LLM-slop rhetoric in the ENGLISH companion demo and were
  carried across to the Tamil lane, where their side effect is a staccato register no one
  speaks. The model is not failing to write natural Tamil; it is obeying a style rule that
  forbids it. **So the cheap move is a brief-level edit, not a rewrite:** keep the ban on
  announcing clauses and antithesis (those are still slop in any language), and lift the
  full-stop rule for the Tamil lane specifically — allow chained clauses and a handful of
  particles. Worth pairing with the render A/B so one Oracle sitting judges both.
  **Third factor, noted and not actionable yet:** both `special_` pieces are MONOLOGUES,
  and this system's founding insight (`JOURNEY.md` ch.2) is that two people chatting is what
  surfaces natural register — a lesson can hide in book Tamil, a conversation cannot. A
  one-voice piece is structurally the form most likely to sound composed. That is a real
  constraint on how natural this artefact can ever get, and it is worth knowing before
  anyone spends effort making a monologue sound spontaneous.

- **TESTS WITHOUT TEETH — a cursory audit, 2026-07-31** (Andrew asked for other axes where a
  case exists but not in the dimension that can fail). Three real findings, none built:
  1. **`render_audio` swallows an UNREADABLE sidecar** (`except (json.JSONDecodeError,
     OSError): pass`, then falls through to scraping `**bold**` words out of the script).
     A corrupt tags file therefore yields a *plausible* word list from a different source,
     silently. This is the same file and the same function the 07-31 pass just made loud
     for *unresolvable keys* — the fix covered the resolvable-but-missing case and left the
     unreadable-file case exactly as it was. Highest blast radius of the three: wrong data,
     not absent data.
  2. **`s32` pins the ordering law, not the property the bug violated.** KF-12 was *45 of
     70 deck items never asked while the meter reported a winning sprint*, and its
     regression case asserts sort-key comparisons on single calls — nothing iterates. The
     floor's twin, `s34`, DOES iterate (`for _ in range(40)` → "every word is reachable",
     "no word is hammered while others wait") because it was written the day after the
     starvation lesson. The deck never got the same treatment. Copy `s34`'s loop into `s32`.
  3. **`s8` (KF-8, lore format takeover) has the same shape.** The bug was *four lore memos
     in four consecutive days*; the case tests that `demand_streak` counts and that the
     cooldown line renders. Nothing simulates N days and asserts no format family exceeds a
     share. Format drift is a distribution property and it is tested pointwise.
  Also measured, for calibration: **22 of 43 smoke cases drive a real command entry point
  AND re-read persisted state.** The other 21 are mostly legitimate pure-function cases
  (`s1` parsing, `s4` normalize, `s18` budgets) — the number is not a defect count, it is
  the denominator to think with when adding the next case.
  **Contained, checked and clean:** `write_thin_learner` is the ONLY whitelist-style writer
  in the codebase (the 07-31 bug class does not have siblings), and the one
  `except Exception: pass` in `morning_knock` is deliberate and correctly commented
  ("never let a cadence check kill a reach") — fail-open on an advisory line, though it
  does mean the eavesdrop-cadence warning can silently never appear.

- **A VOLLEY WHOSE NOTIFICATION IS LOST IS STRANDED BY DESIGN** (2026-07-31, found live —
  Andrew replied to the 17:22 volley and it never reached GitHub). `morning_knock` reads no
  open-volley state: every knock is a fresh decision, so the only re-present path is the
  reply lane (KF-11's chat handler), which needs a reply to arrive — the exact thing that
  was broken. The entry sits at `volley_next: 1` forever, items 2-4 orphaned, and **nothing
  reads "open and stale"**: state is honest, no lane acts on it. Textbook Gate 7.2 —
  indistinguishable from a volley he simply hasn't answered yet. A resend via the queue is
  only a partial recovery (a queued push mints its own `knock_id` and carries no `volley`
  array, so the chain cannot resume). Shape when it comes off the shelf: the rails already
  compute a min-gap, so the cheapest honest version is a rails-side check — an open volley
  older than N hours with no reply is re-presented rather than a new dose being chosen.

- **ORACLE CROSS-POLLINATION — the intro script is a pipeline, not a demo** (2026-07-31,
  Andrew's stated intent; NOT IN SCOPE YET, filed so it isn't re-derived). `special_andrew_intro`
  was never a pocket party trick: the loop is *write a longer script in target Tamil → put a
  numbered question sheet to the Oracle → feed her rulings back into the colloquial engine*.
  Evidence the format works, from this round: she ruled 10, changed 3, and **refused #7** —
  "multiple are correct, but it depends on context" — which is knowledge a generator working
  from a static canon structurally cannot have. Her meta-remark (relayed 07-31, banked in the
  feedback ledger): the agent had *genuinely thought hard*, because several distinctions the
  sheet raised are ones **Tamilians do not consciously notice** — they cling to one form, or a
  form carries a connotation they have never had to name. That is the real asset: the sheet
  surfaces tacit knowledge no corpus holds. **Open questions when this comes off the shelf:**
  where rulings land so they bind generation (`architect.md`? a dialect canon file? lexicon
  connotation fields — a schema change, so frozen), whether a refusal like #7 is storable at
  all or only ever prose, and how a ruling reaches the episode writer without re-litigating
  the fence rules. Do not build before the trip.

- **AT THE COMPUTER: finish the Andrew-intro naturalness pass — it is blocked on the Oracle,
  not on work (2026-07-30).** **⚠ THE BRANCH IS GONE (checked 2026-08-26).**
  `claude/tamil-intro-naturalness-cr4wy2` exists neither locally nor on origin — origin
  carries only `main`. The applied fixes reached `content/scripts/special_andrew_intro.md`
  (it is at v8 on main), so what was lost is the six-section review prose, not the edits.
  **Anything below that describes the branch describes a place you cannot go**; treat the
  summary in this entry as the surviving record. It
  carried a
  six-section Coimbatore-ear review of `special_andrew_intro.md`, judged against attested
  spoken usage rather than grammar-book correctness. The confident zero-cost fixes are
  applied and committed; **the script has NOT been re-rendered and the existing
  `published_audio/special_andrew_intro.mp3` is now stale against it.**
  What was wrong, for context on why this is worth finishing: `பேச மாட்டாரு` was negative
  *volition* ("he refuses to speak Tamil") three sentences before the piece hands the
  conversation to a stranger; the நம்ம/நாங்க beat used a third form (`நாம`) for one of the
  two words it was teaching; the counterfactual fronted its quote so a listener could hear
  `என்னோட தப்பு` as *Anna's* fault two lines before the machine is blamed; and
  `plan-க்கு தெரியும்` gave a sheet of paper a dative mind.
  **The blocking step is her ruling on seven register questions**, written up ranked in
  `content/lessons/special_andrew_intro_brief.md` → Open Flag (on that branch). She does not
  need to read the script, only rule on the seven. Top of the list is `பொண்டாட்டி` — blunt
  said about a man to a stranger, and she is the person being named. Then re-render, then
  merge. **Do not merge before the ruling**: it is a public-facing artefact he plays to
  strangers, and three of the seven change what a native hears in the first twenty seconds.

- **A word-adjacent hyphen becomes a SPACE before TTS, so every Tamil suffix written with a
  hyphen reaches the voice as its own word (2026-07-30, found while reviewing the Andrew
  intro; affects EVERY episode, not that one file).** `clean_for_tts` →
  `defang_hyphens` is `re.sub(r"-(?=\w)|(?<=\w)-", " ", text)`. It exists for a good reason
  (the voice reads a glued hyphen as "minus"), but the cure detaches the suffix: `போலாம்-னா`
  went to Chirp3 as `போலாம் னா`, which severs the "X means Y" gloss — and that was on the
  intro's emotional heart, the நம்ம/நாங்க demo. Fixed *in that one file* by fusing to
  `போலாம்னா`, matching the fusion the same script already uses for `இருந்துச்சுன்னா` and
  `வந்தாருன்னா`.
  **The class is unfixed and is house-wide.** Two shapes:
  1. *Tamil root + Tamil suffix* — always fusible, always should be (`ங்க-க்கு` in the
     intro, still open; it is also a consonant pile-up with no boundary for the ear).
  2. *Tamil-script root + Tamil suffix where house convention hyphenates anyway* —
     `டயர்ட்-ஆ`, and the lexicon itself carries `ஃப்ரீ-யா?`, `இட்லி சூப்பர்-ஆ இருக்கு`,
     `வயிறு ஃபுல்-ஆ இருக்கு`. These all detach at render. Fusing them (`டயர்ட்டா`) is
     probably right but changes an orthographic convention that spans the corpus and the
     lexicon keys, so it is **not** a one-off edit.
  English-root cases (`boring-ஆ`, `phone-க்கு`, `machine-ஓட`) detach too but there is no
  better option — a Latin/Tamil-script join with no separator is worse. Cheapest honest
  move is a lint that flags a hyphen with Tamil script on *both* sides (case 1 only, which
  is unambiguous); the case-2 convention question needs Andrew. **No sighting in a lesson
  episode yet** — this was found by reading the render path, so it is latent-by-inspection
  and sits under the one-sighting bar. Worth one deliberate listen for a detached suffix on
  the next episode before spending anything on it.

- **For a `frame:` payload the episode lane SELF-CERTIFIES delivery without evidence
  (sighted 2026-07-28, first real exercise of the repair-first law).** Two defects were
  found by commissioning `frame:youknow-la` as an episode and watching what came back;
  the first is now fixed, the second is schema-adjacent and stays here.
  1. ~~**The ticket has no soak-order section.**~~ **SHIPPED 2026-07-28 evening** as
     `suggest_targets` section **0. THE COMMISSION** — payload, focus, scene_seed and an
     "outranks every list below" heading, printed ahead of everything the ticket computes,
     with the FOCUS SET stating that it is outranked. `episode_commission()` is the one
     predicate; `commissioned_form()` delegates to it and therefore now respects
     `delivered` (a consumed order used to keep pinning the next episode's form). Smoke
     case `s39`. See DECISIONS, "A commission reaches the episode lane as computed
     context". Original report: the Director's only route to the order was one prose clause
     in `DIRECTOR` (*"read the soak-order in progress/learner.json"*), an agentic read
     competing with a code-assembled list headed *"DRILL these until they fire cold"*. It
     lost — the episode dramatised the focus set and the payload was absent — while in the
     SAME run `form: phone_call` arrived through `scene_spec()`/`claim_spec()` as computed
     context and landed perfectly. The repo's own doctrine failing in the direction it
     predicts.
  2. **`claim_payload()` rubber-stamps frames** (`run_studio.py:418`):
     `if key.startswith("frame:") or key in script:` injects into `new_words_landed`
     unconditionally, because a slot template is verbatim-exempt. So a frame payload is
     claimed whether or not one instance is audible; the produced-check then clears, the
     order stamps delivered, and the debt reads PAID with no evidence. Non-frame keys are
     correctly checked and reported. This is the 07-27 judge fix one lane over — crediting
     the target you wanted rather than what actually happened — and it means the ledger can
     book a repair that never shipped. **The hard part is the design, not the patch:** a
     frame has no fixed surface form, which is *why* it is exempt. Verifying it needs a
     pattern the frame record itself carries (e.g. the invariant tail `…ல`), so it is
     schema-adjacent and sits under the structure freeze — hence parked, not fixed.
  Evidence lives in the 07-28 run: the failed Mission 77 sidecar claimed a 28-item payload
  drawn from the focus set with no `frame:youknow-la` in it. Caught only because the writer
  ALSO broke the fourth wall and failed lint on unrelated grounds; had it passed, the debt
  would have been marked delivered. **Correction to the session-log entry at the bottom of
  this file:** it says a `--soak-*`-only call appends a session row. Verified against
  `sync_state.py:617` — the append is conditional on `cold/hinted/demoted/listened/debrief`,
  so a soak-order-only write appends NOTHING. `--debrief`-only does append; that half stands.

- **Audio is a queue-of-one — give it a real queue (2026-07-28, deliberately NOT bundled
  with the repair-first commissioning law that shipped the same day).**
  `learner.json.soak_order` is a single dict: a new order overwrites the old. Text pushes
  have a real queue (`push_queue.py`) with a drain, retries and pacing rails; audio has a
  slot. So exactly one repair per day survives and the rest fall into debrief prose —
  memory for the next *chat*, never a commission. Under the new backward-first rule this
  binds harder, because a day with three unclosed repairs now genuinely wants three orders.
  The shape is already specced below (the `due` field + the hourly tick acting on it,
  dispatching by `channel`). **HOLD** until the prose rule has run several days: if
  backward-first alone closes the felt signal, the queue is machinery Andrew doesn't need,
  and the standing rule is that new engineering starts from a reproduced signal, not a
  plan. Re-open on evidence — a session close where Anna visibly has to *drop* a repair.

- **Scheduled/unattended episode production — DEFERRED 2026-07-27 by Andrew after
  exploring it.** Wanted: Anna (or Andrew) commissions from either machine, it builds and
  publishes at a chosen time, and the phone gets told. Andrew proposed a `push_queue`
  variant; explored and **not** the recommended shape, for three reasons read out of
  `push_queue.py`: the drain runs at the START of every wake-up including every
  lock-screen reply (a memo is ~1 min of TTS, an episode is three LLM passes plus ~10 min
  — Andrew would wait at a blank shade); the drain has no claim/lease, and the known
  double-fire residual costs a duplicate buzz today but would cost two renders, two
  mission numbers and two racing commits for an episode; and every drain gate
  (`MAX_REACHES_PER_DAY`, one-non-forced-per-tick pacing, quiet-hours deferral) is built
  for *reaches*, so an episode would eat a knock slot.

  **The shape that converges with the parked 07-24 plan:** the soak order already IS the
  queue-of-one — payload / scene_seed / focus / channel / form / from / delivered, with
  `soak_pending()` as the predicate and `MAX_UNATTENDED_PER_DAY` as the rail. It needs a **⚠ THE RAIL IS GONE (2026-08-27):** `MAX_UNATTENDED_PER_DAY` and `produced_today()` retired with `studio_watchdog.py`. This proposal must bring its OWN rate rail — `s27`'s no-unattended-dispatcher check goes red the moment a scheduled lane can fire production, which is the forcing function, not a suggestion.
  `due` field and the HOURLY TICK (never the drain) acting on it, dispatching by `channel`
  through the door built 2026-07-27. One field, one workflow step.

  **Two hazards that block anything unattended, whichever shape wins — fix first:**
  1. `run_studio.next_mission()` is `max(glob) + 1` off the local filesystem. A cloud tick
     and a laptop will claim the same number. Impossible today only because laptops are the
     sole producers and Andrew serialises them by hand. Wants claim-by-commit.
  2. `.studio.lock` is a local file lock and **cannot** exclude a GitHub runner from the
     laptop. Nothing serialises two machines today.

  **Recommended first step (also deferred):** a `workflow_dispatch` input that produces ONE
  cloud episode manually — no policy, no tick integration, no autonomy — to hear whether a
  Flash-written episode holds up before Anna may make them unattended. Andrew's own context
  for the deferral: the starvation that motivated auto-production (episodes arriving only
  when he sat for a lesson) has eased because he is showing up reliably now.

  **⚠ THE DEFERRAL'S PREMISE IS CONTRADICTED (2026-07-28) — but this item stays deferred.**
  The daily ritual did land (*"I'm finally getting into a daily ritual of sitting down and
  doing at least one session"*), so the 07-27 reasoning held on its own terms. The
  starvation did not ease, though — it **changed shape**. It is no longer *"episodes arrive
  only when I sit for a lesson"*; it is *"the episodes that arrive don't target the mistakes
  I'm making, and I have to ask for the ones that would."* His reliability cannot fix that
  one: showing up is precisely what generates the errors that go undosed. **This does not
  reopen unattended production** — the new signal is about WHAT gets loaded into the rails,
  not about who pulls the trigger, and the attended session-open dispatch already works.
  Both hazards below (mission-number claim race, cross-machine lock) remain unfixed and
  remain blocking for anything unattended. See "THE REPAIR EARNS THE DOSE" at the top.

- **Upsert `word_pool.json` into the lexicon, then retire the file (2026-07-26, Andrew's
  call — supersedes the assistant's "just delete it").** Verified safe: `compute_floor`
  counts only comfortable/solid, and `floor_gap_targets` requires the same, so ~295
  imported rows land inert — no meter moves, nothing floods the drill list, and
  `is_unseen` already means "in the curriculum, never encountered", so teach-first covers
  them on day one. Wins: one store instead of two incompatible schemas, and the 11
  duplicate rows dedupe for free on a keyed upsert. **The one thing that must survive the
  move is `cluster`** — it is what lets intake say "food vocabulary is thin, pull there"
  instead of picking at random; it becomes a lexicon field and
  `new_candidates_by_cluster` reads the lexicon instead of the file. Deliberately NOT done
  in the 07-26 session: it is a 295-row change to Andrew's learning state and the
  focus/background split shipped the same night should be watched for a few real sessions
  first (ship the thin slice, widen after it works). Open sub-question for Andrew: do the
  27 rows already in the lexicon keep their live gloss, or does the pool's gloss win?
  (Recommend: live gloss wins — the pool was never vetted by the Oracle.)

- **CURRICULUM ARCHITECTURE AUDIT (2026-07-26, `/recalibrate`, Andrew's felt signal:
  "the curriculum/deck/machinery/catch-response layers grew by iteration and discovery,
  not top-down design — make the abstraction clean, and don't let the deck starve the
  larger goal").** Third strike on this axis (07-18 "wants curriculum/pedagogy made
  pristine" → 07-25 "we are still starving some of these" → today). The 07-25 ruling fixed
  starvation *inside* the deck; Andrew's question today is about everything outside it,
  which has not been ruled on. Read-only evidence sweep, six findings, ordered by cost:

  1. **The floor selector never got the 07-25 ordering law — this is the "deck starves the
     larger goal" mechanism.** `docs/DECISIONS.md` (07-25, "One selector, one ordering law
     — the predecessors are retired, not stacked") records `recent_ask_counts` becoming the
     third term of the one sort key. It landed in `deck_status` only.
     `suggest_targets.floor_gap_targets` (`scripts/suggest_targets.py:94`) still sorts
     `-staleness → ripeness → soak → alphabetical`, **no `asks` term**. Not theoretical:
     121 of 134 pending floor words tie at `NEVER_SURFACED`, so the tiebreak does all the
     work (41 distinct key prefixes over 134 items; largest tie group 14, broken purely
     alphabetically) — and **7 of the current top 14 floor targets were asked within the
     last 3 days** (சரி, ஆனா, இருக்கு, அண்ணா, சொன்னாங்க, மாமா, அவங்க). Exactly the
     rich-get-richer freeze the 07-25 entry diagnosed, still live on the larger goal.
     *Cheapest real move: add the `asks` term, completing a decision already made.*

  2. **The deck doesn't steal reps — it monopolizes instrumentation.** Knock targeting is
     roughly balanced (deck 24 / non-deck 5 / no target 34 / novel 12 across 75 knocks).
     But the deck has tier ordering, a coverage meter (`deck_coverage`), a deadline
     countdown, a status headline and a 3-term sort; the other 230 lexicon words have a
     floor percentage and nothing else — no coverage meter, no tier, no ask term. What gets
     measured gets worked.

  3. **There is no curriculum layer any more; there are three, and the original is dead.**
     `curriculum/word_pool.json` — 333 rows / 322 unique (11 duplicate rows), 20 clusters,
     priority 1|2 — is the abstraction the project was designed around. **27 of 322 have
     ever entered the lexicon (8%); 189 of 212 priority-1 entries never used.**
     `curriculum/trip_deck.json` (82 items, richer schema) is the real working curriculum,
     and shares exactly **1** entry with the word pool — the two were drafted independently,
     have incompatible schemas (`cluster`/`priority` vs `register`/`type`/`direction`), and
     only the deck can express machinery or ear-only. Meanwhile **209 lexicon entries are in
     neither file** — created ad-hoc in session. That is the largest de facto curriculum and
     it has no source file, no taxonomy, and no Oracle vetting. Options: retire the word
     pool as a fixture; or re-seat it as the post-trip curriculum with the deck's schema.

  4. **`register` is three axes wearing one field.** Topical (gossip/mil-table/faq/social/
     public/antifreeze/zinger), type restated (`frame`, on 20 of 21 frames), and priority
     (via `DECK_TIERS` register→tier). So `DECK_TIERS["frame"]=0` means *all machinery is
     auto-survival* — a pedagogy policy hidden inside a taxonomy collision. The single frame
     that declared a topic instead, `frame:youknow-la` (THE gossip opener, Oracle-confirmed),
     is tiered **dessert** — bottom of the queue — purely because its author filled a
     different field. Separately, `REGISTERS` at `suggest_targets.py:58` is the *emotional
     tone* palette (tenderness, dread, mischief…) — an unrelated meaning of the same word in
     the same module as `deck_registers()`.

  5. **"Catch and response" has no representation at all.** Andrew names it as a first-class
     curriculum kind. The schema has `direction: catch` (12 items — not the 5–6 he
     remembered; 1 cleared), but the *pairing* — hear X → say Y — exists only as English
     prose in `note`/`gloss`: "the 'eppo vandheenga?' answer", "HER line — hear it coming".
     No `pairs_with`/`response_to` field anywhere in the repo. The whole `faq` register is
     answers to prompts that live in parentheses, and nothing can drill a pair as a pair or
     meter it. Concrete casualty: the catch item இன்னும் கொஞ்சம் சாப்பிடுங்க (the maami's
     *eat more*) is in the deck; its natural response வேண்டாம்மா, வயிறு நிறைஞ்சிடுச்சு is an
     orphan (see 6) — the pair was split and nothing noticed, because nothing knows it's a pair.

  6. **`seed-deck` is an orphan factory (hygiene + silent state loss, not a lying meter).**
     `sync_state.cmd_seed_deck` un-tags departed items (drops `deck` + `direction`) but
     leaves `type`, stranding 15 rows: 10 chunks + 5 frames. Most of the 10 chunks are
     **superseded rephrasings** where the Oracle changed the wording and the old row stayed —
     எவ்வளவு ஆகும்? / எவ்ளோ ஆகும்? (one phrase, two spellings), பிறகு பார்க்கலாம் /
     அப்புறம் பார்க்கலாம், சாஃப்ட்வேர் வேலை பண்றேன் / …இன்ஜினியரா இருக்கேன்,
     காரம் …பழக்கமாயிடுச்சு / …பழகிப்போச்சு. **Learning state does not transfer to the new
     wording**, so a soaked phrase resets to zero under its new spelling. Good news: they do
     not corrupt the meters — 0 of 10 reach the floor denominator (all still `struggled`).
     The 5 orphan *frames* are the opposite of a bug and should be left alone:
     present-future-toggle, obligation-ணும், cant-முடியல, idum, negative-la are organically
     discovered machinery and **are** counted in Engines (21 = 16 deck-fire + 5 orphan) —
     the machinery axis absorbs discovery correctly. Options: a `supersedes` field on deck
     entries so a rephrase migrates state; or a one-time reconciliation pass.

  **RESOLVED 2026-07-26** (see `DECISIONS.md`): #1 landed — and was *wrong the first way*,
  because a 3-day cooldown is not a coverage term; the real fix is lifetime `rep_counts`,
  `coverage_key` as the one shared law, and a focus/background split (Andrew's design).
  #5 landed as `pairs_with`; the four missing FAQ *questions* are an open Oracle content ask.
  #6 closed as no-mechanism — all four rephrase pairs had zero state on both sides.
  #4 (`register` carrying three axes) is **still open** and deliberately deferred: it is a
  schema change with pedagogy consequences and it is not hurting the trip.
  #3 (`word_pool.json`) is **still open** — retirement was proposed and *overruled*: Andrew
  wants it incorporated, not deleted, by upserting its 322 entries into the lexicon with
  their `cluster` tag so there is one store and one schema. Not done; see below.

- **BUILD (decided 2026-07-24): autonomous cloud episode production, inside the knock
  tick.** The cron question is settled — the local watchdog cron is RETIRED, replaced by
  cloud production. Direction locked with Andrew:
  - *Foundation DONE* (commit dc94bf2 / pushed 737fef5): the studio writer is now
    executor-agnostic — `agy` locally, OpenRouter→`google/gemini-3-flash-preview` in the
    cloud, with `inline_canon()` carrying the protocol files into the single-shot prompt
    (a bare API call has no filesystem). Proven on-canon, ~$0.03/episode, CI green.
  - *Remaining, one coherent phase (touches the KNOCK LOOP — the primary channel; a bug
    there fails silently, so build fail-safe + dry-run-tested before it goes live):*
    1. **New `episode` move in the knock tick.** Anna (he) may CHOOSE to produce (he
       decides *when* — Andrew's call, not a fixed cadence), but Python's guardrails
       dispose: only if `soak_pending()`, `produced_today() < MAX_UNATTENDED_PER_DAY`, and **⚠ THE RAIL IS GONE (2026-08-27):** `MAX_UNATTENDED_PER_DAY` and `produced_today()` retired with `studio_watchdog.py`. This proposal must bring its OWN rate rail — `s27`'s no-unattended-dispatcher check goes red the moment a scheduled lane can fire production, which is the forcing function, not a suggestion.
       waking hours. A gated-out choice logs as grace/silence, never overspends. On go, it
       dispatches `run_studio.py` (which owns write→render→publish→commit→push, incl. the
       "go listen" phone push); then the tick logs the reach so the rails see it. Ordering:
       studio commits/pushes first, then the knock-log commit — no double-push.
    2. The digest must surface the soak-pending signal so Anna can see there's something to
       produce (build_digest currently doesn't).
    3. ~~**Drop the "Cloud never renders episodes" rule**~~ — **DONE 2026-07-24**, in the
       canon (DECISIONS marked SUPERSEDED/CORRECTED) and then in the machine: the rule also
       lived as prose in `JUDGE_MANDATE`, in `/extend` Gate 6, and as a smoke assertion that
       *required* the refusal text — so Anna went on refusing for eight hours after the
       canon changed. Lesson recorded: a dropped rule must be hunted in code, prompts,
       skills and tests, not just in DECISIONS.
    4. ~~**Retire the local cron for real**~~ — **DONE 2026-08-01** (drift audit): the
       paused line is deleted from the crontab. `studio_watchdog.py` stays as a manual
       command — the session-open drain is the live door; the watchdog is the hand-run
       retry for a laptop session that wants one.
    5. ~~**The 9am-audio lane**~~ — **DONE 2026-07-24.** Shipped as the workflow
       consolidation rather than as a GCP wire-up of `push-queue.yml`: one `anna.yml`
       carries every trigger and every secret, `memo_script` rides the queue entry, and the
       drain renders it at fire time. See DECISIONS "One runner, every capability."
  - *Small determinism fix (do alongside):* Python stamps the `scene_spec`-decided
    `episode_form`/`register`/`ingredient` into the sidecar instead of trusting the writer
    to echo them down the Director→Architect→Producer chain (the thin slice caught Flash
    labeling a `vignette` as `classic`; the script was right, the label drifted). Hardens
    `agy` too. Needs the structured spec plumbed into `write_episode` (today it's only in
    the ticket TEXT).
<!-- RESOLVED 2026-07-24: machine-commit-identity — Andrew is OK with automated commits
     signing as him for now. The ambiguity is automated-vs-human-initiated (cloud already
     self-labels github-actions[bot]; only the retiring local cron committed as him
     unattended), and cron retirement mostly dissolves it. No self-labeling machinery to
     build. See DECISIONS.md "Machine commits masquerading as Andrew are acceptable for now". -->


- **The trip harvest** (2026-07-18, direction approved — build when the Aug 5 campaign
  is drafted): the trip is a field-mission arc, not an exam. Final campaign (Aug 5–12)
  goes rehearsal-shaped — Table Rehearsal dominant, the five-scenario checklist as the
  hard artifact, "survived end-to-end at speed" as that week's meter — and live
  encounters get harvested nightly into the ledger. Context locked in: Andrew brings
  phone + laptop, expects MORE free time not less, and keeps working on/with the system
  through the trip — capture rides the existing channels (session close, knock-reply
  meta_notes); no new plumbing needed.

Endorsed in principle 2026-07-08 (pedagogy review — direction approved):

- **Daily spoken reps** — the trip test is mouth-under-pressure, nearly all current production is typed. **Experiment started by hand 2026-07-08:** first drill cut and on the feed ('Cold Fire: Eight Due'); machinery (drill-as-knock, below) waits until a few drills prove the format.
- **Cold decay / re-test dates** — cold is a one-way door today; confirmations at ~2/7/21 days or it demotes. Interacts with the deck meter (headline could go backward mid-sprint) and needs graduation data that doesn't exist yet — **defer past the trip.**

- **Voice loop (speech-IN half)** — let Anna *hear* Andrew: a phone voice-note lands, gets transcribed, judged like a knock reply. The speech-OUT half shipped 2026-07-02 as the drill track (`render_drill.py`); what remains open is Andrew's voice coming back in. **Parked on evidence 2026-07-09 (Andrew):** his block is Thanglish-parse confidence, not friction — run the spike (a few real voice notes through an audio-capable model, no machinery) before building anything.
- **Pull the wife in as the north star** — the real viability floor is "can I say this to her." Anna could hand a line: "try this one, tell me how it landed tomorrow." Costs no code. **Decided 2026-07-09: stays opportunistic** — no daily/scheduled missions; ripe item + obvious moment only (see DECISIONS).
- **Drill as a knock modality** — `morning_knock.py` could choose "drill" and commission `render_drill.py` itself (today Anna-in-session or Andrew runs it). Wait until a few drills prove the format.
- **Single deployment ladder per item** (post-trip) — consolidate the overlapping frames
  (recognition buckets / production axis / floor / engines / deck fire-catch) into one
  per-item stage: heard → understood → spoken-scaffolded → spoken-cold → survived-live,
  everything else derived. From the 2026-07-09 greenfield review; a consolidation, so it
  must *delete* more state than it adds or it doesn't happen.
- **Concurrent drains could double-fire one queue entry** (introduced 2026-07-24 by the
  workflow consolidation — an honest residual, not a sighting). The drain used to be
  serialized by `push-queue.yml`'s own `concurrency: push-queue`. Now it runs at the start
  of every wake-up, and `anna.yml` deliberately gives each reply its own concurrency lane
  (a reply must never queue behind a knock render), so two runs *can* overlap: two replies
  to DIFFERENT knocks inside the same ~30s, with an entry due. Both would push, then the
  second's queue write rebases onto the first — a duplicate notification and a duplicate
  klog entry. Narrow (replies to the same knock share a lane and serialize; the drain is
  the first step, so the window is seconds) and low-consequence. The real fix is a claim/
  lease on a queue entry — a schema change, so it waits per Gate 2. Revisit on first
  sighting, or if scheduled pushes get frequent enough to make the window matter.
- **Published feed titles could still be mutated by any writer** (residual of the
  2026-07-25 Apple-Podcasts fork; the *cause* is fixed, the *class* is not). Apple treats a
  retitle of a published item as a new episode, and `rebuild_rss` derives every knock/
  scheduled/reply title from `knock_log.json` at rebuild time — so any later change to a
  `move` string (a hand repair, a judge rewrite, a klog migration) silently forks that
  episode in Andrew's player. The drain, the only lane that actually did this, now rebuilds
  after the log write (smoke s29 asserts it). The class-level guard is an `existing_titles()`
  in `rebuild_rss` mirroring `existing_pub_dates()`: once published, a title is frozen. ~8
  lines, same shape as code already there. Held per the one-sighting bar, and because it
  would make a genuine title correction unfixable without hand-editing `rss.xml`. Revisit on
  a second fork, or the first time we want to rewrite move labels in bulk.
- **Phantom-fired knock on delivery failure** — the knock logs + commits *before* the
  notify step, so a push that fails all retries leaves `acted: true` for a dose Andrew
  never saw (rails count it; judge could grade against it). Seen once (2026-07-14 DNS
  blip, now retried at the chokepoint). A `delivered: false` mark on final failure
  would make the log honest. Wait for a second occurrence post-retry.
- **Real-media library (songs, kids' TV)** — the Jabberwocky principle: melody stores sound-sequences below comprehension (Andrew still carries sung gibberish from decades ago). Curate Oracle-vetted YouTube links (her childhood film songs, Tamil Dora) as rows of data; Anna sends one as a no-ask dose, lore-style — a skill, not a DJ persona. Feeds the starving catch axis (0/8) and buys shared cultural ground before the trip. Guardrails: stop-chasing-listens applies in full (zero-debt, no follow-up); curation happens at the laptop, studio-style, never in-session. Machinery (a knock "song dose" type) waits until the library exists and a few doses prove the format by hand.

- **Tamil script is banned from TEXT bodies — needs a lint, not prose** (2026-08-02).
  Andrew said it twice in one day, in-session and by phone reply: *"I can't read the Tamil
  I need this phonetic in text."* The constitution's modality split (script is for TTS,
  phonetic for chat) is only ever stated permissively — `knock_reply.py`'s judge mandate
  says phonetic "is fine here", so nothing forbids script, and knock bodies do ship it
  (`💬 போனோம், நல்லா இருந்துச்சு`, 08-01). Second data point ⇒ mechanism: reject Tamil
  codepoints in a text-modality body and in `reply_line`, while `memo_script` and
  `voice_reply` keep script. Deterministic and cheap; the prose rule has now failed twice.
- **Commissioning from the phone — `schedule episode`** (2026-08-02). Anna's reply lane can
  speak (`voice_reply`), queue one push (`schedule`), and write state — but has no way to
  order an *episode*, so "make me an episode about X" becomes a voice memo pretending to be
  one. It should not run the studio inline (minutes long, lint-gated), but setting a soak
  order is just a state write the lane already does: a `commission` object on the reply JSON
  passing through to `--soak-payload/--soak-seed/--soak-focus/--soak-channel`, drained by
  `run_studio` on the next tick. Andrew named this one himself.


<!-- The block below was filed under `## Shipped` between 2026-07-27 and
2026-08-18 and is OPEN. Restored to Ideas 2026-08-26; the heading had stopped
meaning anything and two Gate-2 holds were sitting on the wrong side of it. -->

- **Fielding has no cadence gate, and it is a sole-owner channel** (2026-07-27, noticed
  while mapping the architecture). Catch and heard-question→produced-answer are each
  trained by exactly one modality. Catch has `EAVESDROP_CADENCE_DAYS = 3`, a floor
  frequency that exists because the axis already stalled once. Fielding — which
  `OUTREACH_MANDATE` itself says no other channel trains — has no equivalent term, so
  variety pressure can steer away from it indefinitely and nothing in the digest says so.
  One data point, no evidence it has actually stalled. Cheap version is a digest line,
  not a gate. Do not act mid-sprint.
- **Pre-registering the chat rep's target** (2026-07-27, from the coach/judge discussion —
  see DECISIONS same date). Would give the chat lane the property that makes the phone
  grade meaningful: the target committed before the rep, not reconstructed at close from
  Anna's own account. Schema-adjacent, so it sits under the structure freeze; and there is
  no evidence yet the chat floor is inflated. Revisit only if the trip contradicts the
  floor number.
- **The post-trip arc — three proposals, none chosen** (2026-07-27, awaiting Andrew).
  Diagnosis is in DECISIONS same date. (a) Name the trip itself as the `/recalibrate`
  run — eight days of live fire is the highest-quality felt signal the system will ever
  get, and the existing skill designs the successor from it with zero new structure.
  (b) Let the trip author the next deck: the phrases he needed and did not have, captured
  live via knock replies and `sync_state.py feedback` (both already work from the phone),
  informant-vetted by construction because the informants are the table. (c) The
  denominator that replaces `15/34 survival cold` on the status line is the one decision
  that cannot be deferred past touchdown — and it depends on what the trip exposes, so it
  is deliberately left open rather than guessed now.
- **Volley chained recasts can double the re-presented ask** (2026-07-27). Exchange 2 of the
  antifreeze volley pushed back `· 3/4 — · 3/4 — you know the thing but…`, and one reply_line
  carried mojibake (`mেdhuva`, a Bengali vowel sign spliced into the Latin). Cosmetic, and the
  lock-screen budget makes a doubled prefix cost real characters. Both are one-line fixes in
  the volley re-present path; neither has recurred yet.
- **A word taught in-session cannot enter the lexicon** — ~~first half~~ **SHIPPED
  2026-07-28** as `sync_state.py update --teach "WORD=gloss"`: creates the record at
  `struggled` recognition, seen today, production unset (so it can never inflate the floor),
  Tamil-script-only so keys stay canonical, and it runs BEFORE the axes so a word taught and
  fired in the same close resolves instead of being refused. Re-teaching a known word
  refreshes it without resetting recognition. `பக்கத்துல`, `ஆச்சு` and `இருக்கேன்` were
  entered the same day. Smoke case `s38`. **SECOND HALF SHIPPED 2026-07-31** — the
  session_log inflation below is closed: same-day `update` calls now MERGE into that
  day's row instead of appending (union on the word lists, a later debrief supersedes,
  an absent one never blanks). It had reached 38 rows for 26 real session-days by the
  day it was fixed — and the cosmetic overcount was the smaller half, since
  `cold_fires_recent()` and `fires_today()` sum word lists across entries, so a word
  logged twice in one close inflated the trailing pace the burn rate is computed from.
  Historical rows left as they are pending Andrew's call on a backfill. Smoke case `s42`.
  Original report follows.
  The pakkam/paakkalaam
  deep-dive taught `பக்கத்துல`, `ஆச்சு` and `இருக்கேன்`; all three were refused at close
  (`not in lexicon — add recognition first`), and `--mark-seen` refuses them for the same
  reason. The only entry path is `seed-deck` from `curriculum/trip_deck.json`, which is a
  deck-authoring flow, not a session one. So the live teaching surface — the Teach Beat,
  the lore tangent, an Active Gaps item Andrew asked for **by name** — writes nothing, and
  the next ticket cannot know the word was taught. Worse in the soak lane: `ஆச்சு` is now
  the payload of a queued order for a word the lexicon has never heard of. Cheap version is
  a `--teach WORD --gloss "…"` that creates the record at `struggled` recognition, seen
  today, production unset — one row, no schema change. This is the write-side twin of the
  07-27 credit-the-word-he-said fix: that one taught the judge to credit a substitution,
  this one lets a taught word exist at all.
  **Second and third data points, same day (2026-07-28):** the 07-28 close wrote
  **three** `session_log` rows — fires, debrief, then a debrief correction — because a
  close split across multiple `update` calls appends a row each time. Any multi-call
  close inflates it, not just the court-of-appeal path, so the `--correction` flag
  above is really "don't append a row when this call carries no fires," which is the
  common case for `--debrief`-only and `--soak-*`-only calls. Adherence read off this
  log now overcounts 07-28 by 2.
- **The deck coverage meter counts delivery, not engagement** (2026-08-04, found while
  auditing why delight sat at 1/27). `deck_coverage`'s "worked" is anything that sets
  `last_surfaced`, which a soak tape does — so survival reads worked 33/34 while two of
  those (வலது பக்கம் திரும்புங்க, ஆமா ஆமா) only ever appeared on a tape and were never
  asked. Nine deck items across all tiers have `last_surfaced` with zero reps. The meter
  was built on 07-25 precisely to stop a headline hiding a distribution, and it has a
  softer version of the same blindness. Cheap version: report worked/tested as a pair on
  the ticket, the way the ear-only line already hints at ("4 heard in an episode but never
  asked"). No schema change — `reps` already exists.
- **Episodes run at a fifth of their own spec** — ~~**and the evidence is partly
  fabricated**~~ (2026-08-05). **HALF SHIPPED 2026-08-10, noted here 2026-08-26.** The
  measurement half is fixed: `render_audio.get_duration` now opens *"Measured, or LOUD —
  never a plausible fiction (2026-08-10)"* and refuses to invent a number when ffprobe is
  missing. **The length shortfall itself is still open, and it is now testable** — every
  episode registered since 08-10 carries a real duration or an honest absence, so the
  question "do episodes hit their spec" can finally be answered from `episodes.json` instead
  of argued from nine rows polluted by 3.0-minute placeholders.
  **THE MEASUREMENT IS DONE (2026-08-26). The shortfall is real and much smaller than this
  entry claimed.** Every episode dated by first appearance in `episodes.json`; the ten rows
  stamped exactly 3.0 excluded as unknown rather than short. Post-fix (08-10 onward, n=5):
  median **3.04 min**, mean 3.93, range 2.57–7.24, and **1 of 5 reaches the 5-minute classic
  floor**. Across all 66 honest rows: median 3.5-ish, 15 of 66 reach it. So episodes run at
  roughly **two-thirds of the classic floor, not "a fifth of spec"** — the original figure was
  an artefact of the placeholder rows it was measured on.
  **AND THE CAUSE IS NOT PAYLOAD SIZE.** Correlation between payload word count and duration
  is **r = 0.23** over 66 honest rows — effectively nothing. The two longest episodes ever
  (M68 at 10.20 min, M72 at 10.04) carry 15 and 16 payload words; M6 and M23 carry 53–54 and
  run 8.62 and 7.19. **This is evidence against "The payload IS the scale" (DECISIONS
  2026-08-05), which made item count the only dial.** Not a refutation — n is small, forms are
  mixed, and the decision also bought the deletion of `scale`, which was worth having. But the
  dial does not appear to move the thing it was kept for, and that is worth Andrew's ruling
  rather than a silent drift.
  **WHAT DOES PREDICT LENGTH, on this data: whether the writer honoured its output contract.**
  Episodes whose script opens with a proper H1 run median 4.08 min (15/45 reach the floor);
  those that fall back to `Mission tier2_missionNN` run median 2.45 (**0/21**). The four
  post-fix short ones — M87, M88, M89, M90 — all open with `[SFX: …]` instead of the title.
  M86, the one that opens with its H1, is the one that hits 7.24. **A missed H1 is a free,
  already-recorded proxy for a thin generation**, which makes the 2026-08-20 lint worth more
  than the title guard it was filed as. See the title-reader entry below for the seam that is
  still open.
  M78–M85 remain stamped 3.0 and should be read as unknown, not short. Original report
  follows. `architect.md` targets
  **5–8 min** for a classic and **12–18** for a narrated_drama. Measured recent episodes:
  0.73, 0.73, 0.90, 1.18, 1.18, 1.65, 2.43, 2.43, 3.47 — only M72 (10.04) ever hit spec.
  That is across forms, so the payload-is-the-scale fix (2026-08-05) does not touch it.
  **The measurement itself is unsound:** `render_audio.get_duration` is
  `except: return 3.0` — a bare fallback that writes a plausible number when ffprobe is
  missing, and `anna.yml` shows `Install ffprobe → skipped`. M78 and M81 both carry an
  identical "3.0" that is a placeholder, not a duration. So the length shortfall is real
  on the measured rows, but nobody can say how long M81 actually was. Fix the fallback
  first (record null/unknown, never a number) — a meter that fabricates is worse than an
  absent one, and it is currently the only length evidence we have.
- **A lexicon key containing a comma can never be commissioned into a soak payload**
  (2026-08-05, hit while commissioning the arrival-day drama). `canon_payload` splits on
  commas unconditionally, at write AND at read, so `வேண்டாம்மா, வயிறு நிறைஞ்சிடுச்சு` and
  `காரம் பரவாயில்ல, பழகிப்போச்சு` — both real trip-deck items, both never worked — cannot
  be passed. Their phonetics carry the comma too, and no fragment resolves. Only 2 deck
  keys are affected today, and the eat-more refusal survived via `pairs_with`; the spice
  line had to be named in the scene seed as prose instead. Cheap fix: don't split an item
  that already resolves to a lexicon key, or take a separator that cannot occur in a key.
- **Does a `form` that implies a payload size deserve a Python check?** (2026-08-05,
  deliberately deferred at n=1.) `form: narrated_drama` with a 2-item payload produced M81
  and nothing noticed. The deletion of `scale` makes item count the only dial, which may
  be enough on its own. If Anna under-loads a commissioned drama a **second** time, that
  is the reproduced pattern and it earns the mechanism — the shape would be a coherence
  law like KF-3's (pick the form, then the payload must match it), not a quota.
- **`--mark-seen` and `--produced-cold` disagree about what a word is** (2026-08-05, hit
  at close). `--produced-cold` resolves through the phonetic index; `--mark-seen` does a
  plain `if key in lexicon` dict lookup, so it accepts ONLY the canonical Tamil key. At
  the 08-05 close `vandhutten` — the exact phonetic stored on வந்துட்டேன் — was rejected
  by one flag and would have been accepted by the other, in the same command. Both refuse
  loudly, which is why it cost a retry rather than a wrong write; but Anna writes the
  close in phonetic by the surface-split law, so the flag that rejects phonetics is the
  one he will reach for wrong every time. Cheap fix: route `--mark-seen` through the same
  resolver, or have its error name the canonical key it wanted.
- **A travel day with no session reads as a fade** (2026-08-09, raised two days before
  departure and deliberately scoped out in the same breath — "I don't wanna implement a
  feature there"). Flying to India costs a day or two where the lesson probably won't
  happen. Silence is data in this system: the gap feeds decay, the deck's staleness term,
  and `recent_ask_counts`, so a travel day is currently indistinguishable from a day he
  ducked — the same absence-is-a-signal shape as the dead-reply entry above, but with a
  known, bounded, *scheduled* cause. **Deliberately not built**, and the argument against
  is real: the fade is honest, decay does not care why the rep was missed, and a "travel
  exemption" is a pedagogy change dressed as plumbing. What would earn it is evidence
  after the fact — if the post-trip state shows the deck or the cohort visibly mis-steered
  by the travel gap rather than merely dented, that is the reproduced pattern. Look at it
  post-trip with the session log in hand, not before.
- **The promoted axis has no history** (2026-08-17, found while re-judging the ear wave against
  the written position). `sync_state.py:810-811` stamps `floor_pct` and `engines_pct` onto every
  session row — both production meters, one of them now demoted. Nothing stamps the ear. So
  `Machines heard` leads the scoreboard with **no longitudinal record at all**, and in a month
  there is no way to answer "did it move?" — the one question the constitution's *Ground
  Covered, Not Ground Remaining* law actually needs answered. This is not recoverable after the
  fact: `lexicon.json` carries only today's recognition level, so every day that passes without
  the field is a day of the headline axis permanently unrecorded. Cheap fix: one line,
  `entry["ears_pct"]`, beside the two already there; `smoke/state.py`'s `s42_session_log_one_row_per_day` asserts the row's
  shape and would extend in the same diff. **Held at Gate 2** — schema change to Python-owned
  JSON — not built. The larger question underneath: the session row is the only distance-covered
  record this system keeps, and nothing reads it back to Andrew. `show_status.py:129` prints
  floor% per session into a dashboard he doesn't open, while the numbers that would answer "no
  further than we were" are real and good (engines 26%→90.5%, floor 15.3%→26.2%, 75 cold fires,
  4 demotions across 30 sessions). The law says name ground covered; nothing yet does it from
  the record rather than from Anna's memory of the last session.
- **A per-item pending-ask state, consulted by every writer** (2026-08-18, scoped out of the
  cooldown fix in the same breath). The 08-18 change widens the window and puts ALREADY ASKED in
  front of Anna, but it stays **advisory** on the three lanes that are prose: the soak order, the
  campaign mission and the slip medicine are Anna's sentences, and Python has no choke point on
  them the way the selector demotes a recently-asked row. KF-13's law — say it in the mandate AND cap the
  blast radius in Python — is only half-satisfiable today. The complete answer is an explicit
  per-item state (`asked_at` / `answered_at`, or a derived `pending` view) that `sync_state`
  checks when `--soak-payload` or a campaign line names an item with an unanswered ask
  outstanding, and refuses or warns loudly. **Held at Gate 2** — that is a schema change, and the
  incident that would justify it has now happened exactly once. If a second item reaches three-plus
  surfaces while ALREADY ASKED is on screen, that is the reproduced pattern and it earns the
  mechanism; until then the cheaper guard may well be enough.

- **THE DRILL LANE HAS NO TEACH-FIRST FILTER** (2026-08-18, found while exercising the lanes
  after the deck retirement — **pre-existing, not caused by it**; `git show HEAD~1` confirms
  the old `deck_due_payload` had no filter either). The teach-first law says an UNSEEN item
  (`is_unseen`: never soaked, never surfaced) may be TAUGHT but never cold-quizzed. The knock
  menu marks them and `volley_targets` **excludes** them outright. `render_drill.due_payload`
  does neither: today's real top-8 carried `அதுக்கு அப்புறம்`, UNSEEN, into a tape whose whole
  structure is *English cue → silence → he must say it*. **Why it may not be a defect:** the
  drill hands him the answer twice immediately after the silence, so it is teach-and-test, not
  a bare quiz — measurably different from a volley, where a miss is just a miss. That is a
  pedagogy call, not a plumbing one, so it is filed rather than fixed. **If it should change**,
  the fix is one line in `due_payload` (skip `t["unseen"]`, the flag already rides on every
  `drill_menu` row) plus a case in `s48`; the argument against is that a guaranteed-miss
  followed by the answer twice may be exactly how an unseen item *should* enter the mouth.
  Worth one question to Andrew before either.


## Shipped

- ~~The ear meter reports ignorance as failure~~ — SHIPPED 2026-08-31.
  `compute_machines` returns `tested` beside `heard`; the scoreboard reads `Machines heard 3 ·
  ear-tested 4/26` and the brief names the 22 blanks out loud. 22 of 26 machines carried no
  `heard_on`, so the PRIMARY STEER had been frozen since 08-01 on rows nothing ever asked; of
  the four tested, three were heard. Andrew found it from the armchair — *"how can I say things
  I don't recognize?"* — which is the shape of a meter nobody could falsify. It is the 07-25
  "honest meters must show both" law reaching the ear lane, not a new one. `s60` gained a
  tested-and-missed row; collapsing `tested` onto `heard` turns it red. `engines_pct` was
  proposed for retirement and KEPT — 21/21 is a finished axis, not a dead meter. DECISIONS
  carries the conclusion; production's missing evidence standard stays open.

- ~~NEVER COMMISSIONED can only be cleared by FAILING again~~ — SHIPPED 2026-07-31
  (`update --slip-commissioned TAG`, Andrew's choice of three shapes), hard gate added
  2026-08-01. The flag meant "he has never slipped this while some unrelated order stood",
  so commissioning the right dose could not clear it and only slipping again could — a
  warning dischargeable by failing and ignored by fixing, which is the mechanical reason it
  got walked past. The close now declares which debt its order pays. The wiring turned up a
  worse one: `write_thin_learner` is a whitelist that omitted `slip_closes`, so no slip had
  actually closed since 2026-07-30 and a wiped close looked exactly like never testing.
  Smoke `s44`, `s46`. Full diagnosis in git.

- ~~`inline_canon()` follows references one level deep only~~ — DONE 2026-08-18. Filed
  07-27 as latent, went live the day `agy` stopped being installed and `openrouter_pass`
  became the only writer running anywhere. The walk never recursed, so `constitution.md`
  reached no pass; and the pattern matched `protocol/*.md` only, so the Director's
  "Calibration Notes are LAW" pointed at a `progress/` file it could not carry. Now
  transitive at `CANON_DEPTH = 2`, deduped, `lexicon.json` skipped loudly, anything
  referenced-but-not-carried printed. ~22k → ~83k input tokens per episode.

- ~~A pure state correction inflates the session count~~ and ~~`--debrief` alone counts as
  a session~~ — BOTH CLOSED 2026-08-26 on verification, by the same-day-merge fix that
  shipped 2026-07-31. `sync_state.py`'s session-log write unions into today's row instead
  of appending, so neither a correction nor a debrief-only call can mint a session. **One
  bug held three inbox seats for four weeks** (these two plus the second half of the
  `--teach` entry, still under Ideas), and only one was ever marked — the filing failure,
  not the code, is what these closures are evidence of. Neither proposed flag
  (`--correction`, `--bookkeeping`) was built or is needed.

- ~~Payload lint could match inflected stems~~ — DONE 2026-08-18, after the same failure
  rejected a correct episode twice (script தூக்கறேன், sidecar தூக்கு). The rule is now the
  distinction the lexicon already drew: chunks verbatim, plain words on their stem. The
  2026-07-13 "bends the sidecar" repair still stands for chunks and is annotated there.

- ~~Post-trip: reseed the focus cohort~~ — DONE 2026-08-18 with the deck retirement. The
  08-01 audit found the cohort stale (7/12 never worked, zero graduations); the retirement
  made it worse first, because the tier bar moved onto the rows while all twelve seats were
  held by unregistered words. `sync_state reseed-focus` re-derives membership from the
  pool's current order and was run once — 4/12 seats now carry a register. Correction to the
  08-01 note: சொல்லுங்க was evicted by the re-derivation, not the graduation sweep. Nothing
  owed; the command is the standing mechanism for the next time an ordering changes under a
  stored cohort.


- ~~THE REPAIR EARNS THE DOSE — audio commissioned off his errors~~ — SHIPPED 2026-07-28
  (same session as the `/recalibrate` pass that found it; Andrew: *"I agree with your
  diagnosis and want to fix this now"*). The commissioning law now lives in
  `protocol/audio_channels.md` → "What it carries", split there rather than bumping
  `daily_session.md`'s budget; Close & Log step 2 fires it and points at it. Repairs
  outrank the forward seed order, a survived collision earns its own order, and
  `MAX_UNATTENDED_PER_DAY` went 1 → 3 (Andrew: *"guardrails to a problem that was
  temporary"*). Smoke case s37 is the regression net. The queue-of-one fix stayed
  deliberately unbundled — see the item under Ideas. DECISIONS 2026-07-28 entries.

- ~~The declared-events ledger build~~ — SHIPPED 2026-07-26 (dedicated @build session,
  same day as the design): judge-seam rep increments + `rep_counts` reads declared
  counters only; delivery-seam exposure stamps (`sync_state.mark_exposed`) at episode
  registration, soak, drill, knock push and the queue drain; `-soaked` flipped to a
  least-exposed term in `coverage_key`; focus cohort stored in `learner.json`
  (reconciled at the two graduation seams); reps backfilled from judged replies
  (Andrew's yes — 49 reps / 26 words); s32/s33/s34 rewired to the real seams;
  `pairs_with` split now refuses the whole seed. See DECISIONS 2026-07-26 entries.

- ~~`suggest_targets.py` has zero smoke coverage~~ — SHIPPED 2026-07-19 (wrap-up
  session): smoke case s23 plants the proven crash class (a `special_*` string-mission
  sidecar) and runs the full ticket end-to-end on day-zero state.
- ~~Registration canonical-at-write~~ — SHIPPED 2026-07-17 same evening (Andrew's
  token-discretion grant): `claim_payload()` in `run_studio.py`; corrected diagnosis
  and full record in DECISIONS ("The sidecar must claim the soak payload"). Dupes
  merged; M65/M67 stamps repaired.
- ~~Fixed-time anchor push~~ — MOOT, closed by the 2026-07-17 review on the deferral's own
  test: Anna fires volleys reliably unforced (07-14 15:13, 07-15 15:46, 07-17 13:07 EDT —
  the afternoon slot the 07-13 lunch-anchor decision assigned). No Python-forced anchor;
  "outreach policy is Anna's" stands untouched.
- ~~`frame:idum` has no lexicon record~~ — RESOLVED by 2026-07-17 review: a full record
  exists (new engine record, not folded into done-ittu — gloss even names the boundary:
  "bolts onto a clean single verb, not a compound"). The 07-13 cold fire (`book
  pannidum`) that was skipped for want of a record was applied during the review.

- ~~Explicit contrast beat~~ — DONE 2026-07-08 (same-day canon amendment, Andrew approved):
  a recast may carry ONE clause of why, by example, never terminology — one clause is a
  beat, two is a lecture. Canonical in `constitution.md` → The Contrast Beat; echoed in
  persona/daily_session/judge mandate.
- ~~Per-word verdicts in the reply judge~~ — DONE 2026-07-03 (same day it was found —
  Andrew approved building it): the judge grades each fired word on its own
  (`fired: [{word, verdict}]`), Python derives the reply's overall verdict as the best
  word, the revealed-cap stays deterministic per word, and the burn rate reads the new
  `reply_fired_cold` (legacy entries fall back to the old flat count). Evidence that
  motivated it: 2026-07-02 19:18, three deck items fired in one reply, all flattened to
  the single "hinted".
- ~~Day-zero ticket guard~~ — DONE 2026-07-03: `suggest_targets.py` (and `generate_callbacks.py`) now treat an *empty* lexicon as valid day-zero state; only a missing file errors. A fresh learner gets a real first-session ticket.
- ~~Knock digest could carry the ticket's deck top~~ — DONE 2026-07-02: `build_digest()` appends the deck-due menu (fire + ear-only), and the mandate points `expected_target` at it.
- **Meter the audio lane by outcome, not attendance** — proposed 2026-08-27, replacing the
  retired `listens` counter (`DECISIONS.md`). The lane's job is recognition, so measure
  recognition: for words whose ONLY exposure was a single episode, what state did they reach?
  Computable today from `seen_in` + lexicon state — no new field, no phone, no third party.
  First cut, 2026-08-27: 117 solo-exposure words, 95 still `struggled/none`, 19 reached any
  production, 6 reached comfortable-or-solid. **That number is a FLOOR, not an average** —
  solo-exposure words are by construction the least-reinforced items in the system — and it
  means nothing until it runs against a chat-exposed control cohort at comparable exposure
  counts. Build the control first; a bare 16% invites the same misreading `listens` just cost us.
- ~~**RETIRE `studio_watchdog.py` — the cron is stale**~~ — **DONE 2026-08-27** (Andrew: *"the crontab is
  stale, should be retired"*). It installs as a crontab on the Linux box (`$HOME/projects/Tamil`,
  gnome-keyring `SSH_AUTH_SOCK`, `17 * * * *`) and is not live on any machine we can see. Its job
  — notice work the studio left undone and run the existing dispatch — is covered by the
  session-open auto-drain, which `session_brief` prints and which fires where Andrew actually is.
  **Not urgent any more:** its correctness hazard was `soak_pending()` being registry-only, and
  that is fixed and guarded by `s80` (2026-08-27), so a revived cron would now behave. This is
  cleanup, not a repair.
  **The surface, measured — roughly a dozen sites, several load-bearing:**
  `scripts/studio_watchdog.py` itself; comments in `render_audio.py`, `run_studio.py`,
  `state_io.py`; `smoke/render.py` **`s19_watchdog_detection`** (whole case — its
  `scripted_unrendered()` half dies with it, its `soak_pending()` half is worth re-homing, and
  `s80` already covers the resolver); `smoke/publish.py` **`s25`**'s three `sw.outcome()`
  assertions (watchdog retry semantics — they die with it); `smoke/knock.py` imports it and
  asserts it calls the shared resolver rather than growing its own copy; `smoke/ratchets.py`
  `CODE_BUDGETS` (125) and `LAYERS` (6); `docs/PROTOCOL_MAP.md`, `docs/DECISIONS.md`,
  `docs/feature_inbox.md`; `.claude/skills/{anna,backport}/SKILL.md` and
  `verify/references/flags.md`.
  **What dies with it and needs a decision, not a delete:** `MAX_UNATTENDED_PER_DAY = 3` and
  `produced_today()` — the rail bounding unattended production. Two inbox entries below name
  `MAX_UNATTENDED_PER_DAY` as the guardrail for a *proposed* knock-tick episode move; retiring
  the watchdog strands that rail, and the proposal would have to bring its own. Decide where the
  cap lives before deleting the file, or the next unattended lane is built with no ceiling —
  which is the 2026-07-23 three-episodes-in-one-evening shape, and the reason the cap exists.
  **DONE:** file deleted; `s19` and `s25`'s three retry assertions died with it; `s27`'s cap
  assertions became the no-unattended-dispatcher invariant; budget, layer, PROTOCOL_MAP and
  three skill files repointed. The cap was NOT re-homed — nothing fires production
  unattended any more, so there is nothing to bound; both proposals above now say so.

- **`schedule` is dropped on the agent path** (2026-08-28). `obj()` makes every key it
  names REQUIRED and has no nullable, so `JUDGE_SCHEMA` omits `schedule` on purpose — but
  `claude -p --json-schema` drops undeclared keys, so a clock-bound request judged locally
  can never queue a push. `voice_reply` had the same defect and was fixed by declaring it
  (it is legitimately always-present, empty string when unused); `schedule` cannot be,
  because "no schedule" must stay distinguishable from "an empty schedule". Wants either a
  nullable form in `obj()` (`{"anyOf": [{...}, {"type": "null"}]}`) or a sentinel shape
  with an `at_local: ""` meaning none. Evidence: the last scheduled knock is 2026-08-19,
  and it came through the cloud/API path where undeclared keys survive.
