# Feature Inbox

Two lists, one line per idea, newest first. The reasoning is the commit of the
item's date, never the line (compressed 2026-09-10 from 19k words nobody read past
the titles). An idea that ships gets a `DECISIONS.md` line and leaves; an idea that
dies is deleted, not archived.

- **Inbox** — filed and not yet ruled. Every line here gets a disposition at the next
  drain; an unscoped `/inbox` drains this list and only this list.
- **Backlog** — ruled DEFERRED (the line says why and until when), or filed before the
  drain existed (2026-10-14) and never triaged. It drains only when Andrew names it.

## Inbox

- TRIAGE THE BACKLOG — the lines below `## Backlog` without a DEFERRED mark were filed before the drain existed and have never had a disposition; many look superseded (deck, volley, trip, the post-trip arc). One drain, one commit per line. (2026-10-19, Andrew)
- EVERY SEAT CARRIES A "YOU MAY NOT" — Negative charges, stated on the surface each agent actually reads. Anna (persona/brief): may not change the design — room, difficulty axes, targets, machinery — however the moment feels; design-shaped feedback is logged as boundary evidence (extends TWO SPEEDS OF CHANGE, filed today). Claude in build sessions (AGENTS.md playbook): may not originate design silently — a design idea arising mid-build is left in this inbox or in DECISIONS, where the coach pass can see it, never landed invisibly inside a fix. Rio the coach (charter, off-repo, stated here for symmetry): may not teach, may not write learner state, may not edit DECISIONS.md. Positive charges say what a seat is for; the negative charge is what stops a party of agents becoming a committee of generalists duplicating each other at lower quality. (2026-10-19, Rio — coach filing, NOT built)
- TWO SPEEDS OF CHANGE — Anna's discretion is wide inside the current room (selection, revisits, commissions) and zero outside it (room, difficulty axes, targets, machinery). Design-level changes are decided only at the month boundary, in one sitting, on the month's evidence: finale result, coverage delta, the month's feedback instances, the neglect picture. In-month feedback keeps its force but changes its timing — logged as boundary evidence, not executed as a same-day steer. Record as a DECISIONS line; implement the brief-side behaviour (Anna acknowledges and logs design feedback in-month; he does not re-steer). Andrew's steering cadence (~a day) is shorter than Anna's production loop, so under same-day steering no configuration survives long enough to be judged — the density pendulum is that mismatch, and it is structural, not tonal. (2026-10-19, Rio — coach filing, NOT built)
- PERSONS FICTIONAL, SITUATIONS REAL — Amend the household law: the cast stays fictional, always (the protection is real — real in-laws cannot be portrayed as funny, awkward and wrong), but arc situations are drawn from real life — the actual calendar, festivals, visits, Andrew's real projects, Coimbatore news — the household reacting to a world that exists outside the lesson. Each arc also plants two or three of Andrew's own lines or decisions early and pays them off late (the Oct 15 deadpan line and its planned ambush, systematized): the fiction's continuity becomes partly his biography inside it, which is the stake a manufactured plot cannot supply. This exercises comprehension_plan.md's existing clause — retire the household's exclusivity where it forces contrived content. (2026-10-19, Rio — coach filing, NOT built)
- A "known — don't teach" lever — the 09-09 told/observed split left him no way to say "I already know this", so decade-old words come back as targets (10-12 venaam "announced as a win"; 10-15 soak "words I've learned already"). Proposed: a `known` claim that drops a row from teaching targets (ticket, soak payload, map's in-play) and never votes a rung; `sync_state.py known WORD`, said in chat. (2026-10-19, Andrew, NOT built)
- Stakes run across episodes, inside the arc — README's "no serialized saga, scenes are disposable" (June) and persona's masks "not a cast" still win against the household canon, the monthly arc and "threads left hanging"; he says "struggling with continuity" (09-17) and "the biryani stakes aren't very interesting" (10-16). Proposed: retire the README line and the "do not chain scenes" note in profile.md; let one live question (Paati's announcement) run episode to episode, while each episode stays self-contained enough to land alone. (2026-10-19, Andrew, NOT built)

## Backlog

- Finale escalation order — difficulty rises one axis per room transition: voices, then speed, then reduction and support-removal. The rest of the filing shipped 2026-10-19. (2026-10-19, Rio) DEFERRED (2026-10-19, Andrew): decided with the rooms item at the November cut.
- A density band, not clamps — one stated band (Tamil share; new items per episode) in profile.md Calibration, checked on the sidecar; reopens its "Density is an OUTPUT, never a target" on the 10-15 "too dense" → 10-16 "mostly English" swing. (2026-10-19, Andrew) DEFERRED (2026-10-19, Andrew): goes to its own /recalibrate session.
- Coverage sets the vocabulary queue — a corpus of the real domain's speech; recognition coverage against it (~95% of tokens) ranks the intake queue. Filed in c211a92. (2026-10-19, Rio) DEFERRED (2026-10-19, Andrew): no corpus exists yet; revisit at a month cut once harvests or media supply one.
- The year is a sequence of rooms — situation-rooms (voices, speed, support, his role: follow → react → join) replace the lean as the year's spine; reopens 10-08/10-09. Filed in c211a92. (2026-10-19, Rio) DEFERRED (2026-10-19, Andrew): decide at the November cut, on October's finale.
- Anna picks the shelf's turn — `shelf.py` takes turns by recency; the tick already calls a model to write the tape, so the same call can choose rotation spine / soak / drill by judgement and his ratings (2026-10-15, Andrew, NOT built)
- Shape-escalation inside rotation — an order can name rotation but not which shape, so escalation there needs a `spine` field on the order; reopens 09-29 (2026-10-12, from the repair-dose rerouting, NOT built)
- A scheduler for the catch lane — a time-bound ask in an eavesdrop reply is now logged MISSED SCHEDULE, but nothing can queue it (2026-10-12, NOT built)
- Populate or retire `pairs_with` — 1 of 362 rows, but four readers print "he answers: …" off it; the hear-her-line/produce-the-refusal pair is a real unit starved of data (2026-09-13, from the sparse-field review, NOT built)
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
- No meter counts knock FORMAT share — the trailer monoculture (33% of fires) was invisible until counted by hand (2026-09-16)
- The slip ledger has no eviction rule — an unclosed slip family wins more lanes the longer it fails, and held all three at once (2026-09-16)
- `mandates.py` is at 500/500 code lines and 1992/2000 words — the next addition is a red build; split-or-retire (2026-09-16)
- The episode publish commit leaves the beat (content/household.md) and the exposure events (observations.json, learner.json) uncommitted — M98 needed a hand commit; cloud lanes never see them otherwise (2026-10-16)
