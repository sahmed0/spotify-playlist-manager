"""
Last.fm API client for fetching artist and track tags (genres).
"""
import rate_limiter
import config
import urllib.parse
import app_state as state

class LastFMClient:
    def __init__(self):
        self.api_key = config.LASTFM_API_KEY
        if not self.api_key:
            raise ValueError("LASTFM_API_KEY not found in config. Please add it to your .env file.")
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        
        # Use dedicated rate limiter for Last.fm (4 req/sec) with retry logic
        self.session = rate_limiter.create_resilient_session(bucket=rate_limiter.lastfm_bucket)

    def fetch_artist_tags(self, artist_name):
        """
        Fetch the top tags (genres) for a given artist using Last.fm API.

        Returns:
            list: A list of tag names (strings).
        """
        try:
            # URL Encoded artist name
            encoded_artist = urllib.parse.quote(artist_name)
            
            url = f"{self.base_url}?method=artist.gettoptags&artist={encoded_artist}&api_key={self.api_key}&format=json"
            
            # Use resilient session (Bucket handles rate limit, Adapter handles retries)
            response = self.session.get(url, timeout=10)
            
            # Check for HTTP errors
            if response.status_code != 200:
                print(f"   Last.fm Error ({response.status_code}) for '{artist_name}'")
                return []
                
            data = response.json()
            
            # Parse response
            # Structure: { "toptags": { "tag": [ { "name": "rock", ... }, ... ] } }
            tags = []
            if 'toptags' in data and 'tag' in data['toptags']:
                tag_list = data['toptags']['tag']
                # Ensure it's a list (single tag might be a dict)
                if isinstance(tag_list, dict):
                    tag_list = [tag_list]
                    
                # Get top 3 artist tags
                for tag in tag_list[:3]:
                    if 'name' in tag:
                        tags.append(tag['name'])
            
            return tags

        except Exception as e:
            print(f"   Last.fm Exception for '{artist_name}': {e}")
            return []

    def fetch_track_tags(self, artist_name, track_name):
        """
        Fetch top tags for a specific track.

        Returns:
            list: A list of tags.
        """
        try:
            encoded_artist = urllib.parse.quote(artist_name)
            encoded_track = urllib.parse.quote(track_name)
            
            url = f"{self.base_url}?method=track.gettoptags&artist={encoded_artist}&track={encoded_track}&api_key={self.api_key}&format=json"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                # 404/error is common for obscure tracks
                return []
                
            data = response.json()
            tags = []
            if 'toptags' in data and 'tag' in data['toptags']:
                tag_list = data['toptags']['tag']
                if isinstance(tag_list, dict):
                    tag_list = [tag_list]
                for tag in tag_list[:3]: # Take top 3 for track specificity
                    if 'name' in tag:
                        tags.append(tag['name'])
            return tags
            

        except Exception as e:
            # Silent fail for tracks -> fallback to artist
            return []

def enrich_tracks(songs):
    """
    Fetch genres from Last.fm for a list of songs.
    
    Optimises API usage by:
    1. Sorting songs by artist.
    2. Fetching artist tags only once per artist (batching).
    
    Returns:
        dict: A map of {song_uri: [tags]}
    """
    track_tags_map = {}
    
    if not songs:
        return track_tags_map
        
    try:
        lastfm = LastFMClient()
        total_songs = len(songs)
        
        # Sort songs by artist to allow grouping
        songs.sort(key=lambda s: s['artists'][0]['name'] if s['artists'] else "Unknown")
        
        # Use flat loop for progress tracking, but manage artist state manually
        current_artist_name = None
        current_artist_tags = []
        current_artist_source = None # For logging
        
        for i, song in enumerate(songs):
            song_name = song['name']
            primary_artist = song['artists'][0]['name'] if song['artists'] else "Unknown"
            
            # Check if we switched artists
            if primary_artist != current_artist_name:
                current_artist_name = primary_artist
                # Fetch artist tags ONCE for this new group
                cached = state.get_artist_tags(primary_artist)
                if cached is not None:
                     current_artist_tags = cached
                     current_artist_source = "Artist (DB Cache)"
                else:
                    current_artist_tags = lastfm.fetch_artist_tags(primary_artist)
                    state.save_artist_tags(primary_artist, current_artist_tags)
                    current_artist_source = "Artist (API)"
            else:
                current_artist_source = "Artist (Memory)"

            # 1. Try Track Tags
            tags = lastfm.fetch_track_tags(primary_artist, song_name)
            source = "Track"
            
            # 2. Fallback to stored Artist Tags
            if not tags:
                tags = current_artist_tags
                source = current_artist_source
            
            track_tags_map[song['uri']] = tags
            print(f"[{i+1}/{total_songs}] {song_name} ({primary_artist}) -> {source}: {tags[:3]}...", end='\\r')
            
    except Exception as e:
        print(f"\\nLast.fm Error: {e}")
        
    return track_tags_map
