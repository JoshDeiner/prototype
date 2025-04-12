#!/usr/bin/env python3
"""Test script for verifying file reading functionality."""
import os
import sys
from os_exec import OSExecutionService
from text_assistant import TextAssistant

def test_file_detection():
    """Test various ways of referring to files."""
    
    # Set up test file
    test_file = "test.txt"
    abs_test_file = os.path.abspath(test_file)
    if not os.path.exists(test_file):
        with open(test_file, 'w') as f:
            f.write("This is a test file for the file reading functionality.")
    
    # Create services
    os_exec = OSExecutionService(dry_run=False, safe_mode=True)
    assistant = TextAssistant(config={"os_commands_enabled": True, "dry_run": False})
    
    # Test cases for file detection
    test_cases = [
        "open hi.txt",
        "can you read test.txt",
        "show me the content of test.txt",
        "test.txt",
        "what's in test.txt",
        "read test.txt",
        "display test.txt",
        "view test.txt",
        "cat test.txt",
        "get test.txt",
        "open test.txt please",
        "I need to read test.txt",
        "can you open and read to me the file on my local machine test.txt"
    ]
    
    print("\n===== Testing File Detection =====")
    for i, test_input in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{test_input}'")
        
        # Test direct intent detection
        intent = os_exec.detect_user_intent(test_input)
        if intent['type'] == 'filesystem' and intent['operation'] == 'read':
            print(f"✅ OS_EXEC Intent Detection: {intent['type']}/{intent['operation']} - Filename: {intent.get('filename')}")
        else:
            print(f"❌ OS_EXEC Intent Detection failed: {intent}")
            
            # If direct detection fails, test the TextAssistant's fallback mechanism
            results = assistant.process_input(test_input)
            if results.get('action_result') and 'content' in results.get('action_result', {}):
                print(f"✅ TEXT_ASSISTANT Fallback succeeded")
            else:
                print(f"❌ TEXT_ASSISTANT Fallback failed: {results.get('action_result', {}).get('message', 'Unknown error')}")
    
    # Test follow-up questions
    print("\n===== Testing Follow-up Questions =====")
    follow_up_tests = [
        "what does it say",
        "what's in it",
        "show me the contents",
        "read it",
        "the file",
        "it",
        "open it"
    ]
    
    # First set the last file read
    assistant.last_file_read = "test.txt"
    
    for i, test_input in enumerate(follow_up_tests, 1):
        print(f"\nFollow-up Test {i}: '{test_input}'")
        results = assistant.process_input(test_input)
        
        if results.get('action_result') and 'content' in results.get('action_result', {}):
            print(f"✅ Follow-up succeeded: {results.get('action_result', {}).get('message', 'Unknown')}")
        else:
            print(f"❌ Follow-up failed: {results.get('action_result', {}).get('message', 'Unknown error')}")

if __name__ == "__main__":
    test_file_detection()