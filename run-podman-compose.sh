#!/bin/bash

# Run podman-compose with the specified arguments
# The -it flags ensure proper terminal attachment
podman-compose run --rm -it voice-assistant "$@"