from types import SimpleNamespace

import pytest

from services.quiz_service import QuizService, QuizConfig


def create_questions(count=5):
    questions = []

    for i in range(count):
        question = SimpleNamespace(
            id=i + 1,
            difficulty=2,
            correct_option="A",
            explanation=f"Explanation {i + 1}",
        )

        questions.append(question)

    return questions


def create_config():
    return QuizConfig(
        learner_name="Rawan",
        topic_ids=(1,),
        question_count=5,
        time_limit_seconds=60,
    )


def test_start_quiz():
    service = QuizService()

    first_question = service.start(
        create_config(),
        create_questions()
    )

    assert first_question.id == 1
    assert service.is_active is True
    assert service.get_state().total_questions == 5


def test_submit_correct_answer():
    service = QuizService()

    service.start(create_config(), create_questions())

    feedback = service.submit_answer("A")

    assert feedback.is_correct is True
    assert feedback.correct_option == "A"
    assert len(service.answers) == 1


def test_submit_wrong_answer():
    service = QuizService()

    service.start(create_config(), create_questions())

    feedback = service.submit_answer("B")

    assert feedback.is_correct is False


def test_cannot_move_without_answering():
    service = QuizService()

    service.start(create_config(), create_questions())

    with pytest.raises(RuntimeError):
        service.next_question()


def test_timer_countdown():
    current_time = [100]

    service = QuizService(clock=lambda: current_time[0])

    service.start(create_config(), create_questions())

    assert service.get_remaining_seconds() == 60

    current_time[0] += 20

    assert service.get_remaining_seconds() == 40


def test_timer_timeout():
    current_time = [100]

    service = QuizService(clock=lambda: current_time[0])

    service.start(create_config(), create_questions())

    current_time[0] += 61

    remaining = service.get_remaining_seconds()

    assert remaining == 0
    assert service.is_active is False
    assert service.is_finished is True
    assert service.get_result().status == "TIMED_OUT"


def test_complete_quiz_session():
    service = QuizService()

    questions = create_questions(5)

    first_question = service.start(
        create_config(),
        questions
    )

    assert first_question.id == 1

    # Answer all five questions
    for i in range(5):
        feedback = service.submit_answer("A")

        assert feedback.is_correct is True

        next_question = service.next_question()

        if i < 4:
            assert next_question is not None
        else:
            assert next_question is None

    # Finish the quiz
    result = service.finish()

    assert result.status == "COMPLETED"
    assert result.earned_points == 5
    assert result.max_points == 5
    assert result.score_percent == 100

    assert service.is_active is False
    assert service.is_finished is True


def test_abandon_quiz():
    service = QuizService()

    service.start(
        create_config(),
        create_questions()
    )

    service.submit_answer("A")

    result = service.abandon()

    assert result.status == "ABANDONED"
    assert len(result.answers) == 1
    assert service.is_active is False
    assert service.is_finished is True