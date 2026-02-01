"""
Unit tests for JsonQuestionStore
"""
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from storage.question_store import JsonQuestionStore
from schemas.question import Question
from schemas.question_mutations import QuestionCreate, QuestionUpdate


@pytest.fixture
def mock_data_dir(tmp_path):
    """Create a temporary directory with sample question data"""
    data = {
        "questions": [
            {
                "id": 1,
                "title": "Test Question 1",
                "question_details": "Details 1",
                "think_time_limit_seconds": 60,
                "record_time_limit_seconds": 120,
                "instructions": ["Ins 1"],
                "hints": [{"text": "Hint 1"}],
                "question_image_url": None,
                "subjects": ["Mathematics"],
                "topics": ["Mathematics"],
                "difficulty": "medium",
                "rubric_id": 1,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        ]
    }
    
    questions_file = tmp_path / "questions.json"
    with open(questions_file, "w") as f:
        json.dump(data, f)
        
    return tmp_path


@pytest.fixture
def mock_rubric_store():
    """Create a mock rubric store for FK validation"""
    store = MagicMock()
    # Default: rubric 1 exists, 999 does not
    async def mock_get_by_id(rubric_id):
        if rubric_id == 1:
            return MagicMock(id=1)
        return None
    store.get_by_id = AsyncMock(side_effect=mock_get_by_id)
    return store


@pytest.fixture
def sample_question_create():
    """Create a sample question for testing"""
    return QuestionCreate(
        title="New Test Question",
        question_details="New details",
        think_time_limit_seconds=30,
        record_time_limit_seconds=90,
        instructions=["Test instruction"],
        hints=[{"text": "Test hint"}],
        question_image_url=None,
        subjects=["Mathematics"],
        topics=["Mathematics"],
        difficulty="easy",
        rubric_id=1
    )


@pytest.mark.asyncio
async def test_load_questions_success(mock_data_dir):
    """Test loading questions from valid JSON file"""
    store = JsonQuestionStore(data_dir=mock_data_dir)
    
    questions = await store.get_all()
    assert len(questions) == 1
    assert questions[0].id == 1
    assert questions[0].title == "Test Question 1"

@pytest.mark.asyncio
async def test_get_by_id_found(mock_data_dir):
    """Test get_by_id returns question when found"""
    store = JsonQuestionStore(data_dir=mock_data_dir)
    original_question = await store.get_by_id(1)
    
    # Store loads once, so verify in-memory access
    result = await store.get_by_id(1)
    assert result is not None
    assert result.id == 1
    assert result == original_question

@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_data_dir):
    """Test get_by_id returns None when not found"""
    store = JsonQuestionStore(data_dir=mock_data_dir)
    
    result = await store.get_by_id(999)
    assert result is None

@pytest.mark.asyncio
async def test_missing_file_handled_gracefully(tmp_path):
    """Test that missing file results in empty store, no crash"""
    # Empty dir, no questions.json
    store = JsonQuestionStore(data_dir=tmp_path)
    
    questions = await store.get_all()
    assert len(questions) == 0

@pytest.mark.asyncio
async def test_get_by_ids(mock_data_dir):
    """Test get_by_ids returns correctly filtered list"""
    store = JsonQuestionStore(data_dir=mock_data_dir)
    
    # Request existing and non-existing
    results = await store.get_by_ids([1, 999])
    
    assert len(results) == 1
    assert results[0].id == 1


# ==================== NEW TESTS FOR CRUD OPERATIONS ====================

@pytest.mark.asyncio
async def test_create_with_valid_rubric_id(mock_data_dir, mock_rubric_store, sample_question_create):
    """Test creating a question with valid rubric_id"""
    store = JsonQuestionStore(data_dir=mock_data_dir, rubric_store=mock_rubric_store)
    
    new_question = await store.create(sample_question_create)
    
    # Should have id=2 (after existing id=1)
    assert new_question.id == 2
    assert new_question.rubric_id == 1
    assert new_question.title == "New Test Question"
    
    # Verify it was saved
    all_questions = await store.get_all()
    assert len(all_questions) == 2


@pytest.mark.asyncio
async def test_create_with_invalid_rubric_id_raises(mock_data_dir, mock_rubric_store):
    """Test that creating a question with invalid rubric_id raises ValueError"""
    store = JsonQuestionStore(data_dir=mock_data_dir, rubric_store=mock_rubric_store)
    
    question = QuestionCreate(
        title="Bad Rubric Question",
        question_details="Details",
        think_time_limit_seconds=30,
        record_time_limit_seconds=90,
        instructions=["Ins"],
        hints=[{"text": "Hint"}],
        subjects=["Mathematics"],
        topics=["Mathematics"],
        difficulty="easy",
        rubric_id=999  # Non-existent rubric
    )
    
    with pytest.raises(ValueError, match="Rubric 999 not found"):
        await store.create(question)


@pytest.mark.asyncio
async def test_create_without_rubric_store_skips_validation(mock_data_dir, sample_question_create):
    """Test that create works without rubric_store (backward compatibility)"""
    store = JsonQuestionStore(data_dir=mock_data_dir)  # No rubric_store
    
    # Modify to use non-existent rubric - should succeed without validation
    sample_question_create.rubric_id = 999
    new_question = await store.create(sample_question_create)
    
    assert new_question.id == 2
    assert new_question.rubric_id == 999


@pytest.mark.asyncio
async def test_update_modifies_question(mock_data_dir):
    """Test updating a question"""
    store = JsonQuestionStore(data_dir=mock_data_dir)
    
    # Get original
    original = await store.get_by_id(1)
    assert original.title == "Test Question 1"
    
    # Update it
    updated = await store.update(1, QuestionUpdate(title="Updated Title"))
    
    assert updated is not None
    assert updated.id == 1
    assert updated.title == "Updated Title"
    assert updated.rubric_id == 1  # Unchanged
    
    # Verify persistence
    reloaded = await store.get_by_id(1)
    assert reloaded.title == "Updated Title"


@pytest.mark.asyncio
async def test_update_nonexistent_returns_none(mock_data_dir):
    """Test updating a non-existent question returns None"""
    store = JsonQuestionStore(data_dir=mock_data_dir)
    
    result = await store.update(999, QuestionUpdate(title="Won't work"))
    assert result is None


@pytest.mark.asyncio
async def test_delete_removes_question(mock_data_dir):
    """Test deleting a question"""
    store = JsonQuestionStore(data_dir=mock_data_dir)
    
    # Verify exists
    assert await store.get_by_id(1) is not None
    
    # Delete it
    result = await store.delete(1)
    assert result is True
    
    # Verify gone
    assert await store.get_by_id(1) is None
    
    # Delete again should return False
    result_again = await store.delete(1)
    assert result_again is False


@pytest.mark.asyncio
async def test_validate_rubric_exists_with_store(mock_data_dir, mock_rubric_store):
    """Test FK validation helper"""
    store = JsonQuestionStore(data_dir=mock_data_dir, rubric_store=mock_rubric_store)
    
    # Rubric 1 exists
    assert await store.validate_rubric_exists(1) is True
    
    # Rubric 999 does not exist
    assert await store.validate_rubric_exists(999) is False


@pytest.mark.asyncio
async def test_validate_rubric_exists_without_store(mock_data_dir):
    """Test FK validation returns True when no rubric_store configured"""
    store = JsonQuestionStore(data_dir=mock_data_dir)  # No rubric_store
    
    # Should always return True (skip validation)
    assert await store.validate_rubric_exists(1) is True
    assert await store.validate_rubric_exists(999) is True
