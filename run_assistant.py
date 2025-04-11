#!/usr/bin/env python3
"""
Command-line interface for the text-based assistant with LLM→OS execution flow.
"""
import argparse
import sys
from text_assistant import TextAssistant

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the text assistant in interactive mode."
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["llama", "claude", "gemini", "simulation"],
        default="llama",
        help="LLM model to use (default: llama)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Execute actual OS commands (USE WITH CAUTION!)"
    )
    parser.add_argument(
        "--no-safe-mode",
        action="store_true",
        help="Disable safety checks for OS commands (DANGEROUS!)"
    )
    parser.add_argument(
        "--disable-os-commands",
        action="store_true",
        help="Disable OS command functionality"
    )
    parser.add_argument(
        "--conversation-turns",
        type=int,
        default=3,
        help="Maximum number of conversation turns to remember"
    )
    parser.add_argument(
        "--run-scenario",
        type=str,
        help="Run a specific scenario file instead of interactive mode"
    )
    return parser.parse_args()

def main():
    """Run the text assistant in interactive mode or with a scenario."""
    args = parse_args()
    
    print("\n===== Text Assistant =====")
    print("Stateful controller with LLM→OS execution flow")
    print("Type 'exit' to end the session\n")
    
    # Print configuration information
    print("Configuration:")
    
    # Display model information
    model_info = {
        "llama": "Llama (via Ollama) - Install Ollama locally with 'ollama serve'",
        "claude": "Claude - Requires CLAUDE_API_KEY environment variable",
        "gemini": "Gemini - Requires GEMINI_API_KEY environment variable",
        "simulation": "Simulation mode (no real LLM connected)"
    }
    print(f"- Model: {model_info.get(args.model, args.model)}")
    
    # Display OS command information
    if args.disable_os_commands:
        print("- OS commands: Disabled")
    else:
        print("- OS commands: Enabled")
        print(f"- Execution mode: {'Live' if args.no_dry_run else 'Dry run'}")
        print(f"- Safety checks: {'Disabled' if args.no_safe_mode else 'Enabled'}")
    
    print()
    
    # Configure the text assistant
    config = {
        "llm_model": args.model,
        "dry_run": not args.no_dry_run,
        "safe_mode": not args.no_safe_mode,
        "os_commands_enabled": not args.disable_os_commands,
        "conversation_turns": args.conversation_turns
    }
    
    # Initialize the assistant
    assistant = TextAssistant(config=config)
    
    # Either run a scenario or start interactive session
    if args.run_scenario:
        print(f"\nRunning scenario: {args.run_scenario}")
        result = assistant.process_scenario(args.run_scenario)
        print(f"\nScenario {'succeeded' if result.get('success') else 'failed'}")
        
        # Print results
        if result.get('steps'):
            for i, step in enumerate(result['steps']):
                print(f"\nStep {i+1}:")
                print(f"User: {step.get('user_input', 'N/A')}")
                
                if step.get('llm_response'):
                    print(f"Assistant: {step['llm_response'].get('response', 'N/A')}")
                    
                if step.get('action_result'):
                    action_result = step['action_result']
                    print(f"Action result: {action_result.get('status', 'N/A')}")
                    if 'stdout' in action_result and action_result['stdout']:
                        print(f"Output: {action_result['stdout']}")
    else:
        # Start interactive session
        try:
            # Use the built-in interactive session
            assistant.interactive_session()
                
        except KeyboardInterrupt:
            print("\nSession terminated by user.")
        except EOFError:
            print("\nInput stream closed.")
        
        print("\nThank you for using the Text Assistant!")

if __name__ == "__main__":
    main()