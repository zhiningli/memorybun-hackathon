"""
Answer Service - Manages answers.

Uses the storage layer for data access, enabling easy migration from
JSON files to database in the future.
"""

import logging
from pathlib import Path
from typing import List, Optional

from schemas.answer import Answer
from schemas.answer_mutations import AnswerCreate, AnswerUpdate
from schemas.question import Question
from schemas.questionList import QuestionListMetadata, AccessStatusEnum
from config import settings
from schemas.viewer_context import ViewerContext
from storage import (
    AnswerStore, JsonAnswerStore,
    QuestionStore, JsonQuestionStore,
    QuestionListStore, JsonQuestionListStore,
    QuestionListItemStore, JsonQuestionListItemStore
)

logger = logging.getLogger(__name__)


class AnswerService:
    """Service for managing answers"""
    
    def __init__(
        self, 
        data_dir: Optional[Path] = None,
        answer_store: Optional[AnswerStore] = None,
        question_store: Optional[QuestionStore] = None,
        question_list_store: Optional[QuestionListStore] = None,
        question_list_item_store: Optional[QuestionListItemStore] = None
    ):
        """
        Initialize service with storage backends.
        
        Args:
            data_dir: Optional custom data directory path (for testing).
            answer_store: Optional AnswerStore implementation.
            question_store: Optional QuestionStore implementation.
            question_list_store: Optional QuestionListStore implementation.
            question_list_item_store: Optional QuestionListItemStore implementation.
        """
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        
        # Create question store first (needed for FK validation in answer_store)
        self._question_store = question_store or JsonQuestionStore(self.data_dir)
        
        # Create answer store with question_store for FK validation
        self._answer_store = answer_store or JsonAnswerStore(
            self.data_dir, 
            question_store=self._question_store
        )
        
        self._question_list_store = question_list_store or JsonQuestionListStore(self.data_dir)
        self._question_list_item_store = question_list_item_store or JsonQuestionListItemStore(self.data_dir)
        
    @property
    def answers(self) -> List[Answer]:
        """Backward-compatible property to access answers (read-only from store)."""
        # Note: This accesses private member of JsonAnswerStore specific implementation.
        # Ideally we'd use get_all() but that is async.
        # For backward compatibility where .answers was a list accessor:
        if isinstance(self._answer_store, JsonAnswerStore):
             return list(self._answer_store._answers.values())
        return [] # Should possibly warn or implement a synchronous cache if needed for non-async calling code
        
    @property
    def questions(self) -> List[Question]:
        """Backward-compatible property to access questions."""
        if isinstance(self._question_store, JsonQuestionStore):
             return list(self._question_store._questions.values())
        return []

    @property
    def question_lists(self) -> List[QuestionListMetadata]:
        """Backward-compatible property to access question lists."""
        if isinstance(self._question_list_store, JsonQuestionListStore):
            return list(self._question_list_store._lists.values())
        return []

    # Note: question_list_items was also loaded.
    @property
    def question_list_items(self):
         if isinstance(self._question_list_item_store, JsonQuestionListItemStore):
             return self._question_list_item_store._items
         return []

    def _load_data(self):
        """
        Deprecated. Data is loaded by stores on init.
        Kept empty to satisfy any explicit calls if they exist, or removed if unused.
        """
        pass
    
    async def gen_answer_by_question_id(
        self,
        question_id: int,
        viewer_context: Optional[ViewerContext] = None
    ) -> Optional[Answer]:
        """
        Get an answer by question id.
        Returns None if the answer doesn't exist or viewer doesn't have access.
        """
        # First, check if the question exists
        question = await self._question_store.get_by_id(question_id)
        if question is None:
            return None
        
        # Check if viewer can access this question
        if not await self._can_view_question(question, viewer_context):
            return None
        
        return await self._answer_store.get_by_question_id(question_id)
    
    async def gen_answers_by_question_ids(
        self,
        question_ids: List[int],
        viewer_context: Optional[ViewerContext] = None
    ) -> List[Answer]:
        """
        Get answers for multiple question ids.
        Returns a list of answers that exist and the viewer has access to.
        Questions that don't exist or aren't accessible are simply omitted.
        """
        results = []
        for question_id in question_ids:
            answer = await self.gen_answer_by_question_id(question_id, viewer_context)
            if answer is not None:
                results.append(answer)
        return results
    
    async def _can_view_question(self, question: Question, viewer_context: Optional[ViewerContext] = None) -> bool:
        """
        Check if viewer can see this question.
        A question is accessible if it's in at least one question list that the viewer can access.
        """
        # Find all question lists that contain this question
        question_list_ids = await self._question_list_item_store.get_lists_containing_question(question.id)
        
        if not question_list_ids:
            # Question is not in any list - for now, deny access
            return False
        
        # Check if viewer can access at least one of the question lists containing this question
        for question_list_id in question_list_ids:
            question_list = await self._question_list_store.get_by_id(question_list_id)
            if question_list is None:
                continue
            
            # If no viewer context, check if list is public
            if viewer_context is None:
                if question_list.access_status == AccessStatusEnum.PUBLIC:
                    return True
            else:
                # Check if viewer can view this list
                if self._can_view_list(question_list, viewer_context):
                    return True
        
        return False
    
    def _can_view_list(self, question_list: QuestionListMetadata, context: ViewerContext) -> bool:
        """Check if viewer can see this question list"""
        # Public lists are visible to everyone
        if question_list.access_status == AccessStatusEnum.PUBLIC:
            return True
        
        # Authenticated users can see non-public lists
        if context.is_authenticated:
            return True
        
        return False

    # ==================== MUTATION METHODS (ADMIN) ====================

    async def create_answer(self, answer_create: AnswerCreate) -> Answer:
        """Create a new answer (Admin only)."""
        return await self._answer_store.create(answer_create)

    async def update_answer(self, answer_id: int, answer_update: AnswerUpdate) -> Optional[Answer]:
        """Update an existing answer (Admin only)."""
        return await self._answer_store.update(answer_id, answer_update)

    async def delete_answer(self, answer_id: int) -> bool:
        """Delete an answer (Admin only)."""
        return await self._answer_store.delete(answer_id)



answer_service = AnswerService()