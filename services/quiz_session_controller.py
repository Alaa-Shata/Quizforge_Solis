import json
import logging

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from services.quiz_service import QuizService
from models.quiz import QuizConfig
from services.question_service import QuestionService
from database.repositories.question_repository import QuestionRepository
from database.connection import get_connection
from database.repositories.attempt_repository import AttemptRepository
from utils.errors import ActiveSessionError, QuizForgeError


class QuizSessionController(QObject):

    topicsReady = Signal(str)
    sessionStarted = Signal(str)
    answerFeedback = Signal(str)
    questionReady = Signal(str)
    sessionFinished = Signal(str)
    sessionSummaryReady = Signal(str)
    errorOccurred = Signal(str)
    timerUpdated = Signal(int)
    navigationLockChanged = Signal(bool)

    def __init__(self, parent=None, db_path=None, service=None):
        super().__init__(parent)

        self.db_path = db_path
        self.question_repository = QuestionRepository(
            lambda: get_connection(self.db_path)
        )
        self.attempt_repository = AttemptRepository(
            lambda: get_connection(self.db_path)
        )
        self.question_service = QuestionService(self.question_repository)
        self.service = service or QuizService(
            self.question_service, self.attempt_repository
        )
        if service is not None:
            if service.question_service is None:
                service.question_service = self.question_service
            if service.attempt_repository is None:
                service.attempt_repository = self.attempt_repository
            self.attempt_repository = service.attempt_repository
        self.question_count = 0
        self.attempt_saved = False
        self.pending_result = None
        self._save_in_progress = False
        self._topic_names = {}

        self.timer = QTimer(self)
        self._last_remaining = None
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._update_timer)

    @Slot()
    def loadTopics(self):
        try:
            topics = [
                {
                    "id": topic_id,
                    "name": name,
                    "question_count": len(
                        self.question_repository.list_questions(
                            topic_id=topic_id, active_only=True
                        )
                    )
                }
                for topic_id, name in self.question_repository.list_topics()
            ]
            self.topicsReady.emit(json.dumps(topics))
        except Exception as error:
            logging.exception("Could not load quiz topics")
            self.errorOccurred.emit("Could not load available topics.")

    @Slot(str)
    def startQuiz(self, config_json):
        try:
            if self.pending_result is not None and not self.attempt_saved:
                raise ActiveSessionError(
                    "Please retry saving the previous quiz result first."
                )

            config_data = json.loads(config_json)

            config = QuizConfig(
                learner_name=config_data["learner_name"],
                topic_ids=tuple(dict.fromkeys(int(topic_id) for topic_id in config_data["topic_ids"])),
                question_count=int(config_data["question_count"]),
                time_limit_seconds=int(config_data["time_limit_seconds"])
            )

            self.service.validate_setup(config)

            self.question_count = config.question_count
            self.attempt_saved = False
            self.pending_result = None

            self._topic_names = dict(self.question_repository.list_topics())
            first_question = self.service.start(config)

            self.sessionStarted.emit(
                json.dumps({
                    "total_questions": self.question_count,
                    "remaining_seconds": self.service.get_remaining_seconds(),
                    "question": self._serialize_question(first_question)
                })
            )

            self.timer.start()
            self._last_remaining = None
            self.navigationLockChanged.emit(True)

        except Exception as error:
            if isinstance(error, QuizForgeError):
                self.errorOccurred.emit(str(error))
            else:
                logging.exception("Could not start quiz")
                self.errorOccurred.emit("Could not start the quiz. Check your settings and try again.")

    def _serialize_question(self, question):
        return {
            "id": question.id,
            "topic_id": question.topic_id,
            "topic_name": self._topic_names.get(question.topic_id, "Quiz"),
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
                if self.service.is_finished:
                    self._finish_existing_result()
                else:
                    self.errorOccurred.emit("No next question is available.")
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
    def finishQuiz(self):
        """Finish only after the learner explicitly chooses Finish Quiz."""
        try:
            result = self.service.finish()
            self._save_and_emit(result)
        except Exception as error:
            self._handle_service_error(error)

    @Slot()
    def abandonQuiz(self):
        try:
            result = self.service.abandon()
            self._save_and_emit(result)
        except Exception as error:
            if isinstance(error, QuizForgeError):
                self.errorOccurred.emit(str(error))
            else:
                logging.exception("Could not abandon quiz")
                self.errorOccurred.emit("Could not save the abandoned quiz. Please retry.")

    def _update_timer(self):
        if not self.service.is_active:
            self.timer.stop()
            return

        remaining = self.service.get_remaining_seconds()

        if remaining is None:
            return

        if remaining != self._last_remaining:
            self.timerUpdated.emit(remaining)
            self._last_remaining = remaining

        if self.service.is_finished:
            self._finish_existing_result()

    def _handle_service_error(self, error):
        if self.service.is_finished:
            self._finish_existing_result()
        else:
            self.errorOccurred.emit(str(error))

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

        self._save_and_emit(self.pending_result, is_retry=True)

    def _build_summary_payload(self, result, save_status, attempt_id=None):
        config = self.service.config
        answered = sum(
            1 for answer in result.answers
            if answer.chosen_option is not None
        )
        presented = len(self.service.questions)

        return {
            "status": result.status,
            "attempt_id": attempt_id,
            "save_error": None,
            "save_status": save_status,
            "total_questions": config.question_count,
            "questions_presented": presented,
            "not_presented_questions": max(0, config.question_count - presented),
            "completion_percentage": round(
                answered / config.question_count * 100, 2
            ) if config.question_count else 0,
            "answered_questions": answered,
            "correct_answers": sum(
                1 for answer in result.answers if answer.is_correct
            ),
            "recorded_answer_count": len(result.answers),
            "unanswered_questions": len(result.answers) - answered,
            "earned_points": result.earned_points,
            "max_points": result.max_points,
            "score_percent": result.score_percent
        }

    def _save_and_emit(self, result, is_retry=False):
        if self.attempt_saved or self._save_in_progress:
            return

        if is_retry:
            if self.pending_result is None:
                self.errorOccurred.emit("There is no pending result to save.")
                return
            self._save_pending_result()
            return

        # A failed save must never be retried automatically.
        if self.pending_result is not None:
            return

        self.pending_result = result
        self.timer.stop()

        summary = self._build_summary_payload(
            result, save_status="saving"
        )
        self.sessionSummaryReady.emit(json.dumps(summary))

        # Save synchronously to preserve QWebChannel signal delivery.
        self._save_pending_result()

    def _save_pending_result(self):
        if self.attempt_saved or self._save_in_progress:
            return

        if self.pending_result is None:
            return

        self._save_in_progress = True
        result = self.pending_result
        config = self.service.config

        try:
            attempt_id = self.attempt_repository.save_finished_attempt(
                config=config,
                started_at=self.service.started_at.isoformat(),
                finished_at=self.service.finished_at.isoformat(),
                result=result,
            )
        except Exception:
            logging.exception("Could not persist quiz attempt")
            self._save_in_progress = False
            self.errorOccurred.emit(
                "Could not save quiz result. Please retry saving."
            )
            return

        self.attempt_saved = True
        self.pending_result = None
        self._save_in_progress = False

        payload = self._build_summary_payload(
            result,
            save_status="saved",
            attempt_id=attempt_id
        )
        self.sessionFinished.emit(json.dumps(payload))
        self.navigationLockChanged.emit(False)

    def abandon_and_save_for_close(self) -> bool:
        """Synchronously persist a confirmed close; return False on save failure."""
        try:
            if self.pending_result is None:
                if self.service.is_active:
                    self.pending_result = self.service.abandon()
                elif self.service.is_finished:
                    self.pending_result = self.service.get_result()
                else:
                    return True
            self.timer.stop()
            self.sessionSummaryReady.emit(json.dumps(
                self._build_summary_payload(self.pending_result, save_status="saving")
            ))
            self._save_pending_result()
            return self.attempt_saved
        except Exception:
            logging.exception("Could not persist quiz attempt during close")
            self.errorOccurred.emit(
                "Could not save quiz result. Please retry saving."
            )
            return False
