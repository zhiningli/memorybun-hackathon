"""
Redis Grading Queue Service - Manages grading task queue in Redis.

Uses Redis List as a queue:
- LPUSH to enqueue tasks (add to left/head)
- BRPOP to dequeue tasks (blocking pop from right/tail)
- Tasks are serialized as JSON

Queue Key: grading:queue
"""

import json
import logging
from typing import Optional
from datetime import datetime
from services.redis_client import get_redis_client
from schemas.grading import GradingTask

logger = logging.getLogger(__name__)


class RedisGradingQueue:
    """
    Service for managing grading tasks in Redis queue.
    
    Uses Redis List (FIFO queue) with blocking operations.
    """
    
    def __init__(self):
        """Initialize the grading queue service"""
        self.queue_key = "grading:queue"
    
    async def enqueue_grading_task(self, task: GradingTask) -> bool:
        """
        Enqueue a grading task to Redis queue.
        
        Args:
            task: GradingTask to enqueue
            
        Returns:
            True if enqueued successfully, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            
            # Serialize task to JSON
            task_json = task.model_dump_json()
            
            # Enqueue using LPUSH (add to left/head of list)
            await client.lpush(self.queue_key, task_json)
            
            logger.info(f"Enqueued grading task for session {task.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue grading task: {e}")
            return False
    
    async def dequeue_grading_task(self, timeout: int = 5) -> Optional[GradingTask]:
        """
        Dequeue a grading task from Redis queue (blocking).
        
        Args:
            timeout: Maximum seconds to wait for a task (0 = wait indefinitely)
            
        Returns:
            GradingTask if available, None if timeout or error
        """
        try:
            client = get_redis_client().get_client()
            
            # Use BRPOP (blocking right pop) - waits for task if queue is empty
            # Returns tuple: (list_name, value) or None if timeout
            result = await client.brpop(self.queue_key, timeout=timeout)
            
            if result is None:
                # Timeout - no task available
                return None
            
            # result is (queue_key, task_json)
            _, task_json = result
            
            # Deserialize JSON to GradingTask
            task_dict = json.loads(task_json)
            
            # Convert datetime strings back to datetime objects
            if "created_at" in task_dict and isinstance(task_dict["created_at"], str):
                task_dict["created_at"] = datetime.fromisoformat(task_dict["created_at"].replace("Z", "+00:00"))
            
            task = GradingTask(**task_dict)
            
            logger.info(f"Dequeued grading task for session {task.session_id}")
            return task
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize grading task: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue grading task: {e}")
            return None
    
    async def get_queue_length(self) -> int:
        """
        Get the current length of the grading queue.
        
        Returns:
            Number of tasks in queue, 0 if error
        """
        try:
            client = get_redis_client().get_client()
            length = await client.llen(self.queue_key)
            return length
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def peek_queue(self) -> Optional[GradingTask]:
        """
        Peek at the next task in queue without removing it (for debugging).
        
        Returns:
            GradingTask if available, None if queue is empty or error
        """
        try:
            client = get_redis_client().get_client()
            
            # Use LINDEX to get last element (right side, where BRPOP would get from)
            task_json = await client.lindex(self.queue_key, -1)
            
            if task_json is None:
                return None
            
            # Deserialize
            task_dict = json.loads(task_json)
            
            # Convert datetime strings back to datetime objects
            if "created_at" in task_dict and isinstance(task_dict["created_at"], str):
                task_dict["created_at"] = datetime.fromisoformat(task_dict["created_at"].replace("Z", "+00:00"))
            
            task = GradingTask(**task_dict)
            return task
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize grading task: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to peek queue: {e}")
            return None
    
    async def clear_queue(self) -> int:
        """
        Clear all tasks from the queue (for testing/cleanup).
        
        Returns:
            Number of tasks removed
        """
        try:
            client = get_redis_client().get_client()
            length = await client.llen(self.queue_key)
            await client.delete(self.queue_key)
            logger.info(f"Cleared {length} tasks from grading queue")
            return length
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return 0


# Global queue instance
redis_grading_queue = RedisGradingQueue()

