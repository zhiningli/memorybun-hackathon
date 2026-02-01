"""
Rubric storage interface and JSON implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from config import settings
from schemas.rubric import Rubric
from schemas.rubric_mutations import RubricCreate, RubricUpdate

logger = logging.getLogger(__name__)


class RubricStore(ABC):
    """
    Abstract interface for rubric storage.
    """
    
    # ==================== READ OPERATIONS ====================
    
    @abstractmethod
    async def get_by_id(self, rubric_id: int) -> Optional[Rubric]:
        """Retrieve a single rubric by ID."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[Rubric]:
        """Retrieve all rubrics."""
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> List[Rubric]:
        """Retrieve rubrics filtering by name."""
        pass
    
    # ==================== WRITE OPERATIONS (Stubs) ====================
    
    @abstractmethod
    async def create(self, rubric: RubricCreate) -> Rubric:
        """Create a new rubric. (Deferred)"""
        pass
    
    @abstractmethod
    async def update(self, rubric_id: int, rubric: RubricUpdate) -> Optional[Rubric]:
        """Update an existing rubric. (Deferred)"""
        pass
    
    @abstractmethod
    async def delete(self, rubric_id: int) -> bool:
        """Delete a rubric by ID. (Deferred)"""
        pass


class JsonRubricStore(RubricStore):
    """
    JSON file-backed rubric storage.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        self._rubrics: dict[int, Rubric] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load rubrics from JSON file into memory."""
        try:
            rubrics_path = self.data_dir / "rubrics.json"
            logger.debug(f"Loading rubrics from: {rubrics_path}")
            
            if not rubrics_path.exists():
                logger.warning(f"Rubrics file not found at {rubrics_path}")
                # Initialize empty file if not exists
                self._save_data()
                return
            
            with open(rubrics_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                rubrics = [Rubric(**r) for r in data.get("rubrics", [])]
                self._rubrics = {r.id: r for r in rubrics}
            
            logger.info(f"Loaded {len(self._rubrics)} rubrics into store")
            
        except Exception as e:
            logger.error(f"Failed to load rubrics: {e}", exc_info=True)
            raise
    
    # ==================== READ OPERATIONS ====================
    
    async def get_by_id(self, rubric_id: int) -> Optional[Rubric]:
        return self._rubrics.get(rubric_id)
    
    async def get_all(self) -> List[Rubric]:
        return list(self._rubrics.values())
    
    async def get_by_name(self, name: str) -> List[Rubric]:
        return [r for r in self._rubrics.values() if r.name == name]
    
    # ==================== WRITE OPERATIONS (Stubs) ====================
    
    async def create(self, rubric: RubricCreate) -> Rubric:
        """
        Create a new rubric.
        Generates ID and timestamps, saves to file.
        
        ID Generation Strategy:
        - JSON: Uses max(existing_ids) + 1 (application-generated)
        - RDB: Will use database auto-increment (SERIAL/AUTO_INCREMENT)
        
        For seamless migration to RDB:
        - Keep ID as int (maps to INTEGER PRIMARY KEY)
        - Don't rely on gap-free sequences
        - When migrating, reset sequence to MAX(id) + 1
        """
        # Generate new ID
        new_id = 1
        if self._rubrics:
            new_id = max(self._rubrics.keys()) + 1
            
        now = datetime.now(timezone.utc)
        
        # Create full rubric object
        rubric_data = rubric.model_dump()
        new_rubric = Rubric(
            id=new_id,
            created_at=now,
            updated_at=now,
            **rubric_data
        )
        
        self._rubrics[new_id] = new_rubric
        self._save_data()
        
        logger.info(f"Created rubric {new_id}")
        return new_rubric
    
    async def update(self, rubric_id: int, rubric_update: RubricUpdate) -> Optional[Rubric]:
        """
        Update an existing rubric.
        
        Version is automatically incremented on each update.
        The version field in rubric_update is ignored.
        """
        if rubric_id not in self._rubrics:
            return None
            
        current_rubric = self._rubrics[rubric_id]
        
        # Update only provided fields (excluding version)
        update_data = rubric_update.model_dump(exclude_unset=True)
        update_data.pop('version', None)  # Remove version if present - we auto-increment
        
        updated_rubric = current_rubric.model_copy(update=update_data)
        
        # Auto-increment version and update timestamp
        updated_rubric.version = (current_rubric.version or 1) + 1
        updated_rubric.updated_at = datetime.now(timezone.utc)
        
        self._rubrics[rubric_id] = updated_rubric
        self._save_data()
        
        logger.info(f"Updated rubric {rubric_id} to version {updated_rubric.version}")
        return updated_rubric
    
    async def delete(self, rubric_id: int) -> bool:
        """
        Delete a rubric by ID.
        """
        if rubric_id not in self._rubrics:
            return False
            
        del self._rubrics[rubric_id]
        self._save_data()
        
        logger.info(f"Deleted rubric {rubric_id}")
        return True

    def _save_data(self) -> None:
        """Save rubrics memory state to JSON file."""
        try:
            rubrics_path = self.data_dir / "rubrics.json"
            
            # Convert dict values to list of dicts for JSON
            rubrics_list = [r.model_dump(mode='json') for r in self._rubrics.values()]
            data = {"rubrics": rubrics_list}
            
            with open(rubrics_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save rubrics: {e}", exc_info=True)
            raise
