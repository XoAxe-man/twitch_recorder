import os
import json
import hmac
import hashlib
import datetime
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuration values are loaded from environment variables for use on a Linux-based host.
Secret = os.getenv('TWITCH_SECRET', 'default_fallback_secret_if_empty')
VOD_DIR = '/VOD'
AUTH_TOKEN = os.getenv('Twitch_auth_token', '')
PORT = 8080

# Track active recording processes so the service does not start duplicate captures.
active_recordings = {}

class TwitchWebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the incoming webhook payload to validate its authenticity and parse the event data.
        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length)

        # Extract the Twitch EventSub headers needed for signature verification and event handling.
        message_id = self.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = self.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        signature = self.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_type = self.headers.get('Twitch-Eventsub-Message-Type', '')

        # Validate the request signature to ensure the webhook originated from Twitch.
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
            # Respond to Twitch's initial subscription verification challenge so the webhook can be registered successfully.
            challenge = body['challenge']
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(challenge)))
            self.end_headers()
            self.wfile.write(challenge.encode('utf-8'))
            return

        elif message_type == 'notification':
            event_type = body.get('subscription', {}).get('type', '')
            broadcaster = body.get('event', {}).get('broadcaster_user_login', '')

            if event_type == 'stream.online':
                if broadcaster not in active_recordings or active_recordings[broadcaster].poll() is not None:
                    time_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                    filepath = f'{VOD_DIR}/{broadcaster}_{time_str}'

                    # Capture live streams on Linux and export them into a format that is practical for post-production,
                    # including workflows that may later be imported into DaVinci Resolve.
                    cmd = (
                        f'/usr/bin/streamlink "https://twitch.tv/{broadcaster}" best '
                        f'--retry-streams 5 --retry-max 3 '
                        f'--stream-timeout 30 '
                        f'--twitch-disable-hosting '
                        f'--twitch-disable-reruns '
                        f'--twitch-api-header "Authorization=OAuth {AUTH_TOKEN}" '
                        f'-o "{filepath}.ts" && '
                        f'/usr/bin/ffmpeg -y -i "{filepath}.ts" -c:v h264_nvenc -preset p6 -profile:v high -b:v 8000k -c:a pcm_s16le "{filepath}.mov"'
                    )

                    # Launch the recording process in the background so the webhook handler can continue serving requests.
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
