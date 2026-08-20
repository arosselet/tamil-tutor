# Tamil Learning Repository Context

**Read `AGENTS.md` in this directory now** — it is the canonical router for this
repository (operational modes, the two hats, the skill library) and it is host-neutral.
This file adds only what is specific to Claude Code.

Previously the two were one file joined by a symlink. That symlink does not survive a
Windows checkout (`core.symlinks=false` writes it as a 9-byte text file), so the
agent-neutral half silently vanished while `git status` stayed clean. One real file plus
this pointer replaces it — there is no content here to drift out of sync (2026-08-20).

## Claude Code specifics

- **Anna** — `/anna`, or read `.claude/skills/anna/SKILL.md`.
- **Studio** — `python scripts/run_studio.py` is the default dispatch;
  `.claude/agents/studio.md` is the subagent fallback when it exits non-zero.
- **Engineering playbooks** are slash commands as well as files: `/orient`, `/debug`,
  `/validate`, `/extend`, `/verify`, `/recalibrate`, `/backport`. The table in `AGENTS.md`
  says when to reach for each. Start any `@build` task with `/orient` if the system is
  unfamiliar, and pass `/extend`'s gates before writing code.
