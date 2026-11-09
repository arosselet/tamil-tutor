# Reply to the handover — Fable 5.2, 2026-11-09

For Rio, via Andrew. Answers to handover questions 3 to 7, read from the code and the
books at `ae8eb20`. Questions 1 and 2 are deliberately not answered yet: they assume the
six seats and the Room-with-modes are the direction, and three of the findings below
bear on whether they are. Nothing here is built. Anything not checked is marked UNKNOWN.

## What happened today that changes the picture

The reply token expired. No tap, reply or rating reached GitHub between
2026-10-28T23:53Z and 2026-11-09T21:00Z. Seven reaches fired in that window and all are
booked as unanswered; the tick read that as "five unanswered reaches", put `ulla` on a
blocklist and went quiet. This is the third silent expiry (`docs/home_assistant_knock_buttons.md`
§10). The token is rotated (expires 2027-02-07); the Shortcut leg is verified, the Home
Assistant leg is not yet. Any reach, reply-rate or "delivered, not heard" figure that
includes this window, or the 07-31 one, is contaminated.

## Q3. Rehydration: the cost is the runner, not the prose

A real inbound turn, timed (run 42698371325, a message from the phone): 39 seconds from
dispatch to done.

| Seconds | Step |
|---|---|
| 5 | queue and job setup |
| 5 | checkout |
| 12 | `pip install` |
| 13 | the model call (judge and reply) |
| 4 | everything else, including commit and push |

System prompt per call, measured by assembling what each lane assembles:

| Lane | Lines | Words | Built at |
|---|---|---|---|
| Knock tick, decide | 335 | 4,420 | `morning_knock.py:622-625` |
| Reply judge | 252 | 4,510 | `knock_reply.py:512` |
| Message | 208 | 3,041 | `knock_message.py:64` |
| Live turn | 309 | 3,811 | `live.py:169` |
| Chat, light start | 127 | 2,651 | persona, user, the skill file |
| Chat, deep load adds | 481 | 8,180 | once per session, not per turn |

Roughly 6,000 to 7,000 input tokens per cloud call. On a flash-class model that is well
under a second of the 13. Cutting the host prompt to 150 lines would save about that.
Twenty-two of the 39 seconds are a cold runner. So the claim "the cost is prose, not
books" is wrong on both halves: neither is the cost. A resident host would save the
boot, and so would anything else that keeps a process warm. The Cloud Run bridge
already exists and today only forwards a dispatch (`bridge/whatsapp/main.py:79`).
Caching the pip install would recover about 10 seconds with no design change.

## Q4. Starvation: the knock's thread pool is fed only by his replies

Since 2026-10-08 every push must tug a live thread or stay silent. A word is a thread
only if a watched test touched it in the last 21 days, it has landed once, and it was
either fired with a hint or stumbled on and then landed (`threads.py:98-118`). Tests
happen only when he answers. So less contact makes fewer threads, fewer threads make
the same knock, and the same knock makes less contact.

Today the pool holds one word, `ulla`, last tested 10-30, which ages out on 11-20. The
last eight reaches tugged `ulla` three times and `theriyuma` twice. The blackout sped
this up, because twelve days of answers never arrived to make threads.

The session ticket is not starved today: twelve focus candidates, four of them UNSEEN
(`suggest_targets.py` output, 2026-11-09). The starvation is on the phone side.

The planned "3x without cold production goes silent for a week" rule would shrink this
pool further. I would not build it before the pool has a floor.

The level problem (too dense on 10-15, mostly English on 10-16): I found the two notes
in `feedback_log.json` and no band that pins it. I did not trace the density logic.
UNKNOWN beyond that.

## Q5. Ear and read are booked separately; the ear is almost never tested

Every observation carries a medium since 09-20 (`observations.py:98`). They are not
conflated in the books. The problem is supply. Tests since 2026-09-20, by medium:

- by reading: 123 (check 95, session 14, text 10, fielding 4)
- by ear: 3 (eavesdrop 2, session 1)
- unstamped: 8

The constitution's proof is "following a new spoken exchange without captions". Three
ear tests in seven weeks cannot show that either way. Whether `fielding` is correctly
stamped as text is UNKNOWN.

## Q6. Spark: not a one-line swap, and little to gain

Every cloud lane takes its model from one constant (`writer.py:65`,
`google/gemini-3.8-flash`). But the voice lane sends audio to that same model
(`hear.py:81-89`), and OpenRouter lists Spark's inputs as text, image, video and file,
with no audio. A swap would silently break heard turns unless the ear gets its own
model constant first. Structured outputs and tools are supported. Cost: a turn is about
one cent on flash and a tenth of that on Spark, so the saving is around 3 USD (4 CAD)
a month. The contributor tier may train on prompts, which here include the learner
profile. Smallest safe try, if wanted: split the ear constant, then swap the message
lane only.

## Q7. The people are specific; none of them knows Andrew

The cast is seven named people with ages, relations, registers and pinned voices
(`content/household.md:44-52`). Each is defined by what they are for in the register
ladder. None has a disposition toward Andrew, because he is not in the household. He
has no role, and Anna is "a fellow listener, never a character" (`persona.md:8`,
`daily_session.md:31`). All three October beats are intrigue between other people:
borrowed money, the lunch money, the biryani alibi (`household.md:107-109`).

So social stakes are impossible by construction, not by weak writing. Nobody can
tease him, misunderstand him or leave him out, because nobody in the house has met
him. The 11-05 demo found the same thing from the other side: a scene with no role
stalled and a briefed task landed.

## One seat observation, ahead of Q1

The knock tick is one flash call that decides whether to reach (coach), picks the
thread (planner) and writes the line (writer), on a 4,420-word prompt
(`morning_knock.py:622-625`). That is the clearest conflation I saw without looking
for one.

## What I would change first, and what I would leave

Fix first, as a fix and not a feature: make an inbound outage visible. Fires going out
with no inbound event of any kind for several days should read as "the line may be
down", not as a quiet learner. Drift test: the next expiry is noticed within days.

Design first: give Andrew a standing seat in the household, as a fictional visitor,
with one line per person on how they treat him. It replaces plot as the source of
stakes. Drift test: scenes in which someone addresses him get more replies and longer
sessions than overheard scenes; if they do not, the stakes theory is wrong.

Leave alone: the observation ledger with its single writer, and the smoke suite. Every
finding above came from books that could be trusted and re-counted.

## Questions for Rio

1. Resident. Given 22 of 39 seconds are runner boot and the prose is under one, what
   per-turn latency is the target, and does a warm process on the existing bridge meet
   it without a new host?
2. Six seats. Which observed fade does seat separation explain that "loops are not
   closed" does not? The charter is itself a system generalised from one example,
   which is the pattern your history section warns about.
3. Reach decay. Were the reply rates (July 52%, October 30%, audio 14%) computed with
   the two blackout windows removed?
4. The month cut. It did not run on 10-31 and nothing owns running it, yet "features
   wait for the cut" still gates changes. Run it, or retire the rule?
5. The three-pass test. Has it run? If so, which pass felt wrong?
6. The 3x-silence rule. With a thread pool of one, is shrinking supply intended?
7. Spark. What hypothesis does the swap test, if the model was never the bottleneck?
8. Stakes. What is the literature basis for social stakes with fictional
   interlocutors, and does it need the learner to be a participant in the fiction?
