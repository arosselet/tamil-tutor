# MASTER LESSON PLAN

## 0. SCENE SPEC
**Register:** mischief
**Form:** lore
**Ingredient:** subtext — two people want opposite things under polite words (brother wants to keep the gift, sister wants it but pretends to be too busy to get it).

## 1. CAST
- **Thambi (Younger Brother):** Mischievous, has something Akka wants, pretending to be helpful.
- **Akka (Elder Sister):** Proud, wants the item, pretending to be too busy to care.

## 2. SYNOPSIS
Thambi returned from Uncle's house with news of a beautiful gift (a shirt). He knows Akka wants it but hates asking Uncle. They do a polite dance where she claims she's busy and he threatens to take it for himself, forcing her to finally crack and claim it.

## 3. THE MENU (CONSTRAINTS)
- **Floor-Gap Targets:** சரி, ஆனா, இருக்கு, அண்ணா, சொன்னாங்க, மாமா, கிட்ட, பிடிக்காது
- **Engines to Fire:** `needtogo-place`, `adverb-aa`, `cant-முடியல`, `day-recap`, `obligation-ணும்`, `present-future-toggle`, `we-om`
- **Due Callbacks:** பிடிக்காது, அழகான, வலது, சொன்னாங்க, நேரா
- **New Cluster [verb_future]:** அப்புறமா வரேன், அழைப்பேன், எடுப்பேன், கேப்பேன், கொடுப்பேன்

## 4. THE BEATS

### Beat 1: The Bait
*Thambi casually drops the news of his trip, dropping the hook.*

**Thambi:** நேத்து மாமா வீட்டுக்கு போனோம், ரொம்ப நல்லா இருந்துச்சு.
*(Yesterday we went to Uncle's house, it was really good.)*
[Fires: `day-recap`, `we-om`, மாமா]

**Akka:** சரி.
*(Okay.)*
[Fires: சரி]

**Thambi:** அண்ணா சொன்னாங்க, அங்க ஒரு அழகான சட்டை இருக்கு.
*(Anna said, there is a beautiful shirt there.)*
[Fires: அண்ணா, சொன்னாங்க, அழகான, இருக்கு]

### Beat 2: The Polite Deflection
*Akka wants it, but plays hard to get.*

**Akka:** ஆனா, நான் இப்போ சென்னைக்கு போகணும்.
*(But, I must go to Chennai now.)*
[Fires: ஆனா, `needtogo-place`, `obligation-ணும்`]

**Thambi:** நேரா மாமா கிட்ட போங்க.
*(Go straight to Uncle.)*
[Fires: நேரா, கிட்ட]

**Akka:** என்னால போக முடியல. அப்புறமா வரேன்.
*(I can't go. I'll come later.)*
[Fires: `cant-முடியல`, அப்புறமா வரேன் (verb_future)]

### Beat 3: The Squeeze & The Crack
*Thambi pushes her buttons; she finally breaks.*

**Thambi:** நீங்க கோபமா சொல்றீங்க. சட்டை உனக்கு பிடிக்காது?
*(You are saying it angrily. You don't like the shirt?)*
[Fires: `adverb-aa` (கோபமா), பிடிக்காது]

**Akka:** பிடிக்கும்! நான் இப்போ கேக்குறேன்... இல்ல, நாளைக்கு கேப்பேன்.
*(I like it! I am asking now... no, I will ask tomorrow.)*
[Fires: `present-future-toggle` (கேக்குறேன் / கேப்பேன்), கேப்பேன் (verb_future)]

**Thambi:** நான் வலது பக்கம் போயிட்டு, சட்டை எடுப்பேன்.
*(I will go to the right side, and I will take the shirt.)*
[Fires: வலது, எடுப்பேன் (verb_future)]

**Akka:** வேண்டாம்! நான் உனக்கு பழைய சட்டை கொடுப்பேன். மாமாவை நான் அழைப்பேன்!
*(No! I will give you an old shirt. I will call Uncle!)*
[Fires: பழைய, கொடுப்பேன் (verb_future), அழைப்பேன் (verb_future)]
