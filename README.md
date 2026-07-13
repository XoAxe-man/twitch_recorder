# Twitch Recorder

A lightweight Docker-based service with a decoupled Twitch EventSub monitor and recorder architecture. The monitor container validates incoming EventSub notifications and forwards recording requests to a separate recorder container over an internal Docker network.

## Project Structure

- **`twitch_monitor.py`**: EventSub webhook receiver and internal IPC client
- **`twitch_recorder.py`**: Internal IPC server and stream recorder
- **`Dockerfile`**: Container image build definition (Python 3.9, ffmpeg, streamlink)
- **`docker-compose.yml`**: Service orchestration, environment configuration, and volume management
- **`twitch-recorder.env`**: Environment variable template for configuration

## Dependencies

The project depends on the following runtime components:

- Python 3.9 (base image: `python:3.9-slim`)
- ffmpeg
- streamlink

All dependencies are automatically installed during the container build process.

## Configuration

### Required Environment Variables

| Variable | Purpose |
|----------|----------|
| `TWITCH_SECRET` | EventSub webhook signature validation key |
| `Twitch_auth_token` | OAuth token for authenticated stream access |
| `Twitch_client_id` | Twitch API client identifier |

These values are loaded from the `.env` file and passed to both containers via `docker-compose.yml`.

### Example Configuration

Create `twitch-recorder.env` with your credentials:

```env
TWITCH_SECRET=your_webhook_secret_here
Twitch_auth_token=your_oauth_token_here
Twitch_client_id=your_client_id_here
```

⚠️ **Important**: Never commit actual credentials to version control.

## Usage

1. Create or update `twitch-recorder.env` with valid Twitch credentials.
2. Ensure the host paths mounted under `/volume1/VOD/` exist and are writable.
3. Start the services with Docker Compose:

```bash
docker compose up --build -d
```

4. Register your Twitch EventSub subscription to send webhook notifications to port `8080` on your server.

5. The monitor container receives the EventSub notification and forwards a start command to the recorder container over the internal `internal_ipc` network.

### Recording command flow

The recorder builds and executes a safe two-step command. It writes a temporary `.ts` file, converts it to a `.mov`, removes the intermediate `.ts`, and avoids leaving duplicate output files.

```bash
# Example (run inside the container):
tmp="/tmp/${broadcaster}.ts"
out="/VOD/recordings/${broadcaster}_${timestamp}.mov"

streamlink "https://twitch.tv/${broadcaster}" best -O > "$tmp" \
	&& ffmpeg -y -i "$tmp" -c copy "$out" \
	&& rm -f "$tmp"
```

## Output

Recorded streams are saved to `/VOD/recordings/` on the host system. Files are named with the format: `{broadcaster_login}_{YYYY-MM-DD_HH-MM-SS}.mov`

## Technical Details

- **Decoupled Architecture**: `twitch_monitor` handles EventSub validation, while `twitch_recorder` performs recording.
- **Internal IPC**: The monitor sends JSON start commands to the recorder container over a private Docker network.
- **Signature Validation**: Twitch EventSub webhooks are validated using HMAC-SHA256.
- **Stream Capture**: `streamlink` pipes data to `ffmpeg` for MOV output and temporary `.ts` cleanup.
- **Ports**: The monitor exposes port `8080` for Twitch EventSub; the recorder listens on port `9000` on the internal Docker network only.

## Security Considerations

- **Credentials**: Never commit `.env` files or expose `TWITCH_SECRET`, `Twitch_auth_token`, or `Twitch_client_id` in source control.
- **Storage**: Restrict access to the host VOD recording volume.
- **Logs**: Do not log sensitive values; configure log rotation and retention policies.
- **Network**: Keep the recorder port private by using the internal Docker network `internal_ipc`.
