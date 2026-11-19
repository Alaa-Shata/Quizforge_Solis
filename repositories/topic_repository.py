from pathlib import Path
from typing import Optional

from database.connection import get_connection


class TopicRepository:

    @staticmethod
    def get_all_topics(
        db_path: Optional[str | Path] = None
    ) -> list[dict]:

        conn = get_connection(db_path)

        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name
                FROM topics
                ORDER BY name
            """)

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "name": row["name"]
                }
                for row in rows
            ]

        finally:
            conn.close()