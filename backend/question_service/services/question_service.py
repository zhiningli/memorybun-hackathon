"""
Question Service - Manages questions, answers, and question lists.

Uses the storage layer for data access, enabling easy migration from
JSON files to database in the future.
"""

import logging
from pathlib import Path
from typing import List, Optional

from schemas.question import Question
from schemas.question_mutations import QuestionCreate, QuestionUpdate
from schemas.questionList import QuestionListMetadata, QuestionListItem, AccessStatusEnum
from schemas.viewer_context import ViewerContext
from storage import (
    QuestionStore, JsonQuestionStore,
    QuestionListStore, JsonQuestionListStore,
    QuestionListItemStore, JsonQuestionListItemStore,
)
from config import settings


logger = logging.getLogger(__name__)


class QuestionService:
    """
    Service for managing question lists and questions.
    
    Uses dependency injection for the storage layer, enabling:
    - Easy testing with mock stores
    - Future migration to database without code changes
    """
    
    def __init__(
        self, 
        data_dir: Optional[Path] = None,
        question_store: Optional[QuestionStore] = None,
        question_list_store: Optional[QuestionListStore] = None,
        question_list_item_store: Optional[QuestionListItemStore] = None,
        rubric_store=None,  # Optional: for FK validation in question_store
    ):
        """
        Initialize service with storage backends.
        
        Args:
            data_dir: Optional custom data directory path (for testing).
                     If None, uses path from settings.
            question_store: Optional QuestionStore implementation.
            question_list_store: Optional QuestionListStore implementation.
            question_list_item_store: Optional QuestionListItemStore implementation.
            rubric_store: Optional RubricStore for FK validation (questions have rubric_id).
        """
        self.data_dir = data_dir if data_dir is not None else settings.get_data_dir()
        
        # Store rubric_store for FK validation
        self._rubric_store = rubric_store
        
        # Create question store with rubric_store for FK validation
        self._question_store = question_store or JsonQuestionStore(
            self.data_dir,
            rubric_store=rubric_store
        )
        self._question_list_store = question_list_store or JsonQuestionListStore(self.data_dir)
        self._question_list_item_store = question_list_item_store or JsonQuestionListItemStore(self.data_dir)
    
    @property
    def questions(self) -> List[Question]:
        """
        Backward-compatible property to access questions.
        
        Note: This is a synchronous accessor to the in-memory cache.
        For new code, prefer using the storage layer directly.
        """
        return list(self._question_store._questions.values())
    
    @property
    def question_lists(self) -> List[QuestionListMetadata]:
        """Backward-compatible property to access question lists."""
        return list(self._question_list_store._lists.values())
    
    @property
    def question_list_items(self) -> List[QuestionListItem]:
        """Backward-compatible property to access question list items."""
        return self._question_list_item_store._items.copy()

    async def initialize(self):
        """
        Initialize the service.
        
        Note: Data is now loaded in store constructors, so this method
        only performs validation. Kept for backward compatibility.
        """
        try:
            # Validate weightage
            self._validate_weightage()
            logger.info("QuestionService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}", exc_info=True)
            raise

    def _validate_weightage(self):
        """Validate that weightage for each question list sums to 1.0"""
        list_weights: dict[int, float] = {}
        for item in self.question_list_items:
            if item.question_list_id not in list_weights:
                list_weights[item.question_list_id] = 0.0
            list_weights[item.question_list_id] += item.weightage
        
        for list_id, total_weight in list_weights.items():
            if abs(total_weight - 1.0) > 0.01:  # allow small epsilon
                logger.warning(f"Question List {list_id} has invalid total weightage: {total_weight}")

    # ==================== QUESTION LIST METHODS ====================

    async def gen_all_question_lists(
        self, 
        viewer_context: Optional[ViewerContext] = None
    ) -> List[QuestionListMetadata]:
        """
        Get all question lists visible to the viewer.
        
        Args:
            viewer_context: Context about who is viewing (None = anonymous)
        """
        all_lists = await self._question_list_store.get_all()
        
        # Filter by visibility if user is not authenticated
        if not viewer_context or (not viewer_context.is_authenticated):
            result = [lst for lst in all_lists if lst.access_status == AccessStatusEnum.PUBLIC]
            logger.debug(f"Returning {len(result)}/{len(all_lists)} public lists (anonymous)")
            return result
        else:
            logger.debug(f"Returning {len(all_lists)}/{len(all_lists)} visible lists (authenticated)")
            return all_lists

    async def gen_all_questions_in_question_list(
        self,
        question_list_id: int,
        viewer_context: Optional[ViewerContext] = None
    ) -> Optional[List[Question]]:
        """
        Get all questions in a question list visible to the viewer.
        Returns None if the question list doesn't exist or viewer doesn't have access.
        """
        # First, check if the question list exists
        question_list = await self._question_list_store.get_by_id(question_list_id)
        if question_list is None:
            return None
        
        # Check if viewer can access this question list
        if viewer_context and not self._can_view_list(question_list, viewer_context):
            return None
            
        # Check permissions for anonymous users
        if viewer_context is None and question_list.access_status != AccessStatusEnum.PUBLIC:
            return None
            
        # Get question IDs from items, already sorted by order_index
        list_items = await self._question_list_item_store.get_by_list_id(question_list_id)
        question_ids = [item.question_id for item in list_items]
        
        # Use storage layer to get questions
        questions = await self._question_store.get_by_ids(question_ids)
        
        # Preserve order from question_list_items
        questions_by_id = {q.id: q for q in questions}
        return [questions_by_id[qid] for qid in question_ids if qid in questions_by_id]
    
    def _can_view_list(self, question_list: QuestionListMetadata, context: ViewerContext) -> bool:
        """Check if viewer can see this question list"""
        # Public lists are visible to everyone
        if question_list.access_status == AccessStatusEnum.PUBLIC:
            return True
        
        # Authenticated users can see non-public lists
        if context.is_authenticated:
            return True
        
        return False

    # ==================== QUESTION METHODS ====================

    async def gen_question_by_id(
        self,
        question_id: int,
        viewer_context: Optional[ViewerContext] = None
    ) -> Optional[Question]:
        """Get a single question by ID if visible to the viewer."""
        # Use storage layer to get question
        question = await self._question_store.get_by_id(question_id)
        if question is None:
            return None
        
        # Check access
        if not await self._can_view_question(question, viewer_context):
            return None
            
        return question

    async def _can_view_question(self, question: Question, viewer_context: Optional[ViewerContext] = None) -> bool:
        """
        Check if viewer can see this question.
        A question is accessible if it's in at least one question list that the viewer can access.
        """
        # Find all question lists that contain this question
        question_list_ids = await self._question_list_item_store.get_lists_containing_question(question.id)
        
        if not question_list_ids:
            # Question is not in any list - deny access
            return False
        
        # Check if viewer can access at least one of the question lists
        for question_list_id in question_list_ids:
            question_list = await self._question_list_store.get_by_id(question_list_id)
            if question_list is None:
                continue
            
            # Check permission for this list
            ctx = viewer_context if viewer_context else ViewerContext(is_authenticated=False)
            if self._can_view_list(question_list, ctx):
                return True
        
        
        return False

    # ==================== QUESTION MUTATION METHODS (ADMIN) ====================

    async def create_question(self, question_create: QuestionCreate) -> Question:
        """Create a new question (Admin only)."""
        return await self._question_store.create(question_create)

    async def update_question(self, question_id: int, question_update: QuestionUpdate) -> Optional[Question]:
        """Update an existing question (Admin only)."""
        return await self._question_store.update(question_id, question_update)

    async def delete_question(self, question_id: int) -> bool:
        """Delete a question (Admin only)."""
        return await self._question_store.delete(question_id)

    # ==================== QUESTION LIST MUTATION METHODS (ADMIN) ====================

    async def create_question_list(
        self, 
        list_create: 'QuestionListCreate'
    ) -> 'QuestionListWithItems':
        """
        Create a new question list with items (Admin only).
        
        Uses aggregate pattern: creates list + items atomically.
        Validates all question_ids exist before creation.
        
        Args:
            list_create: QuestionListCreate with embedded question_items
            
        Returns:
            QuestionListWithItems containing list metadata and items
            
        Raises:
            ValueError: If any question_id doesn't exist
        """
        from schemas.question_list_mutations import QuestionListCreate
        from schemas.questionList import QuestionListItem, QuestionListMetadataBase
        from datetime import datetime, timezone
        
        # 1. Validate all questions exist
        for item in list_create.question_items:
            question = await self._question_store.get_by_id(item.question_id)
            if question is None:
                raise ValueError(f"Question {item.question_id} not found")
        
        # 2. Create the list (metadata only)
        list_data = QuestionListMetadataBase(
            title=list_create.title,
            description=list_create.description,
            categories=list_create.categories,
            subjects=list_create.subjects,
            difficulty=list_create.difficulty,
            duration_seconds=list_create.duration_seconds,
            access_status=list_create.access_status
        )
        new_list = await self._question_list_store.create(list_data)
        
        # 3. Create the items with auto-assigned order_index if not provided
        now = datetime.now(timezone.utc)
        items_to_create = []
        for idx, item_input in enumerate(list_create.question_items, start=1):
            order = item_input.order_index if item_input.order_index is not None else idx
            items_to_create.append(QuestionListItem(
                question_list_id=new_list.id,
                question_id=item_input.question_id,
                order_index=order,
                weightage=item_input.weightage,
                created_at=now,
                updated_at=now
            ))
        
        created_items = await self._question_list_item_store.add_items(items_to_create)
        
        # 4. Return combined result
        return {"list": new_list, "items": created_items}

    async def update_question_list(
        self,
        list_id: int,
        list_update: 'QuestionListUpdate'
    ) -> Optional[dict]:
        """
        Update a question list (Admin only).
        
        If question_items is provided, replaces all existing items.
        Validates all question_ids exist before update.
        """
        from schemas.question_list_mutations import QuestionListUpdate
        from schemas.questionList import QuestionListItem
        from datetime import datetime, timezone
        
        # Check list exists
        existing = await self._question_list_store.get_by_id(list_id)
        if existing is None:
            return None
        
        # Prepare update data (exclude question_items for the list metadata)
        update_data = list_update.model_dump(exclude_unset=True, exclude={'question_items'})
        
        # Update list metadata if any fields provided
        if update_data:
            updated_list = await self._question_list_store.update(list_id, update_data)
        else:
            updated_list = existing
        
        # If items provided, replace them
        items = None
        if list_update.question_items is not None:
            # Validate all questions exist
            for item in list_update.question_items:
                question = await self._question_store.get_by_id(item.question_id)
                if question is None:
                    raise ValueError(f"Question {item.question_id} not found")
            
            # Create new items
            now = datetime.now(timezone.utc)
            items_to_create = []
            for idx, item_input in enumerate(list_update.question_items, start=1):
                order = item_input.order_index if item_input.order_index is not None else idx
                items_to_create.append(QuestionListItem(
                    question_list_id=list_id,
                    question_id=item_input.question_id,
                    order_index=order,
                    weightage=item_input.weightage,
                    created_at=now,
                    updated_at=now
                ))
            
            items = await self._question_list_item_store.replace_items_for_list(list_id, items_to_create)
        else:
            items = await self._question_list_item_store.get_by_list_id(list_id)
        
        return {"list": updated_list, "items": items}

    async def delete_question_list(self, list_id: int) -> bool:
        """
        Delete a question list and all its items (Admin only).
        
        Cascade delete: removes list metadata + all associated items.
        """
        # Check list exists
        existing = await self._question_list_store.get_by_id(list_id)
        if existing is None:
            return False
        
        # Delete items first (cascade)
        await self._question_list_item_store.remove_items_by_list(list_id)
        
        # Delete list metadata
        return await self._question_list_store.delete(list_id)
