"""
Tests for TaskDecodeStage.
"""

import pytest
import json
from unittest.mock import AsyncMock

from schemas.grading_state import GradingState, PipelineStage
from pipeline.task_decode_stage import TaskDecodeStage, TaskDecodeError


class TestTaskDecodeStage:
    """Tests for TaskDecodeStage."""
    
    @pytest.mark.asyncio
    async def test_validates_existing_state(self, sample_state):
        """Test that run() validates an existing state."""
        stage = TaskDecodeStage()
        result = await stage.run(sample_state)
        
        assert result.stage == PipelineStage.TASK_DECODE
    
    @pytest.mark.asyncio
    async def test_decode_and_create_from_dict(self):
        """Test creating state from task dict."""
        task_dict = {
            "session_id": "test_sess",
            "transcription_text": "The answer is 42",
            "screenshot_key": "test.png"
        }
        
        stage = TaskDecodeStage()
        state = await stage.decode_and_create(task_dict)
        
        assert state.session_id == "test_sess"
        assert state.stage == PipelineStage.TASK_DECODE
    
    @pytest.mark.asyncio
    async def test_decode_and_create_from_json(self):
        """Test creating state from JSON string."""
        task_json = json.dumps({
            "session_id": "test_sess",
            "transcription_text": "The answer is 42",
            "screenshot_key": "test.png"
        })
        
        stage = TaskDecodeStage()
        state = await stage.decode_and_create(task_json)
        
        assert state.session_id == "test_sess"
    
    @pytest.mark.asyncio
    async def test_raises_error_for_missing_field(self):
        """Test that missing required field raises error."""
        task_dict = {
            "session_id": "test_sess"
            # missing transcription_text and screenshot_url
        }
        
        stage = TaskDecodeStage()
        with pytest.raises(TaskDecodeError, match="Missing required field"):
            await stage.decode_and_create(task_dict)
    
    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_json(self):
        """Test that invalid JSON raises error."""
        stage = TaskDecodeStage()
        with pytest.raises(TaskDecodeError, match="Invalid JSON"):
            await stage.decode_and_create("not valid json")
    
    def test_stage_name(self):
        """Test stage name property."""
        stage = TaskDecodeStage()
        assert stage.name == "TaskDecodeStage"
