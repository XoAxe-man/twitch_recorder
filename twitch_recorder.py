import os
import json
import hmac
import hashlib
import datetime
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

Secret = os.getenv('TWITCH_SECRET', 'default_fallback_secret_if_empty')
VOD_DIR = '/VOD/recordings'
AUTH_TOKEN = os.getenv('Twitch_auth_token', '')
PORT = 9000

active_recordings = {}

class InternalIPC_Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the JSON payload from the Monitor
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        payload = json.loads(post_data.decode('utf-8'))

        broadcaster = payload.get('broadcaster')
        action = payload.get('action')

        if action == "start":
            print(f"Received command to start recording: {broadcaster}")
            time_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filepath = f"{VOD_DIR}/{broadcaster}_{time_str}"
            if broadcaster not in active_recordings:
                # Record stream with streamlink and transcode to MOV format.
                cmd = (
                    f'/usr/local/bin/streamlink "https://twitch.tv/{broadcaster}?token={AUTH_TOKEN}" best '
                    f'--retry-streams 5 --retry-max 3 '
                    f'--stream-timeout 60 '
                    f'-o "{filepath}.ts" > "/VOD/logs/{broadcaster}_{time_str}_streamlink.log" 2>&1 && '
                    f'/usr/bin/ffmpeg -y -vaapi_device /dev/dri/renderD128 -i "{filepath}.ts" -vf "format=nv12,hwupload" -c:v h264_vaapi -profile:v high -qp 23 -c:a pcm_s16le "{filepath}.mov" && '
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
        self.wfile.write(b"Recording triggered")

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), InternalIPC_Handler)
    print('Listening for internal IPC messages on port', PORT)
    server.serve_forever()
