# The Morning Knock — build plan

A once-a-day **audio push from Anna to Andrew's phone**. Fixes the real bottleneck:
not pedagogy, but the **cold start** — Andrew won't initiate, so Anna knocks. The reps
aren't the chore; the transition into them is. Anna reaching the phone unprompted is how
he *earns* continuity across mediums (not via a fake plot).

Guiding principle: **a text from a friend, not the Duolingo owl.** One message, specific,
swipe-valuable, no nagging, no pile-up.

## The spine
```
GitHub Actions cron (~daily, mid-afternoon, sparse; 10–30 min late is fine)
  → headless Anna reads the briefing (sync_state status + suggest_targets + learner.json)
  → writes ONE fresh short memo (Tamil-script payload, English-led)   ← never a template
  → lightweight single-voice Chirp render  (NOT render_audio.py — skip publish/commit/RSS)
  → commit mp3 (unique daily filename)  →  jsDelivr serves it inline
  → curl Home Assistant webhook (ANNA_PUSH_WEBHOOK_URL)  →  iOS notification
```

## DONE — proven manually 2026-06-28
- **Memo voice/content** locked: pinned Chirp voice `ta-IN-Chirp3-HD-Orus`, English logistics
  + Tamil-script payload. Pull = the one word + a real cold-fire challenge + Andrew's own arc
  ("22 fire cold; this is 23"). Grace for gaps, no manufactured suspense. Chosen prototype:
  `knock_v2.mp3`.
- **Lightweight render** works (scratchpad `render_chirp.py`): reuses `render_audio.generate_segment_google`,
  no lifecycle. GCP TTS via local ADC.
- **HA push** works: automation "Notify Andrew", `notify.mobile_app_blue_dragonfly` (iOS),
  `local_only: false`, title via `title:`, tap via `url:`, `tag: anna-knock` (self-replacing).
  File: `anna_knock_automation.yaml`.
- **Audio delivery** works: `raw.githubusercontent.com` forces download (`content-disposition:
  attachment`); **jsDelivr** (`cdn.jsdelivr.net/gh/arosselet/tamil-tutor@main/...`) serves
  inline `audio/mpeg`. Confirmed: tap → Safari player AND long-press → inline notification player.

## DECIDED
- Daily = lightweight Anna memo; full studio episodes stay occasional/on-demand.
- Knock is **read-only** on the learning brain (observes, never fakes reps).
- v1 = **one knock/day, no nag.** Re-engagement earned later with data, not guessed.
- Lock-screen body carries the Tamil phrase = an un-tapped push still lands a 2-sec rep.
- Click default = audio-play; "sollu →" open-a-session button deferred (needs CC-mobile deep-link).
- **Continuity pivot:** disposable scenes + Andrew's-own-arc, NOT a serialized saga.

## REMAINING
1. **Productionize the render** into a repo script (single voice, no lifecycle, **unique daily
   filename** for jsDelivr freshness).
2. **Headless-Anna generation** — the knock mandate (prompt) + invocation. Decide: `claude -p`
   headless (cron-Anna = chat-Anna; Andrew leaned this) vs plain Anthropic API one-shot.
3. **GitHub Actions workflow** + secrets: OPENROUTER_API_KEY, GCP service-account JSON, HA webhook url.
4. **Protocol edits:** rewrite persona.md "Continuity is the hook" → Andrew's arc; reframe
   `last_debrief` "STORY SO FAR"; extend daily_session.md "Between-Session Nudges" into the
   knock palette (grace / press-play / one-word / arc-reflection — judgment, not a decision tree).
5. Cleanup: prototype mp3s in project root are untracked scratch.

## Decided: generation via OpenRouter
One-shot through **OpenRouter** (OpenAI-compatible, one prepaid account, many models) — sidesteps
the Anthropic subscription-vs-API billing question. `morning_knock.py` calls it with the `openai`
SDK pointed at `openrouter.ai/api/v1`. Model is a one-line swap (`MODEL`): default a top model for
Anna's voice; Gemini Flash a trivial A/B fallback. Secret: `OPENROUTER_API_KEY`. (Confirm exact
model slugs at openrouter.ai/models.) Note: cost ~$1/mo either way — pick the model by ear, not price.
