"""
Last.fm API client for fetching artist and track tags (genres).
"""
import requests
import config
import urllib.parse
import time

class LastFMClient:
    def __init__(self):
        self.api_key = config.LASTFM_API_KEY
        if not self.api_key:
            raise ValueError("LASTFM_API_KEY not found in config. Please add it to your .env file.")
        self.base_url = "http://ws.audioscrobbler.com/2.0/"

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
            
            response = requests.get(url, timeout=10)
            time.sleep(0.1) # Rate limiting
            
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
                    
                # Get top 10 tags
                for tag in tag_list[:10]:
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
            
            response = requests.get(url, timeout=10)
            time.sleep(0.1) # Rate limiting
            
            if response.status_code != 200:
                # 404/error is common for obscure tracks
                return []
                
            data = response.json()
            tags = []
            if 'toptags' in data and 'tag' in data['toptags']:
                tag_list = data['toptags']['tag']
                if isinstance(tag_list, dict):
                    tag_list = [tag_list]
                for tag in tag_list[:5]: # Take top 5 for track specificity
                    if 'name' in tag:
                        tags.append(tag['name'])
            return tags
            
        except Exception as e:
            # Silent fail for tracks -> fallback to artist
            return []
