#!/usr/bin/env python3
"""
State management for the Tamil learning system.

Word-state lives in ONE place: progress/lexicon.json — a word-keyed map where each
record carries its static half (gloss, phonetics, type, register, direction) and its
evidence half (both axes, reps, dates). The evidence half is a VIEW: since 2026-09-10
every observation is an event in progress/observations.json and `lexicon_view`
folds it onto the row. This script records what Anna observed at close; it never
sets a rung by hand.

  progress/lexicon.json     → word-state (this file's domain)
  progress/learner.json     → continuity: running story (debrief), soak order, status (thin, LLM-facing)
  progress/episodes.json    → episodes (audio artifacts; no listen counter — 2026-08-27)
  progress/session_log.json → momentum log, one entry per session-DAY (repeat
      update calls in one close merge into that day's entry, never mint a row)

Usage:
    # After a session: record production + recognition movement
    python scripts/sync_state.py update --produced-cold poren --stuck-word வை

    # Show current state (what Anna reads at session start)
    python scripts/sync_state.py status

Canonical-at-write: produced/recognized words are resolved phonetic->script against
the lexicon. A produced word that resolves to no record is WARNED and SKIPPED rather
than silently poisoning state — production presupposes a recognition record.
"""

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from language import is_tamil
from slips import (DOSE_CHANNELS, append_slips, canon_tag, cmd_slips,
                   parse_slip_args, record_slip_commission, record_slip_test,
                   slip_patterns)
from publish import commit_and_push, publish
from rebuild_rss import feed_items
from suggest_targets import reconcile_focus
import lexicon_view
import observations
from state_io import (BASE, DEFAULT_TZ, EPISODES_PATH, FEEDBACK_LOG_PATH,
                      canon_payload,
                      KNOCK_LOG_PATH, LEARNER_PATH, LEXICON_PATH,
                      SESSION_LOG_PATH, SLIP_LOG_PATH,
                      build_phonetic_index,
                      load_json, local_today, resolve, save_json)

# Windows consoles default to cp1252, which can't print Tamil — the status digest
# crashed mid-print on a fresh laptop (2026-07-15) and a dead digest invites the
# agent to improvise state. Harmless everywhere else.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# Recognition ladder. A word the learner *recognizes* is comfortable or solid;
# struggled means shaky; unseen means no record. The floor counts cold production
# among words that are at least comfortable.
RECOGNITION_LEVELS = ["struggled", "comfortable", "solid"]
RECOGNIZED = {"comfortable", "solid"}




# `mark_exposed` / `record_exposure` left for `lexicon_view.expose` (2026-09-10):
# a delivery is an `exposed` event like any other observation, and the counter
# it used to bump is now folded from the log.


def mark_soak_delivered(channel: str) -> bool:
    """The lane that RENDERED the standing order stamps it consumed.

    The episode lane clears itself for free: registration writes the payload
    into episodes.json and creates any missing lexicon row, so "newest episode
    carries it" is answerable. The soak and drill lanes have neither — and
    inferring delivery from `last_surfaced` fails on exactly the words that
    matter, because `split_payload` deliberately passes Tamil-script payload
    items that are legitimately PRE-lexicon (a brand-new word), while
    `mark_exposed` can only stamp rows that already exist. One such word
    (நிறைஞ்சிடுச்சு, 2026-07-27) held an order at NOT YET PRODUCED through a
    successful render — the M72/M73/M74 re-dispatch loop, one layer in.

    So the lane declares it instead of the checker guessing. Same ledger law as
    exposure (2026-07-26): delivery is declared by the seam that ships the dose.

    Returns False when there is no order to stamp; callers add LEARNER_PATH to
    their commit when this returns True."""
    learner = load_json(LEARNER_PATH)
    if not learner or not (learner.get("soak_order") or {}):
        return False
    learner["soak_order"]["delivered"] = {
        "channel": channel, "at": local_today().isoformat()}
    save_json(LEARNER_PATH, learner)
    print(f"   Soak order marked delivered by the {channel} lane")
    return True


def is_pattern(rec: dict) -> bool:
    """A pattern/lemma record is a generative structure (e.g. the present/future
    toggle), tracked on the same axes as a word but metered separately."""
    return rec.get("type") == "pattern"


def compute_floor(lexicon: dict) -> dict:
    """The viability floor: of the WORDS recognized (comfortable+solid),
    how many fire cold? This is the one honest word-level progress meter.
    Patterns are excluded — they get their own Engines meter. Ear-only
    (direction=catch) items are excluded too: they clear on recognition and
    are never forced to fire, so counting them makes the meter lie."""
    recognized = [w for w, r in lexicon.items()
                  if not is_pattern(r) and r.get("direction") != "catch"
                  and r.get("recognition") in RECOGNIZED]
    cleared = [w for w in recognized if lexicon[w].get("production") == "cold"]
    total = len(recognized)
    pct = (len(cleared) / total * 100) if total else 0.0
    return {"cleared": len(cleared), "total": total, "pct": pct}


def compute_engines(lexicon: dict) -> dict:
    """The engine meter: of the tracked generative patterns, how many fire cold —
    i.e. the learner can produce a NOVEL instance unaided? Reported separately
    from the word-level viability floor so neither muddies the other. Ear-only
    (direction=catch) patterns are excluded — they clear on recognition (the
    deck's catch side meters them), so they'd pin this meter below 100% forever."""
    patterns = [w for w, r in lexicon.items()
                if is_pattern(r) and r.get("direction") != "catch"]
    online = [w for w in patterns if lexicon[w].get("production") == "cold"]
    total = len(patterns)
    pct = (len(online) / total * 100) if total else 0.0
    return {"online": len(online), "total": total, "pct": pct}


def is_heard(rec: dict) -> bool:
    """Solid on the ear AND something actually observed it — the evidence rule.

    `recognition` is a CLAIM. Until 2026-08-27 nothing recorded what backed one,
    so a level asserted in a seed commit and a level won on a caught eavesdrop
    were the same value in the same field. Measured that day across all 220
    commits that ever touched the ledger: 74 rows claimed recognized, and 69 of
    them had never earned a single upgrade in the ledger's life — born at that
    level and never assessed since. `heard_on` is the missing half: present only
    where a recognition observation actually happened (Anna's live judgment, or
    the eavesdrop judge), so an assertion is now DERIVED — a level with no date —
    rather than stored as a flag that would drift.

    DELIBERATELY NOT APPLIED TO `compute_floor` (2026-08-27). The floor asks "of
    the words we think he knows, how many can he say" — a soft claim is fine in
    that denominator, and gating it on evidence would collapse it from 49/58 to
    about 3/5 overnight, which measures nothing. The ear meter reads evidence;
    the floor keeps reading the claim. That asymmetry is the design, not an
    oversight — do not "fix" it into consistency.
    """
    return rec.get("recognition") == "solid" and bool(rec.get("heard_on"))


def compute_machines(lexicon: dict) -> dict:
    """The machines meter — of the tracked patterns, how many he actually HEARS.

    THE ONE OWNER OF THIS RULE (2026-08-27). `session_brief` counted it inline
    with its own `recognition == "solid"` loop while `compute_status` counted it
    here; two copies of an invariant is how one of them silently stops matching
    the other, which the spine law (2026-08-23) already bans one lane over.

    `tested` IS THE DENOMINATOR'S HONESTY (2026-08-31, Andrew: *"this seems
    totally backward, how can I say things I don't recognize? recognition should
    easily beat production."*). He was right, and `s60` — the case that shipped
    this meter — had already written the failure down in its own Gate 7.2 note:
    "it prints a plausible fraction that never moves, which is indistinguishable
    from Andrew not improving, and it is the headline, so nobody would question
    it." It then guarded the two ways it thought of (a shrinking denominator, a
    frozen numerator) and not the way it actually happened: on 2026-08-31, 22 of
    the 26 machines carried NO `heard_on` at all. The fraction was frozen because
    nothing had ever ASKED those rows, not because he failed them — of the four
    ever tested, three came back heard. A denominator full of untested rows
    reports IGNORANCE AS FAILURE, and it had read 3/26 as the PRIMARY STEER since
    2026-08-16 while the ear ran 3-of-4 on the only evidence that existed.

    The same defect, sign flipped, is already settled one lane over: "honest
    meters must show both" (2026-07-25) added `deck_coverage`'s worked/total
    beside cold/total because "the headline read a won sprint while most of the
    deck had never been touched", and `s32` guards it. This is that law reaching
    the ear lane, which it never did.

    `tested` counts EVIDENCE, not success — `heard_on` is stamped by a promotion
    and by a demotion alike (a recorded miss is a test), so `tested` is always
    >= `heard` and the gap between them is the ledger's honest unknown. `pct`
    stays keyed to `total`: the goal is 26 machines heard, not 4, so the headline
    can never flatter itself by dividing by whatever it happened to test.
    """
    pats = [r for r in lexicon.values() if is_pattern(r)]
    heard = [r for r in pats if is_heard(r)]
    tested = [r for r in pats if r.get("heard_on")]
    total = len(pats)
    return {"heard": len(heard), "tested": len(tested), "total": total,
            "pct": (len(heard) / total * 100) if total else 0.0}


def compute_ear(lexicon: dict) -> dict:
    """The ear meter: of the rows tagged `direction: "catch"` — ear-only, where
    the win is comprehension and forcing production is the mistake — how many
    have reached solid recognition?

    All that survives of `compute_deck` (retired 2026-08-18). That function
    metered a CONTAINER: the 83 rows tagged `deck: "trip"`, cleared/total/pct on
    the fire side, plus a survival-tier headline joined from the curriculum file.
    The container's reason expired at touchdown; the fire side it metered is the
    viability floor, which `compute_floor` already owns and always did. The ear
    is the one axis nothing else counts, and `direction` was always its
    discriminator — never the deck tag — so its population is unchanged."""
    catch = [r for r in lexicon.values() if r.get("direction") == "catch"]
    solid = [r for r in catch if is_heard(r)]
    return {"caught": len(solid), "total": len(catch),
            "untouched": sum(1 for r in catch if not r.get("last_surfaced"))}


# --- Episode helpers (progress/episodes.json — a flat {id: episode} map) ------

def compute_status() -> str:
    """The status line IS the scoreboard (post the 2026-06-30 listens pivot).
    Never a chore line — episodes are self-contained doses; nothing is ever
    'under-listened'.

    THE HEADLINE IS THE EAR (2026-08-16, Andrew: "we stop counting what comes out
    of your mouth and start counting what you can hear"). Every meter that ever
    led this line measured PRODUCTION — deck cold, floor cold, engines cold — and
    the lexicon says he produces 20 of 26 machines cold while hearing 3. The tails
    carry a Tamil sentence's skeleton, so ten machines he can build himself still
    go past him at speed. That gap is what "two words in a fast sentence does
    almost nothing" actually was.

    ONE ERA, NOT TWO (2026-08-18, the deck retirement). This line carried a
    countdown against `TRIP_DATE` and a required burn rate. The countdown had an
    entry and no exit — `s54` encoded pre-trip and during-trip and there was no
    third era, so after he flew home it would have read "in country, day 32", then
    33, forever — and a winnable countdown is exactly the motivational device the
    08-17 no-numbers rule banned. Deleted rather than given a third era: the
    deadline is what expired, and a required pace with no deadline is not a
    number, it is a guess."""
    lexicon = load_json(LEXICON_PATH) or {}
    mach = compute_machines(lexicon)
    ears = (f"Machines heard {mach['heard']} · ear-tested "
            f"{mach['tested']}/{mach['total']}")
    floor = compute_floor(lexicon)
    return f"{ears} · viability floor {floor['cleared']}/{floor['total']} fire cold ({floor['pct']:.0f}%)"


def cold_fires_recent(days: int = 7) -> int:
    """COLD fires in the trailing `days`-day window, across chat sessions and phone
    replies — the pace side of the burn rate. Live from the logs, never stored.
    Replies count per word via reply_fired_cold (the judge grades each word on its
    own, post revealed-cap); entries from before per-word verdicts (2026-07-03)
    fall back to the flat verdict-gated count."""
    cutoff = (local_today() - timedelta(days=days - 1)).isoformat()
    n = 0
    for s in load_json(SESSION_LOG_PATH) or []:
        if s.get("date", "") >= cutoff:
            n += len(s.get("cold", []))
    for k in load_json(KNOCK_LOG_PATH) or []:
        if k.get("reply_at", "") < cutoff:
            continue
        if "reply_fired_cold" in k:
            n += len(k["reply_fired_cold"])
        elif k.get("reply_verdict") == "cold":
            n += len(k.get("reply_fired", []))
    return n


def trailing_pace(window: int = 7) -> str:
    """The honest pace line: cold/day actually happening. Python states the math;
    Anna narrates what it means.

    Was `burn_rate(pending, days_left)` — cold/day NEEDED to clear a pending
    count by a deadline, beside the trailing rate. Past the deadline there is no
    required pace, and the `max(days_left, 1)` clamp silently froze the ask at
    its final day's value and reported it forever (2026-08-04, guarded there).
    Retired whole 2026-08-18 with the deadline it was computed against: a
    required pace needs a terminus, and with none it WAS only this line already."""
    return f"trailing {window}-day pace {cold_fires_recent(window) / window:.1f}/day"


def fires_today() -> int:
    """Words fired (cold or hinted) TODAY, across chat sessions and phone replies —
    the fast per-day reward counter appended to the scoreboard. Computed live from
    the logs, never stored (a stored counter is a meter that can lie)."""
    today = local_today().isoformat()
    n = 0
    for s in load_json(SESSION_LOG_PATH) or []:
        if s.get("date") == today:
            n += len(s.get("cold", [])) + len(s.get("hinted", []))
    for k in load_json(KNOCK_LOG_PATH) or []:
        # reply_fired is only ever non-empty for a scored (cold/hinted) reply
        if k.get("reply_at", "").startswith(today):
            n += len(k.get("reply_fired", []))
    return n


# Keys this schema retired. Merge-write carries an unknown key through by
# design, so a retired one has to be NAMED to be swept -- the old rebuild-from-
# whitelist dropped them for free, and that free sweep is the one thing
# merge-write gives up. `streak` was a stored counter that lies the moment a day
# is skipped; `slips_closed` is the bare-tag list `slip_closes` replaced.
# `recent_missions` joined them 2026-08-27: it named a population (numbered
# Missions) that was never the one the picker needed, and `recent_audio` reads
# the feed instead. Named here or merge-write carries the stale list forever.
RETIRED_LEARNER_KEYS = ("streak", "slips_closed", "recent_missions", "recent_audio")

# The two books this function does NOT own: `record_slip_test` and
# `record_slip_commission` persist them straight to LEARNER_PATH, so by the time
# we are called the on-disk copy is fresher than any `learner` dict a caller
# read before those writers ran. Disk wins unconditionally -- which is what
# retires the re-read loop that used to sit in `cmd_update` patching the lost
# update this very function created (slip_closes, silently gone for a day,
# 2026-07-30 -> 07-31).
FOREIGN_BOOKS = ("slip_closes", "slip_commissions")


def write_thin_learner(learner: dict):
    """MERGE-WRITE (2026-08-23, Decision D). Read the file, overlay the keys the
    caller owns, recompute the two derived ones, leave everything else alone.

    It used to REBUILD learner.json from a hand-maintained key list, so a key
    absent from that list was DELETED, not left stale -- and the failure was
    invisible, because a wiped value is indistinguishable from one never set. It
    ate state three times: `slip_closes` (lost for a day), `slip_commissions` on
    its first run, and `timezone` / `quiet_until` survived only because someone
    remembered to add them. The guard was prose -- "any future learner-side book
    must be added here too" -- a comment standing in for a mechanism.

    Merge-write inverts the default: an unknown key survives. No schema change;
    the file this writes today is byte-identical to the file it wrote before."""
    thin = load_json(LEARNER_PATH) or {}
    thin.update({k: v for k, v in learner.items() if k not in FOREIGN_BOOKS})
    for key in RETIRED_LEARNER_KEYS:
        thin.pop(key, None)
    # Shape floor, for a fresh or hand-truncated file. `timezone` feeds every
    # clock-facing rule (state_io.LOCAL_TZ), and `quiet_until` is the transit bit
    # the rails read (2026-08-10, Andrew) -- both must exist on a first write.
    for key, default in (("learner", "Andrew"), ("timezone", DEFAULT_TZ),
                         ("quiet_until", ""), ("last_debrief", ""),
                         ("next_engine", "")):
        thin.setdefault(key, default)
    for key in ("soak_order",) + FOREIGN_BOOKS:
        thin.setdefault(key, {})
    thin.setdefault("focus_cohort", [])
    # The two derived views -- recomputed on every write, never stored input.
    # (The <=FOCUS_SIZE drill cohort above is the opposite: stored membership,
    # not an emergent sort, so a counting bug cannot move a seat -- 2026-07-26.)
    thin["status"] = compute_status()
    # The rating picker's list is NOT written here any more (2026-09-01). It is
    # derived from `rss.xml` and was being rewritten on the SESSION clock while
    # its source moved on the PUBLISH clock, so every dose published between two
    # state writes was missing from the picker — the 09-01 soak, minutes after it
    # landed. Its writer is `rebuild_rss.write_recent_audio`, called by the same
    # function that writes the feed. One clock, and it is the source's.
    save_json(LEARNER_PATH, thin)
    print(f"  Updated learner.json ({LEARNER_PATH.relative_to(BASE)})")


# --- Commands ----------------------------------------------------------------

def cmd_update(args):
    lexicon = load_json(LEXICON_PATH)
    learner = load_json(LEARNER_PATH)
    if lexicon is None or learner is None:
        print("Error: lexicon.json or learner.json missing. See BOOTSTRAP.md.")
        sys.exit(1)

    phon_index = build_phonetic_index(lexicon)
    today = local_today().isoformat()
    applied = {"cold": [], "hinted": [], "demoted": [], "recognized": []}  # for the session log

    # ── THE COMMISSION NOTICE (2026-08-01 as a gate; advisory since 2026-08-20)
    # The original complaint stands and is worth keeping: NEVER COMMISSIONED was
    # advisory and got walked past for mechanical reasons — venum-for-kudunga sat
    # 24 days between first slip and first dose while the ticket warned daily
    # ("the flag needs teeth", feedback 07-31, second occurrence).
    #
    # The answer to that was a hard refusal, and it was never tested, because
    # `uncommissioned` could not be true (the dose_channel bug, slips.py). When
    # the detection was fixed on 2026-08-20 the refusal became real for the first
    # time and Andrew ruled it out the same day: commissioning nothing is a
    # first-class outcome, so Python surfaces the debt and never demands payment.
    # The 24-day gap was a VISIBILITY failure, and visibility is what this block
    # now buys. Still runs BEFORE any write so the close stays re-runnable —
    # touch() counts reps, and a partially-applied close must never happen.
    slip_rows = parse_slip_args(getattr(args, "slip", None) or [])
    declared = {canon_tag(t) for t in getattr(args, "slip_commissioned", None) or []}
    landed_now = {canon_tag(r.rpartition(":")[0])
                  for r in getattr(args, "slip_tested", None) or []
                  if r.strip().lower().endswith(":landed")}
    # A declared tag only counts as covered if an order will actually stand —
    # a --slip-commissioned with no order is the typo record_slip_commission
    # rejects later, and it must not sweet-talk the gate first.
    order_stands = bool(args.soak_channel or args.soak_payload
                        or (learner.get("soak_order") or {}).get("channel"))
    sim = [{"tag": canon_tag(r["tag"]), "date": today} for r in slip_rows]
    owed = [p for p in slip_patterns(log=(load_json(SLIP_LOG_PATH) or []) + sim)
            if p["uncommissioned"] and p["tag"] not in landed_now
            and not (p["tag"] in declared and order_stands)]
    # ADVISORY, NEVER A REFUSAL (Andrew, 2026-08-20). This block used to
    # sys.exit(2) on an uncommissioned live pattern. It never once fired —
    # `uncommissioned` was disarmed from 2026-07-31 by the dose_channel bug
    # (see slips.py) — and when the detection was repaired the question became
    # live for the first time: should Python REQUIRE a dose?
    #
    # No. **Commissioning nothing is a first-class outcome.** A dose is earned
    # when a failure pattern is genuinely recurring or Anna has something real
    # to teach — not because a counter reached two. A gate that refuses the
    # close converts a judgement into a toll, and the close is the one command
    # that must never become something to dread: it is where the debrief, the
    # ledger and the campaign all land. Surfacing the debt is the whole job;
    # deciding it is Anna's.
    reason = getattr(args, "no_commission", None)
    if owed:
        print("  ⚠ live slip pattern(s) with no dose ever commissioned: "
              + ", ".join(f"{p['tag']} ({p['count']}× over {p['span_days']}d)"
                          for p in owed))
        print("     Commission one here if it has earned a dose:  --soak-payload … "
              "--soak-channel soak|episode|drill --slip-commissioned <tag>")
        if reason:
            print(f"     Closing without one, on the record: {reason}")

    # Every observation this close makes, folded onto the rows in one write below.
    events: list[dict] = []

    def ev(key, kind, **kw):
        return {"word": key, "channel": "session", "kind": kind,
                "source": f"session:{today}", **kw}

    def mint(word, phon, gloss=""):
        """A row's STATIC half. The evidence half is the fold's — a fresh row
        carries the defaults until an event speaks (2026-09-10)."""
        lexicon[word] = {
            "gloss": gloss, "phonetic": [phon] if phon else [], "recognition": "struggled",
            "production": "none", "seen_in": [], "last_surfaced": None,
        }

    def split_phonetic(spec):
        """Peel the sounds-like form off a mint spec: 'WORD|phonetic'.

        A record born WITHOUT one is unreachable from the surface Anna actually
        writes in. The constitution's split makes phonetics his input; `resolve()`
        is exact-match against this list; and every mint site used to write `[]`
        under a "backfill later" note. Later never came. By 2026-08-14, 96 of 313
        word records carried no phonetic — 88 of them `production: none`, i.e.
        very nearly the floor-gap pool itself — and FIVE OF THE TWELVE items on
        that day's own focus set could not be logged phonetically. The ticket was
        naming targets the logger would then refuse; the session lost a real
        hinted rep to it (`ukkarunga`, then `ukkaarunga`, both bounced).

        The fix is a deletion, not a detector: the phonetic is in Anna's mouth at
        first contact and nowhere else afterwards, and these paths were throwing
        it away while a sibling command (`add-word --phonetic`) took it properly.
        Take it here. Andrew's call, 2026-08-14: refuse at the mint AND ratchet
        the debt in smoke (s59) — the render lane cannot be blocked, so the
        ratchet is what covers it. Existing records are grandfathered; no backfill.
        """
        head, _, phon = spec.partition("|")
        return head.strip(), phon.strip()

    def recognized(spec):
        """Anna watched him recognize it — ONE observation, ONE rung (2026-09-10).
        `--mastered-word` used to write `solid` outright: a claim of level, not
        two observations. Both old flags now mean this."""
        word, phon = split_phonetic(spec)
        key = resolve(word, lexicon, phon_index)
        if key is None:
            if not is_tamil(word) or not phon:
                print(f"  ! '{word}' can't be created — a new record needs Tamil script AND its sounds-like form: '{word}|phonetic'. Skipped.")
                return
            mint(word, phon)
            key = word
            print(f"  + New word '{word}' (phonetic '{phon}'; gloss empty — fill in later)")
        events.append(ev(key, "tested", axis="recognition", result="right",
                         note="recognized in session"))
        applied["recognized"].append(key)
        print(f"  Recognized: {key} — one rung up on the ear")

    def demote_recognition(word):
        key = resolve(word, lexicon, phon_index)
        if key is None:
            print(f"  ! '{word}' not in lexicon — nothing to demote. Skipped.")
            return
        # A MISS IS EVIDENCE TOO — a tested failure must never read as untested.
        events.append(ev(key, "tested", axis="recognition", result="wrong",
                         note="failed cold recall"))
        applied["demoted"].append(key)
        print(f"  Recognition '{key}' — one rung down (tested, missed)")

    def set_production(word, level):
        key = resolve(word, lexicon, phon_index)
        if key is None:
            print(f"  ! Produced '{word}' but no record resolves — add recognition first (script). Skipped.")
            return
        events.append(ev(key, "tested", axis="production",
                         result=observations.FIRE_RESULT[level], note=f"fired {level}"))
        applied[level].append(key)
        print(f"  Produced {level.upper()}: {key}")

    def teach_word(spec):
        """A word taught in-session enters the lexicon at `struggled` recognition.

        The live teaching surface had NO write path (2026-07-28): `--mastered`/
        `--comfortable` overstate what one generous first contact proves,
        `--stuck-word` and `--mark-seen` both refuse an absent key, and
        `seed-deck` is a deck-authoring flow. So the pakkam/paakkalaam deep-dive
        taught பக்கத்துல, ஆச்சு and இருக்கேன் and recorded NONE of them — the next
        ticket could not know they were taught, and a queued soak order carried a
        word the lexicon had never heard of. `struggled` is the honest level: it
        is what a first contact buys. Production stays unset until he fires it,
        so this can never inflate the floor. Accepts `WORD` or `WORD=gloss`.
        """
        spec, phon = split_phonetic(spec)
        word, _, gloss = spec.partition("=")
        word, gloss = word.strip(), gloss.strip()
        if not is_tamil(word):
            print(f"  ! '{word}' is phonetic — teach it in Tamil script so the key "
                  f"can be canonical. Skipped.")
            return
        key = resolve(word, lexicon, phon_index)
        if key is not None:
            if gloss and not lexicon[key].get("gloss"):
                lexicon[key]["gloss"] = gloss
            # The phonetic backfills on the same terms as the gloss (2026-08-19).
            # Only the gloss did, which made --teach the one command able to name
            # an existing row and yet decline to — so every row minted by
            # render_audio from an episode's tags sidecar (no gloss, no phonetic)
            # was permanently unreachable from chat with no sanctioned repair.
            # Found by publishing M87/M90: three fresh rows, three unfillable
            # holes, s61's ratchet red. `not ...` never overwrites a vetted
            # phonetic; it only fills an empty list. Like the new-word branch
            # below it leaves phon_index alone — the index is rebuilt per run,
            # and no lane resolves a phonetic it minted in the same invocation.
            if phon and not lexicon[key].get("phonetic"):
                lexicon[key]["phonetic"] = [phon]
            # Printed, not assumed: a state write nobody can see is the silent
            # no-op this repo keeps paying for. STILL EMPTY names the hole.
            events.append(ev(key, "taught", note="re-taught; row already existed"))
            print(f"  Taught (already known): {key} — refreshed, recognition left "
                  f"at {lexicon[key].get('recognition', 'struggled')}, "
                  f"phonetic {lexicon[key].get('phonetic') or 'STILL EMPTY'}")
            return
        if not phon:
            print(f"  ! '{word}' is new — teach it with its sounds-like form, '{word}=gloss|phonetic', or it can never be logged from chat. Skipped.")
            return
        mint(word, phon, gloss)
        events.append(ev(word, "taught", note="first contact — row created at struggled"))
        print(f"  + Taught '{word}' → recognition struggled"
              f"{', gloss: ' + gloss if gloss else ' (gloss empty — fill in later)'}")

    # Taught this session — must run BEFORE the axes below, so a word taught and
    # then fired in the same close resolves instead of being refused.
    for spec in args.teach:
        teach_word(spec)

    # Recognition movement
    for w in args.recognized:
        recognized(w)
    for w in args.stuck_word:
        demote_recognition(w)

    # Production axis
    for w in args.produced_cold:
        set_production(w, "cold")
    for w in args.produced_hinted:
        set_production(w, "hinted")

    # `--listened` retired 2026-09-10: a listen is evidenced by the rating lane
    # (`rate-episode` exposes the mission's words) — self-report had no other reader.

    # Next engine focus — the frame to unlock next, surfaced in the ticket and digest.
    if args.next_engine:
        learner["next_engine"] = args.next_engine
        print(f"  Next engine set: {args.next_engine}")

    # The transit bit. A DATE and not a boolean on purpose: the failure mode of a
    # bare bit is forgetting to unset it, which kills the knock channel silently
    # for as long as nobody notices — worst exactly when travelling. A date lapses
    # on its own; clearing it early is `--quiet-until ""`.
    # getattr, not args.quiet_until: eight cases in the suite hand-build their own
    # argparse.Namespace from a copied defaults dict, so a new optional flag read
    # directly breaks all eight. This also keeps the block self-contained — delete
    # it and the feature is gone, which is what it was commissioned to be.
    if getattr(args, "quiet_until", None) is not None:
        # The CLEAR path has to be the robust one — it is the command he runs
        # jet-lagged, wanting to carry on, and a shell that eats a bare "" would
        # otherwise leave the channel dead with the fix looking like it worked.
        if args.quiet_until.strip().strip('"\'').lower() in ("", "off", "none", "clear"):
            args.quiet_until = ""
        if args.quiet_until:
            date.fromisoformat(args.quiet_until)   # raises on a typo, before it is stored
            learner["quiet_until"] = args.quiet_until
            print(f"  QUIET UNTIL {args.quiet_until} — knocks held; the rails skip "
                  f"before the LLM, so nothing logs and no silence reads as a fade.")
        else:
            learner["quiet_until"] = ""
            print("  Quiet window cleared — knocks resume on the next tick.")

    # `--mark-seen` retired 2026-09-10 — it wrote `last_surfaced`, which stopped
    # closing the teach gate on 2026-08-31; `--teach` on an existing row is the
    # taught event it was reaching for.

    # Soak order — the intentional payload for the NEXT audio dose (what Anna
    # wants soaked), read by the Director and by the soak sheet. Overwrites;
    # fail-forward, no history.
    #
    # It used to REBUILD the dict from three keys, which silently ate every
    # other key on the next write. That is why the 2026-07-18 narrated_drama
    # decision ("commissioned by Anna via soak order, form: …, scale: …") never
    # had an implementation: nothing wrote a form, nothing read one, and a
    # hand-placed one died at the next close. The order is a BRIEFING now —
    # unnamed keys survive, and it carries `channel` (which lane renders it)
    # and `focus` (what to permute over the payload) beside the words.
    if (args.soak_payload or args.soak_seed or args.soak_focus
            or args.soak_channel or args.soak_form):
        order = dict(learner.get("soak_order") or {})
        # Per-field, not rebuild-from-args. The old code recomputed `payload`
        # on every write, so once the order also carried a focus and a channel,
        # setting one of those ALONE would have silently wiped the words — the
        # same class of bug as the clobber above, introduced by fixing it.
        if args.soak_payload:
            order["payload"] = [resolve(w, lexicon, phon_index) or w
                                for w in canon_payload(args.soak_payload)]
        order.setdefault("payload", [])
        order["scene_seed"] = args.soak_seed or order.get("scene_seed", "")
        if args.soak_focus is not None:
            order["focus"] = args.soak_focus
        if args.soak_channel is not None:
            order["channel"] = args.soak_channel
        # FORM IS A CHOICE PER ORDER, NEVER A STANDING PREFERENCE (2026-08-31).
        # `channel` above may stick: every read site defaults it (`or "episode"`),
        # so an inherited lane is legible. An inherited FORM is not — absent means
        # "let the scene-spec gate roll", which is the whole anti-sameness
        # mechanism, and a form that survives its order silently disables it.
        #
        # MEASURED: `narrated_drama` was set on 2026-08-05 and rode 26 days and six
        # orders across three lanes (08-14 classic, then 08-18 episode, 08-18 drill,
        # 08-25 soak, 08-26 drill, 08-31 soak). On the episode lane
        # `commissioned_form()` pinned it — `"form": commissioned or pick_divergent(...)`
        # short-circuits the roll — so the one form that exists BECAUSE it must be
        # chosen ("commissioned, never spec-rotated", 2026-07-18) re-chose itself
        # indefinitely. On soak and drill it was inert: nothing outside the episode
        # lane reads `form`, so the state recorded an intent no lane would honour.
        # Every instrument read green; the write path even printed "· form: …".
        #
        # The asymmetry decides it. Clearing wrongly costs one rolled form — the
        # correct default. Sticking wrongly costs the gate, silently, forever.
        if args.soak_form is not None:
            order["form"] = args.soak_form
        else:
            order.pop("form", None)
        # A re-set order is a NEW order: drop any prior lane's delivery stamp, or
        # a close on the same day a dose already shipped would read as already
        # produced and never render (date compare alone can't see it — `from` and
        # `delivered.at` are both today). Any change to the brief invalidates it.
        order.pop("delivered", None)
        order["from"] = today
        learner["soak_order"] = order
        extra = "".join(f" · {k}: {order[k]}"
                        for k in ("channel", "form", "focus") if order.get(k))
        print(f"  Soak order set: {', '.join(order['payload']) or '(seed only)'}{extra}")

    if args.debrief:
        learner["last_debrief"] = args.debrief

    # The chat lane's half of the slip ledger. `last_debrief` above is prose and
    # is OVERWRITTEN every close by design (it is the running story); a mistake
    # recorded only there survives exactly as long as Anna keeps retyping it.
    # This is the accumulating half — same ledger the knock judge writes to, so
    # a slip made at the table and a slip made on the phone are one history.
    # (parsed once, up at the gate — the gate and the writer must see one list)
    if slip_rows:
        channel = (learner.get("soak_order") or {}).get("channel", "")
        written = append_slips(slip_rows, lane="chat", modality="session",
                               dose_channel=channel)
        for row in written:
            print(f"  Slip logged: {row['tag']} — “{row['said']}” → “{row['want']}”")
        for p in slip_patterns():
            if p["pattern"] and p["live"] and p["tag"] in {r["tag"] for r in written}:
                print(f"  ⚠ {p['tag']} is now {p['count']}× over {p['span_days']}d "
                      f"— it is a pattern, not a one-off.")

    # The other half of the loop: a slip he was deliberately TESTED on. Capture
    # says what broke; this says whether it healed — and without it a slip can
    # only ever age out on the clock, which cannot distinguish "he learned it"
    # from "nothing asked him".
    for tag, outcome, msg in record_slip_test(getattr(args, "slip_tested", None) or []):
        mark = {"landed": "✓", "missed": "✗", "bad": "!"}[outcome]
        print(f"  {mark} slip {tag}: {msg}")

    # Which debt does the order just set actually PAY? Declared, never inferred:
    # a payload word and a slip tag are different vocabularies, and the slips
    # that most need a dose (1pl-past-om, past-tense) hang off no single word.
    # Reads the order from `learner` as mutated above, so setting the order and
    # naming its debt in ONE close works — which is the only ergonomic worth
    # having here (2026-07-31, Andrew's option A).
    for tag, msg in record_slip_commission(getattr(args, "slip_commissioned", None) or [],
                                           learner.get("soak_order") or {}):
        mark = "✓" if msg.startswith("commissioned") else "!"
        print(f"  {mark} slip {tag}: {msg}")

    # No streak bookkeeping — recency comes from the session log, and a stored
    # streak is a meter that lies the moment a day is skipped (Enjoyment Clause).
    learner.pop("streak", None)

    # Focus cohort — stored membership, reconciled only here and at the judge
    # seam: leave on graduation, enter on seat-open (2026-07-26).
    # THE ONE EVIDENCE WRITE (2026-09-10): record, then fold onto the rows.
    # Before the cohort reconciles, because graduation reads `production`.
    if events:
        lexicon_view.observe(events, lexicon=lexicon)
    old_cohort = learner.get("focus_cohort", [])
    learner["focus_cohort"] = reconcile_focus(lexicon, old_cohort)
    left = sorted(set(old_cohort) - set(learner["focus_cohort"]))
    entered = sorted(set(learner["focus_cohort"]) - set(old_cohort))
    if left or entered:
        print(f"  Focus cohort: -{left or '[]'} +{entered or '[]'}"
              f" ({len(learner['focus_cohort'])} seats held)")

    save_json(LEXICON_PATH, lexicon)
    write_thin_learner(learner)

    floor = compute_floor(lexicon)
    engines = compute_engines(lexicon)

    # Momentum log — ONE entry per session-day that did something.
    #
    # It used to append unconditionally, so every extra `update` call in a close
    # forged a session: repairing a bad key, or setting the soak order in a
    # second command, each minted a row. 38 rows for 26 real days by 2026-07-31
    # — 12 duplicated dates, the counter ~46% high, and the last-5 view in
    # show_status padded with near-empty rows. Worse, cold_fires_recent() and
    # fires_today() SUM word lists across entries, so a word logged twice in one
    # close inflated the trailing pace the burn rate is computed from.
    # Merging restores the documented contract instead of adding a guard on top.
    if any(applied.values()) or args.debrief:
        log = load_json(SESSION_LOG_PATH) or []
        entry = log[-1] if log and log[-1].get("date") == today else None
        if entry is None:
            entry = {"date": today, "cold": [], "hinted": [], "demoted": [], "note": ""}
            log.append(entry)
        # Union, not concatenate — the same word re-logged is one fire, not two.
        for field, values in (("cold", applied["cold"]), ("hinted", applied["hinted"]),
                              ("demoted", applied["demoted"])):
            have = entry.setdefault(field, [])
            have.extend(v for v in values if v not in have)
        # Percentages are a snapshot: the latest call is the truest.
        entry["floor_pct"] = round(floor["pct"], 1)
        entry["engines_pct"] = round(engines["pct"], 1)
        # The debrief is rewritten whole and cumulatively by Anna, so a later
        # one supersedes rather than appends. An update that carries no debrief
        # must never blank the one already written.
        if args.debrief:
            entry["note"] = args.debrief
        save_json(SESSION_LOG_PATH, log)
        print(f"  Logged session ({len(log)} total)")

    print(f"\nViability floor: {floor['cleared']}/{floor['total']} fire cold ({floor['pct']:.0f}%)")
    if engines["total"]:
        print(f"Engines online: {engines['online']}/{engines['total']} ({engines['pct']:.0f}%)")
    ear = compute_ear(lexicon)
    if ear["total"]:
        print(f"Ear-only: {ear['caught']}/{ear['total']} solid on recognition")
    print(f"Fired today: {fires_today()}")
    print("State updated.")


def cmd_add_pattern(args):
    """Seed a generative pattern/lemma record into the lexicon. Patterns are
    tracked on the same axes as words but metered separately (Engines). Movement
    afterward reuses the normal flags, e.g. `update --produced-cold '<key>'` the
    day the learner generates a NOVEL instance of the pattern unaided."""
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:
        print("Error: lexicon.json missing. See BOOTSTRAP.md.")
        sys.exit(1)
    if args.key in lexicon:
        print(f"  ! '{args.key}' already exists — not overwriting. Move its axes with `update`.")
        return
    today = local_today().isoformat()
    lexicon[args.key] = {
        "type": "pattern",
        "gloss": args.gloss,
        "phonetic": [],
        "recognition": "struggled",
        "production": "none",
        "seen_in": [],
        "last_surfaced": today,
    }
    save_json(LEXICON_PATH, lexicon)
    print(f"  + Pattern '{args.key}' seeded — {args.gloss} (struggled until something tests it)")
    print(f"    Log a cold novel instance later with:  update --produced-cold '{args.key}'")


def cmd_add_word(args):
    """Seed a word/chunk record with its gloss and phonetics in one shot — the
    proper birth of a new lexicon entry (`update --recognized` creates gloss-less
    stubs; soak orders don't create records at all). Without a record, a word
    can never be resolved, scored, or surface on a ticket."""
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:
        print("Error: lexicon.json missing. See BOOTSTRAP.md.")
        sys.exit(1)
    if not is_tamil(args.key):
        print(f"  ! '{args.key}' isn't Tamil script — records must be canonical script.")
        sys.exit(1)
    if args.key in lexicon:
        rec = lexicon[args.key]
        if args.gloss and not rec.get("gloss"):
            rec["gloss"] = args.gloss
        for phon in args.phonetic:
            if phon not in rec.setdefault("phonetic", []):
                rec["phonetic"].append(phon)
        save_json(LEXICON_PATH, lexicon)
        print(f"  '{args.key}' already exists — merged gloss/phonetics, learning state untouched.")
        return
    lexicon[args.key] = {
        "gloss": args.gloss,
        "phonetic": list(args.phonetic),
        "recognition": "struggled",
        "production": "none",
        "seen_in": [],
        "last_surfaced": local_today().isoformat(),
    }
    save_json(LEXICON_PATH, lexicon)
    print(f"  + '{args.key}' — {args.gloss} (phonetic {list(args.phonetic)}; struggled until something tests it)")


def cmd_reseed_focus(args):
    """Re-derive the stored focus cohort from the pool's CURRENT order.

    The cohort is stored membership on purpose: a word enters when a seat opens
    and leaves only on graduation, so it is a fact readable in a file and immune
    to counting bugs (Andrew, 2026-07-26). Held seats stand regardless of what
    any counter says — that rule exists to stop churn on a word mid-fight, and it
    is right.

    But a counter is not the only thing that can change. When the ORDERING
    changes, a cohort seeded under the old one holds seats the new one would
    never have given it, and no amount of waiting fixes that — `reconcile_focus`
    only fills seats as they open. That is exactly what the deck retirement did
    (2026-08-18): the tier bar moved onto the rows, and all twelve seats were
    held by unregistered delight-tier words seeded before it existed, so four
    survival items could not enter a pool that now ranks them first.

    Deliberately a COMMAND and not automatic. Rebuilding membership is the churn
    the stored cohort exists to prevent, so it happens when someone decides it
    should, never as a side effect of a status read. `--dry-run` prints the diff
    and writes nothing."""
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:
        print("Error: lexicon.json missing. See BOOTSTRAP.md.")
        sys.exit(1)
    from suggest_targets import FOCUS_SIZE, floor_gap_targets
    learner = load_json(LEARNER_PATH) or {}
    old = learner.get("focus_cohort", [])
    # A cohort of one unmatchable key: no seat is held, so every seat is filled
    # from the pool's own head — which is what "re-derive from the current
    # order" means. An EMPTY cohort would take the day-zero seed branch instead
    # (most-repped first), which is a different question with a different answer.
    focus, _bg = floor_gap_targets(lexicon, local_today(), FOCUS_SIZE,
                                   cohort=["\x00 no seat is held"])
    new = sorted(c["word"] for c in focus)
    left, entered = sorted(set(old) - set(new)), sorted(set(new) - set(old))
    print(f"  Focus cohort: {len(old)} -> {len(new)} seats")
    for w in left:
        print(f"    - out: {w}")
    for w in entered:
        print(f"    + in:  {w}  [{lexicon.get(w, {}).get('register') or 'unranked'}]")
    if args.dry_run:
        print("  (dry run — nothing written)")
        return
    learner["focus_cohort"] = new
    save_json(LEARNER_PATH, learner)
    print("  learner.json updated.")


def cmd_seed_deck(args):
    """Idempotently load a curated set (e.g. curriculum/trip_deck.json) into the
    lexicon. The file is CONTENT (Anna drafts it, the Oracle vets it); this is the
    MECHANISM that lands it — the same LLM-writes / Python-owns-state split as
    word_pool.json.

    Each entry: {"word", "gloss", "phonetic": [...], "type": "chunk"|"frame",
    "register"?, "direction"?: "fire"|"catch", "pairs_with"?}. A "frame" is stored
    as a lexicon `pattern` (an Engine); a "chunk" is word-like (counts in the
    viability floor). "catch" marks ear-only items; "pairs_with" names the chunk
    that answers it and must resolve inside the same file, or the seed refuses.
    "register" is the ORDERING (`suggest_targets.REGISTER_TIERS`).

    Static fields only. A `recognition` in the file is ignored (2026-09-10): a
    curated file cannot observe, and a claim does not vote. The `deck` tag and
    the un-tag sweep retired with it — nothing read the tag.
    """
    path = Path(args.file)
    if not path.is_absolute():
        path = BASE / path
    entries = load_json(path)
    if entries is None:
        print(f"Error: deck file not found: {path}")
        sys.exit(1)
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None:
        print("Error: lexicon.json missing. See BOOTSTRAP.md.")
        sys.exit(1)
    # `pairs_with` is the ONE relation the schema carries: a catch item names the
    # chunk Andrew must say back to it (hear X → say Y). It lives on the catch
    # side because that is the direction of the drill, and it must resolve inside
    # the same file — an unresolvable pair is a SPLIT pair, which is exactly the
    # failure it exists to prevent (2026-07-26: the maami's "eat more" kept its
    # deck slot while its refusal was dropped, and nothing could notice). A split
    # pair refuses the whole seed BEFORE any write: fix the file, re-run.
    # The schema key is "word" (2026-08-28) — see suggest_targets.cluster_gaps.
    in_file = {e.get("word") for e in entries}
    split = [(e.get("word"), e.get("pairs_with")) for e in entries
             if e.get("pairs_with") and e["pairs_with"] not in in_file]
    if split:
        for word, pair in split:
            print(f"  ✗ '{word}' pairs_with '{pair}', which is not in this deck — split pair.")
        print("  Error: seed refused, nothing written. A pair must resolve inside the file.")
        sys.exit(1)
    created = updated = 0
    for e in entries:
        word = e.get("word")
        if not word:
            print(f"  ! deck entry missing 'word' — skipped: {e}")
            continue
        pair = e.get("pairs_with")
        lex_type = "pattern" if e.get("type") == "frame" else e.get("type", "chunk")
        # Chunks/words must be canonical Tamil script; frames use the `frame:...`
        # key convention (like add-pattern), so they're exempt from the script check.
        if lex_type != "pattern" and not is_tamil(word):
            print(f"  ! '{word}' isn't Tamil script — chunks must be canonical script. Skipped.")
            continue
        if word in lexicon:
            rec = lexicon[word]
            rec["direction"] = e.get("direction", "fire")
            if e.get("register"):
                rec["register"] = e["register"]
            rec.setdefault("type", lex_type)
            if pair:
                rec["pairs_with"] = pair
            else:
                rec.pop("pairs_with", None)  # the file is the source of truth
            if e.get("gloss"):
                rec["gloss"] = e["gloss"]  # deck file is the curated content source — its gloss wins
            for phon in e.get("phonetic", []):
                if phon not in rec.setdefault("phonetic", []):
                    rec["phonetic"].append(phon)
            updated += 1
        else:
            lexicon[word] = {
                "type": lex_type,
                "gloss": e.get("gloss", ""),
                "phonetic": e.get("phonetic", []),
                "recognition": "struggled",
                "production": "none",
                "seen_in": [],
                "last_surfaced": None,
                "direction": e.get("direction", "fire"),
                **({"register": e["register"]} if e.get("register") else {}),
                **({"pairs_with": pair} if pair else {}),
            }
            created += 1
    save_json(LEXICON_PATH, lexicon)
    ear = compute_ear(lexicon)
    print(f"  Seeded {path.name}: +{created} new, {updated} updated.")
    floor = compute_floor(lexicon)
    print(f"  Floor now: {floor['cleared']}/{floor['total']} fire cold ({floor['pct']:.0f}%)"
          + (f" · ear-only {ear['caught']}/{ear['total']} solid" if ear["total"] else ""))




# The knock tap (Home Assistant's actionable notification): "got it" — the knock
# landed, the nudge gate backs off, no learning write. A second tap on the same
# knock is a no-op. `listened` retired 2026-09-10: zero taps in 197 knocks, and a
# listen is now evidenced by the rating lane.
KNOCK_RESPONSES = {"ack"}


def cmd_knock_response(args):
    """Record Andrew's tap response against its knock. Called by anna.yml when HA
    fires the event. Idempotent: a duplicate tap is a no-op."""
    from datetime import datetime
    response = args.response.strip().lower()
    if response not in KNOCK_RESPONSES:
        print(f"  Unknown knock response '{response}' (expected one of {sorted(KNOCK_RESPONSES)}). Skipping.")
        return
    log = load_json(KNOCK_LOG_PATH) or []
    # Only FIRED reaches can be tapped; silence entries (acted=False) carry no
    # notification, so skip them and mark the most recent actual knock.
    fired = [k for k in log if k.get("acted", True)]
    if not fired:
        print("No fired knocks in knock_log.json to respond to.")
        sys.exit(1)
    # Notifications stack (2026-07-11): a tap carries its knock's timestamp as
    # knock_id, so an old notification acks the right entry. No id → last fired.
    kid = (getattr(args, "knock_id", "") or "").strip()
    last = next((k for k in reversed(fired) if k.get("timestamp") == kid), None) if kid else None
    if last is None:
        if kid:
            print(f"  ⚠ knock_id {kid!r} not in the log — marking the most recent knock")
        last = fired[-1]
    if last.get("response") is not None:
        print(f"  Knock ({last['date']}) already '{last['response']}'; '{response}' adds nothing. Skipping.")
        return

    last["response"] = response
    last["response_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    save_json(KNOCK_LOG_PATH, log)
    print(f"  Knock {last['date']} marked '{response}'")

    if getattr(args, "commit", False):
        # Replaces the hand-rolled stage/commit/pull/push that lived in the "Log
        # tap" step of anna.yml (2026-08-04). That copy did a bare
        # `git pull --rebase` with NO union resolution and no derived re-render —
        # the same race the reply lane had a net for, in the one lane that had
        # none. It also never re-rendered chat.md, so a tap's "👍 acked" sat
        # unrendered until some later knock happened to rebuild the file.
        # Routed through `publish` so the derived-file rule has ONE owner: this
        # lane used to call render_chat() itself, which is the copy the comment
        # above is about. No audio here, so no feed rebuild.
        commit_and_push(*publish([KNOCK_LOG_PATH], f"Knock response: {response}", feed=False))


# Leading integer off a picker line. The iOS rating shortcut sends whole rows —
# "90 — Mission tier2_mission90" and "4 ★★★★" — because Shortcuts is a bad place
# to parse and a worse place to test one. Parsing lives here, where a smoke case
# can hold it (2026-08-27).
def _leading_int(raw: str) -> int | None:
    m = re.match(r"\s*(\d+)", raw or "")
    return int(m.group(1)) if m else None


# COUNTING STARS WAS TRIED AND REVERTED, same day (2026-08-27, Andrew: "I think you
# were too generous in widening the parser"). The first live rating arrived as
# '⭐️⭐️⭐️' and refused (run 33057942609), so the parser learned to count ★☆⭐ as a
# fallback. That was a worse bug than the one it fixed: ☆ counted, so '★★★☆☆' —
# three filled of five, the ordinary way to DRAW a 3 — scored 5. Not a refusal, a
# confidently wrong number filed into the ledger that steers the Diagnosis pass.
#
# A guessed glyph set is unbounded (🌟 ✨ scored 0 and refused, so coverage felt
# real while being partial), and the row labels are Andrew's to write. One input
# contract: put the digit in front. Anything else refuses, loudly, which is the
# whole reason this parse sits in Python instead of on the phone.


def cmd_rate_episode(args):
    """Record an audio rating from the phone into the feedback ledger.

    RIDES THE EXISTING BOOK. A rating is one more dated note in
    feedback_log.json — the ledger the Diagnosis pass already reads — not a new
    file and not a schema change. It replaces the `listens` counter retired
    earlier today, whose problem was that it recorded ATTENDANCE and could not
    be wrong out loud.

    Every bad input is LOUD. An unparseable line, an unknown mission or a star
    count off the 1-5 scale exits non-zero rather than filing a zero: this lane
    is unattended, and a rating silently recorded as 0/5 would steer the
    diagnosis pass while looking exactly like a rating that never arrived."""
    stars = _leading_int(args.stars)
    if stars is None or not 1 <= stars <= 5:
        print(f"  ! Stars must be 1-5, as a LEADING DIGIT; got {args.stars!r}. "
              f"Star glyphs alone are not counted — the picker row wants '3 ★★★'.")
        sys.exit(1)
    # Resolve against the FEED, by the exact title the picker offered — which is
    # the title his podcast app shows, so the row he taps and the item he heard
    # are the same string by construction. An unmatched title refuses rather than
    # guessing: a rating filed against the wrong episode is worse than none.
    wanted = (args.episode or "").strip()
    item = next((d for d in feed_items() if d["title"] == wanted), None)
    if item is None:
        print(f"  ! {wanted!r} is not in the feed — nothing to rate. "
              f"Pick a row from progress/recent_audio.txt.")
        sys.exit(1)
    note = (f"[audio rating] [{item['format']}] {item['title']} — {stars}/5 "
            f"on wanting to keep listening.")
    log = load_json(FEEDBACK_LOG_PATH) or []
    log.append({"date": local_today().isoformat(), "note": note})
    save_json(FEEDBACK_LOG_PATH, log)
    print(f"  Logged feedback ({len(log)} total): {note}")
    # A RATING IS A LISTEN (2026-09-10): the one proof the ear block happened,
    # and for a numbered mission the words it carried are exposed on that
    # evidence — `--listened` and the `listened` tap, which nothing ever sent,
    # retired in its favour. `ear_block_days` reads these rows.
    ep = (load_json(EPISODES_PATH) or {}).get(str(item["id"]), {})
    exposed = lexicon_view.expose(ep.get("words", []), "episode", source=f"rating:{item['id']}")
    if getattr(args, "commit", False):
        commit_and_push(*publish([FEEDBACK_LOG_PATH, LEXICON_PATH if exposed else None],
                                 f"Audio rating: {item['id']} {stars}/5", feed=False))


def cmd_check(args):
    """THE RECEPTIVE CHECK (2026-09-10) — the one instrument that tests the ear
    at volume, and the only thing that can re-base the comprehension goal's
    checkpoints. Replaces `docs/ledger_audit_2026-09-10.md`, whose 30-row draw
    is exactly this command's first run.

    `--draw N` prints a deterministic sample of rows no watched channel has ever
    tested, seeded by the month, so it cannot be quietly redrawn to a friendlier
    set and Anna can print it at the top of the session and use it in the flow.
    Recognition only: Anna uses the item in an ordinary sentence, Andrew says what
    it means — knows / doesn't / partial, and partial is real data.

    `--heard WORD:right|wrong|partial` records each answer as a `check` event, a
    watched channel, so the rung follows. This tests the LEDGER, not Andrew:
    a low score is a fact about the instrument, and it is engineering data he
    never hears as a number (persona.md)."""
    import hashlib
    import random
    lexicon = load_json(LEXICON_PATH) or {}
    phon_index = build_phonetic_index(lexicon)
    today = local_today().isoformat()
    if args.draw:
        never = sorted(k for k, v in lexicon.items()
                       if not v.get("heard_on") and v.get("production", "none") in ("none", None))
        seed = f"check-{today[:7]}"
        random.seed(seed)
        pick = sorted(random.sample(never, min(args.draw, len(never))))
        digest = hashlib.sha256("\n".join(pick).encode()).hexdigest()[:16]
        print(f"RECEPTIVE CHECK — {len(pick)} of {len(never)} never-tested rows, seed {seed}, "
              f"sample {digest}. Recognition only; one item at a time, in the flow; never show the list.")
        for k in pick:
            print(f"  {k}  [{', '.join(lexicon[k].get('phonetic') or []) or 'no phonetic'}] — {lexicon[k].get('gloss', '')}")
        print("Record with:  sync_state.py check --heard WORD:right --heard WORD:wrong --heard WORD:partial")
        return
    events, bad = [], []
    for spec in args.heard:
        word, _, res = spec.rpartition(":")
        key = resolve(word.strip(), lexicon, phon_index)
        if key is None or res not in ("right", "wrong", "partial"):
            bad.append(spec)
            continue
        events.append(dict(word=key, channel="check", kind="tested", axis="recognition",
                           result=res, source=f"check:{today}", note="receptive check"))
    for spec in bad:
        print(f"  ! {spec!r} — expected WORD:right|wrong|partial with a word the lexicon knows. Skipped.")
    if events:
        lexicon_view.observe(events, lexicon=lexicon)
        save_json(LEXICON_PATH, lexicon)
        write_thin_learner(load_json(LEARNER_PATH) or {})
        right = sum(1 for e in events if e["result"] == "right")
        print(f"  Receptive check: {len(events)} items recorded, {right} known outright. "
              f"Engineering number — steers the pool; never recited.")
    return 1 if bad else 0


def cmd_feedback(args):
    """Capture (append a dated note) or read (list recent) the feedback ledger.
    Feeds the Diagnosis pass (protocol/diagnosis.md): Anna proposes fixes from
    REPRODUCED patterns, never one-offs — capture is cheap, change is not."""
    log = load_json(FEEDBACK_LOG_PATH) or []
    if args.note:
        log.append({"date": local_today().isoformat(), "note": args.note})
        save_json(FEEDBACK_LOG_PATH, log)
        print(f"  Logged feedback ({len(log)} total): {args.note}")
        return
    if not log:
        print("No feedback logged yet.")
        return
    print(f"FEEDBACK LEDGER ({len(log)} entries) — diagnose patterns, not one-offs:")
    for e in log[-args.n:]:
        print(f"  {e['date']}  {e['note']}")


# `untaught` (2026-09-01) retired 2026-09-10 — spent, and the class of repair it
# made (a field nothing could re-derive) no longer exists: a wrong stamp is a
# wrong event, and `lexicon_view --rebuild` re-derives every row from the log.


def main():
    parser = argparse.ArgumentParser(description="Tamil learning state management")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show current state")

    up = sub.add_parser("update", help="Update state after a session")
    up.add_argument("--soak-payload", type=str, action="append", default=[],
                    help="Word(s) to soak in the next audio episode (the Director's payload)")
    up.add_argument("--soak-seed", type=str, default=None,
                    help="One-line scene seed for the next audio soak")
    up.add_argument("--soak-focus", type=str, default=None,
                    help="What the next dose PERMUTES, free text ('the -aachu tail over "
                         "po and mudi') — a carousel brief, not a word list")
    up.add_argument("--soak-channel", type=str, default=None,
                    choices=list(DOSE_CHANNELS),
                    help="Which lane renders the order (default: episode). Capacity "
                         "routes this, never the curriculum — protocol/audio_channels.md")
    # Deferred import: suggest_targets imports THIS module, so a module-level
    # import would be circular. The palette has one owner either way.
    from suggest_targets import ALL_FORMS, COMMISSIONED_FORMS
    up.add_argument("--soak-form", type=str, default=None, choices=ALL_FORMS,
                    help=f"Commission an episode FORM instead of letting the divergence "
                         f"gate roll one. {'/'.join(COMMISSIONED_FORMS)} can ONLY arrive "
                         f"this way; the rest are normally spec-rotated and this pins them.")
    up.add_argument("--teach", type=str, action="append", default=[],
                    metavar="WORD[=GLOSS]|PHONETIC",
                    help="Word(s) TAUGHT this session — creates the lexicon record at "
                         "`struggled` recognition, seen today, production unset. Tamil "
                         "script keeps the key canonical; the |PHONETIC tail is REQUIRED "
                         "on a new word or it can never be logged from chat again.")
    up.add_argument("--recognized", "--mastered-word", "--comfortable-word", dest="recognized",
                    type=str, action="append", default=[], metavar="WORD[|PHONETIC]",
                    help="Word(s) he RECOGNIZED unaided this session — one observation, "
                         "one rung up on the ear (the two old spellings mean the same). "
                         "'WORD|phonetic' if it is new to the lexicon")
    up.add_argument("--stuck-word", type=str, action="append", default=[],
                    help="Word(s) that failed cold recall — demotes recognition one level")
    up.add_argument("--produced-cold", type=str, action="append", default=[],
                    help="Word(s) produced COLD — no hint (production axis)")
    up.add_argument("--produced-hinted", type=str, action="append", default=[],
                    help="Word(s) produced only after a hint (production axis)")
    up.add_argument("--debrief", type=str, default=None,
                    help="Running 'story so far' — rewrite cumulatively (carry what matters, prune what resolved); Anna's persistent narrative memory, not a one-line log")
    up.add_argument("--next-engine", type=str, default=None,
                    help="Frame key to set as the engine to unlock next (e.g. 'frame:polite-nga')")
    up.add_argument("--quiet-until", type=str, default=None, metavar="YYYY-MM-DD|''",
                    help="TRANSIT BIT: hold every knock through this local date "
                         "(the rails skip before the LLM, so nothing is logged and "
                         "no silence reads as a fade). Pass '' to clear it and resume.")
    up.add_argument("--slip", type=str, action="append", default=[],
                    help="A mistake worth remembering: 'tag|what he said|what it should be|the pattern in one clause'. "
                         "Repeatable. Appends to the slip ledger — never overwrites. The knock judge writes these "
                         "itself; this is the chat lane's half, so a session mistake accumulates the same way.")
    up.add_argument("--slip-tested", type=str, action="append", default=[], metavar="TAG:landed|missed",
                    help="Report an UNVERIFIED slip you deliberately tested this session. 'landed' closes it as of "
                         "today (a later miss revives it); 'missed' logs the failure and keeps it live. Only for a "
                         "slip you actually put in his mouth unaided — it asserts an observation, not a verdict.")
    up.add_argument("--slip-commissioned", type=str, action="append", default=[], metavar="TAG",
                    help="Declare that the soak order set in THIS call pays off that slip tag. Repeatable. "
                         "Without it a dose cannot clear NEVER COMMISSIONED — nothing links a payload word to a "
                         "tag, so the flag would stay on for ever no matter what was built. Only for a dose that "
                         "genuinely targets the pattern; it says a debt was ordered, never that it landed "
                         "(that is --slip-tested).")
    up.add_argument("--no-commission", type=str, default=None, metavar="REASON", dest="no_commission",
                    help="Close despite a live uncommissioned slip pattern, with the reason on the record. "
                         "Without this (or a --slip-commissioned covering the debt) the gate REFUSES the "
                         "close and writes nothing (2026-08-01, Andrew's call).")

    ap = sub.add_parser("add-pattern", help="Seed a generative pattern/lemma record (tracked as an Engine)")
    ap.add_argument("key", help="Canonical key, e.g. 'frame:present-future-toggle'")
    ap.add_argument("--gloss", required=True,
                    help="Human description of the engine, e.g. '-uren (now) vs -ven (later) on any verb'")

    aw = sub.add_parser("add-word", help="Seed a word/chunk record (gloss + phonetics) — a word without a record can't be resolved or scored")
    aw.add_argument("key", help="Canonical Tamil script, e.g. 'என்ன சமைக்கிற?'")
    aw.add_argument("--gloss", required=True, help="English gloss")
    aw.add_argument("--phonetic", action="append", default=[],
                    help="Phonetic spelling(s) Andrew might type (repeatable)")

    rf = sub.add_parser("reseed-focus",
                        help="Re-derive the stored focus cohort from the pool's current order")
    rf.add_argument("--dry-run", action="store_true", help="Print the diff; write nothing")
    sd = sub.add_parser("seed-deck", help="Load a curated set (chunks/frames) into the lexicon — static fields only")
    sd.add_argument("file", help="Path to the set's JSON (e.g. curriculum/trip_deck.json), absolute or repo-relative")

    kr = sub.add_parser("knock-response", help="Log Andrew's tap response against its knock (by --knock-id; most recent if absent)")
    kr.add_argument("response", help="The tap value: 'ack' (got it)")
    kr.add_argument("--knock-id", default="", dest="knock_id",
                    help="The knock's log timestamp (from the notification's action_data); empty → most recent")
    kr.add_argument("--commit", action="store_true",
                    help="Land the tap via commit_and_push (union merge + derived re-render)")

    ck = sub.add_parser("check", help="The Receptive Check — draw a never-tested sample, or record its answers")
    ck.add_argument("--draw", type=int, default=0, metavar="N",
                    help="Print N never-tested rows, deterministic for the month; writes nothing")
    ck.add_argument("--heard", action="append", default=[], metavar="WORD:right|wrong|partial",
                    help="Record one item's answer as a `check` event (repeatable)")

    fb = sub.add_parser("feedback", help="Append a feedback note (capture), or list recent (diagnosis)")
    fb.add_argument("note", nargs="?", default=None, help="The feedback to log; omit to list recent")
    fb.add_argument("-n", type=int, default=20, help="How many recent entries to show when listing")

    re_ = sub.add_parser("rate-episode", help="Record an audio rating from the phone (feed title + a star row)")
    re_.add_argument("--episode", required=True, help="Feed title, exactly as the picker offered it")
    re_.add_argument("--stars", required=True, help="Picker line, e.g. '4 ★★★★'")
    re_.add_argument("--commit", action="store_true", help="Commit and push the ledger (CI lane)")

    sl = sub.add_parser("slips", help="Read the slip ledger (what Andrew keeps getting wrong), or report a test")
    sl.add_argument("-n", type=int, default=15, help="How many patterns to show")
    sl.add_argument("--tested", action="append", default=[], metavar="TAG:landed|missed",
                    help="Report the outcome of putting a slip to the test. 'landed' closes it AS OF TODAY "
                         "(a later miss revives it, history intact); 'missed' logs the failure and keeps it live. "
                         "This asserts an observation — that he fired it right unaided — not a verdict.")

    args = parser.parse_args()
    if args.command == "update":
        cmd_update(args)
    elif args.command == "status":
        # Deferred on purpose: session_brief sits ABOVE this module and imports
        # it, so a top-level import here would be a cycle. Loading a subcommand's
        # module at its dispatch branch is ordinary CLI practice, not a dodge.
        from session_brief import cmd_status
        cmd_status(args)
    elif args.command == "add-pattern":
        cmd_add_pattern(args)
    elif args.command == "add-word":
        cmd_add_word(args)
    elif args.command == "reseed-focus":
        cmd_reseed_focus(args)
    elif args.command == "seed-deck":
        cmd_seed_deck(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "feedback":
        cmd_feedback(args)
    elif args.command == "rate-episode":
        cmd_rate_episode(args)
    elif args.command == "slips":
        cmd_slips(args)
    elif args.command == "knock-response":
        cmd_knock_response(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    # A subcommand that reports an unresolvable row returns non-zero; every other
    # branch returns None. Without this the loud absence is loud on stdout and
    # invisible to CI, which is the same class of silent no-op being repaired.
    sys.exit(main() or 0)
