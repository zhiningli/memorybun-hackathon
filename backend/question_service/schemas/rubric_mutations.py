"""
Input schemas for rubric mutations (create/update).

Separated from rubric.py to keep read and write concerns distinct.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from schemas.rubric import RubricDimension

class RubricCreate(BaseModel):
    """
    Schema for creating a new grading rubric.
    """
    name: str = Field(
        ...,
        max_length=100,
        description="Name of the rubric"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description"
    )
    dimensions: List[RubricDimension] = Field(
        ...,
        min_length=1,
        description="List of grading dimensions"
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Initial version number"
    )


class RubricUpdate(BaseModel):
    """
    Schema for updating an existing rubric.
    All fields are optional for partial updates.
    
    Note: version is NOT included here - it is auto-incremented
    by the system on each update.
    """
    name: Optional[str] = Field(
        None,
        max_length=100,
        description="Name of the rubric"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description"
    )
    dimensions: Optional[List[RubricDimension]] = Field(
        None,
        min_length=1,
        description="List of grading dimensions"
    )
