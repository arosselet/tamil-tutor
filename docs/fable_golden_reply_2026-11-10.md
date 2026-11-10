# Reply to the golden prompt — Fable 5.2, 2026-11-10

For Rio, via Andrew. Answers Jobs A, B and C of `docs/golden_prompt_fable_2026-11-10.md`,
read at `14f49be`. Nothing in this reply is built.

## In plain words

Three of the five builds do what they say. Two have a hole.

- **The seat stops at the studio door.** The canon now says people speak to Andrew.
  The episode checker still fails any script that contains his name, the rotation
  tapes never read the household at all, and the push prompt still defines the tape
  as overheard. The November finale, as written, cannot pass the checker.
- **The live lane loses his best answers.** In a full run in a copy of the repo I said
  both targets correctly. Anna answered "cold!" and the close booked nothing. An
  answer only counts on the one turn the clock calls "judge", and he will often say
  the word a turn early because the scene has just said it to him twice.

The bottleneck is not any of this. It is contact: no session since 10-30 and no test
of any kind booked in November. The next step is a test Andrew runs (three real live
sessions), and the live booking has to be repaired first or those sessions will
record the wrong thing.

**Two things in the prompt are already answered** in
`docs/fable_examination_2026-11-09.md`: reply rates are recomputed (the blackout
moves October from 30% to 31%, and the fade began in mid-September), and the seat's
drift test has a first answer in the books (see Job B).

**Three things changed after the prompt's reading list was written**, on Andrew's
rulings at the 11-09 drain: seat separation is two seams, not six seats; the host
bake-off is cancelled and the phone thread is Telegram on the existing bridge; and
three small builds he approved landed (a truncation guard, `pairs_with` retired,
ordering a tape from the phone). DECISIONS has a line for each.

## Job A — the five builds

| # | Build | Verdict | Evidence |
|---|---|---|---|
| 1 | Silent line | **Pass on replay; unverified live** | `morning_knock.line_silence` replayed against the real knock log, cut off at each date: nothing on 11-02, trips on 11-03 at 16:00Z with five reaches since 10-28. It clears on 11-09 when his message arrived. No line check has ever been sent. |
| 2 | Month cut retired | **Pass, with three leftovers** | `learner.json` holds "The upstairs room", 11-09 to 11-30, and the map prints it. Leftovers below. |
| 3 | Thread floor | **Pass today; empty by 11-21** | `threads.live` on today's books returns three words. Projected with no new contact: two by 11-13, one on 11-20, none on 11-21. |
| 4 | Seat in the household | **Pass for push and live; fail for episodes and rotation** | Details below. |
| 5 | Live brief and beat | **Brief, clock and carry-over pass; booking and the unanswered scene fail** | A full run in a sandbox copy. Details below. |

**1. What the first real notice looks like.** One push, written by Python with no
model call: "Line check: nothing from your phone has reached Anna since <date>. If
you tapped or replied, the reply token has expired (HA doc, section 10)."
(`morning_knock.py:194-195`). One per silence.

**2. Leftovers of October.**
- `progress/profile.md:28` still tells the next session to open on "a self-contained
  moment from anywhere in the birthday build-up".
- The standing audio order is still the 10-30 one, an October scene between other
  people ("Karthi drags Athai into the Mama debt"). The map shows it under "On tape
  this week".
- Three backlog lines still say "decide at the November cut" (finale escalation
  order, the year as rooms, the word-pool upsert). Nothing in code gates on the cut.

**3. What empties the floor.** The top-up draws only on words taught in a session,
text, audio or live turn in the last 21 days (`threads.py:132-152`). The last such
teaching was 10-30. One real session refills it. Minor and UNKNOWN in effect: the
21-day cut-off compares timestamp strings that carry four different UTC offsets
(`threads.py:139-143`), so the edge can be off by some hours.

**4. Where the seat reaches, and where it stops.**
- Reaches: the push decision (`morning_knock.py:690` loads the canon) and the live
  turn (`live.py:197`).
- The episode pipeline reads the canon file (`run_studio.py:110`), but three things
  contradict the seat:
  - `run_studio.py:612-615` fails any script that contains the learner's name
    ("fourth wall: script names the learner").
  - `protocol/studio/hosts.md:15`: "The learner is an observer of their world, never
    an addressee."
  - `run_studio.py:100-101`: "You never address the learner".
- The rotation lane builds its prompt from the voice canon alone
  (`render_rotation.py:407`). The 11-09 room tape contains none of the seven names.
  The shelf builds mostly rotation tapes, so most unattended audio is outside the
  household entirely.
- The push prompt still defines the tape as OVERHEARD, "never plot"
  (`mandates.py:52-57`), and the arc thread is labelled "an overheard tape hangs
  here" (`threads.py:223`).
- The reply and message lanes do not load the canon. When he answers Priya, the
  judge that replies has not been told who Priya is.

**5. The live run.** Three sessions and twelve model calls in a copy of the repo with
no push webhook, me typing as Andrew. It is a mechanical test, not his session.
About 23 seconds a turn on the laptop.

- Pass: the brief. Session 1 opened with Athai and gossip, 2 with Deepa and an
  errand, 3 with Karthi and a question. Each person spoke to him.
- Pass: the clock ran open, teach, volley, gate, judge.
- Pass: carry-over. Session 2 opened "Still grinning about Karthi's secret, Deepa
  tugs your sleeve".
- Pass: a taught word was booked as taught and attended, stamped as text.
- **Fail: answers given before the judge turn are never booked.** A verdict is
  recorded only when the clock's job is "judge" (`live.py:238`). I said target 1 on a
  volley turn and target 2 on the turn the clock called "gate". Anna replied "adhu
  dhaan — yaarukku theriyum, cold!" The close printed "0 gate(s) booked". Two correct
  productions, none in the books.
- **Fail: the same slip writes a false story.** After target 1 the beat read "Andrew
  dodged her push for a reaction ... instead of trying the target line". He had said
  it one turn earlier.
- **Fail: one unanswered scene erases the story.** A beat is kept only from a scene he
  took part in (`live.py:249`), and the next session reads only the session
  immediately before it (`live.py:146`). I opened session 2, closed it without
  answering, and session 3 opened with an empty `last_time`. The rotation also moved
  on, so the Deepa errand was skipped.
- Observed once: session 2's opening line contained no Tamil.
- Not verified: a session by Andrew, the WhatsApp path, the judge seat holding a line.

## Job B — three tests, written down before they run

**B1. Addressed against overheard (the seat's drift test).**

The books already give a first answer. Blackout removed, all months:

| Reach | Sent | Replied |
|---|---|---|
| Fielding: a household voice asks him one short question | 19 | 68% |
| Overheard tape, 45 to 90 seconds | 37 | 30% |
| Audio memo from Anna | 37 | 14% |

Correction to my 11-09 write-up: I called this confounded by text against audio.
Fielding is spoken too. The real confound is length and effort: a question takes five
seconds to hear, a tape takes a minute.

- The test: tapes of the same length, alternating by date. Even days, the person
  speaks to him and ends on a question. Odd days, the tape is overheard as now. Ten
  of each.
- Measure: replied or not, within 24 hours.
- Pass: addressed tapes are replied to at 50% or more, and at least 20 points above
  overheard.
- Fail: the two are within 10 points. Then length, not address, is what he is
  avoiding, and the fix is shorter tapes.
- Limits: ten each is two replies' difference. It shows direction, not size. It needs
  an addressed-tape form that does not exist yet.

**B2. The three-pass host test.**

Andrew ruled on 11-09 that separation is two seams and the charter left the inbox, so
this runs only if he wants it.

- The test: the three passes from `docs/role_charter.md`, and on the same day one
  ordinary `/live` session as the comparison. Without the comparison there is nothing
  to judge "better" against.
- Measure: for each of the two sessions, how many gated turns he answered, and one
  line: would he open this again tomorrow.
- Pass: the three-pass session gets a yes and the ordinary one does not, or it gets
  more answered turns.
- Fail: they feel the same, or the ordinary one is better. Then a separate host buys
  nothing he can feel, and the two seams stand as the whole plan.

**B3. Ear supply.**

The claim to test is the constitution's: following a new spoken exchange without
captions.

- The unit: a new exchange of 20 to 30 seconds, built only from words he has been
  taught, played once with no captions. He answers three questions in English: who,
  did what, and what happens next. Two of three right is a followed exchange.
- The number: twelve exchanges in two weeks.
- Pass: eight or more followed.
- Fail: four or fewer.
- Five to seven is no answer: run twelve more.
- Supply today: three ear tests in seven weeks. At that rate twelve takes over six
  months. The test needs about one a day, which is one per live session or one per
  day's push.
- Limits: twelve separates "mostly follows" from "rarely follows". It cannot tell 60%
  from 70%.

## Job C — the binding constraint

**Contact.** There has been no session since 10-30 and not one tested observation in
November. Days with any contact ran six to seven a week through early September and
three or fewer since. Every open question in the prompt (the seat, the ear, the host)
needs him to show up before it can be measured, so nothing else is binding yet.

- One number: 0 tested observations in November.
- One file and line: `scripts/live.py:238`.
- One proposal: before Andrew runs the three live sessions that are now the gate for
  11-19, let any turn in which he says the current target be graded, not only the
  judge turn. Python already refuses a credit for words he did not type
  (`live.py:219`), and that check stays.
- Theory: the scene says the target twice before the gate, so he will often answer
  early. Today that is the case the lane records worst.
- Evidence: two of two correct productions unbooked in the sandbox run.
- It worked if: in the three sessions, no close prints "0 gate(s) booked" while his
  own lines contain a target.
- It made things worse if: a gate is booked for a line that only echoes Anna's last
  turn. Echoes should stay capped at hinted, as now.

**Do not touch:** the observation ledger and its single writer, the smoke suite, and
the live clock itself.

**The next step is a test, not a build:** three real live sessions. The repair above
is the only thing I would do first.

## For Andrew to decide

1. Repair the live booking before your first live session, yes or no.
2. Let an unanswered scene keep the previous beat, yes or no. It is two lines.
3. May the household say your name in an episode? The canon says yes and the checker
   says no. One of them has to change before November's finale.
4. The three leftovers of October in Job A, item 2.
