"""
Tests for Summary Result Schema.

Tests validation, serialization, and edge cases.
"""

import pytest
from datetime import datetime, timezone
from schemas.summary_result import (
    SummaryResult, 
    SummaryLLMResponse, 
    DimensionScore, 
    ModelInfo,
    SUMMARY_DIMENSIONS
)


class TestDimensionScore:
    """Tests for DimensionScore schema."""
    
    def test_valid_dimension_score(self):
        """Test creating a valid dimension score."""
        score = DimensionScore(
            dimension="Problem Framing",
            feedback="Strong ability to identify core principles."
        )
        assert score.dimension == "Problem Framing"
        assert score.feedback == "Strong ability to identify core principles."
    
    def test_dimension_score_minimal(self):
        """Test dimension score with minimal data."""
        score = DimensionScore(
            dimension="Time Management",
            feedback="Good pacing."
        )
        assert score.dimension == "Time Management"
        assert score.feedback == "Good pacing."


class TestSummaryLLMResponse:
    """Tests for SummaryLLMResponse schema (LLM output format)."""
    
    def test_valid_llm_response(self):
        """Test creating a valid LLM response."""
        response = SummaryLLMResponse(
            dimension_scores=[
                DimensionScore(dimension="Problem Framing", feedback="Good"),
                DimensionScore(dimension="Solution Execution", feedback="Good"),
                DimensionScore(dimension="Technical Correctness", feedback="Good"),
                DimensionScore(dimension="Communication & Whiteboard Use", feedback="Good"),
                DimensionScore(dimension="Time Management", feedback="Needs work"),
            ],
            analytics_summary=[
                "Strong overall performance",
                "Best area: Problem Framing",
                "Improvement area: Time Management"
            ],
            overall_feedback="Solid performance overall.",
            key_strengths=["Strong theoretical understanding"],
            areas_for_improvement=["Time management"]
        )
        assert len(response.dimension_scores) == 5
        assert len(response.analytics_summary) == 3
    

    def test_llm_response_requires_5_dimensions(self):
        """Test that exactly 5 dimension scores are required."""
        # Too few dimensions
        with pytest.raises(ValueError):
            SummaryLLMResponse(
                dimension_scores=[
                    DimensionScore(dimension="Problem Framing", feedback="Test")
                ],  # Only 1
                analytics_summary=["Test", "Test", "Test"],
                overall_feedback="Test",
                key_strengths=["Test"],
                areas_for_improvement=["Test"]
            )


class TestSummaryResult:
    """Tests for SummaryResult schema."""
    
    def test_valid_summary_result(self):
        """Test creating a valid summary result."""
        result = SummaryResult(
            summary_id="summ_abc123",
            session_ids=["sess_1", "sess_2"],
            dimension_scores=[
                DimensionScore(dimension=d, feedback=f"Feedback for {d}") 
                for d in SUMMARY_DIMENSIONS
            ],
            analytics_summary=["Strong performance", "Top dimension: Problem Framing"],
            overall_feedback="Good performance overall.",
            key_strengths=["Strong understanding", "Clear communication"],
            areas_for_improvement=["Time management", "Whiteboard clarity"]
        )
        assert result.summary_id == "summ_abc123"
        assert len(result.session_ids) == 2
        assert result.completed_at is not None
    

    def test_summary_result_with_model_info(self):
        """Test summary result with model info."""
        result = SummaryResult(
            summary_id="summ_test",
            session_ids=["sess_1", "sess_2", "sess_3"],
            dimension_scores=[
                DimensionScore(dimension=d, feedback="Good") 
                for d in SUMMARY_DIMENSIONS
            ],
            analytics_summary=["Test"],
            overall_feedback="Excellent work!",
            key_strengths=["Test"],
            areas_for_improvement=["Test"],
            model_info=ModelInfo(provider="gemini", model="gemini-1.5-flash"),
            processing_time=2.5
        )
        assert result.model_info.provider == "gemini"
        assert result.model_info.model == "gemini-1.5-flash"
        assert result.processing_time == 2.5
    
    def test_serialization(self):
        """Test JSON serialization."""
        result = SummaryResult(
            summary_id="summ_abc123",
            session_ids=["sess_1"],
            dimension_scores=[
                DimensionScore(dimension=d, feedback="Good") 
                for d in SUMMARY_DIMENSIONS
            ],
            analytics_summary=["Test"],
            overall_feedback="Good work!",
            key_strengths=["Strength 1"],
            areas_for_improvement=["Improvement 1"]
        )
        
        json_str = result.model_dump_json()
        assert "summ_abc123" in json_str
        assert "sess_1" in json_str
        assert "Problem Framing" in json_str
        
        # Deserialize
        data = result.model_dump()
        assert data["summary_id"] == "summ_abc123"


class TestSummaryDimensions:
    """Tests for the fixed SUMMARY_DIMENSIONS list."""
    
    def test_dimensions_count(self):
        """Test that there are exactly 5 dimensions."""
        assert len(SUMMARY_DIMENSIONS) == 5
    
    def test_dimensions_names(self):
        """Test the dimension names."""
        expected = [
            "Problem Framing",
            "Solution Execution",
            "Technical Correctness",
            "Communication & Whiteboard Use",
            "Time Management"
        ]
        assert SUMMARY_DIMENSIONS == expected
