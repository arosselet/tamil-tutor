#!/usr/bin/env python3
"""The judge seat — provenance for every target-language string a model drafts.

A string the system publishes is either ATTESTED (every form in it is already in
the ledger) or JUDGED (a reviewer passed it). Nothing else ships. The check is
code, never a prompt instruction: "be careful with inflections" is prose, and
prose is how this hole opened.

WHAT HAPPENED (2026-10-12, Andrew). `render_soak.FOCUS_BRIEF` tells the writer
to "inflect the focus roots freely … including forms not on the list", and
nothing downstream looked at what came back. The ledger is guarded at every
door — code-held pen, validated writes, the three-state evidence law — and the
CONTENT, which is what Andrew actually hears, had no door at all. He is the
learner: he cannot judge a form he is being taught. A wrong ending, delivered
confidently in Anna's voice and replayed across a week of soaks, is learned.

THE SEAT, NOT THE SITTER. The review queue is the seat. Andrew sits in it now
(he can recognise a form even where he cannot produce it); a native speaker
can later. Whoever sits there, the routing below does not change.

WHAT THIS REPLACES: the unchecked hand-off from `write_sheet` to the TTS.

The rating is computed in code, per whitespace chunk of a string:

  low  — every target-script run in it is a form the ledger already holds
         (a lexicon key, a word an observation names, or a form a reviewer
         approved), so it publishes;
  high — anything else: a novel inflection, a new pattern, a typo. Blocked from
         the dose and queued for review.

The corpus check is the first judge and it is deliberately dumb. It will block
correct Tamil (the 2026-07-13 lesson: a lemma-literal lint false-flags right
inflections). That is the trade: a correct form the queue holds costs one
review; a wrong form that ships costs a week of his ear.

  python scripts/provenance.py                 # pending reviews
  python scripts/provenance.py approve <id>... # passes; the form becomes JUDGED
  python scripts/provenance.py reject <id>...  # never ships, never re-queued
"""
import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from language import has_target, target_runs
from mandates import PROVENANCE_JUDGE_MANDATE, REPAIR_MANDATE
from observations import OBSERVATIONS_PATH
from state_io import LEXICON_PATH, REVIEW_QUEUE_PATH, load_json, save_json
from writer import INT, MODEL, STR, arr, ask_json, have_agent, obj

# ── The model half of the seat (2026-10-12, Andrew) ──────────────────────────
# The corpus check knows only Andrew's own words, so on dialogue it cannot tell
# a wrong ending from ordinary Tamil he has not met: measured over everything
# published, half of all tape and episode lines carry an unattested form, and the
# sample was correct colloquial speech. Those lanes need a judge that knows
# Tamil. It is a SECOND model, never the writer: same-family review shares the
# writer's blind spots, which is how the drill lint — the writer's own model,
# passing what it was unsure of — let things through. Probed on M95: five calques
# among 38 unattested lines; sixteen memo lines clean.
#
# Attested lines skip it (a form the books hold needs no opinion). A line the
# judge calls wrong OR unsure is held. A judge that errors or miscounts raises:
# an unverified line is not a verified one (fail-closed, the lint's old law).
CROSS_MODEL = "anthropic/claude-sonnet-5"   # judges where the writer is Gemini
JUDGE_SCHEMA = obj(verdicts=arr(n=INT, verdict=STR, reason=STR))
REPAIR_SCHEMA = obj(fixes=arr(n=INT, line=STR))


def judge_model() -> str:
    """The other family from this host's writer: the laptop writes with Claude
    (`claude -p`), so Gemini judges; the cloud writes with Gemini, so Claude
    judges. Always through the API — the agent path cannot pick its model."""
    return MODEL if have_agent() else CROSS_MODEL


def judge(lines: list[str], meanings: list[str] | None = None) -> list[dict]:
    """One independent verdict per line → [{verdict: ok|wrong|unsure, reason}]."""
    if not lines:
        return []
    meanings = meanings or [""] * len(lines)
    listing = "\n".join(f"{n}. {line}" + (f"\n   meaning: {m}" if m else "")
                        for n, (line, m) in enumerate(zip(lines, meanings), 1))
    verdicts = ask_json(PROVENANCE_JUDGE_MANDATE, listing, JUDGE_SCHEMA, prefer="api",
                        model=judge_model(), answer_tokens=150 + 60 * len(lines)).get("verdicts", [])
    by_n = {v.get("n"): v for v in verdicts}
    if set(by_n) != set(range(1, len(lines) + 1)):
        raise ValueError(f"judge returned {len(by_n)} verdicts for {len(lines)} lines")
    out = []
    for n in range(1, len(lines) + 1):
        verdict = str(by_n[n].get("verdict", "")).strip().lower()
        out.append({"verdict": verdict if verdict in ("ok", "wrong") else "unsure",
                    "reason": by_n[n].get("reason", "") or ""})
    return out


def check_lines(lines: list[str], meanings: list[str] | None = None) -> list[dict]:
    """Every line's provenance → [{status: attested|judged|held|plain, reason}].
    `plain` carries no target language at all; only unattested lines are judged."""
    forms = attested_forms()
    meanings = meanings or [""] * len(lines)
    out = [{"status": "plain" if not has_target(l) else
            "attested" if not unattested(l, forms) else "", "reason": ""} for l in lines]
    todo = [i for i, o in enumerate(out) if not o["status"]]
    for i, v in zip(todo, judge([lines[i] for i in todo], [meanings[i] for i in todo])):
        out[i] = {"status": "judged" if v["verdict"] == "ok" else "held",
                  "reason": f"{v['verdict']}: {v['reason']}"}
    return out


def check_script(lines: list[str], context: str) -> tuple[list[str], list[dict]]:
    """A DIALOGUE: judge, let the writer mend what was flagged once, judge the
    mends → (lines, held). A non-empty `held` means the artifact must not ship;
    each entry is ready for `enqueue`. `context` is the writer's own system
    prompt, so the repair speaks in the same voice the script was written in."""
    verdicts = check_lines(lines)
    flagged = [i for i, v in enumerate(verdicts) if v["status"] == "held"]
    if not flagged:
        return lines, []
    listing = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(lines))
    asks = "\n".join(f"{i + 1}. {verdicts[i]['reason']}" for i in flagged)
    fixes = ask_json(context + "\n\n---\n\n" + REPAIR_MANDATE,
                     f"THE SCRIPT:\n{listing}\n\nFLAGGED LINES:\n{asks}", REPAIR_SCHEMA)
    mended = list(lines)
    for f in fixes.get("fixes", []):
        if isinstance(f.get("n"), int) and f["n"] - 1 in flagged and (f.get("line") or "").strip():
            mended[f["n"] - 1] = f["line"].strip()
    second = check_lines([mended[i] for i in flagged])
    held = [{"form": mended[i], "unattested": unattested(mended[i], attested_forms()),
             "where": "line", "reason": v["reason"]}
            for i, v in zip(flagged, second) if v["status"] == "held"]
    return mended, held


def check_items(items: list[dict], say: str, meaning: str = "") -> tuple[list[dict], list[dict]]:
    """An ITEM list (a drill's answers, a rotation movement's beats): each item
    stands alone, so a held one is dropped and the rest ship → (kept, held)."""
    verdicts = check_lines([i.get(say, "") for i in items],
                           [i.get(meaning, "") for i in items] if meaning else None)
    forms = attested_forms()
    kept = [i for i, v in zip(items, verdicts) if v["status"] != "held"]
    held = [{"form": i[say], "en": i.get(meaning, ""), "unattested": unattested(i[say], forms),
             "where": "item", "reason": v["reason"]}
            for i, v in zip(items, verdicts) if v["status"] == "held"]
    return kept, held


def queue() -> list[dict]:
    return load_json(REVIEW_QUEUE_PATH) or []


def attested_forms() -> set[str]:
    """Every surface form the books hold, as single runs: lexicon keys (a chunk
    key such as a two-word phrase contributes each run), every word an
    observation names, and every form a reviewer approved. Nothing a model
    wrote and nobody checked is in here — earlier episode scripts included."""
    forms = set()
    for key in load_json(LEXICON_PATH) or {}:
        forms.update(target_runs(key))
    for event in load_json(OBSERVATIONS_PATH) or []:
        forms.update(target_runs(event.get("word") or ""))
    for row in queue():
        if row.get("status") == "approved":
            forms.update(target_runs(row["form"]))
    return forms


def unattested(text: str, forms: set[str]) -> list[str]:
    """The runs in `text` the books do not hold. Empty means low risk.

    A chunk written as a bare ENDING ("-x" in a thread label naming a tail) is
    a label, not a word: it passes when some attested form ends in it."""
    out = []
    for chunk in text.split():
        for run in target_runs(chunk):
            if run in forms:
                continue
            if chunk.lstrip("\"'(").startswith("-") and any(f.endswith(run) for f in forms):
                continue
            out.append(run)
    return out


def scrub(text: str, forms: set[str]) -> tuple[str, list[str]]:
    """A FRAME string (title, intro, thread, outro) loses only its unattested
    chunks; the English around them still carries the frame. → (kept, missing)."""
    kept, missing = [], []
    for chunk in text.split():
        bad = unattested(chunk, forms)
        missing += bad
        if not bad:
            kept.append(chunk)
    return " ".join(kept), missing


def _id(form: str) -> str:
    return hashlib.sha1(form.encode("utf-8")).hexdigest()[:10]


def enqueue(rows: list[dict], lane: str, source: str) -> int:
    """Route high-risk strings to the seat → how many were NEW. Keyed on the
    form itself: a form already queued, approved or rejected is not queued
    again, so a re-dispatched order cannot flood the reviewer with repeats."""
    book = queue()
    have = {r["id"] for r in book}
    now = datetime.now().isoformat(timespec="seconds")
    added = 0
    for row in rows:
        rid = _id(row["form"])
        if rid in have:
            continue
        have.add(rid)
        book.append({"id": rid, "form": row["form"], "en": row.get("en", ""),
                     "unattested": row["unattested"], "where": row["where"],
                     "reason": row.get("reason", ""),
                     "lane": lane, "source": source, "queued_at": now,
                     "status": "pending"})
        added += 1
    if added:
        save_json(REVIEW_QUEUE_PATH, book)
    return added


def gate_sheet(sheet: dict, spoken: dict[str, str],
               items_key: str = "say") -> tuple[dict, list[dict]]:
    """Rate every model-drafted string in a cluster sheet → (publishable, held).

    Three treatments, by what the string IS:
      an ITEM is the dose — repeated four times a pass — so any unattested run
        drops it whole;
      a SPOKEN frame line (`spoken` maps its key to the lane's fixed fallback)
        is a sentence, and a sentence with a chunk cut out is broken Tamil in
        Anna's voice — the very thing this gate exists to stop (measured on the
        first live dry-run, 2026-10-12) — so it is replaced whole;
      a LABEL (title, thread) is read or announced, not taught, and loses only
        the unattested chunk.
    `held` is what `enqueue` takes. Pure: the caller decides whether to write."""
    forms = attested_forms()
    held = []
    out = dict(sheet)
    for key in ("title", *spoken):
        if has_target(out.get(key) or ""):
            out[key], missing = scrub(out[key], forms)
            if missing:
                held.append({"form": sheet[key], "unattested": missing, "where": key})
                if key in spoken:
                    out[key] = spoken[key]
    clusters = []
    for c in sheet.get("clusters", []):
        thread, missing = scrub(c.get("thread", ""), forms)
        if missing:
            held.append({"form": c["thread"], "unattested": missing, "where": "thread"})
        kept = []
        for item in c.get("items", []):
            missing = unattested(item.get(items_key, ""), forms)
            if missing:
                held.append({"form": item[items_key], "en": item.get("en", ""),
                             "unattested": missing, "where": "item"})
            else:
                kept.append(item)
        if kept and thread:
            clusters.append({**c, "thread": thread, "items": kept})
    out["clusters"] = clusters
    return out, held


def decide(ids: list[str], status: str) -> list[str]:
    """The reviewer's pen → the ids it changed. An unknown id is reported, never
    skipped quietly: a typo that approves nothing must not read as success."""
    book = queue()
    by_id = {r["id"]: r for r in book}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        sys.exit(f"❌ no such review id: {', '.join(unknown)} — nothing changed.")
    now = datetime.now().isoformat(timespec="seconds")
    for i in ids:
        by_id[i].update(status=status, decided_at=now)
    save_json(REVIEW_QUEUE_PATH, book)
    return ids


def main():
    ap = argparse.ArgumentParser(description="The review queue — the judge seat")
    ap.add_argument("verb", nargs="?", default="list", choices=("list", "approve", "reject"))
    ap.add_argument("ids", nargs="*")
    args = ap.parse_args()
    if args.verb == "list":
        pending = [r for r in queue() if r.get("status") == "pending"]
        if not pending:
            print("Review queue empty — nothing is waiting on a judge.")
        for r in pending:
            gloss = f" — {r['en']}" if r.get("en") else ""
            why = f"\n            judge: {r['reason']}" if r.get("reason") else ""
            print(f"{r['id']}  [{r['lane']}/{r['where']}]  {r['form']}{gloss}"
                  f"\n            unattested: {' '.join(r['unattested'])}{why}")
        return
    if not args.ids:
        sys.exit(f"❌ {args.verb} needs at least one review id.")
    changed = decide(args.ids, "approved" if args.verb == "approve" else "rejected")
    print(f"{args.verb}d {len(changed)}.")


if __name__ == "__main__":
    main()
