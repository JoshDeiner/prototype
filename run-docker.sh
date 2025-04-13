#!/bin/bash

# Run the Docker container with the current directory mounted
docker run -it \
  --name assistant-dev-container \
  -v $(pwd):/app \
  -v $(pwd)/data:/data \
  assistant-dev "$@"