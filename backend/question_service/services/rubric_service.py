"""
Rubric Service - Manages grading rubrics.

Uses the storage layer for data access, enabling easy migration from
JSON files to database in the future.
"""

import logging
from pathlib import Path
from typing import List, Optional

from schemas.rubric import Rubric
from schemas.rubric_mutations import RubricCreate, RubricUpdate
from config import settings
from storage import RubricStore, JsonRubricStore

logger = logging.getLogger(__name__)


class RubricService:
    """Service for managing grading rubrics"""
    
    def __init__(
        self, 
        data_dir: Optional[Path] = None,
        rubric_store: Optional[RubricStore] = None
    ):
        """
        Initialize service with storage backends.
        
        Args:
            data_dir: Optional custom data directory path (for testing).
                     If None, uses path from settings.
            rubric_store: Optional RubricStore implementation.
        """
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        
        # Use injected store or create default JSON store
        self._rubric_store = rubric_store or JsonRubricStore(self.data_dir)
        
    @property
    def rubrics(self) -> List[Rubric]:
        """Backward-compatible property to access rubrics."""
        if isinstance(self._rubric_store, JsonRubricStore):
             return list(self._rubric_store._rubrics.values())
        return []
            
    async def gen_rubrics(self, name: Optional[str] = None) -> List[Rubric]:
        """
        Get all available rubrics, optionally filtered by name.
        """
        if name:
            return await self._rubric_store.get_by_name(name)
        return await self._rubric_store.get_all()

    # ==================== MUTATION METHODS (ADMIN) ====================

    async def create_rubric(self, rubric_create: RubricCreate) -> Rubric:
        """Create a new rubric (Admin only)."""
        return await self._rubric_store.create(rubric_create)

    async def update_rubric(self, rubric_id: int, rubric_update: RubricUpdate) -> Optional[Rubric]:
        """Update an existing rubric (Admin only)."""
        return await self._rubric_store.update(rubric_id, rubric_update)

    async def delete_rubric(self, rubric_id: int) -> bool:
        """Delete a rubric (Admin only)."""
        return await self._rubric_store.delete(rubric_id)

# Global service instance
rubric_service = RubricService()

