"""
Task Decode Stage - Validates and decodes task JSON from queue.

First stage in the pipeline. Validates that the dequeued task
has all required fields and creates the initial GradingState.
"""

import json
import logging
from typing import Dict, Any, Optional
from pydantic import ValidationError as PydanticValidationError
from pipeline.base import PipelineStageBase
from schemas.grading_state import GradingState, PipelineStage

logger = logging.getLogger(__name__)


class TaskDecodeError(Exception):
    """Raised when task decoding fails."""
    pass


class TaskDecodeStage(PipelineStageBase):
    """
    Validates and decodes task data from queue.
    
    This stage:
    - Validates required fields are present
    - Creates GradingState from task dict
    - Sets initial stage to TASK_DECODE
    
    Note: This stage is typically called by the orchestrator
    with raw task data, not an existing GradingState.
    """
    
    @property
    def name(self) -> str:
        return "TaskDecodeStage"
    
    def validate_task_dict(self, task_dict: Dict[str, Any]) -> None:
        """
        Validate that task dict has all required fields.
        
        Args:
            task_dict: Raw task data from queue
            
        Raises:
            TaskDecodeError: If validation fails
        """
        required_fields = ["session_id", "transcription_text", "screenshot_key"]
        
        for field in required_fields:
            if field not in task_dict or not task_dict[field]:
                raise TaskDecodeError(f"Missing required field: {field}")
        
        # Validate field types
        if not isinstance(task_dict["session_id"], str):
            raise TaskDecodeError("session_id must be a string")
        if not isinstance(task_dict["transcription_text"], str):
            raise TaskDecodeError("transcription_text must be a string")
        if not isinstance(task_dict["screenshot_key"], str):
            raise TaskDecodeError("screenshot_key must be a string")
    
    def decode_task(self, task_data: str | Dict[str, Any]) -> Dict[str, Any]:
        """
        Decode task data (JSON string or dict).
        
        Args:
            task_data: JSON string or dict
            
        Returns:
            Decoded dict
            
        Raises:
            TaskDecodeError: If decoding fails
        """
        if isinstance(task_data, str):
            try:
                return json.loads(task_data)
            except json.JSONDecodeError as e:
                raise TaskDecodeError(f"Invalid JSON: {e}")
        elif isinstance(task_data, dict):
            return task_data
        else:
            raise TaskDecodeError(f"Unexpected task data type: {type(task_data)}")
    
    def create_state_from_task(self, task_dict: Dict[str, Any]) -> GradingState:
        """
        Create GradingState from validated task dict.
        
        Args:
            task_dict: Validated task data
            
        Returns:
            New GradingState instance
            
        Raises:
            TaskDecodeError: If state creation fails
        """
        try:
            return GradingState.from_task(task_dict)
        except PydanticValidationError as e:
            raise TaskDecodeError(f"Invalid task data: {e}")
    
    async def run(self, state: GradingState) -> GradingState:
        """
        For pipeline consistency, this just validates an existing state.
        
        Note: When used standalone via decode_and_create(), it creates
        a new state. This run() method is for pipeline consistency.
        
        Args:
            state: Existing GradingState
            
        Returns:
            State with stage set to TASK_DECODE
        """
        logger.debug(f"Validating state for session {state.session_id}")
        
        # Validate required fields are present
        if not state.session_id:
            raise TaskDecodeError("session_id is required")
        if not state.transcription_text:
            raise TaskDecodeError("transcription_text is required")
        if not state.screenshot_key:
            raise TaskDecodeError("screenshot_key is required")
        
        # Ensure stage is set
        state.advance_to(PipelineStage.TASK_DECODE)
        
        logger.info(f"Task decoded for session {state.session_id}")
        return state
    
    async def decode_and_create(self, task_data: str | Dict[str, Any]) -> GradingState:
        """
        Decode task data and create GradingState.
        
        This is the main entry point for the orchestrator.
        
        Args:
            task_data: JSON string or dict from queue
            
        Returns:
            New GradingState instance
            
        Raises:
            TaskDecodeError: If decoding or validation fails
        """
        logger.debug("Decoding task data from queue")
        
        # Decode JSON if needed
        task_dict = self.decode_task(task_data)
        
        # Validate required fields
        self.validate_task_dict(task_dict)
        
        # Create state
        state = self.create_state_from_task(task_dict)
        
        # Set stage
        state.advance_to(PipelineStage.TASK_DECODE)
        
        logger.info(f"Task decoded: session_id={state.session_id}")
        return state


def create_task_decode_stage() -> TaskDecodeStage:
    """
    Factory function for TaskDecodeStage.
    
    Returns:
        New TaskDecodeStage instance
    """
    return TaskDecodeStage()
