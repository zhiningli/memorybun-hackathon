"""
Unit tests for JsonAnswerStore
"""
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from storage.answer_store import JsonAnswerStore
from schemas.answer_mutations import AnswerCreate, AnswerUpdate


@pytest.fixture
def mock_data_dir(tmp_path):
    """Create a temporary directory with sample answer data"""
    data = {
        "answers": [
            {
                "id": 1,
                "question_id": 101,
                "text_answer": "Answer 1",
                "graph_answer_url": None,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        ]
    }
    
    answers_file = tmp_path / "answers.json"
    with open(answers_file, "w") as f:
        json.dump(data, f)
        
    return tmp_path


@pytest.fixture
def mock_question_store():
    """Create a mock question store for FK validation"""
    store = MagicMock()
    # Default: question 101 exists, 999 does not
    async def mock_get_by_id(question_id):
        if question_id == 101:
            return MagicMock(id=101)
        return None
    store.get_by_id = AsyncMock(side_effect=mock_get_by_id)
    return store


@pytest.mark.asyncio
async def test_load_answers_success(mock_data_dir):
    """Test loading answers from valid JSON file"""
    store = JsonAnswerStore(data_dir=mock_data_dir)
    
    answers = await store.get_all()
    assert len(answers) == 1
    assert answers[0].id == 1
    assert answers[0].question_id == 101

@pytest.mark.asyncio
async def test_get_by_id(mock_data_dir):
    """Test get_by_id returns answer"""
    store = JsonAnswerStore(data_dir=mock_data_dir)
    
    result = await store.get_by_id(1)
    assert result is not None
    assert result.id == 1

@pytest.mark.asyncio
async def test_get_by_question_id(mock_data_dir):
    """Test get_by_question_id returns correct answer"""
    store = JsonAnswerStore(data_dir=mock_data_dir)
    
    result = await store.get_by_question_id(101)
    assert result is not None
    assert result.id == 1
    assert result.question_id == 101
    
    # Test non-existent Question ID
    result_none = await store.get_by_question_id(999)
    assert result_none is None

@pytest.mark.asyncio
async def test_missing_file(tmp_path):
    """Test handling of missing answers.json"""
    store = JsonAnswerStore(data_dir=tmp_path)
    
    answers = await store.get_all()
    assert len(answers) == 0


# ==================== NEW TESTS FOR CRUD OPERATIONS ====================

@pytest.mark.asyncio
async def test_create_with_valid_question_id(mock_data_dir, mock_question_store):
    """Test creating an answer with valid question_id"""
    store = JsonAnswerStore(data_dir=mock_data_dir, question_store=mock_question_store)
    
    # Existing answer has id=1
    existing = await store.get_all()
    assert len(existing) == 1
    
    new_answer = await store.create(AnswerCreate(
        question_id=101,  # Valid question
        text_answer="New answer for question 101"
    ))
    
    # Should have id=2
    assert new_answer.id == 2
    assert new_answer.question_id == 101
    assert new_answer.text_answer == "New answer for question 101"
    
    # Verify it was saved
    all_answers = await store.get_all()
    assert len(all_answers) == 2


@pytest.mark.asyncio
async def test_create_with_invalid_question_id_raises(mock_data_dir, mock_question_store):
    """Test that creating an answer with invalid question_id raises ValueError"""
    store = JsonAnswerStore(data_dir=mock_data_dir, question_store=mock_question_store)
    
    with pytest.raises(ValueError, match="Question 999 not found"):
        await store.create(AnswerCreate(
            question_id=999,  # Non-existent question
            text_answer="This should fail"
        ))


@pytest.mark.asyncio
async def test_create_without_question_store_skips_validation(mock_data_dir):
    """Test that create works without question_store (backward compatibility)"""
    store = JsonAnswerStore(data_dir=mock_data_dir)  # No question_store
    
    # Should succeed even with non-existent question_id
    new_answer = await store.create(AnswerCreate(
        question_id=999,  # Would fail if validated
        text_answer="No validation"
    ))
    
    assert new_answer.id == 2
    assert new_answer.question_id == 999


@pytest.mark.asyncio
async def test_update_modifies_answer(mock_data_dir):
    """Test updating an answer"""
    store = JsonAnswerStore(data_dir=mock_data_dir)
    
    # Get original
    original = await store.get_by_id(1)
    assert original.text_answer == "Answer 1"
    
    # Update it
    updated = await store.update(1, AnswerUpdate(text_answer="Updated answer"))
    
    assert updated is not None
    assert updated.id == 1
    assert updated.text_answer == "Updated answer"
    assert updated.question_id == 101  # Unchanged
    
    # Verify persistence
    reloaded = await store.get_by_id(1)
    assert reloaded.text_answer == "Updated answer"


@pytest.mark.asyncio
async def test_update_nonexistent_returns_none(mock_data_dir):
    """Test updating a non-existent answer returns None"""
    store = JsonAnswerStore(data_dir=mock_data_dir)
    
    result = await store.update(999, AnswerUpdate(text_answer="Won't work"))
    assert result is None


@pytest.mark.asyncio
async def test_delete_removes_answer(mock_data_dir):
    """Test deleting an answer"""
    store = JsonAnswerStore(data_dir=mock_data_dir)
    
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
async def test_validate_question_exists_with_store(mock_data_dir, mock_question_store):
    """Test FK validation helper"""
    store = JsonAnswerStore(data_dir=mock_data_dir, question_store=mock_question_store)
    
    # Question 101 exists
    assert await store.validate_question_exists(101) is True
    
    # Question 999 does not exist
    assert await store.validate_question_exists(999) is False


@pytest.mark.asyncio
async def test_validate_question_exists_without_store(mock_data_dir):
    """Test FK validation returns True when no question_store configured"""
    store = JsonAnswerStore(data_dir=mock_data_dir)  # No question_store
    
    # Should always return True (skip validation)
    assert await store.validate_question_exists(101) is True
    assert await store.validate_question_exists(999) is True
