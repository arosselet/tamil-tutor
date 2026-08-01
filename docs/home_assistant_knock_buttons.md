# Home Assistant — the knock notification: "landed" button + Tamil reply

The one doc for wiring Anna's knock to the phone: a notification with a
**Got it 👍** button (landed signal) and a **Reply ✍️** text-input action (a real
rep — typed Tamil, judged and scored). Your instance's specifics are filled in;
the only secret you add is the PAT (§1).

> **Secrets note (repo is PUBLIC):** never commit real values. The webhook_id and
> the finished automation live in the gitignored **`anna_knock_automation.yaml`**
> (the mirror of your real HA config — copy from there). This doc uses placeholders.

> **⚠ ONE-TIME (open as of 2026-07-01): rotate the webhook_id.** The current one
> was committed before the sanitize pass and is recoverable from public git
> history. In HA, give "Notify Andrew" a fresh webhook_id, then update the
> `ANNA_PUSH_WEBHOOK_URL` GitHub secret and the gitignored mirror. Delete this
> note once rotated.

## What it does

```
knock push ─▶ iOS notification ─┬▶ tap "Got it 👍"          ─▶ event ANNA_ACK
                                └▶ "Reply ✍️" + typed Tamil  ─▶ event ANNA_REPLY (reply_text)
                                      │
             mobile_app_notification_action
                                      │
             rest_command.anna_knock_response / anna_knock_reply  (→ GitHub dispatches API)
                                      │
             repository_dispatch: knock-response  ─▶  anna.yml
                                      │
             ack   → sync_state.py knock-response ack      (knock marked landed)
             reply → knock_reply.py "<text>"               (Anna judges the rep, moves the
                                                            production axis, pushes back the
                                                            recast + deck scoreboard)
```

The tap is a **landed** signal only — it never writes learning state. The **reply**
is a real rep: Anna judges it against what the knock asked for; unaided Tamil the
notification didn't show can fire **cold** (Tamil the knock revealed caps at
*hinted* — the axis stays honest). (The `listened`/soak-credit path still exists
in code but is intentionally not wired to a button, post the 2026-06-30 listens
pivot.)

---

## 1. GitHub PAT (do this yourself — never paste the token into chat)

The `dispatches` endpoint needs write access to `arosselet/tamil-tutor`.

1. github.com → **Settings → Developer settings → Fine-grained tokens → Generate new**
2. **Name** `ha-anna-knock`; set an expiry you'll rotate.
3. **Repository access:** *Only select repositories* → `arosselet/tamil-tutor`
4. **Permissions:** *Repository permissions → Contents → Read and write* (the only one needed).
5. Generate; copy the `github_pat_…`.

---

## 2. `secrets.yaml`

```yaml
github_dispatch_auth: "Bearer github_pat_xxxxxxxxxxxxxxxxxxxx"   # the WHOLE header value: "Bearer " + the token
```

Store `Bearer ` + a space + the token, so the raw PAT never appears inline.
(The webhook_id is inline in the automation below / the mirror — no secret needed
for it.)

---

## 3. `configuration.yaml` — the `rest_command`

Merge into an existing `rest_command:` block if you have one.

```yaml
rest_command:
  anna_knock_response:
    url: https://api.github.com/repos/arosselet/tamil-tutor/dispatches
    method: POST
    headers:
      Authorization: !secret github_dispatch_auth
      Accept: application/vnd.github+json
      X-GitHub-Api-Version: "2022-11-28"
    content_type: "application/json"
    payload: '{"event_type":"knock-response","client_payload":{"response":"{{ response }}","knock_id":"{{ knock_id | default("") }}"}}'
  anna_knock_reply:
    url: https://api.github.com/repos/arosselet/tamil-tutor/dispatches
    method: POST
    headers:
      Authorization: !secret github_dispatch_auth
      Accept: application/vnd.github+json
      X-GitHub-Api-Version: "2022-11-28"
    content_type: "application/json"
    # tojson quotes AND escapes the typed text, so quotes/emoji can't break the JSON
    payload: '{"event_type":"knock-response","client_payload":{"response":"reply","text":{{ text | tojson }},"knock_id":"{{ knock_id | default("") }}"}}'
```

A successful dispatch returns HTTP **204**.

---

## 4. The "Notify Andrew" automation

**Edit in YAML mode (⋮ → Edit in YAML), replacing the whole automation — not the
visual editor** (it mangles the nested `data.actions` list). Three things make it
save cleanly and render every modality:

- call notify with **`service:`** (not the `action:` alias — it collides with the button's `action:` key),
- **quote** the button's action value,
- make audio **conditional** — Anna's text/challenge/grace doses send no `audio_url`, so an unconditional `attachment` renders an empty file (iOS: *"bad file type"*). Branch on whether an `audio_url` is present.

```yaml
alias: Notify Andrew
description: "Anna's knock — audio conditional so text doses don't error"
triggers:
  - trigger: webhook
    allowed_methods:
      - POST
      - PUT
    local_only: false          # GitHub runners are remote; the webhook_id is the secret
    webhook_id: "<YOUR_WEBHOOK_ID>"   # real value in the gitignored anna_knock_automation.yaml
conditions: []
actions:
  - if:
      - condition: template
        # must render a literal boolean — "is defined and x" yields the STRING x,
        # which HA (post 2026-07 core) counts as false, silently taking the else branch
        value_template: "{{ trigger.json.audio_url | default('') | length > 0 }}"
    then:
      # AUDIO knock — inline player + tap-to-play
      - service: notify.mobile_app_blue_dragonfly
        data:
          title: "{{ trigger.json.title | default('Anna', true) }}"
          message: "{{ trigger.json.text_content }}"
          data:
            # unique per knock (2026-07-11): notifications STACK until dismissed;
            # knock_id rides back with taps/replies so the judge grades the right knock
            tag: "anna-{{ trigger.json.knock_id | default('knock', true) }}"
            action_data:
              knock_id: "{{ trigger.json.knock_id | default('', true) }}"
            url: "{{ trigger.json.audio_url }}"
            attachment:
              url: "{{ trigger.json.audio_url }}"
              content-type: mp3   # file EXTENSION, not MIME — audio/mpeg errors on current iOS app
            actions:
              - action: "ANNA_REPLY"
                title: "Reply ✍️"
                behavior: textInput
                textInputButtonTitle: "anuppu"
                textInputPlaceholder: "tamizh-la sollu…"
              - action: "ANNA_ACK"
                title: "Got it 👍"
    else:
      # TEXT / challenge / grace knock — no attachment; the body IS the dose
      - service: notify.mobile_app_blue_dragonfly
        data:
          title: "{{ trigger.json.title | default('Anna', true) }}"
          message: "{{ trigger.json.text_content }}"
          data:
            tag: "anna-{{ trigger.json.knock_id | default('knock', true) }}"
            action_data:
              knock_id: "{{ trigger.json.knock_id | default('', true) }}"
            actions:
              - action: "ANNA_REPLY"
                title: "Reply ✍️"
                behavior: textInput
                textInputButtonTitle: "anuppu"
                textInputPlaceholder: "tamizh-la sollu…"
              - action: "ANNA_ACK"
                title: "Got it 👍"
mode: single
```

## 5. Tap-handler automations (YAML mode)

The ack tap:

```yaml
alias: "Anna Knock — handle button tap"
triggers:
  - trigger: event
    event_type: mobile_app_notification_action
    event_data:
      action: ANNA_ACK
actions:
  - action: rest_command.anna_knock_response
    data:
      response: ack
      # the notification's action_data comes back in the event — this is what
      # lets a tap on an OLD stacked notification ack the right knock
      knock_id: "{{ trigger.event.data.action_data.knock_id | default('') }}"
mode: single
```

The Tamil reply (the companion app puts the typed text in the event's
`reply_text` — verify in Developer Tools → Events → listen to
`mobile_app_notification_action` on your first test):

```yaml
alias: "Anna Knock — handle Tamil reply"
triggers:
  - trigger: event
    event_type: mobile_app_notification_action
    event_data:
      action: ANNA_REPLY
actions:
  - action: rest_command.anna_knock_reply
    data:
      text: "{{ trigger.event.data.reply_text }}"
      knock_id: "{{ trigger.event.data.action_data.knock_id | default('') }}"
mode: single
```

Reload automations (or restart HA) after saving.

---

## 6. Test before trusting it live

**GitHub side (terminal — don't paste the PAT into chat):**
```bash
curl -X POST https://api.github.com/repos/arosselet/tamil-tutor/dispatches \
  -H "Authorization: Bearer github_pat_xxx" \
  -H "Accept: application/vnd.github+json" \
  -d '{"event_type":"knock-response","client_payload":{"response":"ack"}}'
```
Expect 204, then a **Log Knock Response** run committing `Knock response: ack`.

**HA side:** Developer Tools → Actions → `rest_command.anna_knock_response` with
`{response: ack}` (note the `data:` wrapper). Same result.

**Reply path (terminal):**
```bash
curl -X POST https://api.github.com/repos/arosselet/tamil-tutor/dispatches \
  -H "Authorization: Bearer github_pat_xxx" \
  -H "Accept: application/vnd.github+json" \
  -d '{"event_type":"knock-response","client_payload":{"response":"reply","text":"naan poren"}}'
```
Expect 204, a **Log Knock Response** run through the *Judge Tamil reply* step, a
`Knock reply: …` commit, and a push-back notification ending in `Deck X/47 · Nd`.

**End to end:** fire a real knock (Actions → **Anna Knock** → Run workflow,
`force: true`), long-press the notification, type into **Reply ✍️** — or tap
**Got it 👍** for the landed-only path.

---

## 7. Gotchas

- **Repo is public** — real webhook_id / PAT never go in tracked files; keep them in
  `secrets.yaml` and the gitignored `anna_knock_automation.yaml`.
- **YAML mode, not the visual editor**, for the notify automation (nested actions).
- **Audio is conditional** — text doses carry no `audio_url`; the `if/else` prevents
  the "bad file type" attachment error.
- **`!secret` is read at platform load** — after changing `secrets.yaml`, reload REST
  commands (or restart HA), or the old value 401s.
- **Both secrets must exist before reload** — HA won't load an automation whose
  `!secret` is missing.
- **A tap only records "landed"; a reply is the thing that scores** — and Tamil the
  knock showed you caps at *hinted*; only unaided production fires cold.
- **iOS action buttons are hidden until you long-press / pull down** the notification.
- **Dictation works in the reply field** — saying it aloud and letting iOS transcribe
  the phonetic is a better rep than typing (the table needs your mouth, not your thumbs).
- **Mirror stays honest:** `anna_knock_automation.yaml` (gitignored) mirrors your real
  HA config — if you tweak HA, update it so it doesn't drift.
- **Template conditions must render literal booleans** — `{{ x is defined and x }}`
  returns the *string* x, which HA counts as false; use `| default('') | length > 0`.
  Debug branch choices via the automation's **Traces** UI first (`choice: else` is the
  smoking gun) — it pinpoints the failing branch in one step.
- **`attachment.content-type` is a file extension** (`mp3`), not a MIME type — current
  iOS companion app errors on `audio/mpeg`. Audio attachments cap at **5 MB** (~20 min
  at our bitrate; drills ≈ 700 KB / 3 min).
- **Pre-warm the CDN before an audio push** — iOS fetches the attachment the instant the
  notification lands; a never-requested jsDelivr path can be too slow on first pull.
  `push_to_phone()` in `morning_knock.py` GETs the URL before notifying for this reason.

---

## 8. Home-screen "Tell Anna" button (iOS Shortcut → same pipeline)

A standalone Shortcut that opens the reply channel **without a live notification on
screen** — same endpoint, same judge, same scoring. Confirmed working 2026-07-02.
This is the path that survives a dismissed, expired, or never-rendered notification:
it needs nothing but the phone and the internet.

### 8.1 Build it from scratch

Two actions. Ten minutes including the token.

**Step 0 — the PAT.** The Shortcut carries its own token; it does not share HA's.
If you still have the `github_pat_…` from the old shortcut saved somewhere, reuse it.
Otherwise mint a fresh one exactly as in §1 (fine-grained · *Only select repositories*
→ `arosselet/tamil-tutor` · **Contents: Read and write**, nothing else). Name it
`ios-tell-anna` so it's separately revocable from HA's. Copy it — GitHub shows it once.

**Step 1 — new Shortcut.** Shortcuts app → **+** (top right) → rename it **Tell Anna**
(tap the name at the top → Rename).

**Step 2 — Ask for Input.** Search actions for *Ask for Input*, add it.
- **Input Type:** Text
- **Prompt:** `Tell Anna:`
- Leave *Default Answer* empty.

**Step 3 — Get Contents of URL.** Search for *Get Contents of URL*, add it below.
- **URL:** `https://api.github.com/repos/arosselet/tamil-tutor/dispatches`
- Expand **Show More** (the arrow) to reveal Method / Headers / Request Body.
- **Method:** `POST`
- **Headers** — three rows, *Add new header* for each:

  | Key | Value |
  |---|---|
  | `Authorization` | `Bearer github_pat_…` (the word `Bearer`, a space, then the token) |
  | `Accept` | `application/vnd.github+json` |
  | `X-GitHub-Api-Version` | `2022-11-28` |

- **Request Body:** `JSON`
- Build **two top-level fields** with *Add new field*:

  | Field | Type | Value |
  |---|---|---|
  | `event_type` | **Text** | `knock-response` |
  | `client_payload` | **Dictionary** | (expands — fill in below) |

- Inside `client_payload` (its own *Add new field* rows):

  | Field | Type | Value |
  |---|---|---|
  | `response` | **Text** | `reply` |
  | `text` | **Text** | the **Provided Input** variable — inserted as a blue variable chip, not typed |

  To insert the chip: tap the value box, then pick **Provided Input** from the
  variable bar above the keyboard (or *Select Variable* → *Provided Input*, the
  output of the Ask for Input action). If it reads as the literal words "Provided
  Input" in plain black text, it's a string, not the variable — delete and re-insert.

**Step 4 — put it on the Home Screen.** Shortcut details (ⓘ or the ⌄ by the name) →
**Add to Home Screen** → name it, pick an icon, **Add**. The tile launches straight
into the "Tell Anna:" prompt.

**Step 5 — first run.** Tap it once and send anything (`vanakkam` will do). iOS asks
permission to contact `api.github.com` the first time — **Allow**. It only asks once.

The finished JSON body, for reference — this is exactly what the two nested fields
serialise to:

```json
{"event_type":"knock-response",
 "client_payload":{"response":"reply","text":"<whatever you typed>"}}
```

### 8.2 Prove it worked

A dispatch returns **204 No Content**, so the Shortcut just ends with no visible
output — success looks identical to nothing happening. Confirm downstream instead:

1. **Actions tab** → an **Anna** run with event `repository_dispatch` starts within
   seconds of the tap.
2. That run's **Judge Tamil reply** step runs (not `skipped`).
3. A commit lands on `main`: `Knock reply: <verdict> (…)`.
4. A **push-back notification** arrives on the phone — the recast plus the scoreboard
   line ending `Deck X/47 · Nd`.

If step 1 never happens, the tap never left the phone (token or body problem —
see 8.4). If step 1 happens but step 4 doesn't, the phone leg is fine and it's the
HA notify path — §6.

### 8.3 What the reply gets graded against

The Shortcut sends **no `knock_id`** — unlike the notification's Reply ✍️ button,
which round-trips one in `action_data`. Without it, `knock_reply.py` falls back to
`last_fired_knock()`: your reply is judged against **the most recent knock Anna
fired**, whatever it was. That's the right default for "I want to say something to
Anna now", and it's also why the Shortcut can answer a volley whose notification you
already swiped away — the knock is still the last one in the log.

Consequence worth knowing: if a newer knock has fired since the one you meant to
answer, the Shortcut will grade you against the *newer* one. Use the notification's
own Reply ✍️ button when a specific older knock is the one you're answering, and the
Shortcut when you just want the channel open.

### 8.4 Gotchas

- **Nesting is set by field *type*, not by the key box.** Every field row in the
  Shortcuts JSON editor shows a key box *and* a value box — that's normal. Nesting
  only happens when a field's **type** is explicitly Dictionary (or Array). If a
  plain-string field like `event_type` sprouts its own "Add new field" underneath,
  its type got flipped to Dictionary — set it back to Text.
- **404 from `api.github.com` means the token, not the URL.** GitHub returns 404
  (never 403) for a PAT that is expired, revoked, scoped to the wrong repo, or missing
  *Contents: Read and write*. Re-mint per §1.
- **`Bearer ` is part of the header value.** `Authorization: github_pat_…` without the
  prefix fails the same way.
- **Dictation beats typing.** Tap the mic in the "Tell Anna:" prompt and say the line —
  iOS transcribes the phonetic. The table needs your mouth, not your thumbs.
- **The token lives in the Shortcut.** Deleting the Shortcut deletes your only copy of
  it. Rebuilding means a new PAT unless you saved it; revoke the orphaned one in
  GitHub → Settings → Developer settings → Fine-grained tokens.
- **To debug a silent failure**, temporarily add a *Show Result* action after Get
  Contents of URL — 204 shows empty, an error shows GitHub's JSON message. Remove it
  once it works.

---

## 9. Which leg breaks when — reading a "it disappeared" symptom

The two directions do **not** share a network path, and confusing them costs a day.

| | Outbound (Anna → phone) | Inbound (phone → Anna) |
|---|---|---|
| Path | GitHub runner → `ykf.duckdns.org:4444` (HA webhook) → Apple APNs → phone | phone → `api.github.com:443` → `repository_dispatch` → **Anna** workflow |
| Who makes the call | a GitHub Actions runner | the phone itself (notification button *or* the §8 Shortcut) |
| Port 4444 involved? | **yes** | **no — never** |
| Your laptop involved? | no | no |
| Your Wi-Fi involved? | only for the phone's APNs connection (443, same as any app) | yes, but only as ordinary HTTPS on 443 |

So:

- **A Wi-Fi network blocking 4444 cannot break either direction.** The 4444 hop is made
  by a GitHub runner in Amazon's network, not by anything on your Wi-Fi. The only
  documented 4444 failure is *your laptop* doing a local render behind work TLS
  inspection (DECISIONS, 2026-07-28) — CI has never been affected by it.
- **The Shortcut pointing at GitHub is correct, not a misconfiguration.** Both inbound
  paths — the notification's Reply ✍️ and the Shortcut — go to `api.github.com`. HA is
  a *relay* on the way in (button → HA `rest_command` → GitHub); the Shortcut simply
  skips the relay. Neither one touches 4444.

**How to tell which leg actually failed, in under a minute:**

1. **Actions tab → the Anna run for that time.** The drain step prints
   `HA push -> HTTP 200` on a successful outbound push. A 200 there means GitHub
   handed the notification to Home Assistant and the outbound leg did its job —
   anything missing after that is HA-side (§5 automations, quiet-hours on the phone,
   Focus mode, a stacked/replaced notification tag) or a swipe.
2. **Look for a `repository_dispatch` run.** One exists ⇔ the phone successfully
   reached GitHub. No run = nothing left the phone: dead Shortcut, dead PAT, or an
   action button whose HA automation didn't fire.
3. **A run with `Judge Tamil reply` *skipped*** means the dispatch arrived carrying
   `response: ack`, not `reply` — a **Got it 👍** tap, not a graded rep. This is the
   one that reads as "my reply disappeared" when it didn't: the ack landed, the reply
   was never sent.
