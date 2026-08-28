---
name: backport
description: Milestone re-extraction from Tamil (the reference implementation) into the language-tutor template repo. Use when Andrew says "backport", "sync the template", or a milestone worth porting has landed. Policy is milestone re-extraction — never per-fix backports.
---

# Backport — Milestone Re-extraction to language-tutor

Policy (`docs/DECISIONS.md` 2026-07-06 + 2026-07-10): the template
(`../language-tutor`, github.com/arosselet/language-tutor) syncs by **milestone
re-extraction, never per-fix**. This skill replaces the by-hand diff walk of
2026-07-16 with a bounded procedure.

## 1. Scope the delta

```
git tag -l 'template-v*-source' | sort -V | tail -1        # last sync point
git log --oneline <last-tag>..HEAD
git diff --stat <last-tag>..HEAD -- scripts/ .github/ .claude/skills/
```

No milestone-sized story in that log → stop; say so. Per-fix syncing is the
rejected approach, not a smaller version of this one.

## 2. Classify every changed file by the seam law

| Bucket | What it looks like | Fate in the template |
|---|---|---|
| **Mechanism** | `scripts/*.py` logic, workflows, smoke cases, the @build/recalibrate skills | Ports as code — generalize names, zero Tamil literals |
| **Anna's choice** | Tunables (volley size, cooldown days, voice picks) | Ports as a dial in `config/tutor.json`, never hard-coded |
| **Language law** | Everything in `scripts/language.py`, the Tamil prose rules in `mandates.py`, dialect/persona/hosts prose | Ports as a documented **slot** (`config/tutor.json`, `.template` files) — port the seam, never the Tamil value. Since 2026-08-28 the code half is ONE file: read it, don't hunt for it |
| **Personal / local** | `progress/`, `content/`, `published_audio/`, `run_studio.py` + its writer wiring | **Never ports** |

`/extend` Gate 6 lists the three port-surface items invisible to a
swap-the-md-files pass — check each one against the delta.

**Stop-condition:** a change that doesn't classify cleanly into one bucket goes
to Andrew with the question, not into the template on a guess.

## 3. Apply in the template

Work inside `../language-tutor`. Every ported mechanism carries its smoke case
with it; finish with the template's own smoke test (the Spanish fixture) green.

## 4. Tag and record

```
git tag template-v<N+1>-source        # in Tamil, at the synced commit
git push --tags
```

One `/distill` entry in **both** repos' DECISIONS: the milestone, the new tag,
anything deliberately left behind.
