# -*- coding: utf-8 -*-
"""
Reflective Loop - Adaptive AI Reflection Service for the Sugar Journal.

A standalone FastAPI service implementing:
  - DepthTracker: persistent depth progression per local Sugar profile x activity
  - StrategySelector: bundle-id -> reflection framework mapping with overrides
  - PromptBuilder: strategy x depth x language -> safe reflection prompts
  - LLMClient: pluggable backends (Ollama, Sugar-AI, OpenAI, Mock)
  - Journal adapter: converts raw Sugar Journal metadata into reflection requests
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from config import LLMBackend, ReflectionConfig
from prompts import PEER_QUESTIONS, PROMPTS, SYSTEM_PROMPT_TEMPLATE


LOGGER = logging.getLogger(__name__)


class ReflectRequest(BaseModel):
    """Input from the Sugar Journal when a child finishes or revisits an entry."""

    activity_type: str = Field(
        ..., description="Sugar bundle ID, e.g. 'org.laptop.TurtleArt'"
    )
    entry_title: str = Field(
        default="Untitled",
        description="Journal title for local UI display; not sent to the model",
    )
    profile_id: str = Field(
        default="default",
        description="Stable local Sugar profile identifier for on-device history",
    )
    language: str = Field(default="en", description="ISO 639-1 language code")
    shared_with: list[str] = Field(
        default_factory=list,
        description="Buddy identifiers derived from Journal metadata",
    )


class JournalMetadataRequest(BaseModel):
    """
    Raw datastore-style metadata from Sugar Journal.
    This matches the integration surface we would have inside jarabe.
    """

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw Sugar Journal metadata dictionary",
    )
    profile_id: str = Field(
        default="default",
        description="Stable local Sugar profile identifier for on-device history",
    )
    language: Optional[str] = Field(
        default=None,
        description="Optional locale override; falls back to metadata or LANG",
    )


class ReflectResponse(BaseModel):
    """Output returned to the Sugar Journal UI."""

    question: str
    strategy: str
    depth_level: int
    session_count: int
    is_collaborative: bool
    peer_question: Optional[str] = None


def normalize_language(language: Optional[str], default: str = "en") -> str:
    """
    Collapse locale strings such as en_US.UTF-8 to their ISO 639-1 prefix.
    """
    if not language:
        return default

    normalized = language.strip()
    if not normalized:
        return default

    normalized = normalized.split(".", 1)[0]
    normalized = normalized.split("@", 1)[0]
    normalized = normalized.replace("-", "_")
    primary = normalized.split("_", 1)[0].lower()
    return primary or default


def parse_buddies_metadata(raw_buddies: Any) -> list[str]:
    """
    Sugar stores buddies as JSON metadata that usually decodes to a dict whose
    values are [nick, color] pairs. We keep only the buddy nick locally.
    """
    if not raw_buddies:
        return []

    if isinstance(raw_buddies, list):
        parsed = raw_buddies
    elif isinstance(raw_buddies, dict):
        parsed = list(raw_buddies.values())
    elif isinstance(raw_buddies, str):
        try:
            decoded = json.loads(raw_buddies)
        except json.JSONDecodeError:
            LOGGER.warning("Could not decode buddies metadata: %r", raw_buddies)
            return []
        parsed = list(decoded.values()) if isinstance(decoded, dict) else decoded
    else:
        return []

    if not isinstance(parsed, list):
        return []

    buddies = []
    for buddy in parsed:
        if isinstance(buddy, (list, tuple)) and buddy:
            buddies.append(str(buddy[0]))
        elif isinstance(buddy, str):
            buddies.append(buddy)
    return buddies


class JournalMetadataAdapter:
    """
    Converts raw Sugar Journal metadata into the service's stable request schema.
    """

    def __init__(self, default_language: str = "en"):
        self.default_language = default_language

    def to_reflect_request(self, request: JournalMetadataRequest) -> ReflectRequest:
        metadata = request.metadata or {}
        activity_type = (
            metadata.get("bundle_id")
            or metadata.get("activity")
            or "unknown"
        )
        entry_title = metadata.get("title") or "Untitled"
        language = normalize_language(
            request.language
            or metadata.get("language")
            or os.environ.get("LANG"),
            default=self.default_language,
        )
        shared_with = parse_buddies_metadata(metadata.get("buddies"))

        return ReflectRequest(
            activity_type=str(activity_type),
            entry_title=str(entry_title),
            profile_id=request.profile_id,
            language=language,
            shared_with=shared_with,
        )


class DepthTracker:
    """
    Tracks how many times each local Sugar profile has reflected on each activity.
    Stored in a lightweight JSON file - no external database required.
    """

    def __init__(self, store_path: str = "depth_store.json"):
        self._path = Path(store_path)
        self._data: dict[str, dict[str, int]] = {}
        self._load()

    def _load(self):
        if not self._path.exists():
            self._data = {}
            return

        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.warning("Depth store unreadable at %s: %s", self._path, exc)
            self._data = {}
            return

        self._data = loaded if isinstance(loaded, dict) else {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2, sort_keys=True)

    def get_count(self, profile_id: str, activity_type: str) -> int:
        return self._data.get(profile_id, {}).get(activity_type, 0)

    def increment(self, profile_id: str, activity_type: str) -> int:
        self._data.setdefault(profile_id, {})
        current = self._data[profile_id].get(activity_type, 0)
        self._data[profile_id][activity_type] = current + 1
        self._save()
        return current + 1

    def get_depth_level(self, session_count: int) -> int:
        """
        Adaptive depth sequencing.

        Level 1 (0-2 sessions): descriptive
        Level 2 (3-6 sessions): analytical
        Level 3 (7-14 sessions): connective
        Level 4 (15+ sessions): creative
        """
        if session_count <= 2:
            return 1
        if session_count <= 6:
            return 2
        if session_count <= 14:
            return 3
        return 4

    def get_profile_summary(self, profile_id: str) -> dict[str, int]:
        return self._data.get(profile_id, {})

    def reset_profile(self, profile_id: str, activity_type: str):
        if profile_id in self._data and activity_type in self._data[profile_id]:
            self._data[profile_id][activity_type] = 0
            self._save()


class StrategySelector:
    """
    Maps a seeded set of Sugar activity bundle IDs to reflection frameworks.
    Unknown activities fall back cleanly rather than pretending the whole
    ecosystem can be classified up front.
    """

    DEFAULT_STRATEGY_MAP = {
        "org.laptop.TurtleArt": "socratic",
        "org.sugarlabs.MusicBlocksActivity": "socratic",
        "org.laptop.Write": "kwl",
        "org.laptop.Read": "kwl",
        "org.laptop.Paint": "what_so_what_now_what",
        "org.laptop.Sketch": "what_so_what_now_what",
    }

    STRATEGIES = ["socratic", "kwl", "what_so_what_now_what"]

    def __init__(self, overrides: Optional[dict[str, str]] = None):
        self.strategy_map = dict(self.DEFAULT_STRATEGY_MAP)
        for activity_type, strategy in (overrides or {}).items():
            if strategy in self.STRATEGIES:
                self.strategy_map[activity_type] = strategy

    def select(self, activity_type: str, session_count: int = 0) -> str:
        if activity_type in self.strategy_map:
            return self.strategy_map[activity_type]
        return self.STRATEGIES[session_count % len(self.STRATEGIES)]


class PromptBuilder:
    """
    Builds system and user prompts for the LLM and exposes curated fallbacks.
    """

    def build_system_prompt(self, language: str = "en") -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(language=language)

    def build_user_prompt(
        self,
        request: ReflectRequest,
        strategy: str,
        depth_level: int,
        session_count: int,
    ) -> str:
        language = request.language if request.language in PROMPTS else "en"
        depth_question = PROMPTS[language][strategy].get(
            depth_level, PROMPTS[language][strategy][1]
        )

        prompt = (
            f"The learner just saved or resumed work in {request.activity_type}.\n"
            f"This local profile has reflected on this activity {session_count} time(s) before.\n"
            f"Generate exactly one reflection question similar in depth to: {depth_question}"
        )

        if request.shared_with:
            peer_question = PEER_QUESTIONS.get(language, PEER_QUESTIONS["en"]).get(
                strategy, PEER_QUESTIONS["en"][strategy]
            )
            prompt += (
                "\nThis was a collaborative session with other learners. "
                f"Also consider asking: {peer_question}"
            )

        return prompt

    def get_fallback_question(
        self,
        strategy: str,
        depth_level: int,
        language: str = "en",
    ) -> str:
        normalized = language if language in PROMPTS else "en"
        return PROMPTS[normalized][strategy].get(
            depth_level, PROMPTS[normalized][strategy][1]
        )

    def get_peer_question(self, strategy: str, language: str = "en") -> Optional[str]:
        normalized = language if language in PEER_QUESTIONS else "en"
        return PEER_QUESTIONS[normalized].get(strategy)


class BaseLLMBackend:
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return False

    async def health_check(self) -> bool:
        return True


class MockBackend(BaseLLMBackend):
    """Returns the static fallback question - useful for tests and demos."""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if "similar in depth to:" in user_prompt:
            return user_prompt.split("similar in depth to:", 1)[1].split("\n", 1)[0].strip()
        return "What did you learn from this activity?"

    async def health_check(self) -> bool:
        return True

    async def health_check(self) -> bool:
        return True


class OllamaBackend(BaseLLMBackend):
    """Local LLM inference via Ollama - privacy-first default."""

    def __init__(
        self,
        url: str = "http://localhost:11434",
        model: str = "tinyllama",
        timeout_seconds: float = 30.0,
    ):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
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

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.url}/api/tags")
                response.raise_for_status()
            return True
        except Exception:
            return False

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.url}/api/tags")
                response.raise_for_status()
            return True
        except Exception:
            return False


class SugarAIBackend(BaseLLMBackend):
    """
    Sugar-AI backend using the current prompted chat-style endpoint.
    The response parser is intentionally tolerant because deployments may wrap
    the result in slightly different JSON shapes.
    """

    def __init__(
        self,
        url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        for key in ("response", "answer", "question", "content", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()

        raise ValueError(f"Unsupported Sugar-AI response shape: {payload!r}")

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "chat": True,
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.url}/ask-llm-prompted",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return self._extract_text(response.json())

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.url}/health",
                    headers=self._headers(),
                )
                response.raise_for_status()
            return True
        except Exception:
            return False

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.url}/health",
                    headers=self._headers(),
                )
                response.raise_for_status()
            return True
        except Exception:
            return False


class OpenAIBackend(BaseLLMBackend):
    """Cloud LLM - compatibility path only, not the core deployment target."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
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

    async def health_check(self) -> bool:
        return bool(self.api_key)

    async def health_check(self) -> bool:
        return bool(self.api_key)


class LLMClient:
    """
    Wraps a backend with structural output validation.
    If the model output is malformed or unsafe, a curated static question is used.
    """

    def __init__(self, backend: BaseLLMBackend, blocked_keywords: list[str]):
        self.backend = backend
        self.blocked_keywords = blocked_keywords

    def validate_output(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        if not text.endswith("?"):
            return False
        if text.count("?") != 1:
            return False
        if "\n" in text:
            return False
        if len(text) < 10 or len(text) > 300:
            return False
        if any(keyword in text.lower() for keyword in self.blocked_keywords):
            return False
        return True

    async def get_reflection(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_question: str,
    ) -> str:
        try:
            raw = await self.backend.generate(system_prompt, user_prompt)
            if self.validate_output(raw):
                return raw.strip()
        except Exception as exc:
            LOGGER.warning("LLM generation failed; using fallback question: %s", exc)
        return fallback_question

    async def backend_ready(self) -> bool:
        try:
            return await self.backend.health_check()
        except Exception:
            return False


class ReflectionEngine:
    """
    Orchestrates depth tracking, strategy selection, prompt construction, and generation.
    """

    def __init__(self, config: ReflectionConfig):
        self.config = config
        self.depth_tracker = DepthTracker(config.depth_store_path)
        self.strategy_selector = StrategySelector(config.strategy_overrides)
        self.prompt_builder = PromptBuilder()
        self.metadata_adapter = JournalMetadataAdapter(config.default_language)
        self.llm_client = LLMClient(
            backend=self._create_backend(config),
            blocked_keywords=config.blocked_keywords,
        )

    def _create_backend(self, config: ReflectionConfig) -> BaseLLMBackend:
        if config.llm_backend == LLMBackend.OLLAMA:
            return OllamaBackend(
                config.ollama_url,
                config.ollama_model,
                config.request_timeout_seconds,
            )
        if config.llm_backend == LLMBackend.SUGAR_AI:
            return SugarAIBackend(
                config.sugar_ai_url,
                config.sugar_ai_api_key,
                config.request_timeout_seconds,
            )
        if config.llm_backend == LLMBackend.OPENAI:
            if not config.openai_api_key:
                raise ValueError("OpenAI backend requires an API key")
            return OpenAIBackend(
                config.openai_api_key,
                config.openai_model,
                config.request_timeout_seconds,
            )
        return MockBackend()

    async def reflect(self, request: ReflectRequest) -> ReflectResponse:
        session_count = self.depth_tracker.get_count(
            request.profile_id, request.activity_type
        )
        depth_level = self.depth_tracker.get_depth_level(session_count)
        strategy = self.strategy_selector.select(request.activity_type, session_count)

        system_prompt = self.prompt_builder.build_system_prompt(request.language)
        user_prompt = self.prompt_builder.build_user_prompt(
            request,
            strategy,
            depth_level,
            session_count,
        )
        fallback_question = self.prompt_builder.get_fallback_question(
            strategy,
            depth_level,
            request.language,
        )
        question = await self.llm_client.get_reflection(
            system_prompt,
            user_prompt,
            fallback_question,
        )

        new_count = self.depth_tracker.increment(request.profile_id, request.activity_type)
        is_collaborative = bool(request.shared_with)
        peer_question = None
        if is_collaborative:
            peer_question = self.prompt_builder.get_peer_question(
                strategy,
                request.language,
            )

        return ReflectResponse(
            question=question,
            strategy=strategy,
            depth_level=depth_level,
            session_count=new_count,
            is_collaborative=is_collaborative,
            peer_question=peer_question,
        )

    async def reflect_from_metadata(
        self, metadata_request: JournalMetadataRequest
    ) -> ReflectResponse:
        request = self.metadata_adapter.to_reflect_request(metadata_request)
        return await self.reflect(request)

    async def is_ready(self) -> bool:
        return await self.llm_client.backend.health_check()


def create_app(config_override: Optional[ReflectionConfig] = None) -> FastAPI:
    config = config_override or ReflectionConfig()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.config = config
        app.state.engine = ReflectionEngine(config)
        yield
        app.state.engine = None

    app = FastAPI(
        title="Reflective Loop",
        description="Adaptive AI Reflection Service for the Sugar Journal",
        version="0.2.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "backend": config.llm_backend.value}

    @app.get("/ready")
    async def ready(request: Request):
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine not initialised")

        if not await engine.is_ready():
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "backend": config.llm_backend.value,
                },
            )
        return {"status": "ready", "backend": config.llm_backend.value}

    @app.get("/ready")
    async def ready(request: Request):
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine not initialised")

        is_ready = await engine.llm_client.backend_ready()
        if not is_ready:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "degraded",
                    "backend": config.llm_backend.value,
                },
            )
        return {"status": "ready", "backend": config.llm_backend.value}

    @app.post("/reflect", response_model=ReflectResponse)
    async def reflect(payload: ReflectRequest, request: Request):
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine not initialised")
        return await engine.reflect(payload)

    @app.post("/reflect-from-journal", response_model=ReflectResponse)
    async def reflect_from_journal(payload: JournalMetadataRequest, request: Request):
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine not initialised")
        return await engine.reflect_from_metadata(payload)

    @app.get("/strategies")
    async def strategies(request: Request):
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine not initialised")
        return {
            "mappings": engine.strategy_selector.strategy_map,
            "available_strategies": StrategySelector.STRATEGIES,
        }

    @app.get("/depth/{profile_id}")
    async def get_depth(profile_id: str, request: Request):
        engine = getattr(request.app.state, "engine", None)
        if engine is None:
            raise HTTPException(status_code=503, detail="Engine not initialised")

        summary = engine.depth_tracker.get_profile_summary(profile_id)
        activities = {}
        for activity, count in summary.items():
            activities[activity] = {
                "session_count": count,
                "depth_level": engine.depth_tracker.get_depth_level(count),
            }
        return {"profile_id": profile_id, "activities": activities}

    return app


app = create_app()


async def demo():
    """Run a local demo showing strategies, collaboration, and depth progression."""
    print("=" * 60)
    print("Sugar Journal AI Reflection - Prototype Demo")
    print("=" * 60)

    demo_engine = ReflectionEngine(ReflectionConfig(llm_backend=LLMBackend.MOCK))
    test_entries = [
        ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="My First Spiral",
            profile_id="profile_001",
        ),
        ReflectRequest(
            activity_type="org.laptop.Write",
            entry_title="My Story About Space",
            profile_id="profile_001",
        ),
        ReflectRequest(
            activity_type="org.laptop.Paint",
            entry_title="Sunset Drawing",
            profile_id="profile_001",
        ),
        ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Team Fractal Project",
            profile_id="profile_001",
            shared_with=["profile_002"],
        ),
        ReflectRequest(
            activity_type="org.laptop.Paint",
            entry_title="Mi Dibujo del Sol",
            profile_id="profile_002",
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
            print("  Collaborative: Yes")
            print(f"  Peer Question: {result.peer_question}")

    print("\n" + "=" * 60)
    print("Depth Progression Demo (15 TurtleBlocks sessions)")
    print("=" * 60)

    demo_store = "depth_progression_demo.json"
    progression_engine = ReflectionEngine(
        ReflectionConfig(
            llm_backend=LLMBackend.MOCK,
            depth_store_path=demo_store,
        )
    )

    for i in range(15):
        result = await progression_engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.TurtleArt",
                entry_title=f"TurtleBlocks Session {i + 1}",
                profile_id="depth_demo_profile",
            )
        )
        level_bar = "*" * result.depth_level + "." * (4 - result.depth_level)
        print(f"  Session {i + 1:2d} | {level_bar} | L{result.depth_level} | {result.question}")

    if os.path.exists(demo_store):
        os.remove(demo_store)

    print("\n" + "=" * 60)
    print("DONE - All reflection strategies + depth progression tested.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
