# Sync Ingest Protocol (Desktop-Side)

> **Context:** The learner periodically provides a list of JSON progress updates collected from mobile sessions via Home Assistant. Your job is to apply them to `progress/learner.json` and `curriculum/vocabulary_index.json`.

## When This Protocol Activates

The learner will say something like:
- "Here are my mobile updates" + paste JSON
- "Sync these progress updates"
- "Apply these to my learner file"

## Input Format

The learner provides an **array** of update objects (the contract is defined in `protocol/mobile_sync.md`):

```json
[
  {"v": 1, "ts": "2026-02-17T08:30:00", "type": "session", "level": 4, "episode": 2, ...},
  {"v": 1, "ts": "2026-02-17T09:15:00", "type": "listen", "level": 3, "episode": 1, ...},
  {"v": 1, "ts": "2026-02-17T14:00:00", "type": "feedback", "struggled": ["முன்னாடி"], ...}
]
```

## Processing Steps

### 1. Read Current State
Read `progress/learner.json` and `curriculum/vocabulary_index.json`.

### 2. Sort Updates by Timestamp
Process in chronological order (`ts` field).

### 3. Apply Each Update

For each update:

#### `session` type:
- Append to `sessions[]` in `learner.json`:
  ```json
  {
    "date": "<ts date>",
    "level": "<level>",
    "episode": "<episode>",
    "energy": "<energy>",
    "struggled": ["..."],
    "comfortable": ["..."],
    "zinger": "<zinger>",
    "notes": "<notes>",
    "source": "mobile"
  }
  ```
- Add `struggled` words to `struggled_words[]` (deduplicated)
- Move `comfortable` words from `struggled_words[]` to `comfortable_words[]`
- Update `current_level` and `current_episode` to the highest seen
- Increment `total_sessions`
- Update streak (check if consecutive day)

#### `listen` type:
- Append to `sessions[]` with `"energy": "passive"`
- Do NOT increment `total_sessions` (passive listening doesn't count as a session)
- DO update streak (listening counts for streak)

#### `feedback` type:
- Add `struggled` words to `struggled_words[]` (deduplicated)
- Move `comfortable` words from `struggled_words[]` to `comfortable_words[]`
- Append to `sessions[]` with `"energy": "feedback"`

### 4. Update Vocabulary Index

In `curriculum/vocabulary_index.json`, for each word in `comfortable`:
- Set `mastery_score` to `1` (or increment if already > 0)
- Set `last_reviewed` to the update's `ts`
- Increment `times_reviewed`

For each word in `struggled`:
- Set `mastery_score` to `0`
- Set `last_reviewed` to the update's `ts`
- Increment `times_reviewed`

### 5. Update Tier Progress

Recalculate `tier_progress` in `learner.json`:
- Count comfortable words per tier
- Update `mastered` counts

### 6. Write Back

Write updated `progress/learner.json` and `curriculum/vocabulary_index.json`.

### 7. Report

Show the learner a summary:
```
✅ Synced 3 mobile updates (2 sessions, 1 feedback)

📊 Progress:
  Tier 1: 12/69 mastered (+3)
  Tier 2: 2/46 mastered (+2)
  🔥 Streak: 5 days

⚠️  Struggled: முன்னாடி, தூங்கினேன், எழுந்தேன்
✅ Comfortable: போனேன், வந்தேன், சாப்பிட்டேன், நேத்து, இன்னைக்கு
```

## Idempotency

Updates are identified by their `ts` field. If a session with the same `ts` already exists in `sessions[]`, **skip it**. This prevents double-applying if the learner pastes the same batch twice.
