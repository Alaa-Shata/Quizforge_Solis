from database.connection import init_db, get_connection
from services.question_service import QuestionService
def test_question_workflow():
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO topics (id, name) VALUES (1, 'Cybersecurity');")
    conn.commit()
    conn.close()
    q_id = QuestionService.add_new_question(
        topic_id=1,
        text="What is a firewall in cybersecurity?",
        option_a="Confidentiality, Integrity, Availability",
        option_b="Control, Internet, Access",
        option_c="Encryption, Decryption, Hashing",
        option_d="None of the above",
        correct_option="A",
        difficulty=1,
        explanation="The CIA triad is a foundational model in cybersecurity."
    )
    print(f"تم إضافة السؤال بنجاح، وتحمل الـ ID رقم: {q_id}")

    questions = QuestionService.get_questions_for_topic(1)
    print(f"عدد الأسئلة المسترجعة للموضوع: {len(questions)}")
    for q in questions:
        print(f"- السؤال: {q.text} | الإجابة الصحيحة: {q.correct_option}")

if __name__ == "__main__":
    test_question_workflow()