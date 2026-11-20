import csv
import json
import sqlite3
import tempfile
from pathlib import Path
from repositories.question_repository import QuestionRepository
from services.question_service import QuestionService


def _create_isolated_service(db_path: Path) -> QuestionService:
    def _conn_factory() -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    conn = _conn_factory()
    try:
        with conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL REFERENCES topics(id),
                    text TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_option TEXT NOT NULL CHECK(correct_option IN ('A','B','C','D')),
                    difficulty INTEGER NOT NULL CHECK(difficulty IN (1,2,3)),
                    explanation TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS attempt_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL REFERENCES questions(id)
                );
                INSERT INTO topics (id, name) VALUES (1, 'Cybersecurity');
                """
            )
    finally:
        conn.close()

    repo = QuestionRepository(_conn_factory)
    return QuestionService(repo)


def _assert_raises(exc_type, fn, *args, **kwargs) -> None:
    try:
        fn(*args, **kwargs)
    except exc_type:
        return
    raise AssertionError(f"Expected {exc_type.__name__} to be raised.")


def test_question_workflow_and_edge_cases() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        service = _create_isolated_service(tmp_path / "test_quizforge.db")

        # 1. Create & Retrieve
        q1 = service.create_question(
            topic_id=1,
            text="What does CIA stand for in security?",
            options=(
                "Confidentiality, Integrity, Availability",
                "Control, Internet, Access",
                "Encryption, Decryption, Hashing",
                "Authentication, Authorization, Accounting",
            ),
            correct_option="A",
            difficulty=1,
            explanation="The CIA triad is the core security model.",
        )
        assert q1.id == 1
        assert len(service.list_questions(topic_id=1)) == 1

        # 2. Validation Edge Cases (duplicates, identical options, invalid answer)
        _assert_raises(
            ValueError,
            service.create_question,
            topic_id=1,
            text="  what   does cia stand for in security? ",
            options=("Opt 1", "Opt 2", "Opt 3", "Opt 4"),
            correct_option="A",
            difficulty=1,
            explanation="Duplicate normalized text should fail.",
        )
        _assert_raises(
            ValueError,
            service.create_question,
            topic_id=1,
            text="Unique question with duplicate options?",
            options=("Same", "same ", "Opt 3", "Opt 4"),
            correct_option="A",
            difficulty=1,
            explanation="Duplicate options should fail.",
        )
        _assert_raises(
            ValueError,
            service.create_question,
            topic_id=1,
            text="Unique question with invalid answer?",
            options=("Opt 1", "Opt 2", "Opt 3", "Opt 4"),
            correct_option="E",
            difficulty=1,
            explanation="Invalid correct_option should fail.",
        )

        # 3. Update & Soft Delete (Deactivate)
        updated = service.update_question(
            q1.id,
            topic_id=1,
            text="What does the CIA triad stand for?",
            options=(
                "Confidentiality, Integrity, Availability",
                "Control, Internet, Access",
                "Encryption, Decryption, Hashing",
                "Authentication, Authorization, Accounting",
            ),
            correct_option="A",
            difficulty=2,
            explanation="Updated explanation.",
        )
        assert updated.difficulty == 2
        assert updated.text == "What does the CIA triad stand for?"

        service.deactivate_question(q1.id)
        assert len(service.list_questions(topic_id=1, active_only=True)) == 0
        assert len(service.list_questions(topic_id=1, active_only=False)) == 1

        # 4. Preview & Commit Import (CSV with 1 valid row and 1 invalid row)
        csv_import_path = tmp_path / "import_sample.csv"
        with csv_import_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "topic",
                    "text",
                    "option_a",
                    "option_b",
                    "option_c",
                    "option_d",
                    "correct_option",
                    "difficulty",
                    "explanation",
                ]
            )
            writer.writerow(
                [
                    "Networking",
                    "Which layer handles IP routing?",
                    "Network",
                    "Physical",
                    "Session",
                    "Application",
                    "A",
                    "1",
                    "Layer 3 routes packets.",
                ]
            )
            writer.writerow(
                [
                    "Networking",
                    "Invalid row with bad answer",
                    "A1",
                    "B1",
                    "C1",
                    "D1",
                    "Z",
                    "1",
                    "Should be flagged in invalid_rows.",
                ]
            )

        preview = service.preview_import(str(csv_import_path))
        assert len(preview.valid_rows) == 1
        assert len(preview.invalid_rows) == 1
        inserted = service.commit_import(preview)
        assert inserted == 1

        # 5. Export CSV & JSON (verify no internal 'id' field is exported)
        csv_export_path = tmp_path / "exported.csv"
        json_export_path = tmp_path / "exported.json"

        csv_count = service.export_questions(str(csv_export_path), format="csv")
        json_count = service.export_questions(str(json_export_path), format="json")
        assert csv_count == 1
        assert json_count == 1

        with csv_export_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames is not None
            assert "id" not in reader.fieldnames
            exported_csv_rows = list(reader)
            assert len(exported_csv_rows) == 1

        exported_json_rows = json.loads(json_export_path.read_text(encoding="utf-8"))
        assert len(exported_json_rows) == 1
        assert "id" not in exported_json_rows[0]

    print("ALL M1 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_question_workflow_and_edge_cases()