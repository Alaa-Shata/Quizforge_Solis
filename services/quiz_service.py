"""Quiz lifecycle orchestration; no Qt or SQL lives in this module."""

from datetime import datetime, timezone
import math
import time

from algorithms.adaptive_engine import AdaptiveEngine, calculate_score, select_question
from models.quiz import (
    AnswerFeedback,
    AnswerRecord,
    QuizConfig,
    QuizResult,
    QuizSessionState,
)
from utils.errors import ActiveSessionError, InsufficientQuestionsError, ValidationError


class QuizService:
    VALID_STATUSES = {"COMPLETED", "TIMED_OUT", "ABANDONED"}

    def __init__(self, question_service=None, attempt_repository=None, *, clock=None):
        self.question_service = question_service
        self.attempt_repository = attempt_repository
        self.clock = clock or time.monotonic
        self.config = None
        self.question_pool = []
        self.questions = []  # Questions actually displayed to the learner.
        self.answers = []
        self.used_question_ids = set()
        self.engine = None
        self.times_used = {}
        self.current_question_index = 0
        self.is_active = False
        self.is_finished = False
        self.started_at = None
        self.finished_at = None
        self.deadline = None
        self.result = None

    def validate_setup(self, config: QuizConfig) -> None:
        if not isinstance(config.learner_name, str):
            raise ValidationError("Enter a name between 2 and 40 characters.")
        name = config.learner_name.strip()
        if not 2 <= len(name) <= 40:
            raise ValidationError("Enter a name between 2 and 40 characters.")
        if not config.topic_ids:
            raise ValidationError("Select at least one topic.")
        if not 5 <= config.question_count <= 30:
            raise ValidationError("Choose between 5 and 30 questions.")
        if not 60 <= config.time_limit_seconds <= 7200:
            raise ValidationError("Choose a time limit between 1 and 120 minutes.")

    def _load_questions(self, config):
        if self.question_service is None:
            raise ValidationError("The question service is not configured.")
        questions = []
        for topic_id in config.topic_ids:
            questions.extend(self.question_service.list_questions(
                topic_id=topic_id, active_only=True
            ))
        unique = {question.id: question for question in questions}
        return sorted(unique.values(), key=lambda question: question.id)

    def start(self, config: QuizConfig):
        self.validate_setup(config)
        if self.is_active:
            raise ActiveSessionError("A quiz session is already active.")
        pool = self._load_questions(config)
        active_questions = sorted(
            {
                q.id: q for q in pool
                if getattr(q, "is_active", False)
                and getattr(q, "topic_id", config.topic_ids[0]) in config.topic_ids
            }.values(),
            key=lambda question: question.id,
        )
        if len({q.id for q in active_questions}) < config.question_count:
            raise InsufficientQuestionsError(
                f"Only {len({q.id for q in active_questions})} active questions are available."
            )

        self.config = config
        self.question_pool = active_questions
        times_used = None
        if self.attempt_repository is not None:
            times_used = self.attempt_repository.get_question_usage_counts(
                [q.id for q in active_questions]
            )
        self.times_used = dict(times_used or {})
        self.questions, self.answers, self.used_question_ids = [], [], set()
        self.engine = AdaptiveEngine()
        self.current_question_index = 0
        self.started_at = datetime.now(timezone.utc).replace(microsecond=0)
        self.finished_at = None
        self.deadline = self.clock() + config.time_limit_seconds
        self.is_active, self.is_finished, self.result = True, False, None
        first_question = self._select_next_question()
        if first_question is None:
            self.is_active = False
            raise InsufficientQuestionsError("No active questions are available.")
        return first_question

    def _select_next_question(self):
        question = select_question(
            self.question_pool, self.used_question_ids, self.engine.level,
            self.times_used,
        )
        if question is not None:
            self.questions.append(question)
            self.used_question_ids.add(question.id)
            self.current_question_index = len(self.questions) - 1
        return question

    def get_remaining_seconds(self) -> int:
        if not self.is_active or self.deadline is None:
            return 0
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            self._finish("TIMED_OUT")
            return 0
        return math.ceil(remaining)

    def _check_timeout(self) -> bool:
        if not self.is_active:
            return self.is_finished
        if self.deadline is not None and self.clock() >= self.deadline:
            self._finish("TIMED_OUT")
            return True
        return False

    def get_current_question(self):
        if not self.is_active:
            raise ActiveSessionError("No active quiz session.")
        if self._check_timeout():
            raise ActiveSessionError("Quiz time has expired.")
        return self.questions[self.current_question_index]

    def submit_answer(self, chosen_option: str) -> AnswerFeedback:
        if not self.is_active:
            raise ActiveSessionError("No active quiz session.")
        if self._check_timeout():
            raise ActiveSessionError("Quiz time has expired.")
        question = self.get_current_question()
        if any(a.question_id == question.id for a in self.answers):
            raise ActiveSessionError("This answer has already been submitted.")
        if not isinstance(chosen_option, str) or chosen_option.strip().upper() not in "ABCD" or len(chosen_option.strip()) != 1:
            raise ValidationError("Choose A, B, C, or D.")
        chosen_option = chosen_option.strip().upper()
        correct_option = question.correct_option.upper()
        correct = chosen_option == correct_option
        level_asked = int(question.difficulty)
        self.answers.append(AnswerRecord(
            question_id=question.id,
            order_no=self.current_question_index + 1,
            level_asked=level_asked,
            chosen_option=chosen_option,
            is_correct=correct,
        ))
        next_level = self.engine.record_answer(correct)
        return AnswerFeedback(
            is_correct=correct,
            correct_option=correct_option,
            chosen_option=chosen_option,
            explanation=getattr(question, "explanation", ""),
            earned_for_question=level_asked if correct else 0,
            level_asked=level_asked,
            next_target_level=next_level,
        )

    def next_question(self):
        if not self.is_active:
            if self.is_finished:
                return None
            raise ActiveSessionError("No active quiz session.")
        if self._check_timeout():
            return None
        if len(self.answers) <= self.current_question_index:
            raise ActiveSessionError("Submit your answer before continuing.")
        if len(self.questions) >= self.config.question_count:
            raise ValidationError(
                "All questions have been answered. Select Finish Quiz to view your results."
            )
        question = self._select_next_question()
        if question is None:
            raise InsufficientQuestionsError(
                "No additional question is available. Your submitted answers are still saved in this session."
            )
        return question

    def finish_timeout(self):
        return self._finish("TIMED_OUT")

    def abandon(self):
        if self._check_timeout():
            return self.result
        return self._finish("ABANDONED")

    def finish(self):
        if self.is_finished:
            return self.result
        if not self.is_active:
            raise ActiveSessionError("No active quiz session.")
        if len(self.questions) != self.config.question_count or len(self.answers) != len(self.questions):
            raise ValidationError("Complete every question before finishing.")
        return self._finish("COMPLETED")

    def _finish(self, status):
        if self.is_finished:
            return self.result
        if not self.is_active:
            raise ActiveSessionError("No active quiz session.")
        if status not in self.VALID_STATUSES:
            raise ValidationError("Invalid quiz status.")

        recorded_ids = {answer.question_id for answer in self.answers}
        if status == "TIMED_OUT":
            if self.current_question_index < len(self.questions):
                current = self.questions[self.current_question_index]
                if current.id not in recorded_ids:
                    self.answers.append(AnswerRecord(
                        question_id=current.id,
                        order_no=self.current_question_index + 1,
                        level_asked=int(current.difficulty),
                        chosen_option=None,
                        is_correct=False,
                    ))
                    recorded_ids.add(current.id)
            # Every remaining requested slot is a deterministic unanswered record.
            while len(self.answers) < self.config.question_count:
                question = select_question(
                    self.question_pool, self.used_question_ids, self.engine.level,
                    self.times_used,
                )
                if question is None:
                    break
                self.used_question_ids.add(question.id)
                self.answers.append(AnswerRecord(
                    question_id=question.id,
                    order_no=len(self.answers) + 1,
                    level_asked=int(question.difficulty),
                    chosen_option=None,
                    is_correct=False,
                ))
        elif status == "ABANDONED" and self.current_question_index < len(self.questions):
            question = self.questions[self.current_question_index]
            if question.id not in recorded_ids:
                self.answers.append(AnswerRecord(
                    question_id=question.id,
                    order_no=self.current_question_index + 1,
                    level_asked=int(question.difficulty),
                    chosen_option=None,
                    is_correct=False,
                ))

        self.finished_at = datetime.now(timezone.utc).replace(microsecond=0)
        score = calculate_score(tuple(self.answers))
        self.result = QuizResult(
            status=status,
            earned_points=score.earned,
            max_points=score.maximum,
            score_percent=score.percentage,
            answers=tuple(self.answers),
        )
        self.is_active, self.is_finished = False, True
        return self.result

    def get_result(self):
        return self.result

    def get_state(self) -> QuizSessionState:
        if self.is_active:
            self._check_timeout()
        phase = "FINISHED" if self.is_finished else (
            "SETUP" if self.config is None else
            "FEEDBACK" if self.current_question_index < len(self.answers) else "QUESTION"
        )
        current = self.questions[self.current_question_index] if self.is_active and self.questions else None
        submitted = sum(answer.chosen_option is not None for answer in self.answers)
        return QuizSessionState(
            phase=phase,
            current_question=current,
            requested_count=self.config.question_count if self.config else 0,
            presented_count=len(self.questions),
            submitted_count=submitted,
            target_level=self.engine.level if self.engine else 2,
            remaining_seconds=self.get_remaining_seconds() if self.is_active else 0,
            can_submit=phase == "QUESTION",
            can_advance=phase == "FEEDBACK",
        )
