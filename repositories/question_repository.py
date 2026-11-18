import sqlite3
from typing import List, Optional
from models.question import Question
from database.connection import get_connection

class QuestionRepository:
    @staticmethod
    def add_question(db_path: Optional[str] = None, *, topic_id: int, text: str, 
                     option_a: str, option_b: str, option_c: str, option_d: str, 
                     correct_option: str, difficulty: int, explanation: str = "") -> int:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO questions (topic_id, text, option_a, option_b, option_c, option_d, 
                                      correct_option, difficulty, explanation, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (topic_id, text, option_a, option_b, option_c, option_d, correct_option, difficulty, explanation))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_questions_by_topic(topic_id: int, db_path: Optional[str] = None) -> List[Question]:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, topic_id, text, option_a, option_b, option_c, option_d, 
                       correct_option, difficulty, explanation, is_active
                FROM questions
                WHERE topic_id = ? AND is_active = 1
            """, (topic_id,))
            rows = cursor.fetchall()
            return [
                Question(
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
                    is_active=bool(row["is_active"])
                )
                for row in rows
            ]
        finally:
            conn.close()