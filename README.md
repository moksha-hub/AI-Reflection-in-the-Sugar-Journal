# Reflective Loop

**Adaptive AI Reflection Service for the Sugar Journal**

A standalone FastAPI microservice that generates pedagogically-grounded reflection questions for children using Sugar educational software. Built as a prototype for [GSoC 2026 — Sugar Labs](https://www.sugarlabs.org/).

## What It Does

When a child finishes or revisits a Sugar Journal entry, this service generates an age-appropriate reflection question. Unlike a generic chatbot, Reflective Loop uses three innovations:

1. **Adaptive Depth Sequencing** — Questions deepen automatically based on the child's reflection history. First session: *"What did you create?"* Tenth session: *"Where do you see this pattern in the real world?"*
2. **Activity-Strategy Mapping** — The pedagogical framework is chosen by activity type (Socratic for TurtleBlocks, KWL for Write, What/So What/Now What for Paint), not randomly.
3. **Structural Model Safety** — The LLM only receives metadata (never child content), output is validated against format rules, and any failure silently falls back to a curated static question.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the standalone demo (no LLM needed — uses mock backend)
python reflection_service.py

# Run the test suite
pytest test_reflection_service.py -v

# Start the FastAPI server
uvicorn reflection_service:app --port 8765
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health check |
| `/reflect` | POST | Generate a reflection question |
| `/strategies` | GET | List activity → strategy mappings |
| `/depth/{student_id}` | GET | Get student's depth progression |

### Example `/reflect` request

```json
{
  "activity_type": "org.laptop.TurtleArt",
  "entry_title": "My First Spiral",
  "student_id": "student_001",
  "language": "en",
  "shared_with": []
}
```

### Example response

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

## Architecture

```
ReflectRequest
     │
     ▼
┌─────────────────────────────────────┐
│  ReflectionEngine                   │
│                                     │
│  DepthTracker ── session_count      │
│       │              │              │
│       ▼              ▼              │
│  StrategySelector  get_depth_level  │
│       │              │              │
│       ▼              ▼              │
│  PromptBuilder (system + user)      │
│       │                             │
│       ▼                             │
│  LLMClient                          │
│    ├─ OllamaBackend  (default)      │
│    ├─ SugarAIBackend (school LAN)   │
│    ├─ OpenAIBackend  (opt-in)       │
│    └─ MockBackend    (testing)      │
│       │                             │
│       ▼                             │
│  validate_output() → fallback?      │
└─────────────────────────────────────┘
     │
     ▼
ReflectResponse
```

## Depth Progression

| Level | Sessions | Type | Example |
|---|---|---|---|
| 1 | 0–2 | Descriptive | "What did you create?" |
| 2 | 3–6 | Analytical | "Why did you choose that pattern?" |
| 3 | 7–14 | Connective | "Where do you see spirals in nature?" |
| 4 | 15+ | Creative | "What's the hardest version you can imagine?" |

## Languages Supported

English, Spanish, Hindi, French, Portuguese — with curated static fallback questions for each.

## LLM Backends

| Backend | Privacy | Use Case |
|---|---|---|
| **Ollama** (default) | Data never leaves device | Standard deployment |
| **Sugar-AI** | Stays on school LAN | Schools with Sugar-AI |
| **OpenAI** | Cloud (opt-in) | Explicit admin consent |
| **Mock** | N/A | Testing and demos |

## File Structure

```
reflective-loop/
├── reflection_service.py      # Main FastAPI service + all engines
├── config.py                  # Pydantic configuration schema
├── prompts.py                 # Static prompt library (5 languages)
├── test_reflection_service.py # Full pytest test suite
├── depth_store.json           # Persistent depth tracking (per-student)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Author

**Mokshagna K** — [github.com/moksha-hub](https://github.com/moksha-hub)

GSoC 2026 proposal: *Reflective Loop: An Adaptive AI Reflection System for the Sugar Journal*

## License

GPL-3.0
