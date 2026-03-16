# -*- coding: utf-8 -*-
"""
Test suite for the Reflective Loop service.

Run with: pytest test_reflection_service.py -v
"""

import json

import pytest
from fastapi.testclient import TestClient

from config import LLMBackend, ReflectionConfig
from prompts import PEER_QUESTIONS, PROMPTS
from reflection_service import (
    DepthTracker,
    JournalMetadataAdapter,
    JournalMetadataRequest,
    LLMClient,
    MockBackend,
    PromptBuilder,
    ReflectRequest,
    ReflectResponse,
    ReflectionEngine,
    StrategySelector,
    create_app,
    normalize_language,
    parse_buddies_metadata,
)


@pytest.fixture
def tmp_depth_store(tmp_path):
    return str(tmp_path / "state" / "test_depth.json")


@pytest.fixture
def tracker(tmp_depth_store):
    return DepthTracker(tmp_depth_store)


@pytest.fixture
def selector():
    return StrategySelector()


@pytest.fixture
def builder():
    return PromptBuilder()


@pytest.fixture
def mock_client():
    return LLMClient(
        backend=MockBackend(),
        blocked_keywords=["kill", "hate", "stupid"],
    )


@pytest.fixture
def engine(tmp_depth_store):
    config = ReflectionConfig(
        llm_backend=LLMBackend.MOCK,
        depth_store_path=tmp_depth_store,
    )
    return ReflectionEngine(config)


@pytest.fixture
def client(tmp_depth_store):
    app = create_app(
        ReflectionConfig(
            llm_backend=LLMBackend.MOCK,
            depth_store_path=tmp_depth_store,
            strategy_overrides={"org.sugarlabs.Calculate": "kwl"},
        )
    )
    with TestClient(app) as test_client:
        yield test_client


class TestDepthTracker:
    def test_initial_count_is_zero(self, tracker):
        assert tracker.get_count("profile_1", "org.laptop.TurtleArt") == 0

    def test_increment_returns_new_count(self, tracker):
        assert tracker.increment("profile_1", "org.laptop.TurtleArt") == 1
        assert tracker.increment("profile_1", "org.laptop.TurtleArt") == 2
        assert tracker.increment("profile_1", "org.laptop.TurtleArt") == 3

    def test_separate_profiles_tracked_independently(self, tracker):
        tracker.increment("profile_1", "org.laptop.TurtleArt")
        tracker.increment("profile_2", "org.laptop.TurtleArt")
        assert tracker.get_count("profile_1", "org.laptop.TurtleArt") == 1
        assert tracker.get_count("profile_2", "org.laptop.TurtleArt") == 1

    def test_separate_activities_tracked_independently(self, tracker):
        tracker.increment("profile_1", "org.laptop.TurtleArt")
        tracker.increment("profile_1", "org.laptop.Write")
        assert tracker.get_count("profile_1", "org.laptop.TurtleArt") == 1
        assert tracker.get_count("profile_1", "org.laptop.Write") == 1

    def test_persistence(self, tmp_depth_store):
        tracker1 = DepthTracker(tmp_depth_store)
        tracker1.increment("profile_1", "org.laptop.TurtleArt")

        tracker2 = DepthTracker(tmp_depth_store)
        assert tracker2.get_count("profile_1", "org.laptop.TurtleArt") == 1

    def test_save_creates_parent_directories(self, tmp_path):
        nested_path = tmp_path / "deep" / "nested" / "depth.json"
        tracker = DepthTracker(str(nested_path))
        tracker.increment("profile_1", "org.laptop.TurtleArt")
        assert nested_path.exists()

    def test_corrupted_store_recovers_to_empty_state(self, tmp_path):
        depth_path = tmp_path / "corrupt.json"
        depth_path.write_text("{not-json", encoding="utf-8")
        tracker = DepthTracker(str(depth_path))
        assert tracker.get_profile_summary("profile_1") == {}
        assert tracker.increment("profile_1", "org.laptop.TurtleArt") == 1

    def test_depth_level_boundaries(self, tracker):
        assert tracker.get_depth_level(0) == 1
        assert tracker.get_depth_level(2) == 1
        assert tracker.get_depth_level(3) == 2
        assert tracker.get_depth_level(6) == 2
        assert tracker.get_depth_level(7) == 3
        assert tracker.get_depth_level(14) == 3
        assert tracker.get_depth_level(15) == 4
        assert tracker.get_depth_level(100) == 4

    def test_get_profile_summary(self, tracker):
        tracker.increment("profile_1", "org.laptop.TurtleArt")
        tracker.increment("profile_1", "org.laptop.TurtleArt")
        tracker.increment("profile_1", "org.laptop.Write")
        summary = tracker.get_profile_summary("profile_1")
        assert summary == {"org.laptop.TurtleArt": 2, "org.laptop.Write": 1}

    def test_reset_profile(self, tracker):
        tracker.increment("profile_1", "org.laptop.TurtleArt")
        tracker.increment("profile_1", "org.laptop.TurtleArt")
        tracker.reset_profile("profile_1", "org.laptop.TurtleArt")
        assert tracker.get_count("profile_1", "org.laptop.TurtleArt") == 0


class TestStrategySelector:
    def test_turtle_blocks_gets_socratic(self, selector):
        assert selector.select("org.laptop.TurtleArt") == "socratic"

    def test_write_gets_kwl(self, selector):
        assert selector.select("org.laptop.Write") == "kwl"

    def test_paint_gets_what_so_what(self, selector):
        assert selector.select("org.laptop.Paint") == "what_so_what_now_what"

    def test_unknown_activity_rotates(self, selector):
        results = [selector.select("com.custom.SomeApp", i) for i in range(6)]
        assert results == [
            "socratic",
            "kwl",
            "what_so_what_now_what",
            "socratic",
            "kwl",
            "what_so_what_now_what",
        ]

    def test_all_default_mapped_activities(self, selector):
        for activity, expected_strategy in StrategySelector.DEFAULT_STRATEGY_MAP.items():
            assert selector.select(activity) == expected_strategy

    def test_deployment_overrides_replace_defaults(self):
        selector = StrategySelector({"org.sugarlabs.Calculate": "kwl"})
        assert selector.select("org.sugarlabs.Calculate") == "kwl"

    def test_invalid_override_is_ignored(self):
        selector = StrategySelector({"org.sugarlabs.Calculate": "not-a-strategy"})
        assert selector.select("org.sugarlabs.Calculate", 0) == "socratic"


class TestPromptBuilder:
    def test_system_prompt_contains_language(self, builder):
        prompt = builder.build_system_prompt("es")
        assert "es" in prompt

    def test_fallback_question_exists_for_all_combos(self, builder):
        for lang in PROMPTS:
            for strategy in PROMPTS[lang]:
                for depth in [1, 2, 3, 4]:
                    question = builder.get_fallback_question(strategy, depth, lang)
                    assert question.endswith("?"), f"Missing ? for {lang}/{strategy}/{depth}"

    def test_peer_question_exists_for_all_strategies(self, builder):
        for lang in PEER_QUESTIONS:
            for strategy in ["socratic", "kwl", "what_so_what_now_what"]:
                question = builder.get_peer_question(strategy, lang)
                assert question is not None
                assert question.endswith("?")

    def test_collaborative_prompt_includes_peer(self, builder):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Team Project",
            shared_with=["buddy_1"],
        )
        prompt = builder.build_user_prompt(request, "socratic", 1, 2)
        assert "collaborative" in prompt.lower()

    def test_solo_prompt_no_peer(self, builder):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Solo Project",
        )
        prompt = builder.build_user_prompt(request, "socratic", 1, 0)
        assert "collaborative" not in prompt.lower()

    def test_prompt_uses_session_count_and_omits_entry_title(self, builder):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Private Project Name",
        )
        prompt = builder.build_user_prompt(request, "socratic", 2, 3)
        assert "3 time(s) before" in prompt
        assert "Private Project Name" not in prompt

    def test_unknown_language_falls_back_to_english(self, builder):
        question = builder.get_fallback_question("socratic", 1, "xx")
        assert question == PROMPTS["en"]["socratic"][1]


class TestMetadataHelpers:
    def test_normalize_language_handles_locale(self):
        assert normalize_language("en_US.UTF-8") == "en"
        assert normalize_language("pt-BR") == "pt"

    def test_parse_buddies_from_json_dict(self):
        buddies = parse_buddies_metadata('{"1":["Moksha","#123456,#654321"]}')
        assert buddies == ["Moksha"]

    def test_parse_buddies_from_invalid_json_returns_empty(self):
        assert parse_buddies_metadata("{bad") == []

    def test_metadata_adapter_prefers_bundle_id(self):
        adapter = JournalMetadataAdapter(default_language="en")
        request = JournalMetadataRequest(
            metadata={
                "bundle_id": "org.laptop.Paint",
                "activity": "activity-instance-id",
                "title": "My Painting",
                "buddies": '{"1":["Asha","#000000,#ffffff"]}',
            },
            profile_id="profile_1",
            language="fr_FR.UTF-8",
        )
        adapted = adapter.to_reflect_request(request)
        assert adapted.activity_type == "org.laptop.Paint"
        assert adapted.entry_title == "My Painting"
        assert adapted.language == "fr"
        assert adapted.shared_with == ["Asha"]

    def test_metadata_adapter_uses_environment_locale(self, monkeypatch):
        monkeypatch.setenv("LANG", "es_IN.UTF-8")
        adapter = JournalMetadataAdapter(default_language="en")
        adapted = adapter.to_reflect_request(
            JournalMetadataRequest(metadata={"bundle_id": "org.laptop.Write"})
        )
        assert adapted.language == "es"


class TestLLMClient:
    def test_valid_question_passes(self, mock_client):
        assert mock_client.validate_output("What did you learn today?") is True

    def test_no_question_mark_fails(self, mock_client):
        assert mock_client.validate_output("That was great work.") is False

    def test_too_short_fails(self, mock_client):
        assert mock_client.validate_output("Why?") is False

    def test_too_long_fails(self, mock_client):
        assert mock_client.validate_output("x " * 200 + "?") is False

    def test_empty_fails(self, mock_client):
        assert mock_client.validate_output("") is False

    def test_blocked_keyword_fails(self, mock_client):
        assert mock_client.validate_output("Why do you hate this activity?") is False

    def test_multiple_questions_fail(self, mock_client):
        assert mock_client.validate_output("What did you make? Why did you make it?") is False

    def test_multiline_output_fails(self, mock_client):
        assert mock_client.validate_output("What did you make?\nWhy?") is False

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_output(self):
        class BadBackend:
            async def generate(self, system_prompt, user_prompt):
                return "This is not a question"

        client = LLMClient(BadBackend(), blocked_keywords=[])
        result = await client.get_reflection("sys", "user", "Fallback question?")
        assert result == "Fallback question?"

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        class CrashBackend:
            async def generate(self, system_prompt, user_prompt):
                raise ConnectionError("Ollama not running")

        client = LLMClient(CrashBackend(), blocked_keywords=[])
        result = await client.get_reflection("sys", "user", "Safe fallback?")
        assert result == "Safe fallback?"


class TestReflectionEngine:
    @pytest.mark.asyncio
    async def test_basic_reflection(self, engine):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="My Spiral",
            profile_id="test_profile",
        )
        result = await engine.reflect(request)
        assert isinstance(result, ReflectResponse)
        assert result.strategy == "socratic"
        assert result.depth_level == 1
        assert result.session_count == 1
        assert result.question.endswith("?")
        assert result.is_collaborative is False

    @pytest.mark.asyncio
    async def test_depth_progresses_over_sessions(self, engine):
        levels = []
        for i in range(16):
            result = await engine.reflect(
                ReflectRequest(
                    activity_type="org.laptop.TurtleArt",
                    entry_title=f"Session {i}",
                    profile_id="depth_test",
                )
            )
            levels.append(result.depth_level)

        assert levels[0] == 1
        assert levels[3] == 2
        assert levels[7] == 3
        assert levels[15] == 4

    @pytest.mark.asyncio
    async def test_collaborative_session(self, engine):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Team Fractal",
            profile_id="collab_test",
            shared_with=["buddy_1"],
        )
        result = await engine.reflect(request)
        assert result.is_collaborative is True
        assert result.peer_question is not None
        assert result.peer_question.endswith("?")

    @pytest.mark.asyncio
    async def test_different_activities_get_different_strategies(self, engine):
        turtle = await engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.TurtleArt",
                entry_title="Spirals",
                profile_id="strategy_test",
            )
        )
        write = await engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.Write",
                entry_title="My Story",
                profile_id="strategy_test",
            )
        )
        paint = await engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.Paint",
                entry_title="Sunset",
                profile_id="strategy_test",
            )
        )
        assert turtle.strategy == "socratic"
        assert write.strategy == "kwl"
        assert paint.strategy == "what_so_what_now_what"

    @pytest.mark.asyncio
    async def test_spanish_reflection(self, engine):
        result = await engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.Paint",
                entry_title="Mi Pintura",
                profile_id="es_test",
                language="es",
            )
        )
        assert "?" in result.question or "¿" in result.question

    @pytest.mark.asyncio
    async def test_unknown_activity_rotates(self, engine):
        strategies = []
        for i in range(3):
            result = await engine.reflect(
                ReflectRequest(
                    activity_type="com.custom.Unknown",
                    entry_title=f"Custom {i}",
                    profile_id="rotate_test",
                )
            )
            strategies.append(result.strategy)
        assert strategies == ["socratic", "kwl", "what_so_what_now_what"]

    @pytest.mark.asyncio
    async def test_reflect_from_metadata(self, engine):
        result = await engine.reflect_from_metadata(
            JournalMetadataRequest(
                metadata={
                    "bundle_id": "org.laptop.TurtleArt",
                    "title": "Spiral",
                    "buddies": '{"1":["Asha","#000000,#ffffff"]}',
                },
                profile_id="metadata_test",
                language="en_US.UTF-8",
            )
        )
        assert result.strategy == "socratic"
        assert result.is_collaborative is True


class TestFastAPIEndpoints:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["backend"] == "mock"

    def test_reflect_endpoint(self, client):
        response = client.post(
            "/reflect",
            json={
                "activity_type": "org.laptop.TurtleArt",
                "entry_title": "My Spiral",
                "profile_id": "endpoint_profile",
                "language": "en",
                "shared_with": [],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["strategy"] == "socratic"
        assert payload["session_count"] == 1

    def test_reflect_from_journal_endpoint(self, client):
        response = client.post(
            "/reflect-from-journal",
            json={
                "metadata": {
                    "bundle_id": "org.laptop.Paint",
                    "title": "My Painting",
                    "buddies": '{"1":["Lina","#101010,#fafafa"]}',
                },
                "profile_id": "journal_profile",
                "language": "pt_BR.UTF-8",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["strategy"] == "what_so_what_now_what"
        assert payload["is_collaborative"] is True

    def test_strategies_endpoint_uses_effective_mapping(self, client):
        response = client.get("/strategies")
        assert response.status_code == 200
        payload = response.json()
        assert payload["mappings"]["org.sugarlabs.Calculate"] == "kwl"
        assert "socratic" in payload["available_strategies"]

    def test_depth_endpoint_reports_progress(self, client):
        client.post(
            "/reflect",
            json={
                "activity_type": "org.laptop.Write",
                "entry_title": "Draft One",
                "profile_id": "depth_profile",
                "language": "en",
                "shared_with": [],
            },
        )
        client.post(
            "/reflect",
            json={
                "activity_type": "org.laptop.Write",
                "entry_title": "Draft Two",
                "profile_id": "depth_profile",
                "language": "en",
                "shared_with": [],
            },
        )

        response = client.get("/depth/depth_profile")
        assert response.status_code == 200
        payload = response.json()
        assert payload["activities"]["org.laptop.Write"]["session_count"] == 2
        assert payload["activities"]["org.laptop.Write"]["depth_level"] == 1
