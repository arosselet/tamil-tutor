# Feature Inbox

Build-itches land here instead of in the codebase. The structure is frozen at **Anna 1.0**; when the urge to re-engineer strikes mid-session, write it here in one line and keep learning. Review deliberately, later — never in the moment. Adding a row of data is learning; changing a schema waits.

## Ideas

- **Voice loop** — give Anna speech-in / speech-out on the phone, so downtime becomes *conversation* (the loop closes by talking, not by accounting). The highest-leverage next move.
- **Pull the wife in as the north star** — the real viability floor is "can I say this to her." Anna could hand a line: "try this one, tell me how it landed tomorrow." Costs no code.
- **Knock digest could carry the ticket's deck top** — today the outreach decision sees only `sync_state status` + the story, so knock targets come from the running thread. Appending the top few due deck items (fire-side only) would let doses hit what's actually due. Small `build_digest()` change; evidence: knocks currently can't target the deck directly.
