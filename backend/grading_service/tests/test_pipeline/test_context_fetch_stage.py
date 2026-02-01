"""
Tests for ContextFetchStage.
"""

import pytest
from unittest.mock import AsyncMock

from schemas.grading_state import PipelineStage
from schemas.context import QuestionContext
from pipeline.context_fetch_stage import ContextFetchStage, create_context_fetch_stage


class TestContextFetchStage:
    """Tests for ContextFetchStage."""
    
    @pytest.mark.asyncio
    async def test_fetches_context(self, sample_state):
        """Test that context is fetched and stored in state."""
        # Mock provider to return QuestionContext object
        mock_context = QuestionContext(
            question_id=789,
            rubric={"dimensions": [{"name": "test", "weight": 1.0}]},
            reference_answer={"text_answer": "ans"},
            question={"title": "Test Question"}
        )
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=mock_context)
        
        stage = ContextFetchStage(provider=mock_provider)
        result = await stage.run(sample_state)
        
        # Verify context is populated with QuestionContext object
        assert result.context is not None
        assert isinstance(result.context, QuestionContext)
        assert result.context.rubric is not None
        assert result.context.reference_answer is not None
        
        # Verify stage advanced
        assert result.stage == PipelineStage.CONTEXT_FETCH
    
    @pytest.mark.asyncio
    async def test_context_contains_rubric_dimensions(self, sample_state):
        """Test that context contains rubric with dimensions."""
        # Mock provider with dimensions-based rubric
        mock_context = QuestionContext(
            question_id=789,
            rubric={"dimensions": [{"name": "C1", "weight": 1.0}]},
            reference_answer={"text_answer": "ans"},
            question={"title": "Test"}
        )
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=mock_context)
        
        stage = ContextFetchStage(provider=mock_provider)
        result = await stage.run(sample_state)
        
        # Check rubric dimensions
        rubric = result.context.rubric
        assert "dimensions" in rubric
        assert len(rubric["dimensions"]) > 0
    
    @pytest.mark.asyncio
    async def test_uses_injected_provider(self, sample_state, sample_context):
        """Test that custom provider can be injected."""
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        
        stage = ContextFetchStage(provider=mock_provider)
        result = await stage.run(sample_state)
        
        # Verify mock was called with numeric question_id (converted from string)
        mock_provider.gen_question_context.assert_called_once_with(
            question_id=789  # Converted to int in stage
        )
        
        # Verify custom context was used
        assert result.context == sample_context
        assert isinstance(result.context, QuestionContext)
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = ContextFetchStage()
        assert stage.name == "ContextFetchStage"
    
    def test_factory_function(self):
        """Test factory function creates stage."""
        stage = create_context_fetch_stage()
        assert isinstance(stage, ContextFetchStage)
    
    @pytest.mark.asyncio
    async def test_fetches_screenshot(self, sample_state, sample_context):
        """Test that screenshot is fetched when screenshot_key is provided."""
        from unittest.mock import patch, MagicMock
        import httpx
        from config import settings
        
 
        # Update state with key
        sample_state.screenshot_key = "test.png"
        
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        
        # Mock httpx client
        mock_response = MagicMock()
        mock_response.content = b"fake_screenshot_data"
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class, \
             patch('pipeline.context_fetch_stage.settings.transcription_service_url', 'http://internal-transcription'):
            
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            stage = ContextFetchStage(provider=mock_provider)
            result = await stage.run(sample_state)
            
            # Verify screenshot was fetched
            assert result.screenshot_data == b"fake_screenshot_data"
            
            # Verify HTTP request was made to correct internal URL
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args[0]
            assert "http://internal-transcription/api/v1/transcribe/screenshots/test.png" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_handles_screenshot_fetch_failure(self, sample_state, sample_context):
        """Test that screenshot fetch failure doesn't break the pipeline."""
        from unittest.mock import patch
        import httpx
        
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        
        # Mock httpx to raise an error
        with patch('httpx.AsyncClient') as mock_client_class, \
             patch('pipeline.context_fetch_stage.settings.transcription_service_url', 'http://internal-transcription'):
            
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
            mock_client_class.return_value = mock_client
            
            stage = ContextFetchStage(provider=mock_provider)
            result = await stage.run(sample_state)
            
            # Verify screenshot_data is None on failure
            assert result.screenshot_data is None
            
            # Verify context was still fetched
            assert result.context is not None
            
            # Verify stage still advanced (failure is gracefully handled)
            assert result.stage == PipelineStage.CONTEXT_FETCH
