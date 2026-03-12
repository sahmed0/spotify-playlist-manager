"""
Configuration settings for the Spotify Liked Songs Organiser application.
This centralises all environment variables and categorisation rules to maintain 
a single source of truth for the sorting logic and API configurations.
"""
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

APP_NAME = "liked songs manager"
APP_VERSION = "2.0.0"

SCOPE = "user-library-read playlist-modify-private playlist-modify-public playlist-read-private"

# IF A SONG CANNOT BE CATEGORISED, WHY SHOULD WE ADD IT TO A PLAYLIST AT ALL? WASTE OF TIME AND API CALLS, AS THE SONG IS ALREADY IN THE 'LIKED SONGS' PLAYLIST.
SHOULD_STOP_AFTER_FIRST_MATCH = False

GENRE_MAPPING = {
    'Techno': ['techno', 'detroit techno', 'minimal techno', 'acid techno', 'dub techno', 'industrial techno']
}

UNSORTED_PLAYLIST_NAME = "Unsorted"

IS_DRY_RUN = False

# This maximum only applies to Last.fm (Spotify limit is defined by user in CLI)
MAX_TRACKS_TO_PROCESS = None

SHOULD_RESET_PLAYLIST_CACHE = False
