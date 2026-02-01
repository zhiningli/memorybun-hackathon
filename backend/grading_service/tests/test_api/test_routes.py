"""
Tests for Grading Service API Routes.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

# Import schemas for proper mock return values
from schemas.grading_result import GradingResult, ScoreBreakdown
from schemas.summary_result import SummaryResult, DimensionScore

# Import app after mocking
from main import app


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    client = AsyncMock()
    client.llen = AsyncMock(return_value=5)
    client.lindex = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_result_store():
    """Mock result store."""
    store = AsyncMock()
    store.get_status = AsyncMock(return_value=None)
    store.get_result = AsyncMock(return_value=None)
    return store


class TestGradingStatusEndpoint:
    """Tests for GET /api/v1/grading/session/{session_id}/status"""
    
    @pytest.mark.asyncio
    async def test_status_not_found(self):
        """Test status when session not found."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_status = AsyncMock(return_value=None)
            mock_store.get_result = AsyncMock(return_value=None)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/session/unknown_session/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_status_processing(self):
        """Test status when grading in progress."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_status = AsyncMock(return_value={
                "status": "processing",
                "message": "Grading in progress"
            })
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/session/test_session/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
            assert data["message"] == "Grading in progress"
    
    @pytest.mark.asyncio
    async def test_status_completed(self):
        """Test status when grading completed."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_status = AsyncMock(return_value={"status": "completed"})
            # Return a proper GradingResult model instance
            mock_result = GradingResult(
                session_id="test_session",
                score=0.85,
                feedback="Good work!",
                confidence=0.9,
                completed_at=datetime.now(timezone.utc)
            )
            mock_store.get_result = AsyncMock(return_value=mock_result)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/session/test_session/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["score"] == 0.85
            assert data["feedback"] == "Good work!"


class TestGradingResultEndpoint:
    """Tests for GET /api/v1/grading/session/{session_id}/result"""
    
    @pytest.mark.asyncio
    async def test_result_not_found(self):
        """Test result when not found."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_result = AsyncMock(return_value=None)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/session/unknown/result")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_result_found(self):
        """Test result when available."""
        with patch('api.routes.result_store') as mock_store:
            # Return a proper GradingResult model instance
            mock_result = GradingResult(
                session_id="test_session",
                score=0.85,
                feedback="Good work!",
                confidence=0.9,
                score_breakdown=[ScoreBreakdown(dimension="Understanding", percentage=0.85, feedback="Good grasp")],
                processing_time=1.5,
                completed_at=datetime.now(timezone.utc)
            )
            mock_store.get_result = AsyncMock(return_value=mock_result)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/session/test_session/result")
            
            assert response.status_code == 200
            data = response.json()
            assert data["score"] == 0.85
            assert data["feedback"] == "Good work!"
            assert len(data["score_breakdown"]) == 1


class TestQueueMetricsEndpoint:
    """Tests for GET /api/v1/queue/metrics"""
    
    @pytest.mark.asyncio
    async def test_metrics_success(self):
        """Test queue metrics endpoint."""
        with patch('api.routes.get_redis_client') as mock_redis, \
             patch('api.routes.grading_worker') as mock_worker:
            
            mock_client = AsyncMock()
            mock_client.llen = AsyncMock(return_value=10)
            mock_redis.return_value.get_client.return_value = mock_client
            mock_worker.is_running = True
            mock_worker.num_workers = 2
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/queue/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["queue_length"] == 10
            assert data["worker_status"] == "running"
            assert data["worker_count"] == 2


class TestDebugGradeEndpoint:
    """Tests for POST /api/v1/debug/grade"""
    
    @pytest.mark.asyncio
    async def test_debug_grade_success(self):
        """Test debug grade endpoint success."""
        mock_state = MagicMock()
        mock_state.result = {"score": 0.85, "feedback": "Good!"}
        
        with patch('api.routes.Orchestrator') as MockOrchestrator:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_pipeline = AsyncMock(return_value=mock_state)
            MockOrchestrator.return_value = mock_orchestrator
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/debug/grade", json={
                    "session_id": "test_session",
                    "transcription_text": "The answer is 2x",
                    "screenshot_key": "test.png"
                })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["result"]["score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_debug_grade_failure(self):
        """Test debug grade endpoint when grading fails."""
        with patch('api.routes.Orchestrator') as MockOrchestrator:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_pipeline = AsyncMock(side_effect=Exception("LLM error"))
            MockOrchestrator.return_value = mock_orchestrator
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/debug/grade", json={
                    "session_id": "test_session",
                    "transcription_text": "The answer",
                    "screenshot_key": "test.png"
                })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert "LLM error" in data["message"]


class TestDebugQueueStatusEndpoint:
    """Tests for GET /api/v1/debug/queue-status"""
    
    @pytest.mark.asyncio
    async def test_queue_status_empty(self):
        """Test queue status when empty."""
        with patch('api.routes.get_redis_client') as mock_redis, \
             patch('api.routes.grading_worker') as mock_worker:
            
            mock_client = AsyncMock()
            mock_client.llen = AsyncMock(return_value=0)
            mock_client.lindex = AsyncMock(return_value=None)
            mock_redis.return_value.get_client.return_value = mock_client
            mock_worker.is_running = True
            mock_worker.num_workers = 2
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/debug/queue-status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["queue_length"] == 0
            assert data["next_task"] is None
    
    @pytest.mark.asyncio
    async def test_queue_status_with_task(self):
        """Test queue status with pending task."""
        with patch('api.routes.get_redis_client') as mock_redis, \
             patch('api.routes.grading_worker') as mock_worker:
            
            mock_client = AsyncMock()
            mock_client.llen = AsyncMock(return_value=1)
            mock_client.lindex = AsyncMock(return_value=json.dumps({
                "session_id": "pending_session",
                "created_at": "2025-01-01T00:00:00Z"
            }))
            mock_redis.return_value.get_client.return_value = mock_client
            mock_worker.is_running = True
            mock_worker.num_workers = 2
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/debug/queue-status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["queue_length"] == 1
            assert data["next_task"]["session_id"] == "pending_session"


# ==================== Summary API Tests ====================

class TestCreateSummaryEndpoint:
    """Tests for POST /api/v1/grading/summarize"""
    
    @pytest.mark.asyncio
    async def test_create_summary_success(self):
        """Test successful summary creation."""
        with patch('api.routes.result_store') as mock_store, \
             patch('services.summary_queue.summary_queue') as mock_queue:
            
            # Mock that all sessions have results
            mock_store.get_result = AsyncMock(return_value={
                "session_id": "sess_1",
                "score": 0.85
            })
            mock_store.set_summary_status = AsyncMock(return_value=True)
            mock_queue.enqueue = AsyncMock(return_value=True)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/grading/summarize", json={
                    "session_ids": ["sess_1", "sess_2"]
                })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"
            assert "summary_id" in data
            assert data["session_count"] == 2
    
    @pytest.mark.asyncio
    async def test_create_summary_missing_session(self):
        """Test summary creation with missing session results."""
        with patch('api.routes.result_store') as mock_store:
            # First session found, second not found
            mock_store.get_result = AsyncMock(side_effect=[
                {"session_id": "sess_1"},
                None
            ])
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/grading/summarize", json={
                    "session_ids": ["sess_1", "sess_2"]
                })
            
            assert response.status_code == 400
            assert "Missing grading results" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_summary_empty_sessions(self):
        """Test summary creation with empty session list."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/grading/summarize", json={
                "session_ids": []  # Empty list
            })
        
        assert response.status_code == 422  # Validation error


class TestGetSummaryStatusEndpoint:
    """Tests for GET /api/v1/grading/summary/{summary_id}/status"""
    
    @pytest.mark.asyncio
    async def test_status_not_found(self):
        """Test status when summary not found."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_summary_status = AsyncMock(return_value=None)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/summary/unknown/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_status_processing(self):
        """Test status when summary in progress."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_summary_status = AsyncMock(return_value={
                "status": "processing",
                "message": "Generating summary"
            })
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/summary/summ_123/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
            assert data["message"] == "Generating summary"
    
    @pytest.mark.asyncio
    async def test_status_completed(self):
        """Test status when summary completed."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_summary_status = AsyncMock(return_value={
                "status": "completed"
            })
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/summary/summ_123/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"


class TestGetSummaryResultEndpoint:
    """Tests for GET /api/v1/grading/summary/{summary_id}/result"""
    
    @pytest.mark.asyncio
    async def test_result_not_found(self):
        """Test result when summary not found."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_summary_result = AsyncMock(return_value=None)
            mock_store.get_summary_status = AsyncMock(return_value=None)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/summary/unknown/result")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_result_still_processing(self):
        """Test result when summary still processing."""
        with patch('api.routes.result_store') as mock_store:
            mock_store.get_summary_result = AsyncMock(return_value=None)
            mock_store.get_summary_status = AsyncMock(return_value={
                "status": "processing"
            })
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/summary/summ_123/result")
            
            assert response.status_code == 202
            assert "still processing" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_result_success(self):
        """Test result when available."""
        with patch('api.routes.result_store') as mock_store:
            # Return a proper SummaryResult model instance
            mock_result = SummaryResult(
                summary_id="summ_123",
                session_ids=["sess_1", "sess_2"],
                dimension_scores=[
                    DimensionScore(dimension="Correctness", score=0.8, feedback="Good accuracy")
                ],
                analytics_summary=["Overall score: 75/100"],
                overall_feedback="Good performance",
                key_strengths=["Strong understanding"],
                areas_for_improvement=["Time management"],
                processing_time=2.5,
                completed_at=datetime.now(timezone.utc)
            )
            mock_store.get_summary_result = AsyncMock(return_value=mock_result)
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/grading/summary/summ_123/result")
            
            assert response.status_code == 200
            data = response.json()
            assert data["summary_id"] == "summ_123"
            assert len(data["dimension_scores"]) == 1
            assert len(data["key_strengths"]) == 1

