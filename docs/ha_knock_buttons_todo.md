# Home Assistant — wire the knock "landed" button (paste-ready)

Everything to paste, with this instance's specifics filled in. Do the steps in
order; each block says which HA file it goes in.

**Scope (post-2026-06-30 pivot):** we stopped chasing episode listens, so this
wires a **single "Got it 👍" button**. Its only job is a *landed* signal — when
you tap it, the knock is marked answered and the next knock's gate backs off
(20 h) instead of re-knocking 3× the same day. No learning state is touched.
(The `listened` soak-credit path still exists in code but is intentionally not
wired to a button.)

Flow:

```
knock push ─▶ iOS notification ─▶ tap "Got it 👍"
                                      │
                                      ▼
             mobile_app_notification_action  (event: ANNA_ACK)
                                      │
                                      ▼
             rest_command.anna_knock_response  (curl → GitHub dispatches API)
                                      │
                                      ▼
             repository_dispatch: knock-response  ─▶  log-knock-response.yml
                                      │
                                      ▼
             sync_state.py knock-response ack   (commits knock_log.json)
```

---

## 1. Generate the GitHub PAT (do this yourself — never paste the token into chat)

The GitHub `dispatches` endpoint needs a token that can write to
`arosselet/tamil-tutor`.

1. github.com → **Settings → Developer settings → Fine-grained tokens → Generate new token**
2. **Token name:** e.g. `ha-anna-knock`; set an expiry you'll rotate.
3. **Repository access:** *Only select repositories* → `arosselet/tamil-tutor`
4. **Permissions:** *Repository permissions → Contents → **Read and write*** (the
   `dispatches` endpoint is gated on Contents-write — this one permission is enough).
5. **Generate** and copy the token (`github_pat_…`). You won't see it again.

> Classic PAT works too (scope `repo`), but a fine-grained token scoped to this
> one repo is tighter. If it ever leaks, revoke/rotate it — nothing else uses it.

---

## 2. `secrets.yaml` — add two secrets

```yaml
github_dispatch_auth: "Bearer github_pat_xxxxxxxxxxxxxxxxxxxxxxxx"   # your PAT from step 1, prefixed with "Bearer "
anna_knock_webhook_id: "-boz9pFKLzslxz3tiljDYumKk"                   # the path in ANNA_PUSH_WEBHOOK_URL (already known)
```

Store the **whole `Authorization` header value** — the word `Bearer`, a space,
then the token — so the raw PAT never appears in any config file.

---

## 3. `configuration.yaml` — add the `rest_command`

Merge into an existing `rest_command:` block if you already have one — don't
duplicate the top-level key.

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

A successful dispatch returns HTTP **204** (no body).

---

## 4a. Update the existing "Notify Andrew" automation — add the button

Under the notify `data:` → inner `data:` block, add an `actions:` list (additive;
the lock-screen body and tap-to-play are unchanged). This is exactly what's now
in the repo mirror `anna_knock_automation.yaml`:

```yaml
        actions:
          - action: ANNA_ACK
            title: "Got it 👍"
```

## 4b. Add a NEW automation — the tap handler

Paste as a brand-new automation (YAML mode):

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

## 5. Test before trusting it live

**a) GitHub side only** (no phone needed) — run in a terminal, don't paste the PAT into chat:

```bash
curl -X POST https://api.github.com/repos/arosselet/tamil-tutor/dispatches \
  -H "Authorization: Bearer github_pat_xxx" \
  -H "Accept: application/vnd.github+json" \
  -d '{"event_type":"knock-response","client_payload":{"response":"ack"}}'
```

Expect HTTP 204. Then check the repo's **Actions** tab: a **Log Knock Response**
run should appear and commit `Knock response: ack` to `main`.

**b) HA side** — Developer Tools → **Actions** → `rest_command.anna_knock_response`
with `{"response": "ack"}`. Same result (the Actions run + commit).

**c) End to end** — fire a real knock (Actions → **Anna Knock** → *Run workflow* with
`force: true`), then tap **Got it 👍** on the phone. Confirm the commit lands and
the next scheduled knock backs off instead of re-knocking.

---

## 6. Gotchas

- **Both secrets must exist in `secrets.yaml`** before you reload — HA refuses to
  load an automation whose `!secret` is missing.
- **`webhook_id` IS the secret.** `local_only: false` is required (GitHub's runners
  are remote); the unguessable webhook path is what protects it.
- **The floor is never touched here.** A tap only records "landed." Production only
  moves to `cold` when Anna witnesses an unaided cold fire in chat.
- **Mirror stays honest:** the repo's `anna_knock_automation.yaml` mirrors the
  Notify automation (now incl. the ack button). If you tweak anything in HA, hand
  the final YAML back so the mirror doesn't drift.
