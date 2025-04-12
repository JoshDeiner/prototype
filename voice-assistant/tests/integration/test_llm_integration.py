"""Integration tests for LLM service with real APIs."""
import os
import json
import sys
import pytest

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from llm_service import LLMService

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Fixture for test query
@pytest.fixture
def test_query():
    """Return a test query for the LLM."""
    return "What is a Raspberry Pi?"

# Tests for Ollama integration
class TestOllamaIntegration:
    """Tests for Ollama integration with real API."""
    
    def test_ollama_integration(self, test_query):
        """Test integration with Ollama (if available)."""
        # Create LLM service with Llama model type
        llm_service = LLMService(model_type="llama")
        
        # Skip test if Ollama is not available
        if llm_service.simulation_mode or llm_service.model_type != "llama":
            pytest.skip("Ollama not available for testing")
        
        # Process input and check response
        response = llm_service.process_input(test_query)
        
        # Basic validation of response structure
        assert isinstance(response, dict)
        assert "response" in response
        assert "action" in response
        assert "type" in response["action"]
        
        # Print response for manual verification (shows in pytest verbose output)
        print(f"\nOllama Response: {json.dumps(response, indent=2)}")

# Tests for Gemini integration
class TestGeminiIntegration:
    """Tests for Gemini integration with real API."""
    
    def test_gemini_integration(self, test_query):
        """Test integration with Gemini (if available)."""
        # Skip test if GEMINI_API_KEY is not set
        if not os.environ.get("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
            
        # Create LLM service with Gemini model type
        llm_service = LLMService(model_type="gemini")
        
        # Skip test if Gemini is not available
        if llm_service.simulation_mode or llm_service.model_type != "gemini":
            pytest.skip("Gemini not available for testing")
        
        # Process input and check response
        response = llm_service.process_input(test_query)
        
        # Basic validation of response structure
        assert isinstance(response, dict)
        assert "response" in response
        assert "action" in response
        assert "type" in response["action"]
        
        # Print response for manual verification
        print(f"\nGemini Response: {json.dumps(response, indent=2)}")

# Tests for Claude integration
class TestClaudeIntegration:
    """Tests for Claude integration with real API."""
    
    def test_claude_integration(self, test_query):
        """Test integration with Claude (if available)."""
        # Skip test if CLAUDE_API_KEY is not set
        if not os.environ.get("CLAUDE_API_KEY"):
            pytest.skip("CLAUDE_API_KEY not set")
            
        # Create LLM service with Claude model type
        llm_service = LLMService(model_type="claude")
        
        # Skip test if Claude is not available
        if llm_service.simulation_mode:
            pytest.skip("Claude not available for testing")
        
        # Process input and check response
        response = llm_service.process_input(test_query)
        
        # Basic validation of response structure
        assert isinstance(response, dict)
        assert "response" in response
        assert "action" in response
        assert "type" in response["action"]
        
        # Print response for manual verification
        print(f"\nClaude Response: {json.dumps(response, indent=2)}")

# Tests for fallback mechanism
class TestFallbackMechanismIntegration:
    """Tests for the fallback mechanism with real APIs."""
    
    def test_fallback_mechanism(self, test_query):
        """Test the fallback mechanism from Llama to Gemini."""
        # Only run this test if GEMINI_API_KEY is set
        if not os.environ.get("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")
        
        # Get original OLLAMA_API_URL if it exists
        original_ollama_url = os.environ.get("OLLAMA_API_URL")
        
        try:
            # Set an invalid Ollama URL to force fallback
            os.environ["OLLAMA_API_URL"] = "http://invalid-url:11434/api/generate"
            
            # Create LLM service with Llama model type
            llm_service = LLMService(model_type="llama")
            
            # Check if fallback to Gemini occurred
            if llm_service.simulation_mode:
                pytest.skip("Both Ollama and Gemini not available for testing")
            
            # Verify fallback to Gemini
            assert llm_service.model_type == "gemini"
            
            # Process input and check response
            response = llm_service.process_input(test_query)
            
            # Basic validation of response structure
            assert isinstance(response, dict)
            assert "response" in response
            assert "action" in response
            assert "type" in response["action"]
            
            # Print response for manual verification
            print(f"\nFallback Response: {json.dumps(response, indent=2)}")
            
        finally:
            # Restore original OLLAMA_API_URL
            if original_ollama_url:
                os.environ["OLLAMA_API_URL"] = original_ollama_url
            elif "OLLAMA_API_URL" in os.environ:
                del os.environ["OLLAMA_API_URL"]