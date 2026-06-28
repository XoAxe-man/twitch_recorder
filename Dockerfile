# Base image provides a minimal Python 3.9 runtime.
FROM python:3.9-slim
LABEL maintainer="andrew.woehrle@gmail.com"

# Install FFmpeg via apt, then clean up the cache.
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install the absolute latest version of Streamlink directly from PyPI.
RUN pip install --no-cache-dir streamlink

# Set the working directory for the application.
WORKDIR /app

# Copy the recorder script into the container.
COPY twitch_recorder.py /app/twitch_recorder.py

# Run the recorder script in unbuffered mode for immediate log output.
CMD ["python", "-u", "twitch_recorder.py"]