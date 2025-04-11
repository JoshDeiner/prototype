#!/usr/bin/env python3
"""Demo script to demonstrate the new file tools system."""
import os
import sys
from text_assistant import TextAssistant
from file_tools import FileToolFactory
from utils import logger

def create_demo_files():
    """Create some demo files for testing."""
    # Create a sample text file
    with open("sample.txt", "w") as f:
        f.write("This is a sample text file.\n")
        f.write("It has multiple lines of content.\n")
        f.write("This is line 3.\n")
        f.write("And this is line 4.\n")
    
    # Create a Python file
    with open("example.py", "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("\"\"\"Example Python file for demo.\"\"\"\n\n")
        f.write("def hello_world():\n")
        f.write("    \"\"\"Print hello world message.\"\"\"\n")
        f.write("    print(\"Hello, world!\")\n\n")
        f.write("if __name__ == \"__main__\":\n")
        f.write("    hello_world()\n")
    
    # Create a demo directory with files
    os.makedirs("demo_files", exist_ok=True)
    with open("demo_files/file1.txt", "w") as f:
        f.write("This is file 1 in the demo_files directory.\n")
    with open("demo_files/file2.txt", "w") as f:
        f.write("This is file 2 in the demo_files directory.\n")

def run_demo():
    """Run the file tools demo."""
    # Create the assistant
    assistant = TextAssistant(config={
        "dry_run": False,
        "file_tools_enabled": True
    })
    
    print("\n===== File Operations Tools Demo =====")
    print("This demo shows how file operations are handled without requiring editor selection.")
    print("Type 'exit' to end the demo.\n")
    
    # Suggested commands to try
    print("Suggested commands to try:")
    print("  - read sample.txt")
    print("  - show me example.py")
    print("  - list the files in demo_files")
    print("  - is there a directory called demo_files")
    print("  - what does the file say")
    print("  - show me the content of file1.txt in demo_files")
    print("  - what's in file2.txt\n")
    
    # Start interactive loop
    while True:
        # Get user input
        user_input = input("\n> ")
        
        # Check for exit
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Exiting demo. Goodbye!")
            break
            
        # Check for help
        if user_input.lower() in ['help', '?']:
            print("\nHere are some example commands you can try:")
            print("  - read sample.txt")
            print("  - show me the content of example.py")
            print("  - list files in demo_files directory")
            print("  - find directory called demo_files")
            print("  - what's in file1.txt in the demo_files directory")
            continue
            
        # Process the input
        print("\nProcessing: " + user_input)
        
        # First, try direct file operation detection
        request_type, path = FileToolFactory.detect_request_type(user_input)
        if request_type:
            print(f"Detected file operation: {request_type} operation on '{path}'")
        
        # Process with assistant
        result = assistant.process_input(user_input)
        
        # Display results
        if result.get("file_operation_performed"):
            print("\nFile operation was handled directly:")
            op_result = result.get("file_operation_result", {})
            print(f"  - Operation: {op_result.get('status', 'unknown')}")
            print(f"  - Path: {op_result.get('file_path', op_result.get('dir_path', 'unknown'))}")
            
            # Remember the file for follow-up questions
            if assistant.last_file_processed:
                print(f"  - Remembering file: {os.path.basename(assistant.last_file_processed)}")
        
        # Show LLM response
        if result.get("llm_response"):
            print("\nResponse:")
            print(result["llm_response"]["response"])
        
        # Show if we're in OS mode waiting for confirmation
        if assistant.current_mode == "OS" and result.get("pending_action"):
            action = result.get("pending_action")
            print("\nWaiting for confirmation to execute:")
            print(f"  - Action type: {action.get('type')}")
            if action.get('type') == 'os_command':
                print(f"  - Command: {action.get('command')}")
            elif action.get('type') == 'launch_app':
                print(f"  - Application: {action.get('app_name')}")
                
            # For demo purposes, auto-confirm simple safe commands
            if action.get('type') == 'os_command' and action.get('command', '').startswith(('ls', 'cat')):
                print("\nAuto-confirming safe command...")
                confirm_result = assistant.process_input("yes")
                
                # Show action result
                if confirm_result.get("action_result"):
                    action_result = confirm_result["action_result"]
                    print(f"\nResult: {action_result.get('message', '')}")
                    
                    if "stdout" in action_result and action_result["stdout"].strip():
                        print(f"\nOutput:\n{action_result['stdout']}")
                        
                    if "stderr" in action_result and action_result["stderr"].strip():
                        print(f"\nErrors:\n{action_result['stderr']}")

def main():
    """Main function."""
    # Create demo files
    create_demo_files()
    
    try:
        # Run the demo
        run_demo()
    except KeyboardInterrupt:
        print("\nDemo interrupted. Exiting.")
    except Exception as e:
        print(f"\nError in demo: {e}")
    finally:
        print("\nThank you for trying the file tools demo!")

if __name__ == "__main__":
    main()