"""
Tests for Screenshot Service

Tests screenshot storage, retrieval, validation, and deletion functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
from fastapi import UploadFile
from services.screenshot_service import ScreenshotService

# Minimal valid image data for testing
# PNG signature: 89 50 4E 47 0D 0A 1A 0A
PNG_DATA = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D,  # IHDR chunk length
    0x49, 0x48, 0x44, 0x52,  # IHDR
    0x00, 0x00, 0x00, 0x01,  # width
    0x00, 0x00, 0x00, 0x01,  # height
    0x08, 0x02, 0x00, 0x00, 0x00,  # bit depth, color type, etc.
    0x90, 0x77, 0x53, 0xDE,  # CRC
])

# JPEG signature: FF D8 FF
JPEG_DATA = bytes([
    0xFF, 0xD8, 0xFF, 0xE0,  # JPEG signature
    0x00, 0x10,  # Length
    0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,  # "JFIF"
    0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
])

# WebP signature: RIFF ... WEBP
WEBP_DATA = bytes([
    0x52, 0x49, 0x46, 0x46,  # "RIFF"
    0x00, 0x00, 0x00, 0x00,  # file size (placeholder)
    0x57, 0x45, 0x42, 0x50,  # "WEBP"
])


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test screenshots"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def screenshot_service(temp_dir):
    """Create a screenshot service instance with temporary directory"""
    from services.storage.filesystem import FileSystemStorage
    storage = FileSystemStorage(base_path=temp_dir)
    return ScreenshotService(storage_backend=storage)


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing"""
    def _create(content_type: str, filename: str = "test.png"):
        mock_file = Mock(spec=UploadFile)
        mock_file.content_type = content_type
        mock_file.filename = filename
        return mock_file
    return _create


class TestScreenshotServiceValidation:
    """Test validation methods"""
    
    def test_validate_content_type_png(self, screenshot_service):
        """Test PNG content type validation"""
        assert screenshot_service._validate_content_type("image/png") is True
        assert screenshot_service._validate_content_type("IMAGE/PNG") is True  # Case insensitive
    
    def test_validate_content_type_jpeg(self, screenshot_service):
        """Test JPEG content type validation"""
        assert screenshot_service._validate_content_type("image/jpeg") is True
        assert screenshot_service._validate_content_type("image/jpg") is True
    
    def test_validate_content_type_webp(self, screenshot_service):
        """Test WebP content type validation"""
        assert screenshot_service._validate_content_type("image/webp") is True
    
    def test_validate_content_type_invalid(self, screenshot_service):
        """Test invalid content type rejection"""
        assert screenshot_service._validate_content_type("image/gif") is False
        assert screenshot_service._validate_content_type("text/plain") is False
        assert screenshot_service._validate_content_type(None) is False
        assert screenshot_service._validate_content_type("") is False
    
    def test_validate_file_signature_png(self, screenshot_service):
        """Test PNG file signature validation"""
        content_type = screenshot_service._validate_file_signature(PNG_DATA)
        assert content_type == "image/png"
    
    def test_validate_file_signature_jpeg(self, screenshot_service):
        """Test JPEG file signature validation"""
        content_type = screenshot_service._validate_file_signature(JPEG_DATA)
        assert content_type == "image/jpeg"
    
    def test_validate_file_signature_webp(self, screenshot_service):
        """Test WebP file signature validation"""
        content_type = screenshot_service._validate_file_signature(WEBP_DATA)
        assert content_type == "image/webp"
    
    def test_validate_file_signature_invalid(self, screenshot_service):
        """Test invalid file signature rejection"""
        invalid_data = b"not an image"
        content_type = screenshot_service._validate_file_signature(invalid_data)
        assert content_type is None
    
    def test_validate_upload_file_png(self, screenshot_service, mock_upload_file):
        """Test validating PNG upload file"""
        file = mock_upload_file("image/png", "test.png")
        content_type = screenshot_service.validate_upload_file(file)
        assert content_type == "image/png"
    
    def test_validate_upload_file_jpeg(self, screenshot_service, mock_upload_file):
        """Test validating JPEG upload file"""
        file = mock_upload_file("image/jpeg", "test.jpg")
        content_type = screenshot_service.validate_upload_file(file)
        assert content_type == "image/jpeg"
    
    def test_validate_upload_file_invalid_content_type(self, screenshot_service, mock_upload_file):
        """Test rejecting invalid content type"""
        file = mock_upload_file("image/gif", "test.gif")
        with pytest.raises(ValueError, match="Unsupported content type"):
            screenshot_service.validate_upload_file(file)
    
    def test_validate_upload_file_invalid_extension(self, screenshot_service, mock_upload_file):
        """Test rejecting invalid file extension"""
        file = mock_upload_file("image/png", "test.gif")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            screenshot_service.validate_upload_file(file)


class TestScreenshotServiceStorage:
    """Test storage operations"""
    
    @pytest.mark.asyncio
    async def test_store_screenshot_png(self, screenshot_service):
        """Test storing PNG screenshot"""
        session_id = "sess_test123"
        key = await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=PNG_DATA,
            content_type="image/png"
        )
        
        assert key == f"{session_id}.png"
        
        # Verify file exists
        data, _ = await screenshot_service.get_screenshot(session_id)
        assert data == PNG_DATA
    
    @pytest.mark.asyncio
    async def test_store_screenshot_jpeg(self, screenshot_service):
        """Test storing JPEG screenshot"""
        session_id = "sess_test456"
        key = await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=JPEG_DATA,
            content_type="image/jpeg"
        )
        
        assert key == f"{session_id}.jpeg"
        
        # Verify file exists
        data, _ = await screenshot_service.get_screenshot(session_id)
        assert data == JPEG_DATA
    
    @pytest.mark.asyncio
    async def test_store_screenshot_webp(self, screenshot_service):
        """Test storing WebP screenshot"""
        session_id = "sess_test789"
        key = await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=WEBP_DATA,
            content_type="image/webp"
        )
        
        assert key == f"{session_id}.webp"
        
        # Verify file exists
        data, _ = await screenshot_service.get_screenshot(session_id)
        assert data == WEBP_DATA
    
    @pytest.mark.asyncio
    async def test_store_screenshot_infer_content_type(self, screenshot_service):
        """Test storing screenshot without content type (inferred from signature)"""
        session_id = "sess_test_infer"
        key = await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=PNG_DATA,
            content_type=None
        )
        
        assert key == f"{session_id}.png"
        data, _ = await screenshot_service.get_screenshot(session_id)
        assert data == PNG_DATA
    
    @pytest.mark.asyncio
    async def test_store_screenshot_invalid_content_type(self, screenshot_service):
        """Test storing screenshot with invalid content type"""
        with pytest.raises(ValueError, match="Unsupported content type"):
            await screenshot_service.store_screenshot(
                session_id="sess_test",
                image_data=PNG_DATA,
                content_type="image/gif"
            )
    
    @pytest.mark.asyncio
    async def test_store_screenshot_invalid_signature(self, screenshot_service):
        """Test storing screenshot with invalid file signature"""
        invalid_data = b"not an image"
        with pytest.raises(ValueError, match="Could not determine image format"):
            await screenshot_service.store_screenshot(
                session_id="sess_test",
                image_data=invalid_data,
                content_type=None
            )
    
    @pytest.mark.asyncio
    async def test_store_screenshot_overwrite(self, screenshot_service):
        """Test that storing screenshot overwrites existing file"""
        session_id = "sess_test_overwrite"
        
        # Store first screenshot
        key1 = await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=PNG_DATA,
            content_type="image/png"
        )
        
        # Store different screenshot same extension
        key2 = await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=PNG_DATA,
            content_type="image/png"
        )
        
        assert key2 == key1
        data, _ = await screenshot_service.get_screenshot(session_id)
        assert data == PNG_DATA


class TestScreenshotServiceRetrieval:
    """Test retrieval operations"""
    
    def test_get_screenshot_url_with_extension(self, screenshot_service):
        """Test getting screenshot URL with extension"""
        session_id = "sess_test"
        url = screenshot_service.get_screenshot_url(session_id, ".png")
        assert url == f"http://localhost:8001/api/v1/transcribe/screenshots/{session_id}.png"
    
    @pytest.mark.asyncio
    async def test_get_screenshot_url_without_extension(self, screenshot_service):
        """Test getting screenshot URL without extension (finds existing file)"""
        session_id = "sess_test_find"
        
        # Store a screenshot first
        await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=PNG_DATA,
            content_type="image/png"
        )
        
        # Get URL without extension (should find .png file)
        url = screenshot_service.get_screenshot_url(session_id, extension=None)
        assert url == f"http://localhost:8001/api/v1/transcribe/screenshots/{session_id}.png"
    
    def test_get_screenshot_url_not_found(self, screenshot_service):
        """Test getting screenshot URL when file doesn't exist"""
        session_id = "sess_test_not_found"
        url = screenshot_service.get_screenshot_url(session_id, extension=None)
        # Should default to .png
        assert url == f"http://localhost:8001/api/v1/transcribe/screenshots/{session_id}.png"
    
    @pytest.mark.asyncio
    async def test_get_screenshot_success(self, screenshot_service):
        """Test getting screenshot when file exists"""
        session_id = "sess_test_path"
        
        # Store screenshot
        await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=PNG_DATA,
            content_type="image/png"
        )
        
        # Get screenshot
        data, content_type = await screenshot_service.get_screenshot(session_id)
        assert data == PNG_DATA
        assert content_type == "image/png"
    
    @pytest.mark.asyncio
    async def test_get_screenshot_not_found(self, screenshot_service):
        """Test getting screenshot when file doesn't exist"""
        session_id = "sess_test_path_not_found"
        with pytest.raises(FileNotFoundError):
           await screenshot_service.get_screenshot(session_id)
    
    # We removed get_screenshot_path() from public API so we don't test it directly unless we test private implementation
    # But for valid testing, we should test public behaviors: Store -> Get -> Delete
    
    @pytest.mark.asyncio
    async def test_delete_screenshot_exists(self, screenshot_service):
        """Test deleting existing screenshot"""
        session_id = "sess_test_delete"
        
        # Store screenshot
        await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=PNG_DATA,
            content_type="image/png"
        )
        
        # Verify exists
        await screenshot_service.get_screenshot(session_id)
        
        # Delete
        result = await screenshot_service.delete_screenshot(session_id)
        assert result is True
        
        # Verify deleted
        with pytest.raises(FileNotFoundError):
            await screenshot_service.get_screenshot(session_id)
    
    @pytest.mark.asyncio
    async def test_delete_screenshot_not_found(self, screenshot_service):
        """Test deleting non-existent screenshot"""
        session_id = "sess_test_delete_not_found"
        result = await screenshot_service.delete_screenshot(session_id)
        assert result is False


class TestScreenshotServiceInitialization:
    """Test service initialization"""
    
    def test_init_with_custom_path(self, temp_dir):
        """Test initializing with custom base path via DI"""
        from services.storage.filesystem import FileSystemStorage
        storage = FileSystemStorage(base_path=temp_dir)
        service = ScreenshotService(storage_backend=storage)
        assert service.storage.base_path == temp_dir
        assert service.storage.base_path.exists()
    
    def test_init_with_default_path(self):
        """Test initializing with default path"""
        service = ScreenshotService()
        # Should create storage backend
        assert hasattr(service, 'storage')
    
    def test_init_creates_directory(self, temp_dir):
        """Test that initialization creates directly via storage backend"""
        new_dir = temp_dir / "new_screenshots"
        assert not new_dir.exists()
        
        from services.storage.filesystem import FileSystemStorage
        storage = FileSystemStorage(base_path=new_dir)
        service = ScreenshotService(storage_backend=storage)
       
        assert new_dir.exists()

