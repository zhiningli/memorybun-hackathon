"""
Tests for Grading Result Schema.

Tests validation, serialization, and edge cases.
"""

import pytest
from datetime import datetime, timezone
from schemas.grading_result import GradingResult, ScoreBreakdown, ModelInfo


class TestScoreBreakdown:
    """Tests for ScoreBreakdown schema."""
    
    def test_valid_score_breakdown(self):
        """Test creating a valid score breakdown."""
        breakdown = ScoreBreakdown(
            dimension="Understanding",
            percentage=0.85,
            feedback="Good understanding"
        )
        assert breakdown.dimension == "Understanding"
        assert breakdown.feedback == "Good understanding"
    
    def test_score_breakdown_minimal(self):
        """Test score breakdown with only required fields."""
        breakdown = ScoreBreakdown(
            dimension="Accuracy",
            percentage=0.75
        )
        assert breakdown.feedback is None
    


class TestModelInfo:
    """Tests for ModelInfo schema."""
    
    def test_valid_model_info(self):
        """Test creating valid model info."""
        info = ModelInfo(
            provider="openai",
            model="gpt-4o-mini",
            prompt_version="v1.0",
            temperature=0.3
        )
        assert info.provider == "openai"
        assert info.model == "gpt-4o-mini"
        assert info.prompt_version == "v1.0"
        assert info.temperature == 0.3
    
    def test_model_info_minimal(self):
        """Test model info with only required fields."""
        info = ModelInfo(provider="anthropic", model="claude-3")
        assert info.provider == "anthropic"
        assert info.model == "claude-3"
        assert info.prompt_version is None


class TestGradingResult:
    """Tests for GradingResult schema."""
    
    def test_valid_grading_result(self):
        """Test creating a valid grading result."""
        result = GradingResult(
            session_id="sess_abc123",
            feedback="Good work"
        )
        assert result.session_id == "sess_abc123"
        assert result.feedback == "Good work"
        assert result.completed_at is not None
    
    def test_grading_result_full(self):
        """Test grading result with all fields."""
        result = GradingResult(
            session_id="sess_abc123",
            score_breakdown=[
                ScoreBreakdown(dimension="Understanding", percentage=0.8),
                ScoreBreakdown(dimension="Accuracy", percentage=0.9)
            ],
            feedback="Good work",
            internal_notes="Student shows understanding",
            confidence=0.92,
            model_info=ModelInfo(provider="openai", model="gpt-4o-mini"),
            processing_time=2.3
        )
        assert len(result.score_breakdown) == 2
        assert result.confidence == 0.92
        assert result.model_info.provider == "openai"
        assert result.processing_time == 2.3
    
    
    def test_confidence_bounds(self):
        """Test confidence must be between 0 and 1."""
        # Valid confidence
        result = GradingResult(
            session_id="test",
            feedback="Test",
            confidence=0.95
        )
        assert result.confidence == 0.95
        
        # Invalid confidence
        with pytest.raises(ValueError):
            GradingResult(
                session_id="test",
                feedback="Test",
                confidence=1.5
            )
    
    def test_serialization(self):
        """Test JSON serialization."""
        result = GradingResult(
            session_id="sess_abc123",
            feedback="Good work",
            model_info=ModelInfo(provider="openai", model="gpt-4o-mini")
        )
        
        json_str = result.model_dump_json()
        assert "sess_abc123" in json_str
        assert "openai" in json_str
        
        # Deserialize
        data = result.model_dump()
        assert data["session_id"] == "sess_abc123"
