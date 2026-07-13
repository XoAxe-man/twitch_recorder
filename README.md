# Twitch Recorder

A lightweight Docker Compose service for automatically recording Twitch streams.

This repository contains two Python-based containers:
- `monitor`: receives Twitch EventSub webhook notifications and validates signatures
- `twitch_recorder`: launches recordings when a monitored broadcaster goes live

Recorded VODs are saved to a host-mounted volume for persistent storage.

## Project Structure

- `twitch_monitor.py`: EventSub webhook receiver and internal IPC client
- `twitch_recorder.py`: internal HTTP listener and recorder launcher
- `Dockerfile`: container image build definition
- `docker-compose.yml`: service orchestration for monitor and recorder
- `twitch-recorder.env`: environment configuration template

## Dependencies

The container image installs:
- Python 3.9
- `ffmpeg`
- `streamlink`

These are installed automatically when the Docker image is built.

## Configuration

### Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `TWITCH_SECRET` | EventSub webhook signature validation secret |
| `Twitch_auth_token` | Twitch OAuth token used by Streamlink |
| `Twitch_client_id` | Twitch API client identifier (used externally for subscription setup) |

Put these values into `twitch-recorder.env` and keep the file out of source control.

### Example `twitch-recorder.env`

```env
TWITCH_SECRET=your_webhook_secret_here
Twitch_auth_token=your_oauth_token_here
Twitch_client_id=your_client_id_here
```

## Setup

1. Create or update `twitch-recorder.env` with your Twitch credentials.
2. Ensure the host directories exist and are writable:
   - `/volume1/VOD/recordings`
   - `/volume1/VOD/logs`
3. Start the services with Docker Compose:

```bash
docker compose up --build -d
```

4. Make sure Twitch EventSub webhook events are configured to POST to the host on port `8080`.

## Runtime Behavior

- `monitor` listens on port `8080` for Twitch EventSub requests.
- It validates webhook signatures using `TWITCH_SECRET`.
- When a `stream.online` notification arrives, it sends an internal POST to `twitch_recorder:9000`.
- `twitch_recorder` starts a background Streamlink recording process and logs activity.

## Docker Compose Notes

The compose file defines two services connected by the `internal_ipc` network:
- `monitor` exposes port `8080`
- `twitch_recorder` exposes port `9000` internally

Both services share the same `twitch-recorder.env` file and mount host volumes for logs and recordings.

## Output

Recorded files are stored in the host-mounted `/VOD/recordings/` directory.
Files are named using the broadcaster login and a timestamp, for example:

```text
streamer_2026-07-13_12-34-56.mov
```

## Security Considerations

- Do not commit `twitch-recorder.env` or other secrets to Git.
- Use a private network for webhook delivery and internal container communication.
- Rotate tokens and secrets regularly.
- Protect the host volume mounted at `/VOD/recordings` and `/VOD/logs`.
