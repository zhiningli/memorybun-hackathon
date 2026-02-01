from fastapi import Request
from services.question_service import QuestionService
from schemas.viewer_context import ViewerContext


# Dependency to extract viewer context from request
async def get_viewer_context() -> ViewerContext:
    # In the future, this will be extracted from the request headers
    # For now, we will just return an anonymous context
    return ViewerContext(
        user_id=None,
        is_authenticated=False,
        role=None,
        permissions=[]
    )


def get_question_service(request: Request) -> QuestionService:
    """Dependency to get the initialized QuestionService from app state."""
    return request.app.state.question_service
