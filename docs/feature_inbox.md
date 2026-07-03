# Feature Inbox

Build-itches land here instead of in the codebase. The structure is frozen at **Anna 1.0**; when the urge to re-engineer strikes mid-session, write it here in one line and keep learning. Review deliberately, later — never in the moment. Adding a row of data is learning; changing a schema waits.

## Ideas

- **Voice loop (speech-IN half)** — let Anna *hear* Andrew: a phone voice-note lands, gets transcribed, judged like a knock reply. The speech-OUT half shipped 2026-07-02 as the drill track (`render_drill.py`); what remains open is Andrew's voice coming back in.
- **Pull the wife in as the north star** — the real viability floor is "can I say this to her." Anna could hand a line: "try this one, tell me how it landed tomorrow." Costs no code.
- **Drill as a knock modality** — `morning_knock.py` could choose "drill" and commission `render_drill.py` itself (today Anna-in-session or Andrew runs it). Wait until a few drills prove the format.
- **Per-word verdicts in the reply judge** — one verdict per reply flattens multi-word
  fires: 2026-07-02 19:18 the gauntlet reply fired three deck items unaided, and the single
  "hinted" verdict capped all of them. A `fired: [{word, verdict}]` judge schema would
  credit each word honestly — matters while the sprint burn-rate is the headline meter,
  since the multi-line gauntlet replies are exactly what's being trained. Found 2026-07-03
  during the philosophy audit.

## Shipped

- ~~Day-zero ticket guard~~ — DONE 2026-07-03: `suggest_targets.py` (and `generate_callbacks.py`) now treat an *empty* lexicon as valid day-zero state; only a missing file errors. A fresh learner gets a real first-session ticket.
- ~~Knock digest could carry the ticket's deck top~~ — DONE 2026-07-02: `build_digest()` appends the deck-due menu (fire + ear-only), and the mandate points `expected_target` at it.
