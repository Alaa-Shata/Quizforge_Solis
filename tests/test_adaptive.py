"""Tests for Module 3. Question/answer objects here are TEST-ONLY fixtures
standing in for the shared Question / AnswerRecord models (not yet approved)."""

import copy
from types import SimpleNamespace

import pytest

from algorithms.adaptive_engine import AdaptiveEngine, calculate_score, select_question


def q(id, difficulty, is_active=True):
    return SimpleNamespace(id=id, difficulty=difficulty, is_active=is_active)


def ans(difficulty, is_correct):
    return SimpleNamespace(difficulty=difficulty, is_correct=is_correct)


def pool(per_level=3):
    """ids 1..3 Easy, 4..6 Medium, 7..9 Hard (for per_level=3)."""
    return [q((lvl - 1) * per_level + i + 1, lvl) for lvl in (1, 2, 3) for i in range(per_level)]


def run_session(results, questions=None):
    """Drive engine + selector + scorer like QuizService would. Returns (asked_levels, score)."""
    questions = questions or pool(per_level=8)  # big enough that no fallback kicks in
    engine, used, answers, asked = AdaptiveEngine(), set(), [], []
    for ok in results:
        picked = select_question(questions, used, engine.level, {})
        used.add(picked.id)
        asked.append(picked.difficulty)
        answers.append(ans(picked.difficulty, ok))
        engine.record_answer(ok)
    return asked, calculate_score(answers)


# ---------------------------------------------------------------- engine

def test_initial_level_is_medium():
    assert AdaptiveEngine().level == 2


def test_two_correct_increase_level():
    e = AdaptiveEngine()
    assert e.record_answer(True) == 2
    assert e.record_answer(True) == 3


def test_two_wrong_decrease_level():
    e = AdaptiveEngine()
    assert e.record_answer(False) == 2
    assert e.record_answer(False) == 1


def test_level_stays_within_bounds():
    e = AdaptiveEngine()
    for _ in range(10):
        e.record_answer(True)
    assert e.level == 3
    for _ in range(10):
        e.record_answer(False)
    assert e.level == 1


def test_streaks_reset_after_transition_and_at_bounds():
    e = AdaptiveEngine()
    e.record_answer(True), e.record_answer(True)          # 2 -> 3
    assert e.diagnostics().correct_streak == 0
    e.record_answer(True), e.record_answer(True)          # at max: stays 3, still resets
    assert (e.level, e.diagnostics().correct_streak) == (3, 0)
    e.record_answer(True)                                 # one more alone must NOT change level
    assert e.level == 3 and e.diagnostics().correct_streak == 1

    e = AdaptiveEngine()
    for _ in range(4):
        e.record_answer(False)                            # 2 -> 1, then at min resets
    assert (e.level, e.diagnostics().wrong_streak) == (1, 0)


def test_switching_correctness_resets_opposite_streak():
    e = AdaptiveEngine()
    e.record_answer(True)
    e.record_answer(False)
    d = e.diagnostics()
    assert (d.correct_streak, d.wrong_streak) == (0, 1)


def test_alternating_answers_never_change_level():
    e = AdaptiveEngine()
    for i in range(12):
        assert e.record_answer(i % 2 == 0) == 2


@pytest.mark.parametrize("bad", [1, 0, None, "yes"])
def test_record_answer_rejects_non_bool(bad):
    with pytest.raises(TypeError):
        AdaptiveEngine().record_answer(bad)


# ---------------------------------------------------------------- selection

def test_selection_avoids_used_questions():
    qs = [q(1, 2), q(2, 2)]
    assert select_question(qs, {1}, 2, {}).id == 2


def test_inactive_questions_excluded():
    qs = [q(1, 2, is_active=False), q(2, 3)]
    assert select_question(qs, set(), 2, {}).id == 2


def test_nearest_difficulty_fallback():
    qs = [q(1, 1), q(2, 3)]
    assert select_question(qs, set(), 3, {}).id == 2
    assert select_question([q(1, 1)], set(), 3, {}).id == 1


def test_equal_distance_prefers_lower_level():
    qs = [q(1, 3), q(2, 1)]
    assert select_question(qs, set(), 2, {}).id == 2


def test_less_used_question_preferred():
    qs = [q(1, 2), q(2, 2)]
    assert select_question(qs, set(), 2, {1: 5, 2: 1}).id == 2


def test_smallest_id_breaks_remaining_ties():
    qs = [q(9, 2), q(4, 2), q(7, 2)]
    assert select_question(qs, set(), 2, {}).id == 4


def test_times_used_optional_and_missing_ids_count_as_zero():
    qs = [q(1, 2), q(2, 2)]
    assert select_question(qs, set(), 2, {1: 1}).id == 2
    assert select_question(qs, set(), 2).id == 1


def test_empty_or_exhausted_pool_returns_none():
    assert select_question([], set(), 2, {}) is None
    assert select_question([q(1, 2)], {1}, 2, {}) is None
    assert select_question([q(1, 2, is_active=False)], set(), 2, {}) is None


def test_nine_questions_nine_unique_then_none():
    qs, used, e = pool(per_level=3), set(), AdaptiveEngine()
    for i in range(9):
        picked = select_question(qs, used, e.level, {})
        assert picked is not None and picked.id not in used
        used.add(picked.id)
        e.record_answer(i % 3 != 0)
    assert len(used) == 9
    assert select_question(qs, used, e.level, {}) is None


@pytest.mark.parametrize("bad", [0, 4, -1, True, "2", 2.0, None])
def test_invalid_target_level_rejected(bad):
    with pytest.raises((TypeError, ValueError)):
        select_question([q(1, 2)], set(), bad, {})


def test_invalid_question_difficulty_rejected():
    with pytest.raises(ValueError):
        select_question([q(1, 5)], set(), 2, {})


def test_selection_is_deterministic_and_does_not_mutate_inputs():
    qs, used, usage = pool(), {1, 5}, {2: 3, 6: 1}
    snapshot = copy.deepcopy((qs, used, usage))
    picks = {select_question(qs, used, 2, usage).id for _ in range(5)}
    assert len(picks) == 1
    assert (qs, used, usage) == snapshot
    assert used == {1, 5} and usage == {2: 3, 6: 1}


def test_accepts_generators_and_any_used_collection():
    picked = select_question((x for x in pool()), frozenset({4}), 2, {})
    assert picked.id == 5


# ---------------------------------------------------------------- scoring

def test_weighted_scoring():
    s = calculate_score([ans(1, True), ans(2, True), ans(3, True), ans(3, False)])
    assert (s.earned, s.maximum) == (6, 9)
    assert s.percentage == pytest.approx(6 / 9 * 100)


def test_percentage_keeps_full_precision():
    s = calculate_score([ans(1, True), ans(2, False)])
    assert (s.earned, s.maximum) == (1, 3)
    assert s.percentage == pytest.approx(33.33333333333333)
    assert s.percentage != 33.3


def test_empty_answers_are_safe():
    s = calculate_score([])
    assert (s.earned, s.maximum, s.percentage) == (0, 0, 0.0)


def test_unanswered_scores_zero_but_counts_toward_maximum():
    s = calculate_score([ans(3, None), ans(2, True)])
    assert (s.earned, s.maximum, s.percentage) == (2, 5, 40.0)


def test_scoring_rejects_invalid_difficulty():
    with pytest.raises(ValueError):
        calculate_score([ans(0, True)])
    with pytest.raises(TypeError):
        calculate_score([ans("hard", True)])


def test_scoring_does_not_mutate_answers():
    answers = [ans(2, True), ans(3, None)]
    snapshot = copy.deepcopy(answers)
    calculate_score(answers)
    assert answers == snapshot


# ---------------------------------------------------------------- golden sequences

def test_golden_sequence():
    C, W = True, False
    asked, s = run_session([C, C, W, C, C, W, W, C])
    assert asked == [2, 2, 3, 3, 3, 3, 3, 2]
    assert (s.earned, s.maximum) == (12, 21)
    assert s.percentage == pytest.approx(12 / 21 * 100)


def test_three_correct():
    asked, s = run_session([True] * 3)
    assert asked == [2, 2, 3]
    assert s.earned == 7


def test_four_wrong():
    asked, s = run_session([False] * 4)
    assert asked == [2, 2, 1, 1]
    assert s.earned == 0
