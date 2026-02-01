"""
API Routers Package - All FastAPI routers for Question Service.
"""

from api.routers.question_lists import router as question_lists_router
from api.routers.answers import router as answers_router
from api.routers.rubrics import router as rubrics_router
from api.routers.questions import router as questions_router

__all__ = [
    "question_lists_router",
    "answers_router",
    "rubrics_router",
    "questions_router"
]
