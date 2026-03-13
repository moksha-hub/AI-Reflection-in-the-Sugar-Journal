# GSoC 2026 Proposal - Sugar Labs 

## [AI Reflection in the Sugar Journal]

## Basic Details

| Field | Info |
|---|---|
| **Full Name** | Mokshagna K |
| **Preferred Name** | Moksha |
| **Email** | mokshagnak004@gmail.com |
| **GitHub** | [github.com/moksha-hub](https://github.com/moksha-hub) |
| **Discord** | moksha__k |
| **University** | Amrita Vishwa Vidyapeetham |
| **Program / Year** | B.Tech Computer Science Engineering · 3rd Year |
| **Expected Graduation** | July 2027 |
| **Timezone** | IST (UTC+5:30) — Available 09:00–23:00 IST daily |
| **Resume** | [View Resume](https://drive.google.com/file/d/1uArnYjOXC7WWgvct9johFhrMim46L6dJ/view?usp=sharing) |

## Title

**Reflective Loop: An Adaptive AI Reflection System for the Sugar Journal**

---

## Synopsis

The Sugar Journal stores every project a child has ever made — but it has never helped them think about what they made, why it matters, or what to try next. Reflection is the missing pedagogical gear.

This proposal builds **Reflective Loop** — an AI-powered system that turns the Sugar Journal's passive record-keeping into an **active learning dialogue**. When a child finishes or revisits a Journal entry, a lightweight, privacy-first local AI asks them three to four progressively deeper questions, grounded in Constructionist theory (Papert, 1980). The questions adapt to the specific activity, the child's language, and — critically — how much they have reflected before. A student's first TurtleBlocks session receives beginner-friendly questions. After ten sessions, the same student is prompted to articulate mathematical patterns. Growth is visible, traceable, and owned by the learner.

Unlike a generic "add a chatbot" solution, Reflective Loop is built on three innovations:

1. **Adaptive Depth Sequencing** — reflection questions deepen automatically based on a child's journal history, never repeating the same prompt twice.
2. **Activity-Strategy Mapping** — the system selects the pedagogically appropriate reflection framework (Socratic, KWL, or What/So What/Now What) based on the activity type, not randomly.
3. **Privacy-first, offline-capable inference** — Ollama runs locally on the school device; no child data ever leaves the machine by default.

I have already built a working FastAPI prototype with all three reflection strategies, pluggable backends, and mock-LLM testing. I have two contributions to Sugar Labs (one merged by Walter Bender himself), giving me direct familiarity with the codebase and mentors.

---

## Benefits to the Community

### For Students
- Reflection is consistently shown to improve learning retention (Hattie & Timperley, 2007). Right now Sugar gives children the tools to create but no scaffold to think *about* creating. Reflective Loop closes this gap without requiring a teacher to be present.
- Students in under-resourced schools — the core Sugar demographic — often lack a mentor who can guide metacognition. The AI fills that role gently and consistently.

### For Teachers
- A teacher dashboard summarises the depth and frequency of student reflections across the class — not the content, which remains private — giving educators an early signal about which students are engaged and which need support.

### For Sugar Labs
- This project extends Diwangshu Kakoty's 2025 GSoC work (Reflection Widget for Music Blocks) into the broader Sugar ecosystem, creating a unified pedagogical reflection layer across *all* Sugar activities, not just Music Blocks.
- It demonstrates Sugar's relevance in the era of AI-assisted learning — showing the community that Sugar can integrate modern AI while remaining true to its privacy, offline, and equity commitments.

### For Open Source / Society
- Reflective Loop will be released under the GPL. Any educational platform can adapt the three-tier LLM backend and pedagogical strategy engine for their own learners.
- The system works in English, Spanish, Hindi, French, and Portuguese — directly serving the Global South communities Sugar was designed for.

---

## Related Work

### Diwangshu Kakoty — GSoC 2025: Reflection Widget for Music Blocks
Diwangshu built a reflection widget embedded inside Music Blocks, powered by the Sugar-AI backend. My work **extends, not duplicates** this. Where Diwangshu's widget is activity-specific (Music Blocks only) and triggered manually, Reflective Loop is:
- Integrated into the **Sugar Journal** → applies to every activity automatically
- **Adaptive** → adjusts question depth based on a child's history
- **Offline-first** → Ollama local inference as the default, not cloud Sugar-AI
- **Multi-strategy** → Socratic, KWL, WWWW chosen per-activity-type, not randomly

### Sugar-AI Backend (2025)
Krish Pandya and team built Sugar-AI as a hosted model server. Reflective Loop integrates with it as one of three backends, meaning schools that have Sugar-AI already need zero extra infrastructure. I treat Sugar-AI as an optional upgrade path, not a dependency.

### My Own Contributions to Sugar Labs
- **[PR #5446 — ✅ Merged](https://github.com/sugarlabs/musicblocks/pull/5446)**: `fix: prevent XSS in Reflection widget markdown rendering` — Identified and fixed a security vulnerability in `reflection.js`. Merged by Walter Bender. This gave me line-by-line familiarity with the Reflection Widget's architecture.
- **[PR #5919 — 🔄 In Review](https://github.com/sugarlabs/musicblocks/pull/5919)**: `fix: replace hardcoded IP with dynamic backend URL in reflection.js` — Replaced a hardcoded AWS IP with environment-aware URL resolution (matching `aidebugger.js`), fixing both a mixed-content HTTPS error and broken local dev.
- **[PR #6174 — 🔄 In Review](https://github.com/sugarlabs/musicblocks/pull/6174)**: `fix: prevent projectAlgorithm overwrite in Reflection Widget` — Fixed a bug where the Reflection Widget was overwriting algorithmic project data.
- **[PR #6176 — 🔄 In Review](https://github.com/sugarlabs/musicblocks/pull/6176)**: `fix: prevent dropped user queries in Reflection Widget` — Fixed a concurrency bug in `sendMessage` that caused user queries to be silently dropped.
- **[PR #1077 — 🔄 In Review](https://github.com/sugarlabs/sugar/pull/1077)**: `Journal: fix Select All button deselecting entries instead of selecting` — Fixed the "Select All" button in the **Sugar Journal** itself (`sugarlabs/sugar`), demonstrating familiarity with the Journal's GTK internals.
- **[PR #5772 — 🔄 In Review](https://github.com/sugarlabs/musicblocks/pull/5772)**: `test: expand RhythmBlocks test suite coverage` — 15+ new Jest test cases.
- **[PR #6068 — 🔄 In Review](https://github.com/sugarlabs/musicblocks/pull/6068)**: `chore: remove debug console statements from toolbar.js` — Production code cleanup.

---

## What Am I Making?

### The Core Idea: A Reflective Loop

Most AI integrations in education do one of two things: they generate content *for* the child, or they check if the child's answer is correct. Both are the wrong direction. **Reflective Loop does neither.** It asks questions that have no single correct answer — questions that ask the child to look inward.

```
  Child finishes activity
         │
         ▼
  Journal Entry saved
  ─────────────────────────────────────────────────────
  │  Reflective Loop Engine                           │
  │                                                   │
  │  Step 1: Extract context                          │
  │    activity_type → strategy selector              │
  │    reflection_count → depth selector              │
  │    language → i18n prompt loader                  │
  │                                                   │
  │  Step 2: Generate prompt                          │
  │    strategy × depth × language → system prompt   │
  │    entry metadata → user prompt                   │
  │                                                   │
  │  Step 3: Call LLM backend                         │
  │    Ollama (local) ← default                       │
  │    Sugar-AI (school network) ← optional           │
  │    OpenAI-compatible (cloud) ← explicit opt-in    │
  │                                                   │
  │  Step 4: Display in Journal DETAIL view           │
  │    GTK ReflectionPanel widget                     │
  │    Child types response (optional)                │
  │    Teacher sees summary (not content)             │
  └───────────────────────────────────────────────────
```

### Innovation 1: Adaptive Depth Sequencing

Every other proposal for AI + education picks a strategy and applies it uniformly. Reflective Loop tracks how many times a student has reflected on similar activities and automatically increases question complexity:

| Reflection Depth Level | Description | Example (TurtleBlocks) |
|---|---|---|
| **Level 1** (0–2 prior reflections) | Descriptive — What happened? | "What shapes did you draw?" |
| **Level 2** (3–6 prior) | Analytical — Why did you make those choices? | "Why did you repeat the spiral pattern?" |
| **Level 3** (7–14 prior) | Connective — How does this connect to the real world? | "Where do you see spiral patterns in nature?" |
| **Level 4** (15+ prior) | Creative — What would you do differently? What's the hardest version of this? | "Could you write a program that generates *any* curve from nature?" |

The depth is stored in a lightweight JSON file per student, per activity type. No cloud sync. No external database.

### Innovation 2: Activity-Strategy Mapping

The reflection framework is not chosen randomly. Different creative activities invite different modes of reflection:

| Activity Type | Default Strategy | Why |
|---|---|---|
| **TurtleBlocks, MusicBlocks** | Socratic | Procedural creation → discovery through guided questioning |
| **Write, Read** | KWL (Know/Want/Learn) | Narrative work → knowledge-state reflection maps naturally |
| **Paint, Sketch** | What / So What / Now What | Aesthetic creation → experience-first reflection works best |
| **Calculate, Measure** | Socratic | Quantitative → Socratic questions expose misconceptions |
| **Unknown / custom** | Rotating (cycle through all 3) | Exposure to all frameworks over time |

### Innovation 3: Privacy Architecture

| Backend | Where does inference run? | Data leaves device? | When to use |
|---|---|---|---|
| **Ollama + TinyLlama** | On the XO laptop / device | ❌ Never | Default for all students |
| **Sugar-AI** | School server (LAN) | Stays within school network | Schools with Sugar-AI already deployed |
| **OpenAI-compatible** | Cloud | ⚠️ Yes — requires parental consent UI | Only with explicit administrator opt-in |

The backend selection is a single admin setting. Students and teachers never see it — they just see "the AI asked me a question."

### Innovation 4: Structural Model Safety

Everyone else addresses AI safety with post-hoc content filters. Reflective Loop achieves safety structurally:

1. **No Child Content Sent:** The LLM only receives metadata (`activity_type`, `session_count`), never the child's actual work or personal input.
2. **Constrained Output:** The system prompt forces exactly one question ending in a question mark, preventing open-ended chat or content generation.
3. **Static Fallback:** If the LLM output fails basic format validation (e.g., unexpected length, flagged keywords), the system silently falls back to a curated, pre-written question from a static library. Failure means a safe static question, never unsafe content.

### Innovation 5: Collaborative Reflection Awareness

Sugar's Journal natively tracks when activities are shared over the network (`buddies` metadata). When a shared session is detected, the `PromptBuilder` automatically injects a peer-awareness dimension into the reflection:

- **Socratic (Shared):** "What surprised you about how your partner approached the problem?"
- **KWL (Shared):** "What did your collaborator teach you that you didn't already know?"
- **What/So What/Now What (Shared):** "How did working together change what you ended up making?"

This leverages existing Sugar features without introducing a separate "collaborative mode"—just a contextual injection based on Journal signals.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Sugar Desktop (Python / GTK3)                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  src/jarabe/journal/journalactivity.py               │  │
│  │  Hooks: model.created → trigger reflection           │  │
│  │         model.updated → filter metadata-only edits   │  │
│  │                         before triggering.           │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  src/jarabe/journal/detailview.py              │  │  │
│  │  │  ┌──────────────────────────────────────────┐  │  │  │
│  │  │  │  ReflectionPanel (NEW GTK widget)        │  │  │  │
│  │  │  │  • Reflection question text              │  │  │  │
│  │  │  │  • Optional: child's typed response      │  │  │  │
│  │  │  │  • Strategy badge (Socratic / KWL / WWWW)│  │  │  │
│  │  │  │  • Depth level indicator (●●○○)          │  │  │  │
│  │  │  │  • "Ask me another" button               │  │  │  │
│  │  │  └──────────────────┬───────────────────────┘  │  │  │
│  │  └─────────────────────│──────────────────────────┘  │  │
│  └────────────────────────│─────────────────────────────┘  │
│                           │ HTTP (localhost:8765)           │
│  ┌────────────────────────▼─────────────────────────────┐  │
│  │  src/jarabe/journal/reflectionservice.py (NEW)       │  │
│  │                                                      │  │
│  │  ReflectionEngine                                    │  │
│  │  ├─ DepthTracker    (reads/writes depth_store.json)  │  │
│  │  ├─ StrategySelector (activity_type → strategy)      │  │
│  │  ├─ PromptBuilder   (strategy × depth × lang)        │  │
│  │  └─ LLMClient       (abstraction over 3 backends)    │  │
│  │         ├─ OllamaBackend  (local, default)           │  │
│  │         ├─ SugarAIBackend (school network)           │  │
│  │         └─ OpenAIBackend  (cloud, opt-in only)       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Technologies

| Technology | Role |
|---|---|
| **Python 3.10+** | Sugar Journal integration, ReflectionEngine, FastAPI service |
| **FastAPI + Uvicorn** | Reflection microservice (local HTTP) |
| **GTK3 (PyGObject)** | ReflectionPanel widget — stays on GTK3, no GTK4 dependency |
| **Ollama** | Local LLM inference (TinyLlama for low-spec devices, Llama 3.2 for capable ones) |
| **Sugar-AI** | Optional: school server backend |
| **D-Bus** | Optional bridge between Journal and service |
| **JSON** | Lightweight local depth store (`~/.sugar/reflection_depth.json`) |
| **Pydantic** | Request/response validation in the FastAPI service |
| **pytest + httpx** | Full test suite for the reflection service |

---

## File-Level Implementation Plan

| File | Change | What It Does |
|---|---|---|
| `src/jarabe/journal/reflectionservice.py` | **NEW** | FastAPI service: engine, depth tracker, strategy selector, LLM client |
| `src/jarabe/journal/reflectionpanel.py` | **NEW** | GTK widget: displays question, response box, strategy badge, depth dots |
| `src/jarabe/journal/detailview.py` | **MODIFY** | Embed ReflectionPanel into the detail layout |
| `src/jarabe/journal/journalactivity.py` | **MODIFY** | Start reflection service on launch; connect `model.created` / filter `model.updated` signals |
| `data/org.sugarlabs.gschema.xml` | **MODIFY** | Add GSettings keys: `llm-backend`, `ollama-model`, `reflection-enabled` |
| `tests/test_reflectionservice.py` | **NEW** | Unit + integration tests for the full reflection pipeline |
| `tests/test_reflectionpanel.py` | **NEW** | GTK widget tests using `gi.repository` test harness |

## Deliverables

### Required

| Milestone | Deliverable |
|---|---|
| **M1** (Week 4) | Standalone `reflectionservice.py` — all strategies, all depths, pluggable backends, full test suite |
| **M2** (Week 6) | `ReflectionPanel` GTK widget integrated into Journal DETAIL view — working with Ollama |
| **M3** (Week 8) | Adaptive Depth Sequencing live — questions deepen across sessions, depth stored persistently |
| **M4** (Week 10) | Multilingual support — EN, ES, HI, FR, PT-BR system prompts, language auto-detected from Sugar locale |
| **M5** (Week 12) | Complete documentation, final test suite, GSoC report |

### Optional (stretch goals)

| Stretch | Deliverable |
|---|---|
| **S1** | Voice input — child speaks reflection instead of typing (uses Sugar's existing TTS infrastructure) |
| **S2** | Reflection history view — child sees their own past reflections in a timeline |
| **S3** | Teacher Dashboard — class summary view using existing or new roles logic (out of scope for M1-M5 as `jarabe` lacks classroom management primitives) |

---

## Timeline (12 Coding Weeks + Bonding)

> **Hofstadter buffers are built in**: each phase includes a half-week of buffer. Milestones are conservative, not optimistic.

### Community Bonding Period (before Week 1)
- Set up Sugar development environment (sugar-emu or VM)
- Read and annotate `src/jarabe/journal/` in full: `journalactivity.py`, `detailview.py`, `model.py`, `expandedentry.py`
- Study metadata update flows in `model.updated` and `expandedentry.py` (e.g., suppressing triggers on `update_mtime=False`)
- Discuss design doc with mentors Walter Bender and Ibiam Chihurumnaya
- Publish a public design document on the Sugar Labs wiki for community feedback

---

### Phase 1 — Backend Foundation (Weeks 1–4)
*Goal: A fully tested, standalone reflection service running locally*

**Week 1**
- Finalise the `ReflectionConfig` schema (config file location, admin UI hooks)
- Implement `DepthTracker`: reads/writes per-student, per-activity-type depth levels from `~/.sugar/reflection_depth.json`
- Implement `StrategySelector`: maps activity names to Socratic / KWL / WWWW strategies
- Unit tests for both components

**Week 2**
- Implement `PromptBuilder`: generates system + user prompts from {strategy × depth × language × entry metadata}
- Write all Level 1–4 prompts for Socratic strategy in English
- Test prompt quality with Ollama + TinyLlama running locally

**Week 3**
- Implement `LLMClient` with OllamaBackend (primary)
- Implement full FastAPI app: `/health`, `/reflect`, `/strategies`, `/depth/{student_id}`
- Integration tests using `httpx.AsyncClient` — test all three strategies, all four depth levels, mock + real Ollama

**Week 4 — Buffer + M1**
- Buffer: address test failures, refine prompts based on real LLM output quality
- **M1 Deliverable**: Standalone service, 100% test coverage, documented API
- Blog post: "How Reflective Loop's depth engine works"

---

### Phase 2 — Sugar Journal Integration (Weeks 5–7)
*Goal: Reflection visible in the Journal detail view*

> **⚠ Midterm evaluation occurs after Week 5**
> M1 (standalone service) ensures there is substantial, demonstrable work before the midterm.

**Week 5**
- Implement `ReflectionPanel` GTK widget skeleton: layout, question display, "Ask me another" button
- Hook into `src/jarabe/journal/journalactivity.py`: start the FastAPI service as a subprocess on Journal launch
- Connect `model.created` / filter `model.updated` signals → HTTP POST to `/reflect`
- Ensure metadata-only edits (which call `model.write(..., update_mtime=False)`) don't overfire the reflection trigger.

**Week 6 — M2**
- Wire `ReflectionPanel` into `src/jarabe/journal/detailview.py` — displays below the existing entry detail
- Depth level dots indicator (●●○○) in the panel
- Strategy badge (shows which framework is being used)
- **M2 Deliverable**: Full end-to-end flow — child opens Journal entry → AI question appears
- Screen recording of working integration (for GSoC midterm report)

**Week 7 — Buffer**
- Buffer for integration issues (GTK signal timing, subprocess lifecycle management)
- Mentor review session and UI feedback incorporation
- GTK widget tests using automated test harness

---

### Phase 3 — Adaptive Features + Multilingual (Weeks 8–10)

**Week 8 — M3**
- Adaptive depth sequencing live: depth increments correctly after each reflection session
- Depth state persists across Sugar restarts
- Manual override: teacher can reset a student's depth level
- **M3 Deliverable**: Demonstrated depth progression across 5 simulated sessions

**Week 9**
- Multilingual prompt library: write Level 1–4 prompts for all strategies in ES, HI, FR, PT-BR
- Auto-detect language from `os.environ['LANG']` / Sugar locale setting
- Test each language with a native-speaker word list to verify prompt grammar

**Week 10 — M4 + Buffer**
- **M4 Deliverable**: All 5 languages working, language-switching tested
- Buffer: address translation quality issues, prompt tuning per language

---

### Phase 4 — Documentation & Wrap-up (Weeks 11–12)

**Week 11**
- Security and performance audits. Ensure local Ollama inference scales gracefully on XO hardware limits.
- Complete all documentation: user guide, admin guide, deployment guide (Ollama setup via GSettings)

**Week 12 — M5 + Final**
- Complete all documentation: user guide, teacher guide, deployment guide (Ollama setup)
- Full test suite review: unit, integration, GTK widget tests — aim for 90%+ coverage
- Final GSoC report + Sugar Labs wiki page for the feature
- **M5 Deliverable**: Complete, production-ready Reflective Loop system

---

### Off-Grid / Unavailability
- I have **no planned off-grid periods** during the GSoC coding window.
- University exams end in April, before GSoC coding begins — there is no academic conflict.
- If any emergency arises, I will notify mentors at least 48 hours in advance and make up time the following week.

---

## Evaluation Checkpoints

| Evaluation | Target State |
|---|---|
| **Midterm (after Week 5)** | M1 + M2 complete: standalone service fully tested + Journal integration visible |
| **Final (after Week 12)** | M3 + M4 + M5 complete: adaptive depth, multilingual, teacher dashboard, full docs |

---

## Hours per Week

I will dedicate **30–35 hours per week** to this project during the coding period. This is my primary commitment for the summer — I have no internship or part-time work conflicting with it.

Typical week structure:
- Mon–Fri: 5–6 hours/day (coding + tests)
- Saturday: 3–4 hours (documentation + mentor sync)
- Sunday: reserved for buffer / overrun from the week

---

## Progress Reporting

- **Weekly**: Short written update on the Sugar Labs mailing list (no longer than 10 lines)
- **Biweekly**: Video call with mentors Walter Bender and Ibiam Chihurumnaya
- **Per milestone**: Blog post on my personal dev blog linked from Sugar Labs Planet
- **Continuous**: All work in a public fork with descriptive commit messages; PR opened as draft from Day 1 to enable mentor review at any point

---

## Why My Approach is Different from Every Other Proposal

Most students applying to AI-in-education projects will propose:
> "I will add a chatbot that asks the student a question when an activity ends."

That is a product, not a pedagogical system. Here is the specific dimension where Reflective Loop is architecturally different:

**No other proposal will have Adaptive Depth Sequencing.** The idea that an AI should know it already asked a child "what did you draw?" last week and should now ask "why do spirals appear in nature?" — and that this progression should be automatic, persistent, and privacy-preserving — requires understanding of both LLM prompt engineering AND Constructionist learning theory. Most applicants know one or neither.

**No other proposal will have Activity-Strategy Mapping.** Applying KWL to a painting and Socratic method to a code project is a pedagogical decision grounded in learning science. This is not a configuration option — it is a deliberate design choice informed by reading Hattie, Papert, and the original papers on each framework.

**I have already fixed a bug in the Reflection Widget** that this proposal extends. I am not proposing to work on a system I have never read. I have read `js/widgets/reflection.js` line by line, found a security flaw, fixed it, and had it accepted by Walter Bender. That is the closest thing to a guarantee of codebase familiarity a pre-coding-period applicant can offer.

---

## Working Prototype

**Live repository: [github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal](https://github.com/moksha-hub/AI-Reflection-in-the-Sugar-Journal)**

A standalone FastAPI prototype implements all core engine components. **33 pytest tests pass.** Key code extracts:

**Activity-Strategy Mapping** — selects the pedagogically appropriate framework per activity type:
```python
STRATEGY_MAP = {
    "org.laptop.TurtleArt":    "socratic",
    "org.sugarlabs.MusicBlocksActivity": "socratic",
    "org.laptop.Pippy":        "socratic",
    "org.laptop.Write":        "kwl",
    "org.laptop.Read":         "kwl",
    "org.laptop.Paint":        "what_so_what_now_what",
    "org.laptop.Sketch":       "what_so_what_now_what",
}

def select_strategy(activity_type: str, session_count: int) -> str:
    if activity_type in STRATEGY_MAP:
        return STRATEGY_MAP[activity_type]
    strategies = ["socratic", "kwl", "what_so_what_now_what"]
    return strategies[session_count % len(strategies)]  # rotate for unknown
```

**Adaptive Depth Sequencing** — questions deepen automatically based on reflection history:
```python
def get_depth_level(session_count: int) -> int:
    if session_count <= 2:  return 1  # Descriptive
    if session_count <= 6:  return 2  # Analytical
    if session_count <= 14: return 3  # Connective
    return 4                          # Creative
```

**Output Validation with Static Fallback** — structural model safety:
```python
def validate_output(text: str) -> bool:
    text = text.strip()
    return (
        text.endswith("?")
        and 10 < len(text) < 300
        and not any(w in text.lower() for w in BLOCKED_KEYWORDS)
    )

async def get_reflection(prompt, fallback_question: str) -> str:
    raw = await backend.generate(prompt)
    return raw if validate_output(raw) else fallback_question
```

**Collaborative Reflection Detection** — injects peer-awareness from Journal metadata:
```python
def build_prompt(request, depth_question: str) -> str:
    prompt = f'Activity: {request.activity_type}, Title: "{request.entry_title}"\n'
    prompt += f"Ask: {depth_question}"
    if request.shared_with:  # 'buddies' metadata from Sugar Journal
        peer_q = PEER_QUESTIONS[request.language][request.strategy]
        prompt += f"\nCollaborative session. Also ask: {peer_q}"
    return prompt
```

The summer's work extends this prototype into a fully integrated Sugar Journal feature with GTK widget, persistent depth tracking, and GSettings integration.

---

## Biographical Information

I am a third-year Computer Science student at Amrita Vishwa Vidyapeetham (India) with a focus on systems programming and applied AI. I have been actively contributing to open source since 2024, across testing, security, and backend domains. My Sugar Labs contributions are detailed in the Related Work section above.

### Other Open Source Contributions

| Contribution | Organisation | Status |
|---|---|---|
| [PR #4378 — Registration profile tests](https://github.com/learning-unlimited/ESP-Website/pull/4378) | Learning Unlimited | ✅ Merged |
| [PR #4370 — ClassChangeController tests](https://github.com/learning-unlimited/ESP-Website/pull/4370) | Learning Unlimited | ✅ Merged |
| [PR #4367 — statistics.py tests](https://github.com/learning-unlimited/ESP-Website/pull/4367) | Learning Unlimited | ✅ Merged |
| [PR #2718 — Fix docstring errors](https://github.com/pgmpy/pgmpy/pull/2718) | pgmpy | 🔄 In Review |
| [PR #2716 — Fix RNG in MarkovChain](https://github.com/pgmpy/pgmpy/pull/2716) | pgmpy | 🔄 In Review |

**Relevant Skills:**
- Python: FastAPI, Pydantic, pytest, asyncio, GTK (PyGObject)
- JavaScript: Jest, Node.js (Sugar MusicBlocks testing)
- AI/ML: Prompt engineering, Ollama, OpenAI API, LLM evaluation
- Systems: D-Bus, subprocess management, Linux signals

**Why Sugar Labs specifically:** I have now read enough of the Sugar codebase to know it is not just old code — it is carefully designed software with a coherent pedagogical philosophy. Fixing the XSS vulnerability in the Reflection Widget was the moment I understood that Sugar's AI work is genuinely novel, not a me-too AI integration. I want to spend the summer building the missing piece: the system that asks "what did you learn?" and actually listens.

---

## Post-GSoC Plans

I intend to continue contributing to Sugar Labs after GSoC ends. Specifically:
- Maintain Reflective Loop: triage issues, review PRs from other contributors who extend the system
- Extend multilingual support to additional languages requested by the community (Swahili, Quechua)
- Propose a GSoC 2027 project to add voice-based reflection (child speaks, not types) using the Sugar TTS infrastructure

Sugar Labs is not a summer project for me — it is a platform I believe in.

---

## References

1. Papert, S. (1980). *Mindstorms: Children, Computers, and Powerful Ideas.* Basic Books.
2. Hattie, J. & Timperley, H. (2007). The Power of Feedback. *Review of Educational Research*, 77(1), 81–112.
3. Hofstadter, D. R. (1979). *Gödel, Escher, Bach: An Eternal Golden Braid.* Basic Books. (re: project timeline planning)
4. Kakoty, D. (2025). *GSoC 2025 Report: Reflection Widget for Music Blocks.* Sugar Labs.
5. Sugar Labs. (2026). *AI Reflection in the Sugar Journal — Project Idea.* GSoC 2026 Ideas Page.
6. Bransford, J., Brown, A., & Cocking, R. (2000). *How People Learn.* National Academy Press.

---

*This proposal was written by Mokshagna K. The working prototype, PR contributions, and architectural design are original work.*
