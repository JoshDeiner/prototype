"""
Configuration settings for the Voice Assistant.

This module contains all configuration constants, paths, and default templates.
"""

import os
import yaml
from pathlib import Path

# Base directories
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get DATA_DIR from environment variable if set, otherwise use default
DATA_DIR = Path(os.environ.get('DATA_DIR', str(ROOT_DIR / "data")))
SCENES_DIR = Path(os.environ.get('SCENES_DIR', str(ROOT_DIR / "scenes")))  # Use the original scenes directory

# Log the actual paths being used
from tools.logger import setup_logger
logger = setup_logger()
logger.info(f"Using DATA_DIR: {DATA_DIR}")
logger.info(f"Using SCENES_DIR: {SCENES_DIR}")
OUTPUT_DIR = ROOT_DIR / "output" / "scenes"

# Default configuration
DEFAULT_CONFIG = {
    "llm_model": "gemini",
    "dry_run": False,
    "safe_mode": True,
    "auto_confirm": True,
    "delay": 0.5,
    "scene_path": None,
    "max_history": 5,
    "max_retries": 3
}

# Supported LLM providers
LLM_PROVIDERS = {
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

# Dangerous commands to block in safe mode
DANGEROUS_COMMANDS = [
    'rm -rf', 'mkfs', 'dd', ':(){:|:&};:', 'mv /* ', 
    'chmod -R 777', '> /dev/sda', 'wget', 'curl',
    'sudo rm', 'sudo dd'
]

# Safe applications that can be launched
SAFE_APPLICATIONS = [
    "firefox", "chromium", "chromium-browser", "chrome", "google-chrome",
    "code", "vscode", "gedit", "nano", "vim", "emacs",
    "nautilus", "thunar", "dolphin", "nemo", "pcmanfm",
    "gnome-terminal", "xterm", "konsole", "alacritty",
    "libreoffice", "abiword", "evince", "okular",
    "eog", "gthumb", "shotwell", "gimp", "inkscape",
    "vlc", "mpv", "totem", "rhythmbox", "audacity",
    "calculator", "gnome-calculator", "kcalc"
]

# Default system prompt template
DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant for a Raspberry Pi OS help desk. 
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

def load_scene(scene_path):
    """
    Load a scene configuration from file.
    
    Args:
        scene_path: Path to scene file
        
    Returns:
        dict: Scene configuration or None if loading failed
    """
    # Check if scene_path is just a filename (no path separators)
    if isinstance(scene_path, str) and os.path.basename(scene_path) == scene_path:
        # Look in scenes directory
        alt_path = os.path.join(SCENES_DIR, scene_path)
        if os.path.exists(alt_path):
            scene_path = alt_path
        # Try with extensions if not found
        elif not os.path.exists(scene_path):
            for ext in [".yaml", ".yml", ".json"]:
                test_path = os.path.join(SCENES_DIR, f"{scene_path}{ext}")
                if os.path.exists(test_path):
                    scene_path = test_path
                    break
    
    # Check if file exists
    if not os.path.exists(scene_path):
        return None
        
    try:
        # Determine file type by extension
        _, ext = os.path.splitext(scene_path)
        
        # Load based on file type
        if ext.lower() in ['.yaml', '.yml']:
            with open(scene_path, 'r') as f:
                scene_data = yaml.safe_load(f)
        elif ext.lower() == '.json':
            import json
            with open(scene_path, 'r') as f:
                scene_data = json.load(f)
        else:
            return None
            
        return scene_data
    except Exception:
        return None