#!/usr/bin/env python3
"""
Command-line interface for the scene simulator with automatic scene loading and handling.
This provides a streamlined experience for running scenes with less interaction required.
"""
import argparse
import sys
import time
import os
from scene_simulator import SceneSimulator
from utils import ensure_directory, logger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the auto scene simulator."
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["llama", "claude", "gemini", "simulation"],
        default="llama",
        help="LLM model to use (default: llama)"
    )
    parser.add_argument(
        "--scene",
        type=str,
        help="Path to scene file (will use latest from scene-dir if not specified)"
    )
    parser.add_argument(
        "--scene-dir",
        type=str,
        default="scenes",
        help="Directory for scene files (default: scenes)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/scenes",
        help="Directory for saving output (default: output/scenes)"
    )
    parser.add_argument(
        "--auto-save",
        action="store_true",
        help="Automatically save the conversation when complete"
    )
    parser.add_argument(
        "--auto-save-steps",
        type=int,
        default=0,
        help="Automatically save the conversation after this many steps (0 = only at the end)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Disable all conversation saving (won't prompt to save at the end)"
    )
    parser.add_argument(
        "--response-delay",
        type=float,
        default=0.5,
        help="Delay in seconds between client responses (default: 0.5)"
    )
    parser.add_argument(
        "--user-first",
        action="store_true",
        help="Have the user start the conversation instead of the client"
    )
    
    return parser.parse_args()

def find_scene_to_use(scene_dir):
    """Find the scene file to use, prioritizing default scene.
    
    Args:
        scene_dir: Directory to search for scene files
        
    Returns:
        str: Path to the selected scene file, or None if none found
    """
    if not os.path.exists(scene_dir):
        return None
        
    # First check for a default scene
    default_scene = None
    for file in os.listdir(scene_dir):
        if file.startswith('default_') and file.endswith(('.yaml', '.yml', '.json')):
            default_scene = os.path.join(scene_dir, file)
            return default_scene
    
    # If no default scene, find the most recently modified scene
    scene_files = []
    for file in os.listdir(scene_dir):
        if file.endswith(('.yaml', '.yml', '.json')):
            full_path = os.path.join(scene_dir, file)
            scene_files.append((full_path, os.path.getmtime(full_path)))
    
    # Sort by modification time (newest first)
    if scene_files:
        scene_files.sort(key=lambda x: x[1], reverse=True)
        return scene_files[0][0]
    
    return None

def main():
    """Run the auto scene simulator."""
    args = parse_args()
    
    # Handle scene selection
    scene_path = args.scene
    if not scene_path:
        # If no scene specified, try to find a default one or use the most recent one
        scene_path = find_scene_to_use(args.scene_dir)
        if not scene_path:
            print(f"No scene files found in {args.scene_dir}. Creating a sample scene.")
            # Create scene directory if it doesn't exist
            ensure_directory(args.scene_dir)
            # Create a sample scene
            from run_scene_simulator import create_sample_scene
            scene_path = create_sample_scene(args.scene_dir)
    
    print("\n===== Auto Scene Simulator =====")
    
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
    print(f"- Scene: {scene_path}")
    print(f"- Scene Directory: {args.scene_dir}")
    print(f"- Output Directory: {args.output_dir}")
    print(f"- Response Delay: {args.response_delay} seconds")
    auto_save_status = 'Disabled (will prompt at end)'
    if args.no_save:
        auto_save_status = 'Completely disabled (no prompts)'
    elif args.auto_save:
        auto_save_status = 'Enabled (auto-save at end of session)'
    if args.auto_save_steps > 0 and not args.no_save:
        auto_save_status = f'Enabled (every {args.auto_save_steps} steps and at end of session)'
    print(f"- Saving: {auto_save_status}")
    print(f"- First speaker: {'User' if args.user_first else 'Client (LLM)'}")
    
    print()
    
    # Configure the simulator
    config = {
        "llm_model": args.model,
        "scene_dir": args.scene_dir,
        "output_dir": args.output_dir
    }
    
    # Initialize the simulator
    simulator = SceneSimulator(config=config)
    
    # Load the scene
    if not simulator.load_scene(scene_path):
        print(f"Failed to load scene from {scene_path}. Exiting.")
        return
    
    # Run the interactive session with a client-first approach 
    # (unless user-first is specified)
    try:
        # Add a modified interactive session that adds a delay after client responses
        def run_interactive_with_delay():
            # Print scene information
            simulator._print_scene_info()
            
            print("\n===== Auto Scene Simulator =====")
            print("(Type 'exit' to end the session)")
            
            # If client should start the conversation, generate opening message
            if not args.user_first:
                opening_message = simulator.generate_conversation_starter()
                print(f"\nClient: {opening_message}")
                
                # Update conversation history with this first message
                simulator.conversation.append({
                    "user": "[Scene started]",
                    "client": opening_message
                })
            
            # Main interaction loop
            while True:
                # Get user input
                try:
                    user_input = input(f"\n[Step {simulator.step_count+1}/{simulator.scene_constraints.get('max_steps', 20)}] You: ")
                except (EOFError, KeyboardInterrupt):
                    print("\nEnding scene.")
                    break
                
                # Check for exit command
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nEnding scene.")
                    break
                
                # Process the input
                result = simulator.process_user_input(user_input)
                
                if result["success"]:
                    # Add a small delay before showing the response
                    time.sleep(args.response_delay)
                    
                    # Display client response
                    client_response = result['client_response']
                    print(f"\nClient: {client_response}")
                    
                    # Special handling for file operations in the response
                    if "file_check" in client_response or "os_command" in client_response or "tool_code" in client_response:
                        # Extract any commands wrapped in tool_code blocks
                        if "```tool_code" in client_response and "```" in client_response.split("```tool_code")[1]:
                            tool_code = client_response.split("```tool_code")[1].split("```")[0].strip()
                            if "cat" in tool_code:
                                # Extract filename
                                filename = tool_code.replace("cat", "").strip()
                                if os.path.exists(filename):
                                    # Show file contents
                                    try:
                                        with open(filename, 'r') as f:
                                            content = f.read()
                                        print(f"\n[File contents of {filename}]:\n{content}")
                                    except Exception as e:
                                        print(f"\n[Error reading file: {e}]")
                    
                    # Check if we should auto-save after N steps
                    if not args.no_save and args.auto_save_steps > 0 and simulator.step_count > 0 and simulator.step_count % args.auto_save_steps == 0:
                        saved_path = simulator.save_conversation()
                        if saved_path:
                            print(f"\n[Auto-saved conversation to: {saved_path}]")
                    
                    # Check if scene has ended
                    if result["scene_ended"]:
                        print("\nScene has reached its maximum steps. Ending scene.")
                        break
                else:
                    print(f"\nError: {result.get('error', 'Unknown error')}")
                    if result.get("scene_ended", False):
                        print("Scene has ended.")
                        break
                        
        # Run our modified interactive session
        run_interactive_with_delay()
    
    except Exception as e:
        print(f"Error during execution: {e}")
    
    # Handle conversation saving
    if simulator.conversation and not args.no_save:
        # Auto-save if enabled
        if args.auto_save:
            try:
                saved_path = simulator.save_conversation()
                if saved_path:
                    print(f"\nConversation auto-saved to: {saved_path}")
                else:
                    print("\nFailed to auto-save conversation.")
            except Exception as save_error:
                print(f"\nError during auto-save: {save_error}")
        # Otherwise offer to save
        else:
            try:
                save_option = input("\nWould you like to save this conversation? (yes/no): ")
                if save_option.lower() in ['yes', 'y']:
                    saved_path = simulator.save_conversation()
                    if saved_path:
                        print(f"Conversation saved to: {saved_path}")
                    else:
                        print("Failed to save conversation.")
            except (EOFError, KeyboardInterrupt):
                # If there's an input error, auto-save as a fallback
                print("\nInput error detected. Auto-saving conversation...")
                saved_path = simulator.save_conversation()
                if saved_path:
                    print(f"Conversation auto-saved to: {saved_path}")
                else:
                    print("Failed to auto-save conversation.")
    
    print("\nThank you for using the Auto Scene Simulator!")

if __name__ == "__main__":
    main()