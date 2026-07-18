# Feature Inbox

Build-itches land here instead of in the codebase. The structure is frozen at **Anna 1.0**; when the urge to re-engineer strikes mid-session, write it here in one line and keep learning. Review deliberately, later — never in the moment. Adding a row of data is learning; changing a schema waits.

## Ideas

- **The trip harvest** (2026-07-18, direction approved — build when the Aug 5 campaign
  is drafted): the trip is a field-mission arc, not an exam. Final campaign (Aug 5–12)
  goes rehearsal-shaped — Table Rehearsal dominant, the five-scenario checklist as the
  hard artifact, "survived end-to-end at speed" as that week's meter — and live
  encounters get harvested nightly into the ledger. Context locked in: Andrew brings
  phone + laptop, expects MORE free time not less, and keeps working on/with the system
  through the trip — capture rides the existing channels (session close, knock-reply
  meta_notes); no new plumbing needed.

- **`suggest_targets.py` has zero smoke coverage** (2026-07-17) — the string-mission
  crash proved it load-bearing and untested; one sandbox case (ticket runs end-to-end)
  would have caught it at commit time.

Endorsed in principle 2026-07-08 (pedagogy review — direction approved):

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
- **Payload lint could match inflected stems** — the verbatim check false-flags correct
  inflections (M61: தூக்கு vs தூக்க); a stem-tolerant match would stop the recurring
  manual sidecar repair. See the 2026-07-13 "bends the sidecar" decision for the
  interim rule.
- **Phantom-fired knock on delivery failure** — the knock logs + commits *before* the
  notify step, so a push that fails all retries leaves `acted: true` for a dose Andrew
  never saw (rails count it; judge could grade against it). Seen once (2026-07-14 DNS
  blip, now retried at the chokepoint). A `delivered: false` mark on final failure
  would make the log honest. Wait for a second occurrence post-retry.
- **Real-media library (songs, kids' TV)** — the Jabberwocky principle: melody stores sound-sequences below comprehension (Andrew still carries sung gibberish from decades ago). Curate Oracle-vetted YouTube links (her childhood film songs, Tamil Dora) as rows of data; Anna sends one as a no-ask dose, lore-style — a skill, not a DJ persona. Feeds the starving catch axis (0/8) and buys shared cultural ground before the trip. Guardrails: stop-chasing-listens applies in full (zero-debt, no follow-up); curation happens at the laptop, studio-style, never in-session. Machinery (a knock "song dose" type) waits until the library exists and a few doses prove the format by hand.

## Shipped

- ~~Registration canonical-at-write~~ — SHIPPED 2026-07-17 same evening (Andrew's
  token-discretion grant): `claim_payload()` in `run_studio.py`; corrected diagnosis
  and full record in DECISIONS ("The sidecar must claim the soak payload"). Dupes
  merged; M65/M67 stamps repaired.
- ~~Fixed-time anchor push~~ — MOOT, closed by the 2026-07-17 review on the deferral's own
  test: Anna fires volleys reliably unforced (07-14 15:13, 07-15 15:46, 07-17 13:07 EDT —
  the afternoon slot the 07-13 lunch-anchor decision assigned). No Python-forced anchor;
  "outreach policy is Anna's" stands untouched.
- ~~`frame:idum` has no lexicon record~~ — RESOLVED by 2026-07-17 review: a full record
  exists (new engine record, not folded into done-ittu — gloss even names the boundary:
  "bolts onto a clean single verb, not a compound"). The 07-13 cold fire (`book
  pannidum`) that was skipped for want of a record was applied during the review.

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
