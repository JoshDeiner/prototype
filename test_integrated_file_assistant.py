#!/usr/bin/env python3
"""
Test script for the integrated file assistant solution.
"""
import os
import time
from scene_simulator import SceneSimulator
from file_assistant_middleware import FileAssistantMiddleware

def test_integrated_file_assistant():
    """Test the integrated file assistant with predefined commands."""
    print("\n===== Testing Integrated File Assistant =====\n")
    
    # Initialize the middleware
    middleware = FileAssistantMiddleware(dry_run=False)
    
    # Configure and initialize the scene simulator
    config = {
        "llm_model": "gemini"  # Use Gemini for tests as it's likely available
    }
    simulator = SceneSimulator(config=config)
    
    # Load the filesystem assistant scene
    scene_path = os.path.join("scenes", "filesystem_assistant.yaml")
    if not os.path.exists(scene_path) or not simulator.load_scene(scene_path):
        print(f"Error: Could not load scene file from {scene_path}")
        return
    
    # Test cases - predefined user inputs
    test_cases = [
        "Can you show me what's in hi.txt?",
        "Read the contents of sample.txt for me",
        "List all files in the current directory",
        "Check if test_file.txt exists",
        "Is there a directory called test_dir?"
    ]
    
    # Run through the test cases
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n----- Test #{i}: '{user_input}' -----\n")
        
        # Process the input through the scene simulator
        result = simulator.process_user_input(user_input)
        
        if result["success"]:
            # Display the client's response
            client_response = result["client_response"] 
            print(f"Client: {client_response}")
            
            # Process the response through the middleware
            print("\n[Middleware processing...]")
            middleware_result = middleware.process_response(client_response)
            
            # Display middleware results
            print(f"Action detected: {middleware_result.get('action_detected', False)}")
            if middleware_result.get("action_detected", False):
                print(f"Action type: {middleware_result.get('action_type', 'unknown')}")
                print(f"Success: {middleware_result.get('success', False)}")
                
                # Show content based on action type
                if middleware_result.get("action_type") == "read" and middleware_result.get("success", False):
                    content = middleware_result.get("content", "")
                    if len(content) > 300:
                        content = content[:300] + "...[truncated]"
                    print(f"\n[File Contents]:\n{content}")
                    
                elif middleware_result.get("action_type") == "list" and middleware_result.get("success", False):
                    content = middleware_result.get("content", "")
                    if len(content) > 300:
                        content = content[:300] + "...[truncated]"
                    print(f"\n[Directory Contents]:\n{content}")
                    
                elif middleware_result.get("action_type") == "check":
                    print(f"\n[File Check]: {middleware_result.get('message', '')}")
                
                # Show errors if any
                if not middleware_result.get("success", False) or middleware_result.get("error"):
                    print(f"\n[Error]: {middleware_result.get('error', 'Unknown error')}")
            else:
                print(f"Message: {middleware_result.get('message', '')}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            
        print("\n" + "-" * 60)
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_integrated_file_assistant()