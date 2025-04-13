#!/bin/bash

# Run docker compose with the specified arguments
# The -it flags ensure proper terminal attachment
docker-compose run --rm -it voice-assistant "$@"