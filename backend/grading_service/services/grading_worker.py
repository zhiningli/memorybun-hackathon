"""
Grading Worker - Background worker that processes grading tasks from queue.

Runs event loop, dequeues GradingTask from Redis, and executes the
Orchestrator pipeline to grade student submissions.

Features:
- Configurable worker pool
- Retry with exponential backoff
- Dead-letter queue for permanently failed tasks
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any

from services.redis_client import get_redis_client
from services.result_store import result_store
from services.grading_queue import grading_queue, GRADING_QUEUE_KEY
from pipeline.orchestrator import Orchestrator
from pipeline.task_decode_stage import TaskDecodeError
from pipeline.validate_stage import ValidationError
from middleware.request_id import set_request_id

logger = logging.getLogger(__name__)

# Queue configuration
DEQUEUE_TIMEOUT_SECONDS = 5


class GradingWorker:
    """
    Worker that processes grading tasks from Redis queue.
    
    Uses configurable worker pool. Each worker:
    1. Dequeues task from Redis (blocking)
    2. Runs Orchestrator pipeline
    3. Handles errors with retry logic
    4. Moves to DLQ after max retries
    """
    
    def __init__(self, num_workers: int = 2, orchestrator: Orchestrator = None):
        """
        Initialize grading worker pool.
        
        Args:
            num_workers: Number of concurrent worker tasks
            orchestrator: Optional custom orchestrator (for testing)
        """
        self.num_workers = num_workers
        self._orchestrator = orchestrator or Orchestrator()
        self._running = False
        self._workers: list[asyncio.Task] = []
    
    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            logger.warning("Grading workers already running")
            return
        
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(f"grading-worker-{i}"))
            for i in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} grading workers")
    
    async def stop(self) -> None:
        """Stop the worker pool gracefully."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping grading workers...")
        
        if self._workers:
            # Cancel all worker tasks
            for worker_task in self._workers:
                if not worker_task.done():
                    worker_task.cancel()
            
            # Wait for workers to finish (with timeout)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some grading workers did not stop within timeout")
            except asyncio.CancelledError:
                pass  # Expected during shutdown
            
            self._workers = []
        
        logger.info("Grading workers stopped")
    
    async def _worker_loop(self, worker_name: str) -> None:
        """
        Main worker loop - continuously dequeues and processes tasks.
        
        Args:
            worker_name: Name identifier for logging
        """
        logger.info(f"[{worker_name}] Worker started")
        
        while self._running:
            try:
                # Dequeue task from Redis (blocking with timeout)
                task = await grading_queue.dequeue(timeout=DEQUEUE_TIMEOUT_SECONDS)
                
                if task is None:
                    # Queue empty, continue polling
                    continue
                
                # Restore correlation ID from the original request
                correlation_id = task.get("correlation_id")
                if correlation_id:
                    set_request_id(correlation_id)
                else:
                    # Generate a new one if not present (for legacy tasks)
                    set_request_id()
                
                session_id = task.get("session_id", "unknown")
                retry_count = task.get("retry_count", 0)
                
                logger.info(
                    f"[{worker_name}] Dequeued task for session {session_id} "
                    f"(attempt {retry_count + 1})"
                )
                
                # Process the task through orchestrator
                success = await self._process_task(task, worker_name)
                
                if not success:
                    # Task failed, attempt retry
                    await self._handle_retry(task, worker_name)
                
            except asyncio.CancelledError:
                logger.info(f"[{worker_name}] Worker cancelled, stopping...")
                break
            except Exception as e:
                logger.error(f"[{worker_name}] Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before retrying
        
        logger.info(f"[{worker_name}] Worker stopped")
    
    async def _process_task(self, task: Dict[str, Any], worker_name: str) -> bool:
        """
        Process a single grading task through the orchestrator.
        
        Args:
            task: Task dict with session_id, transcription_text, etc.
            worker_name: Worker identifier for logging
            
        Returns:
            True if processing succeeded, False if failed
        """
        session_id = task.get("session_id", "unknown")
        
        try:
            logger.info(f"[{worker_name}] Processing session {session_id}")
            
            # Update status to processing
            await result_store.set_status(
                session_id=session_id,
                status="processing",
                message="Grading in progress"
            )
            
            # Run the orchestrator pipeline
            final_state = await self._orchestrator.run_pipeline(task)
            
            # Update status to completed
            await result_store.set_status(
                session_id=session_id,
                status="completed",
                message="Grading completed"
            )
            
            logger.info(
                f"[{worker_name}] Completed session {session_id}: "
                f"score={final_state.result.get('score', 'N/A') if final_state.result else 'N/A'}"
            )
            return True
            
        except TaskDecodeError as e:
            logger.error(f"[{worker_name}] Task decode failed for {session_id}: {e}")
            # Non-retryable error - move directly to DLQ
            await grading_queue.move_to_dlq(task, "Task decode error", str(e))
            await self._update_failure_status(session_id, f"Invalid task data: {e}")
            return True  # Don't retry decode errors
            
        except ValidationError as e:
            logger.error(f"[{worker_name}] Validation failed for {session_id}: {e}")
            task["last_error"] = f"Validation error: {e}"
            return False  # Retry validation errors
            
        except Exception as e:
            logger.error(f"[{worker_name}] Processing failed for {session_id}: {e}", exc_info=True)
            task["last_error"] = f"Processing error: {e}"
            return False  # Retry other errors
    
    async def _handle_retry(self, task: Dict[str, Any], worker_name: str) -> None:
        """
        Handle task retry with exponential backoff.
        
        Args:
            task: Failed task
            worker_name: Worker identifier for logging
        """
        session_id = task.get("session_id", "unknown")
        retry_count = task.get("retry_count", 0)
        max_retries = task.get("max_retries", 3)
        
        if retry_count >= max_retries:
            # Max retries exceeded - move to DLQ
            logger.warning(
                f"[{worker_name}] Task {session_id} exceeded max retries ({max_retries})"
            )
            await grading_queue.move_to_dlq(
                task, 
                "Max retries exceeded",
                task.get("last_error")
            )
            await self._update_failure_status(
                session_id, 
                f"Grading failed after {max_retries} attempts"
            )
        else:
            # Requeue with backoff
            await grading_queue.requeue_with_backoff(task)
            
            # Update status to show retry pending
            await result_store.set_status(
                session_id=session_id,
                status="retrying",
                message=f"Retry {retry_count + 1}/{max_retries} pending"
            )
    
    async def _update_failure_status(self, session_id: str, error_message: str) -> None:
        """
        Update status to failed.
        
        Args:
            session_id: Session identifier
            error_message: Error description
        """
        try:
            await result_store.set_status(
                session_id=session_id,
                status="failed",
                message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to update failure status for {session_id}: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if workers are running."""
        return self._running


# Global worker instance
# Using 2 workers for parallelism (can be configured)
grading_worker = GradingWorker(num_workers=2)


async def start_grading_worker() -> None:
    """Start the global grading worker (call during app startup)."""
    await grading_worker.start()


async def stop_grading_worker() -> None:
    """Stop the global grading worker (call during app shutdown)."""
    await grading_worker.stop()

