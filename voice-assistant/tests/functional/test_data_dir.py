#!/usr/bin/env python3
"""
Test script to verify that file operations are properly directed to the data directory.
"""
import os
import sys
from file_assistant_middleware import StatefulController

def test_execution():
    # Create the controller
    config = {
        'llm_model': 'gemini',
        'auto_confirm': True
    }
    
    controller = StatefulController(config=config)
    
    # Ensure test file exists
    data_dir = "/workspaces/codespaces-blank/prototype/data"
    test_file = os.path.join(data_dir, "hi.txt")
    if not os.path.exists(test_file):
        with open(test_file, 'w') as f:
            f.write("Hello from data directory\n")
    
    # Test viewing a file
    print('\n--- Testing with: "show me the contents of hi.txt" ---')
    result = controller.process_input('show me the contents of hi.txt')
    print_result(result)
    
    # Test showing a file that has a path component
    print('\n--- Testing with: "show me the contents of /etc/passwd/hi.txt" ---')
    result = controller.process_input('show me the contents of /etc/passwd/hi.txt')
    print_result(result)
    
    # Test listing files
    print('\n--- Testing with: "list files" ---')
    result = controller.process_input('list files')
    print_result(result, show_full_output=False)

def print_result(result, show_full_output=True):
    """Helper function to print results"""
    print(f'Response: {result.get("response", "No response")}')
    
    if 'action_result' in result and result['action_result']:
        print(f'Command executed: {result["action_result"].get("command", "")}')
        
        # Display output
        stdout = result["action_result"].get("stdout", "")
        if stdout:
            if show_full_output:
                print(f'Output: {stdout}')
            else:
                # Just print a few lines
                print(f'Output (first few lines):')
                print('\n'.join(stdout.split('\n')[:5]) + '\n...')
        
        # Display errors if any
        stderr = result["action_result"].get("stderr", "")
        if stderr:
            print(f'Errors: {stderr}')

if __name__ == "__main__":
    test_execution()