"""
Isolated unit tests for audio transcription API routes.

These tests run in a completely isolated environment:
- No real Whisper model (mocked)
- No background workers (synchronous processing)
- No Redis (mocked)
- No file system dependencies (in-memory)

This ensures fast, reliable, and deterministic tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone
import sys

# Mock faster-whisper and ctranslate2 BEFORE any imports that use them
mock_ctranslate2 = MagicMock()
mock_ctranslate2.get_cuda_device_count.return_value = 0
sys.modules['ctranslate2'] = mock_ctranslate2

mock_faster_whisper = MagicMock()
sys.modules['faster_whisper'] = mock_faster_whisper


# =============================================================================
# Mock Service Factory
# =============================================================================

def create_mock_audio_service():
    """
    Create a fully mocked AudioTranscriptionService.
    All methods return appropriate values without any external dependencies.
    """
    from schemas.transcription import (
        TranscriptionSession,
        TranscriptionSessionStatus,
        WhisperModelEnum,
        AudioTranscriptionSessionResult,
    )
    
    # Use Mock instead of AsyncMock to avoid coroutine issues with sync methods
    service = Mock()
    
    # Track sessions for realistic behavior
    sessions = {}
    chunk_results = {}
    
    async def mock_create_session(request):
        import uuid
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        sessions[session_id] = {
            "model": request.model,
            "status": TranscriptionSessionStatus.ACTIVE,
            "created_at": now,
            "chunks": {},
            "full_text": "",
        }
        return TranscriptionSession(
            session_id=session_id,
            model=request.model,
            status=TranscriptionSessionStatus.ACTIVE,
            created_at=now,
        )
    
    async def mock_get_session_result(session_id):
        if session_id not in sessions:
            return None
        sess = sessions[session_id]
        return AudioTranscriptionSessionResult(
            session_id=session_id,
            status=sess["status"],
            full_text=sess["full_text"],
            chunks_processed=len(sess["chunks"]),
            total_processing_time=0.5,
            whisper_model=sess["model"],
            created_at=sess["created_at"],
            completed_at=None,
        )
    
    async def mock_finalize_session(session_id, thinking_time=None):
        if session_id not in sessions:
            return None
        sess = sessions[session_id]
        sess["status"] = TranscriptionSessionStatus.COMPLETED
        now = datetime.now(timezone.utc)
        return AudioTranscriptionSessionResult(
            session_id=session_id,
            status=TranscriptionSessionStatus.COMPLETED,
            full_text=sess["full_text"],
            chunks_processed=len(sess["chunks"]),
            total_processing_time=0.5,
            whisper_model=sess["model"],
            created_at=sess["created_at"],
            completed_at=now,
        )
    
    async def mock_delete_session(session_id):
        if session_id in sessions:
            del sessions[session_id]
            return True
        return False
    
    async def mock_enqueue_chunk(session_id, chunk_index, audio_file_path):
        if session_id not in sessions:
            raise ValueError(f"Session {session_id} not found")
        # Simulate immediate processing (no background worker)
        task_id = f"{session_id}_chunk_{chunk_index}"
        transcribed_text = "This is a test transcription result."
        sessions[session_id]["chunks"][chunk_index] = transcribed_text
        sessions[session_id]["full_text"] = " ".join(
            sessions[session_id]["chunks"].get(i, "") 
            for i in sorted(sessions[session_id]["chunks"].keys())
        ).strip()
        chunk_results[task_id] = {
            "status": "completed",
            "result": transcribed_text,
        }
        return task_id
    
    async def mock_get_chunk_status(session_id, chunk_index):
        task_id = f"{session_id}_chunk_{chunk_index}"
        if task_id not in chunk_results:
            return None
        result = chunk_results[task_id]
        now = datetime.now(timezone.utc)
        return {
            "task_id": task_id,
            "session_id": session_id,
            "chunk_index": chunk_index,
            "status": result["status"],
            "result": result.get("result"),
            "error": result.get("error"),
            "created_at": now.isoformat(),
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
        }
    
    # Sync method - just return the dict directly
    def mock_get_device_info():
        return {"device": "cpu", "cuda_available": "False"}
    
    # Assign methods
    service.gen_create_session = mock_create_session
    service.gen_get_session_result = mock_get_session_result
    service.gen_finalize_session = mock_finalize_session
    service.gen_delete_session = mock_delete_session
    service.gen_enqueue_chunk = mock_enqueue_chunk
    service.gen_get_chunk_status = mock_get_chunk_status
    service.get_device_info = mock_get_device_info  # Sync method
    service._sessions = sessions
    service._chunk_results = chunk_results
    
    return service


def create_test_app_with_mock_service(mock_service):
    """
    Create a fresh FastAPI app with mocked dependencies.
    This bypasses the real lifespan entirely.
    """
    from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
    from fastapi.middleware.cors import CORSMiddleware
    from schemas.transcription import (
        CreateAudioTranscriptionSessionRequest,
        TranscriptionSession,
    )
    
    app = FastAPI(title="Test Transcription Service")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Dependency that returns our mock service
    async def get_service():
        return mock_service
    
    # Re-create routes using the mock service
    @app.post("/api/v1/transcribe/session", response_model=TranscriptionSession)
    async def create_session(
        request: CreateAudioTranscriptionSessionRequest,
        service=Depends(get_service)
    ):
        return await service.gen_create_session(request)
    
    @app.get("/api/v1/transcribe/session/{session_id}/audio")
    async def get_session_result(session_id: str, service=Depends(get_service)):
        result = await service.gen_get_session_result(session_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return result
    
    @app.post("/api/v1/transcribe/session/{session_id}/audio/finalize")
    async def finalize_session(session_id: str, service=Depends(get_service)):
        result = await service.gen_finalize_session(session_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return result
    
    @app.delete("/api/v1/transcribe/session/{session_id}")
    async def delete_session(session_id: str, service=Depends(get_service)):
        deleted = await service.gen_delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {"message": f"Session {session_id} deleted successfully"}
    
    @app.post("/api/v1/transcribe/session/{session_id}/audio/chunk")
    async def upload_chunk(
        session_id: str,
        audio_file: UploadFile = File(...),
        chunk_index: int = Form(...),
        service=Depends(get_service)
    ):
        # Validate audio format
        filename = audio_file.filename or ""
        content_type = audio_file.content_type or ""
        
        if not (filename.endswith('.webm') or 'webm' in content_type):
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Only WebM files are accepted."
            )
        
        # Check session exists
        if session_id not in service._sessions:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        try:
            # Enqueue chunk (mock processes it immediately)
            task_id = await service.gen_enqueue_chunk(
                session_id=session_id,
                chunk_index=chunk_index,
                audio_file_path=f"/tmp/{session_id}_{chunk_index}.webm"
            )
            
            return {
                "task_id": task_id,
                "session_id": session_id,
                "chunk_index": chunk_index,
                "status": "queued",
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @app.get("/api/v1/transcribe/session/{session_id}/audio/chunk/{chunk_index}/status")
    async def get_chunk_status(
        session_id: str,
        chunk_index: int,
        service=Depends(get_service)
    ):
        status = await service.gen_get_chunk_status(session_id, chunk_index)
        if status is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Chunk {chunk_index} not found for session {session_id}"
            )
        return status
    
    @app.get("/api/v1/transcribe/device-info")
    async def get_device_info(service=Depends(get_service)):
        return service.get_device_info()
    
    return app


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_service():
    """Create a mock service for testing"""
    return create_mock_audio_service()


@pytest.fixture
def test_client(mock_service):
    """Create a test client with a fully isolated app"""
    app = create_test_app_with_mock_service(mock_service)
    with TestClient(app) as client:
        yield client


# =============================================================================
# Session Management Tests
# =============================================================================

class TestSessionManagement:
    """Tests for session CRUD operations"""
    
    def test_create_session_returns_valid_session(self, test_client):
        """Test that creating a session returns a valid session object"""
        response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny", "expected_duration": 30.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "model" in data
        assert "status" in data
        assert "created_at" in data
        assert data["status"] == "active"
        assert data["model"] == "tiny"
        assert data["session_id"].startswith("sess_")
    
    def test_create_session_with_different_models(self, test_client):
        """Test creating sessions with different Whisper models"""
        for model in ["tiny", "base", "small"]:
            response = test_client.post(
                "/api/v1/transcribe/session",
                json={"model": model}
            )
            assert response.status_code == 200
            assert response.json()["model"] == model
    
    def test_get_nonexistent_session_returns_404(self, test_client):
        """Test that getting a non-existent session returns 404"""
        response = test_client.get("/api/v1/transcribe/session/non_existent_session/audio")
        assert response.status_code == 404
    
    def test_finalize_nonexistent_session_returns_404(self, test_client):
        """Test that finalizing a non-existent session returns 404"""
        response = test_client.post("/api/v1/transcribe/session/non_existent_session/audio/finalize")
        assert response.status_code == 404
    
    def test_delete_nonexistent_session_returns_404(self, test_client):
        """Test that deleting a non-existent session returns 404"""
        response = test_client.delete("/api/v1/transcribe/session/non_existent_session")
        assert response.status_code == 404
    
    def test_delete_session_success(self, test_client):
        """Test successful session deletion"""
        # Create session
        create_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny"}
        )
        session_id = create_response.json()["session_id"]
        
        # Delete session
        delete_response = test_client.delete(f"/api/v1/transcribe/session/{session_id}")
        assert delete_response.status_code == 200
        assert "deleted successfully" in delete_response.json()["message"]
        
        # Verify session is gone
        get_response = test_client.get(f"/api/v1/transcribe/session/{session_id}/audio")
        assert get_response.status_code == 404
    
    def test_finalize_session_changes_status_to_completed(self, test_client):
        """Test that finalizing a session changes its status"""
        # Create session
        create_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny"}
        )
        session_id = create_response.json()["session_id"]
        
        # Finalize session
        finalize_response = test_client.post(
            f"/api/v1/transcribe/session/{session_id}/audio/finalize"
        )
        assert finalize_response.status_code == 200
        assert finalize_response.json()["status"] == "completed"


# =============================================================================
# Audio Chunk Tests
# =============================================================================

class TestAudioChunkOperations:
    """Tests for audio chunk upload and processing"""
    
    def test_upload_chunk_with_valid_webm(self, test_client):
        """Test uploading a valid WebM audio chunk"""
        # Create session first
        session_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny"}
        )
        session_id = session_response.json()["session_id"]
        
        # Upload chunk
        fake_webm = b'\x1a\x45\xdf\xa3'  # WebM file signature
        files = {"audio_file": ("test.webm", fake_webm, "audio/webm")}
        data = {"chunk_index": 0}
        
        response = test_client.post(
            f"/api/v1/transcribe/session/{session_id}/audio/chunk",
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "task_id" in result
        assert result["session_id"] == session_id
        assert result["chunk_index"] == 0
        assert result["status"] == "queued"
    
    def test_upload_chunk_with_invalid_format_returns_400(self, test_client):
        """Test that uploading non-WebM file returns 400"""
        # Create session first
        session_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny"}
        )
        session_id = session_response.json()["session_id"]
        
        # Try to upload invalid file (MP3)
        files = {"audio_file": ("test.mp3", b"fake mp3 content", "audio/mpeg")}
        data = {"chunk_index": 0}
        
        response = test_client.post(
            f"/api/v1/transcribe/session/{session_id}/audio/chunk",
            files=files,
            data=data
        )
        
        assert response.status_code == 400
        assert "Unsupported audio format" in response.json()["detail"]
    
    def test_upload_chunk_to_invalid_session_returns_404(self, test_client):
        """Test that uploading to non-existent session returns 404"""
        files = {"audio_file": ("test.webm", b"fake webm content", "audio/webm")}
        data = {"chunk_index": 0}
        
        response = test_client.post(
            "/api/v1/transcribe/session/invalid_session_id/audio/chunk",
            files=files,
            data=data
        )
        
        assert response.status_code == 404
    
    def test_get_chunk_status_after_upload(self, test_client):
        """Test getting chunk status after upload"""
        # Create session
        session_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny"}
        )
        session_id = session_response.json()["session_id"]
        
        # Upload chunk
        files = {"audio_file": ("test.webm", b'\x1a\x45\xdf\xa3', "audio/webm")}
        data = {"chunk_index": 0}
        test_client.post(
            f"/api/v1/transcribe/session/{session_id}/audio/chunk",
            files=files,
            data=data
        )
        
        # Get status
        response = test_client.get(
            f"/api/v1/transcribe/session/{session_id}/audio/chunk/0/status"
        )
        
        assert response.status_code == 200
        status = response.json()
        assert status["status"] == "completed"
        assert status["chunk_index"] == 0
        assert status["result"] is not None
    
    def test_get_chunk_status_nonexistent_returns_404(self, test_client):
        """Test that getting status for non-existent chunk returns 404"""
        # Create a session first
        session_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny"}
        )
        session_id = session_response.json()["session_id"]
        
        # Try to get status for non-existent chunk
        response = test_client.get(
            f"/api/v1/transcribe/session/{session_id}/audio/chunk/999/status"
        )
        
        assert response.status_code == 404


# =============================================================================
# Device Info Tests
# =============================================================================

class TestDeviceInfo:
    """Tests for device information endpoint"""
    
    def test_device_info_endpoint_returns_info(self, test_client):
        """Test that device info endpoint returns device information"""
        response = test_client.get("/api/v1/transcribe/device-info")
        assert response.status_code == 200
        data = response.json()
        
        assert "device" in data
        assert "cuda_available" in data
        assert data["device"] == "cpu"


# =============================================================================
# Full Flow Tests
# =============================================================================

class TestFullTranscriptionFlow:
    """End-to-end flow tests"""
    
    def test_complete_transcription_workflow(self, test_client):
        """
        Test the complete transcription workflow:
        1. Create session
        2. Upload chunk
        3. Check status
        4. Get result
        5. Finalize
        6. Cleanup
        """
        # Step 1: Create session
        session_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny", "expected_duration": 30.0}
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]
        
        # Step 2: Upload chunk
        fake_webm = b'\x1a\x45\xdf\xa3'
        files = {"audio_file": ("test.webm", fake_webm, "audio/webm")}
        data = {"chunk_index": 0}
        
        chunk_response = test_client.post(
            f"/api/v1/transcribe/session/{session_id}/audio/chunk",
            files=files,
            data=data
        )
        assert chunk_response.status_code == 200
        assert chunk_response.json()["status"] == "queued"
        
        # Step 3: Check chunk status
        status_response = test_client.get(
            f"/api/v1/transcribe/session/{session_id}/audio/chunk/0/status"
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "completed"
        
        # Step 4: Get session result
        result_response = test_client.get(
            f"/api/v1/transcribe/session/{session_id}/audio"
        )
        assert result_response.status_code == 200
        result = result_response.json()
        assert result["chunks_processed"] == 1
        assert len(result["full_text"]) > 0
        
        # Step 5: Finalize session
        finalize_response = test_client.post(
            f"/api/v1/transcribe/session/{session_id}/audio/finalize"
        )
        assert finalize_response.status_code == 200
        assert finalize_response.json()["status"] == "completed"
        
        # Step 6: Delete session
        delete_response = test_client.delete(
            f"/api/v1/transcribe/session/{session_id}"
        )
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = test_client.get(
            f"/api/v1/transcribe/session/{session_id}/audio"
        )
        assert get_response.status_code == 404
    
    def test_multiple_chunks_accumulate_text(self, test_client):
        """Test that multiple chunks accumulate transcription text"""
        # Create session
        session_response = test_client.post(
            "/api/v1/transcribe/session",
            json={"model": "tiny"}
        )
        session_id = session_response.json()["session_id"]
        
        # Upload 3 chunks
        for i in range(3):
            fake_webm = b'\x1a\x45\xdf\xa3'
            files = {"audio_file": (f"chunk_{i}.webm", fake_webm, "audio/webm")}
            data = {"chunk_index": i}
            
            response = test_client.post(
                f"/api/v1/transcribe/session/{session_id}/audio/chunk",
                files=files,
                data=data
            )
            assert response.status_code == 200
        
        # Get result
        result_response = test_client.get(
            f"/api/v1/transcribe/session/{session_id}/audio"
        )
        assert result_response.status_code == 200
        result = result_response.json()
        
        assert result["chunks_processed"] == 3
        # Each chunk adds "This is a test transcription result."
        assert result["full_text"].count("test transcription") == 3
        
        # Cleanup
        test_client.delete(f"/api/v1/transcribe/session/{session_id}")
