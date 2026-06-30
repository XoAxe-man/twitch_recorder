import os
import json
import hmac
import hashlib
import datetime
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

# Load Twitch EventSub secrets and configuration from environment.
Secret = os.getenv('TWITCH_SECRET', 'default_fallback_secret_if_empty')
VOD_DIR = '/VOD/recordings'
AUTH_TOKEN = os.getenv('Twitch_auth_token', '')
PORT = 8080

# Track active recording processes to prevent duplicate streams.
active_recordings = {}

class TwitchWebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Parse incoming webhook request.
        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length)

        # Extract Twitch EventSub headers for signature validation.
        message_id = self.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = self.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        signature = self.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_type = self.headers.get('Twitch-Eventsub-Message-Type', '')

        # Verify webhook signature is from Twitch.
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
            # Handle initial webhook verification challenge from Twitch.
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
            time_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            if event_type == 'stream.online':
                if broadcaster not in active_recordings or active_recordings[broadcaster].poll() is not None:
                    filepath = f'{VOD_DIR}/{broadcaster}_{time_str}'

                    # Record stream with streamlink and transcode to MOV format.
                    cmd = (
                        f'/usr/local/bin/streamlink "https://twitch.tv/{broadcaster}?token={AUTH_TOKEN}" best '                   
                        f'--retry-streams 5 --retry-max 3 '
                        f'--stream-timeout 60 '
                        f'-o "{filepath}.ts" > "/VOD/logs/{broadcaster}_{time_str}_streamlink.log" 2>&1 && '
                        f'/usr/bin/ffmpeg -y -i "{filepath}.ts" -c:v h264_qsv -profile:v high -b:v 8000k -c:a pcm_s16le "{filepath}.mov" && '
                        f'rm "{filepath}.ts"'

                    )

                    # Start recording in background.
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
                    with open(f'/VOD/logs/{broadcaster}_{time_str}_recording.log', 'a') as f:
                        f.write(f'Recording already active for {broadcaster}\n')

        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), TwitchWebHookHandler)
    print('Listening for webhooks on port', PORT)
    server.serve_forever()
