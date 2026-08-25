"""L5 — the delivery lane: the push queue.

Two cases, both about a tick that fires more than it should. The queue is the
one lane that can fire without anybody asking it to, so its failures are
same-tick collisions and concurrent appends rather than wrong content.
"""
import argparse
import importlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import _fixtures as fx
from ._fixtures import (
    check, read_json, REAL_BASE, Recorder, write_json,
)


def s29_one_runner_every_capability(mk, pq, kr, sb: Path):
    print("\n29. One workflow, every capability; the drain renders voice (2026-07-24)")

    # --- the consolidation ------------------------------------------------
    # Three workflows held three different subsets of the secrets, so what Anna
    # could DO depended on which event woke him. Andrew asked for a 20:00 voice
    # greeting for his brother; the reply lane had no TTS secret, so Anna
    # refused — while the knock lane rendered Tamil TTS in the same cloud daily.
    wf_dir = REAL_BASE / ".github" / "workflows"
    for retired in ("morning-knock.yml", "log-knock-response.yml", "push-queue.yml"):
        check(f"{retired} is retired", not (wf_dir / retired).exists())
    anna = (wf_dir / "anna.yml").read_text(encoding="utf-8")
    for trigger in ("schedule:", "repository_dispatch:", "workflow_dispatch:"):
        check(f"anna.yml carries the {trigger.rstrip(':')} trigger", trigger in anna)
    for secret in ("OPENROUTER_API_KEY", "ANNA_PUSH_WEBHOOK_URL", "GCP_SA_KEY"):
        check(f"{secret} is wired once, for every lane", anna.count(secret) >= 1)
    # Job-level env is what makes capability structural rather than remembered:
    # a new step cannot be added without it.
    # Comment lines stripped: this file EXPLAINS the bad context in prose, and a
    # guard that trips on its own documentation is a guard nobody keeps.
    job_env = "\n".join(ln for ln in anna.split("steps:")[0].splitlines()
                        if not ln.lstrip().startswith("#"))
    for var in ("OPENROUTER_API_KEY", "ANNA_PUSH_WEBHOOK_URL", "GOOGLE_APPLICATION_CREDENTIALS"):
        check(f"{var} is job-level, not per-step", var in job_env)
    # The 2026-07-24 outage — `runner` in job-level env, valid YAML that GitHub
    # rejects outright — was guarded here by a hand-rolled context whitelist.
    # RETIRED 2026-07-25 for actionlint in smoke.yml, which knows the whole
    # context-availability table (not just jobs.<id>.env), plus schema, action
    # refs and expression syntax. Verified against the real broken file: it flags
    # line 65 with the exact legal-context list the whitelist hard-coded.
    # What's asserted here now is that the mechanism is still WIRED — this suite
    # runs locally where actionlint may be absent, so the guard it can still keep
    # is "CI has not quietly dropped the linter".
    smoke_yml = (wf_dir / "smoke.yml").read_text(encoding="utf-8")
    check("CI lints the workflow files themselves", "./actionlint" in smoke_yml)
    check("the linter is version-pinned",
          re.search(r"actionlint_\d+\.\d+\.\d+_linux", smoke_yml) is not None)
    check("workflow changes trigger the lint", ".github/workflows/**" in smoke_yml)
    # ffprobe is installed because ubuntu-24.04 has no ffmpeg — but never on the
    # lock-screen lane, which has a standing latency constraint (rendering was kept
    # out of the reply path for the same reason). ~20s of apt before a recast is a
    # regression, and durations freeze at first publication anyway.
    ffstep = anna.split("Install ffprobe", 1)[1].split("- name:", 1)[0]
    check("ffprobe is installed for the lanes that publish new audio", "ffmpeg" in ffstep)
    check("the lock-screen lane skips the install",
          "if: github.event_name != 'repository_dispatch'" in ffstep)
    check("a failed install cannot cost a knock", "continue-on-error: true" in ffstep)
    # ...and a HUNG install cannot either (2026-08-19). `continue-on-error` only
    # ever covered a step that FAILS; this step's failure mode is that it never
    # returns — 57 minutes on 08-17 (recovered, unnoticed), unbounded on 08-18
    # (killed at GitHub's 6h ceiling). Both silent: apt prints nothing under -qq.
    check("a HUNG install cannot cost a knock either",
          re.search(r"^\s*timeout-minutes:\s*\d+\s*$", ffstep, re.M) is not None)
    # The lane is ONE serialised FIFO queue (asserted below), so an unbounded job
    # does not stall itself — it stalls everything behind it. On 08-18 one wedged
    # run held two replies and five scheduled ticks for six hours.
    job_block = anna.split("steps:", 1)[0]
    check("the job itself is bounded, so a hang cannot hold the shared lane",
          re.search(r"^\s*timeout-minutes:\s*\d+\s*$", job_block, re.M) is not None)
    # ONE expression still (the 07-24 collapse of three holds). The interval is
    # back to hourly (2026-07-30): */30 ran for two days and was measured against
    # hourly slice-for-slice — 108.9 vs 108.7 median minutes between runs — so the
    # denser expression bought nothing at twice the runner minutes. GitHub drops
    # proportionally more of a denser schedule. The single-expression property and
    # the "don't re-open without data" conclusion are what this guards.
    check("one cron expression replaces three",
          anna.count("- cron:") == 1)
    check("the tick is hourly (*/30 measured identical, at 2x runner minutes)",
          '- cron: "0 * * * *"' in anna)
    # Drain-first is load-bearing: it logs a reach, and rails_gate counts today's
    # reaches when deciding whether to knock. Drain last would double-push.
    # Search the steps block only — the header comment names these scripts too.
    steps = anna.split("steps:", 1)[1]
    check("the drain runs before the knock",
          steps.index("push_queue.py drain") < steps.index("morning_knock.py"))
    check("the drain runs before the reply judge",
          steps.index("push_queue.py drain") < steps.index("knock_reply.py"))
    check("the drain is unconditional (no `if:` gate on its step)",
          "continue-on-error: true\n        run: python scripts/push_queue.py drain" in anna)

    # --- one serialised lane; nothing cancelled (2026-07-28) ---------------
    # Per-knock_id groups let two reply lanes run in parallel. On 07-28 a reply
    # to a stale notification raced the reply to that morning's knock; both
    # appended to the tail of the feedback_log array, the rebase conflicted, and
    # commit_and_push died — losing a judged exchange, not just a green tick.
    conc = anna.split("concurrency:", 1)[1].split("jobs:", 1)[0]
    conc_keys = "\n".join(ln for ln in conc.splitlines() if not ln.lstrip().startswith("#"))
    check("every lane shares ONE concurrency group",
          re.search(r"^\s*group:\s*anna\s*$", conc_keys, re.M) is not None)
    check("no lane is keyed by the knock it answers", "knock_id" not in conc_keys)
    # The half that makes serialising safe. Without it the group holds ONE
    # pending run and GitHub cancels it when the next reply arrives — which
    # would silently eat the middle of a burst (six dispatches in six minutes,
    # 07-28). `queue: max` holds 100, FIFO.
    check("the group queues instead of cancelling",
          re.search(r"^\s*queue:\s*max\s*$", conc_keys, re.M) is not None)
    # GitHub rejects the whole file if these two combine.
    check("cancel-in-progress stays false (illegal beside queue: max)",
          re.search(r"^\s*cancel-in-progress:\s*false\s*$", conc_keys, re.M) is not None)
    # `queue:` shipped 2026-05-07, after actionlint's newest release — the lint
    # step carries a message-exact suppression so the key can land. It is a lag,
    # not a waiver: if the pin ever moves past the key, drop the flag.
    check("the lint step tolerates the queue key actionlint doesn't know yet",
          "-ignore 'unexpected key \"queue\" for \"concurrency\" section'" in smoke_yml)

    # --- the detector that dropped the 8pm push ---------------------------
    # Built 2026-07-23 to catch exactly this; it needed a clock AND a verb, and
    # "schedule" was not in the verb list — the most literal phrasing possible.
    real_8pm_ask = ("My brother James is arriving at 8pm. Schedule a push and say hello "
                    "(aloud a traditional greeting and a couple key survival items)")
    check("the real 8pm ask is detected", kr.wants_scheduled_push(real_8pm_ask))
    for t in ("queue something for 9pm", "play me a line at 7:30am",
              "wish her good morning tomorrow", "record a greeting for tonight"):
        check(f"clock request detected: {t[:30]}", kr.wants_scheduled_push(t))
    for t in ("naan poren", "said it at dinner", "less of the aunty thing",
              "adhu dhaan, she understood"):
        check(f"plain rep is not a clock request: {t[:30]}", not kr.wants_scheduled_push(t))

    # --- memo_script survives the trip from judge to queue ----------------
    # It used to be dropped on the floor here: maybe_enqueue_schedule was
    # text-only, so even a judge that composed a voice dose lost it.
    qpath = sb / "progress" / "push_queue.json"
    write_json(qpath, [])
    future = (datetime.now(timezone.utc) + timedelta(hours=2))
    out = mk.maybe_enqueue_schedule({"schedule": {
        "at_local": future.astimezone(mk.LOCAL_TZ).strftime("%Y-%m-%dT%H:%M"),
        "body": "James is here — say hello 🎧",
        "memo_script": "வணக்கம் ஜேம்ஸ்! நல்லா இருக்கீங்களா?",
        "move": "welcome james"}})
    check("a scheduled voice dose lands in the queue", out is not None)
    queued = read_json(qpath)
    check("memo_script survives judge → queue",
          len(queued) == 1 and "வணக்கம்" in queued[0].get("memo_script", ""),
          f"got {queued}")
    check("it is marked as needing a render", pq.needs_render(queued[0]))
    check("an already-rendered entry is not re-rendered",
          not pq.needs_render({**queued[0], "audio_url": "https://cdn/x.mp3"}))
    check("a text dose never asks for TTS",
          not pq.needs_render({"body": "text only", "memo_script": ""}))

    # --- the render itself, stubbed: fills audio_url, returns the mp3 -----
    calls = []
    real_render = pq.render_memo

    async def fake_render(script, out_path, voice):   # render_memo is a coroutine
        calls.append((script, voice))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"ID3fake")

    pq.render_memo = fake_render
    try:
        entry = dict(queued[0])
        mp3 = pq.render_entry(entry)
        check("render_entry returns an mp3 to commit", mp3 is not None and mp3.exists())
        check("it speaks the queued script", calls and "வணக்கம்" in calls[0][0])
        check("scheduled voice uses Anna's pinned voice", calls[0][1] == mk.ANNA_VOICE)
        check("audio_url is filled from the rendered path",
              entry.get("audio_url", "").startswith("https://cdn.jsdelivr.net/gh/")
              and entry["audio_url"].endswith(".mp3"))
        check("a rendered entry no longer needs rendering", not pq.needs_render(entry))
    finally:
        pq.render_memo = real_render

    # A TTS failure must not swallow the dose — the text still fires.
    pq.render_memo = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("403 Permission denied"))
    try:
        broken = dict(queued[0])
        check("TTS failure returns no mp3", pq.render_entry(broken) is None)
        check("TTS failure leaves no audio_url", not broken.get("audio_url"))
        check("TTS failure is recorded on the entry", "403" in broken.get("render_failed", ""))
    finally:
        pq.render_memo = real_render

    # --- the whole drain, end to end, with ORDER asserted -----------------
    # The ordering is the subtle part: push_to_phone pre-warms the jsDelivr URL,
    # so the mp3 has to be committed to main BEFORE the notification goes out —
    # otherwise the CDN has nothing to serve and iOS drops the inline player.
    # Committing the mp3 separately (not with the state) is what keeps the
    # retry property: a failed push leaves the entry queued.
    prog = sb / "progress"
    klog_path, q_path = prog / "knock_log.json", prog / "push_queue.json"
    events, saved = [], (fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY)
    real_push, real_commit, real_feed = pq.push_to_phone, pq.commit_and_push, fx.pb.refresh_feed
    pq.push_to_phone = lambda body, url=None, knock_id="", requested=False: (
        events.append(("push", url)))
    pq.commit_and_push = lambda paths, msg: events.append(
        ("commit", "mp3" if any(str(p).endswith(".mp3") for p in paths) else "state",
         any(str(p).endswith("rss.xml") for p in paths)))

    # rebuild_rss titles a dose from knock_log.json, so WHEN the feed is rebuilt
    # decides whether the published title carries the move label. Record what the
    # log looked like at rebuild time — a label-less first write means a later
    # lane retitles a published item, which Apple Podcasts forks into a second
    # episode (2026-07-24 8pm dose, seen twice on one guid).
    rss_stub = sb / "rss.xml"

    def fake_feed():
        entries = read_json(klog_path) or []
        events.append(("feed", any(e.get("queue_id") == "qVOICE" for e in entries)))
        return rss_stub

    fx.pb.refresh_feed = fake_feed
    pq.render_memo = fake_render
    try:
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = 0, 24, 99
        write_json(klog_path, [])
        write_json(q_path, [{**queued[0], "id": "qVOICE", "force": True,
                             "due": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}])
        pq.cmd_drain(argparse.Namespace(dry_run=False, no_commit=False))
        kinds = [e[0] for e in events]
        check("mp3 is committed before the notification fires",
              kinds[:2] == ["commit", "push"] and events[0][1] == "mp3", f"got {events}")
        check("state is committed after the push", kinds[-1] == "commit" and events[-1][1] == "state")
        feeds = [e for e in events if e[0] == "feed"]
        check("the feed is rebuilt exactly once per drain", len(feeds) == 1, f"got {feeds}")
        check("the feed is rebuilt only AFTER the fired dose is in the knock log",
              feeds and feeds[0][1], "rebuilt before the log write — title would publish label-less")
        check("the mp3 commit carries no feed rebuild",
              events[0][2] is False, f"got {events[0]}")
        check("rss.xml rides the state commit", events[-1][2] is True, f"got {events[-1]}")
        check("the notification carries the rendered audio_url",
              (events[1][1] or "").startswith("https://cdn.jsdelivr.net/gh/"), f"got {events[1]}")
        logged = read_json(klog_path)[-1]
        check("the fired voice dose logs as modality audio", logged.get("modality") == "audio")
        check("the log keeps what was HEARD for the reply judge",
              "வணக்கம்" in logged.get("memo_script", ""))
        check("the queue is emptied once fired", read_json(q_path) == [])
    finally:
        fx.pb.WAKING_START_HOUR, fx.pb.WAKING_END_HOUR, pq.MAX_REACHES_PER_DAY = saved
        pq.push_to_phone, pq.commit_and_push, fx.pb.refresh_feed = real_push, real_commit, real_feed
        pq.render_memo = real_render


def s45_concurrent_appends_merge(mk, sb: Path):
    """Two writers appending to one state array must BOTH survive (2026-07-31).

    The 20:56 Anna tick died on `git pull --rebase` with a conflict in
    push_queue.json: Anna had queued a 20:30 collect while another lane pushed a
    queue entry during the LLM step. `check=True` raised, the whole tick's work
    was lost — decision, log row and queued dose — and CI went red. The two
    appends never disagreed; git only saw adjacent edits to one JSON array.

    TEETH IN THE DIRECTION THAT FAILS SILENTLY (Gate 7.2): the dangerous outcome
    is not a crash, it is resolving the conflict the WRONG WAY and dropping the
    other writer's row — during a rebase, stage :2 is upstream and :3 is ours, so
    a plausible-looking implementation loses exactly one entry and looks fine. So
    these assert the EFFECT on the pushed file, per writer, not that it ran.
    """
    print("\n45. Concurrent appends to one state array (both writers survive)")
    import subprocess as sp
    # A FRESH module object, not the shared one: earlier cases replace
    # commit_and_push with a Recorder stub, and the first draft of this case
    # spent a run testing that stub. It "passed" the survives-a-conflict check
    # because a no-op never raises. Gate 7.2 in miniature — the execution
    # assertion was green on a dead function; only the effect assertion caught it.
    # The writer and its rebase net live in publish.py since 2026-08-23.
    spec = importlib.util.spec_from_file_location(
        "pb_live", str(Path(mk.__file__).parent / "publish.py"))
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)
    check("the case holds the REAL writer, not a stub",
          not isinstance(live.commit_and_push, Recorder)
          and callable(getattr(live, "_union_conflict", None)))
    root = sb / "gitlab"
    root.mkdir(exist_ok=True)
    origin, runner, other = root / "origin.git", root / "runner", root / "other"

    def git(cwd, *a, **kw):
        return sp.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", **kw)

    sp.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    sp.run(["git", "clone", "-q", str(origin), str(runner)], check=True)
    for c in (runner,):
        git(c, "config", "user.email", "a@b.c"); git(c, "config", "user.name", "t")
    (runner / "progress").mkdir()
    qp = runner / "progress" / "push_queue.json"
    qp.write_text("[]", encoding="utf-8")
    git(runner, "add", "-A"); git(runner, "commit", "-qm", "base")
    git(runner, "push", "-q", "origin", "HEAD:main")
    sp.run(["git", "clone", "-q", str(origin), str(other)], check=True)
    git(other, "config", "user.email", "a@b.c"); git(other, "config", "user.name", "t")

    # THE OTHER WRITER lands first (a laptop session, or a second lane).
    theirs = {"id": "qTHEIRS", "due": "2026-07-31T22:00:00+00:00", "body": "theirs"}
    (other / "progress" / "push_queue.json").write_text(
        json.dumps([theirs], ensure_ascii=False, indent=2), encoding="utf-8")
    git(other, "add", "-A"); git(other, "commit", "-qm", "other writer")
    git(other, "push", "-q", "origin", "HEAD:main")

    # THE RUNNER, still on the stale base, appends its own and commits+pushes.
    mine = {"id": "qMINE", "due": "2026-07-31T21:00:00+00:00", "body": "mine"}
    qp.write_text(json.dumps([mine], ensure_ascii=False, indent=2), encoding="utf-8")
    live.BASE = runner
    try:
        live.commit_and_push([qp], "Anna: silence")
        crashed = ""
    except Exception as e:
        crashed = f"{type(e).__name__}: {e}"

    check("the tick survives a concurrent append", not crashed, crashed)
    pushed = json.loads(git(origin, "show", "main:progress/push_queue.json").stdout or "[]")
    ids = [e.get("id") for e in pushed]
    check("OUR entry reached main", "qMINE" in ids, str(ids))
    check("...and the OTHER writer's entry was not dropped (rebase :2/:3 inversion)",
          "qTHEIRS" in ids, str(ids))
    check("no row is duplicated", len(ids) == len(set(ids)), str(ids))
    check("the queue stays ordered by due", ids == sorted(ids, key=lambda i:
          {"qMINE": "21", "qTHEIRS": "22"}[i]), str(ids))
    check("nothing is left mid-rebase", not (runner / ".git" / "rebase-merge").exists()
          and not (runner / ".git" / "rebase-apply").exists())

    # A conflict OUTSIDE the unionable set must still be loud, not merged.
    check("only true append-arrays are auto-resolvable",
          set(live.UNIONABLE) == {"progress/push_queue.json", "progress/knock_log.json"},
          f"{sorted(live.UNIONABLE)} — session_log merges same-day rows by rule and "
          "feedback_log has no key; a conflict in either is a real disagreement")
