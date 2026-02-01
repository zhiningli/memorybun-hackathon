"""
Tests for Audio Storage Service

Tests audio storage to S3 and FILESYSTEM mode skip logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestAudioStorageServiceFilesystemMode:
    """Test audio storage behavior in FILESYSTEM mode (storage disabled)."""
    
    def test_is_enabled_false_in_filesystem_mode(self):
        """Storage should be disabled in FILESYSTEM mode."""
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "FILESYSTEM"
            mock_settings.s3_bucket = None
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_type="FILESYSTEM")
            
            assert service.is_enabled is False
            assert service.storage is None
    
    @pytest.mark.asyncio
    async def test_store_audio_returns_none_in_filesystem_mode(self):
        """store_audio should return None when storage is disabled."""
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "FILESYSTEM"
            mock_settings.s3_bucket = None
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_type="FILESYSTEM")
            
            result = await service.store_audio(
                session_id="test_session",
                chunk_index=0,
                audio_data=b"test audio data"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_store_session_audio_returns_none_in_filesystem_mode(self):
        """store_session_audio should return None when storage is disabled."""
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "FILESYSTEM"
            mock_settings.s3_bucket = None
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_type="FILESYSTEM")
            
            result = await service.store_session_audio(
                session_id="test_session",
                audio_data=b"test audio data"
            )
            
            assert result is None
    
    def test_get_audio_url_returns_none_in_filesystem_mode(self):
        """get_audio_url should return None when storage is disabled."""
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "FILESYSTEM"
            mock_settings.s3_bucket = None
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_type="FILESYSTEM")
            
            result = service.get_audio_url("test_session")
            
            assert result is None


class TestAudioStorageServiceS3Mode:
    """Test audio storage behavior in S3 mode."""
    
    def test_is_enabled_true_in_s3_mode(self):
        """Storage should be enabled in S3 mode."""
        mock_storage = Mock()
        
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "S3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_backend=mock_storage, storage_type="S3")
            
            assert service.is_enabled is True
            assert service.storage is mock_storage
    
    @pytest.mark.asyncio
    async def test_store_audio_calls_storage_save(self):
        """store_audio should call storage.save with correct parameters."""
        mock_storage = Mock()
        mock_storage.save = AsyncMock(return_value="audio/test_session_chunk_0.webm")
        mock_storage.get_public_url = Mock(return_value="https://bucket.s3.region.amazonaws.com/audio/test_session_chunk_0.webm")
        
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "S3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_backend=mock_storage, storage_type="S3")
            
            audio_data = b"test audio data"
            result = await service.store_audio(
                session_id="test_session",
                chunk_index=0,
                audio_data=audio_data
            )
            
            # Verify save was called with correct parameters
            mock_storage.save.assert_called_once_with(
                "test_session_chunk_0.webm",
                audio_data,
                "video/webm"
            )
            
            # Verify URL was returned
            assert "https://" in result
    
    @pytest.mark.asyncio
    async def test_store_session_audio_calls_storage_save(self):
        """store_session_audio should call storage.save with correct parameters."""
        mock_storage = Mock()
        mock_storage.save = AsyncMock(return_value="audio/test_session.webm")
        mock_storage.get_public_url = Mock(return_value="https://bucket.s3.region.amazonaws.com/audio/test_session.webm")
        
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "S3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_backend=mock_storage, storage_type="S3")
            
            audio_data = b"test audio data"
            result = await service.store_session_audio(
                session_id="test_session",
                audio_data=audio_data
            )
            
            # Verify save was called with correct parameters
            mock_storage.save.assert_called_once_with(
                "test_session.webm",
                audio_data,
                "video/webm"
            )
            
            # Verify URL was returned
            assert "https://" in result
    
    def test_get_audio_url_returns_url_in_s3_mode(self):
        """get_audio_url should return S3 URL when storage is enabled."""
        mock_storage = Mock()
        mock_storage.get_public_url = Mock(return_value="https://bucket.s3.region.amazonaws.com/audio/test_session.webm")
        
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "S3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_backend=mock_storage, storage_type="S3")
            
            result = service.get_audio_url("test_session")
            
            mock_storage.get_public_url.assert_called_once_with("test_session.webm")
            assert "https://" in result


class TestAudioStorageServiceValidation:
    """Test input validation."""
    
    @pytest.mark.asyncio
    async def test_store_audio_rejects_path_traversal(self):
        """store_audio should reject session IDs with path traversal."""
        mock_storage = Mock()
        
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "S3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_backend=mock_storage, storage_type="S3")
            
            with pytest.raises(ValueError, match="Invalid session_id"):
                await service.store_audio(
                    session_id="../malicious",
                    chunk_index=0,
                    audio_data=b"test"
                )
    
    @pytest.mark.asyncio
    async def test_store_session_audio_rejects_path_traversal(self):
        """store_session_audio should reject session IDs with path traversal."""
        mock_storage = Mock()
        
        with patch('config.settings') as mock_settings:
            mock_settings.storage_type = "S3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_audio_prefix = "audio"
            
            from services.audio_storage_service import AudioStorageService
            service = AudioStorageService(storage_backend=mock_storage, storage_type="S3")
            
            with pytest.raises(ValueError, match="Invalid session_id"):
                await service.store_session_audio(
                    session_id="test/session",
                    audio_data=b"test"
                )
