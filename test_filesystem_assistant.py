#!/usr/bin/env python3
"""Test script for the filesystem assistant implementation."""
import json
from text_assistant import TextAssistant

def test_file_operations():
    """Test file operations with the text assistant."""
    print("\n===== Testing Filesystem Assistant =====\n")
    
    # Initialize with real OS command execution but auto-confirmation
    assistant = TextAssistant(config={"dry_run": False})
    
    # Test cases - queries that involve file operations
    file_operation_queries = [
        "Please open hi.txt",
        "Show me the contents of sample.txt",
        "Can you check if file1.txt exists in the demo_files directory?",
        "List all test files in the project",
        "Read test_file.txt and tell me what's inside"
    ]
    
    # Run through the test cases
    print("Testing file operation queries:")
    for i, query in enumerate(file_operation_queries, 1):
        print(f"\n{i}. User Query: '{query}'")
        
        # Process the query
        result = assistant.process_input(query)
        
        # Display LLM response
        if result["success"] and "llm_response" in result:
            print(f"   Assistant: {result['llm_response']['response']}")
            
            # Display action details
            if "pending_action" in result:
                action = result["pending_action"]
                print(f"   Action Type: {action['type']}")
                for key, value in action.items():
                    if key != "type":
                        print(f"      {key}: {value}")
                
                # Auto-confirm any pending action
                if result.get("current_mode") == "OS" and result.get("needs_confirmation"):
                    print("\n   [Auto-confirming...]")
                    confirmation_result = assistant.process_input("yes")
                    
                    if "action_result" in confirmation_result:
                        action_result = confirmation_result["action_result"]
                        print(f"   Action Status: {action_result.get('status', 'unknown')}")
                        print(f"   Action Message: {action_result.get('message', 'No message')}")
                        
                        # Print command output if available
                        if "stdout" in action_result and action_result["stdout"]:
                            print(f"\n   Command Output:\n{action_result['stdout'][:300]}...")
                            if len(action_result["stdout"]) > 300:
                                print("   [output truncated]")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        print("\n" + "-" * 80)

if __name__ == "__main__":
    test_file_operations()