# Home Assistant — knock buttons (the feedback loop)

Closes the loop on the between-session knock. The knock notification gets **two
tap buttons**; tapping one fires a GitHub `repository_dispatch`, which runs the
`log-knock-response` workflow → `sync_state.py knock-response`.

```
knock push ──▶ iOS notification ──▶ Andrew taps a button
                                          │
              ┌───────────────────────────┘
              ▼
  mobile_app_notification_action event
              │
              ▼
  rest_command.anna_knock_response  (curl → GitHub API)
              │
              ▼
  repository_dispatch: knock-response  →  log-knock-response.yml
              │
              ▼
  sync_state.py knock-response  <ack | listened>
```

Two taps, both **soak-tier** (they never touch the viability floor — that only
moves when Anna witnesses a cold fire in chat):

| Button     | `response`   | Effect                                                                 |
|------------|--------------|------------------------------------------------------------------------|
| **Got it** | `ack`        | Marks the knock landed → the nudge gate backs off (no learning write). |
| **Listened** | `listened` | Marks it landed **and** credits the latest published episode's soak (`listens++`, surfaces its words). `listened` upgrades a prior `ack`. |

Duplicate taps are no-ops, so a double-tap can't double-count.

---

## 1. The secret — a GitHub PAT

`repository_dispatch` needs a token that can write to `arosselet/tamil-tutor`.

**Fine-grained PAT (recommended):** github.com → Settings → Developer settings →
Fine-grained tokens → Generate new.
- **Repository access:** Only select repositories → `arosselet/tamil-tutor`
- **Permissions:** *Repository permissions → Contents → **Read and write*** (the
  `dispatches` endpoint is gated on Contents-write).
- Copy the token (`github_pat_…`).

Store the **whole `Authorization` header value** in HA's `secrets.yaml` (so the
PAT never appears inline in a config file):

```yaml
# secrets.yaml
github_dispatch_auth: "Bearer github_pat_xxxxxxxxxxxxxxxxxxxxxxxx"
```

> Classic PAT works too — scope `repo` — but fine-grained scoped to this one repo
> is tighter. Rotate it if it ever leaks; nothing else depends on it.

---

## 2. The `rest_command` — fires the dispatch

Add to `configuration.yaml` (merge if you already have a `rest_command:` block):

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
    # response is 'ack' or 'listened', passed in by the handler automation below.
    payload: '{"event_type":"knock-response","client_payload":{"response":"{{ response }}"}}'
```

A successful dispatch returns HTTP **204** with no body.

---

## 3. The notification — add the two buttons

This is the automation that already fires on the `ANNA_PUSH_WEBHOOK_URL` webhook
(your existing "Notify Andrew"). The only change is the `actions:` list under
`data:`. Adjust `webhook_id` / `notify.mobile_app_…` to your existing values.

```yaml
automation:
  - alias: "Anna Knock — notify with buttons"
    id: anna_knock_notify
    trigger:
      - platform: webhook
        webhook_id: !secret anna_knock_webhook_id   # the path in ANNA_PUSH_WEBHOOK_URL
        local_only: false
        allowed_methods: [POST]
    action:
      - service: notify.mobile_app_blue_dragonfly      # your iOS device
        data:
          title: "{{ trigger.json.title | default('Anna') }}"
          message: "{{ trigger.json.text_content }}"
          data:
            tag: anna-knock                            # self-replacing (one knock at a time)
            url: "{{ trigger.json.audio_url }}"        # default tap still = play the memo
            attachment:
              url: "{{ trigger.json.audio_url }}"
              content-type: audio/mpeg                 # inline player on long-press
            actions:
              - action: ANNA_ACK
                title: "Got it 👍"
              - action: ANNA_LISTENED
                title: "Listened 🎧"
```

> The lock-screen body still carries the Tamil phrase, and the default tap still
> opens the audio — the buttons are additive. An un-tapped knock is unchanged.

---

## 4. The handler — tap → `rest_command`

```yaml
  - alias: "Anna Knock — handle button tap"
    id: anna_knock_tap
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: ANNA_ACK
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: ANNA_LISTENED
    action:
      - service: rest_command.anna_knock_response
        data:
          response: >-
            {{ 'listened' if trigger.event.data.action == 'ANNA_LISTENED' else 'ack' }}
```

---

## Test it without waiting for a knock

1. **Dispatch path only** (no phone needed) — fire the GitHub side directly:
   ```bash
   curl -X POST https://api.github.com/repos/arosselet/tamil-tutor/dispatches \
     -H "Authorization: Bearer github_pat_xxx" \
     -H "Accept: application/vnd.github+json" \
     -d '{"event_type":"knock-response","client_payload":{"response":"ack"}}'
   ```
   Watch the `log-knock-response` run appear in the repo's Actions tab; it commits
   `Knock response: ack`.

2. **Full path** — HA → *Developer Tools → Actions →* `rest_command.anna_knock_response`
   with `{"response": "listened"}`, or fire the actual knock
   (`workflow_dispatch` on **Anna Knock**, `force: true`) and tap a button on the phone.

3. **End to end:** a `listened` tap should bump `progress/episodes.json` (latest
   mission `listens++`) and `progress/lexicon.json` (`last_surfaced` on that
   episode's words). The next knock's gate then backs off (20 h) instead of
   re-advertising the same audio.

## Notes / gotchas

- **`secrets.yaml` needs `anna_knock_webhook_id`** if you adopt the `!secret`
  reference above — or just inline your existing webhook id.
- **`listened` credits the *latest published* episode** (highest mission number),
  not necessarily the one the knock was about. That's the agreed model — a tap
  can't name a mission, so it credits the newest thing in the feed. If you binge
  two episodes, only the newest is credited per tap; Anna reconciles the rest in
  chat.
- **The floor is never touched here.** No tap writes `production: cold`. A future
  third button ("fired it back") would *queue a fire-check* for the next chat, not
  write the floor directly.
