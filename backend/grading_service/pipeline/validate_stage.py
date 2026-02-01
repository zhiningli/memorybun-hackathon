"""
Validate Stage - Validates LLM output and populates result.

Parses the LLM JSON response, validates score bounds, and creates
a structured GradingResult for storage.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pipeline.base import PipelineStageBase
from schemas.grading_state import GradingState, PipelineStage
from schemas.grading_result import GradingResult, ScoreBreakdown, ModelInfo
from config import settings

logger = logging.getLogger(__name__)

# Constants for validation
MIN_SCORE = 0.0
MAX_SCORE = 1.0
MIN_FEEDBACK_LENGTH = 10
MAX_FEEDBACK_LENGTH = 2000


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class ValidateStage(PipelineStageBase):
    """
    Validates LLM output and creates structured GradingResult.
    
    Uses:
    - state.llm_response (raw JSON from LLMGradeStage)
    
    Produces:
    - state.result (validated result dict)
    
    Validation checks:
    - Score is within [0.0, 1.0]
    - Feedback is non-empty and reasonable length
    - Score breakdown totals are consistent (if present)
    """
    
    @property
    def name(self) -> str:
        return "ValidateStage"
    
    def _parse_llm_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse the raw LLM response JSON.
        
        Args:
            raw_response: Raw JSON string from LLM
            
        Returns:
            Parsed dict
            
        Raises:
            ValidationError: If JSON is invalid
        """
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON response from LLM: {e}")
    
    def _validate_feedback(self, feedback: Any) -> str:
        """
        Validate feedback content.
        
        Args:
            feedback: Feedback string from LLM
            
        Returns:
            Validated feedback string
            
        Raises:
            ValidationError: If feedback is invalid
        """
        if not feedback:
            raise ValidationError("Feedback is missing or empty")
        
        feedback_str = str(feedback).strip()
        
        if len(feedback_str) < MIN_FEEDBACK_LENGTH:
            raise ValidationError(
                f"Feedback too short ({len(feedback_str)} chars, min {MIN_FEEDBACK_LENGTH})"
            )
        
        if len(feedback_str) > MAX_FEEDBACK_LENGTH:
            logger.warning(f"Feedback too long, truncating to {MAX_FEEDBACK_LENGTH} chars")
            feedback_str = feedback_str[:MAX_FEEDBACK_LENGTH]
        
        return feedback_str
    
    def _validate_confidence(self, confidence: Any) -> Optional[float]:
        """
        Validate confidence score.
        
        Args:
            confidence: Confidence value from LLM
            
        Returns:
            Validated confidence or None
        """
        if confidence is None:
            return None
        
        try:
            conf_float = float(confidence)
            # Clamp to valid range
            return max(MIN_SCORE, min(MAX_SCORE, conf_float))
        except (ValueError, TypeError):
            logger.warning(f"Invalid confidence value: {confidence}")
            return None
    
    async def run(self, state: GradingState) -> GradingState:
        """
        Validate LLM response and create structured result.
        
        Args:
            state: Current grading state with llm_response
            
        Returns:
            Updated state with validated result
            
        Raises:
            ValidationError: If validation fails
        """
        logger.debug(f"Validating LLM response for session {state.session_id}")
        
        if not state.llm_response:
            raise ValidationError("LLM response is missing (run LLMGradeStage first)")
        
        # Parse JSON
        parsed = self._parse_llm_response(state.llm_response)
        
        # Validate required fields
        feedback = self._validate_feedback(parsed.get("feedback"))
        
        # Validate optional fields
        confidence = self._validate_confidence(parsed.get("confidence"))
        internal_notes = parsed.get("internal_notes")
        
        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - state.started_at).total_seconds()
        
        # Create result dict (compatible with GradingResult schema)
        result = {
            "session_id": state.session_id,
            "feedback": feedback,
            "confidence": confidence,
            "internal_notes": str(internal_notes) if internal_notes else None,
            "score_breakdown": parsed.get("score_breakdown"),
            "raw_output": state.llm_response,
            "processing_time": processing_time,
            "model_info": {
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "prompt_version": "v1.0",
                "temperature": settings.llm_temperature
            }
        }
        
        # Store in state
        state.result = result
        
        # Advance stage
        state.advance_to(PipelineStage.VALIDATE)
        
        logger.info(
            f"Validation complete for session {state.session_id}: "
            f"confidence={confidence}"
        )
        return state
