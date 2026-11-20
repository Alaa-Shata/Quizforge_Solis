"""Headless Qt integration tests; install PySide6 to run these checks."""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

pytest.importorskip('PySide6')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from demo import adaptive_demo as demo


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app):
    widget = demo.AdaptiveDemo()
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_complete_session_no_skips_no_double_submission(window):
    window.start_session()
    seen = set()
    for _ in range(demo.SESSION_LENGTH):
        question = window.current
        assert question.id not in seen
        seen.add(question.id)
        assert not window.submit_btn.isEnabled()
        window.next_question()
        assert window.current is question
        window.options[question.correct_index].click()
        assert window.submit_btn.isEnabled()
        window.submit_btn.click()
        count = len(window.answers)
        window.submit_answer()
        assert len(window.answers) == count
        window.next_btn.click()
    assert window.stack.currentIndex() == window.PAGE_DONE
    assert len(window.answers) == 10
    assert demo.calculate_score(window.answers).percentage == 100.0


def test_reset_preserves_usage_but_clears_session(window):
    window.start_session()
    previous = window.current.id
    window.options[0].click()
    window.submit_answer()
    window.reset_session()
    assert window.stack.currentIndex() == window.PAGE_EMPTY
    assert window.answers == [] and window.used_ids == set()
    assert window.engine.level == 2
    assert window.times_used[previous] == 1
    window.start_session()
    assert window.current.id != previous


def test_keyboard_selection_and_submission(window, app):
    window.start_session()
    app.processEvents()
    QTest.keyClick(window, Qt.Key.Key_1)
    app.processEvents()
    assert window.option_group.checkedId() == 0
    QTest.keyClick(window, Qt.Key.Key_Return)
    app.processEvents()
    assert len(window.answers) == 1


def test_pool_exhaustion_finishes_cleanly(window, monkeypatch):
    monkeypatch.setattr(demo, 'QUESTIONS', demo.QUESTIONS[:1])
    window.start_session()
    assert not window.q_fallback.isHidden()
    window.options[window.current.correct_index].click()
    window.submit_answer()
    window.next_question()
    assert window.stack.currentIndex() == window.PAGE_DONE
    assert 'ran out' in window.finished_reason
    assert len(window.answers) == 1
