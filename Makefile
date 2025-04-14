.PHONY: run run-scene run-file run-help run-test clean docker-build docker-run docker-up docker-up-run docker-up-help docker-down docker-test run-audio run-audio-scene run-audio-file run-audio-help run-audio-browser run-audio-sim run-audio-claude run-audio-gemini list-audio-devices

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

# Audio-enabled versions
# Run with audio support
run-audio:
	python main.py --audio

# Run with audio and specific scene
run-audio-scene:
	python main.py --audio --scene $(SCENE)

# Run file assistant with audio
run-audio-file:
	python main.py --audio --scene filesystem_assistant

# Run help desk with audio
run-audio-help:
	python main.py --audio --scene help_desk_scenario

# Run browser help with audio
run-audio-browser:
	python main.py --audio --scene chrome_help

# Run simulation with audio
run-audio-sim:
	python main.py --audio --model simulation

# Run with specific model and audio
run-audio-claude:
	python main.py --audio --model claude

run-audio-gemini:
	python main.py --audio --model gemini

# List available audio devices
list-audio-devices:
	python main.py --list-audio-devices

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

# Run Docker with audio support
docker-run-audio:
	docker run -it --device /dev/snd voice-assistant --audio $(ARGS)

# Docker Compose commands
docker-up:
	docker-compose up

docker-up-run:
	docker-compose run voice-assistant $(ARGS)

docker-up-help:
	docker-compose run voice-assistant --scene help_desk_scenario --data-dir /app/data

# Docker Compose with audio
docker-up-audio:
	docker-compose run --device /dev/snd voice-assistant --audio $(ARGS)

docker-up-audio-help:
	docker-compose run --device /dev/snd voice-assistant --audio --scene help_desk_scenario --data-dir /app/data

docker-down:
	docker-compose down

# Run tests in Docker
docker-test:
	docker run voice-assistant python -m pytest tests/