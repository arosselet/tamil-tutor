# Feature Inbox

Build-itches land here instead of in the codebase. The structure is frozen at **Anna 1.0**; when the urge to re-engineer strikes mid-session, write it here in one line and keep learning. Review deliberately, later — never in the moment. Adding a row of data is learning; changing a schema waits.

## Ideas

- **Voice loop (speech-IN half)** — let Anna *hear* Andrew: a phone voice-note lands, gets transcribed, judged like a knock reply. The speech-OUT half shipped 2026-07-02 as the drill track (`render_drill.py`); what remains open is Andrew's voice coming back in.
- **Pull the wife in as the north star** — the real viability floor is "can I say this to her." Anna could hand a line: "try this one, tell me how it landed tomorrow." Costs no code.
- **Drill as a knock modality** — `morning_knock.py` could choose "drill" and commission `render_drill.py` itself (today Anna-in-session or Andrew runs it). Wait until a few drills prove the format.
- **Real-media library (songs, kids' TV)** — the Jabberwocky principle: melody stores sound-sequences below comprehension (Andrew still carries sung gibberish from decades ago). Curate Oracle-vetted YouTube links (her childhood film songs, Tamil Dora) as rows of data; Anna sends one as a no-ask dose, lore-style — a skill, not a DJ persona. Feeds the starving catch axis (0/8) and buys shared cultural ground before the trip. Guardrails: stop-chasing-listens applies in full (zero-debt, no follow-up); curation happens at the laptop, studio-style, never in-session. Machinery (a knock "song dose" type) waits until the library exists and a few doses prove the format by hand.

## Shipped

- ~~Per-word verdicts in the reply judge~~ — DONE 2026-07-03 (same day it was found —
  Andrew approved building it): the judge grades each fired word on its own
  (`fired: [{word, verdict}]`), Python derives the reply's overall verdict as the best
  word, the revealed-cap stays deterministic per word, and the burn rate reads the new
  `reply_fired_cold` (legacy entries fall back to the old flat count). Evidence that
  motivated it: 2026-07-02 19:18, three deck items fired in one reply, all flattened to
  the single "hinted".
- ~~Day-zero ticket guard~~ — DONE 2026-07-03: `suggest_targets.py` (and `generate_callbacks.py`) now treat an *empty* lexicon as valid day-zero state; only a missing file errors. A fresh learner gets a real first-session ticket.
- ~~Knock digest could carry the ticket's deck top~~ — DONE 2026-07-02: `build_digest()` appends the deck-due menu (fire + ear-only), and the mandate points `expected_target` at it.
