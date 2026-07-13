import os
import json
import hmac
import hashlib
import datetime
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

# Read EventSub secret and Twitch auth token from environment variables.
Secret = os.getenv('TWITCH_SECRET', 'default_fallback_secret_if_empty')
VOD_DIR = '/VOD/recordings'
AUTH_TOKEN = os.getenv('Twitch_auth_token', '')
PORT = 8080

class TwitchWebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the raw webhook request body for processing.
        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length)

        # Extract EventSub headers required to verify the webhook signature.
        message_id = self.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = self.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        signature = self.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_type = self.headers.get('Twitch-Eventsub-Message-Type', '')

        # Compute and verify the HMAC signature to authenticate the incoming request.
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
            # Respond to Twitch's webhook subscription verification challenge.
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
            
            # Only trigger on 'stream.online' events
            if event_type == 'stream.online':
                print(f"Stream online event received for: {broadcaster}")
                
                # Forward the start-recording command to the recorder container via internal HTTP.
                import urllib.request
                # NOTE: This hostname must match the recorder service name in docker-compose.
                url = 'http://twitch_recorder:9000' 
                payload = json.dumps({
                    "broadcaster": broadcaster, 
                    "action": "start"
                }).encode('utf-8')
                
                req = urllib.request.Request(url, data=payload, method='POST')
                req.add_header('Content-Type', 'application/json')
                
                try:
                    urllib.request.urlopen(req)
                    print("Successfully notified recorder container.")
                except Exception as e:
                    print(f"Failed to reach recorder: {e}")

            # Always acknowledge Twitch with 200 OK after processing the notification.
            self.send_response(200)
            self.end_headers()
        
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Bad Request')
            return
        
if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), TwitchWebHookHandler)
    print('Listening for webhooks on port', PORT)
    server.serve_forever()            