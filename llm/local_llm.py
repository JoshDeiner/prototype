"""
LLM Provider module that interfaces with various language models.

Supports multiple LLM backends (Claude, LLaMA, Gemini) with fallbacks.
"""

import os
import json
import requests
import logging
from tools.logger import setup_logger
import config as app_config

# Setup logger
logger = setup_logger()

# Try importing Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI package not available. Install with 'pip install google-generativeai'")

class LLMProvider:
    """
    Provider for LLM services with multiple model support and fallbacks.
    """
    
    def __init__(self, model_type="llama"):
        """Initialize the LLM provider.
        
        Args:
            model_type: Type of LLM to use ('llama', 'claude', 'gemini', or 'simulation')
        """
        self.model_type = model_type
        self.simulation_mode = True  # Default to simulation for now
        
        # Check available models and set up best available
        if self._check_ollama_available() and model_type == "llama":
            self.simulation_mode = False
            logger.info(f"Initialized LLM provider with Ollama model: {app_config.LLM_PROVIDERS['llama']['model_name']}")
        # If Ollama is not available but Gemini is requested or as fallback, try Gemini
        elif (model_type == "gemini" or model_type == "llama") and self._check_gemini_available():
            self.model_type = "gemini"  # Switch to Gemini even if Llama was requested
            self.simulation_mode = False
            logger.info(f"Initialized LLM provider with Gemini model: {app_config.LLM_PROVIDERS['gemini']['model_name']}")
        # Try Claude as the last option
        elif model_type == "claude" and app_config.LLM_PROVIDERS["claude"]["api_key"]:
            self.simulation_mode = False
            logger.info(f"Initialized LLM provider with Claude model: {app_config.LLM_PROVIDERS['claude']['model_name']}")
        else:
            logger.warning(f"No {model_type} model available, using simulation mode")
    
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
            
        api_key = app_config.LLM_PROVIDERS["gemini"]["api_key"]
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
    
    def generate_response(self, prompt):
        """Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            str: The generated response text
        """
        logger.info(f"Generating response using {self.model_type} model")
        
        # If not in simulation mode, try to use the actual LLM
        if not self.simulation_mode:
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
        return self._simulate_response(prompt)
    
    def _call_ollama(self, prompt):
        """Call the Ollama API to get a response.
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            str: LLM response text
        """
        try:
            # Prepare the API request data
            data = {
                "model": app_config.LLM_PROVIDERS["llama"]["model_name"],
                "prompt": prompt,
                "stream": False
            }
            
            # Make the API request
            response = requests.post(
                app_config.LLM_PROVIDERS["llama"]["api_url"],
                json=data
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                logger.error(f"Ollama API error: Status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return None
    
    def _call_claude(self, prompt):
        """Call the Claude API to get a response.
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            str: LLM response text
        """
        try:
            # Prepare the API request
            headers = {
                "x-api-key": app_config.LLM_PROVIDERS["claude"]["api_key"],
                "Content-Type": "application/json",
                "Accept": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": app_config.LLM_PROVIDERS["claude"]["model_name"],
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000
            }
            
            # Make the API request
            response = requests.post(
                app_config.LLM_PROVIDERS["claude"]["api_url"],
                headers=headers,
                json=data
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                content = result.get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")
                return ""
            else:
                logger.error(f"Claude API error: Status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return None
    
    def _call_gemini(self, prompt):
        """Call the Gemini API to get a response.
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            str: LLM response text
        """
        try:
            # Configure the Gemini API
            genai.configure(api_key=app_config.LLM_PROVIDERS["gemini"]["api_key"])
            
            # Get the model
            model = genai.GenerativeModel(app_config.LLM_PROVIDERS["gemini"]["model_name"])
            
            # Generate content with the model
            response = model.generate_content(prompt)
            
            # Return the response text
            return response.text
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return None
    
    def _simulate_response(self, prompt):
        """Simulate an LLM response for testing purposes.
        
        Args:
            prompt: The prompt to respond to
            
        Returns:
            str: Simulated response text
        """
        # Very simple simulation that returns a generic response
        # In practice, this could be more sophisticated based on the prompt
        
        # Check for file operations
        if "file" in prompt.lower() and ".txt" in prompt.lower():
            # Extract filename using simple regex
            import re
            match = re.search(r'([a-zA-Z0-9_\-\.]+\.txt)', prompt.lower())
            if match:
                filename = match.group(1)
                return f'''{{
  "response": "I'll show you the contents of {filename}.",
  "action": {{
    "type": "os_command",
    "command": "cat {filename}"
  }}
}}'''
        
        # Check for directory listing
        if "list" in prompt.lower() and "file" in prompt.lower():
            return f'''{{
  "response": "I'll list the files in the current directory for you.",
  "action": {{
    "type": "os_command",
    "command": "ls -la"
  }}
}}'''
        
        # Default response with no action
        return f'''{{
  "response": "I'm not sure what you're asking for. Could you please be more specific about what you'd like me to help you with?",
  "action": {{
    "type": "none"
  }}
}}'''