#!/usr/bin/env python3
"""Test script for the new file tools hierarchy."""
import os
from text_assistant import TextAssistant
from file_tools import FileReader, DirectoryLister, DirectorySearcher, FileToolFactory

def create_test_files():
    """Create some test files and directories."""
    # Create text files
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

def test_file_reader():
    """Test the FileReader tool."""
    print("\n===== Testing FileReader =====")
    
    # Test reading existing files
    test_files = ["test.txt", "hi.txt", "notes.txt", "test_dir/sample.txt"]
    
    for file_path in test_files:
        print(f"\nReading file: {file_path}")
        reader = FileReader(file_path)
        result = reader.read()
        
        if result["status"] == "success":
            print(f"✓ Success: {result['message']}")
            print(f"Content ({result['line_count']} lines):")
            print(f"---\n{result['content']}---")
        else:
            print(f"✗ Error: {result['message']}")
    
    # Test reading non-existent file
    print("\nReading non-existent file: missing.txt")
    reader = FileReader("missing.txt")
    result = reader.read()
    
    if result["status"] == "error":
        print(f"✓ Expected error: {result['message']}")
        if "details" in result and "similar_files" in result["details"]:
            print("Similar files found:")
            for f in result["details"]["similar_files"]:
                print(f"  - {f['name']} (similarity: {f['similarity']*100:.0f}%)")
    else:
        print("✗ Expected an error but got success")

def test_directory_lister():
    """Test the DirectoryLister tool."""
    print("\n===== Testing DirectoryLister =====")
    
    # Test listing existing directories
    test_dirs = [".", "test_dir", "/workspaces/codespaces-blank/prototype"]
    
    for dir_path in test_dirs:
        print(f"\nListing directory: {dir_path}")
        lister = DirectoryLister(dir_path)
        result = lister.list()
        
        if result["status"] == "success":
            print(f"✓ Success: {result['message']}")
            print(f"Found {result['count']} items:")
            
            # Show directories
            dirs = [item for item in result["contents"] if item["is_dir"]]
            if dirs:
                print("Directories:")
                for d in dirs[:3]:  # Show only first 3 for brevity
                    print(f"  - {d['name']}/")
                if len(dirs) > 3:
                    print(f"  ... and {len(dirs) - 3} more")
            
            # Show files
            files = [item for item in result["contents"] if not item["is_dir"]]
            if files:
                print("Files:")
                for f in files[:3]:  # Show only first 3 for brevity
                    print(f"  - {f['name']} ({f['size']} bytes)")
                if len(files) > 3:
                    print(f"  ... and {len(files) - 3} more")
        else:
            print(f"✗ Error: {result['message']}")
    
    # Test listing non-existent directory
    print("\nListing non-existent directory: missing_dir")
    lister = DirectoryLister("missing_dir")
    result = lister.list()
    
    if result["status"] == "error":
        print(f"✓ Expected error: {result['message']}")
    else:
        print("✗ Expected an error but got success")

def test_directory_searcher():
    """Test the DirectorySearcher tool."""
    print("\n===== Testing DirectorySearcher =====")
    
    # Test searching for directories
    test_searches = ["test", "prototype", "codespaces", "missing_dir"]
    
    for search_term in test_searches:
        print(f"\nSearching for directory: {search_term}")
        searcher = DirectorySearcher(search_term)
        result = searcher.search()
        
        if result["status"] == "success":
            print(f"✓ Success: {result['message']}")
            directories = result["directories"]
            
            if directories:
                # Check for exact matches
                exact_matches = [d for d in directories if d.get("is_exact_match", False)]
                if exact_matches:
                    print(f"Exact match: {exact_matches[0]['path']}")
                
                # Show partial matches
                if len(directories) > (1 if exact_matches else 0):
                    print(f"Matches:")
                    for i, d in enumerate(directories[:5]):  # Show only first 5 for brevity
                        if not d.get("is_exact_match", False):
                            print(f"  - {d['path']}")
                    
                    if len(directories) > 5:
                        print(f"  ... and {len(directories) - 5} more")
            else:
                print("No directories found")
        else:
            print(f"✗ Error: {result['message']}")

def test_file_tool_factory():
    """Test the FileToolFactory."""
    print("\n===== Testing FileToolFactory =====")
    
    # Test request type detection
    test_inputs = [
        "read test.txt",
        "show me the content of hi.txt",
        "what's in notes.txt",
        "list the files in test_dir",
        "show files in .",
        "find directory test",
        "search for prototype directory",
        "read me the file test.txt"
    ]
    
    for input_text in test_inputs:
        print(f"\nInput: '{input_text}'")
        request_type, path = FileToolFactory.detect_request_type(input_text)
        
        if request_type and path:
            print(f"✓ Detected: {request_type} operation on '{path}'")
            
            # Create and test the tool
            try:
                tool = FileToolFactory.create_tool(request_type, path)
                print(f"  Created {tool.__class__.__name__}")
                
                # Quick validation
                if request_type == 'read':
                    is_valid, _ = tool.validate()
                    print(f"  Validation: {'Valid' if is_valid else 'Invalid'}")
                elif request_type == 'list':
                    result = tool.list()
                    print(f"  Directory exists: {'Yes' if result['status'] == 'success' else 'No'}")
                elif request_type == 'search':
                    result = tool.search()
                    print(f"  Found {len(result['directories'])} matches")
            except Exception as e:
                print(f"✗ Error creating/using tool: {e}")
        else:
            print(f"✗ Could not detect request type or path")

def test_text_assistant_integration():
    """Test the integration with TextAssistant."""
    print("\n===== Testing TextAssistant Integration =====")
    
    # Create a TextAssistant instance with file tools enabled
    assistant = TextAssistant(config={
        "llm_model": "simulation",  # Use simulation mode to avoid real LLM calls
        "dry_run": False,
        "file_tools_enabled": True
    })
    
    # Test queries that should trigger file operations
    test_queries = [
        "Can you read test.txt",
        "Show me what's in hi.txt",
        "List the files in the test_dir directory",
        "Is there a directory called prototype",
        "Read notes.txt please",
        "What's in that file we just viewed"  # Test follow-up
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        result = assistant.process_input(query)
        
        # Print the response
        if result.get("llm_response"):
            print(f"Response: {result['llm_response']['response']}")
        
        # Check if a file operation was performed
        if result.get("file_operation_performed"):
            operation_result = result.get("file_operation_result", {})
            print(f"✓ File operation performed: {operation_result.get('status')}")
            print(f"  Message: {operation_result.get('message')}")
        else:
            print("✗ No file operation was performed")
        
        print("-" * 50)

def main():
    """Run all tests."""
    # Create test files first
    create_test_files()
    
    # Run tools tests
    test_file_reader()
    test_directory_lister() 
    test_directory_searcher()
    test_file_tool_factory()
    
    # Run integration test
    test_text_assistant_integration()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()