"""
Summary Validate Stage - Validates LLM output and populates summary result.

Parses the LLM JSON response, validates structure, and creates
a structured SummaryResult for storage.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pipeline.base import PipelineStageBase
from schemas.summary_state import SummaryState, SummaryPipelineStage
from schemas.summary_result import SummaryResult, DimensionScore, SUMMARY_DIMENSIONS
from config import settings

logger = logging.getLogger(__name__)


class SummaryValidationError(Exception):
    """Raised when summary validation fails."""
    pass


class SummaryValidateStage(PipelineStageBase):
    """
    Validates LLM output and creates structured SummaryResult.
    
    Uses:
    - state.llm_response (raw JSON from LLM)
    
    Produces:
    - state.result (validated result dict)
    
    Validation checks:
    - Valid JSON structure
    - Required fields present
    - Dimension feedback is valid
    """
    
    @property
    def name(self) -> str:
        return "SummaryValidateStage"
    
    def _parse_llm_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse the raw LLM response JSON.
        
        Args:
            raw_response: Raw JSON string from LLM
            
        Returns:
            Parsed dict
            
        Raises:
            SummaryValidationError: If JSON is invalid
        """
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise SummaryValidationError(f"Invalid JSON response from LLM: {e}")
    
    def _validate_dimension_scores(
        self, 
        dimension_scores: Any
    ) -> List[Dict[str, Any]]:
        """
        Validate dimension scores.
        
        Args:
            dimension_scores: List of dimension score dicts from LLM
            
        Returns:
            Validated list of dimension score dicts
            
        Raises:
            SummaryValidationError: If validation fails
        """
        if not dimension_scores:
            raise SummaryValidationError("dimension_scores is missing")
        
        if not isinstance(dimension_scores, list):
            raise SummaryValidationError("dimension_scores must be a list")
        
        validated = []
        found_dimensions = set()
        
        for item in dimension_scores:
            if not isinstance(item, dict):
                continue
            
            dimension = item.get("dimension", "")
            feedback = item.get("feedback", "")
            
            found_dimensions.add(dimension)
            validated.append({
                "dimension": dimension,
                "feedback": str(feedback) if feedback else ""
            })
        
        # Check all required dimensions are present
        missing = set(SUMMARY_DIMENSIONS) - found_dimensions
        if missing:
            logger.warning(f"Missing dimensions in LLM response: {missing}")
            # Add placeholder for missing dimensions
            for dim in missing:
                validated.append({
                    "dimension": dim,
                    "feedback": "Not evaluated"
                })
        
        return validated
    
    def _validate_string_list(
        self, 
        items: Any, 
        field_name: str, 
        min_items: int = 1
    ) -> List[str]:
        """
        Validate a list of strings.
        
        Args:
            items: List from LLM
            field_name: Name of field for error messages
            min_items: Minimum number of items required
            
        Returns:
            Validated list of strings
        """
        if not items:
            logger.warning(f"{field_name} is missing, using empty list")
            return []
        
        if not isinstance(items, list):
            logger.warning(f"{field_name} is not a list, wrapping")
            return [str(items)]
        
        validated = [str(item) for item in items if item]
        
        if len(validated) < min_items:
            logger.warning(f"{field_name} has fewer than {min_items} items")
        
        return validated
    
    async def run(self, state: SummaryState) -> SummaryState:
        """
        Validate LLM response and create structured result.
        
        Args:
            state: Current summary state with llm_response
            
        Returns:
            Updated state with validated result
            
        Raises:
            SummaryValidationError: If validation fails
        """
        logger.debug(f"Validating LLM response for summary {state.summary_id}")
        
        if not state.llm_response:
            raise SummaryValidationError("LLM response is missing")
        
        # Parse JSON
        parsed = self._parse_llm_response(state.llm_response)
        
        # Validate fields
        dimension_scores = self._validate_dimension_scores(parsed.get("dimension_scores"))
        analytics_summary = self._validate_string_list(
            parsed.get("analytics_summary"), "analytics_summary", min_items=1
        )
        overall_feedback = str(parsed.get("overall_feedback", "")).strip()
        if not overall_feedback:
            overall_feedback = "Summary not available."
        
        key_strengths = self._validate_string_list(
            parsed.get("key_strengths"), "key_strengths", min_items=1
        )
        areas_for_improvement = self._validate_string_list(
            parsed.get("areas_for_improvement"), "areas_for_improvement", min_items=1
        )
        
        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - state.started_at).total_seconds()
        
        # Create result dict (compatible with SummaryResult schema)
        result = {
            "summary_id": state.summary_id,
            "session_ids": state.session_ids,
            "dimension_scores": dimension_scores,
            "analytics_summary": analytics_summary,
            "overall_feedback": overall_feedback,
            "key_strengths": key_strengths,
            "areas_for_improvement": areas_for_improvement,
            "model_info": {
                "provider": settings.summary_llm_provider,
                "model": settings.summary_llm_model,
                "prompt_version": "v1.0",
                "temperature": settings.summary_llm_temperature
            },
            "processing_time": processing_time,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store in state
        state.result = result
        
        # Advance stage
        state.advance_to(SummaryPipelineStage.VALIDATE)
        
        logger.info(
            f"Summary validation complete for {state.summary_id}: "
        )
        return state


def create_summary_validate_stage() -> SummaryValidateStage:
    """Factory function for SummaryValidateStage."""
    return SummaryValidateStage()
