"""
Questions Router - Endpoints for managing questions.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from schemas.question import Question
from schemas.viewer_context import ViewerContext
from services.question_service import QuestionService
from api.dependencies import get_viewer_context, get_question_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["Questions"])

@router.get("/{question_id}", response_model=Question)
async def get_question_by_id(
    question_id: int,
    viewer_context: ViewerContext = Depends(get_viewer_context),
    question_service: QuestionService = Depends(get_question_service)
):
    """
    Get a single question by ID.
    Returns 404 if not found or not accessible.
    """
    question = await question_service.gen_question_by_id(question_id, viewer_context)
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    return question
