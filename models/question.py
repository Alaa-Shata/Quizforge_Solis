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
    correct_option: str  # 'A', 'B', 'C', أو 'D'
    difficulty: int      # 1, 2, أو 3
    explanation: str
    is_active: bool = True
