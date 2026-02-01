"""
Unit tests for JsonQuestionListItemStore
"""
import pytest
import json
from pathlib import Path
from storage.question_list_item_store import JsonQuestionListItemStore
from schemas.questionList import QuestionListItem
from datetime import datetime, timezone

@pytest.fixture
def mock_data_dir(tmp_path):
    """Create a temporary directory with sample question list items data"""
    data = {
        "question_list_items": [
            {
                "question_list_id": 1,
                "question_id": 1,
                "order_index": 1,
                "weightage": 0.5,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            },
            {
                "question_list_id": 1,
                "question_id": 2,
                "order_index": 2,
                "weightage": 0.5,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        ]
    }
    
    items_file = tmp_path / "question_list_items.json"
    with open(items_file, "w") as f:
        json.dump(data, f)
        
    return tmp_path

@pytest.mark.asyncio
async def test_load_items_success(mock_data_dir):
    store = JsonQuestionListItemStore(data_dir=mock_data_dir)
    items = await store.get_all()
    assert len(items) == 2

@pytest.mark.asyncio
async def test_get_by_list_id(mock_data_dir):
    store = JsonQuestionListItemStore(data_dir=mock_data_dir)
    items = await store.get_by_list_id(1)
    assert len(items) == 2
    assert items[0].order_index == 1
    assert items[1].order_index == 2

@pytest.mark.asyncio
async def test_add_items(mock_data_dir):
    store = JsonQuestionListItemStore(data_dir=mock_data_dir)
    
    new_items = [
        QuestionListItem(
            question_list_id=2,
            question_id=3,
            order_index=1,
            weightage=1.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]
    
    await store.add_items(new_items)
    
    all_items = await store.get_all()
    assert len(all_items) == 3
    
    list2_items = await store.get_by_list_id(2)
    assert len(list2_items) == 1
    assert list2_items[0].question_id == 3

@pytest.mark.asyncio
async def test_remove_items_by_list(mock_data_dir):
    store = JsonQuestionListItemStore(data_dir=mock_data_dir)
    
    # Remove list 1 items
    count = await store.remove_items_by_list(1)
    assert count == 2
    
    # Verify gone
    items = await store.get_by_list_id(1)
    assert len(items) == 0
    
    # Remove non-existent list
    count = await store.remove_items_by_list(999)
    assert count == 0

@pytest.mark.asyncio
async def test_replace_items_for_list(mock_data_dir):
    store = JsonQuestionListItemStore(data_dir=mock_data_dir)
    
    new_items = [
        QuestionListItem(
            question_list_id=1,
            question_id=5,
            order_index=1,
            weightage=1.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]
    
    # Replace existing list 1 items (which has 2 items) with 1 new item
    result = await store.replace_items_for_list(1, new_items)
    assert len(result) == 1
    
    # Verify in store
    items = await store.get_by_list_id(1)
    assert len(items) == 1
    assert items[0].question_id == 5
