#!/usr/bin/env python3
"""Execute commands directly through the text assistant with auto-confirmation."""
from text_assistant import TextAssistant
import json
import sys

def execute_command(command):
    """Execute a command through the assistant with auto-confirmation."""
    # Initialize the assistant with dry_run=False to actually execute commands
    assistant = TextAssistant(config={"dry_run": False})
    
    print(f"\n=== Executing: '{command}' ===\n")
    
    # Process the command
    result = assistant.process_input(command)
    
    if result["success"] and "llm_response" in result:
        print(f"Assistant: {result['llm_response']['response']}")
        
        # Check if we need confirmation (switched to OS mode)
        if result.get("current_mode") == "OS" and result.get("pending_action"):
            print(f"\nAction detected: {result['pending_action']['type']}")
            
            if result['pending_action']['type'] == "os_command":
                print(f"Command: {result['pending_action']['command']}")
            elif result['pending_action']['type'] == "launch_app":
                print(f"Application: {result['pending_action']['app_name']}")
                
            print("\nAuto-confirming...")
            
            # Auto-confirm by sending "yes"
            confirmation_result = assistant.process_input("yes")
            
            if confirmation_result["success"] and confirmation_result.get("action_result"):
                print(f"\nResult: {confirmation_result['action_result']['message']}")
                
                # Display command output if any
                if "stdout" in confirmation_result["action_result"] and confirmation_result["action_result"]["stdout"].strip():
                    print(f"\nOutput:\n{confirmation_result['action_result']['stdout']}")
                    
                # Display errors if any
                if "stderr" in confirmation_result["action_result"] and confirmation_result["action_result"]["stderr"].strip():
                    print(f"\nErrors:\n{confirmation_result['action_result']['stderr']}")
            else:
                print("\nError executing action")
        else:
            print("No action required")
    else:
        print("Error processing command")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Join all arguments as a single command
        command = " ".join(sys.argv[1:])
        execute_command(command)
    else:
        print("Please provide a command to execute")
        print("Example: python execute_command.py List files in the current directory")
        sys.exit(1)