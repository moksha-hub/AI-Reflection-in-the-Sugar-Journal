# GSoC 2026 Proposal - Sugar Labs

## AI Reflection in the Sugar Journal

## Basic Details

| Field | Info |
|---|---|
| Full Name | Mokshagna K |
| Email | mokshagnak004@gmail.com |
| GitHub Username | [moksha-hub](https://github.com/moksha-hub) |
| First Language | Telugu |
| Location and Timezone | India, IST (UTC+5:30) |
| Availability | 30-35 hours/week during the coding period |

### Previous Open Source Work

| Project | Contribution |
|---|---|
| [Learning Unlimited / ESP Website](https://github.com/learning-unlimited/ESP-Website/pulls?q=is%3Apr+author%3Amoksha-hub) | tests and backend fixes |
| [pgmpy](https://github.com/pgmpy/pgmpy/pulls?q=is%3Apr+author%3Amoksha-hub) | bug fixes and documentation corrections |

### Sugar Labs Contributions

| Contribution | Why it matters here |
|---|---|
| [PR #5446](https://github.com/sugarlabs/musicblocks/pull/5446) | merged XSS fix in the Reflection Widget; direct experience with the existing reflection feature |
| [PR #5919](https://github.com/sugarlabs/musicblocks/pull/5919) | backend URL handling in `reflection.js`; relevant to AI service integration |
| [PR #6174](https://github.com/sugarlabs/musicblocks/pull/6174) | prevent `projectAlgorithm` overwrite in the Reflection Widget |
| [PR #6176](https://github.com/sugarlabs/musicblocks/pull/6176) | prevent dropped user queries in the Reflection Widget |
| [PR #1077](https://github.com/sugarlabs/sugar/pull/1077) | fix Journal Select All behavior; direct work in Sugar Journal code |

These contributions are relevant because this project sits exactly at the intersection of the Sugar Journal and existing reflection-related AI work.

---

## What Am I Making?

I am proposing **Reflective Loop**, an adaptive AI reflection system integrated into the Sugar Journal.

Today, Sugar helps children create, but the Journal still treats reflection mostly as an empty form after the work is done. This project adds a bounded reflection layer so that journaling becomes part of the learning process, not just the storage process.

The system is intentionally not a generic chatbot. It asks one short, age-appropriate question at a time when a Journal entry is created or updated as part of the save or pause journaling flow. The question adapts using local context that Sugar already has:

- the activity type,
- the current locale,
- whether the work was collaborative,
- how often this Sugar profile has reflected on similar work before.

The project directly matches the official Sugar Labs idea:

1. research approaches to reflective practice,
2. adapt an open-source LLM workflow for reflection prompting,
3. develop FastAPI endpoints,
4. deploy the reflection flow inside the Sugar Journal.

---

## How Will It Impact Sugar Labs?

### Pedagogical impact

Sugar is built around constructionist learning: children learn by making. Reflection is a natural next step after making, because it helps children explain what they tried, what worked, what they learned, and what they might do next.

This project strengthens that part of Sugar without turning it into a tutoring chatbot. The system does not generate projects for the learner and does not grade them. It scaffolds reflection.

### Platform impact

Last summer, Diwangshu Kakoty implemented AI-assisted reflection inside Music Blocks. This proposal extends that direction into the Sugar Journal so reflection can become part of the overall Sugar workflow rather than remaining specific to one activity.

### Practical impact

This project is realistic because it builds on:

- existing Journal signals in Sugar,
- existing reflection-related work in Music Blocks,
- existing Sugar-AI and FastAPI-based infrastructure,
- an already working prototype with passing tests.

---

## Related Work and Technical Context

### Music Blocks Reflection Widget

The existing Music Blocks reflection widget already shows that:

- FastAPI is a reasonable boundary between UI and AI logic,
- reflection prompts benefit from strong structure,
- the reflection flow should feel native to the experience rather than bolted on.

Its current backend uses endpoints such as `/projectcode`, `/chat`, `/analysis`, and `/updatecode`. My project does not duplicate that conversational widget. Instead, it adapts the general direction into a Journal-native, one-question reflection flow.

### Sugar-AI

Sugar-AI is now the broader Sugar Labs AI backend and already supports prompted interactions. That makes it a practical integration target.

The project idea also asks for open-source LLM work. To stay realistic within 350 hours, I am not claiming full model pretraining from scratch. My plan is:

- start with prompt-engineered evaluation on open-source instruct models,
- measure reliability for the constrained reflection task,
- use lightweight task adaptation only if prompt-only behavior is not good enough.

### Sugar Journal Grounding

The proposal is grounded in current Sugar code:

- `journalactivity.py` already connects to `model.created` and `model.updated`,
- `detailview.py` already manages the detail view where a reflection panel can be shown,
- `expandedentry.py` already displays metadata and collaborators,
- `model.py` already exposes `buddies` metadata,
- metadata-only writes already use `update_mtime=False`, which matters for controlling reflection triggers.

---

## Core Design

### 1. Adapting Across the Variety of Sugar Activities

Walter Bender asked how the system should adapt to the variety of Sugar activities. My answer is: the v1 design should be seeded, not exhaustive.

Different activities invite different kinds of reflection, but it would be unrealistic to claim a complete taxonomy for the entire Sugar ecosystem in one summer. So the system starts with a small, defensible mapping for core activity families:

- Socratic for procedural creation such as TurtleBlocks and Music Blocks
- KWL for reading and writing activities such as Write and Read
- What / So What / Now What for expressive activities such as Paint and Sketch
- generic fallback for unknown activities

For unknown or custom activities, the system rotates through the available frameworks rather than pretending it can perfectly classify them. The prototype already supports deployment-specific overrides, so the mapping can be extended safely over time.

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

## Architecture Design

```text
Sugar Journal create/update flow
            |
            v
  Raw Journal metadata
            |
            v
  /reflect-from-journal
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
            |
            v
  Journal detail view panel
```

### Service surface

The reflection service exposes:

- `POST /reflect`
- `POST /reflect-from-journal`
- `GET /health`
- `GET /strategies`
- `GET /depth/{profile_id}`

The additional `/reflect-from-journal` endpoint exists specifically to make Sugar integration cleaner: it accepts raw Journal metadata and adapts it into the stable reflection request used by the engine.

### Model workflow

The model pipeline is constrained rather than open-ended:

1. choose a reflection strategy,
2. compute depth from local history,
3. build a short and tightly-scoped prompt,
4. generate one question,
5. validate the output,
6. fall back to a curated static prompt if validation fails.

This structure matters because it makes the AI portion testable and makes failure safe.

---

## Technologies

| Technology | Role |
|---|---|
| Python | core service logic and Sugar integration |
| FastAPI | local reflection service API |
| Pydantic | validated request and response models |
| pytest | unit, integration, and endpoint testing |
| httpx | backend communication and endpoint tests |
| GTK / PyGObject | Journal-side reflection UI integration |
| JSON | lightweight local depth store |
| Ollama / open-source instruct models | local-first model experimentation |
| Sugar-AI | optional Sugar Labs backend target |

---

## Prototype Evidence and Proof

I do not want the proposal to rely only on future promises. I already have a working prototype in this repository.

### Current Prototype Files

| File | What it proves |
|---|---|
| `reflection_service.py` | end-to-end FastAPI reflection service with strategy selection, adaptive depth, backend abstraction, Journal metadata adaptation, validation, and collaboration-aware handling |
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

### Current Verification

At the time of this proposal revision, the prototype test suite passes:

- **51 tests passing**

That does not mean the full Sugar Journal integration is already done, but it does mean the core reflection engine is no longer hypothetical.

---

## Timeline

### Community Bonding Period

- read the full Journal integration path in `jarabe/journal`
- review Diwangshu's reflection work in Music Blocks
- research reflective-practice frameworks and narrow the v1 strategy set
- define evaluation criteria for question quality and model compliance
- discuss the design with mentors and refine integration scope

### Week 1

- finalize request and response schema
- finalize seeded activity-to-strategy mapping
- finalize local depth model
- assemble reflection examples for evaluation

### Week 2

- expand fallback prompt sets
- refine prompt builder and output validator
- improve backend abstraction for local and Sugar-AI-compatible paths
- add more unit tests for core service behavior

### Week 3

- harden FastAPI service endpoints
- improve raw Journal metadata adaptation
- verify collaboration-aware handling
- document service contract for Sugar-side use

### Week 4

- test repeated-session depth progression thoroughly
- test strategy overrides and malformed metadata cases
- tune prompts against open-source instruct models
- keep a buffer for service reliability fixes

### Week 5

- begin Sugar Journal integration in the detail flow
- connect Journal events to service calls
- ensure metadata-only updates do not retrigger incorrectly
- prepare first visible Journal integration demo

### Evaluation 1 Target

Before the first evaluation, I plan to complete:

- the hardened reflection service,
- the seeded activity strategy model,
- adaptive depth persistence,
- collaboration-aware prompting,
- first visible Journal-side integration work.

### Week 6

- continue Journal detail view integration
- add reflection panel UI
- improve loading and refresh behavior in the Journal
- fix integration issues found during mentor review

### Week 7

- expand integration tests
- improve safety and failure handling in Journal-side flow
- verify compatibility with Sugar metadata patterns
- keep a buffer for UI and signal-timing issues

### Week 8

- validate repeated save and revisit flows
- polish collaboration-aware reflection behavior
- verify locale handling and multilingual fallbacks
- continue open-source model evaluation

### Week 9

- improve prompt quality or lightweight task adaptation if needed
- measure reliability and latency in realistic development conditions
- document deployment options and tradeoffs

### Week 10

- finalize robust v1 integration behavior
- clean up edge cases in service and Journal interaction
- keep a buffer for mentor feedback and regression fixes

### Evaluation 2 Target

Before the second evaluation, I plan to complete:

- a working Journal reflection loop,
- adaptive depth persistence,
- collaboration-aware reflection,
- safe bounded prompting and fallback behavior,
- documentation and tested prototype evidence.

### Week 11

- complete documentation
- improve developer setup and configuration notes
- polish UI and API behavior

### Week 12

- final cleanup
- final testing pass
- mentor feedback fixes
- final report and submission materials

### Off-the-grid periods

- I have no planned off-the-grid periods during the coding window.
- If any emergency occurs, I will notify mentors as early as possible and rebalance the following week's goals.

---

## Deliverables

| Milestone | Deliverable | Evidence |
|---|---|---|
| Community Bonding | reflection-framework notes, Journal integration notes, refined design | shared design summary |
| M1 | robust FastAPI reflection service with tested schema, depth tracking, strategy selection, and validation | passing unit and integration tests |
| M2 | raw Journal metadata adaptation and collaboration-aware reflection path | service demo and endpoint tests |
| M3 | Journal detail-view integration with visible reflection question flow | running Sugar demo or mentor walkthrough |
| M4 | adaptive depth persistence and refined safety behavior in integrated flow | repeated-session and shared-session demo |
| M5 | final documentation, cleanup, and final report | final docs and final submission |

### Stretch goals

| Stretch Goal | Why it is stretch-only |
|---|---|
| broader multilingual prompt coverage | useful, but secondary to core Journal integration |
| learner-facing reflection history view | promising once the core loop is stable |
| lower-spec deployment tuning for local model use | depends on time remaining after core functionality lands |

---

## Hours Per Week

I can dedicate **30-35 hours per week** to this project during the coding period. This will be my primary technical commitment during the summer.

---

## How Will I Report Progress?

- weekly written updates on the Sugar Labs mailing list or agreed community channel
- regular mentor syncs for design and implementation review
- public commits and pull requests in my fork
- milestone demos or short recordings when major pieces become visible

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

## Post-GSoC Plans

If selected, I intend to continue contributing to Sugar Labs after GSoC, especially around:

- bug fixing and hardening,
- improving documentation,
- extending prompt coverage once the core integration is stable,
- continuing work in the Journal and reflection-related code paths.

---

## References

1. Papert, S. (1980). *Mindstorms: Children, Computers, and Powerful Ideas.*
2. Hattie, J. and Timperley, H. (2007). *The Power of Feedback.*
3. Bransford, J., Brown, A., and Cocking, R. (2000). *How People Learn.*
4. Sugar Labs GSoC 2026 ideas page - *AI Reflection in the Sugar Journal*.
5. Music Blocks reflection backend documentation and related Sugar Labs AI infrastructure.
6. Current Sugar Journal source in `journalactivity.py`, `detailview.py`, `expandedentry.py`, and `model.py`.
