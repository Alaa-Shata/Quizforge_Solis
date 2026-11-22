from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import time
import math

from algorithms.adaptive_engine import (
    AdaptiveEngine,
    select_question,
    calculate_score
)


@dataclass
class QuizConfig:
    learner_name: str
    topic_ids: tuple[int, ...]
    question_count: int
    time_limit_seconds: int = 600


@dataclass
class AnswerRecord:
    question_id: int
    order_no: int
    level_asked: int
    chosen_option: Optional[str]
    is_correct: bool


@dataclass
class QuizResult:
    status: str
    earned_points: int
    max_points: int
    score_percent: float
    answers: list[AnswerRecord]


@dataclass
class AnswerFeedback:
    is_correct: bool
    correct_option: str
    explanation: str = ""


@dataclass
class QuizSessionState:
    is_active: bool = False
    current_question_index: int = 0
    total_questions: int = 0
    answered_questions: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    remaining_seconds: Optional[int] = None


class QuizService:

    VALID_STATUSES = {"COMPLETED", "TIMED_OUT", "ABANDONED"}

    def __init__(self, clock=None):
        self.config = None
        self.question_pool = []
        self.questions = []
        self.answers = []
        self.used_question_ids = set()
        self.engine = None

        self.current_question_index = 0
        self.is_active = False
        self.is_finished = False
        self.started_at = None
        self.finished_at = None
        self.deadline = None
        self.result = None
        self.clock = clock or time.monotonic

    def validate_setup(self, config: QuizConfig):
        if not isinstance(config.learner_name, str):
            raise ValueError("Invalid learner name.")

        name = config.learner_name.strip()

        if not name:
            raise ValueError("Please enter your name.")
        if len(name) < 2:
            raise ValueError("Name must be at least 2 characters.")
        if len(name) > 40:
            raise ValueError("Name cannot exceed 40 characters.")
        if not config.topic_ids:
            raise ValueError("Please select at least one topic.")
        if not 5 <= config.question_count <= 30:
            raise ValueError("Question count must be between 5 and 30.")
        if config.time_limit_seconds <= 0:
            raise ValueError("Time limit must be greater than zero.")

    def start(self, config: QuizConfig, questions: list):
        self.validate_setup(config)

        if self.is_active:
            raise RuntimeError("A quiz session is already active.")

        active_questions = [
            q for q in questions
            if getattr(q, "is_active", False)
        ]

        if len(active_questions) < config.question_count:
            raise ValueError("Not enough active questions available.")

        self.config = config
        self.question_pool = list(active_questions)
        self.questions = []
        self.answers = []
        self.used_question_ids = set()
        self.engine = AdaptiveEngine()
        self.current_question_index = 0

        self.started_at = datetime.now()
        self.finished_at = None
        self.is_active = True
        self.is_finished = False
        self.result = None

        self.deadline = self.clock() + config.time_limit_seconds

        first_question = self._select_next_question()

        if first_question is None:
            self.is_active = False
            raise RuntimeError("No active questions available.")

        return first_question

    def _select_next_question(self):
        question = select_question(
            questions=self.question_pool,
            used_question_ids=self.used_question_ids,
            target_level=self.engine.level
        )

        if question is None:
            return None

        self.questions.append(question)
        self.used_question_ids.add(question.id)
        self.current_question_index = len(self.questions) - 1

        return question

    def get_remaining_seconds(self):
        if not self.is_active:
            return 0

        if self.deadline is None:
            return None

        remaining = self.deadline - self.clock()

        if remaining <= 0:
            self._finish("TIMED_OUT")
            return 0

        return math.ceil(remaining)

    def _check_timeout(self):
        if not self.is_active:
            return self.is_finished

        if self.deadline is not None and self.clock() >= self.deadline:
            self._finish("TIMED_OUT")
            return True

        return False

    def get_current_question(self):
        if not self.is_active:
            raise RuntimeError("No active quiz session.")

        if self._check_timeout():
            raise RuntimeError("Quiz time has expired.")

        if self.current_question_index >= len(self.questions):
            return None

        return self.questions[self.current_question_index]

    def submit_answer(self, chosen_option: str):
        if not self.is_active:
            raise RuntimeError("No active quiz session.")

        if self._check_timeout():
            raise RuntimeError("Quiz time has expired.")

        if self.current_question_index >= len(self.questions):
            raise RuntimeError("There are no remaining questions.")

        if not isinstance(chosen_option, str):
            raise ValueError("Invalid answer.")

        chosen_option = chosen_option.strip().upper()

        if chosen_option not in ("A", "B", "C", "D"):
            raise ValueError("Choose A, B, C, or D.")

        question = self.questions[self.current_question_index]

        if any(a.question_id == question.id for a in self.answers):
            raise RuntimeError("This question has already been answered.")

        correct_option = question.correct_option.upper()
        is_correct = chosen_option == correct_option

        answer_record = AnswerRecord(
            question_id=question.id,
            order_no=self.current_question_index + 1,
            level_asked=int(question.difficulty),
            chosen_option=chosen_option,
            is_correct=is_correct
        )

        self.answers.append(answer_record)

        # Update the adaptive engine exactly once per submitted answer.
        self.engine.record_answer(is_correct)

        return AnswerFeedback(
            is_correct=is_correct,
            correct_option=correct_option,
            explanation=getattr(question, "explanation", "")
        )

    def next_question(self):
        if not self.is_active:
            raise RuntimeError("No active quiz session.")

        if self._check_timeout():
            raise RuntimeError("Quiz time has expired.")

        if len(self.answers) <= self.current_question_index:
            raise RuntimeError("Submit your answer before continuing.")

        if len(self.questions) >= self.config.question_count:
            return None

        return self._select_next_question()

    def finish_timeout(self):
        return self._finish("TIMED_OUT")

    def abandon(self):
        # Timeout takes precedence if the deadline has already passed.
        if self._check_timeout():
            return self.result

        return self._finish("ABANDONED")

    def finish(self):
        if len(self.questions) != self.config.question_count:
            raise RuntimeError("The requested number of questions was not presented.")

        if len(self.answers) != len(self.questions):
            raise RuntimeError("Cannot complete a quiz with unanswered questions.")

        return self._finish("COMPLETED")

    def _finish(self, status):
        if self.is_finished:
            return self.result

        if not self.is_active:
            raise RuntimeError("No active quiz session.")

        if status not in self.VALID_STATUSES:
            raise ValueError("Invalid quiz status.")

        existing_ids = {a.question_id for a in self.answers}

        if status == "TIMED_OUT":
            # Only questions already presented are recorded as unanswered.
            for index, question in enumerate(self.questions):
                if question.id not in existing_ids:
                    self.answers.append(
                        AnswerRecord(
                            question_id=question.id,
                            order_no=index + 1,
                            level_asked=int(question.difficulty),
                            chosen_option=None,
                            is_correct=False
                        )
                    )

        elif status == "ABANDONED":
            # Record the current question only if it was presented and unanswered.
            if self.current_question_index < len(self.questions):
                question = self.questions[self.current_question_index]

                if question.id not in existing_ids:
                    self.answers.append(
                        AnswerRecord(
                            question_id=question.id,
                            order_no=self.current_question_index + 1,
                            level_asked=int(question.difficulty),
                            chosen_option=None,
                            is_correct=False
                        )
                    )

        self.finished_at = datetime.now()

        score = calculate_score(self.answers)

        self.result = QuizResult(
            status=status,
            earned_points=score.earned,
            max_points=score.maximum,
            score_percent=round(score.percentage, 2),
            answers=self.answers.copy()
        )

        self.is_active = False
        self.is_finished = True

        return self.result

    def get_result(self):
        return self.result

    def get_state(self):
        if self.is_active:
            self._check_timeout()

        return QuizSessionState(
            is_active=self.is_active,
            current_question_index=self.current_question_index,
            total_questions=(
                self.config.question_count if self.config else 0
            ),
            answered_questions=sum(
                1 for a in self.answers if a.chosen_option is not None
            ),
            started_at=self.started_at,
            finished_at=self.finished_at,
            remaining_seconds=(
                self.get_remaining_seconds() if self.is_active else 0
            )
        )
