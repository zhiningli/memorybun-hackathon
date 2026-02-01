"""
Result Store - Persistence layer for grading results.

Stores grading results in Redis with TTL.
Enables frontend polling for grading status.
"""

import json
import logging
from typing import Optional, Union
from datetime import datetime, timezone
from services.redis_client import get_redis_client
from config import settings
from schemas.grading_result import GradingResult
from schemas.summary_result import SummaryResult

logger = logging.getLogger(__name__)


class ResultStore:
    """
    Persistence layer for grading results.
    
    Uses Redis for storage:
    - grading:status:{session_id} -> Hash (status, message, updated_at)
    - grading:result:{session_id} -> String (JSON serialized GradingResult)
    - summary:status:{summary_id} -> Hash (status, message, updated_at)
    - summary:result:{summary_id} -> String (JSON serialized SummaryResult)
    """
    
    def __init__(self):
        """Initialize the result store"""
        self.result_key_prefix = "grading:result:"
        self.status_key_prefix = "grading:status:"
        self.ttl_seconds = settings.result_ttl_seconds
    
    def _get_result_key(self, session_id: str) -> str:
        """Get Redis key for result storage"""
        return f"{self.result_key_prefix}{session_id}"
    
    def _get_status_key(self, session_id: str) -> str:
        """Get Redis key for status storage"""
        return f"{self.status_key_prefix}{session_id}"
    
    async def set_status(
        self,
        session_id: str,
        status: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Set processing status for a session.
        
        Args:
            session_id: Session identifier
            status: Status string (pending, processing, completed, failed)
            message: Optional status message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            status_key = self._get_status_key(session_id)
            
            status_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if message:
                status_data["message"] = message
            
            await client.hset(status_key, mapping=status_data)
            await client.expire(status_key, self.ttl_seconds)
            
            logger.debug(f"Set status for session {session_id}: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set status for session {session_id}: {e}")
            return False
    
    async def get_status(self, session_id: str) -> Optional[dict]:
        """
        Get processing status for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with status info, or None if not found
        """
        try:
            client = get_redis_client().get_client()
            status_key = self._get_status_key(session_id)
            
            status_data = await client.hgetall(status_key)
            if not status_data:
                return None
            
            return status_data
            
        except Exception as e:
            logger.error(f"Failed to get status for session {session_id}: {e}")
            return None
    
    async def store_result(self, result: Union[dict, GradingResult]) -> bool:
        """
        Store a grading result.
        
        Args:
            result: GradingResult object or dict
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert dict to model if necessary
            if isinstance(result, dict):
                session_id = result.get("session_id")
                grading_result = GradingResult(**result)
            else:
                session_id = result.session_id
                grading_result = result

            if not session_id:
                logger.error("Cannot store result without session_id")
                return False
            
            client = get_redis_client().get_client()
            result_key = self._get_result_key(session_id)
            
            # Serialize using Pydantic
            json_data = grading_result.model_dump_json()
            
            # Store as simple string key with expiration
            await client.setex(result_key, self.ttl_seconds, json_data)
            
            # Also update status to completed
            await self.set_status(session_id, "completed")
            
            logger.info(f"Stored grading result for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store result: {e}")
            return False
    
    async def get_result(self, session_id: str) -> Optional[GradingResult]:
        """
        Get a grading result.
        
        Args:
            session_id: Session identifier
            
        Returns:
            GradingResult object, or None if not found
        """
        try:
            client = get_redis_client().get_client()
            result_key = self._get_result_key(session_id)
            
            result_json = await client.get(result_key)
            if not result_json:
                return None
            
            # Deserialize using Pydantic
            return GradingResult.model_validate_json(result_json)
            
        except Exception as e:
            logger.error(f"Failed to get result for session {session_id}: {e}")
            return None
    
    async def delete_result(self, session_id: str) -> bool:
        """
        Delete a grading result (for cleanup/testing).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            result_key = self._get_result_key(session_id)
            status_key = self._get_status_key(session_id)
            
            deleted = await client.delete(result_key, status_key)
            logger.info(f"Deleted result for session {session_id}")
            return deleted > 0
            
        except Exception as e:
            logger.error(f"Failed to delete result for session {session_id}: {e}")
            return False

    # ==================== Summary Results ====================
    
    def _get_summary_result_key(self, summary_id: str) -> str:
        """Get Redis key for summary result storage."""
        return f"summary:result:{summary_id}"
    
    def _get_summary_status_key(self, summary_id: str) -> str:
        """Get Redis key for summary status storage."""
        return f"summary:status:{summary_id}"
    
    async def set_summary_status(
        self,
        summary_id: str,
        status: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Set processing status for a summary.
        
        Args:
            summary_id: Summary identifier
            status: Status string (pending, processing, completed, failed)
            message: Optional status message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            status_key = self._get_summary_status_key(summary_id)
            
            status_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if message:
                status_data["message"] = message
            
            await client.hset(status_key, mapping=status_data)
            await client.expire(status_key, self.ttl_seconds)
            
            logger.debug(f"Set status for summary {summary_id}: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set status for summary {summary_id}: {e}")
            return False
    
    async def get_summary_status(self, summary_id: str) -> Optional[dict]:
        """
        Get processing status for a summary.
        
        Args:
            summary_id: Summary identifier
            
        Returns:
            Dict with status info, or None if not found
        """
        try:
            client = get_redis_client().get_client()
            status_key = self._get_summary_status_key(summary_id)
            
            status_data = await client.hgetall(status_key)
            if not status_data:
                return None
            
            return status_data
            
        except Exception as e:
            logger.error(f"Failed to get status for summary {summary_id}: {e}")
            return None
    
    async def store_summary_result(self, result: Union[dict, SummaryResult]) -> bool:
        """
        Store a summary result.
        
        Args:
            result: SummaryResult object or dict
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert dict to model if necessary
            if isinstance(result, dict):
                summary_id = result.get("summary_id")
                summary_result = SummaryResult(**result)
            else:
                summary_id = result.summary_id
                summary_result = result

            if not summary_id:
                logger.error("Cannot store summary result without summary_id")
                return False
            
            client = get_redis_client().get_client()
            result_key = self._get_summary_result_key(summary_id)
            
            # Serialize using Pydantic
            json_data = summary_result.model_dump_json()
            
            # Store as simple string key with expiration
            await client.setex(result_key, self.ttl_seconds, json_data)
            
            # Also update status to completed
            await self.set_summary_status(summary_id, "completed")
            
            logger.info(f"Stored summary result for {summary_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store summary result: {e}")
            return False
    
    async def get_summary_result(self, summary_id: str) -> Optional[SummaryResult]:
        """
        Get a summary result.
        
        Args:
            summary_id: Summary identifier
            
        Returns:
            SummaryResult object, or None if not found
        """
        try:
            client = get_redis_client().get_client()
            result_key = self._get_summary_result_key(summary_id)
            
            result_json = await client.get(result_key)
            if not result_json:
                return None
            
            # Deserialize using Pydantic
            return SummaryResult.model_validate_json(result_json)
            
        except Exception as e:
            logger.error(f"Failed to get summary result for {summary_id}: {e}")
            return None


# Global result store instance
result_store = ResultStore()
