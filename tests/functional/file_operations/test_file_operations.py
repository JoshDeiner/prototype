#!/usr/bin/env python3
"""Test file operations with the stateful controller architecture."""
import os
import time
from text_assistant import TextAssistant
from os_exec import OSExecutionService

def create_test_files():
    """Create some test files for the tests."""
    # Make sure we have some test files
    with open("test.txt", "w") as f:
        f.write("This is a test file with some content.\n")
    
    with open("hi.txt", "w") as f:
        f.write("Hello, world! This is another test file.\n")
    
    with open("notes.txt", "w") as f:
        f.write("These are some notes for testing file operations.\n")
    
    # Create a test directory and file
    os.makedirs("test_dir", exist_ok=True)
    with open(os.path.join("test_dir", "sample.txt"), "w") as f:
        f.write("This is a sample file in the test directory.\n")

def test_file_checking():
    """Test the file checking functionality."""
    print("\n===== Testing File Checking =====")
    
    # Create a TextAssistant instance
    assistant = TextAssistant(config={
        "llm_model": "simulation",
        "dry_run": False,
        "safe_mode": True,
        "os_commands_enabled": True
    })
    
    # Test queries that should trigger file checks
    test_queries = [
        "Can you show me the content of test.txt",
        "Open the file hi.txt please",
        "I'd like to read notes.txt",
        "Please check if nonexistent.txt exists",
        "Can you verify if test_dir/sample.txt exists?",
        "Is there a file called missing_file.txt?",
        "Show me what's in hello.txt" # Similar to hi.txt
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = assistant.process_input(query)
        
        # Print the LLM response
        if result.get("llm_response"):
            print(f"Assistant: {result['llm_response']['response']}")
        
        # Check if a file check was performed
        if result.get("file_check_performed"):
            file_check = result.get("file_check_result", {})
            print("File check performed:")
            if file_check.get("file_exists", False):
                print(f"✓ File exists: {file_check.get('file_path')}")
                print(f"  Size: {file_check.get('size')} bytes")
                print(f"  Type: {file_check.get('file_type')}")
            elif file_check.get("is_directory", False):
                print(f"! Path is a directory: {file_check.get('path')}")
            else:
                print(f"✗ File not found: {file_check.get('searched_path')}")
                if file_check.get("similar_files"):
                    print("  Similar files found:")
                    for f in file_check.get("similar_files", [])[:3]:
                        print(f"  - {f.get('name')} (similarity: {f.get('similarity')*100:.0f}%)")
        else:
            print("No file check was performed")
        
        print("-" * 50)

def test_directory_searching():
    """Test the directory searching functionality."""
    print("\n===== Testing Directory Searching =====")
    
    # Create a TextAssistant instance
    assistant = TextAssistant(config={
        "llm_model": "simulation",
        "dry_run": False,
        "safe_mode": True,
        "os_commands_enabled": True
    })
    
    # Test queries that should trigger directory searches
    test_queries = [
        "List files in the test_dir directory",
        "Can you find the prototype directory?",
        "Look for a directory called tests",
        "Is there a folder named missing_dir?",
        "Find any directories with 'test' in the name"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = assistant.process_input(query)
        
        # Print the LLM response
        if result.get("llm_response"):
            print(f"Assistant: {result['llm_response']['response']}")
        
        # Check if a directory search was performed
        if result.get("dir_search_performed"):
            dir_search = result.get("dir_search_result", {})
            print("Directory search performed:")
            
            directories = dir_search.get("directories", [])
            if directories:
                print(f"Found {len(directories)} directories:")
                for i, d in enumerate(directories[:5]):
                    match_type = "Exact match" if d.get("is_exact_match", False) else "Partial match"
                    print(f"  {i+1}. [{match_type}] {d.get('path')}")
            else:
                print(f"No directories found matching '{dir_search.get('searched_for', '')}'")
        else:
            print("No directory search was performed")
        
        print("-" * 50)

def test_relative_paths():
    """Test handling of relative paths in commands."""
    print("\n===== Testing Relative Path Resolution =====")
    
    # Create a TextAssistant instance
    assistant = TextAssistant(config={
        "llm_model": "simulation",
        "dry_run": False,
        "safe_mode": True,
        "os_commands_enabled": True
    })
    
    # Test queries with relative paths
    test_queries = [
        "Show me the content of ./test.txt",
        "Read the file ../prototype/hi.txt",
        "List files in ./test_dir",
        "Show me what's in test_dir/sample.txt",
        "Can you check if ./nonexistent.txt exists?"
    ]
    
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = assistant.process_input(query)
        
        # Print the LLM response
        if result.get("llm_response"):
            print(f"Assistant: {result['llm_response']['response']}")
        
        # If we switched to OS mode, auto-confirm to execute the command
        if assistant.current_mode == "OS" and result.get("pending_action"):
            print("Auto-confirming action...")
            action = result.get("pending_action")
            
            if action["type"] == "os_command":
                print(f"Command: {action['command']}")
            
            # Auto-confirm by passing empty string
            confirm_result = assistant.process_input("")
            
            # Print the result
            if confirm_result.get("action_result"):
                action_result = confirm_result["action_result"]
                print(f"Result: {action_result.get('message', '')}")
                
                if "stdout" in action_result and action_result["stdout"].strip():
                    print(f"Output: {action_result['stdout'][:100]}...")
                
                if "file_path" in action_result:
                    print(f"Resolved path: {action_result['file_path']}")
        
        print("-" * 50)

def test_file_to_os_mode_flow():
    """Test the flow from file checking to OS mode execution."""
    print("\n===== Testing File Validation to OS Mode Flow =====")
    
    # Create a TextAssistant instance
    assistant = TextAssistant(config={
        "llm_model": "simulation",
        "dry_run": False,
        "safe_mode": True,
        "os_commands_enabled": True
    })
    
    # Test the complete flow: file check -> confirmation -> OS action
    test_flows = [
        [
            "Can you show me the content of test.txt?",
            "Yes, please show it"
        ],
        [
            "Read the file that has 'hello' in it",
            "Yes, show that file"
        ],
        [
            "List files in the test directory",
            "Yes, list them"
        ]
    ]
    
    for flow in test_flows:
        print("\nStarting new flow:")
        
        for i, query in enumerate(flow):
            print(f"\nStep {i+1}: {query}")
            
            result = assistant.process_input(query)
            
            # Print the LLM response
            if result.get("llm_response"):
                print(f"Assistant: {result['llm_response']['response']}")
            
            # Show file check results
            if result.get("file_check_performed"):
                file_check = result.get("file_check_result", {})
                print("File check performed:")
                if file_check.get("file_exists", False):
                    print(f"✓ File exists: {file_check.get('file_path')}")
                else:
                    print(f"✗ File not found: {file_check.get('searched_path', '')}")
            
            # Show directory search results
            if result.get("dir_search_performed"):
                dir_search = result.get("dir_search_result", {})
                print("Directory search performed:")
                if dir_search.get("directories"):
                    print(f"✓ Directories found: {len(dir_search.get('directories', []))}")
                else:
                    print(f"✗ No directories found")
            
            # Show action results
            if result.get("action_result"):
                action_result = result.get("action_result")
                print(f"Action result: {action_result.get('status', '')}")
                
                if "stdout" in action_result and action_result["stdout"].strip():
                    print(f"Output: {action_result['stdout'][:100]}...")
        
        print("-" * 50)

def main():
    """Run all tests."""
    # Create test files first
    create_test_files()
    
    # Run tests
    test_file_checking()
    test_directory_searching()
    test_relative_paths()
    test_file_to_os_mode_flow()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()