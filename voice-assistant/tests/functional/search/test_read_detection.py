#!/usr/bin/env python3
"""Test improved file reading detection."""
from file_tools import FileToolFactory

def test_file_read_detection():
    """Test the detection of file reading requests."""
    print('\nTesting file reading detection:')
    test_strs = [
        'read sample.txt',
        'show me example.py',
        "what's in notes.txt",
        'what is in hi.txt',
        'show the content of test.txt',
        'display file.txt',
        'open README.md',
        'file.txt'
    ]
    
    for s in test_strs:
        req_type, path = FileToolFactory.detect_request_type(s)
        print(f"  '{s}' → {req_type} operation on '{path}'" if req_type else f"  '{s}' → No detection")

if __name__ == "__main__":
    test_file_read_detection()