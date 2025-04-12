#!/usr/bin/env python3
"""Test file operation detection."""
from file_tools import FileToolFactory, DirectoryLister

def test_directory_detection():
    """Test directory listing detection."""
    print('\nTesting directory listing detection:')
    test_strs = [
        'list the demo_files directory',
        'show files in demo_files',
        'list the files in demo_files directory',
        'what is in the demo_files directory',
        'contents of demo_files',
        'list demo_files'
    ]
    
    for s in test_strs:
        req_type, path = FileToolFactory.detect_request_type(s)
        
        if req_type:
            print(f"  '{s}' → {req_type} operation on '{path}'")
            
            if req_type == 'list':
                lister = DirectoryLister(path)
                resolved = lister.resolve_path(path)
                print(f"    Path resolves to: {resolved}")
                print(f"    Directory exists: {os.path.isdir(resolved)}")
        else:
            print(f"  '{s}' → No detection")

if __name__ == "__main__":
    import os
    # Make sure the demo_files directory exists
    os.makedirs("demo_files", exist_ok=True)
    
    # Run the test
    test_directory_detection()