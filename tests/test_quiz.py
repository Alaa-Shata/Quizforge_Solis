from types import SimpleNamespace

import pytest

from services.quiz_service import QuizService, QuizConfig
from utils.errors import InsufficientQuestionsError, ValidationError


def create_questions(count=5):
    levels = [1, 2, 3, 1, 2, 3, 2, 1]
    return [
        SimpleNamespace(
            id=i + 1,
            topic_id=1,
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


class FixtureQuestionService:
    def __init__(self, questions):
        self.questions = list(questions)

    def list_questions(self, *, topic_id=None, active_only=True, **_filters):
        return [
            question for question in self.questions
            if (topic_id is None or question.topic_id == topic_id)
            and (not active_only or question.is_active)
        ]


def make_service(questions=None, clock=None):
    return QuizService(
        FixtureQuestionService(questions if questions is not None else create_questions()),
        clock=clock,
    )


def test_start_quiz():
    service = make_service()
    first = service.start(create_config())

    assert first.difficulty == 2
    assert service.is_active
    assert service.engine.level == 2
    assert service.get_state().total_questions == 5


def test_setup_rejects_insufficient_pool_before_starting_session():
    service = make_service(create_questions(4))
    with pytest.raises(InsufficientQuestionsError):
        service.start(create_config())
    assert not service.is_active
    assert service.get_state().phase == "SETUP"


def test_time_limit_bounds_are_validated():
    service = make_service()
    with pytest.raises(ValidationError):
        service.validate_setup(QuizConfig("Rawan", (1,), 5, 59))
    with pytest.raises(ValidationError):
        service.validate_setup(QuizConfig("Rawan", (1,), 5, 7201))


def test_submit_correct_answer():
    service = make_service()
    service.start(create_config())

    feedback = service.submit_answer("A")

    assert feedback.is_correct
    assert feedback.correct_option == "A"
    assert len(service.answers) == 1


def test_invalid_answer():
    service = make_service()
    service.start(create_config())

    with pytest.raises(ValueError):
        service.submit_answer("X")


def test_cannot_move_without_answering():
    service = make_service()
    service.start(create_config())

    with pytest.raises(RuntimeError):
        service.next_question()


def test_adaptive_engine_moves_to_hard_after_two_correct():
    service = make_service()
    service.start(create_config())

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
            explanation="", is_active=True, topic_id=1
        )
        for i in range(5)
    ]

    service = make_service(questions)
    service.start(create_config())

    service.submit_answer("B")
    service.next_question()

    service.submit_answer("B")
    next_q = service.next_question()

    assert service.engine.level == 1
    assert next_q.difficulty == 2  # nearest available level


def test_questions_are_not_repeated():
    service = make_service()
    service.start(create_config())

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
            explanation="", is_active=True, topic_id=1
        )
        for i, level in enumerate([1, 2, 3, 1, 2])
    ]

    service = make_service(questions)
    service.start(create_config())

    for index in range(5):
        service.submit_answer("A")
        if index < 4:
            service.next_question()

    assert service.is_active
    assert service.get_result() is None
    result = service.finish()

    assert result.earned_points == 9
    assert result.max_points == 9
    assert result.score_percent == 100


def test_last_answer_waits_for_explicit_finish_action():
    service = make_service()
    service.start(create_config())

    for index in range(5):
        service.submit_answer("A")
        if index < 4:
            service.next_question()

    assert service.is_active is True
    assert service.get_result() is None
    with pytest.raises(ValidationError, match="Finish Quiz"):
        service.next_question()

    result = service.finish()
    assert result.status == "COMPLETED"
    assert service.is_finished is True


def test_timer_countdown():
    current_time = [100]
    service = make_service(clock=lambda: current_time[0])
    service.start(create_config())

    assert service.get_remaining_seconds() == 60

    current_time[0] += 20
    assert service.get_remaining_seconds() == 40


def test_timeout_records_distinct_unanswered_questions_to_requested_count():
    current_time = [100]
    service = make_service(clock=lambda: current_time[0])
    service.start(create_config())

    service.submit_answer("A")
    service.next_question()

    current_time[0] += 61
    assert service.get_remaining_seconds() == 0

    result = service.get_result()

    assert result.status == "TIMED_OUT"
    assert len(result.answers) == 5
    assert sum(a.chosen_option is None for a in result.answers) == 4
    assert len({a.question_id for a in result.answers}) == 5
    assert [a.order_no for a in result.answers] == [1, 2, 3, 4, 5]


def test_timeout_at_deadline_wins_over_late_submission():
    current_time = [10]
    service = make_service(clock=lambda: current_time[0])
    service.start(create_config())

    current_time[0] += 60
    with pytest.raises(RuntimeError):
        service.submit_answer("A")

    result = service.get_result()
    assert result.status == "TIMED_OUT"
    assert len(result.answers) == 5
    assert all(answer.chosen_option is None for answer in result.answers)
    assert service.finish_timeout() is result


def test_timeout_during_feedback_preserves_submitted_answer_and_fills_rest():
    current_time = [10]
    service = make_service(clock=lambda: current_time[0])
    service.start(create_config())
    service.submit_answer("A")
    service.next_question()

    current_time[0] = service.deadline
    result = service.finish_timeout()

    assert result.status == "TIMED_OUT"
    assert len(result.answers) == 5
    assert result.answers[0].chosen_option == "A"
    assert sum(answer.chosen_option is None for answer in result.answers) == 4
    assert len({answer.question_id for answer in result.answers}) == 5


def test_session_state_tracks_phase_and_presented_count():
    service = make_service()
    service.start(create_config())
    state = service.get_state()
    assert state.phase == "QUESTION"
    assert state.presented_count == 1
    assert state.can_submit
    assert not state.can_advance

    service.submit_answer("A")
    state = service.get_state()
    assert state.phase == "FEEDBACK"
    assert state.submitted_count == 1
    assert state.can_advance


def test_nine_available_questions_finish_without_repeats():
    config = QuizConfig("Rawan", (1,), 9, 600)
    service = make_service(create_questions(9))
    service.start(config)
    seen = {service.questions[0].id}

    for index in range(9):
        service.submit_answer("A")
        if index < 8:
            question = service.next_question()
            assert question is not None
            assert question.id not in seen
            seen.add(question.id)

    assert len(seen) == 9
    assert service.is_active
    assert service.get_result() is None
    service.finish()
    assert service.get_result().status == "COMPLETED"


def test_abandon_quiz():
    service = make_service()
    service.start(create_config())

    service.submit_answer("A")
    result = service.abandon()

    assert result.status == "ABANDONED"
    assert len(result.answers) == 1
    assert not service.is_active
    assert service.is_finished


def test_abandon_current_unanswered_question():
    service = make_service()
    service.start(create_config())

    result = service.abandon()

    assert result.status == "ABANDONED"
    assert len(result.answers) == 1
    assert result.answers[0].chosen_option is None


def test_restart_after_finished_session():
    service = make_service()
    service.start(create_config())
    service.abandon()

    first = service.start(create_config())

    assert first.difficulty == 2
    assert service.is_active
    assert len(service.answers) == 0
