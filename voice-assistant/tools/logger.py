"""
Logger setup for the voice assistant.

Provides a configured logger for consistent logging across modules.
"""

import os
import logging
import sys
from pathlib import Path

def setup_logger(name="voice_assistant", level=logging.INFO):
    """Setup and configure logger.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Check if logger already exists
    logger = logging.getLogger(name)
    
    # Only setup handlers if they don't exist
    if not logger.handlers:
        logger.setLevel(level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add formatter to handler
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        
        # Avoid duplicate logging in parent logger
        logger.propagate = False
        
    return logger