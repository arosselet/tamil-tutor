# Podcast Refinement — Residuals (2026-07-19)

> **Status:** the plan is executed and its settled parts live in `docs/DECISIONS.md`
> (three 2026-07-18 entries: the narrated-drama form, script-only narration, the
> re-render/SFX policy). Branch merged. Polyglot v4 is done — the "reps" ear-check fix
> and its re-render rode one commit (`cbc921a`). What remains is Andrew's; **delete
> this file when both boxes are checked.**

- [ ] **Listen-check M68 v2** (`tier2_mission68_v2.mp3`) — SFX cues now render as a
      1.5 s beat; narrator pinned to Charon. If it passes, nothing else to do; if not,
      `/debug` the specific wrongness.
- [ ] **LinkedIn post** — edit voice, then post (draft below). Links in the first
      comment, not the body; weekday morning. Show HN later with `docs/JOURNEY.md`.
      ⚠ **Run `/backport` first** — the post shares the language-tutor template, and
      the delta since `template-v3-source` is milestone-sized (fielding dose, KF-11,
      claim_payload, watchdog, campaign/Teach-Beat protocol, /recalibrate + /backport
      skills). The sync policy's own trigger is "before actively sharing the template."

## Draft (Andrew's voice to edit)

> My in-laws speak Tamil. At their dinner table I've been the ghost — smiling at jokes I
> didn't catch.
>
> So I spent a year building myself a tutor. Not an app — a persistent AI coach with one
> student, living in a git repo. It texts me a challenge at breakfast, judges my typed
> Tamil word by word, and then produces a private podcast that evening that soaks exactly
> what I fumbled that morning. One brain, continuous across every channel; git is its
> save state.
>
> A year of building it solo taught me more about agentic engineering than any work
> project:
>
> 1. LLM is the writer; Python is the brain. Every invariant lives in deterministic
>    code. The model narrates state — it never owns it.
> 2. Separation of concerns applies to prompts. Refactoring one prompt-monolith into
>    single-role files did more for reliability than any model upgrade.
> 3. Meters lie. I rebuilt my headline metric three times; the honest number is always
>    smaller. "Words I can say cold, out loud" outlived every vanity count.
> 4. When a solo project goes quiet, the silence is data. The month I stopped listening
>    was the most information-dense signal the system ever received.
>
> In three weeks I'll be at that table in Coimbatore. The tutor is open source — a Tamil
> reference implementation and a bring-your-own-language template — links in the
> comments.
>
> If you've ever wanted your computer to teach you your family's language: it can. But
> only if you make it honest first.
