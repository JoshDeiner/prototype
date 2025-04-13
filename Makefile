.PHONY: run run-scene run-file run-help run-test clean docker-build docker-run docker-up docker-up-run docker-up-help docker-down docker-test

# Default target
all: run

# Run with default settings
run:
	python main.py

# Run with a specific scene
run-scene:
	python main.py --scene $(SCENE)

# Run file assistant scenario
run-file:
	python main.py --scene filesystem_assistant

# Run help desk scenario
run-help:
	python main.py --scene help_desk_scenario

# Run browser help scenario
run-browser:
	python main.py --scene chrome_help

# Run in simulation mode
run-sim:
	python main.py --model simulation

# Run with specific model
run-claude:
	python main.py --model claude

run-gemini:
	python main.py --model gemini

# List available scenes
list-scenes:
	python main.py --list-scenes

# Run tests
test:
	python -m pytest tests/

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker commands
docker-build:
	docker build -t voice-assistant .

docker-run:
	docker run -it voice-assistant $(ARGS)

# Docker Compose commands
docker-up:
	docker-compose up

docker-up-run:
	docker-compose run voice-assistant $(ARGS)

docker-up-help:
	docker-compose run voice-assistant --scene help_desk_scenario --data-dir /app/data

docker-down:
	docker-compose down

# Run tests in Docker
docker-test:
	docker run voice-assistant python -m pytest tests/