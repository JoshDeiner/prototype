# Voice Assistant

A modular monolith voice assistant that safely bridges natural language understanding with filesystem operations.

## Architecture

This project follows a modular monolith design pattern, organizing functionality into cohesive modules with clear boundaries while maintaining the simplicity of a monolithic deployment.

### Directory Structure

```
voice-assistant/
│
├── main.py                   # Starts app, routes user input
├── config.py                 # Constants, scene templates, paths
│
├── controller/               # Wrapper state machine
│   └── wrapper.py            # Core class controlling LLM ↔ OS flow
│
├── modes/
│   ├── llm_mode.py           # LLM handling, response parsing, validation
│   ├── os_mode.py            # Action executor (safe commands, logging)
│
├── prompts/
│   ├── scene_loader.py       # Load scene files (JSON/YAML)
│   ├── prompt_builder.py     # Compose LLM prompt from scene + state
│
├── llm/
│   └── local_llm.py          # Interface to Claude, LLaMA, or Gemini
│
├── tools/
│   ├── logger.py             # Action/result logging
│   ├── validator.py          # Safety checks for commands/actions
│   └── file_utils.py         # Helpers like checking file paths
│
├── tests/
│   ├── test_wrapper.py
│   └── test_prompt_generation.py
│
└── scenes/
    └── chrome_help.json      # Example scene files
```

## Core Components

### Wrapper Controller (State Machine)

The core of the application is a stateful controller with two operational modes:

1. **LLM Mode**: For understanding, planning, and generating structured responses
2. **OS Mode**: For executing validated system actions with safety checks

The wrapper manages transitions between these modes and maintains conversation context.

### LLM Interface

Supports multiple large language model backends:
- LLaMA (via Ollama)
- Claude (via API)
- Gemini (via API)
- Simulation mode for testing

### Scene System

Supports role-playing scenarios defined in YAML/JSON files with:
- User and assistant roles
- Scene descriptions
- Constraints and behavior guidelines

### Action System

Structured action types with validation:
- `os_command`: Execute system commands
- `launch_app`: Start applications
- `file_check`: Verify file existence
- `dir_search`: Search for directories
- `explain`: Provide information without system action

## Usage

```bash
# Run with default settings
python main.py

# Run with specific model
python main.py --model claude

# Run a specific scene
python main.py --scene help_desk

# Run in safe mode with manual confirmation
python main.py --manual-confirm
```

## Configuration

Configuration options in `config.py`:
- LLM model selection
- Safety mode settings
- Scene paths and templates
- System prompt templates