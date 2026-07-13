# Minimal Python 3.9 runtime for Twitch recorder service.
FROM python:3.9-slim
LABEL maintainer="andrew.woehrle@gmail.com"

# Install FFmpeg and clean up package manager cache.
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ffmpeg intel-media-va-driver vainfo \
    && rm -rf /var/lib/apt/lists/*

# Install Streamlink from PyPI.
RUN pip install --no-cache-dir streamlink

# Set application working directory.
WORKDIR /app

# Copy recorder script to container.
COPY twitch_recorder.py /app/twitch_recorder.py
COPY twitch_monitor.py /app/twitch_monitor.py

# Run with unbuffered output for real-time logging.
# Run both monitor and recorder. Use a shell so both processes run
# (monitor in background, recorder in foreground) and container stays alive.
CMD ["python", "--version"]