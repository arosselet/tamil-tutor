#!/usr/bin/env python3
"""The weekly reflection — the outreach policy learns from its own logs.

WHAT THIS REPLACES (2026-10-12, Andrew). The knobs that shape outreach — how
many reaches a day, how far apart, how often the tease frame — were constants
tuned by hand, and "reward = Andrew coming back" lived in prose. Each `decide()`
tick re-read what happened (`outcome_memory`) and nothing ever updated what it
should try next. The hand-run reflection of 2026-09-25 showed what a pass over
the logs can find; this makes the pass structural, weekly, and numeric.

THE RETURN IS FIXED, AND IT IS CODE. Per reach old enough to judge:
  engaged — he answered it, or came back (any contact: a reply, a tap, a play,
            a test, a session) within `threads.BACK_DAYS`. The floor: showing up.
  learned — the reach's target word was tested RIGHT within
            `threads.TOUCH_DAYS` after it, on any channel (the judged reply to
            the reach itself counts — that is a reach teaching). The maximand.
Return per reach and learning per reach are those, averaged. No model reads the
logs and no model scores anything: a number a model produced is a vibe.

THE UPDATE RULE. The pass PROPOSES a move per knob from a fixed comparison
(later reaches in a day vs the first; close-gap reaches vs spaced ones; tease
openers vs the rest). A group under `MIN_N` reaches or a gap under `MARGIN` is
noise at this sample size, and the knob is held — said so, never guessed. Moves
are bounded by `rails.POLICY_RAILS`, and nothing applies until Andrew approves
(his call, 2026-10-12). `decide()` reads the digest on every tick after.

  python scripts/reflect.py run [--days 28] [--if-due] [--commit] [--dry-run]
  python scripts/reflect.py                      # the digest + pending moves
  python scripts/reflect.py approve <id>... | all
  python scripts/reflect.py reject <id>... | all
"""
import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import threads
from observations import OBSERVATIONS_PATH
from rails import (MAX_REACHES_PER_DAY, MIN_GAP_HOURS, POLICY_RAILS, TEASE_CAP_PER_6,
                   TEASE_RE, clip)
from state_io import (BASE, KNOCK_LOG_PATH, LOCAL_TZ, POLICY_PATH, SLIP_LOG_PATH,
                      is_fire, load_json, local_date, save_json)

DEFAULTS = {"max_reaches_per_day": MAX_REACHES_PER_DAY, "min_gap_hours": MIN_GAP_HOURS,
            "tease_cap_per_6": TEASE_CAP_PER_6}
WINDOW_DAYS = 28   # four weeks: ~35 reaches at the current cadence
MIN_N = 8          # a smaller group proves nothing; the knob is held
MARGIN = 0.15      # a smaller difference is noise at these sizes; the knob is held
DUE_DAYS = 7
REFLECTIONS_DIR = BASE / "progress" / "reflections"


def target_of(k: dict) -> str:
    thread = k.get("thread") or ""
    return (k.get("expected_target") or k.get("pinned_target")
            or (thread[5:] if thread.startswith("word:") else ""))


def reaches(klog: list, events: list, now: datetime, days: int) -> list[dict]:
    """Every fire in the window old enough to judge, with its two outcomes and
    the facts the rules compare on. Position in the day and the gap before it
    are computed over ALL fires, so a window edge cannot renumber a reach."""
    contact = threads.contact_days(klog, events)
    rights = defaultdict(list)
    for e in events:
        if e.get("kind") == "tested" and e.get("result") == "right" and e.get("at"):
            rights[e.get("word")].append(datetime.fromisoformat(e["at"]))
    since, out, prev, per_day = now - timedelta(days=days), [], None, defaultdict(int)
    for k in (k for k in klog if is_fire(k) and k.get("timestamp")):
        sent, day = datetime.fromisoformat(k["timestamp"]), local_date(k["timestamp"])
        per_day[day] += 1
        gap = (sent - prev).total_seconds() / 3600 if prev else None
        prev = sent
        if sent < since or now - sent < timedelta(days=threads.BACK_DAYS):
            continue
        later = {(day + timedelta(days=i)).isoformat() for i in range(1, threads.BACK_DAYS + 1)}
        window = sent + timedelta(days=threads.TOUCH_DAYS)
        hour = sent.astimezone(LOCAL_TZ).hour
        out.append({
            "modality": k.get("modality") or "unlabelled",
            "engaged": bool(k.get("reply") or k.get("response")) or any(contact.get(d) for d in later),
            "learned": any(sent < at <= window for at in rights.get(target_of(k), [])),
            "weekend": day.weekday() >= 5,
            "slot": "morning" if hour < 12 else "afternoon" if hour < 17 else "evening",
            "nth": per_day[day], "gap": gap,
            "tease": bool(TEASE_RE.search(k.get("body") or "")),
        })
    return out


def rate(rows: list[dict], key: str = "engaged") -> float:
    return sum(r[key] for r in rows) / len(rows) if rows else 0.0


def by(rows: list[dict], field: str) -> str:
    """One digest line's body: each group with enough reaches to say anything."""
    groups = defaultdict(list)
    for r in rows:
        groups[r[field]].append(r)
    shown = sorted(((rate(g), name, len(g)) for name, g in groups.items() if len(g) >= MIN_N),
                   reverse=True)
    small = sum(len(g) for g in groups.values() if len(g) < MIN_N)
    body = " · ".join(f"{name} {r:.0%} ({n})" for r, name, n in shown) or "no group large enough"
    return body + (f" · {small} more in groups under {MIN_N}" if small else "")


def compare(name: str, worse: list, better: list, current, what: str):
    """→ (move, evidence). Move −1/+1 is a step in the knob's ROOM-giving
    direction decided by the caller; 0 holds. Holding is the default answer."""
    if len(worse) < MIN_N or len(better) < MIN_N:
        return 0, f"held — too few reaches to compare {what} ({len(worse)} vs {len(better)}, need {MIN_N})"
    a, b = rate(worse), rate(better)
    if a < b - MARGIN:
        return 1, f"{what}: {a:.0%} of {len(worse)} came back vs {b:.0%} of {len(better)}"
    if a >= b and current != DEFAULTS[name]:
        return -1, f"{what} no longer trail ({a:.0%} vs {b:.0%}) — back toward the default"
    return 0, f"held — {what}: {a:.0%} ({len(worse)}) vs {b:.0%} ({len(better)}), inside ±{MARGIN:.0%}"


def propose(rows: list[dict], params: dict, today: str) -> tuple[list[dict], list[str]]:
    """The fixed comparisons → (bounded proposals, every knob's reason)."""
    cur = {n: params.get(n, d) for n, d in DEFAULTS.items()}
    spaced = cur["min_gap_hours"] + 2
    checks = [
        # name, the group that would argue for LESS outreach, the rest, the
        # direction that gives him room (fewer reaches, a longer gap, less tease)
        ("max_reaches_per_day", [r for r in rows if r["nth"] > 1],
         [r for r in rows if r["nth"] == 1], -1, "later reaches in a day vs the first"),
        ("min_gap_hours", [r for r in rows if r["gap"] is not None and r["gap"] < spaced],
         [r for r in rows if r["gap"] is None or r["gap"] >= spaced], +1,
         f"reaches under {spaced}h after the last vs spaced ones"),
        ("tease_cap_per_6", [r for r in rows if r["tease"]],
         [r for r in rows if not r["tease"]], -1, "tease-frame openers vs the rest"),
    ]
    proposals, reasons = [], []
    for name, worse, better, room, what in checks:
        move, evidence = compare(name, worse, better, cur[name], what)
        step = POLICY_RAILS[name][2]
        # +1 from `compare` means "give him room"; −1 means "back toward default".
        delta = room * step if move == 1 else (
            (step if DEFAULTS[name] > cur[name] else -step) if move == -1 else 0)
        to = clip(name, cur[name] + delta)
        if delta and to == cur[name]:
            evidence += f" — but {name} is already at its bound ({to}); held"
        reasons.append(f"{name} = {cur[name]}: {evidence}")
        if delta and to != cur[name]:
            proposals.append({"id": f"{name}@{today}", "param": name, "from": cur[name],
                              "to": to, "evidence": evidence, "status": "pending"})
    return proposals, reasons


def reflect(now: datetime, days: int) -> dict:
    """One full pass over the logs → the digest, the proposals, and the reasons.
    Pure: `run` decides whether to write."""
    klog = load_json(KNOCK_LOG_PATH) or []
    events = load_json(OBSERVATIONS_PATH) or []
    policy = load_json(POLICY_PATH) or {}
    today = now.astimezone(LOCAL_TZ).date().isoformat()
    rows = reaches(klog, events, now, days)
    since = (now - timedelta(days=days)).astimezone(LOCAL_TZ).date().isoformat()
    slips = [s for s in load_json(SLIP_LOG_PATH) or [] if (s.get("date") or s.get("at") or "") >= since]
    proposals, reasons = propose(rows, policy.get("params") or {}, today)
    lines = [
        f"Return per reach: {rate(rows):.0%} of {len(rows)} reaches over {days}d were followed "
        f"by contact within {threads.BACK_DAYS}d · learning per reach: {rate(rows, 'learned'):.2f} "
        f"(target tested right within {threads.TOUCH_DAYS}d) · {len(slips)} slips logged.",
        f"By kind of reach: {by(rows, 'modality')}.",
        f"By time of day: {by(rows, 'slot')}.",
        f"Weekend vs weekday: {by(rows, 'weekend').replace('True', 'weekend').replace('False', 'weekday')}.",
    ]
    return {"digest": {"at": today, "window_days": days, "reaches": len(rows),
                       "return_per_reach": round(rate(rows), 3),
                       "learning_per_reach": round(rate(rows, "learned"), 3), "lines": lines},
            "proposals": proposals, "reasons": reasons}


def write(result: dict) -> list[Path]:
    """Persist one pass: the digest and new proposals into the policy book
    (older pending proposals are superseded — the newest evidence speaks), and
    a dated markdown file a human can read."""
    policy = load_json(POLICY_PATH) or {}
    policy.setdefault("params", {})
    policy.setdefault("history", [])
    for p in policy.setdefault("proposals", []):
        if p.get("status") == "pending":
            p["status"] = "superseded"
    policy["proposals"] += result["proposals"]
    policy["digest"] = result["digest"]
    save_json(POLICY_PATH, policy)
    d = result["digest"]
    md = REFLECTIONS_DIR / f"{d['at']}-policy.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    moves = [f"- `{p['id']}`: {p['param']} {p['from']} → {p['to']} — {p['evidence']}"
             for p in result["proposals"]] or ["- none: every knob held (reasons below)"]
    md.write_text("\n".join([
        f"# Policy reflection {d['at']} (scripts/reflect.py, {d['window_days']}d window)", "",
        "Computed from knock_log, observations, slip_log and the contact days (which include",
        "session_log). Numbers only; no model read these logs.", "",
        "## Digest (what decide() reads)", "", *[f"- {line}" for line in d["lines"]], "",
        "## Proposed moves (nothing applies until approved: `python scripts/reflect.py approve <id>`)",
        "", *moves, "", "## Every knob's reason", "", *[f"- {r}" for r in result["reasons"]], "",
    ]), encoding="utf-8", newline="\n")
    return [POLICY_PATH, md]


def verdict(ids: list[str], status: str) -> list[dict]:
    """Andrew's pen. Code re-applies the bounds, refuses a proposal whose
    starting value is no longer the live one (approving it would undo a later
    decision), and is loud about an id that does not exist."""
    policy = load_json(POLICY_PATH) or {}
    pending = {p["id"]: p for p in policy.get("proposals") or [] if p.get("status") == "pending"}
    ids = list(pending) if ids == ["all"] else ids
    if (unknown := [i for i in ids if i not in pending]):
        sys.exit(f"❌ no pending proposal: {', '.join(unknown)} — nothing changed.")
    params = policy.setdefault("params", {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for i in ids:
        p = pending[i]
        if status == "approved":
            live = params.get(p["param"], DEFAULTS[p["param"]])
            if live != p["from"]:
                sys.exit(f"❌ {i} is stale: it moves {p['param']} from {p['from']}, but it is "
                         f"{live} now. Re-run `reflect.py run` — nothing changed.")
            params[p["param"]] = clip(p["param"], p["to"])
            policy.setdefault("history", []).append(
                {"param": p["param"], "from": p["from"], "to": params[p["param"]],
                 "at": now, "evidence": p["evidence"]})
        p.update(status=status, decided_at=now)
    save_json(POLICY_PATH, policy)
    return [pending[i] for i in ids]


def main():
    ap = argparse.ArgumentParser(description="The weekly outreach reflection")
    ap.add_argument("verb", nargs="?", default="show", choices=("show", "run", "approve", "reject"))
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--days", type=int, default=WINDOW_DAYS)
    ap.add_argument("--if-due", action="store_true", help=f"skip unless the last digest is {DUE_DAYS}+ days old")
    ap.add_argument("--commit", action="store_true", help="commit and push the digest (CI)")
    ap.add_argument("--dry-run", action="store_true", help="print the pass; write nothing")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    policy = load_json(POLICY_PATH) or {}

    if args.verb == "show":
        for line in (policy.get("digest") or {}).get("lines") or ["(no reflection has run yet)"]:
            print(line)
        pending = [p for p in policy.get("proposals") or [] if p.get("status") == "pending"]
        print(f"\n{len(pending)} move(s) await approval:" if pending else "\nNothing awaits approval.")
        for p in pending:
            print(f"  {p['id']}: {p['param']} {p['from']} → {p['to']} — {p['evidence']}")
        return
    if args.verb in ("approve", "reject"):
        if not args.ids:
            sys.exit(f"❌ {args.verb} needs a proposal id, or `all`.")
        done = verdict(args.ids, "approved" if args.verb == "approve" else "rejected")
        print("\n".join(f"{args.verb}d {p['id']}" for p in done))
        return

    last = (policy.get("digest") or {}).get("at")
    if args.if_due and last and (now.astimezone(LOCAL_TZ).date()
                                 - datetime.fromisoformat(last).date()).days < DUE_DAYS:
        print(f"Reflection not due — last ran {last}.")
        return
    result = reflect(now, args.days)
    print("\n".join(result["digest"]["lines"] + [""] + result["reasons"]))
    for p in result["proposals"]:
        print(f"PROPOSED {p['id']}: {p['param']} {p['from']} → {p['to']}")
    if args.dry_run:
        return
    paths = write(result)
    print(f"→ {', '.join(str(p.relative_to(BASE)) for p in paths)}")
    if args.commit:
        from publish import commit_and_push
        commit_and_push(paths, f"Reflection: weekly policy digest ({result['digest']['at']}, "
                               f"{len(result['proposals'])} move(s) proposed)")


if __name__ == "__main__":
    main()
