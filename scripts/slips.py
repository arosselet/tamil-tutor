#!/usr/bin/env python3
"""The slip ledger: what Andrew keeps getting wrong, and what to do about it.

A slip is a specific observed mistake — the wrong verb ending, the wrong body of
a verb — logged the moment it happens. One is noise; twice is a pattern, and a
live pattern is the primary signal for what to teach next. The ledger never
forgets: a tag with no recurrence RETIRES rather than disappearing, and a
retired tag that was never confirmed landed comes back as UNVERIFIED.

Split out of `sync_state.py` 2026-08-04. It was always a subsystem living in a
file about something else: eleven functions and three constants that own exactly
one file (progress/slip_log.json) and are reached from three call sites.

Layering: this imports from `state_io` only. `sync_state` imports FROM here
(cmd_update logs and tests slips), so nothing here may import `sync_state`.
"""

import re
from datetime import date, datetime

from state_io import (LEARNER_PATH, LEXICON_PATH, LOCAL_TZ, SLIP_LOG_PATH,
                      build_phonetic_index, load_json, local_today, resolve,
                      save_json)

# How a slip stops being live evidence. After this many days with no recurrence a
# tag RETIRES — it is not "fixed", it is just no longer evidence. Retiring is not
# disappearing: a retired tag that was never confirmed landed comes back as
# UNVERIFIED, a re-eligible check (Andrew, 2026-07-30). The ledger never forgets;
# the SURFACE forgets, and then asks again.
#
# 21 days deliberately matches generate_callbacks.INTERVAL_DAYS["cold"] — a
# pattern and a cold word age on the same clock, so there is one recheck rhythm
# in the system rather than two constants drifting apart.
SLIP_RETIRE_DAYS = 21
# Recurrence that makes a slip a pattern rather than a one-off — the same bar
# protocol/diagnosis.md sets for the system's own bugs: one is noise, two is signal.
SLIP_PATTERN_COUNT = 2




_TAG_RE = re.compile(r"[^a-z0-9]+")


def canon_tag(s: str) -> str:
    """Normalise a slip tag to a stable slug. The JUDGE names the pattern (it owns
    the morphology — same seam as the fired-word contract); Python only makes the
    name comparable, so 'Past tense' and 'past-tense' are one row and not two.

    Deliberately NOT a closed vocabulary. A fixed enum would force every new error
    into a pre-imagined bucket and silently mislabel the ones that matter most —
    the whole point of the ledger is to show a pattern nobody named in advance.
    The cost is drift (two slugs for one pattern), which is visible in the summary
    and cheap for Anna to merge; the cost of an enum is invisible and is not."""
    return _TAG_RE.sub("-", (s or "").strip().casefold()).strip("-")


def parse_slip_args(raw_specs: list[str]) -> list[dict]:
    """CLI `--slip 'tag|said|want|note'` specs → ledger rows. Shared by the
    close's writer AND the commission gate, which must judge the same rows the
    close is about to append — a slip whose second occurrence lands in this very
    close becomes a pattern the gate already has to see."""
    rows = []
    for raw in raw_specs:
        parts = [p.strip() for p in raw.split("|")]
        if not parts or not parts[0]:
            print(f"  ! --slip {raw!r} has no tag before the first '|' — skipped")
            continue
        parts += [""] * (4 - len(parts))
        rows.append({"tag": parts[0], "said": parts[1],
                     "want": parts[2], "note": parts[3]})
    return rows


def append_slips(entries: list[dict], lane: str, modality: str = "",
                 dose_channel: str = "", when: str = "") -> list[dict]:
    """Append structured errors to the slip ledger. THE LEDGER IS APPEND-ONLY —
    nothing here ever rewrites or prunes a row.

    That is the whole reason this file exists rather than a field on learner.json:
    the system's existing error memory was `last_debrief`, a single string
    OVERWRITTEN on every close (2026-07-30 audit), so a mistake survived only as
    long as Anna retyped it. It also never crossed lanes — `daily_session.md`
    drew repairs from "the day's" chat session, and knock corrections lived only
    as prose in knock_log.json that nothing read back. Result: 'romba nalla
    irukku' → 'irundhuchu' was corrected on 07-08, 07-25 and 07-30, near-verbatim,
    with no mechanism able to notice.

    `dose_channel` is the channel of the soak order live when the slip happened —
    the counter behind audio_channels.md's "the same mistake twice through one
    format is that format's answer." That law shipped 2026-07-28 with nothing
    counting formats, so it could never fire.

    `when` overrides the stamped date. Spans and recurrence are computed from it,
    so it must be the date the mistake was MADE, not the date it was recorded: a
    reply typed at 9pm local is judged after midnight UTC on the runner, and
    `local_today()` there files it under tomorrow — the same local-vs-UTC seam
    apply_verdict already handles with `today_local` for capped fires."""
    if not entries:
        return []
    log = load_json(SLIP_LOG_PATH) or []
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    today = when or datetime.now(LOCAL_TZ).date().isoformat()
    # Resolve `want` to a lexicon key here, once, so every caller gets the same
    # answer and the ticket can hang a slip off the floor-gap row it belongs to.
    # An unresolvable want is normal and fine — a slip about an ENDING often has
    # no single word behind it, and the tag carries the meaning regardless.
    lexicon = load_json(LEXICON_PATH) or {}
    phon_index = build_phonetic_index(lexicon)
    written = []
    for e in entries:
        tag = canon_tag(e.get("tag", ""))
        if not tag:
            continue
        if not e.get("word"):
            e = dict(e, word=resolve(e.get("want", ""), lexicon, phon_index) or "")
        row = {
            "at": now,
            "date": today,
            "lane": lane,
            "modality": modality,
            "tag": tag,
            "said": (e.get("said") or "").strip(),
            "want": (e.get("want") or "").strip(),
            "note": (e.get("note") or "").strip(),
            "word": (e.get("word") or "").strip(),
        }
        if dose_channel:
            row["dose_channel"] = dose_channel
        log.append(row)
        written.append(row)
    if written:
        save_json(SLIP_LOG_PATH, log)
    return written


def slip_closes() -> dict[str, str]:
    """tag → the date it was last observed LANDING. Read-side of the only way a
    slip closes: somebody watched him fire it right, unaided, later.

    Stored dated, never as a bare tag. `slips_closed` (a flat list of names,
    2026-07-30, removed the same day) made closing permanent and unfalsifiable —
    a tag on that list could never be live again no matter how often he missed
    it. A date can be voided by a later failure; a name cannot."""
    raw = (load_json(LEARNER_PATH) or {}).get("slip_closes") or {}
    return {canon_tag(k): v for k, v in raw.items() if v}


def slip_commissions() -> dict[str, list[dict]]:
    """tag → the doses built to pay that debt: [{channel, at, payload}, …].

    The missing link (2026-07-31, Andrew). `dose_channel` is stamped onto a slip
    ROW at the instant it is written, from whatever order happened to be standing
    — so `channels` answered "has he ever slipped while SOME order stood", never
    "was a dose built for THIS". Commissioning the right dose could not clear
    NEVER COMMISSIONED; only slipping again could. The flag was cleared by
    failing and ignored by fixing, which is why it became noise to read past.

    Stored like `slip_closes`: on the learner, keyed by canonical tag, dated.
    A list rather than one entry, because trying a SECOND format is exactly the
    event `audio_channels.md`'s escalation law needs to see."""
    raw = (load_json(LEARNER_PATH) or {}).get("slip_commissions") or {}
    return {canon_tag(k): list(v) for k, v in raw.items() if v}


def record_slip_commission(tags: list[str], order: dict,
                           today: str = "") -> list[tuple[str, str]]:
    """Declare that the standing soak order pays off these slip tags.

    The seam that does the work declares it — the same law as the delivery stamp
    (`mark_soak_delivered`) and the exposure stamp. Python cannot infer this: a
    payload word and a slip tag are different vocabularies, and guessing the link
    from word overlap would be a silent wrong answer on exactly the ending-shaped
    slips (1pl-past-om, past-tense) that hang off no single word."""
    today = today or datetime.now(LOCAL_TZ).date().isoformat()
    if not tags:
        return []
    channel = (order or {}).get("channel") or ""
    payload = list((order or {}).get("payload") or [])
    learner = load_json(LEARNER_PATH) or {}
    book = dict(learner.get("slip_commissions") or {})
    out = []
    known = {p["tag"] for p in slip_patterns()}
    for raw in tags:
        tag = canon_tag(raw)
        if not tag:
            out.append((raw, "expected a slip tag"))
            continue
        if not channel:
            out.append((tag, "no soak order is standing — set one in this same call"))
            continue
        # A tag with no ledger history is a typo, and silently booking a
        # commission against it would mark a debt paid that never existed.
        if tag not in known:
            out.append((tag, "no slip logged under that tag — check the spelling"))
            continue
        entries = list(book.get(tag) or [])
        entries.append({"channel": channel, "at": today, "payload": payload})
        book[tag] = entries
        out.append((tag, f"commissioned via the {channel} lane"))
    learner["slip_commissions"] = book
    save_json(LEARNER_PATH, learner)
    return out


def record_slip_test(results: list[str], today: str = "") -> list[tuple[str, str, str]]:
    """Log the OUTCOME of putting a retired slip to the test: 'tag:landed' or
    'tag:missed'. This is the observation the ledger's own standard demands —
    "a slip is not closed by being corrected; it is closed by firing right,
    unaided, later" — and it is the half that never existed, so nothing could
    ever close except by hand, permanently, on Anna's say-so.

    landed → a dated close. missed → a slip row, because a failed test IS a
    recurrence: it revives the tag, bumps the count, and keeps one ledger rather
    than a second parallel record of the same event.

    Word-anchored slips could in principle close themselves off the lexicon
    going cold; ending-shaped ones (1pl-past-om, past-tense) hang off no row and
    cannot. Rather than build two close paths with different guarantees, both go
    through this one and Anna reports. The weaker guarantee is stated out loud
    in the protocol: this asserts an OBSERVATION, not a verdict."""
    today = today or datetime.now(LOCAL_TZ).date().isoformat()
    learner = load_json(LEARNER_PATH) or {}
    closes = dict(learner.get("slip_closes") or {})
    out, missed = [], []
    for raw in results:
        tag, _, outcome = (raw or "").rpartition(":")
        tag, outcome = canon_tag(tag), outcome.strip().lower()
        if not tag or outcome not in ("landed", "missed"):
            out.append((raw, "bad", "expected 'tag:landed' or 'tag:missed'"))
            continue
        if outcome == "landed":
            closes[tag] = today
            out.append((tag, "landed", f"closed as of {today} — revives if it comes back"))
        else:
            closes.pop(tag, None)
            missed.append({"tag": tag, "said": "", "want": "",
                           "note": "tested and missed — still not landed"})
            out.append((tag, "missed", "still live; the failed test is on the ledger"))
    if missed:
        append_slips(missed, lane="chat", modality="test", when=today)
    learner["slip_closes"] = closes
    learner.pop("slips_closed", None)   # the bare-tag list this replaces
    save_json(LEARNER_PATH, learner)
    return out


def slip_patterns(log: list | None = None, today=None) -> list[dict]:
    """Aggregate the ledger by tag, newest-recurrence first. The MENU, not the
    choice — Python counts and groups; Anna reads the group and decides what it
    means and what to do about it (the 2026-06-17 division of labour).

    Returns one row per tag: how often, over how long, in which lanes, through
    which dose channels, and whether it is still live. `escalate` marks the case
    the channel law cares about — recurred, and every attempt so far went through
    ONE format."""
    log = load_json(SLIP_LOG_PATH) if log is None else log
    log = log or []
    today = today or local_today()
    closes = slip_closes()
    commissions = slip_commissions()
    by_tag: dict[str, dict] = {}
    for row in log:
        tag = row.get("tag")
        if not tag:
            continue
        agg = by_tag.setdefault(tag, {
            "tag": tag, "count": 0, "first": row.get("date"), "last": row.get("date"),
            "lanes": [], "channels": [], "words": [], "examples": [], "notes": [],
            # rows that carry a legacy dose_channel: a slip made WHILE an order
            # stood, which is the pre-2026-07-31 evidence that a dose existed.
            "dosed_rows": [],
        })
        if row.get("dose_channel"):
            agg["dosed_rows"].append((row.get("date") or "", row["dose_channel"],
                                      row.get("lane") or ""))
        agg["count"] += 1
        # first/last are MIN/MAX over the rows, not first-seen/last-seen. The
        # ledger is append-only but not guaranteed date-ordered: append_slips
        # takes a `when` override precisely so a slip is filed under the day the
        # mistake was MADE, and the 07-30 seeding backfilled three weeks of
        # history in one write. A last-seen `last` collapses the span and
        # inflates days_quiet, which can retire a slip that is still live.
        if row.get("date") and row["date"] > (agg["last"] or ""):
            agg["last"] = row["date"]
        if row.get("date") and row["date"] < (agg["first"] or row["date"]):
            agg["first"] = row["date"]
        # `channels` means "formats DECLARED against this tag", and it is filled
        # below from the commission book alone. dose_channel is NOT that: it is
        # whichever order happened to be standing when the slip was made, for
        # some other payload entirely — the noise this file's own header
        # describes. Feeding it in here silently disarmed both gates from
        # 2026-07-31 until 2026-08-20: every slip inherited a channel, so
        # `uncommissioned` could never be true and `escalate`'s one-channel test
        # could never match. It is kept as `dosed_rows` provenance, never as
        # gate input.
        for key, field in (("lanes", "lane"), ("words", "word")):
            v = row.get(field)
            if v and v not in agg[key]:
                agg[key].append(v)
        if row.get("said") or row.get("want"):
            agg["examples"].append((row.get("date"), row.get("said", ""), row.get("want", "")))
        if row.get("note") and row["note"] not in agg["notes"]:
            agg["notes"].append(row["note"])

    out = []
    for agg in by_tag.values():
        try:
            days_quiet = (today - date.fromisoformat(agg["last"])).days
        except (TypeError, ValueError):
            days_quiet = 0
        agg["days_quiet"] = days_quiet
        agg["span_days"] = _span_days(agg["first"], agg["last"])
        # A close is DATED, and a failure after it voids it. That is the whole
        # difference between retiring a pattern and losing it: "he landed it on
        # 08-20" is a claim about 08-20, not about all future time, so a slip
        # that comes back on 09-02 is live again with its history intact. The
        # bare-tag close this replaces (2026-07-30, removed same day) silenced a
        # tag permanently — which muted the single most informative event the
        # ledger can record: a pattern you believed had landed, coming back.
        closed_on = closes.get(agg["tag"], "")
        agg["closed_on"] = closed_on if closed_on and closed_on >= (agg["last"] or "") else ""
        agg["closed"] = bool(agg["closed_on"])
        agg["reopened"] = bool(closed_on) and not agg["closed"]
        agg["live"] = not agg["closed"] and days_quiet <= SLIP_RETIRE_DAYS
        agg["pattern"] = agg["count"] >= SLIP_PATTERN_COUNT
        # RETIRED but never confirmed: quiet long enough to stop being evidence,
        # yet nothing ever observed him getting it right. Silence has two causes
        # — he learned it, or nothing ever asked him — and the ledger cannot tell
        # them apart, so it must not pretend. This surfaces as a re-eligible
        # CHECK rather than vanishing (Andrew, 2026-07-30: "words shouldn't
        # disappear into the aether; they should be retired and then come back").
        # Passive by design: it asks for a test, it does not earn a commission.
        agg["unverified"] = (agg["pattern"] and not agg["live"]
                             and not agg["closed"])
        # Two different failures, two different instructions. NEVER COMMISSIONED
        # means he has been corrected in passing and nothing was ever built for
        # it — the fix is to commission anything at all. ESCALATE means a dose
        # was built, through one format, and he slipped again anyway — that is
        # the audio_channels law, and telling it to "change format" when no
        # format was ever tried would be advice for a problem he doesn't have.
        # Doses DECLARED for this tag (2026-07-31), merged with the legacy
        # dose_channel stamps so "which formats have been tried" is one answer.
        agg["commissions"] = sorted(commissions.get(agg["tag"], []),
                                    key=lambda c: c.get("at") or "")
        for c in agg["commissions"]:
            if c.get("channel") and c["channel"] not in agg["channels"]:
                agg["channels"].append(c["channel"])
        agg["uncommissioned"] = agg["pattern"] and agg["live"] and not agg["channels"]
        # ESCALATE means a dose was built and he slipped ANYWAY — so it needs a
        # slip dated after a dose existed, not merely a dose and a live tag.
        # Only a DECLARED commission counts as "a dose was built": a legacy
        # dose_channel stamp says an unrelated order was standing, which is no
        # evidence that this tag was ever treated. Without the date test,
        # commissioning a debt today would instantly accuse the new dose of
        # having failed, on evidence that predates it.
        dosed_since = min(
            [c["at"] for c in agg["commissions"] if c.get("at")] or [""]) or ""
        agg["slipped_after_dose"] = bool(dosed_since) and (agg["last"] or "") > dosed_since
        agg["escalate"] = (agg["pattern"] and agg["live"]
                           and len(agg["channels"]) == 1
                           and agg["slipped_after_dose"])
        out.append(agg)
    # Live first, then the unverified rechecks, then everything settled.
    out.sort(key=lambda a: (a["live"] and a["pattern"], a["unverified"],
                            a["last"] or "", a["count"]), reverse=True)
    return out


def _span_days(first: str, last: str) -> int:
    try:
        return (date.fromisoformat(last) - date.fromisoformat(first)).days
    except (TypeError, ValueError):
        return 0


def format_slip_block(patterns: list[dict], limit: int = 6) -> list[str]:
    """Render repeated slips for a reader surface. One renderer, three callers
    (status, the knock context, the ticket) — the 07-26 quiet-hours argument:
    four copies of a rule means one of them is the gap, and the gap is the lane
    that fires.

    Two sections, because they carry two different instructions. LIVE is
    evidence and earns a dose. UNVERIFIED is a question — it has gone quiet
    without anyone ever seeing him get it right, and the only honest thing to do
    with it is test it."""
    live = [p for p in patterns if p["live"] and p["pattern"]]
    unverified = [p for p in patterns if p["unverified"]]
    if not live and not unverified:
        return []
    lines = []
    if not live:
        lines.append("No live slips — nothing repeated recently.")
    else:
        lines += ["REPEATED SLIPS — mistakes he has made more than once, newest first.",
                  "  These are the primary signal for what to drill. A slip is not closed by",
                  "  being corrected; it is closed by firing right, unaided, later."]
    for p in live[:limit]:
        when = (f"{p['count']}× over {p['span_days']}d" if p["span_days"]
                else f"{p['count']}×")
        quiet = f", last {p['days_quiet']}d ago" if p["days_quiet"] else ", today"
        lines.append(f"  ⚠ {p['tag']} — {when}{quiet}")
        for d, said, want in p["examples"][-2:]:
            lines.append(f"      {d}: said “{said}” → wanted “{want}”")
        if p["notes"]:
            lines.append(f"      pattern: {p['notes'][-1]}")
        if p.get("commissions"):
            c = p["commissions"][-1]
            lines.append(f"      ✓ dose commissioned {c.get('at','')} "
                         f"({c.get('channel','?')} lane"
                         + (f": {', '.join(c['payload'])}" if c.get("payload") else "")
                         + ") — don't re-order it; test whether it landed.")
        if p["uncommissioned"]:
            # The instruction names the exact flag, because the flag is the only
            # thing that can turn this warning off and prose has already failed
            # here once: daily_session.md sits at its word ceiling and
            # audio_channels.md had a third raise refused in advance, so the
            # place to say it is where the agent is already looking. Same law as
            # the 07-23 scheduling detector — when prose has been walked past,
            # the mechanism carries the rule (2026-07-31).
            lines.append("      ⚠ NEVER COMMISSIONED — corrected in passing every "
                         "time and no dose was ever built for it. This one is owed "
                         "a soak order, not another recast.")
            lines.append(f"        → order it, then DECLARE it in the same close: "
                         f"--soak-payload … --slip-commissioned {p['tag']}")
        elif p["escalate"]:
            lines.append(f"      ⚠ ESCALATE — a {p['channels'][0]} dose was built "
                         f"for this and he slipped again. audio_channels.md: change "
                         f"the format, never loop harder.")
    if len(live) > limit:
        lines.append(f"  … {len(live) - limit} more live slip(s) behind these")
    if unverified:
        lines.append("")
        lines.append("RETIRED BUT UNVERIFIED — quiet, and never once confirmed landed.")
        lines.append("  Silence here has two causes and the ledger cannot tell them apart:")
        lines.append("  he learned it, or nothing ever asked him. Worth a CHECK, not a dose —")
        lines.append("  slip it into a scene and see. Report with --slip-tested tag:landed|missed.")
        for p in unverified[:limit]:
            ago = f"{p['days_quiet']}d quiet" if p["days_quiet"] else "today"
            lines.append(f"  ○ {p['tag']} — {p['count']}× to {p['last']}, {ago}"
                         + ("  · came back after a close" if p["reopened"] else ""))
            for d, said, want in p["examples"][-1:]:
                lines.append(f"      {d}: said “{said}” → wanted “{want}”")
            if p["notes"]:
                lines.append(f"      pattern: {p['notes'][-1]}")
        if len(unverified) > limit:
            lines.append(f"  … {len(unverified) - limit} more unverified behind these")
    return lines


def cmd_slips(args):
    """Read the slip ledger (aggregated), or close a tag by name.

    Capture is NOT here: slips are written by the judge that saw the mistake
    (knock_reply.py) and by `update --slip` at session close, both through
    append_slips(). Reading is the common case — this is Anna's error memory."""
    if args.tested:
        for tag, outcome, msg in record_slip_test(args.tested):
            mark = {"landed": "✓", "missed": "✗", "bad": "!"}[outcome]
            print(f"  {mark} {tag}: {msg}")
        return

    patterns = slip_patterns()
    if not patterns:
        print("No slips logged yet.")
        return
    live = [p for p in patterns if p["live"] and p["pattern"]]
    unver = [p for p in patterns if p["unverified"]]
    print(f"SLIP LEDGER ({sum(p['count'] for p in patterns)} slips, "
          f"{len(patterns)} patterns, {len(live)} live, {len(unver)} awaiting a check):")
    for p in patterns[:args.n]:
        state = ("LIVE" if p["live"] and p["pattern"] else
                 f"closed {p['closed_on']}" if p["closed"] else
                 "UNVERIFIED" if p["unverified"] else
                 "quiet" if not p["live"] else "once")
        print(f"\n  [{state}] {p['tag']} — {p['count']}× "
              f"({p['first']} → {p['last']}, {p['span_days']}d span)")
        if p["lanes"]:
            print(f"        lanes: {', '.join(p['lanes'])}"
                  + (f" · dose channels tried: {', '.join(p['channels'])}"
                     if p["channels"] else " · no dose ever commissioned for it"))
        for d, said, want in p["examples"][-3:]:
            print(f"        {d}: “{said}” → “{want}”")
        if p["notes"]:
            print(f"        pattern: {p['notes'][-1]}")
        for c in p.get("commissions", []):
            print(f"        ✓ dose commissioned {c.get('at','')} via the "
                  f"{c.get('channel','?')} lane"
                  + (f" — {', '.join(c['payload'])}" if c.get("payload") else ""))
        # Provenance only — an order stood on these days, for some other
        # payload. Never evidence that THIS tag was dosed (see slip_patterns).
        if p.get("dosed_rows"):
            print(f"        · slipped while an order stood: "
                  f"{', '.join(f'{d} ({ch})' for d, ch, _ in p['dosed_rows'][-3:])}")
        if p["uncommissioned"]:
            print("        ⚠ NEVER COMMISSIONED — owed a dose, not another recast.")
        elif p["escalate"]:
            print(f"        ⚠ ESCALATE — {p['channels'][0]} was tried; change format.")
        if p["unverified"]:
            print("        ○ never confirmed landed — test it, then --tested "
                  f"{p['tag']}:landed|missed")
        if p["reopened"]:
            print("        ⚠ CAME BACK after being closed — the loudest signal here.")
