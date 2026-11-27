import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from models.question import ImportPreview, ImportRowError, Question
from database.repositories.question_repository import QuestionRepository
from utils.errors import NotFoundError, ValidationError


class QuestionService:
    _EXPORT_FIELDS = (
        "topic",
        "text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "difficulty",
        "explanation",
    )

    def __init__(self, repository: Optional[QuestionRepository] = None) -> None:
        self._repository = repository if repository is not None else QuestionRepository()

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.strip().split())

    @staticmethod
    def _compute_file_sha256(path_obj: Path) -> str:
        hasher = hashlib.sha256()
        with path_obj.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _validate_topic_exists(self, topic_id: int) -> None:
        topics = self._repository.list_topics()
        valid_ids = {t_id for t_id, _ in topics}
        if topic_id not in valid_ids:
            raise ValidationError("Select a valid topic.")

    def _validate_question_payload(
        self,
        *,
        topic_id: int,
        text: str,
        options: Tuple[str, str, str, str],
        correct_option: str,
        difficulty: int,
        explanation: str,
        exclude_question_id: Optional[int] = None,
    ) -> Tuple[str, Tuple[str, str, str, str], str, int, str]:
        self._validate_topic_exists(topic_id)

        clean_text = self._normalize_text(text)
        if not clean_text:
            raise ValidationError("Question text is required.")

        if not isinstance(options, (tuple, list)) or len(options) != 4:
            raise ValidationError("All four options are required.")

        cleaned_opts = tuple(self._normalize_text(str(opt)) for opt in options)
        if any(not opt for opt in cleaned_opts):
            raise ValidationError("All four options are required.")

        folded_opts = [opt.casefold() for opt in cleaned_opts]
        if len(set(folded_opts)) != 4:
            raise ValidationError("Options must be different.")

        clean_correct = str(correct_option).strip().upper()
        if clean_correct not in ("A", "B", "C", "D"):
            raise ValidationError("Select one correct option (A, B, C, or D).")

        if isinstance(difficulty, bool) or not isinstance(difficulty, int) or difficulty not in (1, 2, 3):
            raise ValidationError("Difficulty must be 1, 2, or 3.")

        clean_explanation = self._normalize_text(explanation)
        if not clean_explanation:
            raise ValidationError("Explanation is required.")

        if self._repository.has_normalized_duplicate(
            topic_id=topic_id,
            normalized_text=clean_text,
            exclude_question_id=exclude_question_id,
        ):
            raise ValidationError("This question already exists in this topic.")

        return (
            clean_text,
            (cleaned_opts[0], cleaned_opts[1], cleaned_opts[2], cleaned_opts[3]),
            clean_correct,
            difficulty,
            clean_explanation,
        )

    def list_topics(self) -> List[Tuple[int, str]]:
        return self._repository.list_topics()

    def create_topic(self, name: str) -> Tuple[int, str]:
        clean_name = self._normalize_text(name)
        if not clean_name:
            raise ValidationError("Topic name is required.")
        existing = self._repository.get_topic_by_name(clean_name)
        if existing is not None:
            raise ValidationError("Topic already exists.")
        try:
            return self._repository.create_topic(clean_name)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Topic already exists.") from exc

    def list_questions(
        self,
        *,
        topic_id: Optional[int] = None,
        difficulty: Optional[int] = None,
        search_text: str = "",
        active_only: bool = True,
    ) -> List[Question]:
        return self._repository.list_questions(
            topic_id=topic_id,
            difficulty=difficulty,
            search_text=search_text,
            active_only=active_only,
        )

    def create_question(self,
        *,
        topic_id: int,
        text: str,
        options: Tuple[str, str, str, str],
        correct_option: str,
        difficulty: int,
        explanation: str,
    ) -> Question:
        clean_text, clean_opts, clean_correct, clean_diff, clean_exp = self._validate_question_payload(
            topic_id=topic_id,
            text=text,
            options=options,
            correct_option=correct_option,
            difficulty=difficulty,
            explanation=explanation,
        )
        try:
            return self._repository.create_question(
                topic_id=topic_id,
                text=clean_text,
                options=clean_opts,
                correct_option=clean_correct,
                difficulty=clean_diff,
                explanation=clean_exp,
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationError("This question already exists in this topic.") from exc

    def update_question(
        self,
        question_id: int,
        *,
        topic_id: int,
        text: str,
        options: Tuple[str, str, str, str],
        correct_option: str,
        difficulty: int,
        explanation: str,
    ) -> Question:
        existing = self._repository.get_by_id(question_id)
        if existing is None:
            raise NotFoundError("Question not found.")

        if self._repository.is_referenced_by_attempts(question_id):
            raise ValidationError("Cannot edit a question that has already been used in quiz attempts.")

        clean_text, clean_opts, clean_correct, clean_diff, clean_exp = self._validate_question_payload(
            topic_id=topic_id,
            text=text,
            options=options,
            correct_option=correct_option,
            difficulty=difficulty,
            explanation=explanation,
            exclude_question_id=question_id,
        )
        try:
            return self._repository.update_question(
                question_id,
                topic_id=topic_id,
                text=clean_text,
                options=clean_opts,
                correct_option=clean_correct,
                difficulty=clean_diff,
                explanation=clean_exp,
            )
        except sqlite3.IntegrityError as exc:
            if "history is immutable" in str(exc).lower():
                raise ValidationError(
                    "Cannot edit a question that has already been used in quiz attempts."
                ) from exc
            raise ValidationError("This question already exists in this topic.") from exc

    def deactivate_question(self, question_id: int) -> None:
        existing = self._repository.get_by_id(question_id)
        if existing is None:
            raise NotFoundError("Question not found.")
        self._repository.deactivate_question(question_id)

    def _validate_import_row(
        self,
        row_data: Dict[str, Any],
        row_number: int,
        seen_in_batch: set,
        topic_map_casefold: Dict[str, Tuple[int, str]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[ImportRowError]]:
        missing_keys = [k for k in self._EXPORT_FIELDS if k not in row_data]
        if missing_keys:
            return None, ImportRowError(row_number, f"Missing fields: {', '.join(missing_keys)}")

        raw_topic = str(row_data.get("topic") or "").strip()
        topic_key = self._normalize_text(raw_topic).casefold()
        if not topic_key:
            return None, ImportRowError(row_number, "Topic is required.")

        raw_text = self._normalize_text(str(row_data.get("text") or ""))
        if not raw_text:
            return None, ImportRowError(row_number, "Question text is required.")

        opt_a = self._normalize_text(str(row_data.get("option_a") or ""))
        opt_b = self._normalize_text(str(row_data.get("option_b") or ""))
        opt_c = self._normalize_text(str(row_data.get("option_c") or ""))
        opt_d = self._normalize_text(str(row_data.get("option_d") or ""))
        if not all((opt_a, opt_b, opt_c, opt_d)):
            return None, ImportRowError(row_number, "All four options are required.")

        folded_opts = [o.casefold() for o in (opt_a, opt_b, opt_c, opt_d)]
        if len(set(folded_opts)) != 4:
            return None, ImportRowError(row_number, "Options must be different.")

        correct_option = str(row_data.get("correct_option") or "").strip().upper()
        if correct_option not in ("A", "B", "C", "D"):
            return None, ImportRowError(row_number, "Correct option must be A, B, C, or D.")

        raw_diff = row_data.get("difficulty")
        if isinstance(raw_diff, bool):
            return None, ImportRowError(row_number, "Difficulty must be 1, 2, or 3.")
        try:
            difficulty = int(str(raw_diff).strip())
        except (TypeError, ValueError):
            return None, ImportRowError(row_number, "Difficulty must be 1, 2, or 3.")
        if difficulty not in (1, 2, 3):
            return None, ImportRowError(row_number, "Difficulty must be 1, 2, or 3.")

        explanation = self._normalize_text(str(row_data.get("explanation") or ""))
        if not explanation:
            return None, ImportRowError(row_number, "Explanation is required.")

        batch_key = (topic_key, raw_text.casefold())
        if batch_key in seen_in_batch:
            return None, ImportRowError(row_number, "Duplicate question in import batch.")

        existing_topic = topic_map_casefold.get(topic_key)
        if existing_topic is not None:
            if self._repository.has_normalized_duplicate(existing_topic[0], raw_text):
                return None, ImportRowError(row_number, "Question already exists in this topic.")

        seen_in_batch.add(batch_key)
        normalized_record = {
            "topic": existing_topic[1] if existing_topic else self._normalize_text(raw_topic),
            "text": raw_text,
            "option_a": opt_a,
            "option_b": opt_b,
            "option_c": opt_c,
            "option_d": opt_d,
            "correct_option": correct_option,
            "difficulty": difficulty,
            "explanation": explanation,
        }
        return normalized_record, None

    def preview_import(self, path: str) -> ImportPreview:
        path_obj = Path(path)
        if not path_obj.exists() or not path_obj.is_file():
            raise FileNotFoundError("Import file not found.")

        suffix = path_obj.suffix.lower()
        if suffix not in (".csv", ".json"):
            raise ValidationError("Only CSV and JSON files are supported.")

        source_sha256 = self._compute_file_sha256(path_obj)
        topics = self._repository.list_topics()
        topic_map_casefold = {name.strip().casefold(): (tid, name) for tid, name in topics}
        seen_in_batch: set = set()
        valid_rows: List[Dict[str, Any]] = []
        invalid_rows: List[ImportRowError] = []

        if suffix == ".csv":
            with path_obj.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValidationError("CSV file is empty or missing headers.")
                headers = [h.strip() for h in reader.fieldnames if h is not None]
                if tuple(headers) != self._EXPORT_FIELDS:
                    raise ValidationError("Invalid CSV headers.")
                for row in reader:
                    row_number = reader.line_num
                    if None in row:
                        invalid_rows.append(ImportRowError(
                            row_number, "CSV record has more fields than the header."
                        ))
                        continue
                    if any(row.get(field) is None for field in self._EXPORT_FIELDS):
                        invalid_rows.append(ImportRowError(
                            row_number, "CSV record is missing one or more fields."
                        ))
                        continue
                    cleaned_row = {k.strip(): v for k, v in row.items() if k is not None}
                    rec, err = self._validate_import_row(
                        cleaned_row, row_number, seen_in_batch, topic_map_casefold
                    )
                    if err is not None:
                        invalid_rows.append(err)
                    elif rec is not None:
                        valid_rows.append(rec)
        else:
            with path_obj.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValidationError("JSON root must be a list of question objects.")
            for idx, item in enumerate(data, start=1):
                if not isinstance(item, dict):
                    invalid_rows.append(ImportRowError(idx, "Each item must be a JSON object."))
                    continue
                rec, err = self._validate_import_row(item, idx, seen_in_batch, topic_map_casefold)
                if err is not None:
                    invalid_rows.append(err)
                elif rec is not None:
                    valid_rows.append(rec)

        return ImportPreview(
            source_path=str(path_obj),
            source_format=suffix.lstrip("."),
            valid_rows=tuple(valid_rows),
            invalid_rows=tuple(invalid_rows),
            source_sha256=source_sha256,
        )

    def commit_import(self, preview: ImportPreview) -> int:
        path_obj = Path(preview.source_path)
        if not path_obj.exists() or not path_obj.is_file():
            raise FileNotFoundError("Import source file no longer exists.")

        current_sha = self._compute_file_sha256(path_obj)
        if current_sha != preview.source_sha256:
            raise ValidationError("Source file changed since preview. Please run preview again.")

        if not preview.valid_rows:
            return 0

        resolved_records: List[Dict[str, Any]] = []
        topics = self._repository.list_topics()
        topic_map = {name.strip().casefold(): tid for tid, name in topics}
        seen_keys: set = set()

        for row in preview.valid_rows:
            topic_name = self._normalize_text(str(row["topic"]))
            topic_key = topic_name.casefold()
            text = self._normalize_text(str(row["text"]))
            options = tuple(self._normalize_text(str(row[field])) for field in (
                "option_a", "option_b", "option_c", "option_d"
            ))
            correct_option = str(row["correct_option"]).strip().upper()
            difficulty = int(row["difficulty"])
            explanation = self._normalize_text(str(row["explanation"]))

            if len(options) != 4 or any(not o for o in options) or len({o.casefold() for o in options}) != 4:
                raise ValidationError("Invalid options detected during commit.")
            if correct_option not in ("A", "B", "C", "D") or difficulty not in (1, 2, 3) or not text or not explanation:
                raise ValidationError("Invalid question fields detected during commit.")

            pair_key = (topic_key, text.casefold())
            if pair_key in seen_keys:
                raise ValidationError("Duplicate question detected during commit.")
            seen_keys.add(pair_key)

            topic_id = topic_map.get(topic_key)
            if topic_id is not None and self._repository.has_normalized_duplicate(topic_id, text):
                raise ValidationError("Question already exists in this topic.")

            resolved_records.append(
                {
                    "topic_id": topic_id,
                    "topic_name": topic_name,
                    "text": text,
                    "options": options,
                    "correct_option": correct_option,
                    "difficulty": difficulty,
                    "explanation": explanation,
                }
            )

        try:
            return self._repository.create_questions_bulk(resolved_records)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Import failed due to database constraint.") from exc

    def export_questions(self, path: str, *, format: str, filters: Optional[Dict[str, Any]] = None) -> int:
        fmt = str(format).strip().lower()
        if fmt not in ("csv", "json"):
            raise ValidationError("Export format must be 'csv' or 'json'.")

        flt = filters or {}
        questions = self.list_questions(
            topic_id=flt.get("topic_id"),
            difficulty=flt.get("difficulty"),
            search_text=str(flt.get("search_text") or ""),
            active_only=bool(flt.get("active_only", True)),
        )

        topic_names = {tid: name for tid, name in self.list_topics()}
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        rows_payload = [
            {
                "topic": topic_names.get(q.topic_id, str(q.topic_id)),
                "text": q.text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_option": q.correct_option,
                "difficulty": q.difficulty,
                "explanation": q.explanation,
            }
            for q in questions
        ]

        if fmt == "csv":
            with path_obj.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(self._EXPORT_FIELDS))
                writer.writeheader()
                for item in rows_payload:
                    writer.writerow(item)
        else:
            with path_obj.open("w", encoding="utf-8") as f:
                json.dump(rows_payload, f, ensure_ascii=False, indent=2)

        return len(rows_payload)
