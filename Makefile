# Makefile for the prototype assistant system

# Default Python executable
PYTHON = python
MODEL ?= gemini

# Default directories
OUTPUT_DIR = output
SCENE_DIR = scenes
DATA_DIR = data

# Helper functions
define print_help
	@echo "$$HELP_TEXT"
endef

# Main targets
.PHONY: help run run-scene test clean

help:
	$(call print_help)

# Run the unified assistant (default entry point)
run:
	$(PYTHON) unified_assistant.py --model $(MODEL) --data-dir $(DATA_DIR)

# Run a specific scene
run-scene:
ifdef SCENE
	$(PYTHON) unified_assistant.py --scene $(SCENE) --model $(MODEL) --data-dir $(DATA_DIR)
else
	@echo "Usage: make run-scene SCENE=scene_name.yaml"
endif

# Run the file assistant (convenience shortcut)
run-file:
	$(PYTHON) unified_assistant.py --scene filesystem_assistant.yaml --model $(MODEL) --data-dir $(DATA_DIR)

# Run the help desk assistant (convenience shortcut)
run-help:
	$(PYTHON) unified_assistant.py --scene help_desk_scenario.yaml --model $(MODEL) --data-dir $(DATA_DIR)

# Run the sales assistant (convenience shortcut)
run-sales:
	$(PYTHON) unified_assistant.py --scene sales_inquiry_scenario.yaml --model $(MODEL) --data-dir $(DATA_DIR)

# List all available scenes
list-scenes:
	$(PYTHON) unified_assistant.py --list-scenes

# Run the tests
test:
	$(PYTHON) -m pytest

# Clean output directories
clean:
	rm -rf $(OUTPUT_DIR)/*
	mkdir -p $(OUTPUT_DIR)/audio
	mkdir -p $(OUTPUT_DIR)/scenes
	@echo "Cleaned output directories"

# Create a new scene from template
new-scene:
ifdef NAME
	cp $(SCENE_DIR)/template_scene.yaml $(SCENE_DIR)/$(NAME).yaml
	@echo "Created new scene: $(SCENE_DIR)/$(NAME).yaml"
else
	@echo "Usage: make new-scene NAME=scene_name"
endif

# Define help text
define HELP_TEXT

Prototype Assistant - Makefile Help
=====================================

Available commands:

  make run                Run the unified assistant (primary entry point)
  make run-scene SCENE=x  Run with a specific scene file
  make run-file           Run the file operations assistant
  make run-help           Run the help desk scenario
  make run-sales          Run the sales inquiry scenario
  make list-scenes        List all available scenes
  make test               Run all tests
  make clean              Clean output directories
  make new-scene NAME=x   Create a new scene from template

Options:
  MODEL=x                 Set the LLM model (llama, gemini, claude)
                          Example: make run MODEL=gemini

endef

export HELP_TEXT