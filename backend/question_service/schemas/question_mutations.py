"""
Input schemas for question mutations (create/update).

Separated from question.py to keep read and write concerns distinct.
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from schemas.question import (
    SubjectEnum,
    QuestionTopicEnum,
    QuestionDifficultyEnum,
    Hint,
)


class QuestionCreate(BaseModel):
    """
    Schema for creating a new question.
    All required fields from Question except id and timestamps (auto-generated).
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title of the question"
    )
    question_details: str = Field(
        ...,
        max_length=5000,
        description="Detailed description of the question"
    )
    think_time_limit_seconds: int = Field(
        ...,
        gt=0,
        le=300,
        description="Time limit for thinking in seconds"
    )
    record_time_limit_seconds: int = Field(
        ...,
        gt=0,
        le=600,
        description="Time limit for recording in seconds"
    )
    instructions: List[str] = Field(
        ...,
        min_length=1,
        description="List of instructions for the question"
    )
    hints: List[Hint] = Field(
        ...,
        min_length=1,
        description="List of hints to help the user (at least one required)"
    )
    question_image_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Path or URL to question diagram/image"
    )
    subjects: List[SubjectEnum] = Field(
        ...,
        min_length=1,
        description="Subject areas (e.g., Engineering, Mathematics)"
    )
    topics: List[QuestionTopicEnum] = Field(
        default_factory=list,
        description="Topics/tags for the question. Max 5."
    )
    difficulty: QuestionDifficultyEnum = Field(
        ...,
        description="Difficulty level (required)"
    )
    rubric_id: int = Field(
        ...,
        description="ID of the rubric associated with this question"
    )


class QuestionUpdate(BaseModel):
    """
    Schema for updating an existing question.
    All fields optional for partial updates.
    """
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Title of the question"
    )
    question_details: Optional[str] = Field(
        None,
        max_length=5000,
        description="Detailed description of the question"
    )
    think_time_limit_seconds: Optional[int] = Field(
        None,
        gt=0,
        le=300,
        description="Time limit for thinking in seconds"
    )
    record_time_limit_seconds: Optional[int] = Field(
        None,
        gt=0,
        le=600,
        description="Time limit for recording in seconds"
    )
    instructions: Optional[List[str]] = Field(
        None,
        min_length=1,
        description="List of instructions for the question"
    )
    hints: Optional[List[Hint]] = Field(
        None,
        min_length=1,
        description="List of hints to help the user"
    )
    question_image_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Path or URL to question diagram/image"
    )
    subjects: Optional[List[SubjectEnum]] = Field(
        None,
        min_length=1,
        description="Subject areas"
    )
    topics: Optional[List[QuestionTopicEnum]] = Field(
        None,
        description="Topics/tags for the question"
    )
    difficulty: Optional[QuestionDifficultyEnum] = Field(
        None,
        description="Difficulty level"
    )
    rubric_id: Optional[int] = Field(
        None,
        description="ID of the rubric associated with this question"
    )
