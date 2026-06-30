# Twitch Recorder

A lightweight Docker-based service for automatically recording Twitch streams. This application listens for Twitch EventSub webhook notifications and automatically records streams when configured channels go live, saving VOD files to persistent storage.

## Project Structure

- **`twitch_recorder.py`**: Python-based EventSub webhook handler and recording orchestrator
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

These values are loaded from the `.env` file and passed to the container via `docker-compose.yml`.

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
2. Ensure the host path mounted at `/volume1/VOD/` exists and is writable.
3. Start the service with Docker Compose:

```bash
docker compose up --build -d
```

4. Register your Twitch EventSub subscription to send webhook notifications to port `8080` on your server.

### Recording command

The recorder uses a safe two-step command that writes a temporary `.ts` file, converts it to a `.mov`, removes the intermediate `.ts`, and avoids creating duplicate output files. Variables like `broadcaster` and `timestamp` are set by the recorder at runtime.

```bash
# Example (run inside the container):
tmp="/tmp/${broadcaster}.ts"
out="/VOD/recordings/${broadcaster}_${timestamp}.mov"

streamlink "https://twitch.tv/${broadcaster}" best -O > "$tmp" \
	&& ffmpeg -y -i "$tmp" -c copy "$out" \
	&& rm -f "$tmp"
```
This ensures intermediate `.ts` files are deleted and avoids producing duplicate VOD files when re-running or recovering from failures.

## Output

Recorded streams are saved to `/VOD/recordings/` on the host system. Files are named with the format: `{broadcaster_login}_{YYYY-MM-DD_HH-MM-SS}.mov`

## Technical Details

- **Signature Validation**: EventSub webhooks are validated using HMAC-SHA256 to ensure authenticity
- **Stream Capture**: `streamlink` streams directly to `ffmpeg` for efficient transcoding to MOV format
- **Webhook Port**: The service listens on port `8080` for EventSub notifications
- **Authentication**: OAuth tokens are passed via URL parameters to minimize API header overhead and reduce rate-limiting issues

## Security Considerations

- **Credentials**: Never commit `.env` files or expose `TWITCH_SECRET`, `Twitch_auth_token`, or `Twitch_client_id` in source control
- **Storage**: Restrict access to the VOD recording volume
- **Logs**: Sensitive values should not be logged; configure log rotation and retention policies
- **Network**: Deploy the service within a secure network environment
