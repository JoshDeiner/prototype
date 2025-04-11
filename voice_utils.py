"""Utility functions for the voice-enabled help desk AI."""
import json
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def load_scenario(scenario_path):
    """Load a scenario definition from a JSON file.
    
    Args:
        scenario_path: Path to the scenario JSON file
        
    Returns:
        dict: The scenario definition
    """
    try:
        with open(scenario_path, 'r') as f:
            scenario = json.load(f)
        logger.info(f"Loaded scenario from {scenario_path}")
        return scenario
    except Exception as e:
        logger.error(f"Error loading scenario: {e}")
        return None

def ensure_directory(directory):
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure exists
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")