"""
Question Lists Router - Endpoints for question lists and their questions.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from schemas import QuestionListMetadata, Question
from schemas.viewer_context import ViewerContext
from services.question_service import QuestionService
from api.dependencies import get_viewer_context, get_question_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/question-lists", tags=["Question Lists"])


@router.get("/", response_model=List[QuestionListMetadata])
async def get_all_question_lists(
    viewer_context: ViewerContext = Depends(get_viewer_context),
    question_service: QuestionService = Depends(get_question_service)
):
    """
    Get all question list metadata visible to the current viewer.
    """
    try:
        return await question_service.gen_all_question_lists(viewer_context)
    except Exception as e:
        logger.error(f"Error in get_all_question_lists: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{question_list_id}/questions", response_model=List[Question])
async def get_questions_in_question_list(
    question_list_id: int,
    viewer_context: ViewerContext = Depends(get_viewer_context),
    question_service: QuestionService = Depends(get_question_service)
):
    """
    Get all questions in a question list visible to the current viewer.
    Returns 404 if the question list doesn't exist or viewer doesn't have access.
    """
    result = await question_service.gen_all_questions_in_question_list(question_list_id, viewer_context)
    if result is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Question list {question_list_id} not found or you don't have access to it"
        )
    return result
