# Mobile Sync Protocol (Phone-Side)

> **Context:** Gemini on iOS has no local file system. Progress is captured as JSON blobs displayed in chat, shared via iOS Share Sheet to a Home Assistant webhook.

## When to Emit a Progress Update

Emit a JSON progress blob **whenever any of these happen:**

1. **End of a lesson/drill session** — always
2. **Learner reports listening** — "I listened to Level 3"
3. **Learner reports struggles** — "I'm struggling with future tense"
4. **Learner reports comfort** — "I feel good about past tense now"
5. **Learner explicitly asks** — "save my progress"

## The Update Contract

Every update is a single JSON object. Display it in a code block so the learner can tap Share.

```json
{
  "v": 1,
  "ts": "2026-02-17T16:30:00",
  "type": "session",
  "tier": 2,
  "mission": 1,
  "energy": "HIGH",
  "struggled": ["வேணும்", "வேண்டாம்"],
  "comfortable": ["வணக்கம்", "ஆமா", "சரி"],
  "zinger": "நேத்து என்ன பண்ணினீங்க?",
  "notes": "Good mission, nailing past tense. Future tense still shaky."
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `v` | int | ✅ | Schema version. Always `1`. |
| `ts` | string | ✅ | ISO 8601 timestamp of the update. |
| `type` | string | ✅ | One of: `session`, `listen`, `feedback` |
| `tier` | int | ✅ | Current tier number. |
| `mission` | int | ✅ | Cumulative mission number. |
| `energy` | string | ❌ | `LOW`, `MEDIUM`, `HIGH`. Only for `session` type. |
| `struggled` | string[] | ❌ | Tamil words the learner struggled with. |
| `comfortable` | string[] | ❌ | Tamil words the learner now feels comfortable with. |
| `zinger` | string | ❌ | The doorway phrase from this session. |
| `notes` | string | ❌ | Free-text summary of the session. |

### Type Definitions

| Type | When | Typical Fields |
|---|---|---|
| `session` | After an interactive lesson | All fields |
| `listen` | After passive listening | `tier`, `mission`, `notes` |
| `feedback` | Ad-hoc progress report | `struggled`, `comfortable`, `notes` |

## Example Scenarios

### After a full lesson:
```json
{
  "v": 1,
  "ts": "2026-02-17T08:30:00",
  "type": "session",
  "tier": 2,
  "mission": 2,
  "energy": "HIGH",
  "struggled": ["தூங்கினேன்", "எழுந்தேன்"],
  "comfortable": ["போனேன்", "வந்தேன்", "சாப்பிட்டேன்"],
  "zinger": "சாப்பிட்டீங்களா?",
  "notes": "Past action verbs clicking. Sleep/wake verbs need more reps."
}
```

### After listening on commute:
```json
{
  "v": 1,
  "ts": "2026-02-17T09:15:00",
  "type": "listen",
  "tier": 1,
  "mission": 5,
  "notes": "Listened twice on the train. Auto directions feel natural now."
}
```

### Random feedback mid-conversation:
```json
{
  "v": 1,
  "ts": "2026-02-17T14:00:00",
  "type": "feedback",
  "tier": 2,
  "mission": 3,
  "struggled": ["முன்னாடி", "அதுக்கு அப்புறம்"],
  "comfortable": ["நேத்து", "இன்னைக்கு"],
  "notes": "Sequencing words are hard. Time words are fine."
}
```

## Retrieval: The Pull Protocol (Lesson Initialization)

To keep your mobile context fresh across sessions:

### The Persistent Session Model (Recommended)
You do not need to upload the `mobile_bundle.zip` for every lesson. Maintain a persistent chat session in the Gemini app. To refresh your state daily:

1. **The URL Refresh:** Ask the AI: *"Fetch my latest progress from `<YOUR_HA_URL>/local/learner.json`. Update your memory of my comfortable and struggled words before we start today's session."*
2. **The JSON Paste (Backup):** If the URL fetch fails, use an iOS Shortcut to paste the latest `learner.json` text directly into the chat.

---

## Instructions for the Mobile Instructor

After generating a progress blob:

1. Display it in a fenced `json` code block.
2. Say: **"Tap Share to sync this to your system."**
3. Do NOT assume the update has been saved. You have no file access.
4. If the learner asks "did you save it?" — respond: "I've generated the update. Share it to your webhook to sync."
