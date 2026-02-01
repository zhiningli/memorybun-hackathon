import pytest
import asyncio
from services.rubric_service import RubricService, rubric_service
from pathlib import Path
import json

@pytest.fixture
def mock_data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    
    rubrics_data = {
        "rubrics": [
            {
                "id": 101,
                "name": "Test Rubric",
                "description": "A test rubric for unit testing",
                "version": 1,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z",
                "dimensions": [
                    {
                        "name": "Dim 1",
                        "description": "Desc",
                        "weight": 0.5,
                        "criterias": [
                            {
                                "name": "Crit 1",
                                "description": "Desc 1",
                                "scoring_condition": "Cond 1"
                            }
                        ]
                    }
                ]
            },
            {
                "id": 102,
                "name": "Other Rubric",
                "description": "Another test rubric",
                "version": 1,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z",
                "dimensions": [
                    {
                        "name": "Dim 1",
                        "description": "Desc",
                        "weight": 1.0,
                        "criterias": [
                            {
                                "name": "Crit 1",
                                "description": "Desc 1",
                                "scoring_condition": "Cond 1"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    with open(d / "rubrics.json", "w") as f:
        json.dump(rubrics_data, f)
        
    return d

@pytest.mark.asyncio
async def test_rubric_service_load(mock_data_dir):
    service = RubricService(data_dir=mock_data_dir)
    assert len(service.rubrics) == 2
    assert service.rubrics[0].id == 101

@pytest.mark.asyncio
async def test_get_rubrics_all(mock_data_dir):
    service = RubricService(data_dir=mock_data_dir)
    rubrics = await service.gen_rubrics()
    assert len(rubrics) == 2

@pytest.mark.asyncio
async def test_get_rubrics_filter(mock_data_dir):
    service = RubricService(data_dir=mock_data_dir)
    rubrics = await service.gen_rubrics(name="Test Rubric")
    assert len(rubrics) == 1
    assert rubrics[0].id == 101

@pytest.mark.asyncio
async def test_get_rubrics_filter_empty(mock_data_dir):
    service = RubricService(data_dir=mock_data_dir)
    rubrics = await service.gen_rubrics(name="Non Existent")
    assert len(rubrics) == 0

@pytest.mark.asyncio
async def test_integration_live_data():
    """Test that the live service loads data correctly from the real file"""
    rubrics = await rubric_service.gen_rubrics()
    assert len(rubrics) > 0
    assert any(r.name == "General Rubrics" for r in rubrics)
