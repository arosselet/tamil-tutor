---
name: inbox
description: Drain docs/feature_inbox.md — give every open item in scope a disposition (build, reject, defer), vetted against the live code, state and DECISIONS.md, and close with a summary to Andrew. Use when Andrew says "drain the inbox", "work the queue", or names inbox items to rule on.
---

# Inbox — Drain the Queue

`docs/feature_inbox.md` is one line per idea. It grew to 19k words once because items
went in and nothing came out (compressed 2026-09-10). A drain is the way out: every
item in scope leaves with a disposition, and Andrew hears what happened to each one.
Standing instruction since 2026-10-14 (Andrew, on Rio's filing).

## 0. Scope

Andrew names the scope ("the three newest", "everything from Rio", "the whole queue").
Unscoped, the drain is the whole `## Ideas` list. Items outside the scope are not
touched, re-worded or re-ordered, even when you notice something about them; a finding
on an out-of-scope item goes in the closing summary, not into the file.

Pull first. Filers commit from other machines — the 2026-10-14 items were on origin
and not on the laptop's `main` when the drain began.

## 1. Vet each item before ruling

The filer's evidence is a **claim to verify, not proof**. For each item:

- **Read the owning file** (`docs/PROTOCOL_MAP.md` names it) and the live state it
  talks about. Run the read command if there is one.
- **Grep `docs/DECISIONS.md`** for the subject, and `git log --grep` for it. An idea
  can be already built, already rejected, or already ruled without a DECISIONS line.
- **Check the premise against the tree, not the docstring.** Docstrings go stale too.

Precedent (2026-10-14): the "ladder evidence rule" item quoted `ladder.py`'s
docstring — "that rule is not built yet" — as its premise. Andrew had ruled on 10-09
(commit `652c9ed`: show the books beside the lean, don't automate it) and it had
shipped. Only the docstring and the missing DECISIONS line said otherwise. Ruling
on the docstring would have rebuilt something that already existed.

## 2. One disposition per item

| Disposition | What happens to the line | Where the reasoning goes |
|---|---|---|
| **Build** | Leaves the inbox; gets a `DECISIONS.md` line (or amends the one it completes) | The commit, and the DECISIONS line's clause |
| **Reject** | Deleted, not archived | The commit message and the closing summary |
| **Defer** | Stays, marked `DEFERRED (<date>): <reason>` in its line | The line itself |

A **build** still passes `/extend`. Gate 3 still applies: unless Andrew commissioned
the item in this session, an unexplored build is a decision item (below). Building
something that supersedes a claim adds its `TOMBSTONES` row (`scripts/smoke/ratchets.py`)
in the same diff. One commit per disposition, so `git log` tells each item's story.

**Already built** is a reject of the item ("nothing to build") plus a repair of
whatever made it look unbuilt: the missing DECISIONS line, the stale docstring.

**Modifying an item is allowed, and saying so is required.** If the filer asked for X
and the evidence supports X′, build X′ and name the difference in the commit and the
summary. The failure this gate exists to prevent is **silent partial compliance**:
doing two-thirds of an item, or a softer version of it, and reporting it as done.

## 3. Settled decisions

An item that reopens a `DECISIONS.md` entry needs **new evidence** — something that
was not true or not known on the entry's date. Without it, reject the item and name
the entry it would reopen. With it, the item becomes a decision item: take the entry
and the new evidence to Andrew.

## 4. Decision items

Some items are choices, not tasks ("build X or settle Y"). These drain **only on
Andrew's ruling in the session**. Present the evidence you found and each option with
its cost, recommend one, and ask. Without a ruling, mark it `awaiting Andrew (<date>)`
in its line and leave it open. A ruling you infer from silence or from an old
conversation is not a ruling, but a ruling Andrew already gave on record (a commit,
a DECISIONS line) is: say where it is and ask him to confirm it stands.

## 5. Close with a summary to Andrew

One block, three headings — **Built**, **Rejected**, **Deferred** (plus **Awaiting
you** if any). One line per item: what happened and why, with the commit hash.
Include anything you changed beyond the letter of an item, and anything you noticed
outside the scope. The summary is the point of the drain: an item that leaves the
inbox without Andrew hearing why has just moved its silence somewhere else.

## Budgets

`docs/feature_inbox.md` is 1500 words and a `DECISIONS.md` entry is 70
(`PROSE_BUDGETS`, `DECISION_ENTRY_BUDGET`). Run `python scripts/smoke_test.py` before
each commit; a drain that turns the build red is not a drain.
