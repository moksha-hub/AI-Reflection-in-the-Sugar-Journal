# GSoC 2026 Proposal - Sugar Labs

## AI Reflection in the Sugar Journal

## Basic Details

| Field | Info |
|---|---|
| Full Name | Mokshagna K |
| Preferred Name | Moksha |
| Email | mokshagnak004@gmail.com |
| GitHub | [github.com/moksha-hub](https://github.com/moksha-hub) |
| Discord | moksha__k |
| University | Amrita Vishwa Vidyapeetham |
| Program / Year | B.Tech Computer Science Engineering, 3rd Year |
| Expected Graduation | July 2027 |
| Timezone | IST (UTC+5:30) |
| Availability | 30-35 hours/week during the coding period |

## Title

**Reflective Loop: An Adaptive AI Reflection System for the Sugar Journal**

---

## Synopsis

Sugar gives children powerful tools for creating, but the Journal still treats reflection mostly as an empty form after the work is done. This proposal adds a guided reflection layer to the Sugar Journal so that journaling becomes part of the learning process, not just the storage process.

The feature is intentionally not a generic chatbot. It is a bounded reflection system that asks one short, age-appropriate question at a time when a Journal entry is created or updated as part of the save/pause journaling flow. The question adapts using local context that Sugar already has:

- the activity type,
- the current locale,
- whether the work was collaborative,
- how often this Sugar profile has reflected on similar work before.

The core idea is simple: early reflections should be descriptive, and later reflections can become more analytical or connective. That progression can be implemented locally and safely without requiring a classroom database or semantic analysis of previous private answers.

This project directly matches the official Sugar Labs idea:

1. research approaches to reflective practice,
2. adapt an open-source LLM workflow for reflection prompting,
3. expose the reflection model through FastAPI,
4. integrate it into the Sugar Journal so reflection appears as part of the overall Sugar experience.

---

## Why This Project Matters

### For Learners

Sugar is built around constructionist learning: children learn by making. Reflection is the natural next step after making, because it helps children articulate what they tried, what worked, what they learned, and what they want to do next.

This proposal strengthens that part of the experience without turning Sugar into a tutoring chatbot. The system does not generate projects for the learner and does not grade them. It simply scaffolds reflection.

### For Sugar Labs

Last summer, Diwangshu Kakoty implemented AI-assisted reflection inside Music Blocks. This proposal extends that direction into the Sugar Journal, where reflection can become part of the broader Sugar workflow rather than remaining specific to one activity.

### For Feasibility

This project is realistic because it builds on:

- existing Journal signals in Sugar,
- existing reflection-related work in Music Blocks,
- existing FastAPI-based Sugar Labs AI infrastructure,
- an already working prototype with passing tests.

---

## Related Work and Current Technical Context

### Diwangshu Kakoty's Reflection Widget Work

The Music Blocks reflection widget already demonstrates several useful lessons:

- FastAPI is an acceptable boundary between UI and AI logic,
- reflection prompts benefit from strong structure,
- the reflection flow should feel native to the activity instead of bolted on.

Its current backend uses endpoints such as `/projectcode`, `/chat`, `/analysis`, and `/updatecode`. My project does not duplicate that conversational widget. Instead, it adapts the general direction into a Journal-native, one-question reflection flow.

### Sugar-AI

Sugar-AI is now the broader Sugar Labs AI backend and already supports custom prompting. That makes it a practical target for integration and experimentation.

However, the project idea also asks for open-source LLM work. To stay practical, I am not claiming I will pretrain a model from scratch. My plan is:

- begin with prompt-engineered evaluation on open-source instruct models,
- assess reliability on the constrained reflection task,
- use lightweight task adaptation only if prompt-only behavior is not good enough.

That is a realistic interpretation of the requirement within 350 hours.

### Sugar Journal Internals Relevant to This Project

The proposal is grounded in current Sugar code:

- `journalactivity.py` already connects to `model.created` and `model.updated`.
- `detailview.py` already manages the detail view where a reflection panel can be shown.
- `expandedentry.py` already handles metadata display and collaborator information.
- `model.py` already exposes `buddies` metadata and datastore update behavior.
- metadata-only writes already use `update_mtime=False`, which matters for controlling reflection triggers.

These are the exact code-level anchors I want to build on.

---

## Core Design

### 1. Adapting Across the Variety of Sugar Activities

Walter Bender asked how the system should adapt to the variety of Sugar activities. My answer is: the v1 design should be seeded, not exhaustive.

Different activities invite different kinds of reflection, but it would be unrealistic to claim a complete taxonomy for the whole Sugar ecosystem in one summer. So the system will start with a small, defensible mapping for core activity families:

- Socratic for procedural creation such as TurtleBlocks and Music Blocks
- KWL for reading and writing activities such as Write and Read
- What / So What / Now What for expressive activities such as Paint and Sketch
- generic fallback for unknown activities

For unknown or custom activities, the system rotates through the available frameworks rather than pretending it can perfectly classify them. The prototype already supports deployment-specific overrides, so the mapping can be extended safely as experience grows.

### 2. Adaptive Depth Sequencing

The reflection question should become deeper over time, but that adaptation should remain understandable and safe. In v1, adaptation is based on local per-profile history, not semantic analysis of previous private responses.

| Depth Level | Basis | Reflection Style |
|---|---|---|
| Level 1 | first reflections | descriptive: what happened |
| Level 2 | repeated reflections | analytical: why those choices |
| Level 3 | continued reflections | connective: links to other ideas or experiences |
| Level 4 | sustained reflection history | transfer-oriented: what next, what harder version, what to explain to others |

The progression is stored locally in a lightweight JSON structure keyed by profile and activity.

### 3. Model Safety by Structure

Walter also asked how model safety will be handled. My answer is that safety should be structural, not bolted on afterward.

The v1 safety model is:

- metadata-only prompting rather than sending the child's work or previous private answers,
- a system prompt that asks for exactly one reflection question,
- output validation that rejects malformed or unsafe responses,
- curated static fallbacks when the model output is invalid.

This means a model failure produces a safe static reflection question rather than an unsafe conversational response.

### 4. Collaborative Reflection Awareness

Walter also pointed out that if there is evidence of a share, it should be considered in the reflection. I agree, and this is one of the strongest parts of the design.

When Journal metadata shows collaborators via `buddies`, the reflection question can become collaboration-aware. For example, instead of only asking what the learner did, the system can also ask what changed because the work was shared.

This is feasible because the metadata already exists in Sugar today, and the prototype already parses this metadata shape directly.

---

## Technical Plan

### FastAPI Service

The reflection service will expose:

- `POST /reflect`
- `POST /reflect-from-journal`
- `GET /health`
- `GET /strategies`
- `GET /depth/{profile_id}`

The request will include:

- `activity_type`
- `profile_id`
- `language`
- collaboration signal

The response will include:

- generated reflection question
- selected strategy
- depth level
- updated session count
- whether the work was collaborative

The additional `/reflect-from-journal` endpoint exists specifically to make Sugar integration cleaner: it accepts raw Journal metadata and adapts it into the stable reflection request used by the engine.

### Model and Prompting Workflow

The model pipeline will be constrained rather than open-ended:

1. choose a strategy,
2. compute depth from local history,
3. build a short, tightly-scoped prompt,
4. generate one question,
5. validate the output,
6. fall back to a curated static prompt if validation fails.

This structure matters because it makes the AI portion testable and makes failure safe.

### Sugar Integration

The Journal-side integration will likely involve:

- using Journal create/update events that correspond to save/pause journaling flow,
- requesting a reflection question from the FastAPI service,
- embedding a reflection panel in the Journal detail view,
- refreshing correctly when the underlying metadata changes.

The implementation will also explicitly test how metadata-only edits interact with `model.updated` so that reflection logic does not spam or retrigger incorrectly.

---

## Prototype Evidence

I do not want the proposal to rely only on future promises. I already have a working prototype in this repository.

### Current Prototype Files

| File | What it proves |
|---|---|
| `reflection_service.py` | end-to-end FastAPI reflection service with strategy selection, adaptive depth, backend abstraction, validation, Journal metadata adaptation, and collaboration-aware handling |
| `prompts.py` | curated fallback prompt library and peer-awareness prompts across languages |
| `config.py` | explicit service configuration, backend selection, timeouts, and strategy override model |
| `test_reflection_service.py` | automated evidence that the service behavior is stable and testable |
| `README.md` | developer-facing architecture and usage notes |

### What the Prototype Already Demonstrates

- deterministic adaptive depth progression,
- collaboration-aware prompting,
- FastAPI boundary design,
- direct adaptation from raw Sugar Journal metadata,
- local profile history instead of a classroom-student abstraction,
- deployment-specific strategy overrides,
- metadata-only prompt construction,
- structural output validation with safe fallback,
- automated tests for the full service surface.

### Current Prototype Verification

At the time of this proposal revision, the prototype test suite passes:

- **51 tests passing**

That does not mean the full Sugar Journal integration is already done, but it does mean the core reflection engine is no longer hypothetical.

---

## Deliverables

| Milestone | Deliverable | Evidence |
|---|---|---|
| Community Bonding | reflection-framework research notes, Journal integration notes, design discussion with mentors | shared design summary |
| M1 | reflection strategy library, fallback prompt library, service schema, test harness | passing unit tests and documented API contract |
| M2 | working FastAPI reflection service backed by an open-source model workflow and deterministic fallback behavior | end-to-end service demo and integration tests |
| M3 | Journal detail-view integration showing generated reflection questions after save/update flow | running Sugar demo or mentor walkthrough |
| M4 | adaptive depth persistence plus collaboration-aware reflection using existing metadata | repeated-session and shared-session demo |
| M5 | documentation, packaging notes, final cleanup, final report | final docs and final submission |

### Optional Stretch Goals

| Stretch Goal | Why it is stretch-only |
|---|---|
| broader multilingual prompt coverage | useful, but secondary to core Journal integration |
| learner-facing reflection history view | promising once the core loop is stable |
| lower-spec deployment tuning for local model use | depends on time after core functionality lands |

---

## Timeline

### Community Bonding

- read the full Journal integration path
- review Diwangshu's reflection work in Music Blocks
- research reflective-practice frameworks and narrow the v1 strategy set
- define evaluation criteria for question quality and model compliance

### Weeks 1-2

- finalize strategy library
- create fallback prompt sets
- define request/response schema
- assemble evaluation examples for the reflection task

### Weeks 3-4

- implement and harden the FastAPI service
- add mock mode and open-source-model path
- add validation and fallback logic
- complete tests for core service behavior

### Weeks 5-6

- integrate the service into Sugar Journal detail flow
- add reflection panel UI
- wire up Journal lifecycle triggers
- prepare a midterm demo with visible Journal integration

### Weeks 7-8

- persist adaptive depth locally
- add collaboration-aware questioning
- refine trigger behavior for metadata-only updates
- expand test coverage for repeated and shared cases

### Weeks 9-10

- evaluate open-source model behavior against the reflection rubric
- improve prompts or perform lightweight task adaptation if needed
- test reliability and latency under realistic development conditions

### Weeks 11-12

- finish documentation
- polish the UI and API behavior
- address mentor review feedback
- prepare final report and final code cleanup

---

## Risks and Mitigation

| Risk | Mitigation |
|---|---|
| model produces invalid or unsafe output | strict output validation plus curated static fallback |
| Journal signal behavior is noisy | explicitly test create/update and metadata-only update paths |
| strategy mapping becomes unmanageable | keep a small seeded mapping and use generic fallback |
| local model path is too heavy on some machines | keep mock mode and Sugar-AI-compatible path for development and testing |
| open-source-model tuning takes too much time | treat lightweight adaptation as conditional, not mandatory |

---

## Relevant Preparation

### Sugar Labs Contributions

- [PR #5446](https://github.com/sugarlabs/musicblocks/pull/5446) - merged XSS fix in the Reflection Widget
- [PR #5919](https://github.com/sugarlabs/musicblocks/pull/5919) - backend URL handling in `reflection.js`
- [PR #6174](https://github.com/sugarlabs/musicblocks/pull/6174) - prevent `projectAlgorithm` overwrite in the Reflection Widget
- [PR #6176](https://github.com/sugarlabs/musicblocks/pull/6176) - prevent dropped user queries in the Reflection Widget
- [PR #1077](https://github.com/sugarlabs/sugar/pull/1077) - fix Journal Select All behavior

These contributions are relevant because they are in the exact areas this project touches: Journal code and reflection-related AI UI.

### Skills and Experience

- Python, FastAPI, Pydantic, pytest, asyncio
- JavaScript and existing Sugar Labs frontend code
- prompt engineering and open-source model evaluation
- systems-level debugging in existing codebases

---

## Commitment and Communication

- I can dedicate 30-35 hours per week during the coding period.
- I have no planned conflicting internship or part-time work.
- I will keep work in public branches and share regular progress updates.
- I am comfortable narrowing scope early if evidence shows a smaller, stronger first version is better.

---

## Post-GSoC Plans

If selected, I intend to keep maintaining the Journal reflection work after GSoC, especially around:

- bug fixing and hardening,
- improving documentation,
- extending prompt coverage once the core integration is stable.

---

## References

1. Papert, S. (1980). *Mindstorms: Children, Computers, and Powerful Ideas.*
2. Hattie, J. and Timperley, H. (2007). *The Power of Feedback.*
3. Bransford, J., Brown, A., and Cocking, R. (2000). *How People Learn.*
4. Sugar Labs GSoC 2026 ideas page - *AI Reflection in the Sugar Journal*.
5. Music Blocks reflection backend documentation and related Sugar Labs AI infrastructure.
6. Current Sugar Journal source in `journalactivity.py`, `detailview.py`, `expandedentry.py`, and `model.py`.
