"""
Answer storage interface and JSON implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from config import settings
from schemas.answer import Answer
from schemas.answer_mutations import AnswerCreate, AnswerUpdate

logger = logging.getLogger(__name__)


class AnswerStore(ABC):
    """
    Abstract interface for answer storage.
    """
    
    # ==================== READ OPERATIONS ====================
    
    @abstractmethod
    async def get_by_id(self, answer_id: int) -> Optional[Answer]:
        """Retrieve a single answer by ID."""
        pass
    
    @abstractmethod
    async def get_by_question_id(self, question_id: int) -> Optional[Answer]:
        """Retrieve answer for a specific question."""
        pass

    @abstractmethod
    async def get_all(self) -> List[Answer]:
        """Retrieve all answers."""
        pass
    
    # ==================== FK VALIDATION ====================
    
    @abstractmethod
    async def validate_question_exists(self, question_id: int) -> bool:
        """Check if question exists (FK validation)."""
        pass
    
    # ==================== WRITE OPERATIONS ====================
    
    @abstractmethod
    async def create(self, answer: AnswerCreate) -> Answer:
        """Create a new answer. Validates question_id exists."""
        pass
    
    @abstractmethod
    async def update(self, answer_id: int, answer: AnswerUpdate) -> Optional[Answer]:
        """Update an existing answer."""
        pass
    
    @abstractmethod
    async def delete(self, answer_id: int) -> bool:
        """Delete an answer by ID."""
        pass


class JsonAnswerStore(AnswerStore):
    """
    JSON file-backed answer storage.
    
    Optionally accepts a question_store for FK validation.
    If not provided, FK validation is skipped (for backward compatibility).
    """
    
    def __init__(self, data_dir: Optional[Path] = None, question_store=None):
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        self._answers: dict[int, Answer] = {}
        self._question_store = question_store  # Optional: for FK validation
        self._load_data()
    
    def _load_data(self) -> None:
        """Load answers from JSON file into memory."""
        try:
            answers_path = self.data_dir / "answers.json"
            logger.debug(f"Loading answers from: {answers_path}")
            
            if not answers_path.exists():
                logger.warning(f"Answers file not found at {answers_path}")
                # Initialize empty file if not exists
                self._save_data()
                return
            
            with open(answers_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                answers = [Answer(**a) for a in data.get("answers", [])]
                self._answers = {a.id: a for a in answers}
            
            logger.info(f"Loaded {len(self._answers)} answers into store")
            
        except Exception as e:
            logger.error(f"Failed to load answers: {e}", exc_info=True)
            raise
    
    # ==================== READ OPERATIONS ====================
    
    async def get_by_id(self, answer_id: int) -> Optional[Answer]:
        return self._answers.get(answer_id)
    
    async def get_by_question_id(self, question_id: int) -> Optional[Answer]:
        return next((a for a in self._answers.values() if a.question_id == question_id), None)

    async def get_all(self) -> List[Answer]:
        return list(self._answers.values())
    
    # ==================== FK VALIDATION ====================
    
    async def validate_question_exists(self, question_id: int) -> bool:
        """
        Check if question exists.
        
        Returns True if question_store is not configured (backward compatibility)
        or if the question exists.
        """
        if self._question_store is None:
            # No question_store configured - skip validation
            return True
        return await self._question_store.get_by_id(question_id) is not None
    
    # ==================== WRITE OPERATIONS ====================
    
    async def create(self, answer: AnswerCreate) -> Answer:
        """
        Create a new answer.
        Generates ID and timestamps, saves to file.
        
        ID Generation Strategy:
        - JSON: Uses max(existing_ids) + 1 (application-generated)
        - RDB: Will use database auto-increment (SERIAL/AUTO_INCREMENT)
        
        For seamless migration to RDB:
        - Keep ID as int (maps to INTEGER PRIMARY KEY)
        - Don't rely on gap-free sequences
        - When migrating, reset sequence to MAX(id) + 1
        
        Raises:
            ValueError: If question_id does not exist (FK validation)
        """
        # Validate FK: question must exist
        if not await self.validate_question_exists(answer.question_id):
            raise ValueError(f"Question {answer.question_id} not found")
        
        # Generate new ID
        new_id = 1
        if self._answers:
            new_id = max(self._answers.keys()) + 1
            
        now = datetime.now(timezone.utc)
        
        # Create full answer object
        answer_data = answer.model_dump()
        new_answer = Answer(
            id=new_id,
            created_at=now,
            updated_at=now,
            **answer_data
        )
        
        self._answers[new_id] = new_answer
        self._save_data()
        
        logger.info(f"Created answer {new_id} for question {answer.question_id}")
        return new_answer
    
    async def update(self, answer_id: int, answer_update: AnswerUpdate) -> Optional[Answer]:
        """
        Update an existing answer.
        """
        if answer_id not in self._answers:
            return None
            
        current_answer = self._answers[answer_id]
        
        # Update only provided fields
        update_data = answer_update.model_dump(exclude_unset=True)
        updated_answer = current_answer.model_copy(update=update_data)
        
        # Update timestamp
        updated_answer.updated_at = datetime.now(timezone.utc)
        
        self._answers[answer_id] = updated_answer
        self._save_data()
        
        logger.info(f"Updated answer {answer_id}")
        return updated_answer
    
    async def delete(self, answer_id: int) -> bool:
        """
        Delete an answer by ID.
        """
        if answer_id not in self._answers:
            return False
            
        del self._answers[answer_id]
        self._save_data()
        
        logger.info(f"Deleted answer {answer_id}")
        return True

    def _save_data(self) -> None:
        """Save answers memory state to JSON file."""
        try:
            answers_path = self.data_dir / "answers.json"
            
            # Convert dict values to list of dicts for JSON
            answers_list = [a.model_dump(mode='json') for a in self._answers.values()]
            data = {"answers": answers_list}
            
            with open(answers_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save answers: {e}", exc_info=True)
            raise
