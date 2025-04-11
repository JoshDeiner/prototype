"""Text-based assistant with stateful controller implementing the LLM→OS execution flow."""
import os
import json
import time
from utils import logger, ensure_directory, load_scenario
from llm_service import LLMService
from os_exec import OSExecutionService
from file_tools import FileToolFactory, FileReader, DirectoryLister, DirectorySearcher, FileSearcher

class TextAssistant:
    """
    Stateful controller with two operational modes:
    - LLM Mode (understanding & planning)
    - OS Mode (executing validated system actions)
    """
    def __init__(self, config=None):
        """Initialize the text assistant.
        
        Args:
            config: Configuration dictionary
        """
        # Set default configuration
        self.config = {
            "llm_model": "llama",
            "dry_run": True,
            "safe_mode": True,
            "output_dir": "output",
            "conversation_turns": 3,
            "os_commands_enabled": True,
            "file_tools_enabled": True
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
            
        # Ensure output directory exists
        ensure_directory(self.config["output_dir"])
        
        # Initialize services
        self.llm_service = LLMService(
            model_type=self.config["llm_model"]
        )
        
        self.os_exec_service = OSExecutionService(
            dry_run=self.config["dry_run"],
            safe_mode=self.config["safe_mode"]
        )
        
        # Initialize state
        self.context = []
        self.current_mode = "LLM"  # Start in LLM mode
        self.pending_action = None
        self.last_user_input = None
        self.last_llm_response = None
        self.last_action_result = None
        self.last_file_processed = None
        self.last_file_operation = None
        
        logger.info("Text assistant initialized in LLM mode")
        
    def process_input(self, user_input, expected_action=None):
        """Process user text input through the stateful controller.
        
        Args:
            user_input: User's text input
            expected_action: Expected action for validation (optional)
            
        Returns:
            dict: Results from the processing pipeline
        """
        self.last_user_input = user_input
        
        results = {
            "user_input": user_input,
            "success": False,
            "llm_response": None,
            "action_result": None,
            "current_mode": self.current_mode
        }
        
        # Process based on current mode
        if self.current_mode == "LLM":
            logger.info("Processing input in LLM mode")
            results = self._process_in_llm_mode(user_input, results)
        elif self.current_mode == "OS":
            logger.info("Processing input in OS mode")
            results = self._process_in_os_mode(user_input, results)
        
        # Update state based on processing
        results["current_mode"] = self.current_mode
        return results
    
    def _process_in_llm_mode(self, user_input, results):
        """Process input in LLM mode - understanding user intent and planning actions.
        
        Args:
            user_input: User's text input
            results: Current results dictionary
            
        Returns:
            dict: Updated results
        """
        # First, try to detect if this is a file operation request
        if self.config["file_tools_enabled"]:
            file_op_result = self._process_file_operation(user_input, results)
            if file_op_result:
                return file_op_result
        
        # If not a file operation, process through LLM service
        llm_response = self.llm_service.process_input(user_input, self.context)
        self.last_llm_response = llm_response
        results["llm_response"] = llm_response
        
        if not llm_response:
            logger.error("LLM processing failed")
            return results
        
        # Update conversation context
        self.context.append({"user": user_input, "assistant": llm_response["response"]})
        
        # Check if there's an action to execute
        if "action" in llm_response and llm_response["action"]["type"] != "none":
            # Validate action structure
            action = llm_response["action"]
            is_valid, validation_reason = self.llm_service.validate_action(action)
            
            if is_valid:
                logger.info(f"Valid action detected: {action['type']}")
                
                # Check special action types that don't require switching to OS mode
                if action['type'] == "clarify":
                    logger.info(f"Clarification requested: {action.get('question', '')}")
                    results["clarification_requested"] = True
                    # Stay in LLM mode for clarifications
                elif action['type'] == "file_check":
                    logger.info(f"File check requested: {action.get('file_path', '')}")
                    # Use our new file tool instead of os_exec_service
                    file_reader = FileReader(action.get('file_path', ''))
                    is_valid, message = file_reader.validate()
                    results["file_check_result"] = {
                        "status": "success" if is_valid else "error",
                        "message": message.get("message") if isinstance(message, dict) else message,
                        "file_exists": is_valid,
                        "file_path": file_reader.resolved_path if is_valid else None,
                        "file_info": message.get("file_info") if is_valid else None,
                        "similar_files": message.get("similar_files") if not is_valid and isinstance(message, dict) else []
                    }
                    results["file_check_performed"] = True
                    
                    # Stay in LLM mode and immediately process the result via another LLM call
                    file_info = self._format_file_check_result(results["file_check_result"])
                    follow_up = self.llm_service.process_input(
                        f"I checked the file you mentioned. {file_info}. Based on this information, what would you like to do?", 
                        self.context
                    )
                    results["llm_response"] = follow_up
                    self.context.append({"user": f"[File check: {action.get('file_path', '')}]", "assistant": follow_up["response"]})
                    
                    # Store the last file processed for follow-up questions
                    if is_valid:
                        self.last_file_processed = file_reader.resolved_path
                    
                elif action['type'] == "dir_search":
                    logger.info(f"Directory search requested: {action.get('dir_name', '')}")
                    # Use our new directory search tool
                    dir_searcher = DirectorySearcher(action.get('dir_name', ''))
                    search_result = dir_searcher.search()
                    results["dir_search_result"] = search_result
                    results["dir_search_performed"] = True
                    
                    # Stay in LLM mode and immediately process the result via another LLM call
                    dir_info = self._format_dir_search_result(search_result)
                    follow_up = self.llm_service.process_input(
                        f"I searched for the directory you mentioned. {dir_info}. Based on this information, what would you like to do?", 
                        self.context
                    )
                    results["llm_response"] = follow_up
                    self.context.append({"user": f"[Directory search: {action.get('dir_name', '')}]", "assistant": follow_up["response"]})
                    
                    # Store the last directory processed for follow-up questions
                    if search_result.get("directories") and search_result["directories"]:
                        # Use the first exact match, or first result if no exact match
                        exact_matches = [d for d in search_result["directories"] if d.get("is_exact_match", False)]
                        if exact_matches:
                            self.last_file_processed = exact_matches[0].get("path")
                        else:
                            self.last_file_processed = search_result["directories"][0].get("path")
                
                elif action['type'] == "file_search":
                    logger.info(f"File search requested: {action.get('file_name', '')}")
                    # Use our new file search tool
                    file_searcher = FileSearcher(action.get('file_name', ''))
                    search_result = file_searcher.search(max_depth=5, max_results=10)
                    results["file_search_result"] = search_result
                    results["file_search_performed"] = True
                    
                    # Stay in LLM mode and process the result via another LLM call
                    file_info = self._format_file_search_result(search_result)
                    follow_up = self.llm_service.process_input(
                        f"I searched for the file you mentioned. {file_info}. Based on this information, what would you like to do?", 
                        self.context
                    )
                    results["llm_response"] = follow_up
                    self.context.append({"user": f"[File search: {action.get('file_name', '')}]", "assistant": follow_up["response"]})
                    
                    # Store the last file processed for follow-up questions
                    if search_result.get("files") and search_result["files"]:
                        # Use the first exact match, or first result if no exact match
                        exact_matches = [f for f in search_result["files"] if f.get("is_exact_match", False)]
                        if exact_matches:
                            self.last_file_processed = exact_matches[0].get("path")
                        else:
                            self.last_file_processed = search_result["files"][0].get("path")
                else:
                    # Store the action for execution in OS mode
                    self.pending_action = action
                    # Switch to OS mode
                    self.current_mode = "OS"
                    results["mode_switched"] = True
                    results["pending_action"] = action
            else:
                logger.warning(f"Invalid action detected: {validation_reason}")
                results["action_validation_error"] = validation_reason
        
        results["success"] = True
        return results
        
    def _is_unsure_response(self, response_text):
        """Check if a response indicates uncertainty or confusion.
        
        Args:
            response_text: The response text to check
            
        Returns:
            bool: True if the response indicates uncertainty
        """
        # Patterns that suggest uncertainty
        uncertainty_patterns = [
            "do you want to", "would you like to", 
            "I'm not sure", "I am not sure",
            "could you clarify", "not clear what",
            "specify what", "be more specific",
            "do you mean", "did you mean",
            "not understand", "confusing"
        ]
        
        # Check for uncertainty patterns
        if any(pattern in response_text.lower() for pattern in uncertainty_patterns):
            return True
            
        # Check for question marks (more than one suggests confusion)
        if response_text.count('?') > 1:
            return True
            
        return False

    def _process_file_operation(self, user_input, results):
        """Directly process file operations without requiring LLM inference.
        
        Args:
            user_input: User's text input
            results: Current results dictionary
            
        Returns:
            dict or None: Updated results if a file operation was performed, None otherwise
        """
        # Try to detect the file operation type and path
        request_type, path = FileToolFactory.detect_request_type(user_input)
        
        # If no request detected or path found, try to handle follow-up questions
        if not request_type and self.last_file_processed:
            # Check for follow-up questions about the last file
            follow_up_phrases = [
                'what does it say', 'what\'s in it', 'show me the contents', 'read it', 
                'the file', 'open it', 'show me', 'what is in it', 'what\'s inside',
                'what does that file say', 'what does the file say', 'show', 'read', 'contents',
                'show that', 'read that', 'list the contents', 'list its contents', 
                'read the file again', 'that file', 'we just viewed', 'we just saw'
            ]
            
            if any(phrase in user_input.lower() for phrase in follow_up_phrases) or user_input.lower() in ['it', 'again', 'show it again']:
                logger.info(f"Detected follow-up question about last file: {self.last_file_processed}")
                
                # Set path to last processed file and infer operation type from the last operation
                path = self.last_file_processed
                
                # Use the appropriate operation based on whether it's a file or directory
                if os.path.isfile(path):
                    request_type = 'read'
                elif os.path.isdir(path):
                    request_type = 'list'
                else:
                    # Use the last operation type if we have it, otherwise default to read
                    request_type = self.last_file_operation if self.last_file_operation else 'read'
        
        if not request_type or not path:
            return None
            
        logger.info(f"Detected file operation: {request_type} - {path}")
        
        # Create the appropriate tool
        try:
            tool = FileToolFactory.create_tool(request_type, path)
            
            # Execute the operation
            if request_type == 'read':
                operation_result = tool.read()
                
                if operation_result["status"] == "success":
                    # Store for follow-up questions
                    self.last_file_processed = tool.resolved_path
                    self.last_file_operation = 'read'
                    
                    # Check if the file is empty and provide appropriate response
                    if operation_result.get("content", "").strip() == "":
                        # Handle empty file case
                        response_text = f"The file '{os.path.basename(tool.resolved_path)}' exists but is empty."
                    else:
                        # Normal case with content
                        response_text = f"Here's the content of '{os.path.basename(tool.resolved_path)}':\n\n{operation_result['content']}"
                    
                    # Add to results
                    results["file_operation_result"] = operation_result
                    results["file_operation_performed"] = True
                    results["llm_response"] = {"response": response_text}
                    results["success"] = True
                    
                    # Update context
                    self.context.append({"user": user_input, "assistant": response_text})
                    
                    return results
                    
                elif operation_result["status"] == "error" and operation_result.get("details", {}).get("requires_app", False):
                    # File requires an application to open
                    file_type = operation_result.get("details", {}).get("file_type", "binary")
                    
                    # Create a response explaining why we can't display the content
                    response_text = (f"The file '{os.path.basename(tool.resolved_path)}' is a {file_type} file "
                                     f"and can't be displayed directly in the terminal. "
                                     f"You would need to open it with an appropriate application.")
                    
                    # Add to results
                    results["file_operation_result"] = operation_result
                    results["file_operation_performed"] = True
                    results["llm_response"] = {"response": response_text}
                    results["success"] = True
                    
                    # Update context
                    self.context.append({"user": user_input, "assistant": response_text})
                    
                    return results
            
            elif request_type == 'list':
                operation_result = tool.list()
                
                if operation_result["status"] == "success":
                    # Store for follow-up questions
                    self.last_file_processed = tool.resolved_path
                    self.last_file_operation = 'list'
                    
                    # Create a nicely formatted directory listing
                    contents = operation_result["contents"]
                    dirs = [item for item in contents if item["is_dir"]]
                    files = [item for item in contents if not item["is_dir"]]
                    
                    response_lines = [f"Contents of directory '{os.path.basename(tool.resolved_path)}':"]
                    
                    if dirs:
                        response_lines.append("\nDirectories:")
                        for d in dirs:
                            response_lines.append(f"  - {d['name']}/")
                    
                    if files:
                        response_lines.append("\nFiles:")
                        for f in files:
                            # Format size
                            size = f["size"]
                            if size > 1024*1024:
                                size_str = f"{size/(1024*1024):.2f} MB"
                            elif size > 1024:
                                size_str = f"{size/1024:.2f} KB"
                            else:
                                size_str = f"{size} bytes"
                                
                            response_lines.append(f"  - {f['name']} ({size_str})")
                    
                    response_text = "\n".join(response_lines)
                    
                    # Add to results
                    results["file_operation_result"] = operation_result
                    results["file_operation_performed"] = True
                    results["llm_response"] = {"response": response_text}
                    results["success"] = True
                    
                    # Update context
                    self.context.append({"user": user_input, "assistant": response_text})
                    
                    return results
            
            elif request_type == 'search':
                operation_result = tool.search()
                
                if operation_result["status"] == "success":
                    # Create a response from search results
                    directories = operation_result["directories"]
                    
                    if not directories:
                        response_text = f"I couldn't find any directories matching '{path}'."
                    else:
                        # Check for exact matches
                        exact_matches = [d for d in directories if d.get("is_exact_match", False)]
                        
                        if exact_matches:
                            # Store the exact match for follow-up
                            self.last_file_processed = exact_matches[0]["path"]
                            self.last_file_operation = 'search'
                            
                            response_text = f"I found directory '{os.path.basename(exact_matches[0]['path'])}' at: {exact_matches[0]['path']}"
                        else:
                            # Store the first match for follow-up
                            if directories:
                                self.last_file_processed = directories[0]["path"]
                                self.last_file_operation = 'search'
                            
                            response_lines = [f"I found {len(directories)} directories that match '{path}':"]
                            for i, d in enumerate(directories[:5]):
                                response_lines.append(f"  {i+1}. {d.get('path')}")
                            
                            if len(directories) > 5:
                                response_lines.append(f"  ... and {len(directories) - 5} more.")
                                
                            response_text = "\n".join(response_lines)
                    
                    # Add to results
                    results["file_operation_result"] = operation_result
                    results["file_operation_performed"] = True
                    results["llm_response"] = {"response": response_text}
                    results["success"] = True
                    
                    # Update context
                    self.context.append({"user": user_input, "assistant": response_text})
                    
                    return results
            
            elif request_type == 'find':
                operation_result = tool.search(max_depth=5, max_results=10)
                
                if operation_result["status"] == "success":
                    # Create a response from file search results
                    files = operation_result["files"]
                    
                    if not files:
                        response_text = f"I couldn't find any files matching '{path}'."
                    else:
                        # Check for exact matches
                        exact_matches = [f for f in files if f.get("is_exact_match", False)]
                        
                        if exact_matches:
                            # Store the exact match for follow-up
                            self.last_file_processed = exact_matches[0]["path"]
                            self.last_file_operation = 'find'
                            
                            size_kb = exact_matches[0].get('size', 0) / 1024
                            response_text = f"I found file '{os.path.basename(exact_matches[0]['path'])}' at: {exact_matches[0]['path']} (Size: {size_kb:.1f} KB)"
                        else:
                            # Store the first match for follow-up
                            if files:
                                self.last_file_processed = files[0]["path"]
                                self.last_file_operation = 'find'
                            
                            response_lines = [f"I found {len(files)} files that match '{path}':"]
                            for i, f in enumerate(files[:5]):
                                size_kb = f.get('size', 0) / 1024
                                response_lines.append(f"  {i+1}. {f.get('path')} (Size: {size_kb:.1f} KB)")
                            
                            if len(files) > 5:
                                response_lines.append(f"  ... and {len(files) - 5} more.")
                                
                            response_text = "\n".join(response_lines)
                    
                    # Add to results
                    results["file_operation_result"] = operation_result
                    results["file_operation_performed"] = True
                    results["llm_response"] = {"response": response_text}
                    results["success"] = True
                    
                    # Update context
                    self.context.append({"user": user_input, "assistant": response_text})
                    
                    return results
        
        except Exception as e:
            logger.error(f"Error processing file operation: {e}")
            # Continue with normal LLM processing
        
        return None
    
    def _process_in_os_mode(self, user_input, results):
        """Process input in OS mode - executing validated system actions.
        
        Args:
            user_input: User's input (may be a confirmation)
            results: Current results dictionary
            
        Returns:
            dict: Updated results
        """
        # Check if we have a pending action to execute
        if not self.pending_action:
            logger.warning("No pending action in OS mode")
            # Switch back to LLM mode
            self.current_mode = "LLM"
            # Process the input again, now in LLM mode
            return self._process_in_llm_mode(user_input, results)
        
        # Check if user confirmed or cancelled
        input_lower = user_input.lower()
        confirmation_phrases = ["yes", "yeah", "y", "sure", "ok", "okay", "confirm", "proceed", "do it", "execute"]
        cancellation_phrases = ["no", "nope", "n", "cancel", "stop", "don't", "abort"]
        
        # If user confirmed
        if any(phrase in input_lower for phrase in confirmation_phrases) or input_lower == "":
            # Execute the pending action
            logger.info(f"Executing action: {self.pending_action['type']}")
            action_result = self.os_exec_service.execute_action(self.pending_action)
            self.last_action_result = action_result
            results["action_result"] = action_result
            
            # Include the LLM response from the previous turn
            if self.last_llm_response:
                results["llm_response"] = self.last_llm_response
            
            # Clear the pending action now that it's executed
            self.pending_action = None
            
            # Switch back to LLM mode
            self.current_mode = "LLM"
            results["mode_switched"] = True
        # If user cancelled
        elif any(phrase in input_lower for phrase in cancellation_phrases):
            logger.info("User cancelled pending action")
            # Clear the pending action
            self.pending_action = None
            
            # Switch back to LLM mode
            self.current_mode = "LLM"
            results["mode_switched"] = True
            results["action_cancelled"] = True
            
            # Process the cancellation in LLM mode to get a response
            cancellation_response = self.llm_service.process_input("I changed my mind, please don't execute that action", self.context)
            results["llm_response"] = cancellation_response
            self.context.append({"user": "Cancel action", "assistant": cancellation_response["response"]})
        else:
            # User input is ambiguous, treat as a new query
            logger.info("Ambiguous user input in OS mode, treating as new query")
            # Clear the pending action
            self.pending_action = None
            
            # Switch back to LLM mode and process as new input
            self.current_mode = "LLM"
            return self._process_in_llm_mode(user_input, results)
        
        results["success"] = True
        return results
    
    def _format_file_check_result(self, check_result):
        """Format file check result for LLM consumption.
        
        Args:
            check_result: Result from _check_file_exists
            
        Returns:
            str: Formatted description of file check
        """
        if check_result.get("status") == "error":
            return f"There was an error checking the file: {check_result.get('message', 'Unknown error')}"
        
        if check_result.get("file_exists", False):
            # File exists
            file_info = check_result.get("file_info", {})
            if not file_info and "file_path" in check_result:
                # For compatibility with older format
                file_info = {
                    "size": check_result.get("size", 0),
                    "file_type": check_result.get("file_type", "unknown"),
                    "extension": check_result.get("extension", ""),
                    "file_path": check_result.get("file_path", "")
                }
                
            size = file_info.get("size", 0)
            size_str = f"{size:,} bytes"
            if size > 1024*1024:
                size_str = f"{size/(1024*1024):.2f} MB"
            elif size > 1024:
                size_str = f"{size/1024:.2f} KB"
                
            file_type = file_info.get("file_type", "unknown")
            extension = file_info.get("extension", "")
            
            # Add information about content
            is_empty = file_info.get("is_empty", size == 0)
            empty_note = " The file is empty." if is_empty else ""
            
            # Add line count information if available
            line_info = ""
            if "line_count" in file_info and file_info["line_count"] > 0:
                line_info = f" Contains {file_info['line_count']} lines."
            
            return (f"The file exists at '{check_result.get('file_path', '')}'. "
                   f"It's a {file_type} file{' with ' + extension + ' extension' if extension else ''}. "
                   f"Size: {size_str}.{empty_note}{line_info}")
        elif check_result.get("is_directory", False):
            # It's a directory
            return f"The path '{check_result.get('path', '')}' exists but is a directory, not a file."
        else:
            # File not found
            similar_files = check_result.get("similar_files", [])
            if similar_files:
                similar_info = ", ".join([f"'{f['name']}'" for f in similar_files[:3]])
                return (f"The file '{check_result.get('searched_path', '')}' does not exist. "
                       f"However, I found similar files: {similar_info}.")
            else:
                return f"The file '{check_result.get('searched_path', '')}' does not exist."
                
    def _format_dir_search_result(self, search_result):
        """Format directory search result for LLM consumption.
        
        Args:
            search_result: Result from _search_directory
            
        Returns:
            str: Formatted description of directory search
        """
        if search_result.get("status") == "error":
            return f"There was an error searching for the directory: {search_result.get('message', 'Unknown error')}"
            
        directories = search_result.get("directories", [])
        if not directories:
            return f"I couldn't find any directories matching '{search_result.get('searched_for', '')}'."
            
        # Check for exact matches first
        exact_matches = [d for d in directories if d.get("is_exact_match", False)]
        if exact_matches:
            match = exact_matches[0]
            return f"I found an exact match: '{match.get('path', '')}'."
            
        # Otherwise show some partial matches
        results = []
        for i, d in enumerate(directories[:3]):
            results.append(f"'{d.get('path', '')}'")
            
        if len(directories) > 3:
            return f"I found {len(directories)} directories that might match. The top matches are: {', '.join(results)}."
        else:
            return f"I found the following directories that might match: {', '.join(results)}."
            
    def _format_file_search_result(self, search_result):
        """Format file search result for LLM consumption.
        
        Args:
            search_result: Result from file search operation
            
        Returns:
            str: Formatted description of file search
        """
        if search_result.get("status") == "error":
            return f"There was an error searching for the file: {search_result.get('message', 'Unknown error')}"
            
        files = search_result.get("files", [])
        if not files:
            return f"I couldn't find any files matching '{search_result.get('searched_for', '')}'."
            
        # Check for exact matches first
        exact_matches = [f for f in files if f.get("is_exact_match", False)]
        if exact_matches:
            match = exact_matches[0]
            size_kb = match.get('size', 0) / 1024
            return f"I found an exact match: '{match.get('path', '')}' (Size: {size_kb:.1f} KB)"
            
        # Otherwise show some partial matches
        results = []
        for i, f in enumerate(files[:3]):
            size_kb = f.get('size', 0) / 1024
            results.append(f"'{f.get('path', '')}' (Size: {size_kb:.1f} KB)")
            
        if len(files) > 3:
            return f"I found {len(files)} files that match '{search_result.get('searched_for', '')}'. The top matches are: {'; '.join(results)}."
        else:
            return f"I found the following files that match '{search_result.get('searched_for', '')}': {'; '.join(results)}."
    
    def process_scenario(self, scenario_path):
        """Process a scenario defined in a JSON file.
        
        Args:
            scenario_path: Path to the scenario JSON file
            
        Returns:
            dict: Results from processing the scenario
        """
        scenario = load_scenario(scenario_path)
        if not scenario:
            logger.error(f"Failed to load scenario: {scenario_path}")
            return {"success": False, "error": "Failed to load scenario"}
            
        logger.info(f"Processing scenario: {scenario_path}")
        
        results = {
            "scenario": scenario_path,
            "success": True,
            "steps": []
        }
        
        # Reset context for new scenario
        self.context = []
        
        # Process user input
        user_input = scenario.get("user_input")
        expected_action = scenario.get("expected_action")
        
        step_result = self.process_input(
            user_input,
            expected_action
        )
        
        results["steps"].append(step_result)
        
        # If we switched to OS mode and there's a confirmation in the scenario
        if step_result.get("mode_switched") and self.current_mode == "OS" and "confirmation" in scenario:
            confirmation = scenario.get("confirmation", "yes")
            step_result = self.process_input(confirmation)
            results["steps"].append(step_result)
        
        # Check if all steps were successful
        if not all(step["success"] for step in results["steps"]):
            results["success"] = False
            
        return results
    
    def interactive_session(self):
        """Start an interactive terminal session.
        
        User can type 'exit' to end the session.
        """
        print("\n===== Text-Based Assistant =====")
        print("(Type 'exit' to end the session)")
        
        while True:
            # Indicate current mode
            mode_indicator = "[LLM Mode]" if self.current_mode == "LLM" else "[OS Mode - Waiting for confirmation]"
            
            # Get user input
            user_input = input(f"\n{mode_indicator} You: ")
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'bye'] and self.current_mode == "LLM":
                print("\nAssistant: Goodbye!")
                break
                
            # Process the input
            start_time = time.time()
            result = self.process_input(user_input)
            processing_time = time.time() - start_time
            
            if result["success"] and "llm_response" in result and result["llm_response"]:
                # Display LLM response
                print(f"\nAssistant: {result['llm_response']['response']}")
                
                # If we just switched to OS mode, show a confirmation prompt
                if result.get("mode_switched") and self.current_mode == "OS":
                    print("\n[OS Mode] Would you like to execute this action? (yes/no)")
                
                # Display action results if available
                action_result = result.get("action_result")
                if action_result and action_result.get("status") == "success":
                    print(f"\nAction result: {action_result.get('message', 'Completed')}")
                    
                    if "stdout" in action_result and action_result["stdout"].strip():
                        print(f"\nOutput:\n{action_result['stdout']}")
                        
                    # If there are errors/warnings
                    if "stderr" in action_result and action_result["stderr"].strip():
                        print(f"\nErrors/Warnings:\n{action_result['stderr']}")
                        
                # Log processing time (for development)
                logger.debug(f"Processing time: {processing_time:.2f} seconds")
            else:
                print("\nAssistant: Sorry, I encountered an error processing your request.")


def main():
    """Main function to run the text assistant."""
    # Create a sample scenario file
    test_dir = "test_scenarios"
    ensure_directory(test_dir)
    
    # OS command scenario
    os_command_scenario = {
        "user_input": "List the files in the current directory",
        "expected_action": {
            "type": "os_command",
            "command": "ls -la"
        },
        "confirmation": "yes"
    }
    
    scenario_path = os.path.join(test_dir, "os_command_scenario.json")
    with open(scenario_path, 'w') as f:
        json.dump(os_command_scenario, f, indent=2)
    
    # Initialize the text assistant
    assistant = TextAssistant()
    
    # Start interactive session
    assistant.interactive_session()


if __name__ == "__main__":
    main()