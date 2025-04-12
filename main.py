#!/usr/bin/env python3
"""
Main entry point for the Voice Assistant.

This routes user input to the appropriate controller based on configuration.
"""

import os
import sys
import argparse
from controller.wrapper import Wrapper
import config as app_config

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the voice assistant."
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
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds before auto-executing actions (default: 0.5)"
    )
    parser.add_argument(
        "--manual-confirm",
        action="store_true",
        help="Require manual confirmation for actions (default: auto-confirm)"
    )
    parser.add_argument(
        "--scene",
        type=str,
        help="Scene file to use (optional)"
    )
    parser.add_argument(
        "--list-scenes",
        action="store_true",
        help="List available scenes and exit"
    )
    parser.add_argument(
        "--max-history",
        type=int,
        default=5,
        help="Maximum number of conversation turns to remember (default: 5)"
    )
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="Disable safety checks for OS commands (use with caution!)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing data files (default: data)"
    )
    return parser.parse_args()

def list_available_scenes():
    """List all available scene files in the scenes directory."""
    if not os.path.exists(app_config.SCENES_DIR) or not os.path.isdir(app_config.SCENES_DIR):
        print("Scenes directory not found.")
        return []
        
    scenes = []
    for file in os.listdir(app_config.SCENES_DIR):
        if file.endswith(('.yaml', '.yml', '.json')):
            scenes.append(file)
            
    return scenes

def main():
    """Run the voice assistant."""
    args = parse_args()
    
    # Check if we should just list scenes and exit
    if args.list_scenes:
        print("\n===== Available Scenes =====")
        scenes = list_available_scenes()
        if not scenes:
            print("No scene files found.")
        else:
            for i, scene in enumerate(scenes, 1):
                scene_path = os.path.join(app_config.SCENES_DIR, scene)
                # Try to extract the name from the file
                try:
                    with open(scene_path, 'r') as f:
                        first_line = f.readline().strip()
                        name = first_line.split("name:", 1)[1].strip().strip('"\'') if "name:" in first_line else scene
                except:
                    name = scene
                    
                print(f"{i}. {scene} - {name}")
        return
    
    # Configure the assistant
    user_config = {
        "llm_model": args.model,
        "dry_run": args.dry_run,
        "safe_mode": not args.unsafe,
        "auto_confirm": not args.manual_confirm,
        "delay": args.delay,
        "scene_path": args.scene,
        "max_history": args.max_history,
        "data_dir": args.data_dir
    }
    
    # Print configuration
    print("\n===== Voice Assistant =====")
    print("Configuration:")
    print(f"- Model: {args.model}")
    if args.scene:
        print(f"- Scene: {args.scene}")
    print(f"- Data directory: {args.data_dir}")
    print(f"- Execution mode: {'Dry run' if args.dry_run else 'Live (will execute commands)'}")
    print(f"- Safety checks: {'Disabled (UNSAFE)' if args.unsafe else 'Enabled'}")
    print(f"- Confirmation: {'Manual' if args.manual_confirm else 'Automatic'}")
    print(f"- Auto-confirmation delay: {args.delay} seconds")
    print(f"- History size: {args.max_history} turns")
    print()
    
    try:
        # Initialize and run the assistant
        assistant = Wrapper(config=user_config)
        assistant.run_interactive_session()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Use --list-scenes to see available scenes.")
    except Exception as e:
        print(f"Error initializing assistant: {e}")

if __name__ == "__main__":
    main()