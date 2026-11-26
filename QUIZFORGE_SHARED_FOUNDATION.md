# QUIZFORGE — SHARED FOUNDATION
Version 2.1 — IMPLEMENTATION BASELINE; project owner directed implementation on 2026-11-27. Team review remains open; no teammate approval is implied.
Team: Jana — M1 Question Bank; Rawan — M2 Quiz Session; Alaa — M3 Adaptive Engine & Scoring; Menna — M4 Results & Analytics.

SOURCE: Python GUI Project Catalog 2026, Project 06, and common technical/submission requirements.
RULE: University requirements are mandatory. Decisions labeled TEAM DECISION are proposed implementation choices; they are not explicitly prescribed by the catalog.

## 1. Project invariants
- Python 3.11 (TEAM DECISION within allowed 3.11/3.12; all members use identical minor version).
- PySide6, SQLite through sqlite3, matplotlib FigureCanvasQTAgg, pytest. Offline only.
- Exactly ONE QMainWindow, ONE sidebar, ONE QStackedWidget containing exactly FOUR main screens. Dialogs are allowed.
- S1 Dashboard (Menna); S2 Question Bank Editor (Jana); S3 Quiz Session (Rawan); S4 Results & Analytics (Menna).
- M3 is a pure Python engine (Alaa); it does not create a fifth screen.
- Layering: UI -> Services -> Repositories -> SQLite. QuizService -> AdaptiveEngine. No SQL in widgets; no Qt/SQL in algorithms.
- Validate in services and GUI. Parameterized SQL only. Foreign keys enabled for EVERY SQLite connection.
- Automatically create database from database/schema.sql on first run.
- At least one free-text search and another filter; at least one embedded database-driven chart.
- Import preview with row errors; atomic confirmed import; CSV/JSON question bank import/export; attempts CSV export.
- At least five passing pytest tests, target all six catalog tests; two or more algorithm tests.
- Log unexpected exceptions; present user-friendly errors. Use worker or busy indicator for operations >~0.5s.
- At least 90 explained MCQs (3 topics x 3 levels x 10), 10 completed sample attempts from 3 fictional names.

## 2. Module ownership
| Member | Module | Requirements | Owned implementation |
|---|---|---|---|
| Jana | M1 Question Bank | FR-01, FR-02 | question editor, CRUD, validation, import/export |
| Rawan | M2 Quiz Session | FR-03, FR-04 | setup, question flow, timer, feedback, timeout/abandon |
| Alaa | M3 Adaptation & Scoring | FR-05, FR-06 | deterministic selection, state machine, weighted scoring, algorithm tests |
| Menna | M4 Results & Analytics | FR-07, FR-08 | dashboard, history, review, charts, CSV export |

Shared files (main window, models, schema, connection, requirements) require a designated integration owner and review from affected members. No unilateral edits.

**Current work authorization:** On 2026-11-27 the project owner explicitly directed this implementation to complete the shared shell and missing requirements in this repository. Changes made under that direction do not imply approval from other teammates; the approval table remains open for team review.

## 3. Fixed repository structure
QuizForge/
  main.py
  requirements.txt
  README.md
  .gitignore
  pytest.ini
  ui/{__init__.py,main_window.py,dashboard.py,question_bank.py,quiz_session.py,results.py,theme.py}
  services/{__init__.py,question_service.py,quiz_service.py,results_service.py}
  algorithms/{__init__.py,adaptive_engine.py}
  models/{__init__.py,question.py,quiz.py,attempt.py}
  database/{__init__.py,connection.py,schema.sql}
  database/repositories/{__init__.py,question_repository.py,attempt_repository.py,results_repository.py}
  utils/{__init__.py,errors.py,logging_config.py}
  scripts/seed_demo.py
  data/seed_questions.json
  tests/{test_questions.py,test_adaptive.py,test_quiz.py,test_results.py}
  docs/{QUIZFORGE_SHARED_FOUNDATION.md,modules/,screenshots/}

Runtime .db files, .venv, __pycache__, logs and secrets are gitignored. Canonical runtime database is `data/quizforge.db`, resolved relative to repository root, never current working directory.

## 4. Database contract — TEAM DECISION
The catalog prescribes four tables and essential constraints. Freeze this concrete SQL after team approval. Schema constraints are supplemented by service validation:

```sql
CREATE TABLE IF NOT EXISTS topics (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL COLLATE NOCASE UNIQUE
);
CREATE TABLE IF NOT EXISTS questions (
 id INTEGER PRIMARY KEY,
 topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE RESTRICT,
 text TEXT NOT NULL COLLATE NOCASE,
 option_a TEXT NOT NULL, option_b TEXT NOT NULL,
 option_c TEXT NOT NULL, option_d TEXT NOT NULL,
 correct_option TEXT NOT NULL CHECK(correct_option IN ('A','B','C','D')),
 difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 3),
 explanation TEXT NOT NULL DEFAULT '',
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 UNIQUE(topic_id,text)
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
 UNIQUE(attempt_id,question_id),
 UNIQUE(attempt_id,order_no)
);
CREATE INDEX IF NOT EXISTS idx_questions_filter ON questions(topic_id,difficulty,is_active);
CREATE INDEX IF NOT EXISTS idx_answers_question ON attempt_answers(question_id);
```

Connection interface:
- `get_connection(db_path: str | Path | None = None) -> sqlite3.Connection`: default path is `<repository-root>/data/quizforge.db`; explicit db_path is for isolated tests. Creates parent directory if necessary, sets `row_factory=sqlite3.Row`, `PRAGMA foreign_keys=ON` for EVERY connection, and busy_timeout. Caller closes connection; no global shared connection.
- `init_db(db_path: str | Path | None = None) -> None`: canonical initialization entry point; applies `database/schema.sql` idempotently to the same path used by `get_connection`. `initialize_database = init_db` may exist only as a backwards-compatibility alias, not a second implementation.
- All multi-row saves/imports are transactions with rollback on failure. Never share sqlite connections across threads.
- `questions.is_active=0` means SOFT DELETED by instructor, NOT consumed by a quiz. A question may appear across multiple attempts, but never twice in one attempt.
- `question_count` is requested number; actual saved rows can be fewer if quiz ends early.
- Service layer validates distinct nonempty options, names, normalized duplicate text, etc.; SQL constraints alone are insufficient.
- Catalog has no selected-topic snapshot table and no IN_PROGRESS status. TEAM DECISION: active quiz held in memory, final attempt + answers saved atomically on finish; historical topic filters use joined answer/question/topic records. Empty attempts may have no topic association. Any schema extension requires approval.

## 5. Shared data models — TEAM DECISION
All modules import the SAME dataclasses from models; no duplicate types.

```python
# models/question.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Question:
    id: int
    topic_id: int
    text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str  # A/B/C/D
    difficulty: int      # 1/2/3
    explanation: str
    is_active: bool = True
```

```python
# models/quiz.py
from dataclasses import dataclass
EASY, MEDIUM, HARD = 1, 2, 3

@dataclass(frozen=True)
class QuizConfig:
    learner_name: str
    topic_ids: tuple[int, ...]
    question_count: int
    time_limit_seconds: int

@dataclass(frozen=True)
class AnswerRecord:
    question_id: int
    order_no: int
    level_asked: int
    chosen_option: str | None
    is_correct: bool

@dataclass(frozen=True)
class QuizResult:
    status: str
    earned_points: int
    max_points: int
    score_percent: float
    answers: tuple[AnswerRecord, ...]
```

Other shared DTOs (`AnswerFeedback`, `QuizSessionState`, `ImportPreview`, `DashboardStats`, `AttemptSummary`, `AttemptReview`, `TopicAccuracy`) MUST be defined and approved centrally BEFORE separate AI tools implement dependent modules. No guessing their fields.

Values: difficulty always int 1/2/3, options A/B/C/D, unanswered None, statuses COMPLETED/TIMED_OUT/ABANDONED, IDs integers. Timestamp format: ISO 8601 with timezone offset (TEAM DECISION). Earned/max points integers; displayed percent one decimal, guard zero denominator.

## 6. Adaptive algorithm — required behavior
- Start state `(level=2, correct_streak=0, wrong_streak=0)`.
- Correct increments correct streak and clears wrong streak; wrong does opposite.
- Two consecutive correct => level min(3, level+1); two wrong => max(1, level-1). Reset both streaks after the trigger, including at bounds.
- Select unused eligible question at current level. If none, nearest available level, ties lower level.
- Deterministic ordering within selected level: `(times_used ascending, question_id ascending)`; times_used is number of previous saved uses in attempt_answers.
- No question repeats in one attempt. If no eligible questions remain, end early with explanation.
- Earned points for correct answer = difficulty level at which that question was asked; wrong/unanswered earns 0. Maximum points = sum of asked levels; score = 100 * earned / maximum.
- Required pattern C,C,W,C,C,W,W,C => asked levels 2,2,3,3,3,3,3,2; earned 12/max 21 => 57.1%.
- Required three correct from level 2 => asked 2,2,3 and earned 7; four wrong => asked 2,2,1,1.
- Implementation baseline (project owner direction, 2026-11-27): when nearest-level fallback is used, record/score actual question difficulty; retain adaptation target until answer streak changes it. This is a project choice, not an instructor rule.

Proposed pure interface:
```python
class AdaptiveEngine:
    def __init__(self) -> None: ...
    @property
    def level(self) -> int: ...
    def record_answer(self, is_correct: bool) -> int: ...

def select_question(
    questions: list[Question],
    used_question_ids: set[int],
    target_level: int,
    times_used: dict[int, int]
) -> Question | None: ...

def calculate_score(
    answers: tuple[AnswerRecord, ...]
) -> tuple[int, int, float]: ...
```
No imports of PySide6, sqlite3 or UI from algorithms.

## 7. Service interfaces — TEAM DECISION, to freeze after DTO approval

QuestionService:
- `list_topics() -> list[tuple[int,str]]`
- `list_questions(*, topic_id=None, difficulty=None, search_text="", active_only=True) -> list[Question]`
- `create_question(*, topic_id, text, options, correct_option, difficulty, explanation) -> Question`
- `update_question(question_id, *, topic_id, text, options, correct_option, difficulty, explanation) -> Question`
- `deactivate_question(question_id) -> None`
- `preview_import(path: str) -> ImportPreview` (read-only; valid + invalid rows/reasons)
- `commit_import(preview: ImportPreview) -> int` (atomic)
- `export_questions(path: str, *, format: str, filters: dict) -> int`

QuizService:
- `validate_setup(config: QuizConfig) -> None`
- `start(config: QuizConfig) -> Question`
- `submit_answer(chosen_option: str) -> AnswerFeedback`
- `next_question() -> Question | None`
- `finish() -> QuizResult` (explicit learner action after all requested questions are answered)
- `finish_timeout() -> QuizResult`
- `abandon() -> QuizResult`
- `get_state() -> QuizSessionState`

ResultsService:
- `get_dashboard_stats() -> DashboardStats`
- `list_attempts(*, learner_name="", topic_id=None, date_from=None, date_to=None) -> list[AttemptSummary]`
- `get_attempt_review(attempt_id: int) -> AttemptReview`
- `get_topic_accuracy() -> list[TopicAccuracy]`
- `get_level_path(attempt_id: int) -> list[tuple[int,int]]`
- `export_attempts_csv(path: str, *, filters: dict) -> int`

Typed shared exceptions: `ValidationError`, `NotFoundError`, `InsufficientQuestionsError`, `ActiveSessionError`, `PersistenceError`, all under `QuizForgeError`. Services raise them; UI catches and displays friendly text. Unexpected exceptions logged to local file.

## 8. Quiz and UI behavior
- Name length 2–40 characters; selected topics required; question count 5–30; positive time limit; Start disabled if insufficient eligible active questions.
- Start at Medium. One question at a time. Submit disabled until an option is selected; answer submitted once only; feedback correct/incorrect plus explanation; Next only after Submit.
- Timer updates via QTimer; amber at <=60 seconds, red at <=10 seconds; on expiry save TIMED_OUT, remaining unanswered counted wrong. Confirm on closing an active attempt; confirmed close saves ABANDONED. Sidebar navigation blocked during active quiz.
- Dashboard S1 shows questions, attempts, average score, topic accuracy bar chart, recent attempts, Start Quiz.
- S2 topic/difficulty/text filters, table, four-option editor, correct radio, live preview, import/export with preview.
- S4 attempts filtered by name/topic/date, selected attempt review (question, chosen/correct, level), level path step chart, topic accuracy, CSV export; abandoned clearly labeled. No-data charts display empty states.
- Shared visual language (TEAM DECISION): neutral light UI, blue accent, accessible contrast, 8px spacing scale, reusable buttons and styles in ui/theme.py, 1280x800 design target but resizable, English labels. No hard-coded independent theme in each screen.
- S1 Start -> S3 setup; S1 recent attempt -> S4 selected review. Refresh S1/S4 after saved attempts.

## 9. Import/export and validation
Canonical CSV columns and JSON keys (TEAM DECISION):
`topic,text,option_a,option_b,option_c,option_d,correct_option,difficulty,explanation`.
JSON array of objects; CSV UTF-8 with header. Export filtered active questions by default. No internal database IDs in export. Re-import into empty database must preserve question counts by topic/level.
All question text/options nonempty after strip; options distinct after strip/casefold; correct_option A-D; difficulty 1-3; explanation nonempty (TEAM DECISION). Duplicate text within a topic rejected; service normalizes whitespace/case before comparison. Preview invalid rows with line number/reason; only confirmed valid rows committed, in one transaction.

## 10. GitHub workflow
- `main` is integration branch; no direct feature commits. Enable branch protection where possible.
- Branches: `chore/foundation`, `feature/m1-question-bank`, `feature/m2-quiz-session`, `feature/m3-adaptive-engine`, `feature/m4-results`.
- Start: `git switch main`, `git pull --ff-only`, `git switch -c feature/...`.
- Commit small changes with meaningful messages. Push and open PR to main.
- PR description: requirement IDs, files changed, screenshots for UI, tests executed, known issues, any contract changes.
- At least one teammate reviews; pytest passes; application launches; no unapproved shared edits. Integrate small slices early rather than four giant PRs.
- All four contribute commits. Checkpoint tags cp1/cp2/cp3 and final v1.0.
- Shared contract changes: dedicated reviewed PR updating foundation + impacted module guides together. Never let AI independently modify shared APIs.

## 11. Testing and delivery gates
Catalog tests (target all six):
T-01 three correct from level 2 => levels 2,2,3; earned 7.
T-02 correct_option E or difficulty 4 => ValidationError, nothing saved.
T-03 four wrong from level 2 => levels 2,2,1,1.
T-04 C,C,W,C,C,W,W,C => levels 2,2,3,3,3,3,3,2; score 57.1%.
T-05 duplicate question text in same topic rejected; original persists after reconnect.
T-06 exactly nine available questions => nine distinct IDs; tenth selection ends early.
Extra integration tests: import preview/rollback, JSON/CSV round-trip, fallback tie-break, timer timeout/unanswered, abandonment, soft delete/history, no-data charts, topic filters, DB FK constraints.

Definition of done: required behavior demonstrated, tests pass, no crash/traceback to user, API contracts respected, reviewed PR merged, app launches after merge, screenshots/docs updated.

Phases:
0. Team approves foundation, resolves decisions below, creates skeleton/schema/models, smoke tests.
1. Parallel development: Jana M1; Alaa pure M3; Rawan M2 with mocks; Menna M4 with seeded fixtures.
2. Early integration: question service -> engine + quiz service -> attempt persistence -> results.
3. Hardening: tests, seed, screenshots, final demo and packaging.

## 12. Submission requirements
Source archive, GitHub URL, exact-pinned requirements.txt, README, schema and rebuildable seed, >=5 pytest tests, screenshots of S1–S4 at >=1280x800, technical PDF 3–6 pages, presentation PDF 6–10 slides, runnable executable OR reproducible clean-machine launch. Live demo ~6–7 minutes.
Catalog lists submission Saturday 14 November 2026 (confirm any instructor update).
Use instructor-assigned team ID `Tnn` (not yet known) in final deliverable naming. Project code QUIZFORGE; tags cp1, cp2, cp3, v1.0.

## 13. Implementation decisions and review status
1. Fallback: actual difficulty scored/stored vs target adaptation difficulty (proposal: actual).
2. Timeout: how to allocate unanswered unique questions without fabricating IDs; whether timeout rows affect adaptation (proposal: choose unused questions deterministically; null answers; no streak changes; stop if pool exhausted).
3. Abandon: record answered questions plus currently displayed unanswered question? (proposal: yes; do not fabricate remaining unseen questions).
4. Time limit allowed range/default: catalog doesn't specify (proposal: 1–120 minutes, default 10).
5. Topic accuracy denominator: catalog doesn't specify (proposal: correct / total recorded answers per topic in COMPLETED attempts; unanswered incorrect).
6. Memory-only active quiz, atomically persist when ending; no crash recovery (proposal: yes).
7. Exact DTOs for ImportPreview, AnswerFeedback, QuizSessionState, DashboardStats, AttemptSummary, AttemptReview, TopicAccuracy.
8. Shared file owner + backup; chosen OS; tested dependency pins; UI theme.
The project owner directed implementation to proceed using these stated policies on 2026-11-27. They are not university requirements, and this direction does not represent signatures or consensus from Jana, Rawan, Alaa, Menna, or an integration owner. Team review may refine the policies; any resulting API/schema change must update the affected guides and tests together.

## 14. Mandatory AI tool instruction
Read this shared foundation and the module guide fully. University catalog requirements are authoritative; use this document's implementation baseline for proposals not covered by the catalog. The project owner may explicitly authorize cross-module integration changes; record them here and in affected guides, and do not imply teammate approval. No SQL in UI; no Qt in algorithms. Use parameterized SQL, service validation, typed errors, automated tests and clear integration points. Report files changed, how to run, tests actually executed and known limitations. Never claim tests passed without running them.

END OF SHARED FOUNDATION — approve and freeze before generating the four module guides.


## 15. V2 CONSOLIDATED INTEGRATION CONTRACT — review and approve as a whole

**Status: implementation baseline selected by project owner on 2026-11-27; team review is pending.** This section supersedes contradictory version-1 suggestions in the module guides. The university catalog still takes priority. Do not describe these choices as instructor requirements. The approval record below remains blank until the team approves it.

### 15.1 One database, one initializer, one connection factory

- **Canonical filename:** `data/quizforge.db`, resolved from the repository root (the parent of `database/`), never from `os.getcwd()`. Add `data/*.db`, `data/*.db-*` and SQLite journal/WAL files to `.gitignore`; keep `data/seed_questions.json` tracked.
- **Canonical file:** `database/connection.py`. **Canonical functions:** `get_connection(db_path: str | Path | None = None) -> sqlite3.Connection` and `init_db(db_path: str | Path | None = None) -> None`. The optional path exists only to support temporary test databases; production code omits it.
- `init_db()` reads exactly `database/schema.sql` via a path relative to `connection.py`, applies it idempotently, and is called from `main.py` **before** constructing pages/services. Avoid independent schema initialization in services. If an older caller uses `initialize_database`, supply a trivial alias only if approved; new code calls `init_db`.
- `get_connection()` uses `sqlite3.connect(..., timeout=5.0)`, `row_factory=sqlite3.Row`, `PRAGMA foreign_keys=ON` and `PRAGMA busy_timeout=5000` for **every** connection; verify the pragma returns 1. A connection is owned and closed by its caller; do not share across threads.
- Repositories receive a `connection_factory` callable (default `get_connection`) and do not hardcode paths. For test isolation, inject a factory bound to a temporary **file-backed** database (not a fresh `:memory:` connection per call).
- The only four persistent tables are `topics`, `questions`, `attempts`, `attempt_answers`, with **exactly** the names/columns/constraints in §4. Do not add an `IN_PROGRESS` status or a fifth table without a reviewed schema change.
- `attempts.question_count` means **requested** count (5–30); the number of `attempt_answers` rows means **recorded** count. `level_asked` means the selected question's **actual** difficulty when fallback occurs (proposed policy).
- Database checks are not substitutes for service validation. Preserve original questions for historical review; soft-delete instead of hard-delete.

### 15.2 Shared DTOs — proposed exact shapes, single ownership

Put `Question` in `models/question.py`; put `QuizConfig`, `AnswerRecord`, `QuizResult`, `AnswerFeedback`, `QuizSessionState` in `models/quiz.py`; put reporting DTOs in `models/attempt.py`; put import DTOs in `models/question.py` or another centrally approved shared file. **Only the integration owner edits these shared model files.** All DTOs use `@dataclass(frozen=True)` and explicit type hints.

```python
# models/question.py — additions to the existing Question dataclass
@dataclass(frozen=True)
class ImportRowError:
    row_number: int  # CSV: physical record index, header is row 1; JSON: 1-based item index
    reason: str

@dataclass(frozen=True)
class ImportPreview:
    source_path: str
    source_format: str  # 'csv' | 'json'
    valid_rows: tuple[dict[str, object], ...]  # canonical nine-column normalized records
    invalid_rows: tuple[ImportRowError, ...]
    source_sha256: str  # verified again at commit to reject changed source

# models/quiz.py — additions to QuizConfig, AnswerRecord, QuizResult
@dataclass(frozen=True)
class AnswerFeedback:
    is_correct: bool
    correct_option: str
    chosen_option: str
    explanation: str
    earned_for_question: int
    level_asked: int
    next_target_level: int

@dataclass(frozen=True)
class QuizSessionState:
    phase: str  # SETUP | QUESTION | FEEDBACK | FINISHED
    current_question: Question | None
    requested_count: int
    presented_count: int
    submitted_count: int
    target_level: int
    remaining_seconds: int
    can_submit: bool
    can_advance: bool

# models/attempt.py
@dataclass(frozen=True)
class AttemptSummary:
    attempt_id: int
    learner_name: str
    started_at: str
    finished_at: str
    status: str
    requested_question_count: int
    recorded_answer_count: int
    earned_points: int
    max_points: int
    score_percent: float

@dataclass(frozen=True)
class DashboardStats:
    active_question_count: int
    attempt_count: int
    average_score_percent: float | None
    recent_attempts: tuple[AttemptSummary, ...]

@dataclass(frozen=True)
class TopicAccuracy:
    topic_id: int
    topic_name: str
    correct_count: int
    total_count: int
    accuracy_percent: float | None

@dataclass(frozen=True)
class AttemptAnswerReview:
    order_no: int
    question_id: int
    topic_name: str
    question_text: str
    options: tuple[str, str, str, str]
    correct_option: str
    chosen_option: str | None
    is_correct: bool
    level_asked: int
    explanation: str

@dataclass(frozen=True)
class AttemptReview:
    summary: AttemptSummary
    answers: tuple[AttemptAnswerReview, ...]
```

The `ImportPreview` representation is intentionally serializable; Jana must use canonical field names and validate again **inside the import transaction**, because the DB may have changed after preview. The SHA-256 check guards changes to the source file; it does not replace duplicate checks against current database rows. No partial commits if a valid preview row becomes invalid. Reject conflicting preview imports with a clear error and ask user to preview again.

### 15.3 Exact shared service methods — proposed freeze

**QuestionService (Jana):** retain all signatures from §7. Add `create_topic(name: str) -> tuple[int, str]` for manually adding topics; import can create missing topics **within its single transaction**. `list_topics()` returns `(id, name)` pairs. Define `options` as a tuple of **four strings in A/B/C/D order** for create/update. Keep `preview_import(path)` read-only and `commit_import(preview)` atomic. `export_questions(..., format='csv'|'json', filters=...)` uses approved canonical nine fields.

**QuizService (Rawan):** retain all methods in §7; add `finish() -> QuizResult` and `get_result() -> QuizResult | None`. `next_question() -> Question | None` advances only to another question; it must not complete a quiz. After the final submitted answer, keep its feedback visible and wait for the learner to choose the separate **Finish Quiz** action. The service completes only through `finish()` or a real timeout/abandon action; insufficient remaining questions must never be reported as a completed quiz. An attempt with too few available questions is rejected before Start. Service uses a monotonic deadline; QTimer is visual refresh only. `get_state()` returns the agreed `QuizSessionState`.

**AttemptRepository (Rawan):** `save_finished_attempt(*, config: QuizConfig, started_at: str, finished_at: str, result: QuizResult) -> int` and `get_question_usage_counts(question_ids: list[int]) -> dict[int, int]`. The first inserts one attempt and all answer rows in one transaction, with rollback on any failure. The latter counts **all** previously persisted `attempt_answers`, including NULL/unanswered and all terminal statuses; missing IDs count as zero in the engine. No history writes from Menna.

**ResultsService (Menna):** retain the exact signatures from §7 and the reporting DTOs above. All query and chart semantics in §15.5 below are proposed policies; never recompute adaptation to build the level chart.

**AdaptiveEngine (Alaa):** retain the exact pure API from §6. `record_answer` accepts `bool` only; `select_question` does not mutate inputs; `calculate_score` returns raw numeric percentage and uses actual `level_asked`.

**Shared constructors:** `QuestionService(repository)`, `QuizService(question_service, attempt_repository, *, clock=None)`, `ResultsService(repository)`; page constructors receive service instances (`QuestionBankPage(service)`, `QuizSessionPage(service)`, `DashboardPage(service)`, `ResultsPage(service)`). These are **proposed integration constructor signatures** and should be frozen alongside the DTOs. Do not silently instantiate different databases/services inside pages.

### 15.4 Exact quiz lifecycle policies — proposed

- `start`: learner name 2–40, selected topics nonempty, requested 5–30, sufficient active pool, time limit **1–120 minutes, default 10** (time range is not mandated by catalog); fresh engine state `(2,0,0)`.
- At every selection, prefer exact target difficulty; fallback to nearest, tie to lower; then `(historical times_used, question id)`; add ID to used set on presentation. `level_asked = Question.difficulty` even if engine target differs.
- At Submit, record `level_asked` **before** calling `record_answer`; only a valid, timely, first submission changes the engine. If deadline has expired, timeout wins and late answer is rejected. Submitted answers remain immutable.
- At timeout, fill remaining requested slots with **distinct eligible questions**, selected deterministically from the remaining pool, `chosen_option=None`, `is_correct=False`; these placeholder answers affect the score denominator but **do not** update streaks. If pool is exhausted, record fewer than requested, never invent IDs.
- At confirmed abandonment, save submitted records and the currently presented but unsubmitted question (if any) as unanswered; do **not** create unseen placeholders. Cancelled close does not finalize. Persist only once on successful transaction commit; retry safely after failure.
- Normal completion requires the explicit `finish()` action after the final answer feedback is shown; it must not occur merely because the last answer was submitted or `next_question()` was called. Only `COMPLETED`, `TIMED_OUT`, `ABANDONED` are persisted. Active session is in memory; process crashes are not recovered. UI navigation lock remains until final save succeeds.
- Scoring: correct earns `level_asked` points, incorrect/unanswered earns zero; maximum is the sum of `level_asked` for persisted answer records. Percent is `100 * earned / max` (zero -> 0.0 internally); UI formats one decimal.

### 15.5 Analytics, CSV, dates and historical review — proposed

- `DashboardStats.active_question_count`: `questions.is_active=1`; `attempt_count`: **all persisted terminal attempts**; `average_score_percent`: arithmetic mean of **COMPLETED** attempts with `max_points>0`, or `None` if none.
- Topic accuracy = correct recorded answers / all recorded answers **in COMPLETED attempts**, by `topic_id`; NULL unanswered counts wrong; zero denominator -> `None` (No data). History topic filtering uses `EXISTS` on recorded answers, so a zero-record attempt has no topic association. No duplicate attempts.
- New history timestamps use timezone-aware UTC ISO 8601 strings in `YYYY-MM-DDTHH:MM:SS+00:00`. Date filters use inclusive saved-calendar `date_from` and `date_to` bounds (the end uses an exclusive next-day boundary). Legacy timezone-naive timestamps are preserved and compared by their stored calendar date; they are not silently reinterpreted or shifted.
- Preserve history: **reject changing topic, text, options, correct option, difficulty, or explanation of any question referenced by `attempt_answers`**. Such a question may still be soft-deactivated. For corrections, deactivate and create a replacement question. This avoids a fifth table and makes existing review meaningful. It does not retroactively snapshot data from before the policy; warn if historical records predate it.
- `get_level_path` reads persisted `(order_no, level_asked)` ascending; does not reconstruct engine state.
- Attempt CSV export: one row per filtered attempt with header `attempt_id,learner_name,started_at,finished_at,status,requested_question_count,recorded_answer_count,earned_points,max_points,score_percent`. UTF-8 with BOM (`utf-8-sig`), `csv` module, one-decimal numeric score, stable newest-first order. Prefix dangerous **text** values that start (after leading whitespace) with `=`, `+`, `-`, `@` or control characters with `'` to reduce spreadsheet formula execution; document that this alters exported text. Header even for zero rows. Use temporary sibling file and atomic replace, after UI overwrite confirmation.

### 15.6 Responsibility for shared files and integration

The implementation now has `main.py`, a single four-screen `MainWindow`, shared theme/models/errors, and the canonical repositories. The project owner authorized these cross-module changes for this work session; affected teammates should review them before the team treats the contract as approved. Module ownership remains: Jana M1; Rawan M2; Alaa M3; Menna M4. Four top-level screens only; one QMainWindow; no Qt in algorithm; no SQL in widgets.

### 15.7 Contract verification before parallel coding

1. Implementation is authorized using this baseline; all four members should review it before team sign-off (including date/time, fallback, timeout, abandonment, reporting, edit lock and CSV policies).
2. Shared skeleton, SQL and DTOs are in place; verify `python -m pytest -q` and `python main.py` before integration sign-off.
3. Add a contract smoke test that calls `init_db(temp_path)` and `get_connection(temp_path)`, checks the four table names, exact `PRAGMA foreign_keys=1`, the canonical columns, and shared DTO imports.
4. Jana tests atomic import, duplicate checks and immutable history. Rawan tests exactly-once lifecycle, timer races and atomic saves. Alaa tests golden pattern and deterministic selection. Menna tests filter/aggregate/export semantics.
5. Run full integration with seeded >=90 questions and >=10 completed attempts; verify the golden pattern `2,2,3,3,3,3,3,2` yields `12/21` and **57.1%**, and appears identically in S4.
6. If any API or schema must change, update **this foundation plus all affected guides in the same reviewed PR**. Do not silently diverge.

**Approval record (fill in at team meeting):** Jana ___; Rawan ___; Alaa ___; Menna ___; integration owner ___; date ___; approved commit SHA ___.



## V3 CANONICAL NAME REGISTRY — READ BEFORE IMPLEMENTATION

**Status: one consistent implementation baseline, selected by project owner on 2026-11-27; team review pending.** If an earlier section in this guide says a DTO/API is undefined or suggests a different name/signature, this registry and Shared Foundation §15 take precedence. This status does not imply team approval. The university catalog takes precedence over all proposals.

### Canonical modules and symbols

| Module path | Canonical public names |
|---|---|
| `database/connection.py` | `get_connection(db_path: str \| Path \| None = None)`, `init_db(db_path: str \| Path \| None = None)`; do not call `initialize_database` in new code |
| `models/question.py` | `Question`, `ImportRowError`, `ImportPreview` |
| `models/quiz.py` | `QuizConfig`, `AnswerRecord`, `QuizResult`, `AnswerFeedback`, `QuizSessionState`, `EASY`, `MEDIUM`, `HARD` |
| `models/attempt.py` | `AttemptSummary`, `DashboardStats`, `TopicAccuracy`, `AttemptAnswerReview`, `AttemptReview` |
| `utils/errors.py` | `QuizForgeError`, `ValidationError`, `NotFoundError`, `InsufficientQuestionsError`, `ActiveSessionError`, `PersistenceError` |
| `algorithms/adaptive_engine.py` | `AdaptiveEngine`, `select_question`, `calculate_score` |
| `services/question_service.py` | `QuestionService` |
| `services/quiz_service.py` | `QuizService` |
| `services/results_service.py` | `ResultsService` |
| `database/repositories/question_repository.py` | `QuestionRepository` |
| `database/repositories/attempt_repository.py` | `AttemptRepository` |
| `database/repositories/results_repository.py` | `ResultsRepository` |
| `ui/question_bank.py` | `QuestionBankPage(QWidget)` |
| `ui/quiz_session.py` | `QuizSessionPage(QWidget)` |
| `ui/dashboard.py` | `DashboardPage(QWidget)` |
| `ui/results.py` | `ResultsPage(QWidget)` |
| `ui/main_window.py` | `MainWindow(QMainWindow)` — shared integration owner |

### Constructor and method names — freeze together

```python
QuestionRepository(connection_factory=get_connection)
AttemptRepository(connection_factory=get_connection)
ResultsRepository(connection_factory=get_connection)
QuestionService(repository)
QuizService(question_service, attempt_repository, *, clock=None)
ResultsService(repository)
QuestionBankPage(service)
QuizSessionPage(service)
DashboardPage(service)
ResultsPage(service)

# QuestionService
list_topics() -> list[tuple[int, str]]
create_topic(name: str) -> tuple[int, str]
list_questions(*, topic_id=None, difficulty=None, search_text="", active_only=True) -> list[Question]
create_question(*, topic_id, text, options, correct_option, difficulty, explanation) -> Question
update_question(question_id, *, topic_id, text, options, correct_option, difficulty, explanation) -> Question
deactivate_question(question_id) -> None
preview_import(path: str) -> ImportPreview
commit_import(preview: ImportPreview) -> int
export_questions(path: str, *, format: str, filters: dict) -> int

# QuizService
validate_setup(config: QuizConfig) -> None
start(config: QuizConfig) -> Question
submit_answer(chosen_option: str) -> AnswerFeedback
next_question() -> Question | None
finish() -> QuizResult
finish_timeout() -> QuizResult
abandon() -> QuizResult
get_state() -> QuizSessionState
get_result() -> QuizResult | None

# AttemptRepository
save_finished_attempt(*, config: QuizConfig, started_at: str, finished_at: str, result: QuizResult) -> int
get_question_usage_counts(question_ids: list[int]) -> dict[int, int]

# ResultsService
get_dashboard_stats() -> DashboardStats
list_attempts(*, learner_name="", topic_id=None, date_from=None, date_to=None) -> list[AttemptSummary]
get_attempt_review(attempt_id: int) -> AttemptReview
get_topic_accuracy() -> list[TopicAccuracy]
get_level_path(attempt_id: int) -> list[tuple[int, int]]
export_attempts_csv(path: str, *, filters: dict) -> int

# Adaptive module
AdaptiveEngine().level -> int
AdaptiveEngine().record_answer(is_correct: bool) -> int
select_question(questions: list[Question], used_question_ids: set[int], target_level: int, times_used: dict[int, int]) -> Question | None
calculate_score(answers: tuple[AnswerRecord, ...]) -> tuple[int, int, float]
```

**Names are case-sensitive.** Use `data/quizforge.db` only via the shared connection factory. `QuizConfig.time_limit_seconds` is in seconds; the selected UI range is 60–7200 seconds, default 600 seconds. New timestamps use UTC ISO format `YYYY-MM-DDTHH:MM:SS+00:00`; date filters use saved calendar dates, preserving legacy naive timestamps without conversion. Pages receive service instances. `MainWindow` owns one sidebar and exactly four primary screens; it listens to `navigationLockChanged(bool)` and confirms/saves active attempts on close. `get_result()` is the normal completion result accessor.

**Important behavior clarification:** `validate_setup` and `start` reject a pool smaller than the requested question count; a quiz may end early if its pool changes while running or if eligible questions become unavailable. This is not permission to begin an underfilled quiz. Do not count an unseen timeout placeholder as a question shown to the learner; distinguish presented vs recorded counts. `AnswerFeedback.earned_for_question` is based on actual `level_asked`.

**Approval checklist:** Jana ___ / Rawan ___ / Alaa ___ / Menna ___ / integration owner ___ / approved commit ___ . Until filled, this is a reviewed proposal, not a frozen contract.
