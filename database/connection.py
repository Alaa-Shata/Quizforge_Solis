"""Canonical SQLite connection factory and schema initializer."""

import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        root_dir = Path(__file__).resolve().parent.parent
        data_dir = root_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "quizforge.db"
    else:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        connection.close()
        raise sqlite3.DatabaseError("Could not enable SQLite foreign keys.")
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    connection = get_connection(db_path)
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    try:
        if not schema_path.is_file():
            raise FileNotFoundError(f"Database schema not found: {schema_path}")
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
    print("QuizForge database initialized.")
