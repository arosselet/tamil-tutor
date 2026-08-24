---
name: debug
description: Symptom-to-root-cause triage for the knock loop, push queue, reply judge, studio/feed, session state, and CI. Use when a knock didn't arrive, a reply scored wrong, the feed is stale, CI is red, the push queue misfired, Anna's behaviour looks like a plumbing bug, or Anna over-uses a format / the doses have drifted samey (behavioural drift is a plumbing symptom too).
---

# Debug — Triage and Root-Cause

## 1. Doctrine

**Evidence before action. Plumbing before persona.**

When Anna seems wrong — forgetful, miscalibrated, missing — read the logs first.
The 2026-07-03 incident ("Anna had no knowledge of my reply") was a same-tick
multi-fire collision in the push queue, 100% plumbing, zero persona involvement.
Full law: `docs/DECISIONS.md` → "Fix the tool, not the personality."

Do not touch prompts, protocol files, or persona until you have a log-confirmed
root cause. If the root cause points to a code change, stop here and use `/extend`
for the fix and `/verify` to prove it.

This applies to **behavioural drift**, not just breakage: "Anna sends too much of
one thing" or "the doses all feel the same shape" is a triage-able symptom whose
evidence lives in the log's move labels and the decide prompt's incentive lines —
never propose a quota, rule, or mechanism from taste alone (KF-8: the drift had a
one-line author in the prompt, and no quota would have found it).

Unfamiliar with the jargon below (rails gate, deck, `expected_target`, soak order)?
Start with `/orient` → `references/glossary.md`.

---

## 2. Triage Table

| Observed symptom | Suspect subsystem | First evidence command |
|---|---|---|
| No knock arrived today | Rails gate blocked, or CI never ran | `gh run list --workflow=anna.yml --limit 10` |
| Knock arrived but no audio / "bad file type" | HA automation template branch | check `knock_log.json` → `audio_url` present? + HA Traces |
| Knock body asked X, reply scored against Y | Coherence mismatch (`expected_target` vs body) | read last entry in `knock_log.json` → compare `body` and `expected_target` |
| Reply scored wrong ("miss" when Andrew fired it) | Judge saw stale / mis-targeted knock | `knock_log.json` last entry → `target_revealed`, `expected_target`, `reply`, `reply_verdict` |
| Push arrived twice (or never) | Push queue multi-fire or drain skip | `python scripts/push_queue.py list` + `knock_log.json` → `scheduled` entries |
| Push arrived at wrong time | Queue entry `due` field / quiet-hours deferral | `knock_log.json` → `rationale` field on `scheduled: true` entry |
| Feed shows stale / wrong episode | RSS rebuild didn't run, or episodes.json out of sync | `grep '<title>' rss.xml \| head -5` vs newest `.mp3` in `published_audio/` (+ `knocks/`) — first titles should match the newest files |
| Status looks wrong (floor/deck numbers) | `lexicon.json` state, compute logic | `python scripts/sync_state.py status` (safe) |
| CI red — smoke workflow | Regression in knock/reply/queue plumbing | `gh run list --workflow=smoke.yml --limit 5` then `gh run view <id> --log` |
| CI red — knock/queue workflow | Missing secret, commit conflict, JSON parse fail | `gh run view <id> --log` |
| Audio knock missing from the podcast feed | Feed refresh failed in that knock run (all audio → feed since 2026-07-05; `publish.py refresh_feed()` is failure-tolerant by design) | `gh run view <id> --log` → look for `⚠ rss rebuild failed`; recover the URL from `knock_log.json` → `audio_url`, or rerun `python scripts/rebuild_rss.py` locally |
| Anna keeps making the same mistake | May be a protocol bug, not plumbing | read `progress/feedback_log.json`; if pattern appears 2+ times → `/extend` |
| **I replied and NOTHING happened — no run, no error, no trace** | Inbound leg dead: expired PAT, or the ANNA_REPLY automation (KF-12) | Actions list → filter `repository_dispatch`. **Zero since a datestamp = the return path, not your reply.** Knocks still arriving PROVES HA is alive — outbound crosses the same HA — so suspect the one thing unique to inbound: the token |
| Anna over-uses a format / doses feel same-shaped | Incentive drift in the decide prompt (a preference line, a reward framing) — not persona | `grep -o '"move": "[^"]*"' progress/knock_log.json \| tail -15` → then read the prompt's incentive lines in `morning_knock.py` |

---

## 3. Per-Subsystem Playbooks

See `references/subsystems.md` — load it when the triage table points to a specific subsystem.

---

## 4. Known Failure Modes (archived bugs — real precedents)

### KF-1: Same-tick multi-fire push collision (2026-07-03, fixed)
**Symptom:** Two queued pushes both due → both fire in one drain tick → Andrew's reply is
judged against the second (last-logged) knock, not the one he was actually answering.
**Root cause:** `push_queue.py cmd_drain` fired all due non-forced entries in one batch;
`knock_reply.py last_fired_knock()` always targets the last `acted=true` entry.
**Fix:** Drain caps at one non-forced fire per tick; the rest defers to the next tick.
**Verify:** `python scripts/smoke_test.py` → section 6 (regression #1).
**Commit:** `1f5b304`

### KF-2: Prose-wrapped LLM JSON killed a knock tick (2026-07-04, fixed)
**Symptom:** Knock workflow shows `Expecting value: line 1 column 1 (char 0)`; no knock fired.
**Root cause:** The decision model occasionally wraps its JSON in prose (or returns empty);
the old parser only handled ` ``` ` code fences, so bare prose raised immediately.
**Fix:** `parse_llm_json()` (in `writer.py`) now: strips fences → tries `json.loads`
→ falls back to the outermost `{...}` slice → prints raw text before re-raising so the
log shows what came back, not just that it failed.
**Verify:** `python scripts/smoke_test.py` → section 1 (regression #2).
**Commit:** `dc1e1fd`

### KF-3: Misaligned expected_target — coherence mismatch (2026-07-03–05, fixed)
**Symptom:** Valid Tamil replies repeatedly scored as "miss"; judge felt rigid for days.
**Root cause:** The knock mandate let Anna write a body for one deck item while setting
`expected_target` to a different one ("evlo naal irupeenga?" graded against "we'll go back").
**Fix:** Coherence law (2026-07-05): pick `expected_target` first, write body as the
ask for that target. Judge voids a mis-targeted knock and grades against the body's natural
answers instead. Teach-before-quiz flag (UNSEEN) on never-soaked deck items.
**Verify:** read last `knock_log.json` entries — `body` and `expected_target` must be
aligned (the body's natural answer should be `expected_target`).
**Commit:** `3c4a534`

### KF-4: HA audio branch silently disabled (2026-07-01, fixed)
**Symptom:** Audio knocks deliver text only — no inline player, no attachment error.
**Root cause:** HA template condition `{{ x is defined and x }}` returns the URL *string*,
which a 2026-07 HA core update counts as falsy → automation always took the else branch.
**Fix:** Condition is now `{{ trigger.json.audio_url | default('') | length > 0 }}`.
**Verify:** HA Automation Traces → check "choice" field; `else` on an audio knock = bug.
**Where:** `docs/anna_knock_automation.yaml` (gitignored mirror; real value in HA).

### KF-5: Playlist masked newest episode / stale concatenation (2026-07-03, removed)
**Symptom:** Feed player shows old episode as the newest.
**Root cause:** `build_playlist.py` built a stale concatenation that appeared first in the
feed; listen-count signal that drove it went blind after the stop-chasing-listens pivot.
**Fix:** Playlist removed entirely. `rss.xml` is the only feed.
**Verify:** `cat rss.xml | grep '<title>' | head -5` — first episode title should match
the newest `.mp3` in `published_audio/`.

### KF-7: Single-quoted Python dict bypassed {..} slice fallback (2026-07-07, fixed)
**Symptom:** Anna Knock CI fails with two chained JSONDecodeErrors: first `Expecting value: char 0`, then `Expecting property name enclosed in double quotes: line 1 column 2 (char 1)`. No raw LLM text printed (the print only fires on the `start == -1` path, not on slice-fallback failure).
**Root cause:** Model returned a Python-style dict (`{'act': True, ...}` single-quoted keys). The `{..}` slice found the braces but `json.loads` rejects single quotes. The tell: second error at `char 1` (char after `{` is `'`, not `"`).
**Fix:** `ast.literal_eval` added as third fallback (handles single quotes + Python `True`/`False`/`None`). Logging added before all re-raise paths so the raw text always prints.
**Verify:** `python scripts/smoke_test.py` → section 1 (single-quoted keys, python-dict in prose).
**Commit:** `1f5c38f`

### KF-6: Chain pin destroyed the ask · menu blind to recency · hallucinated reveals (2026-07-06, fixed)
**Symptom:** Log's `expected_target` absurd vs the body (looked like KF-3 returning);
the same surface ask fired 5× in 4 days under different move names; correct unaided
productions stuck at hinted (a real cold denied for a reveal that never happened);
chat.md showed only the last reply of a chain — real cold fires vanished under a test reply.
**Root cause (three-part):** chained follow-ups overwrote `expected_target` and the reply
fields (only fired lists accumulated); the knock menu (`deck_due_list`, since renamed
`due_menu_block`) ranked ripest-first with no recency signal while outcome memory showed
move names only, so the variety law had no evidence of
same-ask repeats; the judge's reveal-cap trusted model memory of what had been shown.
**Fix:** chain moves `pinned_target`/`pinned_revealed`; every exchange appends to
`exchanges` (chat renders the full chain); menu demotes+marks items asked/shown inside the ask cooldown (3 days then; `ASK_COOLDOWN_DAYS` = 7 since 2026-08-18)
and outcome memory carries the ask; `revealed_recently()` computes reveals from the log —
the judge may cap against that list only.
**Verify:** `python scripts/smoke_test.py` → section 10 (regression #3).
**Commit:** `a13d3b9`

### KF-9: Notifications clobbered each other — deliberate tag, obsolete reason (2026-07-11, fixed)
**Symptom:** Each push replaces the previous on the phone; a volley landed, then vanished
when a lore memo arrived — logged as "no-tap" though Andrew never dismissed it.
**Root cause:** `tag: anna-knock` fixed in the HA notify automation, *commented as
deliberate* ("self-replacing — one knock at a time"). The fence it guarded: the reply
pipeline had no correlation field, so `knock_reply.py` judged every reply against
`last_fired_knock()` — one visible knock at a time made that safe.
**Fix:** Correlation replaces the fence. Every push carries its log-entry timestamp as
`knock_id`; HA sets a unique tag (`anna-<knock_id>`) and echoes the id via the
notification's `action_data`, which the tap-handlers forward through `rest_command` →
`client_payload` → workflow env. `find_knock()` (judge) and `--knock-id` (ack) target
the exact entry; last-fired stays as fallback for id-less events. Notifications now
stack until dismissed.
**Gotcha:** on iOS the `tag` does not round-trip through reply actions — `action_data`
does; that's why the id rides both. And inside a single-quoted YAML `payload:` scalar,
Jinja `default('')` gets mangled by YAML quote-escaping — use `default("")`.
**Verify:** `python scripts/smoke_test.py` → section 14. Live: fire two knocks, reply
to the *older* one, check `knock_log.json` → the reply lands on the older entry.
**HA side must be re-pasted** (automation + both tap-handlers + `rest_command`) — mirrors
in `docs/anna_knock_automation.yaml` and `docs/home_assistant_knock_buttons.md`.
**Live-verified 2026-07-12:** two test fires logged in the same second (microsecond
stamps kept the ids distinct); the ack dispatched while the *other* knock was
last-fired and still landed on the tapped one — full round trip through HA proven.
**Gotchas from the live test:**
- *Mirror drift:* the gitignored automation mirror carried a stale `webhook_id` from a
  half-finished rotation (HA/.env/GHA updated, mirror not) — re-pasting it took all
  knocks down for an evening while HA kept answering 200 (it 200s every webhook POST,
  registered or not; a delivered CI knock earlier the same day is the tell that the
  *sender's* id is fine). A rotation touches all four: HA + GHA secret + `.env` + mirror.
- *Webhook re-registration:* after editing a webhook trigger's id, "reload automations"
  can leave the old listener live — toggle the automation off/on.
- *`mode: single` drops stacked sends:* two webhook POSTs ~1s apart lost the second
  (trigger discarded mid-run). With correlation ids, simultaneous pushes are legitimate
  → the notify automation should be `mode: queued` (HA-side edit).
- *A "missing ack" is usually a body-tap:* tapping the notification body opens the app
  and dismisses it WITHOUT firing any action event — no dispatch, no log entry, no bug.
  Only the long-press action buttons ("Got it" / "Reply") reach the tap-handlers.
  (Observed twice on 2026-07-12 before the cause was spotted.)

### KF-10: Prose + `{noun}` gloss before the judge's json fence (2026-07-13, fixed)
**Symptom:** knock-response run fails with the KF-7 error signature (`Expecting value:
char 0`, then `property name … char 1`) even though the raw dump in the log shows a
well-formed ```json block; the judged reply — a real cold fire — is lost, no state
written, no push-back fired.
**Root cause:** the judge narrated its reasoning *before* the fence, and the prose
quoted a frame gloss containing literal braces (`{noun} வேணும்`). `parse_llm_json`'s
fence-strip only fires on a *leading* fence, so it never ran; the `{..}` slice fallback
then bit on the `{` of `{noun}` — garbage for both `json.loads` and `ast.literal_eval`.
**Fix:** a fenced-block-anywhere stage (last fence wins — it's the artifact) between
whole-text `json.loads` and the `{..}` slice.
**Recovery for a lost reply:** the payload survives in the failed run's env block
(`gh run view <id> --log` → `REPLY_TEXT:` / `REPLY_KNOCK_ID:`); replay locally with
`REPLY_KNOCK_ID=… python scripts/knock_reply.py "<REPLY_TEXT>"` *after* the fix is in.
**Verify:** `python scripts/smoke_test.py` → section 1 ("prose with {braces} before a
json fence", "last fence wins when prose precedes multiple fences").

### KF-11: Volley surface desynced from the pin — the judge improvised the chain (2026-07-18, fixed)
**Symptom:** Andrew: "you caught the wrong one so we got re-graded against 1, saw 2 again,
then never saw 3." Log shows Python's pin walked 1→2→3 correctly the whole time.
**Root cause (corrected same day — Andrew: "this smells like code, not instructions"):**
the INITIATING defect was Python's. `judge()` handed the model `notification_body` frozen
at ask 1 while the pin walked the queue, and the current ask's text appeared nowhere in
the context — so from item 2 onward every volley read as a KF-3 mis-target, and the
COHERENCE SAFETY NET *lawfully voided the pin*, grading/recasting against the stale
body's natural answer (kazhuvittu varen, item 1). The judge wasn't sloppy; it obeyed its
law against poisoned input. Two judge-side defects then compounded the hole: chat
mid-volley appended nothing (the open 3/3 vanished, the judge improvised a "fresh start"
re-ask of item 2), and it claimed the next "I don't know" was scored as the 3/3 miss
when its own verdict was chat (confabulated bookkeeping).
**Fix:** `volley_open_ask()` is the one owner of the current ask; `judge()` grades
against it (body coheres with pin by construction) and chat verdicts re-present it
deterministically while the volley is open; the last judged item sets `volley_done`;
JUDGE_MANDATE gains volley discipline (recast the pinned item only; never re-ask earlier
items, declare the volley done, or claim unrecorded scores).
**The meta-lesson:** the LLM must never own chain *surface* any more than chain *state* —
whatever Python tracks, Python must also say.
**Verify:** `python scripts/smoke_test.py` → section 21.

### KF-12: Expired GitHub PAT killed the reply path, silently (2026-07-31, fixed)
**Symptom:** Andrew replies from the phone; no workflow run, no error, no trace anywhere.
Twice in an evening. Knocks kept arriving normally the whole time.
**Root cause:** the fine-grained PAT in HA's `secrets.yaml` (`github_dispatch_auth`) hit its
expiry. GitHub 401s the `dispatches` call, HA's `rest_command` logs it locally, and the repo
sees *nothing* — there is no failed run to find, because no run is created.
**The elimination that localises it in one move:** outbound (`push_to_phone` → HA webhook →
phone) and inbound (notification → HA automation → `rest_command` → GitHub) cross the SAME
Home Assistant. A knock landing on the phone proves HA, its webhook and its automation engine
are all alive, which rules out HA-down, `webhook_id` drift and the KF-9 mirror trap. What is
left is the component unique to the failing direction: the token.
**Dating it:** the last successful `repository_dispatch` run is the outage's start. On
2026-07-31 that was `00:08:30Z` — 20:08 EDT on the 30th, consistent with GitHub's default
30-day expiry on a token minted 2026-06-30.
**Fix:** rotate; replace `github_dispatch_auth` in `secrets.yaml` keeping the `Bearer ` prefix;
reload Rest commands. `configuration.yaml` needs no change — both `rest_command`s read the
same secret, so one line restores the ack path and the reply path together.
**Verify:** Developer Tools → Actions → `rest_command.anna_knock_response` with `response: ack`
→ expect 204 AND an **Anna** run committing `Knock response: ack`. The 204 alone is not proof
the loop works; look for the commit.
**THE EXPENSIVE HALF, and the reason this is a KF and not a footnote:** the outage is not
neutral to state. `knock_log` records `reply: null`, byte-identical to an ignored knock, and
downstream `demand_streak`, `recent_ask_counts` and the deck's staleness term all read silence
as a learner behaviour. A dead return path therefore writes a false portrait of a
non-responsive learner into the state that steers selection — for as long as it lasts.
**Where:** `docs/home_assistant_knock_buttons.md` §1 and §10 (rotation log — record every mint);
§9 is the outbound-vs-inbound table that localises which leg died.

### KF-13: `chat` froze a volley — a verdict overloaded with control flow (2026-08-04, fixed)
**Symptom:** Andrew: "off-by-1 error in our volley knocks." The 08-04 backchannel volley
re-asked 1/4 and 3/4 across six exchanges, never reached 4/4, and his *correct* answer to
item 1 was burned as a miss on the retry.
**Root cause:** `chat` is the only verdict that holds the volley pin
(`knock_reply.py` — `if verdict["verdict"] != "chat"` advances, else re-present). The
mandate defined `chat` by the **shape** of the reply ("English chat, a question,
logistics") — and `Ama ama` *is* item 1's target, ஆமா ஆமா. A backchannel target makes a
correct answer formally identical to chatter, so the judge routed it to `chat` while its
own recast said "aama aama — clean 🔥". A second author compounded it: "A target he keeps
substituting away from is signal for chat, not a miss to punish." **The judge was never
told `chat` freezes the item** — it was picking a label, Python read it as a behaviour.
**The control experiment is in the log:** row 3 (`Nera ponga` + a complaint, mixed) graded
`hinted` and advanced; row 5 (`You just asked me this same question. Seri seri`, identical
shape) went `chat`. The variable is the *target*, not the phrasing — the judge can extract
an answer from a complaint, but not when the target itself looks like chat.
**Not a KF-11 regression:** Python's pin and surface were correct throughout, and
`smoke_test.py` s21 ("chat mid-volley re-presents the open ask") was **green** — it asserts
exactly this behaviour, because KF-11 asked for it. This is the *quiet* class: nothing
failed, every instrument read green, the dose was about the wrong thing.
**Fix (two halves, deliberately):** `chat` is now defined by **relation** to
`expected_target`, not reply shape, with the mid-volley cost stated in the mandate; the
substitution sentence was **deleted** (it contradicted its own paragraph, which already
credits the substitute as a fire). Behind the wording, a **hold-cap**: a second consecutive
chat on the same item advances the pin regardless of the verdict — keyed on Python's own
`"still open · "` marker, not the verdict, so the cap is per item and a capped advance
can't cascade. A prompt fix alone can't be the only guard on a deadlock.
**Verify:** `python scripts/smoke_test.py` → section 21 (hold-cap, per-item, no
double-advance). The relational wording has **no offline proof** — it is a prompt, and only
live volley traffic can confirm it.
**The meta-lesson:** KF-11 said the LLM must never own chain *surface*. This is one turn
further — a verdict the LLM chooses must not silently *be* control flow. If a label stops
the world, say so in the mandate and cap the blast radius in Python.

### KF-14: A blown token ceiling wearing KF-7's face (2026-08-05, fixed)
**Symptom:** knock-response run fails with `Expecting value: line 1 column 1 (char 0)` and
`--- unparseable LLM response (no braces) ---`. A judged reply is lost; the volley freezes
mid-pin. Reads exactly like KF-7/KF-10.
**Root cause:** NOT a parser gap — there was no JSON to find. The judge spent ~750 of its
800 tokens deliberating in prose (which `slip_tags_in_use` tag to reuse, three "Actually…"
reversals) and was cut off **mid-word** before its first brace. `parse_llm_json` reported
truthfully; the message was just ambiguous between two failures that want **opposite**
fixes — a parser gap wants another fallback, a blown ceiling wants a bigger budget.
**The tell that separates them, at a glance:** KF-7/KF-10 throw **two** chained errors
(`char 0`, then `char 1`); this throws **one**, says `no braces`, and the dump ends
mid-sentence. If the dump's last line is a fragment, stop looking at the parser.
**Fix:** `parse_llm_response(resp)` checks `finish_reason == "length"` FIRST and raises a
self-naming ValueError carrying the partial text (the recovery payload). It lives in
`writer.py` beside `parse_llm_json` because only the *response* carries
`finish_reason` — the text cannot know. ValueError so `decide()`'s retry re-rolls it (a
second draft may be terser) while `judge()` surfaces at once. `judge()` 800 → 1600, which
is what `decide()` already used for comparable output; `judge_catch` stays at 400.
**Andrew's read, and it is the durable one:** *"I shouldn't handicap Anna to prevent this
kind of outlier that I can just learn to avoid."* The trigger was one reply carrying two
things at once (a scored answer **and** a meta-dispute about the previous grade). The
input fix — one ask per message — beats any ceiling.
**Verify:** `python scripts/smoke_test.py` → section 1. The teeth are on *telling them
apart*: the case asserts truncation does NOT raise `JSONDecodeError`, that the error names
itself, and that the partial text survives — plus two no-false-positive cases.
**Commit:** `c2a921e`

### KF-8: Lore format takeover — incentive drift, not taste (2026-07-11, fixed)
**Symptom:** Andrew: today's lore push "basically a duplicate" of last week's; the format
"took over." Log confirmed worse: four lore memos in four consecutive days (07-07→10),
every one a frame etymology.
**Root cause (three-part):** the variety law guarded pegs and asks but no *format family*
— "lore memo" had no cooldown; the decide prompt's own line "Prefer a deck word's story
while the sprint is on" funneled every lore dose into frame etymology (the deck is all
frames during the sprint); and OUTREACH MEMORY's reward framing closed the loop — lore
converts → memory shows lore converting → lore fires again.
**Fix:** `last_lore()` + `LORE_COOLDOWN_DAYS` (the `demand_streak` seam: Python counts,
the RAILS mandate owns the rule); the preference line deleted, vein rotation in its place;
constitution → Fresh Execution gains "Formats drift like content."
**The meta-lesson:** the first proposal was a quota, offered before anyone read the file —
a mechanism proposed before diagnosis is a symptom cap. The better half of the real fix
was a *deletion*, which only reading the plumbing could find.
**Verify:** `python scripts/smoke_test.py` → section 8 (lore cooldown cases).

---

## 5. Exit: Once Root-Caused

1. If the fix is a code change → use `/extend` (change discipline gate → surgical edit → smoke case).
2. Use `/verify` to prove the fix end-to-end.
3. Every fixed plumbing bug gets a new smoke case in `scripts/smoke_test.py` — this is the contract that keeps KF-1 and KF-2 from recurring. **Put teeth in the dimension that failed** (`/extend` Gate 7.2, the silent no-op test): assert the *effect*, round-trip through the writer and re-read the state file, and make the absence loud. A green case on a dead feature is the 2026-07-30 `s41` result.

**Triage note for the quiet class.** The KF archive below is loud failures — crashes, parse errors, visible desync — because that is what daily use surfaced first. Since 2026-07-24 the live class is *quiet*: nothing fails, every instrument reads green, and the dose is simply about the wrong thing. When Andrew's felt signal is "this doesn't feel like it's working on my mistakes" rather than "this broke", **do not start from the error log — there won't be one.** Start from the claim: name what the subsystem promises, then find the one place that would prove it happened, and check whether anything reads it.
4. If the fix is HA config → update the gitignored `docs/anna_knock_automation.yaml` mirror.
5. If the root cause is a pattern of 2+ feedback entries → log with `python scripts/sync_state.py feedback "note"` (mutating — appends to `progress/feedback_log.json`) before proposing the fix.

---

**Scope:** This skill owns triage only. Routine health checks → `/validate`. Making the fix → `/extend`. Proving it → `/verify`.
