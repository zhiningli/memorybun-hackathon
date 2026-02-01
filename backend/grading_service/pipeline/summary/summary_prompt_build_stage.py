"""
Summary Prompt Build Stage - Assembles prompts for summary LLM call.

Takes the session grading results and constructs system and user prompts
for the LLM to generate a summary report.
"""

import logging
import json
import os
from typing import List, Dict, Any

from pipeline.base import PipelineStageBase
from schemas.summary_state import SummaryState, SummaryPipelineStage
from schemas.summary_result import SUMMARY_DIMENSIONS

logger = logging.getLogger(__name__)

# Prompt version for auditing
SUMMARY_PROMPT_VERSION = "v1.0"


class SummaryPromptBuildStage(PipelineStageBase):
    """
    Assembles system and user prompts for summary LLM call.
    
    Uses:
    - state.session_results (list of grading results from ContextFetchStage)
    - state.session_ids
    
    Produces:
    - state.system_prompt
    - state.user_prompt
    """
    
    @property
    def name(self) -> str:
        return "SummaryPromptBuildStage"
    
    def _load_system_prompt(self) -> str:
        """
        Load the summary system prompt from file.
        
        Returns:
            System prompt string
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'data', 
            'prompts', 
            'summary_system_prompt.txt'
        )
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Summary system prompt not found at {prompt_path}, using fallback")
            return (
                "You are an expert educational assessment specialist. "
                "Synthesize multiple grading session results into a comprehensive summary. "
                "Respond with JSON only."
            )
    
    def _format_session_results(self, session_results: List[Dict[str, Any]]) -> str:
        """
        Format session results for the user prompt.
        
        Args:
            session_results: List of grading result dicts
            
        Returns:
            Formatted string representation of results
        """
        formatted_parts = []
        
        for i, result in enumerate(session_results, 1):
            session_id = result.get("session_id", f"Session {i}")
            feedback = result.get("feedback", "No feedback")
            score_breakdown = result.get("score_breakdown", [])
            
            part = f"""
=== Session {i}: {session_id} ===
Feedback: {feedback}

Score Breakdown:
"""
            for item in score_breakdown:
                dimension = item.get("dimension", "Unknown")
                score = item.get("score", "N/A")
                max_score = item.get("max_score", "N/A")
                dim_feedback = item.get("feedback", "")
                part += f"  - {dimension}: {score}/{max_score} - {dim_feedback}\n"
            
            formatted_parts.append(part)
        
        return "\n".join(formatted_parts)
    
    def _build_user_prompt(
        self,
        session_ids: List[str],
        session_results: List[Dict[str, Any]]
    ) -> str:
        """
        Build the user prompt with all session results.
        
        Args:
            session_ids: List of session IDs
            session_results: List of grading results
            
        Returns:
            User prompt string
        """
        formatted_results = self._format_session_results(session_results)
        
        prompt = f"""
Please analyze the following grading results and generate a comprehensive summary report.

Number of Sessions: {len(session_ids)}
Sessions: {', '.join(session_ids)}

Required Dimensions for Summary (use these exact names):
{json.dumps(SUMMARY_DIMENSIONS, indent=2)}

=== SESSION GRADING RESULTS ===
{formatted_results}

=== INSTRUCTIONS ===
1. Analyze all session results together to form a complete picture
2. Calculate dimension scores by aggregating across all sessions
3. Generate a comprehensive summary with:
   - Overall score (0-100)
   - Dimension scores for the 5 required dimensions
   - Analytics summary bullets (data-driven observations)
   - Overall feedback (2-3 paragraphs)
   - Key strengths (concrete observations)
   - Areas for improvement (specific, actionable)

Respond with the JSON format specified in the system prompt.
"""
        return prompt
    
    async def run(self, state: SummaryState) -> SummaryState:
        """
        Build prompts from session results.
        
        Args:
            state: Current summary state with session_results populated
            
        Returns:
            Updated state with system_prompt and user_prompt
        """
        logger.debug(f"Building prompts for summary {state.summary_id}")
        
        if not state.session_results:
            raise ValueError("session_results must be populated before prompt build stage")
        
        # Build system prompt
        state.system_prompt = self._load_system_prompt()
        
        # Build user prompt
        state.user_prompt = self._build_user_prompt(
            session_ids=state.session_ids,
            session_results=state.session_results
        )
        
        # Advance stage
        state.advance_to(SummaryPipelineStage.PROMPT_BUILD)
        
        logger.info(
            f"Summary prompts built for {state.summary_id} "
            f"(prompt_version={SUMMARY_PROMPT_VERSION}, sessions={len(state.session_ids)})"
        )
        return state


def create_summary_prompt_build_stage() -> SummaryPromptBuildStage:
    """Factory function for SummaryPromptBuildStage."""
    return SummaryPromptBuildStage()
