"""
Pipeline module for grading orchestration.

Contains stages that process grading tasks through a defined workflow:
1. TaskDecodeStage - Validate and decode task JSON
2. ContextFetchStage - Fetch rubric and reference answer
3. PromptBuildStage - Assemble prompts from context
4. LLMGradeStage - Call LLM and parse response
5. ValidateStage - Validate output bounds and data
6. PersistStage - Save result to storage
"""

from pipeline.base import PipelineStageBase
from pipeline.task_decode_stage import TaskDecodeStage, TaskDecodeError
from pipeline.context_fetch_stage import ContextFetchStage
from pipeline.prompt_build_stage import PromptBuildStage
from pipeline.llm_grade_stage import LLMGradeStage
from pipeline.validate_stage import ValidateStage, ValidationError
from pipeline.persist_stage import PersistStage
from pipeline.orchestrator import Orchestrator

__all__ = [
    "PipelineStageBase",
    "TaskDecodeStage",
    "TaskDecodeError",
    "ContextFetchStage",
    "PromptBuildStage",
    "LLMGradeStage",
    "ValidateStage",
    "ValidationError",
    "PersistStage",
    "Orchestrator",
]

