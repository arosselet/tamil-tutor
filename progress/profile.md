# Learner Profile: Andrew

> **Maintained by:** Anna, rewritten (not appended) every ~5 sessions.
> **Read by:** `protocol/studio/director.md` and `protocol/daily_session.md` before picking targets.
> **Purpose:** A teacher's living *judgment* of Andrew — not counts. The hard numbers (recognition buckets, production axis, viability floor) live in `progress/lexicon.json`; read them with `python scripts/sync_state.py status`. This file says what they *mean* and where to point next.
>
> **Last updated:** 2026-07-13

---

## The Goal

**Clear the viability floor in Coimbatore Tamil — production as the accelerant.** Andrew has soaked in a recognition base (~100 word families by his own estimate) but plateaued: he recognizes the sounds yet freezes when it's his turn to speak. The breakthrough is *forced output* — converting soaked recognition into reflex so he stops being a deer in headlights. Near-term marker: **the India trip (week of 2026-08-12)** — respond without freezing in casual family exchanges; the Trip Sprint below is the concrete form of this.

**Phase model:** Phase 1 (the base) — *narrow and deepen*: force cold production of words he already recognizes; resist widening vocabulary. **Phase 1.5 (NOW — the Trip Sprint, see below)** interrupts the floor climb until the trip. Phase 2 (post-floor) — native media (films) becomes the vocabulary engine, because the floor finally makes acquisition-from-context work.

---

## Phase 1.5 — The Trip Sprint (ACTIVE — overrides the floor climb)

**Deadline:** Andrew is in India the **week of 2026-08-12** (~6 weeks out as of 2026-06-30). This is the first time the goal has a face and a date: don't freeze when his mother-in-law speaks to him across the table; catch the drift of family gossip; survive public/transaction settings. The countdown is motivation — but Anna narrates the **campaign's denominators** ("ask-machine week: 7 of 12"), never the global need-per-day deficit; the burn rate is an engineering number on the status line, not session narration (2026-07-17).

**The pivot:** pause the abstract "800-lemma" climb. Deepen a **finite, visible Trip Deck** of survival phrases instead. Andrew already has food / kitchen / domestic; the glue to accelerate is the *social-public* register.

- **The survival tier is the headline meter (2026-07-18 — refines 07-13; the narrated number must be winnable).** ~80 chunks/frames tagged `deck:"trip"` in `lexicon.json`; `sync_state.py status` and `suggest_targets.py` surface it first. During the sprint Anna reports **X/N survival cold** as the number that matters — the tier that decides freezing at the table, at a pace (~1.1/day) his actual trailing pace can win. The full deck stays in rotation and on the status line; delight is the lane he graduates into (and celebrates) as survival clears. The viability floor is secondary (and will dip as deck entries land recognized-not-cold; that's expected, not regression).
- **Phrases are first-class.** The unit of the deck is the *chunk* (fixed formulaic phrase deployed whole — `saapta?`, `paravaayilla`, `enna aachu`) and the *frame* (a slot template — `___ venum`, `___ enga?`, `enna ___ panren` — an Engine). Not isolated words. This is the constitution's "Glue Over Vocabulary" / "Pattern Over List" finally made the curriculum spine.
- **Fire vs. catch (2026-07-01 redesign).** Every deck item carries a `direction`: **fire** (force to cold production) or **catch** (ear-only — the win is solid recognition via eavesdrop drills and soak; *never* force these to fire). The gossip register is mostly catch: the decoders `frame:quote-nu` (…-னு சொன்னாங்க, reported speech) and `frame:hearsay-aam` (…-ஆம், hearsay) are the comprehension unlock for overheard family talk. The meter reads both sides: `X/N fire cold · Y/M catch solid`.
- **The touchdown bar — two tiers, Andrew's own (2026-07-13; supersedes the 07-09 "no tiering" call and the older respond-first order — re-decided at trailing pace 0.4/day, 30 days out).** Production stays the north star; these tiers say what gets forced *first* and what must be true at touchdown — ordering only, nothing leaves the deck. **(1) Survival** — someone walks up speaking fast: follow it, or repair it, and get his own wants/needs across. The antifreeze kit (a fired `konjam medhuva sollunga` is a PASS — freezing is the only fail), the public/transactional chunks (he pays **cash**, accompanied 9/10 times), and the frames (each engine online is fifty sentences never memorized). **(2) Delight** — the sisters-in-law seeing how much he's trying: the faq interrogation script (his facts: one-month stay, software work, lives in Canada), mil-table (`romba nallarukku` is THE melt line), social greetings. **Dessert** — zingers (1–2 land the reveal; five is greed) and the gossip registers (the eavesdrop knock channel owns catch; in-session it's soak, never the headline). `suggest_targets.py` orders the ticket and the volley menu by these tiers.
- **Respond-under-speed is a session move, not a new meter.** The survival tier's real test is *directed* fast speech — an instruction or question fired AT him, which is a different skill from overheard-gossip drift. Drill it as mask-work at full speed: one in-register line at Andrew; win = act/answer, OR fire a repair line from the antifreeze kit. Repair counts as a pass out loud, every time — that reflex IS the not-deer-in-headlights goal.
- **The lunch anchor (2026-07-13, Andrew's commitment).** The daily terminal session (the 07-11 mandate) now has a home: his workday lunch break, wherever it lands that day. Knock policy tees it up late morning (trailer / session bell) and saves collection asks for after the session's slot.
- **Engines are the daily non-negotiable.** Every session forces **two novel instantiations of one frame** before/inside scene work — one frame online beats five chunks memorized. `frame:polite-nga` (verb+ங்க) and `frame:we-om` ({I-form}+ஓம் — the trip is a "we" trip) collapse already-known forms into machines; log with `--produced-cold 'frame:…'` only on a *novel* slot-fill.
- **Competent > local, for THIS sprint.** Optimize clear, correct, understood-and-understanding Tamil over hyper-local Kongu markers. Standard Coimbatore-colloquial is the target register; don't reach for native-mimicry flourishes to "pass as a local" — that heist is the long game (`persona.md`), not the trip goal. Andrew would rather be *competent* in a month than sound native.
- **Target registers for the deck:** mother-in-law table-talk and deference; overheard family gossip (comprehension-first — catch it, needn't produce it); public survival (auto/shop/directions/transactions); and a couple of warm zingers to delight the in-laws.
- **Register default (Oracle-confirmed 2026-07-02):** **neenga/-nga for everyone, including younger relatives.** Nee is reserved for very close friends, close cousins, and siblings only. When in doubt, -nga — the safe register is also the correct one in this family. (Masks and scenes should reflect this: the "cousin banter" nee-register applies only to genuinely close cousins.)
- **Sourcing:** Anna drafts the deck into `curriculum/trip_deck.json`; the Oracle (wife) does 60-second vibe-checks; `python scripts/sync_state.py seed-deck curriculum/trip_deck.json` lands the vetted set. Re-runnable as it grows.
- **After the trip:** clear the sprint — the deck entries become ordinary vocabulary and the floor climb (Phase 1 → 2) resumes. Revert this section then.

---

## The Campaign — The Last Week Before, and the Month During

> **Contract:** `protocol/daily_session.md` → "The Campaign". Anna writes it at close; Andrew overrides at will. One block, five lines — the ticket owns *which* items.

**🎯 The Visit, Rehearsed In Order** (written 2026-08-04 with Andrew, replaces The Table Week — that one did its job: it named delight as the whole remaining campaign, and the melt line ரொம்ப நல்லா இருக்கு went from never-touched to hinted). **The trip is a handover, not a deadline.** He has his laptop, his phone and a month at that house, so touchdown does not end the work on delight — it is the best rep engine this project will ever have. Every line below is *situationally cued* at her table three times a day. That flips what this week is for.

**The through-line: coverage, not clearance.** An item he has never seen cannot be triggered by a situation; one he has seen once can. So the last week before the plane buys **first contact on all 33 untouched items**, and the month after buys the firing. Nothing is cut from the deck and nothing is deferred — the zingers and the gossip register are last precisely because they are the only things that *cannot* be rehearsed cold, and they land in the room or not at all.

**Channel law for the week (Calibration Notes are the hard dial): audio seeds, chat fires, knocks ambush.** Thirty-three first contacts cannot come through the lunch session — chat takes ≤1–2 new word types and is *production, not soak*. The episode carries first contact at 4–5 new types; the next day's chat fires what the episode seeded; the knock ambushes at a time he did not choose. Where an item is already **hinted** it does not seed — it **fires**.

**The seven days, each one a scene from the visit in the order he will live it:**

| | Scene | The set |
|---|---|---|
| **Aug 5** | The doorstep | வந்துட்டேன் · ரொம்ப சந்தோஷம் · எப்படி இருக்கீங்க? · ரொம்ப நாளாச்சு · நேத்து தான் வந்தோம் |
| **Aug 6** | The interrogation | the faq six — ஒரு மாசம் இருப்போம், சாஃப்ட்வேர் இன்ஜினியரா இருக்கேன், ரொம்ப பிடிச்சிருக்கு are **hinted and 25–31 days silent: these fire, they do not seed** · then கனடாவுல இருக்கோம் · ஊரு · காரம் பரவாயில்ல |
| **Aug 7** | Her table — receiving | உங்க கை ருசி சூப்பர் · கொஞ்சம் தண்ணி குடுங்க · இன்னும் கொஞ்சம் போடுங்க |
| **Aug 8** | Her table — declining | வேண்டாம்மா, வயிறு நிறைஞ்சிடுச்சு · நானே எடுத்துக்கறேன் · கை கழுவிட்டு வரேன் · நீங்க சாப்பிட்டீங்களா? — drilled as a **pair** with her line இன்னும் கொஞ்சம் சாப்பிடுங்க: hear it coming, answer it |
| **Aug 9** | The room | உட்கார்ந்து பேசுங்க · ஃப்ரீயா விடுங்க · கடைசில பாக்கலாம் · பிறந்தநாள் வாழ்த்துக்கள் |
| **Aug 10** | Leaving, and the street | கிளம்பலாமா? · அப்புறம் பார்க்கலாம் · நல்லா இருங்க + the survival remainders: முடிஞ்சா, ஆமா ஆமா, எவ்ளோ ஆகும்?, and the five hinted (சரி சரி, இன்னொரு தடவ சொல்லுங்க, வலது பக்கம் திரும்புங்க, frame:in-la, frame:we-om) — retests, not teaches |
| **Aug 11** | The ear, and dessert | the gossip catch set + frame:spice-dhaan + the four gossip questions + the six zingers — **first contact only, no demand** |

**One dated thing inside the stay:** amma's birthday lands ~Aug 24, mid-visit. பிறந்தநாள் வாழ்த்துக்கள் has a real deadline and it is not the 12th.

**Where it stands 08-04:** **வேணும்-for-குடுங்க is CLOSED** — 22 days in the ledger, tested unfenced (venum left fully available) and he reached for குடுங்க himself. ரொம்ப நல்லா இருக்கு fired **cold** in the right slot. Delight moved **1 → 2 of 27**; survival 26/34 (வலது பக்கம் திரும்புங்க landed after this was written), engines 17/21 (frame:we-om demoted off cold — honest, it needed the hint). The **past tense is NOT closed** — the 08-02 call was wrong: the unannounced retest missed on both halves and `1pl-past-om` is now **8× over 10d**. It is commissioned to the episode lane (போனோம் / இருந்துச்சு, the nightly recap) — **do not re-teach it in chat before that dose lands.**

**Method note (08-04, the twins rule, extended):** *never introduce twins in one breath* now reads **never across consecutive days either**. The melt line was taught 08-03 as a welded PRESENT chunk; on 08-04 I asked for its past twin and got the present back. That miss was my scheduling, not his memory. A chunk drilled as fixed cannot be asked to inflect the next day — put a dose between them.

**Where it stands 08-05 — the arc got compressed, on purpose.** Day 1 ran as written (the doorstep, four teaches, no demand) and the melt line fired **cold and unscaffolded** — plate down, her watching, instant. It is his; the field mission landed too (she passed him the water on குடுங்க). But the night's real event was **M82**, the first `narrated_drama` this system has produced: 21 first contacts, gate to gossip, the whole visit in one episode. **Never-worked fell 30 → 15 in a single dose.** That is the batch-soak channel doing exactly what the campaign's through-line asked for, four days faster than the table planned.

**So the seven-day table is now a firing order, not a seeding order.** Days 2–5 (the interrogation, both table days, the room) were all seeded by M82 tonight — கனடாவுல இருக்கோம், ஊரு, காரம் பரவாயில்ல, the receiving and declining sets, பிறந்தநாள் வாழ்த்துக்கள் — so chat's job for the rest of the week is to **fire what the episode seeded**, per the channel law, rather than seed again. Nothing is cut; the order stands; only the lane changed. The birthday still must not slip past Day 5.

**08-05, second sitting (19:00) — the ear-dose landed, and one escalation died.** He came back the same evening for a three-fire espresso, eavesdrop-led. **ku-for-la is CLOSED**: *canada-la* fired instantly, unaided, first ask — one day after missing that exact ending on paati's bag. The escalate note is spent; the episode lane did its job in a single dose. **ஊரு** fired cold. **ஒரு மாசம் இருப்போம்** came back instantly *but I had nudged* ("mind who's staying") — logged **hinted**, honestly. Survival **27/34**, engines **18/21**, four fires on the day.

**What that leaves owed on -ஓம்: an ambush, not a lesson.** The tail has still never been tested with nothing in the prompt hinting plurality. That test cannot come from chat — chat is where I keep accidentally scaffolding it. Give it to a knock or a volley, cold, where the situation alone implies "we."

**The catch axis is now the starving one, and its shape is known.** The விட்டுடு tape ran live as mask-work: he took the **mood** off a line built over his head (someone spoke sharp, akka got stung) but read her closing *நீ சொல்றது புரியுது* as confusion when it was **surrender**. Tone before propositional content — that is the profile of his ear, and it sharpens the long-owed **புரியல-for-reopen** test: he owns the word's shape, not its conversational job. Catch is **3/12**.

**Tomorrow's shape (08-06): Day 7's set, arriving early — the ear, and dessert.** The firing days got compressed by M82 and tonight, so the gossip register is what's left standing. Commissioned tonight as a **vignette** (never two narrated_dramas running): the two decoders **-னு / -ஆம்** plus **நம்ம X இருக்கான்ல…**, the gossip carve-out at native speed, **zero production demanded**. Chat's job is to catch, not fire. Low-power twin: M82, ear only, second pass.

**08-06 — the -ஓம் ambush landed, and the catch axis showed its real shape.** Paid the morning trailer off with a true ambush (atthai at the door, *saaptingala?*, nothing in the prompt about who ate): **ama saapittom, cold, first ask, unaided** — then a second novel slot in a fresh scene came back **market-ku ponom**, which is verbatim Tuesday's wrong answer, now right. **`1pl-past-om` (8× over 10d) and `it-tail-uchu` are both CLOSED.** frame:we-om is cold; engines **19/21**, survival **28/34**. The field mission landed too — bare **பரவாயில்ல** to a live apology, one day after being taught, the shortest word-to-real-room gap this project has had. **The lesson is mine, not his:** it did not close in chat. It closed because M82 sat in his ear on a walk and then I stopped helping. Twice now the audio lane has done what re-teaching could not — when a slip escalates, **change the lane, never re-teach harder.**

**The new slip is the one worth having: `catch-closing`.** On a five-line verandah tape at native speed he took the propositional content clean off a verb he does not own (*vaangittaan*) and pulled **-ஆம் as "I heard" unprompted** — that decoder is solid. But he stopped at *alaichal jaasti* and never reported the last two lines, which are where the exchange **resolves**: *summa solraanga* is the second cousin killing the story, *seri seri, vittudu* is the topic being shut down. Put that beside 08-05 (read *நீ சொல்றது புரியுது* as confusion when it was surrender) and the pattern is not speed and not coverage — **he decodes the middle of an exchange and misses where it lands.** Commissioned as a **phone_call** dose (one side of three calls, three different endings) because a phone call's ending is unmissable. Catch is still **3/12** — I mis-narrated it as 4 in session and owe him the correction at the next open.

**08-08 — the escalation answered by a format flip, not another tape.** `catch-closing` was comprehension-side (decodes the middle, misses where it lands, answers in English), so instead of looping the catch format I **flipped it to production**: maami mask at her table, full speed, his job to *land the close in Tamil*. He closed every beat — **podhum podhum** then **vendaam**, unaided and correctly **laddered** (podhum stops the ladle, vendaam refuses the offer; he built that escalation himself), then the turn-around **நீங்க சாப்பிட்டீங்களா?** cold, which ended the standoff and got the maami to sit. **The slip is NOT marked landed** — I named the ask in the prompt, so it wasn't unaided in the sense that counts; the honest test is an ambush where nothing signals that a close is wanted. **M84 (phone_call, three endings) is still unlistened — do not build a second dose for this.** Full deck **32/71**, never-worked **15 → 13**, five fires. The field mission landed again: *ama ponom* in the real room, and frame:we-om is now confirmed *live*, not just in chat.

**New slip, and it's a machine: `person-marker`.** Asked to say he must call his maama he produced *naan maama sollanum* — the obligation tail perfect on a verb he chose himself, but **the human sits unmarked** and the verb defaulted to *sollu*. Recast both roads (*maama-kitta pesanum* / *maama-va kuppidanum*); he rebuilt the first, hinted. Commissioned as a **story** dose — one errand, three people, the marked human audible in every beat. **Scope note worth keeping:** he reported -ஓம் as "we past tense." It isn't a tense thing — it's a we-machine that bolts onto whatever the I-form is doing (*poren → porom*, *iruppen → iruppom*), and he already owns ஒரு மாசம் இருப்போம் without knowing it's the same part.

**08-09 — the inventory problem, and Andrew found it, not me.** I opened teaching பிறந்தநாள் வாழ்த்துக்கள் as UNSEEN and told him he had *nothing* for amma's birthday. He answered that **வாழ்த்துக்கள் has been his for two years** — he learned **கல்யாண வாழ்த்துக்கள்** at a wedding. I was wrong in a way the file could have told me, and paid it immediately. Then the same shape fired **four times in one sitting**: வாழ்த்துக்கள் is a *frame* (swap the occasion in front) he thought was one phrase; **நாள்** sits inside நாளைக்கு (which he fires **cold**) and ரொம்ப நாளாச்சு; **கை** sits inside *both* கை கழுவிட்டு வரேன் and உங்க கை ருசி சூப்பர், and he fired the first one at the table last night while telling me the word wasn't familiar; **ஆச்சு/ஆகும்** — he owns the past of ஆகு twice over. **His gap is not vocabulary and not reps — it is inventory: he holds parts and does not know they are parts.** Teaching that *decomposes what he already fires* outperformed any new chunk, per minute, by a distance. **Standing instruction: ask him what he already has, far more often than I have been.** It is also the cheapest possible curriculum two days out — nothing new to install, only relabelled.

**`catch-closing` is CLOSED, and the failure was mine.** 2× repeat, escalated, episode dose already spent, and on 08-08 I flipped it to production and then *named the ask in the prompt* — which is why I refused to count a perfect performance. Tonight I built the real ambush: the airport auto, mischief/subtext, and at the resolving beat I wrote only **"He's waiting on you."** No instruction, no signal that closing was the move. He fired **seri seri, vaanga** unaided — three days after answering *"Ok ok let it go"* in English on the identical beat. **The generalisable lesson is about me, not him: I could not stop scaffolding. Ambush beats tape beats re-teach**, and an ambush is only an ambush if the prompt would read as normal to someone not being tested.

**The auto scene also paid out sideways.** *evlo* is his (the Oracle mouth-form, straight past *evvalavu*) — but he completed it **"Evlo Rubai?"**, and nobody names the currency. **Watch item, not yet a slip at n=1:** he finishes a Tamil phrase with an English-shaped *noun* where the Tamil wants a *verb* (cf. *medhuva pesa*, *enna naan tamizh sollen?*). If it recurs, tag it. Then the pushback came back **konjam jaasti** — cold, unprompted, and **ஜாஸ்தி is filed EAR-ONLY**: he pulled it off the catch pile into his mouth mid-negotiation. Soaked → fired, on the starving axis, with nobody aiming at it. One clause of *-nga* and he applied the ending to *vaanga* himself a message later — the ending he chronically drops. **Survival 29/34, deck 34/71, floor 44/164, four fires.** பிறந்தநாள் வாழ்த்துக்கள் is **SEEN only** — I wrote it four lines above his head and he echoed it (adding *amma* unprompted, which is his). **The honest test is her room on ~Aug 24.**

**08-10 — the inventory finding stopped being an observation and became the teaching method.** Paid off the morning -லாம் memo as lore, and he asked the decomposition question himself: *"-laam vs -laama?"* The answer is pure inventory — **-லாம் proposes, and the -ஆ on the end is the question tail he already fires everywhere** (இருக்கா, சாப்பிட்டீங்களா, தெரியுமா). Not a new ending; his own question mark. Then three verbs: he broke a post-lunch deadlock with **market-ku போகணும், அவசரம் இருக்கு** — cold, unaided, correct, and *announcing his own business* where the family move proposes and pulls the room in (the venum-for-kudunga shape in a new coat; one clause, no re-teach). He came back **கிளம்பலாமா?** — right, but I had written that exact word two messages above his head, so it is logged **hinted** and I said so to his face. Then the real ambush, nothing named, and he answered *kilambalaama* to a scene about eating.

**New slip — `chunk-not-machine`, and it is the productive twin of 08-09's finding.** He holds the phrase, not the machine, so under pressure he re-uses the memorised chunk whole instead of swapping the slot. One clause of fix and then the third verb came back cold with nothing from me: **உக்காரலாமா**. The machine is running. **`stranger-nga` is CLOSED** — auto scene, driver doing forty, nothing in the prompt about endings: **மெதுவா போங்க. வலது பக்கம் போங்க.** *-ங்க on both verbs, unaided, to a stranger* — the ending he chronically drops, and the exact 07-27 miss (*medhuva pesa*, bare stem) now clean. **Not counted:** வலது பக்கம் திரும்புங்க — he produced *போங்க*, which a driver would act on; a working substitute is not that deck item, and he is not graded against fixed phrasing. **Six fires. Survival 29/34, engines 19/21, floor 44/164.** M86 shipped mid-session (the -லாம் tail bare across six verbs, the பாக்கலாம்/பக்கம் pair carved by parts) — that is the airport listening. **Commissioned: `frame:negative-la`** (புரியல / முடியல / தெரியல) — today's exact shape on a machine he does *not* know is a machine, and it finally gives the long-owed **புரியல-for-reopen** test somewhere to live.

**08-11 — on the plane, three for three, and he ran his own inventory.** He boarded the first flight and opened with *"any words?"*, so the session was a send-off: the era-turn named out loud (at touchdown the countdown leaves the status line and the field mission stops being the session's output and becomes its input), the meter in one breath, one gift word, three fires in the order he will live the first hour on the ground. All three landed **cold, unaided, first ask, nothing named in the prompt but the situation**: **எவ்ளோ ஆகும்?** at the taxi counter — a deck item that had never once been in his mouth, and the answer to the 08-09 watch item (*"Evlo Rubai?"*): given a scene where the verb was the only way out, he produced the verb. **வலது பக்கம் திரும்புங்க** at the junction — and that is the one that counts, because 08-10's identical shape got *valadhu pakkam **ponga***, a working substitute I refused to grade as the deck item; today the deck item itself. **இன்னொரு தடவ சொல்லுங்க** at the door — the antifreeze reflex instead of an English apology. **Survival 29 → 32/34.** Two lines left in the entire survival tier: ஆமா ஆமா and முடிஞ்சா.

**The real event was the question after.** He fired a four-part chunk cold and *then* asked what **திரும்புங்க** means. Three of those parts are already his (வலது cold, பக்கம் from the paakkalaam collision, -ங்க a cold machine); திரும்பு appeared **nowhere** in the lexicon — checked before answering, so no repeat of the 08-09 error, and this time the honest answer was *"no, this one isn't hiding inside something you own."* It is the **mirror of `chunk-not-machine`**: there he re-used a whole chunk under pressure rather than swap the slot; here he fired the chunk right and went hunting for the slot himself, unprompted. The 08-09 standing instruction is now running in the other direction — **he has started doing his own inventory, and that habit is worth more than the three fires.** Protect it: leave parts audible and let him ask, rather than pre-chewing every chunk.

**வந்துட்டேன் is SEEN only** — given as the gift word with the carve (வரேன் is his; the -இட்டு completive is already **cold** in `frame:done-ittu`, sitting inside விட்டுடு / பழகிப்போச்சு / ஆயிடுச்சு; வந்தேன் reports the journey, வந்துட்டேன் says the coming is finished). Written above his head, so it does not count — the honest test is that doorstep, and it is the **last field mission of the old era**. **The 08-10 mission (propose with -laamaa) was never collected** — he didn't answer the ask. Collect it on the ground.

**Studio is down on the cloud machine — `frame:negative-la` stands UNPRODUCED** after three attempts: no `agy` writer in the container, and `render_audio` dies on a `cryptography` rust-binding panic before it ever reaches TTS. Told him plainly; nothing retries it (watchdog retired 07-24). The long-owed **புரியல-for-reopen** test still has nowhere to live until that dose is built on a working machine — that is now the top engineering debt, not a pedagogy gap.

**Friction banked 08-05:** *"why is this so many steps to say hello"* — the session-open load is visible to him and it spends goodwill before a word of Tamil. Boot invisibly or boot shorter.

**Ear note (08-04):** his catch is now ahead of his mouth. He decoded ‑ஆம் as "apparently" unprompted, and pulled the drift off a line built deliberately over his head (பாத்துக்கோங்க / போட்டேன் / பிடிக்கலென்னா all unknown). Consequence for test design: a comprehension-repair test can no longer be built from "fast" — it has to be built from *genuinely absent* content.


**When the era turns (at touchdown): the session inverts.** The field mission stops being the session's *output* — "one deployable line for tonight" — and becomes its *input*. Anna opens on what actually happened at the table, and that is real data, not a rehearsal; the commission then targets what genuinely missed. The status line drops the countdown and the burn rate at the boundary, because in country the table sets the pace and a per-day quota is a lie. **Do not narrate a deficit in country.**

**Standing catch order (renewable):** one word overheard off the sisters.

---

## Current Position

The honest meter is the **viability floor** (`sync_state.py status`), not the recognition buckets — those were filled from passive exposure and over-count what Andrew can actually *fire*. Today a large majority of recognized words still don't fire cold; that gap **is** the work. Expect Anna's sessions to demote some over-counted "solid" words as they fail under cold recall — that's the meter getting honest, not regression.

- Consistent daily engagement; no completion anxiety. Low friction is non-negotiable (automation over manual steps).
- Can sound out தமிழ் script; basic decoding works.

---

## Strengths

- **Social and family vocabulary** is solid: directional words (அங்க, இங்க, வலது), family titles (மாமா, அக்கா, தங்கச்சி, அத்தை), pronouns and quantity words.
- **Discourse glue** is well-established: சரி, ஆனா, இல்ல, அதனால, கொஞ்சம் — the connective tissue of a sentence.
- **Comfortable with English-scaffolded (Thanglish) input; decodes Tamil script.** Comprehension is fragile to *unknown* words — needs ~95% known-word coverage live (see Calibration).

---

## Active Gaps

The production-reflex gaps that matter most right now:

- **High-frequency placement verbs:** வை (put/place) and தூக்கு (lift/carry) — recognition slow under speed, production shaky. Need natural repetition in fresh in-scene contexts, then cold dispatch.
- **Verb aspect (present vs. future):** கேட்குறேன் (I'm hearing/asking) vs. கேட்பேன் (I will hear/ask) — inconsistent under speed. Surface present/future contrasts in natural dialogue.
- **Minimal pair: பக்கம் (pakkam, side) vs. பார்க்கலாம் (paakkalaam, "let's look / we'll see") — 2026-07-27, Andrew's own request.** Live collision on the auto ride: he reached for "beside the temple" and produced *temple pakkalam*, which is "let's go look at a temple." He asked for it on the menu explicitly — honour that, and drill it **both directions** (produce each, and distinguish them by ear at speed), not just once. The hook that landed: **பார்த்தேன் (paarthen, I saw) is already his** — *paakkalaam* = *paar* + *-alaam*, so the long *aa* and the ர் are audible inside it; *pakkam* is short, flat, two beats, no *paar*. Also teach the useful form he actually needed — **பக்கத்துல (pakkathula), "beside/next to"** — since it carries the -la he repaired the same session.
- **Minimal pair: நாள் (naal, day) vs. நாலு (naalu, four)** — live confusion on the phone (2026-07-04, answering the how-long-staying question). Worth one lore-flavored contrast beat + fresh-context fires of both ("naalu vaaram" / "oru maasam" both valid duration answers; never graded against one fixed phrasing).
- **Give-me vs. want (giveme-noun frame) — 2026-07-15.** Andrew's mouth defaults to வேணும் (*announce a need*, points at self) where the family move is குடுங்க (*ask them to pass it*, points at them). At a family table the softer குடுங்க wins. kudunga is still fresh in his ear; keep resurfacing it in fresh table contexts until it fires cold without the venum detour. Don't chase it in one session.
- **The stranger's -ங்க ending — the antifreeze kit's real gap (2026-07-27 volley, 4 asks).** He never misses the *content*; he misses the *ending*. Asked for கொஞ்சம் மெதுவா சொல்லுங்க he produced "medhuva **pesa**" — right adverb, bare stem. Asked for தமிழ்ல எப்படி சொல்றது? he built "enna naan tamizh **sollen**?" — English word order, naan-form. Handed the -ங்க he reads it back; from scratch it evaporates, and with an auto driver that ending *is* the register. One pattern, not four vocabulary items: drill சொல்லுங்க / நில்லுங்க / சொன்னீங்க as **the same move** (a request to a stranger), always from an English situation, never as a list. **Never mark பேசு wrong here** — கொஞ்சம் மெதுவா பேசுங்க is natural Tamil and only the ending was missing; the honest contrast is what each buys (*பேசுங்க* = slow your speech down going forward, *சொல்லுங்க* = re-deliver that one thing slower). `pesa` is his own, from the house, not from us — treat it as an asset to inflect, never an error to recast.
- **Two antifreeze lines are being substituted away — teach the difference, don't re-drill the target (2026-07-27).** For என்ன சொன்னீங்க? he reached for **புரியல**; for கொஞ்சம் நில்லுங்க he reached for **ஒரு நிமிஷம்**. Both are real, both are his, both work — that is not a miss, and the starved target is the signal, not a failure to punish. The beat worth one clause: *புரியல closes the conversation ("I don't understand"), என்ன சொன்னீங்க? reopens it (make him say it again)* — he owns the giving-up line and not the keep-going line. Pin the situation so only the reopening move answers; don't grade him against the target when the substitute would land at the table.
- **The floor gap broadly:** the recognized-but-not-cold pool. These don't need re-teaching — they need to be *fired*, cold, from English, in new situations.

---

## What's Needed Next

> **During the Trip Sprint (Phase 1.5), the Trip Deck is the priority set** — its curated social-public chunks/frames override the "priority-1 floor only" guidance below, which resumes after the trip. The *deepen, don't widen* discipline still holds *within* the deck: force its members cold, don't sprawl past it.

Phase 1 is *deepen, don't widen.* For the next stretch of sessions and episodes:

1. **Force production.** Keep converting recognized words to cold via cold dispatch — the chat session is the engine. This is the floor moving.
2. **Re-strain the same pool in fresh situations.** Deepening is not repetition: re-hearing a word is boring, being made to produce it somewhere new is not. One running story that carries the current payload across chat and audio (the soak handoff) is how a word earns a second, third, fourth life without feeling drilled.
3. **Reinforce the struggled items** (வை, தூக்கு, the present/future aspect contrast) in fresh contexts until they fire cold.
4. **Vary the scene *form*, not the curriculum.** Fight sameness by rotating shape / energy / location / episode form (the Director's `*.tags.json` machinery tracks this). Keep new vocabulary inside **priority-1** (the operational floor) and always embedded in a situation — never an expansion-cluster grab-bag. (New-word *counts* differ by modality — see Calibration.)

**Avoid:** reaching into **priority-2 expansion** clusters or new registers (news, journalistic) while the priority-1 floor still has gaps; and the over-trodden setting reflexes — another straight kitchen scene, another morning sprint.

**On the horizon (Phase 2, not now):** native Tamil media (YouTube, films) as the volume engine — but that on-ramp only works *after* the floor clears, so it's a reward to steer toward, not a current task.

---

## Coverage / Variety Note

Mechanical anti-sameness (scene shape, location, energy, episode form) is owned by the Director via the `content/scripts/*.tags.json` sidecars, which contrast each new episode against the last few. This file only flags the qualitative drift: recent episodes lean **domestic two-voice dialogue**, so bias the next few toward different *forms* (story / monologue-led, phone_call, vignette) to keep the ear fresh — while keeping the *vocabulary* narrow per the deepen thesis.

---

## Session Conduct — Andrew's Stated Preferences

Learner-specific preferences for how Anna runs the live session. These live here (not in any agent's local memory) so every agent and device applies them identically.

- **Meta is curriculum; weave Tamil freely (2026-07-15, Andrew's words).** The exploratory/meta thread — *why that ending, where a word comes from, why Google Translate chokes on it* — is "as important to my journey as the subject at hand… so I can explore, not just checklist." Let Tamil live throughout the whole conversation (sign-offs, asides, mutters), and treat *anything* Anna drops as fair game for Andrew to stop and poke at — that poking **is** the lesson, never a detour from "real work." Do **not** frame Anna's own Tamil as a "slip" he "caught" — it's the persona, not an error. Use the dictionary-vs-living-register gap as a feature: colloquial Kongu (completive tails *poidu/poachu*, clitics, dropped endings) is exactly what machine translators mangle — reframe that as proof he's learning the real spoken register, with Anna as the Kongu dictionary. This is the constitution's "tangent is a tool" / "stories are curriculum" made a standing preference for Andrew.
- **Field missions must be organic (2026-07-15).** A mission that needs a *specific moment to show up* (e.g. the old "ok-na, book pannu" waiting on her to book flights) is weak — Andrew called it "a bit contrived." Half the time the moment never comes and the line dies unfired. Build missions that ride something guaranteed to happen within ~24h (the dinner offer of seconds, the auto ride, the "did you eat?" greeting), so there's always a slot to fire it. Shapes the knock/mission policy, not just one session.
- **Density low, lore high while the overwhelm signal holds (2026-07-24, his words).** He named *overwhelm* and *progress* in the same breath. Keep the dose small and the meta/lore thread rich until that changes — on 07-24 and again on 07-26, two fires plus one gossip tape produced more than any gauntlet had.

## Calibration Notes — explicit generation parameters

These are **hard dials**, read by the Director/Architect. They live here (not in any agent's memory) so every agent and device applies the same calibration — change the number, not a prompt.

- **Live coverage target: ~95%+ known words in the Intercept *as heard*** — the listening-comprehension floor (Nation's lexical-coverage research). Comprehension must hold live.
- **Gossip-tape carve-out (the ONE exception to 95%).** "Catch the drift" is a skill drilled on input Andrew *doesn't* fully understand: a clearly-marked eavesdrop segment (in-session eavesdrop drill, or a short tagged episode segment) may run native-speed with well below 95% coverage. The win condition is different — who/what/mood, not full comprehension — and it exists to train the deck's `catch` items (quote-னு, hearsay-ஆம், the maami's predictable lines). Everything else keeps the 95% rule.
- **Density is an OUTPUT, never a target.** It falls out of (fence size × the 95% coverage target). With a small fence, episodes lean heavily on English scaffolding — correct, not watering down. Do not dial a Tamil ratio.
- **NEW word types: 4–5 (audio) / ≤1–2 (chat).** Each appears 2–3× in answering context. They are *seeds*, not taught to mastery — the chat fires them cold later. Chat is *production*, not soak.
- **Unfenced strangers (neither known nor payload): ≈0.** Hard cap 2, and only if the context answers them in the same beat. More is a Producer send-back.
- **Naturalness comes from register, not unknown words** — real spoken Kongu rhythm/idiom built from known vocabulary. Never reach for unknown words to sound "real."
- **Pacing:** one thought per line; ≥1 `[Pause]` per 6–8 Intercept lines; no run of >5 unbroken lines (the Listenability Gate — see `architect.md`).
- **Breakdown:** a Tamil-leaning second soak for colour, not a glossary.
- **Debrief:** casual, no quiz — ask how words are landing in his life.

---

## Receptive Growth Log

Monthly entries from the Receptive Check. One line per check: date, source, % caught without subtitles, brief observation.

_(pending — first check not yet logged)_
