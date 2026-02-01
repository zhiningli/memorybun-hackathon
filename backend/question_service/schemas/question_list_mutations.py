"""
Input schemas for question list mutations (create/update).

Uses aggregate pattern - creates list + items in single transaction.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List

from schemas.questionList import (
    QuestionListMetadataBase,
    QuestionListCategoryEnum,
    QuestionListDifficultyEnum,
    AccessStatusEnum,
)
from schemas.question import SubjectEnum


class QuestionItemInput(BaseModel):
    """Input for a question in a list."""
    question_id: int = Field(..., description="ID of the question")
    weightage: float = Field(..., ge=0.0, le=1.0, description="Weight (0-1)")
    order_index: Optional[int] = Field(None, ge=1, description="Order in list (auto-assigned if not provided)")


class QuestionListCreate(QuestionListMetadataBase):
    """
    Schema for creating a new question list with questions.
    
    Uses aggregate pattern: list metadata + items created together.
    Validates weightage sums to 1.0 and all questions exist.
    """
    question_items: List[QuestionItemInput] = Field(
        ...,
        min_length=1,
        description="Questions in this list with weightages (must sum to 1.0)"
    )
    
    @model_validator(mode='after')
    def validate_weightage_sum(self) -> 'QuestionListCreate':
        """Validate that weightages sum to 1.0 (with small epsilon for float precision)."""
        total = sum(item.weightage for item in self.question_items)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weightage must sum to 1.0, got {total:.2f}")
        return self
    
    @model_validator(mode='after')
    def validate_no_duplicate_questions(self) -> 'QuestionListCreate':
        """Validate no duplicate question IDs."""
        question_ids = [item.question_id for item in self.question_items]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Duplicate question IDs not allowed")
        return self


class QuestionListUpdate(BaseModel):
    """
    Schema for updating an existing question list.
    
    All fields optional for partial updates.
    If question_items is provided, it replaces all existing items.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    categories: Optional[List[QuestionListCategoryEnum]] = Field(None, min_length=1)
    subjects: Optional[List[SubjectEnum]] = Field(None, min_length=1)
    difficulty: Optional[QuestionListDifficultyEnum] = None
    duration_seconds: Optional[int] = Field(None, gt=0)
    access_status: Optional[AccessStatusEnum] = None
    
    # Optional: replace all items
    question_items: Optional[List[QuestionItemInput]] = Field(
        None,
        description="If provided, replaces all existing items"
    )
    
    @model_validator(mode='after')
    def validate_weightage_if_items_provided(self) -> 'QuestionListUpdate':
        """Validate weightage sum if items are being replaced."""
        if self.question_items is not None and len(self.question_items) > 0:
            total = sum(item.weightage for item in self.question_items)
            if abs(total - 1.0) > 0.01:
                raise ValueError(f"Weightage must sum to 1.0, got {total:.2f}")
            
            # Check for duplicates
            question_ids = [item.question_id for item in self.question_items]
            if len(question_ids) != len(set(question_ids)):
                raise ValueError("Duplicate question IDs not allowed")
        return self
