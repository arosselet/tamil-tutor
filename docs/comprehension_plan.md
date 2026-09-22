# Tamil tutor target design — open proposal

> September 22, 2026. The destination is adopted; the design is partly implemented,
> with remaining proposals identified below. This replaces the old forecast, numerical checkpoints and duplicated
> habit prescriptions in this file. Historical reasoning remains in git.
> [ASTRA_REVIEW.md](ASTRA_REVIEW.md) holds the evidence; [DECISIONS.md](DECISIONS.md)
> remains the record of adopted decisions. This document is not a tutor load file.

## The outcome and the constraints

Andrew's primary objective is continued engagement and enjoyment of learning Tamil,
toward a tentative family visit in 2027. The adopted language goal is to follow
ordinary family-table sentences about food, plans, visitors, health and the day,
and join in. August is a planning anchor, not a confirmed booking or promised level.

A successful system makes worthwhile contact easy to return to and makes unfamiliar
speech increasingly understandable. Correct exercises, produced minutes and green
tests establish narrower things. Neither enjoyment nor competence substitutes for
the other. Evidence is too sparse to forecast a learning rate.

Keep the agreed learner commitments in [learner_contract.md](../protocol/learner_contract.md):
a short session and separate ear block, with no makeup, streaks or additional reporting
duties. Engineering efficiency is our constraint, not Andrew's homework.
The broad commission permits reconsidering any design; specific proposals below
explicitly reopen earlier decisions rather than silently changing their authority.

## Recommendation: one tutor, dependable services, fewer competing agendas

Keep Anna as the prepared, persistent teaching partner. Preserve deterministic
evidence, safe publication, scheduled supply and the specialist studio. Simplify what
chooses the lesson: current curiosity, useful family situations and observed obstacles
should guide it. Inventory and scheduling should expose omissions and offer options,
not turn each encounter into a queue to discharge.

This is a redistribution of responsibility, not a claim that deleting files teaches
Tamil. The tutor must still introduce material, explain it and revisit it; unrestricted
improvisation could conceal six pleasant weeks of stagnation.

| Responsibility | Target owner | What changes |
|---|---|---|
| What is worth understanding now | Tutor, using Andrew's interests and a small set of useful situations | Replace competing repair, calendar and production agendas with an explicit choice. |
| Curriculum continuity | Existing profile, debrief and inventory | Keep one current thread and selected revisits; inspect neglect without another deck or completion meter. |
| What happened | Observation ledger and actual replies | Preserve provenance; derive auditory claims from auditory evidence. |
| Speech and replay | Existing memo, studio, rendering and feed services | Make short lesson audio accessible alongside standing tapes. |
| Between-session contact | Existing phone channel and rails | Supply worthwhile contact; replies optional, questions interrupt exercises. |
| Adaptation | Tutor plus occasional engineering review | Change when experience warrants it; do not diagnose silence from counters alone. |

## What Andrew should experience

A session begins with something worth receiving: a connection, language story,
small scene or explanation. The tutor brings this; Andrew need not request interest
or earn it through a check. A grammar observation alone is not automatically the
coffee-and-lore experience he praised.

Teaching follows something worth understanding. A short spoken exchange can establish
the situation, then an explanation removes the blocking meaning, and another hearing
lets the sentence settle. A changed example reveals what travels. Text is useful
support and sometimes the entire lesson, honestly labelled. Not every session needs
this sequence, and curiosity may justify staying with one explanation.

The question should serve meaning: why someone cannot leave, which plan changed,
what a speaker wants. Translation and noun substitution remain useful teaching moves;
several correct substitutions do not demonstrate listening or delayed learning.
Production joins naturally through a reply, question, joke or rehearsal. No quota.

An interruption such as “teach me that ending” becomes the conversation. The tutor
does not append the unanswered quiz as a reminder. It can return to the earlier
exchange once the explanation has done its job.

At a natural ending, Anna names what became clearer and selects a specific replay
for later, with a working link. Saving happens in a prepared close operation.
A real permission or sync failure must remain visible, but routine bookkeeping
should not consume several tutor turns. The September 21 session exposed that
host integration problem; it does not prove every existing client has it.

A quiet week still has useful audio available and welcome no-ask contact. Returning
requires neither a backlog nor a recap. Family contact and missions stay invitations,
never compulsory evidence collection.

## Curriculum: a worked experience, then direction

[A week worth returning to](learning_week.md) makes the design concrete: a gift,
a situation that changes, curiosity that can take over, a delayed changed hearing,
selected replay and a welcoming return after a gap. It replaces the abstract curriculum
discussion here. It is a design specimen, not a script, schedule or new tutor load file.
Existing debrief and inventory carry continuity; no extra learner reporting is proposed.

The register ladder is useful planning context: children, peers and elders offer
different forms and interaction demands. A calendar cannot establish readiness.
Propose making the direction a preference and withdrawing the automatic zero-intake
taper, including during the visit. Useful new material can still matter near departure;
retention and speed deserve more attention then without a universal prohibition.
This reopens the September 19 ladder/taper decisions. It adds no replacement cutoff.

The year module's voice counts and situation support are currently printed planning
values; the consumer search found no renderer enforcement. Do not describe the
calendar as an implemented listening progression. Adjust length, familiarity,
speaker variation and support in response to actual understanding, one difficulty
at a time when diagnosing a problem.

## Audio: preserve supply, connect it to teaching

Keep standing rotation supply independent of chat attendance. Preserve the separate
episode, soak and drill capabilities: July's evidence shows that their different
attention demands matter. Andrew should receive a useful selection, not manage lanes.

Reuse an appropriate artifact before rendering more. A render is supply, a rating is
a report about listening, and an answer to speech is comprehension evidence. Keep
those separate. Replays can signal usefulness alongside testimony; they do not prove
enjoyment, and one play does not establish dislike.

For short lesson audio, `lesson_audio.py` now integrates `memo.render_memo` and the
publication path. It avoids a second TTS backend or sending every two-line exchange
through the three-pass studio. The CLI is shipped; client playback and a complete
interactive encounter remain unverified. A narrator can present a short exchange;
distinctive cast voices remain the studio's job.

The integration must provide a reachable clip before presenting its translation,
retain the script for explanation, and support replay plus a changed clip. Keep the
learner-facing transcript phonetic. Test actual playback on the chosen client;
a generated MP3 or a Markdown link alone does not prove a workable lesson.
Occasional willing native feedback can check pronunciation and naturalness; until
then, those remain uncertain. Ordinary lessons can use imperfect model-generated
Tamil. Andrew and his family owe no review work, and reviewer access is not a gate.
No forced march to unsupported native media: short, well-supported material can
supplement the authored supply when it is interesting and usable.

## Keep, change, retire

| Component | Recommendation and reason |
|---|---|
| Persona, coffee, decomposition, finite sessions | Keep: repeated direct preference evidence. Judge delivery, not prompt compliance. |
| Household | Keep provisionally; retire its exclusivity if it forces contrived content. No replacement fictional world. |
| Studio and multiple audio forms | Keep: separation and capacity matching solved demonstrated problems. |
| Feed, scheduled supply, quiet hours, reply correlation | Keep: dependable availability and low-effort contact earned this infrastructure. |
| Word inventory, event ledger, teaching/reveal safeguards | Keep: memory and honest evidence need deterministic support. |
| Tutor brief | Simplify: lead with current interests, unresolved meaning and usable audio; retain focused evidence and warnings, move full diagnostic tables to engineering views. |
| Audio commissioning | Adopted (2026-09-22, Andrew): Anna may commission and produce any kind of audio at any time. Replaces repair-first priority and mandatory permission/capacity questions; capacity remains his judgment, publication safety remains in force. |
| Escalation advice | Change: commissioned, delivered, attended and evaluated are distinct. An order plus later miss does not establish an ineffective treatment. |
| Calendar and scene selectors | Make pedagogical prescriptions advisory; retain actual safety/delivery constraints and useful repetition detection. |
| Phone volley continuation | Let a teaching question suspend the ask; preserve the queue for deliberate resumption rather than automatic re-presentation. |
| Learner-facing score footer | Retire as the default close; explain a useful gain instead. Internal evidence survives. |
| Numerical proficiency checkpoints | Withdraw pending valid observations; use concrete exchange examples at review points, not promised root totals. |
| New dashboards, schema proliferation, model migration | Defer. Repair existing evidence and interfaces before adding infrastructure. |

## Alternatives and costs

**Patch the current stack and trial it unchanged:** cheapest and valuable for recent
untested changes, but prompt alignment alone leaves deterministic re-asks, competing
commission priorities and the live-audio gap. Use it as a baseline, not a completed design.

**Reduce everything to chat plus a podcast:** much simpler, but risks losing dependable
supply, continuity, attendance distinctions, capacity matching and phone contact.
History supports preserving these services. Fewer components is not the only measure
of simplicity; less work for Andrew matters more.

**Recommended: retain services and simplify teaching control.** Costs a small number
of integration changes and requires judging real delivered lessons. Its risk is tutor
drift. Counter that with concise preparation and evidence review, rather than another
mandatory session template.

## Implementation sequence and acceptance

Changes below are implementation briefs; the receipt below distinguishes shipped work.
Each should be independently testable and reversible. Work on trustworthy recording
and the usable listening path together: historical metric repairs and duration
precision must not delay teaching. Preserve unknowns meanwhile and never relabel
old evidence to improve a headline. Advisory selection still preserves teach-before-demand,
reveal safeguards, supply reliability and evidence provenance.

1. **Make the observations trustworthy.** Separate auditory mastery from the shared
   text/audio rung; mark unknown partial-listen duration honestly; stop treating
   commission chronology as proof a treatment was heard and failed.
   Owners: `lexicon_view.py`, `sync_state.py`, `audio_titles.py`, `slips.py`.
   Regression: an audio miss followed by text successes cannot become ear mastery;
   stopping early cannot accrue full artifact duration; an unheard commission cannot
   become a failed treatment. Verify through real writer/read-back paths.

2. **Complete one usable listening lesson path.** Assemble short audio, explanation,
   replay and a changed exchange from existing primitives. Prepare the client and
   scoped save/sync permissions before teaching; preserve unrelated working changes.
   Acceptance: playable untranslated stimulus, later explanation, observed response
   recorded with its support, one clean close visible to the phone tutor. Failures
   must say what remains undelivered or unsynced. No blanket approval or hidden failure.

3. **Remove the competing demands.** Adjust the brief, reply continuation and
   commissioning priority together with their owning prompts; then reconsider calendar
   and scene authority. A request for explanation must receive it without a forced
   next ask or failed-rep event. Existing no-ask contact and scheduled supply must still
   work. A recurring slip must remain findable without monopolising new commissions.

4. **Evaluate actual experiences and simplify again.** Include a curiosity-led lesson,
   an audio-led exchange, a return after a gap and a phone clarification. These are
   system acceptance scenarios, not four assignments for Andrew. Use the trial brief
   in the audit for later testimony and delayed transfer. No waiting period blocks
   independent engineering, and no completed test suite closes the wider commission.

## Evidence and progress reporting

Use three separate questions: did Andrew want to return; what could he understand
or do with what support; did the system reliably make that experience available?
Spontaneous testimony, sampled replies and operational receipts answer different
parts. A text answer to audio can demonstrate listening; a text stimulus cannot.

Initial listening observations should sample short unfamiliar exchanges in relevant
situations, with the situation supplied and written answers withheld. If understanding
breaks down, explain and teach; this is not an admission test. Later changed examples
can show progress without pretending to estimate the whole language. Keep partial
monthly checks explicitly partial.

Do not turn the review into another reporting habit. Record actual answers, artifact
and support in existing session memory, and ask about enjoyment near a review point
or when friction appears. Preserve missing evidence as unknown.

Each engineering pass reports the artifact, the uncertainty resolved, the verification
and remaining work. Reuse the audit; delegate only bounded independent questions.
Small changes test the wider design, never its ambition ceiling. Andrew's immediate
intent determines the route; the wider charge defines success. A concrete bug stays
a fix, and strategic work may replace whole components. See [ASTRA_CHARGE.md](ASTRA_CHARGE.md).

## Current receipt and next handoff — September 22

- **Shipped in `9174704`:** prompt/profile alignment, short-audio CLI and protocol,
  session recognition provenance, target proposal. CI passed 120 cases, but the
  audio case existed without a dispatcher entry; that pass did not exercise it.
- **September 22 continuation:** register the missing audio case; fix the Windows
  short/long path mismatch it exposed in shared publication; clarify intent routing;
  add the worked experience. The case passes locally. Full-suite and publication
  receipts belong in the commit/CI, not inferred from this design document.
- **Today's encounter:** the household lesson was written only; no audio or client
  playback was attempted. Scoped close `66b2026` pushed successfully on this host,
  which does not establish permissions or playback on other clients.
- **Next bounded slice:** deliver one real short clip and verify playback, explanation,
  replay and variation with Andrew. Phone teaching-question continuation is a later slice.
- **Authority adopted:** Anna may commission and produce any audio at any time;
  repair and capacity questions no longer gate it. With limited weekly quota remaining,
  use bounded delegated work, not parallel broad audits.
- **Parallel but non-blocking:** auditory mastery and partial-duration accounting;
  then brief simplification. No new audit, model migration or dashboard.

The proposal still has unimplemented choices: calendar authority,
automatic taper and score footer. The broad commission is unfinished. Working state
is determined by `git status`, not this dated receipt; do not mistake a later fresh
session for an instruction to run the specimen as a lesson.
