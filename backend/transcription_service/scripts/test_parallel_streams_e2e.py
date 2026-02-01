"""
End-to-End Integration Test: Parallel Audio and Screenshot Streams

This script verifies that audio transcription and screenshot upload can be processed
in two independent streams and correctly assembled into a grading task when both are ready.

Test Scenarios:
1. Audio First: Audio completes → Screenshot uploads → Grading task enqueued
2. Screenshot First: Screenshot uploads → Audio completes → Grading task enqueued
3. Simultaneous: Both processes run concurrently → Grading task enqueued when both ready

Usage:
    python test_parallel_streams_e2e.py --audio-file-path <path> --screenshot-file-path <path> [--scenario SCENARIO] [--api-url URL]

Requirements:
    - Redis running (for verification)
    - pydub (for audio chunking)
    - ffmpeg (for audio processing)
    - PIL/Pillow (for screenshot validation)
"""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import Optional, Tuple
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
DEFAULT_CHUNK_DURATION = audio_script.DEFAULT_CHUNK_DURATION

# Sample PNG data for testing (1x1 pixel PNG)
PNG_DATA = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
)


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


def process_audio_stream_sync(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    audio_file_path: Path
) -> Tuple[bool, Optional[str]]:
    """
    Process audio transcription stream (synchronous version for concurrent execution).
    
    Returns:
        (success: bool, transcribed_text: Optional[str])
    """
    print("=" * 80)
    print("PROCESSING AUDIO STREAM")
    print("=" * 80)
    
    try:
        # Split audio into chunks
        print("Splitting audio into chunks...")
        chunks = split_audio_into_chunks(audio_file_path, DEFAULT_CHUNK_DURATION)
        total_chunks = len(chunks)
        print(f"✓ Split into {total_chunks} chunks")
        
        # Upload all chunks
        print(f"Uploading {total_chunks} chunks...")
        task_ids = []
        for chunk_index, chunk_bytes in chunks:
            task_id = upload_chunk(client, base_url, session_id, chunk_index, chunk_bytes)
            task_ids.append((chunk_index, task_id))
            print(f"  ✓ Chunk {chunk_index}/{total_chunks-1} uploaded")
        
        # Wait for all chunks to complete
        print("Waiting for processing to complete...")
        for chunk_index, task_id in task_ids:
            print(f"  Waiting for chunk {chunk_index}...", end="\r")
            status = wait_for_chunk(client, base_url, session_id, chunk_index)
            print(f"  ✓ Chunk {chunk_index} completed")
        
        # Get final result
        print("Retrieving final transcription...")
        result_response = client.get(f"{base_url}/session/{session_id}")
        result_response.raise_for_status()
        result_data = result_response.json()
        transcribed_text = result_data["full_text"]
        print(f"✓ Transcription retrieved (length: {len(transcribed_text)} chars)")
        
        # Finalize session
        print("Finalizing session...")
        finalize_response = client.post(f"{base_url}/session/{session_id}/finalize")
        finalize_response.raise_for_status()
        print(f"✓ Session finalized\n")
        
        return True, transcribed_text
        
    except Exception as e:
        print(f"✗ Error processing audio stream: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def process_audio_stream(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    audio_file_path: Path
) -> Tuple[bool, Optional[str]]:
    """
    Process audio transcription stream (async wrapper).
    
    Returns:
        (success: bool, transcribed_text: Optional[str])
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        process_audio_stream_sync,
        client,
        base_url,
        session_id,
        audio_file_path
    )


def process_screenshot_stream_sync(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    screenshot_file_path: Optional[Path] = None
) -> Tuple[bool, Optional[str]]:
    """
    Process screenshot upload stream (synchronous version for concurrent execution).
    
    Args:
        screenshot_file_path: Path to screenshot file. If None, uses sample PNG data.
    
    Returns:
        (success: bool, screenshot_url: Optional[str])
    """
    print("=" * 80)
    print("PROCESSING SCREENSHOT STREAM")
    print("=" * 80)
    
    try:
        # Read screenshot data
        if screenshot_file_path and screenshot_file_path.exists():
            print(f"Reading screenshot from {screenshot_file_path}...")
            screenshot_data = screenshot_file_path.read_bytes()
            filename = screenshot_file_path.name
            content_type = "image/png" if filename.endswith(".png") else "image/jpeg"
        else:
            print("Using sample PNG data...")
            screenshot_data = PNG_DATA
            filename = "test.png"
            content_type = "image/png"
        
        print(f"✓ Screenshot data ready (size: {len(screenshot_data)} bytes)")
        
        # Upload screenshot
        print("Uploading screenshot...")
        files = {"screenshot": (filename, screenshot_data, content_type)}
        response = client.post(
            f"{base_url}/session/{session_id}/screenshot",
            files=files
        )
        response.raise_for_status()
        response_data = response.json()
        screenshot_url = response_data["screenshot_url"]
        status = response_data["status"]
        readiness_status = response_data.get("grading_readiness_status")
        
        print(f"✓ Screenshot uploaded")
        print(f"  URL: {screenshot_url}")
        print(f"  Status: {status}")
        print(f"  Readiness: {readiness_status}\n")
        
        return True, screenshot_url
        
    except Exception as e:
        print(f"✗ Error processing screenshot stream: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def process_screenshot_stream(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    screenshot_file_path: Optional[Path] = None
) -> Tuple[bool, Optional[str]]:
    """
    Process screenshot upload stream (async wrapper).
    
    Args:
        screenshot_file_path: Path to screenshot file. If None, uses sample PNG data.
    
    Returns:
        (success: bool, screenshot_url: Optional[str])
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        process_screenshot_stream_sync,
        client,
        base_url,
        session_id,
        screenshot_file_path
    )


async def verify_redis_state(
    session_id: str,
    expected_transcription: Optional[str] = None,
    expected_screenshot_url: Optional[str] = None
) -> bool:
    """
    Verify Redis session state.
    
    Returns:
        True if verification passes, False otherwise
    """
    print("=" * 80)
    print("VERIFYING REDIS STATE")
    print("=" * 80)
    
    try:
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
        
        # Verify transcription text if provided
        if expected_transcription:
            transcription_text = session_state.get("transcription_text", "")
            if transcription_text != expected_transcription:
                print(f"✗ Transcription text mismatch")
                return False
            print(f"✓ Transcription text matches (length: {len(transcription_text)} chars)")
        
        # Verify screenshot status
        screenshot_status = session_state.get("screenshot_status")
        if screenshot_status != ScreenshotStatus.COMPLETED.value:
            print(f"✗ Screenshot status incorrect: expected '{ScreenshotStatus.COMPLETED.value}', got '{screenshot_status}'")
            return False
        print(f"✓ Screenshot status: {screenshot_status}")
        
        # Verify screenshot URL if provided
        if expected_screenshot_url:
            screenshot_url = session_state.get("screenshot_url", "")
            if screenshot_url != expected_screenshot_url:
                print(f"✗ Screenshot URL mismatch: expected '{expected_screenshot_url}', got '{screenshot_url}'")
                return False
            print(f"✓ Screenshot URL matches: {screenshot_url}")
        
        # Verify readiness status
        readiness_status = session_state.get("grading_readiness_status")
        if readiness_status != GradingReadinessStatus.ENQUEUED.value:
            print(f"✗ Readiness status incorrect: expected '{GradingReadinessStatus.ENQUEUED.value}', got '{readiness_status}'")
            return False
        print(f"✓ Readiness status: {readiness_status}")
        
        # Verify grading published flag
        grading_published = session_state.get("grading_published", "false")
        if grading_published != "true":
            print(f"✗ Grading published flag incorrect: expected 'true', got '{grading_published}'")
            return False
        print(f"✓ Grading published: {grading_published}")
        
        print("\n" + "=" * 80)
        print("✓ ALL REDIS VERIFICATIONS PASSED")
        print("=" * 80 + "\n")
        return True
        
    except Exception as e:
        print(f"✗ Error verifying Redis state: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_grading_task(
    session_id: str,
    expected_transcription: Optional[str] = None,
    expected_screenshot_url: Optional[str] = None
) -> bool:
    """
    Verify grading task is in queue.
    
    Returns:
        True if task is in queue and matches expectations, False otherwise
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
        
        # Verify transcription text if provided
        if expected_transcription:
            if task.transcription_text != expected_transcription:
                print(f"✗ Transcription text mismatch")
                return False
            print(f"✓ Transcription text matches")
        
        # Verify screenshot URL if provided
        if expected_screenshot_url:
            if task.screenshot_url != expected_screenshot_url:
                print(f"✗ Screenshot URL mismatch: expected '{expected_screenshot_url}', got '{task.screenshot_url}'")
                return False
            print(f"✓ Screenshot URL matches")
        
        print("\n" + "=" * 80)
        print("✓ GRADING TASK VERIFICATION PASSED")
        print("=" * 80 + "\n")
        return True
        
    except Exception as e:
        print(f"✗ Error verifying grading task: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_scenario_audio_first(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    audio_file_path: Path,
    screenshot_file_path: Optional[Path]
) -> bool:
    """
    Scenario 1: Audio completes first, then screenshot uploads.
    Expected: Grading task enqueued when screenshot uploads.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 1: AUDIO FIRST")
    print("=" * 80)
    print("Flow: Audio completes → Screenshot uploads → Grading task enqueued\n")
    
    # Step 1: Process audio stream
    audio_success, transcribed_text = await process_audio_stream(
        client, base_url, session_id, audio_file_path
    )
    if not audio_success:
        return False
    
    # Small delay to ensure Redis write completes
    await asyncio.sleep(0.5)
    
    # Verify intermediate state (waiting for screenshot)
    print("Verifying intermediate state (waiting for screenshot)...")
    session_state = await grading_publisher.get_session_state(session_id)
    if session_state:
        readiness_status = session_state.get("grading_readiness_status")
        if readiness_status != GradingReadinessStatus.WAITING_FOR_SCREENSHOT.value:
            print(f"⚠ Unexpected readiness status: {readiness_status}")
        else:
            print(f"✓ Readiness status: {readiness_status} (waiting for screenshot)\n")
    
    # Step 2: Process screenshot stream
    screenshot_success, screenshot_url = await process_screenshot_stream(
        client, base_url, session_id, screenshot_file_path
    )
    if not screenshot_success:
        return False
    
    # Small delay to ensure Redis write completes
    await asyncio.sleep(0.5)
    
    # Step 3: Verify final state
    redis_ok = await verify_redis_state(session_id, transcribed_text, screenshot_url)
    if not redis_ok:
        return False
    
    # Step 4: Verify grading task
    task_ok = await verify_grading_task(session_id, transcribed_text, screenshot_url)
    if not task_ok:
        return False
    
    print("=" * 80)
    print("✓ SCENARIO 1 PASSED")
    print("=" * 80 + "\n")
    return True


async def run_scenario_screenshot_first(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    audio_file_path: Path,
    screenshot_file_path: Optional[Path]
) -> bool:
    """
    Scenario 2: Screenshot uploads first, then audio completes.
    Expected: Grading task enqueued when audio finalizes.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 2: SCREENSHOT FIRST")
    print("=" * 80)
    print("Flow: Screenshot uploads → Audio completes → Grading task enqueued\n")
    
    # Step 1: Process screenshot stream
    screenshot_success, screenshot_url = await process_screenshot_stream(
        client, base_url, session_id, screenshot_file_path
    )
    if not screenshot_success:
        return False
    
    # Small delay to ensure Redis write completes
    await asyncio.sleep(0.5)
    
    # Verify intermediate state (waiting for audio)
    print("Verifying intermediate state (waiting for audio)...")
    session_state = await grading_publisher.get_session_state(session_id)
    if session_state:
        readiness_status = session_state.get("grading_readiness_status")
        if readiness_status != GradingReadinessStatus.WAITING_FOR_AUDIO.value:
            print(f"⚠ Unexpected readiness status: {readiness_status}")
        else:
            print(f"✓ Readiness status: {readiness_status} (waiting for audio)\n")
    
    # Step 2: Process audio stream
    audio_success, transcribed_text = await process_audio_stream(
        client, base_url, session_id, audio_file_path
    )
    if not audio_success:
        return False
    
    # Small delay to ensure Redis write completes
    await asyncio.sleep(0.5)
    
    # Step 3: Verify final state
    redis_ok = await verify_redis_state(session_id, transcribed_text, screenshot_url)
    if not redis_ok:
        return False
    
    # Step 4: Verify grading task
    task_ok = await verify_grading_task(session_id, transcribed_text, screenshot_url)
    if not task_ok:
        return False
    
    print("=" * 80)
    print("✓ SCENARIO 2 PASSED")
    print("=" * 80 + "\n")
    return True


async def run_scenario_simultaneous(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    audio_file_path: Path,
    screenshot_file_path: Optional[Path]
) -> bool:
    """
    Scenario 3: Both streams run concurrently.
    Expected: Grading task enqueued when the second stream completes.
    
    Note: Creates separate httpx.Client instances for each stream since httpx.Client
    is not thread-safe and both streams run in separate executors.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 3: SIMULTANEOUS")
    print("=" * 80)
    print("Flow: Audio and Screenshot process concurrently → Grading task enqueued when both ready\n")
    
    # Create separate client instances for each stream (httpx.Client is not thread-safe)
    # We'll create them inside the executor functions to ensure they're in the right thread
    def process_audio_with_client():
        with httpx.Client(timeout=300.0) as audio_client:
            return process_audio_stream_sync(audio_client, base_url, session_id, audio_file_path)
    
    def process_screenshot_with_client():
        with httpx.Client(timeout=300.0) as screenshot_client:
            return process_screenshot_stream_sync(screenshot_client, base_url, session_id, screenshot_file_path)
    
    # Start both streams concurrently
    # Note: run_in_executor returns a Future, not a coroutine, so we can't use create_task
    loop = asyncio.get_event_loop()
    audio_future = loop.run_in_executor(None, process_audio_with_client)
    screenshot_future = loop.run_in_executor(None, process_screenshot_with_client)
    
    # Wait for both to complete
    print("Waiting for both streams to complete...")
    audio_result, screenshot_result = await asyncio.gather(audio_future, screenshot_future)
    
    audio_success, transcribed_text = audio_result
    screenshot_success, screenshot_url = screenshot_result
    
    if not audio_success or not screenshot_success:
        print("✗ One or both streams failed")
        return False
    
    # Small delay to ensure Redis writes complete
    await asyncio.sleep(1.0)
    
    # Verify final state
    redis_ok = await verify_redis_state(session_id, transcribed_text, screenshot_url)
    if not redis_ok:
        return False
    
    # Verify grading task
    task_ok = await verify_grading_task(session_id, transcribed_text, screenshot_url)
    if not task_ok:
        return False
    
    print("=" * 80)
    print("✓ SCENARIO 3 PASSED")
    print("=" * 80 + "\n")
    return True


async def run_e2e_test(
    audio_file_path: Path,
    screenshot_file_path: Optional[Path],
    scenario: str,
    api_url: str = "http://localhost:8001",
    verify_redis: bool = True
) -> bool:
    """
    Run end-to-end integration test for parallel streams.
    
    Returns:
        True if all verifications pass, False otherwise
    """
    print("=" * 80)
    print("E2E INTEGRATION TEST: Parallel Audio and Screenshot Streams")
    print("=" * 80)
    print(f"Audio file: {audio_file_path}")
    print(f"Screenshot file: {screenshot_file_path or 'Sample PNG (generated)'}")
    print(f"Scenario: {scenario}")
    print(f"API URL: {api_url}")
    print(f"Verify Redis: {verify_redis}\n")
    
    # Step 0: Verify Redis connection
    if verify_redis:
        if not await verify_redis_connection():
            print("✗ Redis verification failed. Skipping Redis checks.")
            verify_redis = False
    
    # Normalize API URL
    api_url = api_url.rstrip('/')
    base_url = f"{api_url}/api/v1/transcribe"
    
    # Use httpx client for API calls
    with httpx.Client(timeout=300.0) as client:
        try:
            # Create session
            print("Creating transcription session...")
            session_response = client.post(
                f"{base_url}/session",
                json={"model": "tiny"}
            )
            session_response.raise_for_status()
            session_data = session_response.json()
            session_id = session_data["session_id"]
            print(f"✓ Session created: {session_id}\n")
            
            # Run scenario
            if scenario == "audio_first":
                success = await run_scenario_audio_first(
                    client, base_url, session_id, audio_file_path, screenshot_file_path
                )
            elif scenario == "screenshot_first":
                success = await run_scenario_screenshot_first(
                    client, base_url, session_id, audio_file_path, screenshot_file_path
                )
            elif scenario == "simultaneous":
                success = await run_scenario_simultaneous(
                    client, base_url, session_id, audio_file_path, screenshot_file_path
                )
            else:
                print(f"✗ Unknown scenario: {scenario}")
                return False
            
            if not success:
                return False
            
            # Cleanup
            print("Cleaning up...")
            delete_response = client.delete(f"{base_url}/session/{session_id}")
            delete_response.raise_for_status()
            print(f"✓ In-memory session deleted")
            
            if verify_redis:
                await grading_publisher.delete_session_state(session_id)
                await redis_grading_queue.clear_queue()
                print(f"✓ Redis state cleaned up")
            
            print("\n" + "=" * 80)
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
            await close_redis()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="E2E Integration Test: Parallel Audio and Screenshot Streams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --audio-file-path ./data/test.webm --screenshot-file-path ./screenshot.png --scenario audio_first
  %(prog)s --audio-file-path ./data/test.webm --scenario screenshot_first
  %(prog)s --audio-file-path ./data/test.webm --scenario simultaneous

This script verifies that:
  1. Audio transcription and screenshot upload can process independently
  2. Both streams correctly update Redis state
  3. Grading task is enqueued when both are ready (regardless of order)
  4. State transitions work correctly for all scenarios
        """
    )
    
    parser.add_argument(
        '--audio-file-path',
        type=Path,
        required=True,
        help='Path to the audio file to transcribe'
    )
    
    parser.add_argument(
        '--screenshot-file-path',
        type=Path,
        default=None,
        help='Path to screenshot file (optional, uses sample PNG if not provided)'
    )
    
    parser.add_argument(
        '--scenario',
        type=str,
        choices=['audio_first', 'screenshot_first', 'simultaneous', 'all'],
        default='all',
        help='Test scenario to run (default: all)'
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
        help='Verify Redis state after processing (default: True)'
    )
    
    parser.add_argument(
        '--no-verify-redis',
        dest='verify_redis',
        action='store_false',
        help='Skip Redis verification'
    )
    
    args = parser.parse_args()
    
    # Validate audio file exists
    if not args.audio_file_path.exists():
        print(f"Error: Audio file not found: {args.audio_file_path}")
        sys.exit(1)
    
    # Validate screenshot file if provided
    if args.screenshot_file_path and not args.screenshot_file_path.exists():
        print(f"Error: Screenshot file not found: {args.screenshot_file_path}")
        sys.exit(1)
    
    # Run scenarios
    scenarios_to_run = ['audio_first', 'screenshot_first', 'simultaneous'] if args.scenario == 'all' else [args.scenario]
    all_passed = True
    
    for scenario in scenarios_to_run:
        success = asyncio.run(run_e2e_test(
            args.audio_file_path,
            args.screenshot_file_path,
            scenario,
            args.api_url,
            args.verify_redis
        ))
        if not success:
            all_passed = False
            if args.scenario != 'all':
                # If running single scenario, exit on failure
                sys.exit(1)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

