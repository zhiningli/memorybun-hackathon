import asyncio
import json
import logging
import sys
import os
import argparse
from datetime import datetime

# Add parent directory to path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from services.redis_client import get_redis_client
from services.grading_queue import grading_queue
from schemas.grading_state import GradingState
from pipeline.context_fetch_stage import ContextFetchStage
from pipeline.prompt_build_stage import PromptBuildStage
from pipeline.llm_grade_stage import LLMGradeStage
from pipeline.persist_stage import PersistStage
from pipeline.validate_stage import ValidateStage
from services.rubric_provider import rubric_provider
from services.result_store import ResultStore

from typing import Union
from schemas.grading_result import GradingResult

class MockResultStore(ResultStore):
    async def store_result(self, result: Union[dict, GradingResult]) -> bool:
        print("\n" + "="*60)
        print("MOCK STORE: PRETENDING TO STORE RESULT TO REDIS")
        print("="*60)
        
        data = result
        if isinstance(result, GradingResult):
            data = result.model_dump()
            
        print(json.dumps(data, indent=2, default=str))
        print("-" * 60)
        return True

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Valid 1x1 pixel transparent PNG
MOCK_SCREENSHOT_DATA = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff\x3f\x03\x00\x05\xfe\x02\xfe\xa7V:\xe7\x00\x00\x00\x00IEND\xaeB`\x82'
)

def print_state_summary(state: GradingState, title: str):
    """Print a summary of the grading state."""
    print("\n" + "="*60)
    print(f"STATE AFTER: {title}")
    print("="*60)
    # Convert to dict and handle bytes for printing
    data = state.model_dump()
    if data.get('screenshot_data'):
        data['screenshot_data'] = f"<{len(data['screenshot_data'])} bytes>"
    
    print(json.dumps(data, indent=2, default=str))
    print("-" * 60)

async def enqueue_task(session_id: str, student_id: str, question_id: str = "1"):
    """Enqueue a mock grading task to Redis."""
    logger.info(f"Enqueuing task for session {session_id}")
    
    # Initialize Redis client
    await get_redis_client().connect()
    
    task = {
        "session_id": session_id,
        "student_id": student_id,
        "question_id": question_id,
        "transcription_text": "This is a mock transcription text for testing purposes.",
        "screenshot_key": "screenshot.png",
        "thinking_time": 5.0,
        "speaking_time": 10.0
    }
    
    try:
        # Enqueue dict directly as per grading_queue.py implementation
        await grading_queue.enqueue(task)
        logger.info(f"Successfully enqueued task: {task}")
    except Exception as e:
        logger.error(f"Failed to enqueue task: {e}")
    finally:
        await get_redis_client().disconnect()

async def run_local_pipeline(session_id: str, student_id: str, question_id: str):
    """Run the pipeline locally (full flow)."""
    logger.info(f"Running local pipeline for session {session_id}")
    
    # Configure settings for local execution
    # This assumes question-service is reachable at localhost:8000
    if "question-service" in settings.question_service_url:
         # If default docker hostname is used, replace with localhost for local script
         settings.question_service_url = "http://localhost:8000"
    
    # Create initial state
    task_data = {
        "session_id": session_id,
        "student_id": student_id,
        "question_id": question_id,
        "transcription_text": "This is a mock transcription text for testing purposes.",
        "screenshot_key": "screenshot.png",
        "thinking_time": 5.0,
        "speaking_time": 10.0
    }
    
    state = GradingState.from_task(task_data)
    print_state_summary(state, "INITIALIZATION")
    
    try:
        # Load rubrics from question service first
        print("\nLoading Rubrics...")
        await rubric_provider.load_rubrics()
        print(f"[OK] Rubrics loaded: {list(rubric_provider._cache.keys())}")
        
        # Stage 1: Context Fetch
        print("\nRunning Context Fetch Stage...")
        context_stage = ContextFetchStage()
        state = await context_stage.run(state)
        
        # Inject mock screenshot data (since the URL fetch likely failed or we want to override)
        # We do this here to simulate a successful fetch and allow downstream stages to use it
        state.screenshot_data = MOCK_SCREENSHOT_DATA
        print(f"[OK] Injected mock screenshot data ({len(state.screenshot_data)} bytes)")
        
        print_state_summary(state, "CONTEXT FETCH STAGE")
        
        # Stage 2: Prompt Build
        print("\nRunning Prompt Build Stage...")
        prompt_stage = PromptBuildStage()
        state = await prompt_stage.run(state)
        
        print_state_summary(state, "PROMPT BUILD STAGE")
        
        # Stage 3: LLM Grade
        print("\nRunning LLM Grade Stage...")
        # Use mock response explicitly or rely on settings
        llm_stage = LLMGradeStage(mock_response=None) # Will use MOCK_LLM_RESPONSE default in stage if no provider
        state = await llm_stage.run(state)
        
        print_state_summary(state, "LLM GRADE STAGE")
        
        # Stage 4: Validate
        print("\nRunning Validate Stage...")
        validate_stage = ValidateStage()
        state = await validate_stage.run(state)
        
        print_state_summary(state, "VALIDATE STAGE")

        # Stage 5: Persist
        print("\nRunning Persist Stage...")
        # Use mock mock store
        persist_stage = PersistStage(store=MockResultStore())
        state = await persist_stage.run(state)
        
        print_state_summary(state, "PERSIST STAGE")
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Debug Grading Pipeline")
    parser.add_argument("mode", choices=["enqueue", "local"], help="Mode: enqueue to Redis or run local simulation")
    parser.add_argument("--session_id", default=f"debug-{datetime.now().strftime('%Y%m%d%H%M%S')}", help="Session ID")
    parser.add_argument("--student_id", default="student-123", help="Student ID")
    parser.add_argument("--question_id", default="1", help="Question ID")
    
    args = parser.parse_args()
    
    if args.mode == "enqueue":
        asyncio.run(enqueue_task(args.session_id, args.student_id, args.question_id))
    else:
        asyncio.run(run_local_pipeline(args.session_id, args.student_id, args.question_id))

if __name__ == "__main__":
    main()
