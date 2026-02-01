from fastapi.testclient import TestClient
import pytest

class TestRubricRoutes:
    def test_get_rubrics_returns_200(self, client):
        """Test that GET /api/v1/rubrics returns 200"""
        response = client.get("/api/v1/rubrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # We know we have at least 'General Rubrics' from rubrics.json
        assert len(data) >= 1 

    def test_get_rubrics_schema_validation(self, client):
        """Test that returned data matches Rubric schema"""
        response = client.get("/api/v1/rubrics")
        data = response.json()
        first_rubric = data[0]
        assert "id" in first_rubric
        assert isinstance(first_rubric["id"], int)
        assert "name" in first_rubric
        assert "dimensions" in first_rubric
        assert isinstance(first_rubric["dimensions"], list)
        # Verify new fields exist
        assert "description" in first_rubric
        assert "version" in first_rubric
        assert "created_at" in first_rubric
        assert "updated_at" in first_rubric

    def test_get_rubrics_filter_by_name(self, client):
        """Test that filtering by name works"""
        # Filter for 'General Rubrics' which should exist
        response = client.get("/api/v1/rubrics", params={"name": "General Rubrics"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(r["name"] == "General Rubrics" for r in data)

    def test_get_rubrics_filter_by_nonexistent_name(self, client):
        """Test that filtering by non-existent name returns empty list"""
        response = client.get("/api/v1/rubrics", params={"name": "NonExistentName123"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
