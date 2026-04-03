# auth_check.py
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_creds():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            # Since we are in Cloud Shell, we use a local server on a high port
            creds = flow.run_local_server(port=8081)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    print("✅ OAuth Token Generated Successfully!")

if __name__ == "__main__":
    get_creds()