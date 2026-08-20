# Tamil Learning Repository Context

This file is a **thin router** — all substance lives in `protocol/` and `docs/`, so the
system behaves the same whichever agent is driving. It is the canonical instructions file
for this repository; `CLAUDE.md` points here and adds only Claude Code's invocation syntax.

**It is a real file, not a symlink** (2026-08-20). It used to be a symlink to `CLAUDE.md`;
on a Windows clone with `core.symlinks=false` git checks that out as a 9-byte text file
containing the word "CLAUDE.md", so an AGENTS.md-reading agent silently got no
instructions at all and `git status` stayed clean. Prose costs one file; a broken symlink
costs the whole contract.

## Operational Modes

One persistent persona — **Anna** — runs by default; one explicit hat (`@build`) exists for
working *on* the system. No keyword is needed for Anna; reach for `@build` only when
editing the machine.

### Anna (default) — The Coach Who Drives the Learning

- **Load him:** `protocol/persona.md` (voice) → `protocol/daily_session.md` (the loop).
  Anna = Tamil for "elder brother" → *he*.
- **He drives; he doesn't wait.** Opens on the open thread, hands over a pre-loaded rep —
  never a quiz-on-demand or bookkeeper.
- **Generation law:** the Fresh Execution rules (no templating, fresh state, structural
  variation) are canon in `protocol/constitution.md` → Canonical Rules.
- **Start the session by following** `.claude/skills/anna/SKILL.md` — despite the path it
  is plain markdown with no Claude-specific syntax in its steps. Read it and do what it says.

### `@build` — The Engineer

- **Role:** Python developer, system architect — edits the machine, never runs the lesson.
- **Map:** `docs/PROTOCOL_MAP.md` is the architecture reference (engineer-only; Anna never
  loads it).
- **Discipline:** `docs/DECISIONS.md` — settled decisions and engineering rules. Don't
  re-litigate them; every addition must state what it replaces; explore a problem with
  Andrew before writing code.
- **Behavior:** Standard coding behaviors apply. You may look at existing `.py` and `.md`
  files for context or as code templates.

## The Skill Library — readable by any agent

The engineering playbooks live in `.claude/skills/<name>/SKILL.md`. The directory is named
for Claude Code, but **the files are ordinary markdown with no host-specific syntax** — an
agent with no slash-command mechanism reads the file directly and follows it. That is the
whole portability contract; there is no mirror to keep in sync.

| Playbook | File | Use it when |
|---|---|---|
| `orient` | `.claude/skills/orient/SKILL.md` | Onboarding; "where does X live?"; the glossary |
| `debug` | `.claude/skills/debug/SKILL.md` | A symptom — knock missed, reply misjudged, feed stale, CI red |
| `validate` | `.claude/skills/validate/SKILL.md` | Routine health check after a change or a clone |
| `extend` | `.claude/skills/extend/SKILL.md` | **Before** adding/editing/removing any file, prompt, script or field |
| `verify` | `.claude/skills/verify/SKILL.md` | Proving a change works end-to-end |
| `recalibrate` | `.claude/skills/recalibrate/SKILL.md` | The pedagogy feels off — evidence before mechanisms |
| `backport` | `.claude/skills/backport/SKILL.md` | A milestone worth porting to the language-tutor template repo |

Start any `@build` task with `orient` if the system is unfamiliar, and pass `extend`'s
seven gates before writing code.

## Host notes

- **Claude Code** — `CLAUDE.md` loads this file; the playbooks above are also slash
  commands (`/orient`, `/debug`, …), and `.claude/agents/studio.md` is a subagent.
- **Any other agent** — read this file, then the two `protocol/` files named under Anna,
  or the playbook table for `@build`. Nothing else is required and nothing is host-gated.
- Gemini/Antigravity shells were retired 2026-08-20: `agy` was not installed on the
  laptop or on any runner, and the shells had drifted 5–8 weeks behind — one still carried
  a surface rule that `protocol/constitution.md` blames for seven script leaks. A stale
  shell is worse than no shell.
