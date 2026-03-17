# GSoC 2026 Proposal — Sugar Labs

## AI Reflection in the Sugar Journal

---

## Basic Details

| Field | Info |
|---|---|
| **Full Name** | Mokshagna K |
| **Email** | mokshagnak004@gmail.com |
| **GitHub** | [moksha-hub](https://github.com/moksha-hub) |
| **Discord** | moksha__k |
| **First Language** | Telugu |
| **Location / Timezone** | India, IST (UTC+5:30) |
| **Availability** | 30–35 hours/week during the coding period |

---

## Open Source and Sugar Labs Contributions

### Sugar Labs

| Contribution | Why it matters for this project |
|---|---|
| [PR #5446](https://github.com/sugarlabs/musicblocks/pull/5446) ✅ Merged | XSS fix in the Reflection Widget — direct, line-by-line experience with the existing reflection feature and Walter Bender's expectations for it |
| [PR #5919](https://github.com/sugarlabs/musicblocks/pull/5919) | backend URL handling in `reflection.js` — directly relevant to AI service integration |
| [PR #6174](https://github.com/sugarlabs/musicblocks/pull/6174) | prevent `projectAlgorithm` overwrite in Reflection Widget |
| [PR #6176](https://github.com/sugarlabs/musicblocks/pull/6176) | prevent dropped queries in Reflection Widget |
| [PR #1077](https://github.com/sugarlabs/sugar/pull/1077) | fix Journal Select All — direct work inside `src/jarabe/journal` |

### Other Open Source

| Project | Contribution |
|---|---|
| [Learning Unlimited / ESP Website](https://github.com/learning-unlimited/ESP-Website/pulls?q=is%3Apr+author%3Amoksha-hub) | tests and backend fixes |
| [pgmpy](https://github.com/pgmpy/pgmpy/pulls?q=is%3Apr+author%3Amoksha-hub) | bug fixes and documentation corrections |

---

## What Am I Making?

I am proposing **Reflective Loop**, an adaptive AI reflection system integrated into the Sugar Journal.

Today, Sugar helps children create. The Journal records what they made. But the Journal has never helped a child think about *what* they made, *why* it matters, or *what to try next*. Reflection is the missing step.

This project adds a bounded, one-question reflection flow to the Journal. When a Journal entry is created or revisited, the system asks a single, age-appropriate question. The question adapts using context Sugar already has:

- the activity type,
- the current Sugar locale,
- whether the session was collaborative (from the `buddies` metadata),
- how many times this Sugar profile has reflected on this type of activity before — tracked as a simple local count, not by reading any previous private responses.

This is intentionally not a chatbot. One question, one at a time, grounded in what Sugar already knows.

The project directly matches the official Sugar Labs idea:

1. research approaches to reflective practice,
2. adapt an open-source LLM workflow for reflection prompting,
3. develop FastAPI endpoints,
4. deploy the reflection flow inside the Sugar Journal.

---

## How Will It Impact Sugar Labs?

### Pedagogical impact

Sugar is built around constructionist learning: children learn by making. Reflection is a natural next step — it helps children explain what they tried, what worked, what they learned, and what they might do next.

This project strengthens that part of Sugar without turning the Journal into a tutoring chatbot. The system does not generate content for the learner and does not evaluate them. It scaffolds reflection.

### Platform impact

Last summer, Diwangshu Kakoty implemented AI-assisted reflection inside Music Blocks. This proposal extends that direction into the Sugar Journal so reflection becomes part of the overall Sugar workflow, not just one activity.

### Practical impact

This project is realistic because it builds on things that already exist:

- Journal signals in `journalactivity.py`,
- existing reflection work in Music Blocks,
- Sugar-AI and FastAPI-based infrastructure,
- a working prototype with 51 passing tests.

---

## Related Work and Technical Context

### Music Blocks Reflection Widget

The existing Music Blocks widget already shows that:

- FastAPI is a reasonable boundary between Sugar UI code and AI logic,
- reflection prompts need strong structural constraints,
- the flow should feel native to the activity rather than bolted on.

Its backend uses `/projectcode`, `/chat`, `/analysis`, and `/updatecode`. This proposal does not duplicate that conversational widget. It adapts the general direction into a Journal-native, one-question reflection flow.

### Sugar-AI

Sugar-AI is the broader Sugar Labs AI backend and already supports prompted interactions. The project treats Sugar-AI as one of its optional inference targets — schools that have already deployed Sugar-AI get the integration for free.

To stay realistic within 350 hours, the open-source LLM plan is:

- start with prompt-engineered evaluation on open-source instruct models,
- measure reliability for the constrained one-question reflection task,
- use lightweight task adaptation only if prompt-only behavior is not good enough.

### Sugar Journal Grounding

The proposal is grounded in current Sugar source:

- `src/jarabe/journal/journalactivity.py` connects to `model.created` and `model.updated`,
- `src/jarabe/journal/detailview.py` manages the detail view where a reflection panel fits,
- `src/jarabe/journal/expandedentry.py` displays metadata and `buddies` collaborators,
- metadata-only writes use `update_mtime=False`, which matters for suppressing spurious reflection triggers.

---

## Core Design

### 1. Activity Strategy Mapping

Different activities invite different kinds of reflection. A plain calculator invites no particular reflection strategy at all; forcing Socratic questions onto it would be odd. So the v1 mapping is deliberately small and honest:

The [ASLO repository](https://github.com/sugarlabs/aslo) groups activities into categories. Rather than inferring strategy from the activity name alone, the v1 seed uses bundle categories as a guide:

| Strategy | Activity family | Rationale |
|---|---|---|
| **Socratic** | procedural creation (TurtleBlocks, Music Blocks, Pippy) | child made choices; Socratic questions surface *why* |
| **KWL (Know / Want / Learned)** | reading and writing (Write, Read) | knowledge-state reflection maps naturally to this |
| **What / So What / Now What** | expressive activities (Paint, Sketch) | experience-first reflection before analysis |
| **Generic fallback** | everything else | rotates through available strategies; no force-fit |

The mapping is a seed, not a claim. Activities that resist categorisation use the fallback. The prototype supports deployment-specific overrides so any school or maintainer can adjust the mapping without touching the engine.

### 2. Adaptive Depth Sequencing

The system asks deeper questions as a child reflects more — but adaptation is based on a **local count only**, not on reading previous private responses.

A child who has reflected three times on a TurtleBlocks session gets a slightly deeper question than someone reflecting for the first time. No private content is examined at any point.

| Depth | When it activates | Reflection style |
|---|---|---|
| 1 | early reflections | descriptive — what happened |
| 2 | after repeated reflections | analytical — why those choices |
| 3 | after continued reflections | connective — links to other ideas or the real world |
| 4 | after sustained history | transfer — what next, what would you explain to someone else |

The count is stored in a lightweight JSON file keyed by Sugar profile and activity type. It lives on the device and contains no private content.

### 3. Model Safety by Structure

Safety is structural, not a post-hoc filter.

1. **No child content in prompts.** The LLM only receives metadata: activity type, reflection count, locale. It never sees what the child wrote, drew, or coded.
2. **Constrained output.** A system prompt asks for exactly one short question. Open-ended conversation is structurally prevented.
3. **Output validation with static fallback.** If the model output does not match the expected format, the system returns a safe, curated static question. Model failure means a safe fallback, never an unsafe response.

### 4. Collaborative Reflection Awareness

When Journal metadata via `buddies` (read from `expandedentry.py`) shows that a session was shared, the reflection question can become collaboration-aware. Instead of only asking what the learner did, the system can also ask what changed because the work was shared. This leverages data Sugar already records — no new tracking is added.

### 5. Inference Backend

The service supports three inference paths:

| Path | Where inference runs | When to use |
|---|---|---|
| Local Ollama | on the device | default — no data leaves the machine |
| Sugar-AI | school server | for deployments that already have Sugar-AI |
| OpenAI-compatible | cloud | requires explicit configuration by whoever deploys the Sugar instance — this is a deployment decision made by a Sugar Labs maintainer or school administrator, not by the student |

---

## Architecture

```
Sugar Journal create / update flow
            │
            ▼
  Raw Journal metadata
  (activity_type, buddies, locale, profile id)
            │
            ▼
  POST /reflect-from-journal
            │
            ▼
  JournalMetadataAdapter
            │
            ▼
      ReflectRequest
            │
            ▼
     ReflectionEngine
     ├── DepthTracker       (local JSON, profile × activity)
     ├── StrategySelector   (seeded mapping + generic fallback)
     ├── PromptBuilder      (strategy × depth × locale + buddies injection)
     └── LLMClient          (Ollama / Sugar-AI / OpenAI-compat / Mock)
            │
            ▼
     ReflectResponse  (question + strategy + depth level)
            │
            ▼
  Journal detail view reflection panel
```

### Service endpoints

| Endpoint | Purpose |
|---|---|
| `POST /reflect` | generate a reflection from a structured request |
| `POST /reflect-from-journal` | accept raw Journal metadata and adapt internally |
| `GET /health` | service health + active backend |
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
| JSON | lightweight local depth store (no database) |
| Ollama + open-source instruct models | local-first inference experimentation |
| Sugar-AI | optional Sugar Labs backend |

---

## Prototype Evidence

The working prototype lives at: **[github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal](https://github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal)**

### Prototype files

| File | What it demonstrates |
|---|---|
| `reflection_service.py` | full FastAPI service — strategy selection, adaptive depth, backend abstraction, Journal metadata adaptation, validation, collaboration-aware prompting |
| `prompts.py` | curated static fallback library and peer-awareness prompts across locales |
| `config.py` | service configuration, backend selection, strategy overrides |
| `test_reflection_service.py` | automated evidence the service behaviour is stable |
| `README.md` | architecture and developer setup |

### What the prototype already demonstrates

- deterministic adaptive depth progression,
- collaboration-aware prompting from `buddies` metadata,
- FastAPI service boundary,
- Journal metadata adaptation layer (`/reflect-from-journal`),
- local profile depth history (not classroom abstraction),
- deployment-specific strategy overrides,
- metadata-only prompt construction,
- structural output validation with safe fallback.

At the time of submission: **51 tests passing.**

---

## Timeline

### Community Bonding

- read full Journal integration path: `journalactivity.py`, `detailview.py`, `expandedentry.py`, `model.py`
- review Diwangshu's Music Blocks reflection work
- research reflective-practice frameworks and finalise v1 strategy seed using ASLO categories
- define evaluation criteria for question quality and model compliance
- discuss integration scope and design with mentors

### Week 1

- finalise request and response schema
- finalise seeded activity-to-strategy mapping (ASLO-informed)
- finalise local depth model and profile key structure
- assemble reflection examples for quality evaluation

### Week 2

- expand and validate fallback prompt sets
- refine prompt builder and output validator
- improve backend abstraction
- add more unit tests for core behaviour

### Week 3

- harden FastAPI service endpoints
- improve raw Journal metadata adaptation layer
- verify collaboration-aware path
- document service contract for Sugar-side callers

### Week 4 (buffer)

- test repeated-session depth progression thoroughly
- test strategy overrides and malformed metadata cases
- tune prompts against open-source instruct models
- buffer for reliability fixes

### Week 5

- begin Sugar Journal integration in the detail flow
- connect Journal events to service calls
- ensure metadata-only updates (`update_mtime=False`) do not retrigger incorrectly
- prepare first visible Journal integration demo

---

### Evaluation 1 target

- hardened reflection service,
- seeded activity strategy model,
- adaptive depth persistence,
- collaboration-aware prompting,
- first visible Journal-side integration.

---

### Week 6

- continue Journal detail view integration
- add reflection panel GTK UI
- improve loading and refresh behaviour in the Journal
- fix integration issues from mentor review

### Week 7 (buffer)

- expand integration tests
- improve safety and failure handling in Journal-side flow
- verify compatibility with live Sugar metadata
- buffer for UI and signal-timing issues

### Week 8

- validate repeated save and revisit flows
- polish collaboration-aware reflection behaviour
- verify locale handling and multilingual fallbacks
- continue open-source model evaluation

### Week 9

- prompt quality improvement or lightweight task adaptation if needed
- measure reliability and latency under realistic conditions
- document deployment options and tradeoffs

### Week 10 (buffer)

- finalise v1 integration behaviour
- clean edge cases in service and Journal interaction
- buffer for mentor feedback and regressions

---

### Evaluation 2 target

- working Journal reflection loop,
- adaptive depth persistence,
- collaboration-aware reflection,
- safe bounded prompting and fallback,
- documentation and test evidence.

---

### Week 11

- complete documentation: developer guide, deployment notes
- improve configuration and setup instructions
- polish panel UI and API behaviour

### Week 12

- final cleanup and testing pass
- mentor feedback fixes
- final report and submission materials

### Unavailability

- No planned off-the-grid periods during the coding window.
- If an emergency occurs, I will notify mentors immediately and rebalance the following week.

---

## Deliverables

| Milestone | Deliverable | Evidence |
|---|---|---|
| Community Bonding | framework research notes, refined integration design | design summary shared with mentors |
| M1 | robust FastAPI reflection service — schema, depth tracking, strategy selection, validation | passing unit and integration tests |
| M2 | Journal metadata adaptation layer and collaboration-aware path | service demo and endpoint tests |
| M3 | Journal detail-view integration with visible one-question reflection flow | running Sugar demo or mentor walkthrough |
| M4 | adaptive depth persistence and safety behaviour in integrated flow | repeated-session and shared-session demo |
| M5 | final documentation, cleanup, and report | final docs and submission |

### Stretch goals

| Stretch | Why stretch-only |
|---|---|
| Broader multilingual prompt coverage | useful but secondary to core Journal integration |
| Learner-facing reflection history view | promising once the core loop is stable |
| Lighter-weight local model deployment | depends on time remaining after core lands |

---

## Hours Per Week

30–35 hours per week. This is my primary technical commitment for the summer — no internship or academic conflict during the coding period.

---

## Progress Reporting

- weekly written updates on the Sugar Labs mailing list
- regular mentor syncs for design and implementation review
- public commits and draft pull request open from day one
- milestone demos or short recordings when visible progress lands

---

## Risks and Mitigation

| Risk | Mitigation |
|---|---|
| model produces invalid or unsafe output | strict format validation with safe static fallback |
| Journal signal behaviour is noisy | explicitly test `model.created`, `model.updated`, and `update_mtime=False` paths |
| strategy mapping becomes unmanageable | small seeded mapping; anything unclassifiable uses generic fallback |
| local model too heavy on some machines | mock backend and Sugar-AI path always available for development |
| open-source model adaptation takes too long | treat adaptation as conditional — prompt-only is acceptable if reliable enough |

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
4. Sugar Labs GSoC 2026 ideas page — *AI Reflection in the Sugar Journal.*
5. Diwangshu Kakoty — GSoC 2025 Music Blocks reflection backend.
6. Current Sugar Journal source: `journalactivity.py`, `detailview.py`, `expandedentry.py`, `model.py`.
7. ASLO activity repository — [github.com/sugarlabs/aslo](https://github.com/sugarlabs/aslo).
