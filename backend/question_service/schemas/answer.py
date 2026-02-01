"""
Pydantic schemas for Answers

These schemas serve dual purposes:
1. API request/response validation (now)
2. Blueprint for database models (later)
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# Question Schemas
class AnswerBase(BaseModel):
    """Base answer fields - what the data contains"""
    text_answer: Optional[str] = Field(
        None,
        max_length=5000,
        description="Text answer to the question (max 5000 chars)"
    )
    graph_answer_url: Optional[str] = Field(
        None,
        description="Path or URL to graph answer image. MVP: relative path from /blob/ (e.g., '/blob/answer-images/answer1.svg'). Recommended: SVG for graphs/diagrams (smaller, scalable). Future: can be S3 URL or database reference."
    )
    ideal_answer_structure: Optional[List[str]] = Field(
        None,
        description="List of steps or points that define the ideal structure of the answer."
    )
    key_constraints_to_mention: Optional[List[str]] = Field(
        None,
        description="List of key constraints or specific details that must be mentioned in the answer."
    )


class Answer(AnswerBase):
    """Complete answer - Base fields + system fields (id, timestamps)"""
    id: int = Field(..., description="Unique identifier")
    question_id: int = Field(..., description="ID of the question")
    created_at: datetime = Field(..., description="When this answer was created")
    updated_at: datetime = Field(..., description="When this answer was last updated")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "question_id": 1,
                    "text_answer": "To plot y = e^x, note that it always stays above the x-axis since e^x > 0 for all x. The graph passes through (0, 1). As x → -∞, y → 0, approaching but never touching the x-axis. As x → ∞, y grows rapidly without bound. The curve is smooth, increasing, and concave upward everywhere. Key points include (-∞, 0), (0, 1), (1, 2.718), (∞, ∞).",
                    "graph_answer_url": None,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                } 
            ]
        }
    )

