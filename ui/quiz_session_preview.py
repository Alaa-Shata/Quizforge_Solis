import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from quiz_session import QuizSessionPage


class QuizSessionPreview(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("QuizForge | Quiz Session Preview")
        self.resize(1280, 850)

        self.session_page = QuizSessionPage(parent=self)
        self.setCentralWidget(self.session_page)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("QuizForge")

    window = QuizSessionPreview()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()