import pytest
from fastapi.testclient import TestClient
from main import app
from services.question_service import QuestionService
from pathlib import Path
import json

client = TestClient(app)

@pytest.fixture
def mock_empty_data_dir(tmp_path):
    """Create a temporary directory with empty or missing data files"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create empty valid JSON structs to avoid JSONDecodeError, but empty lists
    with open(data_dir / "question_lists.json", "w") as f:
        json.dump({"question_lists": []}, f)
    with open(data_dir / "question_list_items.json", "w") as f:
        json.dump({"question_list_items": []}, f)
    with open(data_dir / "questions.json", "w") as f:
        json.dump({"questions": []}, f)
        
    return data_dir

@pytest.mark.asyncio
async def test_health_check_healthy():
    """Test that health check returns 200 when data is loaded (using default data)"""
    # Force re-initialization with default data
    service = QuestionService()
    await service.initialize()
    app.state.question_service = service
    
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["questions_count"] > 0

@pytest.mark.asyncio
async def test_health_check_unhealthy_no_data(mock_empty_data_dir):
    """Test that health check returns 503 when data is empty"""
    # Initialize service with empty data
    service = QuestionService(data_dir=mock_empty_data_dir)
    await service.initialize()
    app.state.question_service = service
    
    response = client.get("/health")
    # Should be 503 because questions list is empty
    assert response.status_code == 503
    assert response.json()["detail"] == "Data not loaded"
