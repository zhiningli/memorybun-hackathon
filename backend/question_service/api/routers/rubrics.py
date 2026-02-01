from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from schemas.rubric import Rubric
from services.rubric_service import rubric_service

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.get("/", response_model=List[Rubric])
async def get_rubrics(name: Optional[str] = Query(None, description="Filter rubrics by name")):
    """
    Get all available grading rubrics.
    Optionally filter by name (e.g., 'Graph Plotting Rubrics', 'General Rubrics').
    """
    return await rubric_service.gen_rubrics(name)


@router.get("/{rubric_id}", response_model=Rubric)
async def get_rubric_by_id(rubric_id: int):
    """
    Get a single rubric by ID.
    """
    rubric = await rubric_service._rubric_store.get_by_id(rubric_id)
    if rubric is None:
        raise HTTPException(status_code=404, detail=f"Rubric {rubric_id} not found")
    return rubric


# NOTE: Create, Update, Delete operations are in /admin/rubrics (requires admin key)
