#!/usr/bin/env python3
"""
State management for the Tamil learning system.

Word-state lives in ONE place: progress/lexicon.json — a word-keyed map where each
record carries both axes (recognition + production), its phonetics, provenance, and
last-surfaced date. This script owns all writes to it. The LLM (Anna) calls
`update` at the end of a session to record what it observed.

  progress/lexicon.json     → word-state (this file's domain)
  progress/learner.json     → continuity: running story (debrief), soak order, status (thin, LLM-facing)
  progress/episodes.json    → episodes / listens (audio artifacts)
  progress/session_log.json → momentum log, one entry per session-DAY (repeat
      update calls in one close merge into that day's entry, never mint a row)

Usage:
    # After a session: record production + recognition movement
    python scripts/sync_state.py update --produced-cold poren --stuck-word வை

    # Show current state (what Anna reads at session start)
    python scripts/sync_state.py status

Canonical-at-write: produced/recognition words are resolved phonetic->script against
the lexicon. A produced word that resolves to no record is WARNED and SKIPPED rather
than silently poisoning state — production presupposes a recognition record.
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from slips import (append_slips, canon_tag, cmd_slips, parse_slip_args,
                   record_slip_commission, record_slip_test, slip_patterns)
from state_io import (BASE, DEFAULT_TZ, EPISODES_PATH, FEEDBACK_LOG_PATH,
                      KNOCK_LOG_PATH, LEARNER_PATH, LEXICON_PATH,
                      SESSION_LOG_PATH, SLIP_LOG_PATH, build_phonetic_index,
                      is_tamil, load_json, local_today, resolve, save_json)

# Windows consoles default to cp1252, which can't print Tamil — the status digest
# crashed mid-print on a fresh laptop (2026-07-15) and a dead digest invites the
# agent to improvise state. Harmless everywhere else.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# How a slip stops being live evidence. After this many days with no recurrence a
# tag RETIRES — it is not "fixed", it is just no longer evidence. Retiring is not
# The sprint deadline (profile.md Phase 1.5): Andrew lands in India the week of
# 2026-08-12. The deck countdown is computed against this; clear it after the trip.
TRIP_DATE = date(2026, 8, 12)

# Recognition ladder. A word the learner *recognizes* is comfortable or solid;
# struggled means shaky; unseen means no record. The floor counts cold production
# among words that are at least comfortable.
RECOGNITION_LEVELS = ["struggled", "comfortable", "solid"]
RECOGNIZED = {"comfortable", "solid"}
DEMOTE = {"solid": "comfortable", "comfortable": "struggled", "struggled": "struggled"}



def mark_exposed(lexicon: dict, keys: list[str], phon_index: dict | None = None,
                 today: str | None = None) -> list[str]:
    """A dose carrying these words went OUT THE DOOR — stamp the delivery.

    Exposure is one of the ledger's three declared events (2026-07-26): a rep is
    Andrew producing the word, an ask is spend, an exposure is delivery. It is
    declared by the seam that ASSEMBLES the dose (episode registration, soak
    sheet, drill sheet, knock push), never mined from prose. The stamp is what
    closes the background rotation loop: being exposed moves a word to the back
    of its own queue, so coverage is guaranteed instead of hoped for.

    Mutates in place; callers own the save. Returns the keys actually stamped."""
    if phon_index is None:
        phon_index = build_phonetic_index(lexicon)
    today = today or local_today().isoformat()
    marked = []
    for k in keys:
        key = resolve(k, lexicon, phon_index)
        if key is None:
            print(f"   ⚠ exposure: '{k}' not in lexicon — skipped")
            continue
        lexicon[key]["last_surfaced"] = today
        lexicon[key]["exposures"] = lexicon[key].get("exposures", 0) + 1
        marked.append(key)
    return marked


def record_exposure(keys: list[str]) -> list[str]:
    """Load-stamp-save wrapper around `mark_exposed` for delivery seams that do
    not already hold the lexicon in memory (knock push, soak, drill, drain).
    The caller adds LEXICON_PATH to its commit when this returns anything."""
    lexicon = load_json(LEXICON_PATH)
    if lexicon is None or not keys:
        return []
    marked = mark_exposed(lexicon, keys)
    if marked:
        save_json(LEXICON_PATH, lexicon)
        print(f"   Exposure stamped: {', '.join(marked)}")
    return marked


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


def canon_payload(items: list[str]) -> list[str]:
    """Split comma-joined payload elements into a flat word list. A close once
    passed `--soak-payload "frame:idum,பாத்துக்கறேன்"` as one string (2026-07-13);
    the stored blob could never textually match an episode's words, so the
    session-open drain check read 'not produced' forever. Applied at write AND
    at read, so already-stored blobs heal too."""
    return [p.strip() for item in items for p in item.split(",") if p.strip()]


def resolve_soak_item(token: str, lexicon: dict, phon_index: dict[str, str]) -> str | None:
    """A soak-payload token → its canonical lexicon key, or None.

    Wider than resolve() on purpose: Anna writes the soak order in prose and
    reaches for the bare headword ('avasaram') where the lexicon key is the
    whole chunk ('அவசரம் இருக்கு', phonetic 'avasaram irukku'). A payload item
    that resolves to nothing can never appear in an episode's word list, so the
    produced-check stays False forever — on 2026-07-23 that dispatched a fresh
    episode every hour until the cron was pulled (M72, M73, M74 in one evening).
    """
    exact = resolve(token, lexicon, phon_index)
    if exact is not None:
        return exact
    t = token.strip().lower()
    if not t:
        return None
    # a phonetic that STARTS with the token ('avasaram' → 'avasaram irukku')
    for key, rec in lexicon.items():
        for p in rec.get("phonetic", []):
            if p and (p.lower() == t or p.lower().startswith(t + " ")):
                return key
    # a Tamil token that is a prefix of a longer chunk key
    if is_tamil(token):
        for key in lexicon:
            if key.startswith(token):
                return key
    return None


def split_payload(items: list[str], lexicon: dict) -> tuple[list[str], list[str]]:
    """(resolved canonical keys, tokens that resolve to nothing). Callers must
    treat the unresolved list as a WARNING and never as 'still pending' — an
    unverifiable item is a broken order, not unfinished work."""
    phon_index = build_phonetic_index(lexicon)
    resolved, unresolved = [], []
    for token in canon_payload(items):
        key = resolve_soak_item(token, lexicon, phon_index)
        if key:
            resolved.append(key)
        elif is_tamil(token) or token.startswith("frame:"):
            # A brand-new payload word is legitimately absent from the lexicon
            # until the episode that teaches it registers it — Tamil script and
            # frame keys stay verifiable, because that is exactly the form an
            # episode's word list stores. Only a LATIN fragment that resolves to
            # nothing ('avasaram' vs 'அவசரம் இருக்கு') can never match anything.
            resolved.append(token)
        else:
            unresolved.append(token)
    return resolved, unresolved


def soak_pending() -> bool:
    """True when the standing soak order hasn't been carried by the newest
    episode — the same answer `status` prints as NOT YET PRODUCED.

    Only VERIFIABLE items count. A payload token that resolves to no lexicon
    key can never appear in an episode's word list, so counting it as pending
    is an infinite dispatch loop, not a to-do (2026-07-23: 'avasaram' against
    the key 'அவசரம் இருக்கு' produced three unwanted episodes in one evening).

    Lives here rather than in `studio_watchdog` (2026-07-28) because the session
    ticket needs the same answer and cannot import the studio — `run_studio`
    pulls the whole render stack. One definition, three readers; the watchdog
    re-exports it."""
    soak = (load_json(LEARNER_PATH) or {}).get("soak_order") or {}
    raw = [w for w in soak.get("payload", []) if w]
    if not raw:
        return False
    resolved, unresolved = split_payload(raw, load_json(LEXICON_PATH) or {})
    if unresolved:
        print(f"  ⚠ soak payload unresolvable, ignored for the produced-check: "
              f"{', '.join(unresolved)} — fix the soak order")
    if not resolved:
        return False
    episodes = load_json(EPISODES_PATH) or {}
    newest = episodes[max(episodes, key=int)].get("words", []) if episodes else []
    return not all(w in newest for w in resolved)


def is_unseen(rec: dict) -> bool:
    """Never soaked anywhere — no episode appearance, never surfaced. The
    teach-first law hangs on this: an UNSEEN item may be TAUGHT (shown, with its
    meaning) but never cold-quizzed. One definition; the knock menu, the volley
    picker, and the session ticket all read it."""
    return not rec.get("seen_in") and not rec.get("last_surfaced")


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


def compute_deck(lexicon: dict, deck: str = "trip") -> dict:
    """A named deck is a finite, deadline-driven set (e.g. the India-trip survival
    phrases) tagged `deck: "<name>"`. Its meter is the headline during a sprint:
    of the deck's members, how many fire cold? Members are counted regardless of
    type — a chunk fires cold when said whole, a frame when a novel slot-fill lands.
    Anna narrates the countdown to the deadline (Python counts; Anna narrates).

    Members carry a `direction`: "fire" (default — cleared when production goes
    cold) or "catch" (ear-only — the win is comprehension, cleared when recognition
    reaches solid; never forced to fire). cleared/total/pct stay the FIRE side so
    every caller's headline is honest; caught/catch_total meter the ear."""
    members = {w: r for w, r in lexicon.items() if r.get("deck") == deck}
    fire = [w for w, r in members.items() if r.get("direction", "fire") != "catch"]
    catch = [w for w, r in members.items() if r.get("direction") == "catch"]
    cleared = [w for w in fire if members[w].get("production") == "cold"]
    caught = [w for w in catch if members[w].get("recognition") == "solid"]
    total = len(fire)
    pct = (len(cleared) / total * 100) if total else 0.0
    # Survival-tier headline (2026-07-18, Andrew — refines the 07-13 touchdown bar:
    # the narrated meter counts the tier that decides freezing at the table, not the
    # whole inventory; a 2.5/day full-deck ask read as failure at a winnable 1.1/day
    # survival pace). Tier stays a menu concern owned by suggest_targets — joined
    # lazily so the lexicon schema stays frozen; no curriculum file → survival
    # degrades to the whole fire side.
    try:
        from suggest_targets import DECK_TIERS, deck_registers
        regs = deck_registers(deck)
        surv = [w for w in fire if DECK_TIERS.get(regs.get(w, ""), 1) == 0] if regs else fire
    except Exception:
        surv = fire
    # Coverage rides alongside the headline (2026-07-25): cold/total is honest
    # about what it counts and blind to distribution — it read as a won sprint
    # while 50 of 70 fire items had never been worked. `untouched` is the count
    # of members with no `last_surfaced` at all; the per-tier/per-register
    # breakdown lives on the ticket (suggest_targets → deck_coverage).
    untouched = sum(1 for w in fire if not members[w].get("last_surfaced"))
    surv_untouched = sum(1 for w in surv if not members[w].get("last_surfaced"))
    return {"cleared": len(cleared), "total": total, "pct": pct,
            "caught": len(caught), "catch_total": len(catch),
            "surv_cleared": sum(1 for w in surv if members[w].get("production") == "cold"),
            "surv_total": len(surv),
            "untouched": untouched, "surv_untouched": surv_untouched,
            "catch_untouched": sum(1 for w in catch if not members[w].get("last_surfaced"))}


# --- Episode helpers (progress/episodes.json — a flat {id: episode} map) ------

def compute_status() -> str:
    """The status line IS the scoreboard (post the 2026-06-30 listens pivot):
    the deck countdown during a sprint, the floor otherwise. Never a chore line —
    episodes are self-contained doses; nothing is ever 'under-listened'.

    TWO ERAS, not a deadline (2026-08-04, Andrew: "think of it as pre-trip and
    during-trip eras"). `TRIP_DATE` was modelled as a terminus, so from the day
    he LANDS the line read "-3 days to touchdown · need 8.0 cold/day" and stayed
    there — degenerate on the first day of the era the deck exists for, and the
    line Anna narrates from. In country the countdown is meaningless and the
    burn rate is a lie: the table sets the pace, not a per-day quota."""
    lexicon = load_json(LEXICON_PATH) or {}
    deck = compute_deck(lexicon)
    if deck["total"]:
        days = (TRIP_DATE - local_today()).days
        never = (f" · {deck['untouched']} never worked" if deck["untouched"] else "")
        when = f"{days} days to touchdown" if days > 0 else f"in country, day {1 - days}"
        return (f"Trip Deck {deck['surv_cleared']}/{deck['surv_total']} survival cold · "
                f"{when} · "
                f"{burn_rate(deck['surv_total'] - deck['surv_cleared'], days)} · "
                f"full deck {deck['cleared']}/{deck['total']}{never}")
    floor = compute_floor(lexicon)
    return f"Viability floor {floor['cleared']}/{floor['total']} fire cold ({floor['pct']:.0f}%)"


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


def burn_rate(pending: int, days_left: int, window: int = 7) -> str:
    """The honest pace line: cold/day needed to clear the given pending count by
    the deadline vs. the trailing cold/day actually happening (survival tier since
    2026-07-18). Python states the math; Anna narrates what it means.

    Past the deadline there IS no required pace — the `max(days_left, 1)` clamp
    silently froze the ask at its final day's value and reported it forever
    (2026-08-04). Guarding here rather than at each caller: `show_status` reads
    this directly too, so a caller-side fix would have healed one surface."""
    pace = cold_fires_recent(window) / window
    if days_left <= 0:
        return f"trailing {window}-day pace {pace:.1f}/day"
    return f"need {pending / days_left:.1f} cold/day, trailing {window}-day pace {pace:.1f}/day"


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


def compute_recent_missions(episodes: dict, n: int = 4) -> list[dict]:
    # No listens count here — each episode is a self-contained dose (the
    # 2026-06-30 pivot); surfacing a counter to Anna invites listen-chasing.
    return [{"mission": int(m), "title": ep.get("title", f"Mission {m}")}
            for m, ep in sorted(episodes.items(), key=lambda x: int(x[0]), reverse=True)[:n]]


def write_thin_learner(learner: dict, episodes: dict):
    thin = {
        "learner": learner.get("learner", "Andrew"),
        # The zone every clock-facing rule reads (state_io.LOCAL_TZ). It is in
        # this whitelist for the reason the block below spells out: omitted here,
        # the first sync after he lands in India would silently restore the home
        # clock, and quiet hours would start firing at 3am Chennai with nothing
        # on screen to say why. Travel is exactly when nobody is auditing state.
        "timezone": learner.get("timezone", DEFAULT_TZ),
        # The transit bit (2026-08-10, Andrew). An ISO date through which the
        # rails refuse to wake Anna at all, or "" for off. Whitelisted here for
        # the same reason `slip_closes` had to be: a key missing from this dict
        # is DELETED on the next update, so a flag set before a flight would be
        # wiped by the first session close and nothing would say it had gone.
        "quiet_until": learner.get("quiet_until", ""),
        "last_debrief": learner.get("last_debrief", ""),
        "soak_order": learner.get("soak_order", {}),
        "next_engine": learner.get("next_engine", ""),
        # The ≤FOCUS_SIZE drill cohort — stored state, not an emergent sort
        # (2026-07-26): membership is a fact in a file, immune to counting bugs.
        "focus_cohort": learner.get("focus_cohort", []),
        # The slip ledger's two learner-side books. THIS IS A WHITELIST — a key
        # missing here is DELETED on the next update, not merely left stale.
        # `slip_closes` was absent from it, so `--slip-tested tag:landed` wrote a
        # close and the very same close's write_thin_learner erased it: no slip
        # had ever actually been closed since the mechanism shipped 2026-07-30,
        # and nothing surfaced the loss because a wiped close is indistinguishable
        # from never having tested. Found 2026-07-31 while wiring
        # slip_commissions, which landed in the identical trap on its first run.
        # Any future learner-side book must be added here too.
        "slip_closes": learner.get("slip_closes", {}),
        "slip_commissions": learner.get("slip_commissions", {}),
        "recent_missions": compute_recent_missions(episodes),
        "status": compute_status(),
    }
    save_json(LEARNER_PATH, thin)
    print(f"  Updated learner.json ({LEARNER_PATH.relative_to(BASE)})")


# --- Commands ----------------------------------------------------------------

def cmd_update(args):
    lexicon = load_json(LEXICON_PATH)
    learner = load_json(LEARNER_PATH)
    episodes = load_json(EPISODES_PATH) or {}
    if lexicon is None or learner is None:
        print("Error: lexicon.json or learner.json missing. See BOOTSTRAP.md.")
        sys.exit(1)

    phon_index = build_phonetic_index(lexicon)
    today = local_today().isoformat()
    applied = {"cold": [], "hinted": [], "demoted": []}  # for the session log

    # ── THE COMMISSION GATE (2026-08-01, Andrew: "block the close") ──────
    # NEVER COMMISSIONED was advisory and got walked past for mechanical
    # reasons — venum-for-kudunga sat 24 days between first slip and first
    # dose while the ticket warned daily ("the flag needs teeth", feedback
    # 07-31, second occurrence of the commissioning complaint). Same law as
    # wants_scheduled_push: when prose fails, Python catches the
    # contradiction and forces the re-ask. Runs BEFORE any write so a
    # refused close is safely re-runnable — touch() counts reps, so a
    # partially-applied close must never happen.
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
    reason = getattr(args, "no_commission", None)
    if owed and not reason:
        print("⛔ CLOSE REFUSED — live slip pattern(s) with no dose ever built:")
        for p in owed:
            print(f"   ⚠ {p['tag']} — {p['count']}× over {p['span_days']}d")
        print("   Commission in THIS close:   --soak-payload … --soak-channel "
              "soak|episode|drill --slip-commissioned <tag>")
        print("   …or close over it, reason on the record:   --no-commission '<why>'")
        print("   Nothing was written. Re-run the FULL close with one of the above.")
        sys.exit(2)
    if owed:
        print(f"  ⚠ closing over uncommissioned slip(s) "
              f"({', '.join(p['tag'] for p in owed)}) — reason: {reason}")

    def touch(key):
        """Worked in a session: refresh the date AND count the rep.
        `last_surfaced` is one overwritten date, so it can say WHEN but never HOW
        MANY — and the focus set needs a count (2026-07-26). Both channels write
        THIS counter now: sessions here, knocks at the judge seam
        (knock_reply.apply_verdict) — declared events, never text forensics."""
        lexicon[key]["last_surfaced"] = today
        lexicon[key]["reps"] = lexicon[key].get("reps", 0) + 1

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

    def set_recognition(spec, level):
        """Set recognition; create a record if the word is new (script only)."""
        word, phon = split_phonetic(spec)
        key = resolve(word, lexicon, phon_index)
        if key is None:
            if not is_tamil(word) or not phon:
                print(f"  ! '{word}' can't be created — a new record needs Tamil script AND its sounds-like form: '{word}|phonetic'. Skipped.")
                return
            lexicon[word] = {
                "gloss": "", "phonetic": [phon], "recognition": level,
                "production": "none", "seen_in": [], "last_surfaced": today,
            }
            print(f"  + New word '{word}' → recognition {level} (phonetic '{phon}'; gloss empty — fill in later)")
            return
        lexicon[key]["recognition"] = level
        touch(key)
        print(f"  Recognition '{key}' → {level}")

    def demote_recognition(word):
        key = resolve(word, lexicon, phon_index)
        if key is None:
            print(f"  ! '{word}' not in lexicon — nothing to demote. Skipped.")
            return
        cur = lexicon[key].get("recognition", "struggled")
        new = DEMOTE.get(cur, "struggled")
        lexicon[key]["recognition"] = new
        touch(key)
        applied["demoted"].append(key)
        print(f"  Recognition '{key}' demoted {cur} → {new}")

    def set_production(word, level):
        key = resolve(word, lexicon, phon_index)
        if key is None:
            print(f"  ! Produced '{word}' but no record resolves — add recognition first (script). Skipped.")
            return
        lexicon[key]["production"] = level
        touch(key)
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
            touch(key)
            if gloss and not lexicon[key].get("gloss"):
                lexicon[key]["gloss"] = gloss
            print(f"  Taught (already known): {key} — refreshed, recognition left "
                  f"at {lexicon[key].get('recognition', 'struggled')}")
            return
        if not phon:
            print(f"  ! '{word}' is new — teach it with its sounds-like form, '{word}=gloss|phonetic', or it can never be logged from chat. Skipped.")
            return
        lexicon[word] = {
            "gloss": gloss, "phonetic": [phon], "recognition": "struggled",
            "production": "none", "seen_in": [], "last_surfaced": today,
        }
        print(f"  + Taught '{word}' → recognition struggled"
              f"{', gloss: ' + gloss if gloss else ' (gloss empty — fill in later)'}")

    # Taught this session — must run BEFORE the axes below, so a word taught and
    # then fired in the same close resolves instead of being refused.
    for spec in args.teach:
        teach_word(spec)

    # Recognition movement
    for w in args.mastered_word:
        set_recognition(w, "solid")
    for w in args.comfortable_word:
        set_recognition(w, "comfortable")
    for w in args.stuck_word:
        demote_recognition(w)

    # Production axis
    for w in args.produced_cold:
        set_production(w, "cold")
    for w in args.produced_hinted:
        set_production(w, "hinted")

    # Listened episodes — hearing an episode surfaces its words (audio side of the
    # recency bridge): bump last_surfaced on each of its words that is in the lexicon.
    for mission in args.listened:
        ep = episodes.get(str(mission))
        if not ep:
            print(f"  ! No episode M{mission} to log a listen for. Skipped.")
            continue
        ep["listens"] = ep.get("listens", 0) + 1
        surfaced = 0
        for w in ep.get("words", []):
            key = resolve(w, lexicon, phon_index)
            if key:
                lexicon[key]["last_surfaced"] = today
                surfaced += 1
        print(f"  Listened M{mission} (now {ep['listens']}x) — surfaced {surfaced} lexicon words")

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

    # Mark-seen — update last_surfaced without touching recognition/production.
    # Closes the lore-memo gap: a frame a knock introduced is no longer UNSEEN.
    for key in args.mark_seen:
        if key in lexicon:
            touch(key)
            print(f"  Marked seen: {key}")
        else:
            print(f"  ! '{key}' not in lexicon — skipped")

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
        if args.soak_form is not None:
            order["form"] = args.soak_form
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

    # Both writers above persist straight to LEARNER_PATH, but this function is
    # holding a `learner` read BEFORE they ran and write_thin_learner rebuilds
    # the file from it — so without this re-read the close or commission is
    # erased by the very call that made it. That is exactly how slip_closes was
    # lost silently for a day (2026-07-30 → 07-31).
    fresh = load_json(LEARNER_PATH) or {}
    for book in ("slip_closes", "slip_commissions"):
        if fresh.get(book):
            learner[book] = fresh[book]

    # No streak bookkeeping — recency comes from the session log, and a stored
    # streak is a meter that lies the moment a day is skipped (Enjoyment Clause).
    learner.pop("streak", None)

    # Focus cohort — stored membership, reconciled only here and at the judge
    # seam: leave on graduation, enter on seat-open (2026-07-26).
    from suggest_targets import reconcile_focus  # lazy: suggest_targets imports us
    old_cohort = learner.get("focus_cohort", [])
    learner["focus_cohort"] = reconcile_focus(lexicon, old_cohort)
    left = sorted(set(old_cohort) - set(learner["focus_cohort"]))
    entered = sorted(set(learner["focus_cohort"]) - set(old_cohort))
    if left or entered:
        print(f"  Focus cohort: -{left or '[]'} +{entered or '[]'}"
              f" ({len(learner['focus_cohort'])} seats held)")

    save_json(LEXICON_PATH, lexicon)
    if episodes:
        save_json(EPISODES_PATH, episodes)
    write_thin_learner(learner, episodes)

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
    if applied["cold"] or applied["hinted"] or applied["demoted"] or args.listened or args.debrief:
        log = load_json(SESSION_LOG_PATH) or []
        entry = log[-1] if log and log[-1].get("date") == today else None
        if entry is None:
            entry = {"date": today, "cold": [], "hinted": [], "demoted": [],
                     "listened": [], "note": ""}
            log.append(entry)
        # Union, not concatenate — the same word re-logged is one fire, not two.
        for field, values in (("cold", applied["cold"]), ("hinted", applied["hinted"]),
                              ("demoted", applied["demoted"]), ("listened", list(args.listened))):
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
    deck = compute_deck(lexicon)
    if deck["total"]:
        catch = f" · catch {deck['caught']}/{deck['catch_total']} solid" if deck["catch_total"] else ""
        print(f"Trip Deck: {deck['surv_cleared']}/{deck['surv_total']} survival cold · "
              f"full deck {deck['cleared']}/{deck['total']}{catch}")
        if deck["untouched"]:
            print(f"  ⚠ Coverage: {deck['untouched']} fire item(s) never worked "
                  f"({deck['surv_untouched']} survival)")
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
        "recognition": args.recognition,
        "production": "none",
        "seen_in": [],
        "last_surfaced": today,
    }
    save_json(LEXICON_PATH, lexicon)
    print(f"  + Pattern '{args.key}' seeded — {args.gloss}")
    print(f"    (recognition {args.recognition}, production none)")
    print(f"    Log a cold novel instance later with:  update --produced-cold '{args.key}'")


def cmd_add_word(args):
    """Seed a word/chunk record with its gloss and phonetics in one shot — the
    proper birth of a new lexicon entry (update --comfortable-word creates
    gloss-less stubs; soak orders don't create records at all). Without a record,
    a word can never be resolved, scored, or surface on a ticket."""
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
        "recognition": args.recognition,
        "production": "none",
        "seen_in": [],
        "last_surfaced": local_today().isoformat(),
    }
    save_json(LEXICON_PATH, lexicon)
    print(f"  + '{args.key}' — {args.gloss} (recognition {args.recognition}, phonetic {list(args.phonetic)})")


def cmd_seed_deck(args):
    """Idempotently load a curated deck file (e.g. curriculum/trip_deck.json) into
    the lexicon, tagging each entry `deck: <name>`. The deck file is CONTENT (Anna
    drafts it, the Oracle vets it); this command is the MECHANISM that lands it —
    the same LLM-writes / Python-owns-state split as word_pool.json.

    Each deck entry: {"tamil", "gloss", "phonetic": [...], "type": "chunk"|"frame",
    "recognition"?, "direction"?: "fire"|"catch", "pairs_with"?}. A "frame" is stored as a lexicon
    `pattern` (an Engine); a "chunk" is word-like (counts in the viability floor).
    "catch" marks ear-only items (cleared by recognition, never forced to fire);
    "pairs_with" names the chunk that answers it — hear X → say Y, validated to
    resolve inside the same file so a pair can never be silently split.
    Re-runnable and the file is the source of truth: existing entries get the deck
    tag + direction + any missing gloss/phonetic without clobbering their learning
    state; new entries are created; lexicon entries tagged with this deck but no
    longer in the file are un-tagged (their learning state stays)."""
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
    in_file = {e.get("tamil") for e in entries}
    split = [(e.get("tamil"), e.get("pairs_with")) for e in entries
             if e.get("pairs_with") and e["pairs_with"] not in in_file]
    if split:
        for tamil, pair in split:
            print(f"  ✗ '{tamil}' pairs_with '{pair}', which is not in this deck — split pair.")
        print("  Error: seed refused, nothing written. A pair must resolve inside the file.")
        sys.exit(1)
    created = updated = 0
    for e in entries:
        tamil = e.get("tamil")
        if not tamil:
            print(f"  ! deck entry missing 'tamil' — skipped: {e}")
            continue
        pair = e.get("pairs_with")
        lex_type = "pattern" if e.get("type") == "frame" else e.get("type", "chunk")
        # Chunks/words must be canonical Tamil script; frames use the `frame:...`
        # key convention (like add-pattern), so they're exempt from the script check.
        if lex_type != "pattern" and not is_tamil(tamil):
            print(f"  ! '{tamil}' isn't Tamil script — chunks must be canonical script. Skipped.")
            continue
        if tamil in lexicon:
            rec = lexicon[tamil]
            rec["deck"] = args.deck
            rec["direction"] = e.get("direction", "fire")
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
            lexicon[tamil] = {
                "type": lex_type,
                "gloss": e.get("gloss", ""),
                "phonetic": e.get("phonetic", []),
                "recognition": e.get("recognition", "comfortable"),
                "production": "none",
                "seen_in": [],
                "last_surfaced": None,
                "deck": args.deck,
                "direction": e.get("direction", "fire"),
                **({"pairs_with": pair} if pair else {}),
            }
            created += 1
    # The deck file is the source of truth: un-tag lexicon entries that left it.
    pruned = []
    for w, rec in lexicon.items():
        if rec.get("deck") == args.deck and w not in in_file:
            del rec["deck"]
            rec.pop("direction", None)
            rec.pop("pairs_with", None)
            pruned.append(w)
    save_json(LEXICON_PATH, lexicon)
    deck = compute_deck(lexicon, args.deck)
    print(f"  Seeded deck '{args.deck}': +{created} new, {updated} re-tagged, {len(pruned)} un-tagged.")
    for w in pruned:
        print(f"    - un-tagged (stays in lexicon): {w}")
    print(f"  Trip Deck now: {deck['cleared']}/{deck['total']} fire cold ({deck['pct']:.0f}%)"
          + (f" · catch {deck['caught']}/{deck['catch_total']} solid" if deck["catch_total"] else ""))




# Knock tap responses (from Home Assistant's actionable notification). Both are
# SOAK-tier signals — they record that the knock landed and let the nudge gate
# back off; neither touches the production/viability floor (that only flips when
# Anna witnesses an unaided cold fire in chat). 'listened' additionally credits
# the soak: it bumps the latest published episode's listens + surfaces its words.
#   ack      — "got it / played the memo"      → knock marked landed, no learning write
#   listened — "I listened to the episode"     → knock marked landed + episode soak credit
KNOCK_RESPONSES = {"ack", "listened"}
# A later tap may only *upgrade* an earlier one (strictly more signal); same-or-less is a no-op.
KNOCK_UPGRADES = {None: KNOCK_RESPONSES, "ack": {"listened"}}


def credit_latest_episode_listen() -> str | None:
    """Soak credit for a 'listened' tap. 'Latest published' = the highest mission
    key in episodes.json (the newest one in the feed). Mirrors `update --listened`,
    but a tap can't name a mission so it always credits the newest episode.
    Returns a one-line summary, or None if there's nothing to credit."""
    episodes = load_json(EPISODES_PATH) or {}
    if not episodes:
        return None
    mission = max(episodes, key=int)
    ep = episodes[mission]
    lexicon = load_json(LEXICON_PATH) or {}
    learner = load_json(LEARNER_PATH) or {}
    phon_index = build_phonetic_index(lexicon)
    today = local_today().isoformat()
    ep["listens"] = ep.get("listens", 0) + 1
    surfaced = 0
    for w in ep.get("words", []):
        key = resolve(w, lexicon, phon_index)
        if key:
            lexicon[key]["last_surfaced"] = today
            surfaced += 1
    save_json(EPISODES_PATH, episodes)
    save_json(LEXICON_PATH, lexicon)
    write_thin_learner(learner, episodes)  # refresh recent_missions + status line
    return f"M{mission} '{ep.get('title', mission)}' now {ep['listens']}x — surfaced {surfaced} words"


def cmd_knock_response(args):
    """Record Andrew's tap response against the most recent knock.
    Called by the log-knock-response GitHub Actions workflow when HA fires the event.
    Idempotent: a duplicate tap is a no-op, but 'listened' may upgrade a prior 'ack'."""
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
    prior = last.get("response")
    if prior is not None and response not in KNOCK_UPGRADES.get(prior, set()):
        print(f"  Most recent knock ({last['date']}) already '{prior}'; '{response}' adds nothing. Skipping.")
        return

    last["response"] = response
    last["response_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # 'listened' is the only response that credits a soak (the episode, not the knock).
    if response == "listened":
        summary = credit_latest_episode_listen()
        if summary:
            last["episode_credit"] = summary
            print(f"  Listened → {summary}")
        else:
            print("  Listened, but no episodes in episodes.json to credit.")

    save_json(KNOCK_LOG_PATH, log)
    print(f"  Knock {last['date']} marked '{response}'")

    if getattr(args, "commit", False):
        # Lazy: morning_knock -> render_chat -> sync_state, so importing at module
        # level would be circular.
        from morning_knock import commit_and_push
        from render_chat import render_chat
        # Replaces the hand-rolled stage/commit/pull/push that lived in the "Log
        # tap" step of anna.yml (2026-08-04). That copy did a bare
        # `git pull --rebase` with NO union resolution and no derived re-render —
        # the same race the reply lane had a net for, in the one lane that had
        # none. It also never re-rendered chat.md, so a tap's "👍 acked" sat
        # unrendered until some later knock happened to rebuild the file.
        paths = [KNOCK_LOG_PATH, EPISODES_PATH, LEARNER_PATH, LEXICON_PATH, render_chat()]
        commit_and_push([p for p in paths if p.exists()], f"Knock response: {response}")


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


def cmd_prune_duplicates(args):
    """Drop lexicon rows that duplicate another row and carry nothing of their own.

    Replaces `migrate-session-log` (2026-07-31), which was spent: it reports
    "nothing to do" against the repaired log, and the same-day merge in
    `cmd_update` is the forward fix that stops the rows recurring. A one-time
    migration whose one time has passed is crud, and this file was at 1247/1250.

    THE DUPLICATE SIGNAL IS THE PHONETIC, NEVER THE KEY (2026-08-04). Trailing
    punctuation is load-bearing here: `எங்க` is "our" and `எங்க?` is "where?" —
    two lemmas that differ by one character, so any rule that normalises keys
    merges them and destroys a real distinction. Two rows are duplicates only
    when they share a phonetic AND one is strictly poorer on every axis.

    `frame:` keys are exempt: a frame legitimately shares a phonetic with the
    chunk that exemplifies it (`vandhutten` is both `வந்துட்டேன்` and
    `frame:done-ittu`), which is the one collision that must never be pruned.

    Strict domination is what makes this safe to automate. A row that is better
    on any axis — or that holds a deck tag, a type, or reps the other lacks — is
    never dropped, so the command can only ever remove a row whose deletion
    loses nothing. Anything else is reported for a human and left alone."""
    lexicon = load_json(LEXICON_PATH) or {}
    rank = {"recognition": RECOGNITION_LEVELS,
            "production": ["none", "hinted", "cold"]}

    def poorer(a: str, b: str) -> bool:
        """Is row `a` strictly dominated by row `b` — nothing to lose by dropping it?"""
        ra, rb = lexicon[a], lexicon[b]
        for axis, levels in rank.items():
            if levels.index(ra.get(axis) or levels[0]) > levels.index(rb.get(axis) or levels[0]):
                return False
        if ra.get("reps", 0) > rb.get("reps", 0) or ra.get("last_surfaced"):
            return False
        # A tag the survivor lacks is content: deck membership, type, seen_in.
        return not any(ra.get(f) and not rb.get(f) for f in ("deck", "type", "seen_in"))

    index: dict[str, list[str]] = {}
    for word, rec in lexicon.items():
        if word.startswith("frame:"):
            continue
        for phon in rec.get("phonetic") or []:
            index.setdefault(phon.strip().lower(), []).append(word)

    doomed, flagged = [], []
    for phon, words in sorted(index.items()):
        if len(words) < 2:
            continue
        losers = [w for w in words if any(w != k and poorer(w, k) for k in words)]
        # Never drop every side of a collision: identical twins dominate each
        # other, so keep the first and drop the rest.
        for word in losers[1:] if len(losers) == len(words) else losers:
            doomed.append((word, phon, next(k for k in words if k != word)))
        if not losers:
            flagged.append((phon, words))

    for phon, words in flagged:
        print(f"  ⚠ '{phon}' is shared by {words} — neither is strictly poorer. "
              f"Not a duplicate, or a real merge someone has to make by hand.")
    if not doomed:
        print(f"lexicon.json: {len(lexicon)} rows, no strictly-dominated duplicates.")
        return
    print(f"lexicon.json: {len(lexicon)} rows, {len(doomed)} dominated duplicate(s):")
    for word, phon, keeper in doomed:
        print(f"  - drop {word!r} (shares '{phon}' with {keeper!r}, and carries nothing it lacks)")
    if not args.apply:
        print("\n  DRY RUN — nothing written. Re-run with --apply to commit the change.")
        print("  (git holds the current file; `git checkout -- progress/lexicon.json` reverts.)")
        return
    for word, _, _ in doomed:
        del lexicon[word]
    save_json(LEXICON_PATH, lexicon)
    print(f"\n  ✅ written — {len(lexicon)} rows.")


def main():
    parser = argparse.ArgumentParser(description="Tamil learning state management")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show current state")

    up = sub.add_parser("update", help="Update state after a session")
    up.add_argument("--listened", type=int, action="append", default=[],
                    help="Mission number(s) the learner listened to (bumps listens + surfaces words)")
    up.add_argument("--soak-payload", type=str, action="append", default=[],
                    help="Word(s) to soak in the next audio episode (the Director's payload)")
    up.add_argument("--soak-seed", type=str, default=None,
                    help="One-line scene seed for the next audio soak")
    up.add_argument("--soak-focus", type=str, default=None,
                    help="What the next dose PERMUTES, free text ('the -ஆச்சு tail over "
                         "போ and முடி') — a carousel brief, not a word list")
    up.add_argument("--soak-channel", type=str, default=None,
                    choices=["episode", "soak", "drill"],
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
    up.add_argument("--mastered-word", type=str, action="append", default=[],
                    help="Word(s) now solid — 'WORD|phonetic' if it is new to the lexicon")
    up.add_argument("--comfortable-word", type=str, action="append", default=[],
                    help="Word(s) now comfortable — 'WORD|phonetic' if new to the lexicon")
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
    up.add_argument("--mark-seen", type=str, action="append", default=[],
                    help="Frame/word key(s) to mark as seen today (sets last_surfaced; closes lore-memo gap)")
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
                    help="Human description of the engine, e.g. '-உறேன் (now) vs -வேன் (later) on any verb'")
    ap.add_argument("--recognition", default="comfortable", choices=RECOGNITION_LEVELS,
                    help="Starting recognition level (default: comfortable)")

    aw = sub.add_parser("add-word", help="Seed a word/chunk record (gloss + phonetics) — a word without a record can't be resolved or scored")
    aw.add_argument("key", help="Canonical Tamil script, e.g. 'என்ன சமைக்கிற?'")
    aw.add_argument("--gloss", required=True, help="English gloss")
    aw.add_argument("--phonetic", action="append", default=[],
                    help="Phonetic spelling(s) Andrew might type (repeatable)")
    aw.add_argument("--recognition", default="comfortable", choices=RECOGNITION_LEVELS,
                    help="Starting recognition level (default: comfortable)")

    sd = sub.add_parser("seed-deck", help="Load a curated deck file (chunks/frames) into the lexicon, tagged with a deck name")
    sd.add_argument("file", help="Path to the deck JSON (e.g. curriculum/trip_deck.json), absolute or repo-relative")
    sd.add_argument("--deck", default="trip", help="Deck name to tag entries with (default: trip)")

    kr = sub.add_parser("knock-response", help="Log Andrew's tap response against its knock (by --knock-id; most recent if absent)")
    kr.add_argument("response", help="The tap value: 'ack' (got it) or 'listened' (heard the episode → soak credit)")
    kr.add_argument("--knock-id", default="", dest="knock_id",
                    help="The knock's log timestamp (from the notification's action_data); empty → most recent")
    kr.add_argument("--commit", action="store_true",
                    help="Land the tap via commit_and_push (union merge + derived re-render)")

    fb = sub.add_parser("feedback", help="Append a feedback note (capture), or list recent (diagnosis)")
    fb.add_argument("note", nargs="?", default=None, help="The feedback to log; omit to list recent")
    fb.add_argument("-n", type=int, default=20, help="How many recent entries to show when listing")

    sl = sub.add_parser("slips", help="Read the slip ledger (what Andrew keeps getting wrong), or report a test")
    sl.add_argument("-n", type=int, default=15, help="How many patterns to show")
    sl.add_argument("--tested", action="append", default=[], metavar="TAG:landed|missed",
                    help="Report the outcome of putting a slip to the test. 'landed' closes it AS OF TODAY "
                         "(a later miss revives it, history intact); 'missed' logs the failure and keeps it live. "
                         "This asserts an observation — that he fired it right unaided — not a verdict.")

    pd = sub.add_parser("prune-duplicates",
                        help="Drop lexicon rows that share a phonetic with another row and "
                             "carry nothing it lacks (2026-08-04). Previews unless --apply.")
    pd.add_argument("--apply", action="store_true",
                    help="Actually write. Without it this only reports what would change.")

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
    elif args.command == "seed-deck":
        cmd_seed_deck(args)
    elif args.command == "feedback":
        cmd_feedback(args)
    elif args.command == "slips":
        cmd_slips(args)
    elif args.command == "knock-response":
        cmd_knock_response(args)
    elif args.command == "prune-duplicates":
        cmd_prune_duplicates(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
