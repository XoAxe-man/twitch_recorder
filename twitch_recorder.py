import os   
import json
import hmac
import hashlib
import datetime
import subprocess
import cmd
from http.server import BaseHTTPRequestHandler, HTTPServer

# This script listens for Twitch EventSub webhooks and starts/stops recordings.
# The secret is used to verify that webhook requests really came from Twitch.
Secret = os.getenv('TWITCH_SECRET', 'default_fallback_secret_if_empty')  # Replace with your own secret or set as an environment variable
VOD_DIR = '/VOD'  # Folder where recorded videos are saved
AUTH_TOKEN = os.getenv('Twitch_auth_token', '')  # Twitch token used by streamlink
PORT = 8080  # Local port for the webhook endpoint

# Track currently running subprocesses by broadcaster name.
active_recordings = {}

class TwitchWebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read raw request body so we can verify the signature and parse JSON.
        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length)

        # Read request metadata sent by Twitch in the webhook headers.
        message_id = self.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = self.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        signature = self.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_type = self.headers.get('Twitch-Eventsub-Message-Type', '')

        # Recreate the expected HMAC signature to confirm the message is authentic.
        hmac_message = message_id.encode('utf-8') + timestamp.encode('utf-8') + raw_body
        expected_signature = 'sha256=' + hmac.new(Secret.encode('utf-8'), hmac_message, hashlib.sha256).hexdigest()

        # Reject requests if the signature doesn't match.
        if not hmac.compare_digest(expected_signature, signature):
            print("Unauthorized request!")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        # Parse the JSON payload once the signature has been verified.
        body = json.loads(raw_body)

        # Twitch sends a challenge during webhook setup; we must return it as-is.
        if message_type == 'webhook_callback_verification':
            print("Verification challenge received and approved.")
            challenge = body['challenge']
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(challenge.encode('utf-8'))
            return

        # Handle live notifications from Twitch.
        elif message_type == 'notification':
            event_type = body.get('subscription', {}).get('type', '')
            broadcaster = body.get('event', {}).get('broadcaster_user_login', '')

            # Start recording if a stream goes online and we are not already recording it.
            if event_type == 'stream.online':
                if broadcaster not in active_recordings or active_recordings[broadcaster].poll() is not None:
                    time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                    filename = f"{VOD_DIR}/{broadcaster}_{time_str}_hevc.mp4"

                    # Pipe streamlink output directly into ffmpeg to save resources and because twitch uses mpeg4 h.264 I am not transcoding the video stream, just copying it. Audio is also copied without transcoding.
                    cmd = (
                        f'streamlink "https://twitch.tv/{broadcaster}?token={AUTH_TOKEN}" best -O | '
                        f'ffmpeg -i - -c:v copy -c:a copy "{filename}"'
                    )

                    # Run the recording pipeline in a shell.
                    process = subprocess.Popen(
                             cmd, 
                             shell=True, 
                             executable='/bin/bash',
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL
                            )
                    active_recordings[broadcaster] = process
                else:
                    print(f"--> Received Webhook but already recording.")

        # Always return 200 once the request has been handled.
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    # Start the local webhook server so Twitch can send event notifications.
    server = HTTPServer(('0.0.0.0', PORT), TwitchWebHookHandler)
    print("Listening for Webhooks")
    server.serve_forever()
