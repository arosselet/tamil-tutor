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
             repository_dispatch: knock-response  ─▶  log-knock-response.yml
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
    payload: '{"event_type":"knock-response","client_payload":{"response":"{{ response }}"}}'
  anna_knock_reply:
    url: https://api.github.com/repos/arosselet/tamil-tutor/dispatches
    method: POST
    headers:
      Authorization: !secret github_dispatch_auth
      Accept: application/vnd.github+json
      X-GitHub-Api-Version: "2022-11-28"
    content_type: "application/json"
    # tojson quotes AND escapes the typed text, so quotes/emoji can't break the JSON
    payload: '{"event_type":"knock-response","client_payload":{"response":"reply","text":{{ text | tojson }}}}'
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
            tag: anna-knock                 # self-replacing — one knock at a time
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
            tag: anna-knock
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

A standalone Shortcut that opens the reply channel without a live notification on
screen — same endpoint, same judge. Confirmed working 2026-07-02.

1. **Ask for Input** — Text, prompt "Tell Anna:"
2. **Get Contents of URL**:
   - URL: `https://api.github.com/repos/arosselet/tamil-tutor/dispatches`
   - Method: POST
   - Headers: `Authorization: Bearer <fine-grained PAT, this repo only, Contents: R/W>`,
     `Accept: application/vnd.github+json`
   - Request Body (JSON):
     - `event_type` (Text) = `knock-response`
     - `client_payload` (**Dictionary** type — the one field that needs nesting):
       - `response` (Text) = `reply`
       - `text` (Text) = the *Provided Input* variable (inserted as a variable chip)

**The one real gotcha:** every field row in the Shortcuts JSON editor shows a key box
*and* a value box — that's normal, not nesting. Nesting only happens when a field's
**type** is explicitly set to Dictionary (or Array). If a plain-string field (like
`event_type`) shows its own "Add new field" underneath, its type got flipped to
Dictionary by mistake — set it back to Text.
