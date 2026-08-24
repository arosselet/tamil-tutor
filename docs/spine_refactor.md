# The Spine Refactor — implementation plan

> **STATUS 2026-08-24 (end of day): Phase 1 COMPLETE and merged (Steps 0-7). Q1 is
> most of the way there. Q2's real defect is fixed and its file split is optional.**
> Everything below this block is the plan *as written on 08-23* and is superseded by
> this status wherever the two disagree — it is kept as the record of what was planned
> and why, not as instructions. Five corrections are worth carrying forward.
>
> 1. **Step 2 was not test-neutral.** The suite reaches six moved names as module
>    ATTRIBUTES, which `from X import name` does not cover. 26 addresses moved.
>    The freeze held where it mattered — no case's assertions changed — but "exactly
>    two edits" was wrong about the file: address moves happened in Steps 2, 4, 5
>    and 6, and two source-text greps in `s3`/`s9` were re-pointed at the property
>    they were always testing.
> 2. **H1 arrives in Step 5, not Q1.** Moving the commit and push inside
>    `publish()` breaks 60 stubs at once, so `publish()` owns the feed and the
>    commit ORDERING, and both calls stay at the lane's seam.
> 3. **Q2's premise was measurably wrong** — 68 of 70 cases already ran alone. The
>    fix was stub teardown (`run()`), not the file split. Every case passes alone
>    now, `smoke_test.py s41` runs one, and `s32`/`s8`/`s43` have the teeth §4b
>    asked for. **Still open in Q2: the per-layer file split, now optional.**
> 4. **Q1's open question 1 has an answer, and it is neither (a) nor (b): the seam
>    is an ARGUMENT.** `lanes.deliver_rendered` takes `commit` and `notify` as
>    keyword-only parameters with no defaults, so a lane resolves its own binding
>    at call time and its stub still intercepts. Both import styles coexist and
>    lanes migrate one at a time, which is what decoupled Q1 from Q2 for real.
>    Landed under Q1: all 13 prompt constants in `mandates.py` (`knock_reply`
>    785 -> 570); the write -> render -> publish tail, shared by `render_soak`,
>    `render_drill` and `render_longhaul`; "a derived file follows its source"
>    inside `publish()`, retiring four hand-written copies; and `push_queue`'s
>    "no writer" invariant read off its SOURCE by `s70` instead of merely asserted
>    in this document.
> 5. **§4b's family table puts `run_studio` in the write -> render -> publish
>    family; it is not on that family's tail and should not be.** It shells out to
>    `render_audio.py`, which owns the state write and the commit, so there is no
>    `deliver_rendered` call to make. §4b said as much in prose ("a pipeline of
>    passes, not one call") and the table disagreed with it.
>
> **Still open, in the order the ceiling law would take them:**
>
> - **`run_studio.py` is at 430/430 — zero headroom, and Q1's "done means" says it
>   should be off that ceiling.** It is not, and it cannot be bought with the shared
>   tail (see correction 5) — Step 4's consolidation returned exactly the one line it
>   spent. Its own budget note says the next move is a SPLIT, and that the raise is
>   Andrew's call, not a diff's. Nothing here should raise it quietly.
> - **`publish.py` is at 148/150** — two lines of headroom on a file two days old.
>   The next invariant that lands there needs a re-census in the same diff.
> - **The decide/judge family has no runner.** `morning_knock` and `knock_reply` are
>   the daily drivers and still carry their own tails.
> - **Lanes eight and nine** (media ingestion, the daily catch channel) — Q1's open
>   question 3 is still open. Writing ONE against the new shape is the honest test.
> - **Q2's per-layer file split**, optional since the isolation fix.
>
> **Closed since the 08-23 plan, beyond Phase 1:** the port surface really is one line
> now (`state_io.TAMIL_RE` / `TAMIL_RUN`; §3 promised 4 copies -> 1 and the spine
> refactor left three behind), guarded by `s70`; `s70`'s client allowlist no longer
> names lanes that stopped building clients in Step 4.

> **As written 2026-08-23 — superseded by the status above, kept as the record of what
> was planned and why.** Written from the read-only architecture pass of the same day,
> when nothing in the repo had been changed for it. The four scope decisions were
> answered the same day and are recorded in §8.
>
> **Phase 1 (§4) was the build session: Steps 0–7, numbered in the order they run.**
> **Phase 2 (§4b) was queued for later:** Q1 (lanes as declarations) and Q2 (smoke
> consolidation) — both real and wanted, neither started at the time of writing.
>
> **What this is:** a sequence of *moves* — functions that already exist, relocated so
> something else can stop keeping its own copy. **What it is not:** a redesign, a config
> layer, a domain-pack extraction, or any change to `protocol/`, the schemas, Anna's
> behaviour, or the pedagogy. Every step is independently shippable and revertible.
>
> Companion: `docs/DECISIONS.md` (the 23 prior entries this retires as a class) and
> `docs/PROTOCOL_MAP.md` (the map this updates on completion).

---

## 0. If you were told "execute `docs/spine_refactor.md`"

You are wearing the **`@build`** hat, not Anna. Do not load the persona or open a session.

1. Read `AGENTS.md`, then `docs/DECISIONS.md` → "How to work on this system". If this
   repo is unfamiliar, run `/orient` first.
2. Run `/extend` and pass its gates before writing code. Every step below names what it
   replaces, which is Gate 1; the rest still apply.
3. **Do Phase 1 (§4), Steps 0 through 7, in the order written. Stop at Step 7.** Phase 2
   (§4b) is scoped but explicitly not this session — do not start Q1 or Q2, and do not
   drift into them because a file looks inviting while you are already in it.
4. **The smoke suite is frozen.** Exactly two edits are permitted, both named in the plan:
   the three `rephrase_phonetic` stub sites (Step 3) and the duplicate `s59` renumber
   (Step 7). *A case that needs editing to pass is a behaviour change, not a move* — stop
   and say so rather than editing the case.
5. Run the verification ladder (§6) after **every** step, not at the end. `pyflakes` is
   rung 1 and it is the cheapest signal you have.
6. Andrew is at the laptop. This is exploratory-but-settled work: the scope decisions in
   §8 are answered, so do not re-open them, but surface anything the plan got factually
   wrong the moment you find it rather than working around it.

**If a step turns out to be wrong**, that is expected and useful — the plan was written
from a read-only pass, so it can be wrong about a detail. Say what you found, propose the
correction, and get agreement before improvising. Do not silently take a different route.

---

## 1. Why now

Not taste. Three instruments the repo already built are reading at the redline.

### The code ceiling is hit, exactly, on two files

| file | code lines / budget | headroom |
|---|---|---|
| `scripts/morning_knock.py` | **637 / 637** | **0** |
| `scripts/run_studio.py` | **429 / 429** | **0** |
| `scripts/render_drill.py` | 217 / 220 | 3 |
| `scripts/writer.py` | 70 / 75 | 5 |
| `scripts/knock_reply.py` | 774 / 785 | 11 |

The next line of mechanism in `morning_knock.py` is a red build. The law for that
situation is already settled and says what to do: *"a file that keeps hitting its
ceiling is carrying crud or doing two jobs — a split-or-retire signal"* (2026-07-16),
*"a mandate at its ceiling gets split, not raised"* (2026-07-24), and `knock_reply`'s
own budget comment reads **"NOTE for the next raise: REFUSE it and split instead."**
`morning_knock` made this exact move once already — 700 to 625 when `OUTREACH_MANDATE`
left for `mandates.py`, re-censused DOWN afterwards (2026-08-01).

### 36% of `morning_knock.py` is not a knock

424 of its 1,175 raw lines (197 of its 637 code lines) are the OpenRouter config, the
token budget, both JSON parsers, the Tamil-script regex, the phonetic rewriter, the
pinned TTS voices, `load_env`, the git rebase net, `commit_and_push`, `refresh_feed`,
`jsdelivr_url` and `push_to_phone`. Nine of the twenty-one other modules import it;
almost none of them want the knock.

### The drift class is 10% of the ledger, and accelerating

23 of 233 settled decisions are one bug — *a law that should have been one component's
property was written into every lane, and one lane didn't get the memo.* July: 12 of 149
(8%). August: 11 of 67 (16%). The rate doubled as the seventh lane came online, which is
what `O(lanes)` looks like from the inside.

### The 24th instance, found during this pass — act on it either way

**The 2026-08-23 executor rule reached 3 of 8 LLM call sites.** `writer.ask_json` is
"the one place that chooses an executor… never by a lane," and `render_soak`,
`render_drill` and `render_longhaul` were converted. Five sites still open a raw
`OpenAI(...)` client with no host check:

| site | what it is | cost of the gap |
|---|---|---|
| `morning_knock.py:182` | `rephrase_phonetic` — the phonetic rewrite | reachable from **both** `morning_knock.main` and `knock_reply` push-backs; bills cash on the laptop, every time |
| `morning_knock.py:783` | `decide()` — the knock decision | correct in Actions; bills cash on a local `--force` |
| `knock_reply.py:407` | the production judge | same |
| `knock_reply.py:662` | the catch / drift judge | same |
| `run_studio.py:291` | the cloud writer pass | **not a defect** — it has its own host dispatcher (2026-08-18). But that is a *second implementation* of `have_agent()` |

`rephrase_phonetic` is the unambiguous leak: it is a *text* lane, so the JSON-only
framing of the 08-23 entry left it out, and it runs on every knock body and every reply
line that carries script.

**Also found: four copies of the Tamil script range** — `state_io.TAMIL_RE`,
`morning_knock.TAMIL_RUN`, `run_studio.TAMIL_RE`, and an inline `re.findall` at
`run_studio.py:416`. One of the four is the line labelled
`# PORT SURFACE — a fork to another language replaces this regex`.

---

## 2. The law being installed

One sentence, and it is not new — it is stated twice in the repo already, both times for
a single pair of modules, never for the graph:

> **Imports point one way, down the stack. A lower layer never imports a higher one, and
> a channel never owns an invariant that more than one channel obeys.**

- `state_io.py` docstring (2026-08-04): *"Import direction is one-way and must stay that
  way: this module imports from nothing in `scripts/`, and everything else may import
  from it."*
- `DECISIONS.md` (2026-07-25): *"The move is down a layer — outreach may depend on
  selection, never the reverse."*

The stack, bottom to top:

```
L0  state_io      paths, IO, clock, canonical key, the ONE script regex, load_env
L1  selection     coverage_key, focus cohort, menus         (suggest_targets, slips)
L2  policy        rails, verdict caps, teach-first, variety gate, ask cooldown
L3  compose       model config, budget, parsers, prompt assembly, executor (writer.py)
L4  publish       render, feed, push, commit + rebase                      (publish.py)
L5  lanes         knock, reply, queue, soak, drill, long-haul, episode
```

`sync_state.py` is the sole writer and sits beside L1; it may read L0 and L1, and must
stop reaching up to L4 for `commit_and_push`.

---

## 3. What moves, and where

**One new file.** An earlier draft proposed three; consolidating to one is the version
that passes "every addition must earn its place."

| moves | from | to | replaces |
|---|---|---|---|
| `OPENROUTER_BASE`, `MODEL`, `OPENROUTER_MODEL`, `AGENT_MODEL`, `JSON_MODE`, `REASONING_HEADROOM`, `budget()`, `parse_llm_json()`, `parse_llm_response()` | `morning_knock` | **`writer.py`** (exists) | `writer.py`'s upward import of a leaf feature |
| `to_phonetic()`, `rephrase_phonetic()` | `morning_knock` | **`writer.py`** | the 5th un-hosted LLM call site |
| `load_env()`, `UNIONABLE`, `DERIVED`, `_union_conflict`, `_rerender_derived`, `_rebase_onto_main`, `commit_and_push()`, `refresh_feed()`, `jsdelivr_url()`, `REPO`, `KNOCKS_DIR`, `in_waking_window()`, `push_to_phone()`, `BODY_BUDGET`, `over_budget()` | `morning_knock` | **`publish.py`** (NEW) | 26 hand-built commit-path lists; 2 import cycles |
| `ANNA_VOICE`, `EAVESDROP_VOICE` | `morning_knock` | **`render_audio.py`** (exists — owns TTS) | 5 lanes importing voice ids from the knock module |
| the canonical script regex | 4 copies | **`state_io.py`** (the declared port surface) | 3 duplicates |
| `is_unseen()`, `soak_pending()` | `sync_state` | **L0** (`state_io.py` or a peer) | the last import cycle |

**Projected code lines after the moves:**

| file | before | after | budget action |
|---|---|---|---|
| `morning_knock.py` | 637 / 637 | **~440** | re-census DOWN 637 → 450 |
| `writer.py` | 70 / 75 | ~137 | raise 75 → 150, naming what moved in |
| `publish.py` | — | ~132 | new budget 150 |
| `state_io.py` | 50 / 60 | ~53 | unchanged |
| `render_audio.py` | 484 / 500 | ~486 | unchanged |

A budget raise must ride the same diff as the growth, and the commit must name what it
retired (2026-07-16). Here the raises are paid for by a 187-line *reduction* on the file
with zero headroom — the ceiling law working, not an allowance (2026-08-01, *"a ceiling
split re-censuses the budget DOWN"*).

---

## 4. Phase 1 — the build session, in execution order

### Step 0 — preflight (do not skip)

1. `git pull --ff-only` — cloud Anna commits to `main` all day; this must not start behind.
2. `python scripts/smoke_test.py` — record ALL GREEN and the case count. **This is the
   baseline the whole refactor is measured against.** If it is not green before, nothing
   after it is interpretable.
3. `python -m pyflakes scripts/` — expect 0. This is what makes a hard-cut import
   rewrite safe, and it exists *because* the last extraction of this shape (`state_io`,
   2026-08-04) silently dropped the `DEMOTE` table while 53 cases still went green.
4. Branch. Do not work on `main` — the hourly cron writes there.

### Step 1 — the `learner.json` whitelist writer  *(Decision D: merge-write)*

`write_thin_learner` rebuilds the file from a hand-maintained key list, so **a field
omitted from the list is deleted, not left stale.** It has silently eaten state three
times: `slip_closes` (lost for a day — a wiped close is indistinguishable from an
untested one), `slip_commissions` on its first run, and `timezone` / `quiet_until` were
saved only by someone remembering. It carries the comment *"Any future learner-side book
must be added here too"* — prose guarding a data-loss bug — and ten lines above it sits a
re-read loop patching a lost update the same function creates.

Deliberately first: it is independent, it is the only step that touches live learner
state, and landing it while the module graph is still familiar keeps its diff small.

---

### Step 2 — `publish.py`, and `writer.py` absorbs the LLM client

**Test-neutral by construction** (see H1): every consumer uses `from morning_knock import
push_to_phone`, so the name stays bound on the `morning_knock` module object and all 59
of smoke's attribute stubs (`mk.push_to_phone = …`, `kr.commit_and_push = …`,
`pq.render_memo = …`) keep working untouched.

Three commits, green at every point:

- **2a — move.** Create `publish.py`; move the delivery block and the LLM-client block
  out of `morning_knock.py`. `morning_knock` re-imports both, so every existing caller
  still resolves. Smoke must be identical to the Step 0 baseline.
- **2b — rewrite callers.** Point all nine importers at `publish` / `writer` directly.
  pyflakes catches every missed name statically. Smoke.
- **2c — delete the re-exports.** `morning_knock` keeps only what it uses itself.
  **Do not stop at 2b** — a lingering shim is exactly the "load-bearing line that reads
  as dead" of 2026-08-04. The precedent is good: the `state_io` split was migrated clean,
  and a grep today finds **zero** modules still reaching state_io names via `sync_state`.

### Step 3 — the phonetic pair (the one place the moves touch tests)

Moving `to_phonetic` / `rephrase_phonetic` to `writer.py` **does** break stubbing:
`to_phonetic` calls `rephrase_phonetic` as a module global, so once both live in
`writer`, `mk.rephrase_phonetic = stub` no longer intercepts. Three stub sites
(`smoke_test.py:5620, 5631, 5639`) become `writer.rephrase_phonetic`, and
`load_modules()` gains `writer` in its sandbox import list.

Its own commit, so the test edit is legible. This step **moves** the pair and nothing
more — routing it through the host rule happens in Step 4 with the other four call sites
(Decision B), so that "the code moved" and "the executor changed" never share a commit.

### Step 4 — every remaining executor call site, in one pass  *(Decision B)*

All five, together, so the 2026-08-23 rule is finally true as written: `rephrase_phonetic`
(in Step 3), then `decide()`, `judge()` and `judge_catch()` through `writer.ask_json`,
and `run_studio`'s independent host dispatcher collapsed onto `writer.have_agent()`.

Behaviour in Actions is unchanged **by construction** — `have_agent()` is False on a
runner, so the API branch runs exactly as today. What changes is that a local invocation
stops paying cash. `run_studio` is at 429/429 and this step *removes* lines from it.

**Mitigating the risk Andrew accepted:** this touches the knock and reply lanes, which
are the daily drivers. So it lands as **its own commit, after 1c**, never blended into a
move commit — a bisect must be able to separate "the code moved" from "the executor
changed." Verify with `writer.executor_name()` printed at the head of each lane's run,
and with `s70` (the executor-is-chosen-by-the-host case) green unedited.

### Step 5 — one owner for the publish tail

`publish.publish(dose)` owns the sequence the ledger has already had to defend twice:

```
log  →  exposure  →  feed  →  commit  →  push
```

…with the mp3-first commit split preserved (jsDelivr can only serve what is on `main`)
and the retry property preserved (a failed push leaves the entry queued). A lane hands
over *what it produced*; it never hands over an ordering, and it stops building its own
`commit_paths` list.

**Retires as separate rules:** the drain's feed-before-log fork (2026-07-25), the two
unknown audio producers (2026-07-24), the rebase-net bypass (2026-08-20), and
quiet-hours-per-lane (2026-07-26, already half-done inside `push_to_phone`).

**Verification:** the smoke cases that pin publish ordering — `s29` (records the log's
contents at rebuild time, so a rebuild-before-log is red), `s31`, `s9`, `s35` — must stay
green **without being edited**. A case that needs editing means the move changed
behaviour and is wrong.

### Step 6 — break the last import cycle

`sync_state` ↔ `suggest_targets` is the one cycle Step 2 does not fix. `is_unseen()` and
`soak_pending()` are read-only predicates over state that selection needs;
`reconcile_focus()` is a write and stays in `sync_state`. Move the two predicates down to
L0. That deletes the `# lazy: suggest_targets imports us` deferred import at
`sync_state.py:757` and makes the 2026-07-25 law true for the graph rather than one pair.

**Verification:** `python -c "import suggest_targets"` must still work with no OpenAI or
TTS stack importable — that constraint is load-bearing (2026-07-25: *"suggest_targets
must stay importable without the OpenAI/TTS stack, since it is what opens every
session"*). Then `s23`, `s63`, `s69`.

### Step 7 — close-out

The `s59` renumber, the budget re-census (§3), one `DECISIONS.md` entry, and the
`PROTOCOL_MAP.md` update. Full checklist in §9.

---

## 4b. Phase 2 — queued, NOT this session

Numbered `Q` rather than `Step` on purpose: these are real, scoped and wanted, but
nothing in Phase 1 depends on them and neither should be started in the same session.

### Q1 — a lane becomes a declaration  *(QUEUED)*

**The prize.** With Phase 1 landed, a lane stops re-implementing the pipeline and declares
what is different about it. This is what makes lane eight (media ingestion) and lane nine
(the daily catch channel) — both required by `docs/comprehension_plan.md` §6 —
configuration rather than another 350-line copy that has to remember eight invariants.

#### The correction that must survive into this step

**The seven lanes are NOT uniform, and forcing them into one mould breaks a real
invariant.** Measured 2026-08-23 — mandates, schemas, voice references and LLM call sites
per lane — they are **three families**:

| family | lanes | shape |
|---|---|---|
| **write → render → publish** | `render_soak`, `render_drill`, `render_longhaul`, `run_studio` | Python builds a menu, the writer returns a sheet, Python renders and publishes |
| **decide/judge → maybe render → publish** | `morning_knock`, `knock_reply` | the model returns a *decision or a verdict*, not an artifact; rendering is conditional on modality |
| **pure delivery, no writer** | `push_queue` | **0 LLM calls at fire time, by design** — its invariant is *composed at add time, rendered at fire time* (2026-07-24) |

`push_queue` must never be given a writer stage. `run_studio` is markdown-and-print-only
across three passes, not a single JSON call, and its three-pass structure is settled as
earned complexity (2026-07-09) — it declares a *pipeline of passes*, not one call.

**So the target is a shared delivery tail plus three thin family runners, never one
`run_lane()`.** Anything that flattens the three families into one is a regression wearing
a refactor's clothes.

#### The cheap first move, already prescribed

`knock_reply.py` is at **774/785** and holds **five** mandates (`JUDGE`, `THREAD`, `SLIP`,
`REACH`, `CATCH_JUDGE`). Its own budget comment already says what to do:

> *"NOTE for the next raise: REFUSE it and split instead. ~150 of this file's lines are
> prompt strings, which `code_lines` counts as mechanism. `mandates.py` already exists as
> the home for prompt canon — `morning_knock.py` made exactly this move on 2026-08-01 and
> was re-censused DOWN afterwards. This file should follow, not grow again."*

`mandates.py` holds 2 of the repo's 10 mandate constants; the other 8 are scattered across
`knock_reply` (5), `render_drill` (2) and `render_soak` (1). Consolidating them is a pure
move with a written precedent, it buys `knock_reply` ~150 lines of headroom, and it can be
done **before** anything else in Q1 — or as a standalone session of its own.

#### What stays with the lane, and why

**Schemas stay beside their lane.** This is settled, not open: *"each lane declares its own
shape beside itself"* (2026-08-23, "A `--json-schema` must describe a SHAPE"), because a
generic `{"type": "object"}` made `claude -p` return an envelope and a lane rendered an
empty dose with every instrument green. Centralising schemas re-opens that exact bug.

So a lane declares: its **menu builder** (lane-specific Python), its **mandate** (from
`mandates.py`), its **schema** (local, per the rule above), its **voice(s)**, its **push
copy**, and **what it records**. It stops owning: the ordering, the executor, the commit
list, the feed rebuild, the quiet-hours check.

#### The hazard that decides the order — read H1 first

A lane rewritten to call `publish.push_to_phone(…)` instead of
`from publish import push_to_phone` **silently breaks every smoke stub for that name**, and
a stub that stops intercepting means a test hits the real network and a real phone. There
are 59 such stubs. Two ways through, and this is the first thing to settle:

- **(a) Keep the `from X import name` style** through Q1. The suite keeps working
  untouched and Q1 can ship before Q2. Cost: module namespaces stay a little cluttered.
- **(b) Move to module-attribute calls** — cleaner, but then Q2 must come first.

**(a) is the recommendation:** it decouples Q1 from Q2 entirely and preserves the exact
property that made Phase 1 safe.

#### Done means

- A new lane can be added without touching `publish.py`, and reviewing it means reading a
  declaration rather than auditing it against eight invariants.
- `run_studio` is off its 429/429 ceiling; `knock_reply` is off 774/785.
- Smoke case count unchanged, and no case needed editing to pass.
- The three families are still three. Nothing gave `push_queue` a writer.

#### Open before starting

1. Import style (a) or (b) above.
2. Does the mandate consolidation land first, as its own session? (Recommended: yes.)
3. Are lanes eight and nine written *as* the validation of Q1, or after it? Writing one
   against the new shape is the honest test; writing both is scope creep.

### Q2 — smoke by layer  *(QUEUED — the next consolidation pass)*

**The problem, measured.** 7,115 lines — 40% of all Python — and the single most-churned
code file: 83 human commits in 60 days, ahead of `morning_knock` (62) and `sync_state`
(42). Every change to the system is paid for twice.

Four structural defects, each a consequence of the module shape rather than of sloppiness:

1. **One mutable sandbox for all 70 cases.** `make_sandbox()` runs once; every case mutates
   the same `progress/` tree. State leaks forward silently.
2. **Call order is load-bearing.** `main()` is a hand-maintained ordered list carrying
   comments like *"needs the real `push_to_phone` — s3+ stub it out"* and *"ditto: asserts
   on the real payload"*. Four cases are hoisted out of numeric order for that reason
   alone. A case cannot be run in isolation, so a failure cannot be reproduced in one.
3. **Stubs are global and permanent.** 59 attribute assignments (`mk.judge = …`) with no
   teardown. Case N inherits every stub case N−1 installed.
4. **One chokepoint, three stub sites.** `push_to_phone` is stubbed as `mk.push_to_phone`,
   `kr.push_to_phone` *and* `pq.push_to_phone` — the copy-per-lane problem reproduced
   inside the tests.

**Known weak cases, already diagnosed** (`docs/feature_inbox.md`, 2026-07-31 "TESTS WITHOUT
TEETH") — fix these while re-homing; they are why the suite's size does not equal its
strength:

- `s32` pins sort-key comparisons on single calls, but the bug it guards (KF-12) was *45 of
  70 deck items never asked* — a distribution property tested pointwise. `s34` already has
  the right shape (`for _ in range(40)` → "every word is reachable"); copy it.
- `s8` has the identical flaw: the bug was *four lore memos on four consecutive days*, and
  the case tests that a counter counts.
- `render_audio` swallows an unreadable sidecar and falls through to scraping `**bold**`
  words out of the script — a *plausible* word list from the wrong source, silently.

#### The target shape

Per-layer files, each independently runnable, each building its own sandbox from a shared
fixture helper:

```
smoke/_fixtures.py     make_sandbox(), load_modules(), check(), Recorder()
smoke/test_state.py    L0/L1 — ledger, selection, ordering law, coverage
smoke/test_policy.py   L2   — rails, caps, teach-first, cooldowns, variety
smoke/test_compose.py  L3   — parsers, budgets, schemas, executor choice
smoke/test_publish.py  L4   — ordering, feed, rebase net, quiet hours, retry
smoke/test_lanes.py    L5   — per-lane end-to-end
smoke/test_budgets.py  the ratchet: prose, code lines, pyflakes, actionlint
```

**Migration is a re-home, not a rewrite.** Cases move as-is; only their sandbox setup and
stub scoping change. A case whose *assertions* change is a different case and needs its own
justification — these 70 encode 70 real incidents, and a rewrite destroys exactly that.

#### Hard constraints

- **Case count must not drop.** Each encodes a specific incident with a date and a decision
  entry. Retiring one means naming what made it dead.
- **Keep the `sN` identifiers.** `/debug`, `/verify` and DECISIONS entries cite them by
  number (`s29`, `s32`, `s70`); renaming breaks live cross-references. The duplicate `s59`
  is fixed in Phase 1 Step 7 precisely so Q2 does not inherit it.
- **CI stays hermetic** — no ambient credentials; mock `google.auth.default` (2026-07-24).
- **`smoke.yml` keeps running the whole suite.** Per-file running is for the developer.

#### Done means

A single case runs alone, a failure reproduces without its 40 predecessors, adding a lane
means adding a case to one file, and `s32`/`s8` test the distribution property their
incidents actually violated.

**Decided: LAST, never alongside** (Andrew, 2026-08-23) — *"this is a mechanism we'll use
to prevent regression as we change things, but it is a prime candidate for a subsequent
consolidation pass too."* Phase 1 is only provably behaviour-preserving because the
suite is held still; restructuring it at the same time destroys the instrument being used
to verify the change. **Two edits are permitted this session and no more:** the three
`rephrase_phonetic` stub sites (Step 3) and the duplicate `s59` case number.

The duplicate: `s59_transit_bit` and `s59_a_new_record_is_born_reachable` are both
numbered `s59`. Renumber the later one (`s71`) and update `main()`'s call list. Two lines,
and it removes a real collision from the registry before the consolidation pass has to
reason about it.

## 5. Known hazards

**H1 — `from X import name` binds at import time.** This is why Step 2 is test-neutral,
and it is the trap in Q1. As long as a lane does `from publish import push_to_phone`,
the name exists on the *lane's* module object and smoke's 59 attribute stubs keep
working. If a lane is ever rewritten to call `publish.push_to_phone(…)` instead, every
stub for that name silently stops intercepting — and a stub that stops intercepting means
a test hits the real network. **Keep the `from X import name` style at the seams.**

**H2 — the intra-module call graph.** A function that calls another module-global (as
`to_phonetic` calls `rephrase_phonetic`) must move *with* it, or its stub site moves.
Audit pairwise before each move; this is the one class of breakage pyflakes cannot see.

**H3 — the cloud is a live writer.** `anna.yml` runs hourly and invokes exactly four
scripts: `push_queue`, `knock_reply`, `sync_state`, `morning_knock`. All four are touched
by Step 2. A half-migrated `main` is a broken knock. **Land each step as one merge, never
a partial push**, and check `gh run list` after.

**H4 — budgets move in the same diff.** Re-census `morning_knock` DOWN in the same commit
as the split and name what left; a raise for `writer.py` rides the same diff as its
growth (2026-07-16).

**H5 — `.studio.lock`.** Do not run a verification pass while a render is in flight; the
lock is shared and the state tail runs under it.

---

## 6. Verification ladder

Per step, in order — each rung is cheap and catches a different class:

1. `python -m pyflakes scripts/` — 0 findings. Catches every missed import statically,
   without running anything.
2. `python scripts/smoke_test.py` — ALL GREEN, same case count as the Step 0 baseline.
   **A case that needs editing to pass is a behaviour change, not a move.**
3. `python -c "import suggest_targets"` with no OpenAI/TTS stack — the session-open path
   must stay light.
4. One real `--dry-run` per lane touched. Read `/verify` → `references/flags.md` for what
   each actually skips first — `morning_knock --dry-run` writes an MP3.
5. `python scripts/sync_state.py status` — the digest renders, no stale-banner surprise.
6. After merge: `gh run list --limit 5` — the hourly tick is green on the new tree.

---

## 7. Explicitly out of scope

- **`protocol/`.** The prose layer is in better shape than the Python; the constitution
  already separates domain rules (dialect, noun shortcut, woven Thanglish) from
  domain-neutral pedagogy (contact > completion, the Teach Beat, the Contrast Beat, fresh
  execution) without anyone having planned it. Budgets and split-or-retire work there.
- **Any domain-pack / config-layer extraction.** Settled 2026-07-03 ("portability is
  documented, not engineered") and 2026-07-27 ("the second-level extraction may only go
  toward more domains, never more users" — no validating second consumer exists). This
  plan contains no `domain.yaml` and creates no plugin seam. Consolidating four copies of
  the script regex into the file already labelled PORT SURFACE fixes a *misplacement*; it
  does not build an abstraction.
- **The studio's three passes.** Earned complexity, settled 2026-07-09 and re-affirmed
  after a greenfield review mis-read it as cruft.
- **Anna's side.** The session is the agent reading files, and that is correct.
- **The lexicon schema.** 351 rows, six universal fields, clean. Retired-deck leftovers
  (`deck`, `direction` on 83 rows) are cosmetic and can age out.
- **Any pedagogy or curriculum change.** This refactor must be invisible to the learner.

---

## 8. Scope decisions — SETTLED 2026-08-23 (Andrew)

**A. Where do we stop? → the moves only — Phase 1.** The infrastructure split, the
publish owner, the last import cycle. **Q1** (lanes as declarations) is the real payoff
and stays queued: it is only safe once the layers underneath it exist, and this session's
job is to make them exist. **Q2** (smoke) follows Q1, per Decision C.

**B. The remaining executor call sites? → all five, one pass.** Andrew took the wider
option over the cautious one. Accepted risk: it touches the knock and reply lanes.
Mitigation is sequencing, not scope — Step 4 lands as its own commit after 2c so a bisect
separates "the code moved" from "the executor changed."

**C. Smoke frozen? → yes, plus the duplicate `s59`.** Andrew: *"this is a mechanism we'll
use to prevent regression as we change things, but it is a prime candidate for a
subsequent consolidation pass too."* So: frozen as the instrument now, **Q2** queued as
the next pass. Permitted edits this session: the three `rephrase_phonetic` stub sites and
the `s59` renumber. Nothing else.

**D. `learner.json` → merge-write.** `write_thin_learner` loads current state and updates
only the keys it owns. No schema change, structure freeze untouched, and it retires the
re-read loop above it. The by-owner file split stays unbuilt.

### The resulting order for the build session

```
Phase 1 — this session (§4)
  0   preflight: pull, baseline smoke, pyflakes 0, branch
  1   learner.json merge-write          independent; smallest diff, goes first
  2   move to publish.py + writer.py    2a re-export → 2b rewrite → 2c delete shim
  3   the phonetic pair                 3 smoke stub edits, the only ones permitted
  4   every executor call site          own commit — bisectable (Decision B)
  5   publish(dose) owns the tail
  6   is_unseen / soak_pending down to L0
  7   close-out: s59, budgets, DECISIONS, PROTOCOL_MAP

Phase 2 — queued, not this session (§4b)
  Q1  lanes become declarations         needs Phase 1 landed first
  Q2  smoke consolidation               needs Q1 settled; never runs beside anything
```

**Why Q1 and Q2 are out rather than late.** Q1 rewrites all seven lanes, and hazard H1
says a lane rewritten to call `publish.push_to_phone(…)` silently breaks every smoke stub
for that name — so Q1 wants the suite reshaped first, and Q2 wants the layers finished
first. That circularity is exactly why they are separate sessions and not a tail on this
one. Phase 1 breaks the deadlock: it makes the layers real while the suite is held
perfectly still, which is what earns the right to move either of them later.

---

## 9. On completion

- One `DECISIONS.md` entry, not six — naming the law (§2), what it retires (the 23-entry
  class), and the budget re-census. Written when the last in-scope step lands.
- `docs/PROTOCOL_MAP.md` → the "Python brain" paragraph and the module list.
- `/orient` and `/debug` reference any moved function by **name, never line number**
  (2026-08-01).
- `/backport`: this is a mechanism change, so it ports — but by milestone re-extraction
  at the next `template-v*-source` tag, never as a patch (2026-07-06).

---

*Written 2026-08-23 from the same-day architecture pass. Nothing here is settled until
§8 is answered; nothing here has been built.*
