"""
Input schemas for answer mutations (create/update).

Separated from answer.py to keep read and write concerns distinct.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from schemas.answer import AnswerBase

class AnswerCreate(AnswerBase):
    """
    Schema for creating a new answer.
    Requires question_id. Other fields are optional as per AnswerBase.
    """
    question_id: int = Field(..., description="ID of the question this answer belongs to")


class AnswerUpdate(AnswerBase):
    """
    Schema for updating an existing answer.
    All fields are optional (inherited from AnswerBase) for partial updates.
    """
    pass
