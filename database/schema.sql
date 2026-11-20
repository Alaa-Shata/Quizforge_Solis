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
