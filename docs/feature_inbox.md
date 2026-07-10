# Feature Inbox

Build-itches land here instead of in the codebase. The structure is frozen at **Anna 1.0**; when the urge to re-engineer strikes mid-session, write it here in one line and keep learning. Review deliberately, later — never in the moment. Adding a row of data is learning; changing a schema waits.

## Ideas

Endorsed in principle 2026-07-08 (pedagogy review — direction approved):

- **Fixed-time anchor push** — one predictable daily slot alongside the opportunistic reaches; likely the volley's home. **Deliberately deferred 2026-07-08 (Andrew):** watch a week of volley timing first — if Anna reliably fires morning volleys on his own, this is moot; a Python-forced anchor would also reopen "outreach policy is Anna's."
- **Daily spoken reps** — the trip test is mouth-under-pressure, nearly all current production is typed. **Experiment started by hand 2026-07-08:** first drill cut and on the feed ('Cold Fire: Eight Due'); machinery (drill-as-knock, below) waits until a few drills prove the format.
- **Cold decay / re-test dates** — cold is a one-way door today; confirmations at ~2/7/21 days or it demotes. Interacts with the deck meter (headline could go backward mid-sprint) and needs graduation data that doesn't exist yet — **defer past the trip.**

- **Voice loop (speech-IN half)** — let Anna *hear* Andrew: a phone voice-note lands, gets transcribed, judged like a knock reply. The speech-OUT half shipped 2026-07-02 as the drill track (`render_drill.py`); what remains open is Andrew's voice coming back in. **Parked on evidence 2026-07-09 (Andrew):** his block is Thanglish-parse confidence, not friction — run the spike (a few real voice notes through an audio-capable model, no machinery) before building anything.
- **Pull the wife in as the north star** — the real viability floor is "can I say this to her." Anna could hand a line: "try this one, tell me how it landed tomorrow." Costs no code. **Decided 2026-07-09: stays opportunistic** — no daily/scheduled missions; ripe item + obvious moment only (see DECISIONS).
- **Drill as a knock modality** — `morning_knock.py` could choose "drill" and commission `render_drill.py` itself (today Anna-in-session or Andrew runs it). Wait until a few drills prove the format.
- **Single deployment ladder per item** (post-trip) — consolidate the overlapping frames
  (recognition buckets / production axis / floor / engines / deck fire-catch) into one
  per-item stage: heard → understood → spoken-scaffolded → spoken-cold → survived-live,
  everything else derived. From the 2026-07-09 greenfield review; a consolidation, so it
  must *delete* more state than it adds or it doesn't happen.
- **Real-media library (songs, kids' TV)** — the Jabberwocky principle: melody stores sound-sequences below comprehension (Andrew still carries sung gibberish from decades ago). Curate Oracle-vetted YouTube links (her childhood film songs, Tamil Dora) as rows of data; Anna sends one as a no-ask dose, lore-style — a skill, not a DJ persona. Feeds the starving catch axis (0/8) and buys shared cultural ground before the trip. Guardrails: stop-chasing-listens applies in full (zero-debt, no follow-up); curation happens at the laptop, studio-style, never in-session. Machinery (a knock "song dose" type) waits until the library exists and a few doses prove the format by hand.

## Shipped

- ~~Explicit contrast beat~~ — DONE 2026-07-08 (same-day canon amendment, Andrew approved):
  a recast may carry ONE clause of why, by example, never terminology — one clause is a
  beat, two is a lecture. Canonical in `constitution.md` → The Contrast Beat; echoed in
  persona/daily_session/judge mandate.
- ~~Per-word verdicts in the reply judge~~ — DONE 2026-07-03 (same day it was found —
  Andrew approved building it): the judge grades each fired word on its own
  (`fired: [{word, verdict}]`), Python derives the reply's overall verdict as the best
  word, the revealed-cap stays deterministic per word, and the burn rate reads the new
  `reply_fired_cold` (legacy entries fall back to the old flat count). Evidence that
  motivated it: 2026-07-02 19:18, three deck items fired in one reply, all flattened to
  the single "hinted".
- ~~Day-zero ticket guard~~ — DONE 2026-07-03: `suggest_targets.py` (and `generate_callbacks.py`) now treat an *empty* lexicon as valid day-zero state; only a missing file errors. A fresh learner gets a real first-session ticket.
- ~~Knock digest could carry the ticket's deck top~~ — DONE 2026-07-02: `build_digest()` appends the deck-due menu (fire + ear-only), and the mandate points `expected_target` at it.
