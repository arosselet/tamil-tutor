# Whole-system examination — Fable 5.2, 2026-11-09

For Rio, via Andrew. Andrew asked for a methodical look at the pedagogy, the runtime,
the records, the dialect and the skills, taking Rio's "working / not working" list as
suggestions. Read at `6a4df2b`. Nothing here is built.

**What was checked:** the books recounted with a script (`observations.json`,
`knock_log.json`, `session_log.json`, `lexicon.json`, `slip_log.json`,
`review_queue.json`, `policy.json`); the smoke suite run (157 cases, all green); the last
200 `Anna` workflow runs; `scripts/live.py`; the 25 newest files in `content/scripts/`
and the last four tape scripts; the constitution, the map, `dialect.md`,
`daily_session.md`, `learner_contract.md`, `household.md` and the skill files.

**What was not:** the knock tick, the selection code and the studio pipeline were not
read, and only the tail of `DECISIONS.md`. Causes below are hypotheses unless marked.

## The short answer

Contact fell in mid-September, six weeks before the token blackout. The five builds of
11-09 fix supply, visibility and the seat; none of them yet addresses what the books
suggest about the fade, which is that the reach mix moved toward the kind of reach he
answers least.

## Where Rio's list is wrong or incomplete

**1. Reply rates are known, not unknown.** Recomputed with the blackout
(2026-10-28T23:53Z to 2026-11-09T21:00Z) removed. Seven reaches fell inside it. The
07-31 outage was rotated the same night and changes nothing.

| Month | Reaches | Replied | Replied or tapped |
|---|---|---|---|
| Jul | 88 | 52% | 70% |
| Aug | 71 | 44% | 52% |
| Sep | 51 | 27% | 37% |
| Oct | 48 | 31% | 44% |

Removing the blackout moves October from 30% to 31%.

**2. The fade began in mid-September.** Days with any contact (a session, a reply or a
tap), per ISO week: 6 to 7 from week 27 through week 36; then 5, 3, 3, 3, 1 (week 41,
Oct 5), 4, 6, 3. Sessions per month: Jul 16, Aug 20, Sep 10, Oct 6, none since 10-30.
There was also a 13-day stretch with no inbound, 09-17 to 10-01; whether that was
absence or an outage is UNKNOWN.

**3. The seat's drift test already has a first answer.** Reply rate by kind of reach,
all months, blackout removed:

| Kind | Reaches | Replied |
|---|---|---|
| volley | 26 | 73% |
| fielding (someone asks him) | 19 | 68% |
| challenge | 18 | 67% |
| text | 115 | 39% |
| eavesdrop (overheard tape) | 37 | 30% |
| audio memo | 37 | 14% |

Confounded: a tape has to be listened to before it can be answered, and the kinds were
not assigned at random. It still points the way the seat theory predicts.

**4. October's mix shifted toward audio.** In October 24 of 48 reaches were audio or
eavesdrop, replied to at 12%; the 24 text reaches held at 50%. July was 17 audio of 88.
Hypothesis, not established: the move to comprehension-led reaches lowered replies by
changing the mix, not because he went quiet.

**5. The live lane has never run for real.** There is no `progress/live_session.json`
and no observation on channel `live`. The lane is the right shape, but it is untested
code, not a template with a record. Its gates grade typed text, so it will add
production evidence and no ear evidence.

## Pedagogy

- Working: teach-before-test, ask-never-self-mark and the medium flag are coherent, and
  the books enforce them.
- Repair: production testing has nearly stopped. Tested production events: Jul 97,
  Aug 125, Sep 51, Oct 16, Nov 0. Those are the exchanges he answers (finding 3).
- No evidence: October recognition checks, all by reading: 62 right, 37 wrong,
  9 partial. The sweep asks untaught words too, so this is not a clean score. The 10-30
  session logged `nee` read as "we" twice.
- No evidence: the constitution's proof is following a new spoken exchange without
  captions. Nothing measures it (see Records).

## Records

- Working: the ledger folds with no divergence and the suite is green.
- Repair: 233 of 429 lexicon rows were never taught; 284 were never recognition-tested.
  No test of any kind has been booked in November.
- No evidence: three tested observations carry `medium: audio`, on three words, ever.
  328 tests before 09-20 carry no medium. `attended` events: 27 in September, 5 in
  October, none since.
- Suspect: `policy.json` reports "79% return per reach" over 28 days that include the
  blackout. It counts any contact within two days of a reach, so it is far above the
  reply rate and does not show the fade. `params`, `history` and `proposals` are all
  empty: the weekly reflection has never produced an approved move.
- Review queue: 23 pending, 4 rejected, and no reviewer.

## Runtime

- Working: 200 runs, one failure (a dispatch). The cron delivers 4 to 6 ticks a day,
  as `anna.yml` already documents.
- Repair, as Rio lists: the beat log in `household.md` is empty and only live reads a
  beat; `mandates.py:52-57` still defines the tape as OVERHEARD and "never plot".

## Dialect

I am not a native reader. These are flags for the Oracle, not verdicts.

- Working: the tapes read as natural spoken Tamil (கேக்குறாரு, பண்ணான்,
  மாட்டேங்குறான்). The 25 newest scripts contain no வேண்டும் and no இருக்கிறது.
- Repair: nothing in them is specifically Kongu. A scan for ஏனுங், -ங்கோ and -ங்ணா
  found none, though Paati's stated job is "older Kongu forms". `dialect.md` gives its
  Kongu layer one paragraph and names no forms; its reference ear, Raj, is fictional.
- Repair: the judge and the tutor disagree with no arbiter. The judge holds
  `ஃப்ரீயா விடுங்க` as an English calque (drill, 11-09); Anna praised the same phrase
  as Kovai in the 10-20 session.
- For the Oracle: the 10-31 soak lists `நீ வாங்கினா`, `நீ செஞ்சா`, `நீ போனா` for
  "you bought / did / went". To my reading those are "if you buy / do / go". The 10-30
  session taught `vaangina`. They are pending in the review queue; I found no
  `soak_2026-10-31` script, so whether they were voiced is UNKNOWN.
- Minor: three -றோம் forms of the சாப்பிடறோம் kind in recent scripts; the judge
  rejected one as "unnatural" without naming the dialect.

## Skills

- Working: the playbooks match the code.
- Repair: dead references to `scripts/pack.py`, `docs/CUSTOMIZATION.md` and
  `protocol/studio/dialect.md`; the glossary cites a "Floor-gap targets" section that
  `daily_session.md` no longer has; `/debug` has no entry for `line_silence`.
- Repair: `AGENTS.md` names Astra and `gpt-6-luna` as the operating seats. The charter
  names six seats with Rio as coach. Both are in force and they disagree.

## What I would do first

1. Take the three soak forms and the `ஃப்ரீயா விடுங்க` ruling to the Oracle. It is a
   vocabulary confirmation, which the constitution allows.
2. Run one real live session, so the lane has a record before anything is modelled on
   it.
3. Move the reach mix back toward addressed, answerable turns before building the
   knock-tick seam. Drift test: reply rate per kind, on the table in finding 3.

## Questions for Rio

1. What changed for Andrew in the week of 09-14? The books show the drop and not the
   reason.
2. Is the 09-17 to 10-01 silence an outage or an absence?
3. The seat theory predicts addressed turns win. They already do in the books. Does
   that change what the first live sessions need to prove?
4. If production turns are what he answers, is "comprehension leads" still the right
   order for the phone, or only for the laptop?
