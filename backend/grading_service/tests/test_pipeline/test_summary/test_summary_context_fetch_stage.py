"""
Tests for SummaryContextFetchStage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from schemas.summary_state import SummaryPipelineStage
from pipeline.summary.summary_context_fetch_stage import (
    SummaryContextFetchStage,
    create_summary_context_fetch_stage
)


class TestSummaryContextFetchStage:
    """Tests for SummaryContextFetchStage."""
    
    @pytest.mark.asyncio
    async def test_fetches_all_session_results(self, sample_summary_state, sample_grading_results):
        """Test that all session results are fetched."""
        # Mock result store
        mock_store = AsyncMock()
        mock_store.get_result = AsyncMock(side_effect=sample_grading_results)
        
        stage = SummaryContextFetchStage(store=mock_store)
        result = await stage.run(sample_summary_state)
        
        # Verify all sessions were fetched
        assert len(result.session_results) == 3
        assert mock_store.get_result.call_count == 3
        
        # Verify stage advanced
        assert result.stage == SummaryPipelineStage.CONTEXT_FETCH
    
    @pytest.mark.asyncio
    async def test_uses_prefetched_results(self, sample_summary_state, sample_session_results):
        """Test that pre-fetched results skip the fetch."""
        # Pre-populate results
        sample_summary_state.session_results = sample_session_results
        
        mock_store = AsyncMock()
        mock_store.get_result = AsyncMock()
        
        stage = SummaryContextFetchStage(store=mock_store)
        result = await stage.run(sample_summary_state)
        
        # Verify store was NOT called (results were pre-fetched)
        mock_store.get_result.assert_not_called()
        
        # Verify results are still available
        assert len(result.session_results) == 3
        assert result.stage == SummaryPipelineStage.CONTEXT_FETCH
    
    @pytest.mark.asyncio
    async def test_raises_on_missing_session(self, sample_summary_state):
        """Test that missing session result raises ValueError."""
        mock_store = AsyncMock()
        # Return None for all sessions (missing results)
        mock_store.get_result = AsyncMock(return_value=None)
        
        stage = SummaryContextFetchStage(store=mock_store)
        
        with pytest.raises(ValueError, match="Missing grading results"):
            await stage.run(sample_summary_state)
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = SummaryContextFetchStage()
        assert stage.name == "SummaryContextFetchStage"
    
    def test_factory_function(self):
        """Test factory function creates stage."""
        stage = create_summary_context_fetch_stage()
        assert isinstance(stage, SummaryContextFetchStage)
