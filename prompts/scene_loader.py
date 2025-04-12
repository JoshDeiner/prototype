"""
Scene loader for loading and validating scene files.

This module handles loading scene files from YAML or JSON formats.
"""

import os
import yaml
import json
from pathlib import Path
from tools.logger import setup_logger
import config as app_config

# Setup logger
logger = setup_logger()

class SceneLoader:
    """
    Loader for scene configuration files.
    
    Handles loading and validating scene files from YAML or JSON formats.
    """
    
    def __init__(self):
        """Initialize the scene loader."""
        pass
        
    def load_scene(self, scene_path):
        """Load a scene definition from a configuration file.
        
        Args:
            scene_path: Path to the scene configuration file (YAML or JSON)
            
        Returns:
            dict: Scene context if loaded successfully, None otherwise
        """
        # Check if scene_path is just a filename (no path separators)
        if isinstance(scene_path, str) and os.path.basename(scene_path) == scene_path:
            # Look in scenes directory
            alt_path = os.path.join(app_config.SCENES_DIR, scene_path)
            if os.path.exists(alt_path):
                scene_path = alt_path
            # Try with extensions if not found
            elif not os.path.exists(scene_path):
                for ext in [".yaml", ".yml", ".json"]:
                    test_path = os.path.join(app_config.SCENES_DIR, f"{scene_path}{ext}")
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
                with open(scene_path, 'r') as f:
                    scene_data = yaml.safe_load(f)
            elif ext.lower() == '.json':
                with open(scene_path, 'r') as f:
                    scene_data = json.load(f)
            else:
                logger.error(f"Unsupported scene file format: {ext}")
                return None
                
            # Validate the scene configuration
            if not self._validate_scene_config(scene_data):
                logger.error(f"Invalid scene configuration in {scene_path}")
                return None
                
            logger.info(f"Loaded scene from {scene_path}")
            return scene_data
                
        except Exception as e:
            logger.error(f"Error loading scene: {e}")
            return None
            
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
    
    def list_available_scenes(self):
        """List all available scene files in the scenes directory.
        
        Returns:
            list: List of scene file names
        """
        if not os.path.exists(config.SCENES_DIR) or not os.path.isdir(config.SCENES_DIR):
            logger.warning("Scenes directory not found")
            return []
            
        scenes = []
        for file in os.listdir(config.SCENES_DIR):
            if file.endswith(('.yaml', '.yml', '.json')):
                scenes.append(file)
                
        return scenes