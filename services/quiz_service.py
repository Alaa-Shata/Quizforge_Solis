from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import time
import math


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

    VALID_STATUSES = {
        "COMPLETED",
        "TIMED_OUT",
        "ABANDONED"
    }

    def __init__(self, clock=None):

        self.config = None
        self.questions = []
        self.answers = []

        self.current_question_index = 0

        self.is_active = False
        self.is_finished = False

        self.started_at = None
        self.finished_at = None

        self.deadline = None
        self.result = None

        self.clock = clock or time.monotonic

    # ======================================
    # VALIDATION
    # ======================================

    def validate_setup(self, config: QuizConfig):

        if not isinstance(config.learner_name, str):
            raise ValueError("Invalid learner name.")

        if not config.learner_name.strip():
            raise ValueError("Please enter your name.")

        if len(config.learner_name.strip()) < 2:

            raise ValueError("Name must be at least 2 characters.")


        if len(config.learner_name.strip()) > 40:
            raise ValueError("Name cannot exceed 40 characters.")

        if not config.topic_ids:
            raise ValueError("Please select at least one topic.")

        if not 5 <= config.question_count <= 30:
            raise ValueError(
                "Question count must be between 5 and 30."
            )

        if config.time_limit_seconds <= 0:
            raise ValueError("Time limit must be greater than zero.")

    # ======================================
    # START QUIZ
    # ======================================

    def start(self, config: QuizConfig, questions: list):

        self.validate_setup(config)

        if self.is_active:
            raise RuntimeError(
                "A quiz session is already active."
            )

        if len(questions) < config.question_count:
            raise ValueError(
                "Not enough questions available."
            )

        self.config = config

        self.questions = questions[:config.question_count]

        self.answers = []

        self.current_question_index = 0

        self.started_at = datetime.now()
        self.finished_at = None

        self.is_active = True
        self.is_finished = False

        self.result = None

        if config.time_limit_seconds > 0:

            self.deadline = (
                self.clock() + config.time_limit_seconds
            )

        else:

            self.deadline = None

        return self.get_current_question()

    # ======================================
    # TIMER
    # ======================================

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

        if self.deadline is not None:

            if self.clock() >= self.deadline:

                self._finish("TIMED_OUT")

                return True

        return False

    # ======================================
    # CURRENT QUESTION
    # ======================================

    def get_current_question(self):

        if not self.is_active:
            raise RuntimeError(
                "No active quiz session."
            )

        if self._check_timeout():
            raise RuntimeError(
                "Quiz time has expired."
            )

        if self.current_question_index >= len(self.questions):
            return None

        return self.questions[self.current_question_index]

    # ======================================
    # SUBMIT ANSWER
    # ======================================

    def submit_answer(self, chosen_option: str):

        if not self.is_active:
            raise RuntimeError(
                "No active quiz session."
            )

        if self._check_timeout():
            raise RuntimeError(
                "Quiz time has expired."
            )

        if self.current_question_index >= len(self.questions):
            raise RuntimeError(
                "There are no remaining questions."
            )

        if not isinstance(chosen_option, str):
            raise ValueError("Invalid answer.")

        chosen_option = chosen_option.strip().upper()

        if chosen_option not in ("A", "B", "C", "D"):

            raise ValueError(
                "Choose A, B, C, or D."
            )

        question = self.questions[
            self.current_question_index
        ]

        if any(
            answer.question_id == question.id
            for answer in self.answers
        ):

            raise RuntimeError(
                "This question has already been answered."
            )

        correct_option = question.correct_option.upper()

        is_correct = (
            chosen_option == correct_option
        )

        answer_record = AnswerRecord(

            question_id=question.id,

            order_no=self.current_question_index + 1,

            level_asked=getattr(
                question,
                "difficulty",
                2
            ),

            chosen_option=chosen_option,

            is_correct=is_correct

        )

        self.answers.append(answer_record)

        return AnswerFeedback(

            is_correct=is_correct,

            correct_option=correct_option,

            explanation=getattr(
                question,
                "explanation",
                ""
            )

        )

    # ======================================
    # NEXT QUESTION
    # ======================================

    def next_question(self):

        if not self.is_active:
            raise RuntimeError(
                "No active quiz session."
            )

        if self._check_timeout():
            raise RuntimeError(
                "Quiz time has expired."
            )

        if len(self.answers) <= self.current_question_index:

            raise RuntimeError(
                "Submit your answer before continuing."
            )

        self.current_question_index += 1

        if self.current_question_index >= len(self.questions):
            return None

        return self.get_current_question()

    # ======================================
    # FINISH
    # ======================================

    def finish_timeout(self):
        return self._finish("TIMED_OUT")

    def abandon(self):
        return self._finish("ABANDONED")

    def finish(self):

        if len(self.answers) != len(self.questions):

            raise RuntimeError(
                "Cannot complete a quiz with unanswered questions."
            )

        return self._finish("COMPLETED")

    def _finish(self, status):

        if self.is_finished:
            return self.result

        if not self.is_active:
            raise RuntimeError(
                "No active quiz session."
            )

        if status not in self.VALID_STATUSES:
            raise ValueError("Invalid quiz status.")

        existing_ids = {
            answer.question_id for answer in self.answers
        }

        if status == "TIMED_OUT":
            # Record remaining questions as unanswered.
            for index, question in enumerate(self.questions):
                if question.id not in existing_ids:
                    self.answers.append(
                        AnswerRecord(
                            question_id=question.id,
                            order_no=index + 1,
                            level_asked=int(
                                getattr(question, "difficulty", 2)
                            ),
                            chosen_option=None,
                            is_correct=False
                        )
                    )

        elif status == "ABANDONED":
            # Record only the current unanswered question.
            if self.current_question_index < len(self.questions):
                question = self.questions[self.current_question_index]
                if question.id not in existing_ids:
                    self.answers.append(
                        AnswerRecord(
                            question_id=question.id,
                            order_no=self.current_question_index + 1,
                            level_asked=int(
                                getattr(question, "difficulty", 2)
                            ),
                            chosen_option=None,
                            is_correct=False
                        )
                    )

        self.finished_at = datetime.now()

        earned_points = sum(
            1
            for answer in self.answers
            if answer.is_correct
        )

        max_points = len(self.questions)

        score_percent = (
            earned_points / max_points * 100
            if max_points > 0
            else 0
        )

        self.result = QuizResult(

            status=status,

            earned_points=earned_points,

            max_points=max_points,

            score_percent=round(
                score_percent,
                2
            ),

            answers=self.answers.copy()

        )

        self.is_active = False
        self.is_finished = True

        return self.result

    # ======================================
    # RESULT
    # ======================================

    def get_result(self):
        return self.result

    # ======================================
    # SESSION STATE
    # ======================================

    def get_state(self):

        if self.is_active:
            self._check_timeout()

        return QuizSessionState(

            is_active=self.is_active,

            current_question_index=self.current_question_index,

            total_questions=len(self.questions),

            answered_questions=len(self.answers),

            started_at=self.started_at,

            finished_at=self.finished_at,

            remaining_seconds=(
                self.get_remaining_seconds()
                if self.is_active
                else 0
            )

        )