# Teaching starvation: the word state machine, its bottlenecks, and three separable proposals

Filed 2026-11-14 by Rio, from Andrew's felt report of 2026-11-14 and a live read of
`progress/lexicon.json` and `scripts/lexicon_view.py` the same morning. Andrew's
report, in his words as closely as a summary keeps them: he feels starved of
teaching. The formats multiply — soak, drill, scene, episode, text lessons — and
the terms overload. Over and over, in slightly different flavours, he feels
exposed to something, or demanded something, he was never taught. "Coffee and
lore" was invented so a chat lesson would present something before asking him
anything; it points at a deeper problem, because the presenting had to be forced
into one lane as an opening ritual. He listened to a few episodes this week and
felt frustrated: he does not care about Priya or Athai; the episodes are mostly
dense, boring, contrived. He cannot reconcile three wants: real scenarios to
practise for the settings he cares about; not contrived about real people; not
hokey. And it is a vicious cycle: the system needs his input to advance the
teaching set, he is annoyed, he does not go back, the system keeps producing
the same thing.

## The state machine, as built

A lexicon row is born hand-added as curriculum, or when an episode script
mentions the word (`seen_in`). After birth, three axes move independently; no
state anywhere says "this word is his."

- **Taught.** `taught_on` is set immediately only by a live session — the one
  self-attending channel in `lexicon_view.py` (`SELF_ATTENDING = {"session"}`),
  because there is no press of play between the teaching and the ear. Every
  other channel's teaching sets `taught_pending` only, discharged by an
  `attended` event. Hearing is not knowing (2026-08-23) — that rule is not in
  dispute here.
- **Recognition.** untested → struggled → comfortable → solid, one rung per
  watched-test pass, down one per miss. Shipped or declared channels never vote.
- **Production.** none → hinted → cold, best grade ever.

## Census at filing (live, 2026-11-14, 431 rows)

- Recognition: untested 286, struggled 53, comfortable 85, solid 7.
- Production: none 288, hinted 22, cold 121.
- `taught_on` null on 227 rows; set on 204.
- 226 rows sit at the origin: recognition untested and production none.
- 109 rows have appeared in episodes (`seen_in` non-empty) with `taught_on`
  still null — exposure ran ahead of teaching, by construction.
- `heard_on` is set on 40 rows. Cross-axis leaks both ways: 44 rows are
  production cold with recognition untested; 31 rows are comfortable/solid
  recognition with production none.

## Three separable proposals — rule on each separately

**A. Transition census (do first; read-only; @build).** Count, from the
observation log: how many words are parked at each gate (untaught,
taught-pending, taught-but-untested, recognition-only, production-only); and
for the last 60 days, per lane, how many demands — a test, a catch, a
production prompt, a payoff that presupposes the word — were made on words
whose `taught_on` was null at the time. This proposal stands or falls on its
own numbers: if demands on untaught words turn out rare, part B loses its
premise and should be rejected at the same drain.

**B. No demand without teaching (gated on A).** Define a *demand* as above.
A demand on a word is allowed only if `taught_on` is set, **or** the same item
teaches it first — presents it with gloss and one example before asking
anything. That is coffee-and-lore generalised from an opening ritual in one
lane into an invariant every lane checks. Two clarifications that keep it
honest: passive exposure inside a scene is not a demand, and it is also not
teaching — it changes no claim either way. And the named risk: if the census
shows the taught gate itself is the choke (teaching pending because attendance
is the only discharge, and attendance has collapsed), then B alone would freeze
the lanes, and the discharge rule — what evidence besides a rating tap can
discharge a pending Teach Beat — is the thing to fix first or instead. B is
not a request to build both silently; the census picks the order.

**C. His day as the source (separate experiment; not a Room change).** The
Priya/Athai problem is not fixed by more biography or a better seat: he does
not care about them, and invented dialogue for real people (Roshana, Ava) is
false in a way no writing quality repairs — that is why it feels hokey. What
can be real without being invented is *events*: things that actually happened
in his day. One trial: he reports a day in English in about two minutes (or
Rio supplies events already known), Anna returns the Tamil he could have used
in those moments and replays them with him. Nothing invented about anyone; the
scenario is one he demonstrably cares about because he lived it. It also swaps
the input the cycle starves on: not ratings on episodes he finds boring, but a
short report that itself becomes the teaching set. Trial verdict, stated in
advance: it earns a second trial only if he attends and answers it at a rate
episodes are not getting, and if words it teaches show movement at the next
probe. No cast change, no Room replacement, is proposed or implied by C.

## Not proposed

No new format, no new host or lane, no model swap, no density dial, no change
to "hearing is not knowing." If A, B and C all fail their own tests, the
starvation claim itself needs re-examining — that is the drift test for the
whole filing.

## Census results (proposal A, run 2026-11-14 at the drain)

Read-only, replayed from `progress/observations.json` and `progress/knock_log.json`
with the fold's own rules (`lexicon_view.derive`). "Taught" below means `taught_on`
was set on the day of the ask; "shipped only" means a recording carried a Teach Beat
and nothing shows he heard it; "never" means no Teach Beat anywhere.

**Where the 431 rows are parked.**

| Gate | Rows |
|---|---|
| Never taught, never tested | 61 |
| A Teach Beat shipped in a recording, no sign he heard it, never tested | 137 |
| Tested, but still not counted as taught | 29 |
| Taught, never tested | 28 |
| Recognition moved, production never | 60 |
| Production moved, recognition never | 36 |
| Both moved | 80 |

**Answered tests, 2026-09-15 to 11-14 (142).** Taught 93, shipped only 36, never 13:
35% were on words he had not provably been taught. By lane: check 62 / 33 / 6,
session 13 / 3 / 5, text 9 / 0 / 2, the rest all taught. He was wrong on 19% of the
taught asks, 47% of the shipped-only asks and 31% of the never-taught asks. 39 of the
49 untaught asks came from the check, which asks untaught rows on purpose (DECISIONS
10-05, "all you had to do was ask"); outside the check it is 10 of 41.

**Knocks that asked, answered or not, same window (53).** Text 20, fielding 8 and
volley 2 all asked taught words. The overheard tape asked 23 times, 14 of them on
untaught targets: `frame:cant-முடியல` ten times (never taught as a frame; he produced
it once, 08-25) and `தெரியுமா?` four times. None of those 14 was answered. The 11-12
cooldown (7 days) covers `தெரியுமா?`; the முடியல tapes ran five to seven days apart
and would mostly pass it.

**The taught gate is the choke.** Since 09-01, recordings shipped 244 word-level
Teach Beats and 44 were discharged by a listen. Live sessions, the one channel whose
teaching counts at once, taught 26 words in that time, across 12 sessions. Over the
same 60 days 61 of 86 knocks went unanswered, and 11 of the last 12.

**What the census cannot see.** A demand that left no test event: an episode payoff
that presupposes a word, or an ask inside a session that Anna did not log. M99's
"lost the thread" rating is that kind of evidence and is not counted here.

**Reading.** B's premise holds in two places, the overheard tape and the check, and
not in text, fielding or volley. The larger number is the 137: the named risk in B is
real, and an invariant that only forbids would leave most lanes little they may ask.
