from typing import Optional
from services.question_service import QuestionService

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QButtonGroup,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QRadioButton,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    _HAS_PYSIDE6 = True
except ImportError:
    _HAS_PYSIDE6 = False
    QWidget = object  # type: ignore[misc, assignment]


if _HAS_PYSIDE6:
    class QuestionBankPage(QWidget):
        def __init__(self, service: QuestionService, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)
            self._service = service
            self._selected_question_id: Optional[int] = None
            self._build_ui()
            self.refresh_data()

        def _build_ui(self) -> None:
            root_layout = QVBoxLayout(self)

            top_bar = QHBoxLayout()
            title_lbl = QLabel("Question Bank")
            self._btn_new = QPushButton("+ New")
            self._btn_import = QPushButton("Import")
            self._btn_export = QPushButton("Export")
            top_bar.addWidget(title_lbl)
            top_bar.addStretch()
            top_bar.addWidget(self._btn_new)
            top_bar.addWidget(self._btn_import)
            top_bar.addWidget(self._btn_export)
            root_layout.addLayout(top_bar)

            filter_bar = QHBoxLayout()
            self._txt_search = QLineEdit()
            self._txt_search.setPlaceholderText("Search question text...")
            self._cmb_topic = QComboBox()
            self._cmb_difficulty = QComboBox()
            self._cmb_difficulty.addItem("All", None)
            self._cmb_difficulty.addItem("Easy (1)", 1)
            self._cmb_difficulty.addItem("Medium (2)", 2)
            self._cmb_difficulty.addItem("Hard (3)", 3)
            self._btn_clear = QPushButton("Clear")

            filter_bar.addWidget(self._txt_search)
            filter_bar.addWidget(QLabel("Topic:"))
            filter_bar.addWidget(self._cmb_topic)
            filter_bar.addWidget(QLabel("Difficulty:"))
            filter_bar.addWidget(self._cmb_difficulty)
            filter_bar.addWidget(self._btn_clear)
            root_layout.addLayout(filter_bar)

            body_layout = QHBoxLayout()

            self._table = QTableWidget(0, 4)
            self._table.setHorizontalHeaderLabels(["ID", "Topic", "Question", "Level"])
            self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            body_layout.addWidget(self._table, stretch=1)

            right_panel = QVBoxLayout()
            editor_box = QGroupBox("Question Editor")
            form = QFormLayout(editor_box)

            self._edit_topic = QComboBox()
            self._edit_difficulty = QComboBox()
            self._edit_difficulty.addItem("Easy (1)", 1)
            self._edit_difficulty.addItem("Medium (2)", 2)
            self._edit_difficulty.addItem("Hard (3)", 3)

            self._txt_question = QTextEdit()
            self._txt_question.setMaximumHeight(65)

            self._opt_a = QLineEdit()
            self._opt_b = QLineEdit()
            self._opt_c = QLineEdit()
            self._opt_d = QLineEdit()

            self._rb_a = QRadioButton("A")
            self._rb_b = QRadioButton("B")
            self._rb_c = QRadioButton("C")
            self._rb_d = QRadioButton("D")

            self._correct_group = QButtonGroup(self)
            self._correct_group.addButton(self._rb_a)
            self._correct_group.addButton(self._rb_b)
            self._correct_group.addButton(self._rb_c)
            self._correct_group.addButton(self._rb_d)

            radio_row = QHBoxLayout()
            for rb in (self._rb_a, self._rb_b, self._rb_c, self._rb_d):
                radio_row.addWidget(rb)

            self._txt_explanation = QTextEdit()
            self._txt_explanation.setMaximumHeight(55)

            form.addRow("Topic:", self._edit_topic)
            form.addRow("Difficulty:", self._edit_difficulty)
            form.addRow("Question:", self._txt_question)
            form.addRow("Option A:", self._opt_a)
            form.addRow("Option B:", self._opt_b)
            form.addRow("Option C:", self._opt_c)
            form.addRow("Option D:", self._opt_d)
            form.addRow("Correct:", radio_row)
            form.addRow("Explanation:", self._txt_explanation)

            actions_row = QHBoxLayout()
            self._btn_save = QPushButton("Save")
            self._btn_cancel = QPushButton("Cancel")
            self._btn_deactivate = QPushButton("Deactivate")
            actions_row.addWidget(self._btn_save)
            actions_row.addWidget(self._btn_cancel)
            actions_row.addWidget(self._btn_deactivate)
            form.addRow(actions_row)

            right_panel.addWidget(editor_box)

            preview_box = QGroupBox("Live Question Preview")
            preview_layout = QVBoxLayout(preview_box)
            self._lbl_preview = QLabel("Preview will appear here...")
            self._lbl_preview.setWordWrap(True)
            preview_layout.addWidget(self._lbl_preview)
            right_panel.addWidget(preview_box)

            body_layout.addLayout(right_panel, stretch=1)
            root_layout.addLayout(body_layout)

            self._btn_new.clicked.connect(self._clear_editor)
            self._btn_cancel.clicked.connect(self._clear_editor)
            self._btn_save.clicked.connect(self._on_save)
            self._btn_deactivate.clicked.connect(self._on_deactivate)
            self._btn_import.clicked.connect(self._on_import)
            self._btn_export.clicked.connect(self._on_export)
            self._btn_clear.clicked.connect(self._on_clear_filters)

            self._txt_search.textChanged.connect(self._refresh_table)
            self._cmb_topic.currentIndexChanged.connect(self._refresh_table)
            self._cmb_difficulty.currentIndexChanged.connect(self._refresh_table)
            self._table.itemSelectionChanged.connect(self._on_row_selected)

            for widget in (
                self._txt_question,
                self._opt_a,
                self._opt_b,
                self._opt_c,
                self._opt_d,
                self._txt_explanation,
            ):
                if isinstance(widget, QTextEdit):
                    widget.textChanged.connect(self._update_preview)
                else:
                    widget.textChanged.connect(self._update_preview)

            for rb in (self._rb_a, self._rb_b, self._rb_c, self._rb_d):
                rb.toggled.connect(self._update_preview)

        def refresh_data(self) -> None:
            topics = self._service.list_topics()
            self._cmb_topic.blockSignals(True)
            self._edit_topic.blockSignals(True)

            self._cmb_topic.clear()
            self._cmb_topic.addItem("All", None)
            self._edit_topic.clear()

            for tid, name in topics:
                self._cmb_topic.addItem(name, tid)
                self._edit_topic.addItem(name, tid)

            self._cmb_topic.blockSignals(False)
            self._edit_topic.blockSignals(False)
            self._refresh_table()

        def _refresh_table(self) -> None:
            topic_id = self._cmb_topic.currentData()
            difficulty = self._cmb_difficulty.currentData()
            search_text = self._txt_search.text()
            items = self._service.list_questions(
                topic_id=topic_id,
                difficulty=difficulty,
                search_text=search_text,
                active_only=True,
            )
            topic_map = dict(self._service.list_topics())
            self._table.setRowCount(len(items))
            for row_idx, q in enumerate(items):
                self._table.setItem(row_idx, 0, QTableWidgetItem(str(q.id)))
                self._table.setItem(row_idx, 1, QTableWidgetItem(topic_map.get(q.topic_id, str(q.topic_id))))
                self._table.setItem(row_idx, 2, QTableWidgetItem(q.text))
                self._table.setItem(row_idx, 3, QTableWidgetItem(str(q.difficulty)))

        def _selected_option_letter(self) -> str:
            if self._rb_a.isChecked():
                return "A"
            if self._rb_b.isChecked():
                return "B"
            if self._rb_c.isChecked():
                return "C"
            if self._rb_d.isChecked():
                return "D"
            return ""

        def _update_preview(self) -> None:
            q_text = self._txt_question.toPlainText().strip()
            a_text = self._opt_a.text().strip()
            b_text = self._opt_b.text().strip()
            c_text = self._opt_c.text().strip()
            d_text = self._opt_d.text().strip()
            correct = self._selected_option_letter()
            exp_text = self._txt_explanation.toPlainText().strip()

            self._lbl_preview.setText(
                f"Q: {q_text}\n"
                f"A) {a_text}\n"
                f"B) {b_text}\n"
                f"C) {c_text}\n"
                f"D) {d_text}\n"
                f"Correct: {correct or '-'} | Explanation: {exp_text}"
            )

        def _clear_editor(self) -> None:
            self._selected_question_id = None
            self._txt_question.clear()
            self._opt_a.clear()
            self._opt_b.clear()
            self._opt_c.clear()
            self._opt_d.clear()
            self._txt_explanation.clear()
            self._correct_group.setExclusive(False)
            for rb in (self._rb_a, self._rb_b, self._rb_c, self._rb_d):
                rb.setChecked(False)
            self._correct_group.setExclusive(True)
            self._update_preview()

        def _on_clear_filters(self) -> None:
            self._txt_search.clear()
            self._cmb_topic.setCurrentIndex(0)
            self._cmb_difficulty.setCurrentIndex(0)
            self._refresh_table()

        def _on_row_selected(self) -> None:
            selected_rows = self._table.selectionModel().selectedRows()
            if not selected_rows:
                return
            row_idx = selected_rows[0].row()
            id_item = self._table.item(row_idx, 0)
            if not id_item:
                return
            qid = int(id_item.text())
            matches = [q for q in self._service.list_questions(active_only=False) if q.id == qid]
            if not matches:
                return
            q = matches[0]
            self._selected_question_id = q.id

            idx_topic = self._edit_topic.findData(q.topic_id)
            if idx_topic >= 0:
                self._edit_topic.setCurrentIndex(idx_topic)

            idx_diff = self._edit_difficulty.findData(q.difficulty)
            if idx_diff >= 0:
                self._edit_difficulty.setCurrentIndex(idx_diff)

            self._txt_question.setPlainText(q.text)
            self._opt_a.setText(q.option_a)
            self._opt_b.setText(q.option_b)
            self._opt_c.setText(q.option_c)
            self._opt_d.setText(q.option_d)
            self._txt_explanation.setPlainText(q.explanation)

            rb_map = {"A": self._rb_a, "B": self._rb_b, "C": self._rb_c, "D": self._rb_d}
            target_rb = rb_map.get(q.correct_option)
            if target_rb is not None:
                target_rb.setChecked(True)
            self._update_preview()

        def _on_save(self) -> None:
            topic_id = self._edit_topic.currentData()
            difficulty = self._edit_difficulty.currentData()
            text = self._txt_question.toPlainText()
            options = (
                self._opt_a.text(),
                self._opt_b.text(),
                self._opt_c.text(),
                self._opt_d.text(),
            )
            correct_option = self._selected_option_letter()
            explanation = self._txt_explanation.toPlainText()

            try:
                if self._selected_question_id is None:
                    self._service.create_question(
                        topic_id=int(topic_id),
                        text=text,
                        options=options,
                        correct_option=correct_option,
                        difficulty=int(difficulty),
                        explanation=explanation,
                    )
                else:
                    self._service.update_question(
                        self._selected_question_id,
                        topic_id=int(topic_id),
                        text=text,
                        options=options,
                        correct_option=correct_option,
                        difficulty=int(difficulty),
                        explanation=explanation,
                    )
                self._refresh_table()
                self._clear_editor()
                QMessageBox.information(self, "Saved", "Question saved successfully.")
            except Exception as exc:
                QMessageBox.warning(self, "Validation Error", str(exc))

        def _on_deactivate(self) -> None:
            if self._selected_question_id is None:
                QMessageBox.information(self, "Select Question", "Please select a question first.")
                return
            reply = QMessageBox.question(
                self,
                "Confirm Deactivate",
                "Mark selected question as inactive?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                self._service.deactivate_question(self._selected_question_id)
                self._refresh_table()
                self._clear_editor()
            except Exception as exc:
                QMessageBox.warning(self, "Error", str(exc))

        def _on_import(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Questions",
                "",
                "CSV or JSON (*.csv *.json)",
            )
            if not file_path:
                return
            try:
                preview = self._service.preview_import(file_path)
                msg = (
                    f"Valid rows: {len(preview.valid_rows)}\n"
                    f"Invalid rows: {len(preview.invalid_rows)}\n"
                    f"Commit valid rows now?"
                )
                reply = QMessageBox.question(
                    self,
                    "Import Preview",
                    msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    inserted = self._service.commit_import(preview)
                    self.refresh_data()
                    QMessageBox.information(self, "Imported", f"Inserted {inserted} questions.")
            except Exception as exc:
                QMessageBox.warning(self, "Import Error", str(exc))

        def _on_export(self) -> None:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Questions",
                "questions_export.csv",
                "CSV (*.csv);;JSON (*.json)",
            )
            if not file_path:
                return
            fmt = "json" if file_path.lower().endswith(".json") else "csv"
            filters = {
                "topic_id": self._cmb_topic.currentData(),
                "difficulty": self._cmb_difficulty.currentData(),
                "search_text": self._txt_search.text(),
                "active_only": True,
            }
            try:
                count = self._service.export_questions(file_path, format=fmt, filters=filters)
                QMessageBox.information(self, "Exported", f"Exported {count} questions.")
            except Exception as exc:
                QMessageBox.warning(self, "Export Error", str(exc))