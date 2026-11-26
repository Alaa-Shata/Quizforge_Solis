> **IMPLEMENTATION BASELINE (2026-11-27):** The project owner directed implementation to proceed using `QUIZFORGE_SHARED_FOUNDATION.md` §15 and the policies recorded there. Team review remains open; this instruction does not claim teammate approval. University catalog requirements remain authoritative.

# QUIZFORGE — RAWAN IMPLEMENTATION GUIDE

**Module:** M2 — Quiz Session<br>
**Owner:** Rawan (روان)<br>
**Requirements:** FR-03, FR-04; primary screen S3<br>
**Guide version:** 2.0<br>
**Shared contract:** `docs/QUIZFORGE_SHARED_FOUNDATION.md` version 1.0 — **proposed; team approval required**<br>
**Reference:** *Python GUI Project Catalog 2026*, Project 06, sections D–J and common technical baseline.

> **IMPLEMENTATION RULE:** Read the complete shared foundation and this guide. The university catalog determines required behavior; the 2026-11-27 implementation baseline resolves the documented proposals for this work. Keep the approval record honest and do not claim the team approved it. Never add an unreviewed database column or screen. Never claim a test passed unless it was actually run.

---

## 1. Mission: what you are building

Build the **entire interactive quiz-taking experience**: learner setup, eligibility checks, starting the quiz at Medium, showing one question at a time, selecting/submitting an answer, immediate feedback, Next, progress, countdown, timeout, safe abandonment, and final persistence of an attempt. Rawan owns the orchestration of a quiz session, **not** the adaptive algorithm itself.

### Catalog requirements

**FR-03 — Start a quiz:** Learner enters a display name (**2–40 characters; no login**), chooses one or more topics, requests **5–30 questions**, selects a time limit, and starts. First question is at **Medium (2)**. UI shows one question at a time, four options, progress (e.g., `3/10`), current difficulty and countdown. Start is disabled if there are too few eligible questions.

**FR-04 — Submit / end:** Submit is disabled until an answer is selected. Submitting shows **correct/incorrect** plus the question's **explanation**. Timer expiry ends the attempt as `TIMED_OUT`; remaining questions count as **unanswered/incorrect**. Closing the application during an active quiz requires confirmation and, if confirmed, saves `ABANDONED`.

**S3 — Quiz Session:** A setup panel and question panel within **one** S3 screen. Timer turns **amber at 60 seconds remaining** and **red at 10 seconds remaining**. Include progress bar, difficulty badge, four radio options, Submit and Next. **Block sidebar navigation during an active attempt.**

### Out of scope

Do **not** implement the S2 question editor/import/export (Jana), core selection/state/scoring functions (Alaa), S1/S4 dashboard/results/charts (Menna), or the common `QMainWindow`/sidebar (integration owner). Do not create login, web APIs, a fifth screen, or a second `QMainWindow`.

---

## 2. Ownership and integration dependencies

| File | Owner/action | Purpose |
|---|---|---|
| `ui/quiz_session.py` | **Rawan implements** | `QuizSessionPage(QWidget)`, setup/question/feedback/finished views, QTimer, signals |
| `services/quiz_service.py` | **Rawan implements** | quiz lifecycle, validation, coordinating question bank + engine + persistence |
| `database/repositories/attempt_repository.py` | **Rawan implements** | atomic save of attempts and answer records; parameterized SQL |
| `tests/test_quiz.py` | **Rawan implements** | setup, lifecycle, timeout, abandon, persistence tests |
| `algorithms/adaptive_engine.py` | **Alaa owns** | `AdaptiveEngine`, `select_question`, `calculate_score` — import; do not rewrite |
| `models/question.py`, `models/quiz.py`, `models/attempt.py` | **Shared** | import canonical DTOs, no local duplicates |
| `database/schema.sql`, `database/connection.py` | **Shared** | read, do not change without approval |
| `services/question_service.py` | **Jana owns** | validated question data; use agreed read API |
| `ui/main_window.py`, `ui/theme.py`, `main.py` | **Shared** | navigation and styling; request wiring through integration PR |
| `services/results_service.py` | **Menna owns** | receives saved attempts through database, no direct coupling |

**Parallel work is expected:** Start by implementing the page against **mock `QuizService` and fixture `Question` objects** while Jana/Alaa finish their parts. Implement `QuizService` against approved interfaces; do not wait until their whole modules are finished, and do not write fake production versions of their modules.

**Critical integration boundary:** Rawan is responsible for converting an answer event into an **exactly-once** engine update and a persisted answer record. Alaa is responsible for the algorithm's mathematical correctness. The two must agree on the difference between *target difficulty* and *actual difficulty asked* (especially during fallback).

---

## 3. Architecture: who calls whom

```text
MainWindow (shared)
  └─ QuizSessionPage(QWidget) — Rawan
       ├─ renders setup, question, feedback, result
       ├─ QTimer + UI navigation guards
       └─ QuizService — Rawan
            ├─ QuestionService / QuestionRepository — Jana contract
            ├─ AdaptiveEngine + select_question + calculate_score — Alaa
            └─ AttemptRepository — Rawan
                 └─ sqlite3 connection / schema — shared

ResultsService (Menna) -> persisted attempts/answers
```

**Rules:**

- UI never writes SQL, computes adaptive transitions, or stores business logic.
- Service never imports Qt, widgets or matplotlib; time can be injected for testing.
- Repository never imports Qt or the adaptive engine.
- Engine never imports Qt, sqlite3, or services.
- UI signals communicate `quiz_started`, `quiz_finished`, `navigation_lock_changed`, etc., to the shared shell; Rawan must not directly modify `QMainWindow` without approval.
- Every action is idempotent or guarded against double-clicks, timer race conditions and re-entrancy.

---

## 4. Exact shared models and values

Import canonical classes from the shared foundation; do **not** recreate them.

```python
from models.question import Question
from models.quiz import QuizConfig, AnswerRecord, QuizResult
from algorithms.adaptive_engine import (
    AdaptiveEngine, select_question, calculate_score
)
```

The approved `QuizConfig` contains:

```python
QuizConfig(
    learner_name: str,
    topic_ids: tuple[int, ...],
    question_count: int,       # 5..30
    time_limit_seconds: int,   # positive; approved bounds TBD
)
```

The approved `AnswerRecord` contains `question_id`, `order_no` (1-based), `level_asked` (1/2/3), `chosen_option` (`A`/`B`/`C`/`D` or `None`), `is_correct` (bool).

`QuizResult` contains `status` (`COMPLETED`, `TIMED_OUT`, `ABANDONED`), `earned_points`, `max_points`, `score_percent`, `answers`.

**Data conventions:**

- `Question.correct_option` is one uppercase letter `A`–`D`, not an integer or full option text.
- `Question.difficulty` is 1/2/3, mapped to Easy/Medium/Hard for display.
- `chosen_option=None` means unanswered; `is_correct=False` for unanswered.
- Progress should clearly distinguish **question position** from **submitted count**; do not display `3/10` before the third question has been selected unless the UI labels it correctly.
- Points are integers. Display percentages to **one decimal place**. `max_points == 0` must not cause division by zero.
- Timestamps use the shared agreed ISO 8601 format with timezone offset; do not independently invent a different format.

### Shared DTOs that must be approved before integration

The foundation intentionally leaves `AnswerFeedback` and `QuizSessionState` incomplete. **Do not silently implement competing versions.** Propose the following to the integration owner:

```python
# PROPOSAL ONLY — add to models/quiz.py after approval
from dataclasses import dataclass

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
    phase: str               # SETUP | QUESTION | FEEDBACK | FINISHED
    current_question: Question | None
    requested_count: int
    presented_count: int
    submitted_count: int
    target_level: int
    remaining_seconds: int
    can_submit: bool
    can_advance: bool
```

**Design note:** The proposed `remaining_seconds` in service state requires a clear ownership decision for timekeeping; see §7. Do not use these DTOs in merged production code until the team approves the exact fields.

---

## 5. QuizService public API — do not drift

Use the shared foundation's signatures:

```python
class QuizService:
    def validate_setup(self, config: QuizConfig) -> None: ...
    def start(self, config: QuizConfig) -> Question: ...
    def submit_answer(self, chosen_option: str) -> AnswerFeedback: ...
    def next_question(self) -> Question | None: ...
    def finish_timeout(self) -> QuizResult: ...
    def abandon(self) -> QuizResult: ...
    def get_state(self) -> QuizSessionState: ...
```

**Additional integration questions to resolve, not new APIs to invent:**

1. How does the UI finish a normally completed attempt and retrieve `QuizResult`? The foundation has `next_question() -> Question | None`, but no `finish_completed()` or `get_result()` method. **Propose `get_result() -> QuizResult | None`**, or an agreed signal/result field, and freeze it before coding.
2. Where is the requested time limit tracked: service-owned monotonic deadline, or UI-owned QTimer? **Recommended TEAM DECISION:** service owns a monotonic deadline and exposes remaining time; QTimer only refreshes the UI. This prevents timer reset by a stalled event loop.
3. Does `start()` need to return a `Question` even when the pool becomes unavailable between setup validation and start? **Recommended:** service revalidates and raises `InsufficientQuestionsError` before changing session state.
4. Does `QuestionService.list_questions` return only active questions in selected topics, or does QuizService filter from the complete active list? **Recommended:** call approved list API and filter by `config.topic_ids` in QuizService; use repository-backed usage counts for deterministic selection.

### Errors

Use shared typed exceptions (`ValidationError`, `InsufficientQuestionsError`, `ActiveSessionError`, `PersistenceError`, etc.). UI displays friendly messages, e.g.:

- “Enter a name between 2 and 40 characters.”
- “Select at least one topic.”
- “Choose between 5 and 30 questions.”
- “Only 7 active questions are available for these topics.”
- “Select an answer before submitting.”
- “This answer has already been submitted.”
- “We couldn't save the attempt. Please try again.”

Never show a raw `sqlite3.IntegrityError` or Python traceback in the UI.

---

## 6. State machine — required to prevent race conditions

Use an explicit session phase; recommended states:

```text
SETUP --valid Start--> QUESTION
QUESTION --Submit--> FEEDBACK
FEEDBACK --Next--> QUESTION
FEEDBACK --Next with requested count reached--> FINISHED (COMPLETED)
QUESTION/FEEDBACK --Timer expires--> FINISHED (TIMED_OUT)
QUESTION/FEEDBACK --Confirmed close--> FINISHED (ABANDONED)
```

**Invariants:**

1. Only **one** active attempt per `QuizService` instance.
2. A displayed question has exactly one identity and one immutable `level_asked`.
3. One `Submit` produces **one** `AnswerRecord` and **one** call to `AdaptiveEngine.record_answer()`.
4. `Next` is illegal before a valid Submit; it cannot skip a question.
5. Once in `FINISHED`, timeout/close/Submit/Next must **not** save a second attempt or duplicate answer rows.
6. The used-ID set grows as questions are selected; no repeated question in one attempt.
7. On finish, one atomic transaction saves one `attempts` row and its answer rows; `QuizResult` reflects the same records.
8. The timer continues through feedback (unless team formally chooses otherwise); showing feedback must not silently pause/reset the deadline.
9. On a **cancelled** close confirmation, return to active quiz with the same question and remaining time.
10. The application cannot navigate to S1/S2/S4 while an attempt is active. The integration owner owns the final sidebar guard; Rawan exposes the state/signal.

**Potential bug to avoid:** If timer expires during the instant a user clicks Submit, process only one event. Define a single authoritative deadline check in the service. At or after expiry, reject the late answer and finalize timeout. Never both accept a late answer and count it unanswered.

---

## 7. Countdown timer and time ownership

**Catalog-mandated:** Visible countdown; amber at 60 seconds, red at 10 seconds; timeout closes quiz and marks remaining unanswered.

**Recommended TEAM DECISION:** Use a service-owned **monotonic** deadline (`time.monotonic()`), with injectable clock for tests. `QTimer` ticks every 100–250 ms to redraw remaining time; it is **not** the source of truth. Derive displayed whole seconds consistently (e.g., ceiling of nonnegative remaining seconds) and document this. The timer should not depend on wall-clock changes.

- `remaining > 60` => normal.
- `10 < remaining <= 60` => amber.
- `0 < remaining <= 10` => red.
- `remaining <= 0` => call `finish_timeout()` exactly once.

**Never** start a second QTimer on Next, and stop/disconnect it after finishing or closing the page. Handle multiple tick callbacks safely. QTimer and Qt widgets must remain on the GUI thread. No background worker may directly mutate widgets.

**Time-limit validation:** The catalog does not specify the permitted range or default. The shared foundation proposes **1–120 minutes, default 10 minutes**, pending approval. Do not present this as a university rule.

---

## 8. Question selection and scoring integration

Rawan must **call** Alaa's engine, not recreate the logic in the UI or service.

### Correct selection pipeline

1. Validate selected topics, active question count, and request count.
2. Load eligible active questions from Jana's approved read interface.
3. Obtain usage counts per question from historical `attempt_answers` via approved repository/service method. **This usage-count read API is not yet specified**; request a contract decision rather than writing cross-module SQL inside QuizService.
4. Initialize `AdaptiveEngine()`; its target level starts at **2**.
5. Call `select_question(questions, used_ids, engine.level, times_used)`.
6. Store returned `Question.id` in used IDs immediately, and freeze the **actual** `Question.difficulty` as `level_asked` for that question (**fallback interpretation pending approval**).
7. On Submit, compare chosen letter to `Question.correct_option`, append `AnswerRecord`, call `engine.record_answer(is_correct)` exactly once, then show feedback.
8. On Next, pick another question using updated target level, unless requested count reached or no questions remain.
9. On normal completion, calculate weighted score through `calculate_score(tuple(answers))`, build `QuizResult`, save atomically, and notify UI.

### Selection ordering

- Current target level first.
- If none unused there, nearest available level; if equidistant, choose lower level.
- Within selected level: `times_used` ascending, then `Question.id` ascending.
- Exclude inactive questions, unselected topics, and already used question IDs.
- End early with clear message when pool exhausted.

**Do not use** `random.choice`, `ORDER BY RANDOM()`, current time, or in-memory arbitrary list order to select questions. These would break deterministic acceptance tests.

### Scoring and examples

- Easy=1, Medium=2, Hard=3.
- Correct earns the asked level's weight; wrong/unanswered earns 0; maximum is the sum of recorded asked levels.
- Score = `100 * earned_points / max_points`, shown as `57.1%` for the catalog's worked example.
- **Required regression:** `C,C,W,C,C,W,W,C` asks `2,2,3,3,3,3,3,2`, earned 12, max 21.
- **Required regression:** three correct from Medium asks `2,2,3`, earned 7.
- **Required boundary:** four wrong asks `2,2,1,1`, never 0.

**Fallback ambiguity:** The catalog's example assumes matching levels are available. The foundation proposes recording/scoring the **actual selected question difficulty**, while retaining engine target as a separate variable. This must be approved by all affected members.

---

## 9. Timeout and abandonment — do not improvise

These are high-risk integration cases because they involve **business rules + database persistence + GUI close events**.

### Timeout

The catalog explicitly requires `TIMED_OUT`, remaining unanswered, and unanswered counted wrong. It does **not** fully define how to assign IDs/difficulties to unseen remaining questions.

**Proposed team policy (pending approval):** After expiry, deterministically select as many distinct remaining eligible questions as needed to reach the requested count; record each with `chosen_option=None`, `is_correct=False`, its actual difficulty as `level_asked`; do not feed synthetic wrong answers to the adaptive streak machine. If there are no unused questions, stop rather than invent IDs. The final score denominator includes those recorded unanswered questions. This must be reviewed with Alaa and the integration owner **before** coding.

**Cases to test:** expiry before first submission, expiry after a submitted answer, expiry during feedback, expiry exactly at boundary, and repeated timeout signal. `TIMED_OUT` persisted once, with unique question IDs and correct score denominator.

### Abandon / app close

The catalog explicitly requires a confirmation and `ABANDONED` status when closing mid-quiz.

**Proposed team policy (pending approval):** Save previously submitted answers plus the currently displayed unanswered question (if one is awaiting Submit), with `chosen_option=None`, `is_correct=False`; do **not** fabricate all unseen questions. If user cancels closing, keep the quiz running. If saving fails, do not silently discard the attempt; show error and keep app open or provide a safe retry.

**Close event flow (integration owner must wire):**

```text
MainWindow.closeEvent
  -> if QuizSessionPage reports active attempt:
       ask "Leave quiz? Your attempt will be saved as abandoned."
       Cancel -> event.ignore(); preserve session
       Confirm -> QuizService.abandon(); save succeeds -> event.accept()
                  save fails -> event.ignore(); show error
     else -> event.accept()
```

**Sidebar navigation:** block navigation to other screens without implicitly abandoning. Only the confirmed close action may abandon; any additional explicit “Quit Quiz” control needs its own agreed confirmation flow.

---

## 10. Database persistence contract

Use the shared schema as-is:

```text
attempts:
 id, learner_name, started_at, finished_at, status,
 question_count, earned_points, max_points

attempt_answers:
 id, attempt_id, question_id, order_no,
 level_asked, chosen_option, is_correct
```

### Proposed repository responsibilities

`AttemptRepository` should implement small, testable methods, e.g.:

```python
# INTERNAL API PROPOSAL — coordinate with integration owner
save_finished_attempt(
    *, config: QuizConfig, started_at: str, finished_at: str,
    result: QuizResult
) -> int:
    """Atomically insert attempt + all answers; return attempt ID."""

get_question_usage_counts(question_ids: list[int]) -> dict[int, int]:
    """Prior appearances in saved attempt_answers, including completed/other statuses."""
```

**IMPORTANT:** These are *new repository method proposals*, not already frozen in the shared foundation. Request approval before treating them as cross-module interfaces.

Implementation rules:

- `get_connection()` must set `PRAGMA foreign_keys=ON` **for every connection**.
- SQL is parameterized (`?` placeholders); never interpolate learner names/IDs into SQL.
- Insert attempt + answers in one transaction. If any answer insert fails, rollback the attempt row too.
- `UNIQUE(attempt_id, question_id)` and `UNIQUE(attempt_id, order_no)` enforce no repeats.
- `is_correct` stored as 0/1; unanswered `chosen_option` stored as SQL `NULL`.
- Never hard-delete questions to “clean up” completed quizzes; history must remain reviewable.
- Never mark `questions.is_active=0` merely because it appeared in an attempt.
- Do not use a SQLite connection created on one thread from another thread.
- No IN_PROGRESS status exists in the shared schema. The shared foundation proposes holding the active attempt in memory and saving on finish only; crash recovery is not promised.
- Preserve `started_at` from actual start and `finished_at` from actual end. Save the requested `question_count` separately from actual answer count.
- Once save succeeds, cache/return saved attempt ID as appropriate to prevent accidental duplicate inserts on repeated finalization.

**Failure recovery:** If persistence raises an error, keep the in-memory answer records available for retry. Do not show “Saved” until commit succeeds.

---

## 11. S3 GUI — detailed specification

Implement `QuizSessionPage(QWidget)` in `ui/quiz_session.py`. **It is one of four primary pages**, not a separate window. Use a nested `QStackedWidget` or internal layouts *inside S3* for setup/question/finish states; this does not create an extra top-level screen.

### A. Setup panel

- Header: “Start a Quiz” with short description.
- Learner name `QLineEdit`, with 2–40 character validation feedback.
- Topic multi-select (e.g. checkbox list) populated from real topics.
- Question count `QSpinBox`, range 5–30.
- Time limit control (minutes) with agreed range/default.
- Availability text: “X active questions available for selected topics.”
- Start Quiz primary button, disabled when invalid or insufficient questions.
- Clear inline messages for empty topics/bank; no crash.
- Use a single source of truth for validation: service decides validity; GUI mirrors it.

### B. Active question panel

- Learner name / selected topics summary (optional if space allows).
- Prominent question index, e.g. “Question 3 of 10”; progress bar.
- Difficulty badge: Easy/Medium/Hard based on **asked question**.
- Countdown `MM:SS` with normal/amber/red state and text label (not color alone).
- Question text, four radio buttons in one exclusive `QButtonGroup`.
- Submit button disabled until a choice is selected; then enabled.
- After Submit: lock options and Submit; display correct/incorrect text, correct answer and explanation; show Next button.
- On last question: after Submit, keep the correct/incorrect feedback and explanation visible and show a distinct **Finish Quiz** button. Do not finish on Submit or when attempting to advance; finish only after the learner selects Finish (timeout and confirmed abandonment remain separate terminal actions).
- If no eligible question remains: show early-end explanation, finish safely, no infinite loop.

### C. Finished panel

- Show `COMPLETED`, `TIMED_OUT`, or `ABANDONED` appropriately (the latter usually appears during close rather than as a separate panel).
- Show weighted percentage to one decimal, earned/max points, answered/unanswered counts.
- Provide a route to Results & Analytics through an approved navigation signal; do not import Menna's screen directly.
- Stop timer and release navigation lock only after successful final persistence.

### D. UI quality requirements

- Follow shared `ui/theme.py`, spacing, typography, accessible contrast and focus states.
- Use radio controls with readable labels and correct tab order.
- Never rely on green/red alone; show explicit “Correct”/“Incorrect” and explanation.
- Keep text wrapping robust for long questions/options; allow scrolling without cutting off Submit.
- Avoid freezing the GUI during DB writes; a busy state or worker is appropriate if operations exceed ~0.5 seconds.
- Block repeated clicks while a transition/save is in progress.
- The page must be resizable; shared design target 1280×800 is **not** a fixed-only window size.

---

## 12. Validation and edge-case matrix

| Scenario | Expected behavior |
|---|---|
| Name empty / 1 char / >40 chars | Start disabled; service raises `ValidationError` |
| No topics selected | Start disabled; clear message |
| Count 4 or 31 | Rejected; valid 5–30 |
| Time below 60 seconds or above 7200 seconds | Rejected; accepted range is 1–120 minutes |
| Fewer active questions than requested | Start disabled and service rejects on recheck |
| Inactive questions only | Not eligible |
| Initial target level has no question | Alaa's deterministic nearest-level fallback |
| No question left | Finish early, clear explanation, no repeated ID |
| Submit without choice | Disabled and service rejects |
| Double-click Submit | One answer record and one engine transition |
| Click Next before Submit | Rejected |
| Repeated Next | No skipped question |
| Timer expires during feedback | Finalize timeout exactly once; record deterministic unanswered rows to the requested count |
| Timer expires simultaneously with Submit | Deadline decides; late Submit is rejected and no answer is duplicated |
| Close confirmation cancelled | Keep session and timer running |
| Close confirmed | Save ABANDONED once; only then close |
| Database failure during finish | Roll back; retain state for retry; show friendly error |
| Attempt with unanswered rows | Count wrong; score denominator includes recorded asked levels |
| User tries sidebar navigation | Block until attempt finished |
| Quiz completed and page reopened | Setup reset safely; no leaked QTimer |
| No attempts exist yet | Quiz still starts from bank; results screen handles no-data |

---

## 13. Implementation plan — do these steps in order

### Phase 0 — environment and contracts

1. Clone repository, switch to updated `main`, create Rawan's feature branch.
2. Read foundation and verify the shared schema, models and exception classes exist or are assigned to an integration owner.
3. Use the 2026-11-27 implementation baseline in the shared foundation for `AnswerFeedback`, `QuizSessionState`, completion, usage counts, deadline ownership, fallback, timeout and abandonment.
4. Keep the approval record open for team review; do not block the implementation authorized by the project owner.
5. Set up virtual environment with team's Python 3.11 and pinned requirements; verify `python main.py` and `pytest` run on foundation branch.

### Phase 1 — page UI using mocks

6. Create `QuizSessionPage(QWidget)` with setup/active/finished internal views.
7. Populate topics and sample questions from fixtures or a mock service; avoid modifying Jana's files.
8. Implement radio selection, Submit/Next enable/disable states, feedback panel, progress bar, timer visual states and responsive layout.
9. Add typed signals for start/finish/navigation lock, to be wired by shared integration owner.
10. Manually test UI states with long text, no topics, disabled Start, 60s/10s timer colors.

### Phase 2 — service lifecycle

11. Implement `QuizService` state machine with strict phase guards.
12. Validate setup (name, topics, count, time, available question pool) and recheck at Start.
13. Integrate Alaa's approved `AdaptiveEngine` and `select_question` via dependency injection/mocks until real implementation is available.
14. Ensure one selection adds ID to used set, one Submit adds one answer and updates engine once.
15. Implement normal completion using the approved result retrieval method; calculate score through Alaa's `calculate_score`.
16. Implement monotonic deadline handling, timeout and abandon according to **approved** policies.

### Phase 3 — persistence

17. Implement `AttemptRepository` using shared DB connection and schema.
18. Persist attempt and answer rows atomically; handle rollback and retry without duplicate inserts.
19. Query usage counts through agreed interface for deterministic selection; never place SQL in widget or algorithm.
20. Test reopening database and retrieving saved answers, statuses, and score totals.

### Phase 4 — integration

21. Replace mocks with Jana's real active-question read service and Alaa's real engine.
22. Have integration owner wire `QuizSessionPage` into S3 of `MainWindow` and implement closeEvent/sidebar guard.
23. Confirm Menna's results page sees saved COMPLETED/TIMED_OUT/ABANDONED attempts and answer details.
24. Run full integration flow and the worked-example replay.
25. Open PR with evidence, request review, resolve issues, and merge only after shared tests pass.

---

## 14. Automated tests — write and run

Create `tests/test_quiz.py` with pytest fixtures for isolated temporary SQLite DB and fake clock. Keep GUI tests separate where practical; core service tests should run without launching a visible window.

**Required / high-priority:**

1. `test_setup_rejects_short_name` — 1-character name raises ValidationError.
2. `test_setup_rejects_count_outside_5_to_30` — invalid counts rejected.
3. `test_start_requires_enough_active_questions` — insufficient bank blocks start.
4. `test_first_question_targets_medium` — engine starts at 2 (actual asked may fallback; test with available Medium question).
5. `test_submit_requires_selection` — no valid option rejected.
6. `test_double_submit_records_once` — exactly one record and engine transition.
7. `test_next_before_submit_rejected` — cannot skip.
8. `test_no_repeated_question_ids` — one attempt has distinct question IDs.
9. `test_timeout_persists_status_and_unanswered` — per approved timeout policy; score denominator correct.
10. `test_abandon_persists_after_confirmation` — `ABANDONED` and appropriate answer rows.
11. `test_cancel_close_does_not_abandon` — integration/UI close guard; state preserved.
12. `test_finish_is_idempotent` — repeated timer/close callback does not duplicate attempts.
13. `test_atomic_save_rolls_back_on_duplicate_answer` — no partial attempt persisted.
14. `test_worked_example_integration` — eight-answer sequence matches 12/21 and 57.1%.
15. `test_persistence_reopen` — saved attempt and answers readable from a new connection.
16. `test_deadline_submit_race` — late answer rejected and timeout saved once.

**Catalog tests Rawan must help integrate:** T-01, T-03, T-04 and T-06. Alaa owns core algorithm unit tests, but Rawan must prove the **quiz service calls the algorithm correctly**. Do not duplicate Alaa's algorithm in tests or service.

Suggested commands:

```bash
python -m pytest tests/test_quiz.py -q
python -m pytest -q
python main.py
```

When reporting results, include actual command output and test count. If a test cannot run because a shared dependency is not yet merged, mark it **BLOCKED**, not **PASSED**.

---

## 15. GitHub workflow — exact steps

**Never work directly on `main`.**

```bash
git clone <YOUR_REPO_URL>
cd <YOUR_REPO_FOLDER>
git switch main
git pull --ff-only
git switch -c feature/m2-quiz-session
```

If the repository was already cloned, skip `git clone`. Confirm branch:

```bash
git branch --show-current
```

Work in small commits:

```bash
git status
git add ui/quiz_session.py
git commit -m "feat(m2): add quiz setup and question UI"

git add services/quiz_service.py tests/test_quiz.py
git commit -m "feat(m2): implement guarded quiz lifecycle"

git add database/repositories/attempt_repository.py tests/test_quiz.py
git commit -m "feat(m2): persist finished attempts atomically"
```

Run tests before pushing:

```bash
python -m pytest -q
git status
git push -u origin feature/m2-quiz-session
```

Open a GitHub **Pull Request** from `feature/m2-quiz-session` into `main`. PR should contain:

- **Scope:** FR-03/FR-04 and S3.
- **Summary:** what setup, session, timer, timeout, abandon and persistence do.
- **Changed files:** enumerate paths.
- **Contracts:** confirm no schema/API drift; link any approved changes.
- **Testing:** actual commands/results, including edge cases.
- **Screenshots:** setup, active question, feedback, timer warning, finished state.
- **Dependencies:** Jana's question reads, Alaa's engine, shared shell wiring, Menna's results refresh.
- **Known limitations/blockers:** clearly stated.

Request review from at least one teammate. Do not merge until integration owner confirms compatibility. After merge, all teammates update `main` before continuing work.

**Shared file changes:** open a separate reviewed change request; don't quietly commit modified `schema.sql`, `models/quiz.py`, `ui/main_window.py`, `requirements.txt` or other owners' files on Rawan's branch.

---

## 16. Common mistakes to actively prevent

- Implementing difficulty adjustment twice (in `QuizService` and in Alaa's engine).
- Confusing target difficulty with actual selected question difficulty after fallback.
- Treating `is_active` as “unused” and deactivating questions after attempts.
- Letting Submit or Next fire twice; duplicate answers or skipped questions.
- Starting a new timer for every question or pausing time accidentally during feedback.
- Using `QTimer` ticks as the only clock and losing time when GUI stalls.
- Saving `COMPLETED` at quiz start because schema lacks `IN_PROGRESS`.
- Saving attempt header first and failing halfway through answer inserts.
- Calling sqlite3 from Qt widgets or sharing sqlite connections across threads.
- Fabricating IDs for unanswered questions after timeout.
- Counting unshown questions in ABANDONED without team agreement.
- Allowing the sidebar to navigate away while quiz active.
- Closing app before abandonment commit succeeds.
- Mixing percentage with raw earned points in results.
- Hardcoding question lists instead of consuming Jana's validated data.
- Creating a second QMainWindow or a fifth primary screen.
- Writing tests against mocked algorithm behavior and presenting them as full integration tests.

---

## 17. Definition of Done — Rawan's checklist

- [ ] Shared foundation read; pending team decisions resolved and recorded.
- [ ] Only assigned files edited (or shared edits approved).
- [ ] S3 setup validates name/topics/count/time and available question count.
- [ ] First question starts at Medium when available.
- [ ] Four radio options, correct progress, difficulty badge, countdown.
- [ ] Submit disabled without selection; feedback includes explanation.
- [ ] Next cannot skip; double-click cannot duplicate.
- [ ] Deterministic no-repeat selection via Alaa's engine.
- [ ] Timer amber <=60s and red <=10s; timeout handled once.
- [ ] Timed-out unanswered answers persisted according to approved policy.
- [ ] Confirmed app close saves ABANDONED; cancelled close preserves attempt.
- [ ] Sidebar navigation blocked while active; unlocked on successful finish.
- [ ] Weighted score calculated via M3, not duplicated in M2.
- [ ] All writes parameterized and atomic; foreign keys enabled.
- [ ] COMPLETED, TIMED_OUT, ABANDONED visible to Menna's history/review.
- [ ] All relevant pytest tests actually run and pass; full app launches.
- [ ] No traceback shown to users; errors logged and handled.
- [ ] PR includes screenshots, tests, contract notes, and teammate review.

---

## 18. Ready-to-copy prompt for Rawan's AI coding tool

> You are implementing QuizForge from the project root. Read `QUIZFORGE_SHARED_FOUNDATION.md` and `02_RAWAN_QUIZ_SESSION.md`. University catalog requirements FR-03/FR-04 and S3 are mandatory. Follow the 2026-11-27 implementation baseline and retain the blank team approval record. The project owner has authorized the cross-module integration and UI work in this repository. Use the canonical models, typed errors, services, repositories, and four-screen shell. Use Alaa's pure adaptive engine; do not add SQL to widgets or Qt to algorithms, and do not change the schema. Implement phase guards, deterministic no-repeat selection, exactly-once Submit, monotonic timekeeping, amber/red timer states, atomic persistence, timeout, safe abandonment, analytics and results. Write and run relevant pytest tests; never claim a test passed unless it ran. Finish with modified files, actual test output, launch steps, and remaining delivery limitations. Do not claim teammate approval.

---

**End of Rawan guide.** Next document: `03_ALAA_ADAPTIVE_ENGINE.md`. This guide is intentionally explicit about unresolved team decisions: **do not treat proposals as already approved contracts.**


## V2 cross-file contract reconciliation (implementation baseline; team review pending)

**V2 module-specific implementation:** `QuizService` exposes `get_result() -> QuizResult | None`; `next_question()` finalizes and returns None when done. The repository saves attempts atomically and provides historical usage counts. Use shared `init_db()`/`get_connection()` and only `data/quizforge.db`. Service owns a monotonic deadline, timeout wins over late Submit, and terminal results are cached. Timeout creates distinct deterministic unanswered records up to the requested count without streak updates; abandon records submitted answers plus the current unanswered question only. Save actual selected `Question.difficulty` as `level_asked`. DTOs are frozen and shared from canonical model files. These are project implementation choices, not instructor rules; team review remains pending.



## V3 CANONICAL NAME REGISTRY — READ BEFORE IMPLEMENTATION

**Status: one consistent implementation baseline selected by the project owner on 2026-11-27; team review pending.** If an earlier section in this guide says a DTO/API is undefined or suggests a different name/signature, this registry and Shared Foundation §15 take precedence. Do not interpret this as teammate approval. The university catalog takes precedence over all proposals.

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

**Names are case-sensitive.** Use `data/quizforge.db` only via the shared connection factory. `QuizConfig.time_limit_seconds` is in seconds; the selected UI range is 60–7200 seconds, default 600 seconds. Store timestamps in UTC ISO format `YYYY-MM-DDTHH:MM:SS+00:00`; date filters use UTC `started_at`. `QuizSessionPage` receives a service instance; the M2 shell exposes `navigationLockChanged(bool)` and confirms/saves active attempts on close. `get_result()` is the normal completion result accessor. This repository has no S1/S2/S4 navigation pages; integration remains limited to the available M2 module.

**Important behavior clarification:** `validate_setup` and `start` reject a pool smaller than the requested question count; a quiz may end early if its pool changes while running or if eligible questions become unavailable. This is not permission to begin an underfilled quiz. Do not count an unseen timeout placeholder as a question shown to the learner; distinguish presented vs recorded counts. `AnswerFeedback.earned_for_question` is based on actual `level_asked`.

**Approval checklist:** Jana ___ / Rawan ___ / Alaa ___ / Menna ___ / integration owner ___ / approved commit ___ . These fields remain open for the team; they do not block the implementation already authorized by the project owner.
