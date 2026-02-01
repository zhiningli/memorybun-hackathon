"""
Summary Context Fetch Stage - Fetches all session grading results from Redis.

This stage retrieves the grading results for all sessions included in the summary.
"""

import logging
from typing import List, Dict, Any, Optional

from pipeline.base import PipelineStageBase
from schemas.summary_state import SummaryState, SummaryPipelineStage
from services.result_store import result_store

logger = logging.getLogger(__name__)


class SummaryContextFetchStage(PipelineStageBase):
    """
    Fetches grading results for all sessions in the summary.
    
    Uses:
    - state.session_ids (list of session IDs to fetch)
    
    Produces:
    - state.session_results (list of grading results from Redis)
    """
    
    def __init__(self, store=None):
        """
        Initialize Summary Context Fetch Stage.
        
        Args:
            store: Optional ResultStore instance (for testing)
        """
        self._store = store or result_store
    
    @property
    def name(self) -> str:
        return "SummaryContextFetchStage"
    
    async def run(self, state: SummaryState) -> SummaryState:
        """
        Fetch grading results for all sessions.
        
        Args:
            state: Current summary state
            
        Returns:
            Updated state with session_results populated
            
        Raises:
            ValueError: If any session result is not found
        """
        logger.debug(f"Fetching results for {len(state.session_ids)} sessions")
        
        # If results are already provided (pre-fetched), skip
        if state.session_results and len(state.session_results) == len(state.session_ids):
            logger.info(f"Using pre-fetched results for {len(state.session_results)} sessions")
            state.advance_to(SummaryPipelineStage.CONTEXT_FETCH)
            return state
        
        # Fetch results for each session
        session_results: List[Dict[str, Any]] = []
        missing_sessions: List[str] = []
        
        for session_id in state.session_ids:
            result = await self._store.get_result(session_id)
            
            if result is None:
                missing_sessions.append(session_id)
                logger.warning(f"No grading result found for session {session_id}")
            else:
                # Convert Pydantic model to dict for downstream processing
                session_results.append(result.model_dump())
                logger.debug(f"Fetched result for session {session_id}")
        
        # Check if any results are missing
        if missing_sessions:
            error_msg = f"Missing grading results for sessions: {missing_sessions}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        state.session_results = session_results
        state.advance_to(SummaryPipelineStage.CONTEXT_FETCH)
        
        logger.info(
            f"Fetched {len(session_results)} session results for summary {state.summary_id}"
        )
        return state


def create_summary_context_fetch_stage(store=None) -> SummaryContextFetchStage:
    """
    Factory function for SummaryContextFetchStage.
    
    Args:
        store: Optional ResultStore for testing
        
    Returns:
        Configured SummaryContextFetchStage instance
    """
    return SummaryContextFetchStage(store=store)
