"""
Summary Pipeline Orchestrator - Runs summary stages in sequence.

The orchestrator manages the summary pipeline workflow, running
each stage in order and handling errors/state transitions.
"""

import logging
from typing import List, Optional

from pipeline.base import PipelineStageBase
from pipeline.summary.summary_context_fetch_stage import SummaryContextFetchStage
from pipeline.summary.summary_prompt_build_stage import SummaryPromptBuildStage
from pipeline.summary.summary_llm_stage import SummaryLLMStage
from pipeline.summary.summary_validate_stage import SummaryValidateStage, SummaryValidationError
from pipeline.summary.summary_persist_stage import SummaryPersistStage
from schemas.summary_state import SummaryState, SummaryPipelineStage

logger = logging.getLogger(__name__)


class SummaryOrchestrator:
    """
    Runs the summary pipeline stages in sequence.
    
    Pipeline Order:
    1. SummaryContextFetchStage - Fetch all session results
    2. SummaryPromptBuildStage - Build prompts
    3. SummaryLLMStage - Generate summary with LLM
    4. SummaryValidateStage - Validate output
    5. SummaryPersistStage - Save result
    """
    
    def __init__(self, stages: Optional[List[PipelineStageBase]] = None):
        """
        Initialize orchestrator with pipeline stages.
        
        Args:
            stages: Optional custom list of stages (for testing)
        """
        if stages is not None:
            self._stages = stages
        else:
            self._stages = [
                SummaryContextFetchStage(),
                SummaryPromptBuildStage(),
                SummaryLLMStage(),
                SummaryValidateStage(),
                SummaryPersistStage(),
            ]
    
    @property
    def stages(self) -> List[PipelineStageBase]:
        """Get the list of pipeline stages."""
        return self._stages
    
    async def run_pipeline(self, task_data: dict) -> SummaryState:
        """
        Run the complete summary pipeline.
        
        Args:
            task_data: Dict with summary task fields
                - summary_id: str
                - session_ids: List[str]
                - session_results: Optional[List[dict]] (pre-fetched)
            
        Returns:
            Final SummaryState with result
            
        Raises:
            ValueError: If required fields are missing
            SummaryValidationError: If validation fails
            Exception: If any stage fails
        """
        import time
        
        logger.info("[PIPELINE_START] Summary pipeline initiated")
        pipeline_start = time.perf_counter()
        
        # Validate required fields
        required = ["summary_id", "session_ids"]
        for field in required:
            if field not in task_data:
                raise ValueError(f"Missing required field: {field}")
        
        try:
            # Create initial state
            state = SummaryState.from_task(task_data)
            logger.info(f"[PIPELINE_INFO] summary_id={state.summary_id}")
            
            # Run each stage in sequence
            for stage in self._stages:
                logger.debug(f"Running stage: {stage.name}")
                state = await stage(state)
                logger.debug(f"Stage {stage.name} completed, state: {state.stage}")
            
            # Mark as completed
            state.advance_to(SummaryPipelineStage.COMPLETED)
            
            total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.info(
                f"[PIPELINE_COMPLETE] summary_id={state.summary_id} | "
                f"total_duration_ms={total_duration_ms:.2f}"
            )
            
            return state
            
        except SummaryValidationError as e:
            total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.error(f"[PIPELINE_FAILED] Summary validation failed | duration_ms={total_duration_ms:.2f} | error={e}")
            raise
        except Exception as e:
            total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.error(f"[PIPELINE_FAILED] Summary pipeline error | duration_ms={total_duration_ms:.2f} | error={e}")
            raise
    
    async def run_from_state(self, state: SummaryState) -> SummaryState:
        """
        Run pipeline from an existing state.
        
        Useful for resuming or testing from a specific point.
        
        Args:
            state: Existing SummaryState
            
        Returns:
            Final SummaryState with result
        """
        logger.info(f"Resuming summary pipeline for {state.summary_id} at stage {state.stage}")
        
        try:
            for stage in self._stages:
                state = await stage(state)
            
            state.advance_to(SummaryPipelineStage.COMPLETED)
            logger.info(f"Summary pipeline completed for {state.summary_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"Summary pipeline failed for {state.summary_id}: {e}")
            state.fail(str(e))
            raise


def create_summary_orchestrator(
    stages: Optional[List[PipelineStageBase]] = None
) -> SummaryOrchestrator:
    """
    Factory function for SummaryOrchestrator.
    
    Args:
        stages: Optional custom stages for testing
        
    Returns:
        Configured SummaryOrchestrator instance
    """
    return SummaryOrchestrator(stages=stages)
