# Script: The Tamil2 Protocol — Deep Dive

**Host:** You know, I was looking at the curriculum files. You’ve strictly ignored almost everything from a standard Tamil textbook. Why?

**Guest:** Because if you learn from a textbook, you end up sounding like a news anchor from the 1950s. It’s what we call "Senthamil"—Formal Tamil. It’s beautiful for literature, but it’s a disaster for the streets of Coimbatore.

**Host:** Give me an example. What’s the "Book" version versus the "Street" version?

**Guest:** Okay, take the word for "I want." In a book, you’ll learn *Vendum*. It’s heavy, it’s formal. But on the street, if you say *Vendum*, the auto driver immediately knows you’re a tourist. A local just says **Venum**.

**Host:** *Venum*. It’s shorter.

**Guest:** Exactly. Or "I am going." A book teaches you *Naan pogiraen*. A local says **Naan poren**. If you use the book version, people will understand you, but they’ll treat you like a scholar or a stranger. We’re building **Operational Capacity**. We want you to blend in.

**Host:** That’s where the **800 Lemma Theory** comes in.

**Guest:** Right. We’ve identified 800 high-frequency verbs and connectors—the "Glue" of the language. We don't waste time on Tamil nouns for things like "Computer" or "Office." We use the **Thanglish Hack**. We use the English noun and stick it to a Tamil verb.

**Host:** So I can say "Office-uku poren" (I’m going to the office)?

**Guest:** Exactly! It sounds 100% natural. You’re using your existing English vocabulary as "modules" and just learning the Tamil operating system to run them.

---

**Host:** Let’s talk about the actual engineering. This isn't a cloud app. 

**Guest:** No, I wanted total control. The "Source of Truth" is a set of Markdown files and JSON indices on my desktop. I have a Python script, `generate_episode.py`, that uses dual-voice TTS to turn those Markdowns into the podcasts you're hearing right now.

**Host:** But you listen on your phone. How do you track progress without a server?

**Guest:** That’s the **Mobile Sync Protocol**. My mobile AI generates a lean JSON blob of my progress—words I’m comfortable with, words I’m struggling with. I "Share" that JSON to a **Home Assistant webhook** on my home network. My desktop picks it up and updates the `learner.json` file. It’s a totally private, local-first feedback loop.

---

**Host:** And how does the AI actually "handle" your learning?

**Guest:** We use the **Sandwich structure**. Every session starts with a **Hook**—a high-stakes scenario. "You’re at a stall, you’ve been charged too much, and you need to negotiate." Then we do the **Mechanics**, then a **Drill**, and we end with a **Simulation**. 

**Host:** And it adapts to your energy?

**Guest:** Yeah. If my "Focus Meter" is low, it drops into **The Stream**—passive listening. If I’m on fire, it’s **Boss Fight** mode. No guilt, no pressure. 

---

**Host:** What’s the "muttering at doorways" thing? I see that in the protocol files.

**Guest:** **Quiet Broadcasting**. It’s a somatic hack. We pick one "Zinger" a day—like **நிறுத்துங்க** (*Niruthunga*), which means "Stop." I don't "study" it. I just mutter it three times whenever I walk through a doorway. I’m anchoring the language to my physical movement. I’m moving the data from my logical brain into my muscle memory. 

**Host:** So by the time you’re in an auto-rickshaw in Coimbatore...

**Guest:** My feet remember the word before my brain does.

---

**Host:** It sounds like you’ve engineered the system to be "Amnesty-first."

**Guest:** Exactly. The **Amnesty Clause** is the most important part. If I miss a week, I don't have "makeup work." I just start again. The goal is contact time, not completion.

**Host:** Little by little. 

**Guest:** **கொஞ்சம் கொஞ்சம்** (*Konjam konjam*). We’re not just learning a language; we’re installing a new reflex.

**Host:** *Sari*. I think we’re ready to build it.

**Guest:** Let's trigger the generation.
