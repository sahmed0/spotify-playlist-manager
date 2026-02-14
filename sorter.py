"""
Logic for categorisation of tracks based on genre mapping.
"""
import config

def categorise_tracks(tracks, track_tags_map):
    """
    Sort a list of tracks into buckets based on config.GENRE_MAPPING.

    Args:
        tracks: List of dicts, each must have 'name', 'id', 'uri', etc.
        track_tags_map: Dict mapping track_uri -> list of genre strings [Last.fm].

    Returns:
        Dict: { 'Bucket Name': [track_object, ...], ... }
    """
    # Initialise buckets
    sorted_playlists = {bucket: [] for bucket in config.GENRE_MAPPING.keys()}
    sorted_playlists[config.UNSORTED_PLAYLIST_NAME] = []
    
    for track in tracks:
        track_uri = track.get('uri')
        
        # Get tags from map (already populated with Track > Artist fallback)
        current_genres = track_tags_map.get(track_uri, [])
                
        # Flatten into a single string for easy substring matching
        # e.g. "rock classic rock pop"
        flat_genre_string = " ".join(current_genres).lower()
        
        matched_any = False

        for bucket_name, keywords in config.GENRE_MAPPING.items():
            # Check if any keyword for this bucket matches the track's genres
            match_found = False
            for keyword in keywords:
                if keyword in flat_genre_string:
                    match_found = True
                    break
            
            if match_found:
                sorted_playlists[bucket_name].append(track)
                matched_any = True
                
                # If STOP_AFTER_FIRST_MATCH is True, we stop after the first bucket match
                if config.STOP_AFTER_FIRST_MATCH:
                    break
        
        # If no buckets matched at all, add to Fallback
        if not matched_any:
            sorted_playlists[config.UNSORTED_PLAYLIST_NAME].append(track)
            
    return sorted_playlists
