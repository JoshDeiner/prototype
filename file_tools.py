"""File operation tools hierarchy for handling different file-related requests."""
import os
import glob
import mimetypes
import difflib
from pathlib import Path
from utils import logger

class FileToolBase:
    """Base class for all file operation tools."""
    
    def __init__(self, file_path=None):
        """Initialize the file tool with an optional file path.
        
        Args:
            file_path: Optional path to the file
        """
        self.file_path = file_path
        self.resolved_path = None
        self.file_info = {}
    
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
    
    def validate(self):
        """Validate if the file exists and can be accessed.
        
        Returns:
            tuple: (is_valid, message)
        """
        if not self.file_path:
            return False, "No file path specified"
            
        self.resolved_path = self.resolve_path(self.file_path)
        
        # Check if path exists
        if not os.path.exists(self.resolved_path):
            similar_files = self._find_similar_files(
                os.path.basename(self.resolved_path), 
                os.path.dirname(self.resolved_path) or os.getcwd()
            )
            
            return False, {
                "message": f"File not found: {self.resolved_path}",
                "searched_path": self.resolved_path,
                "similar_files": similar_files
            }
            
        # Check if it's a file, not a directory
        if not os.path.isfile(self.resolved_path):
            return False, {
                "message": f"Path exists but is a directory: {self.resolved_path}",
                "path": self.resolved_path,
                "is_directory": True
            }
            
        try:
            # Basic file info
            stats = os.stat(self.resolved_path)
            
            # Actually check if we can read the file
            with open(self.resolved_path, 'r') as f:
                first_line = f.readline()
                is_readable = True
            
            # Determine file type - more accurately now
            file_type = self._determine_file_type(self.resolved_path)
            
            # Count lines for better information
            line_count = sum(1 for _ in open(self.resolved_path))
            
            self.file_info = {
                "file_path": self.resolved_path,
                "size": stats.st_size,
                "file_type": file_type,
                "extension": os.path.splitext(self.resolved_path)[1],
                "absolute_path": os.path.abspath(self.resolved_path),
                "is_binary": file_type != "text",
                "line_count": line_count,
                "is_empty": stats.st_size == 0
            }
            
            return True, {
                "message": f"File found: {self.resolved_path}",
                "file_info": self.file_info
            }
            
        except UnicodeDecodeError:
            # Handle binary files more gracefully
            stats = os.stat(self.resolved_path)
            self.file_info = {
                "file_path": self.resolved_path,
                "size": stats.st_size,
                "file_type": "binary",
                "extension": os.path.splitext(self.resolved_path)[1],
                "absolute_path": os.path.abspath(self.resolved_path),
                "is_binary": True,
                "is_empty": stats.st_size == 0
            }
            
            return True, {
                "message": f"Binary file found: {self.resolved_path}",
                "file_info": self.file_info
            }
        except Exception as e:
            # If any other error occurs during validation
            logger.error(f"Error validating file {self.resolved_path}: {e}")
            return False, {
                "message": f"Error validating file: {e}",
                "file_path": self.resolved_path
            }
    
    def _determine_file_type(self, file_path, sample_size=512):
        """Determine the type of a file (text, binary, etc).
        
        Args:
            file_path: Path to the file
            sample_size: Number of bytes to sample
            
        Returns:
            str: File type description
        """
        # Get mime type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Standard text extensions
        text_extensions = ['.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.csv', '.xml', '.yaml', '.yml']
        ext = os.path.splitext(file_path)[1].lower()
        
        # Fast check based on extension
        if ext in text_extensions:
            return "text"
        
        # Image formats
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        if ext in image_extensions:
            return "image"
            
        # Document formats
        doc_extensions = ['.pdf', '.doc', '.docx', '.odt', '.rtf']
        if ext in doc_extensions:
            return "document"
            
        # If we have a mime type
        if mime_type:
            if mime_type.startswith('text/'):
                return "text"
            elif mime_type.startswith('image/'):
                return "image"
            elif mime_type.startswith('video/'):
                return "video"
            elif mime_type.startswith('audio/'):
                return "audio"
            elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return "document"
                
        # Check file content for binary characters
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(sample_size)
                
            # If it contains null bytes, it's likely binary
            if b'\x00' in chunk:
                return "binary"
                
            # Count non-ASCII characters
            non_ascii = len([b for b in chunk if b > 127])
            
            # If more than 30% are non-ASCII, likely binary
            if chunk and (non_ascii / len(chunk)) < 0.3:
                return "text"
            else:
                return "binary"
        except Exception:
            return "unknown"
    
    def _find_similar_files(self, file_name, directory):
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


class FileReader(FileToolBase):
    """Tool for reading file contents."""
    
    def __init__(self, file_path=None):
        """Initialize the file reader.
        
        Args:
            file_path: Path to the file to read
        """
        super().__init__(file_path)
        
    def read(self, offset=0, limit=None):
        """Read the contents of the file.
        
        Args:
            offset: Line number to start reading from (0-based)
            limit: Maximum number of lines to read
            
        Returns:
            dict: Result of the read operation
        """
        # First validate the file
        is_valid, message = self.validate()
        if not is_valid:
            return {
                "status": "error",
                "message": message.get("message") if isinstance(message, dict) else message,
                "details": message if isinstance(message, dict) else {}
            }
            
        # Check if it's a binary file
        if self.file_info.get("is_binary", False) and self.file_info.get("file_type") != "text":
            return {
                "status": "error",
                "message": f"Cannot read binary file directly: {self.resolved_path}",
                "details": {
                    "file_type": self.file_info.get("file_type", "binary"),
                    "file_path": self.resolved_path,
                    "requires_app": True
                }
            }
            
        # Read the file
        try:
            with open(self.resolved_path, 'r') as f:
                lines = f.readlines()
                
            # Apply offset and limit
            if offset > 0:
                lines = lines[offset:]
                
            if limit:
                lines = lines[:limit]
                
            content = ''.join(lines)
            
            return {
                "status": "success",
                "message": f"Successfully read file: {self.resolved_path}",
                "content": content,
                "file_path": self.resolved_path,
                "file_info": self.file_info,
                "line_count": len(lines),
                "total_lines": sum(1 for _ in open(self.resolved_path))
            }
            
        except Exception as e:
            logger.error(f"Error reading file {self.resolved_path}: {e}")
            return {
                "status": "error",
                "message": f"Error reading file: {e}",
                "file_path": self.resolved_path
            }


class DirectoryLister(FileToolBase):
    """Tool for listing directory contents."""
    
    def __init__(self, dir_path=None):
        """Initialize the directory lister.
        
        Args:
            dir_path: Path to the directory to list
        """
        super().__init__(dir_path)
        
    def list(self, pattern=None, include_dirs=True, include_files=True):
        """List the contents of a directory.
        
        Args:
            pattern: Optional glob pattern to filter results
            include_dirs: Whether to include directories in results
            include_files: Whether to include files in results
            
        Returns:
            dict: Result of the list operation
        """
        if not self.file_path:
            self.file_path = os.getcwd()
            
        self.resolved_path = self.resolve_path(self.file_path)
        
        # Check if path exists and is a directory
        if not os.path.exists(self.resolved_path):
            return {
                "status": "error",
                "message": f"Directory not found: {self.resolved_path}",
                "searched_path": self.resolved_path
            }
            
        if not os.path.isdir(self.resolved_path):
            return {
                "status": "error",
                "message": f"Path exists but is not a directory: {self.resolved_path}",
                "path": self.resolved_path,
                "is_file": True
            }
            
        try:
            # Get directory contents
            contents = []
            with os.scandir(self.resolved_path) as entries:
                for entry in entries:
                    # Skip hidden files/dirs starting with .
                    if entry.name.startswith('.'):
                        continue
                        
                    # Apply pattern filter if specified
                    if pattern and not glob.fnmatch.fnmatch(entry.name, pattern):
                        continue
                        
                    # Apply type filter
                    if (entry.is_dir() and not include_dirs) or (entry.is_file() and not include_files):
                        continue
                        
                    # Get basic info
                    try:
                        stats = entry.stat()
                        item = {
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": entry.is_dir(),
                            "size": stats.st_size if entry.is_file() else None,
                            "modified": stats.st_mtime
                        }
                        contents.append(item)
                    except Exception as e:
                        logger.warning(f"Error getting stats for {entry.path}: {e}")
                        
            # Sort contents: directories first, then by name
            contents.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            
            return {
                "status": "success",
                "message": f"Successfully listed directory: {self.resolved_path}",
                "dir_path": self.resolved_path,
                "contents": contents,
                "pattern": pattern,
                "count": len(contents)
            }
            
        except Exception as e:
            logger.error(f"Error listing directory {self.resolved_path}: {e}")
            return {
                "status": "error",
                "message": f"Error listing directory: {e}",
                "dir_path": self.resolved_path
            }


class DirectorySearcher(FileToolBase):
    """Tool for searching for directories."""
    
    def __init__(self, search_name=None):
        """Initialize the directory searcher.
        
        Args:
            search_name: Name of the directory to search for
        """
        super().__init__(search_name)
        
    def search(self, max_depth=3, max_results=20):
        """Search for directories matching the specified name.
        
        Args:
            max_depth: Maximum directory depth to search
            max_results: Maximum number of results to return
            
        Returns:
            dict: Result of the search operation
        """
        if not self.file_path:
            return {
                "status": "error",
                "message": "No directory name specified for search"
            }
            
        search_name = self.file_path
        
        # List of common base directories to search
        search_paths = [
            os.getcwd(),  # Current directory
            os.path.dirname(os.getcwd()),  # Parent directory
            "/workspaces/codespaces-blank",  # Project root
            "/workspaces/codespaces-blank/prototype",  # Prototype directory
            os.path.expanduser("~")  # Home directory
        ]
        
        results = []
        
        # First try the exact name as a path
        resolved_path = self.resolve_path(search_name)
        if os.path.exists(resolved_path) and os.path.isdir(resolved_path):
            results.append({
                "path": resolved_path,
                "is_exact_match": True,
                "abs_path": os.path.abspath(resolved_path)
            })
            
        # Then search for the directory name in common locations
        for base_path in search_paths:
            try:
                for root, dirs, _ in os.walk(base_path, topdown=True, followlinks=False):
                    # Skip venv and hidden directories for efficiency
                    dirs[:] = [d for d in dirs if d != "venv" and not d.startswith(".")]
                    
                    # Check depth to avoid going too deep
                    depth = root[len(base_path):].count(os.sep)
                    if depth > max_depth:
                        dirs[:] = []
                        continue
                        
                    # Check each directory for a match
                    for d in dirs:
                        if search_name.lower() in d.lower():
                            full_path = os.path.join(root, d)
                            results.append({
                                "path": full_path,
                                "name": d,
                                "abs_path": os.path.abspath(full_path),
                                "is_exact_match": d.lower() == search_name.lower()
                            })
            except Exception as e:
                logger.warning(f"Error searching in {base_path}: {e}")
                    
        # Sort results: exact matches first, then by path length
        results.sort(key=lambda x: (not x.get("is_exact_match", False), len(x.get("path", ""))))
        
        # Limit the number of results
        if len(results) > max_results:
            results = results[:max_results]
            
        return {
            "status": "success",
            "message": f"Found {len(results)} directories matching '{search_name}'",
            "searched_for": search_name,
            "directories": results
        }


class FileSearcher(FileToolBase):
    """Tool for recursively searching for files by name."""
    
    def __init__(self, search_name=None):
        """Initialize the file searcher.
        
        Args:
            search_name: Name or pattern of the file to search for
        """
        super().__init__(search_name)
        
    def search(self, max_depth=5, max_results=20, search_path=None):
        """Search for files matching the specified name or pattern.
        
        Args:
            max_depth: Maximum directory depth to search
            max_results: Maximum number of results to return
            search_path: Specific directory to search in (if None, will use common search paths)
            
        Returns:
            dict: Result of the search operation
        """
        if not self.file_path:
            return {
                "status": "error",
                "message": "No file name or pattern specified for search"
            }
            
        search_name = self.file_path
        case_sensitive = not search_name.islower()  # If input has uppercase, search is case-sensitive
        
        # Check if search_name contains wildcards
        has_wildcards = '*' in search_name or '?' in search_name
        
        # Determine search paths based on input
        search_paths = []
        
        if search_path:
            # If a specific search path is provided, use only that
            if os.path.exists(search_path) and os.path.isdir(search_path):
                search_paths = [os.path.abspath(search_path)]
            else:
                # If the path doesn't exist, try to resolve it
                resolved_path = self.resolve_path(search_path)
                if os.path.exists(resolved_path) and os.path.isdir(resolved_path):
                    search_paths = [resolved_path]
                else:
                    return {
                        "status": "error",
                        "message": f"Search path not found: {search_path}"
                    }
        else:
            # Use common base directories for search
            search_paths = [
                os.getcwd(),  # Current directory
                "/workspaces/codespaces-blank/prototype",  # Prototype directory (high priority)
                "/workspaces/codespaces-blank",  # Project root
                os.path.dirname(os.getcwd()) if not os.getcwd() == "/" else None,  # Parent directory
                os.path.expanduser("~") if os.path.expanduser("~") != "/" else None  # Home directory if not root
            ]
            # Remove any None entries
            search_paths = [p for p in search_paths if p]
        
        results = []
        searched_dirs = set()  # Keep track of searched directories to avoid duplicates
        
        # First try exact match with resolved path
        if not has_wildcards:
            resolved_path = self.resolve_path(search_name)
            if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
                file_stats = os.stat(resolved_path)
                results.append({
                    "path": resolved_path,
                    "name": os.path.basename(resolved_path),
                    "abs_path": os.path.abspath(resolved_path),
                    "is_exact_match": True,
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        
        # Search in specified directories
        for base_path in search_paths:
            # Skip if we've already searched this directory
            if base_path in searched_dirs:
                continue
                
            searched_dirs.add(base_path)
            
            try:
                for root, dirs, files in os.walk(base_path, topdown=True, followlinks=False):
                    # Skip hidden directories and venv for efficiency
                    dirs[:] = [d for d in dirs if d != "venv" and not d.startswith(".")]
                    
                    # Check depth to avoid going too deep
                    depth = root[len(base_path):].count(os.sep)
                    if depth > max_depth:
                        dirs[:] = []  # Don't go deeper
                        continue
                    
                    # Check each file for a match
                    for file in files:
                        match = False
                        
                        if has_wildcards:
                            # Use glob pattern matching
                            match = glob.fnmatch.fnmatch(file, search_name)
                        else:
                            # Use substring matching with case sensitivity option
                            if case_sensitive:
                                match = search_name in file
                            else:
                                match = search_name.lower() in file.lower()
                                
                        if match:
                            full_path = os.path.join(root, file)
                            try:
                                file_stats = os.stat(full_path)
                                results.append({
                                    "path": full_path,
                                    "name": file,
                                    "abs_path": os.path.abspath(full_path),
                                    "is_exact_match": file.lower() == search_name.lower() if not has_wildcards else False,
                                    "size": file_stats.st_size,
                                    "modified": file_stats.st_mtime
                                })
                                
                                # Stop if we've reached max results
                                if len(results) >= max_results:
                                    break
                            except Exception as e:
                                logger.warning(f"Error getting stats for {full_path}: {e}")
                                
                    # Stop if we've reached max results
                    if len(results) >= max_results:
                        break
                        
            except Exception as e:
                logger.warning(f"Error searching in {base_path}: {e}")
                
        # Sort results: exact matches first, then by modification time (most recent first)
        results.sort(key=lambda x: (not x.get("is_exact_match", False), -x.get("modified", 0)))
        
        return {
            "status": "success",
            "message": f"Found {len(results)} files matching '{search_name}'",
            "searched_for": search_name,
            "files": results,
            "search_paths": list(searched_dirs)
        }


class FileToolFactory:
    """Factory for creating appropriate file tools based on user requests."""
    
    @staticmethod
    def create_tool(request_type, path=None):
        """Create the appropriate file tool based on the request type.
        
        Args:
            request_type: Type of file operation ('read', 'list', 'search', 'find')
            path: File or directory path
            
        Returns:
            FileToolBase: An instance of the appropriate file tool
        """
        if request_type == 'read':
            return FileReader(path)
        elif request_type == 'list':
            return DirectoryLister(path)
        elif request_type == 'search':
            return DirectorySearcher(path)
        elif request_type == 'find':
            return FileSearcher(path)
        else:
            raise ValueError(f"Unknown request type: {request_type}")
    
    @staticmethod
    def detect_request_type(user_input):
        """Analyze user input to determine the file operation they want.
        
        Args:
            user_input: User's input text
            
        Returns:
            tuple: (request_type, path)
        """
        # Convert to lowercase for easier matching
        input_lower = user_input.lower()
        
        # Keywords that indicate file reading
        read_keywords = ['read', 'open', 'show', 'display', 'view', 'cat', 'get', 'content', 
                         "what's in", 'tell me about', 'what is in', 'show me']
        
        # Keywords that indicate directory listing
        list_keywords = ['list', 'ls', 'directory', 'folder', 'files in', 'show files', 
                         'contents of', 'what is in the directory', 'what\'s in the directory']
        
        # Keywords that indicate directory searching
        dir_search_keywords = ['find directory', 'search for directory', 'locate directory', 
                              'is there a folder', 'is there a directory', 'where is directory']
        
        # Keywords that indicate file searching
        file_search_keywords = ['find file', 'search for file', 'locate file', 'find a file',
                               'is there a file', 'where is file', 'search recursively', 
                               'find', 'search for', 'locate', 'find all', 'search all',
                               'where is the', 'look for', 'search for any', 'find any',
                               'search for json', 'search for .py', 'search for py']
        
        # Try to extract a file or directory path using common patterns
        path = None
        
        # Check for file search patterns first (most specific)
        if any(keyword in input_lower for keyword in file_search_keywords):
            # Pattern: "find file X" or "find a file named X"
            file_patterns = [
                'find file ', 'search for file ', 'locate file ', 'find a file ',
                'find a file named ', 'search for a file named ', 'locate a file named ',
                'is there a file called ', 'is there a file named ', 'find the file '
            ]
            
            for pattern in file_patterns:
                if pattern in input_lower:
                    parts = input_lower.split(pattern, 1)
                    if len(parts) > 1:
                        file_name = parts[1].strip('.,;:"\'?').strip()
                        return 'find', file_name
            
            # Pattern: "find X.json" or "search for X.txt" - look for file extensions
            words = input_lower.split()
            for i, word in enumerate(words):
                if i > 0 and words[i-1] in ['find', 'search', 'locate']:
                    # Check for a word that looks like a filename (has extension)
                    if '.' in word and not word.startswith(('http', 'www')):
                        return 'find', word.strip('.,;:"\'?')
            
            # Check for a phrase like "find browser_scenario.json"
            search_terms = ['find', 'search', 'locate', 'where']
            for term in search_terms:
                if term in input_lower:
                    # Get all words after the search term
                    parts = input_lower.split(term, 1)
                    if len(parts) > 1:
                        # Look for words with file extensions in the second part
                        for word in parts[1].split():
                            cleaned_word = word.strip('.,;:"\'?')
                            if '.' in cleaned_word and not cleaned_word.startswith(('http', 'www')):
                                return 'find', cleaned_word
        
        # First, check for specific directory listing patterns
        if any(keyword in input_lower for keyword in list_keywords):
            # Common pattern: "list files in X directory"
            if 'files in' in input_lower and 'directory' in input_lower:
                parts = input_lower.split('files in')
                if len(parts) > 1:
                    dir_part = parts[1].split('directory')[0].strip()
                    if dir_part:
                        return 'list', dir_part
            
            # Pattern: "list the X directory"
            dir_patterns = [
                'list the ', 'show the ', 'list files in ', 'show files in ', 
                'contents of ', 'what\'s in the ', 'what is in the '
            ]
            
            for pattern in dir_patterns:
                if pattern in input_lower:
                    parts = input_lower.split(pattern, 1)
                    if len(parts) > 1:
                        # Extract the directory name, handling common endings
                        dir_name = parts[1].strip()
                        for end in [' directory', ' folder', ' dir']:
                            if dir_name.endswith(end):
                                dir_name = dir_name[:-len(end)]
                        
                        # Clean up any punctuation
                        dir_name = dir_name.strip('.,;:"\'')
                        if dir_name:
                            # Special case: check if 'the' was extracted alone, which is likely a parsing error
                            if dir_name == 'the':
                                # Try to get the next part - e.g., "what is in the demo_files directory"
                                remaining = input_lower.split(pattern + 'the ', 1)
                                if len(remaining) > 1:
                                    better_dir = remaining[1].strip()
                                    for end in [' directory', ' folder', ' dir']:
                                        if better_dir.endswith(end):
                                            better_dir = better_dir[:-len(end)]
                                    better_dir = better_dir.strip('.,;:"\'')
                                    if better_dir:
                                        return 'list', better_dir
                            
                            return 'list', dir_name
        
        # Check for specific directory search patterns
        if any(keyword in input_lower for keyword in dir_search_keywords):
            # Pattern: "is there a directory called X"
            if 'directory called' in input_lower:
                parts = input_lower.split('directory called')
                if len(parts) > 1:
                    return 'search', parts[1].strip('.,;:"\'?').strip()
            
            # Pattern: "is there a folder named X"
            if 'folder named' in input_lower:
                parts = input_lower.split('folder named')
                if len(parts) > 1:
                    return 'search', parts[1].strip('.,;:"\'?').strip()
            
            # Pattern: "find directory X"
            dir_patterns = ['find directory ', 'search for directory ', 'locate directory ']
            for pattern in dir_patterns:
                if pattern in input_lower:
                    parts = input_lower.split(pattern, 1)
                    if len(parts) > 1:
                        return 'search', parts[1].strip('.,;:"\'?').strip()
            
            # Generic patterns like "find X directory"
            for i, word in enumerate(input_lower.split()):
                if word in ['find', 'search', 'locate'] and i < len(input_lower.split()) - 2:
                    next_words = input_lower.split()[i+1:]
                    # Check if "directory" or "folder" appears later
                    if 'directory' in next_words or 'folder' in next_words:
                        # Get the word before "directory" or "folder"
                        for j, next_word in enumerate(next_words):
                            if next_word in ['directory', 'folder']:
                                if j > 0:
                                    return 'search', next_words[j-1].strip('.,;:"\'?')
        
        # Fall back to the word-based extraction for other cases
        words = user_input.split()
        
        # Check for read operations
        if any(keyword in input_lower for keyword in read_keywords):
            # First, check for specific patterns like "what is in file.txt"
            common_patterns = [
                'what is in ', 'what\'s in ', 'show me ', 'read ', 'open ', 
                'display ', 'view ', 'content of ', 'contents of '
            ]
            
            for pattern in common_patterns:
                if pattern in input_lower:
                    parts = input_lower.split(pattern, 1)
                    if len(parts) > 1:
                        # Look for word with extension
                        potential_file = parts[1].strip()
                        words_in_part = potential_file.split()
                        for word in words_in_part:
                            if '.' in word and not word.startswith('http'):
                                return 'read', word.strip('.,;:"\'?')
            
            # Fallback: Look for any word that looks like a filename
            for word in words:
                if '.' in word and not word.startswith('http'):  # Simple heuristic for files
                    path = word.strip('.,;:"\'')
                    return 'read', path
        
        # Fallback for list operations
        if any(keyword in input_lower for keyword in list_keywords):
            # Special case: "list X" where X is likely a directory name
            words = input_lower.split()
            if len(words) >= 2 and words[0] == 'list':
                dir_name = words[1].strip('.,;:"\'')
                return 'list', dir_name
            
            # Look for directory paths after prepositions
            for i, word in enumerate(words):
                if word.lower() in ['in', 'of', 'from'] and i < len(words) - 1:
                    path = words[i+1].strip('.,;:"\'')
                    return 'list', path
        
        # Check for file patterns in the input
        words_with_extensions = [word.strip('.,;:"\'?') for word in words 
                                if '.' in word and not word.startswith(('http', 'www'))]
        
        # If we have search keywords and file patterns, prioritize file search
        if words_with_extensions and any(keyword in input_lower for keyword in file_search_keywords):
            # Use the first file pattern found
            return 'find', words_with_extensions[0]
            
        # Pattern for "search for any json files" or similar
        file_type_patterns = ['json files', '.py files', 'text files', 'python files',
                            'configuration files', 'log files', 'data files']
        for pattern in file_type_patterns:
            if pattern in input_lower:
                # Extract the file extension or type
                file_type = pattern.split()[0]
                # If it's a file extension, add the dot if it's missing
                if not file_type.startswith('.') and file_type in ['py', 'txt', 'json', 'md', 'csv']:
                    file_type = '.' + file_type
                return 'find', f"*{file_type}*"

        # Generic search fallback - this catches simple cases like "find browser_scenario.json" 
        # that weren't caught by the more specific patterns
        if any(keyword in input_lower for keyword in file_search_keywords + dir_search_keywords):
            for i, word in enumerate(words):
                # After a search-related word, look for the object of the search
                if word.lower() in ['find', 'search', 'locate', 'where'] and i < len(words) - 1:
                    next_word = words[i+1].strip('.,;:"\'?')
                    
                    # If it looks like a filename (has a dot), it's a file search
                    if '.' in next_word and not next_word.startswith(('http', 'www')):
                        return 'find', next_word
                    # Otherwise, assume it's a directory search
                    else:
                        # But avoid prepositions and articles
                        if next_word not in ['for', 'the', 'a', 'an', 'in', 'on', 'at', 'any', 'all']:
                            # Special case for "find all" followed by a file type
                            if next_word == 'all' and i+2 < len(words):
                                file_type = words[i+2].strip('.,;:"\'?')
                                if file_type in ['json', 'py', 'txt', 'csv', 'md']:
                                    return 'find', f"*.{file_type}"
                            return 'search', next_word
        
        # Default to read if we found a likely file path but couldn't determine operation
        if path:
            return 'read', path
            
        # If we couldn't determine the type, return None
        return None, None