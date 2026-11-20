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
    topic_names = ["Cybersecurity", "Networking", "Python"]
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


def build_questions(topic_ids: dict[str, int]) -> list[tuple]:
    questions: list[tuple] = []
    options = ["A", "B", "C", "D"]

    # 30 questions per topic * 3 topics = 90 questions
    for topic_name, topic_id in topic_ids.items():
        for idx in range(1, 31):
            difficulty = ((idx - 1) % 3) + 1  # 1, 2, 3 rotating
            correct = options[idx % 4]

            if topic_name == "Cybersecurity":
                q_text = f"[Cybersecurity #{idx}] Which security control or concept applies to scenario {idx}?"
                a, b, c, d = (
                    "Access Control & Least Privilege",
                    "TLS/SSL Encryption",
                    "Input Validation & Sanitization",
                    "Audit Logging & Monitoring",
                )
                exp = f"Cybersecurity reference explanation for item #{idx} (level {difficulty})."

            elif topic_name == "Networking":
                q_text = f"[Networking #{idx}] Which networking protocol, layer, or mechanism matches case {idx}?"
                a, b, c, d = (
                    "TCP Reliable Transport",
                    "IP Network Routing",
                    "DNS Name Resolution",
                    "VLAN Segmentation",
                )
                exp = f"Networking reference explanation for item #{idx} (level {difficulty})."

            else:  # Python
                q_text = f"[Python #{idx}] Which Python feature, structure, or behavior fits case {idx}?"
                a, b, c, d = (
                    "List Comprehension & Indexing",
                    "Dictionary Key-Value Lookup",
                    "Context Manager ('with')",
                    "Exception Handling ('try/except')",
                )
                exp = f"Python reference explanation for item #{idx} (level {difficulty})."

            questions.append((topic_id, q_text, a, b, c, d, correct, difficulty, exp))

    return questions


def seed_questions(topic_ids: dict[str, int]) -> int:
    conn = get_connection()
    existing_count = conn.execute("SELECT COUNT(*) AS cnt FROM questions").fetchone()["cnt"]
    conn.close()

    if existing_count >= 90:
        return existing_count

    all_questions = build_questions(topic_ids)
    added = 0
    for item in all_questions:
        QuestionService.add_new_question(*item)
        added += 1

    return added


if __name__ == "__main__":
    init_db()
    t_ids = ensure_topics()
    count = seed_questions(t_ids)
    print(f"Seed finished. Topics: {t_ids} | Inserted/Total questions: {count}")