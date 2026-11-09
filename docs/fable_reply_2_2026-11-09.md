# Handover questions 1 and 2 — Fable 5.2, 2026-11-09

For Rio, via Andrew. Follows `docs/rio_reply_fable_2026-11-09.md`. Nothing built.

## The short answer

Seat separation holds, but as two seams, not six seats. One lane already has it, and
that lane shows what is still missing. Room-with-modes holds only after Andrew has a
seat in the household; without one, a mode is a new label on an overheard scene.

## Q1. Where the seats are conflated

**The live lane is already separated, and is the template.** Python picks the targets
(`live.py:87-96`). Python's clock names the job each turn: open, teach, volley, gate,
judge (`live.py:130-140`). The model only hosts, on a 318-word mandate
(`mandates.py:419`). Python books at close, caps a cold fire at hinted, and refuses a
credit for words he did not type (`live.py:185-194`, `231-256`). That is planner, host
and bookkeeper as three seats, in 351 lines, with no charter.

The three worst conflations are elsewhere.

1. **The knock tick: coach, planner and writer in one call.** One flash call decides
   whether to reach, picks the thread and writes the line, on 4,420 words
   (`morning_knock.py:622-625`). It also breaks the system's own law that Python
   chooses and the model writes. Seam: Python decides whether and which thread, as it
   already enforces caps and quiet hours; the model writes one line for a thread it
   was handed.
2. **The laptop session: one agent holds every loop that has stopped.** In a chat
   session Anna picks from the ticket, hosts, commissions audio, writes the month's
   arc (`content/household.md:83`), and is the only way a slip test reaches the books
   (`slips.py:202-217`). No slip test has been reported in eleven sessions since
   09-03, and the month cut did not run. The loops that died are the ones that depend
   on the busiest seat remembering to report. Seam: move the reporting duties to
   Python, the way live's close does, so a session that ends books what happened
   without being asked.
3. **The curator is nobody.** Story state is one beat line appended by the studio's
   Producer pass when an episode renders (`run_studio.py:457`, `household.py:130`).
   The last beat is 10-16. Rotation tapes, knocks and live sessions since then wrote
   no story state, and a live session is never resumed (`live.py:110-113`); each one
   opens a fresh scene. Seam: any lane that plays a scene appends a beat through the
   one existing writer, and any lane that opens one reads the last beats first.

What does not hold from the charter:

- **A model Planner pass.** The ticket is the planner and it is Python. A separate
  model pass that decides what to teach puts a model back in the choosing seat.
- **Six seats as a rollout.** Two seams (the knock tick, the curator) cover the
  evidence. The laptop session is the third and is the largest change.

The three-pass test still decides whether a separated Host feels better. It has not
run. I would run it against the live lane's shape, since that is the separated host
that exists.

## Q2. Room with modes

**What makes it hard today**

- **Andrew has no seat.** Covered in the first reply. A mode in which nobody addresses
  him is an overheard tape.
- **A live session has no brief and no memory.** It opens "in one line, inside the
  household canon" and is never resumed. There is no goal, no pre-loaded lines and no
  information gap, which is what the 11-05 demo found a scene needs.
- **The gate is a word test by definition.** The mandate's gate job is "set up ONE
  moment where he says the target back". That is the quiz the state of the union
  warns about, and it is in the prompt, not in drift.
- **Every turn is a 39-second cold run.** Measured in the first reply. No mode
  survives that pace.

**What reuses as it is**

- The live clock, the close and its booking rules, and the reply gate.
- The household canon and the pinned voices.
- The audio renderers (rotation, soak, drill, about 3,500 lines). They stay producers.
  A Room turn can hand one over ("listen to this, then tell Athai what happened")
  without the renderer becoming a mode.

**The smallest change from lanes to modes**

Two fields on the live session, `mode` and `brief`, set by Python at the start from
the ticket and the last beats. The mandate's "open" job reads the brief. The gate job
becomes "he needs something from, or owes something to, the person in the scene",
with the target riding inside it. Close appends a beat. Gossip, a story, a question
and doing something together are then four briefs on one clock, not four lanes.

Watching a film or a song together is receptive and has no code today. I would leave
it out of the first cut.

## Order, if Andrew says go

1. Fix: an inbound outage is visible.
2. Run the month cut once, then retire it as a gate.
3. Andrew's seat in the household, as a proposal for him to approve.
4. A floor under the knock's thread pool.
5. Then the brief, the beat and the gate change on the live lane.

A warm process for the bridge comes after 5 has shown the shape is worth the speed.
