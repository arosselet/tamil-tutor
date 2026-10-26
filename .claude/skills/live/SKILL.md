---
name: live
description: Talk with Anna live — the walk-paced gated rotation (short turns, a gate every few turns, nothing graded until close). The Claude Code cloud simulation of the WhatsApp lane. Use when Andrew says "live", "let's talk", "walk with me", or types /live. NOT the daily session (/anna) and NOT engineering.
---

# Live — be the pipe, not the tutor

`scripts/live.py` is Anna here. Python owns the rhythm (open → volleys → one gate →
judge and recast → next target) and the model writes each turn. This simulation tests
whether short gated turns hold up on a walk, so **you add nothing**: no commentary, no
coaching, no summaries between turns. Anything you add is the desk verbosity being tested.

1. **Open.** `python scripts/live.py start`. If a session is already open, carry on with it
   (`python scripts/live.py show` prints where it stands). Print only the `ANNA:` line.
2. **Each turn.** Pass his message through exactly as he typed it:
   `python scripts/live.py turn "<his words>"`. Reply with Anna's line **verbatim**, and
   nothing else. A turn takes a while; that is expected.
3. **Close** when he says bye, stop, done or end, or asks to wrap up:
   `python scripts/live.py close`. Then commit `progress/` with the message
   `Live: session closed (simulation)` and push to the branch you are on. Tell him in
   one line what was booked (the close prints it).

If a command fails, say so in one line and stop. Changing `live.py` mid-walk is a
`@build` job for later.
