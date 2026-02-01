"""
Unit tests for AnswerService
"""
import sys
from pathlib import Path

# Add the question_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

import pytest
import json
from services.answer_service import AnswerService


class TestAnswerService:
    """Test AnswerService business logic"""
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_returns_answer(self, answer_service_with_test_data):
        """Test that gen_answer_by_question_id returns answer when question exists and is accessible"""
        service = answer_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        # Use authenticated context to see all answers
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_answer_by_question_id(question_id=1, viewer_context=authenticated_context)
        
        assert result is not None
        assert result.id == 1
        assert result.question_id == 1
        assert result.text_answer is not None
        assert "e^x" in result.text_answer
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_returns_none_for_nonexistent_question(self, answer_service_with_test_data):
        """Test that gen_answer_by_question_id returns None for non-existent question"""
        service = answer_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_answer_by_question_id(question_id=999, viewer_context=authenticated_context)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_returns_none_for_nonexistent_answer(self, test_data_dir, sample_question_lists_data, sample_questions_data):
        """Test that gen_answer_by_question_id returns None when question exists but answer doesn't"""
        # Create test data with questions but no answers
        question_lists_only = {
            "question_lists": sample_question_lists_data["question_lists"]
        }
        (test_data_dir / "question_lists.json").write_text(
            json.dumps(question_lists_only), encoding="utf-8"
        )
        
        question_list_items_only = {
            "question_list_items": sample_question_lists_data["question_list_items"]
        }
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps(question_list_items_only), encoding="utf-8"
        )
        
        (test_data_dir / "questions.json").write_text(
            json.dumps(sample_questions_data), encoding="utf-8"
        )
        
        # Create empty answers file
        (test_data_dir / "answers.json").write_text(
            json.dumps({"answers": []}), encoding="utf-8"
        )
        
        service = AnswerService(data_dir=test_data_dir)
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_answer_by_question_id(question_id=1, viewer_context=authenticated_context)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_authorization_allows_public_questions_for_anonymous(self, answer_service_with_test_data):
        """Test that anonymous users CAN access answers for public questions"""
        service = answer_service_with_test_data
        
        # Question 1 is in question list 1 which is public (is_public=True)
        # Anonymous user (viewer_context=None) should be able to access it
        result = await service.gen_answer_by_question_id(question_id=1, viewer_context=None)
        
        assert result is not None
        assert result.question_id == 1
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_authorization_blocks_private_questions_for_anonymous(self, test_data_dir, sample_question_lists_data, sample_questions_data, sample_answers_data):
        """Test that anonymous users cannot access answers for questions ONLY in private lists"""
        # Create test data where question 4 is ONLY in private list 2
        question_lists_only = {
            "question_lists": sample_question_lists_data["question_lists"]
        }
        (test_data_dir / "question_lists.json").write_text(
            json.dumps(question_lists_only), encoding="utf-8"
        )
        
        # Add a question that's only in private list 2
        question_list_items = sample_question_lists_data["question_list_items"].copy()
        question_list_items.append({
            "question_list_id": 2,  # Private list
            "question_id": 4,
            "order_index": 3,
            "weightage": 1.0,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        question_list_items_only = {
            "question_list_items": question_list_items
        }
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps(question_list_items_only), encoding="utf-8"
        )
        
        # Add question 4 to questions data
        questions_data = sample_questions_data.copy()
        questions_data["questions"].append({
            "id": 4,
            "title": "Private Question",
            "question_details": "This question is only in a private list",
            "think_time_limit_seconds": 20,
            "record_time_limit_seconds": 60,
            "instructions": ["Test"],
            "hints": [{"text": "Test hint", "image_url": None}],
            "question_image_url": None,
            "subjects": ["Mathematics"],
            "topics": ["Mathematics"],
            "difficulty": "easy",
            "rubric_id": 1,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        (test_data_dir / "questions.json").write_text(
            json.dumps(questions_data), encoding="utf-8"
        )
        
        # Add answer for question 4
        answers_data = sample_answers_data.copy()
        answers_data["answers"].append({
            "id": 4,
            "question_id": 4,
            "text_answer": "Answer for private question",
            "graph_answer_url": None,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        (test_data_dir / "answers.json").write_text(
            json.dumps(answers_data), encoding="utf-8"
        )
        
        service = AnswerService(data_dir=test_data_dir)
        
        # Question 4 is ONLY in question list 2 which is private (is_public=False)
        # Anonymous user (viewer_context=None) should not be able to access it
        result = await service.gen_answer_by_question_id(question_id=4, viewer_context=None)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_authorization_allows_private_questions_for_authenticated(self, answer_service_with_test_data):
        """Test that authenticated users CAN access answers for questions in private lists"""
        service = answer_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        # Question 2 is in question list 2 which is private, but authenticated user should access it
        result = await service.gen_answer_by_question_id(question_id=2, viewer_context=authenticated_context)
        
        assert result is not None
        assert result.question_id == 2
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_handles_question_in_multiple_lists(self, test_data_dir, sample_question_lists_data, sample_questions_data, sample_answers_data):
        """Test that gen_answer_by_question_id works when question is in multiple lists (one public, one private)"""
        # Question 2 is in both list 1 (public) and list 2 (private)
        # This test ensures the authorization logic works correctly
        
        question_lists_only = {
            "question_lists": sample_question_lists_data["question_lists"]
        }
        (test_data_dir / "question_lists.json").write_text(
            json.dumps(question_lists_only), encoding="utf-8"
        )
        
        question_list_items_only = {
            "question_list_items": sample_question_lists_data["question_list_items"]
        }
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps(question_list_items_only), encoding="utf-8"
        )
        
        (test_data_dir / "questions.json").write_text(
            json.dumps(sample_questions_data), encoding="utf-8"
        )
        
        (test_data_dir / "answers.json").write_text(
            json.dumps(sample_answers_data), encoding="utf-8"
        )
        
        service = AnswerService(data_dir=test_data_dir)
        
        # Anonymous user should be able to access question 2 because it's in public list 1
        result = await service.gen_answer_by_question_id(question_id=2, viewer_context=None)
        
        assert result is not None
        assert result.question_id == 2
    
    @pytest.mark.asyncio
    async def test_gen_answer_by_question_id_returns_none_for_question_not_in_any_list(self, test_data_dir, sample_question_lists_data, sample_questions_data, sample_answers_data):
        """Test that gen_answer_by_question_id returns None when question is not in any list"""
        # Create a question that's not in any list
        questions_data = sample_questions_data.copy()
        questions_data["questions"].append({
            "id": 999,
            "title": "Orphaned Question",
            "question_details": "This question is not in any list",
            "think_time_limit_seconds": 20,
            "record_time_limit_seconds": 60,
            "instructions": ["Test"],
            "hints": [{"text": "Test hint", "image_url": None}],
            "question_image_url": None,
            "subjects": ["Mathematics"],
            "topics": ["Mathematics"],
            "difficulty": "easy",
            "rubric_id": 1,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        
        # Create an answer for this orphaned question
        answers_data = sample_answers_data.copy()
        answers_data["answers"].append({
            "id": 999,
            "question_id": 999,
            "text_answer": "Answer for orphaned question",
            "graph_answer_url": None,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        
        question_lists_only = {
            "question_lists": sample_question_lists_data["question_lists"]
        }
        (test_data_dir / "question_lists.json").write_text(
            json.dumps(question_lists_only), encoding="utf-8"
        )
        
        question_list_items_only = {
            "question_list_items": sample_question_lists_data["question_list_items"]
        }
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps(question_list_items_only), encoding="utf-8"
        )
        
        (test_data_dir / "questions.json").write_text(
            json.dumps(questions_data), encoding="utf-8"
        )
        
        (test_data_dir / "answers.json").write_text(
            json.dumps(answers_data), encoding="utf-8"
        )
        
        service = AnswerService(data_dir=test_data_dir)
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        # Should return None because question is not in any list
        result = await service.gen_answer_by_question_id(question_id=999, viewer_context=authenticated_context)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_gen_answers_by_question_ids_returns_multiple_answers(self, answer_service_with_test_data):
        """Test that gen_answers_by_question_ids returns multiple answers"""
        service = answer_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_answers_by_question_ids(question_ids=[1, 2, 3], viewer_context=authenticated_context)
        
        assert isinstance(result, list)
        assert len(result) == 3
        question_ids = [answer.question_id for answer in result]
        assert 1 in question_ids
        assert 2 in question_ids
        assert 3 in question_ids
    
    @pytest.mark.asyncio
    async def test_gen_answers_by_question_ids_filters_inaccessible_questions(self, test_data_dir, sample_question_lists_data, sample_questions_data, sample_answers_data):
        """Test that gen_answers_by_question_ids only returns accessible answers"""
        # Create test data where question 4 is ONLY in private list 2
        question_lists_only = {
            "question_lists": sample_question_lists_data["question_lists"]
        }
        (test_data_dir / "question_lists.json").write_text(
            json.dumps(question_lists_only), encoding="utf-8"
        )
        
        # Add question 4 only to private list 2
        question_list_items = sample_question_lists_data["question_list_items"].copy()
        question_list_items.append({
            "question_list_id": 2,  # Private list
            "question_id": 4,
            "order_index": 3,
            "weightage": 1.0,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        question_list_items_only = {
            "question_list_items": question_list_items
        }
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps(question_list_items_only), encoding="utf-8"
        )
        
        # Add question 4 to questions data
        questions_data = sample_questions_data.copy()
        questions_data["questions"].append({
            "id": 4,
            "title": "Private Question",
            "question_details": "This question is only in a private list",
            "think_time_limit_seconds": 20,
            "record_time_limit_seconds": 60,
            "instructions": ["Test"],
            "hints": [{"text": "Test hint", "image_url": None}],
            "question_image_url": None,
            "subjects": ["Mathematics"],
            "topics": ["Mathematics"],
            "difficulty": "easy",
            "rubric_id": 1,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        (test_data_dir / "questions.json").write_text(
            json.dumps(questions_data), encoding="utf-8"
        )
        
        # Add answer for question 4
        answers_data = sample_answers_data.copy()
        answers_data["answers"].append({
            "id": 4,
            "question_id": 4,
            "text_answer": "Answer for private question",
            "graph_answer_url": None,
            "created_at": "2025-11-06T00:00:00Z",
            "updated_at": "2025-11-06T00:00:00Z"
        })
        (test_data_dir / "answers.json").write_text(
            json.dumps(answers_data), encoding="utf-8"
        )
        
        service = AnswerService(data_dir=test_data_dir)
        
        # Question 1 is in public list, question 4 is ONLY in private list
        # Anonymous user should only get answer for question 1
        result = await service.gen_answers_by_question_ids(question_ids=[1, 4], viewer_context=None)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].question_id == 1
    
    @pytest.mark.asyncio
    async def test_gen_answers_by_question_ids_returns_empty_list_for_nonexistent_questions(self, answer_service_with_test_data):
        """Test that gen_answers_by_question_ids returns empty list for non-existent questions"""
        service = answer_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_answers_by_question_ids(question_ids=[999, 1000], viewer_context=authenticated_context)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_gen_answers_by_question_ids_handles_mixed_valid_and_invalid(self, answer_service_with_test_data):
        """Test that gen_answers_by_question_ids handles mix of valid and invalid question IDs"""
        service = answer_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_answers_by_question_ids(question_ids=[1, 999, 2], viewer_context=authenticated_context)
        
        assert isinstance(result, list)
        assert len(result) == 2  # Only questions 1 and 2 should be returned
        question_ids = [answer.question_id for answer in result]
        assert 1 in question_ids
        assert 2 in question_ids
        assert 999 not in question_ids

