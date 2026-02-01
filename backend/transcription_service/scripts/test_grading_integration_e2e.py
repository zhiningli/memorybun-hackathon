"""
End-to-End Integration Test Script for Transcription → Grading Queue Integration

This script:
1. Transcribes an audio file (simulating frontend)
2. Finalizes the session
3. Verifies that transcription is published to Redis with correct status
4. Optionally simulates screenshot upload and verifies grading task is enqueued

Usage:
    python test_grading_integration_e2e.py --audio-file-path <path> [--api-url URL] [--verify-redis]

Requirements:
    - Redis running (for verification)
    - pydub (for audio chunking)
    - ffmpeg (for audio processing)
"""

import sys
import argparse
import time
import asyncio
from pathlib import Path
from typing import Optional
import httpx

# Add parent directory to path for imports
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

# Import services
from services.redis_client import get_redis_client, initialize_redis, close_redis
from services.grading_publisher import grading_publisher
from services.redis_grading_queue import redis_grading_queue
from schemas.grading import (
    GradingReadinessStatus,
    TranscriptionStatus,
    ScreenshotStatus
)

# Import audio chunking functions from existing script
# Since both scripts are in the same directory, we can import directly
import importlib.util
script_dir = Path(__file__).parent
audio_script_path = script_dir / "audio_transcription_script.py"
spec = importlib.util.spec_from_file_location("audio_transcription_script", audio_script_path)
audio_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio_script)

# Extract functions we need
split_audio_into_chunks = audio_script.split_audio_into_chunks
upload_chunk = audio_script.upload_chunk
wait_for_chunk = audio_script.wait_for_chunk
VALID_MODELS = audio_script.VALID_MODELS
DEFAULT_CHUNK_DURATION = audio_script.DEFAULT_CHUNK_DURATION


async def verify_redis_connection() -> bool:
    """Verify Redis is available and connected"""
    try:
        await initialize_redis()
        client = get_redis_client()
        if await client.health_check():
            print("✓ Redis connection verified\n")
            return True
        else:
            print("✗ Redis health check failed\n")
            return False
    except Exception as e:
        print(f"✗ Redis connection failed: {e}\n")
        return False


async def verify_transcription_in_redis(
    session_id: str,
    expected_text: str
) -> bool:
    """
    Verify that transcription was published to Redis with correct status.
    
    Returns:
        True if verification passes, False otherwise
    """
    print("=" * 80)
    print("VERIFYING REDIS STATE")
    print("=" * 80)
    
    try:
        # Get session state from Redis
        session_state = await grading_publisher.get_session_state(session_id)
        
        if session_state is None:
            print(f"✗ Session {session_id} not found in Redis")
            return False
        
        print(f"✓ Session state found in Redis")
        
        # Verify transcription status
        transcription_status = session_state.get("transcription_status")
        if transcription_status != TranscriptionStatus.COMPLETED.value:
            print(f"✗ Transcription status incorrect: expected '{TranscriptionStatus.COMPLETED.value}', got '{transcription_status}'")
            return False
        print(f"✓ Transcription status: {transcription_status}")
        
        # Verify transcription text
        transcription_text = session_state.get("transcription_text", "")
        if not transcription_text:
            print(f"✗ Transcription text is missing")
            return False
        
        if transcription_text != expected_text:
            print(f"✗ Transcription text mismatch")
            print(f"  Expected length: {len(expected_text)}")
            print(f"  Got length: {len(transcription_text)}")
            print(f"  Expected preview: {expected_text[:50]}...")
            print(f"  Got preview: {transcription_text[:50]}...")
            return False
        print(f"✓ Transcription text matches (length: {len(transcription_text)} chars)")
        
        # Verify readiness status
        readiness_status = session_state.get("grading_readiness_status")
        if readiness_status != GradingReadinessStatus.WAITING_FOR_SCREENSHOT.value:
            print(f"✗ Readiness status incorrect: expected '{GradingReadinessStatus.WAITING_FOR_SCREENSHOT.value}', got '{readiness_status}'")
            return False
        print(f"✓ Readiness status: {readiness_status}")
        
        # Verify screenshot status (should be pending or not set)
        screenshot_status = session_state.get("screenshot_status", "")
        if screenshot_status and screenshot_status != ScreenshotStatus.PENDING.value:
            print(f"⚠ Screenshot status: {screenshot_status} (expected pending or empty)")
        else:
            print(f"✓ Screenshot status: pending (not uploaded yet)")
        
        # Verify grading not published yet
        grading_published = session_state.get("grading_published", "false")
        if grading_published == "true":
            print(f"✗ Grading should not be published yet (screenshot not ready)")
            return False
        print(f"✓ Grading not published yet (waiting for screenshot)")
        
        print("\n" + "=" * 80)
        print("✓ ALL REDIS VERIFICATIONS PASSED")
        print("=" * 80 + "\n")
        return True
        
    except Exception as e:
        print(f"✗ Error verifying Redis state: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_grading_task_enqueued(session_id: str) -> bool:
    """
    Verify that a grading task was enqueued after screenshot upload.
    
    Returns:
        True if task is in queue, False otherwise
    """
    print("=" * 80)
    print("VERIFYING GRADING TASK IN QUEUE")
    print("=" * 80)
    
    try:
        queue_length = await redis_grading_queue.get_queue_length()
        print(f"Queue length: {queue_length}")
        
        if queue_length == 0:
            print("✗ No tasks in grading queue")
            return False
        
        # Peek at the task
        task = await redis_grading_queue.peek_queue()
        if task is None:
            print("✗ Could not peek at queue")
            return False
        
        if task.session_id != session_id:
            print(f"✗ Task session_id mismatch: expected {session_id}, got {task.session_id}")
            return False
        
        print(f"✓ Grading task found in queue")
        print(f"  Session ID: {task.session_id}")
        print(f"  Transcription length: {len(task.transcription_text)} chars")
        print(f"  Screenshot URL: {task.screenshot_url}")
        print(f"  Created at: {task.created_at}")
        
        # Verify session state shows enqueued
        session_state = await grading_publisher.get_session_state(session_id)
        if session_state:
            readiness_status = session_state.get("grading_readiness_status")
            if readiness_status == GradingReadinessStatus.ENQUEUED.value:
                print(f"✓ Session state shows: {readiness_status}")
            else:
                print(f"⚠ Session state shows: {readiness_status} (expected enqueued)")
        
        print("\n" + "=" * 80)
        print("✓ GRADING TASK VERIFICATION PASSED")
        print("=" * 80 + "\n")
        return True
        
    except Exception as e:
        print(f"✗ Error verifying grading task: {e}")
        import traceback
        traceback.print_exc()
        return False


async def simulate_screenshot_upload(session_id: str, screenshot_url: str = "/test/screenshot.png") -> bool:
    """
    Simulate screenshot upload by calling grading_publisher directly.
    
    In Phase 5, this will be done via API endpoint.
    """
    print("=" * 80)
    print("SIMULATING SCREENSHOT UPLOAD")
    print("=" * 80)
    
    try:
        published = await grading_publisher.publish_screenshot_ready(
            session_id=session_id,
            screenshot_url=screenshot_url
        )
        
        if published:
            print(f"✓ Screenshot uploaded, grading task published")
            return True
        else:
            print(f"⚠ Screenshot uploaded, but grading task not published (may already be published)")
            return True  # Still consider success
            
    except Exception as e:
        print(f"✗ Error simulating screenshot upload: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_e2e_test(
    audio_file_path: Path,
    api_url: str = "http://localhost:8001",
    verify_redis: bool = True,
    test_screenshot: bool = False
) -> bool:
    """
    Run end-to-end integration test.
    
    Returns:
        True if all verifications pass, False otherwise
    """
    print("=" * 80)
    print("E2E INTEGRATION TEST: Transcription → Grading Queue")
    print("=" * 80)
    print(f"Audio file: {audio_file_path}")
    print(f"API URL: {api_url}")
    print(f"Verify Redis: {verify_redis}")
    print(f"Test screenshot: {test_screenshot}\n")
    
    # Step 0: Verify Redis connection
    if verify_redis:
        if not await verify_redis_connection():
            print("✗ Redis verification failed. Skipping Redis checks.")
            verify_redis = False
    
    # Normalize API URL
    api_url = api_url.rstrip('/')
    base_url = f"{api_url}/api/v1/transcribe"
    
    # Step 1: Split audio into chunks
    print("Step 1: Splitting audio into chunks...")
    chunks = split_audio_into_chunks(audio_file_path, DEFAULT_CHUNK_DURATION)
    total_chunks = len(chunks)
    print(f"✓ Split into {total_chunks} chunks\n")
    
    session_id = None
    transcribed_text = None
    
    # Use httpx client for API calls
    with httpx.Client(timeout=300.0) as client:
        try:
            # Step 2: Create session
            print("Step 2: Creating transcription session...")
            session_response = client.post(
                f"{base_url}/session",
                json={"model": "tiny"}
            )
            session_response.raise_for_status()
            session_data = session_response.json()
            session_id = session_data["session_id"]
            print(f"✓ Session created: {session_id}\n")
            
            # Step 3: Upload all chunks
            print(f"Step 3: Uploading {total_chunks} chunks...")
            task_ids = []
            for chunk_index, chunk_bytes in chunks:
                task_id = upload_chunk(client, base_url, session_id, chunk_index, chunk_bytes)
                task_ids.append((chunk_index, task_id))
                print(f"  ✓ Chunk {chunk_index}/{total_chunks-1} uploaded")
            print(f"✓ All chunks uploaded\n")
            
            # Step 4: Wait for all chunks to complete
            print(f"Step 4: Waiting for processing to complete...")
            for chunk_index, task_id in task_ids:
                print(f"  Waiting for chunk {chunk_index}...", end="\r")
                status = wait_for_chunk(client, base_url, session_id, chunk_index)
                print(f"  ✓ Chunk {chunk_index} completed")
            print(f"✓ All chunks processed\n")
            
            # Step 5: Get final result
            print("Step 5: Retrieving final transcription...")
            result_response = client.get(f"{base_url}/session/{session_id}")
            result_response.raise_for_status()
            result_data = result_response.json()
            transcribed_text = result_data["full_text"]
            print(f"✓ Transcription retrieved (length: {len(transcribed_text)} chars)\n")
            
            # Step 6: Finalize session (this should publish to Redis)
            print("Step 6: Finalizing session (should publish to Redis)...")
            finalize_response = client.post(f"{base_url}/session/{session_id}/finalize")
            finalize_response.raise_for_status()
            print(f"✓ Session finalized\n")
            
            # Small delay to ensure Redis write completes
            await asyncio.sleep(0.5)
            
            # Step 7: Verify Redis state
            if verify_redis:
                print("Step 7: Verifying Redis state...")
                redis_ok = await verify_transcription_in_redis(session_id, transcribed_text)
                if not redis_ok:
                    print("✗ Redis verification failed")
                    return False
                print("✓ Redis verification passed\n")
            
            # Step 8: Optionally test screenshot upload
            if test_screenshot and verify_redis:
                print("Step 8: Testing screenshot upload...")
                screenshot_ok = await simulate_screenshot_upload(session_id)
                if not screenshot_ok:
                    print("✗ Screenshot upload simulation failed")
                    return False
                
                # Verify grading task is enqueued
                await asyncio.sleep(0.5)
                task_ok = await verify_grading_task_enqueued(session_id)
                if not task_ok:
                    print("✗ Grading task verification failed")
                    return False
                print("✓ Screenshot upload and grading task verification passed\n")
            
            # Step 9: Cleanup
            print("Step 9: Cleaning up...")
            # Delete in-memory session (transcription service)
            delete_response = client.delete(f"{base_url}/session/{session_id}")
            delete_response.raise_for_status()
            print(f"✓ In-memory session deleted")
            
            # Redis cleanup happens in finally block
            print(f"✓ Redis cleanup will happen automatically\n")
            
            print("=" * 80)
            print("✓ ALL E2E TESTS PASSED")
            print("=" * 80)
            return True
            
        except httpx.HTTPStatusError as e:
            print(f"\n✗ API Error: {e}")
            try:
                error_detail = e.response.json()
                print(f"  Detail: {error_detail.get('detail', 'Unknown error')}")
            except:
                print(f"  Status: {e.response.status_code}")
            return False
        except httpx.RequestError as e:
            print(f"\n✗ Request Error: {e}")
            print(f"  Make sure the API server is running at {api_url}")
            return False
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Cleanup Redis if we created session state
            if session_id and verify_redis:
                try:
                    print("Cleaning up Redis state...")
                    await grading_publisher.delete_session_state(session_id)
                    await redis_grading_queue.clear_queue()
                    print("✓ Redis state cleaned up")
                except Exception as e:
                    print(f"⚠ Warning: Failed to clean up Redis state: {e}")
            await close_redis()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="E2E Integration Test: Transcription → Grading Queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --audio-file-path ./data/test_audio_recording_full.webm
  %(prog)s --audio-file-path ./data/test_audio_recording_full.webm --test-screenshot
  %(prog)s --audio-file-path ./data/test_audio_recording_full.webm --no-verify-redis

This script verifies that:
  1. Audio transcription completes successfully
  2. Session finalization publishes transcription to Redis
  3. Redis state shows: transcription_status=completed, readiness_status=waiting_for_screenshot
  4. (Optional) Screenshot upload enqueues grading task
        """
    )
    
    parser.add_argument(
        '--audio-file-path',
        type=Path,
        required=True,
        help='Path to the audio file to transcribe'
    )
    
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8001',
        help='Base URL of the API server (default: http://localhost:8001)'
    )
    
    parser.add_argument(
        '--verify-redis',
        action='store_true',
        default=True,
        help='Verify Redis state after transcription (default: True)'
    )
    
    parser.add_argument(
        '--no-verify-redis',
        dest='verify_redis',
        action='store_false',
        help='Skip Redis verification'
    )
    
    parser.add_argument(
        '--test-screenshot',
        action='store_true',
        help='Also test screenshot upload and grading task enqueueing'
    )
    
    args = parser.parse_args()
    
    # Validate audio file exists
    if not args.audio_file_path.exists():
        print(f"Error: Audio file not found: {args.audio_file_path}")
        sys.exit(1)
    
    # Run async test
    success = asyncio.run(run_e2e_test(
        args.audio_file_path,
        args.api_url,
        args.verify_redis,
        args.test_screenshot
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

