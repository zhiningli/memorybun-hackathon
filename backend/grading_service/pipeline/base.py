"""
Base class for pipeline stages.

All pipeline stages inherit from PipelineStageBase and implement
the run() method to process GradingState.
"""

from abc import ABC, abstractmethod
import logging
import time
from schemas.grading_state import GradingState

logger = logging.getLogger(__name__)


class PipelineStageBase(ABC):
    """
    Abstract base class for pipeline stages.
    
    Each stage processes the grading state and returns the updated state.
    Stages should be stateless and idempotent when possible.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this stage."""
        pass
    
    @abstractmethod
    async def run(self, state: GradingState) -> GradingState:
        """
        Execute this pipeline stage.
        
        Args:
            state: Current grading state
            
        Returns:
            Updated grading state
            
        Raises:
            Exception: If stage processing fails
        """
        pass
    
    async def __call__(self, state: GradingState) -> GradingState:
        """
        Allow stage to be called directly.
        
        Includes timing instrumentation for profiling pipeline performance.
        """
        logger.info(f"[STAGE_START] {self.name}")
        start_time = time.perf_counter()
        
        try:
            result = await self.run(state)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            # Handle both GradingState (session_id) and SummaryState (summary_id)
            state_id = getattr(state, 'session_id', None) or getattr(state, 'summary_id', 'unknown')
            logger.info(
                f"[STAGE_COMPLETE] {self.name} | "
                f"duration_ms={elapsed_ms:.2f} | "
                f"id={state_id}"
            )
            return result
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[STAGE_FAILED] {self.name} | "
                f"duration_ms={elapsed_ms:.2f} | "
                f"error={e}"
            )
            raise
