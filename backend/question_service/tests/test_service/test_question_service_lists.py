"""
Unit tests for QuestionService list orchestration
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.question_service import QuestionService
from schemas.question_list_mutations import QuestionListCreate, QuestionListUpdate, QuestionItemInput
from schemas.questionList import QuestionListCategoryEnum, SubjectEnum, QuestionListDifficultyEnum

@pytest.fixture
def mock_stores():
    q_store = MagicMock()
    ql_store = MagicMock()
    qli_store = MagicMock()
    
    # Setup async mocks
    q_store.get_by_id = AsyncMock()
    ql_store.create = AsyncMock()
    ql_store.get_by_id = AsyncMock()
    ql_store.update = AsyncMock()
    ql_store.delete = AsyncMock()
    qli_store.add_items = AsyncMock()
    qli_store.remove_items_by_list = AsyncMock()
    qli_store.replace_items_for_list = AsyncMock()
    qli_store.get_by_list_id = AsyncMock()
    
    return q_store, ql_store, qli_store

@pytest.fixture
def service(mock_stores):
    return QuestionService(
        question_store=mock_stores[0],
        question_list_store=mock_stores[1],
        question_list_item_store=mock_stores[2]
    )

@pytest.mark.asyncio
async def test_create_question_list_success(service, mock_stores):
    q_store, ql_store, qli_store = mock_stores
    
    # Mock question existence (questions 1 and 2 exist)
    q_store.get_by_id.side_effect = lambda qid: MagicMock(id=qid) if qid in [1, 2] else None
    
    # Mock list creation
    ql_store.create.return_value = MagicMock(id=10)
    
    # Input data
    create_input = QuestionListCreate(
        title="New List",
        categories=[QuestionListCategoryEnum.GRAPH_PLOTTING],
        subjects=[SubjectEnum.MATHEMATICS],
        difficulty=QuestionListDifficultyEnum.EASY,
        duration_seconds=1800,
        question_items=[
            QuestionItemInput(question_id=1, weightage=0.5),
            QuestionItemInput(question_id=2, weightage=0.5)
        ]
    )
    
    result = await service.create_question_list(create_input)
    
    assert result["list"].id == 10
    
    # Verify ql_store.create called
    assert ql_store.create.called
    
    # Verify qli_store.add_items called with correct items
    assert qli_store.add_items.called
    call_args = qli_store.add_items.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0].question_id == 1
    assert call_args[0].question_list_id == 10
    assert call_args[1].question_id == 2

@pytest.mark.asyncio
async def test_create_question_list_fails_missing_question(service, mock_stores):
    q_store, _, _ = mock_stores
    
    # Only question 1 exists
    q_store.get_by_id.side_effect = lambda qid: MagicMock(id=1) if qid == 1 else None
    
    create_input = QuestionListCreate(
        title="New List",
        categories=[QuestionListCategoryEnum.GRAPH_PLOTTING],
        subjects=[SubjectEnum.MATHEMATICS],
        difficulty=QuestionListDifficultyEnum.EASY,
        duration_seconds=1800,
        question_items=[
            QuestionItemInput(question_id=1, weightage=0.5),
            QuestionItemInput(question_id=999, weightage=0.5) # Missing
        ]
    )
    
    with pytest.raises(ValueError, match="Question 999 not found"):
        await service.create_question_list(create_input)

@pytest.mark.asyncio
async def test_update_question_list_replace_items(service, mock_stores):
    q_store, ql_store, qli_store = mock_stores
    
    # List exists
    ql_store.get_by_id.return_value = MagicMock(id=1, title="Old Title")
    # Questions exist
    q_store.get_by_id.return_value = MagicMock()
    
    update_input = QuestionListUpdate(
        title="New Title",
        question_items=[
            QuestionItemInput(question_id=1, weightage=1.0)
        ]
    )
    
    await service.update_question_list(1, update_input)
    
    # Verify update called
    assert ql_store.update.called
    args = ql_store.update.call_args[0]
    assert args[1]["title"] == "New Title"
    
    # Verify items replaced
    assert qli_store.replace_items_for_list.called

@pytest.mark.asyncio
async def test_delete_question_list_cascade(service, mock_stores):
    _, ql_store, qli_store = mock_stores
    
    # List exists
    ql_store.get_by_id.return_value = MagicMock(id=1)
    ql_store.delete.return_value = True
    
    result = await service.delete_question_list(1)
    
    assert result is True
    # Verify cascade
    ql_store.delete.assert_called_with(1)
    qli_store.remove_items_by_list.assert_called_with(1)
