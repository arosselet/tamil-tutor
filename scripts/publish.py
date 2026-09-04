#!/usr/bin/env python3
"""L4 — THE DELIVERY TAIL. Everything between "a lane made a dose" and "it is on
Andrew's phone and on main": the commit path with its rebase net, the feed
rebuild, the CDN URL, and the one push chokepoint. It ENFORCES the waking window
at that chokepoint; it stopped OWNING it on 2026-09-04, when the window went to
`rails.py` to sit with the daily cap and min gap that `push_queue` obeys too.

WHAT THIS REPLACES: `morning_knock.py` owning all of it. Nine of the twenty-one
other modules imported that file, and almost none of them wanted the knock —
they wanted this. 424 of its raw lines were not a knock, and the import graph
said so: `render_audio` had to defer `from morning_knock import commit_and_push`
to function scope to dodge a cycle, and `sync_state` — the sole state writer,
which sits BELOW every lane — reached UP to a lane to get its commit.

The law being installed (DECISIONS "Imports point one way, down the stack", 2026-08-23;
the spine-refactor plan it came from was retired 2026-08-26 once fully executed — git
holds it): imports point one way, down the stack, and
a channel never owns an invariant that more than one channel obeys. This file is
that invariant for delivery. A lane hands over what it produced; it does not own
the ordering, the quiet-hours check, or the commit list.

Nothing here is new. Every function below is the one that was already running,
moved intact — the rebase net that union-resolves append-only arrays, the
derived-file re-render, the CDN pre-warm, the per-message notification tag, the
work-network TLS exemption. Their dates and incidents travel with them.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from language import REPO
from render_chat import render_chat
from state_io import KNOCK_LOG_PATH, LOCAL_TZ, RECENT_AUDIO_PATH
# The waking window moved to `rails.py` on 2026-09-04, together with the daily
# cap and min gap it was always half of. It lived here because `push_to_phone`
# below is the chokepoint that enforces it for every lane (2026-07-26) — that
# is still true, and enforcing a rail is a different job from OWNING it. This
# file is the delivery tail; `rails.py` answers whether a reach is permitted at
# all, which two lanes ask long before delivery.
from rails import in_waking_window


KNOCKS_DIR = BASE / "published_audio" / "knocks"   # tracked, jsDelivr-served dir


# Lock-screen render budget. The mandate asks for ≤140; past ~160 iOS cuts the
# body and the dose dies unseen (2026-07-05 feedback). Warn-only — a trimmed
# dose is worse than a logged warning; the fix belongs in the composer.
BODY_BUDGET = 160


def over_budget(text: str, budget: int = BODY_BUDGET) -> bool:
    return len(text or "") > budget


def load_env(path: Path):
    """Minimal .env -> os.environ (don't overwrite anything already set, e.g. CI secrets)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Append-only state arrays whose rows carry a genuinely unique key. Two writers
# appending between one checkout and its push collide TEXTUALLY on rows that do
# not disagree — git sees adjacent edits to one JSON array, not two independent
# appends. rel -> (identity key, sort key). Nothing else is auto-resolvable:
# session_log merges same-day rows by rule (2026-07-31) and feedback_log has no
# key at all, so a conflict in either is a real disagreement and must stay loud.
UNIONABLE = {"progress/push_queue.json": ("id", "due"),
             "progress/knock_log.json": ("timestamp", "timestamp")}

# Files with NO state of their own — each is a pure render of a source of truth
# above. Merging one is meaningless: there is nothing in it to disagree about,
# only two renders of two different logs. Reconciling them was also actively
# harmful — a chat.md conflict is what aborted run 30865736387 on 2026-08-04
# while knock_log.json beside it union-resolved cleanly, losing a judged
# exchange to a file that could have been regenerated in a millisecond.
# Rebuild from the merged source instead of merging the output.
DERIVED = {"progress/chat.md": render_chat}


def _union_conflict(rel: str) -> bool:
    """Resolve ONE conflicted append-only array by keeping every row from both
    sides. Returns False if anything is off-pattern, which keeps the abort loud.

    NOTE THE REBASE INVERSION: replaying our commit onto origin/main, stage :2 is
    UPSTREAM (what they pushed) and :3 is OURS. Getting this backwards silently
    drops the other writer's row, which is the failure this exists to prevent."""
    key, order = UNIONABLE[rel]

    def side(stage: int):
        r = subprocess.run(["git", "show", f":{stage}:{rel}"], cwd=BASE,
                           capture_output=True, text=True, encoding="utf-8")
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None

    theirs, ours = side(2), side(3)
    if not isinstance(theirs, list) or not isinstance(ours, list):
        return False
    merged, seen = [], set()
    for row in theirs + ours:
        if not isinstance(row, dict) or row.get(key) is None:
            return False       # a keyless row cannot be deduped; refuse rather than guess
        if row[key] in seen:
            continue
        seen.add(row[key])
        merged.append(row)
    merged.sort(key=lambda r: str(r.get(order, "")))
    (BASE / rel).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(["git", "add", rel], cwd=BASE, check=True)
    print(f"   ↳ merged {rel}: {len(theirs)} theirs + {len(ours)} ours -> {len(merged)}")
    return True


def _rerender_derived(rel: str) -> bool:
    """Resolve a DERIVED conflict by rebuilding the file from its source of truth,
    discarding both sides of the conflict. Ordering is load-bearing: this must run
    AFTER the union pass, which is what leaves the merged source in the working
    tree for the renderer to read.

    The renderer carries its OWN idea of the repo root (render_chat computes it
    from __file__), so it is only this function's source of truth by coincidence
    of both being the checkout. Assert the coincidence rather than trust it: a
    renderer writing somewhere else would otherwise leave the conflict markers
    in place and `git add` them, resolving the rebase by committing garbage —
    silent, and exactly the direction this file's teeth are supposed to face."""
    written = Path(DERIVED[rel]()).resolve()
    if written != (BASE / rel).resolve():
        print(f"   ⚠ {rel} renderer wrote {written}, not {BASE / rel} — refusing")
        return False
    subprocess.run(["git", "add", rel], cwd=BASE, check=True)
    print(f"   ↳ re-rendered {rel} from its source (not merged)")
    return True


def _rebase_onto_main() -> bool:
    """Land our commit on origin/main, union-resolving append conflicts and
    re-rendering derived ones. False if a conflict is real, with the rebase
    aborted so the tree is left clean.

    RETIRED, 2026-08-04: the `for _ in range(5)` this used to open with. Every
    path inside it returned or broke, so the body could not run twice — it read
    as a five-try retry and was a one-shot. We replay exactly one commit (CI
    checks out clean and commits once), so one pass is also all that is correct."""
    if subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"],
                      cwd=BASE).returncode == 0:
        return True
    stopped = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"],
                             cwd=BASE, capture_output=True, text=True, encoding="utf-8").stdout.split()
    unresolvable = [f for f in stopped if f not in UNIONABLE and f not in DERIVED]
    # Sources of truth first, then the files rendered FROM that merged result.
    if (stopped and not unresolvable
            and all(_union_conflict(f) for f in stopped if f in UNIONABLE)
            and all(_rerender_derived(f) for f in stopped if f in DERIVED)):
        subprocess.run(["git", "rebase", "--continue"], cwd=BASE,
                       env={**os.environ, "GIT_EDITOR": "true"}, check=True)
        return True
    print(f"   ⚠ unresolvable rebase conflict: {unresolvable or stopped or 'none reported'}")
    subprocess.run(["git", "rebase", "--abort"], cwd=BASE)
    return False


def commit_and_push(paths: list[Path], msg: str):
    rels = [str(p.relative_to(BASE)) for p in paths]
    subprocess.run(["git", "add", *rels], cwd=BASE, check=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=BASE, check=True)
    # main has three writers (knock CI, ack CI, the laptop) and this checkout goes
    # minutes stale during the LLM/TTS steps — land our commit on top of theirs.
    # A conflict here used to raise and lose the whole tick's work, decision
    # included (2026-07-31): two lanes appending to push_queue.json in one window
    # is routine, not a disagreement, so it is merged rather than surrendered.
    if not _rebase_onto_main():
        raise RuntimeError("rebase onto origin/main needs a human — tree left clean")
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE, check=True)


def refresh_feed() -> Path | None:
    """All audio lands on the podcast feed (2026-07-05): rebuild rss.xml so a
    dismissed audio memo stays findable. Feed polish must never kill the knock."""
    try:
        subprocess.run([sys.executable, str(BASE / "scripts" / "rebuild_rss.py")],
                       cwd=BASE, check=True)
        return BASE / "rss.xml"
    except Exception as e:
        print(f"   ⚠ rss rebuild failed ({e}) — continuing without feed update")
        return None


def jsdelivr_url(mp3: Path) -> str:
    rel = mp3.relative_to(BASE).as_posix()
    return f"https://cdn.jsdelivr.net/gh/{REPO}@main/{rel}"  # unique daily filename => always fresh


def push_to_phone(body: str, audio_url: str | None, knock_id: str = "",
                  requested: bool = False) -> bool:
    """Push a notification. audio_url is optional — a text/challenge/grace dose has none.
    knock_id = the knock's log-entry timestamp; it rides the notification's action_data
    and comes back with taps/replies so the judge grades the knock Andrew actually
    answered. Notifications stack (unique tag per MESSAGE, 2026-08-19; per knock from
    2026-07-11 until two replies to one knock collided) — last-fired correlation is
    only the fallback for id-less events.

    QUIET HOURS ARE ENFORCED HERE, at the one chokepoint every lane shares
    (2026-07-26). They used to be enforced per-lane: `rails_gate` for knocks, a
    hand-rolled hour compare in `run_studio`, `in_waking_window` in the queue —
    and NOTHING in `render_drill` or `render_soak`, which is how a drill reached
    the phone at 23:42. Three copies and two gaps is the same shape as the
    ordering-law drift found the same day; the fix is one owner, not a fourth copy.

    `requested=True` is the deliberate exemption: a reply Andrew's own tap asked
    for is not an interruption, and the rails exist to stop UNrequested reaches.
    Returns True if it pushed, False if quiet hours held it back."""
    if not requested and not in_waking_window():
        local = datetime.now(LOCAL_TZ)
        print(f"   phone: quiet hours ({local:%H:%M} {local.tzname()}) — not pushed. "
              f"The artifact is on the feed for the morning.")
        return False
    if audio_url:
        # Pre-warm the CDN: iOS fetches the attachment the instant the notification
        # lands, and a never-before-requested jsDelivr path can take seconds on its
        # first pull from GitHub — long enough for iOS to drop the inline player.
        try:
            with urllib.request.urlopen(audio_url, timeout=60) as r:
                r.read()
        except OSError as e:
            print(f"   ⚠ CDN pre-warm failed ({e}) — pushing anyway")
    webhook = os.environ["ANNA_PUSH_WEBHOOK_URL"]
    # `tag` is the notification's IDENTITY and nothing else; iOS replaces a
    # notification that arrives bearing a tag already on the lock screen. It used
    # to be derived HA-side from knock_id alone ("anna-{{ knock_id }}", unique per
    # KNOCK, 2026-07-11) — which made one field do two jobs, identity and judging
    # correlation, and they do not want the same key. Correlation must be STABLE
    # per knock so the judge grades the right entry; identity must be UNIQUE per
    # message or a notification eats its predecessor.
    #
    # On 2026-08-18 they collided for real. Two Shortcut replies (which by design
    # send no knock_id — see docs/home_assistant_knock_buttons.md §8.3) both fell
    # back to last_fired_knock, both resolved knock 2026-08-18T10:21, both pushed
    # tag "anna-2026-08-18T10:21" 43 seconds apart, and the second silently
    # replaced the first. The answer to "inge poringe what does it mean?" was
    # generated, judged, committed and delivered HTTP 200 — and Andrew never saw
    # it. Every instrument read green; the only trace was in chat.md.
    #
    # So the tag is minted HERE, per push, and knock_id keeps correlation alone in
    # action_data. The knock prefix stays for legibility in HA's log.
    payload = {"title": "Anna", "text_content": body, "knock_id": knock_id,
               "tag": f"anna-{knock_id or 'knock'}-{time.time_ns()}"}
    if audio_url:
        payload["audio_url"] = audio_url
    req = urllib.request.Request(webhook, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    # Delivery is the one network hop we don't control end-to-end: a transient
    # DNS blip on the runner (2026-07-14, first occurrence) killed an otherwise
    # perfect run at the last step. Retry absorbs blips; the final failure still
    # raises so a genuinely unreachable webhook stays a red run, not a silent drop.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as r:
                print(f"   HA push -> HTTP {r.status}")
            return True
        except OSError as e:  # URLError, gaierror, timeouts
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                # The work network's FortiGate substitutes its own CA on this hop
                # (2026-07-28, Andrew: accepted, "not worth engineering around").
                # Retry cannot heal it and it must not fail the run — on 07-28 a
                # fully successful local render exited non-zero here, read as
                # total failure, and got re-run into a duplicate soak tape. The
                # dose is on the feed; only the lock-screen ping is lost.
                print("   phone: work-network TLS inspection strips this hop "
                      "(known, accepted 2026-07-28) — not pushed; the dose is on the feed.")
                return False
            if attempt == 2:
                raise
            wait = 5 * (attempt + 1)
            print(f"   ⚠ push attempt {attempt + 1} failed ({e}) — retrying in {wait}s")
            time.sleep(wait)


# ── THE TAIL: one owner for the ordering ────────────────────────────────────

def publish(state_paths: list, message: str, *, mp3=None,
            feed: bool | None = None) -> tuple[list, str]:
    """Assemble the commit for a finished dose: rebuild the feed if this run made
    audio, drop the falsy entries a lane's conditionals leave behind, and return
    `(paths, message)` in the ONE order that is correct.

    The lane logs and records exposure first — only it knows what it wrote and
    what went out the door — then hands the result here and passes the answer
    straight to `commit_and_push`, then pushes. Two lines, no ordering decisions.

    WHAT THIS REPLACES: twenty-six hand-built `commit_paths` lists, each one an
    opportunity to get the order wrong and each one having to remember the same
    invariants. The ledger has already had to defend two of them:

      FEED AFTER THE LOG, never before. `rebuild_rss` titles each pushed dose
      from `knock_log.json`, so rebuilding while the entry does not yet exist
      publishes a label-less title — and Apple Podcasts treats a published title
      as part of an item's identity. The 2026-07-24 8pm dose forked into TWO
      episodes on one stable guid. The knock and reply lanes ordered it right;
      the drain did not, because its legitimate two-commit split swept the
      rebuild along with the mp3.

      THE MP3 GOES ON MAIN BEFORE THE NOTIFICATION. `push_to_phone` pre-warms the
      jsDelivr URL and jsDelivr can only serve a path already on `main`, so the
      audio is inserted at the FRONT of the commit rather than appended, and the
      lane's push comes after the commit this returns.

    It also retires the two lanes that shelled out to `rebuild_rss.py` directly
    with `check=True` — a third way of rebuilding the feed, and the only one
    where a feed hiccup killed a render whose mp3 had already been made.
    `refresh_feed` warns and continues: feed polish must never cost a dose.

    WHY THE COMMIT AND THE PUSH STAY AT THE LANE (hazard H1, and it is a choice,
    not an oversight): both are reached as `from publish import commit_and_push`,
    so the names are bound on the LANE's module object, which is where the smoke
    suite's sixty stubs intercept. Pull either call inside this function and all
    sixty silently stop intercepting — a test would hit real git and Andrew's
    real phone — and sixty per-lane stubs would collapse onto one shared address
    in a suite whose stubs have no teardown. That instrument is what makes this
    refactor provably behaviour-preserving; it does not get disarmed to make a
    signature tidier. Reshaping it is Q2's job, and the seam moves after, never
    before.

    `feed` defaults to "this run produced audio", which is what `mp3` means.
    push_queue passes `feed=True` with `mp3=None` on purpose: its mp3s went out
    in an earlier commit to preserve the drain's retry property (a push that
    fails leaves the entry queued), but the rebuild still belongs here, after the
    knock-log write. That split is a property of a BATCH lane and stays with it;
    the ordering it used to carry alongside does not.
    """
    if feed is None:
        feed = mp3 is not None
    paths = [q for q in state_paths if q]
    if mp3 is not None:
        paths.insert(0, mp3)
    if feed:
        rss = refresh_feed()
        if rss:
            # BOTH, always together. `rebuild_rss` rewrites the rating picker's
            # list beside the feed it derives from, and a rewrite that never
            # leaves the runner is indistinguishable from success: the file on
            # disk is correct, the phone fetches `main`, and the row is missing
            # exactly as before (2026-09-01). The pair is the deliverable.
            paths.extend([rss, RECENT_AUDIO_PATH])
    # A DERIVED FILE FOLLOWS ITS SOURCE (2026-08-24). `chat.md` holds no state of
    # its own — `render_chat` builds it from `knock_log.json` and reads nothing
    # else — so a commit carrying the log without a fresh render publishes a page
    # that is already stale, and it stays stale until some later lane happens to
    # rebuild it. That is exactly what the "Log tap" step did before 2026-08-04:
    # a tap's "👍 acked" sat unrendered for hours.
    #
    # Four lanes obeyed this by hand — morning_knock, both knock_reply lanes, the
    # queue drain, and sync_state's knock-response — each calling render_chat()
    # while building its own list. Four copies of one rule is the shape this
    # refactor exists to retire, and `DERIVED` above already names the same
    # relationship for the rebase net. One owner now, and a lane that writes the
    # log cannot forget the page.
    if any(Path(q).name == KNOCK_LOG_PATH.name for q in paths) \
            and not any(Path(q).name == "chat.md" for q in paths):
        paths.append(render_chat())
    return paths, message
