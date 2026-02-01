"""
Tests for Result Store Service.

Note: These tests require a running Redis instance.
Tests will skip if Redis is not available.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone


async def ensure_redis_connected():
    """Ensure Redis is connected in the current event loop"""
    from services.redis_client import get_redis_client, close_redis
    
    client = get_redis_client()
    
    # Always reconnect to ensure we're on the current event loop
    if client.is_connected:
        try:
            if await client.health_check():
                return True
        except Exception:
            pass
        await close_redis()
        client = get_redis_client()
    
    try:
        await client.connect()
        return True
    except Exception:
        return False


from schemas.grading_result import GradingResult, ScoreBreakdown, ModelInfo
from schemas.summary_result import SummaryResult, DimensionScore
from typing import List

@pytest_asyncio.fixture
async def result_store_fixture():
    """Fixture that provides a result store with Redis"""
    if not await ensure_redis_connected():
        pytest.skip("Redis is not available")
    
    from services.result_store import result_store
    yield result_store


@pytest_asyncio.fixture
async def cleanup_session():
    """Fixture to clean up session data after tests"""
    session_ids = []
    yield session_ids
    
    from services.result_store import result_store
    for session_id in session_ids:
        await result_store.delete_result(session_id)


@pytest.mark.asyncio
async def test_set_and_get_status(result_store_fixture, cleanup_session):
    """Test setting and getting status."""
    session_id = "test_sess_123"
    cleanup_session.append(session_id)
    
    # Set status
    success = await result_store_fixture.set_status(session_id, "processing", "Starting LLM call")
    assert success is True
    
    # Get status
    status = await result_store_fixture.get_status(session_id)
    assert status is not None
    assert status["status"] == "processing"
    assert status["message"] == "Starting LLM call"


@pytest.mark.asyncio
async def test_store_and_get_result(result_store_fixture, cleanup_session):
    """Test storing and retrieving results."""
    session_id = "test_sess_456"
    cleanup_session.append(session_id)
    
    result = GradingResult(
        session_id=session_id,
        score=0.85,
        feedback="Good work!",
        score_breakdown=[
            ScoreBreakdown(dimension="Understanding", percentage=0.85, feedback="Good grasp")
        ],
        model_info=ModelInfo(
            provider="openai",
            model="gpt-4o-mini"
        ),
        completed_at=datetime.now(timezone.utc)
    )
    
    # Store result
    success = await result_store_fixture.store_result(result)
    assert success is True
    
    # Get result
    retrieved = await result_store_fixture.get_result(session_id)
    assert retrieved is not None
    assert isinstance(retrieved, GradingResult)
    assert retrieved.score == 0.85
    assert retrieved.feedback == "Good work!"
    # JSON fields should be deserialized objects
    assert isinstance(retrieved.score_breakdown, list)
    assert retrieved.score_breakdown[0].dimension == "Understanding"
    assert isinstance(retrieved.model_info, ModelInfo)
    assert retrieved.model_info.provider == "openai"


@pytest.mark.asyncio
async def test_store_result_sets_completed_status(result_store_fixture, cleanup_session):
    """Test that storing result also sets status to completed."""
    session_id = "test_sess_789"
    cleanup_session.append(session_id)
    
    result = {
        "session_id": session_id,
        "score": 0.75,
        "feedback": "Test feedback"
    }
    
    # Passing dict should also work (auto-converted to Model inside store_result)
    await result_store_fixture.store_result(result)
    
    # Status should be completed
    status = await result_store_fixture.get_status(session_id)
    assert status is not None
    assert status["status"] == "completed"


@pytest.mark.asyncio
async def test_get_nonexistent_result(result_store_fixture):
    """Test getting a result that doesn't exist."""
    result = await result_store_fixture.get_result("nonexistent_session")
    assert result is None


@pytest.mark.asyncio
async def test_delete_result(result_store_fixture, cleanup_session):
    """Test deleting a result."""
    session_id = "test_sess_delete"
    # Don't add to cleanup since we're testing delete
    
    result = {
        "session_id": session_id,
        "score": 0.5,
        "feedback": "Test"
    }
    
    await result_store_fixture.store_result(result)
    
    # Verify it exists
    retrieved = await result_store_fixture.get_result(session_id)
    assert retrieved is not None
    
    # Delete
    success = await result_store_fixture.delete_result(session_id)
    assert success is True
    
    # Verify deleted
    retrieved = await result_store_fixture.get_result(session_id)
    assert retrieved is None


# ==================== Summary Result Tests ====================

@pytest_asyncio.fixture
async def cleanup_summary():
    """Fixture to clean up summary data after tests"""
    summary_ids = []
    yield summary_ids
    
    from services.redis_client import get_redis_client
    client = get_redis_client().get_client()
    for summary_id in summary_ids:
        await client.delete(f"summary:result:{summary_id}")
        await client.delete(f"summary:status:{summary_id}")


@pytest.mark.asyncio
async def test_set_and_get_summary_status(result_store_fixture, cleanup_summary):
    """Test setting and getting summary status."""
    summary_id = "test_summ_status"
    cleanup_summary.append(summary_id)
    
    # Set status
    success = await result_store_fixture.set_summary_status(
        summary_id, "processing", "Fetching session results"
    )
    assert success is True
    
    # Get status
    status = await result_store_fixture.get_summary_status(summary_id)
    assert status is not None
    assert status["status"] == "processing"
    assert status["message"] == "Fetching session results"


@pytest.mark.asyncio
async def test_store_and_get_summary_result(result_store_fixture, cleanup_summary):
    """Test storing and retrieving summary results."""
    summary_id = "test_summ_result"
    cleanup_summary.append(summary_id)
    
    from schemas.summary_result import ModelInfo as SummaryModelInfo

    result = SummaryResult(
        summary_id=summary_id,
        session_ids=["sess_1", "sess_2"],
        dimension_scores=[
            DimensionScore(dimension="Correctness", score=0.8, feedback="Good")
        ],
        analytics_summary=["Overall score: 75/100"],
        overall_feedback="Good performance",
        key_strengths=["Strong understanding"],
        areas_for_improvement=["Time management"],
        model_info=SummaryModelInfo(
            provider="gemini",
            model="gemini-1.5-flash"
        ),
        completed_at=datetime.now(timezone.utc)
    )
    
    # Store result
    success = await result_store_fixture.store_summary_result(result)
    assert success is True
    
    # Get result
    retrieved = await result_store_fixture.get_summary_result(summary_id)
    assert retrieved is not None
    assert isinstance(retrieved, SummaryResult)
    # JSON fields should be deserialized
    assert isinstance(retrieved.dimension_scores, list)
    assert retrieved.dimension_scores[0].dimension == "Correctness"
    assert isinstance(retrieved.session_ids, list)
    assert isinstance(retrieved.key_strengths, list)


@pytest.mark.asyncio
async def test_store_summary_sets_completed_status(result_store_fixture, cleanup_summary):
    """Test that storing summary result also sets status to completed."""
    summary_id = "test_summ_status_auto"
    cleanup_summary.append(summary_id)
    
    result = {
        "summary_id": summary_id,
        "session_ids": ["sess_1"],
        "dimension_scores": [],
        "analytics_summary": [],
        "overall_feedback": "Test",
        "key_strengths": [],
        "areas_for_improvement": []
    }
    
    # Passing dict should also work
    await result_store_fixture.store_summary_result(result)
    
    # Status should be completed
    status = await result_store_fixture.get_summary_status(summary_id)
    assert status is not None
    assert status["status"] == "completed"


@pytest.mark.asyncio
async def test_get_nonexistent_summary_result(result_store_fixture):
    """Test getting a summary result that doesn't exist."""
    result = await result_store_fixture.get_summary_result("nonexistent_summary")
    assert result is None


@pytest.mark.asyncio
async def test_get_nonexistent_summary_status(result_store_fixture):
    """Test getting summary status that doesn't exist."""
    status = await result_store_fixture.get_summary_status("nonexistent_summary")
    assert status is None

