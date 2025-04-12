#!/usr/bin/env python3
"""Test script for filesystem operations."""
import os
import json
import sys

from text_assistant import TextAssistant
from os_exec import OSExecutionService

def test_intent_detection():
    """Test the filesystem intent detection."""
    os_exec = OSExecutionService(dry_run=True)
    
    # Test cases for read operation
    read_queries = [
        "Show me the contents of file.txt",
        "Read the test_file.txt file",
        "Can you open the README.md file",
        "Display the text from config.json",
        "Print the contents of data.csv",
        "What's in the log.txt file?",
        "Get data.json for me",
        "View file.py",
        "Show text from .env file",
        "Display the README"
    ]
    
    # Test cases for list operation
    list_queries = [
        "List the files in the current directory",
        "Show me all files",
        "List files in the prototype folder",
        "What files are in the directory?",
        "Display the contents of this folder",
        "Show the contents of the src directory",
        "List all files in /tmp",
        "Show me the directory structure",
        "List files and folders in current path",
        "What's in this directory?"
    ]
    
    # Test intent detection for read operations
    print("\n===== Testing Read File Intent Detection =====")
    for i, query in enumerate(read_queries, 1):
        intent = os_exec.detect_user_intent(query)
        status = "✓" if intent['type'] == 'filesystem' and intent['operation'] == 'read' else "✗"
        filename = intent.get('filename', 'None') if intent['type'] == 'filesystem' else 'N/A'
        
        print(f"{i}. [{status}] '{query}'")
        print(f"   Intent: {intent['type']} | Operation: {intent.get('operation', 'N/A')} | Filename: {filename}")
        
    # Test intent detection for list operations
    print("\n===== Testing List Directory Intent Detection =====")
    for i, query in enumerate(list_queries, 1):
        intent = os_exec.detect_user_intent(query)
        status = "✓" if intent['type'] == 'filesystem' and intent['operation'] == 'list' else "✗"
        path = intent.get('path', 'None') if intent['type'] == 'filesystem' else 'N/A'
        
        print(f"{i}. [{status}] '{query}'")
        print(f"   Intent: {intent['type']} | Operation: {intent.get('operation', 'N/A')} | Path: {path}")

def test_read_file_operation():
    """Test the read file operation."""
    # Create a test assistant with filesystem operations enabled
    assistant = TextAssistant(config={
        "llm_model": "gemini",  # Use Gemini model or fallback
        "dry_run": False,       # Actually perform the operations
        "os_commands_enabled": True
    })
    
    # Test file path
    test_file = os.path.join(os.getcwd(), "test_file.txt")
    
    # Make sure the test file exists
    if not os.path.exists(test_file):
        with open(test_file, "w") as f:
            f.write("This is a test file content.\nIt has multiple lines.\nEach line has different text.")
    
    # Test read file operation
    print("\n===== Testing Read File Operation =====")
    
    # Process a request to read the test file
    result = assistant.process_input(f"Show me the contents of {os.path.basename(test_file)}")
    
    # Print the result
    print(f"\nUser request: Show me the contents of {os.path.basename(test_file)}")
    
    if result["success"] and result["llm_response"]:
        print(f"\nResponse: {result['llm_response']['response']}")
    else:
        print("\nError: Failed to process the request")
    
    # Print the operation result details
    if result.get("action_result"):
        action_result = result["action_result"]
        print(f"\nOperation status: {action_result['status']}")
        print(f"File path: {action_result.get('file_path', 'N/A')}")
        print(f"File size: {action_result.get('file_size', 'N/A')}")
        print(f"File type: {action_result.get('file_type', 'N/A')}")

def test_list_directory_operation():
    """Test the list directory operation."""
    # Create a test assistant with filesystem operations enabled
    assistant = TextAssistant(config={
        "llm_model": "gemini",  # Use Gemini model or fallback
        "dry_run": False,       # Actually perform the operations
        "os_commands_enabled": True
    })
    
    # Test directory path (current directory)
    test_dir = os.getcwd()
    
    # Test list directory operation
    print("\n===== Testing List Directory Operation =====")
    
    # Process a request to list the current directory
    result = assistant.process_input("List the files in this directory")
    
    # Print the result
    print(f"\nUser request: List the files in this directory")
    
    if result["success"] and result["llm_response"]:
        print(f"\nResponse: {result['llm_response']['response']}")
    else:
        print("\nError: Failed to process the request")
    
    # Print the operation result details
    if result.get("action_result"):
        action_result = result["action_result"]
        print(f"\nOperation status: {action_result['status']}")
        print(f"Directory: {action_result.get('directory', 'N/A')}")
        print(f"Total items: {action_result.get('total_items', 'N/A')}")
        
        # Print file counts
        files = action_result.get('files', [])
        directories = action_result.get('directories', [])
        print(f"Files: {len(files)}")
        print(f"Directories: {len(directories)}")

def simulate_filesystem_conversation():
    """Simulate a conversation about filesystem operations."""
    print("\n===== Simulating Filesystem Operations Conversation =====")
    
    # Create a mock conversation
    conversation = [
        ("user", "What files are in the current directory?"),
        ("assistant", """Contents of /workspaces/codespaces-blank/prototype:

Directories:
- tests/
- output/
- test_scenarios/
- venv/

Files:
- README.md (1345 bytes)
- text_assistant.py (14289 bytes)
- os_exec.py (23567 bytes)
- llm_service.py (8972 bytes)
- utils.py (1038 bytes)
- requirements.txt (89 bytes)
- test_file.txt (47 bytes)
- run_assistant.py (3476 bytes)
- test_os_commands.py (6723 bytes)
- test_filesystem_operations.py (5982 bytes)"""),
        
        ("user", "Show me what's in the test_file.txt"),
        ("assistant", """Here's the content of test_file.txt:

```
This is a test file for the help desk assistant.
```"""),
        
        ("user", "What's in the README.md file?"),
        ("assistant", """Here's the content of README.md:

```
# Help Desk AI Assistant Prototype

This prototype implements a text-based help desk assistant for Raspberry Pi OS that can:
1. Accept user questions via terminal input
2. Process them with an LLM (or simulation)
3. Generate responses and determine OS actions
4. Execute OS actions (in dry-run mode)

## Files and Architecture

### Core Components

- `run_assistant.py` - Main entry point for interactive text assistant. Command-line interface to run and interact with the assistant.
- `text_assistant.py` - Core text assistant implementation. Processes user input, manages conversation state, and coordinates between LLM and OS execution services.
- `voice_assistant.py` - Voice-based assistant that integrates speech transcription, LLM processing, and text-to-speech to provide a voice interface.
- `llm_service.py` - LLM service for processing queries. Supports multiple LLM providers (Llama via Ollama, Claude, and Gemini) with automatic fallback mechanism.
- `os_exec.py` - OS execution service for handling actions. Interprets LLM action directives and executes corresponding OS functions.
- `utils.py` - Utility functions and logging. Provides common functionality used across other modules.

...
```"""),
        
        ("user", "Can you search for any .py files?"),
        ("assistant", """I've searched for .py files in the current directory. Here are the matches:

- /workspaces/codespaces-blank/prototype/text_assistant.py
- /workspaces/codespaces-blank/prototype/os_exec.py
- /workspaces/codespaces-blank/prototype/llm_service.py
- /workspaces/codespaces-blank/prototype/utils.py
- /workspaces/codespaces-blank/prototype/run_assistant.py
- /workspaces/codespaces-blank/prototype/test_os_commands.py
- /workspaces/codespaces-blank/prototype/test_filesystem_operations.py

These are the Python files in the current directory. Would you like me to show the contents of any specific file?"""),
        
        ("user", "Create a new file called notes.txt with some sample text"),
        ("assistant", """I've created a new file called notes.txt with some sample text. The file was created successfully."""),
        
        ("user", "Now show me what's inside the notes.txt file"),
        ("assistant", """Here's the content of notes.txt:

```
This is a sample text file created by the help desk assistant.
It contains some simple text content for testing purposes.
You can edit this file or delete it as needed.
```""")
    ]
    
    # Display the conversation
    for role, content in conversation:
        if role == "user":
            print(f"\nUser: {content}")
        elif role == "assistant":
            print(f"\nAssistant: {content}")
        print("-" * 80)

def main():
    """Run all tests."""
    test_intent_detection()
    test_read_file_operation()
    test_list_directory_operation()
    simulate_filesystem_conversation()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()