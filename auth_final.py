import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Must use Desktop credentials for this to work easily
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/calendar'] 

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, 
        scopes=SCOPES,
        redirect_uri='http://localhost:8081/'
    )

    # 1. Get the Auth URL
    auth_url, _ = flow.authorization_url(prompt='consent')
    print(f"\n1. Open this URL in your browser:\n{auth_url}")

    # 2. Get the redirect URL from the user
    print("\n2. Log in and 'Allow'. You will get a 'Site can't be reached' error on localhost.")
    print("3. COPY THE FULL URL from your browser's address bar (it starts with http://localhost:8081/...)")
    
    returned_url = input("\n4. Paste the FULL redirect URL here: ").strip()

    # 3. Exchange the URL for a token
    flow.fetch_token(authorization_response=returned_url)
    
    creds = flow.credentials
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("\n✅ SUCCESS! token.json has been generated.")

if __name__ == '__main__':
    main()