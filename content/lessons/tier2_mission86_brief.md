# Tier 2, Mission 86 — The Family That Never Decides

## Core Targets
- **Linguistic Pattern:** The `-லாம்` tail as one machine — verb + லாம் (suggestion) → + ஆ (question) → the same tail borrowed for permission. The pattern is the payload; the words are its output.
- **Register:** mischief *(Scene Spec — gate)*
- **Dramatic Ingredient:** subtext — two people want opposite things under polite words *(Scene Spec — gate)*
- **Scenario Shape:** pattern_riff (a ~50-second `eavesdrop` vignette opens as the specimen)
- **Location class:** home_social (the hall of a house on a departure morning; one auto horn from the street)
- **Energy:** medium
- **Episode Form:** lore *(COMMISSIONED by the soak order — not re-picked)*

## Scenario Context

Five people are leaving for somewhere. Nobody is leaving. Every line in the hall
is a `-லாம்` suggestion — shall we go, shall we sit, shall we eat first, we'll see
later — and not one of them converts into a decision. Underneath the politeness two
people want opposite things: she wants to stay home (and says *traffic*, says *food*,
says *the bags are by the door*), he wanted to go twenty minutes ago (and says
*straight out, let's go*). Neither says a rude word; the tail does all the fighting.
It ends the way it always ends: the aunt, who proposed nothing, picks up a suitcase
and walks out, and the decision is made by the person carrying the bag.

Maya and Raj then take the tail apart — that is the episode. `-லாம்` is the protagonist:
what it eats (any verb), what it refuses to do (order anybody), the extra ஆ that
turns it into a question, the permission sense a nephew uses at the door, and why a
family in Coimbatore loves a form that lets everyone propose and nobody commit.
Then the one word that hides inside it — **பார்** — and the near-neighbour that does
*not*: **பக்கம்**.

## Word Payload

**NEW (5 types):**
- **கிளம்பலாமா?** (*kilambalaamaa*) — Shall we leave? — the commissioned anchor
- **அப்புறம் பார்க்கலாம்** (*appuram paakkalaam*) — We'll see later (the polite wall)
- **கடைசில பாக்கலாம்** (*kadaisila paakkalaam*) — We'll see at the end (the verdict that decides nothing)
- **பக்கம்** (*pakkam*) — side / direction — the minimal-pair contrast, short and flat
- **frame:mayi-laama** — {verb}+லாம்(ஆ) — the machine itself, made audible across கிளம்ப / சாப்பிட / போ / உட்கார / பேச / பார்க்க

**CALLBACKS (soft targets):**
- **உட்காரலாமா?** / **பேசலாமா** — deck outputs of the same machine [prod=none]
- **அப்புறம் பாக்கலாம்** — the fast-mouth twin of the payload form
- **முடிஞ்சா** — if possible (deck survival, struggled — one clause as a softener)
- **நேரா** [floor-gap] · **பத்து** [floor-gap] · **ரெண்டு** [floor-gap] · **வயிறு ஃபுல்** [floor-gap]
- **ஆமா ஆமா** · **சீக்கிரம்** · **அலைச்சல்** · **பெட்டி** · **பார்த்தேன்** · **பக்கத்துல**
- **frame:quote-nu** (‑னு, ear-only) · **frame:nearby-noun** (பக்கத்துல) · **frame:in-la**

## The Minimal Pair (Andrew's own standing request — 2026-07-27, live collision 08-09)

He produced *temple pakkalam* for "beside the temple" — which is "let's go look at a
temple." Carve it **both directions**, and carve it by *parts*, not by drill:

- **பார்க்கலாம்** = **பார்** + லாம். பார்த்தேன் (*I saw*) is already his — the same பார் sits
  at the front of it. Long ஆ. In fast speech the ர் gets eaten (**பாக்கலாம்**) but the
  **long ஆ never goes**.
- **பக்கம்** = short, flat, two beats, no ஆ, no பார் anywhere in it. A place, not a plan.
- Teach the form he actually needed: **பக்கத்துல** (*beside / next to*) — same பக்கம் with
  the -ல he repaired last week. "temple பக்கத்துல நிறுத்துங்க" is where the auto stops;
  "temple பாக்கலாம்" is a sightseeing trip.

## Vocabulary Fence (the sea — build from these)

The full 207-word fence from `suggest_targets.py` is the sea. The connective tissue of
this episode draws only from it. The ones actually load-bearing here:

- frame:mayi-laama (laama) — நான் {verb}-லாமா? → may I {verb}?
- frame:quote-nu — …-னு சொன்னாங்க → 'she said that…' (EAR ONLY)
- frame:nearby-noun — பக்கத்துல {noun} இருக்கா?
- frame:in-la (canada-la) — {noun}+ல → in/at/on
- frame:polite-nga (nga) — the polite ask — சொல்லுங்க, குடுங்க, உக்காருங்க, வாங்க
- frame:done-ittu — {verb}+இட்டு/‑ட்டு → done-and-dusted
- கிளம்பு · உட்காருங்க · சாப்பிடுங்க · போறேன் · பார்த்தேன் · குடிச்சேன்
- நேரம் ஆச்சு · நிமிஷம் · பத்து · ரெண்டு · ஒன்னு · இன்னும் கொஞ்சம்
- ஆமா ஆமா · சரி · சரி சரி · ஆனா · அப்புறம் · முதல்ல · கடைசில · தெரியுமா?
- ஜாஸ்தி · ரொம்ப · அலைச்சல் · அவசரம் இருக்கு · சீக்கிரம் · நேரா · வெளிய
- மாமா · அத்தை · தம்பி · அவங்க · எனக்கு · பெட்டி · வயிறு ஃபுல் · நிறுத்துங்க
- சொன்னாங்க · சொல்றாங்க · என்ன? · இருக்கு · இல்ல · கொஞ்சம் · முடிஞ்சா

Unfenced strangers: **0** by design. Every non-payload noun that isn't on the fence is
carried in English (*traffic, bags, door, temple, bus stop, coffee*) — which is exactly
what a Coimbatore hall sounds like anyway.

## Notes

- **Pauses on their own lines only.** `render_audio.py` converts *any* line containing
  `[Pause: N sec]` into a pause and drops that line's speech — an inline pause deletes
  the dialogue around it (M74 lost lines this way). Same for `[SFX]`, which must start
  the line.
- No Latin-script Tamil anywhere: the ta-IN voice reads Latin as English orthography,
  and this episode's whole point is a *sound* contrast. The contrast is delivered in
  Tamil script and described in English.
- Fourth wall: Maya and Raj address each other, never a listener. The auto example is
  told in the third person about "somebody", not "you".
