#!/usr/bin/env python3
"""Test the file checking and directory search functionality."""
from text_assistant import TextAssistant
from os_exec import OSExecutionService
import json

def test_file_check():
    """Test the file check functionality."""
    print("\n=== Testing File Check ===\n")
    os_exec = OSExecutionService()
    
    # Test with existing file
    file_check = os_exec.execute_action({
        "type": "file_check",
        "file_path": "hi.txt"
    })
    
    print("Checking existing file (hi.txt):")
    print(json.dumps(file_check, indent=2))
    
    # Test with non-existent file
    file_check = os_exec.execute_action({
        "type": "file_check",
        "file_path": "nonexistent.txt"
    })
    
    print("\nChecking non-existent file:")
    print(json.dumps(file_check, indent=2))
    
    # Test with directory instead of file
    file_check = os_exec.execute_action({
        "type": "file_check",
        "file_path": "test_scenarios"
    })
    
    print("\nChecking directory instead of file:")
    print(json.dumps(file_check, indent=2))

def test_dir_search():
    """Test the directory search functionality."""
    print("\n=== Testing Directory Search ===\n")
    os_exec = OSExecutionService()
    
    # Test with existing directory
    dir_search = os_exec.execute_action({
        "type": "dir_search",
        "dir_name": "test_scenarios"
    })
    
    print("Searching for existing directory (test_scenarios):")
    print(json.dumps(dir_search, indent=2))
    
    # Test with partial name
    dir_search = os_exec.execute_action({
        "type": "dir_search",
        "dir_name": "test"
    })
    
    print("\nSearching for partial name (test):")
    print(json.dumps(dir_search, indent=2))
    
    # Test with non-existent directory
    dir_search = os_exec.execute_action({
        "type": "dir_search",
        "dir_name": "nonexistent_dir"
    })
    
    print("\nSearching for non-existent directory:")
    print(json.dumps(dir_search, indent=2))

if __name__ == "__main__":
    test_file_check()
    test_dir_search()