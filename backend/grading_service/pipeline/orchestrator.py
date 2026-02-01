"""
Pipeline Orchestrator - Runs grading stages in sequence.

The orchestrator manages the grading pipeline workflow, running
each stage in order and handling errors/state transitions.
"""

import logging
import time
from typing import List, Type, Optional
from pipeline.base import PipelineStageBase
from pipeline.task_decode_stage import TaskDecodeStage, TaskDecodeError
from pipeline.context_fetch_stage import ContextFetchStage
from pipeline.prompt_build_stage import PromptBuildStage
from pipeline.llm_grade_stage import LLMGradeStage
from pipeline.validate_stage import ValidateStage, ValidationError
from pipeline.persist_stage import PersistStage
from schemas.grading_state import GradingState, PipelineStage

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Runs the grading pipeline stages in sequence.
    
    Pipeline Order:
    1. TaskDecodeStage - Validate input
    2. ContextFetchStage - Fetch rubric/answers
    3. PromptBuildStage - Build prompts
    4. LLMGradeStage - Grade with LLM
    5. ValidateStage - Validate output
    6. PersistStage - Save result
    
    The orchestrator handles:
    - Stage sequencing
    - Error handling and state transitions
    - Logging and audit trail
    """
    
    def __init__(
        self,
        stages: Optional[List[PipelineStageBase]] = None
    ):
        """
        Initialize orchestrator with pipeline stages.
        
        Args:
            stages: Optional custom list of stages (for testing)
        """
        if stages is not None:
            self._stages = stages
        else:
            # Default pipeline
            self._stages = [
                ContextFetchStage(),
                PromptBuildStage(),
                LLMGradeStage(),
                ValidateStage(),
                PersistStage(),
            ]
        
        self._task_decode = TaskDecodeStage()
    
    @property
    def stages(self) -> List[PipelineStageBase]:
        """Get the list of pipeline stages."""
        return self._stages
    
    async def run_pipeline(self, task_data: str | dict) -> GradingState:
        """
        Run the complete grading pipeline.
        
        Args:
            task_data: JSON string or dict from queue
            
        Returns:
            Final GradingState with result
            
        Raises:
            TaskDecodeError: If task decoding fails
            ValidationError: If validation fails
            Exception: If any stage fails
        """
        logger.info("[PIPELINE_START] Grading pipeline initiated")
        pipeline_start = time.perf_counter()
        
        try:
            # Decode task and create initial state
            state = await self._task_decode.decode_and_create(task_data)
            logger.info(f"[PIPELINE_INFO] session_id={state.session_id}")
            
            # Run each stage in sequence
            for stage in self._stages:
                logger.debug(f"Running stage: {stage.name}")
                state = await stage(state)
                logger.debug(f"Stage {stage.name} completed, state: {state.stage}")
            
            # Mark as completed
            state.advance_to(PipelineStage.COMPLETED)
            
            total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.info(
                f"[PIPELINE_COMPLETE] session_id={state.session_id} | "
                f"total_duration_ms={total_duration_ms:.2f}"
            )
            
            return state
            
        except TaskDecodeError as e:
            total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.error(f"[PIPELINE_FAILED] Task decode failed | duration_ms={total_duration_ms:.2f} | error={e}")
            raise
        except ValidationError as e:
            total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.error(f"[PIPELINE_FAILED] Validation failed | duration_ms={total_duration_ms:.2f} | error={e}")
            raise
        except Exception as e:
            total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.error(f"[PIPELINE_FAILED] Pipeline error | duration_ms={total_duration_ms:.2f} | error={e}")
            raise
    
    async def run_from_state(self, state: GradingState) -> GradingState:
        """
        Run pipeline from an existing state.
        
        Useful for resuming or testing from a specific point.
        
        Args:
            state: Existing GradingState
            
        Returns:
            Final GradingState with result
        """
        logger.info(f"Resuming pipeline for session {state.session_id} at stage {state.stage}")
        
        try:
            # Run remaining stages
            for stage in self._stages:
                state = await stage(state)
            
            # Mark as completed
            state.advance_to(PipelineStage.COMPLETED)
            logger.info(f"Pipeline completed for session {state.session_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"Pipeline failed for session {state.session_id}: {e}")
            state.fail(str(e))
            raise


def create_orchestrator(
    stages: Optional[List[PipelineStageBase]] = None
) -> Orchestrator:
    """
    Factory function for Orchestrator.
    
    Args:
        stages: Optional custom stages for testing
        
    Returns:
        Configured Orchestrator instance
    """
    return Orchestrator(stages=stages)
