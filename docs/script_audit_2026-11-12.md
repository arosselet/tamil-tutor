# Script audit of the recent feed — findings (2026-11-12, Rio)

Method: the recent feed scripts read on their own terms — episode scripts M95, M97, M98, M99 with tags, briefs and captions; knock tapes Nov 3–12 (`progress/knock_log.json` memo_scripts); rotation scripts Nov 3, 6, 9; plus `progress/learner.json`, `progress/lexicon.json`, `progress/session_log.json` and the recent commits — checked against the repo's own rules and books. Andrew's felt report was not used as evidence here. No fix is proposed in this doc; each finding names what needs looking into.

Scope limit: the Nov 11 drill audio and every payoff audio have no stored script text in the repo, so those feed items were not examinable from the scripts.

Finding 7 overlaps the already-filed episode-99 feedback (`docs/episode_99_feedback_2026-11-12.md`); it is included here because it is a script-vs-rule finding from this audit, not only a felt report.

## 1. Coverage is claimed on appearance, and the books contradict themselves

M99 lands நாம exactly once (`content/scripts/tier2_mission99.tags.json`, new_words_landed நாம: 1), and `progress/learner.json` closes the soak order on it (attempted 2026-11-11, episode 99, unclaimed: []). But the lexicon row for நாம says recognition "untested", production "none", heard_times 1. The order is closed and the word is untested at the same time. Same split inside one row: போனோம் is production "cold" with recognition "untested", reps 6, heard_times 1.

## 2. The payoff rests on a word the books say is not yet heard

நாங்க is recognition "struggled", heard_on null, seen in 6 episodes including 99. The Nov 10 session log records it read as "they" again that same morning. M99's whole turn — "one vowel different: naama" — is built on the naanga/naama pair with naanga as the known half. The script treats it as known; the books say struggled, never heard by ear.

## 3. New-item load is over the standing band in M99, and density swings with no enforced band

M99 lands 7 new words; the proposed band from Oct 23 (never settled) is 5 or fewer. M97 lands 5, M98 lands 4. Intercept Tamil density in the tags: M98 0.45, M97 0.9, M99 0.8. M99's brief also loads four contrasts into one payoff: the person-tail rhyme, naama/naanga, polaam/ponom, irukku/irukken.

## 4. The same knock target twice in six days, with nothing in between

தெரியுமா is the target of the Nov 6 tape and the Nov 12 tape. Its lexicon row says taught_on null, recognition "untested", last surfaced Aug 5 (episode 82). The Nov 6 tape's only exchange is a "Hello world" three days later, verdict "chat", fired []. No evidence it was caught; the lane ordered it again anyway.

## 5. The payoff lags the tape, and the newest tape has none

Payoff audio files run through Nov 10; there is no payoff for the Nov 12 tape. The tapes are Tamil-only — the Nov 10 tape is over a hundred Tamil words with its one target line, "அவரால தூக்கவே முடியல", buried mid-tape — and meaning arrives in a separate artifact, later or never. The Oct 19 tape never got one at all ("will not be retried — no meaning for line [1..6] of 9").

## 6. The recent feed is one-way

Nov 9 fielding, Nov 10 eavesdrop, Nov 12 eavesdrop: reply None, all three. Only the Nov 11 text knock got a reply (hinted). No ratings since Oct 16.

## 7. The naming rule contradicts itself

`protocol/studio/hosts.md` says at the top that the visitor may be spoken to and named, and further down still says "his name never appears in a script." M99 names him three times in the fiction plus once in the Breakdown; the Nov 10 and Nov 12 knock tapes name him three times each in the third person; the Nov 3 and Nov 6 tapes never mention him.

## 8. The rotation tape scaffolds unevenly within itself

The Nov 9 rotation gives Tamil line, then English gloss, line by line, in the drills and inventory — but the eavesdrop movement (ten Tamil lines) and the closing lap repeat everything with no gloss anywhere.

## 9. M96 doesn't exist

Scripts, captions and lessons jump from 95 to 97; no file with 96 anywhere in the tree. Open question: is the gap deliberate?
