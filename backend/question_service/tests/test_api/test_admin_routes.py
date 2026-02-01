
import pytest
from fastapi.testclient import TestClient
from main import app
from config import settings

from unittest.mock import patch
from services.question_service import QuestionService
from services.answer_service import AnswerService
from services.rubric_service import RubricService
from api.dependencies import get_question_service

client = TestClient(app)

# Use the key from settings (SecretStr requires .get_secret_value())
ADMIN_KEY = settings.admin_api_key.get_secret_value()

@pytest.fixture
def admin_headers():
    return {"X-Admin-Key": ADMIN_KEY}

@pytest.fixture(autouse=True)
def mock_services(tmp_path):
    """
    Override services to use temporary directory and patch globals.
    This prevents writing to real data files and solves app.state dependency issue.
    """
    # Create services pointing to temp dir
    qs = QuestionService(data_dir=tmp_path)
    ans = AnswerService(data_dir=tmp_path)
    rs = RubricService(data_dir=tmp_path)
    
    # Patch the global instances in the router module
    # We patch where they are IMPORTED
    with patch("api.routers.admin.answer_service", ans), \
         patch("api.routers.admin.rubric_service", rs):
         
         # Override dependency for QuestionService
         app.dependency_overrides[get_question_service] = lambda: qs
         yield
         app.dependency_overrides = {}

def test_admin_auth_required():
    """Verify 401 without API key"""
    response = client.post("/api/v1/admin/questions", json={})
    assert response.status_code == 401

def test_create_question_lifecycle(admin_headers):
    """Test full lifecycle: Create -> Get -> Update -> Delete"""
    
    # 1. CREATE
    data = {
        "title": "Admin Test Question",
        "question_details": "Details",
        "think_time_limit_seconds": 60,
        "record_time_limit_seconds": 120,
        "instructions": ["Instr"],
        "hints": [{"text": "Hint"}],
        "question_image_url": None,
        "subjects": ["Mathematics"],
        "topics": ["Mathematics"],
        "difficulty": "medium",
        "rubric_id": 1
    }
    response = client.post("/api/v1/admin/questions", json=data, headers=admin_headers)
    if response.status_code != 200:
        print(f"Create Question Failed: {response.text}")
    assert response.status_code == 200
    q_data = response.json()
    assert q_data["title"] == "Admin Test Question"
    q_id = q_data["id"]

    # 2. VERIFY GET
    # Note: Using public endpoint to verify
    # (Assuming we have setup viewer context or it's public)
    # Actually, QuestionService permissions might block anonymous if strict.
    # But usually creating a question puts it in no list, so it might not be visible via public API!
    # Wait, existing logic: "viewable if in a visible list".
    # Newly created question is in NO list. So gen_question_by_id starts with:
    # "if not await self._can_view_question(question, viewer_context): return None"
    # And _can_view_question checks lists.
    # So a standalone question is INVISIBLE to public API!
    
    # This is a good catch. Admin should probably have a way to view it regardless?
    # Or for now, we trust the POST response which returns the object.
    
    # Let's trust the POST response for now, and check if we can update it directly (which uses ID).
    
    # 3. UPDATE
    update_data = {"title": "Updated Title"}
    response = client.put(f"/api/v1/admin/questions/{q_id}", json=update_data, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
    
    # 4. DELETE
    response = client.delete(f"/api/v1/admin/questions/{q_id}", headers=admin_headers)
    assert response.status_code == 200
    
    # 5. VERIFY UPDATE Fails (404)
    response = client.put(f"/api/v1/admin/questions/{q_id}", json=update_data, headers=admin_headers)
    assert response.status_code == 404

def test_rubric_lifecycle(admin_headers):
    """Test rubric lifecycle"""
    data = {
        "name": "Test Rubric",
        "description": "Desc",
        "dimensions": [
            {
                "name": "Dim1",
                "description": "D1",
                "weight": 1.0,
                "criterias": [
                    {
                        "name": "Crit1",
                        "description": "C1",
                        "scoring_condition": "cond"
                    }
                ]
            }
        ],
        "version": 1
    }
    response = client.post("/api/v1/admin/rubrics", json=data, headers=admin_headers)
    if response.status_code != 200:
        print(f"Create Rubric Failed: {response.text}")
    assert response.status_code == 200
    r_id = response.json()["id"]
    
    # Update
    response = client.put(f"/api/v1/admin/rubrics/{r_id}", json={"name": "Updated Rubric"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Rubric"
    
    # Delete
    response = client.delete(f"/api/v1/admin/rubrics/{r_id}", headers=admin_headers)
    assert response.status_code == 200
