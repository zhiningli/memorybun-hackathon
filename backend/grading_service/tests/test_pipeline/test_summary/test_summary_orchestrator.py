"""
Tests for SummaryOrchestrator.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from schemas.summary_state import SummaryState, SummaryPipelineStage
from pipeline.summary.summary_orchestrator import (
    SummaryOrchestrator,
    create_summary_orchestrator
)
from pipeline.summary.summary_validate_stage import SummaryValidationError


def create_mock_stage(name: str):
    """Create a mock stage that is awaitable."""
    mock_stage = AsyncMock(side_effect=lambda s: s)
    mock_stage.name = name
    return mock_stage


class TestSummaryOrchestrator:
    """Tests for SummaryOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_runs_all_stages(self, sample_session_results, valid_summary_llm_response):
        """Test that orchestrator runs all stages in sequence."""
        # Create mock stages that are awaitable
        mock_stages = [
            create_mock_stage(f"Mock{name}Stage")
            for name in ["Context", "Prompt", "LLM", "Validate", "Persist"]
        ]
        
        orchestrator = SummaryOrchestrator(stages=mock_stages)
        
        task_data = {
            "summary_id": "summ_test",
            "session_ids": ["sess_1"]
        }
        
        result = await orchestrator.run_pipeline(task_data)
        
        # Verify all stages were called
        for stage in mock_stages:
            stage.assert_called_once()
        
        # Verify final state
        assert result.stage == SummaryPipelineStage.COMPLETED
    
    @pytest.mark.asyncio
    async def test_creates_state_from_task(self):
        """Test that orchestrator creates state from task data."""
        # Simple mock stage that just returns the state
        mock_stage = create_mock_stage("MockStage")
        
        orchestrator = SummaryOrchestrator(stages=[mock_stage])
        
        task_data = {
            "summary_id": "summ_abc",
            "session_ids": ["sess_1", "sess_2"]
        }
        
        result = await orchestrator.run_pipeline(task_data)
        
        # Verify state was created correctly
        assert result.summary_id == "summ_abc"
        assert len(result.session_ids) == 2
    
    @pytest.mark.asyncio
    async def test_raises_on_missing_fields(self):
        """Test that orchestrator raises on missing required fields."""
        orchestrator = SummaryOrchestrator(stages=[])
        
        # Missing session_ids
        with pytest.raises(ValueError, match="Missing required field"):
            await orchestrator.run_pipeline({
                "summary_id": "test"
            })
        

    
    @pytest.mark.asyncio
    async def test_run_from_state(self):
        """Test running from existing state."""
        mock_stage = create_mock_stage("MockStage")
        
        orchestrator = SummaryOrchestrator(stages=[mock_stage])
        
        state = SummaryState(
            summary_id="summ_test",
            session_ids=["sess_1"]
        )
        
        result = await orchestrator.run_from_state(state)
        
        assert result.stage == SummaryPipelineStage.COMPLETED
    
    def test_default_stages(self):
        """Test that default stages are created."""
        orchestrator = SummaryOrchestrator()
        
        # Should have 5 default stages
        assert len(orchestrator.stages) == 5
    
    def test_custom_stages(self):
        """Test that custom stages can be injected."""
        mock_stage = AsyncMock()
        orchestrator = SummaryOrchestrator(stages=[mock_stage])
        
        assert len(orchestrator.stages) == 1
        assert orchestrator.stages[0] == mock_stage
    
    def test_factory_function(self):
        """Test factory function creates orchestrator."""
        orchestrator = create_summary_orchestrator()
        assert isinstance(orchestrator, SummaryOrchestrator)
