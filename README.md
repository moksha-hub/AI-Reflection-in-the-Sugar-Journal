# 🔄 Reflective Loop

**Adaptive AI Reflection Service for the Sugar Journal**

> *"The Sugar Journal stores every project a child has ever made — but it has never helped them think about what they made, why it matters, or what to try next."*

A standalone FastAPI microservice that generates pedagogically-grounded reflection questions for children using [Sugar](https://www.sugarlabs.org/) educational software. Built as a working prototype for the [GSoC 2026 — Sugar Labs](https://wiki.sugarlabs.org/go/Summer_of_Code/2026) project: **AI Reflection in the Sugar Journal**.

---

## ✨ What Makes This Different

Most AI-in-education proposals do one of two things: generate content *for* the child, or check if the child's answer is correct. **Reflective Loop does neither.** It asks questions that have no single correct answer — questions that ask the child to look inward.

| Feature | Generic Chatbot | Other GSoC Proposals | **Reflective Loop** |
|---|---|---|---|
| Strategy selection | Random | Age-based | **Activity-type-based** (Socratic for coding, KWL for writing) |
| Question depth | Static | Hopes LLM "gets it" | **Deterministic depth progression** (4 levels, history-tracked) |
| Safety model | Content filter | Trust the model | **Structural: no child content sent + output validation + static fallback** |
| Collaborative awareness | None | None | **Detects shared sessions from Journal metadata** |
| Offline support | Cloud-only | Cloud-only | **Ollama local-first by default** |

---

## 🏗️ Architecture

```
ReflectRequest (from Sugar Journal)
     │
     ▼
┌──────────────────────────────────────────────┐
│  ReflectionEngine                            │
│                                              │
│  1. DepthTracker                             │
│     └─ session_count → depth_level (1–4)     │
│                                              │
│  2. StrategySelector                         │
│     └─ activity_type → framework             │
│        TurtleBlocks → Socratic               │
│        Write/Read   → KWL                    │
│        Paint/Sketch → What/So What/Now What  │
│        Unknown      → Rotating cycle         │
│                                              │
│  3. PromptBuilder                            │
│     └─ strategy × depth × language → prompt  │
│     └─ if shared_with → inject peer question │
│                                              │
│  4. LLMClient                                │
│     ├─ OllamaBackend  (local, default)       │
│     ├─ SugarAIBackend (school LAN)           │
│     ├─ OpenAIBackend  (cloud, opt-in)        │
│     └─ MockBackend    (testing)              │
│                                              │
│  5. OutputValidator                          │
│     └─ validate → pass or silent fallback    │
└──────────────────────────────────────────────┘
     │
     ▼
ReflectResponse (question + metadata)
```

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal.git
cd AI-Reflection-in-the-Sugar-Journal

# Install dependencies
pip install -r requirements.txt

# Run the standalone demo (no LLM needed — uses mock backend)
python reflection_service.py

# Run the full test suite
pytest test_reflection_service.py -v

# Start the FastAPI server
uvicorn reflection_service:app --port 8765
```

---

## 📊 Adaptive Depth Sequencing

Questions deepen automatically based on the child's reflection history. This is deterministic — not "hoping the LLM generates something harder."

```
Session  1 │ ●○○○ │ L1 Descriptive │ "What did you create in this activity?"
Session  2 │ ●○○○ │ L1 Descriptive │ "What did you create in this activity?"
Session  3 │ ●●○○ │ L2 Analytical  │ "Why did you choose to do it that way?"
Session  7 │ ●●●○ │ L3 Connective  │ "Where have you seen patterns like this in the real world?"
Session 15 │ ●●●● │ L4 Creative    │ "If you could teach someone else, what would be most important?"
```

The depth is tracked per-student, per-activity in a lightweight JSON file. No cloud sync. No external database.

### How It Works (Code)

```python
def get_depth_level(session_count: int) -> int:
    if session_count <= 2:  return 1  # Descriptive
    if session_count <= 6:  return 2  # Analytical
    if session_count <= 14: return 3  # Connective
    return 4                          # Creative
```

---

## 🎯 Activity-Strategy Mapping

The reflection framework is chosen by **what the child is doing**, not randomly:

| Activity Type | Strategy | Pedagogical Rationale |
|---|---|---|
| **TurtleBlocks, MusicBlocks, Pippy** | Socratic | Procedural creation → guided questioning surfaces *why* those choices were made |
| **Write, Read** | KWL (Know/Want/Learn) | Narrative work → knowledge-state reflection maps naturally |
| **Paint, Sketch, Etoys** | What / So What / Now What | Aesthetic creation → experience-first reflection before analysis |
| **Calculate, Measure** | Socratic | Quantitative → Socratic questions expose misconceptions |
| **Unknown / custom** | Rotating (cycles all 3) | Ensures exposure to all frameworks over time |

### How It Works (Code)

```python
STRATEGY_MAP = {
    "org.laptop.TurtleArt":    "socratic",
    "org.laptop.Write":        "kwl",
    "org.laptop.Paint":        "what_so_what_now_what",
    # ... 11 Sugar activities mapped
}

def select(activity_type: str, session_count: int = 0) -> str:
    if activity_type in STRATEGY_MAP:
        return STRATEGY_MAP[activity_type]
    # Unknown activities: rotate through all strategies
    return STRATEGIES[session_count % len(STRATEGIES)]
```

---

## 🛡️ Structural Model Safety

Safety is **architectural**, not a post-hoc filter:

### Layer 1: No Child Content Sent
The LLM only receives metadata (`activity_type`, `session_count`, `entry_title`). It never sees what the child wrote, drew, or coded.

### Layer 2: Constrained Output
The system prompt forces exactly ONE question ending in `?`. No open-ended conversation. No content generation.

### Layer 3: Output Validation with Static Fallback
```python
def validate_output(text: str) -> bool:
    text = text.strip()
    return (
        text.endswith("?")             # Must be a question
        and 10 < len(text) < 300       # Single question, not a paragraph
        and not any(kw in text.lower() for kw in BLOCKED_KEYWORDS)
    )

async def get_reflection(prompt, fallback_question: str) -> str:
    raw = await backend.generate(prompt)
    return raw if validate_output(raw) else fallback_question
```

**Model failure mode = safe static question. Never unsafe content.**

---

## 🤝 Collaborative Reflection Awareness

Sugar's Journal natively tracks shared sessions via `buddy-list` metadata. When detected, the system injects a peer-awareness question:

| Strategy | Solo Question | + Collaborative Question |
|---|---|---|
| Socratic | *"Why did you choose that pattern?"* | + *"What surprised you about how your partner approached it?"* |
| KWL | *"What did you learn?"* | + *"What did your collaborator teach you that you didn't already know?"* |
| WWWW | *"What would you do differently?"* | + *"How did working together change what you ended up making?"* |

No new mode. No new strategy. Just a contextual injection when the Journal signals a share.

---

## 🌍 Multilingual Support

Curated static fallback questions in **5 languages**:

| Language | Code | Coverage |
|---|---|---|
| English | `en` | All strategies × 4 depths + peer questions |
| Spanish | `es` | All strategies × 4 depths + peer questions |
| Hindi | `hi` | All strategies × 4 depths + peer questions |
| French | `fr` | All strategies × 4 depths + peer questions |
| Portuguese | `pt` | All strategies × 4 depths + peer questions |

Language is auto-detected from the Sugar locale setting.

---

## 🔌 API Reference

### `POST /reflect`

Generate a reflection question for a Journal entry.

**Request:**
```json
{
  "activity_type": "org.laptop.TurtleArt",
  "entry_title": "My First Spiral",
  "student_id": "student_001",
  "language": "en",
  "shared_with": []
}
```

**Response:**
```json
{
  "question": "What did you create in this activity?",
  "strategy": "socratic",
  "depth_level": 1,
  "session_count": 1,
  "is_collaborative": false,
  "peer_question": null
}
```

**Collaborative Response (shared_with populated):**
```json
{
  "question": "Why did you choose to do it that way instead of another way?",
  "strategy": "socratic",
  "depth_level": 2,
  "session_count": 5,
  "is_collaborative": true,
  "peer_question": "What surprised you about how your partner approached the problem?"
}
```

### `GET /health`
Returns service status and active backend.

### `GET /strategies`
Lists all activity → strategy mappings.

### `GET /depth/{student_id}`
Returns depth progression for a specific student across all activities.

---

## 🧪 Test Suite

**33 tests, all passing.** Covers every component:

| Component | Tests | What's Tested |
|---|---|---|
| `DepthTracker` | 8 | Counting, persistence, depth boundaries, student isolation, reset |
| `StrategySelector` | 5 | All mapped activities, unknown activity rotation |
| `PromptBuilder` | 6 | Fallback coverage, peer questions, collaborative injection, language fallback |
| `LLMClient` | 8 | Validation rules, blocked keywords, backend failure fallback |
| `ReflectionEngine` | 6 | Full pipeline, depth progression, collaboration, multilingual, strategy routing |

```bash
$ pytest test_reflection_service.py -q
..................................
33 passed in 0.57s
```

---

## 🔧 LLM Backends

| Backend | Privacy | Use Case | Config |
|---|---|---|---|
| **Mock** | N/A | Testing & demos | `llm_backend: mock` |
| **Ollama** | Data never leaves device | Default deployment | `llm_backend: ollama` |
| **Sugar-AI** | Stays on school LAN | Schools with Sugar-AI | `llm_backend: sugar_ai` |
| **OpenAI** | Cloud (explicit opt-in) | Admin consent required | `llm_backend: openai` |

---

## 📁 File Structure

```
AI-Reflection-in-the-Sugar-Journal/
├── reflection_service.py      # Main FastAPI service + all engine components
├── config.py                  # Pydantic configuration schema
├── prompts.py                 # Static prompt library (5 languages) + peer questions
├── test_reflection_service.py # 33 pytest tests — all passing
├── depth_store.json           # Persistent depth tracking (per-student × activity)
├── requirements.txt           # Python dependencies
├── .gitignore                 # Standard Python gitignore
└── README.md                  # This file
```

---

## 📚 Pedagogical References

1. Papert, S. (1980). *Mindstorms: Children, Computers, and Powerful Ideas.* Basic Books.
2. Hattie, J. & Timperley, H. (2007). The Power of Feedback. *Review of Educational Research*, 77(1), 81–112.
3. Bransford, J., Brown, A., & Cocking, R. (2000). *How People Learn.* National Academy Press.

---

## 🔗 Related

- **GSoC 2026 Proposal**: [Reflective Loop: An Adaptive AI Reflection System for the Sugar Journal](https://github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal)
- **Sugar Labs Contributions by Author**:
  - [PR #5446 — XSS fix in Reflection Widget](https://github.com/sugarlabs/musicblocks/pull/5446) ✅ Merged by Walter Bender
  - [PR #5919 — Dynamic backend URL in reflection.js](https://github.com/sugarlabs/musicblocks/pull/5919)
  - [PR #6174 — Prevent projectAlgorithm overwrite](https://github.com/sugarlabs/musicblocks/pull/6174)
  - [PR #6176 — Prevent dropped user queries](https://github.com/sugarlabs/musicblocks/pull/6176)
  - [PR #1077 — Fix Journal Select All button](https://github.com/sugarlabs/sugar/pull/1077)

---

## 👤 Author

**Mokshagna K** — [github.com/moksha-hub](https://github.com/moksha-hub)

GSoC 2026 · Sugar Labs · *Reflective Loop: An Adaptive AI Reflection System for the Sugar Journal*

## 📄 License

GPL-3.0
