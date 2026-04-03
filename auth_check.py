# auth_check.py
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_creds():
    # Load the client secret you downloaded
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', 
        scopes=SCOPES
    )

    # Use the 'console' or 'redirect_uri' strategy for Cloud Shell
    # This will give you a link and ask you to paste a code back
    print("\n1. Open the URL below in your browser.")
    print("2. Log in and click 'Advanced' -> 'Go to... (unsafe)'.")
    print("3. Copy the 'Authorization Code' shown at the end.")
    
    # This method is more reliable in remote environments
    creds = flow.run_local_server(
        port=8081,
        host='localhost',
        success_message='Success! You can close this tab.',
        open_browser=False # Don't try to open a browser on the remote server
    )

    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("\n✅ token.json Generated Successfully!")

if __name__ == "__main__":
    get_creds()