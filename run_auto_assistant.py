#!/usr/bin/env python3
"""
Command-line interface for the text-based assistant with automatic OS execution.
This version automatically confirms and executes actions without user intervention.
"""
import argparse
import sys
import time
from text_assistant import TextAssistant

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the auto-confirming text assistant."
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["llama", "claude", "gemini", "simulation"],
        default="llama",
        help="LLM model to use (default: llama)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually execute commands (simulate only)"
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        default=True,
        help="Apply safety checks on OS commands"
    )
    parser.add_argument(
        "--conversation-turns",
        type=int,
        default=5,
        help="Maximum number of conversation turns to remember"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds before auto-executing actions (default: 1.0)"
    )
    parser.add_argument(
        "--file-tools",
        action="store_true",
        default=True,
        help="Enable direct file operations with the file tools hierarchy"
    )
    return parser.parse_args()

def auto_interactive_session(assistant, delay=1.0):
    """Start an interactive terminal session that auto-confirms actions.
    
    Args:
        assistant: The TextAssistant instance
        delay: Delay in seconds before auto-executing actions
    """
    print("\n===== Auto-Executing Text Assistant =====")
    print("(Type 'exit' to end the session)")
    print("WARNING: This assistant automatically executes OS commands!")
    
    while True:
        # Indicate current mode
        mode_indicator = "[LLM Mode]" if assistant.current_mode == "LLM" else "[OS Mode - Auto-confirmation]"
        
        # Get user input
        user_input = input(f"\n{mode_indicator} You: ")
        
        # Check for exit command
        if user_input.lower() in ['exit', 'quit', 'bye'] and assistant.current_mode == "LLM":
            print("\nAssistant: Goodbye!")
            break
            
        # Process the input
        start_time = time.time()
        result = assistant.process_input(user_input)
        processing_time = time.time() - start_time
        
        if result["success"] and "llm_response" in result and result["llm_response"]:
            # Display LLM response
            print(f"\nAssistant: {result['llm_response']['response']}")
            
            # Display direct file operation results (from new file tools system)
            if result.get("file_operation_performed"):
                print("\n[File Operation Result]")
                op_result = result.get("file_operation_result", {})
                op_type = op_result.get("status", "unknown")
                
                if op_type == "success":
                    # For file reading
                    if "content" in op_result:
                        print(f"✓ Successfully read file: {op_result.get('file_path')}")
                        if op_result.get("line_count"):
                            print(f"  Lines: {op_result.get('line_count')} of {op_result.get('total_lines', 'unknown')}")
                    
                    # For directory listing
                    elif "contents" in op_result:
                        print(f"✓ Successfully listed directory: {op_result.get('dir_path')}")
                        print(f"  Items: {op_result.get('count')} files/directories")
                    
                    # For directory searching
                    elif "directories" in op_result:
                        print(f"✓ Found {len(op_result.get('directories', []))} directories matching '{op_result.get('searched_for')}'")
                else:
                    print(f"✗ Operation failed: {op_result.get('message', 'Unknown error')}")
                
                # Record what resource was last accessed for follow-up questions
                if assistant.last_file_processed:
                    print(f"  Last accessed: {assistant.last_file_processed}")
            
            # Display special action results for file_check and dir_search (legacy methods)
            if result.get("file_check_performed"):
                print("\n[File Check Result]")
                file_result = result.get("file_check_result", {})
                if file_result.get("file_exists", False):
                    print(f"✓ File exists: {file_result.get('file_path')}")
                    
                    # Get file info - either from new or old format
                    file_info = file_result.get("file_info", {})
                    if not file_info:
                        # For compatibility with older format
                        file_info = {
                            "size": file_result.get("size", 0),
                            "file_type": file_result.get("file_type", "unknown")
                        }
                    
                    # Display size
                    size = file_info.get("size", 0)
                    if size > 1024*1024:
                        size_str = f"{size/(1024*1024):.2f} MB"
                    elif size > 1024:
                        size_str = f"{size/1024:.2f} KB"
                    else:
                        size_str = f"{size} bytes"
                    print(f"  Size: {size_str}")
                    
                    # Display type
                    print(f"  Type: {file_info.get('file_type', 'unknown')}")
                    
                    # Display line count if available
                    if "line_count" in file_info:
                        print(f"  Lines: {file_info['line_count']}")
                        
                    # Indicate if empty
                    if file_info.get("is_empty", size == 0):
                        print(f"  Note: File is empty")
                elif file_result.get("is_directory", False):
                    print(f"! Path exists but is a directory: {file_result.get('path')}")
                else:
                    print(f"✗ File not found: {file_result.get('searched_path')}")
                    if file_result.get("similar_files"):
                        print("  Similar files found:")
                        for f in file_result.get("similar_files", [])[:3]:
                            print(f"  - {f.get('name')} (similarity: {f.get('similarity', 0)*100:.0f}%)")
            
            if result.get("dir_search_performed"):
                print("\n[Directory Search Result]")
                dir_result = result.get("dir_search_result", {})
                directories = dir_result.get("directories", [])
                if directories:
                    print(f"Found {len(directories)} potential matches:")
                    for i, d in enumerate(directories[:5]):
                        match_type = "Exact match" if d.get("is_exact_match", False) else "Partial match"
                        print(f"  {i+1}. [{match_type}] {d.get('path')}")
                else:
                    print(f"No directories found matching '{dir_result.get('searched_for', '')}'")
            
            # If we just switched to OS mode, auto-confirm after a short delay
            if result.get("mode_switched") and assistant.current_mode == "OS":
                action = result.get("pending_action")
                
                # Display the detected action
                print(f"\n[OS Mode] Action detected: {action['type']}")
                if action['type'] == "os_command":
                    print(f"Command: {action['command']}")
                elif action['type'] == "launch_app":
                    print(f"Application: {action['app_name']}")
                
                # Auto-confirm after delay
                print(f"Auto-executing in {delay} seconds...")
                time.sleep(delay)  # Wait for specified delay
                print("Executing action automatically...")
                
                # Send automatic confirmation
                confirmation_result = assistant.process_input("yes")
                
                # Display the result
                if confirmation_result.get("action_result"):
                    action_result = confirmation_result["action_result"]
                    print(f"\nResult: {action_result.get('message', 'Completed')}")
                    
                    # Display command output if any
                    if "stdout" in action_result and action_result["stdout"].strip():
                        print(f"\nOutput:\n{action_result['stdout']}")
                        
                    # Display errors if any
                    if "stderr" in action_result and action_result["stderr"].strip():
                        print(f"\nErrors/Warnings:\n{action_result['stderr']}")
            
            # Show action results from previous turns if available
            action_result = result.get("action_result")
            if action_result and action_result.get("status") == "success":
                print(f"\nAction result: {action_result.get('message', 'Completed')}")
                
                if "stdout" in action_result and action_result["stdout"].strip():
                    print(f"\nOutput:\n{action_result['stdout']}")
                    
                # If there are errors/warnings
                if "stderr" in action_result and action_result["stderr"].strip():
                    print(f"\nErrors/Warnings:\n{action_result['stderr']}")
            
            # Log processing time
            print(f"\n[Processing time: {processing_time:.2f} seconds]")
        else:
            print("\nAssistant: Sorry, I encountered an error processing your request.")

def main():
    """Run the auto-confirming text assistant."""
    args = parse_args()
    
    print("\n===== Auto-Executing Text Assistant =====")
    print("This assistant automatically executes actions without confirmation")
    print("Type 'exit' to end the session\n")
    
    # Print configuration information
    print("Configuration:")
    
    # Display model information
    model_info = {
        "llama": "Llama (via Ollama) - Install Ollama locally with 'ollama serve'",
        "claude": "Claude - Requires CLAUDE_API_KEY environment variable",
        "gemini": "Gemini - Requires GEMINI_API_KEY environment variable",
        "simulation": "Simulation mode (no real LLM connected)"
    }
    print(f"- Model: {model_info.get(args.model, args.model)}")
    print(f"- Execution mode: {'Dry run' if args.dry_run else 'Live (will execute commands)'}")
    print(f"- Safety checks: {'Enabled' if args.safe_mode else 'Disabled (DANGEROUS)'}")
    print(f"- Auto-confirmation delay: {args.delay} seconds")
    print(f"- File operations: {'Direct with file tools hierarchy' if args.file_tools else 'Via LLM and OS commands'}")
    print(f"- File validation: Enabled")
    print(f"- Directory search: Enabled")
    
    print()
    
    # Configure the text assistant
    config = {
        "llm_model": args.model,
        "dry_run": args.dry_run,
        "safe_mode": args.safe_mode,
        "os_commands_enabled": True,  # Always enable OS commands
        "file_tools_enabled": args.file_tools,  # Enable file tools based on argument
        "conversation_turns": args.conversation_turns
    }
    
    # Initialize the assistant
    assistant = TextAssistant(config=config)
    
    # Start auto-interactive session
    try:
        auto_interactive_session(assistant, delay=args.delay)
    except KeyboardInterrupt:
        print("\nSession terminated by user.")
    except EOFError:
        print("\nInput stream closed.")
    
    print("\nThank you for using the Auto-Executing Text Assistant!")

if __name__ == "__main__":
    main()