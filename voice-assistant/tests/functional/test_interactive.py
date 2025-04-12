#!/usr/bin/env python3
"""Simple test script for manual verification of interactive assistant functionality."""
import os
import sys
import time
from text_assistant import TextAssistant

def simulate_interaction():
    """Simulate interaction with the text assistant."""
    print("\n===== Simulating Interactive Session =====")
    
    # Create assistant with live execution
    assistant = TextAssistant(config={
        "llm_model": "gemini",  # Use Gemini model
        "dry_run": False,       # Actually execute commands
        "os_commands_enabled": True,
        "file_tools_enabled": True
    })
    
    # Step 1: Find a file using OS command
    print("\n--- Step 1: Find browser_scenario.json using OS command ---")
    action = {
        "type": "os_command",
        "command": "find /workspaces/codespaces-blank/prototype -name browser_scenario.json"
    }
    result = assistant.os_exec_service.execute_action(action)
    
    # Display the result
    print("Result Status:", result.get("status"))
    print("Result Message:", result.get("message"))
    
    if result.get("stdout"):
        print("\nFound files:")
        print(result.get("stdout"))
    
    if result.get("stderr"):
        print("\nErrors:")
        print(result.get("stderr"))
    
    # Step 2: Try to cat the file
    print("\n--- Step 2: Display contents using cat command ---")
    action = {
        "type": "os_command",
        "command": "cat browser_scenario.json"
    }
    result = assistant.os_exec_service.execute_action(action)
    
    # Display the result
    print("Result Status:", result.get("status"))
    print("Result Message:", result.get("message"))
    
    if result.get("stdout"):
        print("\nFile contents:")
        print(result.get("stdout"))
    
    if result.get("stderr"):
        print("\nErrors:")
        print(result.get("stderr"))

def main():
    """Main entry point."""
    simulate_interaction()

if __name__ == "__main__":
    main()