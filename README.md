# Twitch Recorder

A lightweight Docker Compose service for automatically recording Twitch streams.

This repository contains two Python-based containers:
- `monitor`: receives Twitch EventSub webhook notifications, validates signatures, and optionally polls Twitch Helix for configured streamers
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

## Run the remote transcoder as a daemon

The local recorder and monitor services are managed by Docker Compose, while the remote transcoding computer should keep the `transcode_vod.sh` helper script available and ready to execute.

You can use a systemd service on the transcoding host to ensure the script environment is prepared and mounted paths are available.

### Example systemd service for the transcoder host

```ini
[Unit]
Description=Transcode VOD script helper
After=network.target remote-fs.target

[Service]
Type=oneshot
ExecStart=/opt/scripts/transcode_vod.sh /mnt/vod/last_input.ts
RemainAfterExit=yes
WorkingDirectory=/opt/scripts
User=axe-man
Group=axe-man

[Install]
WantedBy=multi-user.target
```

This example service is a template for ensuring systemd can execute the script in the correct environment. In practice, the recorder container invokes `transcode_vod.sh` over SSH for each completed recording.

### Enable the transcoder host service

```bash
sudo systemctl enable transcode-vod.service
sudo systemctl start transcode-vod.service
```

If the transcoder host must expose the script over SSH, confirm that the SSH key, user account, and mount points are configured before starting the service.

## Runtime Behavior

- `monitor` listens on port `8080` for Twitch EventSub requests.
- It validates webhook signatures using `TWITCH_SECRET`.
- `monitor` also polls the Twitch Helix API periodically for configured streamer logins, triggering the recorder when a live stream is detected.
- When a `stream.online` notification arrives, it sends an internal POST to `twitch_recorder:9000`.
- `twitch_recorder` starts a background Streamlink recording process and logs activity.

## Docker Compose Notes

The compose file defines two services connected by the `internal_ipc` network:
- `monitor` exposes port `8080`
- `twitch_recorder` exposes port `9000` internally

Both services share the same `twitch-recorder.env` file and mount host volumes for logs and recordings.

## Transcoding Computer Setup

The recorder container triggers a remote transcoding script over SSH on a second machine.

- The remote host should have the recorded volume mounted at `/mnt/vod/`.
- The script is expected to live at `/opt/scripts/transcode_vod.sh`.
- The recorder sends the raw `.ts` path in `/VOD/` format, and the script rewrites that path to the local `/mnt/vod/` mount.
- The transcoding host should expose a `~/Logs` directory for ffmpeg logs.
- The script remuxes the raw file, encodes video with NVIDIA CUDA, extracts the audio track, and moves the final files back to the shared recording destination.

Example SSH command used by the recorder container:

```bash
ssh -i ~/.ssh/naspasskey USER@<TRANSCODE_HOST_IP> "/opt/scripts/transcode_vod.sh '/VOD/recordings/streamer_2026-07-13_12-34-56.ts'"
```

Ensure the SSH key and user permissions are configured correctly before using the remote transcoder.

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
