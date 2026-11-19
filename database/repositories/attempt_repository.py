from pathlib import Path
from typing import Optional, Sequence

from database.connection import get_connection


class AttemptRepository:

    VALID_STATUSES = {"COMPLETED", "TIMED_OUT", "ABANDONED"}

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
        db_path: Optional[str | Path] = None
    ) -> int:

        status = status.upper()

        if status not in AttemptRepository.VALID_STATUSES:
            raise ValueError("Invalid attempt status.")

        if not learner_name.strip():
            raise ValueError("Learner name cannot be empty.")

        if not 5 <= question_count <= 30:
            raise ValueError("Question count must be between 5 and 30.")

        if earned_points < 0 or max_points < 0:
            raise ValueError("Points cannot be negative.")

        conn = get_connection(db_path)

        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN")

            cursor.execute(
                """
                INSERT INTO attempts (
                    learner_name,
                    started_at,
                    finished_at,
                    status,
                    question_count,
                    earned_points,
                    max_points
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_name.strip(),
                    started_at,
                    finished_at,
                    status,
                    question_count,
                    earned_points,
                    max_points
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

            cursor.executemany(
                """
                INSERT INTO attempt_answers (
                    attempt_id,
                    question_id,
                    order_no,
                    level_asked,
                    chosen_option,
                    is_correct
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