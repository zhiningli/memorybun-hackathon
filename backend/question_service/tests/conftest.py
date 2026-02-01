"""
Shared test fixtures and configuration for Question Service
"""
import sys
from pathlib import Path

# Add the question_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

import pytest
import json
from services.question_service import QuestionService
from services.answer_service import AnswerService
from fastapi.testclient import TestClient
from main import app

# Original client fixture removed - replaced with one depending on question_service_with_test_data


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_question_lists_data():
    """Sample question lists JSON data"""
    return {
        "question_lists": [
            {
                "id": 1,
                "title": "Test List",
                "description": "Test description",
                "categories": ["Graph Plotting"],
                "subjects": ["Engineering"],
                "difficulty": "Easy",
                "duration_seconds": 1800,
                "access_status": "public",
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "id": 2,
                "title": "Test List 2",
                "description": "Test description 2",
                "categories": ["Circuit Analysis"],
                "subjects": ["Engineering"],
                "difficulty": "Medium",
                "duration_seconds": 2700,
                "access_status": "private",
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "id": 3,
                "title": "Public List",
                "description": "Another public list",
                "categories": ["Graph Plotting"],
                "subjects": ["Engineering"],
                "difficulty": "Advanced",
                "duration_seconds": 3600,
                "access_status": "public",
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            }
        ],
        "question_list_items": [
            {
                "question_list_id": 1,
                "question_id": 1,
                "order_index": 1,
                "weightage": 0.33,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "question_list_id": 1,
                "question_id": 2,
                "order_index": 2,
                "weightage": 0.33,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "question_list_id": 1,
                "question_id": 3,
                "order_index": 3,
                "weightage": 0.34,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "question_list_id": 2,
                "question_id": 2,
                "order_index": 1,
                "weightage": 1.0,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "question_list_id": 2,
                "question_id": 3,
                "order_index": 2,
                "weightage": 0.0,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            }
        ]
    }


@pytest.fixture
def sample_questions_data():
    """Sample questions JSON data"""
    return {
        "questions": [
            {
                "id": 1,
                "title": "Plot y = e^x",
                "question_details": "Create a graph that visualises the exponential function y = e^x",
                "think_time_limit_seconds": 20,
                "record_time_limit_seconds": 60,
                "instructions": [
                    "You will now have {thinkTime} to prepare. After that, you will have up to {recordTime} to record your verbal response and plot the function on the highlighted plot grid to the right. You may also use the white board to show any additional calculations or thoughts.",
                    "You can press the 'Record' button below when you're ready."
                ],
                "hints": [
                    {
                        "text": "think of intersection point on axis and think of value of y when x approach minus or positive infinity",
                        "image_url": None
                    }
                ],
                "question_image_url": None,
                "subjects": ["Mathematics"],
                "topics": ["Graph Plotting", "Mathematics"],
                "difficulty": "easy",
                "rubric_id": 1,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "id": 2,
                "title": "Plot y = sin(x)",
                "question_details": "Draw the sine function y = sin(x)",
                "think_time_limit_seconds": 20,
                "record_time_limit_seconds": 60,
                "instructions": [
                    "You will now have {thinkTime} to prepare. After that, you will have up to {recordTime} to record your verbal response and plot the function on the highlighted plot grid to the right. You may also use the white board to show any additional calculations or thoughts.",
                    "You can press the 'Record' button below when you're ready."
                ],
                "hints": [
                    {
                        "text": "This is a periodic function, try to plot one period first, what are corresponding y values at special x values?",
                        "image_url": None
                    }
                ],
                "question_image_url": None,
                "subjects": ["Mathematics"],
                "topics": ["Graph Plotting", "Mathematics"],
                "difficulty": "easy",
                "rubric_id": 1,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "id": 3,
                "title": "Plot y = e^x * sin(x)",
                "question_details": "Plot the function y = e^x * sin(x) over the range x ∈ [-2, 2]",
                "think_time_limit_seconds": 30,
                "record_time_limit_seconds": 90,
                "instructions": [
                    "You will now have {thinkTime} to prepare. After that, you will have up to {recordTime} to record your verbal response and plot the function on the highlighted plot grid to the right. You may also use the white board to show any additional calculations or thoughts.",
                    "You can press the 'Record' button below when you're ready."
                ],
                "hints": [
                    {
                        "text": "Given that sin(x) has magnitude between -1 and 1, this function should have an 'envelope' function",
                        "image_url": None
                    }
                ],
                "question_image_url": None,
                "subjects": ["Mathematics"],
                "topics": ["Graph Plotting", "Mathematics"],
                "difficulty": "medium",
                "rubric_id": 1,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            }
        ]
    }


@pytest.fixture
def sample_answers_data():
    """Sample answers JSON data"""
    return {
        "answers": [
            {
                "id": 1,
                "question_id": 1,
                "text_answer": "To plot y = e^x, note that it always stays above the x-axis since e^x > 0 for all x. The graph passes through (0, 1).",
                "graph_answer_url": None,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "id": 2,
                "question_id": 2,
                "text_answer": "To plot y = sin(x), begin at the origin (0, 0). The function reaches its maximum of 1 at x = π/2.",
                "graph_answer_url": None,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            },
            {
                "id": 3,
                "question_id": 3,
                "text_answer": "To plot y = e^x * sin(x), start by recalling that sin(x) oscillates between -1 and 1.",
                "graph_answer_url": None,
                "created_at": "2025-11-06T00:00:00Z",
                "updated_at": "2025-11-06T00:00:00Z"
            }
        ]
    }


@pytest.fixture
async def question_service_with_test_data(test_data_dir, sample_question_lists_data, sample_questions_data):
    """Create QuestionService with test data"""
    # Write question lists data (without question_list_items)
    question_lists_only = {
        "question_lists": sample_question_lists_data["question_lists"]
    }
    (test_data_dir / "question_lists.json").write_text(
        json.dumps(question_lists_only), encoding="utf-8"
    )
    
    # Write question list items to separate file
    question_list_items_only = {
        "question_list_items": sample_question_lists_data["question_list_items"]
    }
    (test_data_dir / "question_list_items.json").write_text(
        json.dumps(question_list_items_only), encoding="utf-8"
    )
    
    # Write questions data
    (test_data_dir / "questions.json").write_text(
        json.dumps(sample_questions_data), encoding="utf-8"
    )
    
    # Create service with test data directory
    service = QuestionService(data_dir=test_data_dir)
    await service.initialize()
    
    return service


from api.dependencies import get_question_service

@pytest.fixture
def client(question_service_with_test_data):
    """Create test client with dependency overrides"""
    async def override_question_service():
        return question_service_with_test_data
    
    app.dependency_overrides[get_question_service] = override_question_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}


from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def async_client(question_service_with_test_data):
    """Create async test client with dependency overrides"""
    async def override_question_service():
        return question_service_with_test_data
    
    app.dependency_overrides[get_question_service] = override_question_service
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides = {}



@pytest.fixture
def answer_service_with_test_data(test_data_dir, sample_question_lists_data, sample_questions_data, sample_answers_data):
    """Create AnswerService with test data"""
    # Write question lists data (without question_list_items)
    question_lists_only = {
        "question_lists": sample_question_lists_data["question_lists"]
    }
    (test_data_dir / "question_lists.json").write_text(
        json.dumps(question_lists_only), encoding="utf-8"
    )
    
    # Write question list items to separate file
    question_list_items_only = {
        "question_list_items": sample_question_lists_data["question_list_items"]
    }
    (test_data_dir / "question_list_items.json").write_text(
        json.dumps(question_list_items_only), encoding="utf-8"
    )
    
    # Write questions data
    (test_data_dir / "questions.json").write_text(
        json.dumps(sample_questions_data), encoding="utf-8"
    )
    
    # Write answers data
    (test_data_dir / "answers.json").write_text(
        json.dumps(sample_answers_data), encoding="utf-8"
    )
    
    # Create service with test data directory
    service = AnswerService(data_dir=test_data_dir)
    
    return service

