from types import SimpleNamespace

import pytest

from services.quiz_service import QuizService, QuizConfig


def create_questions(count=5):
    levels = [1, 2, 3, 1, 2, 3, 2, 1]
    return [
        SimpleNamespace(
            id=i + 1,
            difficulty=levels[i % len(levels)],
            correct_option="A",
            explanation=f"Explanation {i + 1}",
            is_active=True
        )
        for i in range(count)
    ]


def create_config():
    return QuizConfig(
        learner_name="Rawan",
        topic_ids=(1,),
        question_count=5,
        time_limit_seconds=60
    )


def test_start_quiz():
    service = QuizService()
    first = service.start(create_config(), create_questions())

    assert first.difficulty == 2
    assert service.is_active
    assert service.engine.level == 2
    assert service.get_state().total_questions == 5


def test_submit_correct_answer():
    service = QuizService()
    service.start(create_config(), create_questions())

    feedback = service.submit_answer("A")

    assert feedback.is_correct
    assert feedback.correct_option == "A"
    assert len(service.answers) == 1


def test_invalid_answer():
    service = QuizService()
    service.start(create_config(), create_questions())

    with pytest.raises(ValueError):
        service.submit_answer("X")


def test_cannot_move_without_answering():
    service = QuizService()
    service.start(create_config(), create_questions())

    with pytest.raises(RuntimeError):
        service.next_question()


def test_adaptive_engine_moves_to_hard_after_two_correct():
    service = QuizService()
    service.start(create_config(), create_questions())

    service.submit_answer("A")
    service.next_question()

    service.submit_answer("A")
    next_q = service.next_question()

    assert service.engine.level == 3
    assert next_q.difficulty == 3


def test_adaptive_engine_moves_to_easy_after_two_wrong():
    questions = [
        SimpleNamespace(
            id=i + 1, difficulty=2, correct_option="A",
            explanation="", is_active=True
        )
        for i in range(5)
    ]

    service = QuizService()
    service.start(create_config(), questions)

    service.submit_answer("B")
    service.next_question()

    service.submit_answer("B")
    next_q = service.next_question()

    assert service.engine.level == 1
    assert next_q.difficulty == 2  # nearest available level


def test_questions_are_not_repeated():
    service = QuizService()
    service.start(create_config(), create_questions())

    seen = {service.questions[0].id}

    for _ in range(4):
        service.submit_answer("A")
        question = service.next_question()

        if question is not None:
            assert question.id not in seen
            seen.add(question.id)

    assert len(seen) == 5


def test_weighted_scoring():
    questions = [
        SimpleNamespace(
            id=i + 1, difficulty=level, correct_option="A",
            explanation="", is_active=True
        )
        for i, level in enumerate([1, 2, 3, 1, 2])
    ]

    service = QuizService()
    service.start(create_config(), questions)

    for _ in range(5):
        service.submit_answer("A")
        service.next_question()

    result = service.finish()

    assert result.earned_points == 9
    assert result.max_points == 9
    assert result.score_percent == 100


def test_timer_countdown():
    current_time = [100]
    service = QuizService(clock=lambda: current_time[0])
    service.start(create_config(), create_questions())

    assert service.get_remaining_seconds() == 60

    current_time[0] += 20
    assert service.get_remaining_seconds() == 40


def test_timeout_records_only_presented_questions():
    current_time = [100]
    service = QuizService(clock=lambda: current_time[0])
    service.start(create_config(), create_questions())

    service.submit_answer("A")
    service.next_question()

    current_time[0] += 61
    assert service.get_remaining_seconds() == 0

    result = service.get_result()

    assert result.status == "TIMED_OUT"
    assert len(result.answers) == 2
    assert sum(a.chosen_option is None for a in result.answers) == 1


def test_abandon_quiz():
    service = QuizService()
    service.start(create_config(), create_questions())

    service.submit_answer("A")
    result = service.abandon()

    assert result.status == "ABANDONED"
    assert len(result.answers) == 1
    assert not service.is_active
    assert service.is_finished


def test_abandon_current_unanswered_question():
    service = QuizService()
    service.start(create_config(), create_questions())

    result = service.abandon()

    assert result.status == "ABANDONED"
    assert len(result.answers) == 1
    assert result.answers[0].chosen_option is None


def test_restart_after_finished_session():
    service = QuizService()
    service.start(create_config(), create_questions())
    service.abandon()

    first = service.start(create_config(), create_questions())

    assert first.difficulty == 2
    assert service.is_active
    assert len(service.answers) == 0
