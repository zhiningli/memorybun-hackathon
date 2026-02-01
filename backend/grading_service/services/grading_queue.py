"""
Grading Queue Service - Redis queue with retry and dead-letter support.

Manages grading task queue in Redis with:
- Task enqueueing/dequeueing
- Retry logic with exponential backoff
- Dead-letter queue for failed tasks
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from services.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Queue keys
GRADING_QUEUE_KEY = "grading:queue"
DEAD_LETTER_QUEUE_KEY = "grading:dead-letter"

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1  # 1s, 2s, 4s, 8s exponential

# DLQ TTL (30 days in seconds)
DLQ_TTL_SECONDS = 30 * 24 * 60 * 60


class GradingQueue:
    """
    Manages grading task queue with retry and dead-letter support.
    
    Features:
    - FIFO queue using Redis List
    - Retry tracking with exponential backoff
    - Dead-letter queue for permanently failed tasks
    """
    
    def __init__(self):
        """Initialize grading queue."""
        self.queue_key = GRADING_QUEUE_KEY
        self.dlq_key = DEAD_LETTER_QUEUE_KEY
        self.max_retries = MAX_RETRIES
        self.backoff_base = BACKOFF_BASE_SECONDS
    
    async def enqueue(self, task: Dict[str, Any]) -> bool:
        """
        Enqueue a grading task.
        
        Args:
            task: Task dict with session_id, transcription_text, etc.
            
        Returns:
            True if enqueued successfully
        """
        try:
            client = get_redis_client().get_client()
            
            # Initialize retry fields if not present
            if "retry_count" not in task:
                task["retry_count"] = 0
            if "max_retries" not in task:
                task["max_retries"] = self.max_retries
            if "created_at" not in task:
                task["created_at"] = datetime.now(timezone.utc).isoformat()
            
            task_json = json.dumps(task)
            await client.lpush(self.queue_key, task_json)
            
            logger.info(f"Enqueued grading task for session {task.get('session_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            return False
    
    async def dequeue(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Dequeue a task from the queue (blocking).
        
        Args:
            timeout: Max seconds to wait
            
        Returns:
            Task dict or None if timeout
        """
        import asyncio
        from redis.exceptions import TimeoutError as RedisTimeoutError
        
        try:
            client = get_redis_client().get_client()
            
            result = await client.brpop(self.queue_key, timeout=timeout)
            
            if result is None:
                # Queue empty, timeout reached - this is normal
                return None
            
            _, task_json = result
            task = json.loads(task_json)
            
            logger.debug(f"Dequeued task for session {task.get('session_id')}")
            return task
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task JSON: {e}")
            return None
        except (RedisTimeoutError, asyncio.TimeoutError, TimeoutError):
            # Timeout waiting for task - this is expected when queue is empty
            # Don't log as error, just return None
            return None
        except Exception as e:
            # Only log unexpected errors
            logger.warning(f"Dequeue error (will retry): {e}")
            return None
    
    async def requeue_with_backoff(self, task: Dict[str, Any]) -> bool:
        """
        Requeue a failed task with incremented retry count.
        
        Uses exponential backoff delay before the task becomes visible.
        
        Args:
            task: Failed task dict
            
        Returns:
            True if requeued, False if max retries exceeded
        """
        retry_count = task.get("retry_count", 0)
        max_retries = task.get("max_retries", self.max_retries)
        
        if retry_count >= max_retries:
            logger.warning(
                f"Task {task.get('session_id')} exceeded max retries ({max_retries}), "
                "moving to dead-letter queue"
            )
            return await self.move_to_dlq(task, "Max retries exceeded")
        
        # Increment retry count
        task["retry_count"] = retry_count + 1
        task["last_retry_at"] = datetime.now(timezone.utc).isoformat()
        
        # Calculate backoff delay
        delay_seconds = self.backoff_base * (2 ** retry_count)
        
        logger.info(
            f"Requeueing task {task.get('session_id')} "
            f"(retry {task['retry_count']}/{max_retries}) "
            f"with {delay_seconds}s backoff"
        )
        
        # Wait for backoff period
        import asyncio
        await asyncio.sleep(delay_seconds)
        
        # Requeue
        return await self.enqueue(task)
    
    async def move_to_dlq(
        self,
        task: Dict[str, Any],
        error_reason: str,
        error_details: Optional[str] = None
    ) -> bool:
        """
        Move a task to the dead-letter queue.
        
        Args:
            task: Failed task
            error_reason: Why the task failed
            error_details: Detailed error info
            
        Returns:
            True if moved successfully
        """
        try:
            client = get_redis_client().get_client()
            
            # Add DLQ metadata
            dlq_entry = {
                "original_task": task,
                "error_reason": error_reason,
                "error_details": error_details,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "retry_count": task.get("retry_count", 0)
            }
            
            dlq_json = json.dumps(dlq_entry)
            await client.lpush(self.dlq_key, dlq_json)
            
            logger.warning(
                f"Moved task {task.get('session_id')} to dead-letter queue: {error_reason}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to move task to DLQ: {e}")
            return False
    
    async def get_queue_length(self) -> int:
        """Get number of tasks in main queue."""
        try:
            client = get_redis_client().get_client()
            return await client.llen(self.queue_key)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def get_dlq_length(self) -> int:
        """Get number of tasks in dead-letter queue."""
        try:
            client = get_redis_client().get_client()
            return await client.llen(self.dlq_key)
        except Exception as e:
            logger.error(f"Failed to get DLQ length: {e}")
            return 0
    
    async def get_dlq_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get tasks from dead-letter queue (for admin review).
        
        Args:
            limit: Max number of tasks to return
            
        Returns:
            List of DLQ entries
        """
        try:
            client = get_redis_client().get_client()
            
            # Get tasks from right side (oldest first)
            tasks_json = await client.lrange(self.dlq_key, -limit, -1)
            
            tasks = []
            for task_json in tasks_json:
                try:
                    tasks.append(json.loads(task_json))
                except json.JSONDecodeError:
                    continue
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get DLQ tasks: {e}")
            return []
    
    async def requeue_from_dlq(self, session_id: str) -> bool:
        """
        Requeue a task from dead-letter queue (admin action).
        
        Args:
            session_id: Session ID of task to requeue
            
        Returns:
            True if found and requeued
        """
        try:
            client = get_redis_client().get_client()
            
            # Get all DLQ tasks
            all_tasks = await client.lrange(self.dlq_key, 0, -1)
            
            for task_json in all_tasks:
                try:
                    dlq_entry = json.loads(task_json)
                    original_task = dlq_entry.get("original_task", {})
                    
                    if original_task.get("session_id") == session_id:
                        # Remove from DLQ
                        await client.lrem(self.dlq_key, 1, task_json)
                        
                        # Reset retry count and requeue
                        original_task["retry_count"] = 0
                        original_task["requeued_from_dlq_at"] = datetime.now(timezone.utc).isoformat()
                        
                        await self.enqueue(original_task)
                        
                        logger.info(f"Requeued task {session_id} from DLQ")
                        return True
                        
                except json.JSONDecodeError:
                    continue
            
            logger.warning(f"Task {session_id} not found in DLQ")
            return False
            
        except Exception as e:
            logger.error(f"Failed to requeue from DLQ: {e}")
            return False
    
    async def clear_dlq(self) -> int:
        """
        Clear all tasks from dead-letter queue (admin action).
        
        Returns:
            Number of tasks cleared
        """
        try:
            client = get_redis_client().get_client()
            length = await client.llen(self.dlq_key)
            await client.delete(self.dlq_key)
            logger.info(f"Cleared {length} tasks from DLQ")
            return length
        except Exception as e:
            logger.error(f"Failed to clear DLQ: {e}")
            return 0


# Global queue instance
grading_queue = GradingQueue()
