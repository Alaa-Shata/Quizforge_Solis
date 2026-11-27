"""Compatibility import; new code uses database.repositories.question_repository."""

from database.repositories.question_repository import QuestionRepository

__all__ = ["QuestionRepository"]
