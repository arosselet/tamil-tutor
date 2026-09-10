# Ledger audit — how wrong is `recognition`?

> **One-off calibration, drawn 2026-09-10. Not machinery** — no script, no schema, no lane.
> When it has run, this file holds its result and retires; if it ever needs running a second
> time, promote the one-liner below to a command then and not before.

## The question

The ledger reports **37 verified-solid rows** — solid *and* tested. It also holds **211 rows
that have never been tested at all**, every one of them sitting at `struggled`, which is the
correct default ("heard, not yet known") and is *not* a claim that he does not know them.

Nothing downstream can tell "tested and weak" from "never asked". So the headline meters, the
viability floor, and every projection in `comprehension_plan.md` are unreadable until somebody
measures how many of those 211 Andrew already recognises. His own read, 2026-09-09: *"I am
thinking about the gap between what I'm tested on and what I actually know, and I am sure the
latter is larger."*

**This does not test Andrew. It tests the ledger.** Frame it that way in session: a low score
is a fact about the instrument, not about him, and the 2026-08-16 signal is why that framing
is not optional.

## The draw — frozen before the test, and deliberately not written down here

The sample is **committed by hash, not by list**, because Andrew reads this repository and a
list of thirty words with their glosses sitting in `docs/` is an answer key. The draw is
reproducible, so it cannot be quietly redrawn to a friendlier set, and it can be verified
after the fact.

- **Pool:** every lexicon row with `reps == 0`, `production in (none, null)`, and no
  `heard_on`. Sorted, so the ordering is deterministic.
- **Pool size at draw:** 211 · pool sha256 (first 16): `6918c0d2b9c07cbf`
- **Seed:** `ledger-audit-2026-09-10`
- **Sample:** 30 rows — 19 single words, 11 phrases
- **Sample sha256:** `49f205d0d44da516ee83ed9511f37a213ad16602b9553daca262bd00253fc5fa`

Regenerate at session time and check the hash matches before running:

```
python -c "import json,random,hashlib;
rows=json.load(open('progress/lexicon.json',encoding='utf-8'));
never=sorted(k for k,v in rows.items() if (v.get('reps',0) or 0)==0 and v.get('production','none') in ('none',None) and not v.get('heard_on'));
random.seed('ledger-audit-2026-09-10'); pick=sorted(random.sample(never,30));
print(hashlib.sha256('\n'.join(pick).encode()).hexdigest()); print('\n'.join(pick))"
```

If the hash differs, the pool moved between the draw and the run — rows got tested in
between. Say so in the result rather than re-drawing silently; a moved pool is a finding.

## How to run it

Anna's call whether it is **one session (~10 min) or ten across three** — Andrew left that
open, and the ritual matters more than the tidiness of the sample. Either way:

- **Recognition only.** Anna uses the item in an ordinary sentence; Andrew says what it means.
  No production, no spelling, no grading of wording.
- **Never show the list.** One item at a time, in the flow.
- **Three outcomes per item, and the third is the point:** `knows` · `doesn't` · `partial`.
  A phrase he half-parses is real data and must not be rounded either way.
- **It is banter, not a gauntlet.** Lore, a story, a mask — whatever keeps it from reading as
  an exam. It will still feel like one for once; that is the trade, and it happens once.

Log results with the ordinary writers (`--mastered-word` / `--comfortable-word` /
`--stuck-word`), so every item stamps `reps` whichever way it goes and the pool shrinks
honestly.

## Result

_(pending — not yet run)_

| | count | of 30 |
|---|---|---|
| knows | | |
| partial | | |
| doesn't | | |

**Implied verified-solid, extrapolated to the 211:** _(pending)_

**What it changes:** if most come back, the roots checkpoint in `comprehension_plan.md` §5 is
re-based upward and Andrew's instinct is confirmed with a number. If they do not, the daily
input dial set on 2026-09-09 is the right call and the ledger was already honest. Either
answer is worth the ten minutes; the current state — not knowing — is the only one that is not.
