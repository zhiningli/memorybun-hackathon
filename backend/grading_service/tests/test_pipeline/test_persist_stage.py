"""
Tests for PersistStage.
"""

import pytest
from unittest.mock import AsyncMock

from schemas.grading_state import PipelineStage
from pipeline.persist_stage import PersistStage, create_persist_stage


class TestPersistStage:
    """Tests for PersistStage."""
    
    @pytest.mark.asyncio
    async def test_persists_result(self, sample_state, valid_llm_response):
        """Test that result is persisted to store."""
        # Setup state with result
        sample_state.result = {
            "session_id": sample_state.session_id,
            "score": 0.85,
            "feedback": "Good work!"
        }
        
        # Mock store
        mock_store = AsyncMock()
        mock_store.store_result = AsyncMock(return_value=True)
        
        stage = PersistStage(store=mock_store)
        result = await stage.run(sample_state)
        
        # Verify store was called
        mock_store.store_result.assert_called_once()
        
        # Verify stage advanced
        assert result.stage == PipelineStage.PERSIST
    
    @pytest.mark.asyncio
    async def test_raises_error_without_result(self, sample_state):
        """Test that error is raised if result not set."""
        sample_state.result = None
        
        stage = PersistStage()
        with pytest.raises(ValueError, match="Result must be set"):
            await stage.run(sample_state)
    
    @pytest.mark.asyncio
    async def test_raises_error_on_store_failure(self, sample_state):
        """Test that error is raised if store fails."""
        sample_state.result = {"session_id": "test", "score": 0.5, "feedback": "ok"}
        
        mock_store = AsyncMock()
        mock_store.store_result = AsyncMock(return_value=False)
        
        stage = PersistStage(store=mock_store)
        with pytest.raises(Exception, match="Failed to store"):
            await stage.run(sample_state)
    
    def test_stage_name(self):
        """Test stage name property."""
        stage = PersistStage()
        assert stage.name == "PersistStage"
    
    def test_factory_function(self):
        """Test factory function creates stage."""
        stage = create_persist_stage()
        assert isinstance(stage, PersistStage)
