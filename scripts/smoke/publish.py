"""L4 — publish: the shared tail every writing lane ends in.

Commit ordering, the feed, the rebase net, the quiet-hours chokepoint, push
retry, and the rule that a derived file is re-rendered rather than merged.

This layer is where a lane's work becomes visible to Andrew, so its silent
failure is the expensive one: the state advanced, the commit landed, and the
dose never reached a surface he looks at. The cases assert arrival, not effort.
"""
import argparse
import email.utils
import importlib
import inspect
import io
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import _fixtures as fx
from ._fixtures import (
    check, lex_row, mechanism, read_json, REAL_BASE, Recorder, write_json,
)


def s6_queue_drain(mk, pq, sb: Path):
    print("\n6. Queue drain (regression #1)")
    prog = sb / "progress"
    klog_path, q_path = prog / "knock_log.json", prog / "push_queue.json"
    pushes, commits = Recorder(), Recorder()
    pq.push_to_phone, pq.commit_and_push = pushes, commits
    # The waking window lives in publish.py now — one owner, read by the rails,
    # this queue, and push_to_phone's backstop. Patch where it lives: `mk` holds
    # an import-time COPY, so patching there reaches morning_knock's rails and
    # nothing else. `in_waking_window` reads publish's binding.
    saved = (fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY)
    now = datetime.now(timezone.utc)

    def q_entry(qid: str, due_hours: float, force: bool = False) -> dict:
        return {"id": qid, "due": (now + timedelta(hours=due_hours)).isoformat(),
                "body": f"dose {qid}", "expected_target": "", "target_revealed": True,
                "audio_url": None, "move": "smoke", "force": force,
                "queued_at": now.isoformat()}

    args = argparse.Namespace(dry_run=False, no_commit=False)
    try:
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 99
        write_json(klog_path, [])
        write_json(q_path, [q_entry("qOLD", -2), q_entry("qNEW", -1), q_entry("qFUT", +6)])
        pq.cmd_drain(args)
        kept = [e["id"] for e in read_json(q_path)]
        check("one non-forced per tick, OLDEST first",
              len(pushes) == 1 and pushes[0][0] == "dose qOLD", f"pushes={list(pushes)}")
        check("newer + future entries deferred, not dropped", kept == ["qNEW", "qFUT"],
              f"kept={kept}")
        check("fired entry logged with queue_id",
              read_json(klog_path)[-1].get("queue_id") == "qOLD")
        pq.cmd_drain(args)
        check("next tick fires the deferred one",
              len(pushes) == 2 and pushes[1][0] == "dose qNEW")

        # quiet hours defer non-forced; --force punches through
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR = 0, 0
        write_json(q_path, [q_entry("qQUIET", -1), q_entry("qFORCE", -1, force=True)])
        pq.cmd_drain(args)
        check("quiet hours defers non-forced, fires forced",
              len(pushes) == 3 and pushes[2][0] == "dose qFORCE"
              and [e["id"] for e in read_json(q_path)] == ["qQUIET"])

        # daily cap defers non-forced; forced ignores it
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 0
        write_json(q_path, [q_entry("qCAP", -1), q_entry("qFORCE2", -1, force=True)])
        pq.cmd_drain(args)
        check("cap defers non-forced, fires forced",
              len(pushes) == 4 and pushes[3][0] == "dose qFORCE2"
              and [e["id"] for e in read_json(q_path)] == ["qCAP"])
    finally:
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = saved


def s15_push_retry(mk):
    print("\n15. Push delivery retry (regression #4)")
    # 2026-07-14: a transient runner-DNS blip killed the notify step after the
    # knock was already logged and committed — a phantom "fired" knock, red run.
    # push_to_phone now retries transient OSErrors; a final failure still raises.
    import os, urllib.error

    class FakeResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    calls = {"n": 0}
    sleeps = []
    real_urlopen, real_sleep = fx.pb.urllib.request.urlopen, fx.pb.time.sleep
    os.environ["ANNA_PUSH_WEBHOOK_URL"] = "https://smoke.invalid/hook"
    try:
        fx.pb.time.sleep = sleeps.append

        def flaky(req, *a, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise urllib.error.URLError(OSError("Temporary failure in name resolution"))
            return FakeResp()
        fx.pb.urllib.request.urlopen = flaky
        # requested=True: this case is about DELIVERY retry, not the rails —
        # without it the quiet-hours chokepoint short-circuits the whole test
        # whenever the suite runs after 21:00 local (2026-07-26).
        mk.push_to_phone("smoke", None, knock_id="smoke", requested=True)
        check("two blips then success — delivered", calls["n"] == 3, f"{calls['n']} calls")
        check("backoff between attempts", sleeps == [5, 10], f"sleeps={sleeps}")

        calls["n"] = 0
        def dead(req, *a, **kw):
            calls["n"] += 1
            raise urllib.error.URLError(OSError("no route"))
        fx.pb.urllib.request.urlopen = dead
        try:
            mk.push_to_phone("smoke", None, knock_id="smoke", requested=True)
            check("unreachable webhook still raises", False, "did not raise")
        except OSError:
            check("unreachable webhook still raises", True)
        check("gave up after 3 attempts", calls["n"] == 3, f"{calls['n']} calls")
    finally:
        fx.pb.urllib.request.urlopen, fx.pb.time.sleep = real_urlopen, real_sleep
        os.environ.pop("ANNA_PUSH_WEBHOOK_URL", None)


def s22_sfx_pause(sb: Path):
    """Cues become air; they never eat the speech around them.

    THE SILENT NO-OP, and it ran for three weeks: when the parser drops a
    spoken line the render still succeeds — it is simply shorter. No crash, no
    warning, no lint, and a duration nobody has a reference for. M74 shipped
    with 18 of its 52 lines missing and taught the -க்கு போகணும் frame to an
    empty room. So every assertion below counts what reached a VOICE, not that
    the parse ran, and the last one holds the whole corpus to it (2026-08-10 —
    the half of the 07-18 audit that was missed)."""
    print("\n22. [SFX] cues render as air, never dropped (M68 drama, 2026-07-18)")
    ra = importlib.import_module("render_audio")
    script = sb / "content" / "scripts" / "smoke_sfx.md"
    script.write_text(
        "# Tier 2, Mission 99 — Smoke\n\n"
        "[SFX: A phone rings in the dark.]\n\n"
        "**HOST (M):** Three fourteen in the morning.\n\n"
        "[SFX: Sheets rustle.]\n"
        "[Pause: 2 sec]\n", encoding="utf-8")
    dialogue, _ = ra.parse_script(str(script))
    check("SFX cue becomes a pause",
          dialogue[0]["speaker"] == "PAUSE" and dialogue[0]["seconds"] == 1.5,
          f"got {dialogue[0]}")
    check("SFX text never reaches a voice",
          not any("phone rings" in d.get("text", "") for d in dialogue))
    check("adjacent SFX + pause coalesce",
          dialogue[-1] == {"speaker": "PAUSE", "seconds": 3.5}, f"got {dialogue[-1]}")

    # A pause written INSIDE a spoken line is a beat in that line. The old
    # ordering asked "does this line CONTAIN a pause?" before "is this speech?",
    # so it answered yes and threw the dialogue away.
    inline = sb / "content" / "scripts" / "smoke_inline_pause.md"
    inline.write_text(
        "# Tier 2, Mission 98 — Smoke\n\n"
        "**RAJ (M):** He told our aunt, [Pause: 1 sec] \"station-kku poganum.\"\n\n"
        "**MAYA (F):** [Pause: 1 sec] Using that frame. [Pause: 0.5 sec] Need to go.\n\n"
        "**RAJ (M):** [pause] And she just fed him.\n\n"
        "[Pause: 2 sec]\n", encoding="utf-8")
    dlg, _ = ra.parse_script(str(inline))
    said = " ".join(d.get("text", "") for d in dlg)
    for fragment in ["He told our aunt,", "station-kku poganum.", "Using that frame.",
                     "Need to go.", "And she just fed him."]:
        check(f"inline pause keeps the speech: {fragment!r}", fragment in said, said)
    check("...and keeps it in written order, split around the beat",
          [d.get("text") for d in dlg[:3]] ==
          ["He told our aunt,", None, '"station-kku poganum."'], str(dlg[:3]))
    check("a fractional cue is honoured, not silently skipped",
          any(d.get("seconds") == 0.5 for d in dlg), str(dlg))
    check("a bare [pause] is one beat of air, never a spoken word",
          any(d.get("seconds") == 1.0 for d in dlg) and "pause" not in said.lower(), said)

    # THE CORPUS GUARD. The fixtures above prove the parser; this proves the
    # actual tank. Every line a writer meant to be heard must reach a voice —
    # a future script inventing a fourth pause dialect fails here, loudly.
    lost = []
    for path in sorted((REAL_BASE / "content" / "scripts").glob("*.md")):
        heard = " ".join(d.get("text", "")
                         for d in ra.parse_script(str(path))[0])
        for raw in path.read_text(encoding="utf-8").splitlines():
            m = ra.SPEAKER_RE.match(raw.strip())
            if not m:
                continue
            # re.split with one capture group interleaves text and the capture;
            # the even slots are the spoken pieces.
            for piece in ra.PAUSE_RE.split(m.group(2))[::2]:
                if piece and piece.strip() and piece.strip() not in heard:
                    lost.append(f"{path.name}: {piece.strip()[:40]}")
    check("no episode in the tank loses speech to a cue",
          not lost, f"{len(lost)} lost: {lost[:3]}")


def s23_ticket_end_to_end(sb: Path):
    print("\n23. suggest_targets: the ticket runs end-to-end (inbox 2026-07-17)")
    import contextlib
    import io
    st = importlib.import_module("suggest_targets")
    # The proven crash class: a special_* reference sidecar carries a STRING
    # mission; sorting it against integers took the ticket down (2026-07-17).
    (sb / "content" / "scripts" / "special_smoke.tags.json").write_text(
        json.dumps({"mission": "smoke reference tape", "register": "neutral"}),
        encoding="utf-8")
    cars = st.load_recent_sidecars()
    check("string-mission sidecar never enters the rotation",
          all(isinstance(c.get("mission"), int) for c in cars))
    check("sidecar history survives the special_ fixture", len(cars) > 0)

    argv, out = sys.argv, io.StringIO()
    try:
        sys.argv = ["suggest_targets.py"]
        with contextlib.redirect_stdout(out):
            st.main()
        ran = True
    except Exception as e:  # noqa: BLE001 — the check IS "it doesn't raise"
        ran, out = False, io.StringIO(f"raised {e!r}")
    finally:
        sys.argv = argv
    text = out.getvalue()
    check("ticket runs end-to-end on day-zero state", ran, text[:200])
    check("ticket prints the menu header", "SESSION TICKET" in text)
    check("day-zero ticket still serves new candidates",
          "not found" not in text, text[:200])

    print("\n24. feed duration is counted, not estimated (2026-07-22)")
    ra = importlib.import_module("render_audio")
    rr = importlib.import_module("rebuild_rss")
    # Our mp3s are raw frame concatenations with no Xing header, so a
    # filesize/bitrate estimate ran 3-5% long on every episode. 100 silence
    # frames is a known 2.4s: 24ms per frame at 24 kHz Layer III.
    fake = sb / "counted.mp3"
    fake.write_bytes(ra.SILENCE_FRAME * 100)
    check("frame scan is exact on a known frame count",
          abs(rr.mp3_duration(fake) - 2.4) < 0.01, rr.mp3_duration(fake))
    check("duration_hms rounds to the counted second",
          rr.duration_hms(fake, "FALLBACK") == "00:00:02", rr.duration_hms(fake, "x"))
    check("an unreadable file falls back instead of raising",
          rr.duration_hms(sb / "nope.mp3", "00:03:30") == "00:03:30")


def s25_studio_concurrency_and_secrets(sb: Path):
    print("\n25. Studio concurrency + credential-less hosts (2026-07-23)")
    ra = importlib.import_module("render_audio")

    # --- the race that cost a draft episode -------------------------------
    # Renders used a fixed "temp_audio_segments"; whichever finished first
    # rmdir'd it out from under the other mid-run (FileNotFoundError on the
    # next segment write). Scratch dirs must be per-run.
    a, b = ra.new_scratch_dir(), ra.new_scratch_dir()
    try:
        check("two renders get distinct scratch dirs", a != b, f"{a} == {b}")
        check("scratch dirs are real and writable",
              Path(a).is_dir() and Path(b).is_dir())
        # the bug shape itself: a scratch dir assigned from a string literal
        src = mechanism(Path(ra.__file__).read_text(encoding="utf-8"))
        check("scratch dir is never a hardcoded path",
              'temp_dir = "' not in src and "temp_dir = '" not in src)
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)

    # --- the deadlock guard on the state lock -----------------------------
    # run_studio/watchdog hold .studio.lock and spawn the renderer; the child
    # must inherit, never block on its own parent.
    prev = os.environ.get("STUDIO_LOCK_HELD")
    os.environ["STUDIO_LOCK_HELD"] = "1"
    try:
        check("child inherits a parent-held lock (no self-deadlock)",
              ra.acquire_state_lock() is None)
    finally:
        os.environ.pop("STUDIO_LOCK_HELD", None)
        if prev is not None:
            os.environ["STUDIO_LOCK_HELD"] = prev

    # --- auth failures are permanent, not transient ------------------------
    class Denied(Exception):
        pass
    check("credential error is fatal",
          ra.is_auth_error(Exception("Could not automatically determine credentials")))
    check("permission error is fatal", ra.is_auth_error(Exception("403 Permission denied")))
    check("network blip stays retryable",
          not ra.is_auth_error(Denied("503 backend unavailable")))

    # --- credential detection: BOTH outcomes mocked, so the test is hermetic --
    # These assertions are the whole point of the feature — "skip cleanly when
    # the secret is absent" — so they must not themselves depend on the host's
    # secrets. The first version did, and CI (which has NO credentials, exactly
    # the case the feature targets) went red: the tests for graceful-skip broke
    # on a host with nothing to skip. Mock google.auth.default both ways.
    import google.auth
    real_default = google.auth.default
    try:
        google.auth.default = lambda *a, **k: (_ for _ in ()).throw(
            Exception("Could not automatically determine credentials"))
        reason = ra.google_credentials_ready()
        check("no ADC → a reason, not a crash", isinstance(reason, str) and bool(reason))

        google.auth.default = lambda *a, **k: (object(), "fake-project")
        check("ADC present → no reason", ra.google_credentials_ready() is None)

        # Re-rendering an existing script needs TTS only. Gating it on the WRITER
        # would strand a scripted-but-unrendered episode on a host that can render.
        # (ADC still mocked-present here, so this isolates the writer axis.)
        rs = importlib.import_module("run_studio")
        real_which = fx.wr.shutil.which
        fx.wr.shutil.which = lambda cmd: None if cmd == "claude" else real_which(cmd)
        try:
            check("no writer → render path still allowed", rs.renderer_preflight() is None)
            check("no writer → fresh-episode path blocked", rs.preflight() is not None)
        finally:
            fx.wr.shutil.which = real_which
    finally:
        google.auth.default = real_default

    # --- GCP_SA_KEY → ADC, the same bridge anna.yml builds (2026-07-27) -----
    # CI writes the secret to a file and points GOOGLE_APPLICATION_CREDENTIALS
    # at it; a laptop had no equivalent, so a clone carrying the SAME secret in
    # .env still reported "this host cannot produce audio". A .env value must
    # also survive on one line, hence base64.
    import base64
    import contextlib
    import io
    saved_env = {k: os.environ.get(k) for k in ("GCP_SA_KEY", "GOOGLE_APPLICATION_CREDENTIALS")}
    key_file = Path(tempfile.gettempdir()) / "anna-gcp.json"
    try:
        doc = {"type": "service_account", "project_id": "smoke",
               "private_key": "-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n",
               "client_email": "a@smoke.iam.gserviceaccount.com"}
        for label, val in (("raw JSON", json.dumps(doc)),
                           ("base64 JSON", base64.b64encode(
                               json.dumps(doc).encode()).decode())):
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
            key_file.unlink(missing_ok=True)
            os.environ["GCP_SA_KEY"] = val
            check(f"{label} secret materializes a credentials file",
                  ra.materialize_sa_key() and key_file.exists())
            check(f"{label} secret points ADC at it",
                  os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == str(key_file))
            check(f"{label} round-trips intact",
                  json.loads(key_file.read_text(encoding="utf-8")) == doc)

        # A value that is not a key must be IGNORED, never written and never
        # half-configured: the real 2026-07-27 .env held 40 chars of something
        # else, and a silent write would have produced an auth error at
        # segment 0 instead of a legible reason before the render starts.
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        key_file.unlink(missing_ok=True)
        os.environ["GCP_SA_KEY"] = "2" * 40
        with contextlib.redirect_stdout(io.StringIO()) as warned:
            wrote = ra.materialize_sa_key()
        check("a non-key GCP_SA_KEY is ignored", wrote is None and not key_file.exists())
        check("...and says why, before any render starts",
              "not a service-account key" in warned.getvalue(), warned.getvalue())
        check("...and leaves ADC unconfigured rather than half-configured",
              not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

        # An operator-supplied path always wins over the secret.
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/preexisting.json"
        os.environ["GCP_SA_KEY"] = json.dumps(doc)
        check("an existing GOOGLE_APPLICATION_CREDENTIALS is never clobbered",
              ra.materialize_sa_key() is None
              and os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/preexisting.json")
    finally:
        key_file.unlink(missing_ok=True)
        for k, v in saved_env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v



def s31_feed_carries_every_pushed_dose(sb: Path):
    print("\n31. Every pushed dose is findable in the feed (2026-07-24)")
    rr = importlib.import_module("rebuild_rss")

    # Andrew's rule: "all audio you push me should go in the feed" — a dismissed
    # notification must stay replayable. Three producers write to knocks/, and
    # only `knock_` was ever taught to the feed, so a scheduled dose and a spoken
    # reply titled as their raw filename and sorted BELOW every episode.
    cases = {
        "knocks/knock_2026-07-05T22-58.mp3": "Knock",
        "knocks/queued_q1784931404_2026-07-24T23-50-00.mp3": "Scheduled",
        "knocks/reply_2026-07-24T23-55-10.mp3": "Reply",
    }
    for path, kind in cases.items():
        title = rr.knock_title(path, {})
        check(f"{kind.lower()} audio gets a real title", title.startswith(f"{kind} — 2026-"),
              f"got {title!r}")
        check(f"{kind.lower()} title carries no raw filename",
              ".mp3" not in title and "_" not in title.split("·")[0], f"got {title!r}")
        m = rr.KNOCK_AUDIO_RE.match(os.path.basename(path))
        check(f"{kind.lower()} audio sorts in the dated push band", m is not None)

    # The move label: the knock lane logs `mp3` (repo path), while the drain and
    # the reply judge log only the CDN url they pushed. Both must resolve.
    log = sb / "progress" / "knock_log.json"
    cdn = "https://cdn.jsdelivr.net/gh/arosselet/tamil-tutor@main/published_audio/knocks"
    write_json(log, [
        {"move": "ambient dose", "mp3": "published_audio/knocks/knock_2026-07-05T22-58.mp3"},
        {"move": "welcome james", "audio_url": f"{cdn}/queued_q1784931404_2026-07-24T23-50-00.mp3"},
        {"move": "said it aloud", "reply_audio_url": f"{cdn}/reply_2026-07-24T23-55-10.mp3"},
    ])
    # rebuild_rss addresses the repo by RELATIVE path (AUDIO_DIR, the knock log),
    # so it must be exercised from a repo root — here, the sandbox's.
    cwd = os.getcwd()
    try:
        os.chdir(sb)
        meta = rr.knock_meta()
    finally:
        os.chdir(cwd)
    # Keyed on the STEM since 2026-08-29 — `feed_items` became the second reader
    # and had already split it out of the enclosure url. `knock_title` is still
    # handed the "knocks/…" path, so both halves of the key change are exercised.
    for path, move in (("knocks/knock_2026-07-05T22-58.mp3", "ambient dose"),
                       ("knocks/queued_q1784931404_2026-07-24T23-50-00.mp3", "welcome james"),
                       ("knocks/reply_2026-07-24T23-55-10.mp3", "said it aloud")):
        stem = path.removeprefix("knocks/").removesuffix(".mp3")
        got = meta.get(stem, ("", ""))[0]
        check(f"move label resolves: {move}", got == move, f"got {got!r}")
        check(f"title carries the move: {move}", move in rr.knock_title(path, meta))

    # "Nothing that isn't playable by my podcast player" (Andrew): extension is
    # not proof — a truncated render or an lfs pointer is a .mp3 that is not audio.
    check("a playability floor exists", rr.MIN_PLAYABLE_BYTES > 0)

    # Feed order must be a function of the library, not the host's listdir():
    # the two special_ files tie at (10, 0), and a rebuild on another machine
    # silently swapped them.
    src = mechanism((REAL_BASE / "scripts" / "rebuild_rss.py").read_text(encoding="utf-8"))
    check("feed sort is deterministic (filename breaks ties)",
          "key=lambda f: (sort_key(f), f)" in src)

    # A dose is announced in Andrew's zone no matter which machine rebuilds.
    # `localtime=True` stamped the HOST's zone, so the laptop wrote -0400 and the
    # CI container +0000 for one listener in one timezone. Same instant, two
    # faces. Simulate a UTC host: the offset must not move.
    stamp = datetime(2026, 7, 24, 19, 56, 25, tzinfo=rr.LOCAL_TZ).timestamp()
    saved_tz = os.environ.get("TZ")
    # `time.tzset()` is POSIX-only. Calling it unguarded raised AttributeError on
    # Andrew's Windows box, and because it fired mid-suite it aborted every case
    # AFTER this one — so the local health check has never once run to completion
    # there, only in CI (2026-07-31). The ASSERTIONS are host-zone independent by
    # construction (fromtimestamp is handed rr.LOCAL_TZ explicitly), so they run
    # everywhere; only the belt-and-braces UTC-host SIMULATION needs the syscall,
    # and it is skipped where the OS has none. Never guard by re-raising: a
    # cross-platform gap in the harness must not read as a failure of the code.
    can_simulate_host_tz = hasattr(time, "tzset")
    try:
        if can_simulate_host_tz:
            os.environ["TZ"] = "UTC"
            time.tzset()
        pub = email.utils.format_datetime(datetime.fromtimestamp(stamp, rr.LOCAL_TZ))
        # Expected offset comes from LOCAL_TZ at that instant. Hardcoding "-0400"
        # made this a test of New York rather than of "Andrew's zone" (2026-08-09).
        want_off = datetime.fromtimestamp(stamp, rr.LOCAL_TZ).strftime("%z")
        check("a pubDate is stamped in Andrew's zone on a UTC host", pub.endswith(want_off),
              f"got {pub}, wanted offset {want_off}")
        check("the pubDate names the local wall clock", "19:56:25" in pub, f"got {pub}")
    finally:
        if can_simulate_host_tz:
            if saved_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = saved_tz
            time.tzset()
    # Comments stripped, per s29: rebuild_rss EXPLAINS the retired host-clock call
    # in prose, and a guard that trips on its own documentation is one nobody keeps.
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    check("the feed never stamps in the host's zone",
          "localtime=True" not in code, "rebuild_rss still uses the host clock")

    # Measure once, then freeze. Duration described a file that never changes, but
    # was re-derived on every rebuild from whatever tool the host had — the laptop
    # has ffprobe, the CI container does not, so each cloud rebuild reverted the
    # library to the frame scan (M72: 13:12 announced for a 10:02 episode, 2026-07-25).
    # The real guard is behavioural: rebuild with ffprobe gone and nothing may move.
    feed = sb / "rss.xml"
    published = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
  <item><title>T</title>
    <enclosure url="{u}" length="9" type="audio/mpeg"/><guid>{u}</guid>
    <pubDate>Thu, 23 Jul 2026 23:27:39 -0400</pubDate>
    <itunes:duration>00:10:02</itunes:duration></item>
</channel></rss>"""
    cwd = os.getcwd()
    try:
        os.chdir(sb)
        url = f"{rr.BASE_URL}/{rr.AUDIO_DIR}/knocks/knock_2026-07-05T22-58.mp3"
        feed.write_text(published.format(u=url), encoding="utf-8")
        prior = rr.existing_items().get(url, {})
        check("a published duration is recovered for the rebuild",
              prior.get("duration") == "00:10:02", f"got {prior}")
        check("a published pubDate is still recovered alongside it",
              prior.get("pubDate", "").endswith("-0400"), f"got {prior}")
        # Malformed markup must not drop either field — one unescaped character
        # once wiped every saved date and collapsed the feed to a single "now".
        feed.write_text(published.format(u=url).replace("<title>T", "<title>R & D"),
                        encoding="utf-8")
        rescued = rr.existing_items().get(url, {})
        check("a malformed feed still yields both published values",
              rescued.get("duration") == "00:10:02" and rescued.get("pubDate"),
              f"got {rescued}")
    finally:
        os.chdir(cwd)
    check("duration is preserved, not re-derived",
          'prior.get("duration") or duration_hms' in code,
          "rebuild_rss still recomputes a published duration")


def s35_quiet_hours_chokepoint(sb: Path):
    """Quiet hours belong to `push_to_phone`, not to each lane (2026-07-26).

    They used to be enforced per-lane: `rails_gate` for knocks, `in_waking_window`
    in the queue, and a hand-rolled hour compare in both `run_studio` and
    `render_soak` — FOUR copies, and `render_drill` had none, which is how a drill
    reached the phone at 23:42. The gap was not on a CI lane, so nothing had fired
    from the runner — this case is what keeps it that way when a lane is added."""
    print("\n35. Quiet hours: one chokepoint, no per-lane copies (2026-07-26)")
    import contextlib
    import io
    mk = importlib.import_module("morning_knock")
    # The scripts directory, named absolutely rather than relative to THIS file:
    # this case is about to move into smoke/, where `__file__.parent` would
    # quietly become the test package and every source read below would miss.
    src_dir = REAL_BASE / "scripts"

    real_urlopen = fx.pb.urllib.request.urlopen
    sent = []

    class FakeResp:
        status = 200
        def read(self): return b""
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, *a, **k):
        sent.append(getattr(req, "full_url", req))
        return FakeResp()

    # Built from LOCAL_TZ, not from frozen UTC instants. They used to be literals
    # (`3:42Z  # 23:42 EDT`), which quietly encoded America/New_York into the
    # quiet-hours case: the moment learner.json named another zone that same
    # instant became mid-morning and the check inverted (2026-08-09). A guard for
    # a rule stated in local hours has to be built in local hours.
    noon_l = datetime.now(mk.LOCAL_TZ).replace(hour=12, minute=0, second=0, microsecond=0)
    night = noon_l.replace(hour=23, minute=42).astimezone(timezone.utc)
    noon = noon_l.astimezone(timezone.utc)
    real_env = os.environ.get("ANNA_PUSH_WEBHOOK_URL")
    try:
        fx.pb.urllib.request.urlopen = fake_urlopen
        os.environ["ANNA_PUSH_WEBHOOK_URL"] = "http://smoke.invalid/push"
        check("the waking window has ONE definition",
              fx.pb.in_waking_window(noon) and not fx.pb.in_waking_window(night),
              "in_waking_window disagrees with the rails")

        real_now = fx.pb.in_waking_window
        fx.pb.in_waking_window = lambda now=None: False
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                pushed = mk.push_to_phone("a drill at 23:42", None)
            check("an UNrequested push is refused during quiet hours",
                  pushed is False and not sent, f"sent={sent}")
            check("the refusal says where the artifact went",
                  "on the feed for the morning" in out.getvalue(), f"got {out.getvalue()!r}")
            with contextlib.redirect_stdout(io.StringIO()):
                pushed = mk.push_to_phone("your reply", None, requested=True)
            check("a REQUESTED push still lands — answering his tap is not an interruption",
                  pushed is True and len(sent) == 1, f"sent={sent}")
        finally:
            fx.pb.in_waking_window = real_now
    finally:
        fx.pb.urllib.request.urlopen = real_urlopen
        if real_env is None:
            os.environ.pop("ANNA_PUSH_WEBHOOK_URL", None)
        else:
            os.environ["ANNA_PUSH_WEBHOOK_URL"] = real_env

    # No lane may re-implement the rule; every push must go through the chokepoint.
    for name in ("run_studio.py", "push_queue.py", "render_drill.py", "render_soak.py"):
        src = mechanism((src_dir / name).read_text(encoding="utf-8"))
        check(f"{name} does not hand-roll the waking-hour compare",
              "WAKING_START_HOUR <=" not in src, f"{name} carries its own copy")
    check("in_waking_window has one home",
          "def in_waking_window" not in mechanism((src_dir / "push_queue.py")
                                                  .read_text(encoding="utf-8")),
          "the queue's copy survived")


def s43_sidecar_callback_never_drops_silently(sb: Path):
    """An unregisterable sidecar word is reported, never swallowed (2026-07-31).

    M78's sidecar filed இருந்துச்சு under `callbacks_used`, but the word had never
    entered the lexicon — Anna had recast it in chat three times and never
    registered it. Only `new_words_landed` may CREATE a record, so the branch fell
    through in total silence: the episode shipped with three real exposures of the
    one word Andrew had been asking for since 07-25, and the ledger held no trace
    of it. Unschedulable, uncollectable, invisible to suggest_targets — and
    indistinguishable from success in the log.

    Creating it here would be the wrong fix: a callback CLAIMS the word already
    exists, so an unresolvable one is far more likely a variant of a real record,
    and inventing a duplicate poisons the axes. The frame branch above had the
    right answer all along — report and skip. Silence is the only thing ruled out.

    Also covers the standalone renderer's .env gap found the same hour: a render
    inside run_studio always had credentials because IT loaded .env, while the
    same command run by hand reported 'this host cannot produce audio'."""
    print("\n43. A sidecar callback that resolves to nothing is loud (2026-07-31)")
    import contextlib, io, inspect
    ra = importlib.import_module("render_audio")

    script = sb / "content" / "scripts" / "tier2_mission97.md"
    script.parent.mkdir(parents=True, exist_ok=True)
    # A word the lexicon cannot possibly hold — இருந்துச்சு itself was registered
    # the day this case was written, and a fixture that drifts into existence
    # turns a regression test green for the wrong reason.
    ghost = "ஸ்மோக்பூதம்"
    script.write_text(f"# Tier 2, Mission 97 — Smoke\n\n**Anna:** {ghost}.\n",
                      encoding="utf-8")
    (script.with_suffix(".tags.json")).write_text(json.dumps({
        "callbacks_used": {ghost: 3},      # never registered — the bug
        "new_words_landed": {},
    }, ensure_ascii=False), encoding="utf-8")

    lex_path = sb / "progress" / "lexicon.json"
    saved_lex = lex_path.read_bytes()
    # No mp3 is written: register_mission_in_state's nested get_duration swallows
    # a missing file and returns its 3.0 default, so duration is not under test here.
    #
    # The day-zero fixture is an EMPTY lexicon, and the exposure block is guarded
    # by a bare `if lexicon:` — so on the fixture as shipped this whole code path
    # is skipped and every assertion below would pass vacuously. Seed one row.
    # (Worth knowing on its own: a genuinely blank day-zero clone registers no
    # words from its first episode at all. Left alone here — day-zero behaviour
    # is BOOTSTRAP's question, not this case's.)
    try:
        lex = read_json(lex_path)
        lex["ஸ்மோக்ஆங்கர்"] = lex_row(gloss="anchor", recognition="solid")
        write_json(lex_path, lex)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ra.register_mission_in_state(script, sb / "published_audio" / "tier2_mission97.mp3")
        text = out.getvalue()
        lex = read_json(lex_path)

        check("an unresolvable callback is NOT invented as a lexicon record",
              ghost not in lex, "a duplicate record was created")
        check("...and the drop is reported, not silent",
              "resolve to no lexicon word" in text, f"got {text[:300]!r}")
        check("...naming the word so the operator can re-file it",
              ghost in text, f"got {text[:300]!r}")
        check("...and saying what to do about it",
              "new_words_landed" in text, f"got {text[:300]!r}")

        # The control: filed correctly, it registers and stops warning.
        (script.with_suffix(".tags.json")).write_text(json.dumps({
            "callbacks_used": {},
            "new_words_landed": {ghost: 3},
        }, ensure_ascii=False), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ra.register_mission_in_state(script, sb / "published_audio" / "tier2_mission97.mp3")
        lex = read_json(lex_path)
        check("the same word filed as NEW does enter the lexicon",
              ghost in lex, "still absent")
        check("...and nothing is reported unresolved",
              "resolve to no lexicon word" not in out.getvalue())

        # ── A BROKEN SIDECAR IS NOT A MISSING ONE (2026-08-24) ──────────────
        # The block above proves an UNRESOLVABLE key is reported. This proves the
        # worse case one level up: a sidecar that exists and cannot be PARSED.
        # It used to be `except (json.JSONDecodeError, OSError): pass`, and the
        # code then fell through to scraping `**bold**` tokens out of the
        # markdown — which is not where an episode's vocab is written. The result
        # was a PLAUSIBLE word list from the wrong source: episodes.json and every
        # row's `seen_in` crediting words the episode never taught, the render
        # succeeding, and every instrument green.
        #
        # THE SILENT NO-OP, stated: a swallowed parse error and a sidecar with no
        # callbacks look identical from outside. So this asserts the two things
        # that tell them apart — the failure is NAMED, and the wrong-source
        # fallback does NOT run. Under-claiming is the ledger's own law
        # (claim_payload, 2026-07-17); inventing is the defect.
        bold = "ஸ்மோக்பொல்ட்"
        script.write_text(f"# Tier 2, Mission 97 — Smoke\n\n**{bold}** is bold.\n",
                          encoding="utf-8")
        (script.with_suffix(".tags.json")).write_text("{ this is not json",
                                                      encoding="utf-8")
        eps_path = sb / "progress" / "episodes.json"
        write_json(eps_path, {})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ra.register_mission_in_state(script, sb / "published_audio" / "tier2_mission97.mp3")
        text = out.getvalue()
        check("an UNREADABLE sidecar is reported, not swallowed",
              "COULD NOT BE READ" in text, f"got {text[:300]!r}")
        check("...naming the file and the parse error",
              "tier2_mission97.tags.json" in text and "JSONDecodeError" in text,
              f"got {text[:300]!r}")
        check("...and saying what to do about it",
              "Fix the sidecar" in text, f"got {text[:300]!r}")
        words = (read_json(eps_path).get("97") or {}).get("words", [])
        check("...and the bold-scrape fallback does NOT run — a plausible word "
              "list from the wrong source is worse than none",
              bold not in words, f"the scrape credited {words}")
        check("...so the episode under-claims rather than invents", words == [],
              f"got {words}")

        # Found by this very case on its first run: the state paths were
        # CWD-relative, so importing the sandbox module without chdir'ing wrote
        # a fake mission into the REAL progress/ files. Assert the containment,
        # not just the behaviour — a test that mutates live state is worse than none.
        real_lex = read_json(REAL_BASE / "progress" / "lexicon.json")
        real_eps = read_json(REAL_BASE / "progress" / "episodes.json")
        check("the render's state writes stay inside the sandbox",
              ghost not in real_lex, "the smoke run wrote into the real lexicon")
        check("...including the episode registry",
              "97" not in real_eps, "the smoke run wrote into the real episodes.json")
    finally:
        lex_path.write_bytes(saved_lex)

    src = mechanism(inspect.getsource(ra.main))
    check("the standalone renderer loads .env, like run_studio does before it",
          "load_env" in src, "a hand-run render still cannot find GCP_SA_KEY")


def s68_the_convergence_audit_fixes(sb: Path):
    """The 2026-08-20 audit's live defects, each asserted where it can actually
    fail. Every one of these was a state INDISTINGUISHABLE FROM SUCCESS — the
    reason a holistic pass found them and seven weeks of green runs did not.

    1. THE COMMISSION DETECTION. `dose_channel` records that SOME soak order was
       standing when a slip was made, for some other payload. slip_patterns fed
       it into `channels`, so every slip inherited one, `uncommissioned` could
       never be true and `escalate`'s one-channel test could never match. Both
       gates were dead from 2026-07-31; on live state 0 of 22 patterns could
       trip either. Silent no-op: a debt ledger that always reads "nothing
       owed" looks exactly like a system with no debts.

    2. THE CLOCK. suggest_targets and generate_callbacks scored staleness on
       date.today() — the HOST's clock — while last_surfaced is stamped with
       local_today(). state_io names this seam and these two callers were
       missed. Silent no-op: an off-by-one due date is invisible; the menu is
       still full, the items are just the wrong ones on a UTC runner.

    3. TARGET_REVEALED. Three defaults in one file: the CLI store_true gave
       False, enqueue() and the drain fallback gave True. A CLI-queued dose
       silently meant "not revealed", so its reply could score COLD off a body
       that had handed the Tamil over. Silent no-op: an inflated cold fire is
       indistinguishable from a real one, and it moves the production axis.

    4. THE PUBLISH NET. render_audio ran a raw add/commit/push with no rebase,
       wrapped in a bare `except` that printed a warning and exited 0 — so
       run_studio then printed "rendered and published" for an episode that
       never landed. Asserted structurally: the lane must route through
       commit_and_push (which carries _rebase_onto_main) and must NOT swallow.

    5. THE EPISODE TITLE. The Architect was never told to emit an H1, so
       rebuild_rss.get_title_from_md — which reads exactly one line — fell back
       to the filename for 30 of 90 episodes on the PUBLIC feed. Asserted
       against the real reader, on the real line it reads.

    6. THE AGENT CONTRACT. AGENTS.md was a symlink; a Windows checkout writes
       that as a 9-byte text file containing "CLAUDE.md", so an AGENTS.md-reading
       agent got no instructions and git status stayed clean."""
    print("\n68. The convergence-audit fixes (2026-08-20)")
    import contextlib
    import subprocess as _sp
    sl = importlib.import_module("slips")
    st = importlib.import_module("suggest_targets")
    gc_ = importlib.import_module("generate_callbacks")
    pq = importlib.import_module("push_queue")
    sio = importlib.import_module("state_io")

    # --- 1. the commission detection, on the exact shape that disarmed it ----
    slip_path = sb / "progress" / "slip_log.json"
    learner_path = sb / "progress" / "learner.json"
    keep = (slip_path.read_bytes(), learner_path.read_bytes())
    try:
        slip_path.write_text("[]", encoding="utf-8")
        learner = read_json(learner_path)
        for k in ("slip_closes", "slip_commissions"):
            learner.pop(k, None)
        write_json(learner_path, learner)
        with contextlib.redirect_stdout(io.StringIO()):
            # TWO slips, BOTH carrying a dose_channel — the shape every real
            # slip has, because sync_state stamps the standing order on all of
            # them. Before the fix this pattern read as fully commissioned.
            sl.append_slips([{"tag": "audit-tag", "said": "a", "want": "b"}],
                            lane="chat", dose_channel="episode", when="2026-08-01")
            sl.append_slips([{"tag": "audit-tag", "said": "a", "want": "b"}],
                            lane="chat", dose_channel="drill",
                            when=sio.local_today().isoformat())
        p = {x["tag"]: x for x in sl.slip_patterns()}["audit-tag"]
        check("a live pattern with dose_channel stamps is still a real pattern",
              p["pattern"] and p["live"], p)
        # THE ASSERTION THAT WOULD HAVE CAUGHT IT.
        check("...and an unrelated standing order does NOT count as its dose",
              p["channels"] == [], f"inherited {p['channels']}")
        check("...so the debt is visible — this read False for three weeks",
              p["uncommissioned"], "the detection is disarmed again")
        check("...and it is not told to change a format nothing ever tried",
              not p["escalate"], "escalated off a phantom dose")
        # Declaring one is the ONLY thing that fills channels.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.record_slip_commission(["audit-tag"], {"channel": "soak"},
                                      today="2026-08-02")
        p = {x["tag"]: x for x in sl.slip_patterns()}["audit-tag"]
        check("a DECLARED commission is what discharges the debt",
              p["channels"] == ["soak"] and not p["uncommissioned"], p["channels"])
    finally:
        slip_path.write_bytes(keep[0])
        learner_path.write_bytes(keep[1])

    # --- 2. the clock: both selectors must read ANDREW's day -----------------
    for mod, name in ((st, "suggest_targets"), (gc_, "generate_callbacks")):
        src = mechanism((sb / "scripts" / f"{name}.py").read_text(encoding="utf-8"))
        check(f"{name} scores staleness on the learner's clock, not the host's",
              "date.today()" not in src, "date.today() is back — UTC runners drift a day")
        check(f"...and {name} takes it from the one owner",
              "local_today" in src and hasattr(mod, "local_today"), name)

    # --- 3. one field, one default -------------------------------------------
    # Drive the real CLI, because the default that was wrong was the PARSER's —
    # reading the function signature alone is what let the three disagree.
    pq_src = mechanism((sb / "scripts" / "push_queue.py").read_text(encoding="utf-8"))
    cli_default = _sp.run([sys.executable, str(sb / "scripts" / "push_queue.py"),
                           "add", "--help"], capture_output=True,
                          encoding="utf-8", errors="replace").stdout
    check("the CLI exposes both directions instead of a one-way store_true",
          "--no-target-revealed" in cli_default, cli_default[-300:])
    enqueue_default = inspect.signature(pq.enqueue).parameters["target_revealed"].default
    check("enqueue() defaults to the conservative end — never over-credit a cold fire",
          enqueue_default is True, enqueue_default)
    check("...and the drain falls back the same way, so all three agree",
          '"target_revealed", True' in pq_src,
          "the drain fallback drifted from the other two")

    # --- 4. the publish net --------------------------------------------------
    tail = mechanism((sb / "scripts" / "render_audio.py").read_text(encoding="utf-8"),
                     after="Lifecycle hooks")
    check("the episode lane publishes through the shared rebase net",
          "commit_and_push(" in tail, "raw git push is back — no rebase under it")
    check("...and a failed publish is LOUD, not a printed warning over exit 0",
          "Lifecycle hooks failed" not in tail, "the bare except is back")

    # --- 5. the episode's public name ----------------------------------------
    rr = importlib.import_module("rebuild_rss")
    tmp = sb / "content" / "scripts" / "smoke_title_probe.md"
    try:
        tmp.write_text("[SFX: chairs scraping]\n\n# Tier 2, Mission 91 — The Real Name\n",
                       encoding="utf-8")
        check("an H1 below the first line is as absent as no H1 — the reader sees one line",
              rr.get_title_from_md(str(tmp)) == "smoke_title_probe.md",
              rr.get_title_from_md(str(tmp)))
        tmp.write_text("# Tier 2, Mission 91 — The Real Name\n\n[SFX: chairs]\n",
                       encoding="utf-8")
        check("...and a first-line H1 becomes the feed's title",
              rr.get_title_from_md(str(tmp)) == "Tier 2, Mission 91 — The Real Name",
              rr.get_title_from_md(str(tmp)))
    finally:
        tmp.unlink(missing_ok=True)
    rs_src = mechanism((sb / "scripts" / "run_studio.py").read_text(encoding="utf-8"))
    check("the lint refuses a script whose FIRST line is not an H1",
          'splitlines()[0].strip().startswith("# ")' in rs_src, "the title lint is gone")
    check("...and the Architect is actually told to write one",
          "VERY FIRST LINE" in rs_src
          and "first line" in (sb / "protocol" / "studio" / "architect.md")
          .read_text(encoding="utf-8").lower(),
          "the prompt or the role file lost the rule")

    # --- 6. the agent contract is a real file --------------------------------
    agents = sb / "AGENTS.md"
    check("AGENTS.md carries real instructions, not a symlink's path text",
          agents.stat().st_size > 500, f"{agents.stat().st_size} bytes")
    mode = _sp.run(["git", "ls-files", "-s", "AGENTS.md"], cwd=REAL_BASE,
                   capture_output=True, encoding="utf-8").stdout.split()
    check("...and git stores it as a regular file, so a Windows clone gets it",
          mode and mode[0] == "100644", mode[0] if mode else "untracked")


def s73_one_tail_for_the_render_family(sb: Path):
    """The write -> render -> publish family's shared tail (2026-08-24, Q1).

    UNTESTED UNTIL NOW, by anything. Both existing drives of a render lane's
    `main()` pass `--dry-run`, which returns before the tail, and the only other
    coverage was a source-grep of one call site. So the sequence that records
    exposure, stamps a soak order, builds the commit and reaches the phone — for
    three lanes, soon five — had never been executed by a test.

    THE SILENT NO-OP, answered: if this function did nothing at all, every lane
    would still print "done", still exit 0, and still look exactly like a
    successful dose. Nothing downstream raises. So the assertions are on the
    EFFECT — what reached the commit and what reached the phone — never on the
    fact that it ran.

    The last block is the one that protects the design rather than the behaviour.
    `commit` and `notify` are passed IN so that a lane's own binding is what gets
    called, which is what keeps the suite's 59 module-attribute stubs
    intercepting once a shared runner does the work (hazard H1). If this function
    ever reaches for `publish.push_to_phone` directly instead of the argument, all
    of them silently stop intercepting and a test hits real git and a real phone.
    That regression would be invisible in every other assertion here, so it gets
    its own: the module-level names are booby-trapped, and must never fire.
    """
    print("\n73. One tail for the write→render→publish family (2026-08-24)")
    import contextlib
    lanes = importlib.import_module("lanes")

    mp3 = sb / "published_audio" / "smoke_family.mp3"
    mp3.parent.mkdir(parents=True, exist_ok=True)
    mp3.write_bytes(b"ID3fake")
    script = sb / "content" / "scripts" / "smoke_family.md"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("the tape's story", encoding="utf-8")

    fx.pb.refresh_feed = lambda: None          # the feed has its own cases (s31)
    commits, pushes = [], []

    def drive(*, delivered=("ஸ்மோக்"), claimed=False, extra=(), exposed=True,
              stamped=True, notified=True, title="smoke name"):
        lanes.record_exposure = lambda words: exposed and bool(words)
        lanes.mark_soak_delivered = lambda lane: stamped
        commits.clear(); pushes.clear()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            got = lanes.deliver_rendered(
                mp3=mp3, lane="soak", delivered=list(delivered), claimed=claimed,
                message="Soak loop: smoke", copy="soak loop's up 🎧",
                noun="soak loop", extra_paths=list(extra), title=title,
                commit=lambda paths, msg: commits.append((list(paths), msg)),
                notify=lambda copy, url: (pushes.append((copy, url)), notified)[1])
        return got, out.getvalue()

    # ── THE DESIGN, before anything else, so its diagnosis arrives BEFORE the
    # crash it exists to prevent. `commit` and `notify` are ARGUMENTS: a lane
    # passes its own binding, which is what keeps this suite's 59
    # module-attribute stubs intercepting once a shared runner does the work
    # (hazard H1). The failure mode is silent by nature — the tail would just
    # start calling the real thing — so it is asserted structurally, twice:
    # nothing boundary-shaped is bound into this module at all, and a booby trap
    # on the owner's names never fires. Measured: with the import form restored,
    # the first check goes red naming the binding; without it the case dies in a
    # git subprocess, which is safe but unreadable.
    def boom(*a, **kw):
        raise AssertionError(
            "deliver_rendered reached for a module-level boundary instead of the "
            "`commit`/`notify` it was handed. Every lane-level stub here stops "
            "intercepting the moment it does that, and a test then writes real "
            "git history and pushes to a real phone.")
    fx.pb.commit_and_push, fx.pb.push_to_phone = boom, boom
    for seam in ("commit_and_push", "push_to_phone"):
        bound = getattr(lanes, seam, None)
        check(f"the tail binds no {seam} of its own — the seam is the argument",
              bound is None, f"lanes.{seam} = {bound!r}")

    # ── the mp3 leads the commit, or the CDN has nothing to serve ────────────
    drive(claimed=True, extra=[script])
    paths, msg = commits[0]
    check("the mp3 is FIRST in the commit — push_to_phone pre-warms the CDN and "
          "jsDelivr can only serve what is already on main",
          paths[0] == mp3, f"got {[Path(p).name for p in paths]}")
    check("...and the lane's own extra paths ride the SAME commit",
          script in paths, f"got {[Path(p).name for p in paths]}")
    check("...under the lane's message", msg == "Soak loop: smoke", msg)

    # ── the two conditional state paths, both directions ────────────────────
    # ── THE DOSE IS NAMED, AND THE NAME IS COMMITTED (2026-09-01) ───────────
    # A soak leaves no script and no caption, so the sheet's name is the only
    # record that it was ever about anything; if it does not ride this commit the
    # feed can only call the dose by its filename, which is how eight soaks
    # shipped as "nothing to do but listen" and two of them became unrateable.
    # Asserted as BOTH halves — written, and in the commit — because a write that
    # never leaves the runner is indistinguishable from success from in here.
    at = importlib.import_module("audio_titles")
    check("the dose's name is recorded under its stem",
          at.load().get("smoke_family") == "smoke name", str(at.load()))
    check("...and the map rides the SAME commit as the mp3 it names",
          fx.si.AUDIO_TITLES_PATH in commits[0][0],
          f"got {[Path(p).name for p in commits[0][0]]}")
    # An UNNAMED dose must not commit the map — a no-op write would put a file in
    # every commit forever and make "was this dose named?" unreadable from history.
    drive(claimed=True, title="")
    check("a dose with no name commits no title map",
          fx.si.AUDIO_TITLES_PATH not in commits[0][0],
          f"got {[Path(p).name for p in commits[0][0]]}")
    check("...and does not erase the name already recorded for that stem",
          at.load().get("smoke_family") == "smoke name", str(at.load()))
    drive(claimed=True, extra=[script])

    check("a recorded exposure puts the lexicon in the commit",
          fx.si.LEXICON_PATH in commits[0][0])
    check("a stamped order puts learner.json in the commit",
          fx.si.LEARNER_PATH in commits[0][0])
    drive(claimed=True, exposed=False, stamped=False)
    check("nothing exposed -> the lexicon is NOT committed",
          fx.si.LEXICON_PATH not in commits[0][0], f"got {commits[0][0]}")
    check("nothing stamped -> learner.json is NOT committed",
          fx.si.LEARNER_PATH not in commits[0][0], f"got {commits[0][0]}")

    # ── the stamp claims a debt is PAID; it must follow the lane's own test ──
    stamped_for = []
    lanes.mark_soak_delivered = lambda lane: stamped_for.append(lane) or True
    drive(claimed=False)
    check("claimed=False never stamps — a wrong stamp buries an owed dose",
          not stamped_for, f"stamped {stamped_for}")

    # ── what reaches the phone ──────────────────────────────────────────────
    got, said = drive()
    copy, url = pushes[0]
    check("the notification carries the lane's copy", copy == "soak loop's up 🎧", copy)
    check("...and the jsDelivr URL for THIS mp3",
          url.startswith("https://cdn.jsdelivr.net/gh/") and mp3.name in url, url)
    check("...and the return says it landed", got is True)
    check("...and the closing line names the lane's noun",
          "done — soak loop on the feed and the lock screen" in said, said.strip())
    got, said = drive(notified=False)
    check("quiet hours propagate — the tail reports NOT on the lock screen",
          got is False and "and the lock screen" not in said, said.strip())

    # Every drive above ran with `pb.commit_and_push` / `pb.push_to_phone`
    # booby-trapped. Reaching either would have raised out of this case.
    check("...and no drive ever touched the owner's names directly",
          len(commits) == 1 and len(pushes) == 1,
          f"commits={len(commits)} pushes={len(pushes)}")


def s74_a_derived_file_follows_its_source(sb: Path):
    """chat.md is a pure render of knock_log.json (2026-08-24).

    `render_chat` reads the log and nothing else, so a commit that carries the log
    without a fresh render publishes a page that is already stale — and it stays
    stale until some later lane happens to rebuild it. That is precisely what the
    old "Log tap" step did: a tap's "👍 acked" sat unrendered for hours
    (2026-08-04).

    Five lanes obeyed the rule by hand, each calling render_chat() while building
    its own commit list: morning_knock's fire AND its silence tick, both
    knock_reply judges, the queue drain, and sync_state's knock-response. Five
    copies of one rule is the shape this refactor exists to retire, and it is a
    rule with no natural home in any of them.

    THE SILENT NO-OP: a stale chat.md raises nothing. The commit succeeds, the
    push succeeds, every instrument reads green, and the only symptom is that the
    page Andrew opens on his phone is missing the exchange he just had. So the
    teeth are on the CONTENT, not on the path list — appending the path without
    rebuilding the file would satisfy a membership check and still ship the stale
    page.
    """
    print("\n74. A derived file follows its source (2026-08-24)")
    klog_path = sb / "progress" / "knock_log.json"
    chat_path = sb / "progress" / "chat.md"
    fx.pb.refresh_feed = lambda: None          # the feed has its own cases (s31)

    marker = "ஸ்மோக்டெரைவ்டு"
    write_json(klog_path, [{"acted": True, "date": "2026-08-24",
                            "timestamp": "2026-08-24T09:00:00+00:00",
                            "body": marker, "modality": "text", "move": "smoke"}])
    chat_path.write_text("STALE — written before that log entry existed\n",
                         encoding="utf-8")

    paths, _ = fx.pb.publish([klog_path], "smoke", feed=False)
    names = [Path(q).name for q in paths]
    check("a commit carrying the knock log also carries chat.md",
          "chat.md" in names, f"got {names}")
    check("...and the page was RE-RENDERED, not merely listed",
          marker in chat_path.read_text(encoding="utf-8"),
          "chat.md rode the commit while still holding the stale text")

    # It must not fire on a commit that has nothing to do with the log — the feed
    # rebuild is already conditional and this must be too, or every soak render
    # rewrites a page it did not touch.
    lex_only, _ = fx.pb.publish([sb / "progress" / "lexicon.json"], "smoke", feed=False)
    check("a commit without the log does NOT drag chat.md in",
          "chat.md" not in [Path(q).name for q in lex_only],
          f"got {[Path(q).name for q in lex_only]}")

    # And a lane that still passes it explicitly must not get it twice — a
    # duplicate path is a `git add` of the same file, harmless but a sign the
    # rule has two owners again.
    twice, _ = fx.pb.publish([klog_path, chat_path], "smoke", feed=False)
    check("...and a lane passing it explicitly does not get it twice",
          [Path(q).name for q in twice].count("chat.md") == 1,
          f"got {[Path(q).name for q in twice]}")
