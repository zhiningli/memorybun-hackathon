"""
Standalone script to test transcription API endpoints with an audio file.

This script simulates what a frontend would do:
1. Split audio into 30-second chunks
2. Upload each chunk to the API
3. Poll for processing completion
4. Get the final concatenated transcription

Usage:
    python transcribe_audio.py --audio-file-path <path> [--model MODEL] [--api-url URL] [--chunk-duration SECONDS]

Examples:
    python transcribe_audio.py --audio-file-path ./test_audio_file/test.webm
    python transcribe_audio.py --audio-file-path ./test_audio_file/test.webm --model base
    python transcribe_audio.py --audio-file-path long_recording.webm --chunk-duration 30 --model small
    python transcribe_audio.py --help

Requirements:
    - pydub (pip install pydub)
    - ffmpeg installed on system (for audio processing)
"""

import sys
import argparse
import time
import tempfile
import io
from pathlib import Path
from typing import List, Tuple
import httpx

# Valid Whisper models
VALID_MODELS = [
    "tiny", "tiny.en",
    "base", "base.en",
    "small", "small.en",
    "medium", "medium.en",
    "large"
]

# Default chunk duration in seconds
DEFAULT_CHUNK_DURATION = 30


def split_audio_into_chunks(
    audio_file_path: Path,
    chunk_duration_seconds: int = DEFAULT_CHUNK_DURATION
) -> List[Tuple[int, bytes]]:
    """
    Split audio file into chunks of specified duration.
    
    Args:
        audio_file_path: Path to audio file
        chunk_duration_seconds: Duration of each chunk in seconds
        
    Returns:
        List of (chunk_index, chunk_bytes) tuples
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        print("Error: pydub is required for audio chunking.")
        print("Install with: pip install pydub")
        print("Also ensure ffmpeg is installed on your system.")
        sys.exit(1)
    
    # Load audio file
    print(f"Loading audio file: {audio_file_path}")
    
    # Determine format from extension
    file_ext = audio_file_path.suffix.lower().lstrip('.')
    if file_ext == 'webm':
        # pydub needs format hint for webm
        audio = AudioSegment.from_file(str(audio_file_path), format="webm")
    else:
        audio = AudioSegment.from_file(str(audio_file_path))
    
    duration_ms = len(audio)
    duration_seconds = duration_ms / 1000
    chunk_duration_ms = chunk_duration_seconds * 1000
    
    print(f"Audio duration: {duration_seconds:.1f} seconds")
    print(f"Chunk duration: {chunk_duration_seconds} seconds")
    
    # Split into chunks
    chunks = []
    chunk_index = 0
    start_ms = 0
    
    while start_ms < duration_ms:
        end_ms = min(start_ms + chunk_duration_ms, duration_ms)
        chunk_audio = audio[start_ms:end_ms]
        
        # Export chunk to bytes (as webm/opus for consistency)
        buffer = io.BytesIO()
        chunk_audio.export(buffer, format="webm", codec="libopus")
        chunk_bytes = buffer.getvalue()
        
        chunks.append((chunk_index, chunk_bytes))
        
        chunk_duration = (end_ms - start_ms) / 1000
        print(f"  Chunk {chunk_index}: {start_ms/1000:.1f}s - {end_ms/1000:.1f}s ({chunk_duration:.1f}s, {len(chunk_bytes)} bytes)")
        
        chunk_index += 1
        start_ms = end_ms
    
    print(f"Split into {len(chunks)} chunks\n")
    return chunks


def upload_chunk(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    chunk_index: int,
    chunk_bytes: bytes
) -> str:
    """Upload a single chunk and return task_id."""
    files = {
        "audio_file": (f"chunk_{chunk_index}.webm", chunk_bytes, "audio/webm")
    }
    data = {"chunk_index": chunk_index}
    
    response = client.post(
        f"{base_url}/session/{session_id}/audio/chunk",
        files=files,
        data=data
    )
    
    if response.status_code != 200:
        error_detail = response.json().get('detail', response.text)
        raise Exception(f"Upload failed: {error_detail}")
    
    upload_data = response.json()
    if "task_id" not in upload_data:
        raise Exception(f"Unexpected response: {upload_data}")
    
    return upload_data["task_id"]


def wait_for_chunk(
    client: httpx.Client,
    base_url: str,
    session_id: str,
    chunk_index: int,
    max_wait_time: int = 300,
    poll_interval: float = 1.0
) -> dict:
    """Wait for a chunk to complete processing."""
    start_time = time.time()
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while time.time() - start_time < max_wait_time:
        try:
            response = client.get(
                f"{base_url}/session/{session_id}/audio/chunk/{chunk_index}/status",
                timeout=30.0
            )
            response.raise_for_status()
            status_data = response.json()
            consecutive_errors = 0
            
            status = status_data["status"]
            
            if status == "completed":
                return status_data
            elif status == "failed":
                raise Exception(f"Chunk {chunk_index} failed: {status_data.get('error', 'Unknown error')}")
            
            time.sleep(poll_interval)
            
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                raise Exception(f"Connection failed {max_consecutive_errors} times: {e}")
            time.sleep(poll_interval)
    
    raise Exception(f"Chunk {chunk_index} timed out after {max_wait_time} seconds")


def transcribe_audio_via_api(
    audio_file_path: Path,
    model_name: str = "tiny",
    api_url: str = "http://localhost:8001",
    chunk_duration: int = DEFAULT_CHUNK_DURATION
) -> None:
    """
    Transcribe an audio file using the transcription API.
    
    Splits audio into chunks, uploads each, waits for processing,
    and retrieves the final concatenated transcription.
    """
    # Validate audio file exists
    if not audio_file_path.exists():
        print(f"Error: Audio file not found: {audio_file_path}")
        sys.exit(1)
    
    # Validate model name
    if model_name not in VALID_MODELS:
        print(f"Error: Invalid model '{model_name}'")
        print(f"Valid models: {', '.join(VALID_MODELS)}")
        sys.exit(1)
    
    # Normalize API URL
    api_url = api_url.rstrip('/')
    base_url = f"{api_url}/api/v1/transcribe"
    
    print("=" * 80)
    print("TRANSCRIPTION CLIENT")
    print("=" * 80)
    print(f"API URL: {api_url}")
    print(f"Audio file: {audio_file_path}")
    print(f"Model: {model_name}")
    print(f"Chunk duration: {chunk_duration} seconds\n")
    
    # Step 1: Split audio into chunks
    print("Step 1: Splitting audio into chunks...")
    chunks = split_audio_into_chunks(audio_file_path, chunk_duration)
    total_chunks = len(chunks)
    
    # Use httpx client for API calls
    with httpx.Client(timeout=300.0) as client:
        try:
            # Step 2: Create session
            print("Step 2: Creating transcription session...")
            session_response = client.post(
                f"{base_url}/session",
                json={"model": model_name}
            )
            session_response.raise_for_status()
            session_data = session_response.json()
            session_id = session_data["session_id"]
            print(f"✓ Session created: {session_id}\n")
            
            # Step 3: Upload all chunks
            print(f"Step 3: Uploading {total_chunks} chunks...")
            task_ids = []
            upload_start = time.time()
            
            for chunk_index, chunk_bytes in chunks:
                task_id = upload_chunk(client, base_url, session_id, chunk_index, chunk_bytes)
                task_ids.append((chunk_index, task_id))
                print(f"  ✓ Chunk {chunk_index}/{total_chunks-1} uploaded (task: {task_id})")
            
            upload_time = time.time() - upload_start
            print(f"✓ All chunks uploaded in {upload_time:.1f}s\n")
            
            # Step 4: Wait for all chunks to complete
            print(f"Step 4: Waiting for processing to complete...")
            process_start = time.time()
            
            for chunk_index, task_id in task_ids:
                print(f"  Waiting for chunk {chunk_index}...", end="\r")
                status = wait_for_chunk(client, base_url, session_id, chunk_index)
                result_preview = status.get("result", "")[:50]
                print(f"  ✓ Chunk {chunk_index} completed: \"{result_preview}...\"")
            
            process_time = time.time() - process_start
            print(f"✓ All chunks processed in {process_time:.1f}s\n")
            
            # Step 5: Get final result
            print("Step 5: Retrieving final transcription...")
            result_response = client.get(f"{base_url}/session/audio/{session_id}")
            result_response.raise_for_status()
            result_data = result_response.json()
            
            transcribed_text = result_data["full_text"]
            total_processing_time = result_data.get("total_processing_time", process_time)
            
            print(f"✓ Transcription retrieved\n")
            
            # Step 6: Finalize session
            print("Step 6: Finalizing session...")
            finalize_response = client.post(f"{base_url}/session/audio/{session_id}/finalize")
            finalize_response.raise_for_status()
            print(f"✓ Session finalized\n")
            
            # Step 7: Cleanup
            print("Step 7: Cleaning up...")
            delete_response = client.delete(f"{base_url}/session/{session_id}")
            delete_response.raise_for_status()
            print(f"✓ Session deleted\n")
            
            # Print results
            print("=" * 80)
            print("TRANSCRIPTION RESULT")
            print("=" * 80)
            print(f"\nModel: {model_name}")
            print(f"Audio duration: {len(chunks) * chunk_duration}s (approx)")
            print(f"Chunks processed: {result_data['chunks_processed']}")
            print(f"Total processing time: {total_processing_time:.2f}s")
            print(f"Upload time: {upload_time:.1f}s")
            print(f"\nTranscribed text:\n")
            print(transcribed_text)
            print("\n" + "=" * 80)
            
            # Save to file
            output_file = audio_file_path.with_suffix('.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(transcribed_text)
            print(f"\nTranscription saved to: {output_file}")
            
        except httpx.HTTPStatusError as e:
            print(f"\n✗ API Error: {e}")
            try:
                error_detail = e.response.json()
                print(f"  Detail: {error_detail.get('detail', 'Unknown error')}")
            except:
                print(f"  Status: {e.response.status_code}")
            sys.exit(1)
        except httpx.RequestError as e:
            print(f"\n✗ Request Error: {e}")
            print(f"  Make sure the API server is running at {api_url}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n✗ Interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n✗ Error: {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test transcription API with an audio file (with chunking)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --audio-file-path ./test_audio_file/test.webm
  %(prog)s --audio-file-path ./test_audio_file/test.webm --model base
  %(prog)s --audio-file-path long_recording.webm --chunk-duration 30
  %(prog)s --audio-file-path podcast.mp3 --model small --chunk-duration 60

Note: Requires ffmpeg installed on your system for audio processing.
        """
    )
    
    parser.add_argument(
        '--audio-file-path',
        type=Path,
        required=True,
        help='Path to the audio file to transcribe'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='tiny',
        help='Whisper model to use (default: tiny). Options: ' + ', '.join(VALID_MODELS)
    )
    
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8001',
        help='Base URL of the API server (default: http://localhost:8001)'
    )
    
    parser.add_argument(
        '--chunk-duration',
        type=int,
        default=DEFAULT_CHUNK_DURATION,
        help=f'Duration of each audio chunk in seconds (default: {DEFAULT_CHUNK_DURATION})'
    )
    
    args = parser.parse_args()
    
    transcribe_audio_via_api(
        args.audio_file_path,
        args.model,
        args.api_url,
        args.chunk_duration
    )


if __name__ == "__main__":
    main()
