# The Household — the canon

**Fictional. Always.** Nobody here is anyone Andrew knows, and no name, role or
situation is lifted from his wife's family. That is a law, not a preference
(`docs/DECISIONS.md`). The point of a parallel household is that it can be
funny, awkward and wrong about things, which a portrait of real in-laws cannot.

**Who writes what.** The build session drafts Place, Cast and Standing facts;
**Andrew approves the cast before anything consumes it.** After that, Anna writes
the arc premise at the month cut, and the studio's Producer pass appends one beat
line per rendered episode. Andrew overrides anything, any time.

**Budget: 1,200 words** (`scripts/smoke/ratchets.py`). Canon that outgrows it is
compressed at the month boundary — this arc's beat log collapses to its one-line
past-arc entry. The number is never raised to fit more lore.

---

## 1. Place

A two-storey house on a short road off Trichy Road, Coimbatore — the kind with a
gate that scrapes, a scooter under the stairs, and a first floor that was added
when there was money and never quite finished. Mornings are loud and brief:
filter coffee, the pressure cooker, somebody shouting up the stairwell about
shoes. The afternoon empties out and belongs to Paati and the television. Evening
is the crowded part — people back from work, children underfoot, the TV on with
nobody watching, and dinner happening in three shifts because nobody can agree on
a time. The kitchen and the front room are where almost everything is said; the
terrace is where things are said that aren't for the front room.

---

## 2. Cast

Seven recurring, across four generations. One-offs rotate through freely — a bus
conductor, the vegetable seller, a wrong number — and are never canon.

**Each voice is pinned.** The Architect copies this map into every script's Voice
Map block; the same person must sound like the same person across months, because
ear-training tracks a speaker before it tracks a word.

**Every name carries its Tamil spelling**, and that is mechanism, not decoration: an eavesdrop tape must name who it is about in its opening or it is refused (`morning_knock.tape_names_a_referent`), and the tape is Tamil script, so a cast whose names existed only in English would have its tapes silently rejected.

| Person | Relation | Age | What they're for | Voice |
|---|---|---|---|---|
| **Paati** (பாட்டி) | Mama's mother | 74 | Older Kongu forms; the full honorific, always, both directions | `ta-IN-Chirp3-HD-Gacrux` |
| **Mama** (மாமா) | Head of the house | 56 | The elder Andrew must address **up** to. Terse, impatient, softens only for the children | `ta-IN-Chirp3-HD-Charon` |
| **Athai** (அத்தை) | Mama's wife | 51 | Fast, gossip register, assumes you kept up and does not repeat | `ta-IN-Chirp3-HD-Kore` |
| **Priya** (பிரியா) | Their daughter | 29 | The **across** room. Warm, banters, still -ங்க to her elders | `ta-IN-Chirp3-HD-Leda` |
| **Karthi** (கார்த்தி) | Their son | 23 | The hard listening: elides every ending, talks at speed, code-switches English mid-sentence | `ta-IN-Chirp3-HD-Puck` |
| **Deepa** (தீபா) | Priya's daughter | 9 | The **down** room. Repeats things, asks *என்ன?* constantly, bare imperatives, no politeness reflex to override | `ta-IN-Chirp3-HD-Zephyr` |
| **Ravi** (ரவி) | Deepa's brother | 6 | Barely intelligible and completely delighted by any adult who tries | `ta-IN-Chirp3-HD-Sulafat` |

**The cast is an instrument, not decoration.** The register ladder the year walks
— down to the children, across to Priya and Karthi, up to Mama and Paati — is
three different rooms with three different moving parts, and the cast is how
those rooms get heard instead of explained. Deepa and Ravi are not garnish: they
are the first room, because a nine-year-old tolerates error completely and cannot
switch to English to be kind.

**Athai carries the pinned eavesdrop voice** (`language.EAVESDROP_VOICE`). Nothing
depends on that yet — eavesdrop tapes set inside the household are a later
increment — but when that lands, the overheard aunty is already this aunty and no
voice has to change.

---

## 3. Standing facts

Things that are true, that scripts may not contradict. Short on purpose.

- Mama and Athai are married. Priya and Karthi are their children.
- Paati is Mama's mother and has lived here since her husband died, some years ago.
  She is not ill; she is old, and she is sharper than Mama thinks.
- Priya is married; her husband works in Chennai and is here at weekends. He is
  mentioned and does not speak. Deepa and Ravi are their children.
- Karthi lives at home, works in an office he is vague about, and owes Mama money.
- The scooter is Karthi's and does not reliably start.
- Nobody in this house is wealthy or poor. Money is discussed and is not a crisis.

---

## 4. This arc

> Written by Anna at the month cut, replaced each month. Two or three sentences:
> the situation, what the finale resolves, and which everyday domains it
> naturally exercises. **It never lists words** — the ticket owns those.

*(Not yet cut. The first arc opens 2026-10-01, inside the year's `down` phase, so
its premise should put the children near the centre of it.)*

### Beat log

> One line per rendered episode, appended by the Producer pass after render,
> saying what happened. This is the continuity — callbacks are read from here.

*(empty)*

---

## 5. Past arcs

One line each. The detail lives in git.

*(none yet)*

---

## Notes for whoever writes the next scene

- **Soap-sized, never plot-sized.** Food, plans, who is coming, health, the day
  just had. That is the register the real table runs on and therefore the register
  this exists to teach. Nothing needs resolving; things persist.
- **Ordinariness is the antidote to hokey.** People with specific small wants,
  mild irritation, and money that is neither a crisis nor absent. If an arc reads
  hollow to Andrew, that is a felt signal to log and a premise to re-cut — never
  a reason to add plot.
- **Variety still comes from the gate**, not from the people
  (`suggest_targets.scene_spec`). The household is a setting; it is never a reason
  to repeat a register, a form or a dramatic ingredient.
- **Anna is not in it.** He talks *about* the household like a show the two of
  them follow. The fourth wall stays up and his name never appears in a script.
