"""Typed errors shared by QuizForge services."""


class QuizForgeError(Exception):
    """Base class for expected, user-facing application errors."""


class ValidationError(QuizForgeError, ValueError):
    pass


class NotFoundError(QuizForgeError, LookupError):
    pass


class InsufficientQuestionsError(QuizForgeError):
    pass


class ActiveSessionError(QuizForgeError, RuntimeError):
    pass


class PersistenceError(QuizForgeError):
    pass
