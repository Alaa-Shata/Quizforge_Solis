"""Interactive developer demo for Module 3 (Adaptive Engine & Weighted Scoring).

STANDALONE DEV TOOL - not a production screen and not part of the 4-screen app.
All adaptive decisions come from algorithms.adaptive_engine; this file only
renders them. Run from the project root:

    python -m demo.adaptive_demo
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from string import Template
from typing import Optional

if __package__ in (None, ""):  # allow `python demo/adaptive_demo.py`
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QGraphicsDropShadowEffect, QGridLayout,
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QRadioButton, QScrollArea,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from algorithms.adaptive_engine import (
    LEVEL_NAMES, MAX_LEVEL, MIN_LEVEL, AdaptiveEngine, EngineDiagnostics,
    calculate_score, select_question,
)

SESSION_LENGTH = 10


# --------------------------------------------------------------------------
# DEMO-ONLY fixtures. Stand-ins for the shared Question / AnswerRecord models,
# carrying only the attributes the engine reads (+ display fields).
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DemoQuestion:
    id: int
    difficulty: int
    topic: str
    text: str
    options: tuple[str, str, str, str]
    correct_index: int
    explanation: str
    is_active: bool = True


@dataclass(frozen=True)
class DemoAnswer:
    question_id: int
    level_asked: int
    is_correct: Optional[bool]


QUESTIONS: tuple[DemoQuestion, ...] = (
    # Easy
    DemoQuestion(1, 1, "Python", "Which keyword defines a function in Python?",
                 ("func", "def", "function", "lambda def"), 1,
                 "`def` starts a function definition; `lambda` creates anonymous functions."),
    DemoQuestion(2, 1, "Data Structures", "Which structure follows First-In, First-Out (FIFO)?",
                 ("Stack", "Queue", "Tree", "Graph"), 1,
                 "A queue removes items in the same order they were added."),
    DemoQuestion(3, 1, "Databases", "Which SQL statement reads rows from a table?",
                 ("INSERT", "UPDATE", "SELECT", "DELETE"), 2,
                 "SELECT queries data; the others modify it."),
    DemoQuestion(4, 1, "Networking", "What is the default port for HTTPS?",
                 ("80", "21", "443", "8080"), 2,
                 "HTTPS uses TCP port 443; plain HTTP uses 80."),
    DemoQuestion(5, 1, "Python", "What does len([3, 1, 4]) return?",
                 ("2", "3", "4", "8"), 1,
                 "len() counts the items in the list: three."),
    # Medium
    DemoQuestion(6, 2, "Algorithms", "What is the time complexity of binary search?",
                 ("O(n)", "O(log n)", "O(n log n)", "O(1)"), 1,
                 "Each step halves the remaining search space, giving O(log n)."),
    DemoQuestion(7, 2, "Python", "Which of these types is immutable?",
                 ("list", "dict", "set", "tuple"), 3,
                 "Tuples cannot be changed after creation; lists, dicts and sets can."),
    DemoQuestion(8, 2, "Databases", "Which constraint guarantees a column has no duplicates?",
                 ("NOT NULL", "UNIQUE", "CHECK", "DEFAULT"), 1,
                 "UNIQUE rejects duplicate values; a PRIMARY KEY implies it too."),
    DemoQuestion(9, 2, "Data Structures", "A hash table lookup is, on average…",
                 ("O(1)", "O(log n)", "O(n)", "O(n²)"), 0,
                 "Hashing jumps straight to a bucket, so average lookup is constant time."),
    DemoQuestion(10, 2, "Networking", "Which protocol resolves domain names to IP addresses?",
                 ("DHCP", "ARP", "DNS", "FTP"), 2,
                 "DNS maps names like example.com to IP addresses."),
    # Hard
    DemoQuestion(11, 3, "Algorithms", "Dijkstra's algorithm fails with which kind of edges?",
                 ("Weighted edges", "Negative weights", "Directed edges", "Cyclic paths"), 1,
                 "Dijkstra assumes a settled node never improves; negative weights break that."),
    DemoQuestion(12, 3, "Python", "What does the GIL primarily restrict in CPython?",
                 ("Memory usage", "Parallel bytecode threads", "File I/O", "Recursion depth"), 1,
                 "Only one thread executes Python bytecode at a time under the GIL."),
    DemoQuestion(13, 3, "Databases", "Which isolation level prevents phantom reads?",
                 ("Read Uncommitted", "Read Committed", "Repeatable Read", "Serializable"), 3,
                 "Only Serializable guarantees no phantom rows in the SQL standard."),
    DemoQuestion(14, 3, "Data Structures", "Worst-case height of an AVL tree with n nodes?",
                 ("O(n)", "O(log n)", "O(√n)", "O(1)"), 1,
                 "AVL rebalancing keeps the height logarithmic in every case."),
    DemoQuestion(15, 3, "Algorithms", "Which problem is NP-complete?",
                 ("Sorting", "Shortest path", "Boolean satisfiability", "Binary search"), 2,
                 "SAT was the first problem proven NP-complete (Cook–Levin)."),
)


# --------------------------------------------------------------------------
# Design tokens + QSS
# --------------------------------------------------------------------------

TOKENS = dict(
    bg="#F3FAF7", surface="#FFFFFF", border="#DDEFE8", border_strong="#BFE3D6",
    text="#0F2A2E", muted="#5B7378", primary="#0A7C6E", primary_hover="#086A5E",
    primary_pressed="#065A50", primary_soft="#E2F5EF", focus="#2BB39A",
    success="#0B7A55", success_soft="#E4F7EE", danger="#B4232A", danger_soft="#FDECEC",
    l1_bg="#E4F7EE", l1_fg="#0B7A55", l2_bg="#FFF3DC", l2_fg="#8A5300",
    l3_bg="#FDE8EC", l3_fg="#A1203A", radius="14px", radius_sm="10px",
)
CHART_COLORS = dict(correct="#10B981", wrong="#EF6461", pending="#BFE3D6",
                    grid="#E3F1EC", label="#5B7378")

QSS = Template("""
* { font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif; color: $text; }
QWidget#root, QWidget#canvas { background: $bg; }
QScrollArea { background: transparent; border: none; }

QFrame#header { background: $surface; border-bottom: 1px solid $border; }
QLabel#logo { background: $primary; color: white; border-radius: 10px;
              font-size: 18px; font-weight: 700; }
QLabel#brand { font-size: 20px; font-weight: 700; }
QLabel#subtitle { color: $muted; font-size: 13px; }
QLabel#devBadge { background: $primary_soft; color: $primary; border-radius: 9px;
                  padding: 3px 10px; font-size: 11px; font-weight: 600; }

QFrame#card { background: $surface; border: 1px solid $border; border-radius: $radius; }
QLabel#cardTitle { font-size: 12px; font-weight: 700; color: $muted; }
QLabel#muted { color: $muted; font-size: 12px; }
QLabel#questionNo { font-size: 13px; font-weight: 600; color: $muted; }
QLabel#questionText { font-size: 18px; font-weight: 600; }
QLabel#emptyTitle { font-size: 20px; font-weight: 700; }
QLabel#emptyIcon { background: $primary_soft; color: $primary; border-radius: 28px;
                   font-size: 26px; font-weight: 700; }

QLabel#chip { border-radius: 9px; padding: 3px 10px; font-size: 12px; font-weight: 600;
              background: $primary_soft; color: $primary; }
QLabel#chip[tone="1"] { background: $l1_bg; color: $l1_fg; }
QLabel#chip[tone="2"] { background: $l2_bg; color: $l2_fg; }
QLabel#chip[tone="3"] { background: $l3_bg; color: $l3_fg; }
QLabel#chip[tone="warn"] { background: $l2_bg; color: $l2_fg; }

QPushButton { border-radius: $radius_sm; padding: 9px 18px; font-size: 14px; font-weight: 600;
              min-height: 22px; }
QPushButton#primary { background: $primary; color: white; border: 2px solid $primary; }
QPushButton#primary:hover { background: $primary_hover; border-color: $primary_hover; }
QPushButton#primary:pressed { background: $primary_pressed; }
QPushButton#primary:focus { border-color: $focus; }
QPushButton#secondary { background: $surface; color: $primary; border: 1px solid $border_strong; }
QPushButton#secondary:hover { background: $primary_soft; }
QPushButton#secondary:focus { border: 2px solid $focus; }
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#secondary:disabled {
    background: #EEF3F2; color: #9AAEAB; border: 1px solid #E1E9E7; }

QRadioButton#option { background: $surface; border: 1px solid $border; border-radius: $radius_sm;
                      padding: 8px 14px; font-size: 15px; spacing: 12px; }
QRadioButton#option::indicator { width: 14px; height: 14px; border-radius: 9px;
                                 border: 2px solid $border_strong; background: $surface; }
QRadioButton#option::indicator:checked { border: 5px solid $primary; width: 8px; height: 8px; }
QRadioButton#option::indicator:disabled { border-color: #D5E3DF; }
QRadioButton#option::indicator:checked:disabled { border-color: #8FB8AF; }
QRadioButton#option:hover { border-color: $border_strong; background: #F8FCFB; }
QRadioButton#option:focus { border: 2px solid $focus; }
QRadioButton#option:checked { border: 2px solid $primary; background: $primary_soft; }
QRadioButton#option:disabled { color: $muted; background: #FAFCFC; }
QRadioButton#option[state="correct"], QRadioButton#option[state="correct"]:disabled {
    border: 2px solid $success; background: $success_soft; color: $success; font-weight: 600; }
QRadioButton#option[state="wrong"], QRadioButton#option[state="wrong"]:disabled {
    border: 2px solid $danger; background: $danger_soft; color: $danger; font-weight: 600; }

QFrame#feedback { border-radius: $radius_sm; border: 1px solid $border; background: $primary_soft; }
QFrame#feedback[kind="success"] { background: $success_soft; border-color: #BDE9D3; }
QFrame#feedback[kind="error"] { background: $danger_soft; border-color: #F5C2C4; }
QLabel#feedbackTitle { font-size: 15px; font-weight: 700; background: transparent; }
QLabel#feedbackTitle[kind="success"] { color: $success; }
QLabel#feedbackTitle[kind="error"] { color: $danger; }
QLabel#feedbackBody { font-size: 13px; background: transparent; }

QLabel#levelSeg { background: #F1F7F5; color: $muted; border: 1px solid $border;
                  border-radius: $radius_sm; font-size: 13px; font-weight: 600; padding: 8px 4px; }
QLabel#levelSeg[active="true"] { background: $primary; color: white; border-color: $primary; }
QLabel#levelBig { font-size: 26px; font-weight: 700; color: $primary; }

QLabel#kvKey { color: $muted; font-size: 13px; }
QLabel#kvValue { font-size: 13px; font-weight: 600; }
QLabel#reason { background: $primary_soft; border-radius: $radius_sm; padding: 10px 12px;
                font-size: 13px; }

QFrame#tile { background: #F7FBFA; border: 1px solid $border; border-radius: $radius_sm; }
QLabel#tileValue { font-size: 20px; font-weight: 700; background: transparent; }
QLabel#tileCaption { color: $muted; font-size: 11px; background: transparent; }
QLabel#scoreBig { font-size: 30px; font-weight: 700; color: $primary; }
QProgressBar { background: #E8F3EF; border: none; border-radius: 5px; max-height: 10px; }
QProgressBar::chunk { background: $primary; border-radius: 5px; }
QLabel#legendDot { border-radius: 5px; }
""").substitute(TOKENS)


# --------------------------------------------------------------------------
# Small UI helpers
# --------------------------------------------------------------------------

def label(text: str = "", name: str = "", wrap: bool = False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(objectName="card")
    shadow = QGraphicsDropShadowEffect(frame, blurRadius=28, xOffset=0, yOffset=4)
    shadow.setColor(QColor(10, 90, 75, 20))
    frame.setGraphicsEffect(shadow)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(20, 18, 20, 20)
    lay.setSpacing(12)
    if title:
        lay.addWidget(label(title.upper(), "cardTitle"))
    return frame, lay


def button(text: str, name: str, slot, tip: str = "") -> QPushButton:
    b = QPushButton(text, objectName=name)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.clicked.connect(slot)
    if tip:
        b.setToolTip(tip)
    return b


def set_prop(w: QWidget, name: str, value) -> None:
    """Set a dynamic property and re-apply QSS so property selectors update."""
    w.setProperty(name, value)
    w.style().unpolish(w)
    w.style().polish(w)


def streak_dots(n: int) -> str:
    on, off = TOKENS["primary"], TOKENS["border_strong"]
    dots = "".join(f"<span style='color:{on if i < n else off}; font-size:16px'>●</span>"
                   for i in range(2))
    return f"{dots}&nbsp;&nbsp;&nbsp;{n} / 2"


class ProgressionChart(QWidget):
    """Bars per presented question: height = difficulty asked, colour = outcome."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[int, Optional[bool]]] = []
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAccessibleName("Difficulty progression chart")

    def set_items(self, items: list[tuple[int, Optional[bool]]]) -> None:
        self.items = list(items)
        desc = ", ".join(f"Q{i + 1} {LEVEL_NAMES[d]}" for i, (d, _) in enumerate(items))
        self.setAccessibleDescription(desc or "No questions yet")
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, top, bottom = 58, 8, 22
        plot_h = self.height() - top - bottom
        plot_w = self.width() - left - 6
        small = QFont(self.font())
        small.setPointSizeF(8.5)
        p.setFont(small)

        for lvl in range(MIN_LEVEL, MAX_LEVEL + 1):
            y = top + plot_h - plot_h * lvl / MAX_LEVEL
            p.setPen(QColor(CHART_COLORS["grid"]))
            p.drawLine(left, int(y), self.width() - 6, int(y))
            p.setPen(QColor(CHART_COLORS["label"]))
            p.drawText(QRectF(0, y - 9, left - 8, 18),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, LEVEL_NAMES[lvl])

        if not self.items:
            p.drawText(QRectF(left, top, plot_w, plot_h), Qt.AlignmentFlag.AlignCenter,
                       "Questions you answer will appear here")
            return

        slot = plot_w / max(len(self.items), SESSION_LENGTH)
        bar_w = min(34.0, slot * 0.62)
        for i, (lvl, ok) in enumerate(self.items):
            colour = CHART_COLORS["pending" if ok is None else "correct" if ok else "wrong"]
            h = plot_h * lvl / MAX_LEVEL
            x = left + i * slot + (slot - bar_w) / 2
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(colour))
            p.drawRoundedRect(QRectF(x, top + plot_h - h, bar_w, h), 6, 6)
            p.setPen(QColor(CHART_COLORS["label"]))
            p.drawText(QRectF(x - 6, top + plot_h + 3, bar_w + 12, bottom - 3),
                       Qt.AlignmentFlag.AlignCenter, f"Q{i + 1}")


# --------------------------------------------------------------------------
# Main demo widget
# --------------------------------------------------------------------------

class AdaptiveDemo(QWidget):
    PAGE_EMPTY, PAGE_QUESTION, PAGE_DONE = range(3)

    def __init__(self) -> None:
        super().__init__(objectName="root")
        self.setWindowTitle("QuizForge — Adaptive Engine Demo (dev tool)")
        self.setMinimumSize(1100, 700)
        # Usage history survives Reset on purpose: it shows "prefer less-used questions".
        self.times_used: dict[int, int] = {}
        self._new_session_state()
        self._build_ui()
        self._bind_keys()
        self._render_all()

    # ---------------------------------------------------------------- state
    def _new_session_state(self) -> None:
        self.engine = AdaptiveEngine()
        self.used_ids: set[int] = set()
        self.answers: list[DemoAnswer] = []
        self.history: list[tuple[int, Optional[bool]]] = []
        self.current: Optional[DemoQuestion] = None
        self.target_when_asked = self.engine.level
        self.answered = False
        self.seen_before = 0
        self.started = False
        self.finished_reason = ""
        self.decision: Optional[tuple[EngineDiagnostics, EngineDiagnostics, bool]] = None

    # ---------------------------------------------------------------- layout
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        scroll = QScrollArea(widgetResizable=True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        canvas = QWidget(objectName="canvas")
        scroll.setWidget(canvas)
        root.addWidget(scroll, 1)

        body = QHBoxLayout(canvas)
        body.setContentsMargins(24, 22, 24, 24)
        body.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(20)
        left.addWidget(self._build_question_card(), 1)
        left.addWidget(self._build_progression_card())
        body.addLayout(left, 3)

        right_box = QWidget()
        right_box.setMinimumWidth(330)
        right_box.setMaximumWidth(430)
        right = QVBoxLayout(right_box)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(20)
        right.addWidget(self._build_level_card())
        right.addWidget(self._build_decision_card())
        right.addWidget(self._build_score_card())
        right.addStretch(1)
        body.addWidget(right_box, 2)

    def _build_header(self) -> QFrame:
        header = QFrame(objectName="header")
        header.setFixedHeight(76)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(24, 12, 24, 12)
        lay.setSpacing(12)
        logo = label("Q", "logo")
        logo.setFixedSize(42, 42)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("QuizForge", "brand"))
        names.addWidget(label("Adaptive Learning Engine", "subtitle"))
        lay.addLayout(names)
        badge = label("DEV DEMO · Module 3", "devBadge")
        badge.setToolTip("Standalone developer tool, not a production screen")
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch(1)
        self.start_btn = button("Start Demo", "primary", self.start_session, "Start a new session (Ctrl+N)")
        self.reset_btn = button("Reset Session", "secondary", self.reset_session, "Clear the session (Ctrl+R)")
        lay.addWidget(self.reset_btn)
        lay.addWidget(self.start_btn)
        return header

    def _build_question_card(self) -> QFrame:
        frame, lay = card()
        self.stack = QStackedWidget()
        lay.addWidget(self.stack)

        # Empty state
        self.stack.addWidget(self._centered_state(
            "?", "Ready when you are",
            "Press <b>Start Demo</b> to begin a 10-question adaptive session. "
            "Every question is picked by <b>select_question()</b> and every answer "
            "is fed to <b>AdaptiveEngine.record_answer()</b>.",
            "Start Demo"))

        # Question page
        page = QWidget()
        q = QVBoxLayout(page)
        q.setContentsMargins(0, 0, 0, 0)
        q.setSpacing(14)
        meta = QHBoxLayout()
        meta.setSpacing(8)
        self.q_number = label("", "questionNo")
        self.q_topic = label("", "chip")
        self.q_level = label("", "chip")
        self.q_fallback = label("Fallback", "chip")
        set_prop(self.q_fallback, "tone", "warn")
        self.q_seen = label("", "muted")
        for w in (self.q_number, self.q_topic, self.q_level, self.q_fallback):
            meta.addWidget(w)
        meta.addStretch(1)
        meta.addWidget(self.q_seen)
        q.addLayout(meta)

        self.q_text = label("", "questionText", wrap=True)
        q.addWidget(self.q_text)

        self.option_group = QButtonGroup(self)
        self.options: list[QRadioButton] = []
        for i in range(4):
            rb = QRadioButton(objectName="option")
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setMinimumHeight(42)
            self.option_group.addButton(rb, i)
            self.options.append(rb)
            q.addWidget(rb)
        self.option_group.idToggled.connect(lambda *_: self._sync_buttons())

        self.feedback = QFrame(objectName="feedback")
        fb = QVBoxLayout(self.feedback)
        fb.setContentsMargins(14, 10, 14, 12)
        fb.setSpacing(4)
        self.feedback_title = label("", "feedbackTitle")
        self.feedback_body = label("", "feedbackBody", wrap=True)
        fb.addWidget(self.feedback_title)
        fb.addWidget(self.feedback_body)
        q.addWidget(self.feedback)
        q.addStretch(1)

        actions = QHBoxLayout()
        actions.addWidget(label("Keys: 1–4 choose · Enter submit / next · Ctrl+R reset", "muted"))
        actions.addStretch(1)
        self.submit_btn = button("Submit Answer", "primary", self.submit_answer)
        self.next_btn = button("Next Question", "secondary", self.next_question)
        actions.addWidget(self.submit_btn)
        actions.addWidget(self.next_btn)
        q.addLayout(actions)
        self.stack.addWidget(page)

        # Completion page
        self.done_page = self._centered_state("✓", "Session complete", "", "Start New Session")
        self.stack.addWidget(self.done_page)
        return frame

    def _centered_state(self, icon: str, title: str, body: str, action: str) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(48, 0, 48, 0)
        lay.setSpacing(12)
        lay.addStretch(1)
        ic = label(icon, "emptyIcon")
        ic.setFixedSize(56, 56)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignHCenter)
        t = label(title, "emptyTitle")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        b = label(body, "muted", wrap=True)
        b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(b)  # no alignment flag: Qt then sizes wrapped text height correctly
        page.body = b  # type: ignore[attr-defined]
        lay.addWidget(button(action, "primary", self.start_session), 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(1)
        return page

    def _build_progression_card(self) -> QFrame:
        frame, lay = card()
        head = QHBoxLayout()
        head.addWidget(label("DIFFICULTY PROGRESSION", "cardTitle"))
        head.addStretch(1)
        for key, text in (("correct", "Correct"), ("wrong", "Wrong"), ("pending", "Pending")):
            dot = label("", "legendDot")
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background: {CHART_COLORS[key]};")
            head.addWidget(dot)
            head.addWidget(label(text, "muted"))
            head.addSpacing(8)
        lay.addLayout(head)
        self.chart = ProgressionChart()
        lay.addWidget(self.chart)
        return frame

    def _build_level_card(self) -> QFrame:
        frame, lay = card("Target difficulty")
        self.level_big = label("", "levelBig")
        lay.addWidget(self.level_big)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.level_segs = {}
        for lvl in range(MIN_LEVEL, MAX_LEVEL + 1):
            seg = label(f"{lvl} · {LEVEL_NAMES[lvl]}", "levelSeg")
            seg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(seg, 1)
            self.level_segs[lvl] = seg
        lay.addLayout(row)
        self.level_caption = label("", "muted", wrap=True)
        lay.addWidget(self.level_caption)
        return frame

    def _build_decision_card(self) -> QFrame:
        frame, lay = card("Adaptive decision")
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        self.kv = {}
        rows = ("Current target", "Correct streak", "Wrong streak", "Previous level", "New level")
        for r, key in enumerate(rows):
            grid.addWidget(label(key, "kvKey"), r, 0)
            v = label("", "kvValue")
            grid.addWidget(v, r, 1)
            self.kv[key] = v
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        self.reason = label("", "reason", wrap=True)
        lay.addWidget(self.reason)
        return frame

    def _build_score_card(self) -> QFrame:
        frame, lay = card("Weighted score")
        top = QHBoxLayout()
        self.score_big = label("", "scoreBig")
        top.addWidget(self.score_big)
        top.addStretch(1)
        top.addWidget(label("Easy 1 · Medium 2 · Hard 3", "muted"), 0, Qt.AlignmentFlag.AlignBottom)
        lay.addLayout(top)
        self.score_bar = QProgressBar(textVisible=False, maximum=1000)
        lay.addWidget(self.score_bar)
        tiles = QGridLayout()
        tiles.setSpacing(8)
        self.tiles = {}
        for i, key in enumerate(("Correct", "Incorrect", "Earned points", "Maximum points")):
            t = QFrame(objectName="tile")
            tl = QVBoxLayout(t)
            tl.setContentsMargins(12, 8, 12, 8)
            tl.setSpacing(0)
            v = label("0", "tileValue")
            tl.addWidget(v)
            tl.addWidget(label(key, "tileCaption"))
            tiles.addWidget(t, i // 2, i % 2)
            self.tiles[key] = v
        lay.addLayout(tiles)
        return frame

    def _bind_keys(self) -> None:
        for seq in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            QShortcut(QKeySequence(seq), self, activated=self._primary_action)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.reset_session)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.start_session)
        for i in range(4):
            QShortcut(QKeySequence(str(i + 1)), self, activated=lambda i=i: self._choose(i))

    # ---------------------------------------------------------------- actions
    def start_session(self) -> None:
        self._new_session_state()
        self.started = True
        self.next_question()

    def reset_session(self) -> None:
        self._new_session_state()
        self._render_all()

    def next_question(self) -> None:
        if not self.started or self.finished_reason:
            return
        if self.current is not None and not self.answered:
            return  # cannot skip an unanswered question
        if len(self.answers) >= SESSION_LENGTH:
            return self._finish(f"All {SESSION_LENGTH} questions answered.")
        try:
            q = select_question(QUESTIONS, self.used_ids, self.engine.level, self.times_used)
        except (TypeError, ValueError) as exc:
            return self._show_error("Could not select a question", str(exc))
        if q is None:
            return self._finish("The question pool ran out of unused questions.")

        self.current = q
        self.target_when_asked = self.engine.level
        self.answered = False
        self.seen_before = self.times_used.get(q.id, 0)
        self.used_ids.add(q.id)
        self.times_used[q.id] = self.seen_before + 1
        self.history.append((q.difficulty, None))
        self._render_all()
        self.options[0].setFocus()

    def submit_answer(self) -> None:
        if self.current is None or self.answered:
            return  # guards double submission (button is also disabled)
        choice = self.option_group.checkedId()
        if choice < 0:
            return self._show_error("Pick an answer first", "Select one of the four options, then submit.")
        self.answered = True
        self.submit_btn.setEnabled(False)

        q = self.current
        ok = choice == q.correct_index
        before = self.engine.diagnostics()
        self.engine.record_answer(ok)
        self.decision = (before, self.engine.diagnostics(), ok)
        self.answers.append(DemoAnswer(q.id, q.difficulty, ok))
        self.history[-1] = (q.difficulty, ok)
        self._render_all()
        self.next_btn.setFocus()

    def _primary_action(self) -> None:
        if self.stack.currentIndex() != self.PAGE_QUESTION:
            self.start_session()
        elif self.submit_btn.isEnabled():
            self.submit_answer()
        elif self.next_btn.isEnabled():
            self.next_question()

    def _choose(self, i: int) -> None:
        if self.current is not None and not self.answered:
            self.options[i].setChecked(True)
            self.options[i].setFocus()

    def _finish(self, reason: str) -> None:
        self.finished_reason = reason
        self.current = None
        self._render_all()

    def _show_error(self, title: str, body: str) -> None:
        self.feedback_title.setText(title)
        self.feedback_body.setText(body)
        self._set_feedback_kind("error")

    def _set_feedback_kind(self, kind: str) -> None:
        set_prop(self.feedback, "kind", kind)
        set_prop(self.feedback_title, "kind", kind)  # Qt doesn't re-polish children
        self.feedback.show()

    # ---------------------------------------------------------------- rendering
    def _render_all(self) -> None:
        self._render_question()
        self._render_level()
        self._render_decision()
        self._render_score()
        self.chart.set_items(self.history)
        self.start_btn.setText("Restart Demo" if self.started else "Start Demo")

    def _sync_buttons(self) -> None:
        live = self.current is not None
        self.submit_btn.setEnabled(live and not self.answered and self.option_group.checkedId() >= 0)
        self.next_btn.setEnabled(live and self.answered)
        last = len(self.answers) >= SESSION_LENGTH
        self.next_btn.setText("See Results" if last else "Next Question")

    def _render_question(self) -> None:
        self._sync_buttons()
        if self.finished_reason:
            s = calculate_score(self.answers)
            self.done_page.body.setText(
                f"{self.finished_reason}<br>You earned <b>{s.earned} of {s.maximum}</b> weighted points "
                f"(<b>{s.percentage:.1f}%</b>) across {len(self.answers)} questions.")
            self.stack.setCurrentIndex(self.PAGE_DONE)
            return
        if self.current is None:
            self.stack.setCurrentIndex(self.PAGE_EMPTY)
            return
        self.stack.setCurrentIndex(self.PAGE_QUESTION)
        q = self.current
        self.q_number.setText(f"Question {len(self.history)} of {SESSION_LENGTH}")
        self.q_topic.setText(q.topic)
        self.q_level.setText(LEVEL_NAMES[q.difficulty])
        set_prop(self.q_level, "tone", str(q.difficulty))
        self.q_fallback.setVisible(q.difficulty != self.target_when_asked)
        self.q_fallback.setToolTip(
            f"No unused {LEVEL_NAMES[self.target_when_asked]} questions left; nearest level chosen.")
        self.q_seen.setText(f"Seen {self.seen_before}× in earlier sessions")
        self.q_text.setText(q.text)

        if not self.answered:
            self.option_group.setExclusive(False)  # allow clearing the previous choice
            for rb in self.options:
                rb.setChecked(False)
            self.option_group.setExclusive(True)
        chosen = self.option_group.checkedId()
        for i, (rb, text) in enumerate(zip(self.options, q.options)):
            rb.setText(f"{chr(65 + i)}.  {text}")
            rb.setEnabled(not self.answered)
            state = ""
            if self.answered and i == q.correct_index:
                state = "correct"
            elif self.answered and i == chosen:
                state = "wrong"
            set_prop(rb, "state", state)

        if self.answered:
            ok = chosen == q.correct_index
            self.feedback_title.setText(
                f"Correct! +{q.difficulty} point{'s' if q.difficulty > 1 else ''}" if ok
                else f"Not quite. The answer is {chr(65 + q.correct_index)}.")
            self.feedback_body.setText(q.explanation)
            self._set_feedback_kind("success" if ok else "error")
        else:
            self.feedback.hide()
        self._sync_buttons()

    def _render_level(self) -> None:
        lvl = self.engine.level
        self.level_big.setText(LEVEL_NAMES[lvl])
        for k, seg in self.level_segs.items():
            set_prop(seg, "active", "true" if k == lvl else "false")
        if self.finished_reason:
            self.level_caption.setText("Final level reached by the engine this session.")
        elif not self.started:
            self.level_caption.setText("Every session starts at Medium.")
        elif self.answered:
            self.level_caption.setText(f"The next question will target {LEVEL_NAMES[lvl]}.")
        else:
            self.level_caption.setText(f"Current question was selected for {LEVEL_NAMES[self.target_when_asked]}.")

    def _render_decision(self) -> None:
        d = self.engine.diagnostics()
        self.kv["Current target"].setText(f"{d.level} · {LEVEL_NAMES[d.level]}")
        self.kv["Correct streak"].setText(streak_dots(d.correct_streak))
        self.kv["Wrong streak"].setText(streak_dots(d.wrong_streak))
        if self.decision is None:
            self.kv["Previous level"].setText("—")
            self.kv["New level"].setText("—")
            self.reason.setText("Submit an answer to see how the engine reacts. "
                                "Two correct in a row raise the level; two wrong lower it.")
            return
        before, after, ok = self.decision
        self.kv["Previous level"].setText(f"{before.level} · {LEVEL_NAMES[before.level]}")
        self.kv["New level"].setText(f"{after.level} · {LEVEL_NAMES[after.level]}")
        self.reason.setText(explain_decision(before, after, ok))

    def _render_score(self) -> None:
        s = calculate_score(self.answers)
        self.score_big.setText(f"{s.percentage:.1f}%")
        self.score_bar.setValue(int(s.percentage * 10))
        self.tiles["Correct"].setText(str(sum(a.is_correct is True for a in self.answers)))
        self.tiles["Incorrect"].setText(str(sum(a.is_correct is False for a in self.answers)))
        self.tiles["Earned points"].setText(str(s.earned))
        self.tiles["Maximum points"].setText(str(s.maximum))


def explain_decision(before: EngineDiagnostics, after: EngineDiagnostics, ok: bool) -> str:
    """Narrates what the engine did, read from its before/after state (no re-implementation)."""
    prev, new = LEVEL_NAMES[before.level], LEVEL_NAMES[after.level]
    word = "correct" if ok else "wrong"
    if after.level > before.level:
        return f"2 correct answers in a row → difficulty raised from {prev} to {new}. Streaks reset."
    if after.level < before.level:
        return f"2 wrong answers in a row → difficulty lowered from {prev} to {new}. Streaks reset."
    streak = after.correct_streak if ok else after.wrong_streak
    if streak == 0:
        bound = "Hard, the maximum" if ok else "Easy, the minimum"
        return f"2 {word} answers in a row, but the level is already {bound}. It stays {new}; streaks reset."
    text = f"1 {word} answer so far. One more in a row would {'raise' if ok else 'lower'} the level"
    if (ok and after.level == MAX_LEVEL) or (not ok and after.level == MIN_LEVEL):
        text = f"1 {word} answer so far. The level is already {new}, so it cannot move further"
    opposite = before.wrong_streak if ok else before.correct_streak
    if opposite:
        text += f"; the {'wrong' if ok else 'correct'} streak was reset"
    return text + f". Level stays {new}."


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    app.setFont(QFont("Segoe UI", 10))
    w = AdaptiveDemo()
    avail = app.primaryScreen().availableGeometry()
    w.resize(min(1320, avail.width()), min(880, avail.height()))
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
