#!/usr/bin/env python3
"""Script to run the File Assistant Scene with auto-confirmation of commands."""
import subprocess
import sys
import os
import time
from text_assistant import TextAssistant

def main():
    """Run an interactive session with the file assistant that auto-confirms commands."""
    print("\n===== Interactive File Assistant =====")
    print("(Type 'exit' to end the session)")
    print("\nThis assistant can help you read files, list directories, and perform basic file operations.")
    print("Commands are automatically confirmed for you.\n")
    
    # Initialize with real OS command execution
    assistant = TextAssistant(config={"dry_run": False})
    
    # Interactive loop
    try:
        while True:
            # Get user input
            user_input = input("\nYou: ")
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\nThank you for using the File Assistant!")
                break
                
            # Process the query
            result = assistant.process_input(user_input)
            
            # Display LLM response
            if result["success"] and "llm_response" in result:
                print(f"\nAssistant: {result['llm_response']['response']}")
                
                # Auto-confirm if there's a pending action
                if result.get("current_mode") == "OS" and result.get("pending_action"):
                    action = result["pending_action"]
                    
                    # Display action details
                    print(f"\n[Auto-confirming: {action['type']}]")
                    if action['type'] == 'os_command':
                        print(f"[Command: {action.get('command', 'unknown')}]")
                    
                    # Execute action with 1-second delay
                    time.sleep(0.5)
                    confirmation_result = assistant.process_input("yes")
                    
                    if "action_result" in confirmation_result:
                        action_result = confirmation_result["action_result"]
                        
                        # If there's stdout in the result, it's likely file content
                        if "stdout" in action_result and action_result["stdout"]:
                            print(f"\nOutput:\n{action_result['stdout']}")
                            
                        # If there are errors, display them
                        if "stderr" in action_result and action_result["stderr"]:
                            print(f"\nErrors: {action_result['stderr']}")
            else:
                print(f"\nError: {result.get('error', 'Unknown error')}")
    
    except KeyboardInterrupt:
        print("\n\nThank you for using the File Assistant!")
        
if __name__ == "__main__":
    main()