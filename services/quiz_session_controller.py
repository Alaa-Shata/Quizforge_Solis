import json
import random

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from services.quiz_service import QuizService, QuizConfig

from repositories.question_repository import QuestionRepository
from repositories.topic_repository import TopicRepository

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

        # Optional database path.
        # Used for integration testing with a separate test database.
        self.db_path = db_path

        self.service = QuizService()

        self.question_count = 0

        self.attempt_saved = False

        self.timer = QTimer(self)
        self.timer.setInterval(1000)

        self.timer.timeout.connect(self._update_timer)

    # ======================================
    # LOAD TOPICS
    # ======================================

    @Slot()
    def loadTopics(self):

        try:

            topics = TopicRepository.get_all_topics(
                self.db_path
            )

            self.topicsReady.emit(
                json.dumps(topics)
            )

        except Exception as error:

            self.errorOccurred.emit(str(error))

    # ======================================
    # START SESSION
    # ======================================

    @Slot(str)
    def startQuiz(self, config_json):

        try:

            config_data = json.loads(config_json)

            config = QuizConfig(

                learner_name=config_data["learner_name"],

                topic_ids=tuple(
                    int(topic_id)
                    for topic_id in config_data["topic_ids"]
                ),

                question_count=int(
                    config_data["question_count"]
                ),

                time_limit_seconds=int(
                    config_data["time_limit_seconds"]
                )

            )

            self.service.validate_setup(config)

            if self.service.is_active:

                raise RuntimeError(
                    "A quiz session is already active."
                )

            questions = []

            for topic_id in config.topic_ids:

                topic_questions = (
                    QuestionRepository.get_questions_by_topic(
                        topic_id,
                        self.db_path
                    )
                )

                questions.extend(topic_questions)

            # Shuffle questions from all selected topics.
            random.shuffle(questions)

            if len(questions) < config.question_count:

                raise ValueError(
                    f"Only {len(questions)} questions are available "
                    "for your selected topics."
                )

            self.question_count = config.question_count

            self.attempt_saved = False

            first_question = self.service.start(
                config,
                questions
            )

            self.sessionStarted.emit(
                json.dumps(
                    {
                        "total_questions": self.question_count,
                        "remaining_seconds": (
                            self.service.get_remaining_seconds()
                        ),
                        "question": self._serialize_question(
                            first_question
                        )
                    }
                )
            )

            self.timer.start()

        except Exception as error:

            self.errorOccurred.emit(str(error))

    # ======================================
    # SERIALIZE QUESTION
    # ======================================

    def _serialize_question(self, question):

        topics = TopicRepository.get_all_topics(
            self.db_path
        )

        topic = next(
            (
                item
                for item in topics
                if item["id"] == question.topic_id
            ),
            None
        )

        return {

            "id": question.id,

            "topic_id": question.topic_id,

            "topic_name": (
                topic["name"]
                if topic
                else "Quiz"
            ),

            "text": question.text,

            "options": {

                "A": question.option_a,

                "B": question.option_b,

                "C": question.option_c,

                "D": question.option_d

            },

            "difficulty": question.difficulty

        }

    # ======================================
    # SUBMIT ANSWER
    # ======================================

    @Slot(str)
    def submitAnswer(self, chosen_option):

        try:

            feedback = self.service.submit_answer(
                chosen_option
            )

            self.answerFeedback.emit(
                json.dumps(
                    {
                        "is_correct": feedback.is_correct,
                        "correct_option": feedback.correct_option,
                        "explanation": feedback.explanation
                    }
                )
            )

        except Exception as error:

            self._handle_service_error(error)

    # ======================================
    # NEXT QUESTION
    # ======================================

    @Slot()
    def nextQuestion(self):

        try:

            question = self.service.next_question()

            if question is None:

                self._finish_session("COMPLETED")

                return

            self.questionReady.emit(
                json.dumps(
                    {
                        "question": self._serialize_question(question),
                        "question_number": (
                            self.service.current_question_index + 1
                        ),
                        "total_questions": self.question_count
                    }
                )
            )

        except Exception as error:

            self._handle_service_error(error)

    # ======================================
    # ABANDON
    # ======================================

    @Slot()
    def abandonQuiz(self):

        try:

            result = self.service.abandon()

            self._save_and_emit(result)

        except Exception as error:

            self.errorOccurred.emit(str(error))

    # ======================================
    # TIMER
    # ======================================

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

    # ======================================
    # HANDLE SERVICE ERROR
    # ======================================

    def _handle_service_error(self, error):

        if self.service.is_finished:

            self._finish_existing_result()

        else:

            self.errorOccurred.emit(str(error))

    # ======================================
    # FINISH SESSION
    # ======================================

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

    # ======================================
    # SAVE RESULT
    # ======================================

    def _save_and_emit(self, result):

        if self.attempt_saved:
            return

        self.timer.stop()

        config = self.service.config

        attempt_id = None
        save_error = None

        try:

            attempt_id = AttemptRepository.save_attempt(

                learner_name=config.learner_name,

                started_at=self.service.started_at.isoformat(),

                finished_at=self.service.finished_at.isoformat(),

                status=result.status,

                question_count=len(self.service.questions),

                earned_points=result.earned_points,

                max_points=result.max_points,

                answers=result.answers,

                db_path=self.db_path

            )

            # Mark as saved only after successful database persistence.
            self.attempt_saved = True

        except Exception as error:

            save_error = str(error)

            print(
                "Attempt persistence failed:",
                save_error
            )

        payload = {

            "status": result.status,

            "attempt_id": attempt_id,

            "save_error": save_error,

            "total_questions": len(self.service.questions),

            "answered_questions": sum(
                1 for answer in result.answers
                if answer.chosen_option is not None
            ),

            "correct_answers": sum(
                1 for answer in result.answers
                if answer.is_correct
            ),

            "unanswered_questions": (
                len(self.service.questions)
                - sum(
                    1 for answer in result.answers
                    if answer.chosen_option is not None
                )
            ),

            "earned_points": result.earned_points,

            "max_points": result.max_points,

            "score_percent": result.score_percent

        }

        self.sessionFinished.emit(
            json.dumps(payload)
        )