"""
Pydantic schemas for Questions, Answers, and Question Lists.

These schemas serve dual purposes:
1. API request/response validation (now)
2. Blueprint for database models (later)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================
# ENUMS
# ============================================

class SubjectEnum(str, Enum):
    """Subject areas for questions"""
    ENGINEERING = "Engineering"
    MATHEMATICS = "Mathematics"
    PHYSICS = "Physics"


class QuestionTopicEnum(str, Enum):
    """Topics/tags that can be assigned to questions (max 3 per question)"""
    MATHEMATICS = "Mathematics"
    ENERGY = "Energy"
    ELECTRICITY = "Electricity"
    GRAPH_PLOTTING = "Graph Plotting"
    FLUID_DYNAMICS = "Fluid Dynamics"
    CIRCUIT_ANALYSIS = "Circuit Analysis"
    DYNAMICS = "Dynamics"


class QuestionDifficultyEnum(str, Enum):
    """Difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ============================================
# HINT SCHEMA
# ============================================

class Hint(BaseModel):
    """
    Hint structure for questions.
    A question can have multiple hints stored as a JSON array.
    At least one of text or image_url must be provided.
    """
    text: Optional[str] = Field(
        None,
        max_length=1000,
        description="Hint text to help the user. Use $...$ for LaTeX math."
    )
    image_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Path or URL to a hint image. MVP: relative path from /blob/. Future: S3 URL."
    )

    @model_validator(mode='after')
    def at_least_one_field(self):
        """Ensure at least one of text or image_url is provided"""
        if not self.text and not self.image_url:
            raise ValueError("Hint must have at least text or image_url")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Calculate $e^x$ when $x = 0, 1, 2$...",
                "image_url": "/blob/hint-images/hint1.svg"
            }
        }
    )


# ============================================
# QUESTION SCHEMAS
# ============================================

class QuestionBase(BaseModel):
    """Base question fields - what the data contains"""
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
        description="Path or URL to question diagram/image. MVP: relative path from /blob/. Future: S3 URL."
    )
    subjects: List[SubjectEnum] = Field(
        ...,
        min_length=1,
        description="Subject areas (e.g., Engineering, Mathematics). At least one required."
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
        description="ID of the rubric associated with this question (required, FK)"
    )

    @field_validator('topics')
    @classmethod
    def validate_topics_max_3(cls, v: List[QuestionTopicEnum]) -> List[QuestionTopicEnum]:
        """Ensure max 5 topics per question"""
        if len(v) > 5:
            raise ValueError("Maximum 5 topics allowed per question")
        return v


class Question(QuestionBase):
    """Complete question - Base fields + system fields (id, timestamps)"""
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="When this question was created")
    updated_at: datetime = Field(..., description="When this question was last updated")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "title": "Graph Plotting 1",
                    "question_details": "Plot function $f(x) = e^x$",
                    "think_time_limit_seconds": 20,
                    "record_time_limit_seconds": 60,
                    "instructions": [
                        "You will now have {thinkTime} to prepare...",
                        "Press 'Record' when ready."
                    ],
                    "hints": [
                        {
                            "text": "Calculate $e^x$ when $x = 0, 1, 2$...",
                            "image_url": None
                        }
                    ],
                    "question_image_url": None,
                    "subjects": ["Mathematics"],
                    "topics": ["Graph Plotting", "Mathematics"],
                    "difficulty": "easy",
                    "rubric_id": 2,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                }
            ]
        }
    )
