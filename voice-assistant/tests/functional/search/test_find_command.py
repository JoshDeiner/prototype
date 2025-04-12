#!/usr/bin/env python3
"""Test script for enhanced 'find' command handling."""
import os
import sys
from os_exec import OSExecutionService

def test_recursive_file_search():
    """Test the recursive file search functionality."""
    print("\n===== Testing Recursive File Search =====")
    
    # Create a test service
    os_exec = OSExecutionService(dry_run=False, safe_mode=True)
    
    # Test cases
    test_cases = [
        # Test direct path to prototype directory
        {
            "description": "Search for JSON files in prototype/test_scenarios",
            "dir": "prototype/test_scenarios",
            "pattern": "*.json"
        },
        # Test absolute path
        {
            "description": "Search for browser_scenario.json by exact name",
            "dir": "/workspaces/codespaces-blank/prototype",
            "pattern": "browser_scenario.json"
        },
        # Test search in current directory
        {
            "description": "Search for Python files in current directory",
            "dir": ".",
            "pattern": "*.py"
        },
        # Test non-existent directory
        {
            "description": "Search in non-existent directory",
            "dir": "non_existent_directory",
            "pattern": "*.txt"
        }
    ]
    
    # Run test cases
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {case['description']}")
        print(f"  Command: find {case['dir']} -name {case['pattern']}")
        
        # Create action
        action = {
            "type": "os_command",
            "command": f"find {case['dir']} -name {case['pattern']}"
        }
        
        # Execute the action
        result = os_exec.execute_action(action)
        
        # Display results
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        
        if "files_found" in result:
            print(f"  Files found: {result['files_found']}")
        
        if result.get("stdout", "").strip():
            print("\n  Files:")
            for line in result["stdout"].splitlines()[:5]:
                print(f"    - {line}")
            
            if len(result["stdout"].splitlines()) > 5:
                print(f"    ... and {len(result['stdout'].splitlines()) - 5} more")
        
        if result.get("stderr", "").strip():
            print(f"\n  Errors: {result['stderr']}")

def main():
    """Main entry point."""
    test_recursive_file_search()

if __name__ == "__main__":
    main()