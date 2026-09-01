#!/usr/bin/env python3
"""L5 — WHAT THE LANES SHARE, once.

A lane declares what is DIFFERENT about it. Everything that is the same for its
whole family lives here, and the family is the unit on purpose: the seven lanes
are not one shape and forcing them into one breaks a real invariant. Measured
2026-08-23, they are three:

  write -> render -> publish    render_soak, render_drill, render_rotation,
                                run_studio — Python builds a menu, the writer
                                returns a sheet, Python renders and publishes.
  decide/judge -> maybe render  morning_knock, knock_reply — the model returns a
                                DECISION or a VERDICT, not an artifact, and
                                rendering is conditional on modality.
  pure delivery, no writer      push_queue — zero LLM calls at fire time, by
                                design: composed at add time, rendered at fire
                                time (2026-07-24). It must never be given a
                                writer stage.

So this is a shared tail plus thin per-family runners, never one `run_lane()`.
Anything that flattens the three into one is a regression wearing a refactor's
clothes.

THE SEAMS ARE ARGUMENTS, and that is the whole design (2026-08-24, Andrew).
`commit` and `notify` reach outside the process — git history, and Andrew's
phone — so a caller names them rather than this module reaching for them. Two
reasons, and the second is the load-bearing one:

  1. It states the contract. In a typed language these would be an interface and
     nobody would have to ask what a lane depends on; Python lets any module
     reach into any other, so the codebase never had to decide. Naming them is
     that decision, made once, for the calls that actually have consequences.

  2. It keeps the test suite's stubs working, at zero migration cost. The suite
     intercepts by module attribute — `kr.push_to_phone = Recorder()`, 59 of
     them — and a name looked up inside THIS module would not see a stub
     installed on the lane. Passed in, the lane resolves its own binding at call
     time and the stub intercepts exactly as before. That is hazard H1 answered
     rather than dodged: the old style and this one coexist, so lanes move over
     one at a time and the suite never has to be reshaped first.

Both are keyword-only and neither has a default. A default would be worse than
no parameter: it would silently reach past a lane's stub, and a test that stops
intercepting `commit` writes real git history while reading green.
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import audio_titles
from publish import jsdelivr_url, publish
from state_io import AUDIO_TITLES_PATH, LEARNER_PATH, LEXICON_PATH
from sync_state import mark_soak_delivered, record_exposure


def deliver_rendered(*, mp3: Path, lane: str, delivered: list, claimed: bool,
                     message: str, copy: str, noun: str, extra_paths=(),
                     title, commit, notify) -> bool:
    """The tail every write -> render -> publish lane ran its own copy of:

        exposure -> soak-order stamp -> commit -> notify

    WHAT THIS REPLACES: that block, written out three times in `render_soak`,
    `render_drill` and `render_rotation` — and about to be written a fourth and
    fifth time by the media-ingestion and daily-catch lanes. Each copy had to
    remember the same four things, and the ledger has already had to defend two
    of them once a lane forgot (the feed rebuild's ordering, and quiet hours).

    The lane still owns everything that makes it that lane: which menu it builds,
    what the writer returns, how it renders, and — critically — `delivered`. Only
    the lane can compute that, because "which of the menu items are actually
    AUDIBLE in the finished artifact" is a different question per family, and
    getting it wrong inflates the ledger for words that never played (the
    claim_payload rule, 2026-07-17).

    `claimed` is "did this run consume a standing soak order" — the lane's own
    test, usually `focus or payload`. It is passed rather than inferred because a
    stamp claims a debt is PAID, and a wrong inference there dispatches a second
    identical dose or suppresses one that was owed.

    `title` is the dose's PUBLIC NAME — what the feed and the rating picker call
    it. Keyword-only with NO DEFAULT, for the same reason `commit` and `notify`
    have none: a default here would let a lane forget, and a forgotten name is
    invisible — the dose publishes under its filename and looks exactly like a
    dose that was never named. That is the failure this parameter exists to end
    (2026-09-01: eight soaks shipped as "nothing to do but listen", two of them
    on one day and unrateable). A lane with nothing better to say passes its
    spine or its focus; it does not pass nothing.

    Returns whether the notification actually left the building — False in quiet
    hours, which `push_to_phone` owns and no lane re-implements.
    """
    exposed = record_exposure(delivered)
    stamped = mark_soak_delivered(lane) if claimed else False
    # THE NAME RIDES THE DOSE'S OWN COMMIT (2026-09-01). A soak leaves no script
    # and no caption, so the moment the sheet is written is the only moment its
    # name exists — record it here, at the one tail all three audio lanes pass
    # through, or the feed can only ever call it by its filename. Named in the
    # same commit as the mp3 for the reason `chat.md` is: a derived file follows
    # its source, and `rebuild_rss` reads this map on the very next rebuild,
    # which `publish()` runs three lines below.
    named = audio_titles.record(mp3.stem, title)
    commit(*publish([*extra_paths,
                     AUDIO_TITLES_PATH if named else None,
                     LEXICON_PATH if exposed else None,
                     LEARNER_PATH if stamped else None],
                    message, mp3=mp3))
    print("4. notify…")
    pushed = notify(copy, jsdelivr_url(mp3))
    print(f"done — {noun} on the feed{' and the lock screen' if pushed else ''}.")
    return pushed
