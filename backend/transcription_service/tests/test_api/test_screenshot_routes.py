"""
Integration tests for Screenshot Upload API Routes

Tests the screenshot upload endpoint and its integration with grading publisher.
Uses mock Redis from conftest.py for isolated testing.
"""

import sys
from pathlib import Path

# Add the transcription_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app
from services.screenshot_service import screenshot_service
from services.grading_publisher import GradingPublisher
from services.redis_grading_queue import RedisGradingQueue
from schemas.screenshot import ScreenshotUploadStatus
from schemas.grading import GradingReadinessStatus

# Minimal valid image data for testing
PNG_DATA = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D,  # IHDR chunk length
    0x49, 0x48, 0x44, 0x52,  # IHDR
    0x00, 0x00, 0x00, 0x01,  # width
    0x00, 0x00, 0x00, 0x01,  # height
    0x08, 0x02, 0x00, 0x00, 0x00,  # bit depth, color type, etc.
    0x90, 0x77, 0x53, 0xDE,  # CRC
])

JPEG_DATA = bytes([
    0xFF, 0xD8, 0xFF, 0xE0,  # JPEG signature
    0x00, 0x10,  # Length
    0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,  # "JFIF"
    0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
])


@pytest_asyncio.fixture
async def client():
    """Create async test client"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def grading_publisher():
    """Get grading publisher instance"""
    return GradingPublisher()


@pytest_asyncio.fixture
async def grading_queue():
    """Get grading queue instance"""
    q = RedisGradingQueue()
    await q.clear_queue()
    yield q
    await q.clear_queue()


@pytest_asyncio.fixture
async def cleanup_session(grading_publisher):
    """Fixture to clean up session state after tests"""
    session_ids = []
    yield session_ids
    # Clean up
    for session_id in session_ids:
        await grading_publisher.delete_session_state(session_id)
        # Also clean up screenshot if it exists
        try:
            await screenshot_service.delete_screenshot(session_id)
        except Exception:
            pass # Ignore errors during cleanup


@pytest.mark.asyncio
async def test_upload_screenshot_success(client, cleanup_session, grading_publisher):
    """Test successful screenshot upload"""
    session_id = "sess_test_upload"
    cleanup_session.append(session_id)
    
    # Upload screenshot
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", PNG_DATA, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["status"] == ScreenshotUploadStatus.UPLOADED.value
    assert "screenshot_key" in data
    assert data["screenshot_key"] == f"{session_id}.png"
    
    # Verify screenshot file exists
    content, _ = await screenshot_service.get_screenshot(session_id)
    assert content == PNG_DATA
    
    # Verify session state in Redis (mock)
    state = await grading_publisher.get_session_state(session_id)
    assert state is not None
    assert state.get("screenshot_status") == "completed"
    assert state.get("screenshot_key") == data["screenshot_key"]


@pytest.mark.asyncio
async def test_upload_screenshot_jpeg(client, cleanup_session):
    """Test uploading JPEG screenshot"""
    session_id = "sess_test_jpeg"
    cleanup_session.append(session_id)
    
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.jpg", JPEG_DATA, "image/jpeg")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ScreenshotUploadStatus.UPLOADED.value
    assert data["screenshot_key"].endswith(".jpeg") or data["screenshot_key"].endswith(".jpg")


@pytest.mark.asyncio
async def test_upload_screenshot_with_transcription_ready(client, cleanup_session, grading_publisher, grading_queue):
    """Test uploading screenshot when transcription is already ready (should trigger grading)"""
    session_id = "sess_test_both_ready"
    cleanup_session.append(session_id)
    
    # First, mark transcription as ready
    await grading_publisher.publish_transcription_ready(
        session_id=session_id,
        transcription_text="Test transcription text"
    )
    
    # Now upload screenshot - should trigger grading
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", PNG_DATA, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ScreenshotUploadStatus.READY_FOR_GRADING.value
    assert data["grading_readiness_status"] == GradingReadinessStatus.ENQUEUED.value
    
    # Verify grading task was enqueued
    queue_length = await grading_queue.get_queue_length()
    assert queue_length >= 1  # At least one task in queue


@pytest.mark.asyncio
async def test_upload_screenshot_invalid_content_type(client):
    """Test uploading screenshot with invalid content type"""
    session_id = "sess_test_invalid"
    
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.gif", b"fake gif data", "image/gif")}
    )
    
    assert response.status_code == 400
    assert "Unsupported content type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_screenshot_invalid_file_signature(client):
    """Test uploading screenshot with invalid file signature"""
    session_id = "sess_test_invalid_sig"
    
    # Send PNG content type but invalid data
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", b"not a real image", "image/png")}
    )
    
    assert response.status_code == 400
    assert "Invalid image format" in response.json()["detail"] or "Could not determine" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_screenshot_empty_file(client):
    """Test uploading empty screenshot file"""
    session_id = "sess_test_empty"
    
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", b"", "image/png")}
    )
    
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_screenshot_missing_file(client):
    """Test uploading without screenshot file"""
    session_id = "sess_test_missing"
    
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot"
    )
    
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_upload_screenshot_readiness_status_waiting(client, cleanup_session):
    """Test that readiness status is correctly set when waiting for transcription"""
    session_id = "sess_test_waiting"
    cleanup_session.append(session_id)
    
    # Upload screenshot without transcription ready
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", PNG_DATA, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ScreenshotUploadStatus.UPLOADED.value
    assert data["grading_readiness_status"] == GradingReadinessStatus.WAITING_FOR_AUDIO.value


@pytest.mark.asyncio
async def test_upload_screenshot_accessible_via_url(client, cleanup_session):
    """Test that uploaded screenshot is accessible via the returned URL"""
    session_id = "sess_test_url"
    cleanup_session.append(session_id)
    
    # Upload screenshot
    response = await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", PNG_DATA, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify screenshot_key is correct
    assert "screenshot_key" in data
    assert data["screenshot_key"] == f"{session_id}.png"
    
    # Verify screenshot file exists and is fetchable
    content, _ = await screenshot_service.get_screenshot(session_id)
    assert content == PNG_DATA


@pytest.mark.asyncio
async def test_upload_screenshot_publisher_error_handling(client, cleanup_session, grading_publisher):
    """Test that upload succeeds even if grading publisher fails"""
    session_id = "sess_test_publisher_error"
    cleanup_session.append(session_id)
    
    # Mock grading publisher to raise an error
    with patch.object(grading_publisher, 'publish_screenshot_ready', side_effect=Exception("Redis error")):
        response = await client.post(
            f"/api/v1/transcribe/session/{session_id}/screenshot",
            files={"screenshot": ("test.png", PNG_DATA, "image/png")}
        )
        
        # Upload should still succeed even if publisher fails
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ScreenshotUploadStatus.UPLOADED.value
        
        # Screenshot file should still be stored
        content, _ = await screenshot_service.get_screenshot(session_id)
        assert content == PNG_DATA


@pytest.mark.asyncio
async def test_get_screenshot_success(client, cleanup_session):
    """Test retrieving a screenshot via GET endpoint"""
    session_id = "sess_test_get"
    cleanup_session.append(session_id)
    
    # First, upload a screenshot
    await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", PNG_DATA, "image/png")}
    )
    
    # Now retrieve it via GET endpoint
    response = await client.get(f"/api/v1/transcribe/screenshots/{session_id}")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG_DATA
    assert "Cache-Control" in response.headers


@pytest.mark.asyncio
async def test_get_screenshot_jpeg(client, cleanup_session):
    """Test retrieving a JPEG screenshot via GET endpoint"""
    session_id = "sess_test_get_jpeg"
    cleanup_session.append(session_id)
    
    # Upload JPEG screenshot
    await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.jpg", JPEG_DATA, "image/jpeg")}
    )
    
    # Retrieve it
    response = await client.get(f"/api/v1/transcribe/screenshots/{session_id}")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == JPEG_DATA


@pytest.mark.asyncio
async def test_get_screenshot_not_found(client):
    """Test retrieving a screenshot that doesn't exist"""
    session_id = "sess_nonexistent"
    
    response = await client.get(f"/api/v1/transcribe/screenshots/{session_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_screenshot_with_extension_in_url(client, cleanup_session):
    """Test retrieving a screenshot where URL includes the extension"""
    session_id = "sess_test_ext_url"
    cleanup_session.append(session_id)
    
    # Upload screenshot
    await client.post(
        f"/api/v1/transcribe/session/{session_id}/screenshot",
        files={"screenshot": ("test.png", PNG_DATA, "image/png")}
    )
    
    # Retrieve using ID + extension (how it appears in absolute URLs)
    response = await client.get(f"/api/v1/transcribe/screenshots/{session_id}.png")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG_DATA
