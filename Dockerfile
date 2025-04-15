FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for audio support
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    pulseaudio \
    libsndfile1 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
# Install dependencies directly from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make sure the entrypoint script is executable
# RUN chmod +x /app/docker-entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV AUDIO_LOG_DIR=/data/audio_logs

# Create directories
RUN mkdir -p /data/audio_logs

# Create volume for data
VOLUME ["/data", "/app"]

# Set the entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD []