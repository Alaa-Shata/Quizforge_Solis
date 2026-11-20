"""Regression tests for the shared AnswerRecord integration contract."""
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from algorithms.adaptive_engine import calculate_score, select_question


@dataclass(frozen=True)
class AnswerRecord:
    question_id: int
    order_no: int
    level_asked: int
    chosen_option: str | None
    is_correct: bool


def test_shared_answer_records_and_tuple_result():
    records = (AnswerRecord(1, 1, 2, 'A', True),
               AnswerRecord(2, 2, 3, None, False))
    result = calculate_score(records)
    earned, maximum, percentage = result
    assert (earned, maximum, percentage) == (2, 5, 40.0)
    assert result.earned == earned


def test_actual_asked_level_takes_precedence_over_target():
    answer = SimpleNamespace(level_asked=1, difficulty=3, is_correct=True)
    assert calculate_score([answer]).maximum == 1


@pytest.mark.parametrize('bad', [0, 1, 'True', [], object()])
def test_score_rejects_invalid_correctness(bad):
    with pytest.raises(TypeError):
        calculate_score([SimpleNamespace(level_asked=2, is_correct=bad)])


@pytest.mark.parametrize('bad', [-1, True, '2', 1.5])
def test_selection_rejects_invalid_usage_counts(bad):
    question = SimpleNamespace(id=1, difficulty=2, is_active=True)
    with pytest.raises((TypeError, ValueError)):
        select_question([question], set(), 2, {1: bad})
