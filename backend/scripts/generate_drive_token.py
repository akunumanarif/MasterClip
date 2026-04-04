"""
Run this ONCE locally to authorize Google Drive access.
It will open a browser window for login, then save the token to credentials/.

Usage:
    cd backend
    pip install google-auth-oauthlib
    python scripts/generate_drive_token.py

Prerequisites:
    1. Google Cloud Console → APIs & Services → Credentials
       → Create Credentials → OAuth 2.0 Client ID → Desktop app
       → Download JSON → save as backend/credentials/oauth_client_secret.json

After running:
    Upload the generated token to your VM:
    scp backend/credentials/google_drive_token.json ubuntu@<VM_IP>:~/MasterClip/backend/credentials/
"""
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'credentials')
CLIENT_SECRET = os.path.join(BASE_DIR, 'oauth_client_secret.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'google_drive_token.json')

if not os.path.exists(CLIENT_SECRET):
    print(f"❌ Client secret not found at: {os.path.abspath(CLIENT_SECRET)}")
    print("   Download it from Google Cloud Console → Credentials → OAuth 2.0 Client IDs")
    exit(1)

print("🌐 Opening browser for Google Drive authorization...")
flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
creds = flow.run_local_server(port=0)

token_data = {
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': list(creds.scopes),
}

with open(TOKEN_PATH, 'w') as f:
    json.dump(token_data, f, indent=2)

print(f"\n✅ Token saved to: {os.path.abspath(TOKEN_PATH)}")
print("\nNext step — upload to VM:")
print(f"  scp backend/credentials/google_drive_token.json ubuntu@136.110.35.155:~/MasterClip/backend/credentials/")
