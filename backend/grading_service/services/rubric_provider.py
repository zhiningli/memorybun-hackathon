import httpx
import logging
from typing import List, Optional, Dict
from pydantic import BaseModel
from config import settings

logger = logging.getLogger(__name__)

# Re-define minimalist schema here to avoid dependency coupling
class RubricCriteria(BaseModel):
    name: str
    description: str
    scoring_condition: str

class RubricDimension(BaseModel):
    name: str
    weight: float = 0.0
    description: str
    criterias: List[RubricCriteria]

class Rubric(BaseModel):
    id: int
    name: str  # Renamed from 'category'
    description: Optional[str] = None
    dimensions: List[RubricDimension]
    version: Optional[int] = 1
    # Note: created_at/updated_at omitted for simplicity in grading service


class RubricProvider:
    """
    Fetches and provides grading rubrics from the Question Service.
    Maintains a local cache to avoid per-request network calls.
    """
    
    def __init__(self):
        self._cache: Dict[int, Rubric] = {}
        self._base_url = settings.question_service_url
    
    async def load_rubrics(self):
        """
        Fetch all rubrics from Question Service and populate cache.
        """
        if not self._base_url:
            logger.warning("Question Service URL not configured. Rubrics will not be loaded.")
            return

        try:
            logger.info(f"Fetching rubrics from {self._base_url}/api/v1/rubrics/")
            
            from middleware.request_id import get_request_id
            from services.circuit_breaker import question_service_breaker
            import pybreaker
            headers = {"X-Correlation-ID": get_request_id()}
            
            @question_service_breaker
            async def _fetch_rubrics():
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self._base_url}/api/v1/rubrics/", headers=headers)
                    response.raise_for_status()
                    return response.json()
            
            rubrics_data = await _fetch_rubrics()
            self._cache.clear()

            for r_data in rubrics_data:
                rubric = Rubric(**r_data)
                # Cache by ID
                self._cache[rubric.id] = rubric

            logger.info(f"Loaded {len(self._cache)} rubrics from Question Service")

        except pybreaker.CircuitBreakerError:
            logger.warning("Circuit breaker OPEN for question_service - skipping rubric load")
        except Exception as e:
            logger.error(f"Failed to load rubrics: {e}")
            # Do not raise here, allow service to start even if rubrics fail

            
    
    def get_rubric_by_rubric_id(self, rubric_id: int) -> Optional[Rubric]:
        """
        Get rubric for a specific ID.
        
        Args:
            rubric_id: ID of the rubric (e.g., 1, 4)
            
        Returns:
            Rubric object or None/Default if not found
        """
        if not rubric_id:
             return self._cache.get(2) # Default to General (ID 2)

        # 1. Try exact match
        rubric = self._cache.get(rubric_id)
        if rubric:
            return rubric
            
        # 2. Fallback to "general" (ID 2) if not found
        logger.warning(f"Rubric for rubric_id '{rubric_id}' not found. Falling back to 'General'.")
        return self._cache.get(2) 

# Global instance
rubric_provider = RubricProvider()
