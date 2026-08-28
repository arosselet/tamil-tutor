#!/usr/bin/env python3
"""What every inbound-message lane needs, whichever lane grades it.

Split out of knock_reply.py on 2026-08-28, when the MESSAGE lane arrived and
needed the same three things the reply lanes already had: a way to answer
ALOUD, the backstop that makes a direct audio request stick, and the one
writer that puts meta-direction in the feedback ledger.

Why a file and not a bigger budget. knock_reply.py went 570 -> 610 code lines
the day before this, and its own commit said the next raise should be a split.
The ratchet's rule is the reason: a file that keeps hitting its ceiling is
doing too many jobs. knock_reply.py owns GRADING — reveal caps, chains,
volleys, the production and catch axes. None of that is needed to render a
greeting or file a complaint, and the message lane needs none of it.

Nothing here imports knock_reply, so knock_reply and knock_message can both
import this without a cycle. That constraint is why `speak` lives here rather
than in publish.py, which would have closed a cycle through morning_knock.
"""
import asyncio
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from morning_knock import KNOCK_LOG_PATH, render_memo
from publish import KNOCKS_DIR, jsdelivr_url
from render_audio import ANNA_VOICE
from state_io import FEEDBACK_LOG_PATH, load_json, local_today, save_json

# A clock in Andrew's own words. Deliberately generous: a false positive costs



TIME_REQUEST_RE = re.compile(
    r"\b("
    r"\d{1,2}\s*(?::\d{2})?\s*(?:am|pm)"          # 9am, 9:15 pm
    r"|(?:at|by|around)\s+\d{1,2}(?::\d{2})?\b"   # at 9, by 9:15
    r"|in\s+(?:an?\s+)?(?:half\s+an?\s+)?(?:hour|minute|min)s?"
    r"|tomorrow|tonight|this\s+(?:morning|afternoon|evening)"
    r"|later\s+today|before\s+bed|first\s+thing"
    r")\b", re.I)


ASK_RE = re.compile(
    r"\b(send|ping|knock|remind|message|text|call|wake|greet\w*|give|do"
    r"|schedul\w*|queue|push|play|say|speak|sing|record|tell|wish)\b", re.I)



AUDIO_RE = re.compile(
    r"\b(audio|voice|voice[- ]?note|aloud|out\s+loud|say|speak|spoken|sing|sung"
    r"|pronounc\w*|record\w*|greeting|memo|hear|listen|sound)\b", re.I)



def wants_spoken_reply(text: str) -> bool:
    """True when Andrew's reply reads as 'let me HEAR this'.

    The voice counterpart of wants_scheduled_push below, and it exists for the
    identical reason: VOICE_MANDATE rations speaking hard — "Empty string is the
    normal answer" — which is right for a recast and wrong for a man who typed
    "Send an audio greeting in Tamil" and then asked twice more when nothing
    arrived (2026-08-27). Prose cannot fix prose; the rule needs a mechanism.

    Wide on the same terms as the clock detector: a false positive costs one
    re-ask, a false negative costs Andrew the thing he asked for. Widen on sight
    — "say vanakkam for me" is the demo he actually wants and it needs `say`
    here, not only in ASK_RE where the AND would never fire.

    `said` and `tell` stay OUT. Both must be readable as a question about
    MEANING — "tell me what she said" wants a gloss, not a rendering — and a
    false positive there is worse than a wasted call: the backstop would write
    MISSED VOICE into the feedback ledger for a request he never made. The
    ledger note quotes his words verbatim so a reader can always see which it
    was."""
    return bool(AUDIO_RE.search(text) and ASK_RE.search(text))



def ensure_voice(verdict: dict, reply_text: str, rejudge) -> dict:
    """The audio-request backstop: one forced re-ask, then a LOUD miss.

    Modelled line-for-line on the clock-request backstop in main(), because the
    failure is the same shape. `rejudge` is a zero-arg callable that re-runs the
    caller's own judge with force_voice=True, so both lanes share this body
    without this function knowing which judge it is talking to.

    The silent-no-op answer (Gate 7): a lane that declines to speak looks EXACTLY
    like a normal text reply — that is precisely how four requests in a row were
    swallowed with every instrument green. So the third outcome is not silence:
    it writes MISSED VOICE into the feedback ledger, where the diagnosis pass
    reads it."""
    if not wants_spoken_reply(reply_text) or verdict.get("voice_reply"):
        return verdict
    print("   🎧 direct audio request with no voice_reply — re-asking once, forced…")
    forced = rejudge()
    if forced.get("voice_reply"):
        print("   → speaking")
        return forced
    print("   ⚠ still silent — logging the miss to the ledger")
    verdict["meta_note"] = (verdict.get("meta_note") or "").strip() or (
        f"MISSED VOICE: Andrew asked to HEAR something ({reply_text[:80]!r}) and "
        f"the push went out text-only — the judge declined twice. Check the voice lane.")
    return verdict



def wants_scheduled_push(text: str) -> bool:
    """True when Andrew's reply reads as 'do something for me at <time>'.

    The mandate says a clock-bound request MUST produce a schedule; this is the
    mechanism that makes the rule real. A prose rule with no enforcement is how
    the 2026-07-23 9am greeting got acknowledged and then silently dropped —
    the judge is steered toward meta_note (a ledger note for later) when what
    Andrew wanted was a queue entry.

    The verb list is deliberately WIDE (2026-07-24). "Schedule a push and say
    hello" — the most literal possible phrasing of the request — matched the
    clock and missed the verb, so the backstop built the day before to catch
    exactly this never fired and the 8pm greeting was dropped a second time.
    A false positive costs one re-ask; a false negative costs Andrew a push he
    asked for and never got. Widen on sight."""
    return bool(TIME_REQUEST_RE.search(text) and ASK_RE.search(text))



def record_meta_note(verdict: dict) -> bool:
    """Meta-direction from a reply lands in the feedback ledger, which is what the
    diagnosis pass reads. Returns whether anything was written, so the caller can
    put the ledger in its commit.

    ONE writer (2026-08-24). This block was byte-identical in both judge lanes of
    this file — the production reply and the eavesdrop drift reply — which is the
    same duplication one file down that the spine refactor spent the day pulling
    out of seven. A note is a note whichever lane heard it."""
    note = (verdict.get("meta_note") or "").strip()
    if not note:
        return False
    flog = load_json(FEEDBACK_LOG_PATH) or []
    flog.append({"date": local_today().isoformat(), "note": f"[phone] {note}"})
    save_json(FEEDBACK_LOG_PATH, flog)
    print(f"   meta → ledger: {note}")
    return True



def speak(verdict: dict, knock: dict, klog: list) -> tuple[str | None, Path | None]:
    """Render Anna's spoken answer and attach it to the knock. Returns (url, mp3).

    Extracted from the production flow on 2026-08-27 so the catch lane could
    reuse it instead of growing a second copy. It had no copy at all: it ended
    `push_to_phone(reply_line, None, ...)` — audio_url hard-coded, the exact bug
    render_voice_reply's own docstring says was fixed in the production lane on
    2026-07-24 and never ported. One body, two callers, nothing left to forget.

    The knock-log write lands on the EXCHANGE as well as the top level: the
    top-level field is the LATEST view, overwritten by the next voice reply, so
    only the per-exchange copy survives as thread history. On a render failure
    `spoke` is cleared — better a silent record than one claiming audio he never
    got, which is what taught `recent_exchanges` to report what Anna DID."""
    if not verdict.get("voice_reply"):
        return None, None
    print("2b. render voice reply…")
    mp3, url = render_voice_reply(verdict["voice_reply"])
    if url:
        knock["reply_audio_url"] = url
        knock["exchanges"][-1].update(audio_url=url)
        save_json(KNOCK_LOG_PATH, klog)
    else:
        knock["exchanges"][-1].update(spoke="", audio_failed=True)
    return url, mp3



def render_voice_reply(spoken: str) -> tuple[Path | None, str | None]:
    """Render Anna's spoken answer for THIS push-back. Returns (mp3, url).

    The other half of the loop (2026-07-24): the knock lane could always speak
    TO Andrew, but the reply lane pushed `audio_url=None` hard-coded, so Anna
    could never speak BACK — a lock-screen ask for "how does that sound?" could
    only ever be answered in writing. The renderer was never the blocker; the
    reply workflow simply had no TTS secret until the workflows were merged.

    Deliberately best-effort: a TTS failure must still deliver the text recast.
    Costs ~60-90s while Andrew waits at the lock screen, which is why the
    mandate rations it to answers where the sound IS the answer."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    mp3 = KNOCKS_DIR / f"reply_{stamp}.mp3"
    try:
        asyncio.run(render_memo(spoken, mp3, ANNA_VOICE))
    except Exception as exc:                       # noqa: BLE001 — text must still land
        print(f"   ⚠ voice reply failed to render ({exc}) — pushing the text alone")
        return None, None
    return mp3, jsdelivr_url(mp3)


RECENT_WINDOW_HOURS = 24.0



RECENT_WINDOW_TURNS = 8



def _ts(raw: str | None) -> datetime | None:
    """A log timestamp as an aware datetime, or None if it is unparseable.
    Three functions parsed this inline (revealed_recently, capped_fire_days,
    and this file's window); one copy, so a naive stamp can never sneak past
    only two of them."""
    try:
        dt = datetime.fromisoformat((raw or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)



def recent_exchanges(klog: list, knock: dict,
                     hours: float = RECENT_WINDOW_HOURS,
                     limit: int = RECENT_WINDOW_TURNS) -> list[dict]:
    """The conversation Anna is actually in — across knocks, not just this one.

    Before 2026-08-02 this was `knock["exchanges"][-4:]`: one knock, four turns,
    and a reply to a NEW knock started from nothing. It also carried only two
    fields — what Andrew typed and what Anna wrote — so nothing on the record
    said what Anna *did*. He composed and sent a whole audio greeting on one
    turn, and told Andrew it was "still pending" on the next, because the record
    only ever showed the promise. Same gap ate a referent: "he's an anglophone"
    resolved to Andrew, because the turn that introduced the third party had
    been reduced to a line of text.

    Safe to widen: cold-fire accounting does NOT read this window.
    `revealed_recently()` owns the evidence of what Tamil was shown (Python-owned,
    48h, whole log) and `shown_in_knock()` stays scoped to its own knock. This is
    continuity only — it can never mint or deny a cold.

    The current knock's own tail is always carried, however old, so this can
    never show less than the per-knock view it replaces.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    keep = {id(x) for x in (knock.get("exchanges") or [])[-4:]}   # never regress
    sources = list(klog) + ([] if any(k is knock for k in klog) else [knock])
    rows, seen = [], set()
    for k in sources:
        for x in k.get("exchanges", []):
            at = _ts(x.get("at"))
            if at is None or id(x) in seen or (at < cutoff and id(x) not in keep):
                continue
            seen.add(id(x))
            rows.append((at, k, x))
    rows.sort(key=lambda r: r[0])
    out = []
    for _, k, x in rows[-limit:]:
        row = {"andrew_said": x.get("reply", ""),
               "anna_said": x.get("reply_line", "")}
        if k is not knock:
            row["earlier_thread"] = k.get("move", "") or k.get("modality", "")
        # What Anna DID. Absent means he did not do it — a promise with no
        # matching field here was never kept.
        row.update({out_key: x[src_key] for src_key, out_key in
                    (("spoke", "anna_sent_audio"), ("scheduled", "anna_queued_push"))
                    if x.get(src_key)})
        out.append(row)

    if not out and knock.get("reply"):
        # Legacy knock: replies predating the `exchanges` list live at top level.
        out = [{"andrew_said": knock["reply"],
                "anna_said": knock.get("reply_line", "")}]
    return out
