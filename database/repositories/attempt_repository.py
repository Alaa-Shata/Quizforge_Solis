from pathlib import Path
from typing import Optional, Sequence
from datetime import datetime, timezone

from database.connection import get_connection
from models.quiz import QuizConfig, QuizResult
from utils.errors import PersistenceError


class AttemptRepository:

    VALID_STATUSES = {"COMPLETED", "TIMED_OUT", "ABANDONED"}

    def __init__(self, connection_factory=get_connection):
        self.connection_factory = connection_factory

    def save_finished_attempt(
        self, *, config: QuizConfig, started_at: str,
        finished_at: str, result: QuizResult,
    ) -> int:
        """Persist a terminal attempt and all recorded answers atomically."""
        try:
            return type(self).save_attempt(
                learner_name=config.learner_name,
                started_at=started_at,
                finished_at=finished_at,
                status=result.status,
                question_count=config.question_count,
                earned_points=result.earned_points,
                max_points=result.max_points,
                answers=result.answers,
                connection_factory=self.connection_factory,
            )
        except Exception as exc:
            raise PersistenceError("Could not persist the quiz attempt.") from exc

    def get_question_usage_counts(self, question_ids: list[int]) -> dict[int, int]:
        ids = list(dict.fromkeys(int(question_id) for question_id in question_ids))
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        conn = self.connection_factory()
        try:
            rows = conn.execute(
                f"SELECT question_id, COUNT(*) AS used FROM attempt_answers "
                f"WHERE question_id IN ({placeholders}) GROUP BY question_id",
                ids,
            ).fetchall()
            counts = {int(row["question_id"]): int(row["used"]) for row in rows}
            return {question_id: counts.get(question_id, 0) for question_id in ids}
        finally:
            conn.close()

    @staticmethod
    def save_attempt(
        learner_name: str,
        started_at: str,
        finished_at: str,
        status: str,
        question_count: int,
        earned_points: int,
        max_points: int,
        answers: Sequence,
        db_path: Optional[str | Path] = None,
        connection_factory=None,
    ) -> int:

        status = status.upper()

        if status not in AttemptRepository.VALID_STATUSES:
            raise ValueError("Invalid attempt status.")

        if not learner_name.strip():
            raise ValueError("Learner name cannot be empty.")

        for label, value in (("started_at", started_at), ("finished_at", finished_at)):
            try:
                timestamp = datetime.fromisoformat(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{label} must be an ISO 8601 timestamp.") from exc
            if timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
                raise ValueError(f"{label} must be stored in UTC.")
        if datetime.fromisoformat(finished_at) < datetime.fromisoformat(started_at):
            raise ValueError("finished_at must not precede started_at.")

        if not 5 <= question_count <= 30:
            raise ValueError("Question count must be between 5 and 30.")

        if earned_points < 0 or max_points < 0:
            raise ValueError("Points cannot be negative.")

        if earned_points > max_points:
            raise ValueError("Earned points cannot exceed maximum points.")

        if len(answers) > question_count:
            raise ValueError("Answered questions cannot exceed question count.")

        if status == "COMPLETED" and len(answers) != question_count:
            raise ValueError("A completed attempt must contain all answers.")

        expected_maximum = sum(int(a.level_asked) for a in answers)
        expected_earned = sum(
            int(a.level_asked) for a in answers if a.is_correct
        )

        if max_points != expected_maximum:
            raise ValueError("Maximum points do not match the presented questions.")

        if earned_points != expected_earned:
            raise ValueError("Earned points do not match the submitted answers.")
        if any(a.chosen_option is None and a.is_correct for a in answers):
            raise ValueError("An unanswered question cannot be correct.")
        if len({a.question_id for a in answers}) != len(answers):
            raise ValueError("An attempt cannot contain duplicate questions.")
        if len({a.order_no for a in answers}) != len(answers):
            raise ValueError("An attempt cannot contain duplicate answer positions.")

        conn = connection_factory() if connection_factory else get_connection(db_path)

        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN")

            cursor.execute(
                """
                INSERT INTO attempts (
                    learner_name, started_at, finished_at, status,
                    question_count, earned_points, max_points
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_name.strip(), started_at, finished_at, status,
                    question_count, earned_points, max_points
                )
            )

            attempt_id = cursor.lastrowid

            answer_data = [
                (
                    attempt_id,
                    answer.question_id,
                    answer.order_no,
                    answer.level_asked,
                    answer.chosen_option,
                    int(answer.is_correct)
                )
                for answer in answers
            ]

            if answer_data:
                cursor.executemany(
                    """
                    INSERT INTO attempt_answers (
                        attempt_id, question_id, order_no,
                        level_asked, chosen_option, is_correct
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    answer_data
                )

            conn.commit()
            return attempt_id

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()
