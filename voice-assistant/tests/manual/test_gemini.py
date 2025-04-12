#!/usr/bin/env python3
"""Interactive script to test the Gemini LLM provider."""
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

def main():
    """Run a simple test of the Gemini LLM provider."""
    # Check if GEMINI_API_KEY is set
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please add your Gemini API key to the .env file or set it directly.")
        return 1

    # Create LLM service with Gemini model type
    llm_service = LLMService(model_type="gemini")
    
    # Check if Gemini is available
    if llm_service.simulation_mode or llm_service.model_type != "gemini":
        print("Error: Gemini is not available. Check API key and internet connection.")
        return 1
    
    print(f"Successfully initialized Gemini LLM with model: {llm_service.model_config['gemini']['model_name']}")
    
    # Default test question
    test_question = "What is a Raspberry Pi?"
    print(f"\nRunning test with question: '{test_question}'")
    
    # Process input
    response = llm_service.process_input(test_question)
    
    # Print response
    print("\nResponse:")
    print(response["response"])
    
    # Print action
    print("\nAction:")
    print(json.dumps(response["action"], indent=2))
    
    print("\nTest completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())