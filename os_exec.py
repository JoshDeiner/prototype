"""OS execution service for handling system actions and commands."""
import subprocess
import shlex
import os
import re
import platform
import glob
from pathlib import Path
from utils import logger

class OSExecutionService:
    def __init__(self, dry_run=True, safe_mode=True):
        """Initialize the OS execution service.
        
        Args:
            dry_run: If True, will only log commands without executing them
            safe_mode: If True, will apply safety checks on OS commands
        """
        self.dry_run = dry_run
        self.safe_mode = safe_mode
        self.system_info = self._get_system_info()
        self.dangerous_commands = [
            'rm -rf', 'mkfs', 'dd', ':(){:|:&};:', 'mv /* ', 
            'chmod -R 777', '> /dev/sda', 'wget', 'curl',
            'sudo rm', 'sudo dd'
        ]
        logger.info(f"Initialized OS execution service (dry_run={dry_run}, safe_mode={safe_mode})")
    
    def _get_system_info(self):
        """Get basic system information to assist with command execution."""
        system_info = {
            "os": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "home_dir": os.path.expanduser("~"),
            "current_dir": os.getcwd()
        }
        
        # Get more detailed OS info
        if system_info["os"] == "Linux":
            try:
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("NAME="):
                            system_info["distro"] = line.split("=")[1].strip().strip('"')
                        if line.startswith("VERSION="):
                            system_info["os_version"] = line.split("=")[1].strip().strip('"')
            except Exception:
                pass
            
        return system_info
        
    def resolve_path(self, path_str):
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
            
        # Handle special case for 'prototype' directory
        if path_str == 'prototype' or path_str.startswith('prototype/'):
            project_root = "/workspaces/codespaces-blank"
            if os.path.exists(project_root):
                prototype_path = os.path.join(project_root, path_str)
                if os.path.exists(prototype_path):
                    return prototype_path
                else:
                    # Even if it doesn't exist, this is a good guess for the prototype path
                    return prototype_path
        
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
            "/workspaces/codespaces-blank/prototype/data",  # Data directory (priority)
            os.getcwd(),  # Current directory
            "/workspaces/codespaces-blank/prototype",  # Project directory
            "/workspaces/codespaces-blank",  # Parent of project
            os.path.expanduser("~")  # Home directory
        ]
        
        for base in common_bases:
            full_path = os.path.join(base, path_str)
            if os.path.exists(full_path):
                return full_path
                
        # Return the best guess (absolute path from current directory)
        return abs_path
        
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
            if self.safe_mode and not self._is_app_safe(app_name):
                return False, f"Application '{app_name}' not allowed or not found"
                
        elif action_type == "os_command":
            command = action.get("command", "")
            if not command:
                return False, "No command specified"
                
            # Safety check for dangerous commands
            if self.safe_mode and self._is_dangerous_command(command):
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
    
    def _is_app_safe(self, app_name):
        """Check if an application is safe to launch.
        
        Args:
            app_name: Name of the application to check
            
        Returns:
            bool: True if the app is considered safe
        """
        # List of common safe applications
        safe_apps = [
            "firefox", "chromium", "chromium-browser", "chrome", "google-chrome",
            "code", "vscode", "gedit", "nano", "vim", "emacs",
            "nautilus", "thunar", "dolphin", "nemo", "pcmanfm",
            "gnome-terminal", "xterm", "konsole", "alacritty",
            "libreoffice", "abiword", "evince", "okular",
            "eog", "gthumb", "shotwell", "gimp", "inkscape",
            "vlc", "mpv", "totem", "rhythmbox", "audacity",
            "calculator", "gnome-calculator", "kcalc"
        ]
        
        return app_name.lower() in safe_apps
        
    def execute_action(self, action):
        """Execute an OS action based on the action dictionary.
        
        Args:
            action: Action dictionary
            
        Returns:
            dict: Result of the action execution
        """
        if not action or "type" not in action:
            logger.error("Invalid action format")
            return {"status": "error", "message": "Invalid action format"}
            
        # Validate the action first
        is_valid, validation_reason = self.validate_action(action)
        if not is_valid:
            logger.warning(f"Action validation failed: {validation_reason}")
            return {"status": "error", "message": validation_reason}
            
        action_type = action["type"]
        logger.info(f"Executing action: {action_type}")
        
        if action_type == "launch_app":
            return self._launch_application(action)
        elif action_type == "explain_download":
            return self._explain_download(action)
        elif action_type == "explain":
            return self._provide_explanation(action)
        elif action_type == "os_command":
            # Check if this is a file search command using find
            command = action.get("command", "")
            if command and command.startswith("find "):
                # Try to parse the find command: find <directory> -name <filename>
                command_parts = shlex.split(command)
                if len(command_parts) >= 4 and command_parts[0] == "find" and command_parts[2] == "-name":
                    search_dir = command_parts[1]
                    file_pattern = command_parts[3]
                    logger.info(f"Converting find command to recursive file search: {command}")
                    return self._recursive_file_search(search_dir, file_pattern)
            
            # Regular command execution
            return self._execute_os_command(action)
        elif action_type == "file_check":
            return self._check_file_exists(action)
        elif action_type == "dir_search":
            return self._search_directory(action)
        elif action_type == "none":
            return {"status": "success", "message": "No action required"}
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return {"status": "error", "message": f"Unknown action type: {action_type}"}
    
    def _launch_application(self, action):
        """Launch an application.
        
        Args:
            action: Action dictionary with app_name
            
        Returns:
            dict: Result of the action execution
        """
        app_name = action.get("app_name", "")
        if not app_name:
            return {"status": "error", "message": "No application name specified"}
            
        command = f"{app_name}"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {command}")
            return {"status": "success", "message": f"Would launch {app_name}", "dry_run": True}
        else:
            try:
                # In production, this would use subprocess to launch the application
                logger.info(f"Launching application: {app_name}")
                subprocess.Popen([app_name], start_new_session=True)
                return {"status": "success", "message": f"Launched {app_name}"}
            except Exception as e:
                logger.error(f"Error launching {app_name}: {e}")
                return {"status": "error", "message": f"Error launching {app_name}: {e}"}
    
    def _execute_os_command(self, action):
        """Execute an OS command.
        
        Args:
            action: Action dictionary with command
            
        Returns:
            dict: Result of the action execution
        """
        command = action.get("command", "")
        if not command:
            return {"status": "error", "message": "No command specified"}
        
        # Safety check for dangerous commands
        if self.safe_mode and self._is_dangerous_command(command):
            error_msg = f"Potentially dangerous command detected: {command}"
            logger.warning(error_msg)
            return {
                "status": "error", 
                "message": error_msg,
                "command": command,
                "needs_confirmation": True
            }
        
        # Check for special case - find command
        command_parts = shlex.split(command)
        if len(command_parts) > 0:
            cmd = command_parts[0]
            
            # Special handling for find command to use our recursive file search
            if cmd == 'find' and len(command_parts) >= 3:
                # Typical format: find <directory> -name <filename>
                if command_parts[2] == '-name' and len(command_parts) >= 4:
                    search_dir = command_parts[1]
                    file_pattern = command_parts[3]
                    
                    # Use our internal recursive file search
                    return self._recursive_file_search(search_dir, file_pattern)
            
            # Special case for "sudo find" command
            elif cmd == 'sudo' and len(command_parts) >= 2 and command_parts[1] == 'find' and len(command_parts) >= 5:
                # Typical format: sudo find <directory> -name <filename>
                if command_parts[3] == '-name' and len(command_parts) >= 5:
                    search_dir = command_parts[2]
                    file_pattern = command_parts[4]
                    
                    # Use our internal recursive file search without sudo
                    logger.info(f"Converting sudo find command to recursive file search: {command}")
                    return self._recursive_file_search(search_dir, file_pattern)
            
            # Check for path patterns in commands like cat, ls, etc.
            file_operation_commands = ['cat', 'ls', 'cd', 'vim', 'nano', 'grep', 'cp', 'mv', 'rm', 'touch', 'mkdir', 'rmdir']
            
            # Special case for "cat browser_scenario.json" 
            if cmd == 'cat' and len(command_parts) > 1:
                # Check for known problematic files
                if command_parts[1] == 'browser_scenario.json':
                    # Try to find this special file using our recursive search
                    logger.info(f"Special handling for cat browser_scenario.json")
                    search_result = self._recursive_file_search("/workspaces/codespaces-blank/prototype", "browser_scenario.json")
                    
                    if search_result["status"] == "success" and search_result.get("files_found", 0) > 0:
                        # Extract the file path from the search result
                        file_path = search_result["stdout"].strip().split("\n")[0]
                        
                        # Replace the command with the full path
                        command_parts[1] = file_path
                        command = ' '.join(command_parts)
                        logger.info(f"Updated cat command with full path: {command}")
            
            # If this is a file operation command (and not just the command alone)
            if cmd in file_operation_commands and len(command_parts) > 1:
                # Process each argument that might be a path (except for flags)
                for i in range(1, len(command_parts)):
                    arg = command_parts[i]
                    
                    # Skip flags/options that start with '-'
                    if arg.startswith('-'):
                        continue
                        
                    # Check if this argument looks like a path
                    if '/' in arg or '.' in arg or not arg.startswith('-'):
                        # Try to resolve the path
                        resolved_path = self.resolve_path(arg)
                        
                        # Replace the original path with resolved path
                        if resolved_path != arg:
                            logger.info(f"Resolved path: '{arg}' -> '{resolved_path}'")
                            command_parts[i] = resolved_path
                
                # Reconstruct command with resolved paths
                command = ' '.join(command_parts)
                logger.info(f"Command with resolved paths: {command}")
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute OS command: {command}")
            return {
                "status": "success", 
                "message": f"Would execute command: {command}", 
                "command": command,
                "dry_run": True
            }
        else:
            try:
                logger.info(f"Executing OS command: {command}")
                # For security, we use shell=False and pass args as a list
                args = shlex.split(command)
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(timeout=60)
                
                if process.returncode == 0:
                    return {
                        "status": "success",
                        "message": f"Command executed successfully",
                        "command": command,
                        "stdout": stdout,
                        "stderr": stderr,
                        "returncode": process.returncode
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Command failed with return code {process.returncode}",
                        "command": command,
                        "stdout": stdout,
                        "stderr": stderr,
                        "returncode": process.returncode
                    }
            except Exception as e:
                logger.error(f"Error executing command '{command}': {e}")
                return {
                    "status": "error", 
                    "message": f"Error executing command: {e}",
                    "command": command
                }
    
    def _is_dangerous_command(self, command):
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
    
    def _explain_download(self, action):
        """Provide download instructions for a target application.
        
        Args:
            action: Action dictionary with target
            
        Returns:
            dict: Result of the action execution
        """
        target = action.get("target", "")
        if not target:
            return {"status": "error", "message": "No target specified"}
            
        logger.info(f"Explaining download for: {target}")
        return {"status": "success", "message": f"Explained download for {target}"}
    
    def _provide_explanation(self, action):
        """Provide an explanation for a topic.
        
        Args:
            action: Action dictionary with content
            
        Returns:
            dict: Result of the action execution
        """
        content = action.get("content", "")
        if not content:
            return {"status": "error", "message": "No content specified"}
            
        logger.info(f"Providing explanation for: {content}")
        return {"status": "success", "message": f"Provided explanation for {content}"}
        
    def _check_file_exists(self, action):
        """Check if a file exists and return information about it.
        
        Args:
            action: Action dictionary with file_path
            
        Returns:
            dict: Result with file info if found
        """
        file_path = action.get("file_path", "")
        if not file_path:
            return {"status": "error", "message": "No file path specified"}
        
        # Check if file has a directory component, if not, first check in data directory
        if os.path.dirname(file_path) == "":
            data_dir = "/workspaces/codespaces-blank/prototype/data"
            data_path = os.path.join(data_dir, file_path)
            
            # If file exists in data directory, use that
            if os.path.exists(data_path) and os.path.isfile(data_path):
                logger.info(f"File found in data directory: {data_path}")
                resolved_path = data_path
            else:
                # Otherwise, use the standard resolution
                resolved_path = self.resolve_path(file_path)
        else:
            # If directory is specified, use the standard resolution
            resolved_path = self.resolve_path(file_path)
            
        logger.info(f"Checking if file exists: {resolved_path}")
        
        try:
            if os.path.exists(resolved_path):
                if os.path.isfile(resolved_path):
                    # Get file info
                    stats = os.stat(resolved_path)
                    file_type = "text" if self._is_text_file(resolved_path) else "binary"
                    
                    return {
                        "status": "success",
                        "message": f"File found: {resolved_path}",
                        "file_exists": True,
                        "file_path": resolved_path,
                        "is_file": True,
                        "size": stats.st_size,
                        "file_type": file_type,
                        "extension": os.path.splitext(resolved_path)[1],
                        "absolute_path": os.path.abspath(resolved_path)
                    }
                else:
                    # It's a directory, not a file
                    return {
                        "status": "success",
                        "message": f"Path exists but is a directory: {resolved_path}",
                        "file_exists": False,
                        "is_directory": True,
                        "path": resolved_path,
                        "absolute_path": os.path.abspath(resolved_path)
                    }
            else:
                # The file doesn't exist, try to find similar files
                file_name = os.path.basename(resolved_path)
                dir_path = os.path.dirname(resolved_path)
                
                # If no directory is specified, use current directory
                if not dir_path:
                    dir_path = os.getcwd()
                    
                similar_files = self._find_similar_files(file_name, dir_path)
                
                return {
                    "status": "success",
                    "message": f"File not found: {resolved_path}",
                    "file_exists": False,
                    "searched_path": resolved_path,
                    "absolute_path": os.path.abspath(resolved_path),
                    "similar_files": similar_files
                }
        except Exception as e:
            logger.error(f"Error checking file: {e}")
            return {
                "status": "error",
                "message": f"Error checking file: {e}"
            }
            
    def _search_directory(self, action):
        """Search for a directory by name.
        
        Args:
            action: Action dictionary with dir_name
            
        Returns:
            dict: Result with matching directories
        """
        dir_name = action.get("dir_name", "")
        if not dir_name:
            return {"status": "error", "message": "No directory name specified"}
            
        logger.info(f"Searching for directory: {dir_name}")
        
        try:
            # List of common base directories to search
            search_paths = [
                os.getcwd(),  # Current directory
                os.path.dirname(os.getcwd()),  # Parent directory
                "/workspaces/codespaces-blank",  # Project root
                os.path.expanduser("~")  # Home directory
            ]
            
            results = []
            
            # First try the exact name as a path
            resolved_path = self.resolve_path(dir_name)
            if os.path.exists(resolved_path) and os.path.isdir(resolved_path):
                results.append({
                    "path": resolved_path,
                    "is_exact_match": True,
                    "abs_path": os.path.abspath(resolved_path)
                })
                
            # Then search for the directory name in common locations
            for base_path in search_paths:
                for root, dirs, _ in os.walk(base_path, topdown=True, followlinks=False):
                    # Skip venv and hidden directories for efficiency
                    dirs[:] = [d for d in dirs if d != "venv" and not d.startswith(".")]
                    
                    # Check depth to avoid going too deep
                    depth = root[len(base_path):].count(os.sep)
                    if depth > 3:  # Limit search depth
                        dirs[:] = []
                        continue
                        
                    # Check each directory for a match
                    for d in dirs:
                        if dir_name.lower() in d.lower():
                            full_path = os.path.join(root, d)
                            results.append({
                                "path": full_path,
                                "name": d,
                                "abs_path": os.path.abspath(full_path),
                                "is_exact_match": d.lower() == dir_name.lower()
                            })
                            
            # Stop if we have too many results
            if len(results) > 20:
                results = results[:20]
                
            return {
                "status": "success",
                "message": f"Found {len(results)} directories matching '{dir_name}'",
                "searched_for": dir_name,
                "directories": results
            }
        except Exception as e:
            logger.error(f"Error searching for directory: {e}")
            return {
                "status": "error",
                "message": f"Error searching for directory: {e}"
            }
            
    def _is_text_file(self, file_path, sample_size=512):
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
            
    def _find_similar_files(self, file_name, directory):
        """Find files with similar names to the one provided.
        
        Args:
            file_name: The file name to compare against
            directory: The directory to search in
            
        Returns:
            list: List of similar files found
        """
        import difflib
        
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
    
    def get_system_info_string(self):
        """Get system information as a formatted string for the LLM."""
        info = self.system_info
        info_str = f"Operating System: {info['os']}"
        
        if 'distro' in info:
            info_str += f" ({info['distro']} {info.get('os_version', '')})"
            
        info_str += f"\nVersion: {info['release']} {info['version']}"
        info_str += f"\nArchitecture: {info['machine']}"
        info_str += f"\nProcessor: {info['processor']}"
        info_str += f"\nPython Version: {info['python_version']}"
        info_str += f"\nCurrent Directory: {info['current_dir']}"
        
        return info_str
        
    def _recursive_file_search(self, search_dir, file_pattern, max_depth=5, max_results=20):
        """Perform a recursive file search (similar to the find command).
        
        Args:
            search_dir: Directory to search in
            file_pattern: File name or pattern to search for
            max_depth: Maximum directory depth to search
            max_results: Maximum number of results to return
            
        Returns:
            dict: Search results
        """
        logger.info(f"Performing recursive file search for '{file_pattern}' in '{search_dir}'")
        
        # Resolve the search directory path
        search_dir = self.resolve_path(search_dir)
        
        # Check if the search directory exists
        if not os.path.exists(search_dir):
            return {
                "status": "error",
                "message": f"Search directory not found: {search_dir}",
                "command": f"find {search_dir} -name {file_pattern}",
                "stdout": "",
                "stderr": f"find: '{search_dir}': No such file or directory",
                "returncode": 1
            }
        
        if not os.path.isdir(search_dir):
            return {
                "status": "error",
                "message": f"Search path is not a directory: {search_dir}",
                "command": f"find {search_dir} -name {file_pattern}",
                "stdout": "",
                "stderr": f"find: '{search_dir}': Not a directory",
                "returncode": 1
            }
        
        # Check if pattern has wildcards
        has_wildcards = "*" in file_pattern or "?" in file_pattern
        
        results = []
        try:
            for root, dirs, files in os.walk(search_dir, topdown=True, followlinks=False):
                # Skip venv and hidden directories
                dirs[:] = [d for d in dirs if d != "venv" and not d.startswith(".")]
                
                # Check depth
                rel_path = os.path.relpath(root, search_dir)
                depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
                if depth > max_depth:
                    dirs[:] = []  # Don't go deeper
                    continue
                
                # Check each file for a match
                for file in files:
                    match = False
                    
                    if has_wildcards:
                        # Use glob pattern matching
                        match = glob.fnmatch.fnmatch(file, file_pattern)
                    else:
                        # Use exact match or substring match
                        match = (file == file_pattern) or (file_pattern in file)
                    
                    if match:
                        full_path = os.path.join(root, file)
                        results.append(full_path)
                        
                        # Limit results
                        if len(results) >= max_results:
                            break
                
                # Break early if we have enough results
                if len(results) >= max_results:
                    break
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during file search: {e}",
                "command": f"find {search_dir} -name {file_pattern}",
                "stdout": "",
                "stderr": str(e),
                "returncode": 1
            }
        
        # Format results as find command would
        stdout = "\n".join(results)
        
        return {
            "status": "success" if results else "error",
            "message": f"Found {len(results)} files matching '{file_pattern}' in '{search_dir}'",
            "command": f"find {search_dir} -name {file_pattern}",
            "stdout": stdout,
            "stderr": "" if results else f"No files matching '{file_pattern}' found in '{search_dir}'",
            "returncode": 0 if results else 1,
            "files_found": len(results),
            "search_dir": search_dir,
            "file_pattern": file_pattern
        }