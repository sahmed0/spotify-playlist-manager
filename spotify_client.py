import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config

class SpotifyClient:
    def __init__(self):
        # Initialise Spotipy
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config.CLIENT_ID,
            client_secret=config.CLIENT_SECRET,
            redirect_uri=config.REDIRECT_URI,
            scope=config.SCOPE,
            open_browser=False
        ))
        
        # Ensure token is valid (crucial for headless execution)
        if config.REFRESH_TOKEN:
            self._force_refresh_token()

    def _force_refresh_token(self):
        """
        Manually refreshes the access token using the REFRESH_TOKEN.
        This is crucial for long-running scripts or CI/CD where interactive login isn't possible.
        """
        try:
            auth_manager = self.sp.auth_manager
            # refresh_access_token returns the new token info
            new_token_info = auth_manager.refresh_access_token(config.REFRESH_TOKEN)
            self.sp = spotipy.Spotify(auth=new_token_info['access_token'])
            print("Successfully refreshed access token.")
        except Exception as e:
            print(f"Warning: Failed to refresh token explicitly: {e}")
            # We continue, maybe the existing cache/env is enough

    def fetch_current_user_saved_tracks(self):
        """
        Fetches all liked songs from the user's library.
        Returns a list of track objects (simplified).
        """
        results = []
        limit = 50
        offset = 0
        
        print("Fetching liked songs...")
        while True:
            try:
                response = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
                items = response['items']
                
                if not items:
                    break
                
                for item in items:
                    track = item['track']
                    # Keep only what we need to save memory
                    simple_track = {
                        'id': track['id'],
                        'name': track['name'],
                        'uri': track['uri'],
                        'added_at': item['added_at'], # Needed for incremental sync
                        # Capture album info for genre fallback
                        'album': {
                            'id': track['album']['id'],
                            'name': track['album']['name']
                        },
                        'artists': [{'id': a['id'], 'name': a['name']} for a in track['artists']]
                    }
                    results.append(simple_track)
                
                offset += limit
                print(f"Fetched {len(results)} songs...", end='\r')
                
                if response['next'] is None:
                    break
                    
                # Small sleep to be nice to API
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\nError fetching songs at offset {offset}: {e}")
                break
                
        print(f"\nTotal liked songs fetched: {len(results)}")
        return results

    def fetch_artist_genres_in_batches(self, artist_ids):
        """
        Fetches genre info for a list of artist IDs.
        Handles batching (max 50 per request).
        Returns: Dict { artist_id: [genre1, genre2, ...] }
        """
        artist_genres = {}
        unique_ids = list(set(artist_ids))
        total = len(unique_ids)
        batch_size = 50
        
        print(f"Fetching genres for {total} artists...")
        
        for i in range(0, total, batch_size):
            chunk = unique_ids[i:i + batch_size]
            try:
                # 2026 UPDATE: Artist Genres are deprecated/unreliable
                # Will still attempt to fetch them, but might get empty lists.
                response = self.sp.artists(chunk)
                for artist in response['artists']:
                    if artist:
                        genres = artist.get('genres', [])
                        if not genres:
                             pass
                        artist_genres[artist['id']] = genres
                
                print(f"Processed {min(i + batch_size, total)}/{total} artists...", end='\r')
                time.sleep(0.1)
            except Exception as e:
                print(f"\nError fetching artists batch: {e}")
                
        print("\nGenre fetching complete.")
        return artist_genres

    def fetch_album_genres_in_batches(self, album_ids):
        """
        Fetches genre info for a list of album IDs.
        Fallback strategy since artist genres are deprecated.
        """
        album_genres = {}
        unique_ids = list(set(album_ids))
        total = len(unique_ids)
        batch_size = 20 # Albums endpoint usually allows 20 per request
        
        print(f"Fetching genres for {total} albums (fallback)...")
        
        for i in range(0, total, batch_size):
            chunk = unique_ids[i:i + batch_size]
            try:
                response = self.sp.albums(chunk)
                for album in response['albums']:
                    if album:
                        album_genres[album['id']] = album.get('genres', [])
                        
                print(f"Processed {min(i + batch_size, total)}/{total} albums...", end='\r')
                time.sleep(0.1)
            except Exception as e:
               print(f"\nError fetching albums batch: {e}")
               
        return album_genres

    def get_current_user_id(self):
        return self.sp.current_user()['id']

    def create_playlist_for_current_user(self, name):
        """
        Creates a playlist for the CURRENT authenticated user.
        Uses POST /me/playlists (2026 compliant).
        """
        user_id = self.sp.me()['id'] # We need to fetch 'me' to be sure
                
        print(f"Creating new playlist: {name}")
        
        try:
             return self.sp.user_playlist_create(user_id, name, public=False, description=f"Auto-generated {name} playlist")['id']
        except Exception as e:
             print(f"Standard create failed ({e}), trying manual /me/playlists...")
             # Fallback to manual requests if spotipy fails
             payload = {
                 "name": name,
                 "public": False,
                 "description": f"Auto-generated {name} playlist"
             }
             return self.sp._post("me/playlists", payload=payload)['id']

    def get_or_create_playlist(self, name):
        """
        Finds a playlist by name for the user, or creates it if missing.
        Returns the playlist ID.
        """
        # First, search user's playlists
        limit = 50
        offset = 0
        target_name = name 
        
        while True:
            playlists = self.sp.current_user_playlists(limit=limit, offset=offset)
            for pl in playlists['items']:
                if pl['name'] == target_name:
                    return pl['id']
            
            if not playlists['next']:
                break
            offset += limit
            
        # If not found, create it
        return self.create_playlist_for_current_user(target_name)

    def get_playlist_tracks(self, playlist_id):
        """
        Fetches all track URIs currently in the playlist.
        Returns a Set of URIs for fast lookup.
        """
        existing_uris = set()
        limit = 100
        offset = 0
        
        while True:
            response = self.sp.playlist_items(playlist_id, fields="items(track(uri)),next", limit=limit, offset=offset)
            items = response['items']
            
            for item in items:
                # Sometimes track can be None if the song was removed from Spotify
                if item and item.get('track'):
                    existing_uris.add(item['track']['uri'])
                    
            if not response['next']:
                break
            offset += limit
            
        return existing_uris

    @staticmethod
    def identify_missing_tracks(new_tracks, existing_uris):
        return [uri for uri in new_tracks if uri not in existing_uris]

    def add_unique_tracks_to_playlist(self, playlist_id, track_uris):
        """
        Adds ONLY missing tracks to the playlist (Non-Destructive).
        Uses PUT /playlists/{id}/items (2026 compliant) equivalent or fallback.
        """
        if not track_uris:
            return

        # 1. Fetch what's already there
        existing_uris = self.get_playlist_tracks(playlist_id)
        
        # 2. Filter out duplicates
        new_uris = self.identify_missing_tracks(track_uris, existing_uris)
        
        if not new_uris:
            print("   -> No new tracks to add (all duplicates).")
            return

        print(f"   -> Adding {len(new_uris)} new tracks...")

        # 3. Add in batches
        batch_size = 100
        total = len(new_uris)
        
        for i in range(0, total, batch_size):
            chunk = new_uris[i:i + batch_size]
            try:                
                self.sp.playlist_add_items(playlist_id, chunk)
                time.sleep(0.2)
            except Exception as e:
                print(f"Standard add failed ({e})...")
                # Raises error if adding fails.
                raise e
