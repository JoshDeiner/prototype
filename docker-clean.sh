#!/bin/bash

# Stop and remove the container if it exists
docker rm -f assistant-dev-container 2>/dev/null || true

# Remove the image
docker rmi -f assistant-dev 2>/dev/null || true

echo "Docker cleanup complete"