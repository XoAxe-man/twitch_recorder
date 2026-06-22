# Default Dockerfile template
FROM python:3.9-slim
LABEL maintainer="andrew.woehrle@gmail.com"

RUN apt-get install && apt-get update -y && apt-get install -y ffmpeg && apt-get install -y streamlink && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY twitch_recorder.py /app/twitch_recorder.py

CMD ["python", "-u", "twitch_recorder.py"]
