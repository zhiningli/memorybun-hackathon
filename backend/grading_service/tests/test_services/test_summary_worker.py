"""
Tests for SummaryWorker.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.summary_worker import SummaryWorker


class TestSummaryWorker:
    """Tests for SummaryWorker."""
    
    @pytest.fixture
    def sample_task(self) -> dict:
        """Sample summary task dict."""
        return {
            "summary_id": "summ_test_123",
            "session_ids": ["sess_1", "sess_2", "sess_3"],
            "retry_count": 0,
            "max_retries": 3
        }
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Mock orchestrator that returns completed state."""
        orchestrator = AsyncMock()
        mock_state = MagicMock()
        mock_state.result = {"overall_score": 75, "overall_feedback": "Good"}
        mock_state.stage = "completed"
        orchestrator.run_pipeline = AsyncMock(return_value=mock_state)
        return orchestrator
    
    def test_init_default_workers(self):
        """Test default worker count."""
        worker = SummaryWorker()
        assert worker.num_workers == 1  # Summary uses 1 worker by default
        assert not worker.is_running
    
    def test_init_custom_workers(self):
        """Test custom worker count."""
        worker = SummaryWorker(num_workers=2)
        assert worker.num_workers == 2
    
    @pytest.mark.asyncio
    async def test_start_creates_workers(self, mock_orchestrator):
        """Test that start() creates worker tasks."""
        worker = SummaryWorker(num_workers=1, orchestrator=mock_orchestrator)
        
        with patch('services.summary_worker.summary_queue') as mock_queue:
            mock_queue.dequeue = AsyncMock(return_value=None)
            
            await worker.start()
            
            assert worker.is_running
            assert len(worker._workers) == 1
            
            await worker.stop()
    
    @pytest.mark.asyncio
    async def test_start_idempotent(self, mock_orchestrator):
        """Test that starting twice doesn't create duplicate workers."""
        worker = SummaryWorker(num_workers=1, orchestrator=mock_orchestrator)
        
        with patch('services.summary_worker.summary_queue') as mock_queue:
            mock_queue.dequeue = AsyncMock(return_value=None)
            
            await worker.start()
            await worker.start()  # Second call should be no-op
            
            assert len(worker._workers) == 1
            
            await worker.stop()
    
    @pytest.mark.asyncio
    async def test_stop_clears_workers(self, mock_orchestrator):
        """Test that stop() clears worker tasks."""
        worker = SummaryWorker(num_workers=1, orchestrator=mock_orchestrator)
        
        with patch('services.summary_worker.summary_queue') as mock_queue:
            mock_queue.dequeue = AsyncMock(return_value=None)
            
            await worker.start()
            await worker.stop()
            
            assert not worker.is_running
            assert len(worker._workers) == 0
    
    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, mock_orchestrator):
        """Test that stop() is safe when not running."""
        worker = SummaryWorker(orchestrator=mock_orchestrator)
        
        # Should not raise
        await worker.stop()
        assert not worker.is_running
    
    @pytest.mark.asyncio
    async def test_process_task_runs_orchestrator(self, sample_task, mock_orchestrator):
        """Test that _process_task calls orchestrator."""
        worker = SummaryWorker(orchestrator=mock_orchestrator)
        
        with patch('services.summary_worker.result_store') as mock_store:
            mock_store.set_summary_status = AsyncMock(return_value=True)
            
            result = await worker._process_task(sample_task, "test-worker")
            
            assert result is True
            mock_orchestrator.run_pipeline.assert_called_once_with(sample_task)
    
    @pytest.mark.asyncio
    async def test_process_task_handles_failure(self, sample_task, mock_orchestrator):
        """Test that _process_task returns False on failure."""
        mock_orchestrator.run_pipeline = AsyncMock(side_effect=Exception("LLM error"))
        worker = SummaryWorker(orchestrator=mock_orchestrator)
        
        with patch('services.summary_worker.result_store') as mock_store:
            mock_store.set_summary_status = AsyncMock(return_value=True)
            
            result = await worker._process_task(sample_task, "test-worker")
            
            assert result is False
            assert "last_error" in sample_task
    
    @pytest.mark.asyncio
    async def test_update_failure_status(self, mock_orchestrator):
        """Test that _update_failure_status updates status."""
        worker = SummaryWorker(orchestrator=mock_orchestrator)
        
        with patch('services.summary_worker.result_store') as mock_store:
            mock_store.set_summary_status = AsyncMock(return_value=True)
            
            await worker._update_failure_status("summ_test", "Test error message")
            
            mock_store.set_summary_status.assert_called_once_with(
                summary_id="summ_test",
                status="failed",
                message="Test error message"
            )
    
    @pytest.mark.asyncio
    async def test_handle_retry_requeues_on_failure(self, sample_task, mock_orchestrator):
        """Test that _handle_retry requeues task with backoff."""
        worker = SummaryWorker(orchestrator=mock_orchestrator)
        sample_task["retry_count"] = 0
        
        with patch('services.summary_worker.summary_queue') as mock_queue, \
             patch('services.summary_worker.result_store') as mock_store:
            mock_queue.requeue_with_backoff = AsyncMock(return_value=True)
            mock_store.set_summary_status = AsyncMock(return_value=True)
            
            await worker._handle_retry(sample_task, "test-worker")
            
            mock_queue.requeue_with_backoff.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_retry_moves_to_dlq_after_max(self, sample_task, mock_orchestrator):
        """Test that _handle_retry moves to DLQ after max retries."""
        worker = SummaryWorker(orchestrator=mock_orchestrator)
        sample_task["retry_count"] = 3
        sample_task["max_retries"] = 3
        
        with patch('services.summary_worker.summary_queue') as mock_queue, \
             patch('services.summary_worker.result_store') as mock_store:
            mock_queue.move_to_dlq = AsyncMock(return_value=True)
            mock_store.set_summary_status = AsyncMock(return_value=True)
            
            await worker._handle_retry(sample_task, "test-worker")
            
            mock_queue.move_to_dlq.assert_called_once()
    
    def test_is_running_property(self, mock_orchestrator):
        """Test is_running property."""
        worker = SummaryWorker(orchestrator=mock_orchestrator)
        
        assert not worker.is_running
        
        worker._running = True
        assert worker.is_running
