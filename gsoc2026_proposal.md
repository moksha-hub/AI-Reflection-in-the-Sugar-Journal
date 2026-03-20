# GSoC 2026 Proposal - Sugar Labs

## AI Reflection in the Sugar Journal

---

## Basic Details

| Field | Info |
|---|---|
| Full Name | Mokshagna K |
| Email | mokshagnak004@gmail.com |
| GitHub | [moksha-hub](https://github.com/moksha-hub) |
| Discord | `moksha__k` |
| First Language | Telugu |
| Location / Timezone | India, IST (UTC+5:30) |
| Organisation | Sugar Labs |
| Project Idea | AI Reflection in the Sugar Journal |
| Coding Mentors | Walter Bender, Ibiam Chihurumnaya |
| Assisting Mentors | Diwangshu Kakoty, Aman Naik |
| Project Size | 350 hours |
| Difficulty | Hard |
| Availability | 30-35 hours/week during the coding period |

---

## Open Source and Sugar Labs Contributions

### Sugar Labs

| Contribution | Why it matters for this project |
|---|---|
| [PR #5446](https://github.com/sugarlabs/musicblocks/pull/5446) | merged XSS fix in the Reflection Widget; direct line-by-line experience with the existing reflection feature |
| [PR #5919](https://github.com/sugarlabs/musicblocks/pull/5919) | backend URL handling in `reflection.js`; directly relevant to AI service integration |
| [PR #6174](https://github.com/sugarlabs/musicblocks/pull/6174) | prevent `projectAlgorithm` overwrite in Reflection Widget |
| [PR #6176](https://github.com/sugarlabs/musicblocks/pull/6176) | prevent dropped queries in Reflection Widget |
| [PR #1077](https://github.com/sugarlabs/sugar/pull/1077) | fix Journal Select All; direct work inside `src/jarabe/journal` |

### Other Open Source

| Project | Contribution |
|---|---|
| [Learning Unlimited / ESP Website](https://github.com/learning-unlimited/ESP-Website/pulls?q=is%3Apr+author%3Amoksha-hub) | tests and backend fixes |
| [pgmpy](https://github.com/pgmpy/pgmpy/pulls?q=is%3Apr+author%3Amoksha-hub) | bug fixes and documentation corrections |

These contributions matter because this project sits directly at the intersection of the Sugar Journal and reflection-related AI work.

I am a third-year Computer Science student at Amrita Vishwa Vidyapeetham, India. I have been contributing to open source since 2024 across testing, security, and backend work. I fixed the XSS vulnerability in the Sugar Reflection Widget because I was reading the code out of curiosity, not as part of any assignment. That is the level of engagement I bring to Sugar Labs work.

---

## What Am I Making?

I am proposing **Reflective Loop**, an adaptive AI reflection system integrated into the Sugar Journal.

Today, Sugar helps children create. The Journal records what they made. But the Journal does not help a child think about what they made, why it mattered, what they learned, or what to try next. Reflection is the missing step.

This project adds a bounded, one-question reflection flow to the Journal. When a Journal entry is created, saved, resumed, or revisited through the normal journaling flow, the system asks a single, age-appropriate question. That question adapts using context Sugar already has:

- the activity type,
- the current Sugar locale,
- whether the session was collaborative, from `buddies` metadata,
- how many times this Sugar profile has reflected on this type of activity before.

Adaptation in v1 is based on a simple local count only. It does not read or analyze previous private reflection responses.

This is intentionally not a chatbot. One question, one at a time, grounded in what Sugar already knows.

The project directly matches the official Sugar Labs idea:

1. research approaches to reflective practice,
2. adapt an open-source LLM workflow for reflection prompting,
3. develop FastAPI endpoints,
4. deploy the reflection flow inside the Sugar Journal.

---

## How Will It Impact Sugar Labs?

### Pedagogical impact

Sugar is built around constructionist learning: children learn by making. Reflection is the natural next step, because it helps children explain what they tried, what worked, what they learned, and what they might do next.

This project strengthens that part of Sugar without turning the Journal into a tutoring chatbot. The system does not generate content for the learner and does not evaluate them. It scaffolds reflection.

### Platform impact

Last summer, Diwangshu Kakoty implemented AI-assisted reflection inside Music Blocks. This proposal extends that direction into the Sugar Journal so reflection becomes part of the overall Sugar workflow, not just one activity.

### Practical impact

This project is realistic because it builds on things that already exist:

- Journal signals in `journalactivity.py`,
- existing reflection work in Music Blocks,
- Sugar-AI and FastAPI-based infrastructure,
- a working prototype with 52 passing tests.

---

## Related Work and Technical Context

### Music Blocks Reflection Widget

The existing Music Blocks widget already shows that:

- FastAPI is a reasonable boundary between Sugar UI code and AI logic,
- reflection prompts need strong structural constraints,
- the flow should feel native to the experience rather than bolted on.

Its backend uses `/projectcode`, `/chat`, `/analysis`, and `/updatecode`. This proposal does not duplicate that conversational widget. It adapts the same general direction into a Journal-native, one-question reflection flow.

### Sugar-AI

Sugar-AI is the broader Sugar Labs AI backend and already supports prompted interactions. The project treats Sugar-AI as one of its inference targets, especially for deployments that already use a local or LAN-based Sugar-AI setup.

To stay realistic within 350 hours, the open-source LLM plan is:

- start with prompt-engineered evaluation on open-source instruct models,
- measure reliability for the constrained one-question reflection task,
- use lightweight task adaptation only if prompt-only behavior is not good enough.

### Reflective Practice Research

The project idea explicitly asks for research into reflective practice, so I compared several candidate frameworks before narrowing the v1 design. The frameworks I looked at were Gibbs, Kolb, What / So What / Now What, KWL, and Socratic questioning. For Sugar Journal integration, the key constraint is that the model should produce one short reflection prompt at a time, not a multi-step questionnaire. Under that constraint, Socratic questioning, KWL, and What / So What / Now What are the strongest fit: they are lightweight, distinct from one another, and map naturally to procedural, knowledge-oriented, and expressive activities respectively.

### Sugar Journal Grounding

The proposal is grounded in current Sugar source:

- `src/jarabe/journal/journalactivity.py` connects to `model.created` and `model.updated`; `model.created` is the primary clean trigger, while `model.updated` requires filtering because metadata edits can also fire it,
- `src/jarabe/journal/detailview.py` manages the detail view where a reflection panel fits,
- `src/jarabe/journal/expandedentry.py` displays metadata and `buddies` collaborators,
- `src/jarabe/journal/model.py` exposes `activity` and `buddies` metadata through the datastore query interface,
- metadata-only writes use `update_mtime=False`, which matters for suppressing spurious reflection triggers.

---

## Core Design

### 1. Activity Strategy Mapping

Different activities invite different kinds of reflection. Some activities naturally support guided reasoning, some fit knowledge-state reflection, and some fit experience-first reflection. Just as importantly, some activities do not fit any strong framework and should not be forced into one.

For that reason, the v1 mapping is deliberately small and honest. It starts with a seed for core activity families and uses a generic fallback for everything else.

| Strategy | Activity family | Rationale |
|---|---|---|
| Socratic | procedural creation such as TurtleBlocks, Music Blocks, and Pippy | the learner made choices; guided questions surface why |
| KWL (Know / Want / Learned) | reading and writing activities such as Write and Read | knowledge-state reflection maps naturally here |
| What / So What / Now What | expressive activities such as Paint and Sketch | experience-first reflection works well before analysis |
| Generic fallback | everything else | no force-fit; rotates through available strategies when classification is weak |

ASLO categories and bundle metadata can help seed this mapping, but the project does not depend on an exhaustive taxonomy. The prototype already supports deployment-specific overrides so the mapping can be adjusted without changing the engine.

### 2. Adaptive Depth Sequencing

The system asks deeper questions as a child reflects more, but the adaptation remains simple and privacy-preserving. It is based on a local count only, not on reading previous private responses.

| Depth | When it activates | Reflection style |
|---|---|---|
| 1 | early reflections | descriptive: what happened |
| 2 | after repeated reflections | analytical: why those choices |
| 3 | after continued reflections | connective: links to other ideas or the real world |
| 4 | after sustained history | transfer: what next, what would you explain to someone else |

The count is stored in a lightweight JSON file keyed by Sugar profile and activity type. It lives on the device and contains no private content.

### 3. Model Safety by Structure

Safety is structural, not a post-hoc filter.

1. **No child content in prompts.** The model receives metadata only: activity type, reflection count, locale, and collaboration state. It never sees what the child wrote, drew, or coded.
2. **Constrained output.** The system prompt asks for exactly one short question. Open-ended conversation is structurally prevented.
3. **Output validation with static fallback.** If the model output does not match the expected format, the system returns a safe, curated static question. Model failure means a safe fallback, never an unsafe response.

### 4. Collaborative Reflection Awareness

Collaborative work should change the reflection, not be ignored. When Journal metadata via `buddies` shows that a session was shared, the reflection can become collaboration-aware. Instead of only asking what the learner did, it can also ask what changed because the work was shared. This leverages data Sugar already records; no new tracking is added.

### 5. Inference Backend

The first version focuses on feasible, clearly scoped deployment paths:

| Path | Where inference runs | When to use |
|---|---|---|
| Local Ollama | on the device | default path; no data leaves the machine |
| Sugar-AI | school or lab server | for deployments that already use Sugar-AI |
| Mock backend | local test path | for development, testing, and safe fallback during early integration |

Model selection will be evidence-driven. The prototype already supports a very small local model for smoke testing, but the main local evaluation during the project will compare small instruction-tuned Ollama models and select the smallest one that reliably follows the one-question prompt, behaves well across the target languages, and stays within acceptable latency and fallback rates. If a device cannot support that path reliably, Sugar-AI remains the supported non-cloud alternative.

The prototype also keeps a compatibility-oriented cloud backend, but that is not a core deliverable for the project.

---

## Architecture

```text
Sugar Journal create / update flow
            |
            v
  Raw Journal metadata
  (activity type, buddies, locale, profile id)
            |
            v
  POST /reflect-from-journal
            |
            v
  JournalMetadataAdapter
            |
            v
      ReflectRequest
            |
            v
     ReflectionEngine
     |- DepthTracker       (local JSON, profile x activity)
     |- StrategySelector   (seeded mapping + generic fallback)
     |- PromptBuilder      (strategy x depth x locale + buddies injection)
     `- LLMClient          (Ollama / Sugar-AI / Mock)
            |
            v
     ReflectResponse
     (question + strategy + depth level)
            |
            v
  Journal detail view reflection panel
```

### Service endpoints

| Endpoint | Purpose |
|---|---|
| `POST /reflect` | generate a reflection from a structured request |
| `POST /reflect-from-journal` | accept raw Journal metadata and adapt internally |
| `GET /health` | service health plus active backend |
| `GET /ready` | readiness check for the currently configured backend |
| `GET /strategies` | list active activity-to-strategy mapping |
| `GET /depth/{profile_id}` | return profile depth state across activities |

---

## Technologies

| Technology | Role |
|---|---|
| Python | core service logic and Sugar integration |
| FastAPI | local reflection service API |
| Pydantic | request and response schema validation |
| pytest / httpx | unit, integration, and endpoint testing |
| GTK / PyGObject | Journal-side reflection panel UI |
| JSON | lightweight local depth store |
| Ollama plus open-source instruct models | local-first inference experimentation |
| Sugar-AI | optional Sugar Labs backend target |

---

## Prototype Evidence

The working prototype lives at: [github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal](https://github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal)

### Prototype files

| File | What it demonstrates |
|---|---|
| `reflection_service.py` | full FastAPI service: strategy selection, adaptive depth, backend abstraction, Journal metadata adaptation, validation, collaboration-aware prompting |
| `prompts.py` | curated static fallback library and peer-awareness prompts across locales |
| `config.py` | service configuration, backend selection, strategy overrides |
| `evaluation/metrics.py` | lightweight scoring for bounded prompt quality, collaboration handling, and structural safety |
| `evaluation/evaluate_service.py` | a small evaluation harness for representative reflection requests across strategies and locales |
| `docs/frameworks.md` | reflective-practice research rationale behind the seeded v1 framework set |
| `docs/deployment.md` | realistic deployment notes for mock, local Ollama, and Sugar-AI paths |
| `docs/journal-integration.md` | intended Journal trigger and metadata flow for `jarabe` integration |
| `test_reflection_service.py` | automated evidence that the service behaviour is stable |
| `test_evaluation.py` | automated checks for evaluation metrics and the prototype evaluation harness |
| `README.md` | architecture and developer setup |

### What the prototype already demonstrates

- deterministic adaptive depth progression,
- collaboration-aware prompting from `buddies` metadata,
- FastAPI service boundary,
- Journal metadata adaptation via `/reflect-from-journal`,
- local profile depth history instead of a classroom abstraction,
- deployment-specific strategy overrides,
- metadata-only prompt construction,
- structural output validation with safe fallback,
- backend readiness checks for integration and deployment demos,
- a lightweight evaluation harness for bounded prompt behaviour.

### Current implementation status

| Area | Status |
|---|---|
| reflection engine | implemented and tested |
| adaptive depth tracking | implemented and tested |
| seeded strategy selection | implemented and tested |
| metadata-only prompt construction | implemented and tested |
| collaborative reflection from `buddies` metadata | implemented and tested |
| FastAPI endpoints | implemented and tested |
| lightweight evaluation harness | implemented and tested |
| deployment and integration notes | implemented |
| Sugar Journal metadata adapter | implemented and tested |
| Sugar Journal UI integration in `jarabe` | grounded in current source, planned for project implementation |
| Journal trigger wiring in `jarabe` | grounded in current source, planned for project implementation |

At the time of submission: **52 tests passing.**

This does not mean the full Sugar Journal integration is already done. It means the core reflection engine is already real, testable, and ready to be integrated.

---

## Timeline

### Community Bonding

- read the full Journal integration path in `src/jarabe/journal/journalactivity.py`, `src/jarabe/journal/detailview.py`, `src/jarabe/journal/expandedentry.py`, and related datastore code
- review Diwangshu's Music Blocks reflection work
- finalise the v1 strategy seed using prior framework research and bundle/category analysis
- define evaluation criteria for question quality and model compliance
- refine integration scope with mentors

### Week 1 - schema and strategy foundation

- finalise request and response schema
- finalise seeded activity-to-strategy mapping
- finalise local depth model and profile key structure
- assemble reflection examples for quality evaluation

### Week 2 - prompt and validation hardening

- expand and validate fallback prompt sets
- refine prompt builder and output validator
- improve backend abstraction
- add more unit tests for core behaviour

### Week 3 - service API and Journal adapter

- harden FastAPI service endpoints
- improve the raw Journal metadata adaptation layer
- verify collaboration-aware behaviour
- document the service contract for Sugar-side callers
- build a minimal Sugar-side integration spike that can render a mock reflection question in the Journal detail flow

### Week 4 - integration spike and model evaluation

- connect the Sugar-side spike to the service using the stable API contract
- test repeated-session depth progression thoroughly
- test malformed metadata and strategy override cases
- compare candidate local models on latency, prompt compliance, multilingual behaviour, and fallback rate
- tune prompts against open-source instruct models
- keep buffer for reliability fixes

### Week 5 - first Journal-side flow

- continue Sugar Journal integration in the detail flow
- connect Journal events to service calls
- ensure metadata-only updates using `update_mtime=False` do not retrigger incorrectly
- prepare the first visible Journal integration demo

---

### Evaluation 1 target

- hardened reflection service,
- seeded strategy model,
- adaptive depth persistence,
- collaboration-aware prompting,
- visible Journal-side integration path using either a mock or live local service call.

---

### Week 6 - panel UI and end-to-end stabilisation

- complete the reflection panel GTK UI
- improve loading and refresh behaviour in the Journal
- fix integration issues from mentor review
- stabilise the end-to-end flow from Journal event to rendered question

### Week 7 - integration hardening

- expand integration tests
- improve safety and failure handling in Journal-side flow
- verify compatibility with live Sugar metadata
- keep buffer for UI and signal-timing issues

### Week 8 - repeated-flow and locale validation

- validate repeated save and revisit flows
- polish collaboration-aware reflection behaviour
- verify locale handling and multilingual fallbacks
- continue open-source model evaluation

### Week 9 - model evaluation and deployment analysis

- improve prompt quality or do lightweight task adaptation if needed
- measure reliability and latency under realistic conditions
- document deployment options and tradeoffs

### Week 10 - v1 polish and regression buffer

- finalise v1 integration behaviour
- clean up edge cases in service and Journal interaction
- keep buffer for mentor feedback and regressions

---

### Evaluation 2 target

- working Journal reflection loop triggered from the save or revisit flow,
- adaptive depth persistence,
- collaboration-aware reflection,
- safe bounded prompting and fallback,
- documentation and test evidence.

---

### Week 11 - documentation and setup polish

- complete documentation: developer guide and deployment notes
- improve configuration and setup instructions
- polish panel UI and API behaviour

### Week 12 - final cleanup and submission

- final cleanup and testing pass
- mentor feedback fixes
- final report and submission materials

### Unavailability

- no planned off-the-grid periods during the coding window
- if an emergency occurs, I will notify mentors immediately and rebalance the following week

---

## Deliverables

| Milestone | Deliverable | Evidence |
|---|---|---|
| Community Bonding | framework research notes, refined integration design | design summary shared with mentors |
| M1 | robust FastAPI reflection service: schema, depth tracking, strategy selection, validation | passing unit and integration tests |
| M2 | Journal metadata adaptation layer plus collaboration-aware path and minimal Journal-side integration spike | service demo, endpoint tests, and Sugar-side walkthrough |
| M3 | Journal detail-view integration with visible one-question reflection flow | running Sugar demo or mentor walkthrough |
| M4 | adaptive depth persistence, collaboration-aware prompting, and locale-aware fallback behaviour in the integrated flow | repeated-session and shared-session demo |
| M5 | final documentation, cleanup, and report | final docs and submission |

### Stretch goals

| Stretch | Why stretch-only |
|---|---|
| broader multilingual prompt coverage | useful, but secondary to core Journal integration |
| learner-facing reflection history view | promising once the core loop is stable |
| lighter-weight local model deployment | depends on time remaining after the core loop lands |

---

## Hours Per Week

About 30 hours per week on average, with some weeks reaching 35 hours around integration or milestone work. This keeps the plan aligned with a 350-hour project while leaving realistic room for debugging and buffer time.

---

## Progress Reporting

- weekly written updates on the Sugar Labs mailing list
- regular mentor syncs for design and implementation review
- public commits and a draft pull request open from day one
- milestone demos or short recordings when visible progress lands

---

## Risks and Mitigation

| Risk | Mitigation |
|---|---|
| model produces invalid or unsafe output | strict format validation with safe static fallback |
| Journal signal behaviour is noisy | explicitly test `model.created`, `model.updated`, and `update_mtime=False` paths |
| strategy mapping becomes unmanageable | keep the mapping small and honest; anything unclassifiable uses generic fallback |
| local model too heavy on some machines | keep mock backend and Sugar-AI path available for development and testing |
| open-source model adaptation takes too long | treat adaptation as conditional; prompt-only is acceptable if reliable enough |

---

## Post-GSoC

If selected, I intend to continue contributing to Sugar Labs after the programme:

- hardening and bug fixing,
- extending prompt coverage and language support,
- continuing work in Journal and reflection-related code paths.

---

## References

1. Papert, S. (1980). *Mindstorms: Children, Computers, and Powerful Ideas.*
2. Hattie, J. and Timperley, H. (2007). *The Power of Feedback.*
3. Bransford, J., Brown, A., and Cocking, R. (2000). *How People Learn.*
4. Sugar Labs GSoC 2026 ideas page, *AI Reflection in the Sugar Journal*.
5. Diwangshu Kakoty's Music Blocks reflection work and related Sugar-AI infrastructure.
6. Current Sugar Journal source: `journalactivity.py`, `detailview.py`, `expandedentry.py`, `model.py`.
7. ASLO repository: [github.com/sugarlabs/aslo](https://github.com/sugarlabs/aslo).
