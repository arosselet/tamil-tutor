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
| **Mechanism** | `scripts/*.py` logic, workflows, smoke cases, the @build/recalibrate skills | Ports as code into its v6 module (core / audio / phone / timeline), names generalized (`tutor`, `learner`), history comments cut to the rule, inside the module's line budget |
| **Anna's choice** | Tunables (reach rails, voice picks, writer models) | Ports as a key in `config/tutor.json`, read only through `scripts/pack.py`, never hard-coded |
| **Language law** | Everything in `scripts/language.py`, the Tamil prose rules in `mandates.py` / `run_studio.py`, dialect/persona/hosts prose | Ports as a **slot**: a config key, an `examples.*` line, or a file in `pack.PROSE_SLOTS`. Port the seam, never the Tamil value. A new lane question lands in `pack.py` answered for BOTH fixtures (distinct and shared script) |
| **Personal / local** | `progress/`, `content/`, `published_audio/`, `ladder.py`'s stated lean, Andrew's incidents | **Never ports**. `ladder.py` changes port as `timeline.py` mechanism; Andrew's lean stays in `config/examples/tamil.json`. (The template's dated schedule predates the 2026-10-08 trip-date retirement — a backport decision.) |

**The v6 seam, name for name** (`language-tutor` `docs/CUSTOMIZATION.md` is the full map):
`language.py` → `pack.py`; `ANNA_VOICE` → `TUTOR_VOICE`; `VOICE_FORM`/`READ_FORM` →
`AUDIO_FORM`/`CHAT_FORM`; `TAMIL_RE` → `language.script_regex`; `TAMIL_TAIL_RE` /
`host_stem`'s pulli → `stem_tail` / `host_tail`; `rails.py` constants → `rails.*`;
`writer.MODEL`/`AGENT_MODEL` → `writer.*`; `ladder.LEADS`/`ROOMS`/`MARKERS` → `timeline.*`.

`/extend` Gate 6 lists the three port-surface items invisible to a
swap-the-md-files pass — check each one against the delta.

**Stop-condition:** a change that doesn't classify cleanly into one bucket goes
to Andrew with the question, not into the template on a guess.

## 3. Apply in the template

Work inside `../language-tutor`. Every ported mechanism carries its smoke case
with it; finish with the template's own smoke suite green against BOTH fixtures
(`config/examples/tamil.json`, distinct script; `spanish.json`, shared script).

## 4. Tag and record

```
git tag template-v<N+1>-source        # in Tamil, at the synced commit
git push --tags
```

One line in **both** repos' `DECISIONS.md`: the milestone, the new tag, anything
deliberately left behind.
