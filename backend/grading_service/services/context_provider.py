"""
Context Provider - Fetches rubrics and reference answers for grading.

MVP stub implementation that returns mock data.
Designed for future expansion to fetch from question_service via HTTP.
"""

import logging
import httpx
from typing import Dict, Optional, Any
from config import settings
from services.rubric_provider import rubric_provider, RubricProvider
from schemas import Context, QuestionContext

logger = logging.getLogger(__name__)

class ContextProvider:
    """
    Provides context (rubrics, reference answers) for grading.
    
    Fetches reference answers from question_service via HTTP.
    Delegates rubric retrieval to RubricProvider.
    """
    
    # Fields to keep when reducing metadata (updated for new schema)
    _QUESTION_FIELDS = {
        "question_details",
        "title", 
        "think_time_limit_seconds",
        "record_time_limit_seconds",
        "question_image_url",
        "topics",
        "subjects",
    }
    
    _ANSWER_FIELDS = {
        "text_answer",
        "graph_answer_url",
        "ideal_answer_structure",
        "key_constraints_to_mention",
    }
    
    def __init__(self, rubric_provider_instance: RubricProvider = None):
        """
        Initialize ContextProvider.
        
        Args:
            rubric_provider_instance: Optional RubricProvider (default: global instance)
        """
        self._rubric_provider = rubric_provider_instance or rubric_provider
        self._base_url = settings.question_service_url
    
    # ==================== Reducer Helpers ====================
    
    def _reduce_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reduce question metadata to only grading-relevant fields.
        
        Keeps: question_details, title, think_time_limit_seconds, record_time_limit_seconds, 
               question_image_url, topics, subjects
        """
        if not question:
            return {}
        return {k: v for k, v in question.items() if k in self._QUESTION_FIELDS}
    
    def _reduce_answer(self, answer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reduce answer metadata to only grading-relevant fields.
        
        Keeps: text_answer, graph_answer_url
        """
        if not answer:
            return {}
        return {k: v for k, v in answer.items() if k in self._ANSWER_FIELDS}
    
    def _reduce_rubric(self, rubric: Dict[str, Any]) -> Dict[str, Any]:
        """
        Keep all rubric fields (no reduction needed).
        """
        return rubric if rubric else {}
    
    # ==================== Data Fetching ====================
    
    async def gen_rubric_by_rubric_id(self, rubric_id: int) -> Dict[str, Any]:
        """
        Get rubric for a specific category from RubricProvider.
        """
        rubric_model = self._rubric_provider.get_rubric_by_rubric_id(rubric_id)
        if rubric_model:
            return rubric_model.model_dump()
        return {}
    
    async def gen_reference_answer_by_question_id(self, question_id: int) -> Dict[str, Any]:
        """
        Fetch model/reference answer for a question from Question Service.
        
        Returns:
            Dict with text_answer and graph_answer_url fields (reduced)
        """
        if not question_id:
            return {}
            
        logger.debug(f"Fetching reference answer for question_id: {question_id}")
        
        if not self._base_url:
            logger.warning("Question Service URL not configured. Returning empty answer.")
            return {}
            
        try:
            from services.circuit_breaker import question_service_breaker
            import pybreaker
            
            @question_service_breaker
            async def _fetch_answer():
                async with httpx.AsyncClient() as client:
                    params = {"question_id": question_id}
                    response = await client.get(
                        f"{self._base_url}/api/v1/answers/",
                        params=params
                    )
                    response.raise_for_status()
                    return response.json()
            
            answers = await _fetch_answer()
            if answers and len(answers) > 0:
                return self._reduce_answer(answers[0])
            
            logger.warning(f"No answer found for question_id {question_id}")
            return {}
                
        except pybreaker.CircuitBreakerError:
            logger.warning(f"Circuit breaker OPEN - cannot fetch answer for question {question_id}")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch reference answer: {e}")
            return {}

    async def gen_question_by_id(self, question_id: int) -> Dict:
        if not question_id:
            return {}
            
        logger.debug(f"Fetching question for question_id: {question_id}")
        
        if not self._base_url:
            logger.warning("Question Service URL not configured. Returning empty question.")
            return {}
            
        try:
            from services.circuit_breaker import question_service_breaker
            import pybreaker
            
            @question_service_breaker
            async def _fetch_question():
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self._base_url}/api/v1/questions/{question_id}")
                    if response.status_code == 404:
                        return None  # Signal not found
                    response.raise_for_status()
                    return response.json()
            
            result = await _fetch_question()
            if result is None:
                logger.warning(f"Question {question_id} not found")
                return {}
            return result
                
        except pybreaker.CircuitBreakerError:
            logger.warning(f"Circuit breaker OPEN - cannot fetch question {question_id}")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch question: {e}")
            return {}
    
    async def gen_question_context(
        self, 
        question_id: Optional[int] = None,
    ) -> Dict:
        """
        Fetch complete context for grading a question.
        
        Returns reduced metadata for each component:
        - question: question_details, title, think_time_limit_seconds, record_time_limit_seconds, 
                    question_image_url, topics, subjects
        - reference_answer: text_answer, graph_answer
        - rubric: all fields
        """
        # 1. Fetch Question
        question_raw = await self.gen_question_by_id(question_id)
        if not question_raw:
             logger.warning(f"Could not fetch context for question {question_id}: Question not found")
             return {}

        # 2. Extract Rubric ID and Fetch Rubric
        # Default to 2 (General) if not found
        rubric_id = question_raw.get("rubric_id", 2)
        rubric_raw = await self.gen_rubric_by_rubric_id(rubric_id)

        # 3. Fetch Answer
        reference_answer_raw = await self.gen_reference_answer_by_question_id(question_id)
        
        # 4. Apply reducers to filter relevant fields
        return QuestionContext(
            rubric=self._reduce_rubric(rubric_raw),
            reference_answer=reference_answer_raw,
            question=self._reduce_question(question_raw),
            question_id=question_id
        )


# Global context provider instance
context_provider = ContextProvider()
