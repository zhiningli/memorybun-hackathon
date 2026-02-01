"""
Tests for SummaryPersistStage.
"""

import pytest
from unittest.mock import AsyncMock

from schemas.summary_state import SummaryPipelineStage
from pipeline.summary.summary_persist_stage import (
    SummaryPersistStage,
    create_summary_persist_stage
)


class TestSummaryPersistStage:
    """Tests for SummaryPersistStage."""
    
    @pytest.mark.asyncio
    async def test_persists_result(self, sample_summary_state):
        """Test that result is persisted to store."""
        sample_summary_state.result = {
            "summary_id": "summ_test",
            "overall_score": 75
        }
        
        mock_store = AsyncMock()
        mock_store.store_summary_result = AsyncMock(return_value=True)
        
        stage = SummaryPersistStage(store=mock_store)
        result = await stage.run(sample_summary_state)
        
        # Verify store was called
        mock_store.store_summary_result.assert_called_once()
        
        # Verify stage advanced
        assert result.stage == SummaryPipelineStage.PERSIST
    
    @pytest.mark.asyncio
    async def test_adds_completed_at(self, sample_summary_state):
        """Test that completed_at is added if missing."""
        sample_summary_state.result = {
            "summary_id": "summ_test",
            "overall_score": 75
            # No completed_at
        }
        
        mock_store = AsyncMock()
        mock_store.store_summary_result = AsyncMock(return_value=True)
        
        stage = SummaryPersistStage(store=mock_store)
        result = await stage.run(sample_summary_state)
        
        # Verify completed_at was added
        assert "completed_at" in result.result
    
    @pytest.mark.asyncio
    async def test_raises_without_result(self, sample_summary_state):
        """Test that stage raises without result."""
        mock_store = AsyncMock()
        stage = SummaryPersistStage(store=mock_store)
        
        with pytest.raises(ValueError, match="Result must be populated"):
            await stage.run(sample_summary_state)
    
    @pytest.mark.asyncio
    async def test_raises_on_store_failure(self, sample_summary_state):
        """Test that stage raises when store fails."""
        sample_summary_state.result = {
            "summary_id": "summ_test",
            "overall_score": 75
        }
        
        mock_store = AsyncMock()
        mock_store.store_summary_result = AsyncMock(return_value=False)
        
        stage = SummaryPersistStage(store=mock_store)
        
        with pytest.raises(ValueError, match="Failed to store"):
            await stage.run(sample_summary_state)
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = SummaryPersistStage()
        assert stage.name == "SummaryPersistStage"
    
    def test_factory_function(self):
        """Test factory function creates stage."""
        stage = create_summary_persist_stage()
        assert isinstance(stage, SummaryPersistStage)
