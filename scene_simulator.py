"""Scene simulator for role-playing conversations."""
import os
import yaml
import json
import random
from utils import logger, ensure_directory
from llm_service import LLMService

class SceneSimulator:
    """
    Simulates conversational scenes between a user and an LLM-powered client.
    Scenes are defined by configuration files (YAML/JSON) specifying:
    - Roles (user, client)
    - Scene context
    - Constraints (e.g., max conversation steps)
    """
    def __init__(self, config=None):
        """Initialize the scene simulator.
        
        Args:
            config: Configuration dictionary for simulator options
        """
        # Set default configuration
        self.config = {
            "llm_model": "llama",
            "output_dir": "output/scenes",
            "scene_dir": "scenes",
            "max_steps": 20  # Default max steps if not specified in scene
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
            
        # Ensure directories exist
        ensure_directory(self.config["output_dir"])
        ensure_directory(self.config["scene_dir"])
        
        # Initialize LLM service
        self.llm_service = LLMService(
            model_type=self.config["llm_model"]
        )
        
        # Initialize state
        self.current_scene = None
        self.conversation = []
        self.step_count = 0
        self.scene_constraints = {}
        
        logger.info("Scene simulator initialized")
    
    def load_scene(self, scene_path):
        """Load a scene definition from a configuration file.
        
        Args:
            scene_path: Path to the scene configuration file (YAML or JSON)
            
        Returns:
            bool: True if scene loaded successfully, False otherwise
        """
        if not os.path.exists(scene_path):
            logger.error(f"Scene file not found: {scene_path}")
            return False
        
        try:
            # Determine file type by extension
            _, ext = os.path.splitext(scene_path)
            
            if ext.lower() in ['.yaml', '.yml']:
                with open(scene_path, 'r') as f:
                    scene_config = yaml.safe_load(f)
            elif ext.lower() == '.json':
                with open(scene_path, 'r') as f:
                    scene_config = json.load(f)
            else:
                logger.error(f"Unsupported scene file format: {ext}")
                return False
            
            # Validate the scene configuration
            if not self._validate_scene_config(scene_config):
                logger.error(f"Invalid scene configuration in {scene_path}")
                return False
            
            # Set the current scene
            self.current_scene = scene_config
            
            # Reset conversation
            self.conversation = []
            self.step_count = 0
            
            # Extract scene constraints
            self.scene_constraints = scene_config.get("constraints", {})
            if "max_steps" not in self.scene_constraints:
                self.scene_constraints["max_steps"] = self.config["max_steps"]
            
            logger.info(f"Loaded scene from {scene_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading scene: {e}")
            return False
    
    def _validate_scene_config(self, config):
        """Validate scene configuration.
        
        Args:
            config: Scene configuration dictionary
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check for required fields
        required_fields = ["roles", "scene", "name"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required field in scene configuration: {field}")
                return False
        
        # Check roles (must have user and client)
        roles = config.get("roles", {})
        if "user" not in roles or "client" not in roles:
            logger.error("Scene must define both 'user' and 'client' roles")
            return False
        
        # Validate scene description
        if not isinstance(config.get("scene", ""), str):
            logger.error("Scene description must be a string")
            return False
        
        return True
    
    def generate_client_prompt(self, user_input):
        """Generate a prompt for the client LLM based on current scene.
        
        Args:
            user_input: The user's latest input
            
        Returns:
            str: Formatted prompt for the LLM
        """
        if not self.current_scene:
            logger.error("No scene loaded")
            return None
        
        # Extract scene components
        roles = self.current_scene["roles"]
        scene_description = self.current_scene["scene"]
        constraints = self.scene_constraints
        
        # Build the prompt components
        prompt_parts = [
            "You will role-play according to the following guidelines:",
            f"## Your Role\n{roles['client']}",
            f"## User's Role\n{roles['user']}",
            f"## Scene\n{scene_description}",
            "## Conversation History"
        ]
        
        # Add conversation history
        for turn in self.conversation:
            prompt_parts.append(f"User: {turn['user']}")
            prompt_parts.append(f"You: {turn['client']}")
        
        # Add constraints
        prompt_parts.append("## Constraints")
        remaining_steps = constraints.get("max_steps", 20) - self.step_count
        prompt_parts.append(f"This conversation must resolve within {remaining_steps} more turns.")
        if remaining_steps <= 3:
            prompt_parts.append("The conversation is nearing its end. Work toward a conclusion.")
        
        # Add current user input
        prompt_parts.append(f"## Current User Input\n{user_input}")
        
        # Add response instruction
        prompt_parts.append("## Instructions\nRespond in-character based on the scene description.")
        
        # Join all parts with double newlines for clear separation
        return "\n\n".join(prompt_parts)
    
    def process_user_input(self, user_input):
        """Process user input and generate client response.
        
        Args:
            user_input: User's text input
            
        Returns:
            dict: Results from processing the input
        """
        if not self.current_scene:
            return {
                "success": False,
                "error": "No scene loaded",
                "scene_ended": False
            }
        
        # Check if we've reached the max steps
        if self.step_count >= self.scene_constraints.get("max_steps", 20):
            return {
                "success": False,
                "error": "Maximum conversation steps reached",
                "scene_ended": True
            }
        
        # Generate client prompt
        client_prompt = self.generate_client_prompt(user_input)
        
        # Get client response from LLM
        llm_result = self.llm_service.process_raw_prompt(client_prompt)
        
        if not llm_result or "response" not in llm_result:
            return {
                "success": False,
                "error": "Failed to generate client response",
                "scene_ended": False
            }
        
        client_response = llm_result["response"]
        
        # Update conversation history
        self.conversation.append({
            "user": user_input,
            "client": client_response
        })
        
        # Increment step count
        self.step_count += 1
        
        # Check if we've reached the end
        scene_ended = self.step_count >= self.scene_constraints.get("max_steps", 20)
        
        # Return results
        return {
            "success": True,
            "client_response": client_response,
            "step_count": self.step_count,
            "max_steps": self.scene_constraints.get("max_steps", 20),
            "scene_ended": scene_ended
        }
    
    def save_conversation(self, filename=None):
        """Save the current conversation to a file.
        
        Args:
            filename: Optional filename to save to
            
        Returns:
            str: Path to the saved file
        """
        if not self.current_scene or not self.conversation:
            logger.error("No conversation to save")
            return None
        
        # Generate filename if not provided
        if not filename:
            scene_name = self.current_scene.get("name", "unnamed_scene")
            filename = f"{scene_name}_{self.step_count}_steps.json"
        
        # Ensure it has a .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Full path
        file_path = os.path.join(self.config["output_dir"], filename)
        
        # Prepare data for saving
        save_data = {
            "scene_name": self.current_scene.get("name", "Unnamed Scene"),
            "scene_description": self.current_scene.get("scene", ""),
            "roles": self.current_scene.get("roles", {}),
            "constraints": self.scene_constraints,
            "steps": self.step_count,
            "conversation": self.conversation
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            logger.info(f"Saved conversation to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return None
    
    def generate_conversation_starter(self):
        """Generate an initial prompt from the client to start the conversation.
        
        Returns:
            str: The client's opening message
        """
        if not self.current_scene:
            logger.error("No scene loaded")
            return None
        
        # Extract scene components
        roles = self.current_scene["roles"]
        scene_description = self.current_scene["scene"]
        
        # Build the prompt for conversation starter
        prompt = (
            "You will role-play according to the following guidelines:\n\n"
            f"## Your Role\n{roles['client']}\n\n"
            f"## User's Role\n{roles['user']}\n\n"
            f"## Scene\n{scene_description}\n\n"
            "## Instructions\n"
            "Generate an opening message to start this conversation. "
            "This should be your first line as the client, initiating the interaction "
            "with the user based on the scene description. "
            "Stay completely in character."
        )
        
        # Get client response from LLM
        result = self.llm_service.process_raw_prompt(prompt)
        
        if not result or "response" not in result:
            return "Hello, I need your assistance today."
        
        return result["response"]
    
    def interactive_session(self, scene_path=None, client_first=True):
        """Start an interactive scene simulation session.
        
        Args:
            scene_path: Optional path to scene file to load
            client_first: Whether the client (LLM) should start the conversation
        """
        # Load scene if provided
        if scene_path:
            if not self.load_scene(scene_path):
                print("\nFailed to load scene. Exiting.")
                return
        
        # If no scene is loaded, prompt for one
        if not self.current_scene:
            scene_files = self._list_available_scenes()
            if not scene_files:
                print("\nNo scene files found in the scenes directory.")
                return
            
            print("\n=== Available Scenes ===")
            for i, scene_file in enumerate(scene_files):
                print(f"{i+1}. {os.path.basename(scene_file)}")
            
            try:
                choice = int(input("\nSelect a scene (number): "))
                if choice < 1 or choice > len(scene_files):
                    print("Invalid selection.")
                    return
                
                if not self.load_scene(scene_files[choice-1]):
                    print("\nFailed to load scene. Exiting.")
                    return
            except ValueError:
                print("Invalid input. Please enter a number.")
                return
        
        # Print scene information
        self._print_scene_info()
        
        print("\n===== Scene Simulator =====")
        print("(Type 'exit' to end the session)")
        
        # If client should start the conversation, generate opening message
        if client_first:
            opening_message = self.generate_conversation_starter()
            print(f"\nClient: {opening_message}")
            
            # Update conversation history with this first message
            self.conversation.append({
                "user": "[Scene started]",
                "client": opening_message
            })
        
        # Main interaction loop
        while True:
            # Get user input
            user_input = input(f"\n[Step {self.step_count+1}/{self.scene_constraints.get('max_steps', 20)}] You: ")
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\nEnding scene.")
                break
            
            # Process the input
            result = self.process_user_input(user_input)
            
            if result["success"]:
                # Display client response
                print(f"\nClient: {result['client_response']}")
                
                # Check if scene has ended
                if result["scene_ended"]:
                    print("\nScene has reached its maximum steps. Ending scene.")
                    break
            else:
                print(f"\nError: {result.get('error', 'Unknown error')}")
                if result.get("scene_ended", False):
                    print("Scene has ended.")
                    break
        
        # Offer to save the conversation
        if self.conversation:
            save_option = input("\nWould you like to save this conversation? (yes/no): ")
            if save_option.lower() in ['yes', 'y']:
                saved_path = self.save_conversation()
                if saved_path:
                    print(f"Conversation saved to: {saved_path}")
                else:
                    print("Failed to save conversation.")
        
        print("\nThank you for using the Scene Simulator!")
    
    def _list_available_scenes(self):
        """List available scene files in the scenes directory.
        
        Returns:
            list: Paths to available scene files
        """
        scene_dir = self.config["scene_dir"]
        if not os.path.exists(scene_dir):
            return []
        
        scene_files = []
        default_scene = None
        
        for file in os.listdir(scene_dir):
            if file.endswith(('.yaml', '.yml', '.json')):
                scene_path = os.path.join(scene_dir, file)
                scene_files.append(scene_path)
                
                # Check if this is the default scene
                if file.startswith('default_'):
                    default_scene = scene_path
        
        # If we found a default scene, move it to the front of the list
        if default_scene and len(scene_files) > 1:
            scene_files.remove(default_scene)
            scene_files.insert(0, default_scene)
        
        return scene_files
    
    def _print_scene_info(self):
        """Print information about the current scene."""
        if not self.current_scene:
            print("No scene loaded.")
            return
        
        print("\n=== Scene Information ===")
        print(f"Name: {self.current_scene.get('name', 'Unnamed Scene')}")
        print(f"Max Steps: {self.scene_constraints.get('max_steps', 20)}")
        print("\nRoles:")
        print(f"- User: {self.current_scene['roles']['user']}")
        print(f"- Client: {self.current_scene['roles']['client']}")
        print(f"\nScene Description:\n{self.current_scene['scene']}")
        print("\n========================")


def main():
    """Run the scene simulator as a standalone program."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the scene simulator.")
    parser.add_argument("--model", type=str, choices=["llama", "claude", "gemini"], 
                      default="llama", help="LLM model to use")
    parser.add_argument("--scene", type=str, help="Path to scene file")
    
    args = parser.parse_args()
    
    # Configure the simulator
    config = {
        "llm_model": args.model
    }
    
    # Initialize the simulator
    simulator = SceneSimulator(config=config)
    
    # Start interactive session
    simulator.interactive_session(scene_path=args.scene)


if __name__ == "__main__":
    main()