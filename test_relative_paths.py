#!/usr/bin/env python3
"""Test the relative path resolution feature in the OS execution service."""
from os_exec import OSExecutionService
import os

def test_resolve_path():
    """Test the path resolver functionality with various path types."""
    os_exec = OSExecutionService(dry_run=True)
    
    # Get current directory for reference
    cwd = os.getcwd()
    print(f"Current directory: {cwd}")
    
    # Test cases
    test_cases = [
        "hi.txt",  # Simple filename
        "./hi.txt",  # Relative path with current dir
        "../hi.txt",  # Parent directory
        "~/hi.txt",  # Home directory
        "prototype/hi.txt",  # Subdirectory
        "/workspaces/codespaces-blank/prototype/hi.txt",  # Absolute path
    ]
    
    print("\n=== Testing Path Resolution ===")
    for path in test_cases:
        resolved = os_exec.resolve_path(path)
        print(f"Original: '{path}' → Resolved: '{resolved}'")

def test_command_resolution():
    """Test command resolution with paths."""
    os_exec = OSExecutionService(dry_run=True)
    
    # Test cases for commands
    test_commands = [
        {"command": "cat hi.txt"},
        {"command": "cat ./hi.txt"},
        {"command": "ls -la ../"},
        {"command": "grep test hi.txt"},
        {"command": "cat prototype/hi.txt"},
    ]
    
    print("\n=== Testing Command Resolution ===")
    for action in test_commands:
        result = os_exec._execute_os_command(action)
        print(f"Original: '{action['command']}' → Resolved: '{result['command']}'")

if __name__ == "__main__":
    test_resolve_path()
    test_command_resolution()