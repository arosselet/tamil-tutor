# Home Assistant — the knock notification + "landed" button

The one doc for wiring Anna's knock to the phone: a notification with a single
**Got it 👍** button whose tap flows back to GitHub. Your instance's specifics are
filled in; the only secret you add is the PAT (§1).

> **Secrets note (repo is PUBLIC):** never commit real values. The webhook_id and
> the finished automation live in the gitignored **`anna_knock_automation.yaml`**
> (the mirror of your real HA config — copy from there). This doc uses placeholders.

## What it does

```
knock push ─▶ iOS notification ─▶ tap "Got it 👍"
                                      │
             mobile_app_notification_action  (event: ANNA_ACK)
                                      │
             rest_command.anna_knock_response  (curl → GitHub dispatches API)
                                      │
             repository_dispatch: knock-response  ─▶  log-knock-response.yml
                                      │
             sync_state.py knock-response ack   (commits knock_log.json)
```

The tap is a **landed** signal only: it marks the knock answered so the rails gate
backs off and Anna won't re-pitch. It never writes learning state — the floor only
moves when Anna witnesses a cold fire in chat. (The `listened`/soak-credit path
still exists in code but is intentionally not wired to a button, post the
2026-06-30 listens pivot.)

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
        value_template: "{{ trigger.json.audio_url is defined and trigger.json.audio_url }}"
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
              content-type: audio/mpeg
            actions:
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
              - action: "ANNA_ACK"
                title: "Got it 👍"
mode: single
```

## 5. Tap-handler automation (new, YAML mode)

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

**End to end:** fire a real knock (Actions → **Anna Knock** → Run workflow,
`force: true`), long-press the notification, tap **Got it 👍**.

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
- **The floor is never touched here** — a tap only records "landed."
- **iOS action buttons are hidden until you long-press / pull down** the notification.
- **Mirror stays honest:** `anna_knock_automation.yaml` (gitignored) mirrors your real
  HA config — if you tweak HA, update it so it doesn't drift.
