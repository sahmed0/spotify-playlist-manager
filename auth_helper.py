"""
Authentication helper for Spotify OAuth.
"""
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config

def generate_token():
    """
    Run a local web server to handle the OAuth flow and print the Refresh Token.

    User needs to set CLIENT_ID and CLIENT_SECRET in .env or environment before running.
    """
    if not config.CLIENT_ID or not config.CLIENT_SECRET:
        print("Error: SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET must be set.")
        print("Please create a .env file or set them in your environment variables.")
        return

    sp_oauth = SpotifyOAuth(
        client_id=config.CLIENT_ID,
        client_secret=config.CLIENT_SECRET,
        redirect_uri=config.REDIRECT_URI,
        scope=config.SCOPE
    )

    print(f"""
    >>> Opening browser for Spotify Authentication...
    
    [Fallback URL]
    {sp_oauth.get_authorize_url()}
    """)

    # This will open the browser, ask the user to login, and then return the access token info
    # It automatically handles the local server part if redirect_uri is a loopback address (localhost or 127.0.0.1)
    token_info = sp_oauth.get_access_token(as_dict=True)
    
    if token_info:
        refresh_token = token_info.get('refresh_token')
        print("\n\nSUCCESS! Authentication complete.")
        print("-" * 60)
        print("Here is your REFRESH TOKEN. Save this as a GitHub Secret named 'REFRESH_TOKEN'.")
        print("-" * 60)
        print(refresh_token)
        print("-" * 60)
        
        # Asks to save to .env for local testing
        save = input("\nDo you want to append this REFRESH_TOKEN to your local .env file? (y/n): ")
        if save.lower() == 'y':
            with open(".env", "a") as f:
                f.write(f"\nSPOTIPY_REFRESH_TOKEN={refresh_token}")
            print("Saved to .env.")
    else:
        print("Authentication failed.")

if __name__ == "__main__":
    generate_token()
