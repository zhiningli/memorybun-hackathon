"""
Tests for Redis Grading Queue Service

Uses mock Redis from conftest.py for isolated testing.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from services.redis_grading_queue import RedisGradingQueue
from schemas.grading import GradingTask


@pytest_asyncio.fixture
async def queue():
    """Fixture that provides a clean grading queue instance"""
    # Create new instance to ensure clean state for each test
    q = RedisGradingQueue()
    await q.clear_queue()
    yield q
    await q.clear_queue()


@pytest.mark.asyncio
async def test_enqueue_grading_task(queue):
    """Test enqueueing a grading task"""
    task = GradingTask(
        session_id="sess_test123",
        transcription_text="Test transcription",
        screenshot_key="test.png"
    )
    
    result = await queue.enqueue_grading_task(task)
    assert result is True
    
    # Verify queue length
    length = await queue.get_queue_length()
    assert length == 1


@pytest.mark.asyncio
async def test_dequeue_grading_task(queue):
    """Test dequeueing a grading task"""
    # Enqueue a task
    task = GradingTask(
        session_id="sess_test123",
        transcription_text="Test transcription",
        screenshot_key="test.png"
    )
    await queue.enqueue_grading_task(task)
    
    # Dequeue
    dequeued = await queue.dequeue_grading_task(timeout=1)
    
    assert dequeued is not None
    assert dequeued.session_id == "sess_test123"
    assert dequeued.transcription_text == "Test transcription"
    assert dequeued.screenshot_key == "test.png"
    
    # Queue should be empty now
    length = await queue.get_queue_length()
    assert length == 0


@pytest.mark.asyncio
async def test_dequeue_timeout(queue):
    """Test dequeue timeout when queue is empty"""
    # Try to dequeue from empty queue with short timeout
    result = await queue.dequeue_grading_task(timeout=1)
    assert result is None


@pytest.mark.asyncio
async def test_get_queue_length(queue):
    """Test getting queue length"""
    # Initially empty
    length = await queue.get_queue_length()
    assert length == 0
    
    # Add tasks
    for i in range(3):
        task = GradingTask(
            session_id=f"sess_test{i}",
            transcription_text=f"Text {i}",
            screenshot_key=f"test{i}.png"
        )
        await queue.enqueue_grading_task(task)
    
    length = await queue.get_queue_length()
    assert length == 3


@pytest.mark.asyncio
async def test_peek_queue(queue):
    """Test peeking at queue without removing"""
    # Enqueue a task
    task = GradingTask(
        session_id="sess_test123",
        transcription_text="Test transcription",
        screenshot_key="test.png"
    )
    await queue.enqueue_grading_task(task)
    
    # Peek
    peeked = await queue.peek_queue()
    assert peeked is not None
    assert peeked.session_id == "sess_test123"
    
    # Queue should still have the task
    length = await queue.get_queue_length()
    assert length == 1


@pytest.mark.asyncio
async def test_fifo_order(queue):
    """Test that queue maintains FIFO order"""
    # Enqueue multiple tasks
    tasks = []
    for i in range(3):
        task = GradingTask(
            session_id=f"sess_test{i}",
            transcription_text=f"Text {i}",
            screenshot_key=f"test{i}.png"
        )
        tasks.append(task)
        await queue.enqueue_grading_task(task)
    
    # Dequeue and verify order
    for i, expected_task in enumerate(tasks):
        dequeued = await queue.dequeue_grading_task(timeout=1)
        assert dequeued is not None
        assert dequeued.session_id == expected_task.session_id


@pytest.mark.asyncio
async def test_clear_queue(queue):
    """Test clearing the queue"""
    # Add some tasks
    for i in range(3):
        task = GradingTask(
            session_id=f"sess_test{i}",
            transcription_text=f"Text {i}",
            screenshot_key=f"test{i}.png"
        )
        await queue.enqueue_grading_task(task)
    
    # Clear
    removed = await queue.clear_queue()
    assert removed == 3
    
    # Verify empty
    length = await queue.get_queue_length()
    assert length == 0
