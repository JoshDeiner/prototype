"""Integration tests for LLM service with real APIs."""
import os
import unittest
import sys
import json

# Add parent directory to path to import module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prototype.llm_service import LLMService

class TestLLMIntegration(unittest.TestCase):
    """Integration tests for the LLMService class.
    
    These tests attempt to connect to actual LLM services.
    They will be skipped if the necessary services aren't available.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Sample text for testing
        self.test_query = "What is a Raspberry Pi?"
        
    def test_ollama_integration(self):
        """Test integration with Ollama (if available)."""
        # Create LLM service with Llama model type
        llm_service = LLMService(model_type="llama")
        
        # Skip test if Ollama is not available
        if llm_service.simulation_mode or llm_service.model_type != "llama":
            self.skipTest("Ollama not available for testing")
        
        # Process input and check response
        response = llm_service.process_input(self.test_query)
        
        # Basic validation of response structure
        self.assertIsInstance(response, dict)
        self.assertIn("response", response)
        self.assertIn("action", response)
        self.assertIn("type", response["action"])
        
        # Print response for manual verification
        print(f"\nOllama Response: {json.dumps(response, indent=2)}")

    def test_gemini_integration(self):
        """Test integration with Gemini (if available)."""
        # Skip test if GEMINI_API_KEY is not set
        if not os.environ.get("GEMINI_API_KEY"):
            self.skipTest("GEMINI_API_KEY not set")
            
        # Create LLM service with Gemini model type
        llm_service = LLMService(model_type="gemini")
        
        # Skip test if Gemini is not available
        if llm_service.simulation_mode or llm_service.model_type != "gemini":
            self.skipTest("Gemini not available for testing")
        
        # Process input and check response
        response = llm_service.process_input(self.test_query)
        
        # Basic validation of response structure
        self.assertIsInstance(response, dict)
        self.assertIn("response", response)
        self.assertIn("action", response)
        self.assertIn("type", response["action"])
        
        # Print response for manual verification
        print(f"\nGemini Response: {json.dumps(response, indent=2)}")

    def test_claude_integration(self):
        """Test integration with Claude (if available)."""
        # Skip test if CLAUDE_API_KEY is not set
        if not os.environ.get("CLAUDE_API_KEY"):
            self.skipTest("CLAUDE_API_KEY not set")
            
        # Create LLM service with Claude model type
        llm_service = LLMService(model_type="claude")
        
        # Skip test if Claude is not available
        if llm_service.simulation_mode:
            self.skipTest("Claude not available for testing")
        
        # Process input and check response
        response = llm_service.process_input(self.test_query)
        
        # Basic validation of response structure
        self.assertIsInstance(response, dict)
        self.assertIn("response", response)
        self.assertIn("action", response)
        self.assertIn("type", response["action"])
        
        # Print response for manual verification
        print(f"\nClaude Response: {json.dumps(response, indent=2)}")

    def test_fallback_mechanism(self):
        """Test the fallback mechanism from Llama to Gemini."""
        # Only run this test if GEMINI_API_KEY is set
        if not os.environ.get("GEMINI_API_KEY"):
            self.skipTest("GEMINI_API_KEY not set")
        
        # Get original OLLAMA_API_URL if it exists
        original_ollama_url = os.environ.get("OLLAMA_API_URL")
        
        try:
            # Set an invalid Ollama URL to force fallback
            os.environ["OLLAMA_API_URL"] = "http://invalid-url:11434/api/generate"
            
            # Create LLM service with Llama model type
            llm_service = LLMService(model_type="llama")
            
            # Check if fallback to Gemini occurred
            if llm_service.simulation_mode:
                self.skipTest("Both Ollama and Gemini not available for testing")
            
            # Verify fallback to Gemini
            self.assertEqual(llm_service.model_type, "gemini")
            
            # Process input and check response
            response = llm_service.process_input(self.test_query)
            
            # Basic validation of response structure
            self.assertIsInstance(response, dict)
            self.assertIn("response", response)
            self.assertIn("action", response)
            self.assertIn("type", response["action"])
            
            # Print response for manual verification
            print(f"\nFallback Response: {json.dumps(response, indent=2)}")
            
        finally:
            # Restore original OLLAMA_API_URL
            if original_ollama_url:
                os.environ["OLLAMA_API_URL"] = original_ollama_url
            elif "OLLAMA_API_URL" in os.environ:
                del os.environ["OLLAMA_API_URL"]

if __name__ == '__main__':
    unittest.main()