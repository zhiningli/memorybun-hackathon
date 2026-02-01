"""
Unit tests for transcription worker.
"""
import sys
from pathlib import Path
import asyncio
import tempfile
import os
from unittest.mock import MagicMock

# Add the transcription_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

# Mock faster-whisper and ctranslate2 BEFORE any imports that use them
mock_ctranslate2 = MagicMock()
mock_ctranslate2.get_cuda_device_count.return_value = 0
sys.modules['ctranslate2'] = mock_ctranslate2

mock_faster_whisper = MagicMock()
sys.modules['faster_whisper'] = mock_faster_whisper

import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.transcription_worker import TranscriptionWorker
from services.transcription_queue import TranscriptionQueue, TranscriptionTask, TaskStatus
from services.audio_transcription_service import AudioTranscriptionService


class TestTranscriptionWorker:
    """Tests for TranscriptionWorker class"""
    
    @pytest.fixture
    def worker(self):
        """Create a worker instance for testing"""
        return TranscriptionWorker(num_workers=1)
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock transcription service"""
        service = Mock(spec=AudioTranscriptionService)
        service.gen_process_chunk_async = AsyncMock()
        return service
    
    @pytest.fixture
    def temp_audio_file(self):
        """Create a temporary audio file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as f:
            f.write(b"fake audio content")
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            os.unlink(temp_path)
    
    def test_worker_initialization(self, worker):
        """Test worker initialization"""
        assert worker.num_workers == 1
        assert worker._running is False
        assert len(worker._workers) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_worker(self, worker, mock_service):
        """Test starting and stopping worker"""
        await worker.start(mock_service)
        assert worker._running is True
        assert len(worker._workers) == 1
        assert worker.audio_transcription_service == mock_service
        
        await worker.stop()
        assert worker._running is False
        assert len(worker._workers) == 0
        assert worker.audio_transcription_service is None
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, worker, mock_service):
        """Test starting worker when already running"""
        await worker.start(mock_service)
        assert worker._running is True
        
        # Starting again should not create duplicate workers
        await worker.start(mock_service)
        assert len(worker._workers) == 1
        
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, worker):
        """Test stopping worker when not running"""
        # Should not raise an error
        await worker.stop()
        assert worker._running is False
    
    @pytest.mark.asyncio
    async def test_process_task_success(self, worker, temp_audio_file, mock_service):
        """Test processing a task successfully"""
        # Create a task
        task = TranscriptionTask(
            session_id="sess_test",
            chunk_index=0,
            audio_file_path=str(temp_audio_file)
        )
        
        # Mock the service to return a successful result
        mock_result = Mock()
        mock_result.chunk_text = "This is transcribed text"
        mock_result.session_id = "sess_test"
        mock_result.chunk_index = 0
        mock_result.accumulated_text = "This is transcribed text"
        mock_result.chunks_processed = 1
        mock_result.processing_time = 1.5
        
        mock_service.gen_process_chunk_async.return_value = mock_result
        
        # Create queue and enqueue task
        queue = TranscriptionQueue()
        task_id = queue.enqueue(task)
        
        # Set service on worker directly
        worker.audio_transcription_service = mock_service
        
        # Patch the global queue in the worker module
        with patch('services.transcription_worker.transcription_queue', queue):
            # Process the task
            await worker._process_task(task, "test-worker")
        
        # Check task was updated
        updated_task = queue.get_task(task_id)
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.result == "This is transcribed text"
        assert updated_task.completed_at is not None
        
        # Verify service was called correctly
        mock_service.gen_process_chunk_async.assert_called_once()
        call_args = mock_service.gen_process_chunk_async.call_args
        assert call_args[1]['session_id'] == "sess_test"
        assert call_args[1]['chunk_index'] == 0
    
    @pytest.mark.asyncio
    async def test_process_task_failure(self, worker, temp_audio_file, mock_service):
        """Test processing a task that fails"""
        # Create a task
        task = TranscriptionTask(
            session_id="sess_test",
            chunk_index=0,
            audio_file_path=str(temp_audio_file)
        )
        
        # Mock the service to raise an error
        mock_service.gen_process_chunk_async.side_effect = Exception("Processing failed")
        
        # Create queue and enqueue task
        queue = TranscriptionQueue()
        task_id = queue.enqueue(task)
        
        # Set service on worker directly
        worker.audio_transcription_service = mock_service
        
        # Patch the global queue in the worker module
        with patch('services.transcription_worker.transcription_queue', queue):
            # Process the task (should handle error)
            with pytest.raises(Exception):
                await worker._process_task(task, "test-worker")
        
        # Check task was marked as failed
        updated_task = queue.get_task(task_id)
        assert updated_task.status == TaskStatus.FAILED
        assert updated_task.error == "Processing failed"
        assert updated_task.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_process_task_cleanup_temp_file(self, worker, temp_audio_file, mock_service):
        """Test that temp file is cleaned up after processing"""
        # Create a task
        task = TranscriptionTask(
            session_id="sess_test",
            chunk_index=0,
            audio_file_path=str(temp_audio_file)
        )
        
        # Mock the service to return a successful result
        mock_result = Mock()
        mock_result.chunk_text = "Transcribed text"
        mock_result.session_id = "sess_test"
        mock_result.chunk_index = 0
        mock_result.accumulated_text = "Transcribed text"
        mock_result.chunks_processed = 1
        mock_result.processing_time = 1.0
        
        mock_service.gen_process_chunk_async.return_value = mock_result
        
        # Verify file exists before processing
        assert temp_audio_file.exists()
        
        # Set service on worker directly
        worker.audio_transcription_service = mock_service
        
        # Process the task
        await worker._process_task(task, "test-worker")
        
        # Verify file was deleted after processing
        assert not temp_audio_file.exists()
    
    @pytest.mark.asyncio
    async def test_worker_loop_handles_empty_queue(self, worker):
        """Test that worker loop handles empty queue gracefully"""
        # Start worker loop
        worker._running = True
        worker_task = asyncio.create_task(worker._worker_loop("test-worker"))
        
        # Let it run briefly with empty queue
        await asyncio.sleep(0.2)
        
        # Stop the worker
        worker._running = False
        await asyncio.sleep(0.1)
        
        # Cancel the worker task
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        
        # Should complete without errors
        assert True

