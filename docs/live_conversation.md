# Live conversation — the gated rotation, and WhatsApp as its medium

**Status:** BUILT 2026-10-26 (inbox drain, Andrew). The Claude Code cloud simulation
(`/live`) runs today. The WhatsApp half is code-complete and tested with stand-ins.
It goes live once the Meta app, the Cloud Run bridge and three repo secrets exist
(setup below). Audio, a hosted turn loop and pronunciation are **not** built.

## What it is

A new mode, separate from the knock lanes, which it leaves alone. It's a back-and-forth
with Anna, paced for a walk:

```
open → volley → volley → GATE → judge + recast → volley → volley → GATE → …
```

- **Python owns the clock** (`live.next_job`). The model writes one turn for the job
  Python names.
- **Short turns.** `mandates.LIVE_TURN_WORDS` (30) is stated in the mandate and enforced
  with one re-ask. A turn still over the cap is kept whole and stamped `over_cap`. That
  stamp is the walk-pacing evidence this simulation exists to collect.
- **One target per gate** comes from `suggest_targets.drill_menu`, in its own order.
  UNSEEN items are skipped (teach-first). The target is woven into Anna's volleys, and
  the gate invites him to say it back. If he answers in English, nothing is demanded.
- **Context per turn:** the whole session transcript, the ticket's target, `threads.block`,
  the household canon, profile.md's Calibration Notes, and the voice canon.

## State

`progress/live_session.json` holds the session: transcript, targets, phase. It lasts the
whole session, not the message lane's 24h/8-turn window, and no scene decay applies
inside it. **Nothing in it votes.** `close` books what the gates earned, through the
seams every lane uses:

| What | Seam | Stamp |
|---|---|---|
| A gate he tried (`cold`/`hinted`/`miss`) | `lexicon_view.observe`, production, `tested` | `channel: "live"` |
| A slip from a recast | `slips.append_slips` | `lane: "live"` |
| A note about the system | `reply_common.record_meta_note` | `[phone]` |

**Cold is capped at hinted.** He heard the target in Anna's volleys first, so a live gate
is never a cold test. **A fire must quote what he typed.** A gate he didn't try books
nothing. The next session starts from the books, not the old transcript.

## Two ways in

| Path | How | Commits |
|---|---|---|
| **Simulation** | `/live` in a Claude Code cloud session: the agent relays his line to `live.py turn` and prints Anna verbatim. The writer is `claude -p` (`writer.have_agent`). | At close |
| **WhatsApp** | Meta webhook → Cloud Run bridge → `live-turn` dispatch → `anna.yml` → `live.py whatsapp` → Meta Cloud API | Every turn (each turn is a separate run) |

On WhatsApp a session ends on `bye`/`stop`/`done`/`end`, or when a turn arrives more
than 3 hours after the last one. That turn closes the old session and opens a new one.
A turn takes about a minute (one Actions run). So this tests format and narrowness,
not live speed.

## The bridge (`bridge/whatsapp/main.py`)

GitHub Actions can't be a public webhook. Meta can't send a GitHub token, and GitHub
can't answer Meta's verification GET. The bridge does exactly that translation:

- it echoes the handshake;
- it checks `X-Hub-Signature-256`;
- it keeps text messages from the one allowed sender and dispatches `{text, id}`;
- it always answers 200, and `live.py` drops a repeated id.

The bridge holds no state and has no dependencies beyond the Python standard library.
**His number never rides the dispatch**, because a public repo's run is public; the
runner answers `WHATSAPP_TO`, a secret.

## Setup

Step by step, including which Google identity deploys the bridge and which one runs it
(not the TTS key): **`docs/live_setup.md`**.

Knocks stay on the phone push. Outreach that Anna starts on WhatsApp after 24 hours of
silence would need a pre-approved template, so WhatsApp adds to knocks before it could
ever replace them.

## The gate this build is for

Before audio: **does gated talk last, is it enjoyable, does it feel like a conversation
rather than a graded quiz, and does it expose gaps that typed tests hide?** Read the
`over_cap` stamps and the gates' verdicts in the session files, and ask him.

After that, in order:

1. Audio at either end: WhatsApp voice notes downloaded server-side by media ID, through
   `hear.py`; `speak()` for answers.
2. A hosted turn loop for replies within seconds.
3. Pronunciation, which is out of scope (level 2, the spike).
