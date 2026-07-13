import os
import json
import hmac
import hashlib
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

# Monitor configuration and Twitch API credentials.
# The script supports both EventSub webhook notifications and a polling fallback
# for configured streamer login names.
Secret = os.getenv('TWITCH_SECRET', 'default_fallback_secret_if_empty')
VOD_DIR = '/VOD/recordings'
CLIENT_ID = os.getenv('Twitch_client_id', '')
AUTH_TOKEN = os.getenv('Twitch_auth_token', '')
PORT = 8080

# Streamer logins to poll for live status when EventSub delivery is unavailable.
# This list is used by the polling fallback thread to query Twitch Helix.
TARGET_STREAMERS=['deme']

def trigger_recorder(broadcaster):
    """Send a recorder start command to the recorder service over internal HTTP."""
    url = 'http://twitch_recorder:9000' 
    payload = json.dumps({
        "broadcaster": broadcaster, 
        "action": "start"
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    
    try:
        urllib.request.urlopen(req)
        print(f"Successfully notified recorder container to start: {broadcaster}")
    except Exception as e:
        print(f"Failed to reach recorder for {broadcaster}: {e}")


def polling_loop():
    """Background thread function that polls the Twitch Helix API.

    This provides a polling fallback in addition to EventSub webhook handling.
    Polling can detect live streams for configured streamer logins and trigger
    recording even when webhook delivery is not available or delayed.
    """
    print(f"Starting Twitch polling background thread for: {TARGET_STREAMERS}")
    
    # Build the Twitch Helix API query for configured streamer logins.
    # The endpoint returns only live stream data for the requested users.
    query_string = '&'.join([f'user_login={s}' for s in TARGET_STREAMERS])
    url = f'https://api.twitch.tv/helix/streams?{query_string}'
    
    while True:
        if not TARGET_STREAMERS:
            time.sleep(60)
            continue
            
        try:
            req = urllib.request.Request(url, headers={
                'Client-Id': CLIENT_ID,
                'Authorization': f'Bearer {AUTH_TOKEN}'
            })
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            # Parse the Helix response and extract live streamer logins.
            active_streams = [stream.get('user_login') for stream in data.get('data', []) if stream.get('type') == 'live']
            
            for broadcaster in active_streams:
                print(f"[Polling] Detected {broadcaster} is live!")
                # Send the same recorder start command as the webhook path.
                # Duplicate start commands are safely ignored by the recorder service.
                trigger_recorder(broadcaster)
                
        except urllib.error.URLError as e:
            print(f"[Polling] Network error checking streams: {e}")
        except Exception as e:
            print(f"[Polling] Unexpected error: {e}")
            
        # Sleep for 2 minutes before polling again to respect Twitch rate limits.
        time.sleep(120)

class TwitchWebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length)

        message_id = self.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = self.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        signature = self.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_type = self.headers.get('Twitch-Eventsub-Message-Type', '')

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
            # Respond to Twitch subscription challenge verification.
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
                print(f"[Webhook] Stream online event received for: {broadcaster}")
                # Forward the request to the same recorder trigger helper used by polling.
                trigger_recorder(broadcaster)

            self.send_response(200)
            self.end_headers()
        
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Bad Request')
            return
        
if __name__ == '__main__':
    poller_thread = threading.Thread(target=polling_loop, daemon=True)
    poller_thread.start()

    server = HTTPServer(('0.0.0.0', PORT), TwitchWebHookHandler)
    print('Listening for webhooks on port', PORT)
    server.serve_forever()            