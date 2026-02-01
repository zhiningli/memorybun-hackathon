"""
Tests for GradingWorker.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.grading_worker import GradingWorker


class TestGradingWorker:
    """Tests for GradingWorker."""
    
    @pytest.fixture
    def sample_task(self) -> dict:
        """Sample task dict (not JSON string)."""
        return {
            "session_id": "test_sess_123",
            "student_id": "student_456",
            "question_id": "789",  # String type
            "transcription_text": "The derivative of x^2 is 2x.",
            "screenshot_key": "test.png",
            "retry_count": 0,
            "max_retries": 3
        }
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Mock orchestrator that returns completed state."""
        orchestrator = AsyncMock()
        mock_state = MagicMock()
        mock_state.result = {"score": 0.85, "feedback": "Good"}
        mock_state.stage = "completed"
        orchestrator.run_pipeline = AsyncMock(return_value=mock_state)
        return orchestrator
    
    def test_init_default_workers(self):
        """Test default worker count."""
        worker = GradingWorker()
        assert worker.num_workers == 2
        assert not worker.is_running
    
    def test_init_custom_workers(self):
        """Test custom worker count."""
        worker = GradingWorker(num_workers=4)
        assert worker.num_workers == 4
    
    @pytest.mark.asyncio
    async def test_start_creates_workers(self, mock_orchestrator):
        """Test that start() creates worker tasks."""
        worker = GradingWorker(num_workers=2, orchestrator=mock_orchestrator)
        
        # Mock grading_queue to avoid Redis connection
        with patch('services.grading_worker.grading_queue') as mock_queue:
            mock_queue.dequeue = AsyncMock(return_value=None)
            
            await worker.start()
            
            assert worker.is_running
            assert len(worker._workers) == 2
            
            # Stop immediately
            await worker.stop()
    
    @pytest.mark.asyncio
    async def test_start_idempotent(self, mock_orchestrator):
        """Test that starting twice doesn't create duplicate workers."""
        worker = GradingWorker(num_workers=1, orchestrator=mock_orchestrator)
        
        with patch('services.grading_worker.grading_queue') as mock_queue:
            mock_queue.dequeue = AsyncMock(return_value=None)
            
            await worker.start()
            await worker.start()  # Second call should be no-op
            
            assert len(worker._workers) == 1
            
            await worker.stop()
    
    @pytest.mark.asyncio
    async def test_stop_clears_workers(self, mock_orchestrator):
        """Test that stop() clears worker tasks."""
        worker = GradingWorker(num_workers=2, orchestrator=mock_orchestrator)
        
        with patch('services.grading_worker.grading_queue') as mock_queue:
            mock_queue.dequeue = AsyncMock(return_value=None)
            
            await worker.start()
            await worker.stop()
            
            assert not worker.is_running
            assert len(worker._workers) == 0
    
    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, mock_orchestrator):
        """Test that stop() is safe when not running."""
        worker = GradingWorker(orchestrator=mock_orchestrator)
        
        # Should not raise
        await worker.stop()
        assert not worker.is_running
    
    @pytest.mark.asyncio
    async def test_process_task_runs_orchestrator(self, sample_task, mock_orchestrator):
        """Test that _process_task calls orchestrator."""
        worker = GradingWorker(orchestrator=mock_orchestrator)
        
        with patch('services.grading_worker.result_store') as mock_store:
            mock_store.set_status = AsyncMock(return_value=True)
            
            # Pass dict, not JSON string
            result = await worker._process_task(sample_task, "test-worker")
            
            assert result is True
            mock_orchestrator.run_pipeline.assert_called_once_with(sample_task)
    
    @pytest.mark.asyncio
    async def test_process_task_handles_failure(self, sample_task, mock_orchestrator):
        """Test that _process_task returns False on failure."""
        mock_orchestrator.run_pipeline = AsyncMock(side_effect=Exception("LLM error"))
        worker = GradingWorker(orchestrator=mock_orchestrator)
        
        with patch('services.grading_worker.result_store') as mock_store:
            mock_store.set_status = AsyncMock(return_value=True)
            
            # Should return False for retry
            result = await worker._process_task(sample_task, "test-worker")
            
            assert result is False
            assert "last_error" in sample_task
    
    @pytest.mark.asyncio
    async def test_update_failure_status(self, mock_orchestrator):
        """Test that _update_failure_status updates status."""
        worker = GradingWorker(orchestrator=mock_orchestrator)
        
        with patch('services.grading_worker.result_store') as mock_store:
            mock_store.set_status = AsyncMock(return_value=True)
            
            await worker._update_failure_status("test_session", "Test error message")
            
            mock_store.set_status.assert_called_once_with(
                session_id="test_session",
                status="failed",
                message="Test error message"
            )
    
    @pytest.mark.asyncio
    async def test_handle_retry_requeues_on_failure(self, sample_task, mock_orchestrator):
        """Test that _handle_retry requeues task with backoff."""
        worker = GradingWorker(orchestrator=mock_orchestrator)
        sample_task["retry_count"] = 0
        
        with patch('services.grading_worker.grading_queue') as mock_queue, \
             patch('services.grading_worker.result_store') as mock_store:
            mock_queue.requeue_with_backoff = AsyncMock(return_value=True)
            mock_store.set_status = AsyncMock(return_value=True)
            
            await worker._handle_retry(sample_task, "test-worker")
            
            mock_queue.requeue_with_backoff.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_retry_moves_to_dlq_after_max(self, sample_task, mock_orchestrator):
        """Test that _handle_retry moves to DLQ after max retries."""
        worker = GradingWorker(orchestrator=mock_orchestrator)
        sample_task["retry_count"] = 3
        sample_task["max_retries"] = 3
        
        with patch('services.grading_worker.grading_queue') as mock_queue, \
             patch('services.grading_worker.result_store') as mock_store:
            mock_queue.move_to_dlq = AsyncMock(return_value=True)
            mock_store.set_status = AsyncMock(return_value=True)
            
            await worker._handle_retry(sample_task, "test-worker")
            
            mock_queue.move_to_dlq.assert_called_once()
    
    def test_is_running_property(self, mock_orchestrator):
        """Test is_running property."""
        worker = GradingWorker(orchestrator=mock_orchestrator)
        
        assert not worker.is_running
        
        worker._running = True
        assert worker.is_running


class TestGradingWorkerIntegration:
    """Integration tests for worker with full pipeline."""
    
    @pytest.fixture
    def sample_context(self):
        """Sample context."""
        from schemas.context import QuestionContext
        return QuestionContext(
            question_id=789,
            rubric={"dimensions": []},
            reference_answer={"text_answer": "2x"},
            question={"title": "Test", "topics": ["Mathematics"]}
        )
    
    @pytest.fixture
    def valid_llm_response(self) -> str:
        """Valid LLM response JSON."""
        return json.dumps({
            "score": 0.85,
            "feedback": "Good understanding of the power rule.",
            "confidence": 0.9
        })
    
    @pytest.mark.asyncio
    async def test_full_task_processing(self, sample_context, valid_llm_response):
        """Test processing task through full pipeline with mocked stages."""
        from pipeline.orchestrator import Orchestrator
        from pipeline.context_fetch_stage import ContextFetchStage
        from pipeline.prompt_build_stage import PromptBuildStage
        from pipeline.llm_grade_stage import LLMGradeStage
        from pipeline.validate_stage import ValidateStage
        from pipeline.persist_stage import PersistStage
        
        # Setup mocks
        mock_store = AsyncMock()
        mock_store.store_result = AsyncMock(return_value=True)
        
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        
        # Create orchestrator with mocked stages
        stages = [
            ContextFetchStage(provider=mock_provider),
            PromptBuildStage(),
            LLMGradeStage(mock_response=valid_llm_response),
            ValidateStage(),
            PersistStage(store=mock_store),
        ]
        orchestrator = Orchestrator(stages=stages)
        
        # Create worker
        worker = GradingWorker(orchestrator=orchestrator)
        
        # Use dict, not JSON string
        task = {
            "session_id": "test_sess",
            "transcription_text": "The derivative is 2x",
            "screenshot_key": "test.png"
        }
        
        with patch('services.grading_worker.result_store') as result_mock:
            result_mock.set_status = AsyncMock(return_value=True)
            
            result = await worker._process_task(task, "test-worker")
            
            assert result is True
            # Verify store was called (persist stage)
            mock_store.store_result.assert_called_once()

