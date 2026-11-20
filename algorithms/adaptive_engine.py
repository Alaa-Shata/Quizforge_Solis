"""Module 3 - Adaptive Engine & Weighted Scoring (owner: Alaa).

Pure Python: no Qt, no database. Safe to import from QuizService or tests.

The shared models are owned by the integration layer. Protocols keep this
module independent of Qt and persistence while accepting those models:

    Question:      id: int, difficulty: int (1..3), is_active: bool
    AnswerRecord:  level_asked: int (1..3), is_correct: bool
Legacy records with difficulty instead of level_asked and None for unanswered
remain supported. None scores zero and does not update engine streaks.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from typing import NamedTuple, Optional, Protocol, TypeVar

EASY, MEDIUM, HARD = 1, 2, 3
MIN_LEVEL, MAX_LEVEL = EASY, HARD
STREAK_TO_CHANGE = 2
LEVEL_NAMES = {EASY: "Easy", MEDIUM: "Medium", HARD: "Hard"}
# Points per correct answer equal the difficulty weight (Easy 1, Medium 2, Hard 3).


class QuestionLike(Protocol):
    id: int
    difficulty: int
    is_active: bool


class AnswerLike(Protocol):
    level_asked: int
    is_correct: Optional[bool]


class LegacyAnswerLike(Protocol):
    difficulty: int
    is_correct: Optional[bool]


Q = TypeVar("Q", bound=QuestionLike)


def _check_level(value: object, what: str) -> int:
    # bool is an int subclass; True must not sneak in as level 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{what} must be an int, got {type(value).__name__}")
    if not MIN_LEVEL <= value <= MAX_LEVEL:
        raise ValueError(f"{what} must be between {MIN_LEVEL} and {MAX_LEVEL}, got {value}")
    return value


@dataclass(frozen=True)
class EngineDiagnostics:
    """Read-only snapshot for demos/debugging. Not part of the integration contract."""

    level: int
    correct_streak: int
    wrong_streak: int


class AdaptiveEngine:
    """Tracks answer streaks and moves the target difficulty between 1 and 3."""

    def __init__(self) -> None:
        self._level = MEDIUM
        self._correct_streak = 0
        self._wrong_streak = 0

    @property
    def level(self) -> int:
        return self._level

    def record_answer(self, is_correct: bool) -> int:
        """Register one answer and return the target level for the NEXT question."""
        if not isinstance(is_correct, bool):
            raise TypeError(f"is_correct must be a bool, got {type(is_correct).__name__}")

        if is_correct:
            self._correct_streak += 1
            self._wrong_streak = 0
            if self._correct_streak >= STREAK_TO_CHANGE:
                self._level = min(self._level + 1, MAX_LEVEL)
                self._correct_streak = 0  # reset even when already at Hard
        else:
            self._wrong_streak += 1
            self._correct_streak = 0
            if self._wrong_streak >= STREAK_TO_CHANGE:
                self._level = max(self._level - 1, MIN_LEVEL)
                self._wrong_streak = 0  # reset even when already at Easy
        return self._level

    def diagnostics(self) -> EngineDiagnostics:
        return EngineDiagnostics(self._level, self._correct_streak, self._wrong_streak)


def select_question(
    questions: Iterable[Q],
    used_question_ids: Collection[int],
    target_level: int,
    times_used: Optional[Mapping[int, int]] = None,
) -> Optional[Q]:
    """Pick the next question deterministically, or None when the pool is exhausted.

    Ranking (first difference wins):
      1. distance from target_level (exact match first, else nearest)
      2. lower difficulty on equal distance
      3. fewer historical uses (times_used, missing id = 0)
      4. smaller question id
    Inactive and already-used questions are never returned. Inputs are not mutated.
    """
    _check_level(target_level, "target_level")
    if times_used is None:
        times_used = {}

    best_key = None
    best = None
    for q in questions:
        if not q.is_active or q.id in used_question_ids:
            continue
        d = _check_level(q.difficulty, f"Question {q.id} difficulty")
        count = times_used.get(q.id, 0)
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError(f"Question {q.id} usage count must be an int")
        if count < 0:
            raise ValueError(f"Question {q.id} usage count must not be negative")
        key = (abs(d - target_level), d, count, q.id)
        if best_key is None or key < best_key:
            best_key, best = key, q
    return best


class ScoreResult(NamedTuple):
    """Tuple contract (earned, maximum, percentage), with named access for demos."""
    earned: int
    maximum: int
    percentage: float  # 0.0 - 100.0, full precision; round only for display


def calculate_score(answers: Iterable[AnswerLike | LegacyAnswerLike]) -> ScoreResult:
    """Weighted score: correct answers earn their difficulty; wrong/unanswered earn 0.

    The maximum is the sum of the difficulties actually asked. Empty input -> 0/0, 0.0%.
    """
    earned = maximum = 0
    for a in answers:
        try:
            asked = a.level_asked
        except AttributeError:
            asked = a.difficulty
        weight = _check_level(asked, "Answer level_asked")
        if a.is_correct is not None and not isinstance(a.is_correct, bool):
            raise TypeError("Answer is_correct must be a bool or None")
        maximum += weight
        if a.is_correct is True:  # None (unanswered) and False both score 0
            earned += weight
    percentage = earned / maximum * 100 if maximum else 0.0
    return ScoreResult(earned, maximum, percentage)
