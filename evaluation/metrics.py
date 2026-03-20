"""Lightweight metrics for bounded reflection prompt evaluation."""

from __future__ import annotations


def is_single_question(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and stripped.endswith("?") and stripped.count("?") == 1 and "\n" not in stripped


def appropriate_length(text: str, min_words: int = 4, max_words: int = 60) -> bool:
    words = text.strip().split()
    return min_words <= len(words) <= max_words


def avoids_blocked_keywords(text: str, blocked_keywords: list[str]) -> bool:
    lowered = text.lower()
    return not any(keyword in lowered for keyword in blocked_keywords)


def contains_blocked_keyword(text: str, blocked_keywords: list[str]) -> bool:
    return not avoids_blocked_keywords(text, blocked_keywords)


def has_valid_length(text: str, min_words: int = 4, max_words: int = 60) -> bool:
    return appropriate_length(text, min_words=min_words, max_words=max_words)


def has_collaboration_signal(response: dict) -> bool:
    return bool(response.get("is_collaborative") and response.get("peer_question"))


def score_response(response: dict, blocked_keywords: list[str]) -> dict[str, float]:
    question = response.get("question", "")
    scores = {
        "single_question": float(is_single_question(question)),
        "valid_length": float(has_valid_length(question)),
        "safe_keywords": float(not contains_blocked_keyword(question, blocked_keywords)),
        "collaboration_handled": float(has_collaboration_signal(response)),
    }
    scores["total"] = sum(scores.values())
    scores["max_total"] = float(len(scores))
    return scores


def summarise_scores(scores: list[dict[str, float]]) -> dict[str, float]:
    if not scores:
        return {"count": 0.0, "avg_total": 0.0}

    count = float(len(scores))
    keys = [key for key in scores[0] if key not in ("total", "max_total")]
    summary = {key: sum(item[key] for item in scores) / count for key in keys}
    summary["avg_total"] = sum(item["total"] for item in scores) / count
    summary["count"] = count
    return summary


def summarize_results(results: list[dict]) -> dict[str, float]:
    if not results:
        return {
            "count": 0,
            "valid_rate": 0.0,
            "single_question_rate": 0.0,
            "length_ok_rate": 0.0,
            "blocked_keyword_safe_rate": 0.0,
            "avg_latency_ms": 0.0,
            "collaborative_case_count": 0.0,
        }

    count = len(results)
    return {
        "count": count,
        "valid_rate": sum(1 for item in results if item["is_valid"]) / count,
        "single_question_rate": sum(1 for item in results if item["single_question"]) / count,
        "length_ok_rate": sum(1 for item in results if item["length_ok"]) / count,
        "blocked_keyword_safe_rate": sum(1 for item in results if item["blocked_keyword_safe"]) / count,
        "avg_latency_ms": sum(item["latency_ms"] for item in results) / count,
        "collaborative_case_count": sum(1 for item in results if item["is_collaborative"]),
    }
