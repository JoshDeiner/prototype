"""
LLM Mode controller for the voice assistant.

This module handles the processing of user input through the LLM service,
validates responses, and extracts actions.
"""

import json
import re
import os
from pathlib import Path

from llm.local_llm import LLMProvider
from prompts.scene_loader import SceneLoader
from prompts.prompt_builder import PromptBuilder
from tools.logger import setup_logger
import config as app_config

# Setup logger
logger = setup_logger()

class LLMController:
    """
    Controller for LLM mode operations.
    
    Handles interaction with LLM providers, parsing responses, and validating actions.
    """
    
    def __init__(self, model_type="llama", scene_path=None):
        """Initialize the LLM controller.
        
        Args:
            model_type: Type of LLM to use ('llama', 'claude', 'gemini', or 'simulation')
            scene_path: Optional path to a scene definition file (YAML or JSON)
        """
        # Initialize components
        self.llm_provider = LLMProvider(model_type=model_type)
        self.prompt_builder = PromptBuilder()
        self.scene_loader = SceneLoader()
        
        # Initialize scene context if provided
        self.scene_context = None
        if scene_path:
            self.scene_context = self.scene_loader.load_scene(scene_path)
            if self.scene_context:
                logger.info(f"Loaded scene context: {self.scene_context.get('name', 'Unnamed')}")
            else:
                logger.warning(f"Failed to load scene from {scene_path}")
    
    def process_input(self, user_input, conversation_history=None):
        """Process user input through the LLM.
        
        Args:
            user_input: User text input
            conversation_history: Optional conversation history
            
        Returns:
            dict: Response with text and action
        """
        logger.info(f"Processing input: '{user_input}'")
        
        # Check for file patterns in the input to handle file operations more directly
        file_action = self._detect_file_operations(user_input)
        if file_action:
            action_type = file_action.get('action', {}).get('type', 'unknown')
            logger.info(f"Detected direct file operation: {action_type}")
            return file_action
        
        # Build prompt based on whether we have scene context
        if self.scene_context:
            # Format prompt with scene context
            prompt = self.prompt_builder.build_scene_prompt(
                user_input=user_input,
                scene_context=self.scene_context,
                conversation_history=conversation_history
            )
        else:
            # Build standard prompt
            prompt = self.prompt_builder.build_standard_prompt(
                user_input=user_input, 
                conversation_history=conversation_history
            )
        
        # Process through LLM provider
        raw_response = self.llm_provider.generate_response(prompt)
        
        # Extract structured response from raw text
        structured_response = self._extract_structured_response(raw_response)
        
        if structured_response:
            logger.info("Successfully extracted structured response from LLM")
            return structured_response
        
        # If we couldn't extract a structured response, create a basic one
        fallback_response = {
            "response": raw_response.strip(),
            "action": {
                "type": "none"
            }
        }
        
        logger.info("Using fallback structured response (no action extracted)")
        return fallback_response
    
    def _extract_structured_response(self, response_text):
        """Extract structured response (with action) from a raw text response.
        
        Args:
            response_text: Raw text response from LLM
            
        Returns:
            dict or None: Structured response with action if found, None otherwise
        """
        # Check if response contains JSON block
        json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', response_text)
        if json_match:
            try:
                json_str = json_match.group(1)
                json_data = json.loads(json_str)
                
                # Check if it has the expected format
                if isinstance(json_data, dict) and "response" in json_data:
                    # Ensure action field exists
                    if "action" not in json_data:
                        json_data["action"] = {"type": "none"}
                    return json_data
            except json.JSONDecodeError:
                pass

        # Try to find JSON without code blocks
        try:
            # Look for JSON object pattern
            json_pattern = r'({[\s\S]*?})'
            matches = re.findall(json_pattern, response_text)
            
            for match in matches:
                try:
                    json_data = json.loads(match)
                    # Check if it has the expected format
                    if isinstance(json_data, dict) and "response" in json_data:
                        # Ensure action field exists
                        if "action" not in json_data:
                            json_data["action"] = {"type": "none"}
                        return json_data
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
            
        # Try to extract file operations using regex patterns
        try:
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
                    return {
                        "response": response_text,
                        "action": {
                            "type": "os_command",
                            "command": f"cat {file_path}"
                        }
                    }
                    
            # Directory listing patterns
            if "list the files in the current directory" in response_text.lower():
                return {
                    "response": response_text,
                    "action": {
                        "type": "os_command",
                        "command": "ls -la"
                    }
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
                        "response": response_text,
                        "action": {
                            "type": "file_check",
                            "file_path": file_path
                        }
                    }
        except Exception:
            pass
                
        # No structured response detected
        return None
    
    def _detect_file_operations(self, text_input):
        """Detect direct file operation requests from user input.
        This enables handling file operations in a single step.
        
        Args:
            text_input: User text input
            
        Returns:
            dict or None: Structured response with file action if detected, None otherwise
        """
        import re  # Make sure we import it in the function scope
        text_lower = text_input.lower()
        
        # Data directory path - all file operations will be directed here
        data_dir = str(app_config.DATA_DIR)
        
        # Common file viewing and reading patterns
        view_patterns = [
            r"what('s| is) in (?:the )?file (?:named )?[\"']?([a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+)[\"']?",
            r"(show|display|view|read|open|cat)(?:[ \t]+me)? (?:the )?(?:contents of )?(?:file )?[\"']?([a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+)[\"']?",
            r"tell (?:me )?what('s| is) in [\"']?([a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+)[\"']?",
            r"(?:can you )?check (?:the )?contents of [\"']?([a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+)[\"']?",
            r"what is in ([a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+)",  # Simpler pattern for direct questions
            r"show me ([a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+)",     # Common "show me file.txt" pattern
            r"show me the contents of ([a-zA-Z0-9_\.\/-]+\.[a-zA-Z0-9]+)"  # Explicit "show me the contents of" pattern
        ]
        
        # Check for file viewing patterns
        for pattern in view_patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Extract the filename from the pattern match
                filename = match.group(2) if len(match.groups()) > 1 else match.group(1)
                
                # Always use just the basename of the file in the data directory
                # This ensures all file operations are contained within the data directory
                base_filename = os.path.basename(filename)
                file_path = os.path.join(data_dir, base_filename)
                
                return {
                    "response": f"I'll check if the file '{base_filename}' exists in the data directory and show you its contents.",
                    "action": {
                        "type": "os_command",
                        "command": f"cat {file_path}"
                    },
                    "chained_action": True
                }
                
        # Common file listing patterns
        list_patterns = [
            r"(?:can you )?(list|show|display) (?:all )?(?:the )?files(?: in this directory)?",
            r"what files (?:are|do we have)(?: in this directory)?",
            r"(?:can you )?show me (?:all )?(?:the )?files"
        ]
        
        # Check for file listing patterns
        for pattern in list_patterns:
            if re.search(pattern, text_lower):
                return {
                    "response": "I'll list the files in the data directory for you.",
                    "action": {
                        "type": "os_command",
                        "command": f"ls -la {data_dir}"
                    },
                    "chained_action": True
                }
        
        # No direct file operation detected
        return None
    
    def validate_action(self, action):
        """Validate the structure and completeness of an action.
        
        Args:
            action: The action dictionary to validate
            
        Returns:
            tuple: (is_valid, reason)
        """
        if not action or not isinstance(action, dict):
            return False, "Action is not a valid dictionary"
            
        if "type" not in action:
            return False, "Action missing required 'type' field"
            
        action_type = action.get("type")
        
        # Check required fields for specific action types
        if action_type == "launch_app":
            if "app_name" not in action or not action["app_name"]:
                return False, "launch_app action missing required 'app_name' field"
        elif action_type == "explain_download":
            if "target" not in action or not action["target"]:
                return False, "explain_download action missing required 'target' field"
        elif action_type == "explain":
            if "content" not in action or not action["content"]:
                return False, "explain action missing required 'content' field"
        elif action_type == "os_command":
            if "command" not in action or not action["command"]:
                return False, "os_command action missing required 'command' field"
        elif action_type == "clarify":
            if "question" not in action or not action["question"]:
                return False, "clarify action missing required 'question' field"
        elif action_type == "file_check":
            if "file_path" not in action or not action["file_path"]:
                return False, "file_check action missing required 'file_path' field"
        elif action_type == "dir_search":
            if "dir_name" not in action or not action["dir_name"]:
                return False, "dir_search action missing required 'dir_name' field"
        elif action_type != "none":
            return False, f"Unknown action type: {action_type}"
            
        return True, "Action is valid"
    
    def generate_opening_message(self):
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
        
        # Process through LLM provider
        opening_message = self.llm_provider.generate_response(prompt)
        
        if not opening_message or not opening_message.strip():
            return "Hello, how can I assist you today?"
            
        return opening_message.strip()