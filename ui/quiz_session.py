from pathlib import Path

from PySide6.QtCore import QUrl

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QMessageBox
)

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from services.quiz_session_controller import QuizSessionController


class QuizSessionPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.html_path = (
            Path(__file__).resolve().parent
            / "quiz_session.html"
        )

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

        self.quiz_controller = QuizSessionController(self)

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

        self.web_view.load(
            QUrl.fromLocalFile(
                str(self.html_path)
            )
        )