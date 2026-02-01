"""
Summary Queue Service - Redis queue for summary tasks.

Manages summary task queue in Redis with:
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
SUMMARY_QUEUE_KEY = "summary:queue"
SUMMARY_DLQ_KEY = "summary:dead-letter"

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1


class SummaryQueue:
    """
    Manages summary task queue with retry and dead-letter support.
    
    Features:
    - FIFO queue using Redis List
    - Retry tracking with exponential backoff
    - Dead-letter queue for permanently failed tasks
    """
    
    def __init__(self):
        """Initialize summary queue."""
        self.queue_key = SUMMARY_QUEUE_KEY
        self.dlq_key = SUMMARY_DLQ_KEY
        self.max_retries = MAX_RETRIES
        self.backoff_base = BACKOFF_BASE_SECONDS
    
    async def enqueue(self, task: Dict[str, Any]) -> bool:
        """
        Enqueue a summary task.
        
        Args:
            task: Task dict with summary_id, question_id, session_ids, etc.
            
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
            
            logger.info(f"Enqueued summary task {task.get('summary_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue summary task: {e}")
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
                return None
            
            _, task_json = result
            task = json.loads(task_json)
            
            logger.debug(f"Dequeued summary task {task.get('summary_id')}")
            return task
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse summary task JSON: {e}")
            return None
        except (RedisTimeoutError, asyncio.TimeoutError, TimeoutError):
            return None
        except Exception as e:
            logger.warning(f"Summary dequeue error (will retry): {e}")
            return None
    
    async def requeue_with_backoff(self, task: Dict[str, Any]) -> bool:
        """
        Requeue a failed task with incremented retry count.
        
        Args:
            task: Failed task dict
            
        Returns:
            True if requeued, False if max retries exceeded
        """
        retry_count = task.get("retry_count", 0)
        max_retries = task.get("max_retries", self.max_retries)
        
        if retry_count >= max_retries:
            logger.warning(
                f"Summary task {task.get('summary_id')} exceeded max retries ({max_retries})"
            )
            return await self.move_to_dlq(task, "Max retries exceeded")
        
        task["retry_count"] = retry_count + 1
        task["last_retry_at"] = datetime.now(timezone.utc).isoformat()
        
        delay_seconds = self.backoff_base * (2 ** retry_count)
        
        logger.info(
            f"Requeueing summary task {task.get('summary_id')} "
            f"(retry {task['retry_count']}/{max_retries}) "
            f"with {delay_seconds}s backoff"
        )
        
        import asyncio
        await asyncio.sleep(delay_seconds)
        
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
                f"Moved summary task {task.get('summary_id')} to dead-letter queue: {error_reason}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to move summary task to DLQ: {e}")
            return False
    
    async def get_queue_length(self) -> int:
        """Get number of tasks in main queue."""
        try:
            client = get_redis_client().get_client()
            return await client.llen(self.queue_key)
        except Exception as e:
            logger.error(f"Failed to get summary queue length: {e}")
            return 0
    
    async def get_dlq_length(self) -> int:
        """Get number of tasks in dead-letter queue."""
        try:
            client = get_redis_client().get_client()
            return await client.llen(self.dlq_key)
        except Exception as e:
            logger.error(f"Failed to get summary DLQ length: {e}")
            return 0


# Global queue instance
summary_queue = SummaryQueue()
