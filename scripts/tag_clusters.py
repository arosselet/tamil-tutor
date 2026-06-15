#!/usr/bin/env python3
"""
scripts/tag_clusters.py

Two-pass curriculum enrichment tool.

Pass 1 — Tag: classify every existing word/phrase with a single cluster label.
Pass 2 — Gap-fill: for each cluster, propose missing high-frequency Coimbatore
         Tamil words AND phrases, written to curriculum/proposed_additions.json.

Usage:
    python scripts/tag_clusters.py [--key sk-or-...] [--tier N] [--skip-gap-fill]
    python scripts/tag_clusters.py --write   # commit Pass 1 tags + write additions file

OPENROUTER_KEY env var is also accepted.
Default: dry-run (nothing written to disk).
"""

import json
import os
import re
import sys
import time
import argparse
from collections import Counter
from pathlib import Path
import urllib.request
import urllib.error

BASE = Path(__file__).parent.parent
TIERS_DIR = BASE / "curriculum" / "tiers"
ADDITIONS_OUT = BASE / "curriculum" / "proposed_additions.json"

CLUSTER_TAXONOMY = {
    "verb_past":
        "Past-tense verbs and phrases: I went, I ate, I said, I saw, I just ate, Did you eat?",
    "verb_present":
        "Present-progressive verbs: I am going, I'm asking, I'm doing it right now",
    "verb_future":
        "Future-tense verbs: I will go, I will ask, I'll come later, I'll do it",
    "verb_command":
        "Imperative/command forms: Go!, Take!, Put!, Lift!, Open!, Come here!, Be quiet!",
    "connectors":
        "Time and logic glue — words and phrases: because, therefore, but, first, "
        "after that, yesterday, today, not yet, even so",
    "family":
        "Kinship terms and family-role phrases: elder brother, maternal uncle, "
        "cross-cousin, my mother-in-law called",
    "pronouns":
        "Personal pronouns, possession, and person-marking: he, she, they (respectful), "
        "our side, your house",
    "social_reaction":
        "Conversational glue, reactions, affirmations, gossip tags: Really?, Is that so?, "
        "Yes, Okay, Right, Hmm, That's why!, Exactly!",
    "questions":
        "Question words and common question phrases: Who?, Why?, When did you go?, "
        "What happened?, How much?, Which one?",
    "emotions":
        "Feelings, attitudes, and preference phrases: happy, angry, I like this, "
        "I don't like it, Don't worry, I'm scared, I feel shy",
    "descriptions":
        "Adjectives of all kinds — size, age, quality, temperature, difficulty, color: "
        "big, new, beautiful, hot, difficult, red, tall",
    "obligation_ability":
        "Must, can, cannot, should not — and phrases: must go, can't come today, "
        "shouldn't do that, I can manage",
    "proposals":
        "Let's and shall-we forms and invitation phrases: Let's go, Shall we eat?, "
        "Want to come?, Come on, Shall we see?",
    "daily_routine":
        "Morning and household routine verbs and phrases: wake up, brush teeth, "
        "get ready, I'm leaving, came back late, it's gotten late",
    "home_kitchen":
        "House objects, controls, cooking verbs, food nouns, and domestic phrases: "
        "close the door, pour the water, rice is ready, turn on the fan, degree coffee",
    "phone_scheduling":
        "Digital communication and plan coordination — words and phrases: call me, "
        "did you get my message?, I'll confirm, cancel the plan, are you free?, postpone",
    "home_environment":
        "Domestic objects and spaces beyond the kitchen — TV, remote, newspaper, book, "
        "rooms (bedroom, bathroom, hall), spatial (inside/outside, upstairs/downstairs, "
        "near/far), noise/quiet commands, door/window/fan/light controls",
}

CLUSTER_NAMES = list(CLUSTER_TAXONOMY.keys())
CLUSTER_LIST_STR = "\n".join(f'  "{k}": {v}' for k, v in CLUSTER_TAXONOMY.items())


# ── API ────────────────────────────────────────────────────────────────────

def call_openrouter(messages, key, retries=3):
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = json.dumps({
        "model": "google/gemini-2.5-flash",
        "messages": messages,
        "temperature": 0.1,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "tamil-learning-local",
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                text = raw["choices"][0]["message"]["content"]
                # Strip markdown code fences if present
                text = re.sub(r"^```(?:json)?\s*", "", text.strip())
                text = re.sub(r"\s*```$", "", text.strip())
                return json.loads(text)
        except Exception as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"API call failed: {exc}") from exc
            time.sleep(2 ** attempt)


# ── Pass 1: Tagging ────────────────────────────────────────────────────────

TAG_SYSTEM = f"""You are classifying Tamil vocabulary entries (single words AND multi-word phrases) \
for a language-learning curriculum.

Assign each entry exactly ONE cluster from this list:
{CLUSTER_LIST_STR}

Rules:
- If an entry could fit multiple clusters, choose the one that best represents \
its PRIMARY communicative function.
- Phrases follow the same rules as single words.

Return a JSON object: {{"tags": ["cluster_name", ...]}} — one string per input entry, \
same order as input, no extras."""


def tag_batch(entries, key, batch_size=25):
    """Classify a list of entries. Returns list of cluster strings, same order."""
    all_tags = []
    for i in range(0, len(entries), batch_size):
        batch = entries[i:i + batch_size]
        numbered = "\n".join(
            f'{j+1}. Tamil: {e["tamil"]} | English: {e["english"]}'
            for j, e in enumerate(batch)
        )
        result = call_openrouter(
            [{"role": "system", "content": TAG_SYSTEM},
             {"role": "user", "content": f"Classify these {len(batch)} entries:\n{numbered}"}],
            key,
        )
        raw = result.get("tags", [])
        for k, tag in enumerate(raw):
            if tag not in CLUSTER_NAMES:
                entry = batch[k] if k < len(batch) else {}
                print(f"\n  WARN: unknown cluster '{tag}' for '{entry.get('tamil', '?')}'"
                      f" — defaulting to 'social_reaction'")
                raw[k] = "social_reaction"
        all_tags.extend(raw)
        time.sleep(0.3)
    return all_tags


# ── Pass 2: Gap-fill ───────────────────────────────────────────────────────

GAP_SYSTEM = """You are enriching a Tamil vocabulary curriculum for a specific learner:
- Andrew: an English speaker married to a native Coimbatore Tamil speaker
- Lives in Coimbatore, daily household immersion
- Target dialect: Coimbatore spoken Tamil (Kongu Tamil) — NOT formal or written Tamil
- Goal: ~800 high-frequency items for day-to-day household and social survival

CRITICAL: Include high-value PHRASES and CHUNKS, not just isolated words.
Examples of what we want: "போயிட்டு வரேன்" (I'll go and come back — the Tamil goodbye),
"சாப்பிட்டீங்களா?" (Did you eat? — the Tamil care question), "என்னாச்சு?" (What happened?).
A well-chosen phrase is worth more than five individual words.

Aim for a natural mix of roughly 50% phrases and 50% single words.

Return JSON: {"additions": [{"tamil": "...", "english": "...", "cluster": "..."}, ...]}

Only include items that genuinely come up in daily Coimbatore household life.
No literary, formal, or obscure terms. Aim for 8-12 additions per cluster."""


def gap_fill_cluster(cluster, description, existing, key):
    existing_str = (
        "\n".join(f'  {w["tamil"]} — {w["english"]}' for w in existing)
        or "  (none yet)"
    )
    user = (
        f"Cluster: {cluster}\nDescription: {description}\n\n"
        f"Already in this cluster:\n{existing_str}\n\n"
        "What important Coimbatore Tamil words and phrases are missing from this cluster? "
        "Remember: phrases are as valuable as words."
    )
    result = call_openrouter(
        [{"role": "system", "content": GAP_SYSTEM},
         {"role": "user", "content": user}],
        key,
    )
    additions = result.get("additions", [])
    for a in additions:
        a["cluster"] = cluster
    return additions


# ── I/O ────────────────────────────────────────────────────────────────────

def load_tier_files(tier_filter=None):
    files = []
    for path in sorted(TIERS_DIR.glob("tier_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if tier_filter is None or data.get("tier") == tier_filter:
            files.append((path, data))
    return files


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Tag and gap-fill the Tamil curriculum")
    parser.add_argument("--key", help="OpenRouter API key (or set OPENROUTER_KEY)")
    parser.add_argument("--write", action="store_true",
                        help="Write tagged JSONs and proposed_additions.json to disk")
    parser.add_argument("--tier", type=int, help="Process only this tier number")
    parser.add_argument("--skip-gap-fill", action="store_true",
                        help="Run Pass 1 only (no gap-fill)")
    parser.add_argument("--batch-size", type=int, default=25,
                        help="Entries per tagging API call (default: 25)")
    args = parser.parse_args()

    key = args.key or os.environ.get("OPENROUTER_KEY", "")
    if not key:
        sys.exit("Error: provide --key or set OPENROUTER_KEY env var")

    tier_files = load_tier_files(args.tier)
    if not tier_files:
        sys.exit(f"No tier files found (tier filter: {args.tier})")

    # ── Pass 1 ─────────────────────────────────────────────────────────────
    print("=== Pass 1: Tagging ===\n")
    for path, data in tier_files:
        vocab = data.get("vocabulary", [])
        untagged = [w for w in vocab if not w.get("cluster")]
        print(f"{path.name}: {len(vocab)} entries total, {len(untagged)} untagged")
        if not untagged:
            print("  All already tagged — skipping.\n")
            continue

        print(f"  Classifying in batches of {args.batch_size}...", flush=True)
        tags = tag_batch(untagged, key, batch_size=args.batch_size)
        for entry, tag in zip(untagged, tags):
            entry["cluster"] = tag

        dist = dict(sorted(Counter(w.get("cluster") for w in vocab).items()))
        print(f"  Cluster distribution: {dist}\n")

        if args.write:
            save_json(path, data)
            print(f"  Saved {path.name}")

    if args.skip_gap_fill:
        print("Gap-fill skipped (--skip-gap-fill).")
        return

    # ── Pass 2 ─────────────────────────────────────────────────────────────
    print("\n=== Pass 2: Gap-fill ===\n")

    cluster_words = {c: [] for c in CLUSTER_NAMES}
    for _, data in tier_files:
        for w in data.get("vocabulary", []):
            c = w.get("cluster")
            if c in cluster_words:
                cluster_words[c].append({"tamil": w["tamil"], "english": w["english"]})

    all_additions = {}
    total_proposed = 0
    for cluster, description in CLUSTER_TAXONOMY.items():
        existing = cluster_words[cluster]
        print(f"  {cluster} ({len(existing)} existing) ... ", end="", flush=True)
        additions = gap_fill_cluster(cluster, description, existing, key)
        all_additions[cluster] = additions
        total_proposed += len(additions)
        print(f"+{len(additions)} proposed")
        time.sleep(0.3)

    print(f"\nTotal proposed additions: {total_proposed}")
    for cluster, items in all_additions.items():
        if items:
            for item in items[:2]:
                print(f"  [{cluster}] {item['tamil']} — {item['english']}")
            if len(items) > 2:
                print(f"  [{cluster}] ... and {len(items) - 2} more")

    if args.write:
        save_json(ADDITIONS_OUT, all_additions)
        print(f"\nWrote {ADDITIONS_OUT.relative_to(BASE)}")
        print("Review curriculum/proposed_additions.json, then run:")
        print("  python scripts/apply_additions.py --write")
    else:
        print("\nDry-run — pass --write to save results.")


if __name__ == "__main__":
    main()
