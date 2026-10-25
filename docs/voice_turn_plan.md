# Voice turns — talking to Anna, one turn at a time

**Status:** SPEC, not built. Filed 2026-10-25 (Andrew, @build session). Waiting on
Andrew's ruling at the next inbox drain; nothing in this file is policy until a
`DECISIONS.md` line says so.

## What Andrew asked for

> "Can we skip the spike and just build it? … I just want to build a back and forth
> conversation with Anna … it can work the same as our knock pipeline and our reply
> pipeline … I'm okay with the turns taking 40 seconds a minute … It's not the full
> agentic harness. It's just turn-by-turn chat."

Press a button, speak for about ten seconds, hit send. A minute later Anna answers aloud
on the lock screen. Answer that, and keep going. Grading pronunciation comes later.

## What it reopens

- **07-09 "Speech-in is parked on evidence, not desire"** and **10-23 "No lane follows
  without the verdict"**. This plan builds the lane before the spike's verdict. It still
  respects what the spike was protecting by doing two things. First, **nothing heard is
  graded in v1.** A voice turn goes to the message lane: Anna answers it and nothing
  scores it. If the ear launders a wrong take into the right one, the conversation still
  works and no rung moves on bad evidence. Second, **every real turn collects evidence.**
  Each clip is kept next to what the ear made of it, so the spike's question (does it
  launder?) gets answered by real use rather than a recording session Andrew keeps not
  doing. `content/spike/voice_spike.py` stays where it is and can still be run. It just
  stops gating the lane.
- Nothing else. The message lane, the push chokepoint, TTS, the `anna` queue and the
  Shortcut auth pattern are all reused unchanged.

## The shape: an ear in front of the lanes we already have

```
 iPhone "Talk to Anna" Shortcut
   1. Record Audio (≈10 s, m4a)
   2. Base64 Encode
   3. PUT  api.github.com/repos/arosselet/anna-voice-inbox/contents/in/<stamp>.m4a   ← PRIVATE repo
   4. POST api.github.com/repos/arosselet/tamil-tutor/dispatches
          {event_type: "voice-turn", client_payload: {clip: "in/<stamp>.m4a", knock_id: <opt>}}
                              │
                 anna.yml (same runner, same `anna` FIFO lane)
                              │
   5. hear.py   — fetch clip (VOICE_INBOX_TOKEN) → ONE multimodal call (OpenRouter → Gemini flash)
                  → {transcript, romanized, meaning, deviations, confidence}
   6. knock_message path, unchanged — text = the transcript, plus a `heard` block on the exchange,
                  voice reply FORCED (voice in → voice out)
   7. speak() → TTS mp3 → commit → jsDelivr URL → push_to_phone(requested=True)
                              │
   lock screen: Anna's audio + a "🎙 Answer" action that re-runs the Shortcut ──▶ (1)
```

The only new code is step 5, plus the wiring to and from it. Everything after the
transcript already runs today for typed messages. That's why this is a small build and
not a harness.

## The unknown Andrew named: getting ten seconds of voice off the phone

The text path works because a typed message fits in `client_payload`. Audio needs
somewhere to live between the phone and the runner. Three options:

| Option | How | Verdict |
|---|---|---|
| **A. Private sidecar repo** | The Shortcut PUTs the clip to `arosselet/anna-voice-inbox` via the Contents API, then dispatches the path | **Recommended.** It uses the same PAT pattern and the same "Get Contents of URL" action the Shortcuts already use. A file of any realistic size is fine. The clip never touches the public repo. Cost: one new private repo, one PAT scope, one new Actions secret. |
| B. Inline in the dispatch | Base64 the m4a straight into `client_payload.audio` | Fewer moving parts, but unproven. 10 s of iPhone "Normal" m4a is roughly 60–100 KB, or about 80–130 KB as base64. That's near the size where dispatch payload limits and the runner's per-env-var limit (128 KB, `MAX_ARG_STRLEN`) start to bite. It also puts Andrew's voice into a public repo's event data. Measure it before relying on it. Don't build on it. |
| C. A clip in the public repo | Same as A, but into `tamil-tutor` | **No.** Public history keeps it forever, and the spike already ruled that "a voice corpus does not belong in a public repo." |

(The "Dictate Text" option needs nothing new and is not this feature. Apple's English
dictation is exactly the Thanglish-mangling ear the 07-09 fear was about, and it throws
away the sound, which pronunciation grading will need.)

### The Shortcut — "Talk to Anna"

These are the same building blocks as Tell Anna (§8 of
`home_assistant_knock_buttons.md`):

1. **Receive** text input from Shortcut / URL. This is the optional `knock_id` when the
   Shortcut is launched from a notification.
2. **Record Audio**: Start *Immediately*, Finish *On Tap*. The 10 s is a habit, not a
   cap. Audio quality *Normal*.
3. **Base64 Encode**, with line breaks set to *None*. If line breaks are left on, the
   Contents API rejects the body.
4. **Format Date** (`yyyyMMdd-HHmmss`) → `stamp`.
5. **Get Contents of URL**: `PUT https://api.github.com/repos/arosselet/anna-voice-inbox/contents/in/<stamp>.m4a`,
   JSON body `{"message": "voice <stamp>", "content": <Base64>}`, with the same three headers.
6. **Get Contents of URL**: `POST …/tamil-tutor/dispatches`,
   `{"event_type": "voice-turn", "client_payload": {"clip": "in/<stamp>.m4a", "knock_id": <Shortcut Input>}}`.
7. **Show Notification** "Sent — Anna's thinking". This is the only feedback until the
   answer lands.

The PAT gets one more repository in its *Only select repositories* list
(`anna-voice-inbox`, with Contents: Read and write). Add a row to the PAT rotation log
when it's re-minted.

### Closing the loop from the lock screen

`push_to_phone` already carries `knock_id` in the notification's action data. The HA
notify automation gets a third action next to Got it / Reply:
`🎙 Answer` → `uri: shortcuts://run-shortcut?name=Talk%20to%20Anna&input=text&text=<knock_id>`.
This is the URL-scheme route that Rate From Notes already uses. Tapping it unlocks the
phone, opens Shortcuts and starts recording. That one tap is the whole "turn" gesture.
Recording needs the phone unlocked and in the foreground, which iOS requires anyway.

## The runner side

- **Trigger:** add `voice-turn` to `repository_dispatch.types` in `anna.yml`, then add
  one step:
  `if: github.event.action == 'voice-turn'` → `python scripts/hear.py --clip "$VOICE_CLIP" --knock-id "$VOICE_KNOCK_ID"`,
  with both values passed through `env` and never spliced into the script, same as the
  note lane.
- **New secret:** `VOICE_INBOX_TOKEN`, a fine-grained PAT with Contents: Read and write
  on `anna-voice-inbox` only. `GITHUB_TOKEN` can't read another repo.
- **`scripts/hear.py`** (one job: turn a clip into text Anna can answer):
  1. Fetch the clip with the raw media type (`Accept: application/vnd.github.raw`). The
     JSON form base64-wraps it and caps at 1 MB.
  2. Run one ear call. This is the spike's `hear()` lifted as-is: OpenRouter, the writer
     model, `input_audio`. The ear mandate is the spike's **context** condition, filled
     with the open ask from the knock if there is one. That condition is the one meant
     for conversation hearing. The **target** condition is for coaching hearing, which
     is level 2.
  3. **Format.** OpenRouter documents `wav` and `mp3` for `input_audio`. Gemini itself
     accepts AAC. The first build slice sends the m4a as-is. If that's refused, it
     transcodes with the `imageio-ffmpeg` wheel (a pip-installed static binary).
     **Don't use apt.** The ffprobe apt step is skipped on `repository_dispatch` on
     purpose (latency), and it's the step that hung the lane for six hours on 08-18.
  4. Hand off to the message lane with `text = transcript` and the intent forced to
     `message`. Force the voice reply, so voice in always gets voice out. Use the
     existing `FORCE_VOICE_ADDENDUM`.
  5. Stamp the exchange with `channel: "voice"`, `clip: "<private path>"` and
     `heard: {transcript, romanized, meaning, deviations, confidence, model}`.
     `render_chat` then shows that the turn was spoken and what the ear thought it heard.
     The clip itself stays private. Only the path is public.
- **Failure has to be loud.** A clip that won't fetch, or an ear that errors or returns
  `confidence: low` with an empty transcript, still pushes something:
  "Couldn't hear that one — try again?" A voice turn that dies silently is the
  `expired-PAT` outage again, and Andrew would read it as Anna ignoring him.
- **Retention:** clips stay in the private repo as the real-use corpus (see "Level 2").
  Whether old clips get pruned is Andrew's call. It's not needed for v1.

### What a turn costs in time (estimated, not measured)

| Leg | Rough |
|---|---|
| Shortcut upload + dispatch | 2–4 s |
| Dispatch → runner picks it up | 5–30 s (longer if a render holds the `anna` lane) |
| checkout + setup-python + `pip install` | 25–40 s |
| ear call (10 s of audio ≈ 320 tokens) | 3–8 s |
| message judge (existing) | 5–15 s |
| TTS + commit/push + jsDelivr prewarm + HA push | 8–15 s |
| **Total** | **≈ 50–110 s** |

That's inside the "40 seconds to a minute or whatever it takes" Andrew accepted. Cheap
v1.5 speed-ups, none needed to ship: a pip cache, and skipping the drain and payoff steps
on `voice-turn`. A warm, continuously running substrate is v2, and Andrew named it as v2.

The known tradeoff is the shared FIFO. A voice turn can wait behind a rotation render,
because the 07-28 ruling put one writer first and lock-screen latency second. Leave that
as it is and measure it. Ten real turns will say whether it actually happens.

## Level 2: grading pronunciation (not v1)

The ear already returns `deviations` on every turn. In v1 they're **logged, never
applied**. Promoting them to coaching (Anna says "your ற was trilled") or to a rung needs
a laundering check on real data. That means a handful of turns where Andrew says
something deliberately wrong, plus the spike's `report` logic run over the voice-inbox
corpus instead of a recording sheet. That's the spike, done in place: the measurement
comes from the conversation instead of blocking it. Speech that's graded as a *rep*
(production axis, cold fires) also waits on that check. That's when the reply lane, not
the message lane, would start taking voice.

## Build slices (for the session that builds it)

0. **Andrew, by hand (≈15 min):** create the private repo `anna-voice-inbox`, add it to
   the PAT, mint `VOICE_INBOX_TOKEN`, add it as an Actions secret.
1. **Ear on the laptop.** Record one m4a on the phone and AirDrop it over. Run `hear.py`
   against it locally with `--dry-run` (no message lane, no push). This proves the
   format question and the Thanglish transcript in one go, on a real clip. **This is the
   only gate.** If the transcript of a plain Tanglish sentence is unusable, stop and
   rule again.
2. **Runner wiring:** the `voice-turn` dispatch, the step, the secret and the loud
   failure push. Add a smoke case that `voice-turn` routes to `hear.py` and that a failed
   ear still pushes. Map `hear.py` in `PROTOCOL_MAP.md` (s125 checks this).
3. **Shortcut:** build Talk to Anna from the steps above, and add §8.8 to
   `home_assistant_knock_buttons.md`.
4. **Lock-screen loop:** add the `🎙 Answer` action to the HA notify automation. This is
   Andrew's edit, in the gitignored mirror.
5. Ten real turns, then read the `heard` blocks before saying anything about level 2.

## What it replaces

The 07-09 and 10-23 gate on a lane. Nothing in the code. The lane is additive and sits
in front of `knock_message`.
