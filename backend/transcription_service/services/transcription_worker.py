"""
Background worker that processes transcription tasks from queue.

This worker runs in the background and processes audio chunks asynchronously,
allowing the API to return immediately without blocking.
"""
import asyncio
import os
import logging
import traceback
from pathlib import Path
from typing import Optional
from services.transcription_queue import transcription_queue, TaskStatus


logger = logging.getLogger(__name__)



class TranscriptionWorker:
    """Worker that processes transcription tasks from the queue"""
    
    def __init__(self, num_workers: int = 2):
        """
        Initialize worker pool.
        
        Args:
            num_workers: Number of concurrent worker tasks to run
        """
        self.num_workers = num_workers
        self._running = False
        self._workers: list[asyncio.Task] = []
        self.audio_transcription_service = None
    
    async def start(self, audio_transcription_service):
        """Start worker pool"""
        if self._running:
            logger.info("Workers already running")
            return
        
        self.audio_transcription_service = audio_transcription_service
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(f"worker-{i}"))
            for i in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} transcription workers")
    
    async def stop(self):
        """Stop worker pool gracefully"""
        if not self._running:
            return
        
        self._running = False
        if self._workers:
            # Cancel all worker tasks first
            for worker_task in self._workers:
                if not worker_task.done():
                    worker_task.cancel()
            
            # Wait for all workers to finish/cancel (with timeout)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Warning: Some workers did not stop within timeout")
            except asyncio.CancelledError:
                # Expected during shutdown, ignore
                pass
            
            self._workers = []
        
        self.audio_transcription_service = None
        logger.info("Stopped transcription workers")
    
    async def _worker_loop(self, worker_name: str):
        """
        Main worker loop - continuously processes tasks from queue.
        
        Args:
            worker_name: Name identifier for this worker (for logging)
        """
        logger.info(f"[{worker_name}] Worker started")
        
        while self._running:
            try:
                # Get task from queue (non-blocking with timeout)
                task_id = await transcription_queue.dequeue()
                
                if not task_id:
                    # Queue is empty, brief pause before checking again
                    await asyncio.sleep(0.1)
                    continue
                
                logger.debug(f"[{worker_name}] Dequeued task: {task_id}")
                
                # Get task details
                task = transcription_queue.get_task(task_id)
                if not task:
                    logger.warning(f"[{worker_name}] Task {task_id} not found, skipping")
                    continue
                
                # Process the task
                await self._process_task(task, worker_name)
                
            except asyncio.CancelledError:
                # Expected during shutdown, break out of loop
                logger.info(f"[{worker_name}] Worker cancelled, stopping...")
                break
            except Exception as e:
                logger.error(f"[{worker_name}] Error in worker loop: {e}")
                logger.error(f"[{worker_name}] Traceback: {traceback.format_exc()}")
                await asyncio.sleep(1)  # Brief pause before retrying
        
        logger.info(f"[{worker_name}] Worker stopped")
    
    async def _process_task(self, task, worker_name: str):
        """
        Process a single transcription task.
        
        Args:
            task: TranscriptionTask to process
            worker_name: Name of worker processing this task
        """
        # Safety check if service is available
        if not self.audio_transcription_service:
            logger.error(f"[{worker_name}] AudioTranscriptionService not initialized")
            # Re-queue task? For now just fail
            transcription_queue.update_task_status(
                f"{task.session_id}_chunk_{task.chunk_index}",
                TaskStatus.FAILED,
                error="AudioTranscriptionService not initialized"
            )
            return

        task_id = f"{task.session_id}_chunk_{task.chunk_index}"
        logger.info(f"[{worker_name}] Processing {task_id}")
        
        # Update status to processing
        transcription_queue.update_task_status(task_id, TaskStatus.PROCESSING)
        
        audio_path = Path(task.audio_file_path)
        
        try:
            # Store audio to S3 before transcription (if S3 mode is enabled)
            # This preserves original audio for future evaluation/training
            try:
                from services.audio_storage_service import audio_storage_service
                
                if audio_storage_service.is_enabled and audio_path.exists():
                    audio_data = audio_path.read_bytes()
                    audio_url = await audio_storage_service.store_audio(
                        session_id=task.session_id,
                        chunk_index=task.chunk_index,
                        audio_data=audio_data
                    )
                    if audio_url:
                        logger.info(f"[{worker_name}] Stored audio chunk to S3: {audio_url}")
                        # Store audio URL in session for later use during finalize
                        await self._store_audio_url(task.session_id, task.chunk_index, audio_url)
            except Exception as e:
                # Don't fail transcription if S3 upload fails - log and continue
                logger.warning(f"[{worker_name}] Failed to store audio to S3: {e}, continuing with transcription")
            
            # Call service method to process chunk
            result = await self.audio_transcription_service.gen_process_chunk_async(
                session_id=task.session_id,
                chunk_index=task.chunk_index,
                audio_file_path=audio_path
            )
            
            if result:
                # Update task with result
                transcription_queue.update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    result=result.chunk_text
                )
                logger.info(f"[{worker_name}] Completed {task_id}: {len(result.chunk_text)} chars")
            else:
                raise Exception("Service returned None - session may not exist")
                
        except Exception as e:
            error_msg = str(e)
            transcription_queue.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=error_msg
            )
            logger.error(f"[{worker_name}] Failed {task_id}: {error_msg}")
            
            # Re-raise to potentially retry or log
            raise
        finally:
            # Clean up temp file after processing (success or failure)
            try:
                if audio_path.exists():
                    os.unlink(audio_path)
                    logger.debug(f"[{worker_name}] Cleaned up temp file: {audio_path}")
            except Exception as e:
                logger.error(f"[{worker_name}] Failed to delete temp file {task.audio_file_path}: {e}")
    
    async def _store_audio_url(self, session_id: str, chunk_index: int, audio_url: str):
        """
        Store audio URL in Redis session state for later retrieval during finalize.
        Uses the session state to accumulate audio URLs.
        """
        try:
            from services.redis_client import get_redis_client
            
            client = get_redis_client().get_client()
            session_key = f"session:{session_id}"
            
            # Store audio URL as a field in the session hash
            # For now, store the first chunk's URL as the representative (or latest)
            # A more sophisticated approach could store all chunk URLs
            if chunk_index == 0:
                # Store first chunk URL as the session's audio URL
                await client.hset(session_key, "audio_url", audio_url)
                logger.debug(f"Stored audio URL for session {session_id}: {audio_url}")
        except Exception as e:
            logger.warning(f"Failed to store audio URL in session {session_id}: {e}")


# Global worker instance
# Using 1 worker since Whisper model is not thread-safe and requires
# serialized access. Multiple workers would just wait on the lock.
transcription_worker = TranscriptionWorker(num_workers=1)


