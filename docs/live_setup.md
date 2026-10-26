# Live lane — setup checklist (at the computer)

**For:** Andrew, once. **Filed:** 2026-10-26. **Design:** `docs/live_conversation.md`.
Work top to bottom; each step says what to keep for later. Five things come out of
it. Keep them in a password manager, never in the repo or a chat:

| Keep | From | Goes to |
|---|---|---|
| Phone number ID | Meta, step 2 | GitHub secret `WHATSAPP_PHONE_ID` |
| Permanent access token | Meta, step 3 | GitHub secret `WHATSAPP_TOKEN` |
| App secret | Meta, step 2 | Cloud Run `APP_SECRET` |
| Verify token (any string you invent) | you | Cloud Run `VERIFY_TOKEN` + Meta webhook form |
| GitHub fine-grained token | GitHub, step 4 | Cloud Run `GITHUB_TOKEN` |

---

## 0. Two quick ones first

1. **Merge the code.** Merge `claude/live-conversation` into `main`. The WhatsApp step
   in `anna.yml` only runs from `main`.
2. **Let `/live` judge Tamil script in the cloud.** In the Claude Code app: open the
   cloud environment menu in the session's title bar → **Edit** → add an environment
   variable `OPENROUTER_API_KEY` (the same key the repo's Actions secret holds). Add it
   under *Network secrets* / *API credentials* if that section is offered. New sessions
   pick it up. Without it, any line that carries real Tamil script comes back as
   "Got it, noted."

## 1. Your service account question: you don't need one to deploy

**Don't use the TTS key (`GCP_SA_KEY`) for this, and don't widen it.** That service
account only has Text-to-Speech. Deploying needs Cloud Run, Cloud Build and Artifact
Registry permissions. Granting those to a key that already sits in GitHub secrets would
turn a TTS key into one that can deploy code to your project.

Instead:
- **To deploy,** use **your own Google login** on the laptop (`gcloud auth login`). As
  project owner you already have every permission. No key file is created.
- **To run,** the bridge gets **its own service account with no roles at all**
  (`anna-whatsapp`). It calls no Google API (only Meta and GitHub), so it needs nothing.
  A dedicated identity just keeps it from inheriting the broad default compute account.

It stays in the same project and on the same billing account as the TTS.

## 2. Meta app and test number (developers.facebook.com, ~15 min)

1. **My Apps → Create app.** Choose the WhatsApp use case ("Connect with customers
   through WhatsApp"; on the older form, type *Business*). Let it create or attach a
   Business portfolio.
2. **WhatsApp → API Setup.** Meta gives you a free **test number** (the "From").
   - Under **To**, add **your own number** and confirm it with the code WhatsApp sends.
   - Copy the **Phone number ID**. This is the ID, not the phone number itself.
   - **App settings → Basic → App secret → Show**, and copy it.
3. **Permanent token.** The token on the API Setup page dies in 24 hours, which is fine
   for a first test, but you'll want one that lasts:
   - Go to business.facebook.com → **Settings → Users → System users → Add**, with the
     Admin role.
   - **Assign assets**: the app, and the WhatsApp account with full control.
   - **Generate token** for the app, with permissions `whatsapp_business_messaging` and
     `whatsapp_business_management`, and expiry **Never**. Copy it.

## 3. Cloud Run (laptop terminal, from the repo root, ~10 min)

```bash
gcloud auth login                          # you, not the TTS key
gcloud config set project <YOUR-TTS-PROJECT-ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# The bridge's own identity — created with no roles, on purpose
gcloud iam service-accounts create anna-whatsapp --display-name="Anna WhatsApp bridge"

gcloud run deploy anna-whatsapp \
  --source bridge/whatsapp \
  --region europe-west1 \
  --service-account anna-whatsapp@<YOUR-TTS-PROJECT-ID>.iam.gserviceaccount.com \
  --allow-unauthenticated --min-instances 0 --max-instances 2 \
  --set-env-vars "VERIFY_TOKEN=<your string>,APP_SECRET=<app secret>,ALLOWED_FROM=<your number>,GITHUB_TOKEN=<github token>"
```

- **`ALLOWED_FROM`** is your number the way WhatsApp writes it: country code plus
  number, digits only, no `+`, no leading 0 (e.g. `447700900123`). A message from any
  other number is dropped.
- **First deploy:** it asks to create an Artifact Registry repo
  (`cloud-run-source-deploy`). Say **Y**.
- **Region:** pick one near you. `europe-west1` and `us-central1` are both in the free
  tier.
- **Copy the URL it prints** (`https://anna-whatsapp-….run.app`).
- **Check it:** opening `<URL>/?hub.mode=subscribe&hub.verify_token=<your string>&hub.challenge=hello`
  in a browser should show `hello`.
- **`--allow-unauthenticated` is safe here.** Meta can't send a Google login, and the
  bridge refuses anything not signed with your app secret.

**If the deploy fails on permissions for the build:** newer projects build with the
default compute service account. Grant it the builder role once, then rerun the deploy.

```bash
PROJECT_NUMBER=$(gcloud projects describe <YOUR-TTS-PROJECT-ID> --format='value(projectNumber)')
gcloud projects add-iam-policy-binding <YOUR-TTS-PROJECT-ID> \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/run.builder"
```

**Cost.** Cloud Run's free tier is 2 million requests a month; a walk is a few dozen.
Builds fit the free build minutes. The only likely charge is Artifact Registry
storage once old images pass 0.5 GB, which comes to cents. To keep it at zero, delete
old images under Artifact Registry → `cloud-run-source-deploy` now and then.

**Optional hardening:** put `APP_SECRET` and `GITHUB_TOKEN` in Secret Manager. Grant
`anna-whatsapp` the `roles/secretmanager.secretAccessor` role, and deploy with
`--set-secrets APP_SECRET=<name>:latest,GITHUB_TOKEN=<name>:latest` in place of those
two env vars.

## 4. GitHub token for the bridge

github.com → Settings → Developer settings → **Fine-grained tokens → Generate**:
- **Repository access:** only `arosselet/tamil-tutor`.
- **Permissions:** Repository → **Contents: Read and write** (that is what
  `repository_dispatch` needs). Nothing else.
- **Expiry:** the longest offered. Put a calendar reminder a week before it lapses. When
  it lapses, the bridge logs `dispatch failed … 401` and Anna goes quiet on WhatsApp.

This token goes into Cloud Run (step 3). If you made the GitHub token after deploying,
update it with `gcloud run services update anna-whatsapp --region europe-west1
--update-env-vars GITHUB_TOKEN=<token>`.

## 5. Connect the webhook (Meta)

1. App → **WhatsApp → Configuration → Webhook → Edit.** Callback URL = the Cloud Run
   URL; Verify token = your string. **Verify and save.**
2. **Webhook fields → Manage →** subscribe to **messages**.

## 6. Repo secrets (github.com → the repo → Settings → Secrets and variables → Actions)

| Secret | Value |
|---|---|
| `WHATSAPP_TOKEN` | the permanent token (step 2.3) |
| `WHATSAPP_PHONE_ID` | the Phone number ID (step 2.2) |
| `WHATSAPP_TO` | your number, same digits as `ALLOWED_FROM` |

## 7. First message

From your phone, message the **test number** in WhatsApp: "vanakkam anna". Anna
answers in about a minute.

- **In GitHub Actions** you'll see a run with a **Live turn (WhatsApp)** step.
- **To end a session**, say **bye** (or stop / done / end). That closes it and books the
  gates. A session silent for 3 hours closes itself on your next message.
- **You always message first.** WhatsApp only lets Anna reply inside 24 hours of your
  last message, so knocks stay on the phone push for now.

**If nothing comes back, go in order:**

| Where | What you see | What it means |
|---|---|---|
| Cloud Run → `anna-whatsapp` → **Logs** | `refused: bad or missing signature` | `APP_SECRET` is wrong. |
| | `skip: a sender who is not on the list` | `ALLOWED_FROM` doesn't match your number. |
| | `dispatch failed … 401/403/404` | The GitHub token is wrong, expired, or lacks Contents write. |
| | `dispatched … 204` | The bridge worked. Check Actions. |
| | No log line at all | Meta isn't calling. Recheck step 5, and that your number is a verified recipient. |
| Actions → the run → **Live turn (WhatsApp)** | `WhatsApp send failed` / HTTP 401 | `WHATSAPP_TOKEN` expired (was it the 24-hour one?). |
| | HTTP 400 | `WHATSAPP_TO` or `WHATSAPP_PHONE_ID` is wrong. |
| | No run at all | Is the code on `main`? (step 0.1) |
