from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget as BaseWidget

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QMessageBox
)

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from services.quiz_session_controller import QuizSessionController


class QuizSessionPage(QWidget):

    def __init__(self, service=None, parent=None):

        # Preserve the previous QWidget(parent) call while exposing the
        # service-injected constructor used by the shared application shell.
        if isinstance(service, BaseWidget) and parent is None:
            parent, service = service, None

        super().__init__(parent)

        self.html_path = (
            Path(__file__).resolve().parent
            / "quiz_session.html"
        )

        self.service = service
        self._page_ready = False
        self._setup_requested = False
        self.setup_ui()

    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView(self)

        layout.addWidget(self.web_view)

        # Python <-> JavaScript communication.
        self.channel = QWebChannel(
            self.web_view.page()
        )

        self.quiz_controller = QuizSessionController(self, service=self.service)

        self.channel.registerObject(
            "quizBridge",
            self.quiz_controller
        )

        self.web_view.page().setWebChannel(
            self.channel
        )

        self.load_page()

    def load_page(self):

        if not self.html_path.exists():

            QMessageBox.critical(
                self,
                "QuizForge",
                f"HTML file not found:\n{self.html_path}"
            )

            return

        self.web_view.loadFinished.connect(self._on_page_loaded)
        self.web_view.load(
            QUrl.fromLocalFile(
                str(self.html_path)
            )
        )

    def show_setup(self):
        self._setup_requested = True
        if not self._page_ready:
            return
        self._scroll_to_setup()

    def _on_page_loaded(self, success):
        self._page_ready = bool(success)
        if self._page_ready and self._setup_requested:
            self._scroll_to_setup()

    def _scroll_to_setup(self):
        self.web_view.page().runJavaScript(
            "document.body.classList.add('focus-mode');"
            "document.getElementById('quiz-setup')?.scrollIntoView({behavior:'smooth'});"
        )
