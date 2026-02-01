"""
Prompt Build Stage - Assembles prompts from context for LLM grading.

Takes the grading context (rubric, reference answer) and student response
to construct system and user prompts for the LLM.
"""

import logging
from typing import Optional
from pipeline.base import PipelineStageBase
from schemas.grading_state import GradingState, PipelineStage

logger = logging.getLogger(__name__)

# Prompt version for auditing
PROMPT_VERSION = "v1.0"


class PromptBuildStage(PipelineStageBase):
    """
    Assembles system and user prompts for LLM grading.
    
    Uses:
    - state.context (rubric, reference_answer from ContextFetchStage)
    - state.transcription_text (student answer)
    - state.screenshot_url (reference to visual work)
    
    Produces:
    - state.system_prompt
    - state.user_prompt
    """
    
    @property
    def name(self) -> str:
        return "PromptBuildStage"
    
    def _build_system_prompt(self) -> str:
        """
        Load the static system prompt from file.
        
        Returns:
            System prompt string (rubric-agnostic)
        """
        import os
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'data', 
            'prompts', 
            'question_system_prompt.txt'
        )
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found at {prompt_path}, using fallback")
            return "You are an expert educational grader. Evaluate the student's answer and provide feedback in JSON format."
    
    def _build_user_prompt(
        self,
        transcription_text: str,
        screenshot_key: str,
        reference_answer: Optional[str] = None,
        question_id: Optional[str] = None
    ) -> str:
        """
        Build the user prompt with student submission.
        
        Args:
            transcription_text: Student's spoken/written answer
            screenshot_key: Key/Filename of visual work screenshot
            reference_answer: Optional model answer
            question_id: Optional question ID for context
            
        Returns:
            User prompt string
        """
        prompt_parts = []
        
        if question_id:
            prompt_parts.append(f"Question ID: {question_id}")
        
        prompt_parts.append(f"""
STUDENT'S ANSWER (transcribed from audio):
\"\"\"
{transcription_text}
\"\"\"

STUDENT'S VISUAL WORK:
Screenshot available at: {screenshot_key}
(Note: Please consider any diagrams, equations, or written work shown in the screenshot)
""")
        
        if reference_answer:
            prompt_parts.append(f"""
REFERENCE ANSWER:
\"\"\"
{reference_answer}
\"\"\"
""")
        
        prompt_parts.append("""
Please grade this submission according to the rubric and provide your assessment in the JSON format specified.""")
        
        return "\n".join(prompt_parts)
    
    async def run(self, state: GradingState) -> GradingState:
        """
        Build prompts from context and student submission.
        
        Args:
            state: Current grading state with context populated
            
        Returns:
            Updated state with system_prompt and user_prompt
        """
        logger.debug(f"Building prompts for session {state.session_id}")
        
        # Import here to avoid circular imports
        from schemas.context import QuestionContext
        
        # Extract context (populated by previous ContextFetchStage)
        context = state.context
        
        # Get context prompt (includes question, reference answer, and rubric)
        if isinstance(context, QuestionContext):
            # Use to_prompt() for the full context section (question + answer + rubric)
            context_prompt = context.to_prompt()
        else:
            # Fallback for dict context (backward compatibility)
            context_prompt = None
        
        # Build system prompt (generic grading instructions)
        state.system_prompt = self._build_system_prompt()
        
        # Build user prompt with student submission
        user_prompt_parts = [
            self._build_user_prompt(
                transcription_text=state.transcription_text,
                screenshot_key=state.screenshot_key,
                reference_answer=None,  # Now included via context_prompt
                question_id=state.question_id
            )
        ]
        
        # Prepend context section if available (from QuestionContext.to_prompt())
        if context_prompt:
            user_prompt_parts.insert(0, context_prompt + "\n")
        
        state.user_prompt = "\n".join(user_prompt_parts)
        
        # Advance stage
        state.advance_to(PipelineStage.PROMPT_BUILD)
        
        logger.info(f"Prompts built for session {state.session_id} (prompt_version={PROMPT_VERSION})")
        return state
