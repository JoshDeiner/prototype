#!/usr/bin/env python3
"""
Command-line interface for the scene simulator.
"""
import argparse
import sys
import os
from scene_simulator import SceneSimulator
from utils import ensure_directory

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the scene simulator."
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
        help="Path to scene file"
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create a sample scene file"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum number of conversation steps (default: 20)"
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
    
    return parser.parse_args()

def create_sample_scene(scene_dir):
    """Create a sample scene file.
    
    Args:
        scene_dir: Directory to create the sample in
    
    Returns:
        str: Path to the created sample
    """
    # Ensure directory exists
    ensure_directory(scene_dir)
    
    # Help desk scenario
    help_desk_scenario = {
        "name": "Tech Support Call",
        "roles": {
            "user": "You are a technical support representative for a large tech company. You are patient, knowledgeable about computers and software, and committed to helping customers solve their problems.",
            "client": "You are a customer having problems with your computer. You're frustrated because your computer keeps freezing, especially when you try to use specific applications."
        },
        "scene": "A customer has called the tech support hotline with a computer problem. The tech support representative needs to identify the issue and provide a solution. The customer is moderately tech-savvy but frustrated.",
        "constraints": {
            "max_steps": 20,
            "style": "The tech support rep should be professional but empathetic. The customer starts frustrated but can be calmed with good support."
        }
    }
    
    # Create the file
    import yaml
    sample_path = os.path.join(scene_dir, "help_desk_scenario.yaml")
    with open(sample_path, 'w') as f:
        yaml.dump(help_desk_scenario, f, default_flow_style=False, sort_keys=False)
    
    print(f"Created sample scene at: {sample_path}")
    return sample_path

def main():
    """Run the scene simulator."""
    args = parse_args()
    
    # Create sample scene if requested
    if args.create_sample:
        sample_path = create_sample_scene(args.scene_dir)
        if args.scene is None:
            args.scene = sample_path
    
    print("\n===== Scene Simulator =====")
    
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
    print(f"- Max Steps: {args.max_steps}")
    print(f"- Scene Directory: {args.scene_dir}")
    print(f"- Output Directory: {args.output_dir}")
    print(f"- Scene File: {args.scene if args.scene else 'To be selected'}")
    
    print()
    
    # Configure the simulator
    config = {
        "llm_model": args.model,
        "max_steps": args.max_steps,
        "scene_dir": args.scene_dir,
        "output_dir": args.output_dir
    }
    
    # Initialize the simulator
    simulator = SceneSimulator(config=config)
    
    # Start interactive session
    try:
        simulator.interactive_session(scene_path=args.scene)
    except KeyboardInterrupt:
        print("\nSession terminated by user.")
    except EOFError:
        print("\nInput stream closed.")
    
    print("\nThank you for using the Scene Simulator!")

if __name__ == "__main__":
    main()