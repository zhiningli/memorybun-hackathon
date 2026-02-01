"""
Pydantic schemas for Question Lists.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

from schemas.question import SubjectEnum


class AccessStatusEnum(str, Enum):
    """Access status for question lists"""
    PUBLIC = "public"
    PRIVATE = "private"
    PREMIUM = "premium"


class QuestionListCategoryEnum(str, Enum):
    """Categories for question lists"""
    GRAPH_PLOTTING = "Graph Plotting"
    CIRCUIT_ANALYSIS = "Circuit Analysis"
    DYNAMICS = "Dynamics"
    FLUID_DYNAMICS = "Fluid Dynamics"
    GUIDED = "Guided"
    FULL_RUN = "Full Run"


class QuestionListDifficultyEnum(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    ADVANCED = "Advanced"


class QuestionListMetadataBase(BaseModel):
    """Base question list metadata fields - what the data contains"""
    title: str = Field(..., min_length=1, max_length=200, description="Title of the question list")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    categories: List[QuestionListCategoryEnum] = Field(..., min_length=1, description="Categories of questions (multi-value)")
    subjects: List[SubjectEnum] = Field(..., min_length=1, description="Subject areas (e.g., Engineering, Mathematics)")
    difficulty: QuestionListDifficultyEnum = Field(..., description="Overall difficulty level")
    duration_seconds: int = Field(..., gt=0, description="Estimated duration in seconds")
    access_status: AccessStatusEnum = Field(default=AccessStatusEnum.PUBLIC, description="Access status of the list")


class QuestionListMetadata(QuestionListMetadataBase):
    """
    Question list metadata - Contains information about a question list without the actual questions.
    
    This represents the metadata/summary of a question list (title, description, category, etc.)
    but does not include the questions themselves. Use this for listing question sets.
    """
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="When this list was created")
    updated_at: datetime = Field(..., description="When this list was last updated")
    
    model_config = ConfigDict(
        title="QuestionListMetadata",
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Graph Plotting",
                "description": "Learn the basics of graphing mathematical functions",
                "categories": ["Graph Plotting"],
                "subjects": ["Engineering"],
                "difficulty": "Easy",
                "duration_seconds": 1800,
                "access_status": "public",
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            }
        }
    )



# Question List Item Schemas
class QuestionListItem(BaseModel):
    """
    This schema is used to link a question to a question list
    Used for joint table between question and question list
    Very unlikely to be exposed to the client
    """
    question_list_id: int
    question_id: int
    order_index: int
    weightage: float = Field(..., ge=0.0, le=1.0, description="Weight of the question in the list")
    created_at: datetime = Field(..., description="When this item was created")
    updated_at: datetime = Field(..., description="When this item was last updated")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question_list_id": 1,
                "question_id": 1,
                "order_index": 1,
                "weightage": 0.33,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            }
        }
    )

