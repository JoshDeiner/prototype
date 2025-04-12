"""
Prompt builder for generating prompts for the LLM.

This module constructs prompts based on user input, conversation history,
and optional scene context.
"""

import config as app_config
from tools.logger import setup_logger

# Setup logger
logger = setup_logger()

class PromptBuilder:
    """
    Builder for constructing prompts for the LLM.
    
    Handles standard prompts and scene-based prompts with rich context.
    """
    
    def __init__(self):
        """Initialize the prompt builder."""
        self.system_prompt = app_config.DEFAULT_SYSTEM_PROMPT
    
    def build_standard_prompt(self, user_input, conversation_history=None):
        """Build a standard prompt for the LLM.
        
        Args:
            user_input: The user's input text
            conversation_history: Optional conversation history
        
        Returns:
            str: Formatted prompt
        """
        # Add conversation context if available
        conversation = ""
        if conversation_history:
            for turn in conversation_history:
                conversation += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n\n"
                
        # Add the current user input
        conversation += f"User: {user_input}\nAssistant:"
        
        return f"{self.system_prompt}\n\n{conversation}"
    
    def build_scene_prompt(self, user_input, scene_context, conversation_history=None):
        """Build a scene-based prompt for the LLM.
        
        Args:
            user_input: The user's input text
            scene_context: Scene context dictionary
            conversation_history: Optional conversation history
        
        Returns:
            str: Formatted prompt
        """
        # Extract scene components
        roles = scene_context.get("roles", {})
        scene_description = scene_context.get("scene", "")
        constraints = scene_context.get("constraints", {})
        
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
                prompt_parts.append(f"User: {entry['user']}")
                prompt_parts.append(f"You: {entry['assistant']}")
        
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
    
    def build_opening_message_prompt(self, scene_context):
        """Build a prompt to generate an opening message for a scene.
        
        Args:
            scene_context: Scene context dictionary
        
        Returns:
            str: Formatted prompt
        """
        # Extract scene components
        roles = scene_context.get("roles", {})
        scene_description = scene_context.get("scene", "")
        
        # Build the prompt
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
        
        return prompt