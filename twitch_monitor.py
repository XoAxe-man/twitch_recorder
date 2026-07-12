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

        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Bad Request')
            return
            