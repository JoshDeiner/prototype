#!/usr/bin/env python3
"""
Unified Assistant implementing the updated architecture pattern.
This strictly follows the Text-Based LLM to OS Execution Flow with a state machine.
"""
import os
import sys
import time
import json
import argparse
import re
from utils import logger, ensure_directory
from llm_service import LLMService
from os_exec import OSExecutionService

class UnifiedAssistant:
    """
    Unified Assistant with a stateful controller implementing two operational modes:
    - LLM Mode (understanding & planning)
    - OS Mode (executing validated system actions)
    
    This follows the Wrapper Controller pattern that manages transitions
    between modes and handles both scene-based and direct interactions.
    """
    
    def __init__(self, config=None):
        """Initialize the unified assistant.
        
        Args:
            config: Configuration dictionary
        """
        # Set default configuration
        self.config = {
            "llm_model": "llama",
            "dry_run": False,
            "safe_mode": True,
            "auto_confirm": True,
            "delay": 0.5,
            "scene_path": None,
            "max_history": 5,
            "data_dir": "data"
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Initialize LLM service
        self.llm_service = LLMService(
            model_type=self.config["llm_model"]
        )
        
        # Initialize OS execution service
        self.os_exec_service = OSExecutionService(
            dry_run=self.config["dry_run"],
            safe_mode=self.config["safe_mode"]
        )
        
        # Initialize state
        self.current_mode = "LLM"  # Start in LLM mode
        self.pending_action = None
        self.context = []
        self.last_user_input = None
        self.last_llm_response = None
        self.last_action_result = None
        self.last_file_processed = None
        
        # Load scene if provided
        self.scene_context = None
        if self.config["scene_path"]:
            self.scene_context = self._load_scene(self.config["scene_path"])
            
        logger.info(f"Unified Assistant initialized in {self.current_mode} mode")
        logger.info(f"Scene {'loaded' if self.scene_context else 'not loaded'}")
    
    def _load_scene(self, scene_path):
        """Load a scene from a file.
        
        Args:
            scene_path: Path to the scene file
            
        Returns:
            dict: Scene context if loading successful, None otherwise
        """
        # Check if scene_path is just a filename (no path separators)
        if os.path.basename(scene_path) == scene_path:
            # Look in scenes directory
            alt_path = os.path.join("scenes", scene_path)
            if os.path.exists(alt_path):
                scene_path = alt_path
            # Try with extensions if not found
            elif not os.path.exists(scene_path):
                for ext in [".yaml", ".yml", ".json"]:
                    test_path = os.path.join("scenes", f"{scene_path}{ext}")
                    if os.path.exists(test_path):
                        scene_path = test_path
                        break
        
        # Check if file exists
        if not os.path.exists(scene_path):
            logger.error(f"Scene file not found: {scene_path}")
            return None
            
        try:
            # Determine file type by extension
            _, ext = os.path.splitext(scene_path)
            
            # Load based on file type
            if ext.lower() in ['.yaml', '.yml']:
                import yaml
                with open(scene_path, 'r') as f:
                    scene_data = yaml.safe_load(f)
            elif ext.lower() == '.json':
                import json
                with open(scene_path, 'r') as f:
                    scene_data = json.load(f)
            else:
                logger.error(f"Unsupported scene file format: {ext}")
                return None
                
            logger.info(f"Successfully loaded scene from {scene_path}")
            return scene_data
        except Exception as e:
            logger.error(f"Error loading scene: {e}")
            return None
    
    def process_input(self, user_input):
        """Process user input based on current mode.
        
        Args:
            user_input: User text input
            
        Returns:
            dict: Results from processing
        """
        # Store the user input for reference
        self.last_user_input = user_input
        
        # Initialize results structure
        results = {
            "success": False,
            "current_mode": self.current_mode,
            "mode_switched": False,
            "llm_response": None,
            "pending_action": None,
            "action_result": None
        }
        
        # Process based on current mode
        if self.current_mode == "LLM":
            logger.info("Processing input in LLM mode")
            results = self._process_in_llm_mode(user_input, results)
        elif self.current_mode == "OS":
            logger.info("Processing input in OS mode")
            results = self._process_in_os_mode(user_input, results)
        
        # Update results with current mode
        results["current_mode"] = self.current_mode
        
        return results
    
    def _process_in_llm_mode(self, user_input, results):
        """Process input in LLM mode.
        
        Args:
            user_input: User text input
            results: Current results dictionary
            
        Returns:
            dict: Updated results
        """
        # Format prompt with scene context if available
        prompt = self._format_prompt_with_scene(user_input)
        
        # Process through LLM service
        llm_result = self.llm_service.process_raw_prompt(prompt)
        
        if not llm_result or "response" not in llm_result:
            logger.error("Failed to get valid response from LLM")
            results["error"] = "Failed to get valid response from LLM"
            return results
            
        # Extract response
        llm_response = llm_result.get("response", "")
        results["llm_response"] = {"response": llm_response}
        self.last_llm_response = llm_response
        
        # Try to extract action from response (may be in JSON format)
        action = self._extract_action_from_response(llm_response)
        
        # If action detected, validate and process
        if action:
            logger.info(f"Extracted action: {action}")
            
            # Validate action using OS execution service
            is_valid, validation_reason = self.os_exec_service.validate_action(action)
            
            if is_valid:
                logger.info(f"Valid action detected: {action['type']}")
                
                # Check for special action types that remain in LLM mode
                if action["type"] in ["clarify", "explain", "explain_download", "none"]:
                    logger.info(f"Action {action['type']} doesn't require mode switch")
                    # No mode switch needed
                elif action["type"] == "file_check":
                    logger.info(f"File check requested: {action.get('file_path', '')}")
                    # Process file check within LLM mode
                    check_result = self._process_file_check(action)
                    results["file_check_result"] = check_result
                    results["file_check_performed"] = True
                elif action["type"] == "dir_search":
                    logger.info(f"Directory search requested: {action.get('dir_name', '')}")
                    # Process directory search within LLM mode
                    search_result = self._process_dir_search(action)
                    results["dir_search_result"] = search_result
                    results["dir_search_performed"] = True
                else:
                    # For other action types, switch to OS mode
                    self.pending_action = action
                    self.current_mode = "OS"
                    results["mode_switched"] = True
                    results["pending_action"] = action
            else:
                logger.warning(f"Invalid action detected: {validation_reason}")
                results["action_validation_error"] = validation_reason
        
        # If no action detected or validation failed, stay in LLM mode
        
        # Update context history
        self._update_context(user_input, llm_response)
        
        results["success"] = True
        return results
    
    def _process_in_os_mode(self, user_input, results):
        """Process input in OS mode.
        
        Args:
            user_input: User text input (should be confirmation)
            results: Current results dictionary
            
        Returns:
            dict: Updated results
        """
        # Check if we have a pending action
        if not self.pending_action:
            logger.error("No pending action in OS mode")
            results["error"] = "No pending action in OS mode"
            # Switch back to LLM mode
            self.current_mode = "LLM"
            return results
            
        # Check if input is a confirmation
        is_confirmation = self._is_confirmation(user_input)
        
        if not is_confirmation:
            # Not a confirmation, switch back to LLM mode
            self.current_mode = "LLM"
            # Reprocess the input in LLM mode
            return self._process_in_llm_mode(user_input, results)
            
        # It's a confirmation, execute the pending action
        logger.info(f"Executing action: {self.pending_action['type']}")
        action_result = self.os_exec_service.execute_action(self.pending_action)
        
        # Process special results for file operations
        if self.pending_action["type"] == "os_command":
            command = self.pending_action.get("command", "")
            # Check if this is a file-related command
            if command.startswith("cat ") and len(command.split()) > 1:
                # Extract filename
                filename = command.split()[1]
                self.last_file_processed = filename
        
        # Store the action result
        results["action_result"] = action_result
        self.last_action_result = action_result
        
        # Switch back to LLM mode
        self.current_mode = "LLM"
        results["mode_switched"] = True
        
        # Clear pending action
        self.pending_action = None
        
        results["success"] = True
        return results
    
    def _format_prompt_with_scene(self, user_input):
        """Format the prompt with scene context if available.
        
        Args:
            user_input: User text input
            
        Returns:
            str: Formatted prompt
        """
        if not self.scene_context:
            # No scene, use direct prompt
            return user_input
            
        # Extract scene components
        roles = self.scene_context.get("roles", {})
        scene_description = self.scene_context.get("scene", "")
        
        # Build prompt with scene context
        prompt_parts = [
            "You will role-play according to the following guidelines:",
            f"## Your Role\n{roles.get('client', 'Assistant')}",
            f"## User's Role\n{roles.get('user', 'Human')}",
            f"## Scene\n{scene_description}",
            "## Conversation History"
        ]
        
        # Add conversation history
        for entry in self.context:
            prompt_parts.append(f"User: {entry['user']}")
            prompt_parts.append(f"You: {entry['assistant']}")
        
        # Add current user input
        prompt_parts.append(f"## Current User Input\n{user_input}")
        
        # Add response instruction
        prompt_parts.append("## Instructions\nRespond in-character based on the scene description.")
        
        # Join all parts with double newlines for clear separation
        return "\n\n".join(prompt_parts)
    
    def _extract_action_from_response(self, response_text):
        """Extract action from LLM response.
        
        Args:
            response_text: LLM response text
            
        Returns:
            dict or None: Action dictionary if found, None otherwise
        """
        # Check if response contains JSON block
        json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', response_text)
        if json_match:
            try:
                json_str = json_match.group(1)
                json_data = json.loads(json_str)
                
                # Extract action if present
                if isinstance(json_data, dict) and "action" in json_data:
                    return json_data["action"]
            except json.JSONDecodeError:
                pass
                
        # Check for file operations using regex patterns
        # File read patterns
        read_patterns = [
            r"show you what's in ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)",
            r"show you the contents of ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)",
            r"read ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)",
            r"open ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)"
        ]
        
        for pattern in read_patterns:
            match = re.search(pattern, response_text.lower())
            if match:
                file_path = match.group(1)
                return self._create_file_read_action(file_path)
                
        # Directory listing patterns
        if "list the files in the current directory" in response_text.lower():
            return {
                "type": "os_command",
                "command": "ls -la"
            }
            
        # File check patterns
        check_patterns = [
            r"check if ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+) exists"
        ]
        
        for pattern in check_patterns:
            match = re.search(pattern, response_text.lower())
            if match:
                file_path = match.group(1)
                return {
                    "type": "file_check",
                    "file_path": file_path
                }
        
        # Check the last_user_input for direct file references
        if self.last_user_input:
            # Looking for patterns like "what does X.txt say" or "show me X.txt"
            file_patterns = [
                r"what(?:'s| is) in ([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)",
                r"what does ([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+) say",
                r"show me ([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)",
                r"contents of ([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)",
                r"read ([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)",
                r"open ([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)",
                r"([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)"  # Direct filename mention
            ]
            
            user_input_lower = self.last_user_input.lower()
            for pattern in file_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    file_path = match.group(1)
                    logger.info(f"Detected file reference in user input: {file_path}")
                    return self._create_file_read_action(file_path)
                
        # No action detected
        return None
        
    def _create_file_read_action(self, file_path):
        """Create a file read action with proper path resolution.
        
        Args:
            file_path: The file path to read
            
        Returns:
            dict: A structured action for reading the file
        """
        # Check if file_path has a directory component, if not, look in data directory
        if os.path.dirname(file_path) == "":
            # First try the configured data directory
            data_dir = os.path.join(os.getcwd(), self.config["data_dir"])
            if os.path.exists(data_dir) and os.path.isdir(data_dir):
                full_path = os.path.join(data_dir, file_path)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    logger.info(f"Found file in data directory: {full_path}")
                    return {
                        "type": "os_command",
                        "command": f"cat {full_path}"
                    }
                
            # Also check if we were told the file is in the data directory by the user
            if self.last_user_input and "data directory" in self.last_user_input.lower():
                # Force the path to be in the data directory
                full_path = os.path.join(data_dir, file_path)
                logger.info(f"User mentioned data directory, using path: {full_path}")
                return {
                    "type": "os_command",
                    "command": f"cat {full_path}"
                }
        
        # Fall back to the original file path
        return {
            "type": "os_command",
            "command": f"cat {file_path}"
        }
    
    def _is_confirmation(self, user_input):
        """Check if user input is a confirmation.
        
        Args:
            user_input: User text input
            
        Returns:
            bool: True if input is a confirmation, False otherwise
        """
        # Convert to lowercase
        input_lower = user_input.lower().strip()
        
        # Common confirmation phrases
        confirmations = [
            "yes", "sure", "ok", "okay", "y", "yep", "yeah", "confirm", 
            "do it", "execute", "run it", "proceed", "go", "go ahead"
        ]
        
        # Check if input matches any confirmation phrase
        return any(input_lower == confirm or input_lower.startswith(confirm + " ") 
                  for confirm in confirmations)
    
    def _update_context(self, user_input, assistant_response):
        """Update conversation context.
        
        Args:
            user_input: User text input
            assistant_response: Assistant's response
        """
        # Add new turn to context
        self.context.append({
            "user": user_input,
            "assistant": assistant_response
        })
        
        # Limit context length
        while len(self.context) > self.config["max_history"]:
            self.context.pop(0)
    
    def _process_file_check(self, action):
        """Process a file check action.
        
        Args:
            action: File check action
            
        Returns:
            dict: File check result
        """
        # Execute the file check action
        file_check_result = self.os_exec_service.execute_action(action)
        
        # Check if path should be stored for follow-up questions
        if file_check_result.get("file_exists", False):
            self.last_file_processed = file_check_result.get("file_path", "")
            
        return file_check_result
    
    def _process_dir_search(self, action):
        """Process a directory search action.
        
        Args:
            action: Directory search action
            
        Returns:
            dict: Directory search result
        """
        # Execute the directory search action
        dir_search_result = self.os_exec_service.execute_action(action)
        
        # Store directory path for potential follow-ups
        if dir_search_result.get("status") == "success":
            directories = dir_search_result.get("directories", [])
            if directories:
                # Use the first exact match or first result
                exact_matches = [d for d in directories if d.get("is_exact_match", False)]
                if exact_matches:
                    self.last_file_processed = exact_matches[0].get("path")
                else:
                    self.last_file_processed = directories[0].get("path")
                    
        return dir_search_result
    
    def run_interactive_session(self):
        """Run an interactive session with the unified assistant."""
        print("\n===== Unified Assistant =====")
        print("(Type 'exit' to end the session)")
        
        # Print scene information if available
        if self.scene_context:
            self._print_scene_info()
            
            # Generate opening message if in scene mode
            opening_message = self._generate_opening_message()
            if opening_message:
                print(f"\nAssistant: {opening_message}")
                self._update_context("[Session started]", opening_message)
        
        # Main interaction loop
        try:
            while True:
                # Get user input with mode indicator
                mode_indicator = "[LLM Mode]" if self.current_mode == "LLM" else "[OS Mode]"
                try:
                    user_input = input(f"\n{mode_indicator} You: ")
                except (EOFError, KeyboardInterrupt):
                    print("\nEnding assistant session.")
                    break
                    
                # Check for exit command in LLM mode
                if user_input.lower() in ['exit', 'quit', 'bye'] and self.current_mode == "LLM":
                    print("\nEnding assistant session.")
                    break
                    
                # Process the input
                result = self.process_input(user_input)
                
                if result["success"]:
                    # Display LLM response if available
                    if result.get("llm_response"):
                        print(f"\nAssistant: {result['llm_response']['response']}")
                        
                    # Show file check results if applicable
                    if result.get("file_check_performed") and result.get("file_check_result"):
                        self._display_file_check_result(result["file_check_result"])
                        
                    # Show directory search results if applicable
                    if result.get("dir_search_performed") and result.get("dir_search_result"):
                        self._display_dir_search_result(result["dir_search_result"])
                    
                    # If we just switched to OS mode, handle confirmation
                    if result.get("mode_switched") and self.current_mode == "OS" and self.pending_action:
                        self._handle_os_mode_transition(result["pending_action"])
                    
                    # Show action results if available
                    if result.get("action_result"):
                        self._display_action_result(result["action_result"])
                else:
                    print(f"\nError: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            
        print("\nThank you for using the Unified Assistant!")
    
    def _handle_os_mode_transition(self, action):
        """Handle transition to OS mode.
        
        Args:
            action: Pending action
        """
        # Display the pending action
        action_type = action.get("type", "unknown")
        print(f"\n[OS Mode] Action detected: {action_type}")
        
        if action_type == "os_command":
            print(f"Command: {action.get('command', 'unknown')}")
        elif action_type == "launch_app":
            print(f"Application: {action.get('app_name', 'unknown')}")
        
        # Auto-confirm if configured
        if self.config["auto_confirm"]:
            # Add delay if specified
            if self.config["delay"] > 0:
                print(f"Auto-executing in {self.config['delay']} seconds...")
                time.sleep(self.config["delay"])
                
            print("Executing action automatically...")
            confirmation_result = self.process_input("yes")
            
            # Display results
            if confirmation_result.get("action_result"):
                self._display_action_result(confirmation_result["action_result"])
        else:
            print("Type 'yes' to confirm, or any other input to cancel.")
    
    def _display_file_check_result(self, result):
        """Display file check result.
        
        Args:
            result: File check result
        """
        print("\n[File Check Result]")
        if result.get("file_exists", False):
            print(f"✓ File exists: {result.get('file_path')}")
            
            file_info = result.get("file_info", {})
            if file_info:
                print(f"  Type: {file_info.get('file_type', 'unknown')}")
                size = file_info.get('size', 0)
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.2f} MB"
                elif size > 1024:
                    size_str = f"{size/1024:.2f} KB"
                else:
                    size_str = f"{size} bytes"
                print(f"  Size: {size_str}")
                
                if "line_count" in file_info:
                    print(f"  Lines: {file_info['line_count']}")
        elif result.get("is_directory", False):
            print(f"! Path exists but is a directory: {result.get('path')}")
        else:
            print(f"✗ File not found: {result.get('searched_path')}")
            
            similar_files = result.get("similar_files", [])
            if similar_files:
                print("  Similar files found:")
                for f in similar_files[:3]:
                    print(f"  - {f.get('name')} (similarity: {f.get('similarity', 0)*100:.0f}%)")
    
    def _display_dir_search_result(self, result):
        """Display directory search result.
        
        Args:
            result: Directory search result
        """
        print("\n[Directory Search Result]")
        directories = result.get("directories", [])
        
        if directories:
            print(f"Found {len(directories)} potential matches:")
            for i, d in enumerate(directories[:5]):
                match_type = "Exact match" if d.get("is_exact_match", False) else "Partial match"
                print(f"  {i+1}. [{match_type}] {d.get('path')}")
        else:
            print(f"No directories found matching '{result.get('searched_for', '')}'")
    
    def _display_action_result(self, result):
        """Display action execution result.
        
        Args:
            result: Action result
        """
        print(f"\nResult: {result.get('message', 'Completed')}")
        
        # Display command output if any
        if "stdout" in result and result["stdout"].strip():
            print(f"\nOutput:\n{result['stdout']}")
            
        # Display errors if any
        if "stderr" in result and result["stderr"].strip():
            print(f"\nErrors/Warnings:\n{result['stderr']}")
    
    def _print_scene_info(self):
        """Print information about the current scene."""
        if not self.scene_context:
            return
            
        print("\n=== Scene Information ===")
        print(f"Name: {self.scene_context.get('name', 'Unnamed Scene')}")
        
        if "constraints" in self.scene_context and "max_steps" in self.scene_context["constraints"]:
            print(f"Max Steps: {self.scene_context['constraints']['max_steps']}")
            
        print("\nRoles:")
        roles = self.scene_context.get("roles", {})
        if "user" in roles:
            print(f"- User: {roles['user']}")
        if "client" in roles:
            print(f"- Assistant: {roles['client']}")
            
        print(f"\nScene Description:\n{self.scene_context.get('scene', '')}")
        print("\n========================")
    
    def _generate_opening_message(self):
        """Generate an opening message based on the scene.
        
        Returns:
            str: Opening message or None if not applicable
        """
        if not self.scene_context:
            return None
            
        # Build a prompt for generating the opening message
        roles = self.scene_context.get("roles", {})
        scene_description = self.scene_context.get("scene", "")
        
        prompt = (
            "You will role-play according to the following guidelines:\n\n"
            f"## Your Role\n{roles.get('client', 'Assistant')}\n\n"
            f"## User's Role\n{roles.get('user', 'Human')}\n\n"
            f"## Scene\n{scene_description}\n\n"
            "## Instructions\n"
            "Generate an opening message to start this conversation. "
            "This should be your first line as the assistant, initiating the interaction "
            "with the user based on the scene description. "
            "Stay completely in character."
        )
        
        # Get client response from LLM
        result = self.llm_service.process_raw_prompt(prompt)
        
        if not result or "response" not in result:
            return "Hello, how can I assist you today?"
            
        return result["response"]

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

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the unified assistant."
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

def main():
    """Run the unified assistant."""
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
        "safe_mode": not args.unsafe,
        "auto_confirm": not args.manual_confirm,
        "delay": args.delay,
        "scene_path": args.scene,
        "max_history": args.max_history,
        "data_dir": args.data_dir
    }
    
    # Print configuration
    print("\n===== Unified Assistant =====")
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
        assistant = UnifiedAssistant(config=config)
        assistant.run_interactive_session()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Use --list-scenes to see available scenes.")
    except Exception as e:
        print(f"Error initializing assistant: {e}")

if __name__ == "__main__":
    main()