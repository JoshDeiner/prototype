FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make sure the entrypoint script is executable
# RUN chmod +x /app/docker-entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data

# Create volume for data
VOLUME ["/data", "/app"]

# Set the entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD []