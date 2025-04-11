# Help Desk AI Assistant Prototype

This prototype implements a text-based help desk assistant that can:
1. Accept user questions via terminal input
2. Process them with an LLM
3. Generate responses and determine OS actions
4. Execute OS actions (with appropriate safeguards)

## Architecture

The system follows the **Text-Based LLM to OS Execution Flow** pattern with a stateful controller that manages two operational modes:

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

### Key Components

| Component        | Purpose |
|------------------|---------|
| `unified_assistant.py` | Main entry point implementing the wrapper controller |
| `Scene Context`  | Optional role-playing context injected into LLM prompts |
| `LLM Mode`       | Understands user input, generates structured response with action |
| `OS Mode`        | Executes real actions on system with proper validation |
| `Transition`     | Based on action confidence and validation |
| `Retries`        | Handles invalid or ambiguous actions with retry mechanism |

## Setup and Installation

1. Create a virtual environment:
```bash
cd prototype
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Prototype

The assistant supports various command-line options and different running modes. The easiest way to run the assistant is using the Makefile:

```bash
# List all available commands
make help

# Run the unified assistant (main entry point)
make run

# Run with a specific scene file
make run-scene SCENE=help_desk_scenario.yaml

# Run the file operations assistant 
make run-file

# Run the help desk assistant
make run-help

# Run the sales assistant
make run-sales

# List all available scenes
make list-scenes
```

### Running Options

You can also run the Python script directly with various options:

```bash
# Run with default settings
python unified_assistant.py

# Select a specific LLM model
python unified_assistant.py --model [llama|claude|gemini]

# Run with a specific scene
python unified_assistant.py --scene scenes/help_desk_scenario.yaml

# Run in dry-run mode (won't execute actual commands)
python unified_assistant.py --dry-run

# Require manual confirmation for actions
python unified_assistant.py --manual-confirm

# Set delay before auto-executing actions (seconds)
python unified_assistant.py --delay 2.0

# Specify maximum conversation history size
python unified_assistant.py --max-history 10

# List available scenes and exit
python unified_assistant.py --list-scenes
```

## How the Stateful Controller Works

The unified assistant is implemented as a stateful controller with two operational modes and scene context support:

1. **Scene Context** (optional):
   - Provides role-playing context for the LLM
   - Injected directly into prompts during LLM mode
   - Enables simulation of different scenarios and behaviors

2. **LLM Mode** (default state):
   - Processes user input (with optional scene context) through the LLM service
   - Receives structured JSON with a response and potential action
   - Validates action structure and completeness
   - For valid actions requiring system execution, transitions to OS Mode
   - Implements retry mechanism for invalid or ambiguous actions

3. **OS Mode**:
   - Presents the proposed action to the user for confirmation
   - If confirmed, executes the action through the OS execution service
   - Records action results in conversation history
   - Automatically transitions back to LLM Mode after execution

This state management approach provides several benefits:
- Clean separation of concerns between understanding (LLM) and execution (OS)
- Explicit user confirmation before any system action
- Robust validation at each step of the process
- Scene integration as part of LLM input generation
- Comprehensive error handling with retry mechanism
- Conversation history that includes system actions and results

## Supported Features

### File and Directory Operations

The assistant includes robust file and directory capabilities:

- **File Reading**: Read and display file contents
- **Directory Listing**: List files in directories
- **File Validation**: Check if files exist before operations
- **Path Resolution**: Handle relative and absolute paths
- **Similar File Finding**: Suggest similar files when exact matches aren't found
- **Directory Search**: Find directories by name or partial match

### OS Command Actions

The assistant can execute OS commands with the following safeguards:

1. **LLM Generation**: The LLM generates a structured action with command details
2. **Validation**: The OS execution service validates the action for safety
3. **User Confirmation**: The user must explicitly confirm before any execution
4. **Safe Execution**: Commands run in a controlled manner with proper error handling
5. **Result Feedback**: Command output is displayed to the user

### Supported Action Types

- **launch_app**: Open an application
- **os_command**: Execute a system command  
- **explain_download**: Explain how to download something
- **explain**: Provide an explanation about a topic
- **clarify**: Ask follow-up questions when user request is unclear
- **file_check**: Verify if a file exists before taking action
- **dir_search**: Search for directories by name
- **none**: No action required

## Scene-Based Interactions

The system supports scene-based interactions for role-playing and specialized behavior:

### Available Scenes

- **default_scene.yaml**: Default conversation between assistant and user
- **filesystem_assistant.yaml**: Specialized for file operations
- **help_desk_scenario.yaml**: Technical support role-play
- **sales_inquiry_scenario.yaml**: Sales representative role-play
- **template_scene.yaml**: Template for creating new scenes

### Scene Configuration Format

Here's an example scene configuration:

```yaml
name: Tech Support Call
roles:
  user: You are a technical support representative for a large tech company. You are patient, knowledgeable about computers and software, and committed to helping customers solve their problems.
  client: You are a customer having problems with your computer. You're frustrated because your computer keeps freezing, especially when you try to use specific applications.
scene: A customer has called the tech support hotline with a computer problem. The tech support representative needs to identify the issue and provide a solution. The customer is moderately tech-savvy but frustrated.
constraints:
  max_steps: 20
  style: The tech support rep should be professional but empathetic. The customer starts frustrated but can be calmed with good support.
```

### Creating New Scenes

You can create new scenes easily:

```bash
# Create a new scene from template
make new-scene NAME=my_custom_scene
```

Then edit the resulting file in the scenes directory.

## LLM Provider Configuration

The assistant supports different LLM backends:

### Ollama Integration (LLaMA)
To use Ollama with LLaMA:
1. Install Ollama: https://ollama.com/
2. Start Ollama server: `ollama serve`
3. Pull LLaMA model: `ollama pull llama2`
4. Set environment variables (optional):
   ```
   export OLLAMA_API_URL="http://localhost:11434/api/generate"
   export OLLAMA_MODEL="llama2"
   ```

### Claude Integration
To use Claude API:
1. Get a Claude API key
2. Set environment variables:
   ```
   export CLAUDE_API_KEY="your_api_key_here"
   export CLAUDE_MODEL="claude-3-haiku-20240307" # Optional, defaults to this
   ```

### Gemini Integration
To use Google's Gemini API:
1. Get a Gemini API key from Google AI Studio
2. Set environment variables:
   ```
   export GEMINI_API_KEY="your_api_key_here"
   export GEMINI_MODEL="gemini-2.0-flash-001" # Optional, defaults to this
   ```

## Next Steps

- Enhance file and directory operations with additional capabilities
- Expand the LLM's knowledge of file formats and handling
- Improve context handling for more natural conversations
- Add support for context-aware action generation
- Develop more advanced testing scenarios
- Expand scene simulator with multi-agent support

For detailed architecture information, see [ARCHITECTURE.md](ARCHITECTURE.md).