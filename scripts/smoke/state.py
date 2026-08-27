"""L0 + L1 — the ledger and what it is asked for.

The lexicon and learner state on disk, and everything that reads them to decide
what Andrew sees next: selection and its staleness term, the ordering law,
coverage, the slip ledger, the session log, cooldowns, and the ticket.

This is where the system's worst bugs have lived, and they share a shape: the
step ran, the meter read green, and its PURPOSE was not served. 45 of 70 deck
items never asked while cold/total reported a winning sprint; a record minted
without a phonetic, unreachable by the only key he can type. So the cases here
assert reachability and distribution over many draws, not a single call's
return value — s34's range(40) loop is the pattern the rest copy.
"""
import argparse
import importlib
import io
import json
import re
import sys
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path

from . import _fixtures as fx
from ._fixtures import (
    check, mechanism, read_json, REAL_BASE, write_json,
)


def s7_integrity(sb: Path):
    print("\n7. State integrity sweep")
    for f in sorted((sb / "progress").glob("*.json")):
        try:
            read_json(f)
            check(f"{f.name} valid JSON", True)
        except json.JSONDecodeError as e:
            check(f"{f.name} valid JSON", False, str(e))
    for e in read_json(sb / "progress" / "knock_log.json"):
        if not ("date" in e and "timestamp" in e):
            check("knock_log entries carry date+timestamp", False, str(e)[:80])
            break
    else:
        check("knock_log entries carry date+timestamp", True)


def s16_stale_clone_gates(sb: Path):
    print("\n16. Stale-clone gates + payload canon (regression 2026-07-15)")
    # A session opened on a clone 14 commits behind origin: re-collected a paid
    # field mission, missed the morning trailer, and the comma-joined soak payload
    # could never match an episode's words. The pure halves of the fixes:
    sys.path.insert(0, str(sb / "scripts"))
    ss = importlib.import_module("sync_state")
    sbf = importlib.import_module("session_brief")

    check("behind origin → STALE banner", "STALE" in (sbf.sync_banner((14, 0)) or ""))
    check("ahead only → unpushed warning", "not on origin" in (sbf.sync_banner((0, 1)) or ""))
    check("in sync → no banner", sbf.sync_banner((0, 0)) is None)
    check("sync unknown → soft warning", "SYNC UNKNOWN" in (sbf.sync_banner(None) or ""))

    check("comma-joined payload splits",
          ss.canon_payload(["frame:idum,பாத்துக்கறேன்"]) == ["frame:idum", "பாத்துக்கறேன்"])
    check("clean payload passes through",
          ss.canon_payload(["a", "b"]) == ["a", "b"])

    check("no record → unseen", fx.si.is_unseen({}))
    check("surfaced → not unseen", not fx.si.is_unseen({"last_surfaced": "2026-07-01"}))
    check("in an episode → not unseen", not fx.si.is_unseen({"seen_in": ["M60"]}))

    trailer = {"date": "2026-07-15", "move": "session bell trailer", "body": "ஆச்சு today"}
    volley = {"date": "2026-07-15", "move": "afternoon volley", "body": "…"}
    check("newest-knock trailer with no session after → unpaid",
          sbf.unpaid_trailer([volley, trailer], "2026-07-13") is trailer)
    check("session on/after trailer date → paid",
          sbf.unpaid_trailer([trailer], "2026-07-15") is None)
    check("newest knock not a trailer → nothing owed",
          sbf.unpaid_trailer([trailer, volley], "2026-07-13") is None)
    check("knocks_since filters to the gap",
          [k["date"] for k in sbf.knocks_since([{"date": "2026-07-10"}, {"date": "2026-07-14"}],
                                              "2026-07-13")] == ["2026-07-14"])


def s32_pool_rotation_and_coverage(mk, sb: Path):
    """Starvation (2026-07-25 audit). The selector ordered by tier -> ripeness ->
    alphabetical, with no staleness term — so the head of each tier was frozen
    and the tail never surfaced: 16 frames took 51 of 74 lifetime reps while 45
    of 70 fire items had never been asked once, and `cold/total` reported a
    winning sprint throughout because it counts progress and cannot see
    distribution. Ripeness-first was rich-get-richer (an item only becomes
    `hinted` by being worked, which promoted it again).

    Two mechanisms, both proven here: least-recently-worked sorts first WITHIN a
    tier (the tier prefix itself is the touchdown bar and must survive), and
    `register_coverage` counts worked/total so the tail is legible.

    REWRITTEN 2026-08-18 for the deck retirement. Every assertion below survives
    it — what changed is that `register` rides on the row instead of being joined
    from `curriculum/trip_deck.json` on `deck` membership, and one pool replaces
    the deck/floor pair. The fixture therefore carries NO `deck` tag: that is the
    point of the retirement, and a tier assertion that still needed one would be
    testing the container, not the ordering it left behind."""
    print("\n32. Pool rotation + coverage: the tail is not starved (2026-07-25)")
    st = importlib.import_module("suggest_targets")
    ss = importlib.import_module("sync_state")
    today = date_cls.today()

    def ago(n):
        return (today - timedelta(days=n)).isoformat()

    def item(reg, **kw):
        base = {"register": reg, "gloss": "x", "phonetic": [], "type": "chunk",
                "recognition": "struggled", "production": "none",
                "seen_in": [1], "last_surfaced": None}
        base.update(kw)
        return base

    lex = {
        # survival tier (antifreeze/frame/public), one row per starvation state
        "smoke:surv-hot": item("frame", type="pattern", production="hinted",
                               recognition="solid", last_surfaced=ago(2)),
        "smoke:surv-mid": item("antifreeze", recognition="comfortable", last_surfaced=ago(30)),
        "smoke:surv-tail": item("antifreeze"),                    # never worked, soaked
        "smoke:surv-unseen": item("public", seen_in=[]),          # never worked, never seen
        "smoke:surv-done": item("frame", type="pattern", production="cold",
                                recognition="solid", last_surfaced=ago(1)),
        "smoke:delight-new": item("social"),
        "smoke:dessert-new": item("gossip"),
        # ear-only: same law, and must never land in the fire tiers
        "smoke:ear-stale": item("gossip", direction="catch"),
        "smoke:ear-fresh": item("gossip", direction="catch",
                                recognition="comfortable", last_surfaced=ago(1)),
    }
    # The UNREGISTERED population (2026-07-26): rows with no register, which
    # degrade to delight. Both never-surfaced and identical on every other term,
    # so the ask count is the only thing that can separate them — and `-a` sorts
    # first alphabetically, which is what the old key fell through to.
    lex.update({
        "smoke:floor-a": {"gloss": "asked outside the cooldown", "phonetic": [], "type": "chunk",
                          "recognition": "comfortable", "production": "none",
                          "seen_in": [1], "last_surfaced": None},
        "smoke:floor-b": {"gloss": "never asked", "phonetic": [], "type": "chunk",
                          "recognition": "comfortable", "production": "none",
                          "seen_in": [1], "last_surfaced": None},
    })
    lex_path = sb / "progress" / "lexicon.json"
    klog_path = sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())
    # Yesterday's volley asked surv-tail as its SECOND item — `expected_target`
    # names only item 1, so items 2..n were invisible to the ask count while the
    # volley is the main volume channel.
    recent_ts = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
    # Derived from the constant, never a literal: this was `days=5`, which sat
    # outside the 3-day cooldown and INSIDE the 7-day one (2026-08-18), so
    # widening the window silently flipped an assertion about lifetime reps.
    old_ts = (datetime.now(timezone.utc)
              - timedelta(days=st.ASK_COOLDOWN_DAYS + 2)).isoformat()
    klog = [{"acted": True, "timestamp": recent_ts, "modality": "volley",
             "expected_target": "smoke:surv-mid", "body": "volley 1/2",
             "volley": [{"target": "smoke:surv-mid", "ask": "a"},
                        {"target": "smoke:surv-tail", "ask": "b"}]},
            {"acted": True, "timestamp": old_ts, "modality": "knock",
             "expected_target": "smoke:floor-a", "body": "the floor ask"}]
    try:
        write_json(lex_path, lex)
        write_json(klog_path, klog)

        asked = st.recent_ask_counts(klog, lex)
        check("a volley's later items count as asked, not just item 1",
              asked.get("smoke:surv-tail") == 1, f"got {asked}")
        check("the volley's opening item still counts",
              asked.get("smoke:surv-mid") == 1, f"got {asked}")

        # Ask-count breaks the tie the never-worked cohort sits in: surv-tail and
        # surv-unseen are both NEVER_SURFACED, and tail was asked.
        focus, _bg = st.floor_gap_targets(lex, today, 20, asked=asked, cohort=[])
        order = [t["word"] for t in focus]
        check("within the never-worked cohort, least-asked leads (not alphabetical)",
              order.index("smoke:surv-unseen") < order.index("smoke:surv-tail"), f"got {order}")
        check("ask-count stays subordinate to tier: an asked survival item still "
              "outranks an unasked dessert one",
              order.index("smoke:surv-tail") < order.index("smoke:dessert-new"), f"got {order}")
        # ── THE DISTRIBUTION PROPERTY — what the incident actually was ──────
        # Every assertion above is POINTWISE: one call, one pair compared. KF-12
        # was not a pair in the wrong order. It was 45 of 70 fire items never
        # asked once, across weeks, while cold/total reported a winning sprint —
        # and a selector can satisfy every ordering rule above and still starve
        # its tail, because starvation is a property of the SEQUENCE, not of any
        # single call. `s34` already tests its own ordering this way (its
        # `range(40)` loop); this is that shape, applied to the bug it was
        # written for. Feeding `asked` back in is what closes the loop: being
        # asked must move an item to the back of its own queue, or the head
        # freezes and the tail is never reached.
        #
        # WITHIN A TIER, deliberately. Tier order is the touchdown bar and must
        # survive — a dessert item legitimately waits while survival work is
        # outstanding, so a cross-tier fairness assertion would be testing the
        # opposite of the design. The starvation was always inside a tier: the
        # head frozen by ripeness-first (an item became `hinted` by being worked,
        # which promoted it again), the tail never surfacing.
        tier = ["smoke:surv-mid", "smoke:surv-tail", "smoke:surv-unseen"]
        turns = {}
        for _ in range(40):
            f, _b = st.floor_gap_targets(lex, today, 20, asked=dict(turns), cohort=[])
            for t in f[:2]:
                turns[t["word"]] = turns.get(t["word"], 0) + 1
        starved = [w for w in tier if not turns.get(w)]
        check("over 40 selections every item in the tier is reached — no starved tail",
              not starved, f"never asked once: {starved} (turns={turns})")
        hi, lo = max(turns.get(w, 0) for w in tier), min(turns.get(w, 0) for w in tier)
        check("...and the tier's turns are SHARED, not taken by its head",
              lo and hi <= lo * 1.5,
              f"head took {hi}, tail took {lo} — rich-get-richer is back ({turns})")

        check("the ask count rides on the item for the menu's warning",
              [t["asks"] for t in focus if t["word"] == "smoke:surv-tail"] == [1],
              f"got {focus}")
        check("the knock menu names the recent ask",
              "asked/shown 1×" in mk.due_menu_block(), f"got {mk.due_menu_block()}")
        # One owner: the knock channel no longer re-sorts, so its picks must be
        # the selector's own order.
        vt = [t["target"] for t in mk.volley_targets(n=4)]
        menu = [t["word"] for t in st.drill_menu(lex, today=today, asked=asked)]
        check("the volley reads the selector's order, it does not re-sort",
              [w for w in menu if w in vt] == vt, f"volley={vt} menu={menu}")
        check("recent_ask_counts has one home",
              not hasattr(mk, "recent_ask_counts"), "the knock-side copy survived")

        # THE 2026-07-26 defects, both halves. (1) The cooldown-as-coverage key
        # forgot floor-a's work on day 4 — that reset is why ~24 words cycled
        # forever while 110 of 134 were unreachable. (2) The knock rep counter
        # MINED Anna's prose for mentions — the same-day audit measured 100% of
        # live knock "reps" as mentions. Reps are DECLARED now: the judge seam
        # increments the lexicon counter per fired word (any verdict — partial
        # counts) and `rep_counts` reads that counter, never the log.
        kr = importlib.import_module("knock_reply")
        kr.apply_verdict({"fired": [{"word": "smoke:floor-a", "verdict": "hinted"}]},
                         {}, lex, [])
        check("a judged fired word increments the declared rep counter",
              lex["smoke:floor-a"].get("reps") == 1, f"got {lex['smoke:floor-a']}")
        reps = st.rep_counts(lex)
        mention = {"acted": True, "timestamp": recent_ts, "modality": "text",
                   "expected_target": "", "body": "Anna printed smoke:floor-b in prose"}
        check("a word PRINTED in a knock is a mention, never a rep",
              "smoke:floor-b" not in reps, f"got {reps}")
        check("the mention still feeds the reveal-cooldown — its one legitimate home",
              st.recent_ask_counts(klog + [mention], lex).get("smoke:floor-b") == 1,
              "the cooldown lost its probe matching")
        check("coverage counts LIFETIME reps, not the ask cooldown",
              reps.get("smoke:floor-a") == 1 and not asked.get("smoke:floor-a"),
              f"got {reps} / asked {asked}")
        focus, _bg = st.floor_gap_targets(lex, today, 20, asked=asked, reps=reps,
                                          cohort=[])
        order = [t["word"] for t in focus]
        check("the never-drilled word leads the drilled one (not alphabetical)",
              order.index("smoke:floor-b") < order.index("smoke:floor-a"), f"got {order}")
        check("the rep count rides on the item so the ticket can show it",
              [t["reps"] for t in focus if t["word"] == "smoke:floor-a"] == [1],
              "floor item lost its reps")
        check("the selector's default path reads the same declared counter",
              [t["word"] for t in st.floor_gap_targets(lex, today, 20, cohort=[])[0]] == order,
              "the default path disagrees with the injected one")
        # One law, one definition: the pool prefixes tier and then defers.
        check("the pool prefixes tier and then defers to the shared law",
              st.coverage_key({"word": "x", "reps": 0}) < st.coverage_key({"word": "x", "reps": 1})
              and st.pool_key({"word": "x", "reps": 0, "tier_rank": 0})
              < st.pool_key({"word": "x", "reps": 0, "tier_rank": 1}),
              "coverage_key does not lead with reps, or pool_key does not lead with tier")

        # Re-run the ordering laws with an empty log, so the coverage assertions
        # below read the same fixture the rest of the case was written against.
        write_json(klog_path, [])
        focus, _bg = st.floor_gap_targets(lex, today, 20, asked={}, cohort=[])
        order = [t["word"] for t in focus]

        # The regression: under the old key the ripe, recently-worked headliner
        # led its tier forever. Least-recently-worked now leads.
        check("a never-worked item outranks the ripe recently-worked headliner",
              order[0] == "smoke:surv-tail", f"got {order}")
        # Asserted on `drill_menu`, not the pool: surv-hot is a PATTERN, and the
        # pool has never held those (they are forced by producing a novel
        # instance, which is the Engines block's job). The menu is where the two
        # views meet, so it is where the two rows are comparable at all — and
        # dropping the assertion because the row moved would retire the
        # regression it exists for.
        hot = [t["word"] for t in st.drill_menu(lex, today=today, asked={})]
        check("the worked headliner falls behind the starved row of its tier",
              hot.index("smoke:surv-mid") < hot.index("smoke:surv-hot"), f"got {hot}")
        check("staleness beats ripeness, not tier: survival still precedes delight",
              order.index("smoke:surv-unseen") < order.index("smoke:delight-new"), f"got {order}")
        check("the touchdown bar survives: delight still precedes dessert",
              order.index("smoke:delight-new") < order.index("smoke:dessert-new"), f"got {order}")
        check("a cold item leaves the pending queue", "smoke:surv-done" not in order)

        # The ear starved worst of all (1 of 12 ever touched) — same law applies.
        ear = st.ear_targets(lex, today=today)
        catch_order = [t["word"] for t in ear["pending"]]
        check("the ear rotates too: the never-worked catch item leads",
              catch_order[0] == "smoke:ear-stale", f"got {catch_order}")
        check("the ear is never in the fire pool — a different axis, not a rival",
              not any(w.startswith("smoke:ear") for w in order), f"got {order}")

        # Rotation must not smuggle an UNSEEN item into a cold quiz (teach-first).
        vt = [t["target"] for t in mk.volley_targets(n=4)]
        check("rotation respects teach-first: UNSEEN stays out of the volley",
              "smoke:surv-unseen" not in vt, f"got {vt}")
        check("a never-worked but soaked item IS volley-eligible",
              "smoke:surv-tail" in vt, f"got {vt}")

        cov = st.register_coverage(lex, today=today)
        surv, delight, dessert = (cov["tiers"][t] for t in ("survival", "delight", "dessert"))
        check("survival coverage counts worked, not cold",
              (surv["touched"], surv["total"], surv["cleared"]) == (3, 5, 1),
              f"got {surv}")
        check("ear-only items never inflate a fire tier",
              dessert["total"] == 1, f"dessert={dessert}")
        check("the ear is metered on its own axis",
              (cov["catch"]["touched"], cov["catch"]["total"]) == (1, 2), f"got {cov['catch']}")
        check("a fully starved register is visible by name",
              cov["registers"]["public"]["untouched"] == 1
              and cov["registers"]["antifreeze"]["touched"] == 1,
              f"got {cov['registers']}")
        check("delight/dessert starvation is reported, not hidden",
              (delight["untouched"], dessert["untouched"]) == (1, 1),
              f"got {delight} {dessert}")
        # GENERALISED off the deck: unregistered rows get their own bucket rather
        # than swelling the tier they degrade into, where 256 of 339 would hide
        # exactly the distribution this block exists to show.
        check("unregistered rows are counted apart, not folded into delight",
              cov["unregistered"]["total"] == 2 and delight["total"] == 1,
              f"got unregistered={cov['unregistered']} delight={delight}")
        never = {u["word"] for u in cov["untouched"]}
        check("every never-worked ranked item is named",
              never == {"smoke:surv-tail", "smoke:surv-unseen",
                        "smoke:delight-new", "smoke:dessert-new", "smoke:ear-stale"},
              f"got {sorted(never)}")
        check("soaked-but-never-asked is distinguished from never-encountered",
              [u["soaked_only"] for u in cov["untouched"]
               if u["word"] == "smoke:surv-unseen"] == [False], f"got {cov['untouched']}")
        # A global deficit in a warm voice is guilt machinery (2026-07-17), and
        # this number is bigger and scarier than the burn rate that rule was
        # written for. Both surfaces that carry it must say so.
        import contextlib
        import io
        argv, out = sys.argv, io.StringIO()
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = argv
        check("the ticket marks coverage as an engineering number",
              "never narrated" in out.getvalue(), "coverage block carries no narration guard")
        # THE RETIREMENT ITSELF: no section may claim to outrank the others any
        # more. That primacy claim, times three, is what made a 361-line ticket
        # depend on which section Anna weighted that day.
        check("no pool claims primacy on the ticket",
              "force these before the general floor" not in out.getvalue()
              and "TRIP DECK" not in out.getvalue(), "a primacy headline survived")

        # The ear meter carries its own coverage count, so a green headline can
        # never again hide a starved ear.
        ce = ss.compute_ear(lex)
        check("the status meter carries the ear's coverage count",
              (ce["caught"], ce["total"], ce["untouched"]) == (0, 2, 1), f"got {ce}")
    finally:
        lex_path.write_bytes(saved[0])
        klog_path.write_bytes(saved[1])


def s33_catch_response_pairs(mk, sb: Path):
    """Catch-and-response is a first-class curriculum kind, and the schema had no
    way to say it (2026-07-26 audit). The pairing lived as English prose in
    `note`/`gloss` — "the maami's line at the table" — so nothing could drill a
    pair as a pair, and nothing noticed when `seed-deck` dropped the response
    while its prompt kept its slot. `pairs_with` is the one relation the schema
    carries; it must resolve inside the seed file, ride onto the lexicon, and
    reach both surfaces that show catch items.

    `seed-deck` outlived the trip deck (2026-08-18): curated-set seeding is
    useful for any future set, and only the *trip* framing retired. So this case
    keeps exercising it — and now also guards the field the retirement added,
    `register`, whose writer path this command is."""
    print("\n33. Catch/response pairs: hear X → say Y is representable (2026-07-26)")
    import contextlib
    import io
    st = importlib.import_module("suggest_targets")
    ss = importlib.import_module("sync_state")
    deck_file = sb / "curriculum" / "trip_deck.json"
    lex_path = sb / "progress" / "lexicon.json"
    saved = (deck_file.read_bytes(), lex_path.read_bytes())

    class Args:
        deck = "trip"

    def seed(entries):
        write_json(deck_file, entries)
        a = Args()
        a.file = str(deck_file)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ss.cmd_seed_deck(a)
        return buf.getvalue(), json.loads(lex_path.read_text(encoding="utf-8"))

    def ticket_text():
        argv, out = sys.argv, io.StringIO()
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = argv
        return out.getvalue()

    prompt = "இன்னும் கொஞ்சம் சாப்பிடுங்க"
    answer = "வேண்டாம்மா, வயிறு நிறைஞ்சிடுச்சு"
    paired = [
        {"tamil": prompt, "gloss": "eat more", "type": "chunk", "direction": "catch",
         "recognition": "struggled", "phonetic": ["innum konjam saapidunga"],
         "register": "mil-table", "pairs_with": answer},
        {"tamil": answer, "gloss": "no thanks, I'm full", "type": "chunk",
         "recognition": "struggled", "phonetic": ["vendaamma"],
         "register": "antifreeze"},
    ]
    try:
        write_json(lex_path, {})
        out, lex = seed(paired)
        check("the pair rides from the deck file onto the lexicon",
              lex[prompt].get("pairs_with") == answer, f"got {lex.get(prompt)}")
        check("the answer is a FIRE item — the catch half alone is not the win",
              lex[answer].get("direction") == "fire", f"got {lex.get(answer)}")
        # THE MIGRATION'S WRITER PATH (2026-08-18). The tier ordering outlived the
        # deck only because `register` reaches the ROW; if it stopped at the
        # curriculum file the ordering would be joined off a container that no
        # longer exists, which is the silent no-op the retirement was written to
        # avoid. `progress/*.json` is never hand-edited, so this command is the
        # only way that field can legitimately land.
        check("seed-deck lands the register on the lexicon row, not just the tag",
              lex[answer].get("register") == "antifreeze"
              and lex[prompt].get("register") == "mil-table", f"got {lex.get(answer)}")
        check("...and the ordering reads it back as the survival tier",
              st.tier_rank(lex[answer]) == 0 and st.tier_rank(lex[prompt]) == 1,
              f"got {st.tier_rank(lex[answer])}/{st.tier_rank(lex[prompt])}")

        ear = st.ear_targets(lex, today=date_cls.today())
        cp = [t for t in ear["pending"] if t["word"] == prompt]
        check("ear_targets resolves the pair for the drill",
              cp and cp[0]["pairs_with"] == answer and cp[0]["response_gloss"] == "no thanks, I'm full",
              f"got {cp}")
        check("the ticket names the answer under the line he'll hear",
              "he answers:" in ticket_text(), "the ear-only block hid the pair")
        check("the knock menu marks a paired item so Anna plays HER line",
              "[pair]" in mk.due_menu_block() and "never quiz the catch half alone" in mk.due_menu_block(),
              f"got {mk.due_menu_block()}")

        # THE regression: the response was dropped from the seed file while its
        # prompt stayed. Silent before, then a loud drop — a HARD seed-time
        # error now (2026-07-26): the seed is refused whole BEFORE any write,
        # so a split pair can never half-land. Fix the file, re-run.
        before = lex_path.read_bytes()
        try:
            seed([paired[0]])
            check("a split pair refuses the whole seed", False, "seed did not exit")
        except SystemExit as e:
            check("a split pair refuses the whole seed, loudly", e.code == 1,
                  f"exit code {e.code}")
        check("a refused seed writes NOTHING — no half-landed set",
              lex_path.read_bytes() == before, "lexicon changed on a refused seed")
    finally:
        deck_file.write_bytes(saved[0])
        lex_path.write_bytes(saved[1])


def s34_focus_and_background(sb: Path):
    """Two budgets, not one ranked list (Andrew, 2026-07-26: "10-15 getting most
    reps until they fire cold, the remaining on a slow guaranteed background").

    Coverage-first and dense-repetition genuinely conflict: one ranked list either
    touches every word once a month and graduates nothing, or hammers a dozen and
    lets the tail rot. The first attempt at the fix used a 3-day cooldown as the
    coverage term and reached 24 of 134 words in a simulated month, spending 100
    of 240 asks on ten words. Splitting the budget is what makes both hold."""
    print("\n34. Focus set + background: dense reps without starving the tail (2026-07-26)")
    st = importlib.import_module("suggest_targets")
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    klog_path = sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())
    today = date_cls.today()

    # 20 words, all recognized and none cold: more than the focus set can hold.
    lex = {f"smoke:w{i:02d}": {"gloss": f"w{i}", "phonetic": [], "type": "chunk",
                               "recognition": "comfortable", "production": "none",
                               "seen_in": [1], "last_surfaced": None,
                               **({"reps": 3} if i < 5 else {})}
           for i in range(20)}
    try:
        write_json(lex_path, lex)
        write_json(klog_path, [])
        # cohort=[] is the SEED path — no membership stored yet.
        focus, background = st.floor_gap_targets(lex, today, 99, cohort=[])
        fw = [t["word"] for t in focus]

        check("the focus set is capped at FOCUS_SIZE",
              len(focus) == st.FOCUS_SIZE, f"got {len(focus)}")
        check("everything else lands in background, nothing is dropped",
              len(focus) + len(background) == len(lex),
              f"{len(focus)}+{len(background)} != {len(lex)}")
        check("seeding gives words already started their focus seats",
              all(f"smoke:w{i:02d}" in fw for i in range(5)), f"got {fw}")
        check("open seats are filled from the never-drilled words",
              len([w for w in fw if not lex[w].get("reps")]) == st.FOCUS_SIZE - 5, f"got {fw}")
        check("the background is exposure-only and knows it",
              all(t["band"] == "background" for t in background), "band mislabelled")
        check("within the focus set the least-drilled lead, so the cohort advances together",
              [t["reps"] for t in focus] == sorted(t["reps"] for t in focus), f"got {fw}")

        # Membership is STORED STATE (2026-07-26): reconcile persists the seed,
        # and held seats then stand regardless of what any counter says —
        # a membership fact in a file cannot be reallocated by a counting bug.
        cohort = st.reconcile_focus(lex, [])
        check("reconcile seeds the same cohort the seed derivation shows",
              sorted(cohort) == sorted(fw), f"got {cohort}")
        noisy = {w: 99 for w in cohort}  # a corrupt counter must not move seats
        held = [t["word"] for t in st.floor_gap_targets(lex, today, 99, reps=noisy,
                                                        cohort=cohort)[0]]
        check("stored membership holds its seats against counter noise",
              sorted(held) == sorted(cohort), f"got {held}")

        # Graduation: cold leaves the cohort for good and the seat refills from
        # the background order — the ONLY way membership changes.
        lex["smoke:w00"]["production"] = "cold"
        cohort2 = st.reconcile_focus(lex, cohort)
        check("a word that fires cold leaves the cohort for good",
              "smoke:w00" not in cohort2, f"got {cohort2}")
        check("the other seats survive the graduation",
              set(cohort) - {"smoke:w00"} <= set(cohort2), f"got {cohort2}")
        focus2, bg2 = st.floor_gap_targets(lex, today, 99, cohort=cohort2)
        check("its seat is refilled from the background",
              len(focus2) == st.FOCUS_SIZE, f"got {len(focus2)}")
        check("the graduated word is gone from both budgets",
              "smoke:w00" not in [t["word"] for t in focus2] + [t["word"] for t in bg2],
              "a graduated word came back")

        # The tail must actually be reachable — the property the first fix lacked.
        # 6 drills + 2 exposures a day is Anna's pacing, not a code constant —
        # the property under test is that the ORDER spreads reps, at any pace.
        seen, reps = set(), {}
        for _ in range(40):
            f, b = st.floor_gap_targets(lex, today, 99, asked={}, reps=dict(reps),
                                        cohort=[])
            for t in f[:6]:
                seen.add(t["word"])
                reps[t["word"]] = reps.get(t["word"], 0) + 1
            # Exposure closes the loop through the REAL delivery seam
            # (sync_state.mark_exposed — the write every dose channel calls).
            # Without it the background order never changes and the SAME two
            # words are exposed forever: rotation is only guaranteed because
            # being exposed moves a word to the back of its own queue.
            for t in b[:2]:
                seen.add(t["word"])
                ss.mark_exposed(lex, [t["word"]], today=today.isoformat())
        check("every word is reachable — no word is stranded behind the alphabet",
              len(seen) == len(lex) - 1, f"reached {len(seen)} of {len(lex) - 1}")
        check("no word is hammered while others wait",
              max(reps.values()) - min(reps.values()) <= 2, f"spread {sorted(reps.values())}")
        check("the delivery stamp counts as well as dates",
              any(r.get("exposures") for r in lex.values()), "mark_exposed wrote no count")
        check("less-exposed sorts ahead of more-exposed — the 07-26 flip of `-soaked`",
              st.coverage_key({"word": "x", "exposures": 0})
              < st.coverage_key({"word": "x", "exposures": 3}),
              "coverage_key still rewards prior exposure")
    finally:
        lex_path.write_bytes(saved[0])
        klog_path.write_bytes(saved[1])


def s36_soak_order_carries_shape(sb: Path):
    """The soak order is a BRIEFING, not a word list (2026-07-27, Andrew: "soak
    is one flavour of briefing — why does learner.json need to change?").

    It didn't: nothing validates that file. What was broken is that `cmd_update`
    REBUILT the dict from three keys on every write, so any other key died at the
    next close — which is why the 2026-07-18 narrated_drama decision ("commissioned
    via soak order, form: …, scale: …") had no implementation anywhere in the repo.
    A shape could be decided in canon and never reach a renderer."""
    print("\n36. The soak order carries shape and focus, and no lane loops (2026-07-27)")
    import contextlib
    import io
    ss = importlib.import_module("sync_state")
    sbf = importlib.import_module("session_brief")

    def _capture(fn):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            fn(argparse.Namespace())
        return out.getvalue()

    learner_path = sb / "progress" / "learner.json"
    lex_path = sb / "progress" / "lexicon.json"
    saved = (learner_path.read_bytes(), lex_path.read_bytes())

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        for k, v in defaults.items():
            kw.setdefault(k, v)
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(argparse.Namespace(**kw))
        return read_json(learner_path).get("soak_order", {})

    try:
        write_json(lex_path, {"போறேன்": {"gloss": "I go", "phonetic": ["poren"],
                                         "type": "chunk", "recognition": "solid",
                                         "production": "cold", "seen_in": [],
                                         "last_surfaced": None}})
        learner = read_json(learner_path)
        learner["soak_order"] = {}
        write_json(learner_path, learner)

        order = update(soak_payload=["போறேன்"], soak_seed="s",
                       soak_focus="the -ஆச்சு tail over போ", soak_channel="soak")
        check("the order carries a focus", order.get("focus") == "the -ஆச்சு tail over போ")
        check("the order carries a channel", order.get("channel") == "soak")

        # THE BUG: a later close that touches only the payload used to rebuild the
        # dict down to three keys and silently drop everything else.
        order = update(soak_payload=["போறேன்"])
        check("a payload-only rewrite does not eat the focus",
              order.get("focus") == "the -ஆச்சு tail over போ", f"got {order}")
        check("a payload-only rewrite does not eat the channel",
              order.get("channel") == "soak", f"got {order}")

        # …and the inverse: setting a shape alone must not wipe the words.
        order = update(soak_focus="the -ல negative over முடி")
        check("a focus-only rewrite does not eat the payload",
              order.get("payload") == ["போறேன்"], f"got {order}")

        # And an unknown key survives, so the NEXT shape needs no writer change.
        learner = read_json(learner_path)
        # Deliberately a key that does NOT exist in canon. This fixture used to
        # be `scale: "long"`, which read as evidence that `scale` was real —
        # it never was (no writer, no reader; deleted 2026-08-05).
        learner["soak_order"]["not_a_real_key"] = "sentinel"
        write_json(learner_path, learner)
        check("an unnamed key survives a rewrite — the door is open",
              update(soak_payload=["போறேன்"]).get("not_a_real_key") == "sentinel")

        # A soak-channel order can never be cleared by the newest-EPISODE compare
        # (soak registers no episode), which is the 2026-07-23 M72/M73/M74
        # re-dispatch loop with a new trigger. Delivery clears it instead.
        write_json(sb / "progress" / "episodes.json", {})
        status = _capture(sbf.cmd_status)
        check("an undelivered soak order routes to the soak lane, not the studio",
              "render_soak.py" in status and "run_studio.py" not in status, status[:400])
        check("the rendering lane's own stamp clears it — no second dispatch",
              ss.mark_soak_delivered("soak")
              and "produced ✓" in _capture(sbf.cmd_status))

        # The shape that hung a real order through a SUCCESSFUL render: a
        # Tamil-script payload word that is legitimately pre-lexicon. It passes
        # split_payload by design, but mark_exposed can only stamp rows that
        # exist, so any last_surfaced-based check waits on it forever.
        learner = read_json(learner_path)
        learner["soak_order"]["payload"] = ["நிறைஞ்சிடுச்சு"]   # not in this lexicon
        write_json(learner_path, learner)
        res, unres = fx.si.split_payload(["நிறைஞ்சிடுச்சு"], read_json(lex_path))
        check("a pre-lexicon Tamil payload word is resolvable, not junk",
              res == ["நிறைஞ்சிடுச்சு"] and not unres, f"{res} / {unres}")
        check("...and a delivered order still clears with one in the payload",
              "produced ✓" in _capture(sbf.cmd_status))

        # A stamp from ANOTHER lane must not clear this one.
        ss.mark_soak_delivered("drill")
        check("a stamp from a different lane does not clear a soak order",
              "NOT YET PRODUCED" in _capture(sbf.cmd_status))
        ss.mark_soak_delivered("soak")

        # A NEW order supersedes an old delivery — `from` moves, the stamp doesn't.
        update(soak_payload=["போறேன்"])
        check("a freshly-set order is pending again despite the old stamp",
              "NOT YET PRODUCED" in _capture(sbf.cmd_status))
        ss.mark_soak_delivered("soak")

        # The reader half: the brief only reaches the sheet on the soak channel.
        rs = importlib.import_module("render_soak")
        rs_focus, rs_payload = rs.soak_brief()
        check("render_soak reads the order's focus",
              rs_focus == "the -ல negative over முடி", f"got {rs_focus!r}")
        check("a focused sheet gets the carousel brief",
              "CAROUSEL" in rs.FOCUS_BRIEF and "stays out" in rs.FOCUS_BRIEF)

        # A lane that ignores its payload can never satisfy the order that
        # dispatched it — that is the re-dispatch loop arriving through the door.
        check("the ordered words lead the menu even when the week-window missed them",
              [r["word"] for r in rs.with_payload([], rs_payload)] == ["போறேன்"])
        check("an ordered word already in the menu is not duplicated",
              len(rs.with_payload([{"word": "போறேன்", "gloss": "", "production": "cold",
                                    "last_surfaced": None}], rs_payload)) == 1)

        update(soak_payload=["போறேன்"], soak_channel="episode")
        check("an episode-channel order does NOT hijack the soak lane",
              rs.soak_brief() == (None, []))

        # --- The commissioned form: doctrine since 2026-07-18, wired 2026-07-27 ---
        st = importlib.import_module("suggest_targets")
        check("the divergence gate cannot roll a commissioned form by itself",
              all(f not in st.FORMS for f in st.COMMISSIONED_FORMS))
        check("ALL_FORMS is the one palette the CLI and the gate share",
              set(st.ALL_FORMS) == set(st.FORMS) | set(st.COMMISSIONED_FORMS))

        order = update(soak_form="narrated_drama")
        check("the order carries a commissioned form", order.get("form") == "narrated_drama")
        check("suggest_targets reads it back", st.commissioned_form() == "narrated_drama")

        sidecars = [{"mission": 70, "register": "dread", "episode_form": "classic",
                     "dramatic_ingredient": list(st.INGREDIENTS)[0]}]
        spec = st.scene_spec(sidecars, st.commissioned_form())
        check("a commissioned form overrides the gate", spec["form"] == "narrated_drama")
        check("and says so, so the Director does not re-pick", spec["commissioned"])
        check("register still diverges — commissioning a form costs no other variety",
              spec["register"] != "dread")
        check("an uncommissioned spec stays inside the rotated palette",
              st.scene_spec(sidecars)["form"] in st.FORMS
              and not st.scene_spec(sidecars)["commissioned"])

        # A typo must not steer the Director off-palette, and must never mean
        # "no episode" — the order still dispatches, the gate just rolls.
        learner = read_json(learner_path)
        learner["soak_order"]["form"] = "narrated_dramaa"
        write_json(learner_path, learner)
        with contextlib.redirect_stdout(io.StringIO()) as warned:
            bad = st.commissioned_form()
        check("an unbuildable form is ignored, not obeyed", bad is None)
        check("...and says so out loud rather than failing silently",
              "cannot build" in warned.getvalue(), warned.getvalue())

        update(soak_form="narrated_drama", soak_channel="soak")
        check("a form on a non-episode order does not reach the studio",
              st.commissioned_form() is None)
    finally:
        learner_path.write_bytes(saved[0])
        lex_path.write_bytes(saved[1])


def s37_repair_earns_the_dose(sb: Path):
    """The repair earns the dose (2026-07-28, Andrew's spoken felt signal:
    "I don't feel like Anna is commissioning enough audio, and specifically
    audio to close the gap in the mistakes I'm making... I shouldn't have to
    beg for a soak or an episode").

    The system had a channel-ROUTING law (audio_channels.md) and a PRODUCTION
    law (studio.md) and NO COMMISSIONING law: nothing said which gaps earn a
    dose. Close & Log step 2 was a menu ("payload... MAY be a seed order"), so
    the campaign's forward pull outranked the backward repair need and his
    errors went undosed — pakkathula reached the order as one of three items
    and the collision was still open hours later.

    This is a PROSE rule, so a prose lint is its only regression net. The
    2026-07-24 lesson (a dropped rule must be hunted in code, prompts, skills
    and tests) applies in reverse: assert every surface that carries it."""
    print("\n37. The repair earns the dose — commissioning is a priority (2026-07-28)")
    # The law lived in audio_channels.md from 07-28 and moved to its own file on
    # 2026-08-01 when the refused-in-advance third raise came due — "what a dose
    # carries" and "which channel carries it" are two files now, each pointing
    # at the other. Close & Log keeps a pointer, because that is where it fires.
    routing = (REAL_BASE / "protocol" / "commissioning.md").read_text(encoding="utf-8")
    check("the commissioning law exists", "repair earns the dose" in routing)
    check("...and it is an ORDER of precedence, not a menu",
          "Backward beats forward" in routing)
    # The repair population used to be enumerated in prose ("hinted, recast, or
    # corrected and still came out wrong") and scoped to "the day's" repairs —
    # which meant the chat session's own day, so a mistake made on the phone was
    # never in the draw at all (2026-07-30 audit: the same recast shipped 07-08,
    # 07-25 and 07-30). The population is now the slip ledger, which is that
    # enumeration made durable and cross-lane.
    check("...drawing the payload from the ledger, not one session's memory",
          "live slips" in routing and "sync_state.py slips" in routing)
    check("...and the ledger spans every lane, not just the day's session",
          "every* lane" in routing or "every lane" in routing)
    check("...and he never has to ask for it", "never has\nto ask" in routing
          or "never has to ask" in routing)
    check("a survived collision earns its own order, not a share of a mixed one",
          "earns its own order" in routing)
    # 2026-07-28 evening, Andrew: "using them in context can be very effective for
    # sticking in my brain... it shouldn't be the only choice when I'm struggling
    # regardless of whether two words sound similar." The scope rule had a format
    # clause welded to it ("a chunk fires it") and a chunk is what the soak loop
    # makes — so the rule read as "every mix-up gets the loop". Scope and format
    # are now separate questions, and format follows the ERROR, not the collision.
    check("the collision rule no longer prescribes a format",
          "chunk fires it" not in routing)
    check("...it says so explicitly, so the clause cannot grow back",
          "says nothing about its format" in routing)
    channels = (REAL_BASE / "protocol" / "audio_channels.md").read_text(encoding="utf-8")
    check("format follows the error, and capacity keeps its veto",
          "Capacity vetoes" in channels and "the ERROR chooses" in channels)
    check("...naming the mouth-takes-the-wrong-one case as an EPISODE, not a loop",
          "his mouth takes the wrong one" in channels)
    check("a repeated mistake escalates the format instead of repeating it",
          "same mistake twice through one format" in channels
          and "never loop harder" in channels)
    check("the forward seed order survives as the fallback, not the default",
          "seed order" in routing and "Only when none are live" in routing)
    check("the escalation law names the counter that makes it fireable",
          "ledger counts recurrences" in channels)
    check("the two halves are two files, each pointing at the other (08-01 split)",
          "audio_channels.md" in routing and "commissioning.md" in channels)

    session = (REAL_BASE / "protocol" / "daily_session.md").read_text(encoding="utf-8")
    # The PRIORITY must be stated where the order is actually set — a pointer
    # alone would make the loop depend on Anna following a link mid-close. The
    # wording moved to the ledger's vocabulary on 2026-07-30 ("live slips draw
    # first" IS backward-beats-forward); the duplicated law behind it was
    # retired to a pointer, so assert the rule and the owner, not the phrasing.
    check("Close & Log fires the rule at the moment the order is set",
          "repair earns the dose" in session and "Live slips draw first" in session)
    check("...and points at the file that owns it", "audio_channels.md" in session)
    check("...and says an unverified slip is a check, not a commission",
          "checks, not commissions" in session)

    # The glossary is what a new engineer reads before touching the interface.
    glossary = (REAL_BASE / ".claude" / "skills" / "orient" / "references"
                / "glossary.md").read_text(encoding="utf-8")
    check("the glossary carries the priority too", "repair earns the dose" in glossary)

    # A retry that does not exist is worse than no retry: it makes a dropped
    # dose look covered. The local cron was retired 2026-07-24.
    anna_skill = (REAL_BASE / ".claude" / "skills" / "anna"
                  / "SKILL.md").read_text(encoding="utf-8")
    check("Anna's skill does not promise a cron retry that was retired",
          "hourly local cron) retries any miss" not in anna_skill)


def s38_teach_enters_the_lexicon(sb: Path):
    """A word taught in-session can now exist (2026-07-28).

    The pakkam/paakkalaam deep-dive taught பக்கத்துல, ஆச்சு and இருக்கேன் and
    recorded none of them: --mastered/--comfortable overstate a first contact,
    --stuck-word and --mark-seen refuse an absent key, and seed-deck is a
    deck-authoring flow. So the live teaching surface wrote nothing, the next
    ticket could not know, and a queued soak order named a word the lexicon had
    never heard of. This is the write-side twin of the 07-27 credit-the-word-he-
    said fix: that taught the judge to credit a substitution, this lets a taught
    word exist at all."""
    print("\n38. A word taught in-session enters the lexicon (2026-07-28)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    lex_path, learner_path = sb / "progress" / "lexicon.json", sb / "progress" / "learner.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes())

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        return read_json(lex_path), out.getvalue()

    try:
        # The |phonetic tail became mandatory on a NEW word 2026-08-14 (s59) —
        # a record minted without one can never be logged from chat again.
        word = "பக்கத்துல"
        lex, _ = update(teach=[f"{word}=beside/next to|pakkathula"])
        rec = lex.get(word)
        check("a taught word is created", rec is not None, "still absent")
        check("...at struggled recognition, not solid",
              rec and rec["recognition"] == "struggled", f"got {rec}")
        check("...with production unset, so the floor cannot inflate",
              rec and rec["production"] == "none", f"got {rec}")
        check("...carrying the gloss", rec and rec["gloss"] == "beside/next to")
        check("...and seen today", rec and rec["last_surfaced"] == ss.local_today().isoformat())

        # Teaching runs before the axes, so teach-then-fire in ONE close resolves.
        lex, _ = update(teach=["ஆச்சு=it happened / it's done|aachu"], produced_cold=["ஆச்சு"])
        check("a word taught and fired in the same close is credited",
              lex["ஆச்சு"]["production"] == "cold", f"got {lex.get('ஆச்சு')}")

        # Re-teaching must not silently demote a word he already owns.
        lex, _ = update(teach=[word])
        check("re-teaching a known word does not reset its recognition",
              lex[word]["recognition"] == "struggled", f"got {lex[word]}")
        lex, out = update(teach=["pakkathula"])
        check("a phonetic teach is refused, so keys stay canonical",
              "pakkathula" not in lex and "phonetic" in out)
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])


def s41_slip_ledger(kr, sb: Path):
    """Mistakes accumulate, cross lanes, and reach the next lesson (2026-07-30).

    The audit that produced this: 'romba nalla irukku' → 'irundhuchu' was pushed
    back on 07-08, 07-25 and 07-30, near-verbatim, and nothing in the system
    could notice. Three independent holes, one per direction of the loop:

    1. CAPTURE — the diagnosis existed only as prose in knock_log's reply_line.
       The synthesis lived in learner.last_debrief, a single string OVERWRITTEN
       every close, so an error survived exactly as long as Anna retyped it.
    2. CREDIT — apply_verdict is upgrade-only on the phone, and the 07-30 volley
       scored ரொம்ப நல்லா இருக்கு as a hinted FIRE off a reply whose own recast
       corrected its tense. A wrong answer moved the axis and took a rep.
    3. RESURFACE — reply_line was read back only by the reveal-window and
       deck-coverage scans. Nothing on the status digest or the ticket said what
       he keeps getting wrong, so selection re-offered the item and the scene
       re-asked it the same way.
    """
    print("\n41. The slip ledger — errors accumulate and steer the next lesson (2026-07-30)")
    sl = importlib.import_module("slips")
    st = importlib.import_module("suggest_targets")
    slip_path = sb / "progress" / "slip_log.json"
    if slip_path.exists():
        slip_path.unlink()

    # --- 2. credit: a corrected item is not a fire -----------------------------
    d = kr.normalize_verdict(
        {"verdict": "hinted",
         "fired": [{"word": "ரொம்ப நல்லா இருக்கு", "said": "Romba nalla irukku",
                    "verdict": "hinted"}],
         "slips": [{"tag": "past-tense", "said": "irukku",
                    "want": "ரொம்ப நல்லா இருக்கு", "note": "present for a past scene"}],
         "reply_line": "x"},
        "Market ku ponnam, Romba nalla irukku")
    check("a word corrected in the same breath is not credited", d["fired"] == [])
    check("...and the headline degrades rather than celebrating", d["verdict"] == "miss")
    check("...and the drop is loud, not silent",
          any("corrected in the same breath" in u for u in d["unverified"]))
    d = kr.normalize_verdict(
        {"verdict": "cold",
         "fired": [{"word": "ஒரு நிமிஷம்", "said": "Oru nimsham", "verdict": "cold"}],
         "slips": [{"tag": "stranger-nga", "said": "pesa", "want": "pesunga", "note": "n"}],
         "reply_line": "x"}, "Oru nimsham")
    check("an unrelated slip does not cost him a clean fire",
          [i["word"] for i in d["fired"]] == ["ஒரு நிமிஷம்"] and d["verdict"] == "cold")
    check("a slip with no tag cannot enter the ledger",
          kr.normalize_verdict({"verdict": "chat", "slips": [{"said": "x", "want": "y"}]},
                               "")["slips"] == [])

    # --- 1. capture: append-only, cross-lane, dated by when it happened --------
    sl.append_slips([{"tag": "Past tense", "said": "irukku", "want": "irundhuchu",
                      "note": "present for a past scene"}],
                    lane="knock", when="2026-07-25")
    sl.append_slips([{"tag": "past-tense", "said": "irukku", "want": "irundhuchu",
                      "note": "present for a past scene"}],
                    lane="chat", when="2026-07-30")
    rows = read_json(slip_path)
    check("the ledger is append-only — the second write keeps the first", len(rows) == 2)
    check("...and tag casing/punctuation collapses to one pattern",
          {r["tag"] for r in rows} == {"past-tense"})
    check("...and each row keeps the lane it came from",
          {r["lane"] for r in rows} == {"knock", "chat"})
    pats = {p["tag"]: p for p in sl.slip_patterns(today=date_cls(2026, 7, 30))}
    p = pats["past-tense"]
    check("a mistake made twice is a pattern, not a one-off", p["pattern"] and p["count"] == 2)
    check("...spanning the real days it happened on, not the day it was written",
          p["span_days"] == 5 and p["first"] == "2026-07-25")
    check("...and it crosses lanes — the phone and the table are one history",
          sorted(p["lanes"]) == ["chat", "knock"])
    check("a pattern nothing was ever built for is NOT told to change format",
          p["uncommissioned"] and not p["escalate"])

    # A dose was commissioned and he slipped anyway — that is the escalation the
    # audio_channels law describes, and it could not fire before this counter.
    #
    # FIXTURE CORRECTED 2026-08-20. This used to express "a dose was
    # commissioned" as `dose_channel="soak"` on the slip row. That is a
    # different fact — dose_channel records that SOME order was standing when
    # the slip happened, for some other payload — and feeding it into
    # `channels` is the bug that disarmed both gates for three weeks. The
    # assertion below was always right; the way it staged the world was not.
    # "A dose was commissioned for THIS tag" has exactly one spelling:
    sl.record_slip_commission(["past-tense"],
                              {"channel": "soak", "payload": ["irundhuchu"]},
                              today="2026-07-29")
    sl.append_slips([{"tag": "past-tense", "said": "irukku", "want": "irundhuchu"}],
                    lane="knock", when="2026-07-30")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 7, 30))}["past-tense"]
    check("a slip that survived a dose escalates the FORMAT",
          p["escalate"] and p["channels"] == ["soak"])

    # --- retire → verify → revive: the surface forgets, then ASKS AGAIN --------
    # Andrew, 2026-07-30: "words shouldn't disappear into the aether. They should
    # be retired and then come back." Retiring on the clock alone cannot tell
    # "he learned it" from "nothing ever asked him", so a retired slip that was
    # never confirmed landed comes back as a CHECK rather than vanishing.
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 9, 30))}["past-tense"]
    check("a long-quiet slip stops being live evidence", not p["live"])
    check("...but its history is still on the record", p["count"] == 3)
    check("...and it does NOT vanish — it returns as an unverified check",
          p["unverified"] and not p["closed"])
    block = "\n".join(sl.format_slip_block([p]))
    check("...which the reader surface asks for by name",
          "UNVERIFIED" in block and "past-tense" in block)
    check("...and an unverified slip is a check, not a commission",
          "not a dose" in block.lower() or "worth a check" in block.lower())

    # Closing is an OBSERVATION and it is DATED. The bare-tag list this replaced
    # silenced a pattern permanently — muting the most informative event the
    # ledger can record: one you believed had landed, coming back.
    out = sl.record_slip_test(["past-tense:landed"], today="2026-09-30")
    check("a landed test closes the slip as of that date",
          out and out[0][1] == "landed")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 10, 1))}["past-tense"]
    check("...and a closed slip stops surfacing entirely",
          p["closed"] and not p["unverified"] and sl.format_slip_block([p]) == [])
    check("...but the close is dated, not permanent", p["closed_on"] == "2026-09-30")

    sl.append_slips([{"tag": "past-tense", "said": "irukku", "want": "irundhuchu"}],
                    lane="knock", when="2026-11-02")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 11, 2))}["past-tense"]
    check("A CLOSED SLIP THAT COMES BACK IS LIVE AGAIN — the close is voided",
          p["live"] and not p["closed"] and p["reopened"])
    check("...with its whole history intact, not restarted at one", p["count"] == 4)

    # A failed test is itself a recurrence — one ledger, not a parallel record.
    sl.record_slip_test(["past-tense:missed"], today="2026-11-03")
    p = {x["tag"]: x for x in sl.slip_patterns(today=date_cls(2026, 11, 3))}["past-tense"]
    check("a failed test lands on the ledger as a recurrence",
          p["count"] == 5 and p["live"])
    check("a malformed test report is rejected, not guessed at",
          sl.record_slip_test(["nonsense"])[0][1] == "bad")

    # --- 3. resurface: status, and the ticket that picks the next lesson -------
    block = "\n".join(sl.format_slip_block(sl.slip_patterns(today=date_cls(2026, 7, 30))))
    check("the digest names the pattern, not just that a reply happened",
          "past-tense" in block and "irundhuchu" in block)
    check("...and says a recast does not close it",
          "closed by firing right" in block)

    src = mechanism((REAL_BASE / "scripts" / "session_brief.py").read_text(encoding="utf-8"))
    check("the session digest shows what Anna CORRECTED on the phone",
          "corrected: " in src)
    # The string this used to grep for — `commit_paths.append(SLIP_LOG_PATH)` —
    # was one of the twenty-six hand-built commit lists that publish.publish
    # retired (2026-08-23). The PROPERTY is untouched and is what is asserted:
    # the reply lane names the slip ledger among the paths it hands to the
    # commit, conditioned on the verdict actually carrying slips.
    check("the knock reply commits the ledger — an unpushed slip dies with the runner",
          'SLIP_LOG_PATH if verdict.get("slips")' in
          mechanism((REAL_BASE / "scripts" / "knock_reply.py").read_text(encoding="utf-8")))

    # The ticket hangs the slip off the item it belongs to, so a selected word
    # arrives with HOW it keeps failing, not just that it is due.
    # An explicit key, not one scraped from the sandbox lexicon: the linkage under
    # test is slip → row, and it must hold whether or not the want resolves.
    key = "frame:day-recap"
    sl.append_slips([{"tag": "ending", "said": "ponnam", "want": "ponnom", "word": key,
                      "note": "the ending"}], lane="knock", when="2026-07-30")
    hung = st.slips_by_word(sl.slip_patterns(today=date_cls(2026, 7, 30)))
    check("a slip attaches to the lexicon row it is about", key in hung)
    check("...and annotates it with what he actually said",
          "SLIPPED" in st.slip_note(hung[key]))
    check("a single slip still annotates an item already selected",
          "once" in st.slip_note(hung[key]))

    slip_path.unlink()


def s39_ticket_carries_the_commission(sb: Path):
    """The episode lane must CONSUME the commission (2026-07-28, first real
    exercise of the repair-first law).

    frame:youknow-la was commissioned as an episode; M77 came back drilling the
    computed FOCUS SET with the payload absent. Cause: the ticket had no
    commission section at all. The order reached the Director only as one prose
    clause in DIRECTOR ("read the soak-order in progress/learner.json") — an
    agentic read competing with a code-assembled list headed "DRILL these until
    they fire cold" — and lost. In the SAME run the commissioned FORM landed
    perfectly, because it arrived through scene_spec() as computed context.

    That is the repo's own doctrine failing in the direction it predicts:
    code-assembled context beats an agentic read when the invariant is known.
    So the payload arrives the way the form does."""
    print("\n39. The ticket carries the commission, ahead of the focus set (2026-07-28)")
    import contextlib, io
    st = importlib.import_module("suggest_targets")
    learner_path = sb / "progress" / "learner.json"
    saved = learner_path.read_bytes()

    order = {"payload": ["frame:youknow-la"], "scene_seed": "Two aunties on the phone.",
             "focus": "The -ல tag as THE gossip opener.", "from": "2026-07-28",
             "channel": "episode", "form": "phone_call"}

    def ticket(o):
        learner = read_json(learner_path)
        if o is None:
            learner.pop("soak_order", None)
        else:
            learner["soak_order"] = o
        write_json(learner_path, learner)
        argv, out = sys.argv, io.StringIO()
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = argv
        return out.getvalue()

    try:
        text = ticket(order)
        check("the commissioned payload is IN the ticket, not left to an agentic read",
              "frame:youknow-la" in text.split("FOCUS SET")[0], text[:400])
        check("...with the focus that says what the dose is for",
              order["focus"] in text)
        check("...and the scene seed", order["scene_seed"] in text)
        check("...headed so it cannot be read as one more list",
              "THE COMMISSION" in text and "OUTRANKS" in text)
        check("the focus set says out loud that it is outranked",
              "A COMMISSION IS LIVE" in text.split("FOCUS SET")[1])
        check("the form is still pinned by the same order",
              "COMMISSIONED by the soak order" in text)

        # A consumed order must not keep steering the next episode. Before this,
        # commissioned_form() ignored `delivered` entirely.
        done = ticket({**order, "delivered": {"channel": "episode", "at": "2026-07-28"}})
        check("a delivered order stops commanding the ticket",
              "THE COMMISSION" not in done)
        check("...and stops pinning the form, so the divergence gate rolls again",
              "COMMISSIONED by the soak order" not in done)

        # The episode lane never stamps `delivered` — it clears itself by
        # registering the payload into episodes.json. Reading only the stamp
        # would leave a filled order commanding every future ticket, which is
        # the 07-23 three-episodes-in-one-evening failure wearing a new hat.
        eps_path = sb / "progress" / "episodes.json"
        saved_eps = eps_path.read_bytes()
        try:
            eps = read_json(eps_path)
            newest = str(max((int(k) for k in eps), default=0) + 1)
            eps[newest] = {"title": f"Mission {newest}",
                           "words": ["frame:youknow-la"], "duration_min": 1.6,
                           "produced": "2026-07-28"}
            write_json(eps_path, eps)
            carried = ticket(order)
            check("an order the newest episode already carries is no longer live",
                  "THE COMMISSION" not in carried)
            check("...and the divergence gate takes the form axis back",
                  "COMMISSIONED by the soak order" not in carried)
        finally:
            eps_path.write_bytes(saved_eps)

        soaked = ticket({**order, "channel": "soak", "delivered": None})
        check("an order routed elsewhere does not command the episode ticket",
              "THE COMMISSION" not in soaked)
        empty = ticket({"payload": [], "channel": "episode"})
        check("an empty order is not a commission", "THE COMMISSION" not in empty)
        check("no order at all still builds a ticket",
              "SESSION TICKET" in ticket(None))
    finally:
        learner_path.write_bytes(saved)


def s44_a_commission_can_discharge_the_flag(sb: Path):
    """NEVER COMMISSIONED could only ever be cleared by FAILING again (2026-07-31).

    `uncommissioned` read `agg["channels"]`, fed by `dose_channel` — stamped onto
    a slip ROW at the instant it is written, from whatever soak order happened to
    be standing. So the flag answered "has he ever slipped while SOME order
    stood", never "was a dose built for THIS". Nothing anywhere associated a
    commission with a tag, so building the right dose could not clear it and only
    a fresh slip could: cleared by failing, ignored by fixing. Proof on the day it
    was found — the போனோம் episode shipped and read `produced ✓` while both slips
    it was built for still printed the warning, permanently. A warning that can
    never be discharged becomes noise you learn to read past, which is the
    mechanical reason it was walked past rather than agent inattention.

    Andrew's option A: the close DECLARES which debt an order pays. Python cannot
    infer it — a payload word and a slip tag are different vocabularies, and the
    slips that most need a dose (1pl-past-om, past-tense) hang off no single word.

    The second bug, found wiring the first and far worse: `write_thin_learner` is
    a WHITELIST, and `slip_closes` was not on it. So `--slip-tested tag:landed`
    wrote a close and the very same close's update DELETED it. No slip had ever
    actually closed since the mechanism shipped 2026-07-30, and nothing surfaced
    the loss, because a wiped close looks exactly like never having tested."""
    print("\n44. A commissioned dose discharges the flag; a close survives (2026-07-31)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    sl = importlib.import_module("slips")
    learner_path = sb / "progress" / "learner.json"
    slip_path = sb / "progress" / "slip_log.json"
    saved = (learner_path.read_bytes(),
             slip_path.read_bytes() if slip_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[])

    def update(**kw):
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))

    def pat(tag):
        return {p["tag"]: p for p in sl.slip_patterns()}.get(tag)

    try:
        slip_path.write_text("[]", encoding="utf-8")
        learner = read_json(learner_path)
        for k in ("slip_closes", "slip_commissions"):
            learner.pop(k, None)
        write_json(learner_path, learner)

        # A pattern: same mistake twice, nothing ever built for it.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "smoke-tag", "said": "x", "want": "y"}],
                            lane="chat", when="2026-01-01")
            sl.append_slips([{"tag": "smoke-tag", "said": "x", "want": "y"}],
                            lane="chat", when=ss.local_today().isoformat())
        p = pat("smoke-tag")
        check("a twice-made mistake with no dose reads NEVER COMMISSIONED",
              p and p["uncommissioned"], f"got {p and p.get('uncommissioned')}")
        check("...and the surface names the flag that would clear it",
              any("--slip-commissioned smoke-tag" in ln
                  for ln in sl.format_slip_block([p])), "the instruction is missing")

        # Commissioning WITHOUT an order standing must refuse, not book a lie.
        # (The 08-01 gate would refuse this whole close — a declared tag with no
        # order does not cover the debt — so the override rides along; the gate
        # itself is s46's subject.)
        update(slip_commissioned=["smoke-tag"],
               no_commission="smoke: exercising the phantom-dose refusal")
        check("a commission with no standing order is refused",
              pat("smoke-tag")["uncommissioned"], "it booked a phantom dose")

        # The real path: set the order and name its debt in ONE close.
        update(soak_payload=["ஸ்மோக்பேலோடு"], soak_channel="episode",
               slip_commissioned=["smoke-tag"])
        p = pat("smoke-tag")
        check("declaring the debt in the same close clears the flag",
              not p["uncommissioned"], "still NEVER COMMISSIONED")
        check("...recording which lane carried it",
              p["commissions"] and p["commissions"][-1]["channel"] == "episode",
              f"got {p['commissions']}")
        check("...and the surface reports the dose instead of the warning",
              any("dose commissioned" in ln for ln in sl.format_slip_block([p]))
              and not any("NEVER COMMISSIONED" in ln for ln in sl.format_slip_block([p])))
        check("...but it does NOT accuse the new dose of having failed",
              not p["escalate"], "escalated on evidence that predates the dose")

        # It survives the next ordinary close — the whitelist bug.
        update(produced_cold=[], debrief="a later close")
        check("the commission survives a later update",
              not pat("smoke-tag")["uncommissioned"], "the whitelist ate it")

        # Only a slip DATED AFTER the dose escalates.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "smoke-tag", "said": "x", "want": "y"}],
                            lane="chat", when="2099-01-01")
        check("a slip made AFTER the dose escalates the format",
              pat("smoke-tag")["escalate"], "escalation never fired")

        # A tag with no history is a typo, not a debt.
        update(soak_payload=["ஸ்மோக்பேலோடு"], soak_channel="soak",
               slip_commissioned=["no-such-tag-at-all"])
        check("an unknown tag cannot be booked as commissioned",
              "no-such-tag-at-all" not in sl.slip_commissions(), "a typo booked a debt")

        # --- the whitelist bug, on the mechanism it actually broke -------------
        with contextlib.redirect_stdout(io.StringIO()):
            sl.record_slip_test(["smoke-tag:landed"])
        check("a close is recorded", sl.slip_closes().get("smoke-tag"))
        update(debrief="the close that used to erase it")
        check("...and SURVIVES the update that follows it",
              sl.slip_closes().get("smoke-tag"), "write_thin_learner deleted the close")
    finally:
        learner_path.write_bytes(saved[0])
        if saved[1] is not None:
            slip_path.write_bytes(saved[1])
        else:
            slip_path.unlink(missing_ok=True)


def s42_session_log_one_row_per_day(sb: Path):
    """A close is one session however many update calls it takes (2026-07-31).

    The momentum log appended unconditionally, so every extra `update` in a close
    forged a session — repairing a bad key, or setting the soak order in a second
    command, each minted a row. By 2026-07-31 it held 38 rows for 26 real
    session-days: 12 duplicated dates, the counter ~46% high, and show_status's
    last-5 view padded with near-empty rows. The quiet half is worse than the
    cosmetic one: cold_fires_recent() and fires_today() SUM word lists across
    entries, so a word logged twice in one close inflated the trailing pace that
    the burn rate — and therefore the sprint's whole honest-meter story — is
    computed from. Merging restores the documented contract rather than guarding
    it from outside."""
    print("\n42. One session-day, one log row (2026-07-31)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    learner_path = sb / "progress" / "learner.json"
    slog_path = sb / "progress" / "session_log.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes(),
             slog_path.read_bytes() if slog_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[],
                    mark_seen=[], next_engine=None, debrief=None,
                    # the sandbox copies REAL slip state, so a live pattern out
                    # in the world must not red these unrelated cases — the
                    # commission gate is s46's subject, waived everywhere else
                    no_commission="smoke sandbox")

    def update(**kw):
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        return read_json(slog_path) or []

    try:
        slog_path.write_text("[]", encoding="utf-8")
        today = ss.local_today().isoformat()
        # Seed two words the sandbox lexicon can actually resolve, so the axes move.
        lex = read_json(lex_path)
        for w in ("ஸ்மோக்ஒன்", "ஸ்மோக்டூ"):
            lex.setdefault(w, {"gloss": "smoke", "phonetic": [], "recognition": "solid",
                               "production": "none", "seen_in": []})
        write_json(lex_path, lex)

        log = update(produced_cold=["ஸ்மோக்ஒன்"])
        check("the first call of a close opens the day's row", len(log) == 1, f"got {len(log)}")

        log = update(produced_cold=["ஸ்மோக்டூ"])
        check("a second update in the same close does NOT forge a session",
              len(log) == 1, f"got {len(log)} rows")
        check("...and its fires land in the same row",
              set(log[-1]["cold"]) == {"ஸ்மோக்ஒன்", "ஸ்மோக்டூ"}, f"got {log[-1]['cold']}")

        # The pace-corrupting half: re-logging one word must not count it twice.
        before = len(log[-1]["cold"])
        log = update(produced_cold=["ஸ்மோக்ஒன்"])
        check("...a word re-logged in the same day stays one fire, not two",
              len(log[-1]["cold"]) == before, f"got {log[-1]['cold']}")

        log = update(debrief="STORY SO FAR: first pass")
        log = update(soak_payload=["ஸ்மோக்டூ"], debrief="STORY SO FAR: rewritten")
        check("a later debrief supersedes rather than appending a row",
              len(log) == 1 and log[-1]["note"] == "STORY SO FAR: rewritten",
              f"got {len(log)} rows, note={log[-1]['note'][:40]!r}")

        log = update(produced_cold=["ஸ்மோக்ஒன்"])
        check("...and an update carrying no debrief never blanks the one written",
              log[-1]["note"] == "STORY SO FAR: rewritten", f"got {log[-1]['note'][:40]!r}")

        check("the row is still dated today", log[-1]["date"] == today)
        check("...and still carries the snapshot meters",
              "floor_pct" in log[-1] and "engines_pct" in log[-1], f"got {sorted(log[-1])}")

        # Yesterday's row is untouched: merging is same-day only, never a fold-up.
        log = read_json(slog_path)
        log.insert(0, {"date": "2020-01-01", "cold": ["old"], "hinted": [], "demoted": [],
                       "listened": [], "note": "ancient"})
        write_json(slog_path, log)
        log = update(produced_cold=["ஸ்மோக்டூ"])
        check("an older day is never merged into today", len(log) == 2, f"got {len(log)}")
        check("...and keeps its own note", log[0]["note"] == "ancient")

    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])
        if saved[2] is not None:
            slog_path.write_bytes(saved[2])


def s53_unverify_rows_nothing_ever_tested(sb: Path):
    """A recognition rating nobody ever earned (2026-08-23, Andrew).

    Replaces the prune-duplicates case with its own command. The lexicon's first
    populated commit already held 153 rows at solid:93 / comfortable:54 — a
    day-one self-estimate written into the field evidence writes into. Nothing
    downstream could tell the two apart, so the ticket offered a June guess as a
    known word and Anna demanded four words he had never met in one session.
    Andrew's ruling: repair the data, do not build a label around it.

    Gate 7.2 — the honest answer is nasty, because this tool has TWO silent
    failures pointing opposite ways. (a) A wrong predicate selects nothing and
    prints "every recognized one has been worked" — which is also exactly what a
    correct run prints once the migration has landed, forever after. So the case
    must prove it FINDS rows in a fixture that has them; a green "no-op" proves
    nothing. (b) An over-broad predicate silently wipes recognition off rows that
    were earned, and no meter would show it as anything but a lower floor. So
    every row below that carries evidence — a rep, a cold fire, or both — is
    asserted to survive untouched.

    And the third teeth: `reps` and `last_surfaced` must come through the write
    unchanged. Demoting via `--stuck-word` would have reached `touch()` and
    bumped both, destroying the signal that identifies these rows and faking a
    working date for callback due-ness. That is a round-trip assertion — re-read
    the file, never trust the dict the command was handed."""
    print("\n53. Recognition nobody ever tested is dropped to struggled (2026-08-23)")
    import contextlib, io, argparse as _ap
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    try:
        row = lambda **kw: {"gloss": "x", "phonetic": [], "recognition": "struggled",
                            "production": "none", "seen_in": [], "last_surfaced": None, **kw}
        lex = {
            # THE POPULATION: rated recognized, never worked by any channel.
            "அது": row(recognition="solid"),
            "இது": row(recognition="comfortable", seen_in=[3, 7], last_surfaced=None),
            # EVIDENCE, three ways — each of these must survive at its rating.
            "வா": row(recognition="solid", reps=4, last_surfaced="2026-08-01"),
            "போ": row(recognition="comfortable", production="cold"),
            "வை": row(recognition="solid", reps=1, production="hinted",
                      last_surfaced="2026-08-19"),
            # already at the floor — nothing to do, and it must not churn
            "சரி": row(recognition="struggled"),
        }
        write_json(lex_path, lex)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ss.cmd_unverify(_ap.Namespace(apply=False))
        check("a dry run writes nothing", read_json(lex_path) == lex, "the preview mutated the file")
        check("...and says so", "DRY RUN" in out.getvalue())
        # (a) The no-op that reads as success: prove it SEES them.
        check("the preview names every untested row", "2 rated without evidence" in out.getvalue(),
              f"got {out.getvalue()!r}")

        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_unverify(_ap.Namespace(apply=True))
        after = read_json(lex_path)
        check("an unearned 'solid' drops to struggled",
              after["அது"]["recognition"] == "struggled", f"got {after['அது']}")
        check("an unearned 'comfortable' drops too",
              after["இது"]["recognition"] == "struggled", f"got {after['இது']}")
        # (b) The opposite failure — silently wiping ratings that were earned.
        check("a row with reps survives at its rating",
              after["வா"]["recognition"] == "solid", f"got {after['வா']}")
        check("a row that has FIRED survives even with no reps",
              after["போ"]["recognition"] == "comfortable", f"got {after['போ']}")
        check("a hinted row with a rep survives",
              after["வை"]["recognition"] == "solid", f"got {after['வை']}")
        # The signal has to survive its own repair, or the rows stop being findable.
        check("reps is never bumped by the repair",
              all(after[w].get("reps", 0) == lex[w].get("reps", 0) for w in lex),
              f"reps moved: {[(w, after[w].get('reps')) for w in lex]}")
        check("last_surfaced is never stamped by the repair",
              all(after[w].get("last_surfaced") == lex[w].get("last_surfaced") for w in lex),
              f"dates moved: {[(w, after[w].get('last_surfaced')) for w in lex]}")
        check("nothing is added or dropped", sorted(after) == sorted(lex), f"got {sorted(after)}")

        with contextlib.redirect_stdout(out := io.StringIO()):
            ss.cmd_unverify(_ap.Namespace(apply=True))
        check("re-running on repaired data is a no-op",
              read_json(lex_path) == after and "every recognized one has been worked" in out.getvalue(),
              f"got {out.getvalue()!r}")
    finally:
        lex_path.write_bytes(saved)


def s54_no_deadline_reaches_any_surface(sb: Path):
    """The trip was modelled as a terminus, and a terminus has to be maintained
    forever. `TRIP_DATE` had an entry and no exit: `compute_status` counted down
    past zero, and `burn_rate`'s `max(days_left, 1)` clamp froze the required
    pace at its final day's value and reported it forever — on 2026-09-01 the
    scoreboard read "-20 days to touchdown · need 8.0 cold/day", during the month
    in country, which is the era the whole deck existed to serve.

    2026-08-04 answered that with a SECOND era (pre-trip, during-trip). There was
    never a third, so after he flew home the line would have read "in country,
    day 32", then 33, forever — the same defect one era further along.

    2026-08-18 answered it by deletion. The deadline is what expired; a required
    pace with no deadline is not a number, it is a guess; and a winnable countdown
    is the motivational device the 08-17 no-numbers rule banned outright.

    Gate 7.2 — this failure never looked like nothing happening. It printed a
    confident, well-formed, wrong line every day, and it was the line Anna
    narrates from. So the checks are on the SHAPE of what every surface emits, not
    on the absence of one constant: a countdown re-added under another name, or a
    quota composed inline from some other date, must fail here."""
    print("\n54. No deadline reaches any surface (2026-08-18)")
    ss = importlib.import_module("sync_state")
    kr = importlib.import_module("knock_reply")
    sbf = importlib.import_module("session_brief")
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    try:
        # The population the countdown used to hang off: a live set with items
        # still open, which is what put `compute_status` on the deck branch.
        write_json(lex_path, {f"smoke:era{i}": {
            "gloss": "x", "phonetic": [], "type": "chunk", "recognition": "comfortable",
            "production": "cold" if i < 2 else "none", "seen_in": [],
            "last_surfaced": None, "register": "antifreeze"} for i in range(10)})
        lex = read_json(lex_path)

        check("the deadline constant is gone, not merely unused",
              not hasattr(ss, "TRIP_DATE"), "TRIP_DATE survived")
        check("...and so is the meter that was computed against it",
              not hasattr(ss, "compute_deck") and not hasattr(ss, "burn_rate"),
              "compute_deck or burn_rate survived")

        line = ss.compute_status()
        check("the scoreboard still leads with the ear", line.startswith("Machines heard"), line)
        check("no countdown reaches it", "touchdown" not in line and "in country" not in line, line)
        check("no required pace reaches it — a quota needs a terminus",
              "need " not in line, line)
        check("no day count of any spelling reaches it",
              not re.search(r"\bday -?\d|\b-?\d+\s*d(ays)?\b", line), line)

        # The trailing pace is the half that was always true — it measures what
        # happened, not what is owed — so it must survive, and say only that.
        pace = ss.trailing_pace()
        check("the trailing pace survives", "trailing" in pace and "pace" in pace, pace)
        check("...and states no requirement", "need" not in pace, pace)

        # The phone. `catch_meter` was deleted on 08-17 for pushing a fraction and
        # a countdown to the lock screen; the production path kept composing the
        # same thing from `compute_deck` until this retirement.
        score = kr.scoreboard(lex)
        check("the push-back carries no fraction",
              re.search(r"\d+\s*/\s*\d+", score) is None, repr(score))
        check("...and no countdown", "d" != score[-1:] and "touchdown" not in score, repr(score))

        # Every surface, not just the one-liner — a countdown that survived in the
        # dashboard or the session load would still be read aloud.
        import contextlib, io
        sbf.git_sync_counts = lambda: (0, 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sbf.cmd_status(None)
        text = out.getvalue()
        check("the session load names no deadline",
              "touchdown" not in text and "in country" not in text
              and "Trip Deck" not in text, "a deadline survived in session_brief")
    finally:
        lex_path.write_bytes(saved)


def s55_demotion_survives_the_close(sb: Path):
    """A word that fails under pressure is demoted — and the path had no test.

    Caught 2026-08-04 while splitting sync_state: the state_io extraction dropped
    the DEMOTE table by an off-by-one, leaving `demote_recognition` referencing an
    undefined name. `python -m pyflakes` found it; the full smoke suite did not,
    and reported ALL GREEN on a commit where any close carrying `--stuck-word`
    against a known word would raise NameError and take the whole update down.

    That is the Gate 7.2 failure in its loudest form rather than its quietest: not
    a silent no-op, but a hard crash on a path nothing exercised. Demotion is not
    an edge case — it is the mechanism that keeps the viability floor honest
    ("expect Anna to demote over-counted 'solid' words as they fail under cold
    recall; that is the meter getting honest, not regression", profile.md). A
    floor that can only go up is the thing this whole system refuses to be.

    Round-trips through the real writer and re-reads the file, because the bug
    was in module-level state, not in the function's logic."""
    print("\n55. A demotion survives the close (2026-08-04)")
    import contextlib, io, argparse as _ap
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    learner_path = sb / "progress" / "learner.json"
    slog_path = sb / "progress" / "session_log.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes(), slog_path.read_bytes())
    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[], no_commission="smoke sandbox")
    try:
        write_json(lex_path, {
            "ஸ்மோக்சாலிட்": {"gloss": "was solid", "phonetic": ["solidword"], "type": "chunk",
                              "recognition": "solid", "production": "cold", "seen_in": [],
                              "last_surfaced": None},
            "ஸ்மோக்ஷேக்கி": {"gloss": "already shaky", "phonetic": ["shakyword"], "type": "chunk",
                              "recognition": "struggled", "production": "none", "seen_in": [],
                              "last_surfaced": None}})
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults,
                                           "stuck_word": ["ஸ்மோக்சாலிட்", "ஸ்மோக்ஷேக்கி"]}))
        lex = read_json(lex_path)
        check("a solid word demotes one step, not straight to the floor",
              lex["ஸ்மோக்சாலிட்"]["recognition"] == "comfortable",
              f"got {lex['ஸ்மோக்சாலிட்']['recognition']}")
        check("...and an already-shaky word stays put rather than falling off",
              lex["ஸ்மோக்ஷேக்கி"]["recognition"] == "struggled",
              f"got {lex['ஸ்மோக்ஷேக்கி']['recognition']}")
        check("...and the demotion is recorded in the day's row",
              sorted(read_json(slog_path)[-1]["demoted"]) == ["ஸ்மோக்சாலிட்", "ஸ்மோக்ஷேக்கி"],
              f"got {read_json(slog_path)[-1]}")
        # Production is a separate axis and must not move on a recognition demotion.
        check("...while production is left alone — the two axes are independent",
              lex["ஸ்மோக்சாலிட்"]["production"] == "cold",
              f"got {lex['ஸ்மோக்சாலிட்']['production']}")
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])
        slog_path.write_bytes(saved[2])


def s46_the_commission_notice_names_the_debt(sb: Path):
    """A live slip pattern with no dose is NAMED at the close (2026-08-01;
    demoted from a refusal 2026-08-20, Andrew).

    The original complaint is real and still the reason this case exists:
    NEVER COMMISSIONED got walked past for mechanical reasons — venum-for-kudunga
    sat 24 days between first slip and first dose while the ticket warned daily
    ("the flag needs teeth", feedback 07-31).

    The 08-01 answer was a hard refusal. It never fired once: `uncommissioned`
    was disarmed the same week by the dose_channel conflation in slips.py, so
    for three weeks this case was green against a gate that could not trip. When
    the detection was repaired on 08-20 the refusal became real for the first
    time, and Andrew ruled it out immediately — commissioning nothing is a
    first-class outcome; a dose is earned by a genuinely recurring pattern or
    something real to teach, never by a counter reaching two.

    Gate 7.2 — the silent no-op here is a notice that never prints, which looks
    exactly like a clean close. So the case asserts the EFFECT in both
    directions: the debt is named in the output, AND the close still applies in
    full (rep, cold, debrief, slip row) — a notice that eats the session would
    be the worse bug. Then each door: the override echoing its reason, a
    commission covering the debt in the same close, and a landed test
    discharging its own tag."""
    print("\n46. The commission notice names the debt (2026-08-01; advisory 2026-08-20)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    sl = importlib.import_module("slips")
    lex_path = sb / "progress" / "lexicon.json"
    learner_path = sb / "progress" / "learner.json"
    slip_path = sb / "progress" / "slip_log.json"
    slog_path = sb / "progress" / "session_log.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes(),
             slip_path.read_bytes() if slip_path.exists() else None,
             slog_path.read_bytes() if slog_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[], no_commission=None)

    def update(**kw):
        out, code = io.StringIO(), 0
        try:
            with contextlib.redirect_stdout(out):
                ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        except SystemExit as e:
            code = e.code
        return code, out.getvalue()

    try:
        # Clean ledger, then one live uncommissioned pattern.
        slip_path.write_text("[]", encoding="utf-8")
        learner = read_json(learner_path)
        for k in ("slip_closes", "slip_commissions"):
            learner.pop(k, None)
        write_json(learner_path, learner)
        lex = read_json(lex_path)
        lex["கேட்வேர்ட்"] = {"gloss": "gate word", "recognition": "solid",
                            "production": "none", "phonetic": [], "seen_in": []}
        write_json(lex_path, lex)
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "gate-tag", "said": "a", "want": "b"}],
                            lane="chat", when="2026-01-01")
            sl.append_slips([{"tag": "gate-tag", "said": "a", "want": "b"}],
                            lane="chat", when=ss.local_today().isoformat())

        # ADVISORY, NOT A GATE (Andrew, 2026-08-20). These two cases used to
        # assert `code == 2` and a byte-identical tree — the close refused, and
        # nothing was written. That contract is retired: commissioning nothing
        # is a first-class outcome, so an uncommissioned debt is NAMED and the
        # close completes. The property worth keeping is that the notice cannot
        # eat the close — a debt must never cost Andrew his debrief.
        code, out = update(produced_cold=["கேட்வேர்ட்"], debrief="a close over a debt")
        check("an uncommissioned debt is named out loud",
              "gate-tag" in out, out[:200])
        check("...and the close still completes — the notice never eats the session",
              code == 0, f"exit {code}")
        check("...and the whole close applied: the rep, the cold, the debrief",
              read_json(lex_path)["கேட்வேர்ட்"]["production"] == "cold"
              and read_json(learner_path).get("last_debrief") == "a close over a debt")

        # Door 1: the override, reason on the record.
        code, out = update(produced_cold=["கேட்வேர்ட்"], no_commission="trip-eve triage")
        check("the override closes, echoing the reason",
              code == 0 and "trip-eve triage" in out, f"exit {code}")
        check("...and the overridden close actually applied",
              read_json(lex_path)["கேட்வேர்ட்"]["production"] == "cold")

        # Door 2: commission the debt in the same close.
        code, _ = update(soak_payload=["கேட்வேர்ட்"], soak_channel="soak",
                         slip_commissioned=["gate-tag"])
        check("a close that commissions the debt passes the gate", code == 0)
        check("...and the debt is booked",
              "gate-tag" in sl.slip_commissions(), "the gate passed but nothing was booked")

        # The sim path: a slip whose SECOND occurrence arrives in this very
        # close is already a pattern to the gate.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "gate-tag3", "said": "a", "want": "b"}],
                            lane="chat", when="2026-01-03")
        n_rows = len(read_json(slip_path))
        code, out = update(slip=["gate-tag3|x|y|"])
        check("a second occurrence landing IN the close is named the same day",
              code == 0 and "gate-tag3" in out, f"exit {code}: {out[:200]}")
        check("...and the slip row it names was still written",
              len(read_json(slip_path)) == n_rows + 1,
              "the notice swallowed the row it was warning about")

        # Door 3: a landed test in the same close discharges its own tag.
        with contextlib.redirect_stdout(io.StringIO()):
            sl.append_slips([{"tag": "gate-tag4", "said": "a", "want": "b"}],
                            lane="chat", when="2026-01-04")
            sl.append_slips([{"tag": "gate-tag4", "said": "a", "want": "b"}],
                            lane="chat", when=ss.local_today().isoformat())
        code, _ = update(slip_tested=["gate-tag4:landed"])
        check("a landed test in the same close discharges its own tag", code == 0)
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])
        if saved[2] is not None:
            slip_path.write_bytes(saved[2])
        if saved[3] is not None:
            slog_path.write_bytes(saved[3])


def s47_hinted_retest_rule(sb: Path):
    """Hinted had no follow-up path ("open and unanswered", DECISIONS 07-28;
    built 2026-08-01). `coverage_key` leads with fewest-reps, so a
    repped-but-stale hinted item sorts behind every never-worked item in its
    tier FOREVER — the three FAQ answers sat hinted 22–28 days silent at 11
    days to touchdown.

    Gate 7.2 — the silent no-op is an empty block reading as "nothing stale",
    so the case asserts presence, ordering, the fresh and ear-only exclusions,
    and that the real ticket entry point surfaces it at all.

    EXTENDED 2026-08-04, after the block spent four weeks working for the wrong
    five items. The 08-01 case asserted ordering at `max_n=100` — where nothing
    can fall off — so it never tested the CUT, which is the only place this can
    fail silently. It still returned five rows and still read as success while
    the deck's three hinted FAQ answers sat below the line behind ordinary
    vocabulary that happened to be staler, and while the top slot went to a
    bootstrap artifact (hinted, zero reps, never surfaced).

    FOLDED IN 2026-08-18. "HINTED, GOING DARK" was its own ticket section — a
    rival pool on a ticket that had nine of them — when it is a RULE
    (`RETEST_DAYS`), not a population. It is now `is_going_dark` plus a
    reservation inside the pool's focus set. The fold-in had to cost nothing:
    every assertion below is the 08-01/08-04 assertion re-aimed at the pool, and
    the cut it survives is now FOCUS_SIZE seats rather than a five-item list. A
    flag on a row nothing selects would have been the same silent no-op in a new
    costume, which is why the reservation exists and why the cut is tested."""
    print("\n47. Hinted items going dark are retested, inside the pool (2026-08-01)")
    import contextlib, io
    st = importlib.import_module("suggest_targets")
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    today = date_cls.today()
    try:
        lex = {}
        mk_day = lambda d: (today - timedelta(days=d)).isoformat()
        dark = lambda d: mk_day(st.RETEST_DAYS + d)
        lex["ரீடெஸ்ட்1"] = {"gloss": "stale hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(6), "reps": 5}
        lex["ரீடெஸ்ட்2"] = {"gloss": "staler hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(16), "reps": 2}
        lex["ரீடெஸ்ட்3"] = {"gloss": "fresh hinted", "production": "hinted",
                           "recognition": "solid", "last_surfaced": mk_day(3), "reps": 1}
        lex["ரீடெஸ்ட்4"] = {"gloss": "stale but ear-only", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(16),
                           "direction": "catch", "reps": 0}
        # RANKED rows, deliberately FRESHER than the unranked ones above: only a
        # tier prefix can float them — staleness alone sinks both.
        lex["ரீடெஸ்ட்5"] = {"gloss": "survival, antifreeze", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(2),
                           "reps": 5, "register": "antifreeze"}
        lex["ரீடெஸ்ட்6"] = {"gloss": "survival, public", "production": "hinted",
                           "recognition": "solid", "last_surfaced": dark(1),
                           "reps": 3, "register": "public"}
        # The bootstrap artifact: a hinted grade with no work behind it. There is
        # no prior test for a RE-test to repeat, and it is already at the head of
        # the pool (coverage_key leads with fewest-reps), so it must not spend a
        # reserved seat here.
        lex["ரீடெஸ்ட்7"] = {"gloss": "hinted, never surfaced", "production": "hinted",
                           "recognition": "struggled", "last_surfaced": None, "reps": 0}

        # --- the RULE, on its own ---
        def gd(w):
            r = lex[w]
            return st.is_going_dark(r, st.days_since(r["last_surfaced"], today))

        check("a hinted item silent past RETEST_DAYS is going dark", gd("ரீடெஸ்ட்1"))
        check("a recently-worked hinted item is not", not gd("ரீடெஸ்ட்3"))
        check("ear-only items are excluded — a retest is a production move",
              not gd("ரீடெஸ்ட்4"))
        check("a hinted grade with no work behind it is excluded — nothing to re-test",
              not gd("ரீடெஸ்ட்7"))
        check("the boundary is the constant, not a literal",
              not st.is_going_dark({"production": "hinted"}, st.RETEST_DAYS - 1)
              and st.is_going_dark({"production": "hinted"}, st.RETEST_DAYS))

        # --- the RULE, reaching the pool ---
        write_json(lex_path, lex)
        focus, _bg = st.floor_gap_targets(lex, today, st.FOCUS_SIZE, asked={}, cohort=[])
        words = [t["word"] for t in focus if t["retest"]]
        check("the dark rows reach the pool and are flagged there",
              set(words) == {"ரீடெஸ்ட்1", "ரீடெஸ்ட்2", "ரீடெஸ்ட்5", "ரீடெஸ்ட்6"},
              f"got {words}")
        check("...most-stale first within a tier",
              words.index("ரீடெஸ்ட்2") < words.index("ரீடெஸ்ட்1"), f"got {words}")
        check("the never-surfaced bootstrap row is never flagged for retest",
              not any(t["retest"] for t in focus if t["word"] == "ரீடெஸ்ட்7"),
              f"got {focus}")

        # THE 2026-08-04 defect, re-aimed. A staleness-only sort passes every
        # check above and fails both of these: the ranked rows are the two
        # FRESHEST candidates and must still lead on the tier prefix alone.
        check("the ranked items lead, even when unranked rows are staler",
              words[:2] == ["ரீடெஸ்ட்6", "ரீடெஸ்ட்5"], f"got {words}")
        # THE RESERVATION, on the only fixture that can test it. The two ranked
        # rows above win seats on the tier prefix alone, so they prove ordering,
        # not reachability. Drop them and the survivors are UNRANKED, repped and
        # stale — precisely the shape `coverage_key` buries behind every
        # never-worked row forever, and precisely the incident: the FAQ answers
        # sat 22-28 days silent while the ticket kept offering fresh ground.
        crowd = {w: r for w, r in lex.items() if w not in ("ரீடெஸ்ட்5", "ரீடெஸ்ட்6")}
        crowd.update({f"smoke:crowd{i}": {"gloss": "never worked", "production": "none",
                                          "recognition": "comfortable",
                                          "last_surfaced": None, "reps": 0}
                      for i in range(40)})
        # A held cohort, so this runs the LIVE path (a stored membership) rather
        # than the day-zero seed derivation, which fills from reps and would let
        # a repped row in through a door the reservation is not being asked about.
        held = ["smoke:crowd0"]
        focus, _bg = st.floor_gap_targets(crowd, today, st.FOCUS_SIZE, asked={}, cohort=held)
        cut = [t["word"] for t in focus if t["retest"]]
        check("a dark row survives a wall of never-worked rows — reachability is "
              "the whole reason this was ever a block",
              "ரீடெஸ்ட்2" in cut, f"got {cut} of {[t['word'] for t in focus]}")
        check("...staler first among them", cut[:1] == ["ரீடெஸ்ட்2"], f"got {cut}")
        # A FLOOR, NEVER A CEILING: no dark row wins a seat on the ordering in
        # this fixture (reps 2 and 5 against forty at zero), so anything above
        # the reservation would be the retest rule flooding the set — which is
        # how it earned its own section, and its own primacy, the first time.
        check("...and the reservation tops up without taking over",
              0 < len(cut) <= st.RETEST_SLOTS, f"{len(cut)} of {len(focus)} seats: {cut}")

        out, real_argv = io.StringIO(), sys.argv
        try:
            sys.argv = ["suggest_targets.py"]
            with contextlib.redirect_stdout(out):
                st.main()
        finally:
            sys.argv = real_argv
        text = out.getvalue()
        check("the ticket marks the going-dark rows — the rule is only worth "
              "having if the entry point says so", "GOING DARK" in text, text[-800:])
        check("...and it is no longer a rival section with its own headline",
              "★ HINTED, GOING DARK" not in text, "the block survived the fold-in")
    finally:
        lex_path.write_bytes(saved)


def s56_timezone_is_one_dial(sb: Path):
    """The zone is a field in learner.json, and it SURVIVES the next update
    (2026-08-09).

    `LOCAL_TZ` was already the single definition every clock-facing rule read —
    quiet hours, the rails gate, `local_today`, feed pubDates — but it lived in
    source as `ZoneInfo("America/New_York")`. Fine while he is home; a code edit
    on the road, from an airport, on the day the rails matter most. Andrew asked
    for the dial to move into his profile: one field, changed when he lands.

    The trap this section exists for is NOT the read — that is four lines — it is
    `write_thin_learner`, a whitelist that DELETES any learner key not named in
    it. That exact shape already ate `slip_closes` silently for a week (see s44).
    A wiped zone is worse than a wiped close, because the fallback is a perfectly
    valid zone: everything keeps running, on the wrong clock, and the only
    symptom is a push at 3am in Chennai. So the assertion that earns its keep is
    the round-trip through an update, not the parse."""
    print("\n56. The timezone is one dial in learner.json (2026-08-09)")
    import argparse as _ap
    import contextlib, io
    ss = importlib.import_module("sync_state")
    si = importlib.import_module("state_io")
    learner_path = sb / "progress" / "learner.json"
    saved = learner_path.read_bytes()

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None, soak_focus=None,
                    soak_channel=None, soak_form=None, mastered_word=[], comfortable_word=[],
                    stuck_word=[], produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[],
                    # This section is not testing the commission gate, and by the
                    # time it runs the sandbox carries live uncommissioned slips
                    # from earlier sections — which refuse the close (exit 2).
                    no_commission="smoke: zone round-trip, not a real close")

    try:
        # The trip zone, set the way Andrew will set it: edit the one field.
        learner = read_json(learner_path)
        learner["timezone"] = "Asia/Kolkata"
        write_json(learner_path, learner)

        check("the profile carries the zone", si._resolve_local_tz().key == "Asia/Kolkata",
              f"got {si._resolve_local_tz()}")

        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_update(_ap.Namespace(**{**defaults, "debrief": "landed"}))
        check("...and it SURVIVES the update that follows (write_thin_learner whitelist)",
              read_json(learner_path).get("timezone") == "Asia/Kolkata",
              f"got {read_json(learner_path).get('timezone')!r} — the whitelist ate the zone")

        # Silence is the home zone: a fork, or a clone that never set the field.
        learner = read_json(learner_path)
        del learner["timezone"]
        write_json(learner_path, learner)
        check("a profile with no zone falls back to home",
              si._resolve_local_tz().key == si.DEFAULT_TZ, f"got {si._resolve_local_tz()}")

        # A typo must not take the unattended lanes down with it — the knock cron,
        # the queue and the studio all import this module at start-up.
        learner["timezone"] = "Nowhere/Atlantis"
        write_json(learner_path, learner)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            tz = si._resolve_local_tz()
        check("a bad zone falls back instead of crashing every lane",
              tz.key == si.DEFAULT_TZ, f"got {tz}")
        check("...and says so on stderr", "Nowhere/Atlantis" in err.getvalue(),
              f"silent fallback: {err.getvalue()!r}")
    finally:
        learner_path.write_bytes(saved)


DEBT_CEILING_NO_PHONETIC = 96


def s71_a_new_record_is_born_reachable(sb: Path):
    """A minted record must carry its sounds-like form (2026-08-14, Andrew).

    Found live at a session close: `--produced-hinted ukkarunga` bounced, so did
    `ukkaarunga`, and the rep only landed by falling back to Tamil script through
    a UTF-8 shell. `resolve()` is exact-match against each record's `phonetic`
    list, and three mint sites wrote `[]` under a "backfill later" note — 96 of
    313 word records had none by that day, 88 of them `production: none`, and 5
    of the 12 items on that session's own focus set were unloggable phonetically.
    The ticket was naming targets the logger would refuse.

    Gate 7.2 — a guard that never fires looks exactly like a clean close, and a
    guard that fires but stores nothing useful looks exactly like a fixed bug. So
    this asserts the EFFECT in the dimension that actually failed: not "the mint
    was refused" alone, but that a word taught WITH its phonetic can afterwards be
    logged BY that phonetic, round-tripped through the real command and re-read
    from disk. That round trip is the whole purpose; everything else is ceremony.

    The ratchet is the second half of Andrew's call: `render_audio` mints records
    unattended and cannot be blocked without killing renders, so the debt is
    capped instead. Existing records are grandfathered — no backfill, by his
    decision. The number may only ever fall; lower it when a tranche is vetted."""
    print("\n71. A new record is born reachable (2026-08-14)")
    import argparse as _ap
    import contextlib
    ss = importlib.import_module("sync_state")
    lex_path = sb / "progress" / "lexicon.json"
    slip_path = sb / "progress" / "slip_log.json"
    saved = (lex_path.read_bytes(),
             slip_path.read_bytes() if slip_path.exists() else None)

    defaults = dict(listened=[], teach=[], soak_payload=[], soak_seed=None,
                    soak_focus=None, soak_channel=None, soak_form=None,
                    mastered_word=[], comfortable_word=[], stuck_word=[],
                    produced_cold=[], produced_hinted=[], mark_seen=[],
                    next_engine=None, debrief=None, slip=[], slip_tested=[],
                    slip_commissioned=[], no_commission=None, quiet_until=None)

    def update(**kw):
        out, code = io.StringIO(), 0
        try:
            with contextlib.redirect_stdout(out):
                ss.cmd_update(_ap.Namespace(**{**defaults, **kw}))
        except SystemExit as e:
            code = e.code
        return code, out.getvalue()

    try:
        # An empty ledger so the commission gate can't refuse these closes for
        # reasons of its own (s46 owns that behaviour).
        slip_path.write_text("[]", encoding="utf-8")

        # 1. The refusal — teaching without a phonetic must NOT mint a record.
        word = "ஸ்மோக்வார்த்தை"
        _, out = update(teach=[f"{word}=smoke word"])
        check("teach without a phonetic is refused, naming the word",
              word in out and "Skipped" in out, out.strip()[-160:])
        check("...and nothing was written for it",
              word not in read_json(lex_path),
              "a record was minted anyway — the guard is decorative")

        # 2. The same refusal on the recognition mint path.
        _, out = update(comfortable_word=[word])
        check("--comfortable-word without a phonetic is refused too",
              word not in read_json(lex_path), "recognition path still mints holes")

        # 3. The legal door — taught WITH its sounds-like form.
        _, _ = update(teach=[f"{word}=smoke word|smokevaarthai"])
        rec = read_json(lex_path).get(word)
        check("teach with a phonetic mints the record",
              rec is not None, "the legal form was refused as well")
        check("...and the phonetic is stored on it",
              bool(rec) and rec.get("phonetic") == ["smokevaarthai"],
              f"phonetic={rec.get('phonetic') if rec else None}")

        # 4. THE POINT — round-trip: the word is now loggable BY its phonetic,
        #    which is the exact operation that failed live.
        _, out = update(produced_cold=["smokevaarthai"])
        check("the phonetic now resolves for a later production log",
              read_json(lex_path)[word].get("production") == "cold",
              f"still unreachable from phonetics: {out.strip()[-160:]}")

        # 5. The ratchet — real tree, not the sandbox: the debt binds the
        #    lexicon as committed. Frames are exempt (addressed by `frame:` key).
        real_lex = read_json(REAL_BASE / "progress" / "lexicon.json") or {}
        debt = sum(1 for k, v in real_lex.items()
                   if not k.startswith("frame:") and not v.get("phonetic"))
        check(f"records with no phonetic: {debt}/{DEBT_CEILING_NO_PHONETIC}",
              debt <= DEBT_CEILING_NO_PHONETIC,
              f"{debt - DEBT_CEILING_NO_PHONETIC} new unreachable record(s) — give "
              f"them a phonetic, or lower the ceiling in this same diff if you "
              f"vetted a tranche. It may never be raised.")
    finally:
        lex_path.write_bytes(saved[0])
        if saved[1] is not None:
            slip_path.write_bytes(saved[1])


def s62_the_return_clock_is_keyed_to_the_ear(sb: Path):
    """Decayed items come back, and due-ness reads the recognition axis (2026-08-17).

    The spacing effect is the shape memory has, not a technique, and the system
    had a real spaced-repetition selector all along — `generate_callbacks.py`,
    intervals on `last_surfaced`. Two exclusions gutted it for the ear: patterns
    were skipped ("tracked engines, not soak words") and struggled rows were
    skipped ("repeated audio exposure doesn't fix cold-production gaps"). Both
    were right for a production headline. Both removed precisely the inventory a
    recognition headline lives on — the 26 machines, and the 144 struggled rows
    that are the cheapest material in the ledger to recover.

    Gate 7.2 — the silent no-op is severe here and reads as good news: a clock
    that selects nothing prints "(nothing due — the recognized set is fresh)",
    which looks like a healthy ledger rather than a dead selector. So the checks
    assert that specific rows COME BACK, and that due-ness moves when the
    recognition axis moves and not when production does."""
    print("\n62. The return clock is keyed to the ear (2026-08-17)")
    gc = importlib.import_module("generate_callbacks")
    today = date_cls(2026, 8, 17)
    row = lambda **kw: {"gloss": "g", "phonetic": ["p"], "seen_in": [], **kw}
    lex = {
        # struggled pattern, 6 days stale — the exact row both old rules dropped
        "frame:struggled": row(type="pattern", recognition="struggled",
                               production="cold", last_surfaced="2026-08-11"),
        # solid, same staleness — retained, not yet due at 21 days
        "solid-fresh": row(recognition="solid", production="cold",
                           last_surfaced="2026-08-11"),
        # comfortable at 12 days — past its 10-day interval
        "comfortable-due": row(recognition="comfortable", production="none",
                               last_surfaced="2026-08-05"),
    }
    due = {c["word"]: c for c in gc.due_callbacks(lex, today, 10)}

    check("a struggled PATTERN is due — both old exclusions lifted",
          "frame:struggled" in due, str(sorted(due)))
    check("a solid row at 6 days is NOT due (21-day interval)",
          "solid-fresh" not in due, str(sorted(due)))
    check("a comfortable row at 12 days IS due (10-day interval)",
          "comfortable-due" in due, str(sorted(due)))
    # Overdue-ness leads the sort; RECOGNITION_RANK only breaks ties. Equal
    # overdue (both 1 day past their own interval) is where it shows.
    tie = {"a-solid": row(recognition="solid", production="cold", last_surfaced="2026-07-26"),
           "b-struggled": row(recognition="struggled", production="cold", last_surfaced="2026-08-11")}
    order = [c["word"] for c in gc.due_callbacks(tie, today, 10)]
    check("on equal overdue the weaker trace comes back first",
          order[0] == "b-struggled", str(order))

    # Due-ness must follow the EAR. Flipping production alone changes nothing;
    # flipping recognition to solid must retire the row from today's list.
    lex["frame:struggled"]["production"] = "none"
    check("production no longer drives due-ness",
          "frame:struggled" in {c["word"] for c in gc.due_callbacks(lex, today, 10)})
    lex["frame:struggled"]["recognition"] = "solid"
    check("...and recognition does",
          "frame:struggled" not in {c["word"] for c in gc.due_callbacks(lex, today, 10)})

    # The failure the green suite missed: with the sentinel in play, EVERY slot
    # on the live ticket read "(last: never surfaced)" — the clock had never
    # returned a single decayed row, and it looked like a working selector
    # because it was producing output. A return clock returns what was met.
    lex["never-worked"] = row(recognition="struggled", production="none")
    picked = [c["word"] for c in gc.due_callbacks(lex, today, 10)]
    check("a never-surfaced row is not 'due' — it is new ground, not decay",
          "never-worked" not in picked, str(picked))
    check("...and the decayed rows still come back",
          "comfortable-due" in picked, str(picked))


def s63_the_machines_reach_the_ticket():
    """Patterns are reachable, not merely eligible (2026-08-17).

    Letting patterns into the pool (s62) made them ELIGIBLE. It did not make them
    REACHABLE: on the live ledger 100 rows came back due, the first pattern sat at
    rank 59, and the five-slot ticket therefore returned words only. The 26
    machines — the set the comprehension threshold rides on, since the tails carry
    the sentence skeleton — had a return path in principle and none in fact. Words
    outnumber patterns ~12:1 and decay on the same clock, so the majority pool
    takes every seat on staleness alone, forever.

    Gate 7.2 — what does this look like when it silently does nothing? A ticket of
    five genuinely-overdue words, which is indistinguishable from a healthy
    selection: nothing errors, every row is real and really due, and the absence of
    a machine is invisible unless something asserts it. That is exactly how the
    original defect survived a green suite — s62 proved eligibility against a
    three-row lexicon, a shape in which the bug cannot appear.

    So this reproduces the LIVE shape — many ancient words against a few
    less-ancient patterns — and asserts the machines are on the ticket anyway,
    that the reservation is a floor and never a ceiling, and that it can never
    grow to starve the words."""
    print("\n63. The machines reach the ticket (2026-08-17)")
    gc = importlib.import_module("generate_callbacks")
    today = date_cls(2026, 8, 17)
    row = lambda **kw: {"gloss": "g", "phonetic": ["p"], "seen_in": [], **kw}
    # The live distribution: words far more overdue than any pattern.
    lex = {f"word{i}": row(recognition="struggled", production="cold",
                           last_surfaced="2026-06-24") for i in range(40)}
    lex.update({f"frame:m{i}": row(type="pattern", recognition="struggled",
                                   production="cold", last_surfaced="2026-08-05")
                for i in range(3)})

    picked = gc.due_callbacks(lex, today, 5)
    pats = [c for c in picked if c["pattern"]]
    check("the ticket is still full", len(picked) == 5, str(len(picked)))
    check("machines are on it despite losing on staleness",
          len(pats) == gc.PATTERN_SLOTS, f"{len(pats)} of {[c['word'] for c in picked]}")
    check("...and the words keep the majority of the seats",
          len(picked) - len(pats) == 3, str(len(picked) - len(pats)))

    # A FLOOR, NOT A CEILING: when patterns are the most decayed rows in the
    # ledger, the reservation must not cap them back down to two.
    flip = {f"word{i}": row(recognition="struggled", production="cold",
                            last_surfaced="2026-08-05") for i in range(40)}
    flip.update({f"frame:m{i}": row(type="pattern", recognition="struggled",
                                    production="cold", last_surfaced="2026-06-24")
                 for i in range(4)})
    won = [c for c in gc.due_callbacks(flip, today, 5) if c["pattern"]]
    check("machines that win on merit are not capped at the reservation",
          len(won) == 4, f"{len(won)} patterns won seats")

    # The reservation may never take the whole ticket.
    one = gc.due_callbacks(lex, today, 1)
    check("a single-slot ticket is not handed to the reservation",
          not one[0]["pattern"], one[0]["word"])
    check("half is the hard cap on a two-slot ticket",
          sum(1 for c in gc.due_callbacks(lex, today, 2) if c["pattern"]) == 1)

    # And the pool is unchanged — no pattern arrives that was never met.
    lex["frame:unmet"] = row(type="pattern", recognition="struggled", production="none")
    check("the reservation cannot smuggle in a never-surfaced row",
          "frame:unmet" not in {c["word"] for c in gc.due_callbacks(lex, today, 5)})


def s64_the_ask_cooldown_covers_the_session_lane(sb: Path):
    """One item, six surfaces, four move names (2026-08-18, Andrew).

    `இன்னொரு தடவ சொல்லுங்க` was pushed on 08-09 (fielding), 08-12 (volley 3/4),
    08-15 (slip medicine + soak order + campaign mission) and 08-16 (challenge)
    until Andrew asked why he was being taught the same line for a week. Two
    independent holes, both closed here:

      1. THE WINDOW WAS SHORTER THAN HIS REPLY LATENCY. Gaps of exactly 3 and 4
         days against a 3-day cooldown, so every re-ask landed just outside it.
         He answered 4 of 14 knocks that week — a guard that expires in 3 days
         cannot hold an item that takes 4-7 to get answered.
      2. THE SESSION LANE COULD NOT SEE THE COOLDOWN AT ALL. The knock menu
         warns the knock decider, but the soak order, the campaign mission and
         the slip medicine are written by Anna off `session_brief`, which never
         imported the selector. Three of the six surfaces came from there.

    This is KF-6 returning through the door KF-6 left open: its fix counted asks
    for the deck menu and assumed one menu.

    Gate 7.2 — the silent no-op: a cooldown that suppresses nothing renders as a
    perfectly healthy ticket. Every row is real, every row is genuinely due, and
    the only evidence of failure is a repeat a week later that no instrument
    reports. So the assertions are on the EFFECT at both surfaces — the count
    itself, and the text the session surface actually prints, re-read off
    `cmd_status` rather than off the function that computes it."""
    print("\n64. The ask cooldown covers the session lane (2026-08-18)")
    import contextlib
    st = importlib.import_module("suggest_targets")
    sbf = importlib.import_module("session_brief")
    lex_path, klog_path = sb / "progress" / "lexicon.json", sb / "progress" / "knock_log.json"
    saved = (lex_path.read_bytes(), klog_path.read_bytes())
    now = datetime.now(timezone.utc)
    ago = lambda d: (now - timedelta(days=d)).isoformat()
    w, other = "இன்னொரு தடவ சொல்லுங்க", "smoke:answered"

    check("the window exceeds the observed reply latency (4-7d)",
          st.ASK_COOLDOWN_DAYS >= 7, f"got {st.ASK_COOLDOWN_DAYS}")

    write_json(lex_path, {
        w: {"gloss": "say it once more", "phonetic": ["innoru thadava sollunga"],
            "type": "chunk", "recognition": "struggled", "production": "hinted",
            "deck": "trip", "direction": "fire", "seen_in": []},
        other: {"gloss": "x", "phonetic": ["x"], "type": "chunk", "recognition": "struggled",
                "production": "hinted", "seen_in": []},
        # `recent_ask_counts` walks the LEXICON and probes the log, so a filler
        # target with no row is invisible to it. Distinct phonetics, and bodies
        # below that share no token with them — otherwise a probe matches another
        # row's body and the counts stop meaning what the assertions say.
        "smoke:once": {"gloss": "asked once", "phonetic": ["onlyoncehere"],
                       "type": "chunk", "recognition": "struggled",
                       "production": "hinted", "seen_in": []},
        **{f"smoke:filler{i}": {"gloss": "f", "phonetic": [f"fillerword{i}"],
                               "type": "chunk", "recognition": "struggled",
                               "production": "hinted", "seen_in": []}
           for i in range(9)},
    })
    # The real sequence: gaps of 3 then 4 days, none answered.
    klog = [{"acted": True, "timestamp": ago(6), "modality": "fielding",
             "move": "fielding: innoru thada", "expected_target": w, "body": "answer her"},
            {"acted": True, "timestamp": ago(3), "modality": "volley",
             "move": "volley: sprint burn 3/4", "expected_target": w, "body": "ask her again"},
            # answered, and inside the window — must NOT be marked unanswered.
            # TWICE, because one mention is below `ASK_REPEAT_FLOOR` and the block
            # is a repeat-detector: a single ask is the case it exists to permit.
            {"acted": True, "timestamp": ago(4), "modality": "text", "move": "collect",
             "expected_target": other, "body": "x", "reply": "aama", "reply_verdict": "cold"},
            {"acted": True, "timestamp": ago(3), "modality": "text", "move": "collect",
             "expected_target": other, "body": "x", "reply": "seri", "reply_verdict": "cold"},
            {"acted": True, "timestamp": ago(2), "modality": "text", "move": "collect",
             "expected_target": other, "body": "x", "reply": "sari", "reply_verdict": "cold"},
            # The third surface, and the one that named the session lane: the
            # 08-15 soak order PRINTED the item as prose rather than targeting
            # it, which `recent_ask_counts` catches through the body probe. Kept
            # outside 3 days like the other two — the retired guard has to see
            # NOTHING here, which is the reproduction this case is built on.
            {"acted": True, "timestamp": ago(5), "modality": "text", "move": "soak order",
             "expected_target": "", "body": f"today we soak {w}"},
            {"acted": True, "timestamp": ago(2), "modality": "text", "move": "one-off",
             "expected_target": "smoke:once", "body": "situation only"},
            # long past the window — must age out entirely
            {"acted": True, "timestamp": ago(30), "modality": "text", "move": "old",
             "expected_target": "smoke:ancient", "body": "x"}]
    # Enough repeats to make the CAP bind. Without these the fixture has two
    # qualifying rows and a cap of 99 would pass the assertion below — a guard
    # that cannot fail is the thing this whole case exists to argue against.
    ASK_FILLER = 9
    for i in range(ASK_FILLER):
        for d in (5, 3):
            klog.append({"acted": True, "timestamp": ago(d), "modality": "text",
                         "move": f"filler {i}", "expected_target": f"smoke:filler{i}",
                         "body": "situation only"})
    write_json(klog_path, klog)

    lex_now = read_json(lex_path)
    # THE DELTA IS THE PROOF, not an absolute count: under the retired 3-day
    # guard this exact sequence was invisible, which is why it fired three times.
    old = st.recent_ask_counts(klog, lex_now, days=3)
    asked = st.recent_ask_counts(klog, lex_now)
    check("the retired 3-day guard saw NOTHING here — this is the bug, reproduced",
          not old.get(w), f"got {old}")
    check("the widened window catches both re-asks and the prose mention",
          asked.get(w) == 3, f"got {asked}")
    check("an ANSWERED repeat outranks unanswered ties only on count, not on being read",
          asked.get(other) == 3, f"got {asked}")
    check("an ask well outside the window still ages out",
          "smoke:ancient" not in asked, f"got {asked}")

    sbf.git_sync_counts = lambda: (0, 0)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sbf.cmd_status(None)
    text = out.getvalue()

    check("the session surface prints the cooldown at all", "ALREADY ASKED" in text)
    check("...and names the over-asked item", w in text.split("ALREADY ASKED")[1][:400])
    check("an unanswered ask is called out — silence must not read as a reason to re-ask",
          "UNANSWERED" in text.split("ALREADY ASKED")[1][:400])
    body = [ln for ln in text.splitlines() if ln.strip().startswith(f"- {other}")]
    check("an ANSWERED ask is listed without the unanswered warning",
          body and "UNANSWERED" not in body[0], f"got {body}")

    # THE BLOCK IS BOUNDED (2026-08-18, Andrew, hours after the block shipped).
    # The first cut printed every row in the window — 50 on live state, 27 of
    # them single mentions — so the 6× and 5× rows that caused the incident sat
    # at the top of a wall. A guard nobody reads guards nothing, which is the
    # same silent-no-op family one layer up: the mechanism fires, the human
    # doesn't. Both terms are asserted because both can rot quietly — a cap that
    # stops capping just gets long again, and a floor that creeps to 3 hides a
    # genuine second surface.
    lines = [ln for ln in text.split("ALREADY ASKED")[1].splitlines()
             if ln.strip().startswith("- ")]
    check("the block is capped, not the whole window",
          len(lines) == sbf.ASK_BLOCK_CAP,
          f"printed {len(lines)} of {2 + ASK_FILLER} qualifying rows, "
          f"cap is {sbf.ASK_BLOCK_CAP}")
    check("...and the remainder is counted, never silently dropped",
          f"{2 + ASK_FILLER - sbf.ASK_BLOCK_CAP} more" in text, "no overflow line")
    check("a single mention is not a repeat and stays out of the block",
          sbf.ASK_REPEAT_FLOOR >= 2 and "smoke:once" not in text)
    # THE SAME ROW, THE OTHER SIDE. The demotion the SELECTOR does is a different
    # question from what the brief prints, and trimming the reading must not trim
    # it: a 1× row still rides the cooldown inside `floor_gap_targets`. Asserted
    # on the row the block just hid, so the two cannot drift apart quietly.
    check("...while the selector still counts it — only the reading is trimmed",
          st.recent_ask_counts(klog, lex_now).get("smoke:once") == 1,
          f"got {st.recent_ask_counts(klog, lex_now).get('smoke:once')}")

    write_json(lex_path, json.loads(saved[0].decode("utf-8")))
    write_json(klog_path, json.loads(saved[1].decode("utf-8")))


def s69_two_readers_two_tickets(sb: Path):
    """The ticket is split by audience (2026-08-21). Anna's load was measured at
    25.8k tokens before he spoke, and the ticket was 8.3k of it — of which the
    Vocabulary Fence alone was 65%, a studio input no protocol file asks Anna to
    read, and the SLIP LEDGER was a verbatim second copy of what `status`
    already gave him that same session.

    THE SILENT NO-OP, and it runs in the expensive direction: if the fence stops
    reaching the DIRECTOR, nothing raises. The studio still writes an episode,
    still lints, still renders, still publishes — it just quietly stops building
    dialogue from words Andrew knows, and comprehension-as-heard drifts down
    over a run of episodes with every instrument green. So this asserts the
    fence is PRESENT for the studio path, not merely absent from Anna's.

    The mirror failure is the ledger going missing from BOTH surfaces at once,
    which would silently end slip-steered teaching. `status` is the one that
    keeps it — the knock lane reads that digest too."""
    print("\n69. Two readers, two tickets (2026-08-21)")
    import subprocess as _sp

    # THIS CASE DECLARES ITS OWN DATA (2026-08-24). Three of its assertions —
    # COVERAGE, ENGINES TO FIRE, and the slip ledger on `status` — are about
    # blocks that only PRINT when there is something to print, and the day-zero
    # fixtures are empty. Until now it read whatever the forty cases ahead of it
    # happened to leave in the sandbox, which made it the last case in the suite
    # that could not be reproduced alone. What it seeds is the minimum each block
    # needs and nothing else: a registered fire word (coverage), a pattern not
    # yet cold (an engine), and a tag slipped twice (a REPEATED slip — once is
    # not a pattern, and the ledger says so).
    lex_path, slip_path = sb / "progress" / "lexicon.json", sb / "progress" / "slip_log.json"
    lex = read_json(lex_path)
    lex.setdefault("ஸ்மோக்வார்த்தை", {
        "gloss": "smoke word", "phonetic": ["smoke vaarthai"], "register": "survival",
        "recognition": "comfortable", "production": "hinted", "reps": 2})
    lex.setdefault("frame:smoke-engine", {
        "gloss": "the smoke frame", "phonetic": [], "type": "pattern",
        "recognition": "comfortable", "production": "hinted", "reps": 1})
    write_json(lex_path, lex)
    slips_now = read_json(slip_path)
    for n in (1, 2):   # twice — a slip is REPEATED or it is not on this list
        slips_now.append({"date": date_cls.today().isoformat(), "tag": "smoke-repeat",
                          "said": f"wrong-{n}", "want": "right", "lane": "chat",
                          "note": "seeded by s69 so the ledger has something to report"})
    write_json(slip_path, slips_now)

    def ticket(*args):
        return _sp.run([sys.executable, str(sb / "scripts" / "suggest_targets.py"), *args],
                       cwd=sb, capture_output=True, encoding="utf-8",
                       errors="replace").stdout

    anna, director = ticket(), ticket("--fence")
    check("Anna's ticket drops the Architect's fence", "VOCABULARY FENCE" not in anna)
    # The assertion that matters — the expensive direction.
    check("...and the Director still gets it, or scripts drift off-fence silently",
          "VOCABULARY FENCE" in director, director[-300:])
    check("...so the studio's copy is the strictly larger one",
          len(director) > len(anna), f"anna={len(anna)} director={len(director)}")
    # NOT a size ratio. The first draft asserted anna < director/2, which is true
    # of the live lexicon (2,160 vs 7,614 tokens) and false in a sandbox seeded
    # from the near-empty .example fixtures — a property of the DATA masquerading
    # as a property of the code. What is fixture-independent: the Director's
    # surplus is exactly the fence block and nothing else.
    head = director.index("4. VOCABULARY FENCE")
    check("the Director's extra content IS the fence — the split adds nothing else",
          director[:head].rstrip() == anna.rstrip(),
          "the two tickets diverge somewhere other than the fence")

    # The blocks Andrew kept, and the one he cut (2026-08-21).
    for keep in ("FOCUS SET", "COVERAGE", "NEW CANDIDATES", "ENGINES TO FIRE"):
        check(f"Anna keeps {keep}", keep in anna, anna[:200])
    check("BACKGROUND is not printed to either reader",
          "1b. BACKGROUND" not in anna and "1b. BACKGROUND" not in director)

    # The ledger: exactly one of Anna's two session inputs carries it.
    status = _sp.run([sys.executable, str(sb / "scripts" / "sync_state.py"), "status"],
                     cwd=sb, capture_output=True, encoding="utf-8",
                     errors="replace").stdout
    in_status, in_ticket = "REPEATED SLIPS" in status, "REPEATED SLIPS" in anna
    check("the slip ledger survives — it is still on a surface Anna loads",
          in_status, "the ledger vanished from BOTH inputs")
    check("...and it is not also repeated by the ticket",
          not in_ticket, "the duplicate is back")


def s65_the_ordering_outlives_the_deck(sb: Path):
    """The deck retirement's load-bearing case (2026-08-18). The container
    expired at touchdown; the ORDERING — survival > delight > dessert — is
    durable knowledge about which failures cost most at a table, and retiring
    the one must not delete the other.

    THE TRAP, and why this case was written before a line was removed: tiers
    were computed by joining `curriculum/trip_deck.json` at menu time, keyed on
    `deck == "trip"` membership. 0 of 339 lexicon rows carried a `register`.
    Delete the deck without migrating and the ordering vanishes SILENTLY — the
    selector keeps returning rows, they are simply no longer tier-ordered.
    Nothing raises, no list is empty, every instrument reads green. That is the
    exact silent-no-op class Gate 7.2 exists for, so the assertions below are on
    rows that carry a `register` and NO `deck` tag at all: the shape every row
    has after retirement, and the shape that had no test before it."""
    print("\n65. The ordering outlives the deck (2026-08-18)")
    st = importlib.import_module("suggest_targets")
    today = date_cls.today()
    ago = lambda n: (today - timedelta(days=n)).isoformat()

    def row(**kw):
        base = {"gloss": "x", "phonetic": [], "type": "chunk",
                "recognition": "comfortable", "production": "none",
                "seen_in": [1], "last_surfaced": ago(10), "reps": 1}
        base.update(kw)
        return base

    # No `deck` key anywhere in this fixture. Equal staleness, equal reps: the
    # register is the ONLY thing that can separate these.
    lex = {
        "smoke:ord-dessert": row(register="zinger"),
        "smoke:ord-survival": row(register="antifreeze"),
        "smoke:ord-delight": row(register="social"),
        "smoke:ord-plain": row(),                      # no register at all
    }
    focus, _bg = st.floor_gap_targets(lex, today, 12, asked={}, cohort=["smoke:ord-plain"])
    order = [t["word"] for t in focus]
    check("a survival-register row leads, with no deck tag in sight",
          order[0] == "smoke:ord-survival", f"got {order}")
    check("...and dessert still sorts last — the whole bar survives",
          order[-1] == "smoke:ord-dessert", f"got {order}")
    check("an unregistered row degrades to delight, not to unreachable",
          "smoke:ord-plain" in order
          and order.index("smoke:ord-delight") < order.index("smoke:ord-dessert"),
          f"got {order}")

    # THE MIGRATION ITSELF: the tier must be read off the row, never joined from
    # a curriculum file. A rank that still needed the deck file would score every
    # row here at the non-member fallback and the ordering would be flat.
    check("the tier is read off the lexicon row, not joined from a deck file",
          st.tier_rank(lex["smoke:ord-survival"]) == 0
          and st.tier_rank(lex["smoke:ord-dessert"]) == 2
          and st.tier_rank(lex["smoke:ord-plain"]) == 1,
          "tier_rank does not read `register`")
    check("the curriculum join is gone — no reader is left to drift",
          not hasattr(st, "deck_registers") and not hasattr(st, "deck_rank"),
          "a deck-keyed reader survived the retirement")

    # THE INVARIANT, stated as the work order stated it: retiring the container
    # must not delete the ordering. A survival row with no deck tag outranks an
    # ordinary row of EQUAL staleness — equal, so nothing but the bar can do it.
    plain, surv = lex["smoke:ord-plain"], lex["smoke:ord-survival"]
    check("survival outranks an ordinary row of equal staleness",
          st.pool_key({"word": "a", "reps": 1, "tier_rank": st.tier_rank(surv)})
          < st.pool_key({"word": "a", "reps": 1, "tier_rank": st.tier_rank(plain)}),
          "the bar does not survive in pool_key")

    # ONE POOL, not three. The deck, the focus set and the going-dark block were
    # separate sections, and the first two claimed primacy in their own words.
    check("the rival selectors are gone, not merely unused",
          not any(hasattr(st, n) for n in ("deck_status", "deck_coverage", "retest_targets")),
          "a retired pool survived")
    check("the knock lane and the session lane read the SAME pool",
          st.drill_menu.__module__ == st.floor_gap_targets.__module__,
          "the menu drifted out of the selector")

    # THE STALE-COHORT HOLE, and why `reseed-focus` exists. Stored membership is
    # the point ("held seats stand regardless of what any counter says") and it
    # is right — but a counter is not the only thing that can change. When the
    # ORDERING changes, a cohort seeded under the old one holds seats the new one
    # would never grant, and `reconcile_focus` cannot fix it: it only fills seats
    # as they OPEN. On 2026-08-18 all twelve were held by unregistered rows
    # seeded before the tier bar existed, so no survival row could enter a pool
    # that ranks them first. Migrating `register` was necessary and not
    # sufficient — this is the other half, and without it the whole retirement is
    # inert in exactly the way Gate 7.2 describes: green, ordered, and unable to
    # act on its own order.
    import contextlib, io
    ss = importlib.import_module("sync_state")
    lex_path, learner_path = sb / "progress" / "lexicon.json", sb / "progress" / "learner.json"
    saved = (lex_path.read_bytes(), learner_path.read_bytes())
    try:
        stale = dict(lex)
        stale.update({f"smoke:ord-held{i}": row() for i in range(st.FOCUS_SIZE)})
        write_json(lex_path, stale)
        learner = read_json(learner_path)
        learner["focus_cohort"] = [f"smoke:ord-held{i}" for i in range(st.FOCUS_SIZE)]
        write_json(learner_path, learner)

        focus, _bg = st.floor_gap_targets(stale, today, st.FOCUS_SIZE,
                                          asked={}, cohort=learner["focus_cohort"])
        check("a stale cohort locks the ordering out — the hole, reproduced",
              "smoke:ord-survival" not in [t["word"] for t in focus],
              "the fixture does not reproduce the stale-cohort hole")

        class A:
            dry_run = True
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ss.cmd_reseed_focus(A())
        check("a dry run writes nothing",
              read_json(learner_path)["focus_cohort"] == learner["focus_cohort"],
              "reseed-focus wrote on a dry run")
        check("...and says what it would do",
              "smoke:ord-survival" in out.getvalue() and "dry run" in out.getvalue(),
              out.getvalue())

        A.dry_run = False
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_reseed_focus(A())
        seated = read_json(learner_path)["focus_cohort"]
        check("the reseed lets the ordering take its seats",
              "smoke:ord-survival" in seated, f"got {seated}")
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_reseed_focus(A())
        check("...and it is idempotent — re-running is not churn",
              read_json(learner_path)["focus_cohort"] == seated,
              "a second reseed moved the cohort")
    finally:
        lex_path.write_bytes(saved[0])
        learner_path.write_bytes(saved[1])


def s76_the_ear_queue_is_not_the_catch_tag(sb: Path):
    """The ear's pool stopped being gated on `direction: "catch"` (2026-08-25).

    The tag answers a PRODUCTION question — never force this to fire — and it was
    also the ear queue's membership test, so a row had to be FORBIDDEN from
    production to be ELIGIBLE for ear work. On the live ledger that day: 21 of 26
    machines fire cold, 3 are solid on the ear, and 5 carried the tag. The axis
    `sync_state status` prints as PRIMARY STEER could reach the ticket with 5 of
    its 26 rows.

    Gate 7.2 — what does this look like when it silently does nothing? A tidy
    eight-row ear block of real, really-stale catch chunks. Nothing errors, every
    row is genuine, and the machines' absence is invisible unless asserted. That
    is the s63 shape one lane over, so this copies s63: reproduce the LIVE
    distribution (catch rows that beat machines on the ordering outright) and
    assert reachability anyway.

    The second half guards the regression the widening CREATES. `due_menu_block`
    had one line for an ear row — "never ask him to fire it" — which is true of a
    catch row and false of a machine Andrew fires cold every session. Widening a
    pool silently widens every law written against it."""
    print("\n76. The ear queue is not the catch tag (2026-08-25)")
    st = importlib.import_module("suggest_targets")
    mk = importlib.import_module("morning_knock")
    today = date_cls(2026, 8, 25)
    row = lambda **kw: {"gloss": "g", "phonetic": ["p"], "seen_in": [], **kw}

    # THE LIVE SHAPE: catch chunks never worked and ancient; machines worked and
    # recent. `coverage_key` leads with fewest-lifetime-reps, so every catch row
    # outranks every machine before the reservation exists.
    lex = {f"catch{i}": row(direction="catch", recognition="struggled",
                            production="none", last_surfaced="2026-06-01")
           for i in range(20)}
    lex.update({f"frame:m{i}": row(type="pattern", direction="fire",
                                   recognition="struggled", production="cold",
                                   last_surfaced="2026-08-24")
                for i in range(6)})
    reps = {f"frame:m{i}": 5 for i in range(6)}

    ear = st.ear_targets(lex, today=today, reps=reps)
    shown = ear["pending"][:8]
    frames = [t for t in shown if t["kind"] == "frame"]
    check("the machines are on the block despite losing the ordering outright",
          len(frames) == st.EAR_PATTERN_SLOTS,
          f"{len(frames)} of {[t['word'] for t in shown]}")
    check("...and the catch rows keep the rest of the seats",
          len(shown) - len(frames) == 8 - st.EAR_PATTERN_SLOTS, str(len(shown)))
    check("a machine is NOT marked ear-only — the tag is a row property",
          all(not t["ear_only"] for t in frames), str(frames[:1]))
    check("...and a catch row still is",
          all(t["ear_only"] for t in shown if t["kind"] != "frame"))

    # A FLOOR, NEVER A CEILING — when machines win on merit, do not cap them back.
    flip = {f"catch{i}": row(direction="catch", recognition="struggled",
                             production="none", last_surfaced="2026-08-24")
            for i in range(20)}
    flip.update({f"frame:m{i}": row(type="pattern", direction="fire",
                                    recognition="struggled", production="cold",
                                    last_surfaced="2026-06-01")
                 for i in range(6)})
    won = [t for t in st.ear_targets(flip, today=today)["pending"][:8]
           if t["kind"] == "frame"]
    check("machines that win on merit are not capped at the reservation",
          len(won) == 6, f"{len(won)} machines won seats")

    # THE MET-ONLY RULE, TRIED AND REVERTED THE SAME DAY. Excluding never-surfaced
    # rows (the callbacks' rule) emptied the pool `remaining_room` reads to decide
    # the eavesdrop cadence is overdue — a warning going silent behind a bare
    # `except: pass`. A catch row's first contact IS the eavesdrop dose.
    unmet = {"catch:new": row(direction="catch", recognition="struggled",
                              production="none", last_surfaced=None)}
    check("a never-surfaced catch row stays in the queue — eavesdrop is its first contact",
          [t["word"] for t in st.ear_targets(unmet, today=today)["pending"]] == ["catch:new"])
    check("...and it is still what the cadence warning counts",
          "1 catch item(s) pending" in _room_for(mk, sb, unmet),
          _room_for(mk, sb, unmet))

    # THE LAW THE WIDENING WOULD HAVE OVERWRITTEN. The block needs one drillable
    # fire word or `due_menu_block` returns empty and both checks below pass on a
    # string that was never rendered — a green case proving nothing, which is the
    # very shape this file exists to refuse.
    menu_lex = dict(lex)
    menu_lex["smoke:fire"] = row(recognition="comfortable", production="none",
                                 register="survival", last_surfaced="2026-08-01")
    menu = _menu_for(mk, sb, menu_lex)
    behind = [ln for ln in menu.splitlines() if "[ear-behind]" in ln]
    check("the machine reaches the knock menu as its own kind of ear row",
          len(behind) == 1, menu)
    check("...and it did NOT take both slots — the catch pair keeps one",
          len([ln for ln in menu.splitlines() if "[ear-only]" in ln or "[pair]" in ln]) == 1,
          menu)
    check("...and that line never tells Anna not to fire it",
          behind and "never ask him to fire it" not in behind[0], str(behind))
    check("...it says the ear is behind, and a fire there earns no ear credit",
          behind and "EAR is what is behind" in behind[0]
          and "no ear credit" in behind[0], str(behind))


def _sandbox_lexicon(mod, sb: Path, lex: dict, fn):
    """Run `fn()` with the sandbox lexicon replaced, then put it back."""
    lex_path = sb / "progress" / "lexicon.json"
    saved = lex_path.read_bytes()
    real = mod.LEXICON_PATH
    try:
        mod.LEXICON_PATH = lex_path
        write_json(lex_path, lex)
        return fn()
    finally:
        mod.LEXICON_PATH = real
        lex_path.write_bytes(saved)


def _menu_for(mk, sb: Path, lex: dict) -> str:
    return _sandbox_lexicon(mk, sb, lex, lambda: mk.due_menu_block())


def _room_for(mk, sb: Path, lex: dict) -> str:
    real_last = mk.last_eavesdrop
    try:
        mk.last_eavesdrop = lambda klog: None
        return _sandbox_lexicon(
            mk, sb, lex,
            lambda: mk.remaining_room([], datetime.now(timezone.utc).astimezone()))
    finally:
        mk.last_eavesdrop = real_last


def s77_the_wild_line_reaches_the_session(sb: Path):
    """What Andrew heard out there reaches the session brief (2026-08-25).

    The channel existed for months and the consumption did not: `[heard]` lines
    land in `feedback_log.json`, which only the `@build` diagnosis pass reads.
    The 2026-08-19 entry — "apora wandete", both words already in the lexicon, one
    at `comfortable` after 22 sessions — diagnosed the segmentation gap and the
    stale phonetics, and did it weeks after the moment had passed.

    Gate 7.2 — what does this look like when it silently does nothing? A brief that
    renders perfectly with no wild-line block, which is byte-identical to a week in
    which he heard nothing worth reporting. Absence of a prompt is indistinguishable
    from absence of input, and the reader is one prefix typo away from that state
    forever. So this drives the REAL writer, re-reads the REAL brief, and asserts
    the line is on it — the round-trip s41 was written for after a green case tested
    a function whose write path deleted the field.

    It also asserts the CLOSE, because an open loop nothing can discharge is noise
    by construction and gets walked past for mechanical reasons."""
    print("\n77. The wild line reaches the session (2026-08-25)")
    import contextlib
    ss = importlib.import_module("sync_state")
    sb_mod = importlib.import_module("session_brief")

    def feedback(note: str):
        class A:
            pass
        A.note = note
        with contextlib.redirect_stdout(io.StringIO()):
            ss.cmd_feedback(A())

    def brief() -> str:
        out = io.StringIO()
        real = sb_mod.git_sync_counts
        try:
            sb_mod.git_sync_counts = lambda: (0, 0)
            with contextlib.redirect_stdout(out):
                sb_mod.cmd_status(argparse.Namespace())
        finally:
            sb_mod.git_sync_counts = real
        return out.getvalue()

    fb_path = sb / "progress" / "feedback_log.json"
    saved = fb_path.read_bytes()
    try:
        write_json(fb_path, [])
        check("no wild lines, no block — quiet is earned, not accidental",
              "HEARD IN THE WILD" not in brief())

        feedback("[heard] apora wandete")
        page = brief()
        check("a wild line reaches the brief through the real writer",
              "HEARD IN THE WILD" in page and "apora wandete" in page, page[-600:])
        check("...and the brief says DECODE, never grade — it is not a test of him",
              "decode it, never grade it" in page, page[-600:])

        feedback("[heard] enna sonninga")
        check("a second one queues rather than replacing the first",
              brief().count("·") >= 2)

        feedback("[heard-worked] apora wandete")
        page = brief()
        check("working it closes it", "apora wandete" not in page, page[-600:])
        check("...and closing one does not close the others",
              "enna sonninga" in page, page[-600:])

        # An ordinary feedback note must not be dragged in — the log is shared, and
        # a reader that matched everything would bury the signal it exists to raise.
        feedback("the podcast felt long today")
        check("a plain feedback note is not a wild line",
              "podcast felt long" not in brief())
    finally:
        fb_path.write_bytes(saved)


def s79_a_rating_lands_or_says_why(sb: Path):
    """The soak rating reaches the ledger, and a bad one refuses (2026-08-27).

    This lane replaces the `listens` counter retired the same day. That counter's
    defect was not that it was wrong — it was that it could not BE wrong out loud:
    self-report went blind on 2026-06-30 and kept publishing a number for two
    months, which was then read as audience data.

    So the case that matters here is the refusal. The rating arrives unattended
    from a phone, through a workflow nobody watches, and the parse is the fragile
    part precisely because it was moved off the phone to be testable. A rating
    silently filed as 0/5 would steer the Diagnosis pass while looking exactly
    like a rating that never arrived — the retired counter's failure wearing a
    new hat.

    Drives the REAL writer and re-reads the REAL ledger, per s41: a green parse
    proves nothing if the write path drops it."""
    print("\n79. A rating lands, or says why (2026-08-27)")
    import contextlib
    ss = importlib.import_module("sync_state")

    def rate(mission: str, stars: str):
        """Returns (exit_code, stdout). Non-zero is the loud refusal."""
        out = io.StringIO()
        args = argparse.Namespace(mission=mission, stars=stars, commit=False)
        try:
            with contextlib.redirect_stdout(out):
                ss.cmd_rate_episode(args)
            return 0, out.getvalue()
        except SystemExit as e:
            return e.code or 1, out.getvalue()

    def ledger():
        return read_json(sb / "progress" / "feedback_log.json") or []

    fb_path = sb / "progress" / "feedback_log.json"
    eps_path = sb / "progress" / "episodes.json"
    saved_fb, saved_eps = fb_path.read_bytes(), eps_path.read_bytes()
    try:
        write_json(fb_path, [])
        write_json(eps_path, {"90": {"title": "Mission tier2_mission90",
                                     "words": [], "duration_min": 3.0}})

        # The phone sends whole picker rows — never a bare number.
        code, out = rate("90 — Mission tier2_mission90", "4 ★★★★")
        check("a whole picker row parses to its leading integer", code == 0, out)
        log = ledger()
        check("...and the note is IN the ledger, re-read from disk", len(log) == 1, str(log))
        note = log[0]["note"] if log else ""
        check("...carrying the mission, the title and the score",
              "M90" in note and "tier2_mission90" in note and "4/5" in note, note)
        check("...tagged so the Diagnosis pass can find the lane",
              note.startswith("[soak rating]"), note)

        # THE FIRST REAL RATING FAILED HERE (run 33057942609): the phone sent
        # '⭐️⭐️⭐️' — no leading digit, because that is what a person builds when
        # told to make five star rows. The label list is the one surface in this
        # lane with no test around it, so the parser widened rather than the human.
        # U+2B50 carries a trailing U+FE0F, so len() would score this 3 as a 6.
        for label, row, want in (
                ("emoji stars with variation selectors", "⭐️⭐️⭐️", 3),
                ("bare emoji stars", "⭐⭐", 2),
                ("the ★ form the walkthrough specified", "★★★★★", 5),
                ("a leading digit still wins over the glyphs", "4 ★★", 4),
        ):
            write_json(fb_path, [])
            code, out = rate("90 — Mission tier2_mission90", row)
            got = (ledger()[0]["note"] if ledger() else "")
            check(f"{label} scores {want}/5",
                  code == 0 and f"{want}/5" in got, out or got)

        # ── The refusals. Each must exit non-zero AND write nothing. ──
        for label, mission, stars in (
                ("an unparseable mission row", "Mission tier2_mission90", "4 ★★★★"),
                ("a mission with no episode",  "404 — ghost",             "4 ★★★★"),
                ("a zero-star payload",        "90 — Mission",            "0"),
                ("a six-star payload",         "90 — Mission",            "6 ★★★★★★"),
                ("an empty star row",          "90 — Mission",            ""),
        ):
            before = len(ledger())
            code, out = rate(mission, stars)
            check(f"{label} REFUSES loudly", code != 0, out or "(silent)")
            check("...and files nothing", len(ledger()) == before, str(ledger()))
    finally:
        fb_path.write_bytes(saved_fb)
        eps_path.write_bytes(saved_eps)
