import json
import sqlite3

import pytest

from database.connection import init_db
from services.quiz_session_controller import QuizSessionController
from models.quiz import AnswerRecord, QuizConfig, QuizResult
from utils.errors import PersistenceError


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_quizforge.db"
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO topics (name) VALUES (?)", ("Networking",))

    topic_id = conn.execute(
        "SELECT id FROM topics WHERE name = ?", ("Networking",)
    ).fetchone()[0]

    for i, level in enumerate([1, 2, 3, 1, 2]):
        conn.execute(
            """
            INSERT INTO questions (
                topic_id, text, option_a, option_b, option_c, option_d,
                correct_option, difficulty, explanation, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id, f"Test question {i + 1}",
                "Option A", "Option B", "Option C", "Option D",
                "A", level, f"Explanation {i + 1}", 1
            )
        )

    conn.commit()
    conn.close()
    return db_path, topic_id


def create_controller(db_path):
    return QuizSessionController(db_path=db_path)


def start_quiz(controller, topic_id, time_limit=60):
    config = {
        "learner_name": "Integration Tester",
        "topic_ids": [topic_id],
        "question_count": 5,
        "time_limit_seconds": time_limit
    }
    controller.startQuiz(json.dumps(config))


def read_attempt(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    attempt = conn.execute("SELECT * FROM attempts").fetchone()
    answers = conn.execute(
        "SELECT * FROM attempt_answers ORDER BY order_no"
    ).fetchall()

    conn.close()
    return attempt, answers


def test_controller_loads_topics(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    controller.topicsReady.connect(received.append)
    controller.loadTopics()

    assert len(received) == 1
    topics = json.loads(received[0])
    assert len(topics) == 1
    assert topics[0]["id"] == topic_id

    controller.timer.stop()


def test_controller_starts_adaptive_quiz(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    errors = []
    controller.sessionStarted.connect(received.append)
    controller.errorOccurred.connect(errors.append)

    start_quiz(controller, topic_id)

    assert errors == []
    assert len(received) == 1

    session = json.loads(received[0])
    assert session["total_questions"] == 5
    assert session["question"]["difficulty"] == 2

    controller.timer.stop()


def test_completed_weighted_quiz_is_saved(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    errors = []
    controller.sessionFinished.connect(received.append)
    controller.errorOccurred.connect(errors.append)

    start_quiz(controller, topic_id)
    assert errors == []

    feedback = []
    controller.answerFeedback.connect(feedback.append)
    final_question = None
    for index in range(5):
        final_question = controller.service.get_current_question()
        controller.submitAnswer("A")
        if index < 4:
            controller.nextQuestion()

    assert len(feedback) == 5
    assert json.loads(feedback[-1])["correct_option"] == final_question.correct_option
    assert received == []
    assert controller.service.is_active
    controller.nextQuestion()
    assert received == []
    assert "Finish Quiz" in errors[-1]
    controller.finishQuiz()

    assert len(received) == 1
    result = json.loads(received[0])

    assert result["status"] == "COMPLETED"
    assert result["attempt_id"] is not None
    assert result["answered_questions"] == 5
    assert result["correct_answers"] == 5
    assert result["earned_points"] == 9
    assert result["max_points"] == 9
    assert result["score_percent"] == 100

    attempt, answers = read_attempt(db_path)
    assert attempt["status"] == "COMPLETED"
    assert attempt["question_count"] == 5
    assert attempt["earned_points"] == 9
    assert attempt["max_points"] == 9
    assert len(answers) == 5

    controller.timer.stop()


def test_abandoned_quiz_saves_only_presented_questions(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    controller.sessionFinished.connect(received.append)

    start_quiz(controller, topic_id)
    controller.submitAnswer("A")
    controller.abandonQuiz()

    assert len(received) == 1
    result = json.loads(received[0])

    assert result["status"] == "ABANDONED"
    assert result["questions_presented"] == 1
    assert result["answered_questions"] == 1
    assert result["unanswered_questions"] == 0

    attempt, answers = read_attempt(db_path)
    assert attempt["status"] == "ABANDONED"
    assert len(answers) == 1

    controller.timer.stop()


def test_timed_out_quiz_records_remaining_questions_as_unanswered(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    controller.sessionFinished.connect(received.append)

    start_quiz(controller, topic_id)
    controller.submitAnswer("A")

    controller.service.clock = lambda: controller.service.deadline + 1
    controller._update_timer()

    assert len(received) == 1
    result = json.loads(received[0])

    assert result["status"] == "TIMED_OUT"
    assert result["questions_presented"] == 1
    assert result["answered_questions"] == 1
    assert result["recorded_answer_count"] == 5
    assert result["unanswered_questions"] == 4

    attempt, answers = read_attempt(db_path)
    assert attempt["status"] == "TIMED_OUT"
    assert len(answers) == 5
    assert len({answer["question_id"] for answer in answers}) == 5

    controller.timer.stop()


def test_database_save_failure_can_be_retried(test_db, monkeypatch):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    errors = []
    controller.sessionFinished.connect(received.append)
    controller.errorOccurred.connect(errors.append)

    from services.quiz_session_controller import AttemptRepository

    original_save = AttemptRepository.save_attempt
    calls = {"count": 0}

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("Simulated database failure")
        return original_save(*args, **kwargs)

    monkeypatch.setattr(AttemptRepository, "save_attempt", fail_once)

    start_quiz(controller, topic_id)

    for index in range(5):
        controller.submitAnswer("A")
        if index < 4:
            controller.nextQuestion()

    assert received == []
    assert controller.service.is_active
    controller.finishQuiz()

    assert received == []
    assert len(errors) == 1
    assert controller.attempt_saved is False
    assert controller.pending_result is not None

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0
    conn.close()

    controller.retrySave()

    assert len(received) == 1
    assert controller.attempt_saved is True
    assert controller.pending_result is None

    attempt, answers = read_attempt(db_path)
    assert attempt["status"] == "COMPLETED"
    assert attempt["max_points"] == 9
    assert len(answers) == 5

    controller.retrySave()

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1
    conn.close()

    controller.timer.stop()


def test_timeout_with_unanswered_current_question(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    controller.sessionFinished.connect(received.append)

    start_quiz(controller, topic_id)

    controller.service.clock = lambda: controller.service.deadline + 1
    controller._update_timer()

    assert len(received) == 1
    result = json.loads(received[0])

    assert result["status"] == "TIMED_OUT"
    assert result["questions_presented"] == 1
    assert result["answered_questions"] == 0
    assert result["recorded_answer_count"] == 5
    assert result["unanswered_questions"] == 5

    attempt, answers = read_attempt(db_path)
    assert attempt["status"] == "TIMED_OUT"
    assert len(answers) == 5
    assert all(answer["chosen_option"] is None for answer in answers)

    controller.timer.stop()


def test_abandon_after_deadline_is_timed_out(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)

    received = []
    controller.sessionFinished.connect(received.append)

    start_quiz(controller, topic_id)

    controller.service.clock = lambda: controller.service.deadline + 1
    controller.abandonQuiz()

    assert len(received) == 1
    result = json.loads(received[0])

    assert result["status"] == "TIMED_OUT"
    assert result["questions_presented"] == 1
    assert result["answered_questions"] == 0
    assert result["recorded_answer_count"] == 5
    assert result["unanswered_questions"] == 5

    attempt, answers = read_attempt(db_path)
    assert attempt["status"] == "TIMED_OUT"
    assert len(answers) == 5
    assert answers[0]["chosen_option"] is None

    controller.timer.stop()


def test_confirmed_close_abandons_and_saves_before_exit(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)
    start_quiz(controller, topic_id)
    controller.submitAnswer("A")

    assert controller.abandon_and_save_for_close()
    assert controller.attempt_saved
    attempt, answers = read_attempt(db_path)
    assert attempt["status"] == "ABANDONED"
    assert len(answers) == 1
    assert answers[0]["chosen_option"] == "A"


def test_attempt_save_rolls_back_attempt_when_answer_insert_fails(test_db):
    db_path, topic_id = test_db
    controller = create_controller(db_path)
    config = QuizConfig("Rollback Tester", (topic_id,), 5, 600)
    result = QuizResult(
        status="ABANDONED",
        earned_points=0,
        max_points=2,
        score_percent=0.0,
        answers=(AnswerRecord(999999, 1, 2, None, False),),
    )

    with pytest.raises(PersistenceError) as error:
        controller.attempt_repository.save_finished_attempt(
            config=config,
            started_at="2026-11-27T10:00:00+00:00",
            finished_at="2026-11-27T10:01:00+00:00",
            result=result,
        )
    assert isinstance(error.value.__cause__, sqlite3.IntegrityError)

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0
    conn.close()
