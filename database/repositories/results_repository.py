from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from database.connection import get_connection

ConnectionFactory = Callable[[Any], sqlite3.Connection]


def _escape_like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class ResultsRepository:
    """Read-only SQLite queries for Module 4 (Dashboard & Results)."""

    def __init__(self, connection_factory: ConnectionFactory | None = None) -> None:
        self._connection_factory: ConnectionFactory = connection_factory or get_connection

    def _connect(self) -> sqlite3.Connection:
        conn = self._connection_factory(None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def get_active_question_count(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM questions WHERE is_active = 1"
            ).fetchone()
            return int(row["n"]) if row is not None else 0
        finally:
            conn.close()

    def get_attempt_count(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS n FROM attempts").fetchone()
            return int(row["n"]) if row is not None else 0
        finally:
            conn.close()

    def get_average_completed_score(self) -> float | None:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT AVG(100.0 * earned_points / max_points) AS avg_score
                FROM attempts
                WHERE status = 'COMPLETED'
                  AND max_points > 0
                """
            ).fetchone()
            if row is None or row["avg_score"] is None:
                return None
            return float(row["avg_score"])
        finally:
            conn.close()

    def list_topics(self) -> list[tuple[int, str]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, name
                FROM topics
                ORDER BY name COLLATE NOCASE ASC, id ASC
                """
            ).fetchall()
            return [(int(r["id"]), str(r["name"])) for r in rows]
        finally:
            conn.close()

    def list_attempt_rows(
        self,
        *,
        learner_name: str = "",
        topic_id: int | None = None,
        date_from_bound: str | None = None,
        date_to_exclusive_bound: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        cleaned_name = learner_name.strip().lower()
        if cleaned_name:
            clauses.append("LOWER(a.learner_name) LIKE ? ESCAPE '\\'")
            params.append(_escape_like(cleaned_name))

        if topic_id is not None:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM attempt_answers AS ax
                    JOIN questions AS qx ON qx.id = ax.question_id
                    WHERE ax.attempt_id = a.id
                      AND qx.topic_id = ?
                )
                """
            )
            params.append(int(topic_id))

        if date_from_bound is not None:
            clauses.append("a.started_at >= ?")
            params.append(date_from_bound)

        if date_to_exclusive_bound is not None:
            clauses.append("a.started_at < ?")
            params.append(date_to_exclusive_bound)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = " LIMIT ?" if limit is not None else ""
        if limit is not None:
            params.append(int(limit))

        sql = f"""
            SELECT
                a.id,
                a.learner_name,
                a.started_at,
                a.finished_at,
                a.status,
                a.question_count,
                a.earned_points,
                a.max_points,
                COUNT(aa.id) AS recorded_answer_count
            FROM attempts AS a
            LEFT JOIN attempt_answers AS aa
                ON aa.attempt_id = a.id
            {where_sql}
            GROUP BY a.id
            ORDER BY a.started_at DESC, a.id DESC
            {limit_sql}
        """

        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_attempt_summary_row(self, attempt_id: int) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT
                    a.id,
                    a.learner_name,
                    a.started_at,
                    a.finished_at,
                    a.status,
                    a.question_count,
                    a.earned_points,
                    a.max_points,
                    COUNT(aa.id) AS recorded_answer_count
                FROM attempts AS a
                LEFT JOIN attempt_answers AS aa
                    ON aa.attempt_id = a.id
                WHERE a.id = ?
                GROUP BY a.id
                """,
                (int(attempt_id),),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def get_attempt_answer_rows(self, attempt_id: int) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT
                    aa.order_no,
                    aa.question_id,
                    aa.level_asked,
                    aa.chosen_option,
                    aa.is_correct,
                    q.text,
                    q.option_a,
                    q.option_b,
                    q.option_c,
                    q.option_d,
                    q.correct_option,
                    q.explanation,
                    t.name AS topic_name
                FROM attempt_answers AS aa
                JOIN questions AS q ON q.id = aa.question_id
                JOIN topics AS t ON t.id = q.topic_id
                WHERE aa.attempt_id = ?
                ORDER BY aa.order_no ASC, aa.id ASC
                """,
                (int(attempt_id),),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_topic_accuracy_rows(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT
                    t.id AS topic_id,
                    t.name AS topic_name,
                    COUNT(aa.id) AS total_count,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN aa.is_correct = 1 AND aa.chosen_option IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS correct_count
                FROM topics AS t
                LEFT JOIN questions AS q
                    ON q.topic_id = t.id
                LEFT JOIN attempt_answers AS aa
                    ON aa.question_id = q.id
                   AND aa.attempt_id IN (
                       SELECT id FROM attempts WHERE status = 'COMPLETED'
                   )
                GROUP BY t.id, t.name
                ORDER BY t.name COLLATE NOCASE ASC, t.id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_level_path_rows(self, attempt_id: int) -> list[tuple[int, int]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT order_no, level_asked
                FROM attempt_answers
                WHERE attempt_id = ?
                ORDER BY order_no ASC, id ASC
                """,
                (int(attempt_id),),
            ).fetchall()
            return [(int(r["order_no"]), int(r["level_asked"])) for r in rows]
        finally:
            conn.close()