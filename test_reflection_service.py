# -*- coding: utf-8 -*-
"""
Test suite for the Reflective Loop service.

Run with: pytest test_reflection_service.py -v
"""

import os
import json
import pytest
import asyncio
from pathlib import Path

from config import ReflectionConfig, LLMBackend
from reflection_service import (
    DepthTracker,
    StrategySelector,
    PromptBuilder,
    LLMClient,
    MockBackend,
    ReflectionEngine,
    ReflectRequest,
    ReflectResponse,
)
from prompts import PROMPTS, PEER_QUESTIONS


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_depth_store(tmp_path):
    """Return a temporary depth store path."""
    return str(tmp_path / "test_depth.json")


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


# ── DepthTracker Tests ────────────────────────────────────────────────────

class TestDepthTracker:

    def test_initial_count_is_zero(self, tracker):
        assert tracker.get_count("student_1", "org.laptop.TurtleArt") == 0

    def test_increment_returns_new_count(self, tracker):
        assert tracker.increment("student_1", "org.laptop.TurtleArt") == 1
        assert tracker.increment("student_1", "org.laptop.TurtleArt") == 2
        assert tracker.increment("student_1", "org.laptop.TurtleArt") == 3

    def test_separate_students_tracked_independently(self, tracker):
        tracker.increment("student_1", "org.laptop.TurtleArt")
        tracker.increment("student_2", "org.laptop.TurtleArt")
        assert tracker.get_count("student_1", "org.laptop.TurtleArt") == 1
        assert tracker.get_count("student_2", "org.laptop.TurtleArt") == 1

    def test_separate_activities_tracked_independently(self, tracker):
        tracker.increment("student_1", "org.laptop.TurtleArt")
        tracker.increment("student_1", "org.laptop.Write")
        assert tracker.get_count("student_1", "org.laptop.TurtleArt") == 1
        assert tracker.get_count("student_1", "org.laptop.Write") == 1

    def test_persistence(self, tmp_depth_store):
        tracker1 = DepthTracker(tmp_depth_store)
        tracker1.increment("student_1", "org.laptop.TurtleArt")

        tracker2 = DepthTracker(tmp_depth_store)
        assert tracker2.get_count("student_1", "org.laptop.TurtleArt") == 1

    def test_depth_level_boundaries(self, tracker):
        assert tracker.get_depth_level(0) == 1
        assert tracker.get_depth_level(2) == 1
        assert tracker.get_depth_level(3) == 2
        assert tracker.get_depth_level(6) == 2
        assert tracker.get_depth_level(7) == 3
        assert tracker.get_depth_level(14) == 3
        assert tracker.get_depth_level(15) == 4
        assert tracker.get_depth_level(100) == 4

    def test_get_student_summary(self, tracker):
        tracker.increment("student_1", "org.laptop.TurtleArt")
        tracker.increment("student_1", "org.laptop.TurtleArt")
        tracker.increment("student_1", "org.laptop.Write")
        summary = tracker.get_student_summary("student_1")
        assert summary == {"org.laptop.TurtleArt": 2, "org.laptop.Write": 1}

    def test_reset_student(self, tracker):
        tracker.increment("student_1", "org.laptop.TurtleArt")
        tracker.increment("student_1", "org.laptop.TurtleArt")
        tracker.reset_student("student_1", "org.laptop.TurtleArt")
        assert tracker.get_count("student_1", "org.laptop.TurtleArt") == 0


# ── StrategySelector Tests ────────────────────────────────────────────────

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
            "socratic", "kwl", "what_so_what_now_what",
            "socratic", "kwl", "what_so_what_now_what",
        ]

    def test_all_mapped_activities(self, selector):
        for activity, expected_strategy in StrategySelector.STRATEGY_MAP.items():
            assert selector.select(activity) == expected_strategy


# ── PromptBuilder Tests ───────────────────────────────────────────────────

class TestPromptBuilder:

    def test_system_prompt_contains_language(self, builder):
        prompt = builder.build_system_prompt("es")
        assert "es" in prompt

    def test_fallback_question_exists_for_all_combos(self, builder):
        for lang in PROMPTS:
            for strategy in PROMPTS[lang]:
                for depth in [1, 2, 3, 4]:
                    q = builder.get_fallback_question(strategy, depth, lang)
                    assert q.endswith("?"), f"Missing ? for {lang}/{strategy}/{depth}"

    def test_peer_question_exists_for_all_strategies(self, builder):
        for lang in PEER_QUESTIONS:
            for strategy in ["socratic", "kwl", "what_so_what_now_what"]:
                q = builder.get_peer_question(strategy, lang)
                assert q is not None
                assert q.endswith("?")

    def test_collaborative_prompt_includes_peer(self, builder):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Team Project",
            shared_with=["buddy_1"],
        )
        prompt = builder.build_user_prompt(request, "socratic", 1)
        assert "collaborative" in prompt.lower()

    def test_solo_prompt_no_peer(self, builder):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Solo Project",
        )
        prompt = builder.build_user_prompt(request, "socratic", 1)
        assert "collaborative" not in prompt.lower()

    def test_unknown_language_falls_back_to_english(self, builder):
        q = builder.get_fallback_question("socratic", 1, "xx")
        assert q == PROMPTS["en"]["socratic"][1]


# ── OutputValidator Tests ─────────────────────────────────────────────────

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

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_output(self):
        class BadBackend:
            async def generate(self, system, user):
                return "This is not a question"

        client = LLMClient(BadBackend(), blocked_keywords=[])
        result = await client.get_reflection("sys", "user", "Fallback question?")
        assert result == "Fallback question?"

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        class CrashBackend:
            async def generate(self, system, user):
                raise ConnectionError("Ollama not running")

        client = LLMClient(CrashBackend(), blocked_keywords=[])
        result = await client.get_reflection("sys", "user", "Safe fallback?")
        assert result == "Safe fallback?"


# ── ReflectionEngine Integration Tests ────────────────────────────────────

class TestReflectionEngine:

    @pytest.mark.asyncio
    async def test_basic_reflection(self, engine):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="My Spiral",
            student_id="test_student",
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
                    student_id="depth_test",
                )
            )
            levels.append(result.depth_level)

        # Should progress through 1 → 2 → 3 → 4
        assert levels[0] == 1   # session 0 → level 1
        assert levels[3] == 2   # session 3 → level 2
        assert levels[7] == 3   # session 7 → level 3
        assert levels[15] == 4  # session 15 → level 4

    @pytest.mark.asyncio
    async def test_collaborative_session(self, engine):
        request = ReflectRequest(
            activity_type="org.laptop.TurtleArt",
            entry_title="Team Fractal",
            student_id="collab_test",
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
                student_id="strategy_test",
            )
        )
        write = await engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.Write",
                entry_title="My Story",
                student_id="strategy_test",
            )
        )
        paint = await engine.reflect(
            ReflectRequest(
                activity_type="org.laptop.Paint",
                entry_title="Sunset",
                student_id="strategy_test",
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
                student_id="es_test",
                language="es",
            )
        )
        # Spanish fallback question should contain Spanish characters
        assert "?" in result.question or "¿" in result.question

    @pytest.mark.asyncio
    async def test_unknown_activity_rotates(self, engine):
        strategies = []
        for i in range(3):
            result = await engine.reflect(
                ReflectRequest(
                    activity_type="com.custom.Unknown",
                    entry_title=f"Custom {i}",
                    student_id="rotate_test",
                )
            )
            strategies.append(result.strategy)
        assert strategies == ["socratic", "kwl", "what_so_what_now_what"]
