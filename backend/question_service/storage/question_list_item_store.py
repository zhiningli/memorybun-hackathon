"""
Question list item (join table) storage interface and JSON implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from config import settings
from schemas.questionList import QuestionListItem

logger = logging.getLogger(__name__)


class QuestionListItemStore(ABC):
    """Abstract interface for question list items (join table) storage."""
    
    # ==================== READ OPERATIONS ====================
    
    @abstractmethod
    async def get_by_list_id(self, list_id: int) -> List[QuestionListItem]:
        """Retrieve all items for a given question list, ordered by order_index."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[QuestionListItem]:
        """Retrieve all question list items."""
        pass
    
    @abstractmethod
    async def get_lists_containing_question(self, question_id: int) -> List[int]:
        """Get all list IDs that contain a specific question."""
        pass
    
    # ==================== WRITE OPERATIONS ====================
    
    @abstractmethod
    async def add_items(self, items: List[QuestionListItem]) -> List[QuestionListItem]:
        """Add multiple items to a list (bulk create)."""
        pass
    
    @abstractmethod
    async def remove_items_by_list(self, list_id: int) -> int:
        """Remove all items for a given list (cascade delete). Returns count removed."""
        pass
    
    @abstractmethod
    async def replace_items_for_list(self, list_id: int, items: List[QuestionListItem]) -> List[QuestionListItem]:
        """Replace all items for a list (delete existing + add new)."""
        pass


class JsonQuestionListItemStore(QuestionListItemStore):
    """JSON file-backed question list items (join table) storage."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        self._items: List[QuestionListItem] = []
        self._load_data()
    
    def _load_data(self) -> None:
        """Load question list items from JSON file into memory."""
        try:
            items_path = self.data_dir / "question_list_items.json"
            logger.debug(f"Loading question list items from: {items_path}")
            
            if not items_path.exists():
                logger.warning(f"Question list items file not found at {items_path}")
                self._save_data()  # Create empty file
                return
            
            with open(items_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._items = [QuestionListItem(**qli) for qli in data.get("question_list_items", [])]
            
            logger.info(f"Loaded {len(self._items)} question list items into store")
            
        except Exception as e:
            logger.error(f"Failed to load question list items: {e}", exc_info=True)
            raise
    
    def _save_data(self) -> None:
        """Save question list items to JSON file."""
        try:
            items_path = self.data_dir / "question_list_items.json"
            items_list = [item.model_dump(mode='json') for item in self._items]
            data = {"question_list_items": items_list}
            
            with open(items_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save question list items: {e}", exc_info=True)
            raise
    
    # ==================== READ OPERATIONS ====================
    
    async def get_by_list_id(self, list_id: int) -> List[QuestionListItem]:
        items = [item for item in self._items if item.question_list_id == list_id]
        return sorted(items, key=lambda x: x.order_index)
    
    async def get_all(self) -> List[QuestionListItem]:
        return self._items.copy()
    
    async def get_lists_containing_question(self, question_id: int) -> List[int]:
        return [item.question_list_id for item in self._items if item.question_id == question_id]
    
    # ==================== WRITE OPERATIONS ====================
    
    async def add_items(self, items: List[QuestionListItem]) -> List[QuestionListItem]:
        """Add multiple items to a list."""
        self._items.extend(items)
        self._save_data()
        logger.info(f"Added {len(items)} question list items")
        return items
    
    async def remove_items_by_list(self, list_id: int) -> int:
        """Remove all items for a given list. Returns count removed."""
        original_count = len(self._items)
        self._items = [item for item in self._items if item.question_list_id != list_id]
        removed = original_count - len(self._items)
        
        if removed > 0:
            self._save_data()
            logger.info(f"Removed {removed} items for list {list_id}")
        
        return removed
    
    async def replace_items_for_list(self, list_id: int, items: List[QuestionListItem]) -> List[QuestionListItem]:
        """Replace all items for a list (delete existing + add new)."""
        # Remove existing
        self._items = [item for item in self._items if item.question_list_id != list_id]
        
        # Add new
        self._items.extend(items)
        self._save_data()
        
        logger.info(f"Replaced items for list {list_id} with {len(items)} items")
        return items

