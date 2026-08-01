# Feature Inbox

Build-itches land here instead of in the codebase. The structure is frozen at **Anna 1.0**; when the urge to re-engineer strikes mid-session, write it here in one line and keep learning. Review deliberately, later — never in the moment. Adding a row of data is learning; changing a schema waits.

## Ideas

- **Post-trip: reseed the focus cohort** (2026-08-01, month-end audit). The stored ≤12
  cohort was seeded pre-sprint and is correctly dormant during it, but the membership is
  stale: 7/12 never worked, none are trip-deck items, zero graduations. When the sprint
  ends, reseed from whatever the post-trip denominator becomes (rides "The post-trip
  horizon gap", DECISIONS 07-27) and verify the reconcile sweep evicted சொல்லுங்க — it
  went cold in-session 08-01 while still holding a seat.

- **THE REPLY PATH CAN DIE AND THE SYSTEM READS IT AS "HE DIDN'T ANSWER"** (2026-07-31,
  found live — Andrew replied twice, to the 17:22 volley and the 22:04 resend, and neither
  produced a `repository_dispatch`). **The dead-token diagnosis is in the session notes; this
  entry is about the part that is ours.** Nothing in the repo failed and nothing warned:
  `knock_log.json` simply carries `reply: null` on those knocks, which is byte-identical to
  a knock he ignored. Downstream, silence is not neutral — it is *data*: `demand_streak`
  counts trailing asks, `recent_ask_counts` demotes items that "got no reply", the deck's
  staleness term reads unanswered asks, and the slip ledger never gets the fires he actually
  made. **So an outage on the inbound leg does not merely lose replies; it writes a false
  portrait of a non-responsive learner into the state that steers selection.** Textbook Gate
  7.2: absence indistinguishable from success, except here the absence is indistinguishable
  from a *learner behaviour* the system then acts on.
  **The asymmetry that makes this cheap to detect:** outbound and inbound both traverse the
  same Home Assistant, so a knock landing on the phone PROVES the middle is alive. Anna
  already computes `hours_since_exchange`. The shape when it comes off the shelf is a
  liveness check, not a new meter — *N consecutive knocks carrying an `expected_target`,
  every one with no inbound event of ANY kind (no ack, no tap, no reply), while knocks are
  still being delivered* is not a quiet learner, it is a broken return path, and it should
  say so on the status line rather than deepening the demand streak. Deliberately NOT built
  tonight: it is a new detector (Gate 2) and the immediate fix is a credential rotation.
  **Second, smaller:** `docs/home_assistant_knock_buttons.md` §1 says "set an expiry you'll
  rotate" and nothing anywhere records WHICH expiry was chosen or when the token was minted.
  A dated line in that doc at rotation time costs nothing and turns a silent outage into a
  calendar entry.

- **RE-RENDER THE ANDREW INTRO AT v8 — next laptop session** (2026-07-31, Andrew).
  The script is v8 (register pass, "state the fact and stop" retired for the Tamil lane);
  the mp3 on the feed is still v7, because the cloud session that wrote v8 has no Google
  credentials (`google_credentials_ready` -> `DefaultCredentialsError`). One command on a
  host that has them:
  `python scripts/render_demo.py content/scripts/special_andrew_intro.md <out>.mp3`
  (never `render_audio.py` — the special_ lane must touch no state and reach no feed).
  **Then the test, which is the actual point:** she has heard v7, so play v8 without
  saying what changed and ask *"does anything sound wrong now"* rather than "is it
  better" — the nine comma-joins are the risk (over-joining trades staccato for the
  breathless run-on of the 2026-07-07 finding), and change #10, the native quotative
  reorder, is the one expected to move the needle. The unruled sheet is in the brief,
  one row per change, ready for the same Oracle sitting as the ல/ள–ர/ற audio A/B.

- **THE TTS OVER-ARTICULATES — a corpus-wide finding wearing a demo's clothes** (2026-07-31,
  Andrew's wife, Coimbatore native, on the rendered Andrew intro: natives mostly do not
  pronounce the ல/ள and ர/ற distinctions, the voice does, and that is what reads as uncanny).
  **Scope first: this is not about the demo.** Episodes, drills, soaks and knock memos all
  route through one `clean_for_tts` in `render_audio.py` and the same Chirp3-HD voices, so
  whatever the fix is, it lands once and covers everything. The pedagogy question it opens is
  bigger than the artefact: Andrew has been training his ear — and his mouth — on a register
  no one at the table speaks, which is the same class of problem as the fridge
  (`குளிர்சாதனப்பெட்டி`), one layer down from the words into the phonemes.
  **The concentration measured on this script, which makes the experiment cheap:** the ழ
  inventory is essentially TWO roots (`தமிழ்`, `எழுது-`) plus `செவ்வாய்க்கிழமை` — 23 tokens,
  3 lemmas. Roughly two-thirds of the ற tokens are ONE morpheme: the present/relative
  participle `-ற-` (`சொல்றேன்`, `பேசுற`, `இருக்கற`, `வர்றதுக்கு`), which recurs every other
  sentence and is a light tap in Coimbatore speech. So the uncanny surface is not diffuse —
  it is one high-frequency suffix and two lemmas.
  **DO NOT respell blind, and do not treat this as settled.** Non-standard orthography
  (`சொல்ரேன்`) may make Chirp3 worse, not better, and no one here can hear the output. The
  cheap honest path is an A/B: render one paragraph both ways at the `clean_for_tts` seam
  behind a flag, and let the Oracle judge — a dialect-realisation call is hers by the same
  law that gave her `சாத்து`. Second lever worth pricing in the same experiment: a different
  voice may already do this, in which case the fix is a constant, not a transform.

- **THE STACCATO IS OURS, NOT THE MODEL'S — why the Tamil reads "composed"** (2026-07-31,
  second half of the native-ear verdict: "sentence structures are mostly good, although they
  are evidently composed by not a native speaker"). **Measured on `special_andrew_intro.md`:
  121 sentences, median 4 words, mean 4.1, 67% at four words or shorter, longest 11.** Clause
  chaining is nearly absent (`-ட்டு` 11, `-னா` 7, `-றப்ப` 0, `-ும்போது` 2) and so are the
  discourse particles a Coimbatore speaker leans on (`ஆமா` 0, `இல்ல?` 0, `தெரியுமா` 0,
  `ஏன்னா` 0, `அதான்` 0). Uniformly short, unchained, unhedged declaratives — which is a very
  good description of "composed by a non-native".
  **The finding is that this is enforced, not emergent.** The script's own banned list says
  *"State the fact and stop"*, no announcing clauses, no `X, not Y` antithesis, no em-dashes.
  Those rules were written to kill LLM-slop rhetoric in the ENGLISH companion demo and were
  carried across to the Tamil lane, where their side effect is a staccato register no one
  speaks. The model is not failing to write natural Tamil; it is obeying a style rule that
  forbids it. **So the cheap move is a brief-level edit, not a rewrite:** keep the ban on
  announcing clauses and antithesis (those are still slop in any language), and lift the
  full-stop rule for the Tamil lane specifically — allow chained clauses and a handful of
  particles. Worth pairing with the render A/B so one Oracle sitting judges both.
  **Third factor, noted and not actionable yet:** both `special_` pieces are MONOLOGUES,
  and this system's founding insight (`JOURNEY.md` ch.2) is that two people chatting is what
  surfaces natural register — a lesson can hide in book Tamil, a conversation cannot. A
  one-voice piece is structurally the form most likely to sound composed. That is a real
  constraint on how natural this artefact can ever get, and it is worth knowing before
  anyone spends effort making a monologue sound spontaneous.

- **TESTS WITHOUT TEETH — a cursory audit, 2026-07-31** (Andrew asked for other axes where a
  case exists but not in the dimension that can fail). Three real findings, none built:
  1. **`render_audio` swallows an UNREADABLE sidecar** (`except (json.JSONDecodeError,
     OSError): pass`, then falls through to scraping `**bold**` words out of the script).
     A corrupt tags file therefore yields a *plausible* word list from a different source,
     silently. This is the same file and the same function the 07-31 pass just made loud
     for *unresolvable keys* — the fix covered the resolvable-but-missing case and left the
     unreadable-file case exactly as it was. Highest blast radius of the three: wrong data,
     not absent data.
  2. **`s32` pins the ordering law, not the property the bug violated.** KF-12 was *45 of
     70 deck items never asked while the meter reported a winning sprint*, and its
     regression case asserts sort-key comparisons on single calls — nothing iterates. The
     floor's twin, `s34`, DOES iterate (`for _ in range(40)` → "every word is reachable",
     "no word is hammered while others wait") because it was written the day after the
     starvation lesson. The deck never got the same treatment. Copy `s34`'s loop into `s32`.
  3. **`s8` (KF-8, lore format takeover) has the same shape.** The bug was *four lore memos
     in four consecutive days*; the case tests that `demand_streak` counts and that the
     cooldown line renders. Nothing simulates N days and asserts no format family exceeds a
     share. Format drift is a distribution property and it is tested pointwise.
  Also measured, for calibration: **22 of 43 smoke cases drive a real command entry point
  AND re-read persisted state.** The other 21 are mostly legitimate pure-function cases
  (`s1` parsing, `s4` normalize, `s18` budgets) — the number is not a defect count, it is
  the denominator to think with when adding the next case.
  **Contained, checked and clean:** `write_thin_learner` is the ONLY whitelist-style writer
  in the codebase (the 07-31 bug class does not have siblings), and the one
  `except Exception: pass` in `morning_knock` is deliberate and correctly commented
  ("never let a cadence check kill a reach") — fail-open on an advisory line, though it
  does mean the eavesdrop-cadence warning can silently never appear.

- **A VOLLEY WHOSE NOTIFICATION IS LOST IS STRANDED BY DESIGN** (2026-07-31, found live —
  Andrew replied to the 17:22 volley and it never reached GitHub). `morning_knock` reads no
  open-volley state: every knock is a fresh decision, so the only re-present path is the
  reply lane (KF-11's chat handler), which needs a reply to arrive — the exact thing that
  was broken. The entry sits at `volley_next: 1` forever, items 2-4 orphaned, and **nothing
  reads "open and stale"**: state is honest, no lane acts on it. Textbook Gate 7.2 —
  indistinguishable from a volley he simply hasn't answered yet. A resend via the queue is
  only a partial recovery (a queued push mints its own `knock_id` and carries no `volley`
  array, so the chain cannot resume). Shape when it comes off the shelf: the rails already
  compute a min-gap, so the cheapest honest version is a rails-side check — an open volley
  older than N hours with no reply is re-presented rather than a new dose being chosen.

- **ORACLE CROSS-POLLINATION — the intro script is a pipeline, not a demo** (2026-07-31,
  Andrew's stated intent; NOT IN SCOPE YET, filed so it isn't re-derived). `special_andrew_intro`
  was never a pocket party trick: the loop is *write a longer script in target Tamil → put a
  numbered question sheet to the Oracle → feed her rulings back into the colloquial engine*.
  Evidence the format works, from this round: she ruled 10, changed 3, and **refused #7** —
  "multiple are correct, but it depends on context" — which is knowledge a generator working
  from a static canon structurally cannot have. Her meta-remark (relayed 07-31, banked in the
  feedback ledger): the agent had *genuinely thought hard*, because several distinctions the
  sheet raised are ones **Tamilians do not consciously notice** — they cling to one form, or a
  form carries a connotation they have never had to name. That is the real asset: the sheet
  surfaces tacit knowledge no corpus holds. **Open questions when this comes off the shelf:**
  where rulings land so they bind generation (`architect.md`? a dialect canon file? lexicon
  connotation fields — a schema change, so frozen), whether a refusal like #7 is storable at
  all or only ever prose, and how a ruling reaches the episode writer without re-litigating
  the fence rules. Do not build before the trip.

- **~~NEVER COMMISSIONED can only be cleared by FAILING again~~ — SHIPPED 2026-07-31 as
  option A (`update --slip-commissioned TAG`), Andrew's choice.** The close now declares
  which debt the order it just set pays off; the flag discharges, the surface reports the
  dose instead of the warning, and ESCALATE waits for a slip dated after the dose rather
  than accusing a brand-new one. **The wiring turned up a worse bug and fixed it:**
  `write_thin_learner` is a WHITELIST and `slip_closes` was not on it, so
  `--slip-tested tag:landed` wrote a close that the very same update deleted — **no slip had
  ever actually closed since that mechanism shipped 2026-07-30**, invisibly, because a wiped
  close looks exactly like never having tested. Smoke `s44`. **STILL OPEN, deliberately:**
  whether the flag should also GATE the close. Worth asking only now that it can be turned
  off; a hard gate on the daily ritual is the kind of mechanism the Enjoyment Clause has
  beaten before, and the softer shapes (print the order it would have written; refuse only
  after N closes) were never tested. Original diagnosis follows.

  **NEVER COMMISSIONED can only be cleared by FAILING again — nothing links a soak order to
  a slip tag (2026-07-31, sharpened by Andrew's question the same evening; supersedes this
  entry's first draft, which called it "a detector with no actuator" and understated it).**
  The trigger: the ledger correctly flagged three uncommissioned slips at the head of the
  status digest and the ticket, Anna read the warning, ran a good session, and still shipped
  no dose — so Andrew had to ask a **second time** for the இருந்துச்சு dose he first asked
  for on 07-25, precisely the failure `audio_channels.md` exists to prevent (*"I shouldn't
  have to beg for a soak or an episode"*, 07-28).

  **But the deeper defect, found when Andrew asked why the session-open drain hadn't covered
  this:** `agg["uncommissioned"] = pattern and live and not agg["channels"]`
  (`sync_state.py:1442`), and `channels` aggregates `dose_channel`, which is stamped onto a
  slip **only at the instant the slip row is written**, copied from whatever soak order
  happened to be standing right then (`sync_state.py:652`, `knock_reply.py:998`). Nothing,
  anywhere, associates a commission with a slip TAG. So the flag does not mean "no dose was
  built for this" — it means "he has never made this mistake while some unrelated order
  happened to be standing." **Commissioning the correct dose cannot clear it; only slipping
  again can.** The flag is cleared by failing and ignored by fixing. Live proof on the day it
  was found: the போனோம் episode shipped and reads `produced ✓`, and both slips it was built
  for still print NEVER COMMISSIONED, permanently. A warning that can never be discharged
  becomes noise that must be learned-past — which is the mechanical reason it got walked
  past, not agent inattention.

  **Distinct from the session-open drain, which works** (verified 2026-07-31: digest said NOT
  YET PRODUCED → `render_soak.py` → tape on the feed → `produced ✓`). The drain PRODUCES an
  order that exists; commissioning WRITES the order. A debt that never became an order is
  invisible to it. Note also that the drain is now the only live door — `studio_watchdog.py`'s
  cron was retired 2026-07-24.

  **Not built, deliberately — Andrew's design call.** Cheapest shape, matching an idiom
  already in the file: `--slip-commissioned TAG` beside the existing
  `--slip-tested TAG:landed|missed`, so the close declares which debt an order pays — the
  same "the seam that does the work declares it" law the delivery stamp follows. The
  alternative, a `for_slip` field on the soak order, is schema and waits on the structure
  freeze. Only ONCE the flag is dischargeable is it worth asking whether it should also gate
  the close; a hard gate on the daily ritual is exactly the kind of mechanism the Enjoyment
  Clause has beaten before. Route through `/recalibrate` — the felt signal is banked verbatim
  in the feedback ledger, second occurrence, past the diagnosis bar.

- **AT THE COMPUTER: finish the Andrew-intro naturalness pass — it is blocked on the Oracle,
  not on work (2026-07-30).** Branch `claude/tamil-intro-naturalness-cr4wy2` carries a
  six-section Coimbatore-ear review of `special_andrew_intro.md`, judged against attested
  spoken usage rather than grammar-book correctness. The confident zero-cost fixes are
  applied and committed; **the script has NOT been re-rendered and the existing
  `published_audio/special_andrew_intro.mp3` is now stale against it.**
  What was wrong, for context on why this is worth finishing: `பேச மாட்டாரு` was negative
  *volition* ("he refuses to speak Tamil") three sentences before the piece hands the
  conversation to a stranger; the நம்ம/நாங்க beat used a third form (`நாம`) for one of the
  two words it was teaching; the counterfactual fronted its quote so a listener could hear
  `என்னோட தப்பு` as *Anna's* fault two lines before the machine is blamed; and
  `plan-க்கு தெரியும்` gave a sheet of paper a dative mind.
  **The blocking step is her ruling on seven register questions**, written up ranked in
  `content/lessons/special_andrew_intro_brief.md` → Open Flag (on that branch). She does not
  need to read the script, only rule on the seven. Top of the list is `பொண்டாட்டி` — blunt
  said about a man to a stranger, and she is the person being named. Then re-render, then
  merge. **Do not merge before the ruling**: it is a public-facing artefact he plays to
  strangers, and three of the seven change what a native hears in the first twenty seconds.

- **A word-adjacent hyphen becomes a SPACE before TTS, so every Tamil suffix written with a
  hyphen reaches the voice as its own word (2026-07-30, found while reviewing the Andrew
  intro; affects EVERY episode, not that one file).** `clean_for_tts` →
  `defang_hyphens` is `re.sub(r"-(?=\w)|(?<=\w)-", " ", text)`. It exists for a good reason
  (the voice reads a glued hyphen as "minus"), but the cure detaches the suffix: `போலாம்-னா`
  went to Chirp3 as `போலாம் னா`, which severs the "X means Y" gloss — and that was on the
  intro's emotional heart, the நம்ம/நாங்க demo. Fixed *in that one file* by fusing to
  `போலாம்னா`, matching the fusion the same script already uses for `இருந்துச்சுன்னா` and
  `வந்தாருன்னா`.
  **The class is unfixed and is house-wide.** Two shapes:
  1. *Tamil root + Tamil suffix* — always fusible, always should be (`ங்க-க்கு` in the
     intro, still open; it is also a consonant pile-up with no boundary for the ear).
  2. *Tamil-script root + Tamil suffix where house convention hyphenates anyway* —
     `டயர்ட்-ஆ`, and the lexicon itself carries `ஃப்ரீ-யா?`, `இட்லி சூப்பர்-ஆ இருக்கு`,
     `வயிறு ஃபுல்-ஆ இருக்கு`. These all detach at render. Fusing them (`டயர்ட்டா`) is
     probably right but changes an orthographic convention that spans the corpus and the
     lexicon keys, so it is **not** a one-off edit.
  English-root cases (`boring-ஆ`, `phone-க்கு`, `machine-ஓட`) detach too but there is no
  better option — a Latin/Tamil-script join with no separator is worse. Cheapest honest
  move is a lint that flags a hyphen with Tamil script on *both* sides (case 1 only, which
  is unambiguous); the case-2 convention question needs Andrew. **No sighting in a lesson
  episode yet** — this was found by reading the render path, so it is latent-by-inspection
  and sits under the one-sighting bar. Worth one deliberate listen for a detached suffix on
  the next episode before spending anything on it.

- **For a `frame:` payload the episode lane SELF-CERTIFIES delivery without evidence
  (sighted 2026-07-28, first real exercise of the repair-first law).** Two defects were
  found by commissioning `frame:youknow-la` as an episode and watching what came back;
  the first is now fixed, the second is schema-adjacent and stays here.
  1. ~~**The ticket has no soak-order section.**~~ **SHIPPED 2026-07-28 evening** as
     `suggest_targets` section **0. THE COMMISSION** — payload, focus, scene_seed and an
     "outranks every list below" heading, printed ahead of everything the ticket computes,
     with the FOCUS SET stating that it is outranked. `episode_commission()` is the one
     predicate; `commissioned_form()` delegates to it and therefore now respects
     `delivered` (a consumed order used to keep pinning the next episode's form). Smoke
     case `s39`. See DECISIONS, "A commission reaches the episode lane as computed
     context". Original report: the Director's only route to the order was one prose clause
     in `DIRECTOR` (*"read the soak-order in progress/learner.json"*), an agentic read
     competing with a code-assembled list headed *"DRILL these until they fire cold"*. It
     lost — the episode dramatised the focus set and the payload was absent — while in the
     SAME run `form: phone_call` arrived through `scene_spec()`/`claim_spec()` as computed
     context and landed perfectly. The repo's own doctrine failing in the direction it
     predicts.
  2. **`claim_payload()` rubber-stamps frames** (`run_studio.py:418`):
     `if key.startswith("frame:") or key in script:` injects into `new_words_landed`
     unconditionally, because a slot template is verbatim-exempt. So a frame payload is
     claimed whether or not one instance is audible; the produced-check then clears, the
     order stamps delivered, and the debt reads PAID with no evidence. Non-frame keys are
     correctly checked and reported. This is the 07-27 judge fix one lane over — crediting
     the target you wanted rather than what actually happened — and it means the ledger can
     book a repair that never shipped. **The hard part is the design, not the patch:** a
     frame has no fixed surface form, which is *why* it is exempt. Verifying it needs a
     pattern the frame record itself carries (e.g. the invariant tail `…ல`), so it is
     schema-adjacent and sits under the structure freeze — hence parked, not fixed.
  Evidence lives in the 07-28 run: the failed Mission 77 sidecar claimed a 28-item payload
  drawn from the focus set with no `frame:youknow-la` in it. Caught only because the writer
  ALSO broke the fourth wall and failed lint on unrelated grounds; had it passed, the debt
  would have been marked delivered. **Correction to the session-log entry at the bottom of
  this file:** it says a `--soak-*`-only call appends a session row. Verified against
  `sync_state.py:617` — the append is conditional on `cold/hinted/demoted/listened/debrief`,
  so a soak-order-only write appends NOTHING. `--debrief`-only does append; that half stands.

- **Audio is a queue-of-one — give it a real queue (2026-07-28, deliberately NOT bundled
  with the repair-first commissioning law that shipped the same day).**
  `learner.json.soak_order` is a single dict: a new order overwrites the old. Text pushes
  have a real queue (`push_queue.py`) with a drain, retries and pacing rails; audio has a
  slot. So exactly one repair per day survives and the rest fall into debrief prose —
  memory for the next *chat*, never a commission. Under the new backward-first rule this
  binds harder, because a day with three unclosed repairs now genuinely wants three orders.
  The shape is already specced below (the `due` field + the hourly tick acting on it,
  dispatching by `channel`). **HOLD** until the prose rule has run several days: if
  backward-first alone closes the felt signal, the queue is machinery Andrew doesn't need,
  and the standing rule is that new engineering starts from a reproduced signal, not a
  plan. Re-open on evidence — a session close where Anna visibly has to *drop* a repair.

- **Scheduled/unattended episode production — DEFERRED 2026-07-27 by Andrew after
  exploring it.** Wanted: Anna (or Andrew) commissions from either machine, it builds and
  publishes at a chosen time, and the phone gets told. Andrew proposed a `push_queue`
  variant; explored and **not** the recommended shape, for three reasons read out of
  `push_queue.py`: the drain runs at the START of every wake-up including every
  lock-screen reply (a memo is ~1 min of TTS, an episode is three LLM passes plus ~10 min
  — Andrew would wait at a blank shade); the drain has no claim/lease, and the known
  double-fire residual costs a duplicate buzz today but would cost two renders, two
  mission numbers and two racing commits for an episode; and every drain gate
  (`MAX_REACHES_PER_DAY`, one-non-forced-per-tick pacing, quiet-hours deferral) is built
  for *reaches*, so an episode would eat a knock slot.

  **The shape that converges with the parked 07-24 plan:** the soak order already IS the
  queue-of-one — payload / scene_seed / focus / channel / form / from / delivered, with
  `soak_pending()` as the predicate and `MAX_UNATTENDED_PER_DAY` as the rail. It needs a
  `due` field and the HOURLY TICK (never the drain) acting on it, dispatching by `channel`
  through the door built 2026-07-27. One field, one workflow step.

  **Two hazards that block anything unattended, whichever shape wins — fix first:**
  1. `run_studio.next_mission()` is `max(glob) + 1` off the local filesystem. A cloud tick
     and a laptop will claim the same number. Impossible today only because laptops are the
     sole producers and Andrew serialises them by hand. Wants claim-by-commit.
  2. `.studio.lock` is a local file lock and **cannot** exclude a GitHub runner from the
     laptop. Nothing serialises two machines today.

  **Recommended first step (also deferred):** a `workflow_dispatch` input that produces ONE
  cloud episode manually — no policy, no tick integration, no autonomy — to hear whether a
  Flash-written episode holds up before Anna may make them unattended. Andrew's own context
  for the deferral: the starvation that motivated auto-production (episodes arriving only
  when he sat for a lesson) has eased because he is showing up reliably now.

  **⚠ THE DEFERRAL'S PREMISE IS CONTRADICTED (2026-07-28) — but this item stays deferred.**
  The daily ritual did land (*"I'm finally getting into a daily ritual of sitting down and
  doing at least one session"*), so the 07-27 reasoning held on its own terms. The
  starvation did not ease, though — it **changed shape**. It is no longer *"episodes arrive
  only when I sit for a lesson"*; it is *"the episodes that arrive don't target the mistakes
  I'm making, and I have to ask for the ones that would."* His reliability cannot fix that
  one: showing up is precisely what generates the errors that go undosed. **This does not
  reopen unattended production** — the new signal is about WHAT gets loaded into the rails,
  not about who pulls the trigger, and the attended session-open dispatch already works.
  Both hazards below (mission-number claim race, cross-machine lock) remain unfixed and
  remain blocking for anything unattended. See "THE REPAIR EARNS THE DOSE" at the top.

- **`inline_canon()` follows references one level deep only (found 2026-07-27).**
  `CANON_REF_RE.findall(prompt)` scans the PROMPT for `protocol/**.md` and inlines those
  files; it does not follow references *inside* them. Safe today only because the studio
  prompts were written to name every file explicitly. Add a "see `hosts.md`" line inside
  `producer.md` and the agy path reads it off disk while the one-shot cloud path silently
  does not — surfacing as a subtly off episode, not an error. Latent, not sighted. Wants a
  lint (or a recursive scan) if episodes ever move to the cloud in earnest.

- **Upsert `word_pool.json` into the lexicon, then retire the file (2026-07-26, Andrew's
  call — supersedes the assistant's "just delete it").** Verified safe: `compute_floor`
  counts only comfortable/solid, and `floor_gap_targets` requires the same, so ~295
  imported rows land inert — no meter moves, nothing floods the drill list, and
  `is_unseen` already means "in the curriculum, never encountered", so teach-first covers
  them on day one. Wins: one store instead of two incompatible schemas, and the 11
  duplicate rows dedupe for free on a keyed upsert. **The one thing that must survive the
  move is `cluster`** — it is what lets intake say "food vocabulary is thin, pull there"
  instead of picking at random; it becomes a lexicon field and
  `new_candidates_by_cluster` reads the lexicon instead of the file. Deliberately NOT done
  in the 07-26 session: it is a 295-row change to Andrew's learning state and the
  focus/background split shipped the same night should be watched for a few real sessions
  first (ship the thin slice, widen after it works). Open sub-question for Andrew: do the
  27 rows already in the lexicon keep their live gloss, or does the pool's gloss win?
  (Recommend: live gloss wins — the pool was never vetted by the Oracle.)

- **CURRICULUM ARCHITECTURE AUDIT (2026-07-26, `/recalibrate`, Andrew's felt signal:
  "the curriculum/deck/machinery/catch-response layers grew by iteration and discovery,
  not top-down design — make the abstraction clean, and don't let the deck starve the
  larger goal").** Third strike on this axis (07-18 "wants curriculum/pedagogy made
  pristine" → 07-25 "we are still starving some of these" → today). The 07-25 ruling fixed
  starvation *inside* the deck; Andrew's question today is about everything outside it,
  which has not been ruled on. Read-only evidence sweep, six findings, ordered by cost:

  1. **The floor selector never got the 07-25 ordering law — this is the "deck starves the
     larger goal" mechanism.** `docs/DECISIONS.md` (07-25, "One selector, one ordering law
     — the predecessors are retired, not stacked") records `recent_ask_counts` becoming the
     third term of the one sort key. It landed in `deck_status` only.
     `suggest_targets.floor_gap_targets` (`scripts/suggest_targets.py:94`) still sorts
     `-staleness → ripeness → soak → alphabetical`, **no `asks` term**. Not theoretical:
     121 of 134 pending floor words tie at `NEVER_SURFACED`, so the tiebreak does all the
     work (41 distinct key prefixes over 134 items; largest tie group 14, broken purely
     alphabetically) — and **7 of the current top 14 floor targets were asked within the
     last 3 days** (சரி, ஆனா, இருக்கு, அண்ணா, சொன்னாங்க, மாமா, அவங்க). Exactly the
     rich-get-richer freeze the 07-25 entry diagnosed, still live on the larger goal.
     *Cheapest real move: add the `asks` term, completing a decision already made.*

  2. **The deck doesn't steal reps — it monopolizes instrumentation.** Knock targeting is
     roughly balanced (deck 24 / non-deck 5 / no target 34 / novel 12 across 75 knocks).
     But the deck has tier ordering, a coverage meter (`deck_coverage`), a deadline
     countdown, a status headline and a 3-term sort; the other 230 lexicon words have a
     floor percentage and nothing else — no coverage meter, no tier, no ask term. What gets
     measured gets worked.

  3. **There is no curriculum layer any more; there are three, and the original is dead.**
     `curriculum/word_pool.json` — 333 rows / 322 unique (11 duplicate rows), 20 clusters,
     priority 1|2 — is the abstraction the project was designed around. **27 of 322 have
     ever entered the lexicon (8%); 189 of 212 priority-1 entries never used.**
     `curriculum/trip_deck.json` (82 items, richer schema) is the real working curriculum,
     and shares exactly **1** entry with the word pool — the two were drafted independently,
     have incompatible schemas (`cluster`/`priority` vs `register`/`type`/`direction`), and
     only the deck can express machinery or ear-only. Meanwhile **209 lexicon entries are in
     neither file** — created ad-hoc in session. That is the largest de facto curriculum and
     it has no source file, no taxonomy, and no Oracle vetting. Options: retire the word
     pool as a fixture; or re-seat it as the post-trip curriculum with the deck's schema.

  4. **`register` is three axes wearing one field.** Topical (gossip/mil-table/faq/social/
     public/antifreeze/zinger), type restated (`frame`, on 20 of 21 frames), and priority
     (via `DECK_TIERS` register→tier). So `DECK_TIERS["frame"]=0` means *all machinery is
     auto-survival* — a pedagogy policy hidden inside a taxonomy collision. The single frame
     that declared a topic instead, `frame:youknow-la` (THE gossip opener, Oracle-confirmed),
     is tiered **dessert** — bottom of the queue — purely because its author filled a
     different field. Separately, `REGISTERS` at `suggest_targets.py:58` is the *emotional
     tone* palette (tenderness, dread, mischief…) — an unrelated meaning of the same word in
     the same module as `deck_registers()`.

  5. **"Catch and response" has no representation at all.** Andrew names it as a first-class
     curriculum kind. The schema has `direction: catch` (12 items — not the 5–6 he
     remembered; 1 cleared), but the *pairing* — hear X → say Y — exists only as English
     prose in `note`/`gloss`: "the 'eppo vandheenga?' answer", "HER line — hear it coming".
     No `pairs_with`/`response_to` field anywhere in the repo. The whole `faq` register is
     answers to prompts that live in parentheses, and nothing can drill a pair as a pair or
     meter it. Concrete casualty: the catch item இன்னும் கொஞ்சம் சாப்பிடுங்க (the maami's
     *eat more*) is in the deck; its natural response வேண்டாம்மா, வயிறு நிறைஞ்சிடுச்சு is an
     orphan (see 6) — the pair was split and nothing noticed, because nothing knows it's a pair.

  6. **`seed-deck` is an orphan factory (hygiene + silent state loss, not a lying meter).**
     `sync_state.cmd_seed_deck` un-tags departed items (drops `deck` + `direction`) but
     leaves `type`, stranding 15 rows: 10 chunks + 5 frames. Most of the 10 chunks are
     **superseded rephrasings** where the Oracle changed the wording and the old row stayed —
     எவ்வளவு ஆகும்? / எவ்ளோ ஆகும்? (one phrase, two spellings), பிறகு பார்க்கலாம் /
     அப்புறம் பார்க்கலாம், சாஃப்ட்வேர் வேலை பண்றேன் / …இன்ஜினியரா இருக்கேன்,
     காரம் …பழக்கமாயிடுச்சு / …பழகிப்போச்சு. **Learning state does not transfer to the new
     wording**, so a soaked phrase resets to zero under its new spelling. Good news: they do
     not corrupt the meters — 0 of 10 reach the floor denominator (all still `struggled`).
     The 5 orphan *frames* are the opposite of a bug and should be left alone:
     present-future-toggle, obligation-ணும், cant-முடியல, idum, negative-la are organically
     discovered machinery and **are** counted in Engines (21 = 16 deck-fire + 5 orphan) —
     the machinery axis absorbs discovery correctly. Options: a `supersedes` field on deck
     entries so a rephrase migrates state; or a one-time reconciliation pass.

  **RESOLVED 2026-07-26** (see `DECISIONS.md`): #1 landed — and was *wrong the first way*,
  because a 3-day cooldown is not a coverage term; the real fix is lifetime `rep_counts`,
  `coverage_key` as the one shared law, and a focus/background split (Andrew's design).
  #5 landed as `pairs_with`; the four missing FAQ *questions* are an open Oracle content ask.
  #6 closed as no-mechanism — all four rephrase pairs had zero state on both sides.
  #4 (`register` carrying three axes) is **still open** and deliberately deferred: it is a
  schema change with pedagogy consequences and it is not hurting the trip.
  #3 (`word_pool.json`) is **still open** — retirement was proposed and *overruled*: Andrew
  wants it incorporated, not deleted, by upserting its 322 entries into the lexicon with
  their `cluster` tag so there is one store and one schema. Not done; see below.

- **`--debrief` alone counts as a session (found 2026-07-25).** `sync_state.py update`
  appends a session-log row when *any* of cold/hinted/demoted/listened/debrief is present
  (line 451), so correcting a debrief for bookkeeping reasons writes a zero-fire "session"
  — it moved *last logged session* to today and put a zero-fire day into the trailing-pace
  window, both of which steer knock policy. Found while correcting the 07-25 -aam record.
  A debrief edit is not a rep. Options: gate the append on cold/hinted/demoted/listened
  only; or a `--bookkeeping` flag that suppresses it. Schema-adjacent → waits for Andrew.
  (The stray 2026-07-25 row is still in `session_log.json`; there is no CLI to remove one,
  and hand-editing Python-owned state is out of bounds.)

- **BUILD (decided 2026-07-24): autonomous cloud episode production, inside the knock
  tick.** The cron question is settled — the local watchdog cron is RETIRED, replaced by
  cloud production. Direction locked with Andrew:
  - *Foundation DONE* (commit dc94bf2 / pushed 737fef5): the studio writer is now
    executor-agnostic — `agy` locally, OpenRouter→`google/gemini-3-flash-preview` in the
    cloud, with `inline_canon()` carrying the protocol files into the single-shot prompt
    (a bare API call has no filesystem). Proven on-canon, ~$0.03/episode, CI green.
  - *Remaining, one coherent phase (touches the KNOCK LOOP — the primary channel; a bug
    there fails silently, so build fail-safe + dry-run-tested before it goes live):*
    1. **New `episode` move in the knock tick.** Anna (he) may CHOOSE to produce (he
       decides *when* — Andrew's call, not a fixed cadence), but Python's guardrails
       dispose: only if `soak_pending()`, `produced_today() < MAX_UNATTENDED_PER_DAY`, and
       waking hours. A gated-out choice logs as grace/silence, never overspends. On go, it
       dispatches `run_studio.py` (which owns write→render→publish→commit→push, incl. the
       "go listen" phone push); then the tick logs the reach so the rails see it. Ordering:
       studio commits/pushes first, then the knock-log commit — no double-push.
    2. The digest must surface the soak-pending signal so Anna can see there's something to
       produce (build_digest currently doesn't).
    3. ~~**Drop the "Cloud never renders episodes" rule**~~ — **DONE 2026-07-24**, in the
       canon (DECISIONS marked SUPERSEDED/CORRECTED) and then in the machine: the rule also
       lived as prose in `JUDGE_MANDATE`, in `/extend` Gate 6, and as a smoke assertion that
       *required* the refusal text — so Anna went on refusing for eight hours after the
       canon changed. Lesson recorded: a dropped rule must be hunted in code, prompts,
       skills and tests, not just in DECISIONS.
    4. ~~**Retire the local cron for real**~~ — **DONE 2026-08-01** (drift audit): the
       paused line is deleted from the crontab. `studio_watchdog.py` stays as a manual
       command — the session-open drain is the live door; the watchdog is the hand-run
       retry for a laptop session that wants one.
    5. ~~**The 9am-audio lane**~~ — **DONE 2026-07-24.** Shipped as the workflow
       consolidation rather than as a GCP wire-up of `push-queue.yml`: one `anna.yml`
       carries every trigger and every secret, `memo_script` rides the queue entry, and the
       drain renders it at fire time. See DECISIONS "One runner, every capability."
  - *Small determinism fix (do alongside):* Python stamps the `scene_spec`-decided
    `episode_form`/`register`/`ingredient` into the sidecar instead of trusting the writer
    to echo them down the Director→Architect→Producer chain (the thin slice caught Flash
    labeling a `vignette` as `classic`; the script was right, the label drifted). Hardens
    `agy` too. Needs the structured spec plumbed into `write_episode` (today it's only in
    the ticket TEXT).
<!-- RESOLVED 2026-07-24: machine-commit-identity — Andrew is OK with automated commits
     signing as him for now. The ambiguity is automated-vs-human-initiated (cloud already
     self-labels github-actions[bot]; only the retiring local cron committed as him
     unattended), and cron retirement mostly dissolves it. No self-labeling machinery to
     build. See DECISIONS.md "Machine commits masquerading as Andrew are acceptable for now". -->


- **The trip harvest** (2026-07-18, direction approved — build when the Aug 5 campaign
  is drafted): the trip is a field-mission arc, not an exam. Final campaign (Aug 5–12)
  goes rehearsal-shaped — Table Rehearsal dominant, the five-scenario checklist as the
  hard artifact, "survived end-to-end at speed" as that week's meter — and live
  encounters get harvested nightly into the ledger. Context locked in: Andrew brings
  phone + laptop, expects MORE free time not less, and keeps working on/with the system
  through the trip — capture rides the existing channels (session close, knock-reply
  meta_notes); no new plumbing needed.

Endorsed in principle 2026-07-08 (pedagogy review — direction approved):

- **Daily spoken reps** — the trip test is mouth-under-pressure, nearly all current production is typed. **Experiment started by hand 2026-07-08:** first drill cut and on the feed ('Cold Fire: Eight Due'); machinery (drill-as-knock, below) waits until a few drills prove the format.
- **Cold decay / re-test dates** — cold is a one-way door today; confirmations at ~2/7/21 days or it demotes. Interacts with the deck meter (headline could go backward mid-sprint) and needs graduation data that doesn't exist yet — **defer past the trip.**

- **Voice loop (speech-IN half)** — let Anna *hear* Andrew: a phone voice-note lands, gets transcribed, judged like a knock reply. The speech-OUT half shipped 2026-07-02 as the drill track (`render_drill.py`); what remains open is Andrew's voice coming back in. **Parked on evidence 2026-07-09 (Andrew):** his block is Thanglish-parse confidence, not friction — run the spike (a few real voice notes through an audio-capable model, no machinery) before building anything.
- **Pull the wife in as the north star** — the real viability floor is "can I say this to her." Anna could hand a line: "try this one, tell me how it landed tomorrow." Costs no code. **Decided 2026-07-09: stays opportunistic** — no daily/scheduled missions; ripe item + obvious moment only (see DECISIONS).
- **Drill as a knock modality** — `morning_knock.py` could choose "drill" and commission `render_drill.py` itself (today Anna-in-session or Andrew runs it). Wait until a few drills prove the format.
- **Single deployment ladder per item** (post-trip) — consolidate the overlapping frames
  (recognition buckets / production axis / floor / engines / deck fire-catch) into one
  per-item stage: heard → understood → spoken-scaffolded → spoken-cold → survived-live,
  everything else derived. From the 2026-07-09 greenfield review; a consolidation, so it
  must *delete* more state than it adds or it doesn't happen.
- **Payload lint could match inflected stems** — the verbatim check false-flags correct
  inflections (M61: தூக்கு vs தூக்க); a stem-tolerant match would stop the recurring
  manual sidecar repair. See the 2026-07-13 "bends the sidecar" decision for the
  interim rule.
- **Concurrent drains could double-fire one queue entry** (introduced 2026-07-24 by the
  workflow consolidation — an honest residual, not a sighting). The drain used to be
  serialized by `push-queue.yml`'s own `concurrency: push-queue`. Now it runs at the start
  of every wake-up, and `anna.yml` deliberately gives each reply its own concurrency lane
  (a reply must never queue behind a knock render), so two runs *can* overlap: two replies
  to DIFFERENT knocks inside the same ~30s, with an entry due. Both would push, then the
  second's queue write rebases onto the first — a duplicate notification and a duplicate
  klog entry. Narrow (replies to the same knock share a lane and serialize; the drain is
  the first step, so the window is seconds) and low-consequence. The real fix is a claim/
  lease on a queue entry — a schema change, so it waits per Gate 2. Revisit on first
  sighting, or if scheduled pushes get frequent enough to make the window matter.
- **Published feed titles could still be mutated by any writer** (residual of the
  2026-07-25 Apple-Podcasts fork; the *cause* is fixed, the *class* is not). Apple treats a
  retitle of a published item as a new episode, and `rebuild_rss` derives every knock/
  scheduled/reply title from `knock_log.json` at rebuild time — so any later change to a
  `move` string (a hand repair, a judge rewrite, a klog migration) silently forks that
  episode in Andrew's player. The drain, the only lane that actually did this, now rebuilds
  after the log write (smoke s29 asserts it). The class-level guard is an `existing_titles()`
  in `rebuild_rss` mirroring `existing_pub_dates()`: once published, a title is frozen. ~8
  lines, same shape as code already there. Held per the one-sighting bar, and because it
  would make a genuine title correction unfixable without hand-editing `rss.xml`. Revisit on
  a second fork, or the first time we want to rewrite move labels in bulk.
- **Phantom-fired knock on delivery failure** — the knock logs + commits *before* the
  notify step, so a push that fails all retries leaves `acted: true` for a dose Andrew
  never saw (rails count it; judge could grade against it). Seen once (2026-07-14 DNS
  blip, now retried at the chokepoint). A `delivered: false` mark on final failure
  would make the log honest. Wait for a second occurrence post-retry.
- **Real-media library (songs, kids' TV)** — the Jabberwocky principle: melody stores sound-sequences below comprehension (Andrew still carries sung gibberish from decades ago). Curate Oracle-vetted YouTube links (her childhood film songs, Tamil Dora) as rows of data; Anna sends one as a no-ask dose, lore-style — a skill, not a DJ persona. Feeds the starving catch axis (0/8) and buys shared cultural ground before the trip. Guardrails: stop-chasing-listens applies in full (zero-debt, no follow-up); curation happens at the laptop, studio-style, never in-session. Machinery (a knock "song dose" type) waits until the library exists and a few doses prove the format by hand.

## Shipped

- ~~THE REPAIR EARNS THE DOSE — audio commissioned off his errors~~ — SHIPPED 2026-07-28
  (same session as the `/recalibrate` pass that found it; Andrew: *"I agree with your
  diagnosis and want to fix this now"*). The commissioning law now lives in
  `protocol/audio_channels.md` → "What it carries", split there rather than bumping
  `daily_session.md`'s budget; Close & Log step 2 fires it and points at it. Repairs
  outrank the forward seed order, a survived collision earns its own order, and
  `MAX_UNATTENDED_PER_DAY` went 1 → 3 (Andrew: *"guardrails to a problem that was
  temporary"*). Smoke case s37 is the regression net. The queue-of-one fix stayed
  deliberately unbundled — see the item under Ideas. DECISIONS 2026-07-28 entries.

- ~~The declared-events ledger build~~ — SHIPPED 2026-07-26 (dedicated @build session,
  same day as the design): judge-seam rep increments + `rep_counts` reads declared
  counters only; delivery-seam exposure stamps (`sync_state.mark_exposed`) at episode
  registration, soak, drill, knock push and the queue drain; `-soaked` flipped to a
  least-exposed term in `coverage_key`; focus cohort stored in `learner.json`
  (reconciled at the two graduation seams); reps backfilled from judged replies
  (Andrew's yes — 49 reps / 26 words); s32/s33/s34 rewired to the real seams;
  `pairs_with` split now refuses the whole seed. See DECISIONS 2026-07-26 entries.

- ~~`suggest_targets.py` has zero smoke coverage~~ — SHIPPED 2026-07-19 (wrap-up
  session): smoke case s23 plants the proven crash class (a `special_*` string-mission
  sidecar) and runs the full ticket end-to-end on day-zero state.
- ~~Registration canonical-at-write~~ — SHIPPED 2026-07-17 same evening (Andrew's
  token-discretion grant): `claim_payload()` in `run_studio.py`; corrected diagnosis
  and full record in DECISIONS ("The sidecar must claim the soak payload"). Dupes
  merged; M65/M67 stamps repaired.
- ~~Fixed-time anchor push~~ — MOOT, closed by the 2026-07-17 review on the deferral's own
  test: Anna fires volleys reliably unforced (07-14 15:13, 07-15 15:46, 07-17 13:07 EDT —
  the afternoon slot the 07-13 lunch-anchor decision assigned). No Python-forced anchor;
  "outreach policy is Anna's" stands untouched.
- ~~`frame:idum` has no lexicon record~~ — RESOLVED by 2026-07-17 review: a full record
  exists (new engine record, not folded into done-ittu — gloss even names the boundary:
  "bolts onto a clean single verb, not a compound"). The 07-13 cold fire (`book
  pannidum`) that was skipped for want of a record was applied during the review.

- ~~Explicit contrast beat~~ — DONE 2026-07-08 (same-day canon amendment, Andrew approved):
  a recast may carry ONE clause of why, by example, never terminology — one clause is a
  beat, two is a lecture. Canonical in `constitution.md` → The Contrast Beat; echoed in
  persona/daily_session/judge mandate.
- ~~Per-word verdicts in the reply judge~~ — DONE 2026-07-03 (same day it was found —
  Andrew approved building it): the judge grades each fired word on its own
  (`fired: [{word, verdict}]`), Python derives the reply's overall verdict as the best
  word, the revealed-cap stays deterministic per word, and the burn rate reads the new
  `reply_fired_cold` (legacy entries fall back to the old flat count). Evidence that
  motivated it: 2026-07-02 19:18, three deck items fired in one reply, all flattened to
  the single "hinted".
- ~~Day-zero ticket guard~~ — DONE 2026-07-03: `suggest_targets.py` (and `generate_callbacks.py`) now treat an *empty* lexicon as valid day-zero state; only a missing file errors. A fresh learner gets a real first-session ticket.
- ~~Knock digest could carry the ticket's deck top~~ — DONE 2026-07-02: `build_digest()` appends the deck-due menu (fire + ear-only), and the mandate points `expected_target` at it.

- **Fielding has no cadence gate, and it is a sole-owner channel** (2026-07-27, noticed
  while mapping the architecture). Catch and heard-question→produced-answer are each
  trained by exactly one modality. Catch has `EAVESDROP_CADENCE_DAYS = 3`, a floor
  frequency that exists because the axis already stalled once. Fielding — which
  `OUTREACH_MANDATE` itself says no other channel trains — has no equivalent term, so
  variety pressure can steer away from it indefinitely and nothing in the digest says so.
  One data point, no evidence it has actually stalled. Cheap version is a digest line,
  not a gate. Do not act mid-sprint.
- **Pre-registering the chat rep's target** (2026-07-27, from the coach/judge discussion —
  see DECISIONS same date). Would give the chat lane the property that makes the phone
  grade meaningful: the target committed before the rep, not reconstructed at close from
  Anna's own account. Schema-adjacent, so it sits under the structure freeze; and there is
  no evidence yet the chat floor is inflated. Revisit only if the trip contradicts the
  floor number.
- **The post-trip arc — three proposals, none chosen** (2026-07-27, awaiting Andrew).
  Diagnosis is in DECISIONS same date. (a) Name the trip itself as the `/recalibrate`
  run — eight days of live fire is the highest-quality felt signal the system will ever
  get, and the existing skill designs the successor from it with zero new structure.
  (b) Let the trip author the next deck: the phrases he needed and did not have, captured
  live via knock replies and `sync_state.py feedback` (both already work from the phone),
  informant-vetted by construction because the informants are the table. (c) The
  denominator that replaces `15/34 survival cold` on the status line is the one decision
  that cannot be deferred past touchdown — and it depends on what the trip exposes, so it
  is deliberately left open rather than guessed now.
- **A pure state correction inflates the session count** (2026-07-27). `sync_state.py update`
  appends a `session_log.json` row unconditionally, so crediting the two 07-27 volley fires
  from the court-of-appeal path wrote a second 07-27 session with an empty note. Recency from
  the session log is the honest momentum signal (no streak, by design) — a correction is not a
  session, and adherence numbers read off that log now carry a small overcount. One data point.
  Cheap version is a `--correction` flag that skips the row, not a schema change.
- **Volley chained recasts can double the re-presented ask** (2026-07-27). Exchange 2 of the
  antifreeze volley pushed back `· 3/4 — · 3/4 — you know the thing but…`, and one reply_line
  carried mojibake (`mেdhuva`, a Bengali vowel sign spliced into the Latin). Cosmetic, and the
  lock-screen budget makes a doubled prefix cost real characters. Both are one-line fixes in
  the volley re-present path; neither has recurred yet.
- **A word taught in-session cannot enter the lexicon** — ~~first half~~ **SHIPPED
  2026-07-28** as `sync_state.py update --teach "WORD=gloss"`: creates the record at
  `struggled` recognition, seen today, production unset (so it can never inflate the floor),
  Tamil-script-only so keys stay canonical, and it runs BEFORE the axes so a word taught and
  fired in the same close resolves instead of being refused. Re-teaching a known word
  refreshes it without resetting recognition. `பக்கத்துல`, `ஆச்சு` and `இருக்கேன்` were
  entered the same day. Smoke case `s38`. **SECOND HALF SHIPPED 2026-07-31** — the
  session_log inflation below is closed: same-day `update` calls now MERGE into that
  day's row instead of appending (union on the word lists, a later debrief supersedes,
  an absent one never blanks). It had reached 38 rows for 26 real session-days by the
  day it was fixed — and the cosmetic overcount was the smaller half, since
  `cold_fires_recent()` and `fires_today()` sum word lists across entries, so a word
  logged twice in one close inflated the trailing pace the burn rate is computed from.
  Historical rows left as they are pending Andrew's call on a backfill. Smoke case `s42`.
  Original report follows.
  The pakkam/paakkalaam
  deep-dive taught `பக்கத்துல`, `ஆச்சு` and `இருக்கேன்`; all three were refused at close
  (`not in lexicon — add recognition first`), and `--mark-seen` refuses them for the same
  reason. The only entry path is `seed-deck` from `curriculum/trip_deck.json`, which is a
  deck-authoring flow, not a session one. So the live teaching surface — the Teach Beat,
  the lore tangent, an Active Gaps item Andrew asked for **by name** — writes nothing, and
  the next ticket cannot know the word was taught. Worse in the soak lane: `ஆச்சு` is now
  the payload of a queued order for a word the lexicon has never heard of. Cheap version is
  a `--teach WORD --gloss "…"` that creates the record at `struggled` recognition, seen
  today, production unset — one row, no schema change. This is the write-side twin of the
  07-27 credit-the-word-he-said fix: that one taught the judge to credit a substitution,
  this one lets a taught word exist at all.
  **Second and third data points, same day (2026-07-28):** the 07-28 close wrote
  **three** `session_log` rows — fires, debrief, then a debrief correction — because a
  close split across multiple `update` calls appends a row each time. Any multi-call
  close inflates it, not just the court-of-appeal path, so the `--correction` flag
  above is really "don't append a row when this call carries no fires," which is the
  common case for `--debrief`-only and `--soak-*`-only calls. Adherence read off this
  log now overcounts 07-28 by 2.
