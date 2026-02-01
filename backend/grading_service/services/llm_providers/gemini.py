"""
Gemini Provider - Google Gemini implementation for LLM grading.

Uses google-genai SDK with multimodal support (text + images).
"""

from google import genai
from google.genai import types
import logging
import re
from typing import Optional
from config import settings
from schemas.grading_result import LLMGradingResponse
from schemas.summary_result import SummaryLLMResponse
from services.llm_providers.base import LLMProvider


logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation of LLMProvider.
    Supports multimodal inputs (text + screenshot).
    """
    
    def __init__(self, model_override: Optional[str] = None):
        """
        Initialize Gemini provider.
        
        Args:
            model_override: Optional model name to use instead of settings.llm_model.
                            Useful for summary generation with different model.
        """
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        
        # Use .get_secret_value() to extract the actual API key from SecretStr
        self.client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self.model_name = model_override or settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
        logger.info(f"Initialized Gemini provider: {self.model_name}")

    async def generate_grade(
        self, 
        system_prompt: str, 
        user_prompt: str,
        screenshot_data: Optional[bytes] = None
    ) -> str:
        """
        Generate grading response using Gemini.
        
        Supports multimodal input with screenshot if provided.
        Uses LLMGradingResponse schema for structured output.
        """
        try:
            # Build content parts for multimodal request
            parts = []
            
            # Add screenshot first if provided (image before text is recommended)
            if screenshot_data:
                logger.info(f"Adding screenshot to request ({len(screenshot_data)} bytes)")
                # Use SDK's types.Part.from_bytes for proper multimodal content
                image_part = types.Part.from_bytes(
                    data=screenshot_data,
                    mime_type="image/png"
                )
                parts.append(image_part)
            else:
                logger.warning("No screenshot data provided")
            
            # Combine system and user prompts as text
            full_text = f"{system_prompt}\n\n{user_prompt}"
            parts.append(full_text)
            
            # Call Gemini API with LLMGradingResponse schema
            logger.debug(f"Calling Gemini API with {len(parts)} parts for grading")
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=parts,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    response_mime_type="application/json",
                    response_schema=LLMGradingResponse.model_json_schema(),
                    # Disable extended thinking for faster response times
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            
            response_text = response.text
            logger.debug(f"Gemini grading response length: {len(response_text)} chars")
            
            # Extract JSON from markdown code blocks if needed
            clean_json = self._extract_json(response_text)
            
            return clean_json
            
        except Exception as e:
            logger.error(f"Gemini grading generation error: {e}", exc_info=True)
            raise
    
    async def generate_summary(
        self, 
        system_prompt: str, 
        user_prompt: str
    ) -> str:
        """
        Generate summary response using Gemini.
        
        Text-only input (no screenshot) with SummaryLLMResponse schema.
        """
        try:
            # Combine system and user prompts as text
            full_text = f"{system_prompt}\n\n{user_prompt}"
            
            # Call Gemini API with SummaryLLMResponse schema
            logger.debug(f"Calling Gemini API for summary generation")
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=full_text,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    response_mime_type="application/json",
                    response_schema=SummaryLLMResponse.model_json_schema(),
                    # Disable extended thinking for faster response times
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            
            response_text = response.text
            logger.debug(f"Gemini summary response length: {len(response_text)} chars")
            
            # Extract JSON from markdown code blocks if needed
            clean_json = self._extract_json(response_text)
            
            return clean_json
            
        except Exception as e:
            logger.error(f"Gemini summary generation error: {e}", exc_info=True)
            raise
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from response text.
        
        LLM may wrap JSON in markdown code blocks like:
        ```json
        {... }
        ```
        
        Args:
            text: Raw response text
            
        Returns:
            Cleaned JSON string
        """
        # Try to extract from markdown code block
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            logger.debug("Extracted JSON from markdown code block")
            return match.group(1)
        
        # Return as-is (should already be JSON with response_mime_type)
        return text

