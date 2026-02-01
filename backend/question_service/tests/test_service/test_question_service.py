"""
Unit tests for QuestionService
"""
import sys
from pathlib import Path

# Add the question_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

import pytest
import json
from services.question_service import QuestionService


class TestQuestionService:
    """Test QuestionService business logic"""
    
    @pytest.mark.asyncio
    async def test_get_all_question_lists_returns_all_lists(self, question_service_with_test_data):
        """Test that get_all_question_lists returns all question lists when authenticated"""
        service = question_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        # Use authenticated context to see all lists
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_all_question_lists(viewer_context=authenticated_context)
        
        assert len(result) == 3  # Now we have 3 lists in test data
        assert result[0].id == 1
        assert result[0].title == "Test List"
        assert result[0].categories == ["Graph Plotting"]
        assert result[1].id == 2
        assert result[1].title == "Test List 2"
    

    @pytest.mark.asyncio
    async def test_get_all_question_lists_returns_empty_list_when_no_data(self, test_data_dir):
        """Test that get_all_question_lists returns empty list when no data"""
        # Create empty data files
        (test_data_dir / "question_lists.json").write_text(
            json.dumps({"question_lists": []}), encoding="utf-8"
        )
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps({"question_list_items": []}), encoding="utf-8"
        )
        (test_data_dir / "questions.json").write_text(
            json.dumps({"questions": []}), encoding="utf-8"
        )
        
        service = QuestionService(data_dir=test_data_dir)
        await service.initialize()
        
        result = await service.gen_all_question_lists(viewer_context=None)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_gen_all_questions_in_question_list_returns_questions_in_order(self, question_service_with_test_data):
        """Test that gen_all_questions_in_question_list returns questions sorted by order_index"""
        service = question_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_all_questions_in_question_list(question_list_id=1, viewer_context=authenticated_context)
        
        # Should return 3 questions for question list 1
        assert result is not None
        assert len(result) == 3
        # Questions should be in order by order_index
        assert result[0].id == 1
        assert result[0].title == "Plot y = e^x"
        assert result[1].id == 2
        assert result[1].title == "Plot y = sin(x)"
        assert result[2].id == 3
        assert result[2].title == "Plot y = e^x * sin(x)"

    @pytest.mark.asyncio
    async def test_gen_all_questions_in_question_list_returns_none_for_nonexistent_list(self, question_service_with_test_data):
        """Test that gen_all_questions_in_question_list returns None for non-existent question list"""
        service = question_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_all_questions_in_question_list(question_list_id=999, viewer_context=authenticated_context)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_gen_all_questions_in_question_list_authorization_blocks_private_lists_for_anonymous(self, question_service_with_test_data):
        """Test that anonymous users cannot access private question lists"""
        service = question_service_with_test_data
        
        # Question list 2 is private (is_public=False)
        # Anonymous user (viewer_context=None) should not be able to access it
        result = await service.gen_all_questions_in_question_list(question_list_id=2, viewer_context=None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_gen_all_questions_in_question_list_authorization_allows_public_lists_for_anonymous(self, question_service_with_test_data):
        """Test that anonymous users CAN access public question lists"""
        service = question_service_with_test_data
        
        # Question list 1 is public (is_public=True)
        # Anonymous user (viewer_context=None) should be able to access it
        result = await service.gen_all_questions_in_question_list(question_list_id=1, viewer_context=None)
        
        assert result is not None
        assert len(result) == 3
        assert [q.id for q in result] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_gen_all_questions_in_question_list_returns_correct_questions_for_different_lists(self, question_service_with_test_data):
        """Test that gen_all_questions_in_question_list returns correct questions for different question lists"""
        service = question_service_with_test_data
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        # Question list 1 (public) has questions 1, 2, 3
        result_list_1 = await service.gen_all_questions_in_question_list(question_list_id=1, viewer_context=authenticated_context)
        assert result_list_1 is not None
        assert len(result_list_1) == 3
        assert [q.id for q in result_list_1] == [1, 2, 3]
        
        # Question list 2 (private) has questions 2, 3 - authenticated user can see it
        result_list_2 = await service.gen_all_questions_in_question_list(question_list_id=2, viewer_context=authenticated_context)
        assert result_list_2 is not None
        assert len(result_list_2) == 2
        assert [q.id for q in result_list_2] == [2, 3]
        
        # Question list 3 (public) has no questions - should return empty list
        result_list_3 = await service.gen_all_questions_in_question_list(question_list_id=3, viewer_context=authenticated_context)
        assert result_list_3 == []

    @pytest.mark.asyncio
    async def test_gen_all_questions_in_question_list_handles_non_sequential_order_index(self, test_data_dir, sample_questions_data):
        """Test that gen_all_questions_in_question_list correctly sorts by order_index even when not sequential"""
        # Create test data with non-sequential order_index values
        question_lists_data = {
            "question_lists": [
                {
                    "id": 1,
                    "title": "Test List",
                    "description": "Test description",
                    "categories": ["Graph Plotting"],
                    "subjects": ["Engineering"],
                    "difficulty": "Easy",
                    "duration_seconds": 1800,
                    "access_status": "public",
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                }
            ],
            "question_list_items": [
                {
                    "question_list_id": 1,
                    "question_id": 3,
                    "order_index": 10,
                    "weightage": 0.34,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                },
                {
                    "question_list_id": 1,
                    "question_id": 1,
                    "order_index": 5,
                    "weightage": 0.33,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                },
                {
                    "question_list_id": 1,
                    "question_id": 2,
                    "order_index": 7,
                    "weightage": 0.33,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                }
            ]
        }
        
        # Write question lists (without question_list_items)
        question_lists_only = {
            "question_lists": question_lists_data["question_lists"]
        }
        (test_data_dir / "question_lists.json").write_text(
            json.dumps(question_lists_only), encoding="utf-8"
        )
        
        # Write question list items to separate file
        question_list_items_only = {
            "question_list_items": question_lists_data["question_list_items"]
        }
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps(question_list_items_only), encoding="utf-8"
        )
        
        (test_data_dir / "questions.json").write_text(
            json.dumps(sample_questions_data), encoding="utf-8"
        )
        
        service = QuestionService(data_dir=test_data_dir)
        await service.initialize()
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_all_questions_in_question_list(question_list_id=1, viewer_context=authenticated_context)
        
        # Should be sorted by order_index: 5, 7, 10
        assert result is not None
        assert len(result) == 3
        assert result[0].id == 1  # order_index 5
        assert result[1].id == 2  # order_index 7
        assert result[2].id == 3  # order_index 10

    @pytest.mark.asyncio
    async def test_gen_all_questions_in_question_list_handles_missing_questions(self, test_data_dir, sample_questions_data):
        """Test that gen_all_questions_in_question_list handles question_list_items referencing non-existent questions"""
        # Create test data where a question_list_item references a question that doesn't exist
        question_lists_data = {
            "question_lists": [
                {
                    "id": 1,
                    "title": "Test List",
                    "description": "Test description",
                    "categories": ["Graph Plotting"],
                    "subjects": ["Engineering"],
                    "difficulty": "Easy",
                    "duration_seconds": 1800,
                    "access_status": "public",
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                }
            ],
            "question_list_items": [
                {
                    "question_list_id": 1,
                    "question_id": 1,
                    "order_index": 1,
                    "weightage": 0.33,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                },
                {
                    "question_list_id": 1,
                    "question_id": 999,  # Non-existent question
                    "order_index": 2,
                    "weightage": 0.33,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                },
                {
                    "question_list_id": 1,
                    "question_id": 2,
                    "order_index": 3,
                    "weightage": 0.34,
                    "created_at": "2025-11-06T00:00:00Z",
                    "updated_at": "2025-11-06T00:00:00Z"
                }
            ]
        }
        
        # Write question lists (without question_list_items)
        question_lists_only = {
            "question_lists": question_lists_data["question_lists"]
        }
        (test_data_dir / "question_lists.json").write_text(
            json.dumps(question_lists_only), encoding="utf-8"
        )
        
        # Write question list items to separate file
        question_list_items_only = {
            "question_list_items": question_lists_data["question_list_items"]
        }
        (test_data_dir / "question_list_items.json").write_text(
            json.dumps(question_list_items_only), encoding="utf-8"
        )
        
        (test_data_dir / "questions.json").write_text(
            json.dumps(sample_questions_data), encoding="utf-8"
        )
        
        service = QuestionService(data_dir=test_data_dir)
        await service.initialize()
        from schemas.viewer_context import ViewerContext
        
        authenticated_context = ViewerContext(
            user_id=1,
            is_authenticated=True,
            role="student",
            permissions=[]
        )
        
        result = await service.gen_all_questions_in_question_list(question_list_id=1, viewer_context=authenticated_context)
        
        # Should only return questions that exist (1 and 2)
        assert result is not None
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2

