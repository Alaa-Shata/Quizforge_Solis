import json
import random

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from services.quiz_service import QuizService, QuizConfig
from repositories.question_repository import QuestionRepository
from database.connection import get_connection
from database.repositories.attempt_repository import AttemptRepository


class QuizSessionController(QObject):

    topicsReady = Signal(str)
    sessionStarted = Signal(str)
    answerFeedback = Signal(str)
    questionReady = Signal(str)
    sessionFinished = Signal(str)
    errorOccurred = Signal(str)
    timerUpdated = Signal(int)

    def __init__(self, parent=None, db_path=None):
        super().__init__(parent)

        self.db_path = db_path
        self.question_repository = QuestionRepository(
            lambda: get_connection(self.db_path)
        )
        self.service = QuizService()
        self.question_count = 0
        self.attempt_saved = False
        self.pending_result = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._update_timer)

    @Slot()
    def loadTopics(self):
        try:
            topics = [
                {"id": topic_id, "name": name}
                for topic_id, name in self.question_repository.list_topics()
            ]
            self.topicsReady.emit(json.dumps(topics))
        except Exception as error:
            self.errorOccurred.emit(str(error))

    @Slot(str)
    def startQuiz(self, config_json):
        try:
            if self.pending_result is not None and not self.attempt_saved:
                raise RuntimeError(
                    "Please retry saving the previous quiz result first."
                )

            config_data = json.loads(config_json)

            config = QuizConfig(
                learner_name=config_data["learner_name"],
                topic_ids=tuple(
                    int(topic_id) for topic_id in config_data["topic_ids"]
                ),
                question_count=int(config_data["question_count"]),
                time_limit_seconds=int(config_data["time_limit_seconds"])
            )

            self.service.validate_setup(config)

            if self.service.is_active:
                raise RuntimeError("A quiz session is already active.")

            questions = []

            for topic_id in config.topic_ids:
                questions.extend(
                    self.question_repository.list_questions(
                        topic_id=topic_id, active_only=True
                    )
                )

            random.shuffle(questions)

            if len(questions) < config.question_count:
                raise ValueError(
                    f"Only {len(questions)} questions are available "
                    "for your selected topics."
                )

            self.question_count = config.question_count
            self.attempt_saved = False
            self.pending_result = None

            first_question = self.service.start(config, questions)

            self.sessionStarted.emit(
                json.dumps({
                    "total_questions": self.question_count,
                    "remaining_seconds": self.service.get_remaining_seconds(),
                    "question": self._serialize_question(first_question)
                })
            )

            self.timer.start()

        except Exception as error:
            self.errorOccurred.emit(str(error))

    def _serialize_question(self, question):
        topics = [
            {"id": topic_id, "name": name}
            for topic_id, name in self.question_repository.list_topics()
        ]

        topic = next(
            (item for item in topics if item["id"] == question.topic_id),
            None
        )

        return {
            "id": question.id,
            "topic_id": question.topic_id,
            "topic_name": topic["name"] if topic else "Quiz",
            "text": question.text,
            "options": {
                "A": question.option_a,
                "B": question.option_b,
                "C": question.option_c,
                "D": question.option_d
            },
            "difficulty": question.difficulty
        }

    @Slot(str)
    def submitAnswer(self, chosen_option):
        try:
            feedback = self.service.submit_answer(chosen_option)

            self.answerFeedback.emit(
                json.dumps({
                    "is_correct": feedback.is_correct,
                    "correct_option": feedback.correct_option,
                    "explanation": feedback.explanation
                })
            )

        except Exception as error:
            self._handle_service_error(error)

    @Slot()
    def nextQuestion(self):
        try:
            question = self.service.next_question()

            if question is None:
                self._finish_session("COMPLETED")
                return

            self.questionReady.emit(
                json.dumps({
                    "question": self._serialize_question(question),
                    "question_number": self.service.current_question_index + 1,
                    "total_questions": self.question_count
                })
            )

        except Exception as error:
            self._handle_service_error(error)

    @Slot()
    def abandonQuiz(self):
        try:
            result = self.service.abandon()
            self._save_and_emit(result)
        except Exception as error:
            self.errorOccurred.emit(str(error))

    def _update_timer(self):
        if not self.service.is_active:
            self.timer.stop()
            return

        remaining = self.service.get_remaining_seconds()

        if remaining is None:
            return

        self.timerUpdated.emit(remaining)

        if self.service.is_finished:
            self._finish_existing_result()

    def _handle_service_error(self, error):
        if self.service.is_finished:
            self._finish_existing_result()
        else:
            self.errorOccurred.emit(str(error))

    def _finish_session(self, status):
        if status == "COMPLETED":
            result = self.service.finish()
        elif status == "TIMED_OUT":
            result = self.service.finish_timeout()
        else:
            result = self.service.abandon()

        self._save_and_emit(result)

    def _finish_existing_result(self):
        result = self.service.get_result()

        if result is not None:
            self._save_and_emit(result)

    @Slot()
    def retrySave(self):
        if self.attempt_saved:
            return

        if self.pending_result is None:
            self.errorOccurred.emit("There is no pending result to save.")
            return

        self._save_and_emit(self.pending_result)

    def _save_and_emit(self, result):
        if self.attempt_saved:
            return

        self.pending_result = result
        self.timer.stop()
        config = self.service.config

        try:
            attempt_id = AttemptRepository.save_attempt(
                learner_name=config.learner_name,
                started_at=self.service.started_at.isoformat(),
                finished_at=self.service.finished_at.isoformat(),
                status=result.status,
                question_count=config.question_count,
                earned_points=result.earned_points,
                max_points=result.max_points,
                answers=result.answers,
                db_path=self.db_path
            )

        except Exception as error:
            self.errorOccurred.emit(
                "Could not save quiz result. Please retry saving. " + str(error)
            )
            return

        self.attempt_saved = True
        self.pending_result = None

        answered = sum(
            1 for answer in result.answers
            if answer.chosen_option is not None
        )

        presented = len(self.service.questions)

        payload = {
            "status": result.status,
            "attempt_id": attempt_id,
            "save_error": None,
            "total_questions": config.question_count,
            "questions_presented": presented,
            "answered_questions": answered,
            "correct_answers": sum(
                1 for answer in result.answers if answer.is_correct
            ),
            "unanswered_questions": presented - answered,
            "earned_points": result.earned_points,
            "max_points": result.max_points,
            "score_percent": result.score_percent
        }

        self.sessionFinished.emit(json.dumps(payload))
