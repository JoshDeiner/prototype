#!/usr/bin/env python3
"""
Middleware for the file assistant, implementing the stateful controller pattern.

This implements the updated architecture with:
- Stateful controller with two modes (LLM and OS)
- Support for scene injection
- Clear transition logic for state machine
"""
import os
import json
import re
import time
from utils import logger
from llm_service import LLMService
from os_exec import OSExecutionService

class StatefulController:
    """
    Stateful controller implementing the two-mode architecture:
    - LLM Mode: For understanding, planning and generating structured responses
    - OS Mode: For executing validated system actions
    
    The controller manages state transitions and provides fallback mechanisms.
    """
    
    def __init__(self, config=None):
        """Initialize the stateful controller.
        
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
            "max_retries": 3
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Initialize components
        self.llm_service = LLMService(
            model_type=self.config["llm_model"],
            scene_path=self.config["scene_path"]
        )
        
        self.os_exec_service = OSExecutionService(
            dry_run=self.config["dry_run"],
            safe_mode=self.config["safe_mode"]
        )
        
        # Initialize state
        self.current_mode = "LLM"  # Start in LLM mode
        self.pending_action = None
        self.conversation_history = []
        self.retry_count = 0
        self.last_user_input = None
        self.last_response = None
        
        logger.info(f"Initialized StatefulController in {self.current_mode} mode")
        logger.info(f"Scene context: {'Loaded' if self.llm_service.scene_context else 'None'}")
    
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
        # Process through LLM service
        llm_response = self.llm_service.process_input(user_input, self.conversation_history)
        
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
        is_valid, validation_reason = self.os_exec_service.validate_action(action)
        
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
        action_result = self.os_exec_service.execute_action(self.pending_action)
        
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
        if not self.llm_service.scene_context:
            return None
            
        return self.llm_service.generate_opening_message()
    
    def reset(self):
        """Reset the controller state."""
        self.current_mode = "LLM"
        self.pending_action = None
        self.retry_count = 0
        self.conversation_history = []
        logger.info("StatefulController reset to initial state")

# Keep the old FileAssistantMiddleware for backward compatibility
class FileAssistantMiddleware:
    """
    Middleware that processes LLM responses from the scene simulator,
    extracts file operation requests, and executes them.
    """
    
    def __init__(self, dry_run=False):
        """Initialize the middleware with an OS execution service.
        
        Args:
            dry_run: If True, will only log commands without executing them
        """
        self.os_exec = OSExecutionService(dry_run=dry_run, safe_mode=True)
        
        # Extract filenames from responses
        self.filename_pattern = r"(?:['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*)"
        
        # Patterns for detecting file operations
        self.file_read_patterns = [
            r"show you (?:what's|what is) in\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*",
            r"show you the contents of\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*",
            r"open\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*",
            r"read\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*",
            r"contents of\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*",
            r"display\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*",
            r"let me show you\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*"
        ]
        
        self.file_list_patterns = [
            r"list (?:the )?files in\s+['\"]*([a-zA-Z0-9_\-\.\/~]+)['\"]*",
            r"list\s+['\"]*([a-zA-Z0-9_\-\.\/~]+)['\"]*",
            r"directory\s+['\"]*([a-zA-Z0-9_\-\.\/~]+)['\"]*",
            r"show you the files in\s+['\"]*([a-zA-Z0-9_\-\.\/~]+)['\"]*"
        ]
        
        self.file_check_patterns = [
            r"check if\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*\s+exists",
            r"see if\s+['\"]*([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)['\"]*\s+exists"
        ]
        
    def process_response(self, client_response):
        """Process an LLM response to detect and handle file operations.
        
        Args:
            client_response: The LLM's response text
            
        Returns:
            dict: Results of any file operations performed
        """
        # Skip processing if response is JSON or code block formatted
        if "```" in client_response or "{" in client_response and "}" in client_response:
            return {
                "action_detected": False,
                "message": "Response format not suitable for middleware processing"
            }
        
        # Exact matches for our template responses
        
        # Check for file content requests with exact pattern: "show you what's in FILENAME"
        match = re.search(r"show you what's in ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)", client_response.lower())
        if match:
            file_path = match.group(1)
            return self._handle_file_read(file_path)
            
        # Check for "show you the contents of FILENAME"
        match = re.search(r"show you the contents of ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+)", client_response.lower())
        if match:
            file_path = match.group(1)
            return self._handle_file_read(file_path)
            
        # Check for exact current directory listing phrase
        if "list the files in the current directory" in client_response.lower():
            return self._handle_directory_list(".")
            
        # Check for exact file check pattern: "check if FILENAME exists"
        match = re.search(r"check if ([a-zA-Z0-9_\-\.\/~]+\.[a-zA-Z0-9]+) exists", client_response.lower())
        if match:
            file_path = match.group(1)
            return self._handle_file_check(file_path)
            
        # Alternative patterns for broader matching when exact patterns aren't used
        
        # Special case for general file content checks
        if any(phrase in client_response.lower() for phrase in 
               ["show you what", "let me show you", "read the file", "contents of"]):
            # Try to extract any filename with extension
            match = re.search(self.filename_pattern, client_response)
            if match:
                file_path = match.group(1)
                return self._handle_file_read(file_path)
        
        # Special case for directory listing
        if any(phrase in client_response.lower() for phrase in 
               ["list the files", "list files", "directory"]):
            # Default to current directory
            dir_path = "."
            return self._handle_directory_list(dir_path)
        
        # Special case for file checking
        if any(phrase in client_response.lower() for phrase in 
               ["check if", "see if", "exists"]):
            # Try to extract any filename with extension
            match = re.search(self.filename_pattern, client_response)
            if match:
                file_path = match.group(1)
                return self._handle_file_check(file_path)
        
        # Regular pattern matching
        # Check for file read operations
        for pattern in self.file_read_patterns:
            match = re.search(pattern, client_response, re.IGNORECASE)
            if match:
                file_path = match.group(1)
                return self._handle_file_read(file_path)
        
        # Check for file listing operations
        for pattern in self.file_list_patterns:
            match = re.search(pattern, client_response, re.IGNORECASE)
            if match:
                dir_path = match.group(1)
                if dir_path.lower() in ["the current directory", "this directory", "here", "current directory", "."]:
                    dir_path = "."
                return self._handle_directory_list(dir_path)
        
        # Check for file check operations
        for pattern in self.file_check_patterns:
            match = re.search(pattern, client_response, re.IGNORECASE)
            if match:
                file_path = match.group(1)
                return self._handle_file_check(file_path)
        
        # Default: no action detected
        return {
            "action_detected": False,
            "message": "No file operation detected in response"
        }
    
    def _handle_file_read(self, file_path):
        """Handle a file read operation.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            dict: Results of the operation
        """
        # Check if file path has a directory component, if not, look in data directory
        import os
        if os.path.dirname(file_path) == "":
            data_dir = "/workspaces/codespaces-blank/prototype/data"
            full_path = os.path.join(data_dir, file_path)
        else:
            full_path = file_path
            
        action = {
            "type": "os_command",
            "command": f"cat {full_path}"
        }
        
        # Validate and execute
        is_valid, validation_reason = self.os_exec.validate_action(action)
        if not is_valid:
            return {
                "action_detected": True,
                "action_type": "read",
                "file_path": file_path,
                "success": False,
                "message": validation_reason
            }
        
        # Execute the command
        result = self.os_exec.execute_action(action)
        return {
            "action_detected": True,
            "action_type": "read",
            "file_path": file_path,
            "success": result["status"] == "success",
            "message": result.get("message", ""),
            "content": result.get("stdout", ""),
            "error": result.get("stderr", "")
        }
    
    def _handle_directory_list(self, dir_path):
        """Handle a directory listing operation.
        
        Args:
            dir_path: Path to the directory to list
            
        Returns:
            dict: Results of the operation
        """
        # If listing the current directory or no directory specified, use data directory
        import os
        if dir_path == "." or dir_path.lower() in ["the current directory", "this directory", "here", "current directory"]:
            dir_path = "/workspaces/codespaces-blank/prototype/data"
            
        action = {
            "type": "os_command",
            "command": f"ls -la {dir_path}"
        }
        
        # Validate and execute
        is_valid, validation_reason = self.os_exec.validate_action(action)
        if not is_valid:
            return {
                "action_detected": True,
                "action_type": "list",
                "dir_path": dir_path,
                "success": False,
                "message": validation_reason
            }
        
        # Execute the command
        result = self.os_exec.execute_action(action)
        return {
            "action_detected": True,
            "action_type": "list",
            "dir_path": dir_path,
            "success": result["status"] == "success",
            "message": result.get("message", ""),
            "content": result.get("stdout", ""),
            "error": result.get("stderr", "")
        }
    
    def _handle_file_check(self, file_path):
        """Handle a file check operation.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            dict: Results of the operation
        """
        action = {
            "type": "file_check",
            "file_path": file_path
        }
        
        # Validate and execute
        is_valid, validation_reason = self.os_exec.validate_action(action)
        if not is_valid:
            return {
                "action_detected": True,
                "action_type": "check",
                "file_path": file_path,
                "success": False,
                "message": validation_reason
            }
        
        # Execute the check
        result = self.os_exec.execute_action(action)
        
        # Format the result for display
        file_exists = result.get("file_exists", False)
        message = ""
        if file_exists:
            file_info = result.get("file_info", {})
            message = f"File '{file_path}' exists. Type: {file_info.get('file_type', 'unknown')}, Size: {file_info.get('size', 0)} bytes."
        else:
            message = f"File '{file_path}' does not exist."
            
        return {
            "action_detected": True,
            "action_type": "check",
            "file_path": file_path,
            "success": True,
            "file_exists": file_exists,
            "message": message,
            "details": result
        }