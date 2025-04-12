"""Unit tests for the LLM service module."""
import os
import json
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from llm_service import LLMService

# Fixture to manage environment variables
@pytest.fixture
def clean_env():
    """Fixture to temporarily clear relevant environment variables for testing."""
    # Save original environment variables
    original_env = {
        "OLLAMA_API_URL": os.environ.get("OLLAMA_API_URL"),
        "CLAUDE_API_KEY": os.environ.get("CLAUDE_API_KEY"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY")
    }
    
    # Clear environment variables that might affect tests
    for key in original_env:
        if key in os.environ:
            del os.environ[key]
    
    # Run the test
    yield
    
    # Restore original environment variables
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]

# Tests for the Ollama/Llama functionality
class TestOllamaFunctionality:
    """Tests related to Ollama/Llama functionality."""
    
    @patch('llm_service.requests.get')
    def test_check_ollama_available(self, mock_get, clean_env):
        """Test _check_ollama_available method."""
        # Set up mock response for success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Initialize LLMService
        llm_service = LLMService(model_type="llama")
        
        # Test Ollama available
        assert llm_service._check_ollama_available() is True
        
        # Test Ollama not available (exception)
        mock_get.side_effect = Exception("Connection error")
        assert llm_service._check_ollama_available() is False
        
        # Test Ollama not available (non-200 status)
        mock_get.side_effect = None
        mock_response.status_code = 404
        assert llm_service._check_ollama_available() is False

# Tests for the Gemini functionality
class TestGeminiFunctionality:
    """Tests related to Gemini functionality."""
    
    @patch('llm_service.GEMINI_AVAILABLE', True)
    @patch('llm_service.genai', create=True)
    def test_check_gemini_available(self, mock_genai, clean_env):
        """Test _check_gemini_available method."""
        # Initialize LLMService with Gemini API key
        os.environ["GEMINI_API_KEY"] = "fake_api_key"
        llm_service = LLMService(model_type="gemini")
        
        # Test Gemini available
        mock_genai.list_models.return_value = ["model1", "model2"]
        assert llm_service._check_gemini_available() is True
        
        # Test Gemini not available (exception)
        mock_genai.list_models.side_effect = Exception("API error")
        assert llm_service._check_gemini_available() is False
        
        # Test Gemini not available (no API key)
        del os.environ["GEMINI_API_KEY"]
        llm_service = LLMService(model_type="gemini")
        assert llm_service._check_gemini_available() is False
    
    @patch('llm_service.GEMINI_AVAILABLE', False)
    def test_gemini_library_not_available(self, clean_env):
        """Test behavior when Gemini library is not available."""
        llm_service = LLMService(model_type="gemini")
        assert llm_service._check_gemini_available() is False
        assert llm_service.simulation_mode is True
    
    @patch('llm_service.GEMINI_AVAILABLE', True)
    @patch('llm_service.genai', create=True)
    def test_call_gemini(self, mock_genai, clean_env):
        """Test _call_gemini method."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.text = '{"response": "This is a test response", "action": {"type": "none"}}'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        # Initialize LLMService with Gemini API key
        os.environ["GEMINI_API_KEY"] = "fake_api_key"
        llm_service = LLMService(model_type="gemini")
        llm_service.simulation_mode = False
        
        # Test with valid JSON response
        prompt = {
            "system": "You are a helpful assistant",
            "conversation": "User: Hello\nAssistant:"
        }
        result = llm_service._call_gemini(prompt)
        assert result["response"] == "This is a test response"
        assert result["action"]["type"] == "none"
        
        # Test with non-JSON response
        mock_response.text = "This is not a JSON response"
        result = llm_service._call_gemini(prompt)
        assert result["response"] == "This is not a JSON response"
        assert result["action"]["type"] == "none"
        
        # Test with exception
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = Exception("API error")
        result = llm_service._call_gemini(prompt)
        assert result is None

# Tests for fallback mechanism
class TestFallbackMechanism:
    """Tests related to LLM provider fallback mechanism."""
    
    @patch('llm_service.LLMService._check_ollama_available')
    @patch('llm_service.LLMService._check_gemini_available')
    def test_llm_fallback_mechanism(self, mock_check_gemini, mock_check_ollama, clean_env):
        """Test LLM fallback mechanism."""
        # Test Llama available
        mock_check_ollama.return_value = True
        mock_check_gemini.return_value = False
        llm_service = LLMService(model_type="llama")
        assert llm_service.model_type == "llama"
        assert llm_service.simulation_mode is False
        
        # Test Llama not available, Gemini available
        mock_check_ollama.return_value = False
        mock_check_gemini.return_value = True
        os.environ["GEMINI_API_KEY"] = "fake_api_key"
        llm_service = LLMService(model_type="llama")
        assert llm_service.model_type == "gemini"
        assert llm_service.simulation_mode is False
        
        # Test neither available
        mock_check_ollama.return_value = False
        mock_check_gemini.return_value = False
        llm_service = LLMService(model_type="llama")
        assert llm_service.simulation_mode is True
        
        # Test explicit request for Gemini
        mock_check_gemini.return_value = True
        llm_service = LLMService(model_type="gemini")
        assert llm_service.model_type == "gemini"
        assert llm_service.simulation_mode is False

# Tests for process_input method
class TestProcessInput:
    """Tests related to the process_input method."""
    
    @patch('llm_service.LLMService._call_ollama')
    @patch('llm_service.LLMService._call_gemini')
    @patch('llm_service.LLMService._call_claude')
    def test_process_input(self, mock_call_claude, mock_call_gemini, mock_call_ollama, clean_env):
        """Test process_input method with different model types."""
        # Set up mock responses
        mock_response = {
            "response": "This is a test response",
            "action": {"type": "none"}
        }
        mock_call_ollama.return_value = mock_response
        mock_call_gemini.return_value = mock_response
        mock_call_claude.return_value = mock_response
        
        # Test with Llama
        with patch('llm_service.LLMService._check_ollama_available', return_value=True):
            llm_service = LLMService(model_type="llama")
            result = llm_service.process_input("Hello")
            assert result == mock_response
            mock_call_ollama.assert_called_once()
        
        # Reset mocks
        mock_call_ollama.reset_mock()
        mock_call_gemini.reset_mock()
        mock_call_claude.reset_mock()
        
        # Test with Gemini
        with patch('llm_service.LLMService._check_gemini_available', return_value=True):
            llm_service = LLMService(model_type="gemini")
            result = llm_service.process_input("Hello")
            assert result == mock_response
            mock_call_gemini.assert_called_once()
        
        # Reset mocks
        mock_call_ollama.reset_mock()
        mock_call_gemini.reset_mock()
        mock_call_claude.reset_mock()
        
        # Test with Claude
        with patch('llm_service.LLMService._check_claude_available', return_value=True, create=True):
            os.environ["CLAUDE_API_KEY"] = "fake_api_key"
            llm_service = LLMService(model_type="claude")
            llm_service.simulation_mode = False
            result = llm_service.process_input("Hello")
            assert result == mock_response
            mock_call_claude.assert_called_once()