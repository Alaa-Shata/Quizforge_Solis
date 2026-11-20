import sqlite3
from typing import Callable, Dict, List, Optional, Tuple
from database.connection import get_connection
from models.question import Question


class QuestionRepository:
    def __init__(self, connection_factory: Callable[[], sqlite3.Connection] = get_connection) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _row_to_question(row: sqlite3.Row) -> Question:
        return Question(
            id=row["id"],
            topic_id=row["topic_id"],
            text=row["text"],
            option_a=row["option_a"],
            option_b=row["option_b"],
            option_c=row["option_c"],
            option_d=row["option_d"],
            correct_option=row["correct_option"],
            difficulty=row["difficulty"],
            explanation=row["explanation"],
            is_active=bool(row["is_active"]),
        )

    def list_topics(self) -> List[Tuple[int, str]]:
        conn = self._connection_factory()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM topics ORDER BY id ASC")
            rows = cursor.fetchall()
            return [(int(row["id"]), str(row["name"])) for row in rows]
        finally:
            conn.close()

    def get_topic_by_name(self, name: str) -> Optional[Tuple[int, str]]:
        conn = self._connection_factory()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM topics WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (name,))
            row = cursor.fetchone()
            if row is None:
                return None
            return (int(row["id"]), str(row["name"]))
        finally:
            conn.close()

    def create_topic(self, name: str) -> Tuple[int, str]:
        clean_name = " ".join(name.strip().split())
        conn = self._connection_factory()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO topics (name) VALUES (?)", (clean_name,))
                topic_id = int(cursor.lastrowid)
            return (topic_id, clean_name)
        finally:
            conn.close()

    def get_by_id(self, question_id: int) -> Optional[Question]:
        conn = self._connection_factory()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, topic_id, text, option_a, option_b, option_c, option_d,
                       correct_option, difficulty, explanation, is_active
                FROM questions
                WHERE id = ?
                """,
                (question_id,),
            )
            row = cursor.fetchone()
            return self._row_to_question(row) if row is not None else None
        finally:
            conn.close()

    def list_questions(
        self,
        *,
        topic_id: Optional[int] = None,
        difficulty: Optional[int] = None,
        search_text: str = "",
        active_only: bool = True,
    ) -> List[Question]:
        clauses: List[str] = []
        params: List[object] = []

        if active_only:
            clauses.append("is_active = 1")
        if topic_id is not None:
            clauses.append("topic_id = ?")
            params.append(topic_id)
        if difficulty is not None:
            clauses.append("difficulty = ?")
            params.append(difficulty)
        if search_text.strip():
            clauses.append("LOWER(text) LIKE LOWER(?)")
            params.append(f"%{search_text.strip()}%")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT id, topic_id, text, option_a, option_b, option_c, option_d,
                   correct_option, difficulty, explanation, is_active
            FROM questions
            {where_sql}
            ORDER BY id ASC
        """

        conn = self._connection_factory()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_question(row) for row in rows]
        finally:
            conn.close()

    def has_normalized_duplicate(
        self,
        topic_id: int,
        normalized_text: str,
        exclude_question_id: Optional[int] = None,
    ) -> bool:
        sql = """
            SELECT id, text
            FROM questions
            WHERE topic_id = ?
        """
        params: List[object] = [topic_id]
        if exclude_question_id is not None:
            sql += " AND id != ?"
            params.append(exclude_question_id)

        conn = self._connection_factory()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            target = " ".join(normalized_text.strip().split()).casefold()
            for row in rows:
                existing = " ".join(str(row["text"]).strip().split()).casefold()
                if existing == target:
                    return True
            return False
        finally:
            conn.close()

    def is_referenced_by_attempts(self, question_id: int) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM attempt_answers WHERE question_id = ? LIMIT 1",
                (question_id,),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def create_question(
        self,
        *,
        topic_id: int,
        text: str,
        options: Tuple[str, str, str, str],
        correct_option: str,
        difficulty: int,
        explanation: str,
    ) -> Question:
        option_a, option_b, option_c, option_d = options
        conn = self._connection_factory()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO questions (
                        topic_id, text, option_a, option_b, option_c, option_d,
                        correct_option, difficulty, explanation, is_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        topic_id,
                        text,
                        option_a,
                        option_b,
                        option_c,
                        option_d,
                        correct_option,
                        difficulty,
                        explanation,
                    ),
                )
                new_id = int(cursor.lastrowid)
            created = self.get_by_id(new_id)
            if created is None:
                raise RuntimeError("Failed to load created question.")
            return created
        finally:
            conn.close()

    def create_questions_bulk(self, records: List[Dict[str, object]]) -> int:
        conn = self._connection_factory()
        try:
            inserted_count = 0
            with conn:
                cursor = conn.cursor()
                for rec in records:
                    topic_id = int(rec["topic_id"])  # type: ignore[arg-type]
                    text = str(rec["text"])
                    options = rec["options"]  # type: ignore[assignment]
                    option_a, option_b, option_c, option_d = options
                    correct_option = str(rec["correct_option"])
                    difficulty = int(rec["difficulty"])  # type: ignore[arg-type]
                    explanation = str(rec["explanation"])

                    cursor.execute(
                        """
                        INSERT INTO questions (
                            topic_id, text, option_a, option_b, option_c, option_d,
                            correct_option, difficulty, explanation, is_active
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            topic_id,
                            text,
                            option_a,
                            option_b,
                            option_c,
                            option_d,
                            correct_option,
                            difficulty,
                            explanation,
                        ),
                    )
                    inserted_count += 1
            return inserted_count
        finally:
            conn.close()

    def update_question(
        self,
        question_id: int,
        *,
        topic_id: int,
        text: str,
        options: Tuple[str, str, str, str],
        correct_option: str,
        difficulty: int,
        explanation: str,
    ) -> Question:
        option_a, option_b, option_c, option_d = options
        conn = self._connection_factory()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE questions
                    SET topic_id = ?, text = ?, option_a = ?, option_b = ?,
                        option_c = ?, option_d = ?, correct_option = ?,
                        difficulty = ?, explanation = ?
                    WHERE id = ?
                    """,
                    (
                        topic_id,
                        text,
                        option_a,
                        option_b,
                        option_c,
                        option_d,
                        correct_option,
                        difficulty,
                        explanation,
                        question_id,
                    ),
                )
            updated = self.get_by_id(question_id)
            if updated is None:
                raise RuntimeError("Failed to load updated question.")
            return updated
        finally:
            conn.close()

    def deactivate_question(self, question_id: int) -> None:
        conn = self._connection_factory()
        try:
            with conn:
                conn.execute(
                    "UPDATE questions SET is_active = 0 WHERE id = ?",
                    (question_id,),
                )
        finally:
            conn.close()