CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE RESTRICT,
    text TEXT NOT NULL COLLATE NOCASE,
    option_a TEXT NOT NULL, 
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL, 
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL CHECK(correct_option IN ('A','B','C','D')),
    difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 3),
    explanation TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    UNIQUE(topic_id, text)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY,
    learner_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('COMPLETED','TIMED_OUT','ABANDONED')),
    question_count INTEGER NOT NULL CHECK(question_count BETWEEN 5 AND 30),
    earned_points INTEGER NOT NULL DEFAULT 0 CHECK(earned_points >= 0),
    max_points INTEGER NOT NULL DEFAULT 0 CHECK(max_points >= 0)
);

CREATE TABLE IF NOT EXISTS attempt_answers (
    id INTEGER PRIMARY KEY,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
    order_no INTEGER NOT NULL CHECK(order_no >= 1),
    level_asked INTEGER NOT NULL CHECK(level_asked BETWEEN 1 AND 3),
    chosen_option TEXT CHECK(chosen_option IN ('A','B','C','D') OR chosen_option IS NULL),
    is_correct INTEGER NOT NULL CHECK(is_correct IN (0,1)),
    UNIQUE(attempt_id, question_id),
    UNIQUE(attempt_id, order_no)
);

CREATE INDEX IF NOT EXISTS idx_questions_filter ON questions(topic_id, difficulty, is_active);
CREATE INDEX IF NOT EXISTS idx_answers_question ON attempt_answers(question_id);
```[cite: 5]

---

### الخطوة 4: إنشاء ملف الاتصال الموحد (`database/connection.py`)
1. داخل مجلد `database` أيضاً، أنشئي ملفاً جديداً باسم `connection.py`.
2. ضعي بداخله الكود المطابق للمعيار الموحد (§15) والذي يضمن إنشاء ملف `quizforge.db` داخل مجلد `data/` وتفعيل قيود المفاتيح الخارجية لكل اتصال[cite: 5]:

```python
import sqlite3
from pathlib import Path

def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """إنشاء وإرجاع اتصال بقاعدة بيانات SQLite مع تفعيل المفاتيح الخارجية"""
    if db_path is None:
        root_dir = Path(__file__).resolve().parent.parent
        data_dir = root_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "quizforge.db"
    else:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

def init_db(db_path: str | Path | None = None) -> None:
    """تهيئة قاعدة البيانات وإنشاء الجداول من ملف الschema.sql"""
    conn = get_connection(db_path)
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    else:
        raise FileNotFoundError(f"ملف الـ schema غير موجود في المسار: {schema_path}")
    
    conn.close()

if __name__ == "__main__":
    init_db()
    print("تم إنشاء قاعدة البيانات وجداول النظام الموحدة بنجاح تام! ✅")
```[cite: 5]

---

### الخطوة 5: ربط المشروع بـ GitHub وإنشاء البرانش الخاص بكِ (`feature/m1-question-bank`)
لتفادي أي Conflicts مع التيم، سنتبع الخطوات الاحترافية للتعامل مع الـ Git:

1. **تهيئة مستودع الـ Git محلياً:**
   في الـ Terminal، اكتبي:
   ```bash
   git init