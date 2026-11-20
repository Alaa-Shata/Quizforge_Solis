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

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

def init_db(db_path: str | Path | None = None) -> None:
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
