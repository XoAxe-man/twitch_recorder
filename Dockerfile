# Base image provides a minimal Python 3.9 runtime.
FROM python:3.9-slim
LABEL maintainer="andrew.woehrle@gmail.com"

# Install required system packages for video downloading and playback.
# Update the package lists first, then install ffmpeg and streamlink in one command.
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ffmpeg streamlink \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory for the application.
WORKDIR /app

# Copy the recorder script into the container.
COPY twitch_recorder.py /app/twitch_recorder.py

# Run the recorder script in unbuffered mode for immediate log output.
CMD ["python", "-u", "twitch_recorder.py"]
