"""
Question storage interface and JSON implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from config import settings
from schemas.question import Question
from schemas.question_mutations import QuestionCreate, QuestionUpdate

logger = logging.getLogger(__name__)


class QuestionStore(ABC):
    """
    Abstract interface for question storage.
    
    Implementations:
    - JsonQuestionStore: MVP implementation using JSON files
    - DynamoDBQuestionStore: Future serverless implementation
    - PostgresQuestionStore: Future relational implementation
    """
    
    # ==================== READ OPERATIONS ====================
    
    @abstractmethod
    async def get_by_id(self, question_id: int) -> Optional[Question]:
        """Retrieve a single question by ID."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[Question]:
        """Retrieve all questions."""
        pass
    
    @abstractmethod
    async def get_by_ids(self, question_ids: List[int]) -> List[Question]:
        """Retrieve multiple questions by their IDs."""
        pass
    
    # ==================== FK VALIDATION ====================
    
    @abstractmethod
    async def validate_rubric_exists(self, rubric_id: int) -> bool:
        """Check if rubric exists (FK validation)."""
        pass
    
    # ==================== WRITE OPERATIONS ====================
    
    @abstractmethod
    async def create(self, question: QuestionCreate) -> Question:
        """Create a new question. Validates rubric_id exists."""
        pass
    
    @abstractmethod
    async def update(self, question_id: int, question: QuestionUpdate) -> Optional[Question]:
        """Update an existing question."""
        pass
    
    @abstractmethod
    async def delete(self, question_id: int) -> bool:
        """Delete a question by ID."""
        pass


class JsonQuestionStore(QuestionStore):
    """
    JSON file-backed question storage.
    
    For read operations: Loads data into memory at startup for fast access.
    Optionally accepts a rubric_store for FK validation.
    """
    
    def __init__(self, data_dir: Optional[Path] = None, rubric_store=None):
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        self._questions: dict[int, Question] = {}
        self._rubric_store = rubric_store  # Optional: for FK validation
        self._load_data()
    
    def _load_data(self) -> None:
        """Load questions from JSON file into memory."""
        try:
            questions_path = self.data_dir / "questions.json"
            logger.debug(f"Loading questions from: {questions_path}")
            
            if not questions_path.exists():
                logger.warning(f"Questions file not found at {questions_path}")
                # Initialize empty file if not exists
                self._save_data()
                return
            
            with open(questions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                questions = [Question(**q) for q in data.get("questions", [])]
                self._questions = {q.id: q for q in questions}
            
            logger.info(f"Loaded {len(self._questions)} questions into store")
            
        except Exception as e:
            logger.error(f"Failed to load questions: {e}", exc_info=True)
            # Do not raise here to allow service to start even if data is corrupted?
            # Or maybe raise. For MVP let's raise.
            raise
    
    # ==================== READ OPERATIONS ====================
    
    async def get_by_id(self, question_id: int) -> Optional[Question]:
        return self._questions.get(question_id)
    
    async def get_all(self) -> List[Question]:
        return list(self._questions.values())
    
    async def get_by_ids(self, question_ids: List[int]) -> List[Question]:
        return [self._questions[qid] for qid in question_ids if qid in self._questions]
    
    # ==================== FK VALIDATION ====================
    
    async def validate_rubric_exists(self, rubric_id: int) -> bool:
        """
        Check if rubric exists.
        
        Returns True if rubric_store is not configured (backward compatibility)
        or if the rubric exists.
        """
        if self._rubric_store is None:
            # No rubric_store configured - skip validation
            return True
        return await self._rubric_store.get_by_id(rubric_id) is not None
    
    # ==================== WRITE OPERATIONS ====================
    
    async def create(self, question: QuestionCreate) -> Question:
        """
        Create a new question.
        Generates ID and timestamps, saves to file.
        
        ID Generation Strategy:
        - JSON: Uses max(existing_ids) + 1 (application-generated)
        - RDB: Will use database auto-increment (SERIAL/AUTO_INCREMENT)
        
        For seamless migration to RDB:
        - Keep ID as int (maps to INTEGER PRIMARY KEY)
        - Don't rely on gap-free sequences
        - When migrating, reset sequence to MAX(id) + 1
        
        Raises:
            ValueError: If rubric_id does not exist (FK validation)
        """
        # Validate FK: rubric must exist
        if not await self.validate_rubric_exists(question.rubric_id):
            raise ValueError(f"Rubric {question.rubric_id} not found")
        
        # Generate new ID
        new_id = 1
        if self._questions:
            new_id = max(self._questions.keys()) + 1
            
        now = datetime.now(timezone.utc)
        
        # Create full question object
        question_data = question.model_dump()
        new_question = Question(
            id=new_id,
            created_at=now,
            updated_at=now,
            **question_data
        )
        
        self._questions[new_id] = new_question
        self._save_data()
        
        logger.info(f"Created question {new_id}")
        return new_question
    
    async def update(self, question_id: int, question_update: QuestionUpdate) -> Optional[Question]:
        """
        Update an existing question.
        """
        if question_id not in self._questions:
            return None
            
        current_question = self._questions[question_id]
        
        # Update only provided fields
        update_data = question_update.model_dump(exclude_unset=True)
        updated_question = current_question.model_copy(update=update_data)
        
        # Update timestamp
        updated_question.updated_at = datetime.now(timezone.utc)
        
        self._questions[question_id] = updated_question
        self._save_data()
        
        logger.info(f"Updated question {question_id}")
        return updated_question
    
    async def delete(self, question_id: int) -> bool:
        """
        Delete a question by ID.
        """
        if question_id not in self._questions:
            return False
            
        del self._questions[question_id]
        self._save_data()
        
        logger.info(f"Deleted question {question_id}")
        return True

    def _save_data(self) -> None:
        """Save questions memory state to JSON file."""
        try:
            questions_path = self.data_dir / "questions.json"
            
            # Convert dict values to list of dicts for JSON
            questions_list = [q.model_dump(mode='json') for q in self._questions.values()]
            data = {"questions": questions_list}
            
            # Atomic write pattern (write to temp, then rename) could be better, 
            # but simple write is fine for MVP.
            # We use mode='json' in model_dump to handle datetimes correctly.
            with open(questions_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save questions: {e}", exc_info=True)
            raise
