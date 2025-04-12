"""
Action validator for the voice assistant.

Validates actions for safety and completeness before execution.
"""

import os
import re
import config as app_config
from tools.logger import setup_logger

# Setup logger
logger = setup_logger()

class ActionValidator:
    """
    Validator for action safety and completeness.
    
    Ensures actions have required fields and don't contain dangerous commands.
    """
    
    def __init__(self, safe_mode=True):
        """Initialize the action validator.
        
        Args:
            safe_mode: If True, apply strict safety checks
        """
        self.safe_mode = safe_mode
        self.dangerous_commands = app_config.DANGEROUS_COMMANDS
        self.safe_apps = app_config.SAFE_APPLICATIONS
        
    def validate_action(self, action):
        """Validate if an action is safe to execute.
        
        Args:
            action: Action dictionary from LLM
            
        Returns:
            tuple: (is_valid, reason)
        """
        if not action or "type" not in action:
            return False, "Invalid action format"
            
        action_type = action["type"]
        
        # Validate based on action type
        if action_type == "launch_app":
            app_name = action.get("app_name", "")
            if not app_name:
                return False, "No application name specified"
                
            # Check if app exists in common locations (simplified)
            if self.safe_mode and not self.is_app_safe(app_name):
                return False, f"Application '{app_name}' not allowed or not found"
                
        elif action_type == "os_command":
            command = action.get("command", "")
            if not command:
                return False, "No command specified"
                
            # Safety check for dangerous commands
            if self.safe_mode and self.is_dangerous_command(command):
                return False, f"Potentially dangerous command detected: {command}"
                
        elif action_type == "file_check":
            file_path = action.get("file_path", "")
            if not file_path:
                return False, "No file path specified"
                
        elif action_type == "dir_search":
            dir_name = action.get("dir_name", "")
            if not dir_name:
                return False, "No directory name specified"
                
        elif action_type not in ["explain_download", "explain", "clarify", "none"]:
            return False, f"Unknown action type: {action_type}"
            
        return True, "Action is valid"
    
    def is_app_safe(self, app_name):
        """Check if an application is safe to launch.
        
        Args:
            app_name: Name of the application to check
            
        Returns:
            bool: True if the app is considered safe
        """
        return app_name.lower() in self.safe_apps
        
    def is_dangerous_command(self, command):
        """Check if a command might be dangerous.
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if the command appears dangerous
        """
        # Convert to lowercase for matching
        cmd_lower = command.lower()
        
        # Check against known dangerous patterns
        for dangerous in self.dangerous_commands:
            if dangerous in cmd_lower:
                return True
                
        # Check for command chaining that might be trying to bypass checks
        if ';' in cmd_lower or '&&' in cmd_lower or '||' in cmd_lower:
            # Command chaining isn't automatically dangerous, but deserves extra scrutiny
            for dangerous in self.dangerous_commands:
                parts = re.split(r'[;&|]+', cmd_lower)
                for part in parts:
                    if dangerous in part.strip():
                        return True
                        
        return False