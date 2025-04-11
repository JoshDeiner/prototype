#!/usr/bin/env python3
"""Test script for enhanced file searching functionality."""
import os
import sys
from os_exec import OSExecutionService
from text_assistant import TextAssistant

def test_find_commands():
    """Test handling of find commands."""
    print("\n===== Testing Enhanced Find Command Handling =====")
    
    # Create a test service
    os_exec = OSExecutionService(dry_run=False, safe_mode=True)
    
    # Test cases for find commands
    find_commands = [
        # Standard find command
        "find prototype/test_scenarios -name browser_scenario.json",
        # Find command with non-existent directory
        "find non_existent_dir -name browser_scenario.json",
        # Find with wildcard
        "find /workspaces/codespaces-blank/prototype -name *.json",
        # Sudo find command
        "sudo find / -name browser_scenario.json"
    ]
    
    # Run test cases
    for i, command in enumerate(find_commands, 1):
        print(f"\nTest Case {i}: {command}")
        
        # Create action
        action = {
            "type": "os_command",
            "command": command
        }
        
        # Execute the action
        result = os_exec.execute_action(action)
        
        # Display results
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        
        if result.get("stdout", "").strip():
            print("\n  Files:")
            for line in result["stdout"].splitlines()[:3]:
                print(f"    - {line}")
            
            if len(result["stdout"].splitlines()) > 3:
                print(f"    ... and {len(result['stdout'].splitlines()) - 3} more")
        
        if result.get("stderr", "").strip():
            print(f"\n  Errors: {result['stderr']}")

def test_cat_commands():
    """Test handling of cat commands for browser_scenario.json."""
    print("\n===== Testing Enhanced Cat Command Handling =====")
    
    # Create a test service
    os_exec = OSExecutionService(dry_run=False, safe_mode=True)
    
    # Test cases for cat commands
    cat_commands = [
        # Direct cat command that would normally fail
        "cat browser_scenario.json",
        # Cat with relative path
        "cat prototype/test_scenarios/browser_scenario.json",
        # Cat with absolute path
        "cat /workspaces/codespaces-blank/prototype/test_scenarios/browser_scenario.json"
    ]
    
    # Run test cases
    for i, command in enumerate(cat_commands, 1):
        print(f"\nTest Case {i}: {command}")
        
        # Create action
        action = {
            "type": "os_command",
            "command": command
        }
        
        # Execute the action
        result = os_exec.execute_action(action)
        
        # Display results
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        
        if result.get("stdout", "").strip():
            print("\n  Content:")
            content = result["stdout"].strip()
            # Truncate if too long
            if len(content) > 200:
                print(f"    {content[:200]}...")
            else:
                print(f"    {content}")
        
        if result.get("stderr", "").strip():
            print(f"\n  Errors: {result['stderr']}")

def main():
    """Main entry point."""
    # Test find commands
    test_find_commands()
    
    # Test cat commands
    test_cat_commands()

if __name__ == "__main__":
    main()