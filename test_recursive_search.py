#!/usr/bin/env python3
"""Test script for enhanced recursive file search functionality."""
import os
import sys
from text_assistant import TextAssistant
from file_tools import FileToolFactory, FileSearcher

def test_file_search_with_text_assistant():
    """Test the file search functionality using the TextAssistant interface."""
    print("\n===== Testing Enhanced File Search with TextAssistant =====")
    
    # Create a test assistant with file tools enabled
    assistant = TextAssistant(config={
        "llm_model": "gemini",  # Use Gemini model or fallback
        "dry_run": True,        # Don't actually execute OS commands
        "file_tools_enabled": True
    })
    
    # Test direct file operation detection
    print("\nTesting file operation detection:")
    test_operations = [
        "find browser_scenario.json",
        "search for *.json files",
        "locate any Python files in the prototype directory",
        "where is the browser_scenario.json file"
    ]
    
    for op in test_operations:
        request_type, path = FileToolFactory.detect_request_type(op)
        print(f"  '{op}' → {request_type} operation for '{path}'" if request_type else f"  '{op}' → No detection")
    
    # Test actual file search operations
    print("\nTesting file search operations:")
    
    # Test finding a specific file
    print("\n1. Searching for a specific file:")
    result = assistant.process_input("find browser_scenario.json")
    
    if result["success"] and "llm_response" in result:
        print(f"Response: {result['llm_response']['response']}")
    else:
        print("Error: Failed to process the request")
    
    # Test wildcard search
    print("\n2. Searching with wildcard pattern:")
    result = assistant.process_input("find all *.json files")
    
    if result["success"] and "llm_response" in result:
        print(f"Response: {result['llm_response']['response']}")
    else:
        print("Error: Failed to process the request")
    
    # Test search in specific directory
    print("\n3. Searching in a specific directory:")
    result = assistant.process_input("find *.py files in the prototype directory")
    
    if result["success"] and "llm_response" in result:
        print(f"Response: {result['llm_response']['response']}")
    else:
        print("Error: Failed to process the request")

def main():
    """Main function to run the test."""
    test_file_search_with_text_assistant()

if __name__ == "__main__":
    main()