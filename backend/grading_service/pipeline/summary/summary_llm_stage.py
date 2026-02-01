"""
Summary LLM Stage - Calls LLM to generate summary.

This stage is similar to LLMGradeStage but uses summary-specific
configuration (text-only model, summary prompts).
"""

import json
import logging

from pipeline.base import PipelineStageBase
from schemas.summary_state import SummaryState, SummaryPipelineStage
from config import settings

logger = logging.getLogger(__name__)

# Mock response for development
MOCK_SUMMARY_RESPONSE = json.dumps({
  "dimension_scores": [
    {"dimension": "Problem Framing", "feedback": "Strong ability to identify core principles and structure problems logically."},
    {"dimension": "Solution Execution", "feedback": "Good approach but algebraic errors in integration affected final answers."},
    {"dimension": "Technical Correctness", "feedback": "Solid understanding with occasional sign errors reducing accuracy."},
    {"dimension": "Communication & Whiteboard Use", "feedback": "Clear verbal explanations with well-organized diagrams."},
    {"dimension": "Time Management", "feedback": "Efficient pacing with good use of preparation time."}
  ],
  "analytics_summary": [
    "Communication & Whiteboard Use; Clear verbal explanations with well-organized diagrams.",
    "Problem Framing; Strong ability to identify core principles and structure problems logically.",
    "Technical Correctness; Solid understanding with occasional sign errors reducing accuracy.",
    "Moderate score spread (65-90%) showing inconsistent execution.",
    "Strong setup and communication, weaker execution."
  ],
  "overall_feedback": "You showed excellent problem-solving intuition and communication throughout the interview. Your ability to identify relevant principles and explain reasoning clearly was impressive, with consistently organized whiteboard work.\n\nTechnical execution needs improvement. Calculation errors, particularly with signs during integration, prevented correct final answers. Focus on verifying each step to improve accuracy.",
  "key_strengths": [
    "Consistently identified the core objective of each problem before attempting a solution",
    "Demonstrated structured problem-solving with clear step-by-step reasoning",
    "Applied relevant engineering concepts accurately across multiple questions",
    "Used diagrams and written working effectively to support explanations"
  ],
  "key_strengths": [
  "Consistently identified the core objective of each problem before attempting a solution",
  "Demonstrated structured problem-solving with clear step-by-step reasoning",
  "Applied relevant engineering concepts accurately across multiple questions",
  "Used diagrams and written working effectively to support explanations"
],
  "areas_for_improvement": [
    "Double-check signs during integration",
    "Verify intermediate calculations",
    "Practice dimensional analysis",
    "Slow down during critical steps"
  ]
})


class SummaryLLMStage(PipelineStageBase):
    """
    Generates summary using configured LLM provider.
    
    Uses summary-specific configuration from settings.
    """
    
    def __init__(self, mock_response: str = None):
        """
        Initialize Summary LLM Stage.
        
        Args:
            mock_response: Optional custom mock response for testing
        """
        self._mock_response = mock_response
        self._provider = None
        
        if not mock_response:
            try:
                from services.llm_providers.factory import get_llm_provider
                # Use summary-specific model (gemini-1.5-flash for text-only)
                self._provider = get_llm_provider(
                    model_override=settings.summary_llm_model
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider for summary: {e}")
    
    @property
    def name(self) -> str:
        return "SummaryLLMStage"
    
    async def run(self, state: SummaryState) -> SummaryState:
        """
        Execute summary generation using LLM.
        
        Args:
            state: Current summary state with prompts
            
        Returns:
            Updated state with llm_response
        """
        logger.debug(f"Generating summary for {state.summary_id}")
        
        if not state.system_prompt or not state.user_prompt:
            raise ValueError("Prompts must be set before LLM stage")
        
        response_text = ""
        
        # Check global mock flag first
        if settings.mock_llm_response:
            logger.info(f"[MOCK MODE] Returning dummy summary for {state.summary_id}")
            response_text = self._mock_response or MOCK_SUMMARY_RESPONSE
        elif self._mock_response or not self._provider:
            logger.info(f"[MOCK MODE - Fallback] Returning dummy summary for {state.summary_id}")
            response_text = self._mock_response or MOCK_SUMMARY_RESPONSE
        else:
            # Use real provider (text-only, no screenshot)
            try:
                logger.info(f"Generating summary with {self._provider.__class__.__name__}")
                response_text = await self._provider.generate_summary(
                    system_prompt=state.system_prompt,
                    user_prompt=state.user_prompt
                )
            except Exception as e:
                logger.error(f"LLM generation failed for summary: {e}")
                raise
        
        state.llm_response = response_text
        
        # Validate JSON
        try:
            parsed = json.loads(response_text)
            logger.info(f"Summary generated successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Summary response not valid JSON: {e}")
        
        state.advance_to(SummaryPipelineStage.LLM_SUMMARIZE)
        return state


def create_summary_llm_stage(mock_response: str = None) -> SummaryLLMStage:
    """Factory function for SummaryLLMStage."""
    return SummaryLLMStage(mock_response=mock_response)
