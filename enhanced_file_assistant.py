#!/usr/bin/env python3
"""
Enhanced file assistant that integrates the scene-based system with the state machine architecture.
This combines our file assistant middleware with the TextAssistant's state machine.
"""
import os
import sys
import re
import time
import argparse
from text_assistant import TextAssistant
from llm_service import LLMService
from scene_simulator import SceneSimulator
from os_exec import OSExecutionService

class EnhancedFileMiddleware:
    """
    Enhanced middleware that processes LLM responses from the scene simulator,
    extracts file operation requests, and helps transition to OS mode.
    """
    
    def __init__(self, text_assistant):
        """Initialize the middleware with a TextAssistant instance.
        
        Args:
            text_assistant: An instance of TextAssistant
        """
        self.text_assistant = text_assistant
        self.os_exec = text_assistant.os_exec_service
        
        # Extract filenames from responses
        self.filename_pattern = r"(?:['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*)"
        
        # Patterns for detecting file operations
        self.file_read_patterns = [
            r"show you what's in ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)",
            r"show you the contents of ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)",
            r"open ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)",
            r"read ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)",
            r"contents of ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)"
        ]
        
        self.file_list_patterns = [
            r"list the files in the current directory",
            r"list files in ([a-zA-Z0-9_\-\.\/~]+)"
        ]
        
        self.file_check_patterns = [
            r"check if ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+) exists"
        ]
    
    def process_response(self, client_response):
        """Process an LLM response to detect file operations and integrate with state machine.
        
        Args:
            client_response: The LLM's response text
            
        Returns:
            dict: Results indicating if a file operation was detected
        """
        # Skip processing if response is JSON or code block formatted
        if "```" in client_response or "{" in client_response and "}" in client_response:
            return {
                "action_detected": False,
                "message": "Response format not suitable for middleware processing"
            }
        
        # Check file reading patterns
        for pattern in self.file_read_patterns:
            match = re.search(pattern, client_response.lower())
            if match:
                file_path = match.group(1)
                return self._create_read_action(file_path)
        
        # Check directory listing patterns
        if "list the files in the current directory" in client_response.lower():
            return self._create_list_action(".")
            
        # Check for directory list with path
        for pattern in self.file_list_patterns:
            if pattern != "list the files in the current directory":  # Skip the one we already checked
                match = re.search(pattern, client_response.lower())
                if match and len(match.groups()) > 0:
                    dir_path = match.group(1)
                    return self._create_list_action(dir_path)
        
        # Check file check patterns
        for pattern in self.file_check_patterns:
            match = re.search(pattern, client_response.lower())
            if match:
                file_path = match.group(1)
                return self._create_check_action(file_path)
                
        # Final attempt - see if there's a filename mentioned
        if any(phrase in client_response.lower() for phrase in ["show", "read", "content", "what's in", "open"]):
            match = re.search(self.filename_pattern, client_response)
            if match:
                file_path = match.group(1)
                return self._create_read_action(file_path)
        
        # No file operation detected
        return {
            "action_detected": False,
            "message": "No file operation detected in response"
        }
    
    def _create_read_action(self, file_path):
        """Create an OS command action to read a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            dict: Action information for state machine
        """
        # Create the action
        action = {
            "type": "os_command",
            "command": f"cat {file_path}"
        }
        
        # Set up the state machine transition
        self.text_assistant.pending_action = action
        self.text_assistant.current_mode = "OS"
        
        return {
            "action_detected": True,
            "action_type": "read",
            "file_path": file_path,
            "action": action,
            "mode_switched": True
        }
    
    def _create_list_action(self, dir_path):
        """Create an OS command action to list directory contents.
        
        Args:
            dir_path: Path to the directory to list
            
        Returns:
            dict: Action information for state machine
        """
        # Create the action
        action = {
            "type": "os_command",
            "command": f"ls -la {dir_path}"
        }
        
        # Set up the state machine transition
        self.text_assistant.pending_action = action
        self.text_assistant.current_mode = "OS"
        
        return {
            "action_detected": True,
            "action_type": "list",
            "dir_path": dir_path,
            "action": action,
            "mode_switched": True
        }
    
    def _create_check_action(self, file_path):
        """Create a file check action.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            dict: Action information for state machine
        """
        # Create the action
        action = {
            "type": "file_check",
            "file_path": file_path
        }
        
        # This stays in LLM mode
        return {
            "action_detected": True,
            "action_type": "check",
            "file_path": file_path,
            "action": action,
            "mode_switched": False
        }

class EnhancedFileAssistant:
    """
    Enhanced assistant that integrates the scene simulator with the TextAssistant state machine.
    """
    
    def __init__(self, config=None):
        """Initialize the enhanced file assistant.
        
        Args:
            config: Configuration dictionary
        """
        # Default configuration
        self.config = {
            "llm_model": "llama",
            "dry_run": False,
            "auto_confirm": True,
            "delay": 0.5
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Initialize the TextAssistant for state machine
        assistant_config = {
            "llm_model": self.config["llm_model"],
            "dry_run": self.config["dry_run"],
            "safe_mode": True,
            "os_commands_enabled": True,
            "file_tools_enabled": True
        }
        self.text_assistant = TextAssistant(config=assistant_config)
        
        # Initialize the scene simulator for LLM guidance
        simulator_config = {
            "llm_model": self.config["llm_model"]
        }
        self.scene_simulator = SceneSimulator(config=simulator_config)
        
        # Set default scene path
        self.scene_path = self.config.get("scene_path", os.path.join("scenes", "filesystem_assistant.yaml"))
        
        # If the specified scene doesn't exist, look for it in the scenes directory
        if not os.path.exists(self.scene_path) and not os.path.isabs(self.scene_path):
            alternate_path = os.path.join("scenes", self.scene_path)
            if os.path.exists(alternate_path):
                self.scene_path = alternate_path
                
        # If still not found and it's just a filename, try to find it
        if not os.path.exists(self.scene_path) and os.path.basename(self.scene_path) == self.scene_path:
            # Try to find any file with this name in scenes directory
            for file in os.listdir("scenes"):
                if file == self.scene_path or file == f"{self.scene_path}.yaml" or file == f"{self.scene_path}.yml":
                    self.scene_path = os.path.join("scenes", file)
                    break
        
        # Final validation
        if not os.path.exists(self.scene_path):
            raise FileNotFoundError(f"Scene file not found: {self.scene_path}")
            
        if not self.scene_simulator.load_scene(self.scene_path):
            raise ValueError(f"Failed to load scene: {self.scene_path}")
        
        # Initialize the middleware
        self.middleware = EnhancedFileMiddleware(self.text_assistant)
    
    def run_interactive_session(self):
        """Run an interactive session with the enhanced file assistant."""
        print("\n===== Enhanced File Assistant =====")
        print("(Type 'exit' to end the session)")
        
        # Print scene information
        self.scene_simulator._print_scene_info()
        
        # Generate opening message from the client
        opening_message = self.scene_simulator.generate_conversation_starter()
        print(f"\nClient: {opening_message}")
        
        # Update conversation history with this first message
        self.scene_simulator.conversation.append({
            "user": "[Scene started]",
            "client": opening_message
        })
        
        # Main interaction loop
        try:
            while True:
                # Get user input
                mode_indicator = "[LLM Mode]" if self.text_assistant.current_mode == "LLM" else "[OS Mode]"
                try:
                    user_input = input(f"\n{mode_indicator} [Step {self.scene_simulator.step_count+1}/{self.scene_simulator.scene_constraints.get('max_steps', 20)}] You: ")
                except (EOFError, KeyboardInterrupt):
                    print("\nEnding assistant session.")
                    break
                    
                # Check for exit command
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nEnding assistant session.")
                    break
                
                # Process based on current mode
                if self.text_assistant.current_mode == "LLM":
                    # Process through scene simulator to get LLM guidance
                    scene_result = self.scene_simulator.process_user_input(user_input)
                    
                    if scene_result["success"]:
                        client_response = scene_result["client_response"]
                        print(f"\nClient: {client_response}")
                        
                        # Process the response through middleware
                        middleware_result = self.middleware.process_response(client_response)
                        
                        # If a file operation was detected and mode was switched
                        if middleware_result.get("action_detected", False) and middleware_result.get("mode_switched", False):
                            # We're now in OS mode, display the pending action
                            action = middleware_result.get("action")
                            action_type = action.get("type")
                            
                            print(f"\n[OS Mode] Action detected: {action_type}")
                            if action_type == "os_command":
                                print(f"Command: {action['command']}")
                            
                            # Auto-confirm if configured
                            if self.config["auto_confirm"]:
                                if self.config["delay"] > 0:
                                    print(f"Auto-executing in {self.config['delay']} seconds...")
                                    time.sleep(self.config["delay"])
                                print("Executing action automatically...")
                                
                                # Process the confirmation through the TextAssistant
                                confirmation_result = self.text_assistant.process_input("yes")
                                
                                # Display the results
                                if confirmation_result.get("action_result"):
                                    action_result = confirmation_result["action_result"]
                                    print(f"\nResult: {action_result.get('message', 'Completed')}")
                                    
                                    # Display command output if any
                                    if "stdout" in action_result and action_result["stdout"].strip():
                                        print(f"\nOutput:\n{action_result['stdout']}")
                                        
                                    # Display errors if any
                                    if "stderr" in action_result and action_result["stderr"].strip():
                                        print(f"\nErrors/Warnings:\n{action_result['stderr']}")
                        
                        # If file_check was processed, display the results
                        elif middleware_result.get("action_detected", False) and middleware_result.get("action_type") == "check":
                            action = middleware_result.get("action")
                            
                            # Process the file check through TextAssistant
                            file_check_result = self.text_assistant._process_file_check(action)
                            
                            if file_check_result:
                                print("\n[File Check Result]")
                                if file_check_result.get("file_exists", False):
                                    print(f"✓ File exists: {file_check_result.get('file_path')}")
                                    
                                    file_info = file_check_result.get("file_info", {})
                                    print(f"  Type: {file_info.get('file_type', 'unknown')}")
                                    print(f"  Size: {file_info.get('size', 0)} bytes")
                                else:
                                    print(f"✗ File not found: {file_check_result.get('searched_path')}")
                    else:
                        print(f"\nError: {scene_result.get('error', 'Unknown error')}")
                else:  # OS Mode
                    # Process through TextAssistant directly
                    result = self.text_assistant.process_input(user_input)
                    
                    if result["success"]:
                        if "llm_response" in result and result["llm_response"]:
                            print(f"\nAssistant: {result['llm_response']['response']}")
                            
                        # Display action results if any
                        if result.get("action_result"):
                            action_result = result["action_result"]
                            print(f"\nResult: {action_result.get('message', 'Completed')}")
                            
                            # Display command output if any
                            if "stdout" in action_result and action_result["stdout"].strip():
                                print(f"\nOutput:\n{action_result['stdout']}")
                                
                            # Display errors if any
                            if "stderr" in action_result and action_result["stderr"].strip():
                                print(f"\nErrors/Warnings:\n{action_result['stderr']}")
                    else:
                        print(f"\nError: {result.get('error', 'Unknown error')}")
                
                # Check if scene has ended
                if self.scene_simulator.step_count >= self.scene_simulator.scene_constraints.get("max_steps", 20):
                    print("\nScene has reached its maximum steps. Ending session.")
                    break
                
        except Exception as e:
            print(f"\nAn error occurred: {e}")
        
        print("\nThank you for using the Enhanced File Assistant!")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the enhanced file assistant."
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
        default="filesystem_assistant.yaml",
        help="Scene file to use (default: filesystem_assistant.yaml)"
    )
    parser.add_argument(
        "--list-scenes",
        action="store_true",
        help="List available scenes and exit"
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
            scenes.append(file)
            
    return scenes

def main():
    """Run the enhanced file assistant."""
    args = parse_args()
    
    # Check if we should just list scenes and exit
    if args.list_scenes:
        print("\n===== Available Scenes =====")
        scenes = list_available_scenes()
        if not scenes:
            print("No scene files found.")
        else:
            for i, scene in enumerate(scenes, 1):
                scene_path = os.path.join("scenes", scene)
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
    config = {
        "llm_model": args.model,
        "dry_run": args.dry_run,
        "auto_confirm": not args.manual_confirm,
        "delay": args.delay,
        "scene_path": args.scene
    }
    
    # Print configuration
    print("\n===== Enhanced File Assistant =====")
    print("Configuration:")
    print(f"- Model: {args.model}")
    print(f"- Scene: {args.scene}")
    print(f"- Execution mode: {'Dry run' if args.dry_run else 'Live (will execute commands)'}")
    print(f"- Confirmation: {'Manual' if args.manual_confirm else 'Automatic'}")
    print(f"- Auto-confirmation delay: {args.delay} seconds")
    print()
    
    try:
        # Initialize and run the assistant
        assistant = EnhancedFileAssistant(config=config)
        assistant.run_interactive_session()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Use --list-scenes to see available scenes.")
    except Exception as e:
        print(f"Error initializing assistant: {e}")

if __name__ == "__main__":
    main()