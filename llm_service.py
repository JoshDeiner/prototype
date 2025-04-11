"""LLM service for processing text input and generating responses.
Includes integrated scene context functionality for role-playing simulations.
"""
import json
import logging
import os
import requests
import re
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()
from utils import logger, ensure_directory

# Import Google Generative AI library
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI package not available. Install with 'pip install google-generativeai'")

class LLMService:
    def __init__(self, model_type="llama", scene_path=None):
        """Initialize the LLM service.
        
        Args:
            model_type: Type of LLM to use ('llama', 'claude', 'gemini', or 'simulation')
            scene_path: Optional path to a scene definition file (YAML or JSON)
        """
        self.model_type = model_type
        self.context = []
        self.simulation_mode = True  # Default to simulation for now
        
        # Scene-related attributes
        self.scene_context = None
        self.scene_path = scene_path
        
        # Placeholder for model configuration
        self.model_config = {
            "llama": {
                "api_url": os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate"),
                "model_name": os.environ.get("OLLAMA_MODEL", "llama2")
            },
            "claude": {
                "api_key": os.environ.get("CLAUDE_API_KEY", ""),
                "api_url": "https://api.anthropic.com/v1/messages",
                "model_name": os.environ.get("CLAUDE_MODEL", "claude-3-haiku-20240307")
            },
            "gemini": {
                "api_key": os.environ.get("GEMINI_API_KEY", ""),
                "model_name": os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-001")
            }
        }
        
        # Check if Ollama is available first
        if self._check_ollama_available() and model_type == "llama":
            self.simulation_mode = False
            logger.info(f"Initialized LLM service with Ollama model: {self.model_config['llama']['model_name']}")
        # If Ollama is not available but Gemini is requested or as fallback, try Gemini
        elif (model_type == "gemini" or model_type == "llama") and self._check_gemini_available():
            self.model_type = "gemini"  # Switch to Gemini even if Llama was requested
            self.simulation_mode = False
            logger.info(f"Initialized LLM service with Gemini model: {self.model_config['gemini']['model_name']}")
        # Try Claude as the last option
        elif model_type == "claude" and self.model_config["claude"]["api_key"]:
            self.simulation_mode = False
            logger.info(f"Initialized LLM service with Claude model: {self.model_config['claude']['model_name']}")
        else:
            logger.warning(f"No {model_type} model available, using simulation mode")
            
        # Load scene if provided
        if scene_path:
            self.load_scene(scene_path)
            
    def _check_ollama_available(self):
        """Check if Ollama is available on the local machine."""
        try:
            # Simple ping to check if Ollama is running
            response = requests.get("http://localhost:11434/api/tags")
            return response.status_code == 200
        except:
            return False
            
    def _check_gemini_available(self):
        """Check if Gemini API is available and configured."""
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini Python library not installed")
            return False
            
        api_key = self.model_config["gemini"]["api_key"]
        if not api_key:
            logger.warning("Gemini API key not configured")
            return False
            
        try:
            # Configure the Gemini API
            genai.configure(api_key=api_key)
            # Try to list models to verify API key works (lightweight check)
            genai.list_models()
            return True
        except Exception as e:
            logger.warning(f"Gemini API check failed: {e}")
            return False
            
    def _format_prompt(self, text_input, context=None):
        """Format the prompt for the LLM.
        
        Args:
            text_input: The user text input
            context: Optional conversation context
            
        Returns:
            str: Formatted prompt for the LLM
        """
        # Create a structured prompt for the LLM
        system_prompt = """You are a helpful assistant for a Raspberry Pi OS help desk. 
You provide clear, concise answers to user questions about using their Raspberry Pi.
Your responses should be helpful and accurate.

IMPORTANT: When a user's request is unclear, ask clarifying questions instead of guessing OS commands.
For example, if they just say "open a file" or "show me files," ask which file or directory they want to interact with.
Only construct OS commands when you have sufficient information to do so accurately.

When handling file operations:
1. If the user mentions a file but you're not sure if it exists, use file_check action first
2. If the user mentions a directory path that might not exist, use dir_search action to find it
3. Only proceed with file operations after confirming the file or directory exists

For each user question, provide:
1. A helpful response (which may be a follow-up question if needed)
2. An action if needed (in JSON format)

Valid action types:
- "launch_app": To open an application (requires "app_name")
- "explain_download": To explain how to download something (requires "target")
- "explain": To provide an explanation about a topic (requires "content")
- "os_command": To execute an OS command (requires "command")
- "clarify": When you need more information before suggesting an action (requires "question")
- "file_check": To check if a file exists before taking action (requires "file_path")
- "dir_search": To search for a directory by name (requires "dir_name")
- "none": When no action is needed

Your response MUST be in the following JSON format:
{
  "response": "Your helpful text response here (may be a question)",
  "action": {
    "type": "action_type", 
    "app_name": "application_name",  // Only for launch_app
    "target": "download_target",     // Only for explain_download
    "content": "explanation_topic",  // Only for explain
    "command": "command_to_execute", // Only for os_command
    "question": "what you need to know" // Only for clarify
  }
}

If you need clarification, use the "clarify" action type with a clear question.
"""
        
        # Add conversation context if available
        conversation = ""
        if context:
            for turn in context:
                conversation += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n\n"
                
        # Add the current user input
        conversation += f"User: {text_input}\nAssistant:"
        
        return {"system": system_prompt, "conversation": conversation}
        
    def _call_ollama(self, prompt):
        """Call the Ollama API to get a response.
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            dict: LLM response
        """
        # This would be implemented for actual Ollama integration
        # For now, just log that we would call Ollama
        logger.info("Would call Ollama API (not implemented yet)")
        return None
        
    def _call_claude(self, prompt):
        """Call the Claude API to get a response.
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            dict: LLM response
        """
        # This would be implemented for actual Claude API integration
        # For now, just log that we would call Claude
        logger.info("Would call Claude API (not implemented yet)")
        return None
        
    def _call_gemini(self, prompt):
        """Call the Gemini API to get a response.
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            dict: LLM response with text and action
        """
        try:
            # Configure the Gemini API
            genai.configure(api_key=self.model_config["gemini"]["api_key"])
            
            # Get the model
            model = genai.GenerativeModel(self.model_config["gemini"]["model_name"])
            
            # Prepare the complete prompt with system prompt and conversation
            system_prompt = prompt["system"]
            conversation = prompt["conversation"]
            
            complete_prompt = f"{system_prompt}\n\n{conversation}"
            
            # Generate content with the model
            response = model.generate_content(complete_prompt)
            
            # Parse the response to extract the JSON
            response_text = response.text
            
            try:
                # Extract JSON from the response text
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_part = response_text[json_start:json_end]
                    parsed_response = json.loads(json_part)
                    logger.info("Successfully parsed JSON response from Gemini")
                    return parsed_response
                else:
                    # If no valid JSON found, create a basic response
                    logger.warning("No valid JSON found in Gemini response, creating basic format")
                    return {
                        "response": response_text.strip(),
                        "action": {
                            "type": "none"
                        }
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from Gemini response: {e}")
                # Return a basic format with the raw response
                return {
                    "response": response_text.strip(),
                    "action": {
                        "type": "none"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return None
    
    def process_input(self, text_input, conversation_history=None):
        """Process text input through the LLM.
        
        Args:
            text_input: The user text input
            conversation_history: Optional conversation history
            
        Returns:
            dict: JSON response with text and action
        """
        logger.info(f"Processing input: '{text_input}'")
        
        # Check for file patterns in the input to handle file operations more directly
        file_action = self._detect_file_operations(text_input)
        if file_action:
            action_type = file_action.get('action', {}).get('type', 'unknown')
            logger.info(f"Detected direct file operation: {action_type}")
            return file_action
            
        # Check if we have scene context
        if self.scene_context:
            # Format prompt with scene
            formatted_prompt = self.format_prompt_with_scene(text_input, conversation_history)
            
            # Process with raw prompt method
            raw_response = self.process_raw_prompt(formatted_prompt)
            
            # Try to extract JSON response with action
            if raw_response and "response" in raw_response:
                structured_response = self._extract_structured_response(raw_response["response"])
                if structured_response:
                    logger.info("Successfully extracted structured response from scene-based prompt")
                    return structured_response
            
            # Create a fallback structured response if extraction failed
            response_text = raw_response.get("response", "I'm not sure how to respond to that.")
            fallback_response = {
                "response": response_text,
                "action": {
                    "type": "none"
                }
            }
            logger.info("Using fallback structured response for scene-based prompt")
            return fallback_response
        
        # If not in simulation mode, try to use the actual LLM
        if not self.simulation_mode:
            prompt = self._format_prompt(text_input, conversation_history)
            
            if self.model_type == "llama":
                response = self._call_ollama(prompt)
                if response:
                    return response
            elif self.model_type == "gemini":
                response = self._call_gemini(prompt)
                if response:
                    return response
            elif self.model_type == "claude":
                response = self._call_claude(prompt)
                if response:
                    return response
                    
            # Fall back to simulation if the LLM call fails
            logger.warning("LLM call failed, falling back to simulation mode")
        
        # Simulation mode (hardcoded responses for testing)
        # Simple mock implementation for testing
        if "browser" in text_input.lower():
            if "open" in text_input.lower():
                response = {
                    "response": "I'll open a web browser for you.",
                    "action": {
                        "type": "launch_app",
                        "app_name": "firefox"
                    }
                }
            elif "install" in text_input.lower():
                response = {
                    "response": "To install Google Chrome, you can open a terminal and run 'sudo apt install chromium-browser' or download Chrome from the official website.",
                    "action": {
                        "type": "explain_download",
                        "target": "Google Chrome"
                    }
                }
            else:
                response = {
                    "response": "Browsers like Firefox and Chrome can be used to access websites.",
                    "action": {
                        "type": "explain",
                        "content": "web_browsers"
                    }
                }
        elif "list files" in text_input.lower() and "directory" in text_input.lower():
            response = {
                "response": "I'll list the files in your current directory.",
                "action": {
                    "type": "os_command",
                    "command": "ls -la"
                }
            }
        elif "show files" in text_input.lower() or "list files" in text_input.lower():
            response = {
                "response": "Which directory would you like me to list files from? For example, the current directory or a specific location?",
                "action": {
                    "type": "clarify",
                    "question": "which_directory"
                }
            }
        elif "open file" in text_input.lower() or ("open" in text_input.lower() and "file" in text_input.lower()):
            response = {
                "response": "Which file would you like me to open? Please provide the filename or path.",
                "action": {
                    "type": "clarify",
                    "question": "which_file"
                }
            }
        elif ".txt" in text_input.lower() and ("open" in text_input.lower() or "cat" in text_input.lower() or "show" in text_input.lower() or "read" in text_input.lower()):
            # Extract filename or path
            import re
            
            # Try to extract a full path first 
            path_match = re.search(r'([~\w\/\.-]+\.txt)', text_input.lower())
            
            # Then try just a filename
            filename_match = re.search(r'(\w+\.txt)', text_input.lower())
            
            if path_match:
                file_path = path_match.group(1)
                # Directly use os_command to cat the file
                response = {
                    "response": f"I'll show you the contents of '{file_path}'.",
                    "action": {
                        "type": "os_command",
                        "command": f"cat {file_path}"
                    }
                }
            elif filename_match:
                filename = filename_match.group(1)
                # Directly use os_command to cat the file
                response = {
                    "response": f"I'll show you the contents of '{filename}'.",
                    "action": {
                        "type": "os_command",
                        "command": f"cat {filename}"
                    }
                }
            else:
                response = {
                    "response": "Which text file would you like me to show?",
                    "action": {
                        "type": "clarify",
                        "question": "which_text_file"
                    }
                }
        else:
            response = {
                "response": "I'm not sure how to help with that. Could you please be more specific about what you'd like me to do?",
                "action": {
                    "type": "none"
                }
            }
            
        # Store interaction in context if no history was provided
        if conversation_history is None:
            self.context.append({"user": text_input, "assistant": response["response"]})
        
        logger.info(f"LLM response generated: {json.dumps(response, indent=2)}")
        return response
    
    def _detect_file_operations(self, text_input):
        """Detect direct file operation requests from user input.
        This enables handling file operations in a single step.
        
        Args:
            text_input: User text input
            
        Returns:
            dict or None: Structured response with file action if detected, None otherwise
        """
        import re  # Make sure we import it in the function scope
        import os
        text_lower = text_input.lower()
        
        # Data directory path - all file operations will be directed here
        data_dir = "/workspaces/codespaces-blank/prototype/data"
        
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
                    "type": "os_command",  # Add explicit type for logging
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
                    "type": "os_command",  # Add explicit type for logging
                    "chained_action": True
                }
        
        # No direct file operation detected
        return None
        
        # If not in simulation mode, try to use the actual LLM
        if not self.simulation_mode:
            prompt = self._format_prompt(text_input, conversation_history)
            
            if self.model_type == "llama":
                response = self._call_ollama(prompt)
                if response:
                    return response
            elif self.model_type == "gemini":
                response = self._call_gemini(prompt)
                if response:
                    return response
            elif self.model_type == "claude":
                response = self._call_claude(prompt)
                if response:
                    return response
                    
            # Fall back to simulation if the LLM call fails
            logger.warning("LLM call failed, falling back to simulation mode")
        
        # Simulation mode (hardcoded responses for testing)
        # Simple mock implementation for testing
        if "browser" in text_input.lower():
            if "open" in text_input.lower():
                response = {
                    "response": "I'll open a web browser for you.",
                    "action": {
                        "type": "launch_app",
                        "app_name": "firefox"
                    }
                }
            elif "install" in text_input.lower():
                response = {
                    "response": "To install Google Chrome, you can open a terminal and run 'sudo apt install chromium-browser' or download Chrome from the official website.",
                    "action": {
                        "type": "explain_download",
                        "target": "Google Chrome"
                    }
                }
            else:
                response = {
                    "response": "Browsers like Firefox and Chrome can be used to access websites.",
                    "action": {
                        "type": "explain",
                        "content": "web_browsers"
                    }
                }
        elif "list files" in text_input.lower() and "directory" in text_input.lower():
            response = {
                "response": "I'll list the files in your current directory.",
                "action": {
                    "type": "os_command",
                    "command": "ls -la"
                }
            }
        elif "show files" in text_input.lower() or "list files" in text_input.lower():
            response = {
                "response": "Which directory would you like me to list files from? For example, the current directory or a specific location?",
                "action": {
                    "type": "clarify",
                    "question": "which_directory"
                }
            }
        elif "open file" in text_input.lower() or ("open" in text_input.lower() and "file" in text_input.lower()):
            response = {
                "response": "Which file would you like me to open? Please provide the filename or path.",
                "action": {
                    "type": "clarify",
                    "question": "which_file"
                }
            }
        elif ".txt" in text_input.lower() and ("open" in text_input.lower() or "cat" in text_input.lower() or "show" in text_input.lower() or "read" in text_input.lower()):
            # Extract filename or path
            import re
            
            # Try to extract a full path first 
            path_match = re.search(r'([~\w\/\.-]+\.txt)', text_input.lower())
            
            # Then try just a filename
            filename_match = re.search(r'(\w+\.txt)', text_input.lower())
            
            if path_match:
                file_path = path_match.group(1)
                # Directly use os_command to cat the file
                response = {
                    "response": f"I'll show you the contents of '{file_path}'.",
                    "action": {
                        "type": "os_command",
                        "command": f"cat {file_path}"
                    }
                }
            elif filename_match:
                filename = filename_match.group(1)
                # Directly use os_command to cat the file
                response = {
                    "response": f"I'll show you the contents of '{filename}'.",
                    "action": {
                        "type": "os_command",
                        "command": f"cat {filename}"
                    }
                }
            else:
                response = {
                    "response": "Which text file would you like me to show?",
                    "action": {
                        "type": "clarify",
                        "question": "which_text_file"
                    }
                }
        else:
            response = {
                "response": "I'm not sure how to help with that. Could you please be more specific about what you'd like me to do?",
                "action": {
                    "type": "none"
                }
            }
            
        # Store interaction in context if no history was provided
        if conversation_history is None:
            self.context.append({"user": text_input, "assistant": response["response"]})
        
        logger.info(f"LLM response generated: {json.dumps(response, indent=2)}")
        return response
        
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
    
    def load_scene(self, scene_path):
        """Load a scene definition from a configuration file.
        
        Args:
            scene_path: Path to the scene configuration file (YAML or JSON)
            
        Returns:
            bool: True if scene loaded successfully, False otherwise
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
            return False
            
        try:
            # Determine file type by extension
            _, ext = os.path.splitext(scene_path)
            
            # Load based on file type
            if ext.lower() in ['.yaml', '.yml']:
                with open(scene_path, 'r') as f:
                    scene_data = yaml.safe_load(f)
            elif ext.lower() == '.json':
                with open(scene_path, 'r') as f:
                    scene_data = json.load(f)
            else:
                logger.error(f"Unsupported scene file format: {ext}")
                return False
                
            # Validate the scene configuration
            if not self._validate_scene_config(scene_data):
                logger.error(f"Invalid scene configuration in {scene_path}")
                return False
                
            # Set the scene context
            self.scene_context = scene_data
            self.scene_path = scene_path
                
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
        
    def format_prompt_with_scene(self, user_input, conversation_history=None):
        """Format the prompt with scene context if available.
        
        Args:
            user_input: User text input
            conversation_history: Optional list of conversation turns
            
        Returns:
            str: Formatted prompt
        """
        if not self.scene_context:
            # No scene, use system prompt for LLM
            return self._format_prompt(user_input, conversation_history)
            
        # Extract scene components
        roles = self.scene_context.get("roles", {})
        scene_description = self.scene_context.get("scene", "")
        constraints = self.scene_context.get("constraints", {})
        
        # Build prompt with scene context
        prompt_parts = [
            "You will role-play according to the following guidelines:",
            f"## Your Role\n{roles.get('client', 'Assistant')}",
            f"## User's Role\n{roles.get('user', 'Human')}",
            f"## Scene\n{scene_description}",
            "## Conversation History"
        ]
        
        # Add conversation history
        if conversation_history:
            for entry in conversation_history:
                prompt_parts.append(f"User: {entry.get('user', '')}")
                prompt_parts.append(f"You: {entry.get('assistant', '')}")
        
        # Add current user input
        prompt_parts.append(f"## Current User Input\n{user_input}")
        
        # Add constraints if available
        if constraints:
            prompt_parts.append("## Constraints")
            if "max_steps" in constraints:
                prompt_parts.append(f"This conversation must resolve within {constraints['max_steps']} turns.")
            if "style" in constraints:
                prompt_parts.append(f"Style: {constraints['style']}")
        
        # Add response instruction
        prompt_parts.append("""## Instructions
Respond in-character based on the scene description.

Your response MUST be in the following JSON format:
{
  "response": "Your in-character text response here",
  "action": {
    "type": "action_type", 
    "app_name": "application_name",  // Only for launch_app
    "target": "download_target",     // Only for explain_download
    "content": "explanation_topic",  // Only for explain
    "command": "command_to_execute", // Only for os_command
    "question": "what you need to know" // Only for clarify
  }
}

If no action is needed, use "type": "none" for the action.
""")
        
        # Join all parts with double newlines for clear separation
        return "\n\n".join(prompt_parts)
            
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
        
        # Get response from LLM
        result = self.process_raw_prompt(prompt)
        
        if not result or "response" not in result:
            return "Hello, how can I assist you today?"
            
        return result["response"]
            
    def process_raw_prompt(self, raw_prompt):
        """Process a raw prompt string directly through the LLM.
        
        This method allows for custom prompts without the standard formatting.
        Useful for scene simulation and other specialized applications.
        
        Args:
            raw_prompt: The complete prompt string to send to the LLM
            
        Returns:
            dict: Response with 'response' field containing the LLM's text output
        """
        logger.info(f"Processing raw prompt (length: {len(raw_prompt)} chars)")
        
        # If in simulation mode, return a generic response
        if self.simulation_mode:
            logger.info("Simulation mode: generating mock response for raw prompt")
            sample_responses = [
                "I understand your situation. Could you tell me more details about the problem you're experiencing?",
                "I'm here to help. Based on what you've described, I would recommend trying to restart the application first.",
                "Thank you for providing that information. Let me check if I can find a solution for you.",
                "I'll need to look into this further. Can you please confirm if this issue started recently or has been ongoing?",
                "Based on your description, this seems like a common issue that can be resolved by updating your software."
            ]
            import random
            return {
                "response": random.choice(sample_responses)
            }
        
        # Try to use the actual LLM
        try:
            if self.model_type == "llama":
                # Implementation for Ollama
                # This would need to be implemented for actual Ollama integration
                logger.warning("Raw prompt processing not implemented for Ollama")
                return {
                    "response": "I'm unable to process this request at the moment."
                }
                
            elif self.model_type == "gemini":
                # Configure the Gemini API
                genai.configure(api_key=self.model_config["gemini"]["api_key"])
                
                # Get the model
                model = genai.GenerativeModel(self.model_config["gemini"]["model_name"])
                
                # Generate content with the model
                response = model.generate_content(raw_prompt)
                
                # Return the response text
                return {
                    "response": response.text
                }
                
            elif self.model_type == "claude":
                # Implementation for Claude API
                # This would need to be implemented for actual Claude API integration
                logger.warning("Raw prompt processing not implemented for Claude")
                return {
                    "response": "I'm unable to process this request at the moment."
                }
                
        except Exception as e:
            logger.error(f"Error processing raw prompt: {e}")
            return {
                "response": "I encountered an error processing your request."
            }
    
    def validate_response(self, response, expected_action):
        """Validate the LLM response against expected action.
        
        Args:
            response: The LLM response
            expected_action: The expected action
            
        Returns:
            bool: True if action matches expected, False otherwise
        """
        if not response or not expected_action or "action" not in response:
            return False
            
        actual_action = response["action"]
        
        # Check if action type matches
        if actual_action.get("type") != expected_action.get("type"):
            logger.warning(f"Action type doesn't match. Expected: {expected_action.get('type')}, Got: {actual_action.get('type')}")
            return False
            
        # For specific action types, check additional fields
        if actual_action.get("type") == "launch_app":
            match = actual_action.get("app_name") == expected_action.get("app_name")
        elif actual_action.get("type") == "explain_download":
            match = actual_action.get("target") == expected_action.get("target")
        else:
            # Simple match for other action types
            match = True
            
        if match:
            logger.info("LLM response action matches expected action")
        else:
            logger.warning(f"LLM response action doesn't match expected action. Expected: {expected_action}, Got: {actual_action}")
            
        return match