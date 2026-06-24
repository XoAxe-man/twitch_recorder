import os
import json
import hmac
import hashlib
import datetime
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

# Production configuration values are loaded from environment variables.
Secret = os.getenv('TWITCH_SECRET', 'default_fallback_secret_if_empty')
VOD_DIR = '/VOD'
AUTH_TOKEN = os.getenv('Twitch_auth_token', '')
PORT = 8080

# Maintain active recording subprocesses keyed by broadcaster login.
active_recordings = {}

class TwitchWebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the full request body for signature validation and payload parsing.
        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length)

        # Extract required EventSub headers.
        message_id = self.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = self.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        signature = self.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_type = self.headers.get('Twitch-Eventsub-Message-Type', '')

        # Validate request authenticity using HMAC SHA-256.
        hmac_message = message_id.encode('utf-8') + timestamp.encode('utf-8') + raw_body
        expected_signature = 'sha256=' + hmac.new(Secret.encode('utf-8'), hmac_message, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            print('Unauthorized request')
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Forbidden')
            return

        body = json.loads(raw_body)

        if message_type == 'webhook_callback_verification':
            # Respond to Twitch's initial subscription verification challenge.
            challenge = body['challenge']
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(challenge.encode('utf-8'))
            return

        elif message_type == 'notification':
            event_type = body.get('subscription', {}).get('type', '')
            broadcaster = body.get('event', {}).get('broadcaster_user_login', '')

            if event_type == 'stream.online':
                if broadcaster not in active_recordings or active_recordings[broadcaster].poll() is not None:
                    time_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
                    filepath = f'{VOD_DIR}/{broadcaster}_{time_str}'

                    # Create a recording pipeline: streamlink retrieves the Twitch stream,
                    # and ffmpeg copies the input stream into an MP4 container.
                    cmd = (
                        f'/usr/bin/streamlink "https://twitch.tv/{broadcaster}" best '
                        f'--retry-streams 5 --retry-max 3 '
                        f'--stream-timeout 30 '
                        f'--twitch-disable-hosting '
                        f'--twitch-disable-reruns '
                        f'--twitch-api-header "Authorization=OAuth {AUTH_TOKEN}" '
                        f'-o "{filepath}.ts" && '
                        f'/usr/bin/ffmpeg -y -i "{filepath}.ts" -c copy "{filepath}.mp4"'
                    )

                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        executable='/bin/bash',
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                    )
                    active_recordings[broadcaster] = process
                else:
                    print(f'Recording already active for {broadcaster}')

        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), TwitchWebHookHandler)
    print('Listening for webhooks on port', PORT)
    server.serve_forever()
