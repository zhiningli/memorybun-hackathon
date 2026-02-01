"""
Shared fixtures for pipeline tests.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from schemas.grading_state import GradingState, PipelineStage
from schemas.context import QuestionContext


@pytest.fixture
def sample_state() -> GradingState:
    """Create a sample grading state for testing."""
    return GradingState(
        session_id="test_sess_123",
        student_id="student_456",
        question_id="789",  # String type as defined in schema
        transcription_text="The derivative of x squared is 2x because we apply the power rule.",
        screenshot_key="test_sess_123.png"
    )


@pytest.fixture
def sample_context() -> QuestionContext:
    """Sample context from ContextFetchStage."""
    return QuestionContext(
        question_id=789,
        rubric={
            "id": 1,
            "name": "Calculus Rubrics",
            "description": "Rubric for calculus questions",
            "dimensions": [
                {"name": "Understanding", "description": "Shows understanding of power rule", "weight": 0.4, "example_criteria": "Identifies power rule"},
                {"name": "Explanation", "description": "Clear explanation", "weight": 0.3, "example_criteria": "Steps are clear"},
                {"name": "Accuracy", "description": "Mathematical accuracy", "weight": 0.3, "example_criteria": "Correct result"}
            ],
            "version": 1
        },
        reference_answer={
            "text_answer": "The derivative of x^2 is 2x by the power rule.",
            "ideal_answer_structure": ["Identify the power rule", "Apply derivative formula", "State final result"],
            "key_constraints_to_mention": ["Power rule", "Exponent reduction"]
        },
        question={
            "title": "Derivative of x^2",
            "question_details": "Find the derivative of x squared",
            "topics": ["Mathematics"]
        }
    )


@pytest.fixture
def valid_llm_response() -> str:
    """Valid JSON response from LLM."""
    return json.dumps({
        "feedback": "Good understanding of the power rule. Your explanation is clear and correct.",
        "confidence": 0.92,
        "internal_notes": "Student correctly applied power rule.",
        "score_breakdown": [
            {"dimension": "Understanding", "feedback": "Good"},
            {"dimension": "Explanation", "feedback": "Clear"},
            {"dimension": "Accuracy", "feedback": "Correct"}
        ]
    })
