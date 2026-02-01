"""
Tests for Summary Queue Service.

Uses mocked Redis to avoid requiring a running instance.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from services.summary_queue import SummaryQueue, SUMMARY_QUEUE_KEY, SUMMARY_DLQ_KEY


class TestSummaryQueue:
    """Tests for SummaryQueue."""
    
    @pytest.fixture
    def sample_task(self) -> dict:
        """Sample summary task dict."""
        return {
            "summary_id": "summ_test_123",
            "question_id": "q_1",
            "session_ids": ["sess_1", "sess_2"]
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
        queue = SummaryQueue()
        
        with patch('services.summary_queue.get_redis_client') as mock_redis:
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
        queue = SummaryQueue()
        task_json = json.dumps(sample_task)
        mock_redis_client.brpop = AsyncMock(return_value=(SUMMARY_QUEUE_KEY, task_json))
        
        with patch('services.summary_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.dequeue()
            
            assert result is not None
            assert result["summary_id"] == "summ_test_123"
    
    @pytest.mark.asyncio
    async def test_dequeue_returns_none_on_timeout(self, mock_redis_client):
        """Test dequeue returns None on timeout."""
        queue = SummaryQueue()
        mock_redis_client.brpop = AsyncMock(return_value=None)
        
        with patch('services.summary_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.dequeue(timeout=1)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_requeue_with_backoff_increments_retry_count(self, sample_task, mock_redis_client):
        """Test requeue increments retry count."""
        queue = SummaryQueue()
        sample_task["retry_count"] = 0
        sample_task["max_retries"] = 3
        
        with patch('services.summary_queue.get_redis_client') as mock_redis:
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
    async def test_move_to_dlq(self, sample_task, mock_redis_client):
        """Test moving task to dead-letter queue."""
        queue = SummaryQueue()
        
        with patch('services.summary_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            result = await queue.move_to_dlq(
                sample_task, 
                "Test error",
                "Detailed error info"
            )
            
            assert result is True
            
            # Check DLQ entry structure
            call_args = mock_redis_client.lpush.call_args
            assert call_args[0][0] == SUMMARY_DLQ_KEY
            dlq_json = call_args[0][1]
            dlq_entry = json.loads(dlq_json)
            
            assert dlq_entry["error_reason"] == "Test error"
            assert dlq_entry["error_details"] == "Detailed error info"
            assert "failed_at" in dlq_entry
            assert "original_task" in dlq_entry
    
    @pytest.mark.asyncio
    async def test_get_queue_length(self, mock_redis_client):
        """Test getting queue length."""
        queue = SummaryQueue()
        mock_redis_client.llen = AsyncMock(return_value=5)
        
        with patch('services.summary_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            length = await queue.get_queue_length()
            
            assert length == 5
            mock_redis_client.llen.assert_called_with(SUMMARY_QUEUE_KEY)
    
    @pytest.mark.asyncio
    async def test_get_dlq_length(self, mock_redis_client):
        """Test getting DLQ length."""
        queue = SummaryQueue()
        mock_redis_client.llen = AsyncMock(return_value=3)
        
        with patch('services.summary_queue.get_redis_client') as mock_redis:
            mock_redis.return_value.get_client.return_value = mock_redis_client
            
            length = await queue.get_dlq_length()
            
            assert length == 3
            mock_redis_client.llen.assert_called_with(SUMMARY_DLQ_KEY)
