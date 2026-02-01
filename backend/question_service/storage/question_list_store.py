"""
Question list storage interface and JSON implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from config import settings
from schemas.questionList import QuestionListMetadata, QuestionListMetadataBase

logger = logging.getLogger(__name__)


class QuestionListStore(ABC):
    """Abstract interface for question list metadata storage."""
    
    # ==================== READ OPERATIONS ====================
    
    @abstractmethod
    async def get_by_id(self, list_id: int) -> Optional[QuestionListMetadata]:
        """Retrieve a single question list by ID."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[QuestionListMetadata]:
        """Retrieve all question lists."""
        pass
    
    # ==================== WRITE OPERATIONS ====================
    
    @abstractmethod
    async def create(self, list_data: QuestionListMetadataBase) -> QuestionListMetadata:
        """Create a new question list. Generates ID and timestamps."""
        pass
    
    @abstractmethod
    async def update(self, list_id: int, update_data: dict) -> Optional[QuestionListMetadata]:
        """Update an existing question list with partial data."""
        pass
    
    @abstractmethod
    async def delete(self, list_id: int) -> bool:
        """Delete a question list by ID."""
        pass


class JsonQuestionListStore(QuestionListStore):
    """JSON file-backed question list metadata storage."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        self._lists: dict[int, QuestionListMetadata] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load question lists from JSON file into memory."""
        try:
            lists_path = self.data_dir / "question_lists.json"
            logger.debug(f"Loading question lists from: {lists_path}")
            
            if not lists_path.exists():
                logger.warning(f"Question lists file not found at {lists_path}")
                self._save_data()  # Create empty file
                return
            
            with open(lists_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                lists = [QuestionListMetadata(**ql) for ql in data.get("question_lists", [])]
                self._lists = {lst.id: lst for lst in lists}
            
            logger.info(f"Loaded {len(self._lists)} question lists into store")
            
        except Exception as e:
            logger.error(f"Failed to load question lists: {e}", exc_info=True)
            raise
    
    def _save_data(self) -> None:
        """Save question lists to JSON file."""
        try:
            lists_path = self.data_dir / "question_lists.json"
            lists_list = [lst.model_dump(mode='json') for lst in self._lists.values()]
            data = {"question_lists": lists_list}
            
            with open(lists_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save question lists: {e}", exc_info=True)
            raise
    
    # ==================== READ OPERATIONS ====================
    
    async def get_by_id(self, list_id: int) -> Optional[QuestionListMetadata]:
        return self._lists.get(list_id)
    
    async def get_all(self) -> List[QuestionListMetadata]:
        return list(self._lists.values())
    
    # ==================== WRITE OPERATIONS ====================
    
    async def create(self, list_data: QuestionListMetadataBase) -> QuestionListMetadata:
        """
        Create a new question list.
        
        ID Generation Strategy:
        - JSON: Uses max(existing_ids) + 1
        - RDB: Will use database auto-increment
        """
        # Generate new ID
        new_id = 1
        if self._lists:
            new_id = max(self._lists.keys()) + 1
            
        now = datetime.now(timezone.utc)
        
        # Create full object with ID and timestamps
        new_list = QuestionListMetadata(
            id=new_id,
            created_at=now,
            updated_at=now,
            **list_data.model_dump()
        )
        
        self._lists[new_id] = new_list
        self._save_data()
        
        logger.info(f"Created question list {new_id}: {new_list.title}")
        return new_list
    
    async def update(self, list_id: int, update_data: dict) -> Optional[QuestionListMetadata]:
        """Update an existing question list with partial data."""
        if list_id not in self._lists:
            return None
            
        current = self._lists[list_id]
        
        # Apply updates
        updated = current.model_copy(update=update_data)
        updated.updated_at = datetime.now(timezone.utc)
        
        self._lists[list_id] = updated
        self._save_data()
        
        logger.info(f"Updated question list {list_id}")
        return updated
    
    async def delete(self, list_id: int) -> bool:
        """Delete a question list by ID."""
        if list_id not in self._lists:
            return False
            
        del self._lists[list_id]
        self._save_data()
        
        logger.info(f"Deleted question list {list_id}")
        return True
