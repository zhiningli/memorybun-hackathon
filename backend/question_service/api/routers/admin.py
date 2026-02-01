from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from middleware.auth import verify_admin_key
from services.question_service import QuestionService
from api.dependencies import get_question_service

from services.answer_service import answer_service
from services.rubric_service import rubric_service

from schemas.question import Question
from schemas.question_mutations import QuestionCreate, QuestionUpdate
from schemas.answer import Answer
from schemas.answer_mutations import AnswerCreate, AnswerUpdate
from schemas.rubric import Rubric
from schemas.rubric_mutations import RubricCreate, RubricUpdate

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)]
)

# ==================== QUESTIONS ====================

@router.post("/questions", response_model=Question)
async def create_question(
    question: QuestionCreate,
    service: QuestionService = Depends(get_question_service)
):
    """
    Create a new question.
    Validates that rubric_id exists.
    """
    try:
        return await service.create_question(question)
    except ValueError as e:
        # FK validation failed
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/questions/{question_id}", response_model=Question)
async def update_question(
    question_id: int,
    question: QuestionUpdate,
    service: QuestionService = Depends(get_question_service)
):
    """Update an existing question."""
    updated = await service.update_question(question_id, question)
    if not updated:
        raise HTTPException(status_code=404, detail="Question not found")
    return updated

@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: int,
    service: QuestionService = Depends(get_question_service)
):
    """Delete a question."""
    success = await service.delete_question(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"status": "success", "id": question_id}

# ==================== ANSWERS ====================

@router.post("/answers", response_model=Answer)
async def create_answer(answer: AnswerCreate):
    """
    Create a new answer.
    Validates that question_id exists.
    """
    try:
        return await answer_service.create_answer(answer)
    except ValueError as e:
        # FK validation failed
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/answers/{answer_id}", response_model=Answer)
async def update_answer(answer_id: int, answer: AnswerUpdate):
    """Update an existing answer."""
    updated = await answer_service.update_answer(answer_id, answer)
    if not updated:
        raise HTTPException(status_code=404, detail="Answer not found")
    return updated

@router.delete("/answers/{answer_id}")
async def delete_answer(answer_id: int):
    """Delete an answer."""
    success = await answer_service.delete_answer(answer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Answer not found")
    return {"status": "success", "id": answer_id}

# ==================== RUBRICS ====================

@router.post("/rubrics", response_model=Rubric)
async def create_rubric(rubric: RubricCreate):
    """Create a new rubric."""
    return await rubric_service.create_rubric(rubric)

@router.put("/rubrics/{rubric_id}", response_model=Rubric)
async def update_rubric(rubric_id: int, rubric: RubricUpdate):
    """Update an existing rubric."""
    updated = await rubric_service.update_rubric(rubric_id, rubric)
    if not updated:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return updated

@router.delete("/rubrics/{rubric_id}")
async def delete_rubric(rubric_id: int):
    """Delete a rubric."""
    success = await rubric_service.delete_rubric(rubric_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return {"status": "success", "id": rubric_id}

# ==================== QUESTION LISTS ====================

from schemas.question_list_mutations import QuestionListCreate, QuestionListUpdate

@router.post("/question-lists")
async def create_question_list(
    list_create: QuestionListCreate,
    service: QuestionService = Depends(get_question_service)
):
    """
    Create a new question list with questions (aggregate pattern).
    
    Validates all question_ids exist and weightage sums to 1.0.
    """
    try:
        return await service.create_question_list(list_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/question-lists/{list_id}")
async def update_question_list(
    list_id: int,
    list_update: QuestionListUpdate,
    service: QuestionService = Depends(get_question_service)
):
    """
    Update a question list.
    
    If question_items is provided, replaces all existing items.
    """
    try:
        result = await service.update_question_list(list_id, list_update)
        if result is None:
            raise HTTPException(status_code=404, detail="Question list not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/question-lists/{list_id}")
async def delete_question_list(
    list_id: int,
    service: QuestionService = Depends(get_question_service)
):
    """
    Delete a question list and all its items (cascade delete).
    """
    success = await service.delete_question_list(list_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question list not found")
    return {"status": "success", "id": list_id}

