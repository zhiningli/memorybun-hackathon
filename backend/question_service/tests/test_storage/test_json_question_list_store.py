"""
Unit tests for JsonQuestionListStore
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from storage.question_list_store import JsonQuestionListStore
from schemas.questionList import QuestionListMetadata, QuestionListMetadataBase, QuestionListCategoryEnum, SubjectEnum, QuestionListDifficultyEnum

@pytest.fixture
def mock_data_dir(tmp_path):
    """Create a temporary directory with sample question list data"""
    data = {
        "question_lists": [
            {
                "id": 1,
                "title": "Test List 1",
                "description": "Description 1",
                "categories": ["Graph Plotting"],
                "subjects": ["Mathematics"],
                "difficulty": "Easy",
                "duration_seconds": 1800,
                "access_status": "public",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        ]
    }
    
    lists_file = tmp_path / "question_lists.json"
    with open(lists_file, "w") as f:
        json.dump(data, f)
        
    return tmp_path

@pytest.fixture
def sample_list_base():
    return QuestionListMetadataBase(
        title="New List",
        description="New Desc",
        categories=[QuestionListCategoryEnum.GRAPH_PLOTTING],
        subjects=[SubjectEnum.MATHEMATICS],
        difficulty=QuestionListDifficultyEnum.MEDIUM,
        duration_seconds=3600,
        access_status="private"
    )

@pytest.mark.asyncio
async def test_load_question_lists_success(mock_data_dir):
    store = JsonQuestionListStore(data_dir=mock_data_dir)
    lists = await store.get_all()
    assert len(lists) == 1
    assert lists[0].id == 1
    assert lists[0].title == "Test List 1"

@pytest.mark.asyncio
async def test_create_question_list(mock_data_dir, sample_list_base):
    store = JsonQuestionListStore(data_dir=mock_data_dir)
    
    new_list = await store.create(sample_list_base)
    
    assert new_list.id == 2
    assert new_list.title == "New List"
    assert isinstance(new_list.created_at, datetime)
    
    # Verify persistence
    all_lists = await store.get_all()
    assert len(all_lists) == 2

@pytest.mark.asyncio
async def test_update_question_list(mock_data_dir):
    store = JsonQuestionListStore(data_dir=mock_data_dir)
    
    updated = await store.update(1, {"title": "Updated Title", "duration_seconds": 999})
    
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.duration_seconds == 999
    
    # Verify persistence
    reloaded = await store.get_by_id(1)
    assert reloaded.title == "Updated Title"

@pytest.mark.asyncio
async def test_update_nonexistent_returns_none(mock_data_dir):
    store = JsonQuestionListStore(data_dir=mock_data_dir)
    result = await store.update(999, {"title": "Fail"})
    assert result is None

@pytest.mark.asyncio
async def test_delete_question_list(mock_data_dir):
    store = JsonQuestionListStore(data_dir=mock_data_dir)
    
    # Delete existing
    assert await store.delete(1) is True
    assert await store.get_by_id(1) is None
    
    # Delete again
    assert await store.delete(1) is False
