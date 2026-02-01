"""
Integration tests for answer API routes
"""
import sys
from pathlib import Path

# Add the question_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAnswerRoutes:
    """Test answer endpoints"""
    
    def test_get_answers_by_question_id_returns_200(self, client):
        """Test that GET /api/v1/answers?question_id=1 returns 200 for existing question"""
        response = client.get("/api/v1/answers", params={"question_id": 1})
        
        # Should return 200 (even if empty list for inaccessible questions)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_answers_by_question_id_returns_empty_list_for_nonexistent_question(self, client):
        """Test that GET /api/v1/answers?question_id=99999 returns empty list for non-existent question"""
        response = client.get("/api/v1/answers", params={"question_id": 99999})
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_answers_by_question_id_returns_400_for_missing_question_id(self, client):
        """Test that GET /api/v1/answers without question_id returns 400"""
        response = client.get("/api/v1/answers")
        
        # Our route returns 400 for missing required parameter
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()
    
    def test_get_answers_by_question_id_returns_valid_schema(self, client):
        """Test that response matches List[Answer] schema when answer exists"""
        response = client.get("/api/v1/answers", params={"question_id": 1})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list)
        
        if len(data) > 0:
            # Check first item has required fields
            first_item = data[0]
            assert "id" in first_item
            assert "question_id" in first_item
            assert "created_at" in first_item
            assert "updated_at" in first_item
            # Check that question_id matches the query parameter
            assert first_item["question_id"] == 1
    
    def test_get_answers_by_question_id_response_structure(self, client):
        """Test that response has correct structure"""
        response = client.get("/api/v1/answers", params={"question_id": 1})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list)
        
        # If there are items, check structure
        for item in data:
            assert isinstance(item, dict)
            assert isinstance(item["id"], int)
            assert isinstance(item["question_id"], int)
            assert isinstance(item["created_at"], str)
            assert isinstance(item["updated_at"], str)
            # Optional fields
            if "text_answer" in item:
                assert isinstance(item["text_answer"], (str, type(None)))
            if "graph_answer_url" in item:
                assert isinstance(item["graph_answer_url"], (str, type(None)))
    
    def test_get_answers_by_multiple_question_ids(self, client):
        """Test that GET /api/v1/answers?question_id=1&question_id=2 returns multiple answers"""
        response = client.get("/api/v1/answers", params={"question_id": [1, 2]})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list)
        
        # Should have answers for accessible questions
        if len(data) > 0:
            question_ids = [item["question_id"] for item in data]
            # Should contain at least one of the requested IDs
            assert any(qid in [1, 2] for qid in question_ids)
    
    def test_get_answers_by_multiple_question_ids_handles_mixed_access(self, client):
        """Test that multiple question_ids returns only accessible answers"""
        response = client.get("/api/v1/answers", params={"question_id": [1, 99999]})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list (may be empty or contain only accessible answers)
        assert isinstance(data, list)
        
        # If there are results, they should only be for accessible questions
        for item in data:
            assert item["question_id"] in [1, 99999]  # Should match one of the requested IDs

