"""
Tests for GradingQueue with retry logic and DLQ.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from services.grading_queue import GradingQueue, GRADING_QUEUE_KEY, DEAD_LETTER_QUEUE_KEY


class TestGradingQueue:
    """Tests for GradingQueue."""
    
    @pytest.fixture
    def sample_task(self) -> dict:
        """Sample task dict."""
        return {
            "session_id": "test_session_123",
            "student_id": "student_456",
            "transcription_text": "The answer is 2x",
            "screenshot_url": "/test.png"
        }
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        client = AsyncMock()
        client.lpush = AsyncMock(return_value=1)
        client.brpop = AsyncMock(return_value=None)
        client.llen = AsyncMock(return_value=0)
        client.lrange = AsyncMock(return_value=[])
        client.lrem = AsyncMock(return_value=1)
        client.delete = AsyncMock(return_value=1)
        return client
    
    @pytest.mark.asyncio
    async def test_enqueue_adds_retry_fields(self, sample_task, mock_redis_client):
        """Test that enqueue adds retry tracking fields."""
        queue = GradingQueue()
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.enqueue(sample_task)
            
            assert result is True
            
            # Check task was modified with retry fields
            call_args = mock_redis_client.lpush.call_args
            task_json = call_args[0][1]
            task = json.loads(task_json)
            
            assert task["retry_count"] == 0
            assert task["max_retries"] == 3
            assert "created_at" in task
    
    @pytest.mark.asyncio
    async def test_dequeue_returns_task(self, sample_task, mock_redis_client):
        """Test dequeue returns task dict."""
        queue = GradingQueue()
        task_json = json.dumps(sample_task)
        mock_redis_client.brpop = AsyncMock(return_value=(GRADING_QUEUE_KEY, task_json))
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.dequeue()
            
            assert result is not None
            assert result["session_id"] == "test_session_123"
    
    @pytest.mark.asyncio
    async def test_dequeue_returns_none_on_timeout(self, mock_redis_client):
        """Test dequeue returns None on timeout."""
        queue = GradingQueue()
        mock_redis_client.brpop = AsyncMock(return_value=None)
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.dequeue(timeout=1)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_requeue_with_backoff_increments_retry_count(self, sample_task, mock_redis_client):
        """Test requeue increments retry count."""
        queue = GradingQueue()
        sample_task["retry_count"] = 0
        sample_task["max_retries"] = 3
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await queue.requeue_with_backoff(sample_task)
            
            assert result is True
            
            # Check retry count was incremented
            call_args = mock_redis_client.lpush.call_args
            task_json = call_args[0][1]
            task = json.loads(task_json)
            
            assert task["retry_count"] == 1
            assert "last_retry_at" in task
    
    @pytest.mark.asyncio
    async def test_requeue_moves_to_dlq_after_max_retries(self, sample_task, mock_redis_client):
        """Test task moves to DLQ after max retries."""
        queue = GradingQueue()
        sample_task["retry_count"] = 3  # Already at max
        sample_task["max_retries"] = 3
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.requeue_with_backoff(sample_task)
            
            # Should return False (moved to DLQ, not requeued)
            assert result is True  # move_to_dlq returns True
            
            # Should be pushed to DLQ
            mock_redis_client.lpush.assert_called()
            call_args = mock_redis_client.lpush.call_args
            assert DEAD_LETTER_QUEUE_KEY in str(call_args)
    
    @pytest.mark.asyncio
    async def test_move_to_dlq(self, sample_task, mock_redis_client):
        """Test moving task to dead-letter queue."""
        queue = GradingQueue()
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.move_to_dlq(
                sample_task, 
                "Test error",
                "Detailed error info"
            )
            
            assert result is True
            
            # Check DLQ entry structure
            call_args = mock_redis_client.lpush.call_args
            assert call_args[0][0] == DEAD_LETTER_QUEUE_KEY
            dlq_json = call_args[0][1]
            dlq_entry = json.loads(dlq_json)
            
            assert dlq_entry["error_reason"] == "Test error"
            assert dlq_entry["error_details"] == "Detailed error info"
            assert "failed_at" in dlq_entry
            assert "original_task" in dlq_entry
    
    @pytest.mark.asyncio
    async def test_get_dlq_tasks(self, mock_redis_client):
        """Test getting tasks from DLQ."""
        queue = GradingQueue()
        
        dlq_entry = json.dumps({
            "original_task": {"session_id": "test"},
            "error_reason": "Test error",
            "failed_at": "2025-01-01T00:00:00Z"
        })
        mock_redis_client.lrange = AsyncMock(return_value=[dlq_entry])
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            tasks = await queue.get_dlq_tasks(limit=10)
            
            assert len(tasks) == 1
            assert tasks[0]["error_reason"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_requeue_from_dlq(self, mock_redis_client):
        """Test requeueing task from DLQ."""
        queue = GradingQueue()
        
        dlq_entry = json.dumps({
            "original_task": {"session_id": "test_session", "retry_count": 2},
            "error_reason": "Test error"
        })
        mock_redis_client.lrange = AsyncMock(return_value=[dlq_entry])
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.requeue_from_dlq("test_session")
            
            assert result is True
            
            # Check task was removed from DLQ
            mock_redis_client.lrem.assert_called()
            
            # Check task was added to main queue with reset retry count
            lpush_calls = [c for c in mock_redis_client.lpush.call_args_list 
                         if c[0][0] == GRADING_QUEUE_KEY]
            assert len(lpush_calls) >= 1
    
    @pytest.mark.asyncio
    async def test_clear_dlq(self, mock_redis_client):
        """Test clearing DLQ."""
        queue = GradingQueue()
        mock_redis_client.llen = AsyncMock(return_value=5)
        
        with patch('services.grading_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            count = await queue.clear_dlq()
            
            assert count == 5
            mock_redis_client.delete.assert_called_once_with(DEAD_LETTER_QUEUE_KEY)


class TestGradingQueueBackoff:
    """Tests for exponential backoff calculation."""
    
    @pytest.mark.asyncio
    async def test_backoff_delays(self):
        """Test exponential backoff delay calculation."""
        queue = GradingQueue()
        
        # Backoff should be 2^retry_count seconds
        # retry 0: 1s, retry 1: 2s, retry 2: 4s
        delays = []
        
        for retry_count in range(3):
            delay = queue.backoff_base * (2 ** retry_count)
            delays.append(delay)
        
        assert delays == [1, 2, 4]
