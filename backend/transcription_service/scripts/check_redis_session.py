"""
Quick script to check if a session exists in Redis.

Usage:
    python scripts/check_redis_session.py <session_id>
    python scripts/check_redis_session.py --list-all
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

from services.redis_client import get_redis_client, initialize_redis, close_redis
from services.grading_publisher import grading_publisher
from schemas.grading import GradingReadinessStatus


async def check_session(session_id: str):
    """Check if a specific session exists in Redis"""
    try:
        await initialize_redis()
        
        session_state = await grading_publisher.get_session_state(session_id)
        
        if session_state is None:
            print(f"✗ Session {session_id} NOT found in Redis")
            return False
        
        print(f"✓ Session {session_id} found in Redis")
        print("\nSession State:")
        print("-" * 60)
        for key, value in sorted(session_state.items()):
            if key == "transcription_text":
                print(f"  {key}: {value[:50]}... ({len(value)} chars)")
            else:
                print(f"  {key}: {value}")
        
        # Parse readiness status
        readiness_status = session_state.get("grading_readiness_status")
        if readiness_status:
            try:
                status_enum = GradingReadinessStatus(readiness_status)
                print(f"\n  Readiness Status (enum): {status_enum}")
            except ValueError:
                print(f"\n  Readiness Status: {readiness_status} (unknown)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error checking session: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await close_redis()


async def list_all_sessions():
    """List all session keys in Redis"""
    try:
        await initialize_redis()
        client = get_redis_client().get_client()
        
        # Find all session keys
        keys = await client.keys("session:*")
        
        if not keys:
            print("No sessions found in Redis")
            return
        
        print(f"Found {len(keys)} session(s) in Redis:\n")
        for key in sorted(keys):
            session_id = key.replace("session:", "")
            print(f"  - {session_id}")
            
            # Get basic info
            session_state = await grading_publisher.get_session_state(session_id)
            if session_state:
                readiness = session_state.get("grading_readiness_status", "unknown")
                print(f"    Status: {readiness}")
        
    except Exception as e:
        print(f"✗ Error listing sessions: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_redis()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/check_redis_session.py <session_id>")
        print("  python scripts/check_redis_session.py --list-all")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == "--list-all":
        asyncio.run(list_all_sessions())
    else:
        session_id = arg
        asyncio.run(check_session(session_id))


if __name__ == "__main__":
    main()

