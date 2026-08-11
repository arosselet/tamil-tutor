# The Pack Boundary

*Written 2026-08-11, takeoff day, at Andrew's request: "if we've built a very tidy
version of this, then what else could we ask of it than language learning?"*

*This is an engineer's note, not canon. It settles nothing on its own — the one
decision it produced is recorded in `docs/DECISIONS.md` (2026-08-11). Anna never
loads this file.*

---

## 1. The tape already answered a smaller question

`content/scripts/special_institution_of_one.md` ends with the system saying it
plainly:

> **ANNA:** Five of those six have nothing to do with Tamil.
> **FRENCH:** Rien à voir avec le tamoul.
> **SPANISH:** Cambias el paquete del idioma.
> **ANNA:** Change the pack. The other five stay where they are.

That claim is true and it is also the easy case. It demonstrates the swap with
French and Spanish — *another language*. The question now on the table is
different: does the boundary hold at *another domain*?

Partly. Not where the tape puts it. Here is the audit, taken against the code
rather than against the story we tell about it.

## 2. Where the seams actually are

**Travels anywhere — no notion of a "word" appears in it.**

| Part | What it is in this repo | Why it ports |
|---|---|---|
| **RAILS** | `rails_gate` (waking hours, daily cap, min-gap, self-set `next_check`, the transit bit), `push_to_phone`'s quiet-hours chokepoint, `knock_id` correlation so a reply is bound to its own question, `push_queue`'s durable defer-never-drop, one non-forced fire per tick | Every rule is about *reaching a person*, not about what is being taught |
| **GOVERN** | `DECISIONS.md` and its "state what it replaces" law, `PROSE_BUDGETS` / `CODE_BUDGETS` ratchets, "a fixed bug becomes a smoke case the day it is fixed", the structure freeze, split-or-retire | Pure change discipline. This is the part that turned the March–April soup into a 294-commit July that compounded |
| **STUDIO (shape only)** | Narrow passes — plan, then write, then dialect; agents that get no filesystem and only print; deterministic Python lints deciding whether output ships; non-zero exit falls back | A general answer to "have a model produce an artifact you cannot fully verify." The *specific* lints — Woven-Thanglish density, fourth wall, verbatim deck fidelity — are pack |

**Looks general, is actually a theory of learning.** MODEL is the part most
likely to be mistaken for domain-free, and it is not. "Every word carries two
numbers: what he understands, and what he can say cold" encodes a specific
claim — that competence has a **recognition–production gap**, and that closing
that gap is the whole job. The viability floor, the soak order, engines, slips,
the drill/volley/eavesdrop channels and every "cold" in the codebase exist
because of that claim.

It ports to anything with the same gap. It ports to *nothing* about tasks,
goals, or intentions. There is no cold recall of "book the dentist."

**Language-specific — the pack proper.** `persona.md`, `hosts.md`,
`dialect.md`, `TAMIL_RE`, the pinned `ta-IN-…` voices, the Tamil worked examples
inside `SLIP_MANDATE` and the judge prompt, Woven Thanglish, the
phonetic/script modality split. All already documented as the port surface in
`BOOTSTRAP.md` → *What Generalizes*.

**So the tape's "five of six" is really: three travel anywhere, one and a half
travel to any recognition–production skill, one and a half are Tamil.**

## 3. The fingerprint — what this machine is actually shaped for

Better than listing candidate domains: state the shape of problem the machinery
is fitted to. Each property below exists in the code as a mechanism, which is
what makes this a test rather than a mood.

1. **A recognition–production gap.** You "know" far more than you can do
   unaided. → *MODEL's two axes exist only for this.*
2. **Progress is real but invisible inside any one session.** → *the debrief as
   running prose, contact-time-over-completion, the meters.*
3. **Nobody is enforcing it.** No exam, no employer, no sunk money. → *MOTIVE:
   no streak, cheap return, the coach reaches first.*
4. **A real-world moment of truth you do not control.** The table. → *forced
   cold output, and "an ambush is only an ambush if the prompt would read as
   normal to someone not being tested."*
5. **An expert oracle exists who must never become an examiner.** → *the Oracle
   policy.*

**Matches, and would get most of the machine:** another language (trivially),
an instrument, sight-reading, mental arithmetic, clinical or legal recall, a
chess repertoire, getting fluent in a large unfamiliar codebase, speaking in
public in a second language. Anything where *"I have read it"* and *"I can do it
cold"* are far apart.

**Does not match:** reminders, habits, fitness logging, task management,
"goals I want to hit." These fail property 1 outright — you do not skip a run
because you failed to *retrieve* running. For those, the only useful parts are
RAILS and MOTIVE, which is to say: a notification scheduler with good manners.
Andrew's own read — *"I don't need all of this exceptional engineering for a
reminder app"* — is correct, and this is the reason why. Most of the value here
is machinery a reminder has no use for.

**The interesting middle.** He named a third class: *"things I want to do that
feel very slow in progress and are hard to stick to."* That class fails
property 1 and passes 2, 3 and 4. What it needs from this repo is **RAILS +
MOTIVE + GOVERN and nothing else** — which is a much smaller fork than "Anna
with a different pack," and a different product. Not a tutor with a new
subject. The reach layer, standalone.

## 4. The thing that should decide this, and it is not an argument

Andrew's own account: eleven months of coming back without a trip in the books,
and then a month of crunch that finally moved him. The state files agree, and
the size of it is worth seeing:

| | Sessions | Per day | Longest gap | Deck cold |
|---|---|---|---|---|
| **2026-06-21 → 07-12** (no date in the books) | 5 in 22 days | 0.23 | 7 days | 5/69 |
| **2026-07-13 → 08-10** ("war footing, 30 days out") | 23 in 29 days | 0.79 | 2 days | 34/71 |

That is the largest behavioural change in the project's history, and it lines up
with an externally imposed date rather than with anything built.

**But it does not prove what it looks like it proves.** July 13 is also when the
Trip Deck was seeded, when the knock channel went from 1 fire in June to 86 in
July, and (07-17) when the campaign block shipped. The deadline and a large step
up in machinery arrived in the same week. **July cannot separate them**, and any
confident story about which one did the work is a story, not a measurement.

Which is exactly why what happens next matters more than any argument in this
document. Two eras land back to back, and each one removes a variable:

- **Era 2 — in country (~Aug 12 → Sep 12).** The deadline is spent; the stake
  becomes continuous and situational. Reality supplies the reps three times a
  day. *Question it answers:* what is the system worth when the environment is
  doing the work — does Anna stay useful beside a live informant, or become
  noise?
- **Era 3 — the return (~Sep 12 on).** No deadline, no table, and a learner who
  now knows exactly what fluent contact feels like and can measure himself below
  it. *Question it answers:* does MOTIVE hold anything up on its own?

Era 3 is the real experiment, because it is the only condition in this project's
history where **the machinery is fully built and the deadline is fully absent.**
The eleven-month baseline says he keeps coming back and does not produce. If
that repeats with all of this running, then MOTIVE as currently designed is a
**retention** system, not an **activation** one — and reading its own words
back, that is what it was built as: *"Nothing gets worse if he skips today. No
streak. Coming back is made cheap."* That brief is anti-quit. It succeeded at
anti-quit for eleven months. It has never yet been shown to produce.

## 5. The recommendation

**Do not fork during the trip.** Not out of caution about scope — because the
fork would copy a motivation layer that has never been observed working without
an external deadline, and the four weeks that could tell us are running right
now and cannot be re-run.

**Instrument Era 2 and Era 3 instead, and do it before they start.** There is a
specific gap here worth naming: the era-turn rule says the status line drops the
countdown and the burn rate at touchdown, which is right — a per-day quota is a
lie when the table sets the pace. But it means that at the exact moment the
interesting question becomes *"is he still showing up?"*, the system stops
reporting the only number that would answer it. Session cadence is already
computable from `session_log.json` and nothing surfaces it. Filed to
`docs/feature_inbox.md`.

**If and when it forks, fork RAILS + GOVERN first — not Anna.** They are the
two parts that are proven, domain-free, and expensive to rebuild; 112 fires,
four silences and a July's worth of bugs bought that gate. The pack question is
downstream and cheap by comparison.

**And fork it — never grow it inside Anna.** Andrew's instinct is right and
there is a mechanical reason beyond taste: Anna's leverage is that he is *one*
thing, with a stake, a dialect, and ten years of family standing behind him. An
assistant that also teaches Tamil is a worse tutor, because the persona stops
being a person.

---

*One honest residual: everything above is an audit of code and state, not a
result. The tape's own close applies to this document too — a system describing
itself is a demonstration, not a proof. The proof is the number, and the number
is his.*
