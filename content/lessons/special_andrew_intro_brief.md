# Brief + Beat Sheet — "Andrew Introduces Himself" (the Tamil-speaker demo)

> Companion to `content/scripts/special_anna_intro.md`. Same lane (`special_` prefix,
> `render_demo.py`, no state, no feed), inverted on every axis that matters.
> **This file is the reviewable layer.** Change a beat here and the Tamil gets rewritten
> from it — don't edit the Tamil first.

---

## The Situation This Is Built For

Andrew is standing on a street, in a shop, at a wedding, next to a Tamil speaker who has
just discovered he is learning Tamil. That person is delighted and curious. They are about
to ask him things faster than he can answer.

**The English demo's job:** explain a system to a peer who can follow the substance.
**This demo's job:** explain a *person* to someone who can't check the substance and
doesn't care about it — and then hand the conversation back, warmer than it started.

So the centre of mass moves:

| | English demo | This one |
|---|---|---|
| Subject | Anna (the system) | **Andrew** (the man) |
| Listener | a peer who can evaluate the claim | a stranger who is charmed and curious |
| Language | English carrying Tamil specimens | **Tamil carrying English tech nouns** |
| Andrew's role | narrator-by-proxy, in control | **standing there, exposed, only half-following** |
| Ends on | the family table, a private promise | **an invitation to the stranger to speak to him** |

**The hard constraint that shapes every line:** Andrew has to follow this while it plays.
He can't be standing next to a stranger nodding at his own demo without understanding it —
that's the exact deer-in-headlights the whole system exists to kill. So the Tamil is built
from his own vocabulary fence (191 words), and where the piece needs a word he doesn't
own, the context answers it inside the same breath.

**This is also why the inverted gradient works instead of being a stunt.** In Coimbatore
Tamil the technology words *are* English — phone, code, message, program, podcast, memory,
model. So a Tamil sentence about software is already half-English, natively. The piece
sounds like a local talking about computers, and Andrew can follow it, for the same reason.
The form is the argument: own the joints, the furniture comes free.

---

## Voice & Lane

- **Single voice: Anna**, ta-IN male, `ta-IN-Chirp3-HD-Orus` (his pinned knock voice).
- Fourth wall is **deliberately down** — Anna addresses the stranger directly. The
  fourth-wall and no-learner-name rules in `hosts.md` govern *lesson* episodes; the
  `special_` lane is a README/pocket artefact and the companion piece already breaks both.
  Noted here so nobody "fixes" it later.
- **Target 4–5 minutes** (Andrew, 2026-07-29). Shorter than the English demo, because you
  are standing up and so is the person listening. v4 ran ~6 min; v5 trimmed to ~4.5.
  **Where the time came from, and the rule for next time:** every cut came out of the
  journey's connective tissue and the pause padding. The three grammar structures, the
  fridge, the trade and the invitation were untouched, because that is the payload and the
  back third is where the piece does its work. Lines cut: "one job / four jobs" (the
  hand-copy line already showed it), "before he told me / now I tell him" (the memory beat
  says it concretely), "then he did it a different way" (the turn is the pivot), "I came
  out from the desk" (reduced to one clause), one of two written-vs-spoken statements, and
  a mountain line. Git holds the 6-minute cut if any of it is wanted back.
- Same bans as the companion: no clause that announces what the next clause will do, no
  "X, not Y" antithesis, no em-dashes, no feature enumeration.

---

## The Spine

**A man is trying to move a mountain five pebbles a day, and the hard part was never the
pebbles. It was that nobody could remember which five. So he built something that could.**

---

## The Beats

### 1. Who is talking (~20 sec)
Anna, a program, not a person. The man standing here wrote him. Flat and immediate — the
robot-honesty is the charm, same as the companion. No warm-up.

### 2. Why (~30 sec)
His wife is from Coimbatore. There is a house where everyone talks in Tamil and he sits
there smiling. **This is the image the whole piece hangs on** — every Indian listener has
seen that man at that table, and half of them have been him at some in-law's house. It buys
instant sympathy without asking for it.

### 3. The mountain and the five pebbles (~25 sec)
Learning Tamil looks like a mountain. Five stones a day and in a year the mountain moves.
The difficulty isn't the five stones. It's knowing *which* five today. No human can hold
that for you every single day, which is a statement about time and attention, not about
Tamil.

### 4. How it got built — the real journey (~2 min)

> **Sourced from `docs/JOURNEY.md`.** v1 of this brief invented an "it forgot who he was
> overnight" beat. That's a generic LLM-amnesia story and none of it happened. Any future
> build beat comes out of JOURNEY.md, never out of what these systems typically do. The
> true history is also better drama, because the machine isn't the one who failed.
>
> **Pre-repo history, not in JOURNEY.md (Andrew, 2026-07-29).** The May fade was neither
> the first nor the only one. It went effectively silent **September to November 2025**:
> he hit a complexity wall trying to improve the monolith prompt and stopped. What broke
> the wall was refactoring that single prompt into distinct roles, with Claude Code, which
> is also when he pivoted off browser-Gemini onto a coding agent. This repo was started a
> few months later out of the remnants of that experiment. So JOURNEY.md's Chapter 1 → 3
> jump has a gap in it, and the "separation of concerns" lesson it dates to April was
> actually learned the first time here. **Do not dramatise this in the script** — it earns
> exactly one generalising line after the May fade. It's recorded so no future pass writes
> the fade as a single tidy incident.

0. **Where it actually starts.** He was chatting with a program called Gemini. *You ask it
   something, it tells you. That's all it was.* Then one day the thought: **could this
   teach me Tamil?** So he wrote it some instructions in English, and that was the first
   version of Anna. **No jargon** — "Gemini gem" assumes a vocabulary this listener has no
   reason to have, and the beat is about a man having an idea, not about a product. The
   English instructions here deliberately rhyme with the dialect file in beat 8, which is
   the same move made competently with a lot of hindsight.
1. **The Google Doc.** He then wrote eight weeks of curriculum himself, in advance,
   *before he knew any Tamil.* Then a beat of silence, and the question the stranger is
   already thinking: **how would he know?** A beginner deciding his own syllabus is the
   joke that tells itself.
2. **Four jobs and one job.** Each week he pulled a lesson out of the doc, handed it over,
   got a script back, and hand-copied it into a separate program to get audio. The machine
   had one job. He had four. (Author, renderer, delivery, progress tracker — stated as the
   count, not the list. No enumeration.)
3. **The podcast pivot, and the discovery.** Mid-summer he wanted episodes: **two people
   just talking**, not one voice reciting a lesson. That's when he found out: **the Tamil it
   was writing, nobody speaks.** Written Tamil is one thing, spoken Tamil is another, and he
   had no idea there was a difference when he started. **The fridge lands here** as the
   proof: ask a computer for "fridge" and it says குளிர்சாதனப்பெட்டி. *Who talks like that?
   Here a fridge is a fridge and a bus is a bus.*

   **The pivot is lesson → conversation, never text → audio.** v3 got this wrong and it
   broke the story: beat 2 already has him hand-copying scripts into a TTS tool, so audio
   existed from the start and "better to listen than type" contradicted it. The correction
   is also the better causal claim, and it's why the discovery happened when it did:
   *a lesson can hide in book Tamil; two people chatting cannot.* The script says it
   straight — you couldn't tell while it was writing a lesson, only when two people were
   talking. This also relocates the NotebookLM insight (two voices beat a monologue) to its
   true home, so the reach beat later just refers back to "that podcast."

   This moved in v3. It used to float after the rebuild with no cause. Now the problem is
   *discovered* mid-journey, stays open across the fade, and beat 8 closes it — the listener
   feels the thread pull without being told there is one.

   **Cultural note: this is the most important beat in the piece for the emotional job.** In
   the English demo the fridge is information. Here it's a shared joke at officialdom's
   expense, and it does something else besides: it tells the stranger that this foreigner
   chose *their* Tamil, the one newsreaders and school teachers call improper. That lands as
   respect, and it can't be said out loud without ruining it.
4. **Why a plan is the wrong shape.** *Another* problem: a plan written in advance knows
   what week three contains. It doesn't know what he got wrong on Tuesday. **This is the
   beat you asked for** — curriculum abstracted out of a lesson plan and into what actually
   happened.
5. **He quit.** It got boring. Same words, same made-up scenes. One month, nothing. (May:
   nine commits.) **Then one line saying it happened more than once**, because it did — see
   the pre-repo history above. The script names the May fade concretely and generalises in
   the next breath; it does not narrate a second incident.
6. **The turn, and the moral centre of the piece.** He could have said the fault was his.
   He didn't. *If it's boring, that's the machine's fault.* That is now a rule. This is the
   Enjoyment Clause, stated without naming it, and it's the line that makes the whole
   system make sense to someone who has quit three language apps.
7. **Rebuilt the other way round.** Before: he told it what to teach today. Now it tells
   him. A memory in plain code holding every word, what's warm, what went cold, what he got
   wrong on Tuesday — which is what finally answers *which five stones today.*
8. **The dialect file — beat 3 paid off.** He fixed the குளிர்சாதனப்பெட்டி problem too: an
   English file telling it to talk like Coimbatore. Rhymes with the English instructions in
   beat 0, deliberately.
9. **Reach.** A message to his phone in the morning. A podcast at the bus stop with two
   people talking while he listens in (the NotebookLM insight, compressed to one clause:
   two people talking beats a teacher lecturing). And on a night he comes home wrecked, two
   minutes and goodnight — **the rule from beat 6, visibly running.**

### 5. What Tamil has that English doesn't (~60 sec) — the heart
Andrew's specific ask: things a Tamil speaker has owned since they were small, that have to
be *rebuilt* to be sayable in English. Three, each one line to state and one line to prove:

- **நம்ம / நாங்க.** English has one "we" and it is permanently ambiguous. Tamil has two,
  and the difference is an open door versus a closed one. *நம்ம போலாம்* includes you.
  *நாங்க போறோம்* shuts you out. A Tamil four-year-old never gets this wrong. An English
  speaker has no way to say it at all without adding a whole clause.
- **எனக்கு நேரம் இருக்கு.** English says "I *have* time," as though you'd grabbed hold of
  it. Tamil says the time *exists, to you.* It arrived. It isn't yours. (Using நேரம்
  because he owns it cold — same point as money, zero comprehension cost.)
- **வா / வாங்க.** English has one "come" for your boss and your little brother, and does
  respect with tone and the word "please." Tamil conjugates it into the verb. **And this is
  Andrew's real, current, live failure** — the -ங்க falls off the end when he's under
  pressure. Naming his actual weakness here is what stops the beat being trivia.

### 6. The trade (~20 sec) — the beat that makes the stranger an equal
When *you* learned English, you had to fight "a" and "the." Tamil has no such thing. He got
those for free and now he's paying for it with -ங்க. Even trade.

This is the anti-condescension valve. Without it the piece is a foreigner being praised for
effort. With it, two people are standing there having each done the same difficult thing
from opposite ends.

### 7. The handoff (~25 sec) — the actual function of the artefact
He doesn't speak well. Some of it he'll catch, some he won't. He will try. Speak to him a
little slowly. **Then: say something to him in Tamil. Let's see what he does.**

The piece ends by making the stranger the next move, which puts Andrew in a live rep with a
real person and a warm audience. That is the point of carrying this in his pocket.

---

## Vocabulary Notes (the comprehension audit)

Built from the fence in `suggest_targets.py`. Words used deliberately from **today's**
session, so playing this doubles as a soak: **யாரு**, **தெரியல**, **-னு**, **சில்லறை**'s
sibling frame **இருக்கு**, **போலாம்** (the exact form that beat him today, used correctly
here, which is worth something).

Outside the fence, each answered in-breath by context or an English echo:

| Word | Why it's safe |
|---|---|
| மலை (mountain) | carries its own image; repeated with கல்லு |
| கல்லு (stone) | arrives attached to மலை |
| வாரம் (week) / மாசம் (month) | both arrive holding a number; top-5 acquisitions anyway |
| பாடம் (lesson) | the sentence around it is about teaching |
| மரியாதை (respect) | high-frequency, and the வா/வாங்க demo *is* its definition |
| ஞாபகம் → replaced by English **memory** | Coimbatore says memory |
| நியாயம் (fair) | sits inside the trade beat, which explains it |

Everything else is fence or English noun. **boring** is deliberately the English word —
it's what a Coimbatore speaker actually reaches for, and it's the pivot of beat 5, so it
has to land with zero decoding cost.

**Gap this audit missed, found by the v6 pass (2026-07-30).** The நம்ம/நாங்க door line
(`ஒரு வார்த்தைல கதவ திறக்குறோம். இன்னொரு வார்த்தைல மூடுறோம்.`) carries **three unfenced
items in one sentence** — கதவு, திற, மூடு — sitting mid-payload on a line he plays blind to
a stranger without the caption. The table above accounts for none of them. The surrounding
நம்ம/நாங்க and சின்ன வயசுலயே do carry it and the image is strong enough to survive one
unknown noun, so this is recorded as a *known* cost rather than a cut. Next audit: count
unfenced items per sentence, not just per piece — a beat can pass a whole-script fence
check and still have one sentence the learner cannot enter.

Two more table corrections from the same pass: **நேரம்** is not a standalone lexicon key
(it lives in `நேரம் ஆச்சு` / `நேரம் இருக்கா?`), so "he owns it cold" rests on chunk
membership; and **வார்த்தை** is unfenced, though the script establishes it twice before the
வா/வாங்க beat needs it.

---

## Oracle — RULED (2026-07-31)

The v6 dialect pass deferred seven register questions plus three minor ones. All ten were
put to the Oracle (native Coimbatore speaker, and an engineer — the sheet was written to
peer register, with the coverage and TTS constraints stated rather than hidden). **Her
rulings, verbatim from the sheet:**

| # | Item | Ruling | Effect |
|---|---|---|---|
| 1 | `பொண்டாட்டி` (L84) | **Use `வொய்ஃப்`** | changed |
| 2 | apodosis (L186) | **Keep `நாங்க மட்டும்`** | no change |
| 3 | `மூடு` vs `சாத்து` (L188) | **Use `சாத்து`** | changed |
| 4 | `ங்க-க்கு` (L214) | **It survives** | no change |
| 5 | `விழுந்துடும்` (L206) | **Use `வராது`** | changed |
| 6 | `சரி சமம்` (L214) | **Keep** | no change |
| 7 | `நேரம் வந்திருக்கு` (L194) | **Too portentous** — cut for now | sentence removed |
| — | `ஆளு` (L80) | **Keep** | no change |
| — | `சின்ன வயசுலயே` (L188) | **Keep** | no change |
| — | `கொடு`/`குடு` | **Both are fine** | no change; corpus NOT normalised |

**What the rulings settle beyond this script.** #3 overrode the coverage objection: she chose
the idiom over the fence, so `சாத்து` enters unfenced and the corpus owes it a teach —
the fence argument loses to a native-speaker idiom call, which is the whole point of having
an Oracle. #10 closes the `கொடு`/`குடு` normalisation question in the *negative*: both are
live, so the lexicon keeps carrying both and no repo-wide pass is owed. #1 removes an
unfenced Tamil word as a side effect, which is free.

**#7 was cut, not reworded — and the reason is the finding.** She rejected `நேரம் வந்திருக்கு`
and, asked for a replacement, declined to name one: **"multiple are correct, but it depends on
context"** (2026-07-31). That is a stronger result than any single wording would have been.
The arrival image the beat wanted — *time turning up as a guest that isn't yours* — is not
carried by one fixed phrase in Coimbatore Tamil; the right form is selected by the frame around
it, which is precisely the knowledge a generator working from a static canon does not have.
So the sentence is **removed** and the payoff now rests on the dative alone
(`எனக்கு நேரம் இருக்கு. அது என்னோடது இல்ல.`), which already carries the possession contrast
without reaching for an arrival verb. Revisit when the surrounding frame is settled.

**The generalisable point:** the Oracle's most valuable answers are the ones that refuse the
question's shape. Six rulings picked a form; #7 said the question had no context-free answer.
A system that only records verdicts would have logged this as unresolved and re-asked it; the
useful record is *why* it has no answer yet.

**Line numbers in this brief were stale** (they predated the v6 edits — the old sheet
pointed `பொண்டாட்டி` at L72, which is a comment). The table above is re-verified against
the current file.
