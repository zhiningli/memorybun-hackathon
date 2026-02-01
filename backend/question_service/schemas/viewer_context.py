"""
Pydantic schemas for Viewer Context.

Viewer Context is the context that describes the current state of the viewer.
This affects
    1. What questions are available to the viewer
    2. What questions are the viewer has already answered
    3. What questions are the viewer is currently answering 
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class ViewerContext(BaseModel):
    """Context about the current viewer/user"""
    user_id: Optional[int] = Field(None, description="User ID if authenticated")
    is_authenticated: bool = Field(default=False, description="Whether user is authenticated")
    role: Optional[str] = Field(None, description="User role (e.g., 'student', 'teacher', 'admin')")
    permissions: Optional[List[str]] = Field(default_factory=list, description="List of user permissions")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "is_authenticated": True,
                "role": "student",
                "permissions": ["view_premium"]
            }
        }
    )

