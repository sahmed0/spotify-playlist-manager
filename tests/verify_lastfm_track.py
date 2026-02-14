import requests
import config
import urllib.parse

def test_track_tags():
    print("Testing Last.fm Track Tags...")
    
    if not config.LASTFM_API_KEY:
        print("ERROR: LASTFM_API_KEY is missing.")
        return

    base_url = "http://ws.audioscrobbler.com/2.0/"
    
    # Test Case: "Creep" by Radiohead
    artist = "Radiohead"
    track = "Creep"
    
    encoded_artist = urllib.parse.quote(artist)
    encoded_track = urllib.parse.quote(track)
    
    url = f"{base_url}?method=track.gettoptags&artist={encoded_artist}&track={encoded_track}&api_key={config.LASTFM_API_KEY}&format=json"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print(f"Status: {response.status_code}")
        
        tags = []
        if 'toptags' in data and 'tag' in data['toptags']:
            tag_list = data['toptags']['tag']
            if isinstance(tag_list, dict):
                tag_list = [tag_list]
            for tag in tag_list[:5]:
                tags.append(tag['name'])
                
        print(f"Tags for {artist} - {track}: {tags}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_track_tags()
