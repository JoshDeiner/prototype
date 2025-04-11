#!/usr/bin/env python3
"""Test script for recursive file search functionality."""
import os
import sys
from file_tools import FileToolFactory, FileSearcher

def test_file_search_detection():
    """Test the detection of file search requests."""
    print("\n===== Testing File Search Detection =====")
    
    test_strs = [
        'find browser_scenario.json',
        'search for file1.txt',
        'locate *.json in test_scenarios',
        'is there a file called browser_scenario.json',
        'where is the browser_scenario.json file',
        'find all .py files',
        'search for any json files',
        'locate configuration file',
    ]
    
    for s in test_strs:
        req_type, path = FileToolFactory.detect_request_type(s)
        print(f"  '{s}' → {req_type} operation for '{path}'" if req_type else f"  '{s}' → No detection")

def test_file_search():
    """Test the file search functionality."""
    print("\n===== Testing File Search Functionality =====")
    
    # Test specific file search
    searcher = FileSearcher("browser_scenario.json")
    results = searcher.search()
    
    print(f"\nSearch for 'browser_scenario.json':")
    print(f"  Status: {results['status']}")
    print(f"  Message: {results['message']}")
    print(f"  Searched paths: {len(results['search_paths'])}")
    
    if results['files']:
        print("\nFiles found:")
        for file in results['files']:
            print(f"  - {file['path']} (Size: {file['size']} bytes)")
    else:
        print("  No files found.")
    
    # Test wildcard pattern search
    searcher = FileSearcher("*.json")
    results = searcher.search(max_results=5)
    
    print(f"\nSearch for '*.json':")
    print(f"  Status: {results['status']}")
    print(f"  Message: {results['message']}")
    
    if results['files']:
        print("\nFiles found (top 5):")
        for file in results['files']:
            print(f"  - {file['path']} (Size: {file['size']} bytes)")
    else:
        print("  No files found.")
    
    # Test search within a specific directory
    prototype_dir = "/workspaces/codespaces-blank/prototype"
    searcher = FileSearcher("*.py")
    results = searcher.search(search_path=prototype_dir, max_results=5)
    
    print(f"\nSearch for '*.py' in {prototype_dir}:")
    print(f"  Status: {results['status']}")
    print(f"  Message: {results['message']}")
    
    if results['files']:
        print("\nFiles found (top 5):")
        for file in results['files']:
            print(f"  - {os.path.basename(file['path'])} (Size: {file['size']} bytes)")
    else:
        print("  No files found.")

def test_integration_with_factory():
    """Test the integration with the FileToolFactory."""
    print("\n===== Testing Integration with FileToolFactory =====")
    
    file_to_find = "browser_scenario.json"
    
    # Detect the request type
    request_type, path = FileToolFactory.detect_request_type(f"find {file_to_find}")
    print(f"Request detection: '{request_type}' operation for '{path}'")
    
    # Create the appropriate tool
    tool = FileToolFactory.create_tool(request_type, path)
    print(f"Created tool: {tool.__class__.__name__}")
    
    # Execute the search
    results = tool.search(max_depth=5)
    
    print(f"\nSearch for '{file_to_find}':")
    print(f"  Status: {results['status']}")
    print(f"  Message: {results['message']}")
    
    if results['files']:
        print("\nFiles found:")
        for file in results['files']:
            print(f"  - {file['path']} (Size: {file['size']} bytes)")
    else:
        print("  No files found.")

def main():
    """Main entry point."""
    # Add parent directory to path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Run tests
    test_file_search_detection()
    test_file_search()
    test_integration_with_factory()

if __name__ == "__main__":
    main()