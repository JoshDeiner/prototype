#!/usr/bin/env python3
"""
Run the integrated file assistant with the new stateful controller architecture.
This implements the updated architecture with LLM and OS modes, with scene support.
"""
import os
import argparse
import time
from utils import logger
from file_assistant_middleware import StatefulController

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the integrated file assistant with the new stateful controller architecture."
    )
    
    # Model selection
    parser.add_argument(
        "--model", 
        type=str, 
        choices=["llama", "claude", "gemini", "simulation"],
        default="llama",
        help="LLM model to use (default: llama)"
    )
    
    # Scene management
    parser.add_argument(
        "--scene", 
        type=str,
        help="Path to a scene file to use"
    )
    parser.add_argument(
        "--list-scenes", 
        action="store_true",
        help="List available scenes and exit"
    )
    
    # OS execution options
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Don't actually execute OS commands (simulate only)"
    )
    parser.add_argument(
        "--unsafe", 
        action="store_true",
        help="Disable safety checks on OS commands (use with caution!)"
    )
    
    # Confirmation behavior
    parser.add_argument(
        "--manual-confirm", 
        action="store_true",
        help="Require manual confirmation for actions"
    )
    parser.add_argument(
        "--delay", 
        type=float, 
        default=0.5,
        help="Delay in seconds before auto-executing actions (default: 0.5)"
    )
    
    # Conversation history
    parser.add_argument(
        "--max-history", 
        type=int, 
        default=5,
        help="Maximum number of conversation turns to remember (default: 5)"
    )
    parser.add_argument(
        "--max-retries", 
        type=int, 
        default=3,
        help="Maximum number of LLM retries for invalid actions (default: 3)"
    )
    parser.add_argument(
        "--max-steps", 
        type=int, 
        default=20,
        help="Maximum number of conversation steps before automatically ending (default: 20, 0 for unlimited)"
    )
    
    return parser.parse_args()

def list_available_scenes():
    """List all available scene files in the scenes directory."""
    scene_dir = "scenes"
    
    if not os.path.exists(scene_dir) or not os.path.isdir(scene_dir):
        print("Scenes directory not found.")
        return []
        
    scenes = []
    
    for file in os.listdir(scene_dir):
        if file.endswith(('.yaml', '.yml', '.json')):
            scene_path = os.path.join(scene_dir, file)
            
            # Try to extract the name from the file
            try:
                import yaml
                with open(scene_path, 'r') as f:
                    scene_data = yaml.safe_load(f)
                    name = scene_data.get('name', file)
            except:
                name = file
            
            scenes.append((file, name))
            
    return scenes

def main():
    """Run the integrated file assistant."""
    args = parse_args()
    
    # Check if we should just list scenes and exit
    if args.list_scenes:
        print("\n===== Available Scenes =====")
        scenes = list_available_scenes()
        
        if not scenes:
            print("No scene files found.")
        else:
            for i, (filename, name) in enumerate(scenes, 1):
                print(f"{i}. {filename} - {name}")
                
        return
    
    # Configure the controller
    config = {
        "llm_model": args.model,
        "dry_run": args.dry_run,
        "safe_mode": not args.unsafe,
        "auto_confirm": not args.manual_confirm,
        "delay": args.delay,
        "scene_path": args.scene,
        "max_history": args.max_history,
        "max_retries": args.max_retries,
        "max_steps": args.max_steps
    }
    
    # Initialize the controller
    try:
        controller = StatefulController(config=config)
    except Exception as e:
        print(f"Error initializing controller: {e}")
        return
    
    # Print configuration
    print("\n===== Integrated File Assistant =====")
    print("Configuration:")
    print(f"- Model: {args.model}")
    if args.scene:
        print(f"- Scene: {args.scene}")
    print(f"- Execution mode: {'Dry run' if args.dry_run else 'Live (will execute commands)'}")
    print(f"- Safety checks: {'Disabled (UNSAFE)' if args.unsafe else 'Enabled'}")
    print(f"- Confirmation: {'Manual' if args.manual_confirm else 'Automatic'}")
    print(f"- History size: {args.max_history} turns")
    print(f"- Max retries: {args.max_retries}")
    if args.max_steps > 0:
        print(f"- Max steps: {args.max_steps}")
    else:
        print("- Max steps: Unlimited")
    print()
    
    # Generate opening message if using a scene
    opening_message = controller.get_opening_message()
    if opening_message:
        print(f"Assistant: {opening_message}")
    
    # Main interaction loop
    print("(Type 'exit' to end the session)")
    
    # Initialize step counter
    step_count = 0
    max_steps = args.max_steps
    
    try:
        while True:
            # Check if we've reached the maximum steps
            if max_steps > 0 and step_count >= max_steps:
                print(f"\nReached maximum number of steps ({max_steps}). Ending session.")
                break
                
            # Get user input with mode indicator and step count
            mode_indicator = "[LLM Mode]" if controller.current_mode == "LLM" else "[OS Mode]"
            step_indicator = f"[Step {step_count+1}/{max_steps}]" if max_steps > 0 else f"[Step {step_count+1}]"
            user_input = input(f"\n{step_indicator} {mode_indicator} You: ")
            
            # Check for exit command
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nEnding session.")
                break
                
            # Increment step counter
            step_count += 1
            
            # Process the input
            result = controller.process_input(user_input)
            
            if result["success"]:
                # Display response if available
                if "response" in result and result["response"]:
                    print(f"\nAssistant: {result['response']}")
                
                # If in OS mode with pending action
                if controller.current_mode == "OS" and controller.pending_action:
                    action = controller.pending_action
                    action_type = action.get("type", "unknown")
                    
                    if action_type == "os_command":
                        print(f"\n[OS Mode] Will execute command: {action.get('command', '')}")
                    elif action_type == "launch_app":
                        print(f"\n[OS Mode] Will launch application: {action.get('app_name', '')}")
                    
                    # Delay before auto-confirming
                    if not args.manual_confirm and args.delay > 0:
                        print(f"Auto-executing in {args.delay} seconds...")
                        time.sleep(args.delay)
                        
                        # Auto-confirm
                        result = controller.process_input("yes")
                        
                        # Show action result
                        if "action_result" in result and result["action_result"]:
                            action_result = result["action_result"]
                            
                            if "stdout" in action_result and action_result["stdout"].strip():
                                print(f"\nOutput:\n{action_result['stdout'].strip()}")
                                
                            if "stderr" in action_result and action_result["stderr"].strip():
                                print(f"\nErrors/Warnings:\n{action_result['stderr'].strip()}")
                    else:
                        print("Type 'yes' to confirm, or any other input to cancel")
                
                # Show action result if present (for direct or chained actions)
                if "action_result" in result and result["action_result"]:
                    action_result = result["action_result"]
                    
                    # For chained actions, make it clear that this was executed automatically
                    if not result.get("mode_switched", False) and controller.current_mode == "LLM":
                        print("\n[Automatic Action Completed]")
                        
                    if "stdout" in action_result and action_result["stdout"].strip():
                        print(f"\nOutput:\n{action_result['stdout'].strip()}")
                        
                    if "stderr" in action_result and action_result["stderr"].strip():
                        print(f"\nErrors/Warnings:\n{action_result['stderr'].strip()}")
                    
                    # If this was a file check that failed, offer to create the file
                    if action_result.get("status") == "error" and "file not found" in action_result.get("message", "").lower():
                        filename = action_result.get("command", "").split()[-1] if "command" in action_result else ""
                        if filename:
                            print(f"\nThe file '{filename}' doesn't exist. You can create it with a text editor.")
            else:
                # Display error
                print(f"\nError: {result.get('error', 'Unknown error')}")
                
                # If max retries reached, notify user
                if result.get("max_retries_reached", False):
                    print(f"\nMaximum retries ({args.max_retries}) reached.")
                    
    except KeyboardInterrupt:
        print("\nSession interrupted.")
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\nThank you for using the Integrated File Assistant!")

if __name__ == "__main__":
    main()