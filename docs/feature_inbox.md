# Feature Inbox

Two lists, one line per idea, newest first; the reasoning is the commit, never the
line (compressed 2026-09-10 from 19k words). An idea that ships gets a `DECISIONS.md`
line and leaves; one that dies is deleted, not archived.

- **Inbox** — filed and not yet ruled. Every line here gets a disposition at the next
  drain; an unscoped `/inbox` drains this list and only this list.
- **Backlog** — ruled DEFERRED (the line says why and until when), or filed before the
  drain existed (2026-10-14) and never triaged. It drains only when Andrew names it.

## Inbox
- GLOSSES DROPPED AT INTAKE — Rows are born from episode scripts with their meanings lost: 59 of 422 lexicon rows carry a blank gloss, in whole-episode batches (E70-74, E78, E81, E97, E98). Today's case: senjom, vaanginom and iruppom entered from Ep 98 unglossed, untaught (taught_on null) and untested, then carried a session as its sharpening pattern. A row born without a gloss should park loudly, the way malformed commissions park in failed/; minimum fix: backfill Ep 98's three from the script that birthed them. Fix-class — lands when drained, no boundary needed. (2026-10-20, Rio — coach filing, NOT built)
- CANDIDATE GATE FOR "IN PLAY" — 238 of 422 rows were never taught; 118 of those have already appeared in episodes, and nothing stops an untaught word being listed as in play, tested, or used as assumed material. His words, mid-lesson 2026-10-20: he feels "tested on something that was never explained." Proposal: script appearance creates a candidate; only a teaching event (taught_on) makes it a player; the candidate count shows in the books. The boundary owns the 118-row backlog's disposition — coach recommendation: drain by ear over time, not by mass lessons. Feature-class: for the Oct 31 cut. (2026-10-20, Rio — coach filing, NOT built)
- TRIAGE THE BACKLOG — backlog lines with no DEFERRED mark predate the drain and never had a disposition; many look superseded (deck, volley, trip, post-trip arc). (2026-10-19, Andrew)

## Backlog

- Finale escalation order — difficulty rises one axis per room transition: voices, then speed, then reduction and support-removal. The rest shipped. (2026-10-19, Rio) DEFERRED (2026-10-19, Andrew): decided with the rooms item at the November cut.
- A density band, not clamps — one stated band (Tamil share; new items per episode) in profile.md Calibration, checked on the sidecar; reopens its "Density is an OUTPUT, never a target" on the 10-15 "too dense" → 10-16 "mostly English" swing. (2026-10-19, Andrew) DEFERRED (2026-10-19, Andrew): goes to its own /recalibrate session.
- Coverage sets the vocabulary queue — a corpus of the real domain's speech; recognition coverage against it (~95% of tokens) ranks the intake queue. Filed in c211a92. (2026-10-19, Rio) DEFERRED (2026-10-19, Andrew): no corpus exists yet; revisit at a month cut once harvests or media supply one.
- The year is a sequence of rooms — situation-rooms (voices, speed, support, his role: follow → react → join) replace the lean as the year's spine; reopens 10-08/10-09. Filed in c211a92. (2026-10-19, Rio) DEFERRED (2026-10-19, Andrew): decide at the November cut, on October's finale.
- Anna picks the shelf's turn — `shelf.py` takes turns by recency; the tick already calls a model to write the tape, so the same call can choose rotation spine / soak / drill by judgement and his ratings (2026-10-15, Andrew, NOT built) awaiting Andrew (2026-10-20): a model choosing the turn is a selection-policy change; explore first
- Shape-escalation inside rotation — an order can name rotation but not which shape, so escalation there needs a `spine` field on the order; reopens 09-29 (2026-10-12, from the repair-dose rerouting, NOT built) DEFERRED (2026-10-20): 37d06bf lets a repair name rotation; revisit when a repair needs a non-default spine
- Populate or retire `pairs_with` — 1 of 362 rows, but four readers print "he answers: …" off it; the hear-her-line/produce-the-refusal pair is a real unit starved of data (2026-09-13, from the sparse-field review, NOT built) awaiting Andrew (2026-10-20): still 1 of 427 rows; recommend retiring the field and its four readers
- Denominator floor in `suggest_targets.new_candidates_by_cluster` — `body` at 0/2 outranks `verb_root` at 3/49; a Laplace prior or minimum denominator (2026-09-04, from the curriculum expansion review, NOT built) DEFERRED (2026-10-20): rides the word_pool upsert, which waits on the coverage-queue ruling
- A `(word, cluster)` uniqueness ratchet on `curriculum/word_pool.json` in `scripts/smoke/` — the §7.1 validator died with its session (2026-09-04, NOT built) DEFERRED (2026-10-20): rides the word_pool upsert, which waits on the coverage-queue ruling
- `_api_text` HAS NO TRUNCATION GUARD, and the failure is silent (2026-09-07). awaiting Andrew (2026-10-20): still latent; ship-and-say-TRUNCATED vs raise is his call
- THE BENCHMARK TAPE — felt progress without a meter (2026-08-25) DEFERRED (2026-10-20): needs a real-speech clip; revisit with the coverage corpus
- RE-RENDER THE ANDREW INTRO AT v8 — next laptop session (2026-07-31) DEFERRED (2026-10-20): waits on an Oracle sitting
- THE TTS OVER-ARTICULATES — a corpus-wide finding wearing a demo's clothes (2026-07-31) DEFERRED (2026-10-20): the A/B waits on an Oracle sitting
- ORACLE CROSS-POLLINATION — the intro script is a pipeline, not a demo (2026-07-31) DEFERRED (2026-10-20): waits on an Oracle sitting
- AT THE COMPUTER: finish the Andrew-intro naturalness pass — it is blocked on the Oracle, not on work (2026-07-30). DEFERRED (2026-10-20): her seven rulings first, then the v8 render
- A word-adjacent hyphen becomes a SPACE before TTS, so every Tamil suffix written with a hyphen reaches the voice as its own word (2026-07-30, found while reviewing the Andrew intro; … DEFERRED (2026-10-20): latent; revisit on a heard detached suffix
- For a `frame:` payload the episode lane SELF-CERTIFIES delivery without evidence (sighted 2026-07-28, first real exercise of the repair-first law). DEFERRED (2026-10-20): still self-certifies (run_studio.py:703); revisit on a sighting
- Upsert `word_pool.json` into the lexicon, then retire the file (2026-07-26, Andrew's call — supersedes the assistant's "just delete it"). DEFERRED (2026-10-20): decide with the coverage queue at a month cut
- Real-media library (songs, kids' TV)
- Tamil script is banned from TEXT bodies — needs a lint, not prose (2026-08-02)
- Commissioning from the phone — `schedule episode` (2026-08-02)
- Fielding has no cadence gate, and it is a sole-owner channel (2026-07-27)
- Pre-registering the chat rep's target (2026-07-27)
- The post-trip arc — three proposals, none chosen (2026-07-27)
- Volley chained recasts can double the re-presented ask (2026-07-27)
- A word taught in-session cannot enter the lexicon (2026-07-28)
- The deck coverage meter counts delivery, not engagement (2026-08-04)
- Episodes run at a fifth of their own spec (2026-08-05)
- A lexicon key containing a comma can never be commissioned into a soak payload (2026-08-05)
- Does a `form` that implies a payload size deserve a Python check? (2026-08-05)
- `--mark-seen` and `--produced-cold` disagree about what a word is (2026-08-05)
- A travel day with no session reads as a fade (2026-08-09)
- The promoted axis has no history (2026-08-17)
- A per-item pending-ask state, consulted by every writer (2026-08-18)
- THE DRILL LANE HAS NO TEACH-FIRST FILTER (2026-08-18)
- The model contract is written twice — half fixed (`writer.nullable`), half withdrawn; a static key-declared check CONSIDERED AND DECLINED (2026-09-05)
- No meter counts knock FORMAT share — the trailer monoculture (33% of fires) was invisible until counted by hand (2026-09-16)
- The slip ledger has no eviction rule — an unclosed slip family wins more lanes the longer it fails, and held all three at once (2026-09-16)
- `mandates.py` is at 500/500 code lines and 1992/2000 words — the next addition is a red build; split-or-retire (2026-09-16)
- The episode publish commit leaves the beat (content/household.md) and the exposure events (observations.json, learner.json) uncommitted — M98 needed a hand commit; cloud lanes never see them otherwise (2026-10-16)
