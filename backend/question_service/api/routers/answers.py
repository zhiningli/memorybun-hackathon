"""
Answers Router - Endpoints for getting answers.

NOTE: Create, Update, Delete operations are in /admin/answers (requires admin key)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import List
from schemas import Answer
from schemas.viewer_context import ViewerContext
from services import answer_service
from api.dependencies import get_viewer_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/answers", tags=["Answers"])


@router.get("/", response_model=List[Answer])
async def get_answers_by_question_ids(
    request: Request,
    question_id: List[int] = Query(default=[], description="One or more question IDs to get answers for"),
    viewer_context: ViewerContext = Depends(get_viewer_context)
):
    """
    Get answers by question id(s).
    
    Query Parameters:
        question_id: One or more question IDs (e.g., ?question_id=1&question_id=2)
    
    Returns a list of answers for the provided question IDs.
    """
    # Handle query params directly for single value case
    query_params = request.query_params.getlist("question_id")
    if not query_params:
        raise HTTPException(status_code=400, detail="At least one question_id is required")
    
    try:
        question_ids = [int(qid) for qid in query_params]
    except ValueError:
        raise HTTPException(status_code=400, detail="question_id must be an integer")
    
    if not question_ids:
        raise HTTPException(status_code=400, detail="At least one question_id is required")
    
    results = await answer_service.gen_answers_by_question_ids(question_ids, viewer_context)
    return results


@router.get("/{answer_id}", response_model=Answer)
async def get_answer_by_id(answer_id: int):
    """
    Get a single answer by ID.
    """
    answer = await answer_service._answer_store.get_by_id(answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail=f"Answer {answer_id} not found")
    return answer
