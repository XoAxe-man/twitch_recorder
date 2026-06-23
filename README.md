# Twitch Recorder

This repository contains a lightweight Twitch EventSub webhook listener and recording service.
It is designed to start recording when a configured Twitch channel goes live, saving VOD files to a mounted host volume.

## Overview

- `twitch_recorder.py`: Python-based webhook handler for Twitch EventSub notifications.
- `Dockerfile`: Builds a container with Python 3.9, `ffmpeg`, and `streamlink`.
- `docker-compose.yml`: Defines the service configuration, environment injection, port mapping, and storage mount.
- `twitch-recorder.env`: Example environment variable file for local deployment.

## Dependencies

The project depends on the following runtime components:

- Python 3.9 (base image: `python:3.9-slim`)
- ffmpeg
- streamlink

The container installs these dependencies automatically during image build.

## Configuration

Required environment variables:

- `TWITCH_SECRET`: Secret used to validate Twitch EventSub webhook signatures.
- `Twitch_auth_token`: OAuth token used by `streamlink` to access Twitch streams.
- `Twitch_client_id`: Twitch client ID used for Twitch API interactions.

The service reads these values from environment variables, typically provided through the `.env` file referenced by `docker-compose.yml`.

### Example `.env` values

```env
TWITCH_SECRET=your_webhook_secret
Twitch_auth_token=your_twitch_auth_token
Twitch_client_id=your_twitch_client_id
```

> Do not commit actual secret values to source control.

## Usage

1. Create or update `twitch-recorder.env` with valid Twitch credentials.
2. Ensure the host path mounted at `/volume1/VOD/` exists and is writable.
3. Start the service with Docker Compose:

```bash
docker compose up --build -d
```

4. Configure your Twitch EventSub subscription to send webhook notifications to the container's exposed port `8080`.

## Recorded Output

Recorded video files are saved to the mounted volume at `/VOD` inside the container.
Files are named using the broadcaster's login and the current timestamp.

## Notes

- The script validates Twitch EventSub webhook signatures using HMAC SHA-256.
- `streamlink` is piped directly into `ffmpeg` to capture the live stream without transcoding.
- The container exposes port `8080` for receiving webhook callbacks.

## Security

- Keep `TWITCH_SECRET`, `Twitch_auth_token`, and `Twitch_client_id` confidential.
- Use a secure volume for recorded VOD files and avoid exposing secret values in logs or source control.
