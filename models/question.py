from dataclasses import dataclass


@dataclass(frozen=True)
class ImportRowError:
    row_number: int
    reason: str


@dataclass(frozen=True)
class ImportPreview:
    source_path: str
    source_format: str
    valid_rows: tuple[dict[str, object], ...]
    invalid_rows: tuple[ImportRowError, ...]
    source_sha256: str


@dataclass(frozen=True)
class Question:
    id: int
    topic_id: int
    text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str  # 'A', 'B', 'C', أو 'D'
    difficulty: int      # 1, 2, أو 3
    explanation: str
    is_active: bool = True
