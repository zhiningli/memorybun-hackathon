import logging
from typing import Optional
from config import settings
from services.llm_providers.base import LLMProvider
from services.llm_providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)

def get_llm_provider(model_override: Optional[str] = None) -> LLMProvider:
    """
    Factory function to get the configured LLM provider.
    
    Reads settings.llm_provider to determine which class to instantiate.
    
    Args:
        model_override: Optional model name to use instead of settings.llm_model.
                        Useful for summary generation which uses a different model.
    
    Returns:
        Configured LLMProvider instance
        
    Raises:
        ValueError: If provider is not supported or API keys missing
    """
    provider_type = settings.llm_provider.lower()
    model = model_override or settings.llm_model
    
    if provider_type == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set. Cannot initialize Gemini provider.")
            
        logger.info(f"Initializing Gemini provider with model: {model}")
        return GeminiProvider(model_override=model_override)

        
    elif provider_type == "openai":
        # Placeholder for future implementation
        raise NotImplementedError("OpenAI provider not yet implemented")
        
    elif provider_type == "mock":
        # We could return a MockProvider here if we wanted to formalize it
        raise ValueError("Use MockLLMStage directly for mock mode, or implement MockProvider")
        
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")

