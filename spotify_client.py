"""
Spotify API client wrapper with rate limiting and state management.
"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config
import rate_limiter
import app_state as state

# Initialise a global leaky bucket
# VERY CAREFUL LIMIT: 5 requests per 30 seconds
bucket = rate_limiter.LeakyBucket(max_requests=5, time_window_seconds=30)

class SpotifyClient:
    """
    A wrapper around `spotipy.Spotify` that resiliently handles rate limits and session management.
    """
    def __init__(self, dry_run=False):
        self.session = rate_limiter.create_resilient_session()
        self.dry_run = dry_run
        self.playlist_cache = None # Cache for {name: id}
        
        # 2. Initialise Spotipy with custom session
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config.CLIENT_ID,
                client_secret=config.CLIENT_SECRET,
                redirect_uri=config.REDIRECT_URI,
                scope=config.SCOPE,
                open_browser=False
            ),
            requests_session=self.session
        )
        
        # Ensure token is valid (crucial for headless execution)
        if config.REFRESH_TOKEN:
            self._force_refresh_token()

    def _force_refresh_token(self):
        """
        Manually refresh the access token using the REFRESH_TOKEN.
        """
        try:
            auth_manager = self.sp.auth_manager
            new_token_info = auth_manager.refresh_access_token(config.REFRESH_TOKEN)
            self.sp.auth_manager = auth_manager
            self.sp = spotipy.Spotify(auth=new_token_info['access_token'], requests_session=self.session)
            
            print("Successfully refreshed access token.")
        except Exception as e:
            print(f"Warning: Failed to refresh token explicitly: {e}")

    @bucket
    def fetch_current_user_saved_tracks(self, max_tracks=None, cutoff_date=None, start_offset=0):
        """
        Fetch all liked songs from the user's library.
        
        Args:
            max_tracks (int): Maximum number of tracks to fetch.
            cutoff_date (str): ISO 8601 timestamp. If a track is older than this, stop fetching.
            start_offset (int): Offset to start fetching from (for incremental sync).
        """
        results = []
        if max_tracks:
            limit = min(50, max_tracks)
        else:
            limit = 50 # API limit for getting liked songs
            
        offset = start_offset
        
        print(f"Fetching liked songs starting from offset {offset}...")
        stop_fetching = False
        fully_synced = False
        
        while True:
            try:
                bucket.acquire()
                response = self.sp._get(f"me/tracks?limit={limit}&offset={offset}")
                items = response['items']
                
                if not items:
                    fully_synced = True # Reached end of library
                    break
                
                for item in items:
                    # Smart Fetching Check (Maintenance Mode)
                    if cutoff_date and item['added_at'] <= cutoff_date:
                        print(f"   -> Reached previously sync'd track ({item['added_at']}). Stopping fetch.")
                        stop_fetching = True
                        fully_synced = True # We are up to date
                        break
                        
                    track = item['track']
                    simple_track = {
                        'id': track['id'],
                        'name': track['name'],
                        'uri': track['uri'],
                        'added_at': item['added_at'], 
                        'album': {
                            'id': track['album']['id'],
                            'name': track['album']['name']
                        },
                        'artists': [{'id': a['id'], 'name': a['name']} for a in track['artists']]
                    }
                    results.append(simple_track)
                    
                    if max_tracks and len(results) >= max_tracks:
                        stop_fetching = True
                        break
                
                offset += len(items) # Advance offset by actual number of items fetched
                
                if stop_fetching:
                    break
                    
                print(f"Fetched {len(results)} songs... (Total offset: {offset})", end='\r')

                if response['next'] is None:
                    fully_synced = True
                    break
                    
            except Exception as e:
                print(f"\nError fetching songs at offset {offset}: {e}")
                break
                
        print(f"\nTotal liked songs fetched: {len(results)}")
        return results, offset, fully_synced

    @bucket
    def get_current_user_id(self):
        """Return the current user's Spotify ID."""
        return self.sp._get("me")['id']

    def create_playlist_for_current_user(self, name):
        """
        Create a new playlist for the current user.

        Args:
            name (str): The name of the playlist.
            
        Returns:
            str: The ID of the created playlist.
        """
        if self.dry_run:
            print(f"   [DRY RUN] Would create playlist '{name}'")
            return f"DRY_RUN_ID_{name}"

        user_id = self.get_current_user_id()  # Still fetch user ID for logging/verification if needed
        print(f"Creating new playlist: {name}")
        
        payload = {
            "name": name,
            "public": False,
            "description": f"Auto-generated {name} playlist"
        }
        
        playlist_id = None
        try:
             bucket.acquire()
             # Use /me/playlists directly as it is more robust and less prone to 403s
             playlist_id = self.sp._post("me/playlists", payload=payload)['id']
             
        except Exception as e:
             print(f"Creation failed for '{name}': {e}")
             # Do not retry locally; let it fail or return None so we can skip this playlist
             # If we retry blindly, we risk rate limits.
             return None
             
        # Save to persistent cache
        if playlist_id:
            state.cache_playlist(name, playlist_id)
            if self.playlist_cache is not None:
                self.playlist_cache[name] = playlist_id
                
        return playlist_id

    def refresh_playlist_cache(self, force=False):
        """
        Fetches all user playlists and caches them.
        
        Args:
            force (bool): If True, ignore DB cache and force fetch from API.
        """
        print("Building playlist cache...")
        
        # 1. Try loading from DB first
        if not force:
            db_cache = state.get_all_cached_playlists()
            if db_cache:
                self.playlist_cache = db_cache
                print(f"   Loaded {len(self.playlist_cache)} playlists from local database.")
                return

        # 2. Fetch from API if DB is empty or forced
        self.playlist_cache = {}
        limit = 50 # API limit for getting playlists
        offset = 0
        
        while True:
            print(f"   Fetching playlists from Spotify... (offset {offset})", end='\r')
            bucket.acquire()
            response = self.sp._get(f"me/playlists?limit={limit}&offset={offset}")
            
            for pl in response['items']:
                self.playlist_cache[pl['name']] = pl['id']
                
            if not response['next']:
                break
            offset += limit
            
        # 3. Save to DB
        print(f"\n   Cache built. Found {len(self.playlist_cache)} playlists. Saving to DB...")
        state.bulk_cache_playlists(self.playlist_cache)

    def get_or_create_playlist(self, name):
        """
        Find a playlist by name for the user, or create it if missing.
        Uses in-memory cache to avoid repeated API calls.
        """
        if self.playlist_cache is None:
            self.refresh_playlist_cache()
            
        # Check cache
        if name in self.playlist_cache:
            return self.playlist_cache[name]
            
        # If not found, create it
        new_id = self.create_playlist_for_current_user(name)
        
        # Update cache
        if not new_id.startswith("DRY_RUN_ID"):
             self.playlist_cache[name] = new_id
             
        return new_id

    def get_playlist_tracks(self, playlist_id):
        """
        Fetch all track URIs currently in the playlist.

        Checks Snapshot ID first to avoid unnecessary API calls.
        """
        if playlist_id.startswith("DRY_RUN_ID"):
             return set()

        # Check Snapshot ID
        bucket.acquire()
        response = self.sp._get(f"playlists/{playlist_id}?fields=snapshot_id")
        current_snapshot = response['snapshot_id']
        
        stored_snapshot = state.get_stored_snapshot_id(playlist_id)
                
        if current_snapshot == stored_snapshot:
            print(f"Snapshot match for {playlist_id} ({current_snapshot[:8]}...). Skipping fetch.")
            return None # Signal that we don't need to fetch
            
        # If different, we must fetch
        existing_uris = set()
        limit = 100 # API limit for getting playlist tracks
        offset = 0
        
        print(f"Snapshot changed or new. Fetching tracks for {playlist_id}...")
        
        while True:
            bucket.acquire()
            response = self.sp._get(f"playlists/{playlist_id}/items?fields=items(track(uri)),next&limit={limit}&offset={offset}")
            items = response['items']
            
            for item in items:
                if item and item.get('track'):
                    existing_uris.add(item['track']['uri'])
            
            # Show progress
            if offset > 0:
                 print(f"   Fetching playlist tracks... ({len(existing_uris)} found)", end='\r')

            if not response['next']:
                break
            offset += limit
            
        if not self.dry_run:
            state.update_snapshot_id(playlist_id, current_snapshot)
            
        return existing_uris

    @staticmethod
    def identify_missing_tracks(new_tracks, existing_uris):
        """Return a list of track URIs that are in new_tracks but not in existing_uris."""
        if existing_uris is None:
            pass
        return [uri for uri in new_tracks if uri not in (existing_uris or set())]

    def add_unique_tracks_to_playlist(self, playlist_id, track_uris):
        """
        Add ONLY missing tracks to the playlist.
        """
        if not track_uris:
            return        
        
        existing_uris_in_playlist = self.get_playlist_tracks(playlist_id)        
        to_add = []
        if existing_uris_in_playlist is None:
            to_add = track_uris
        else:
            to_add = [uri for uri in track_uris if uri not in existing_uris_in_playlist]
        
        if not to_add:
            print("   -> No new tracks to add.")
            return

        if self.dry_run:
            print(f"   [DRY RUN] Would add {len(to_add)} new tracks to {playlist_id}...")
            # We don't save state in dry run
            return

        print(f"   -> Adding {len(to_add)} new tracks...")

        # Batch Processing (Up to 100 tracks per request)
        batch_size = 100 # API limit for adding tracks to playlist
        total_added = 0
        
        for i in range(0, len(to_add), batch_size):
            batch = to_add[i : i + batch_size]
            try:
                bucket.acquire()
                payload = {"uris": batch}
                # Explicitly use the 'items' endpoint
                self.sp._post(f"playlists/{playlist_id}/items", payload=payload)
                
                total_added += len(batch)
                print(f"   -> Added batch {i//batch_size + 1} ({len(batch)} songs)...")
                
            except Exception as e:
                print(f"\nError adding batch to {playlist_id}: {e}")
