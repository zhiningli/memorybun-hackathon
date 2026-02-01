import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pydantic import SecretStr
from services.llm_providers.base import LLMProvider
from services.llm_providers.gemini import GeminiProvider
from services.llm_providers.factory import get_llm_provider

@pytest.fixture
def mock_settings():
    with patch("services.llm_providers.factory.settings") as mock_settings:
        yield mock_settings

@pytest.mark.asyncio
async def test_factory_returns_gemini_provider(mock_settings):
    mock_settings.llm_provider = "gemini"
    mock_settings.gemini_api_key = SecretStr("test_key")  # Use SecretStr
    mock_settings.llm_model = "gemini-2.0-flash-exp"
    
    # Mock the genai.Client constructor AND settings in gemini module
    with patch("services.llm_providers.gemini.genai") as mock_genai, \
         patch("services.llm_providers.gemini.settings", mock_settings):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        
        provider = get_llm_provider()
        
        assert isinstance(provider, GeminiProvider)
        assert provider.model_name == "gemini-2.0-flash-exp"
        # Verify Client was called with mocked test_key (extracted via get_secret_value)
        mock_genai.Client.assert_called_with(api_key="test_key")

@pytest.mark.asyncio
async def test_gemini_generate_grade():
    with patch("services.llm_providers.gemini.genai") as mock_genai:
        # Mock the Client
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        
        # Mock settings so GeminiProvider() works
        with patch("services.llm_providers.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = SecretStr("test_key")  # Use SecretStr
            mock_settings.llm_model = "gemini-2.0-flash-exp"
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1000
            
            provider = GeminiProvider()
            
            # Mock the async response
            mock_response = MagicMock()
            mock_response.text = '{"score": 1.0}'
            
            # Mock the async API call - aio.models.generate_content
            mock_aio = MagicMock()
            mock_models = MagicMock()
            mock_client.aio = mock_aio
            mock_aio.models = mock_models
            
            # Make generate_content return an awaitable
            async def mock_generate(*args, **kwargs):
                return mock_response
            mock_models.generate_content = mock_generate
            
            result = await provider.generate_grade("sys", "user")
            assert result == '{"score": 1.0}'


@pytest.mark.asyncio
async def test_gemini_generate_summary():
    """Test that generate_summary uses SummaryLLMResponse schema."""
    with patch("services.llm_providers.gemini.genai") as mock_genai:
        # Mock the Client
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        
        # Mock settings so GeminiProvider() works
        with patch("services.llm_providers.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = SecretStr("test_key")  # Use SecretStr
            mock_settings.llm_model = "gemini-2.0-flash-exp"
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1000
            
            provider = GeminiProvider()
            
            # Mock summary response
            mock_response = MagicMock()
            mock_response.text = '{"dimension_scores": [], "analytics_summary": [], "overall_feedback": "test", "key_strengths": [], "areas_for_improvement": []}'
            
            # Mock the async API call - aio.models.generate_content
            mock_aio = MagicMock()
            mock_models = MagicMock()
            mock_client.aio = mock_aio
            mock_aio.models = mock_models
            
            # Track the call to verify schema is SummaryLLMResponse
            call_kwargs = {}
            async def mock_generate(*args, **kwargs):
                call_kwargs.update(kwargs)
                return mock_response
            mock_models.generate_content = mock_generate
            
            result = await provider.generate_summary("sys", "user")
            
            # Verify result
            assert "dimension_scores" in result
            assert "overall_feedback" in result
            
            # Verify SummaryLLMResponse schema was used (not LLMGradingResponse)
            config = call_kwargs.get("config")
            assert config is not None
            schema = config.response_schema
            # SummaryLLMResponse has dimension_scores, LLMGradingResponse has score_breakdown
            assert "dimension_scores" in schema.get("properties", {})
            assert "score_breakdown" not in schema.get("properties", {})

