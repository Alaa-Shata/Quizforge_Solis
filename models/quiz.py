"""Shared immutable quiz DTOs."""

from dataclasses import dataclass

from models.question import Question

EASY, MEDIUM, HARD = 1, 2, 3


@dataclass(frozen=True)
class QuizConfig:
    learner_name: str
    topic_ids: tuple[int, ...]
    question_count: int
    time_limit_seconds: int = 600


@dataclass(frozen=True)
class AnswerRecord:
    question_id: int
    order_no: int
    level_asked: int
    chosen_option: str | None
    is_correct: bool


@dataclass(frozen=True)
class QuizResult:
    status: str
    earned_points: int
    max_points: int
    score_percent: float
    answers: tuple[AnswerRecord, ...]


@dataclass(frozen=True)
class AnswerFeedback:
    is_correct: bool
    correct_option: str
    chosen_option: str
    explanation: str
    earned_for_question: int
    level_asked: int
    next_target_level: int


@dataclass(frozen=True)
class QuizSessionState:
    phase: str
    current_question: Question | None
    requested_count: int
    presented_count: int
    submitted_count: int
    target_level: int
    remaining_seconds: int
    can_submit: bool
    can_advance: bool

    @property
    def is_active(self) -> bool:
        return self.phase in {"QUESTION", "FEEDBACK"}

    @property
    def current_question_index(self) -> int:
        return max(0, self.presented_count - 1)

    @property
    def total_questions(self) -> int:
        return self.requested_count

    @property
    def answered_questions(self) -> int:
        return self.submitted_count
