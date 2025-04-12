#!/usr/bin/env python3
"""Test script for the file assistant with predefined inputs."""
import os
import json
from text_assistant import TextAssistant

def test_file_assistant():
    """Test the file assistant with predefined inputs."""
    print("\n===== Testing File Assistant (Auto Mode) =====\n")
    
    # Initialize with real OS command execution
    assistant = TextAssistant(config={"dry_run": False})
    
    # Test cases - file operations to test
    test_cases = [
        "Show me what's in hi.txt",
        "Read the contents of sample.txt",
        "List all files in the current directory",
        "Check if test_file.txt exists",
        "Can you show me what's in the test directory?"
    ]
    
    # Run tests
    for i, test_input in enumerate(test_cases, 1):
        print(f"\nTest #{i}: '{test_input}'")
        
        # Process the query
        result = assistant.process_input(test_input)
        
        # Display LLM response
        if result["success"] and "llm_response" in result:
            print(f"Assistant: {result['llm_response']['response']}")
            
            # Auto-confirm if there's a pending action
            if result.get("current_mode") == "OS" and result.get("pending_action"):
                action = result["pending_action"]
                
                # Display action details
                print(f"[Auto-confirming: {action['type']}]")
                if action['type'] == 'os_command':
                    print(f"[Command: {action.get('command', 'unknown')}]")
                
                # Execute action
                confirmation_result = assistant.process_input("yes")
                
                if "action_result" in confirmation_result:
                    action_result = confirmation_result["action_result"]
                    
                    # Show status
                    print(f"Status: {action_result.get('status', 'unknown')}")
                    
                    # If there's stdout in the result, it's likely file content
                    if "stdout" in action_result and action_result["stdout"]:
                        max_length = 300  # Limit output length for display
                        content = action_result["stdout"]
                        if len(content) > max_length:
                            print(f"Output: {content[:max_length]}...[truncated]")
                        else:
                            print(f"Output: {content}")
                        
                    # If there are errors, display them
                    if "stderr" in action_result and action_result["stderr"]:
                        print(f"Errors: {action_result['stderr']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print("-" * 60)

if __name__ == "__main__":
    test_file_assistant()