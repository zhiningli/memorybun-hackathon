"""
Simple in-memory queue for transcription tasks.
Will be replaced with Redis in Phase 2.

This queue manages transcription tasks that are processed by background workers.
"""
import asyncio
import queue
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of a transcription task"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TranscriptionTask:
    """Represents a single transcription task"""
    session_id: str
    chunk_index: int
    audio_file_path: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        """Set created_at if not provided"""
        if self.created_at is None:
            self.created_at = datetime.now()


class TranscriptionQueue:
    """
    Simple in-memory queue for transcription tasks.
    
    Uses a thread-safe queue.Queue for task IDs (works across event loops),
    and stores task data in a dict for thread-safe access.
    """
    
    def __init__(self):
        # Use thread-safe queue.Queue instead of asyncio.Queue
        # This allows enqueue from any thread/loop and dequeue from worker's loop
        self._queue: queue.Queue = queue.Queue()
        self._tasks: Dict[str, TranscriptionTask] = {}  # task_id -> task
    
    def enqueue(self, task: TranscriptionTask) -> str:
        """
        Add task to queue, return task_id.
        
        Args:
            task: TranscriptionTask to enqueue
            
        Returns:
            task_id: Unique identifier for this task
        """
        task_id = f"{task.session_id}_chunk_{task.chunk_index}"
        task.created_at = datetime.now()
        self._tasks[task_id] = task
        self._queue.put_nowait(task_id)
        logger.info(f"Enqueued task {task_id} for session {task.session_id}, chunk {task.chunk_index}")
        return task_id
    
    async def dequeue(self) -> Optional[str]:
        """
        Get next task_id from queue.
        
        Returns:
            task_id if available, None if queue is empty (after timeout)
        """
        def _get_from_queue():
            """Helper function to get from queue in executor"""
            try:
                return self._queue.get(block=True, timeout=1.0)
            except queue.Empty:
                return None
        
        try:
            # Use run_in_executor to wait on thread-safe queue in async context
            # queue.Queue.get(block=True, timeout=1.0) blocks for up to 1 second
            loop = asyncio.get_event_loop()
            task_id = await loop.run_in_executor(None, _get_from_queue)
            return task_id
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Error in dequeue: {e}")
            return None
    
    def get_task(self, task_id: str) -> Optional[TranscriptionTask]:
        """
        Get task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TranscriptionTask if found, None otherwise
        """
        return self._tasks.get(task_id)
    
    def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus, 
        result: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Update task status and optional fields.
        
        Args:
            task_id: Task identifier
            status: New status
            result: Transcription result (if completed)
            error: Error message (if failed)
        """
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = status
            
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
                
            if status == TaskStatus.PROCESSING:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.now()
    
    def get_tasks_for_session(self, session_id: str) -> Dict[int, TranscriptionTask]:
        """
        Get all tasks for a session, indexed by chunk_index.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict mapping chunk_index to TranscriptionTask
        """
        result = {}
        for task_id, task in self._tasks.items():
            if task.session_id == session_id:
                result[task.chunk_index] = task
        return result
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a task from the queue by task_id.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was removed, False if not found
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"Removed task {task_id} from queue")
            return True
        return False
    
    def cleanup_completed_tasks(self, older_than_minutes: int = 60) -> int:
        """
        Remove completed tasks that are older than specified time.
        
        Args:
            older_than_minutes: Remove tasks completed more than this many minutes ago
            
        Returns:
            Number of tasks removed
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=older_than_minutes)
        removed_count = 0
        task_ids_to_remove = []
        
        for task_id, task in self._tasks.items():
            if task.status == TaskStatus.COMPLETED:
                if task.completed_at and task.completed_at < cutoff_time:
                    task_ids_to_remove.append(task_id)
        
        for task_id in task_ids_to_remove:
            del self._tasks[task_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} completed tasks older than {older_than_minutes} minutes")
        
        return removed_count
    
    def cleanup_failed_tasks(self, older_than_minutes: int = 60) -> int:
        """
        Remove failed tasks that are older than specified time.
        
        Args:
            older_than_minutes: Remove tasks failed more than this many minutes ago
            
        Returns:
            Number of tasks removed
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=older_than_minutes)
        removed_count = 0
        task_ids_to_remove = []
        
        for task_id, task in self._tasks.items():
            if task.status == TaskStatus.FAILED:
                if task.completed_at and task.completed_at < cutoff_time:
                    task_ids_to_remove.append(task_id)
        
        for task_id in task_ids_to_remove:
            del self._tasks[task_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} failed tasks older than {older_than_minutes} minutes")
        
        return removed_count
    
    def cleanup_old_tasks(self, older_than_minutes: int = 60) -> int:
        """
        Remove all completed and failed tasks that are older than specified time.
        
        Args:
            older_than_minutes: Remove tasks completed/failed more than this many minutes ago
            
        Returns:
            Number of tasks removed
        """
        completed_count = self.cleanup_completed_tasks(older_than_minutes)
        failed_count = self.cleanup_failed_tasks(older_than_minutes)
        return completed_count + failed_count
    
    def cleanup_tasks_for_session(self, session_id: str) -> int:
        """
        Remove all tasks for a specific session.
        Useful when a session is deleted or finalized.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of tasks removed
        """
        removed_count = 0
        task_ids_to_remove = []
        
        for task_id, task in self._tasks.items():
            if task.session_id == session_id:
                task_ids_to_remove.append(task_id)
        
        for task_id in task_ids_to_remove:
            del self._tasks[task_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} tasks for session {session_id}")
        
        return removed_count


# Global queue instance
transcription_queue = TranscriptionQueue()

