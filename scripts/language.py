#!/usr/bin/env python3
"""L0 — THE LANGUAGE PACK. Every value a fork to another language replaces, and
nothing else.

WHAT THIS REPLACES: the answer to "what would a port have to change?" being an
archaeology session across four files. `BOOTSTRAP.md` → "What Generalizes" has
listed the port surface in prose since 2026-07; `state_io` has carried the label
PORT SURFACE on the script range since 2026-08-04; and DECISIONS said the quiet
part out loud on 2026-08-24 — *the port surface is one line, or it is not a port
surface* — after finding three live copies of a range that was labelled as
having one. Prose said where the surface was; nothing made it enumerable. This
file does: the question is now `wc -l scripts/language.py`, and the guard in
`smoke/compose.py` fails the build if a value in here acquires a second home.

WHAT DOES NOT LIVE HERE, and the boundary is the useful part:

  - **Dials.** `MIN_ENGLISH_SHARE` (run_studio) is a *tripwire, not a dial* —
    it fires on an observed failure mode and has no correct per-language value
    to set. Moving it here would reframe it as something a port tunes, which is
    exactly backwards. Same for the outreach rails and the waking window: those
    are facts about ANDREW, and they already have one owner each.
  - **Prompt prose.** `mandates.py` holds the Tamil-flavoured pedagogy, and no
    refactor makes rewriting it cheaper — a port rewrites those examples rather
    than substituting a constant into them. That is the irreducible half of an
    extraction and it is honest to leave it looking that way.
  - **The episode voice POOLS.** `render_audio._CHIRP_POOL_*` and friends are
    private to the caster that reads them; one reader, one file. Only the two
    PINNED voices come here, because a pinned voice is an identity fact that six
    modules ask about, which is the property that earned this file.

Import direction: this module imports nothing — not even `state_io`, which
imports IT. Everything may import from here.
"""

import re

# ── The script ───────────────────────────────────────────────────────────────
# Tamil script is the canonical lexicon key, so a phonetic-only token can never
# mint a record. Moved here from `state_io` 2026-08-28; it arrived there from
# `sync_state` on 2026-08-04, and the last three stray copies folded in on
# 2026-08-24.
#
# THREE FORMS, TWO RANGES, and the split is the useful part.
#
# `TAMIL_RE` answers "is there any script here at all" — a lexicon key, a lint
# gate. `TAMIL_RUN` answers "where are the script spans", which is what the
# phonetic rewriter's before/after check and the English-share meter need,
# because both count WORDS and a per-character class counts characters.
TAMIL_RE = re.compile(r"[஀-௿]")
TAMIL_RUN = re.compile(r"[஀-௿]+")

# `TAMIL_TAIL_RE` is the third, and it is a DIFFERENT range: Tamil vowel signs
# plus the pulli — exactly what inflection replaces on a stem. It lived in
# `run_studio` from 2026-08-18 until 2026-08-28 and survived the 08-24 sweep for
# a precise reason worth keeping written down: that sweep's guard reads its
# needle off `TAMIL_RE.pattern` and asserts no other file's mechanism lines
# contain it. This range shares no characters with that needle, so a second
# language fact sat in a lane, four days old, passing the guard written to catch
# it. A port that changed only the labelled range would have gone on stemming
# Tamil. The guard now carries a needle per declared pattern.
TAMIL_TAIL_RE = re.compile(r"[ா-்]$")


def is_tamil(word: str) -> bool:
    """Is this token written in the canonical script?

    Lives beside its regex rather than in `state_io` (where it sat until
    2026-08-28) because a predicate is the *accessor form* of the value it
    tests, and splitting the two across files is how the range came to have four
    copies in the first place: a caller that cannot see the declaration writes
    its own.
    """
    return bool(TAMIL_RE.search(word))


# ── The pinned voices ────────────────────────────────────────────────────────
# One tutor, one sound. These moved from `render_audio` on 2026-08-28, and the
# 2026-08-23 reasoning that put them there is preserved rather than overturned:
# they belong with neither of the six lanes that read them. What changed is that
# "not a lane" turned out to have a better answer than "the TTS stack" — a
# pinned voice is an identity fact, it is a value a port replaces, and it was the
# only such value not reachable from the file that claims to hold them all. The
# episode POOLS stay in `render_audio`, which is their one reader.
ANNA_VOICE = "ta-IN-Chirp3-HD-Orus"       # pinned: Anna always sounds like the same someone
EAVESDROP_VOICE = "ta-IN-Chirp3-HD-Kore"  # pinned: the overheard aunty is one consistent voice too — ear-training tracks a speaker, and the trip's real voices are the aunties, not Anna


# ── The repository identity ──────────────────────────────────────────────────
# ONE fact, and it had three spellings until 2026-08-28: `publish.REPO` for the
# jsDelivr CDN URL, and `rebuild_rss`'s own BASE_URL and SITE_URL, each written
# out in full. A fork updated whichever one it found. Both consumers now derive
# from this, so the fork edits one line and the feed, the CDN and the site link
# move together.
REPO = "arosselet/tamil-tutor"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{REPO}/main"
SITE_URL = f"https://github.com/{REPO}"
