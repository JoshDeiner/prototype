#!/usr/bin/env python3
"""Test the stateful controller with LLM→OS execution flow."""
from text_assistant import TextAssistant
import time
import json
import os
from utils import logger, ensure_directory

def test_llm_os_flow():
    """Test the LLM → OS execution flow with a simple command."""
    print("\n=== Testing LLM → OS Execution Flow ===")
    
    # Initialize assistant in simulation mode
    assistant = TextAssistant()
    
    print("Sending query: 'List the files in the current directory'")
    result = assistant.process_input("List the files in the current directory")
    
    if result["success"] and result.get("current_mode") == "OS":
        print("Success! Transition to OS mode detected.")
        print(f"LLM Response: {result['llm_response']['response']}")
        print(f"Pending Action: {json.dumps(result.get('pending_action', {}), indent=2)}")
        
        # Now confirm the action
        print("\nSending confirmation: 'yes'")
        confirmation_result = assistant.process_input("yes")
        
        if confirmation_result["success"] and confirmation_result.get("action_result"):
            print("Success! Action execution detected.")
            print(f"Action Result: {json.dumps(confirmation_result['action_result'], indent=2)}")
            
            # Check for transition back to LLM mode
            if confirmation_result.get("current_mode") == "LLM":
                print("Success! Transition back to LLM mode detected.")
            else:
                print(f"Error: Failed to transition back to LLM mode. Current mode: {confirmation_result.get('current_mode')}")
        else:
            print("Error: Failed to execute action.")
    else:
        print("Error: Failed to transition to OS mode.")
        print(f"Result: {json.dumps(result, indent=2)}")

def test_action_cancellation():
    """Test cancelling an action in OS mode."""
    print("\n=== Testing Action Cancellation ===")
    
    # Initialize assistant in simulation mode
    assistant = TextAssistant()
    
    print("Sending query: 'List the files in the current directory'")
    result = assistant.process_input("List the files in the current directory")
    
    if result["success"] and result.get("current_mode") == "OS":
        print("Success! Transition to OS mode detected.")
        print(f"LLM Response: {result['llm_response']['response']}")
        print(f"Pending Action: {json.dumps(result.get('pending_action', {}), indent=2)}")
        
        # Now cancel the action
        print("\nSending cancellation: 'no'")
        cancellation_result = assistant.process_input("no")
        
        if cancellation_result["success"] and cancellation_result.get("action_cancelled"):
            print("Success! Action cancellation detected.")
            print(f"Response: {cancellation_result['llm_response']['response']}")
            
            # Check for transition back to LLM mode
            if cancellation_result.get("current_mode") == "LLM":
                print("Success! Transition back to LLM mode detected.")
            else:
                print(f"Error: Failed to transition back to LLM mode. Current mode: {cancellation_result.get('current_mode')}")
        else:
            print("Error: Failed to cancel action.")
    else:
        print("Error: Failed to transition to OS mode.")

def main():
    """Run the integration tests."""
    test_llm_os_flow()
    test_action_cancellation()

if __name__ == "__main__":
    main()