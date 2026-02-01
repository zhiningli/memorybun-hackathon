"""
Pydantic schemas for Rubrics.

Rubrics define grading criteria for evaluating student responses.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class RubricCriteria(BaseModel):
    """
    A specific criteria within a dimension.
    """
    name: str = Field(
        ...,
        max_length=100,
        description="Name of the criteria"
    )
    description: str = Field(
        ...,
        max_length=500,
        description="Description of the criteria"
    )
    scoring_condition: str = Field(
        ...,
        max_length=500,
        description="Condition to be met for scoring"
    )


class RubricDimension(BaseModel):
    """
    A single dimension of a grading rubric (e.g., "Technical Correctness").
    """
    name: str = Field(
        ...,
        max_length=100,
        description="Name of the dimension"
    )
    description: str = Field(
        ...,
        max_length=1000,
        description="Detailed description of what to look for"
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight of this dimension (0.0 to 1.0)"
    )
    criterias: List[RubricCriteria] = Field(
        ...,
        min_length=1,
        description="List of specific grading criteria"
    )


class Rubric(BaseModel):
    """
    Full grading rubric for a specific category or question type.
    """
    id: int = Field(..., description="Unique identifier for the rubric")
    name: str = Field(
        ...,
        max_length=100,
        description="Name of the rubric (e.g., 'Graph Plotting', 'General')"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description of the rubric's purpose"
    )
    dimensions: List[RubricDimension] = Field(
        ...,
        min_length=1,
        description="List of grading dimensions"
    )
    version: Optional[int] = Field(
        default=1,
        ge=1,
        description="Version number for tracking rubric revisions"
    )
    created_at: datetime = Field(..., description="When this rubric was created")
    updated_at: datetime = Field(..., description="When this rubric was last updated")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Graph Plotting",
                "description": "Rubric for evaluating graph plotting questions",
                "dimensions": [
                    {
                        "name": "Technical Correctness",
                        "description": "Equations, assumptions, results correct",
                        "weight": 0.25,
                        "criterias": [
                            {
                                "name": "Correct equations",
                                "description": "Mathematical expressions are correct",
                                "scoring_condition": "Equations are dimensionally and conceptually correct"
                            }
                        ]
                    }
                ],
                "version": 1,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            }
        }
    )
