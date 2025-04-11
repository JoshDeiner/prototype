#!/usr/bin/env python3
"""Script to run the File Assistant Scene."""
import os
import sys
from scene_simulator import SceneSimulator

def main():
    """Run the File Assistant Scene with the specified LLM model."""
    # Set default model or use command-line arg
    model = "llama"  # default
    if len(sys.argv) > 1:
        model = sys.argv[1]
        
    # Check if the scene file exists
    scene_path = os.path.join("scenes", "filesystem_assistant.yaml")
    if not os.path.exists(scene_path):
        print(f"Error: Scene file not found at {scene_path}")
        return
        
    # Configure the simulator with the specified model
    config = {
        "llm_model": model
    }
    
    # Initialize and run the scene simulator
    simulator = SceneSimulator(config=config)
    simulator.interactive_session(scene_path=scene_path)

if __name__ == "__main__":
    main()