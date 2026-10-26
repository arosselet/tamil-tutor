#!/usr/bin/env python3
"""THE WHATSAPP BRIDGE — Meta's webhook in, a GitHub `live-turn` dispatch out
(2026-10-26, Andrew; `docs/live_conversation.md`). Runs on Cloud Run, in the
same Google Cloud project as the TTS.

WHY A BRIDGE AT ALL. GitHub Actions cannot be a public endpoint: it runs only
when something calls `api.github.com/.../dispatches` with a token. Meta cannot
send that token or reshape its payload, and GitHub cannot answer Meta's
verification handshake (a GET that must echo `hub.challenge`). So this does the
three things in between, and nothing else:

  1. GET  — the one-time handshake: echo the challenge if the verify token matches.
  2. POST — check Meta's signature (X-Hub-Signature-256, HMAC of the raw body
            with the app secret), keep only TEXT messages from the one allowed
            sender, and dispatch each as {text, id}.
  3. Answer 200 quickly, always, once the body is authentic — Meta retries what
     it thinks was missed, and `live.py` drops a repeated id.

IT HOLDS NO STATE. The transcript lives in the repo (`progress/live_session.json`),
and the answer goes back from the runner through Meta's API directly. HIS NUMBER
NEVER RIDES THE DISPATCH: the event payload is readable in a public repo's run
log, so the runner answers a secret recipient (WHATSAPP_TO) instead.

Standard library only — no requirements, nothing to patch.

ENV: VERIFY_TOKEN (any string you also type into Meta's dashboard), APP_SECRET
(Meta app → Settings → Basic), ALLOWED_FROM (his number as Meta sends it, digits
only, e.g. 4479…), GITHUB_TOKEN (fine-grained PAT, this repo, Contents: write),
GITHUB_REPO (default arosselet/tamil-tutor), PORT (Cloud Run sets it).
"""
import hashlib
import hmac
import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def handshake(query: str) -> str | None:
    """The challenge to echo, or None to refuse."""
    q = urllib.parse.parse_qs(query)
    ok = (q.get("hub.mode", [""])[0] == "subscribe" and env("VERIFY_TOKEN")
          and hmac.compare_digest(q.get("hub.verify_token", [""])[0], env("VERIFY_TOKEN")))
    return q.get("hub.challenge", [""])[0] if ok else None


def authentic(body: bytes, signature: str) -> bool:
    """Meta signs the RAW body; anything unsigned or mis-signed is dropped."""
    secret = env("APP_SECRET").encode()
    if not secret or not signature.startswith("sha256="):
        return False
    want = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, signature[len("sha256="):])


def turns(update: dict) -> list[dict]:
    """The text messages from the one allowed sender, as {text, id}. Delivery
    receipts, other senders and non-text messages (voice notes: a later slice)
    are skipped and said so in the log, never forwarded."""
    out = []
    allowed = env("ALLOWED_FROM")
    for entry in update.get("entry") or []:
        for change in entry.get("changes") or []:
            for m in (change.get("value") or {}).get("messages") or []:
                if not allowed or m.get("from") != allowed:
                    print("skip: a sender who is not on the list")
                elif m.get("type") != "text":
                    print(f"skip: a {m.get('type')} message — text only for now")
                else:
                    out.append({"text": (m.get("text") or {}).get("body", ""), "id": m.get("id", "")})
    return out


def dispatch(turn: dict) -> None:
    """One `live-turn` repository_dispatch. Raises on failure (logged, still 200)."""
    repo = env("GITHUB_REPO", "arosselet/tamil-tutor")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/dispatches",
        data=json.dumps({"event_type": "live-turn", "client_payload": turn}).encode(),
        headers={"Authorization": f"Bearer {env('GITHUB_TOKEN')}",
                 "Accept": "application/vnd.github+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"dispatched {turn['id']}: HTTP {r.status}")


class Bridge(BaseHTTPRequestHandler):
    send_turn = staticmethod(dispatch)   # a test swaps this

    def reply(self, code: int, body: str = "") -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        challenge = handshake(urllib.parse.urlsplit(self.path).query)
        self.reply(200, challenge) if challenge is not None else self.reply(403)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if not authentic(body, self.headers.get("X-Hub-Signature-256", "")):
            print("refused: bad or missing signature")
            return self.reply(401)
        for turn in turns(json.loads(body or b"{}")):
            try:
                self.send_turn(turn)
            except Exception as e:   # still 200: a retry would not fix GitHub, and the log says why
                print(f"dispatch failed for {turn['id']}: {e}")
        self.reply(200)


if __name__ == "__main__":
    port = int(env("PORT", "8080"))
    print(f"whatsapp bridge on :{port}")
    HTTPServer(("", port), Bridge).serve_forever()
