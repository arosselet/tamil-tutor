# Feature Inbox

Two lists, one line per idea, newest first; the reasoning is the commit, never the
line (compressed 2026-09-10 from 19k words). An idea that ships gets a `DECISIONS.md`
line and leaves; one that dies is deleted, not archived.

- **Inbox** — filed and not yet ruled. Every line here gets a disposition at the next
  drain; an unscoped `/inbox` drains this list and only this list.
- **Backlog** — ruled DEFERRED (the line says why and until when), or filed before the
  drain existed (2026-10-14) and never triaged. It drains only when Andrew names it.

## Inbox

- What in this public repo is actually private? Profile, family and state are public now by choice ("security by obscurity, for the goodwill"). Raised when voice storage suggested a private repo. Not urgent: the voice spec avoids it. To rule on its own, not inside a feature. (2026-10-25, Andrew, NOT built)

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
- Real-media library (songs, kids' TV) DEFERRED (2026-10-20): revisit with the coverage corpus, which needs the same media supply
- Commissioning from the phone — `schedule episode` (2026-08-02) awaiting Andrew (2026-10-20): now cheap — the reply lane could drop a commission into pending/
- A lexicon key containing a comma can never be commissioned into a soak payload (2026-08-05) DEFERRED (2026-10-20): live (canon_payload splits); 3 keys, none ordered since 08-05
