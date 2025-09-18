# Use slim image to reduce size & deploy time
FROM python:3.11-slim

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install only required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /SilentXBotz

# Copy and install dependencies first (better caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy rest of the bot code
COPY . .

# Run bot
CMD ["python3", "bot.py"]
