"""
Summary Worker - Background worker that processes summary tasks from queue.

Runs event loop, dequeues SummaryTask from Redis, and executes the
SummaryOrchestrator pipeline to generate summary reports.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from services.redis_client import get_redis_client
from services.result_store import result_store
from services.summary_queue import summary_queue
from pipeline.summary.summary_orchestrator import SummaryOrchestrator
from pipeline.summary.summary_validate_stage import SummaryValidationError
from middleware.request_id import set_request_id

logger = logging.getLogger(__name__)

DEQUEUE_TIMEOUT_SECONDS = 5


class SummaryWorker:
    """
    Worker that processes summary tasks from Redis queue.
    
    Each worker:
    1. Dequeues task from summary:queue (blocking)
    2. Runs SummaryOrchestrator pipeline
    3. Handles errors with retry logic
    4. Moves to DLQ after max retries
    """
    
    def __init__(self, num_workers: int = 1, orchestrator: SummaryOrchestrator = None):
        """
        Initialize summary worker pool.
        
        Args:
            num_workers: Number of concurrent worker tasks
            orchestrator: Optional custom orchestrator (for testing)
        """
        self.num_workers = num_workers
        self._orchestrator = orchestrator or SummaryOrchestrator()
        self._running = False
        self._workers: list[asyncio.Task] = []
    
    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            logger.warning("Summary workers already running")
            return
        
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(f"summary-worker-{i}"))
            for i in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} summary workers")
    
    async def stop(self) -> None:
        """Stop the worker pool gracefully."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping summary workers...")
        
        if self._workers:
            for worker_task in self._workers:
                if not worker_task.done():
                    worker_task.cancel()
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some summary workers did not stop within timeout")
            except asyncio.CancelledError:
                pass
            
            self._workers = []
        
        logger.info("Summary workers stopped")
    
    async def _worker_loop(self, worker_name: str) -> None:
        """
        Main worker loop - continuously dequeues and processes tasks.
        
        Args:
            worker_name: Name identifier for logging
        """
        logger.info(f"[{worker_name}] Worker started")
        
        while self._running:
            try:
                task = await summary_queue.dequeue(timeout=DEQUEUE_TIMEOUT_SECONDS)
                
                if task is None:
                    continue
                
                # Restore correlation ID from the original request
                correlation_id = task.get("correlation_id")
                if correlation_id:
                    set_request_id(correlation_id)
                else:
                    # Generate a new one if not present (for legacy tasks)
                    set_request_id()
                
                summary_id = task.get("summary_id", "unknown")
                retry_count = task.get("retry_count", 0)
                
                logger.info(
                    f"[{worker_name}] Dequeued summary task {summary_id} "
                    f"(attempt {retry_count + 1})"
                )
                
                success = await self._process_task(task, worker_name)
                
                if not success:
                    await self._handle_retry(task, worker_name)
                
            except asyncio.CancelledError:
                logger.info(f"[{worker_name}] Worker cancelled, stopping...")
                break
            except Exception as e:
                logger.error(f"[{worker_name}] Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"[{worker_name}] Worker stopped")
    
    async def _process_task(self, task: Dict[str, Any], worker_name: str) -> bool:
        """
        Process a single summary task through the orchestrator.
        
        Args:
            task: Task dict with summary_id, session_ids
            worker_name: Worker identifier for logging
            
        Returns:
            True if processing succeeded, False if failed
        """
        summary_id = task.get("summary_id", "unknown")
        
        try:
            logger.info(f"[{worker_name}] Processing summary {summary_id}")
            
            # Update status to processing
            await result_store.set_summary_status(
                summary_id=summary_id,
                status="processing",
                message="Generating summary"
            )
            
            # Run the orchestrator pipeline
            final_state = await self._orchestrator.run_pipeline(task)
            
            logger.info(
                f"[{worker_name}] Completed summary {summary_id}: "
                f"score={final_state.result.get('overall_score', 'N/A') if final_state.result else 'N/A'}"
            )
            return True
            
        except ValueError as e:
            # Missing data errors - likely non-retryable
            logger.error(f"[{worker_name}] Data error for {summary_id}: {e}")
            await summary_queue.move_to_dlq(task, "Data validation error", str(e))
            await self._update_failure_status(summary_id, f"Invalid data: {e}")
            return True  # Don't retry
            
        except SummaryValidationError as e:
            logger.error(f"[{worker_name}] Validation failed for {summary_id}: {e}")
            task["last_error"] = f"Validation error: {e}"
            return False  # Retry
            
        except Exception as e:
            logger.error(f"[{worker_name}] Processing failed for {summary_id}: {e}", exc_info=True)
            task["last_error"] = f"Processing error: {e}"
            return False
    
    async def _handle_retry(self, task: Dict[str, Any], worker_name: str) -> None:
        """Handle task retry with exponential backoff."""
        summary_id = task.get("summary_id", "unknown")
        retry_count = task.get("retry_count", 0)
        max_retries = task.get("max_retries", 3)
        
        if retry_count >= max_retries:
            logger.warning(
                f"[{worker_name}] Task {summary_id} exceeded max retries ({max_retries})"
            )
            await summary_queue.move_to_dlq(
                task, 
                "Max retries exceeded",
                task.get("last_error")
            )
            await self._update_failure_status(
                summary_id, 
                f"Summary failed after {max_retries} attempts"
            )
        else:
            await summary_queue.requeue_with_backoff(task)
            
            await result_store.set_summary_status(
                summary_id=summary_id,
                status="retrying",
                message=f"Retry {retry_count + 1}/{max_retries} pending"
            )
    
    async def _update_failure_status(self, summary_id: str, error_message: str) -> None:
        """Update status to failed."""
        try:
            await result_store.set_summary_status(
                summary_id=summary_id,
                status="failed",
                message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to update failure status for {summary_id}: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if workers are running."""
        return self._running


# Global worker instance (single worker since summaries are less frequent)
summary_worker = SummaryWorker(num_workers=1)


async def start_summary_worker() -> None:
    """Start the global summary worker (call during app startup)."""
    await summary_worker.start()


async def stop_summary_worker() -> None:
    """Stop the global summary worker (call during app shutdown)."""
    await summary_worker.stop()
