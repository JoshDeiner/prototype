"""
Wrapper controller for the voice assistant.

This implements the core state machine and manages the flow between LLM and OS modes.
"""

import os
import sys
import time
import json
from pathlib import Path
import re

from modes.llm_mode import LLMController
from modes.os_mode import OSController
from tools.logger import setup_logger
from prompts.scene_loader import SceneLoader
import config as app_config

# Setup logger
logger = setup_logger()

class Wrapper:
    """
    Wrapper controller implementing the two-mode architecture:
    - LLM Mode: For understanding, planning and generating structured responses
    - OS Mode: For executing validated system actions
    
    The wrapper controls flow between modes and manages transitions.
    """
    
    def __init__(self, config=None):
        """Initialize the wrapper controller.
        
        Args:
            config: Configuration dictionary
        """
        # Set default configuration from config module
        self.config = dict(app_config.DEFAULT_CONFIG)
        
        # Update with provided config (user config)
        if config is not None:
            self.config.update(config)
        
        # Initialize controllers
        self.llm_controller = LLMController(
            model_type=self.config["llm_model"],
            scene_path=self.config["scene_path"]
        )
        
        self.os_controller = OSController(
            dry_run=self.config["dry_run"],
            safe_mode=self.config["safe_mode"]
        )
        
        # Initialize scene support
        self.scene_loader = SceneLoader()
        self.scene_context = None
        if self.config["scene_path"]:
            self.scene_context = app_config.load_scene(self.config["scene_path"])
        
        # Initialize state
        self.current_mode = "LLM"  # Start in LLM mode
        self.pending_action = None
        self.conversation_history = []
        self.retry_count = 0
        self.last_user_input = None
        self.last_response = None
        
        logger.info(f"Initialized Wrapper controller in {self.current_mode} mode")
        logger.info(f"Scene context: {'Loaded' if self.scene_context else 'None'}")
    
    def process_input(self, user_input):
        """Process user input based on current mode.
        
        Args:
            user_input: The text input from the user
            
        Returns:
            dict: Result of processing
        """
        self.last_user_input = user_input
        
        # Initialize result
        result = {
            "success": False,
            "current_mode": self.current_mode,
            "mode_switched": False,
            "response": None,
            "pending_action": None,
            "action_result": None
        }
        
        # Process based on current mode
        if self.current_mode == "LLM":
            logger.info("Processing input in LLM mode")
            result = self._process_llm_mode(user_input, result)
        elif self.current_mode == "OS":
            logger.info("Processing input in OS mode")
            result = self._process_os_mode(user_input, result)
        
        # Update result with current mode
        result["current_mode"] = self.current_mode
        
        return result
    
    def _process_llm_mode(self, user_input, result):
        """Process input in LLM mode.
        
        Args:
            user_input: User text input
            result: Current result dictionary
            
        Returns:
            dict: Updated result
        """
        # Process through LLM controller
        llm_response = self.llm_controller.process_input(user_input, self.conversation_history)
        
        if not llm_response or "response" not in llm_response:
            logger.error("Failed to get valid response from LLM")
            result["error"] = "Failed to get valid response from LLM"
            return result
        
        # Extract the response text
        response_text = llm_response.get("response", "")
        result["response"] = response_text
        self.last_response = response_text
        
        # Extract and validate action
        action = llm_response.get("action", {"type": "none"})
        
        # Check if this is a chained action (direct file operation)
        is_chained_action = llm_response.get("chained_action", False)
        
        # Validate the action
        is_valid, validation_reason = self.os_controller.validate_action(action)
        
        if is_valid:
            logger.info(f"Valid action detected: {action['type']}")
            
            # Check for special action types that remain in LLM mode
            if action["type"] in ["clarify", "explain", "explain_download", "none"]:
                logger.info(f"Action {action['type']} doesn't require mode switch")
                # Reset retry count on successful processing
                self.retry_count = 0
            else:
                # For other action types, switch to OS mode
                self.pending_action = action
                self.current_mode = "OS"
                result["mode_switched"] = True
                result["pending_action"] = action
                
                # For chained actions, we auto-execute immediately
                if is_chained_action:
                    logger.info("Auto-executing chained action")
                    # Store the current result for restoring later
                    temp_result = result.copy()
                    
                    # Execute the pending action
                    os_result = self._process_os_mode("yes", {"success": False})
                    
                    # Add the action result to our result
                    result["action_result"] = os_result.get("action_result")
                    
                    # Make sure we remain in LLM mode when done
                    self.current_mode = "LLM"
                    
                    # No mode switch needed since we already handled it
                    result["mode_switched"] = False
        else:
            logger.warning(f"Invalid action detected: {validation_reason}")
            result["action_validation_error"] = validation_reason
            
            # Increment retry count for invalid actions
            self.retry_count += 1
            if self.retry_count >= self.config["max_retries"]:
                logger.warning(f"Maximum retries ({self.config['max_retries']}) reached, resetting")
                result["max_retries_reached"] = True
                # Reset retry count
                self.retry_count = 0
        
        # Update conversation history
        self._update_conversation(user_input, response_text)
        
        result["success"] = True
        return result
    
    def _process_os_mode(self, user_input, result):
        """Process input in OS mode.
        
        Args:
            user_input: User text input
            result: Current result dictionary
            
        Returns:
            dict: Updated result
        """
        # Check if we have a pending action
        if not self.pending_action:
            logger.error("No pending action in OS mode")
            result["error"] = "No pending action in OS mode"
            # Switch back to LLM mode
            self.current_mode = "LLM"
            return result
        
        # Check if input is a confirmation
        is_confirmation = self._is_confirmation(user_input)
        
        if not is_confirmation:
            logger.info("Input not recognized as confirmation, switching back to LLM mode")
            # Not a confirmation, switch back to LLM mode
            self.current_mode = "LLM"
            # Reprocess the input in LLM mode
            return self._process_llm_mode(user_input, result)
        
        # It's a confirmation, execute the pending action
        logger.info(f"Executing action: {self.pending_action['type']}")
        action_result = self.os_controller.execute_action(self.pending_action)
        
        # Store the action result
        result["action_result"] = action_result
        
        # Update history with system action
        self._update_system_action(self.pending_action, action_result)
        
        # Switch back to LLM mode
        self.current_mode = "LLM"
        result["mode_switched"] = True
        
        # Clear pending action
        self.pending_action = None
        
        # Reset retry count
        self.retry_count = 0
        
        result["success"] = True
        return result
    
    def _is_confirmation(self, user_input):
        """Check if user input is a confirmation.
        
        Args:
            user_input: User text input
            
        Returns:
            bool: True if input is a confirmation, False otherwise
        """
        # Auto confirm if configured
        if self.config["auto_confirm"]:
            return True
        
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
    
    def _update_conversation(self, user_input, response_text):
        """Update conversation history.
        
        Args:
            user_input: User text input
            response_text: Assistant response text
        """
        self.conversation_history.append({
            "user": user_input,
            "assistant": response_text
        })
        
        # Limit history size
        while len(self.conversation_history) > self.config["max_history"]:
            self.conversation_history.pop(0)
    
    def _update_system_action(self, action, result):
        """Update conversation history with system action.
        
        Args:
            action: The action that was executed
            result: The result of the action execution
        """
        action_type = action.get("type", "unknown")
        
        # Create a descriptive message based on action type
        if action_type == "os_command":
            command = action.get("command", "")
            message = f"[System executed command: {command}]"
            if "stdout" in result and result["stdout"].strip():
                message += f"\n\nOutput:\n{result['stdout'].strip()}"
        elif action_type == "launch_app":
            app_name = action.get("app_name", "")
            message = f"[System launched application: {app_name}]"
        elif action_type == "file_check":
            file_path = action.get("file_path", "")
            exists = result.get("file_exists", False)
            message = f"[System checked file: {file_path}] {'Exists' if exists else 'Not found'}"
        else:
            message = f"[System action: {action_type}]"
        
        # Add to conversation history as a system message
        self.conversation_history.append({
            "user": "[System action requested]",
            "assistant": message
        })
        
        # Limit history size
        while len(self.conversation_history) > self.config["max_history"]:
            self.conversation_history.pop(0)
    
    def get_opening_message(self):
        """Get an opening message based on the scene.
        
        Returns:
            str or None: Opening message or None if no scene is loaded
        """
        if not self.scene_context:
            return None
            
        return self.llm_controller.generate_opening_message()
    
    def reset(self):
        """Reset the controller state."""
        self.current_mode = "LLM"
        self.pending_action = None
        self.retry_count = 0
        self.conversation_history = []
        logger.info("Wrapper controller reset to initial state")

    def run_interactive_session(self):
        """Run an interactive session with the voice assistant."""
        print("\n===== Voice Assistant =====")
        print("(Type 'exit' to end the session)")
        
        # Print scene information if available
        if self.scene_context:
            self._print_scene_info()
            
            # Generate opening message if in scene mode
            opening_message = self.get_opening_message()
            if opening_message:
                print(f"\nAssistant: {opening_message}")
                self._update_conversation("[Session started]", opening_message)
        
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
                    if result.get("response"):
                        # Extract plain text from JSON response if needed
                        response_text = result['response']
                        if response_text.startswith('{') and response_text.endswith('}'):
                            try:
                                json_data = json.loads(response_text)
                                if isinstance(json_data, dict) and "response" in json_data:
                                    response_text = json_data["response"]
                            except json.JSONDecodeError:
                                pass
                        print(f"\nAssistant: {response_text}")
                    
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
            
        print("\nThank you for using the Voice Assistant!")
    
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