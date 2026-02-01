"""
Summary Persist Stage - Persists summary result to Redis.

Stores the validated summary result using the result store service.
"""

import logging
from datetime import datetime, timezone

from pipeline.base import PipelineStageBase
from schemas.summary_state import SummaryState, SummaryPipelineStage
from services.result_store import result_store

logger = logging.getLogger(__name__)


class SummaryPersistStage(PipelineStageBase):
    """
    Persists the validated summary result to Redis.
    
    Uses:
    - state.result (validated summary result dict)
    
    Produces:
    - Result stored in Redis at summary:result:{summary_id}
    """
    
    def __init__(self, store=None):
        """
        Initialize Summary Persist Stage.
        
        Args:
            store: Optional ResultStore instance (for testing)
        """
        self._store = store or result_store
    
    @property
    def name(self) -> str:
        return "SummaryPersistStage"
    
    async def run(self, state: SummaryState) -> SummaryState:
        """
        Persist the summary result to Redis.
        
        Args:
            state: Current summary state with result populated
            
        Returns:
            Updated state
            
        Raises:
            ValueError: If result is missing or storage fails
        """
        logger.debug(f"Persisting result for summary {state.summary_id}")
        
        if not state.result:
            raise ValueError("Result must be populated before persist stage")
        
        # Ensure completed_at is set
        if "completed_at" not in state.result:
            state.result["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Store to Redis
        success = await self._store.store_summary_result(state.result)
        
        if not success:
            raise ValueError(f"Failed to store summary result for {state.summary_id}")
        
        # Advance stage
        state.advance_to(SummaryPipelineStage.PERSIST)
        
        logger.info(
            f"Summary result persisted for {state.summary_id}: "
        )
        return state


def create_summary_persist_stage(store=None) -> SummaryPersistStage:
    """
    Factory function for SummaryPersistStage.
    
    Args:
        store: Optional ResultStore for testing
        
    Returns:
        Configured SummaryPersistStage instance
    """
    return SummaryPersistStage(store=store)
