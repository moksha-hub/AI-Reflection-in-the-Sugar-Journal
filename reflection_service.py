# -*- coding: utf-8 -*-
"""
Reflective Loop — Adaptive AI Reflection Service for the Sugar Journal.

A standalone FastAPI service implementing:
  - DepthTracker:      session-based depth progression per student × activity
  - StrategySelector:  activity-type → reflection framework mapping
  - PromptBuilder:     strategy × depth × language → system + user prompts
  - LLMClient:         pluggable backends (Ollama, Sugar-AI, OpenAI, Mock)
  - Output Validator:  structural safety with static fallback

Author: Mokshagna K (moksha-hub)
License: GPL-3.0
"""

import json
import os
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx

from config import ReflectionConfig, LLMBackend
from prompts import PROMPTS, PEER_QUESTIONS, SYSTEM_PROMPT_TEMPLATE


# ═══════════════════════════════════════════════════════════════════════════
# Request / Response Models
# ═══════════════════════════════════════════════════════════════════════════

class ReflectRequest(BaseModel):
    """Input from the Sugar Journal when a child finishes/revisits an entry."""
    activity_type: str = Field(
        ..., description="Sugar bundle ID, e.g. 'org.laptop.TurtleArt'"
    )
    entry_title: str = Field(
        default="Untitled", description="Title of the Journal entry"
    )
    student_id: str = Field(
        default="default", description="Anonymised student identifier"
    )
    language: str = Field(
        default="en", description="ISO 639-1 language code"
    )
    shared_with: list[str] = Field(
        default_factory=list,
        description="Buddy list from Journal metadata (empty = solo session)",
    )


class ReflectResponse(BaseModel):
    """Output returned to the Sugar Journal UI."""
    question: str
    strategy: str
    depth_level: int
    session_count: int
    is_collaborative: bool
    peer_question: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════
# DepthTracker — persistent per-student, per-activity depth progression
# ═══════════════════════════════════════════════════════════════════════════

class DepthTracker:
    """
    Tracks how many times each student has reflected on each activity type.
    Stored in a lightweight JSON file — no external database needed.
    """

    def __init__(self, store_path: str = "depth_store.json"):
        self._path = Path(store_path)
        self._data: dict[str, dict[str, int]] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get_count(self, student_id: str, activity_type: str) -> int:
        return self._data.get(student_id, {}).get(activity_type, 0)

    def increment(self, student_id: str, activity_type: str) -> int:
        if student_id not in self._data:
            self._data[student_id] = {}
        current = self._data[student_id].get(activity_type, 0)
        self._data[student_id][activity_type] = current + 1
        self._save()
        return current + 1

    def get_depth_level(self, session_count: int) -> int:
        """
        Adaptive Depth Sequencing — our core innovation.

        Level 1 (0–2 sessions):  Descriptive  — "What happened?"
        Level 2 (3–6 sessions):  Analytical   — "Why did you make those choices?"
        Level 3 (7–14 sessions): Connective   — "How does this connect to the world?"
        Level 4 (15+ sessions):  Creative     — "What's the hardest version?"
        """
        if session_count <= 2:
            return 1
        if session_count <= 6:
            return 2
        if session_count <= 14:
            return 3
        return 4

    def get_student_summary(self, student_id: str) -> dict:
        return self._data.get(student_id, {})

    def reset_student(self, student_id: str, activity_type: str):
        if student_id in self._data and activity_type in self._data[student_id]:
            self._data[student_id][activity_type] = 0
            self._save()


# ═══════════════════════════════════════════════════════════════════════════
# StrategySelector — activity-type → pedagogical framework mapping
# ═══════════════════════════════════════════════════════════════════════════

class StrategySelector:
    """
    Maps Sugar activity types to the most pedagogically appropriate
    reflection framework. This is NOT random — each mapping is deliberate.
    """

    STRATEGY_MAP = {
        # Procedural activities → Socratic questioning
        # (child made deliberate choices; questions surface WHY)
        "org.laptop.TurtleArt": "socratic",
        "org.sugarlabs.MusicBlocksActivity": "socratic",
        "org.laptop.Pippy": "socratic",
        "org.laptop.Calculate": "socratic",
        "org.laptop.Measure": "socratic",

        # Narrative activities → KWL (Know / Want / Learned)
        # (child engaged with existing knowledge; KWL externalises change)
        "org.laptop.Write": "kwl",
        "org.laptop.Read": "kwl",
        "org.laptop.Jukebox": "kwl",

        # Aesthetic activities → What / So What / Now What
        # (aesthetic work invites experience-first reflection)
        "org.laptop.Paint": "what_so_what_now_what",
        "org.laptop.Sketch": "what_so_what_now_what",
        "org.laptop.Etoys": "what_so_what_now_what",
    }

    STRATEGIES = ["socratic", "kwl", "what_so_what_now_what"]

    def select(self, activity_type: str, session_count: int = 0) -> str:
        """
        Select strategy for the given activity.
        Unknown activities rotate through all three frameworks across sessions.
        """
        if activity_type in self.STRATEGY_MAP:
            return self.STRATEGY_MAP[activity_type]
        # Unknown / custom activities: cycle through all frameworks
        return self.STRATEGIES[session_count % len(self.STRATEGIES)]


# ═══════════════════════════════════════════════════════════════════════════
# PromptBuilder — constructs LLM prompts from strategy × depth × language
# ═══════════════════════════════════════════════════════════════════════════

class PromptBuilder:
    """
    Builds system + user prompts for the LLM.
    Also handles collaborative session detection and peer question injection.
    """

    def build_system_prompt(self, language: str = "en") -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(language=language)

    def build_user_prompt(
        self,
        request: ReflectRequest,
        strategy: str,
        depth_level: int,
    ) -> str:
        """Build user prompt with optional peer-awareness injection."""
        lang = request.language if request.language in PROMPTS else "en"

        # Get the static fallback question for this strategy × depth
        depth_question = PROMPTS[lang][strategy].get(depth_level, PROMPTS[lang][strategy][1])

        prompt = (
            f'The child just finished "{request.entry_title}" '
            f"using {request.activity_type} (session #{self._get_session_count(request)}).\n"
            f"Generate a reflection question similar in depth to: {depth_question}"
        )

        # Collaborative injection — if buddies present, add peer question
        if request.shared_with:
            peer_q = PEER_QUESTIONS.get(lang, PEER_QUESTIONS["en"]).get(
                strategy, PEER_QUESTIONS["en"][strategy]
            )
            prompt += (
                f"\nThis was a collaborative session with others. "
                f"Also consider asking: {peer_q}"
            )

        return prompt

    def get_fallback_question(
        self,
        strategy: str,
        depth_level: int,
        language: str = "en",
    ) -> str:
        """Return a safe, pre-written static question."""
        lang = language if language in PROMPTS else "en"
        return PROMPTS[lang][strategy].get(depth_level, PROMPTS[lang][strategy][1])

    def get_peer_question(self, strategy: str, language: str = "en") -> Optional[str]:
        """Return peer-awareness question for collaborative sessions."""
        lang = language if language in PEER_QUESTIONS else "en"
        return PEER_QUESTIONS[lang].get(strategy)

    def _get_session_count(self, request: ReflectRequest) -> int:
        """Placeholder — actual count comes from DepthTracker in the engine."""
        return 0


# ═══════════════════════════════════════════════════════════════════════════
# LLM Backends — pluggable inference providers
# ═══════════════════════════════════════════════════════════════════════════

class BaseLLMBackend:
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class MockBackend(BaseLLMBackend):
    """Returns the static fallback question — useful for testing."""
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Extract the fallback question from the user prompt
        if "similar in depth to:" in user_prompt:
            return user_prompt.split("similar in depth to:")[1].split("\n")[0].strip()
        return "What did you learn from this activity?"


class OllamaBackend(BaseLLMBackend):
    """Local LLM inference via Ollama — default, privacy-first."""

    def __init__(self, url: str = "http://localhost:11434", model: str = "tinyllama"):
        self.url = url.rstrip("/")
        self.model = model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"]


class SugarAIBackend(BaseLLMBackend):
    """School network Sugar-AI server."""

    def __init__(self, url: str = "http://localhost:5000"):
        self.url = url.rstrip("/")

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.url}/api/reflect",
                json={
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                },
            )
            response.raise_for_status()
            return response.json().get("question", "")


class OpenAIBackend(BaseLLMBackend):
    """Cloud LLM — explicit opt-in only."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


# ═══════════════════════════════════════════════════════════════════════════
# LLMClient — output validation + fallback logic
# ═══════════════════════════════════════════════════════════════════════════

class LLMClient:
    """
    Wraps a backend with output validation.
    If the LLM output is malformed or unsafe, silently return a static question.
    """

    def __init__(self, backend: BaseLLMBackend, blocked_keywords: list[str]):
        self.backend = backend
        self.blocked_keywords = blocked_keywords

    def validate_output(self, text: str) -> bool:
        """Structural safety check — not a content filter, a format guard."""
        text = text.strip()
        if not text:
            return False
        if not text.endswith("?"):
            return False
        if len(text) < 10 or len(text) > 300:
            return False
        if any(kw in text.lower() for kw in self.blocked_keywords):
            return False
        return True

    async def get_reflection(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_question: str,
    ) -> str:
        """Generate a reflection question with safety fallback."""
        try:
            raw = await self.backend.generate(system_prompt, user_prompt)
            if self.validate_output(raw):
                return raw.strip()
        except Exception:
            pass
        # Silent fallback — child sees a safe, curated question
        return fallback_question


# ═══════════════════════════════════════════════════════════════════════════
# ReflectionEngine — orchestrates all components
# ═══════════════════════════════════════════════════════════════════════════

class ReflectionEngine:
    """
    The main engine that ties together:
      DepthTracker → StrategySelector → PromptBuilder → LLMClient
    """

    def __init__(self, config: ReflectionConfig):
        self.config = config
        self.depth_tracker = DepthTracker(config.depth_store_path)
        self.strategy_selector = StrategySelector()
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient(
            backend=self._create_backend(config),
            blocked_keywords=config.blocked_keywords,
        )

    def _create_backend(self, config: ReflectionConfig) -> BaseLLMBackend:
        if config.llm_backend == LLMBackend.OLLAMA:
            return OllamaBackend(config.ollama_url, config.ollama_model)
        elif config.llm_backend == LLMBackend.SUGAR_AI:
            return SugarAIBackend(config.sugar_ai_url)
        elif config.llm_backend == LLMBackend.OPENAI:
            if not config.openai_api_key:
                raise ValueError("OpenAI backend requires an API key")
            return OpenAIBackend(config.openai_api_key, config.openai_model)
        else:
            return MockBackend()

    async def reflect(self, request: ReflectRequest) -> ReflectResponse:
        """Full reflection pipeline: context → strategy → depth → prompt → question."""

        # 1. Get session count and compute depth
        session_count = self.depth_tracker.get_count(
            request.student_id, request.activity_type
        )
        depth_level = self.depth_tracker.get_depth_level(session_count)

        # 2. Select pedagogical strategy based on activity type
        strategy = self.strategy_selector.select(
            request.activity_type, session_count
        )

        # 3. Build prompts
        system_prompt = self.prompt_builder.build_system_prompt(request.language)
        user_prompt = self.prompt_builder.build_user_prompt(
            request, strategy, depth_level
        )
        fallback = self.prompt_builder.get_fallback_question(
            strategy, depth_level, request.language
        )

        # 4. Generate question (with safety fallback)
        question = await self.llm_client.get_reflection(
            system_prompt, user_prompt, fallback
        )

        # 5. Increment session count for next time
        new_count = self.depth_tracker.increment(
            request.student_id, request.activity_type
        )

        # 6. Handle collaborative session
        is_collaborative = len(request.shared_with) > 0
        peer_question = None
        if is_collaborative:
            peer_question = self.prompt_builder.get_peer_question(
                strategy, request.language
            )

        return ReflectResponse(
            question=question,
            strategy=strategy,
            depth_level=depth_level,
            session_count=new_count,
            is_collaborative=is_collaborative,
            peer_question=peer_question,
        )


# ═══════════════════════════════════════════════════════════════════════════
# FastAPI Application
# ═══════════════════════════════════════════════════════════════════════════

config = ReflectionConfig()
engine: Optional[ReflectionEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = ReflectionEngine(config)
    yield
    engine = None


app = FastAPI(
    title="Reflective Loop",
    description="Adaptive AI Reflection Service for the Sugar Journal",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "backend": config.llm_backend.value}


@app.post("/reflect", response_model=ReflectResponse)
async def reflect(request: ReflectRequest):
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    return await engine.reflect(request)


@app.get("/strategies")
async def strategies():
    """List all known activity → strategy mappings."""
    return {
        "mappings": StrategySelector.STRATEGY_MAP,
        "available_strategies": StrategySelector.STRATEGIES,
    }


@app.get("/depth/{student_id}")
async def get_depth(student_id: str):
    """Get reflection depth summary for a student."""
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    summary = engine.depth_tracker.get_student_summary(student_id)
    result = {}
    for activity, count in summary.items():
        result[activity] = {
            "session_count": count,
            "depth_level": engine.depth_tracker.get_depth_level(count),
        }
    return {"student_id": student_id, "activities": result}


# ═══════════════════════════════════════════════════════════════════════════
# Standalone demo runner
# ═══════════════════════════════════════════════════════════════════════════

async def demo():
    """Run a quick demo showing all three strategies and depth progression."""
    print("=" * 60)
    print("Sugar Journal AI Reflection — Prototype Demo")
    print("=" * 60)

    demo_config = ReflectionConfig(llm_backend=LLMBackend.MOCK)
    demo_engine = ReflectionEngine(demo_config)

    test_entries = [
        ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="My First Spiral",
            student_id="student_001",
        ),
        ReflectRequest(
            activity_type="org.laptop.Write",
            entry_title="My Story About Space",
            student_id="student_001",
        ),
        ReflectRequest(
            activity_type="org.laptop.Paint",
            entry_title="Sunset Drawing",
            student_id="student_001",
        ),
        # Collaborative session
        ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Team Fractal Project",
            student_id="student_001",
            shared_with=["student_002"],
        ),
        # Spanish session
        ReflectRequest(
            activity_type="org.laptop.Paint",
            entry_title="Mi Dibujo del Sol",
            student_id="student_002",
            language="es",
        ),
    ]

    for entry in test_entries:
        result = await demo_engine.reflect(entry)
        print(f"\n--- Entry: {entry.activity_type} / {entry.entry_title} ---")
        print(f"  Strategy:      {result.strategy}")
        print(f"  Depth Level:   {result.depth_level}")
        print(f"  Session #:     {result.session_count}")
        print(f"  Question:      {result.question}")
        if result.is_collaborative:
            print(f"  Collaborative: Yes")
            print(f"  Peer Question: {result.peer_question}")

    # Show depth progression
    print("\n" + "=" * 60)
    print("Depth Progression Demo (15 TurtleBlocks sessions)")
    print("=" * 60)

    progression_engine = ReflectionEngine(
        ReflectionConfig(
            llm_backend=LLMBackend.MOCK,
            depth_store_path="depth_progression_demo.json",
        )
    )

    for i in range(15):
        result = await progression_engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.TurtleArt",
                entry_title=f"TurtleBlocks Session {i + 1}",
                student_id="depth_demo_student",
            )
        )
        level_bar = "●" * result.depth_level + "○" * (4 - result.depth_level)
        print(f"  Session {i + 1:2d} | {level_bar} | L{result.depth_level} | {result.question}")

    # Clean up demo files
    for f in ["depth_progression_demo.json"]:
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "=" * 60)
    print("DONE — All reflection strategies + depth progression tested.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
