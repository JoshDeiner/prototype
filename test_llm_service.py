"""Test cases for the LLM service module."""
import unittest
import os
import json
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path to import module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prototype.llm_service import LLMService

class TestLLMService(unittest.TestCase):
    """Test cases for the LLMService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Save original environment variables
        self.original_env = os.environ.copy()
        
        # Clear environment variables that might affect tests
        if "OLLAMA_API_URL" in os.environ:
            del os.environ["OLLAMA_API_URL"]
        if "CLAUDE_API_KEY" in os.environ:
            del os.environ["CLAUDE_API_KEY"]
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('prototype.llm_service.requests.get')
    def test_check_ollama_available(self, mock_get):
        """Test _check_ollama_available method."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Initialize LLMService
        llm_service = LLMService(model_type="llama")
        
        # Test Ollama available
        self.assertTrue(llm_service._check_ollama_available())
        
        # Test Ollama not available (exception)
        mock_get.side_effect = Exception("Connection error")
        self.assertFalse(llm_service._check_ollama_available())
        
        # Test Ollama not available (non-200 status)
        mock_get.side_effect = None
        mock_response.status_code = 404
        self.assertFalse(llm_service._check_ollama_available())

    @patch('prototype.llm_service.GEMINI_AVAILABLE', True)
    @patch('prototype.llm_service.genai')
    def test_check_gemini_available(self, mock_genai):
        """Test _check_gemini_available method."""
        # Initialize LLMService with Gemini API key
        os.environ["GEMINI_API_KEY"] = "fake_api_key"
        llm_service = LLMService(model_type="gemini")
        
        # Test Gemini available
        mock_genai.list_models.return_value = ["model1", "model2"]
        self.assertTrue(llm_service._check_gemini_available())
        
        # Test Gemini not available (exception)
        mock_genai.list_models.side_effect = Exception("API error")
        self.assertFalse(llm_service._check_gemini_available())
        
        # Test Gemini not available (no API key)
        del os.environ["GEMINI_API_KEY"]
        llm_service = LLMService(model_type="gemini")
        self.assertFalse(llm_service._check_gemini_available())

    @patch('prototype.llm_service.GEMINI_AVAILABLE', False)
    def test_gemini_library_not_available(self):
        """Test behavior when Gemini library is not available."""
        llm_service = LLMService(model_type="gemini")
        self.assertFalse(llm_service._check_gemini_available())
        self.assertTrue(llm_service.simulation_mode)

    @patch('prototype.llm_service.LLMService._check_ollama_available')
    @patch('prototype.llm_service.LLMService._check_gemini_available')
    def test_llm_fallback_mechanism(self, mock_check_gemini, mock_check_ollama):
        """Test LLM fallback mechanism."""
        # Test Llama available
        mock_check_ollama.return_value = True
        mock_check_gemini.return_value = False
        llm_service = LLMService(model_type="llama")
        self.assertEqual(llm_service.model_type, "llama")
        self.assertFalse(llm_service.simulation_mode)
        
        # Test Llama not available, Gemini available
        mock_check_ollama.return_value = False
        mock_check_gemini.return_value = True
        os.environ["GEMINI_API_KEY"] = "fake_api_key"
        llm_service = LLMService(model_type="llama")
        self.assertEqual(llm_service.model_type, "gemini")
        self.assertFalse(llm_service.simulation_mode)
        
        # Test neither available
        mock_check_ollama.return_value = False
        mock_check_gemini.return_value = False
        llm_service = LLMService(model_type="llama")
        self.assertTrue(llm_service.simulation_mode)
        
        # Test explicit request for Gemini
        mock_check_gemini.return_value = True
        llm_service = LLMService(model_type="gemini")
        self.assertEqual(llm_service.model_type, "gemini")
        self.assertFalse(llm_service.simulation_mode)

    @patch('prototype.llm_service.LLMService._call_ollama')
    @patch('prototype.llm_service.LLMService._call_gemini')
    @patch('prototype.llm_service.LLMService._call_claude')
    def test_process_input(self, mock_call_claude, mock_call_gemini, mock_call_ollama):
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
        with patch('prototype.llm_service.LLMService._check_ollama_available', return_value=True):
            llm_service = LLMService(model_type="llama")
            result = llm_service.process_input("Hello")
            self.assertEqual(result, mock_response)
            mock_call_ollama.assert_called_once()
        
        # Reset mocks
        mock_call_ollama.reset_mock()
        mock_call_gemini.reset_mock()
        mock_call_claude.reset_mock()
        
        # Test with Gemini
        with patch('prototype.llm_service.LLMService._check_gemini_available', return_value=True):
            llm_service = LLMService(model_type="gemini")
            result = llm_service.process_input("Hello")
            self.assertEqual(result, mock_response)
            mock_call_gemini.assert_called_once()
        
        # Reset mocks
        mock_call_ollama.reset_mock()
        mock_call_gemini.reset_mock()
        mock_call_claude.reset_mock()
        
        # Test with Claude
        with patch('prototype.llm_service.LLMService._check_claude_available', return_value=True, create=True):
            os.environ["CLAUDE_API_KEY"] = "fake_api_key"
            llm_service = LLMService(model_type="claude")
            llm_service.simulation_mode = False
            result = llm_service.process_input("Hello")
            self.assertEqual(result, mock_response)
            mock_call_claude.assert_called_once()

    @patch('prototype.llm_service.GEMINI_AVAILABLE', True)
    @patch('prototype.llm_service.genai')
    def test_call_gemini(self, mock_genai):
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
        self.assertEqual(result["response"], "This is a test response")
        self.assertEqual(result["action"]["type"], "none")
        
        # Test with non-JSON response
        mock_response.text = "This is not a JSON response"
        result = llm_service._call_gemini(prompt)
        self.assertEqual(result["response"], "This is not a JSON response")
        self.assertEqual(result["action"]["type"], "none")
        
        # Test with exception
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = Exception("API error")
        result = llm_service._call_gemini(prompt)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()