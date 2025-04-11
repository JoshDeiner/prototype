#!/usr/bin/env python3
"""Script to run tests for the LLM service."""
import os
import sys
import argparse
import subprocess

def run_command(command):
    """Run a command and return the result."""
    print(f"\nRunning: {' '.join(command)}\n")
    
    # Set PYTHONPATH to include the current directory
    env = os.environ.copy()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{current_dir}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = current_dir
    
    result = subprocess.run(command, capture_output=False, env=env)
    return result.returncode

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for the LLM service")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "gemini", "fallback"],
        help="Type of tests to run",
    )
    return parser.parse_args()

def check_env():
    """Check if necessary environment variables are set."""
    # Check if .env file exists
    if not os.path.exists(os.path.join(os.path.dirname(__file__), ".env")):
        print("Warning: .env file not found. Some tests may fail.")
        return False
    
    # Check for Gemini API key
    with open(os.path.join(os.path.dirname(__file__), ".env"), "r") as f:
        env_content = f.read()
    
    if "GEMINI_API_KEY=" in env_content and "GEMINI_API_KEY=" not in env_content.split("\n"):
        print("Warning: GEMINI_API_KEY is not set in .env file. Gemini tests will be skipped.")
        return False
    
    return True

def main():
    """Run tests based on command line arguments."""
    args = parse_args()
    
    # Check environment before running tests
    check_env()
    
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if args.test_type == "unit":
        # Run unit tests
        return run_command(["python", "-m", "pytest", "tests/unit", "-v"])
        
    elif args.test_type == "integration":
        # Run integration tests
        return run_command(["python", "-m", "pytest", "tests/integration", "-v"])
        
    elif args.test_type == "all":
        # Run all pytest tests
        return run_command(["python", "-m", "pytest", "-v"])
        
    elif args.test_type == "gemini":
        # Run Gemini interactive test
        return run_command(["python", "tests/manual/test_gemini.py"])
        
    elif args.test_type == "fallback":
        # Run fallback test
        return run_command(["python", "tests/manual/test_llm_fallback.py"])
    
    return 0

if __name__ == "__main__":
    sys.exit(main())