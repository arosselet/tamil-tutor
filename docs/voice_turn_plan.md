# Voice turns — talking to Anna, one turn at a time

**Status:** SPEC, not built. Filed 2026-10-25 and revised the same day after Andrew's
second pass (@build session). Waiting on Andrew's ruling at the next inbox drain;
nothing in this file is policy until a `DECISIONS.md` line says so.

## What Andrew asked for

> "Can we skip the spike and just build it? … I just want to build a back and forth
> conversation with Anna … it can work the same as our knock pipeline and our reply
> pipeline … I'm okay with the turns taking 40 seconds a minute …"

And on the second pass:

> "I actually want something more like what I've already worked in the knocks and the
> knock replies and the different channels there, where I can initiate a conversation
> and you have some tools to take feedback, or I can answer a question and you can figure
> out what I was trying to answer … grade it on the intention and the ways in which I was
> wrong, which is not about pronunciation, but there will be multiple right answers. And
> if I'm on the right track, Anna shouldn't just be saying, nope, that's wrong … 'oh, hey,
> you could also say it this way.'"

And the working theory he's building on:

> "Tanglish isn't a weird invention … people … will send messages in phonetic English
> instead of using Tamil characters, even though they're saying entirely Tamil sentences
> … I'm imagining the model will [cope], and I'm not waiting for the spike. That's still
> going to come, but I imagine I can get something conversational."

So voice is **a new way in to every channel that typing already reaches**. It is not a
separate conversation lane. Andrew can start a conversation (message), answer a knock
(reply, graded on intent), give feedback, or ask for audio or a scheduled ping. Spoken,
he gets the same tools he gets typed.

## The shape: an ear in front of `knock_reply.py`

```
 iPhone "Talk to Anna" Shortcut
   1. Record Audio (short, m4a)
   2. Base64 Encode
   3. POST api.github.com/repos/arosselet/tamil-tutor/dispatches
          {event_type: "voice-turn",
           client_payload: {audio: <base64>, knock_id: <opt>, intent: "message"|"reply"}}
                              │
                 anna.yml (same runner, same `anna` FIFO lane)
                              │
   4. hear.py   — read the clip from $GITHUB_EVENT_PATH (never env, never logged)
                  → ONE multimodal ear call (OpenRouter → Gemini flash), BLIND to the target
                  → {transcript (Tanglish, as he'd type it), meaning, confidence}
   5. knock_reply.py, unchanged routing — exactly as if he'd typed the transcript:
         intent=message → message lane (requests, scheduling, meta-notes, audio asks)
         intent=reply   → reply judge (intent-graded, substitutes credited, recast)
                          or the catch lane, whichever the knock calls for
      plus: a spoken answer is forced (voice in → voice out), and the exchange is
      stamped `channel: "voice"` with the ear's `heard` block
   6. speak() → TTS → commit → jsDelivr → push_to_phone(requested=True)
                              │
   lock screen: Anna's audio + "🎙 Answer" (re-runs the Shortcut with this knock_id) ──▶ (1)
```

The first draft sent every voice turn to the message lane, where nothing is graded. That
was the safe choice and the wrong one. Once a turn has become text, `knock_reply.py`
already does the routing Andrew described, so the ear just hands it over.

## Getting the audio off the phone, with no new repository

The first draft proposed a private sidecar repo. Andrew pointed out that a private repo
opens the much larger question of what else in this public repo is really private
(profile, family, state). That question is real and is filed on its own (see the inbox).
**This feature doesn't need to settle it**, so it doesn't:

- **The clip travels inside the dispatch.** It's base64 in `client_payload.audio`, and
  nothing gets stored anywhere. `hear.py` reads it from the event file at
  `$GITHUB_EVENT_PATH` and **never** through a step `env:` block. Actions prints a step's
  env values into the run log, and run logs on a public repo are public. A typed reply's
  text already shows up there today; the audio must not.
- **The clip is thrown away after it's heard.** Only the transcript and the `heard` block
  are committed, which is the same exposure as a typed reply today. The cost is that v1
  builds no voice corpus, so the laundering evidence that level 2 needs (see below) will
  have to be collected deliberately when level 2 comes up. That's a fair trade for not
  opening the privacy question now.
- **Payload size is the one real unknown.** GitHub documents a 10-top-level-property cap
  on `client_payload` and a "too large" error, but no published byte limit. Third-party
  reports put it somewhere around 50–140 KB. Ten seconds of iPhone "Normal" m4a is
  probably 40–100 KB raw, about a third more as base64. So build slice 1 **measures it**:
  send 5, 10 and 20 s clips from the phone and record which ones land. If a natural turn
  doesn't fit, the options in order are:
  1. a shorter cap in the Shortcut;
  2. lower-bitrate encoding on the phone (Shortcuts' *Encode Media*);
  3. only then, a private store just for audio.

  Option 3 re-raises the privacy question, deliberately, by bringing it back to Andrew.

### The Shortcut — "Talk to Anna"

These are the same building blocks as Tell Anna (§8 / §8.5 of
`home_assistant_knock_buttons.md`), and it uses the same PAT. No new token is needed.

1. **Receive** text input. This is the `knock_id` when the Shortcut is launched from a
   notification's 🎙 Answer.
2. **If** there's no input, show **Choose from Menu** `Message` / `Reply`, the same
   intent split as Tell Anna (08-28). With a `knock_id`, the intent is `reply` and there's
   no menu. The 08-28 lesson holds: no machine can tell those two apart, so the Shortcut
   asks.
3. **Record Audio**: Start *Immediately*, Finish *On Tap*, quality *Normal*.
4. **Base64 Encode**, with line breaks set to *None*.
5. **Get Contents of URL**: POST the dispatch above, with the same three headers.
6. **Show Notification** "Sent — Anna's listening". This is the only feedback until the
   answer lands.

### Closing the loop from the lock screen

`push_to_phone` already carries `knock_id` in the notification's action data. The HA
notify automation gets one more action next to Got it / Reply:
`🎙 Answer` → `uri: shortcuts://run-shortcut?name=Talk%20to%20Anna&input=text&text=<knock_id>`.
Rate From Notes already uses this URL-scheme route. One tap unlocks the phone and starts
recording, and that tap is the whole turn gesture.

## The runner side

- **Trigger:** add `voice-turn` to `repository_dispatch.types`, then add one step:
  `if: github.event.action == 'voice-turn'` → `python scripts/hear.py`.
  Small fields (`knock_id`, `intent`) may go through `env` like the note lane does. The
  audio may not.
- **`scripts/hear.py`** has one job: turn a clip into the text `knock_reply` would have
  received.
  1. **The ear hears blind.** The prompt says who is speaking (an English speaker
     learning Kongu Tamil, code-mixing freely) and asks for what was said and what was
     meant. It **doesn't** get the expected target. In the spike's design, telling the
     ear the target is the condition most likely to launder a wrong take into the right
     one. Kept blind, the transcript is evidence. Told the target, it would just echo the
     target back.
     **The transcript is written in Tanglish**, meaning phonetic Roman letters, the way
     people actually text Tamil and the way Andrew already types to Anna (`poren`, not
     போறேன்). That has two benefits. Downstream, nothing changes: the judge already reads
     phonetic spelling ("poren IS போறேன்; judge the Tamil, not the spelling"), so a voice
     turn looks just like a typed one. It's also more honest: asking for Tamil script
     invites the ear to correct toward standard spelling, while phonetic letters keep
     closer to what was actually said.
  2. **Format.** OpenRouter documents `wav` and `mp3` for `input_audio`, and Gemini
     itself accepts AAC. The first slice sends m4a as-is. If that's refused, transcode
     with the `imageio-ffmpeg` wheel. **Never apt.** The ffprobe apt step is skipped on
     dispatch for latency, and it's the step that held the lane for six hours on 08-18.
  3. **Hand off** to `knock_reply`'s entry point with `text = transcript`, the intent and
     `knock_id` from the payload, and the voice reply forced
     (`FORCE_VOICE_ADDENDUM`, which already exists).
  4. **Stamp** the exchange with `channel: "voice"` and
     `heard: {transcript, meaning, confidence, model}`. `render_chat` shows the turn was
     spoken and what the ear made of it.
- **Failure has to be loud.** A missing clip, an ear error, or `confidence: low` with an
  empty transcript still pushes a line: "Couldn't hear that one — try again?" A voice
  turn that dies silently is the expired-PAT outage again, and Andrew would read it as
  Anna ignoring him.

## Grading by voice: on intent, never on sound

The reply judge **already** grades the way Andrew described. `JUDGE_MANDATE` says
"generous in spirit, honest on the axis". Under "CREDIT WHAT HE SAID, NOT WHAT YOU
WANTED", a socially coherent substitute is a real rep and gets credited on its own
merits. It grades word by word and recasts a miss. A voice reply goes through that judge
unchanged. Two additions apply to voice only:

- **`said` matches against the transcript.** Python's rule that "a word he never typed
  can never score" becomes "a word the ear didn't hear can never score". Being blind is
  what keeps that honest.
- **Every voice fire is stamped `channel: "voice"`.** If level 2 later shows the ear
  launders, voice fires can be found and re-weighed. Nothing is lost by grading them now.
  A fire on a turn where the ear reported `confidence: low` is held to `hinted` at most.

**One tension to rule on, separately, because it changes typed replies too.** Andrew
wants "if I'm on the right track … 'oh, hey, you could also say it this way.'" Today the
mandate says the opposite for substitutes: "credit … on their own merits, leave the
untested target where it is, **skip the lesson**". It also says "Keep unsolicited
correction brief". So a good substitute currently gets credit and silence about the
other way to say it. The change would be: on a credited substitute or a hinted near-miss,
the reply line offers one alternative, framed as "also" and not as "instead". The
existing machinery already prices this correctly: any Tamil Anna prints counts as
revealed and caps that word at hinted for 48 h. It's filed as its own inbox line, because
a voice spec is the wrong place to change how every reply is answered.

## Level 2: pronunciation (not v1)

Nothing here judges sound. The `deviations` field from the spike's ear isn't even
requested in v1. Pronunciation coaching needs the spike's laundering check on real takes,
including deliberate wrong ones. Because v1 stores no clips, that becomes a deliberate
session when level 2 is raised: `content/spike/voice_spike.py` as it stands, or a
"keep clips" switch on this lane once the privacy question has an answer.

## What a turn costs in time (estimated, not measured)

| Leg | Rough |
|---|---|
| Shortcut encode + dispatch | 1–3 s |
| Dispatch → runner picks it up | 5–30 s (longer if a render holds the `anna` lane) |
| checkout + setup-python + `pip install` | 25–40 s |
| ear call | 3–8 s |
| judge / message lane (existing) | 5–15 s |
| TTS + commit/push + jsDelivr prewarm + HA push | 8–15 s |
| **Total** | **≈ 50–110 s** |

This is within the minute Andrew accepted. v1.5 speed-ups that aren't needed to ship: a
pip cache, and skipping the drain and payoff steps on `voice-turn`. A warm substrate is
v2. The shared FIFO can make a turn wait behind a render (one writer first, 07-28).
Measure that before acting on it.

## What it reopens and replaces

- **07-09 "Speech-in is parked on evidence, not desire"** and **10-23 "No lane follows
  without the verdict"**. The lane ships before the spike's verdict, on Andrew's bet that
  the model is good enough for conversation. The spike still runs and still decides
  level 2. It's guarded by the
  blind ear, the `said`-in-transcript rule, the `channel: voice` stamp and the
  low-confidence cap, and pronunciation stays out of scope.
- The code is purely additive: one script, one workflow step and one notification
  action. `knock_reply.py`, the judges, `speak()` and the push chokepoint are reused
  as they are.

## Build slices (for the session that builds it)

1. **Measure on the phone (Andrew, ≈10 min):** build a two-action test Shortcut (Record
   Audio → Base64 → dispatch to a no-op event type) and send 5/10/20 s clips. Record
   which ones GitHub accepts. **This is the transport gate.**
2. **First clip on the laptop:** AirDrop one Tanglish m4a and run `hear.py --dry-run`
   (no handoff, no push). This settles the audio format and lets you see a real
   transcript on day one. Andrew's bet is that a current flash model hears
   conversational Tanglish well enough, so this is a quick check, not a gate waiting on
   the spike. Only a transcript that's plainly unusable stops the build.
3. **Runner wiring:** the dispatch type, the step, the handoff, the stamp and the loud
   failure. Add smoke cases for: audio never reaches `env`; the voice turn routes by
   intent; a failed ear still pushes; a low-confidence fire is capped. Map `hear.py` in
   `PROTOCOL_MAP.md` (s125).
4. **Shortcut:** build Talk to Anna and add §8.8 to `home_assistant_knock_buttons.md`.
5. **Lock-screen loop:** add the 🎙 Answer action in the HA automation. This is
   Andrew's edit, in the gitignored mirror.
6. Ten real turns, then read the `heard` blocks next to the verdicts.
