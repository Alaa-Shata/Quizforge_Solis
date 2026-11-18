from typing import List, Optional
from models.question import Question
from repositories.question_repository import QuestionRepository

class QuestionService:
    @staticmethod
    def add_new_question(topic_id: int, text: str, option_a: str, option_b: str, 
                         option_c: str, option_d: str, correct_option: str, 
                         difficulty: int, explanation: str = "", db_path: Optional[str] = None) -> int:

        correct_option = correct_option.upper()
        if correct_option not in ('A', 'B', 'C', 'D'):
            raise ValueError("يجب أن يكون الخيار الصحيح أحد الحروف التالية: A, B, C, أو D")
        
        if not (1 <= difficulty <= 3):
            raise ValueError("مستوى الصعوبة يجب أن يكون بين 1 و 3")
            
        if not text.strip():
            raise ValueError("نص السؤال لا يمكن أن يكون فارغاً")
        return QuestionRepository.add_question(
            db_path,
            topic_id=topic_id,
            text=text.strip(),
            option_a=option_a.strip(),
            option_b=option_b.strip(),
            option_c=option_c.strip(),
            option_d=option_d.strip(),
            correct_option=correct_option,
            difficulty=difficulty,
            explanation=explanation.strip()
        )

    @staticmethod
    def get_questions_for_topic(topic_id: int, db_path: Optional[str] = None) -> List[Question]:
        return QuestionRepository.get_questions_by_topic(topic_id, db_path)