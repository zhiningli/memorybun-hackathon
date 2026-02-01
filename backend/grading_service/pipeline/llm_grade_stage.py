"""
LLM Grade Stage - Returns mock grading response for development.

MVP: Returns dummy grading response for development.
Future: Will integrate with LLM provider (OpenAI, Anthropic, etc.)
when fields are finalized.
"""

import json
import logging
from pipeline.base import PipelineStageBase
from schemas.grading_state import GradingState, PipelineStage
from config import settings

logger = logging.getLogger(__name__)

# Mock response for development (before LLM is finalized)
MOCK_LLM_RESPONSE = json.dumps({
  "confidence": 0.85,
  "internal_notes": "Student correctly identified the Torricelli's theorem application but made a sign error in the final integration. The verbal explanation was clear and the diagram was well-labeled. Time was used efficiently with good pacing.",
  "score_breakdown": [
    {"dimension": "Problem Framing", "percentage": 0.90, "feedback": "Correctly identified the problem as fluid dynamics with Torricelli's law."},
    {"dimension": "Solution Execution", "percentage": 0.70, "feedback": "Good approach but made a sign error during the integration step."},
    {"dimension": "Technical Correctness", "percentage": 0.65, "feedback": "Final answer was off by a factor of 2 due to the integration error."},
    {"dimension": "Communication & Whiteboard Use", "percentage": 0.85, "feedback": "Clear verbal explanation with well-organized whiteboard work."},
    {"dimension": "Time Management", "percentage": 0.80, "feedback": "Good pacing throughout, completed within the time limit."}
  ],
  "feedback": "You correctly set up the differential equation using Torricelli's theorem and communicated your approach clearly. However, the sign error in the integration led to an incorrect final answer - double-check your integration limits next time."
})


class LLMGradeStage(PipelineStageBase):
    """
    Grades the student submission using configured LLM provider.
    """
    
    def __init__(self, mock_response: str = None):
        """
        Initialize LLM Grade Stage.
        
        Args:
            mock_response: Optional custom mock response for testing.
                           If provided, bypasses real LLM provider.
        """
        self._mock_response = mock_response
        self._provider = None
        
        if not mock_response:
            try:
                from services.llm_providers.factory import get_llm_provider
                self._provider = get_llm_provider()
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider: {e}. Falling back to mock response.")
    
    @property
    def name(self) -> str:
        return "LLMGradeStage"
    
    async def run(self, state: GradingState) -> GradingState:
        """
        Execute grading using LLM.
        """
        logger.debug(f"Grading session {state.session_id}")
        
        # Validate prompts exist
        if not state.system_prompt or not state.user_prompt:
            raise ValueError("Prompts must be set before LLM stage")
        
        response_text = ""
        
        # 1. Check global config flag first
        if settings.mock_llm_response:
            logger.info(f"[MOCK MODE - Config Flag] Returning dummy response for session {state.session_id}")
            response_text = self._mock_response or MOCK_LLM_RESPONSE
        # 2. Use Mock if provided via constructor or provider init failed
        elif self._mock_response or not self._provider:
            logger.info(f"[MOCK MODE - Fallback] Returning dummy response for session {state.session_id}")
            response_text = self._mock_response or MOCK_LLM_RESPONSE
        else:
            # 3. Use Real Provider
            try:
                logger.info(f"Generating grade with {self._provider.__class__.__name__}")
                response_text = await self._provider.generate_grade(
                    system_prompt=state.system_prompt,
                    user_prompt=state.user_prompt,
                    screenshot_data=state.screenshot_data
                )
            except Exception as e:
                logger.error(f"LLM Generation failed: {e}")
                # Fallback to mock?? Or fail?
                # For resilience, we might want to retry or fail.
                # Here we raise to let retry logic handle it.
                raise
        
        state.llm_response = response_text
        
        # Validate JSON (common for both real and mock)
        try:
            parsed = json.loads(response_text)
            logger.info(f"Graded successfully based on {len(parsed.get('score_breakdown', []))} dimensions.")
        except json.JSONDecodeError as e:
            logger.error(f"Response not valid JSON: {e}")
            # If real LLM fails JSON, this is a failure we should probably signal
            # But the stage just writes to state. 
            # Validation stage might catch this later?
            # For now, we log but proceed.
        
        state.advance_to(PipelineStage.LLM_GRADE)
        return state


def create_llm_grade_stage(mock_response: str = None) -> LLMGradeStage:
    return LLMGradeStage(mock_response=mock_response)
