"""Pytest configuration file."""
import os
import sys
import pytest

# Add the parent directory to the Python path
# This allows imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define fixtures that can be used across all tests
@pytest.fixture
def test_query():
    """Return a standard test query for LLM testing."""
    return "What is a Raspberry Pi?"