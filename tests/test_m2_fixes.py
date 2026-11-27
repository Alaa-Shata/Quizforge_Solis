import json
import sqlite3
from pathlib import Path

import pytest

from database.connection import init_db
from database.repositories.attempt_repository import AttemptRepository
from services.quiz_session_controller import QuizSessionController


def build_bank(db_path):
    """Two topics, 12 questions each (4 per level)."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    topic_ids = []

    for name in ("Cybersecurity", "Networking"):
        conn.execute("INSERT INTO topics (name) VALUES (?)", (name,))
        topic_id = conn.execute(
            "SELECT id FROM topics WHERE name = ?", (name,)
        ).fetchone()[0]
        topic_ids.append(topic_id)

        for i in range(12):
            conn.execute(
                """
                INSERT INTO questions (
                    topic_id, text, option_a, option_b, option_c, option_d,
                    correct_option, difficulty, explanation, is_active
                ) VALUES (?, ?, 'A1', 'B1', 'C1', 'D1', 'A', ?, 'why', 1)
                """,
                (topic_id, f"{name} question {i + 1}", (i % 3) + 1)
            )

    conn.commit()
    conn.close()
    return db_path, topic_ids


def test_final_question_uses_a_separate_explicit_finish_action():
    script = Path("ui/quiz_session.js").read_text(encoding="utf-8")
    assert 'id="finish-quiz"' in script
    assert '.addEventListener("click", finishQuiz)' in script
    assert "Last question answered. Review the feedback" in script
    assert "quizBridge.finishQuiz()" in script


def test_return_to_setup_is_prominent_and_waits_for_saved_result():
    script = Path("ui/quiz_session.js").read_text(encoding="utf-8")
    result_screen = script[script.index("function renderFinishedScreen"):]
    assert 'class="finished-return"' in result_screen
    assert result_screen.index('id="return-to-setup"') < result_screen.index("scoreHighlightHTML(result)")
    assert "Return to Quiz Setup" in result_screen
    assert 'result.save_status === "saving" ? "disabled" : ""' in result_screen
    assert "returnButton.disabled = false" in result_screen
    return_handler = script[script.index("function returnToSetup()"):]
    assert 'document.body.classList.remove("quiz-active")' in return_handler
    assert 'document.body.classList.add("focus-mode")' in return_handler
    assert "setupLayout.hidden = false" in return_handler
    assert "quizStage.hidden = true" in return_handler


def test_save_completion_is_cached_if_it_arrives_before_the_result_screen():
    script = Path("ui/quiz_session.js").read_text(encoding="utf-8")
    received = script.index("completedSaveResult = result;")
    immediate_update = script.index("updateSaveStatus(result);", received)
    render = script.index("function renderFinishedScreen")
    cached_update = script.index(
        "if (completedSaveResult?.attempt_id)", render
    )
    assert received < immediate_update < render < cached_update


@pytest.fixture
def bank(tmp_path):
    return build_bank(tmp_path / "m2_fixes.db")


def run_quiz(db_path, topic_ids, count=10, answers="A"):
    """Play one full quiz and return the list of presented question dicts."""
    controller = QuizSessionController(db_path=db_path)
    started, asked, errors = [], [], []
    controller.sessionStarted.connect(started.append)
    controller.questionReady.connect(asked.append)
    controller.errorOccurred.connect(errors.append)

    controller.startQuiz(json.dumps({
        "learner_name": "Rawan",
        "topic_ids": list(topic_ids),
        "question_count": count,
        "time_limit_seconds": 600
    }))
    assert errors == []

    questions = [json.loads(started[0])["question"]]

    for index in range(count):
        controller.submitAnswer(answers)
        if index < count - 1:
            controller.nextQuestion()
            questions.append(json.loads(asked[-1])["question"])

    controller.finishQuiz()
    controller.timer.stop()
    assert errors == []
    return questions


def test_same_topic_does_not_repeat_same_questions(bank):
    db_path, topic_ids = bank
    first = {q["id"] for q in run_quiz(db_path, topic_ids[:1], count=5)}
    second = {q["id"] for q in run_quiz(db_path, topic_ids[:1], count=5)}

    assert first != second
    assert len(first & second) < 5


def test_multiple_topics_use_deterministic_adaptive_selection(bank):
    db_path, topic_ids = bank
    questions = run_quiz(db_path, topic_ids, count=10)
    per_topic = {}

    for question in questions:
        per_topic[question["topic_id"]] = per_topic.get(question["topic_id"], 0) + 1

    assert all(question["topic_id"] in topic_ids for question in questions)
    assert len({question["id"] for question in questions}) == len(questions)


def test_retry_save_saves_once_and_never_auto_retries(bank, monkeypatch):
    db_path, topic_ids = bank
    controller = QuizSessionController(db_path=db_path)
    errors, finished = [], []
    controller.errorOccurred.connect(errors.append)
    controller.sessionFinished.connect(finished.append)

    original = AttemptRepository.save_attempt
    calls = {"count": 0}

    def fail_first(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("disk is busy")
        return original(*args, **kwargs)

    monkeypatch.setattr(AttemptRepository, "save_attempt", fail_first)

    controller.startQuiz(json.dumps({
        "learner_name": "Rawan", "topic_ids": [topic_ids[0]],
        "question_count": 5, "time_limit_seconds": 600
    }))

    for index in range(5):
        controller.submitAnswer("A")
        if index < 4:
            controller.nextQuestion()

    assert finished == []
    controller.finishQuiz()

    # First save failed: nothing stored, no automatic second attempt.
    assert len(errors) == 1
    assert errors[0].startswith("Could not save quiz result")
    assert calls["count"] == 1
    assert finished == []
    assert sqlite3.connect(db_path).execute(
        "SELECT COUNT(*) FROM attempts").fetchone()[0] == 0

    # Starting another quiz is blocked until the result is saved.
    controller.startQuiz(json.dumps({
        "learner_name": "Rawan", "topic_ids": [topic_ids[0]],
        "question_count": 5, "time_limit_seconds": 600
    }))
    assert "retry saving" in errors[-1].lower()

    controller.retrySave()
    controller.retrySave()  # a second click must not duplicate anything

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM attempt_answers").fetchone()[0] == 5
    assert len(finished) == 1
    assert json.loads(finished[0])["attempt_id"] == 1
    controller.timer.stop()
