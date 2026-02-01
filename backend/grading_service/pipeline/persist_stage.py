"""
Persist Stage - Saves grading result to ResultStore.

Final stage in the pipeline. Persists the validated result
to Redis for frontend polling.
"""

import logging
from pipeline.base import PipelineStageBase
from schemas.grading_state import GradingState, PipelineStage
from services.result_store import result_store, ResultStore

logger = logging.getLogger(__name__)


class PersistStage(PipelineStageBase):
    """
    Persists grading result to storage.
    
    Uses:
    - state.result (validated result from ValidateStage)
    
    Actions:
    - Saves result to ResultStore (Redis)
    - Sets status to completed
    
    Note: This is the final stage before COMPLETED.
    """
    
    def __init__(self, store: ResultStore = None):
        """
        Initialize Persist Stage.
        
        Args:
            store: Optional ResultStore instance (for testing)
        """
        self._store = store or result_store
    
    @property
    def name(self) -> str:
        return "PersistStage"
    
    async def run(self, state: GradingState) -> GradingState:
        """
        Persist the grading result to storage.
        
        Args:
            state: Current grading state with validated result
            
        Returns:
            Updated state with stage set to PERSIST
            
        Raises:
            ValueError: If result is missing
            Exception: If persistence fails
        """
        logger.debug(f"Persisting result for session {state.session_id}")
        
        # Validate result exists
        if not state.result:
            raise ValueError("Result must be set before persist stage (run ValidateStage first)")
        
        try:
            # Store result
            success = await self._store.store_result(state.result)
            
            if not success:
                raise Exception("Failed to store result in Redis")
            
            # Advance stage
            state.advance_to(PipelineStage.PERSIST)
            
            logger.info(f"Result persisted for session {state.session_id}")
            return state
            
        except Exception as e:
            logger.error(f"Persist failed for session {state.session_id}: {e}")
            raise


def create_persist_stage(store: ResultStore = None) -> PersistStage:
    """
    Factory function for PersistStage.
    
    Args:
        store: Optional ResultStore for testing
        
    Returns:
        Configured PersistStage instance
    """
    return PersistStage(store=store)
