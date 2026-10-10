#!/usr/bin/env python3
"""
YouTube OAuth Channel Authenticator for New Viral Shorts Channel.
Run this command in terminal to link your new YouTube channel!
Command: python3 authenticate_youtube.py
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
os.makedirs(CONFIG_DIR, exist_ok=True)

CLIENT_SECRETS_FILE = os.path.join(CONFIG_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(CONFIG_DIR, "youtube_token.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

def main():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"❌ Error: {CLIENT_SECRETS_FILE} not found!")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("🔑 YOUTUBE CHANNEL 1-CLICK AUTHENTICATOR")
    print("=" * 65)
    print("Browser khulega, apna NAYA BRAND CHANNEL select kijiye!")
    print("=" * 65 + "\n")

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=8080, prompt="consent")

    with open(TOKEN_FILE, "w", encoding="utf-8") as token:
        token.write(creds.to_json())

    print("\n" + "🎉" * 20)
    print(f"✅ Mubarak ho! Naya YouTube Channel connect ho gaya hai!")
    print(f"Token saved at: {TOKEN_FILE}")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
