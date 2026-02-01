"""
Storage layer for question service.

This module provides abstraction over data storage, enabling easy migration
from JSON files to databases in the future.

Usage:
    from storage import QuestionStore, JsonQuestionStore
    from storage import QuestionListStore, JsonQuestionListStore
    from storage import QuestionListItemStore, JsonQuestionListItemStore
    from storage import AnswerStore, JsonAnswerStore
    from storage import RubricStore, JsonRubricStore
"""

# Question storage
from storage.question_store import QuestionStore, JsonQuestionStore

# Question list storage
from storage.question_list_store import QuestionListStore, JsonQuestionListStore

# Question list item storage (join table)
from storage.question_list_item_store import QuestionListItemStore, JsonQuestionListItemStore

# Answer storage
from storage.answer_store import AnswerStore, JsonAnswerStore

# Rubric storage
from storage.rubric_store import RubricStore, JsonRubricStore

__all__ = [
    # Interfaces
    "QuestionStore",
    "QuestionListStore",
    "QuestionListItemStore",
    "AnswerStore",
    "RubricStore",
    # JSON Implementations
    "JsonQuestionStore",
    "JsonQuestionListStore",
    "JsonQuestionListItemStore",
    "JsonAnswerStore",
    "JsonRubricStore",
]
