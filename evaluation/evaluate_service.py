"""Evaluate the reflection service on a small set of representative scenarios."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from config import LLMBackend, ReflectionConfig
from evaluation.metrics import (
    appropriate_length,
    avoids_blocked_keywords,
    is_single_question,
    summarize_results,
)
from reflection_service import ReflectRequest, ReflectionEngine


SCENARIOS = [
    ReflectRequest(
        activity_type="org.laptop.TurtleArt",
        entry_title="Spiral",
        profile_id="eval_profile",
        language="en",
    ),
    ReflectRequest(
        activity_type="org.laptop.Write",
        entry_title="My Story",
        profile_id="eval_profile",
        language="en",
    ),
    ReflectRequest(
        activity_type="org.laptop.Paint",
        entry_title="Mi Pintura",
        profile_id="eval_profile_es",
        language="es",
    ),
    ReflectRequest(
        activity_type="com.custom.Unknown",
        entry_title="Custom Tool",
        profile_id="eval_profile",
        language="en",
        shared_with=["Asha"],
    ),
]


async def run_evaluation(config: ReflectionConfig | None = None) -> dict[str, object]:
    if config is None:
        config = ReflectionConfig(llm_backend=LLMBackend.MOCK)

    engine = ReflectionEngine(config)
    results: list[dict] = []

    for scenario in SCENARIOS:
        started = time.perf_counter()
        response = await engine.reflect(scenario)
        latency_ms = (time.perf_counter() - started) * 1000
        question = response.question
        single_question = is_single_question(question)
        length_ok = appropriate_length(question)
        blocked_keyword_safe = avoids_blocked_keywords(
            question,
            config.blocked_keywords,
        )
        is_valid = single_question and length_ok and blocked_keyword_safe

        results.append(
            {
                "activity_type": scenario.activity_type,
                "language": scenario.language,
                "strategy": response.strategy,
                "depth_level": response.depth_level,
                "question": question,
                "latency_ms": latency_ms,
                "single_question": single_question,
                "length_ok": length_ok,
                "blocked_keyword_safe": blocked_keyword_safe,
                "is_valid": is_valid,
                "is_collaborative": response.is_collaborative,
            }
        )

    return {"responses": results, "summary": summarize_results(results)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Reflective Loop service.")
    parser.add_argument(
        "--backend",
        choices=[backend.value for backend in LLMBackend],
        default=LLMBackend.MOCK.value,
        help="Backend to use for evaluation",
    )
    parser.add_argument(
        "--output",
        default="evaluation/report.json",
        help="Where to write the evaluation report",
    )
    args = parser.parse_args()

    config = ReflectionConfig(llm_backend=LLMBackend(args.backend))
    report = asyncio.run(run_evaluation(config))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report["summary"], indent=2))
    print(f"Saved full report to {output_path}")


if __name__ == "__main__":
    main()
