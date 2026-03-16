# Reflective Loop

Adaptive AI reflection service for the Sugar Journal.

This repository is a working prototype for the Sugar Labs GSoC 2026 idea "AI Reflection in the Sugar Journal". The goal is not to generate content for the learner, but to prompt reflective practice when a Journal entry is saved or revisited.

The prototype is now structured to be adaptable to Sugar itself:
- it accepts raw Sugar Journal metadata through a dedicated endpoint
- it keeps reflection history locally per Sugar profile and per activity
- it supports deployment overrides for activity-to-strategy mapping
- it uses metadata-only prompting and curated fallbacks for safety
- it includes endpoint tests, integration tests, and failure-recovery tests

## What the prototype demonstrates

### 1. Adaptive depth is deterministic and local

Depth progression is based on prior reflection count for the same profile and activity:

```python
def get_depth_level(session_count: int) -> int:
    if session_count <= 2:
        return 1
    if session_count <= 6:
        return 2
    if session_count <= 14:
        return 3
    return 4
```

The state is stored in a lightweight JSON file. No external database is required.

### 2. Strategy mapping is seeded, not overclaimed

The prototype does not pretend to classify every Sugar activity. It seeds a small, defensible core mapping and rotates unknown activities through all frameworks:

```python
DEFAULT_STRATEGY_MAP = {
    "org.laptop.TurtleArt": "socratic",
    "org.sugarlabs.MusicBlocksActivity": "socratic",
    "org.laptop.Write": "kwl",
    "org.laptop.Read": "kwl",
    "org.laptop.Paint": "what_so_what_now_what",
    "org.laptop.Sketch": "what_so_what_now_what",
}
```

Deployments can extend or override this mapping through configuration.

### 3. The Journal integration surface is real

The service exposes `POST /reflect-from-journal`, which accepts raw datastore-style metadata and adapts it into the stable reflection request used by the engine.

Supported metadata fields include:
- `bundle_id`
- `activity`
- `title`
- `buddies`
- `language`

The buddies parser matches Sugar's current metadata pattern, where `buddies` is typically JSON that decodes to a dictionary of buddy records.

### 4. Privacy and safety are structural

The model prompt contains metadata only:
- activity bundle ID
- local session count
- language
- collaborative state

The Journal title remains local to the UI and is not sent to the model.

Generated output must pass a strict structural validator:
- exactly one question
- ends with `?`
- no newline
- bounded length
- no blocked keywords

If generation fails or validation fails, the service silently falls back to a curated static question.

### 5. The backend layer matches current deployment reality better

Backends included:
- `mock` for tests and demos
- `ollama` for local inference
- `sugar_ai` for LAN deployments
- `openai` as a compatibility path only

The Sugar-AI client uses a prompted chat-style request shape and tolerates response-shape variations to make integration less brittle.

## Architecture

```text
Raw Journal metadata
        |
        v
JournalMetadataAdapter
        |
        v
ReflectRequest
        |
        v
ReflectionEngine
  |- DepthTracker
  |- StrategySelector
  |- PromptBuilder
  |- LLMClient
        |
        v
ReflectResponse
```

## API

### `POST /reflect`

Use this when the caller already knows the normalized request shape.

Example:

```json
{
  "activity_type": "org.laptop.TurtleArt",
  "entry_title": "My Spiral",
  "profile_id": "profile_001",
  "language": "en",
  "shared_with": []
}
```

### `POST /reflect-from-journal`

Use this when the caller is passing raw Sugar Journal metadata.

Example:

```json
{
  "metadata": {
    "bundle_id": "org.laptop.Paint",
    "title": "My Painting",
    "buddies": "{\"1\": [\"Asha\", \"#000000,#ffffff\"]}"
  },
  "profile_id": "profile_001",
  "language": "pt_BR.UTF-8"
}
```

### `GET /health`

Returns service status and the active backend.

### `GET /strategies`

Returns the effective strategy map, including deployment overrides.

### `GET /depth/{profile_id}`

Returns local reflection counts and computed depth levels per activity.

## Quick start

```bash
git clone https://github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal.git
cd AI-Reflection-in-the-Sugar-Journal
pip install -r requirements.txt
python reflection_service.py
pytest -q
uvicorn reflection_service:app --port 8765
```

## Configuration

Key options in `config.py`:
- `llm_backend`
- `ollama_url`
- `ollama_model`
- `sugar_ai_url`
- `sugar_ai_api_key`
- `openai_api_key`
- `request_timeout_seconds`
- `depth_store_path`
- `default_language`
- `strategy_overrides`
- `blocked_keywords`

## Test status

The test suite currently has `51` passing tests.

It covers:
- depth tracking, persistence, reset, and corrupted-store recovery
- strategy selection and deployment overrides
- prompt construction and metadata-only prompting
- locale normalization and buddies parsing
- output validation and fallback behavior
- end-to-end reflection flow
- FastAPI endpoints, including `/reflect-from-journal`

Run:

```bash
pytest -q
```

Expected output:

```text
51 passed
```

## Repository layout

```text
AI-Reflection-in-the-Sugar-Journal/
|- reflection_service.py
|- config.py
|- prompts.py
|- test_reflection_service.py
|- requirements.txt
`- README.md
```

## Why this is a stronger proposal prototype

This prototype now proves the parts of the proposal that matter most:
- adaptive questioning can be implemented without reading prior private answers
- the state model fits Sugar's local profile model better than a classroom roster model
- Journal metadata can be adapted directly into the service
- collaborative reflection can be grounded in existing `buddies` metadata
- the backend story is pluggable without making the proposal depend on cloud inference

What it does not claim:
- exhaustive mapping for every Sugar activity
- a teacher dashboard
- semantic analysis of past reflection content
- full-scale model pretraining from scratch

## Related Sugar work

- [Sugar Labs organization](https://github.com/sugarlabs)
- [Music Blocks Reflection Widget PR #5446](https://github.com/sugarlabs/musicblocks/pull/5446)
- [Sugar Journal Select All fix PR #1077](https://github.com/sugarlabs/sugar/pull/1077)

## License

GPL-3.0
