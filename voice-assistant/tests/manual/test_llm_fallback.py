#!/usr/bin/env python3
"""Script to test the LLM fallback mechanism."""
# Tell pytest to ignore this file for test collection
__test__ = False
import os
import json
import sys
from dotenv import load_dotenv

# Add parent directory to path to import module if running from another directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file
load_dotenv()

# Import LLMService
from llm_service import LLMService

def test_service(service_name, llm_service):
    """Test a specific LLM service with a question.
    
    Returns:
        bool: True if the test passed successfully, False otherwise
    """
    print(f"\n===== Testing {service_name} =====")
    print(f"Model type: {llm_service.model_type}")
    print(f"Simulation mode: {llm_service.simulation_mode}")
    
    # If in simulation mode, explain why
    if llm_service.simulation_mode:
        print(f"Reason: No {service_name} API available or configured")
        return False
    
    # Ask a simple question
    question = "What is a Raspberry Pi?"
    print(f"\nQuestion: {question}")
    
    try:
        # Process the question
        response = llm_service.process_input(question)
        
        # Print response
        print("\nResponse:")
        print(response["response"])
        
        # Print action
        print("\nAction:")
        print(json.dumps(response["action"], indent=2))
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run tests for different LLM providers and fallback mechanism."""
    print("LLM Provider Fallback Test")
    print("=========================")
    
    # Get original OLLAMA_API_URL if it exists
    original_ollama_url = os.environ.get("OLLAMA_API_URL")
    
    try:
        # Test Llama (will likely use fallback)
        print("\n\n1. Testing Llama (default):")
        llm_service = LLMService(model_type="llama")
        test_service("Llama", llm_service)
        
        # Force fallback by setting invalid Ollama URL
        print("\n\n2. Testing fallback mechanism:")
        os.environ["OLLAMA_API_URL"] = "http://invalid-url:11434/api/generate"
        llm_service = LLMService(model_type="llama")
        if llm_service.model_type != "llama":
            print(f"Fallback successfully activated: Using {llm_service.model_type} instead of llama")
        test_service("Fallback", llm_service)
        
        # Test Gemini explicitly
        print("\n\n3. Testing Gemini explicitly:")
        llm_service = LLMService(model_type="gemini")
        test_service("Gemini", llm_service)
        
        # Test Claude explicitly
        print("\n\n4. Testing Claude explicitly:")
        llm_service = LLMService(model_type="claude")
        test_service("Claude", llm_service)
        
    finally:
        # Restore original OLLAMA_API_URL
        if original_ollama_url:
            os.environ["OLLAMA_API_URL"] = original_ollama_url
        elif "OLLAMA_API_URL" in os.environ:
            del os.environ["OLLAMA_API_URL"]
    
    print("\n\nTest complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())