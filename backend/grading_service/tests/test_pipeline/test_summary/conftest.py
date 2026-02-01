"""
Shared fixtures for summary pipeline tests.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from schemas.summary_state import SummaryState, SummaryPipelineStage
from schemas.summary_result import SUMMARY_DIMENSIONS
from schemas.grading_result import GradingResult, ScoreBreakdown


@pytest.fixture
def sample_summary_state() -> SummaryState:
    """Create a sample summary state for testing."""
    return SummaryState(
        summary_id="summ_test_123",
        session_ids=["sess_1", "sess_2", "sess_3"]
    )


@pytest.fixture
def sample_session_results():
    """Sample session grading results."""
    return [
        {
            "session_id": "sess_1",
            "feedback": "Good understanding of the concept.",
            "score_breakdown": [
                {"dimension": "Correctness", "percentage": 0.8, "feedback": "Accurate"},
                {"dimension": "Reasoning Clarity", "percentage": 0.75, "feedback": "Clear"}
            ]
        },
        {
            "session_id": "sess_2",
            "feedback": "Solid performance with minor issues.",
            "score_breakdown": [
                {"dimension": "Correctness", "percentage": 0.7, "feedback": "Some errors"},
                {"dimension": "Communication", "percentage": 0.85, "feedback": "Well explained"}
            ]
        },
        {
            "session_id": "sess_3",
            "feedback": "Completed all parts effectively.",
            "score_breakdown": [
                {"dimension": "Whiteboard Use", "percentage": 0.8, "feedback": "Good visuals"},
                {"dimension": "Time Management", "percentage": 0.65, "feedback": "Slightly rushed"}
            ]
        }
    ]


@pytest.fixture
def sample_grading_results(sample_session_results):
    """Sample session grading results as GradingResult objects."""
    # Note: This constructs GradingResult objects. 
    # If ScoreBreakdown specific fields like 'score' are missing in logic
    # schema, they might be dropped here depending on model config.
    # For test purposes of context fetch, this is sufficient.
    return [GradingResult(**res) for res in sample_session_results]


@pytest.fixture
def valid_summary_llm_response() -> str:
    """Valid JSON response from LLM for summary."""
    return json.dumps({
        "dimension_scores": [
            {"dimension": "Problem Framing", "feedback": "Good ability to identify core principles."},
            {"dimension": "Solution Execution", "feedback": "Effective approach with minor errors."},
            {"dimension": "Technical Correctness", "feedback": "Clear logical reasoning."},
            {"dimension": "Communication & Whiteboard Use", "feedback": "Well articulated explanations."},
            {"dimension": "Time Management", "feedback": "Some pacing issues."}
        ],
        "analytics_summary": [
            "Strong performance overall",
            "Best area: Problem Framing",
            "Improvement area: Time Management"
        ],
        "overall_feedback": "Solid performance with room for improvement in time management.",
        "key_strengths": [
            "Strong technical accuracy",
            "Clear communication"
        ],
        "areas_for_improvement": [
            "Time management",
            "Consistent pacing"
        ]
    })


@pytest.fixture
def sample_state_with_results(sample_summary_state, sample_session_results):
    """Summary state with session results populated."""
    sample_summary_state.session_results = sample_session_results
    return sample_summary_state


@pytest.fixture
def sample_state_with_prompts(sample_state_with_results):
    """Summary state with prompts populated."""
    sample_state_with_results.system_prompt = "You are an expert grader..."
    sample_state_with_results.user_prompt = "Summarize these sessions..."
    return sample_state_with_results
