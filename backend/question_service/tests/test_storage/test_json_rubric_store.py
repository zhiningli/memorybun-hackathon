"""
Unit tests for JsonRubricStore
"""
import pytest
import json
from pathlib import Path
from storage.rubric_store import JsonRubricStore
from schemas.rubric_mutations import RubricCreate, RubricUpdate
from schemas.rubric import RubricDimension, RubricCriteria

@pytest.fixture
def mock_data_dir(tmp_path):
    """Create a temporary directory with sample rubric data"""
    data = {
        "rubrics": [
            {
                "id": 1,
                "name": "General Rubric",
                "description": "Standard rubric",
                "dimensions": [
                    {
                        "name": "Correctness",
                        "description": "Is it correct?",
                        "weight": 1.0,
                        "criterias": [
                            {
                                "name": "Yes",
                                "description": "Totally correct",
                                "scoring_condition": "100%"
                            }
                        ]
                    }
                ],
                "version": 1,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        ]
    }
    
    rubrics_file = tmp_path / "rubrics.json"
    with open(rubrics_file, "w") as f:
        json.dump(data, f)
        
    return tmp_path


@pytest.fixture
def sample_dimension():
    """Create a sample dimension for testing"""
    return RubricDimension(
        name="Test Dimension",
        description="A test dimension",
        weight=1.0,
        criterias=[
            RubricCriteria(
                name="Test Criteria",
                description="A test criteria",
                scoring_condition="Must pass test"
            )
        ]
    )


@pytest.mark.asyncio
async def test_load_rubrics_success(mock_data_dir):
    """Test loading rubrics from valid JSON file"""
    store = JsonRubricStore(data_dir=mock_data_dir)
    
    rubrics = await store.get_all()
    assert len(rubrics) == 1
    assert rubrics[0].id == 1
    assert rubrics[0].name == "General Rubric"

@pytest.mark.asyncio
async def test_get_by_name(mock_data_dir):
    """Test filtering rubrics by name"""
    store = JsonRubricStore(data_dir=mock_data_dir)
    
    # Exact match
    results = await store.get_by_name("General Rubric")
    assert len(results) == 1
    assert results[0].id == 1
    
    # No match
    results_none = await store.get_by_name("Nonexistent")
    assert len(results_none) == 0

@pytest.mark.asyncio
async def test_missing_file(tmp_path):
    """Test handling of missing rubrics.json"""
    store = JsonRubricStore(data_dir=tmp_path)
    
    rubrics = await store.get_all()
    assert len(rubrics) == 0


@pytest.mark.asyncio
async def test_update_auto_increments_version(mock_data_dir):
    """Test that update automatically increments the version field"""
    store = JsonRubricStore(data_dir=mock_data_dir)
    
    # Get original rubric
    original = await store.get_by_id(1)
    assert original is not None
    assert original.version == 1
    
    # Update the rubric
    await store.update(1, RubricUpdate(name="Updated Rubric"))
    
    # Verify version was incremented
    updated = await store.get_by_id(1)
    assert updated is not None
    assert updated.version == 2
    assert updated.name == "Updated Rubric"
    
    # Second update should increment again
    await store.update(1, RubricUpdate(description="New description"))
    
    updated_again = await store.get_by_id(1)
    assert updated_again is not None
    assert updated_again.version == 3
    assert updated_again.description == "New description"
    assert updated_again.name == "Updated Rubric"  # Previous update preserved


@pytest.mark.asyncio
async def test_create_assigns_incremental_id(mock_data_dir, sample_dimension):
    """Test that create assigns sequential IDs"""
    store = JsonRubricStore(data_dir=mock_data_dir)
    
    # Existing rubric has id=1
    existing = await store.get_all()
    assert len(existing) == 1
    assert existing[0].id == 1
    
    # Create new rubric
    new_rubric = await store.create(RubricCreate(
        name="New Rubric",
        description="A new rubric",
        dimensions=[sample_dimension]
    ))
    
    # Should have id=2 and version=1
    assert new_rubric.id == 2
    assert new_rubric.version == 1
    assert new_rubric.name == "New Rubric"
    
    # Create another one
    another_rubric = await store.create(RubricCreate(
        name="Another Rubric",
        dimensions=[sample_dimension]
    ))
    
    assert another_rubric.id == 3
    assert another_rubric.version == 1


@pytest.mark.asyncio
async def test_delete_removes_rubric(mock_data_dir):
    """Test that delete removes the rubric entirely"""
    store = JsonRubricStore(data_dir=mock_data_dir)
    
    # Verify rubric exists
    rubric = await store.get_by_id(1)
    assert rubric is not None
    
    # Delete it
    result = await store.delete(1)
    assert result is True
    
    # Verify it's gone
    deleted = await store.get_by_id(1)
    assert deleted is None
    
    # Delete non-existent should return False
    result_again = await store.delete(1)
    assert result_again is False


@pytest.mark.asyncio
async def test_update_nonexistent_returns_none(mock_data_dir):
    """Test that updating a non-existent rubric returns None"""
    store = JsonRubricStore(data_dir=mock_data_dir)
    
    result = await store.update(999, RubricUpdate(name="Won't work"))
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id(mock_data_dir):
    """Test fetching a specific rubric by ID"""
    store = JsonRubricStore(data_dir=mock_data_dir)
    
    rubric = await store.get_by_id(1)
    assert rubric is not None
    assert rubric.id == 1
    assert rubric.name == "General Rubric"
    
    # Non-existent ID
    missing = await store.get_by_id(999)
    assert missing is None
