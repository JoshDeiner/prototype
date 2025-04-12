"""
File utilities for the voice assistant.

Provides helper functions for file path resolution and similarity checking.
"""

import os
import glob
import difflib
from pathlib import Path

import config as app_config
from tools.logger import setup_logger

# Setup logger
logger = setup_logger()

def resolve_path(path_str):
    """Resolve a path string to its absolute form, handling relative paths.
    
    Args:
        path_str: A file or directory path that may be relative or contain wildcards
        
    Returns:
        str: Resolved absolute path
    """
    # Handle empty path
    if not path_str:
        return os.getcwd()
        
    # Replace ~ with home directory
    if path_str.startswith("~"):
        path_str = os.path.expanduser(path_str)
        
    # If it's already absolute, just normalize it
    if os.path.isabs(path_str):
        return os.path.normpath(path_str)
        
    # If it's a relative path, make it absolute from current directory
    abs_path = os.path.abspath(path_str)
    
    # Check if path exists
    if os.path.exists(abs_path):
        return abs_path
        
    # Try to resolve wildcards
    if "*" in path_str:
        matches = glob.glob(path_str)
        if matches:
            return os.path.abspath(matches[0])
            
    # If we still don't have a valid path, try common base directories
    common_bases = [
        str(app_config.DATA_DIR),  # Data directory (priority)
        os.getcwd(),  # Current directory
        str(app_config.ROOT_DIR),  # Project directory
        os.path.expanduser("~")  # Home directory
    ]
    
    for base in common_bases:
        full_path = os.path.join(base, path_str)
        if os.path.exists(full_path):
            return full_path
            
    # Return the best guess (absolute path from current directory)
    return abs_path

def find_similar_files(file_name, directory):
    """Find files with similar names to the one provided.
    
    Args:
        file_name: The file name to compare against
        directory: The directory to search in
        
    Returns:
        list: List of similar files found
    """
    similar_files = []
    
    try:
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return []
            
        # Get all files in the directory
        all_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        
        # Get file name without extension
        base_name = os.path.splitext(file_name)[0]
        
        # Find files with similar names
        for f in all_files:
            # Calculate similarity scores
            name_similarity = difflib.SequenceMatcher(None, file_name, f).ratio()
            basename_similarity = difflib.SequenceMatcher(None, base_name, os.path.splitext(f)[0]).ratio()
            
            # Use the higher of the two similarity scores
            similarity = max(name_similarity, basename_similarity)
            
            # Include files above a certain similarity threshold
            if similarity > 0.5:
                full_path = os.path.join(directory, f)
                similar_files.append({
                    "name": f,
                    "path": full_path,
                    "similarity": round(similarity, 2),
                    "size": os.path.getsize(full_path)
                })
                
        # Sort by similarity (highest first)
        similar_files.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Limit the number of results
        return similar_files[:5]
        
    except Exception as e:
        logger.error(f"Error finding similar files: {e}")
        return []

def is_text_file(file_path, sample_size=512):
    """Check if a file is a text file by looking for binary characters.
    
    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample
        
    Returns:
        bool: True if the file is likely a text file
    """
    try:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
            
        # Standard text extensions
        text_extensions = ['.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.csv', '.xml', '.yaml', '.yml']
        ext = os.path.splitext(file_path)[1].lower()
        
        # Fast check based on extension
        if ext in text_extensions:
            return True
            
        # Check file content for binary characters
        with open(file_path, 'rb') as f:
            chunk = f.read(sample_size)
            
        # If it contains null bytes or too many non-ASCII chars, it's likely binary
        if b'\x00' in chunk:
            return False
            
        # Count non-ASCII characters
        non_ascii = len([b for b in chunk if b > 127])
        
        # If more than 30% are non-ASCII, likely binary
        return (non_ascii / len(chunk)) < 0.3 if chunk else True
        
    except Exception:
        return False

def ensure_directory(directory):
    """Create directory if it doesn't exist.
    
    Args:
        directory: Directory path to create
        
    Returns:
        bool: True if directory exists or was created
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False