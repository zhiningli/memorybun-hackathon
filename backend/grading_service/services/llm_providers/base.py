from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement this interface to be used by the grading service.
    """
    
    @abstractmethod
    async def generate_grade(
        self, 
        system_prompt: str, 
        user_prompt: str,
        screenshot_data: Optional[bytes] = None
    ) -> str:
        """
        Generate a grading response from the LLM.
        
        Args:
            system_prompt: The system instructions (rubric, role)
            user_prompt: The student submission content with question context
            screenshot_data: Optional raw screenshot bytes (PNG/JPEG/WebP)
                           Fetched by context_fetch_stage from transcription service
            
        Returns:
            JSON string with grading result:
            {
                "score": float (0.0 to 1.0),
                "feedback": str,
                "confidence": float (0.0 to 1.0),
                "internal_notes": str (optional),
                "score_breakdown": [
                    {"dimension": str, "score": float, "max_score": float, "feedback": str}
                ]
            }
            
        Raises:
            Exception: If generation fails or response is invalid
        """
        pass
    
    @abstractmethod
    async def generate_summary(
        self, 
        system_prompt: str, 
        user_prompt: str
    ) -> str:
        """
        Generate a session summary response from the LLM.
        
        This is text-only (no screenshot) and uses a summary-specific schema.
        
        Args:
            system_prompt: The system instructions for summarization
            user_prompt: The aggregated session results for summarization
            
        Returns:
            JSON string with summary result:
            {
                "dimension_scores": [{"dimension": str, "feedback": str}],
                "analytics_summary": [str],
                "overall_feedback": str,
                "key_strengths": [str],
                "areas_for_improvement": [str]
            }
            
        Raises:
            Exception: If generation fails or response is invalid
        """
        pass

