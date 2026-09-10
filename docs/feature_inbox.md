# Feature Inbox

One line per idea, newest first: what it is, when it was raised, and its status where
it has one (SHIPPED / WITHDRAWN / DEFERRED / NOT built). The reasoning is the commit of
that date — this file used to carry it, 19k words of it, and nobody read past the
titles (compressed 2026-09-10). An idea that ships gets a `DECISIONS.md` line and
leaves; an idea that dies is deleted, not archived.

## Ideas

- Denominator floor in `suggest_targets.new_candidates_by_cluster` — `body` at 0/2 outranks `verb_root` at 3/49; a Laplace prior or minimum denominator (2026-09-04, from the curriculum expansion review, NOT built)
- A `(word, cluster)` uniqueness ratchet on `curriculum/word_pool.json` in `scripts/smoke/` — the §7.1 validator died with its session (2026-09-04, NOT built)
- Tactical Rule 8, the dative pair (*naan kaapi kudikiren* vs *enakku kaapi venum*) — in the constitution's idiom, awaiting Andrew's wording (2026-09-04)
- A clitic drill contract for `daily_session.md` — a clitic is a bound operator, not a flashcard (2026-09-04, awaiting a standalone proposal)
- `LINT_MANDATE` extension for verb paradigms — the real form of the rejected `VERB_PARADIGMS` table (2026-09-04, if still wanted)
- PERSIST THE JUDGE'S HEARD LIST — the ear's best evidence is never written down (2026-09-10).
- SPLIT `scripts/writer.py` — the ceiling has now been asked twice, unpaid (2026-09-07).
- `_api_text` HAS NO TRUNCATION GUARD, and the failure is silent (2026-09-07).
- MULTI-TARGET EAVESDROP SCORING — proposed and WITHDRAWN in the same session (2026-08-31), because the obvious version manufactures the exact rows the 08-24 purge had just deleted.
- A THIRD-PARTY NAME GUARD ON THE PHONE-RECORD LANE — and the reason the obvious version cannot be built (2026-08-30)
- DO NOT MAKE `resolve()` FUZZY — measured 2026-08-26, and the answer is no.
- THREE READERS, THREE DIFFERENT IDEAS OF WHAT AN EPISODE TITLE IS (2026-08-26)
- THREE STATE ROWS EXIST ONLY ON DELETED BRANCHES — a backfill decision, not a bug (2026-08-26)
- ⏳ THE WINDOW IS STILL OPEN — READ THIS BEFORE THE OTHER EAVESDROP ENTRIES
- HARVEST REAL EAVESDROP AUDIO WHILE THE SUPPLY AND THE RULING AUTHORITY ARE IN THE SAME ROOM (2026-08-13)
- THE TICKET NAMES TARGETS THE LOGGER WON'T ACCEPT — 84 floor-gap words are still unreachable from the surface Anna writes in
- `PROSE_BUDGETS` HAS NO COMPLETENESS GUARD — `CODE_BUDGETS` DOES (2026-08-26)
- `docs/` IS THE SURFACE WITH NO CEILING (2026-08-26)
- THE BUDGET THAT MATTERS IS THE SUM AT THE LOAD POINT (2026-08-26)
- MAP FRESHNESS COULD BE COMPUTED INSTEAD OF REMEMBERED (2026-08-26)
- A GUARANTEE-VOCABULARY LINT FOR OUR OWN PROSE (2026-08-26)
- THE BENCHMARK TAPE — felt progress without a meter (2026-08-25)
- CAPTURE THE ROOM — spike first, and it may not survive the spike (2026-08-26)
- THE KNOCK LANE MEASURES THE AXIS THAT IS NO LONGER THE GOAL (2026-08-25)
- `docs/DECISIONS.md` IS 30,000 WORDS AND EVERY CHANGE READS IT (2026-08-25)
- THE AUTO-DRAIN'S FALLBACK RULE IS ONE PIPE AWAY FROM BEING DEAD (2026-08-14)
- THE REPLY PATH CAN DIE AND THE SYSTEM READS IT AS "HE DIDN'T ANSWER" (2026-07-31)
- RE-RENDER THE ANDREW INTRO AT v8 — next laptop session (2026-07-31)
- THE TTS OVER-ARTICULATES — a corpus-wide finding wearing a demo's clothes (2026-07-31)
- THE STACCATO IS OURS, NOT THE MODEL'S — why the Tamil reads "composed" (2026-07-31)
- TESTS WITHOUT TEETH — a cursory audit, 2026-07-31
- A VOLLEY WHOSE NOTIFICATION IS LOST IS STRANDED BY DESIGN (2026-07-31)
- ORACLE CROSS-POLLINATION — the intro script is a pipeline, not a demo (2026-07-31)
- AT THE COMPUTER: finish the Andrew-intro naturalness pass — it is blocked on the Oracle, not on work (2026-07-30).
- A word-adjacent hyphen becomes a SPACE before TTS, so every Tamil suffix written with a hyphen reaches the voice as its own word (2026-07-30, found while reviewing the Andrew intro; …
- For a `frame:` payload the episode lane SELF-CERTIFIES delivery without evidence (sighted 2026-07-28, first real exercise of the repair-first law).
- Audio is a queue-of-one — give it a real queue (2026-07-28, deliberately NOT bundled with the repair-first commissioning law that shipped the same day).
- Scheduled/unattended episode production — DEFERRED 2026-07-27 by Andrew after exploring it.
- Upsert `word_pool.json` into the lexicon, then retire the file (2026-07-26, Andrew's call — supersedes the assistant's "just delete it").
- CURRICULUM ARCHITECTURE AUDIT (2026-07-26, `/recalibrate`, Andrew's felt signal: "the curriculum/deck/machinery/catch-response layers grew by iteration and discovery, not top-down design — make the abstraction clean, and don't let the deck starve …
- BUILD (decided 2026-07-24): autonomous cloud episode production, inside the knock tick.
- The trip harvest (2026-07-18)
- Daily spoken reps
- Cold decay / re-test dates
- Voice loop (speech-IN half)
- Pull the wife in as the north star
- Drill as a knock modality
- Single deployment ladder per item
- Concurrent drains could double-fire one queue entry
- Published feed titles could still be mutated by any writer
- Phantom-fired knock on delivery failure (2026-07-14)
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
