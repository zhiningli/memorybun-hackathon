"""
Unit tests for transcription queue infrastructure.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the transcription_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

import pytest
from services.transcription_queue import (
    TranscriptionQueue,
    TranscriptionTask,
    TaskStatus
)


class TestTranscriptionTask:
    """Tests for TranscriptionTask dataclass"""
    
    def test_task_creation_with_defaults(self):
        """Test creating a task with minimal required fields"""
        task = TranscriptionTask(
            session_id="sess_123",
            chunk_index=0,
            audio_file_path="/tmp/audio.webm"
        )
        
        assert task.session_id == "sess_123"
        assert task.chunk_index == 0
        assert task.audio_file_path == "/tmp/audio.webm"
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None
        assert isinstance(task.created_at, datetime)
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
        assert task.error is None
    
    def test_task_creation_with_custom_status(self):
        """Test creating a task with custom status"""
        task = TranscriptionTask(
            session_id="sess_123",
            chunk_index=0,
            audio_file_path="/tmp/audio.webm",
            status=TaskStatus.PROCESSING
        )
        
        assert task.status == TaskStatus.PROCESSING


class TestTranscriptionQueue:
    """Tests for TranscriptionQueue class"""
    
    @pytest.fixture
    def queue(self):
        """Create a fresh queue instance for each test"""
        return TranscriptionQueue()
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        return TranscriptionTask(
            session_id="sess_test",
            chunk_index=0,
            audio_file_path="/tmp/test.webm"
        )
    
    def test_enqueue_task(self, queue, sample_task):
        """Test enqueueing a task"""
        task_id = queue.enqueue(sample_task)
        
        assert task_id == "sess_test_chunk_0"
        assert queue.get_task(task_id) is not None
        assert queue.get_task(task_id).session_id == "sess_test"
        assert queue.get_task(task_id).chunk_index == 0
    
    def test_enqueue_multiple_tasks(self, queue):
        """Test enqueueing multiple tasks"""
        task1 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task2 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=1,
            audio_file_path="/tmp/2.webm"
        )
        task3 = TranscriptionTask(
            session_id="sess_2",
            chunk_index=0,
            audio_file_path="/tmp/3.webm"
        )
        
        id1 = queue.enqueue(task1)
        id2 = queue.enqueue(task2)
        id3 = queue.enqueue(task3)
        
        assert id1 == "sess_1_chunk_0"
        assert id2 == "sess_1_chunk_1"
        assert id3 == "sess_2_chunk_0"
        
        assert queue.get_task(id1) is not None
        assert queue.get_task(id2) is not None
        assert queue.get_task(id3) is not None
    
    def test_get_task_nonexistent(self, queue):
        """Test getting a non-existent task"""
        assert queue.get_task("nonexistent_task") is None
    
    def test_update_task_status_to_processing(self, queue, sample_task):
        """Test updating task status to processing"""
        task_id = queue.enqueue(sample_task)
        
        queue.update_task_status(task_id, TaskStatus.PROCESSING)
        
        task = queue.get_task(task_id)
        assert task.status == TaskStatus.PROCESSING
        assert task.started_at is not None
        assert isinstance(task.started_at, datetime)
    
    def test_update_task_status_to_completed(self, queue, sample_task):
        """Test updating task status to completed with result"""
        task_id = queue.enqueue(sample_task)
        
        queue.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result="This is the transcribed text"
        )
        
        task = queue.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "This is the transcribed text"
        assert task.completed_at is not None
        assert isinstance(task.completed_at, datetime)
    
    def test_update_task_status_to_failed(self, queue, sample_task):
        """Test updating task status to failed with error"""
        task_id = queue.enqueue(sample_task)
        
        queue.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error="Processing failed: file not found"
        )
        
        task = queue.get_task(task_id)
        assert task.status == TaskStatus.FAILED
        assert task.error == "Processing failed: file not found"
        assert task.completed_at is not None
    
    def test_get_tasks_for_session(self, queue):
        """Test getting all tasks for a specific session"""
        # Create tasks for two different sessions
        task1 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task2 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=1,
            audio_file_path="/tmp/2.webm"
        )
        task3 = TranscriptionTask(
            session_id="sess_2",
            chunk_index=0,
            audio_file_path="/tmp/3.webm"
        )
        
        queue.enqueue(task1)
        queue.enqueue(task2)
        queue.enqueue(task3)
        
        # Get tasks for sess_1
        sess_1_tasks = queue.get_tasks_for_session("sess_1")
        
        assert len(sess_1_tasks) == 2
        assert 0 in sess_1_tasks
        assert 1 in sess_1_tasks
        assert sess_1_tasks[0].session_id == "sess_1"
        assert sess_1_tasks[1].session_id == "sess_1"
        
        # Get tasks for sess_2
        sess_2_tasks = queue.get_tasks_for_session("sess_2")
        assert len(sess_2_tasks) == 1
        assert 0 in sess_2_tasks
        assert sess_2_tasks[0].session_id == "sess_2"
        
        # Get tasks for non-existent session
        sess_3_tasks = queue.get_tasks_for_session("sess_3")
        assert len(sess_3_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self, queue):
        """Test dequeueing from empty queue returns None after timeout"""
        task_id = await queue.dequeue()
        assert task_id is None
    
    @pytest.mark.asyncio
    async def test_dequeue_with_task(self, queue, sample_task):
        """Test dequeueing a task"""
        task_id = queue.enqueue(sample_task)
        
        # Dequeue should return the task_id
        dequeued_id = await queue.dequeue()
        
        assert dequeued_id == task_id
    
    @pytest.mark.asyncio
    async def test_dequeue_fifo_order(self, queue):
        """Test that tasks are dequeued in FIFO order"""
        task1 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task2 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=1,
            audio_file_path="/tmp/2.webm"
        )
        
        id1 = queue.enqueue(task1)
        id2 = queue.enqueue(task2)
        
        # Dequeue should return tasks in order
        dequeued_1 = await queue.dequeue()
        dequeued_2 = await queue.dequeue()
        
        assert dequeued_1 == id1
        assert dequeued_2 == id2
    
    def test_remove_task(self, queue, sample_task):
        """Test removing a task by task_id"""
        task_id = queue.enqueue(sample_task)
        
        assert queue.get_task(task_id) is not None
        
        # Remove the task
        result = queue.remove_task(task_id)
        
        assert result is True
        assert queue.get_task(task_id) is None
    
    def test_remove_task_nonexistent(self, queue):
        """Test removing a non-existent task returns False"""
        result = queue.remove_task("nonexistent_task")
        assert result is False
    
    def test_cleanup_completed_tasks(self, queue):
        """Test cleaning up old completed tasks"""
        # Create tasks with different completion times
        now = datetime.now()
        
        # Old completed task (2 hours ago)
        task1 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task_id1 = queue.enqueue(task1)
        queue.update_task_status(task_id1, TaskStatus.COMPLETED, result="text1")
        # Get task from queue and manually set completed_at to 2 hours ago
        stored_task1 = queue.get_task(task_id1)
        stored_task1.completed_at = now - timedelta(hours=2)
        
        # Recent completed task (30 minutes ago)
        task2 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=1,
            audio_file_path="/tmp/2.webm"
        )
        task_id2 = queue.enqueue(task2)
        queue.update_task_status(task_id2, TaskStatus.COMPLETED, result="text2")
        stored_task2 = queue.get_task(task_id2)
        stored_task2.completed_at = now - timedelta(minutes=30)
        
        # Pending task (should not be removed)
        task3 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=2,
            audio_file_path="/tmp/3.webm"
        )
        task_id3 = queue.enqueue(task3)
        
        # Clean up tasks older than 60 minutes
        removed_count = queue.cleanup_completed_tasks(older_than_minutes=60)
        
        assert removed_count == 1
        assert queue.get_task(task_id1) is None  # Old completed task removed
        assert queue.get_task(task_id2) is not None  # Recent completed task kept
        assert queue.get_task(task_id3) is not None  # Pending task kept
    
    def test_cleanup_failed_tasks(self, queue):
        """Test cleaning up old failed tasks"""
        now = datetime.now()
        
        # Old failed task (2 hours ago)
        task1 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task_id1 = queue.enqueue(task1)
        queue.update_task_status(task_id1, TaskStatus.FAILED, error="error1")
        stored_task1 = queue.get_task(task_id1)
        stored_task1.completed_at = now - timedelta(hours=2)
        
        # Recent failed task (30 minutes ago)
        task2 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=1,
            audio_file_path="/tmp/2.webm"
        )
        task_id2 = queue.enqueue(task2)
        queue.update_task_status(task_id2, TaskStatus.FAILED, error="error2")
        stored_task2 = queue.get_task(task_id2)
        stored_task2.completed_at = now - timedelta(minutes=30)
        
        # Processing task (should not be removed)
        task3 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=2,
            audio_file_path="/tmp/3.webm"
        )
        task_id3 = queue.enqueue(task3)
        queue.update_task_status(task_id3, TaskStatus.PROCESSING)
        
        # Clean up tasks older than 60 minutes
        removed_count = queue.cleanup_failed_tasks(older_than_minutes=60)
        
        assert removed_count == 1
        assert queue.get_task(task_id1) is None  # Old failed task removed
        assert queue.get_task(task_id2) is not None  # Recent failed task kept
        assert queue.get_task(task_id3) is not None  # Processing task kept
    
    def test_cleanup_old_tasks(self, queue):
        """Test cleaning up both completed and failed old tasks"""
        now = datetime.now()
        
        # Old completed task
        task1 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task_id1 = queue.enqueue(task1)
        queue.update_task_status(task_id1, TaskStatus.COMPLETED, result="text1")
        stored_task1 = queue.get_task(task_id1)
        stored_task1.completed_at = now - timedelta(hours=2)
        
        # Old failed task
        task2 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=1,
            audio_file_path="/tmp/2.webm"
        )
        task_id2 = queue.enqueue(task2)
        queue.update_task_status(task_id2, TaskStatus.FAILED, error="error1")
        stored_task2 = queue.get_task(task_id2)
        stored_task2.completed_at = now - timedelta(hours=2)
        
        # Recent completed task
        task3 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=2,
            audio_file_path="/tmp/3.webm"
        )
        task_id3 = queue.enqueue(task3)
        queue.update_task_status(task_id3, TaskStatus.COMPLETED, result="text2")
        stored_task3 = queue.get_task(task_id3)
        stored_task3.completed_at = now - timedelta(minutes=30)
        
        # Clean up tasks older than 60 minutes
        removed_count = queue.cleanup_old_tasks(older_than_minutes=60)
        
        assert removed_count == 2
        assert queue.get_task(task_id1) is None  # Old completed removed
        assert queue.get_task(task_id2) is None  # Old failed removed
        assert queue.get_task(task_id3) is not None  # Recent completed kept
    
    def test_cleanup_tasks_for_session(self, queue):
        """Test cleaning up all tasks for a specific session"""
        # Create tasks for two sessions
        task1 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task2 = TranscriptionTask(
            session_id="sess_1",
            chunk_index=1,
            audio_file_path="/tmp/2.webm"
        )
        task3 = TranscriptionTask(
            session_id="sess_2",
            chunk_index=0,
            audio_file_path="/tmp/3.webm"
        )
        
        task_id1 = queue.enqueue(task1)
        task_id2 = queue.enqueue(task2)
        task_id3 = queue.enqueue(task3)
        
        # Mark tasks with different statuses
        queue.update_task_status(task_id1, TaskStatus.COMPLETED, result="text1")
        queue.update_task_status(task_id2, TaskStatus.FAILED, error="error1")
        queue.update_task_status(task_id3, TaskStatus.PROCESSING)
        
        # Clean up tasks for sess_1
        removed_count = queue.cleanup_tasks_for_session("sess_1")
        
        assert removed_count == 2
        assert queue.get_task(task_id1) is None  # sess_1 task removed
        assert queue.get_task(task_id2) is None  # sess_1 task removed
        assert queue.get_task(task_id3) is not None  # sess_2 task kept
    
    def test_cleanup_tasks_for_session_nonexistent(self, queue):
        """Test cleaning up tasks for non-existent session returns 0"""
        removed_count = queue.cleanup_tasks_for_session("nonexistent_session")
        assert removed_count == 0
    
    def test_cleanup_completed_tasks_no_completed_at(self, queue):
        """Test that completed tasks without completed_at are not removed"""
        task = TranscriptionTask(
            session_id="sess_1",
            chunk_index=0,
            audio_file_path="/tmp/1.webm"
        )
        task_id = queue.enqueue(task)
        queue.update_task_status(task_id, TaskStatus.COMPLETED, result="text1")
        # Get task from queue and manually set completed_at to None (edge case)
        stored_task = queue.get_task(task_id)
        stored_task.completed_at = None
        
        removed_count = queue.cleanup_completed_tasks(older_than_minutes=0)
        
        assert removed_count == 0
        assert queue.get_task(task_id) is not None

