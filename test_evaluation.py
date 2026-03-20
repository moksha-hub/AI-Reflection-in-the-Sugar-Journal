from evaluation.evaluate_service import run_evaluation
from evaluation.metrics import (
    contains_blocked_keyword,
    has_collaboration_signal,
    has_valid_length,
    is_single_question,
    score_response,
    summarise_scores,
)


def test_is_single_question():
    assert is_single_question("What did you make today?")
    assert not is_single_question("What did you make today")
    assert not is_single_question("What did you make? Why did you choose it?")


def test_has_valid_length():
    assert has_valid_length("What part of this activity felt most interesting to you?")
    assert not has_valid_length("Why?")


def test_contains_blocked_keyword():
    assert contains_blocked_keyword("Why do you hate this?", ["hate"])
    assert not contains_blocked_keyword("What did you enjoy here?", ["hate"])


def test_score_response_for_collaboration():
    scores = score_response(
        {
            "question": "What changed when you worked together on this project?",
            "strategy": "socratic",
            "depth_level": 2,
            "is_collaborative": True,
            "peer_question": "What did your partner help you notice?",
        },
        blocked_keywords=["hate"],
    )
    assert scores["collaboration_handled"] == 1


def test_has_collaboration_signal():
    assert has_collaboration_signal(
        {"is_collaborative": True, "peer_question": "What did your partner notice?"}
    )
    assert not has_collaboration_signal(
        {"is_collaborative": True, "peer_question": None}
    )


def test_summarise_scores():
    summary = summarise_scores(
        [
            {"single_question": 1, "valid_length": 1, "safe_keywords": 1, "total": 3, "max_total": 3},
            {"single_question": 0, "valid_length": 1, "safe_keywords": 1, "total": 2, "max_total": 3},
        ]
    )
    assert summary["single_question"] == 0.5
    assert summary["avg_total"] == 2.5
    assert summary["count"] == 2.0


def test_run_evaluation_returns_report():
    report = __import__("asyncio").run(run_evaluation())
    assert len(report["responses"]) == 4
    assert report["summary"]["count"] == 4.0
