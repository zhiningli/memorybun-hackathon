"""
Tests for Grading Publisher Service

Uses mock Redis from conftest.py for isolated testing.
"""

import pytest
import pytest_asyncio
from services.grading_publisher import GradingPublisher
from services.redis_grading_queue import RedisGradingQueue
from schemas.grading import (
    GradingReadinessStatus,
    TranscriptionStatus,
    ScreenshotStatus
)


@pytest_asyncio.fixture
async def queue():
    """Fixture that provides a clean grading queue"""
    q = RedisGradingQueue()
    await q.clear_queue()
    yield q
    await q.clear_queue()


@pytest_asyncio.fixture
async def publisher(queue):
    """Fixture that provides a grading publisher"""
    pub = GradingPublisher()
    yield pub


@pytest_asyncio.fixture
async def cleanup_session():
    """Fixture to clean up session state after tests"""
    session_ids = []
    yield session_ids
    # Clean up
    pub = GradingPublisher()
    for session_id in session_ids:
        await pub.delete_session_state(session_id)


@pytest.mark.asyncio
async def test_publish_transcription_ready(publisher, cleanup_session):
    """Test publishing transcription ready"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Publish transcription (screenshot not ready yet)
    result = await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    
    # Should not publish yet (screenshot not ready)
    assert result is False
    
    # Check session state
    state = await publisher.get_session_state(session_id)
    assert state is not None
    assert state.get("transcription_status") == TranscriptionStatus.COMPLETED.value
    assert state.get("transcription_text") == "Test transcription"
    assert state.get("grading_readiness_status") == GradingReadinessStatus.WAITING_FOR_SCREENSHOT.value


@pytest.mark.asyncio
async def test_publish_screenshot_ready(publisher, cleanup_session):
    """Test publishing screenshot ready"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Publish screenshot (transcription not ready yet)
    result = await publisher.publish_screenshot_ready(
        session_id=session_id,
        screenshot_key="test.png"
    )
    
    # Should not publish yet (transcription not ready)
    assert result is False
    
    # Check session state
    state = await publisher.get_session_state(session_id)
    assert state is not None
    assert state.get("screenshot_status") == ScreenshotStatus.COMPLETED.value
    assert state.get("screenshot_key") == "test.png"
    assert state.get("grading_readiness_status") == GradingReadinessStatus.WAITING_FOR_AUDIO.value


@pytest.mark.asyncio
async def test_publish_when_both_ready(publisher, cleanup_session, queue):
    """Test publishing when both transcription and screenshot are ready"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Publish transcription first
    result1 = await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    assert result1 is False  # Screenshot not ready yet
    
    # Publish screenshot - should trigger grading task
    result2 = await publisher.publish_screenshot_ready(
        session_id=session_id,
        screenshot_key="test.png"
    )
    assert result2 is True  # Both ready, should publish
    
    # Verify task in queue
    queue_length = await queue.get_queue_length()
    assert queue_length == 1
    
    # Verify session state shows enqueued
    state = await publisher.get_session_state(session_id)
    assert state.get("grading_readiness_status") == GradingReadinessStatus.ENQUEUED.value
    assert state.get("grading_published") == "true"
    
    # Dequeue and verify
    task = await queue.dequeue_grading_task(timeout=1)
    assert task is not None
    assert task.session_id == session_id
    assert task.transcription_text == "Test transcription"
    assert task.screenshot_key == "test.png"


@pytest.mark.asyncio
async def test_publish_idempotent(publisher, cleanup_session, queue):
    """Test that publishing is idempotent (won't create duplicate tasks)"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Publish both
    await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    await publisher.publish_screenshot_ready(
        session_id=session_id,
        screenshot_key="test.png"
    )
    
    # Try to publish again (should not create duplicate)
    result = await publisher.check_and_publish_if_ready(session_id)
    assert result is False  # Already published
    
    # Should only have one task in queue
    queue_length = await queue.get_queue_length()
    assert queue_length == 1


@pytest.mark.asyncio
async def test_check_and_publish_if_ready(publisher, cleanup_session):
    """Test check_and_publish_if_ready method"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Not ready yet
    result = await publisher.check_and_publish_if_ready(session_id)
    assert result is False
    
    # Add transcription
    await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    
    # Still not ready (screenshot missing)
    result = await publisher.check_and_publish_if_ready(session_id)
    assert result is False
    
    # Add screenshot
    await publisher.publish_screenshot_ready(
        session_id=session_id,
        screenshot_key="test.png"
    )
    
    # Should be ready now
    result = await publisher.check_and_publish_if_ready(session_id)
    assert result is False  # Already published by publish_screenshot_ready


@pytest.mark.asyncio
async def test_get_session_state(publisher, cleanup_session):
    """Test getting session state"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # No state yet
    state = await publisher.get_session_state(session_id)
    assert state is None or len(state) == 0
    
    # Add transcription
    await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    
    # Should have state now
    state = await publisher.get_session_state(session_id)
    assert state is not None
    assert "transcription_status" in state
    assert "transcription_text" in state


@pytest.mark.asyncio
async def test_delete_session_state(publisher, cleanup_session):
    """Test deleting session state"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Add some state
    await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    
    # Verify it exists
    state = await publisher.get_session_state(session_id)
    assert state is not None
    
    # Delete
    result = await publisher.delete_session_state(session_id)
    assert result is True
    
    # Verify deleted
    state = await publisher.get_session_state(session_id)
    assert state is None or len(state) == 0


@pytest.mark.asyncio
async def test_get_readiness_status(publisher, cleanup_session):
    """Test getting readiness status as enum"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # No state yet
    status = await publisher.get_readiness_status(session_id)
    assert status is None
    
    # Add transcription
    await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    
    # Should return waiting_for_screenshot
    status = await publisher.get_readiness_status(session_id)
    assert status == GradingReadinessStatus.WAITING_FOR_SCREENSHOT
    
    # Add screenshot
    await publisher.publish_screenshot_ready(
        session_id=session_id,
        screenshot_key="test.png"
    )
    
    # Should return enqueued
    status = await publisher.get_readiness_status(session_id)
    assert status == GradingReadinessStatus.ENQUEUED


@pytest.mark.asyncio
async def test_readiness_status_transitions(publisher, cleanup_session, queue):
    """Test readiness status transitions through all states"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Scenario A: Transcription arrives first
    await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    status = await publisher.get_readiness_status(session_id)
    assert status == GradingReadinessStatus.WAITING_FOR_SCREENSHOT
    
    # Add screenshot - should transition to enqueued
    await publisher.publish_screenshot_ready(
        session_id=session_id,
        screenshot_key="test.png"
    )
    status = await publisher.get_readiness_status(session_id)
    assert status == GradingReadinessStatus.ENQUEUED
    
    # Clean up for next scenario
    await publisher.delete_session_state(session_id)
    await queue.clear_queue()
    
    # Scenario B: Screenshot arrives first
    session_id2 = "sess_test456"
    cleanup_session.append(session_id2)
    
    await publisher.publish_screenshot_ready(
        session_id=session_id2,
        screenshot_key="test2.png"
    )
    status = await publisher.get_readiness_status(session_id2)
    assert status == GradingReadinessStatus.WAITING_FOR_AUDIO
    
    # Add transcription - should transition to enqueued
    await publisher.publish_transcription_ready(
        session_id=session_id2,
        transcription_text="Test transcription 2"
    )
    status = await publisher.get_readiness_status(session_id2)
    assert status == GradingReadinessStatus.ENQUEUED


@pytest.mark.asyncio
async def test_status_enum_values_in_redis(publisher, cleanup_session):
    """Test that enum values are correctly stored and retrieved from Redis"""
    session_id = "sess_test123"
    cleanup_session.append(session_id)
    
    # Publish transcription
    await publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription"
    )
    
    # Verify enum values are stored as strings in Redis
    state = await publisher.get_session_state(session_id)
    assert state.get("transcription_status") == TranscriptionStatus.COMPLETED.value
    assert state.get("grading_readiness_status") == GradingReadinessStatus.WAITING_FOR_SCREENSHOT.value
    
    # Verify we can parse back to enum
    status = await publisher.get_readiness_status(session_id)
    assert isinstance(status, GradingReadinessStatus)
    assert status == GradingReadinessStatus.WAITING_FOR_SCREENSHOT
