#!/usr/bin/env python3
"""Test the clarification feature in the text assistant."""
from text_assistant import TextAssistant

def test_clarification_flow():
    """Test the clarification flow with different inputs."""
    # Initialize the assistant
    print("\n=== Testing Clarification Flow ===\n")
    assistant = TextAssistant()
    
    # Test case 1: Vague command that needs clarification
    print("Test 1: Vague command")
    print("User: show me files")
    result1 = assistant.process_input("show me files")
    
    if "clarification_requested" in result1 and result1["llm_response"]["action"]["type"] == "clarify":
        print("Success! Assistant asked for clarification:")
        print(f"Assistant: {result1['llm_response']['response']}")
        print(f"Clarification type: {result1['llm_response']['action']['question']}")
        
        # Now respond with more specific information
        print("\nUser: list all files in the current directory with details")
        result2 = assistant.process_input("list all files in the current directory with details")
        
        if result2.get("current_mode") == "OS" and result2.get("pending_action"):
            print("Success! Now has enough information for an action")
            print(f"Assistant: {result2['llm_response']['response']}")
            print(f"Action type: {result2['pending_action']['type']}")
            print(f"Command: {result2['pending_action'].get('command', 'N/A')}")
            
            # Auto-confirm
            print("\nAuto-confirming...")
            result3 = assistant.process_input("yes")
            
            print(f"Result: {result3['action_result']['message']}")
            if "stdout" in result3["action_result"]:
                print(f"Command output preview: {result3['action_result']['stdout'][:200]}...")
        else:
            print("Error: Failed to proceed to action after clarification")
    else:
        print("Error: Assistant did not ask for clarification as expected")
    
    # Test case 2: Vague file request
    print("\n\nTest 2: Vague file request")
    assistant = TextAssistant()  # Fresh instance
    
    print("User: open a file")
    result4 = assistant.process_input("open a file")
    
    if "clarification_requested" in result4 and result4["llm_response"]["action"]["type"] == "clarify":
        print("Success! Assistant asked for clarification:")
        print(f"Assistant: {result4['llm_response']['response']}")
        
        # Now respond with more specific command
        print("\nUser: show contents of hi.txt")
        result5 = assistant.process_input("show contents of hi.txt")
        
        if result5.get("current_mode") == "OS" and result5.get("pending_action"):
            print("Success! Now has enough information for an action")
            print(f"Assistant: {result5['llm_response']['response']}")
            print(f"Action type: {result5['pending_action']['type']}")
            print(f"Command: {result5['pending_action'].get('command', 'N/A')}")
            
            # Auto-confirm
            print("\nAuto-confirming...")
            result6 = assistant.process_input("yes")
            
            print(f"Result: {result6['action_result']['message']}")
            if "stdout" in result6["action_result"]:
                print(f"File content preview: {result6['action_result']['stdout'][:200]}...")
        else:
            print("Error: Failed to proceed to action after clarification")
    else:
        print("Error: Assistant did not ask for clarification as expected")

if __name__ == "__main__":
    test_clarification_flow()