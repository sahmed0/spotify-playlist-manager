"""
Authentication helper for Spotify OAuth using raw requests.
This ensures the system can manually manage scopes and refresh tokens 
without relying on heavy third-party authentication wrappers.
"""
import os
import requests
import urllib.parse
import base64
import config

def generateAuthUrl():
    """
    Generates the Spotify Authorization URL.
    This is necessary to prompt the user to manually authorise the application permissions.
    """
    baseUrl = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": config.CLIENT_ID,
        "response_type": "code",
        "redirect_uri": config.REDIRECT_URI,
        "scope": config.SCOPE
    }
    urlParams = urllib.parse.urlencode(params)
    return f"{baseUrl}?{urlParams}"

def getTokensFromCode(code):
    """
    Exchanges an authorization code for an access token and refresh token.
    This facilitates the final step of the OAuth loop to establish a persistent session.
    """
    url = "https://accounts.spotify.com/api/token"
    
    authStr = f"{config.CLIENT_ID}:{config.CLIENT_SECRET}"
    authB64 = base64.b64encode(authStr.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {authB64}"
    }

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.REDIRECT_URI
    }

    print("   [API] accounts.spotify.POST -> api/token (authorization_code)")
    response = requests.post(url, data=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching tokens: {response.status_code} - {response.text}")
        return None

def generateToken():
    """
    Handles the manual OAuth flow and prints the Refresh Token.
    This allows the user to perform the one-time setup required to run automated syncs later.
    """
    if not config.CLIENT_ID or not config.CLIENT_SECRET:
        print("Error: SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET must be set.")
        print("Please create a .env file or set them in your environment variables.")
        return

    authUrl = generateAuthUrl()
    
    print(f"""
    >>> Manual Spotify Authentication...
    
    1. Open this URL in your browser:
       {authUrl}
       
    2. Authorize the application.
    3. You will be redirected to a URL that looks like: {config.REDIRECT_URI}?code=XXXXXX
    4. Copy the ENTIRE redirected URL and paste it below.
    """)

    redirectInput = input("Enter the redirected URL: ").strip()
    
    code = redirectInput
    if "code=" in redirectInput:
        parsedUrl = urllib.parse.urlparse(redirectInput)
        queryParams = urllib.parse.parse_qs(parsedUrl.query)
        if "code" in queryParams:
            code = queryParams["code"][0]
            
    if not code:
        print("No code provided. Authentication failed.")
        return

    tokenInfo = getTokensFromCode(code)
    
    if tokenInfo and 'refresh_token' in tokenInfo:
        refreshToken = tokenInfo['refresh_token']
        print("\n\nSUCCESS! Authentication complete.")
        print("-" * 60)
        print("Here is your REFRESH TOKEN. Save this in your .env file or as a GitHub Secret named 'REFRESH_TOKEN'.")
        print("-" * 60)
        print(refreshToken)
        print("-" * 60)
        
        saveChoice = input("\nDo you want to append/update this REFRESH_TOKEN in your local .env file? (y/n): ")
        if saveChoice.lower() == 'y':
            updateEnvFile("SPOTIPY_REFRESH_TOKEN", refreshToken)
            print("Successfully updated .env file.")
    else:
        print("Authentication failed.")

def updateEnvFile(key, value):
    """
    Updates or appends a key-value pair in the .env file.
    This automates the configuration persistence so the user does not have to manually edit files.
    """
    envFile = ".env"
    lines = []
    hasUpdated = False
    
    if os.path.exists(envFile):
        with open(envFile, "r") as f:
            lines = f.readlines()
            
    with open(envFile, "w") as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                hasUpdated = True
            else:
                f.write(line)
        if not hasUpdated:
            if lines and not lines[-1].endswith("\n"):
                f.write("\n")
            f.write(f"{key}={value}\n")

if __name__ == "__main__":
    generateToken()
