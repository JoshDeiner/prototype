# Unified Assistant Architecture

## Overview

This document outlines the architecture for the Unified Assistant system, which follows the **Text-Based LLM to OS Execution Flow** pattern. The system consists of a stateful controller with two operational modes (LLM and OS) that enable safe interaction between language models and the operating system.

## Core Components

```
[ User Input (text) ]
        │
        ▼
[ Wrapper Controller ] ◀────────────────────────────┐
        │                                           │
        ▼                                           │
  ┌───────────────────────┐                         │
  │  Scene Context (opt.) │                         │
  │  ──────────────────── │                         │
  │  - Injected at prompt │                         │
  │  - Defines simulated  │                         │
  │    LLM behavior       │                         │
  └───────────────────────┘                         │
        │                                           │
        ▼                                           │
  ┌───────────────┐                                 │
  │   LLM Mode    │                                 │
  │ ───────────── │                                 │
  │ - Send input + scene to LLM                     │
  │ - Receive JSON: response + action candidate     │
  │ - Validate structure + intent clarity           │
  │ - If action is clear + valid ➝ inform wrapper   │
  └───────────────┘                                 │
        │                                           │
        ▼                                           │
┌─────────────────────┐                             │
│   Wrapper Switches   │                            │
│   to OS Mode         │                            │
└─────────────────────┘                             │
        │                                           │
        ▼                                           │
  ┌───────────────┐                                 │
  │   OS Mode     │                                 │
  │ ───────────── │                                 │
  │ - Receive structured action (type + value)      │
  │ - Validate (path exists, action safe, etc.)     │
  │ - Execute using `os.system()` or `subprocess`   │
  │ - Log result + status                           │
  └───────────────┘                                 │
        │                                           │
        ▼                                           │
[ Result or next input → back to Wrapper ] ─────────┘
```

### Primary Files

- **unified_assistant.py** - Main entry point implementing the wrapper controller
- **llm_service.py** - Handles LLM interactions and processes scene contexts
- **os_exec.py** - Executes system actions with safety checks
- **file_assistant_middleware.py** - Contains the StatefulController implementation

## Key Responsibilities

### Wrapper Controller
- Controls the flow between LLM and OS modes
- Maintains conversation context
- Validates actions before execution
- Manages transitions between modes
- Handles action refinement when needed

### LLM Mode
- Processes user input with context
- Generates structured responses with potential actions
- Validates output format and clarity
- Implements fallback logic for unclear responses

### OS Mode
- Validates action safety before execution
- Executes system commands with appropriate guards
- Captures results and errors
- Returns control to LLM mode after execution

## Scene Support

The architecture supports scene-based interactions where:
- Scenes define roles, personas, and objectives
- Scene context influences how the LLM interprets input
- Scene constraints ensure behavior follows expected patterns
- Scene flow can be structured into steps or phases

## Operational Design

### State Machine
The controller operates as a state machine that:
1. Starts in LLM mode
2. Processes user input to generate responses
3. Switches to OS mode when valid actions are detected
4. Executes actions and captures results
5. Returns to LLM mode for subsequent interactions

### Action Structure
Actions follow a standardized JSON format:
```json
{
  "type": "os_command",
  "command": "ls -la /path/to/directory"
}
```

Other action types include:
- `launch_app` - Start an application
- `file_check` - Verify if a file exists
- `dir_search` - Look for directories
- `explain` - Provide information

### Safety and Fallbacks
- Commands are validated before execution
- Potentially dangerous operations are blocked
- LLM retries are capped to prevent loops
- Clear error messages guide the user

## Execution Flow Example

1. User asks: "Show me what's in the test.txt file"
2. LLM processes and returns: 
   ```json
   {
     "response": "I'll show you the contents of test.txt",
     "action": {
       "type": "os_command",
       "command": "cat test.txt"
     }
   }
   ```
3. Wrapper validates action and switches to OS mode
4. OS mode executes command and captures output
5. System returns to LLM mode with execution results
6. LLM incorporates results in the next response

## Usage

The system can be used through:

```
python unified_assistant.py [options]
```

Or via Makefile shortcuts:
```
make run                # Run with default settings
make run-scene SCENE=x  # Run with a specific scene
make run-file           # Run file assistant scenario
make run-help           # Run help desk scenario
```

## Configuration Options

- `--model` - Select LLM model (llama, claude, gemini)
- `--scene` - Path to scene file
- `--dry-run` - Simulate without executing commands
- `--unsafe` - Disable safety checks (use with caution)
- `--delay` - Set delay before auto-execution
- `--manual-confirm` - Require confirmation for actions