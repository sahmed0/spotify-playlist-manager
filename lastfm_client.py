"""
Last.fm API client for fetching artist and track tags (genres).
This enriches the base track data with community-driven tags, allowing for 
more robust categorisation than Spotify's internal, opaque genre lists.
"""
import rate_limiter
import config
import urllib.parse
import app_state as state

class LastFMClient:
    """
    Client for interacting with the Last.fm API to fetch artist and track metadata.
    """
    def __init__(self):
        self.apiKey = config.LASTFM_API_KEY
        if not self.apiKey:
            raise ValueError("LASTFM_API_KEY not found in config. Please add it to your .env file.")
        self.baseUrl = "http://ws.audioscrobbler.com/2.0/"
        
        # Use dedicated rate limiter for Last.fm with retry logic
        self.session = rate_limiter.createResilientSession(bucket=rate_limiter.lastfmBucket)

        # Set user agent for identification with Last.fm API
        self.session.headers.update({
            "User-Agent": f"{config.APP_NAME}/{config.APP_VERSION}"
        })

    def fetchArtistTags(self, artistName):
        """
        Fetches the top tags (genres) for a given artist using Last.fm API.
        This provides a fallback set of genres when track-specific tags are unavailable.

        Returns:
            list: A list of tag names (strings).
        """
        try:
            encodedArtist = urllib.parse.quote(artistName)
            
            url = f"{self.baseUrl}?method=artist.gettoptags&artist={encodedArtist}&api_key={self.apiKey}&format=json"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"   Last.fm Error ({response.status_code}) for '{artistName}'")
                return []
                
            data = response.json()
            
            tags = []
            if 'toptags' in data and 'tag' in data['toptags']:
                tagList = data['toptags']['tag']
                if isinstance(tagList, dict):
                    tagList = [tagList]
                    
                for tag in tagList[:5]:
                    if 'name' in tag:
                        tags.append(tag['name'])
            
            return tags

        except Exception as e:
            print(f"   Last.fm Exception for '{artistName}': {e}")
            return []

    def fetchTrackTags(self, artistName, trackName):
        """
        Fetches top tags for a specific track.
        This yields the most precise categorisation based on community listening habits.

        Returns:
            list: A list of tags.
        """
        try:
            encodedArtist = urllib.parse.quote(artistName)
            encodedTrack = urllib.parse.quote(trackName)
            
            url = f"{self.baseUrl}?method=track.gettoptags&artist={encodedArtist}&track={encodedTrack}&api_key={self.apiKey}&format=json"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
                
            data = response.json()
            tags = []
            if 'toptags' in data and 'tag' in data['toptags']:
                tagList = data['toptags']['tag']
                if isinstance(tagList, dict):
                    tagList = [tagList]
                for tag in tagList[:5]:
                    if 'name' in tag:
                        tags.append(tag['name'])
            return tags
            
        except Exception as e:
            return []

def enrichTracks(songs):
    """
    Fetches genres from Last.fm for a list of songs.
    This optimises API usage by caching artist tags locally and applying them 
    when individual track lookups fail, significantly reducing network calls.
    
    Returns:
        dict: A map of {song_uri: [tags]}
    """
    trackTagsMap = {}
    
    if not songs:
        return trackTagsMap
        
    try:
        lastfm = LastFMClient()
        totalSongs = len(songs)
        
        # Sort songs by artist to allow grouping
        songs.sort(key=lambda s: s['artists'][0]['name'] if s['artists'] else "Unknown")
        
        currentArtistName = None
        currentArtistTags = []
        currentArtistSource = None 
        
        for i, song in enumerate(songs):
            songName = song['trackName']
            primaryArtist = song['artists'][0]['name'] if song['artists'] else "Unknown"
            
            if primaryArtist != currentArtistName:
                currentArtistName = primaryArtist
                cached = state.getArtistTags(primaryArtist)
                if cached is not None:
                     currentArtistTags = cached
                     currentArtistSource = "Artist (DB Cache)"
                else:
                    currentArtistTags = lastfm.fetchArtistTags(primaryArtist)
                    state.saveArtistTags(primaryArtist, currentArtistTags)
                    currentArtistSource = "Artist (API)"
            else:
                currentArtistSource = "Artist (Memory)"

            # 1. Try Track Tags
            tags = lastfm.fetchTrackTags(primaryArtist, songName)
            source = "Track"
            
            # 2. Fallback to stored Artist Tags
            if not tags:
                tags = currentArtistTags
                source = currentArtistSource
            
            trackTagsMap[song['trackUri']] = tags
            print(f"[{i+1}/{totalSongs}] {songName} ({primaryArtist}) -> {source}: {tags[:5]}...", end='\r')
            
    except Exception as e:
        print(f"\nLast.fm Error: {e}")
        
    return trackTagsMap
