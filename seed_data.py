from pathlib import Path
from database.connection import get_connection
from services.question_service import QuestionService


def init_db() -> None:
    conn = get_connection()
    schema_path = Path("database/schema.sql")
    with conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.close()


def ensure_topics() -> dict[str, int]:
    conn = get_connection()
    topic_names = ["Cybersecurity", "Networking", "Python", "Databases"]
    topic_ids: dict[str, int] = {}

    with conn:
        for name in topic_names:
            row = conn.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()
            if row:
                topic_ids[name] = row["id"]
            else:
                cur = conn.execute("INSERT INTO topics (name) VALUES (?)", (name,))
                topic_ids[name] = cur.lastrowid

    conn.close()
    return topic_ids


def seed_questions(topic_ids: dict[str, int]) -> None:
    conn = get_connection()
    existing_count = conn.execute("SELECT COUNT(*) AS cnt FROM questions").fetchone()["cnt"]
    conn.close()

    if existing_count > 0:
        return

    sample_questions = [
        (
            topic_ids["Cybersecurity"],
            "Which protocol encrypts web traffic between browser and server?",
            "HTTP",
            "HTTPS",
            "FTP",
            "SMTP",
            "B",
            1,
            "HTTPS uses TLS/SSL to encrypt HTTP traffic.",
        ),
        (
            topic_ids["Cybersecurity"],
            "What type of attack involves injecting malicious SQL statements into an entry field?",
            "Cross-Site Scripting (XSS)",
            "SQL Injection",
            "Brute Force",
            "Man-in-the-Middle",
            "B",
            2,
            "SQL Injection exploits improper input sanitization in database queries.",
        ),
        (
            topic_ids["Networking"],
            "Which layer of the OSI model handles IP routing?",
            "Data Link",
            "Transport",
            "Network",
            "Session",
            "C",
            2,
            "Layer 3 (Network layer) handles logical addressing and routing.",
        ),
        (
            topic_ids["Networking"],
            "What is the default port number for SSH?",
            "21",
            "22",
            "23",
            "80",
            "B",
            1,
            "SSH operates by default on TCP port 22.",
        ),
        (
            topic_ids["Python"],
            "Which built-in data type stores unique elements in Python?",
            "list",
            "tuple",
            "set",
            "dict",
            "C",
            1,
            "A set stores unique unordered elements.",
        ),
        (
            topic_ids["Python"],
            "What does the 'with' statement ensure when working with files or connections?",
            "Faster execution speed",
            "Automatic resource cleanup and closing",
            "Parallel threading",
            "Global variable scope",
            "B",
            2,
            "Context managers ensure proper setup and teardown of resources.",
        ),
        (
            topic_ids["Databases"],
            "Which SQL clause filters grouped rows after GROUP BY?",
            "WHERE",
            "HAVING",
            "ORDER BY",
            "DISTINCT",
            "B",
            2,
            "HAVING filters aggregated groups created by GROUP BY.",
        ),
        (
            topic_ids["Databases"],
            "Which constraint uniquely identifies each record in a database table?",
            "FOREIGN KEY",
            "CHECK",
            "PRIMARY KEY",
            "INDEX",
            "C",
            1,
            "A PRIMARY KEY uniquely identifies each row and cannot be NULL.",
        ),
    ]

    for item in sample_questions:
        QuestionService.add_new_question(*item)


if __name__ == "__main__":
    init_db()
    t_ids = ensure_topics()
    seed_questions(t_ids)
    print("Seed completed successfully. Topics:", t_ids)