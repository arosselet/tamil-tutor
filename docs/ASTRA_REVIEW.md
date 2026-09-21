# Tamil tutor investigation — findings and unfinished programme

Commissioned September 20, 2026; first audit completed September 21 against `e70a193`.
The wider commission remains unfinished. This is the engineering handoff, not another
file Anna must load. Sprints bound expenditure; they do not redefine the objective.

## Recommendation

The initial recommendation was to trial September 20's comprehension-led design, removing the
older instructions still competing with it. Preserve the experiences Andrew has
repeatedly enjoyed: coffee-and-lore, explanations that make a form click, short
sessions with a natural finish, useful audio matched to available attention,
and a partner who prepares and leads. Keep targeted practice available. Let a
meaningful exchange supply the reason to learn, with mistakes informing the teaching.

The strongest recurring problem is **curiosity meeting a checking machine**.
Andrew asks to understand; the tutor often corrects, scores, advances a queue,
or commissions something instead. The record contains clear examples of this.
It also contains real gains and pleasure. Neither a wholesale failure verdict
nor a confident success forecast is supported.

One necessary outcome is lessons Andrew wants to return to, alongside honest
observations of understanding new spoken exchanges. That does not finish the design work.
The household introduced September 19–20 is a plausible source of continuity,
with almost no outcome history. It should earn its place through use.

The primary objective is continued engagement and enjoyment in learning Tamil
toward a tentative visit next year. August 2027 is a planning anchor, not a
confirmed booking. More engineering time does not imply more learner duties.

## The strongest evidence

### Positive preferences are consistent

The [feedback ledger](../progress/feedback_log.json) records:

| Date | Andrew's reported experience | Implication |
|---|---|---|
| July 7 | A lore memo was “an example of what I've been searching for months for,” rated 9/10. | Discovery and cultural connection have substantive learning value. |
| July 9 | Short audio felt like “a weight lifted”; he reported replaying it. | Portable, finite doses can sustain contact during busy weeks. |
| July 20 | “Picking it apart piece by piece is way more dense learning than listening to it on repeat.” | Explanation deserves space when it unlocks the sound. |
| July 23–24 | He requested passive repetition, initially received a dense scene, then praised the corrected dose. | Match the work to his capacity. |
| July 28 | Coffee before the scenario “is a success”; ten-to-fifteen minutes fits a workday break. | Protect the opening and a reachable ending. |
| July 30 | A familiar episode shape returned “like an old friend.” | Enjoyment includes welcome familiarity as well as novelty. |

These are strong preference signals, not isolated causal effects on acquisition.
Quoted testimony is distinct from the tutor interpretations surrounding it.

He also explicitly endorsed honest mistakes on July 28: “I would rather get it
wrong than make a false signal that I've learned something that I haven't.”
Removing compulsory testing must preserve useful feedback and practice. He asked
for targeted audio addressing recurring confusion, and wanted mission invitations
retained as contact even after rejecting their use as observed performance.

### Operational instructions repeatedly override teaching

The [phone transcript](../progress/chat.md) makes July 25 concrete. Andrew asks
for a line-by-line breakdown. Anna replies, “that's a system note, not a drift
answer,” and asks what he caught. Later, “Can you teach me the irunduhuchu form?”
is passed over while the quiz moves on. A request to teach two unfamiliar words
is labelled MISS.

Similar complaints recur: teaching starvation in July, the fixed
coffee/catch/production/debrief sequence August 31, demand-heavy pushes September 5,
and lessons “short and pointed at my failures” September 16. The missing coffee
opening is raised again September 20.

Historical diffs identify mechanisms:

- `391771a` introduced give-first while still saying zero cold attempts did not
  count as a session.
- `d25e2cd` found mission collection listed as receiving a gift; a temporary
  profile repair had not fixed the owning protocol.
- `3b71052` found an invariant had become a prescribed sequence.
- `7506dba` removes compulsory cold volume and the explanation ceiling and makes
  comprehension lead. This is a substantive recent correction, not a failed trial.

At the audit baseline, [mandates.py](../scripts/mandates.py) still rewards
“showing up and producing in chat,” calls for a volley most days, and limits
correction to one clause even when Andrew asks for teaching. The profile says
recognized-but-not-cold words need no re-teaching. These are specific conflicts
with the new contract. Removing them cannot by itself guarantee good teaching.

### There are gains, but no reliable trip forecast

Actual phone responses include requests to slow down, a food response, a price
question and words caught from audio. Session records describe Andrew bringing
fragments overheard from his family. Those gains deserve to survive the
instrumentation critique.

A typed reply to an English situation does not demonstrate following a new Tamil
exchange. August's immersion exposed that gap. Andrew states it precisely on
September 13: “95% words I know doesn't mean 95% I can decode in context at speed.”

| Baseline record | Count | What it establishes |
|---|---:|---|
| Lexicon rows | 372 | Curriculum inventory, not known vocabulary size. |
| Observation events | 1,783 | Teaching, delivery, attendance, tests and reconstructions. |
| Recognition test events | 56 | 33 ledger imports, 9 session events, 6 check events, 8 eavesdrop events. |
| September Receptive Check | 6 written items | Partial written recognition; no completed audio baseline. |
| Session log | 46 entries | Logged sessions; completeness is unknown. |
| Audio ratings | 9 entries | Sparse feedback under changing rating systems. |
| Ratings carrying artifact ID and duration | 3 | Three distinct artifacts, one recorded play each. |

Historical medium is partly derived from channel: session/text and
eavesdrop/audio must remain distinct. Ledger imports reconstruct prior state;
they are not 33 fresh observations. The assumed 3.5 plays per tape is useful
supply arithmetic, not measured adherence.

Initial inflated recognition, later purges, attendance repairs and medium
corrections break naive comparisons of historical totals. `b8934a9` raised the
floor percentage by shrinking its denominator, without new learning.
A clean fold makes the record repairable; it does not create missing observations.

### Silence and noncompliance were overinterpreted

Andrew explicitly attributed reduced episode listening August 23 to hearing
Tamil all day during the visit, and requested no adjustment. Travel/offline
periods have their own explanations. Neither establishes unpalatable content.

September 9's clarification said mission debriefs described felt readiness,
often for homework he had not done. `d884afa` withdrew response-versus-initiation
and trigger-frequency theories built from those reports. September's anchor
rationale subsequently reused the old “four missions died at the trigger” story.
Anchors remain wanted; that causal story was not valid evidence for them.

The [comprehension plan](comprehension_plan.md) likewise retained a categorical
unreachable-goal verdict and throughput diagnosis after withdrawing the broken
meter arithmetic and correcting single-listen accounting. Withdraw the forecast;
do not replace it with a promise of success.

## What to preserve and what remains a hypothesis

| Decision | Recommendation |
|---|---|
| Anna prepares and leads | Keep. Removing logistics from Andrew is part of teaching. |
| Coffee/lore and finite sessions | Keep. Repeated direct positive testimony. |
| Decomposition, contrasts, useful production | Keep. Compulsory frequency was the problem. |
| Separate listening anchor | Keep the agreed 10–15 minutes and bad-day floor. |
| Household continuity | Trial. Self-contained scenes, supplied context, room for tangents. |
| Studio passes, feed, deterministic state | Keep. They solve real production/reliability problems. |
| Slips and repair audio | Use as teaching context alongside standing material, not the whole agenda. |
| Calendar/register ladder | A planning hypothesis, not a validated acquisition sequence. |
| Six-week zero-intake taper | Reconsider before it binds. July learning being unavailable in August is unsupported here. |
| New schema, dashboards, scheduling machinery | Defer; use existing records for this trial. |
| Whole-system model migration | Defer; first evaluate the hosted lesson experience. |

The [learner contract](../protocol/learner_contract.md) bounds the work: roughly
15-minute sessions, a separate ear block, a bad-day floor, no streaks or makeup.
The ear block remains the agreed habit Anna cues. It should neither become debt
nor disappear into a permission nobody helps Andrew act on.

## Learning assumptions checked

These primary sources refine the recommendation; none validates a Tamil forecast.

**Coverage is a planning aid.** Van Zeeland and Schmitt manipulated coverage in
four spoken informal narratives with 36 native and 40 non-native participants.
Comprehension was often adequate at 90%, with less variation at 95%. This supports
accessible input, not a universal threshold, a Coimbatore vocabulary count, or
guaranteed recognition of written-known words in speech. Keep the current dial
as a working preference and judge the exchange itself.
[Original study](https://doi.org/10.1093/applin/ams074).

**Guided listening can help beyond replay count.** In a semester study of 106
French learners, guided listening processes outperformed a comparison condition
hearing the same texts the same number of times, adjusting for initial differences.
This is consistent with explanation followed by another hearing; it does not
mean every listen needs an exercise.
[Vandergrift and Tafaghodtari](https://onlinelibrary.wiley.com/doi/10.1111/j.1467-9922.2009.00559.x).

**Interpretation and production deserve separate observation.** VanPatten and
Cadierno found gains in both after processing instruction, while traditional
output practice improved production only. Understanding-focused practice is a
reasonable choice; that result does not make output unnecessary or guarantee
transfer to Andrew's Tamil.
[Original study](https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/abs/explicit-instruction-and-input-processing/3223F7D239B7C322970B134F0A693435).

**Corpus size is not representativeness.** LDC-IL's sentence-aligned Tamil resource
describes read speech from news, creative text, sentences and dates. It is not a
denominator for spontaneous family talk. IruMozhi addresses literary/spoken
Tamil distinctions, not this family's coverage. The bounded search did not
establish a representative Coimbatore conversational frequency list; further
corpus work is not a prerequisite for the next lesson.
[LDC-IL documentation](https://www.ldcil.org/files/publication/2023_Compendium_SLA.pdf),
[IruMozhi](https://arxiv.org/abs/2311.07804).

## Focused local alignment

This sprint implements the agreed continuation's narrow prompt/document changes.
It alters no evidence events, state schema or model executor.

| Owner | Replacement |
|---|---|
| Outreach and reply mandates | Enjoyable contact and understanding replace production-only success; optional volleys replace their daily expectation; requested teaching replaces the blanket explanation ceiling. |
| Profile | Comprehension-led use replaces blanket cold-retrieval/no-reteaching directives. |
| Studio Breakdown | Permission to explain a blocking contrast replaces the prohibition on teaching; banter and avoidance of inventories stay. |
| Heist and decision entry | The anchor preference remains; the withdrawn trigger diagnosis leaves. |
| Comprehension plan | An explicit evidence gap replaces the stale impossibility/throughput forecast and references to its old horizon. |

The existing daily-session contract already expresses the intended lesson.
It needs no new sequence or required beat.

## Trial brief — the next ordinary lessons

**Window.** Review after roughly six to eight opportunities over about two weeks.
This is our observation window, not Andrew's quota. Busy days and silence are
missing evidence. Change sooner when friction repeats.

**Opening.** Anna arrives prepared and gives coffee-and-lore: a true connection,
promised story or discovery worth receiving. No recap question or overdue test
earns access. Pay off an existing hook before creating another.

**Teaching.** One short exchange has something worth understanding. The household
can supply it, but curiosity may lead elsewhere. Hear it when playable audio is
available, explain the obstacle, and return to the whole meaning. Pursue Andrew's
question. Useful Tamil replies may follow; output is not the admission price for
new material. Stop at a natural workday-break ending.

**Continuity.** Anna selects and cues suitable existing audio for the separate
ear block, or commissions through the existing channel rules when needed.
Replay is welcome. Supply continues through quieter weeks without becoming a
backlog Andrew owes. He should not manage the catalogue.

**Observation.** Occasionally, after the gift, offer a short changed spoken
exchange using taught material. Supply the situation, not its answer. Ask what
happened, who did what, or what changed. A typed English answer can demonstrate
listening if the stimulus was audio and the written answer stayed hidden.
Record the actual answer, audio artifact, prior exposure and support in the
existing debrief. Use word-level flags only for what that answer establishes.
One understood exchange is local evidence, not a new global level. A changed
exchange on a later day helps distinguish learning from plot recall.
Silence receives no failure mark. With text-only delivery, teach and record
reading honestly.

**Enjoyment.** Preserve spontaneous comments verbatim. Near the review point,
have one short conversation about what Andrew looked forward to, what clicked
and what grated. Avoid a satisfaction survey after every lesson. Completion and
replay can corroborate his account, but do not establish enjoyment or understanding.

**Decision.** Continue when Andrew wants more and exchanges become clearer with
manageable support. If enjoyment improves but listening transfer remains unclear,
work the blocking contrast without inflating the score. If the story feels
contrived, change or drop its premise. If administration and checking dominate,
correct that immediately. If no listening observations occur, the result is
unknown: fix the opportunity to observe it.

**Model choice.** Compare experiences under the same contract and similar demands.
Do not reteach identical content as an allegedly fair comparison; exposure
advantages the second tutor. Familiarity, topic and order effects limit inference.
Andrew's preference is enough to choose his tutor without claiming general model
superiority. The current writer configuration delegates local production to
Claude and cloud work to Gemini; Astra hosting the lesson does not replace those
components. Keep that production stack steady during the initial trial.

## Residual engineering risks

The audit identified limits this prompt alignment does not fix:

1. **Mixed evidence can count as ear mastery.** `sync_state.is_heard` combines the
   shared recognition rung with any `heard_on`; `lexicon_view.derive` moves the
   rung from text and audio. An audio miss followed by enough text passes can
   satisfy the predicate. This is a code-derived counterexample, not demonstrated
   current inflation of the four solid rows. Their paired successes are imported
   ledger events, not fresh independent listening observations. Use actual trial
   replies rather than this headline to claim auditory progress.
2. **Partial playback can receive full duration.** `sync_state.cmd_rate_episode`
   stores artifact duration; `audio_titles.dose_minutes` sums it, even for a
   stopped-early rating. No such new-format row was present at baseline. These
   are not measured watch-time minutes; a fix should preserve unknown duration.
3. **A cue is not a completed sample.** `suggest_targets.check_due` uses the
   latest audio check event. Partial completion lives in the debrief. One answer
   must not be described as a completed baseline.
4. **Phone volleys still own the queue.** Reply code can re-present or advance a
   pinned ask after the model's explanation. Prompt permission to teach does not
   redesign that interaction. If explanations remain crowded out, inspect the
   join before adding another persona rule. The existing Python-produced
   fired-today footer also remains; removing the composer's campaign-count
   instruction does not make the phone surface wholly free of numbers.

Future fixes to the first two deserve real writer round-trip regressions in the
smoke sandbox. They are separate from this sprint's state-free alignment.

## Receipts and verification

The investigation used three delegated reviews, source/history reading, smoke tests
and the primary sources above. Oversized reads and full-context delegation duplicated
work. The alignment sprint reused findings without delegation. The stale goal counter
cannot establish subscription cost; earlier percentage estimates were rough judgments.

| Commit | Why it matters |
|---|---|
| `7ff602a`, `0a7c5cc` | RSS preceded retirement of the fragile mobile wall workflow. |
| `c9b7ad2`, `31ccdd5` | Concern separation and studio isolation solved real problems. |
| `391771a`, `22532a1` | Break-first sessions and passive soak addressed stated needs. |
| `b8934a9`, `3b71052`, `266330f` | Seed purge, template repair, delivery/callback distinction. |
| `d884afa` | Withdraws theories based on mission debriefs. |
| `f16f2a6`, `9066d08`, `c84d22a` | Observation log, attendance gate, rating lookup repair. |
| `e83a076`, `920c462` | Recent household/year and standing audio supply. |
| `7506dba`, `5213fa5` | Comprehension-led sessions and explicit recognition medium. |

Inspect receipts with `git show <commit>`. Narrative dates may denote decisions:
`e83a076` was authored September 19 and committed September 20.
[Journey](JOURNEY.md) is a July retrospective, not a current outcome report.

**Verification:** post-edit `python scripts/smoke_test.py` passed all 119 cases,
including budgets and the live ledger-fold check. The first run caught an
exact-phrase guard on Tamil-script drafting; its original wording was restored
and the full rerun passed. `git diff --check` passed, all six local report links
resolve, and learner JSON has no diff. The report has a 3,000-word budget and is
not added to any tutor load path. Changes remain local, uncommitted and unpushed.
Smoke stubs model generation, TTS and delivery; it cannot establish enjoyable
lessons, pronunciation or transfer. No lesson was run during this audit.

## Programme status — corrected after Andrew's September 21 reminder

The original commission seeks an enjoyable, effective, focused system for the tentative
2027 visit. No design is sacred. Completing an audit and proposing a trial did not
complete that commission; switching automatically into lessons lost its scope.

| Work | Status / completion evidence |
|---|---|
| Historical evidence and initial conflicts | First pass complete; findings above, local alignment tested but not deployed. |
| Focused system design | Proposed in [comprehension_plan.md](comprehension_plan.md): responsibilities, keep/change/retire choices, alternatives and implementation acceptance. Not deployed. |
| Implementation and integration | Incomplete: selected changes must work through actual learner journeys, including hearing, explanation and unobtrusive saving. |
| Experience and transfer | Ongoing: use lesson evidence and Andrew's testimony to revise the design; technical checks cannot establish enjoyment or learning. |

The September 21 lesson yielded supported written comprehension and one scaffolded
question, not auditory transfer. It also exposed repeated exercise structure, no live
listening, and intrusive save/permission operations. These are delivery observations,
not a satisfaction verdict. The lesson is evidence within the investigation.

Next implementation slice: trustworthy recording alongside a usable short listening
path; historical metric repairs do not gate teaching. The design names acceptance cases.
Each bounded pass reports its artifact, resolved uncertainty and remaining work;
no invented overall percentage. Reuse prior research and delegate only non-overlapping
questions that can change a decision. Longitudinal evidence need not block independent
design and integration work. Remain in engineering until a lesson is explicitly chosen.
