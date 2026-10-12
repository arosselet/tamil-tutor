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
from language import stem
from lexicon_view import expose
from state_io import (AUDIO_TITLES_PATH, LEARNER_PATH, LEXICON_PATH, load_json,
                      mark_soak_attempted)
from sync_state import mark_soak_delivered



def payload_present(word: str, script: str, lexicon: dict) -> bool:
    """Is a claimed item really in the text?

    VERBATIM FOR CHUNKS, STEM-TOLERANT FOR WORDS (2026-08-18). The rule was a flat
    substring test, which a VERB STEM can essentially never satisfy in natural
    speech: on 2026-08-18 a script said தூக்கறேன் — the word used correctly and
    conjugated — while the sidecar honestly claimed தூக்கு, and the episode was
    rejected. Every verb in the pool had the same problem waiting.

    The lexicon already draws the distinction the rule needs. A `chunk` is a fixed
    phrase the learner drills WHOLE, and both incidents that earned this check were
    chunk mutations (ஒரு மாசம் இருப்போம் inverted, then bent to இருப்போங்க) — so
    chunks keep zero tolerance. A plain word is a lexical item the sentence around
    it inflects, so it is matched on its stem: the item minus one trailing vowel
    sign or pulli.

    The tolerance stays narrow on purpose. தூக்கு → தூக்க admits தூக்கறேன் and
    தூக்குங்க and nothing that is not that verb; வேணும் → வேணும் still refuses
    வேண்டும், which is the literary form the dialect pass exists to remove. A stem
    under 3 characters is no evidence at all (வை → வ), so those fall back to
    verbatim — harmless, because inflection APPENDS to a short stem anyway.

    Moved here from `run_studio` 2026-10-12 so every lane's claim asks it."""
    if word in script:
        return True
    if " " in word or (lexicon.get(word) or {}).get("type") == "chunk":
        return False
    root = stem(word)
    return len(root) >= 3 and root in script


def audible(words, spoken, played_frames=(), lexicon: dict | None = None) -> list[str]:
    """ONE CLAIM RULE FOR EVERY LANE (2026-10-12) — which menu `words` the
    finished artifact actually said. The 07-26 ledger law (only what was AUDIBLE
    is claimed) had four implementations that disagreed: the studio matched on
    stems, the rotation on verbatim substrings, a focused soak on what its sheet
    said — and an unfocused soak and every drill stamped the WHOLE MENU, whatever
    the writer dropped, the empty-field filter cut or the judge seat held.

    `spoken` is the target-language text that reached the TTS, after every gate.
    A word is claimed when `payload_present` finds it there. A `frame:` key is a
    label for a pattern and is never in the audio (the 08-10 machines tape taught
    26 frames and stamped 0), so it is claimed only when the caller can say the
    part of the artifact carrying it PLAYED — `played_frames`. A lane that cannot
    say so under-claims: the frame re-airs sooner, which is the cheap error."""
    lexicon = load_json(LEXICON_PATH) or {} if lexicon is None else lexicon
    blob = " ".join(spoken)
    played = set(played_frames)
    return [w for w in words
            if (w in played if w.startswith("frame:") else payload_present(w, blob, lexicon))]


def deliver_rendered(*, mp3: Path, lane: str, delivered: list, claimed: bool,
                     message: str, copy: str, noun: str, extra_paths=(), owed=(),
                     taught=(), intake=None, title, commit, notify) -> bool:
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
    identical dose or suppresses one that was owed. Since 2026-10-12 it is
    necessary, not sufficient: `owed` (the order's payload words on this run's
    menu) must also be audible, or the order is left STALLED instead.

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
    # `taught` is the subset a TEACHING shape gave — first contact, with its
    # meaning — as against the recall shapes that merely re-air it. It defaults
    # empty because most lanes teach nothing, and a lane that claimed teaching it
    # did not do would re-mine the gate s105 cleared. Pending either way: the
    # render says the beat happened, the tap says it reached him.
    #
    # `intake` (2026-09-13) is the pool words a lane led with that have no row yet
    # — the rotation's quota. One becomes a row HERE, and only if a teaching shape
    # gave it: a planned word the clock cut stays in the pool and leads the next tape.
    intake = intake or {}
    born = {w: {"gloss": intake[w].get("gloss", "")} for w in taught if w in intake}
    exposed = expose(delivered, lane, source=mp3.stem, taught=taught, mint=born)
    # A CLAIM IS PAID ONLY IN WHAT PLAYED (2026-10-12). `owed` is the order's
    # payload words this run put on its menu. The stamp fired on `claimed` alone,
    # so a payload word the judge seat held — or the writer skipped, or the clock
    # cut — retired the order anyway: the repair was booked paid, never re-sent,
    # and nothing anywhere said so. A word owed and not audible now leaves the
    # order STALLED with that word named (the episode lane's 09-11 stamp), so the
    # brief says so and does not re-dispatch into a loop. Frames are excused: no
    # soak or drill can say which line realised one (`audible` under-claims them).
    unpaid = [w for w in owed if not w.startswith("frame:") and w not in delivered]
    if claimed and unpaid:
        mark_soak_attempted(mp3.stem, unpaid)
        print(f"   ⚠ soak order NOT paid — {', '.join(unpaid)} never reached the audio; "
              "left STALLED for the brief")
    stamped = claimed and (bool(unpaid) or mark_soak_delivered(lane))
    # THE NAME RIDES THE DOSE'S OWN COMMIT (2026-09-01). A soak leaves no script
    # and no caption, so the moment the sheet is written is the only moment its
    # name exists — record it here, at the one tail all three audio lanes pass
    # through, or the feed can only ever call it by its filename. Named in the
    # same commit as the mp3 for the reason `chat.md` is: a derived file follows
    # its source, and `rebuild_rss` reads this map on the very next rebuild,
    # which `publish()` runs three lines below.
    # `delivered` RIDES ALONG (2026-09-13). `expose` above spends it and forgets
    # it; keeping it is what lets a tap on this artifact open the Teach Beats it
    # carried. Without it the audio lanes can say a new word and never open one,
    # because only `episodes.json` ever wrote an artifact's words down.
    named = audio_titles.record(mp3.stem, title, delivered)
    commit(*publish([*extra_paths,
                     AUDIO_TITLES_PATH if named else None,
                     LEXICON_PATH if exposed else None,
                     LEARNER_PATH if stamped else None],
                    message, mp3=mp3))
    print("4. notify…")
    pushed = notify(copy, jsdelivr_url(mp3))
    print(f"done — {noun} on the feed{' and the lock screen' if pushed else ''}.")
    return pushed
